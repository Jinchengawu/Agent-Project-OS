"""Deterministic cadence plans designed to be awakened by external schedulers."""

import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List

from .organization import due_projects, load_organization, parse_timestamp
from .records import read_json, utc_now, write_json


MAX_ATTEMPTS = 3


def safe_fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def cadence_directory(root: Path) -> Path:
    return root / ".agent-project" / "cadence"


def run_path(root: Path, run_id: str) -> Path:
    return cadence_directory(root) / "cadence-run-{}.json".format(safe_fragment(run_id))


def list_runs(root: Path) -> List[Dict[str, Any]]:
    if not cadence_directory(root).exists():
        return []
    return [read_json(path) for path in sorted(cadence_directory(root).glob("cadence-run-*.json"))]


def dedupe_key(root: Path, window_start: str, window_end: str) -> str:
    organization_id = str(load_organization(root)["organization_id"])
    raw = "{}\0{}\0{}".format(organization_id, window_start, window_end).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def plan_run(
    root: Path,
    run_id: str,
    window_start: str,
    window_end: str,
    as_of: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    start = parse_timestamp(window_start)
    end = parse_timestamp(window_end)
    moment = parse_timestamp(as_of)
    if end <= start:
        raise ValueError("cadence window end must be after its start")
    if moment < start or moment > end:
        raise ValueError("cadence as-of must fall inside the requested window")
    key = dedupe_key(root, window_start, window_end)
    for existing in list_runs(root):
        if existing.get("dedupe_key") == key:
            return existing
    if run_path(root, run_id).exists():
        raise ValueError("cadence run id already exists with a different window")
    actions = []
    for item in due_projects(root, as_of):
        action_id = "supervision-{}-{}".format(item["project_id"], safe_fragment(str(item["due_at"])))
        actions.append(
            {
                "action_id": action_id,
                "kind": "supervision_dispatch",
                "project_id": item["project_id"],
                "assigned_to": item["pm_agent_id"],
                "due_at": item["due_at"],
                "status": "planned",
                "attempts": [],
            }
        )
    run = {
        "$schema": "https://agent-project-os.org/schemas/cadence-run-v1.schema.json",
        "protocol_version": "1.0",
        "run_id": run_id,
        "organization_id": load_organization(root)["organization_id"],
        "window_start": window_start,
        "window_end": window_end,
        "as_of": as_of,
        "dedupe_key": key,
        "status": "planned",
        "actions": actions,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_json(run_path(root, run_id), run, dry_run)
    return run


def get_run(root: Path, run_id: str) -> Dict[str, Any]:
    return read_json(run_path(root, run_id))


def record_attempt(
    root: Path,
    run_id: str,
    action_id: str,
    result: str,
    result_ref: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    run = get_run(root, run_id)
    if run.get("status") in {"completed", "failed"}:
        raise ValueError("cadence run is already closed")
    action = next((item for item in run.get("actions", []) if item.get("action_id") == action_id), None)
    if not action:
        raise ValueError("unknown cadence action: {}".format(action_id))
    attempts = action.setdefault("attempts", [])
    if len(attempts) >= MAX_ATTEMPTS:
        raise ValueError("cadence action reached retry limit {}".format(MAX_ATTEMPTS))
    if action.get("status") == "succeeded":
        raise ValueError("cadence action already succeeded")
    attempts.append(
        {
            "attempt": len(attempts) + 1,
            "result": result,
            "result_ref": result_ref,
            "recorded_at": utc_now(),
        }
    )
    action["status"] = result
    run["status"] = "running"
    run["updated_at"] = utc_now()
    write_json(run_path(root, run_id), run, dry_run)
    return run


def close_run(root: Path, run_id: str, outcome: str, dry_run: bool = False) -> Dict[str, Any]:
    run = get_run(root, run_id)
    if run.get("status") in {"completed", "failed"}:
        raise ValueError("cadence run is already closed")
    actions = run.get("actions", [])
    if outcome == "completed" and any(item.get("status") != "succeeded" for item in actions):
        raise ValueError("completed cadence run requires every action to succeed")
    run["status"] = outcome
    run["closed_at"] = utc_now()
    run["updated_at"] = utc_now()
    write_json(run_path(root, run_id), run, dry_run)
    return run


def validate_cadence(root: Path) -> List[str]:
    errors: List[str] = []
    keys = set()
    for run in list_runs(root):
        key = run.get("dedupe_key")
        if key in keys:
            errors.append("duplicate cadence window: {}".format(key))
        keys.add(key)
        action_ids = set()
        for action in run.get("actions", []):
            action_id = action.get("action_id")
            if action_id in action_ids:
                errors.append("cadence run {} has duplicate action {}".format(run.get("run_id"), action_id))
            action_ids.add(action_id)
            if len(action.get("attempts", [])) > MAX_ATTEMPTS:
                errors.append("cadence action {} exceeds retry limit".format(action_id))
    return errors
