"""Repo-native records and lifecycle rules."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Iterable, List, Optional
import uuid


TASK_STATES = {
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "waiting_review",
    "done",
    "paused",
    "cancelled",
}

TASK_TRANSITIONS = {
    "planned": {"ready", "paused", "cancelled"},
    "ready": {"in_progress", "paused", "cancelled"},
    "in_progress": {"blocked", "waiting_review", "paused", "cancelled"},
    "blocked": {"in_progress", "paused", "cancelled"},
    "waiting_review": {"in_progress", "blocked", "done", "paused", "cancelled"},
    "done": {"in_progress"},
    "paused": {"planned", "ready", "in_progress", "cancelled"},
    "cancelled": set(),
}

DECISION_STATES = {"proposed", "accepted", "rejected", "superseded"}
EVIDENCE_GRADES = {"E0", "E1", "E2", "E3", "E4"}
BLOCKER_TYPES = {"dependency", "needs_input", "capability", "transient", "risk_gate"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("record not found: {}".format(path))
    except json.JSONDecodeError as error:
        raise ValueError("invalid JSON in {}: {}".format(path, error))
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object: {}".format(path))
    return value


def write_json(path: Path, value: Dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent), prefix=".agent-project-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def require_project(root: Path) -> Dict[str, Any]:
    return read_json(root / ".agent-project" / "manifest.json")


def runtime_identity(args: Any) -> Dict[str, Any]:
    identity = {
        "runtime": getattr(args, "runtime", None) or "manual",
        "client_version": getattr(args, "client_version", None) or "unknown",
    }
    if getattr(args, "model_id", None):
        identity["model_id"] = args.model_id
    if getattr(args, "provider_hint", None):
        identity["provider_hint"] = args.provider_hint
    return identity


def record_event(
    root: Path,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    runtime: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    now = utc_now()
    event_id = "event-{}".format(uuid.uuid4().hex)
    event = {
        "$schema": "https://agent-project-os.org/schemas/activity-event-v1.schema.json",
        "protocol_version": "1.0",
        "event_id": event_id,
        "event_type": event_type,
        "entity": {"type": entity_type, "id": entity_id},
        "actor": actor,
        "runtime_identity": runtime,
        "payload": payload or {},
        "occurred_at": now,
    }
    write_json(root / ".agent-project" / "events" / "{}.json".format(event_id), event, dry_run)
    return event


def validate_transition(current: str, target: str) -> None:
    if target not in TASK_STATES:
        raise ValueError("unknown task status: {}".format(target))
    if current == target:
        return
    if target not in TASK_TRANSITIONS.get(current, set()):
        raise ValueError("invalid task transition: {} -> {}".format(current, target))


def accepted_task_evidence(root: Path, task_id: str, minimum_grade: str = "E2") -> List[str]:
    grade_order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}
    found = []
    evidence_dir = root / ".agent-project" / "evidence"
    if not evidence_dir.exists():
        return found
    for path in sorted(evidence_dir.glob("*.json")):
        record = read_json(path)
        if (
            record.get("task_id") == task_id
            and record.get("acceptance_status") == "accepted"
            and grade_order.get(str(record.get("grade")), -1) >= grade_order[minimum_grade]
        ):
            found.append(str(record.get("evidence_id")))
    return found


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()
