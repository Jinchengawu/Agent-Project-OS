"""Deterministic validation for the repo-native record set.

The JSON Schemas are the interchange contract. This module provides a standard-library
runtime validator so the CLI remains usable without network access or third-party packages.
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set

from .records import (
    BLOCKER_TYPES,
    DECISION_STATES,
    EVIDENCE_GRADES,
    TASK_STATES,
    accepted_task_evidence,
    read_json,
)


PROTOCOL_VERSION = "1.0"


def required(record: Dict[str, Any], names: Sequence[str], label: str, errors: List[str]) -> None:
    for name in names:
        if name not in record or record[name] in (None, ""):
            errors.append("{}: missing required field '{}'".format(label, name))


def validate_runtime_identity(value: Any, label: str, errors: List[str]) -> None:
    if not isinstance(value, dict):
        errors.append("{}: runtime_identity must be an object".format(label))
        return
    required(value, ("runtime", "client_version"), "{} runtime_identity".format(label), errors)


def load_records(directory: Path, label: str, errors: List[str]) -> List[Dict[str, Any]]:
    records = []
    if not directory.exists():
        errors.append("missing directory: {}".format(directory))
        return records
    for path in sorted(directory.glob("*.json")):
        try:
            record = read_json(path)
        except ValueError as error:
            errors.append(str(error))
            continue
        if record.get("protocol_version") != PROTOCOL_VERSION:
            errors.append("{} {}: incompatible protocol_version {!r}".format(label, path.name, record.get("protocol_version")))
        record["__path"] = str(path)
        records.append(record)
    return records


def validate_project(root: Path) -> List[str]:
    errors: List[str] = []
    control = root / ".agent-project"
    try:
        manifest = read_json(control / "manifest.json")
    except ValueError as error:
        return [str(error)]
    required(
        manifest,
        ("protocol_version", "project_id", "name", "owner", "lifecycle", "repository", "verification"),
        "manifest",
        errors,
    )
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        errors.append("manifest: incompatible protocol_version {!r}".format(manifest.get("protocol_version")))

    try:
        policy = read_json(control / "policy.json")
        required(policy, ("protocol_version", "acceptance", "human_gates"), "policy", errors)
    except ValueError as error:
        errors.append(str(error))

    tasks = load_records(control / "tasks", "task", errors)
    task_ids: Set[str] = set()
    for task in tasks:
        label = "task {}".format(task.get("task_id", task.get("__path")))
        required(task, ("task_id", "title", "status", "owner", "acceptance_criteria", "evidence_refs"), label, errors)
        task_id = task.get("task_id")
        if isinstance(task_id, str):
            if task_id in task_ids:
                errors.append("{}: duplicate task id".format(label))
            task_ids.add(task_id)
        if task.get("status") not in TASK_STATES:
            errors.append("{}: unknown status {!r}".format(label, task.get("status")))
        blocker = task.get("blocker")
        if task.get("status") == "blocked":
            if not isinstance(blocker, dict) or blocker.get("type") not in BLOCKER_TYPES:
                errors.append("{}: blocked task requires a typed blocker".format(label))

    evidence = load_records(control / "evidence", "evidence", errors)
    evidence_ids: Set[str] = set()
    for item in evidence:
        label = "evidence {}".format(item.get("evidence_id", item.get("__path")))
        required(
            item,
            ("evidence_id", "task_id", "grade", "kind", "summary", "acceptance_status", "runtime_identity"),
            label,
            errors,
        )
        evidence_id = item.get("evidence_id")
        if isinstance(evidence_id, str):
            evidence_ids.add(evidence_id)
        if item.get("task_id") not in task_ids:
            errors.append("{}: references unknown task {!r}".format(label, item.get("task_id")))
        if item.get("grade") not in EVIDENCE_GRADES:
            errors.append("{}: unknown evidence grade {!r}".format(label, item.get("grade")))
        validate_runtime_identity(item.get("runtime_identity"), label, errors)
        if item.get("grade") == "E2":
            verification = item.get("verification")
            required_verification = ("command", "result", "executor", "exit_code", "executed_at", "duration_ms", "output_sha256")
            if (
                not isinstance(verification, dict)
                or any(name not in verification for name in required_verification)
                or verification.get("result") != "passed"
                or verification.get("exit_code") != 0
            ):
                errors.append("{}: E2 requires verification executed by a declared executor with exit code 0".format(label))
        if item.get("grade") == "E3" and not item.get("receipt_ref"):
            errors.append("{}: E3 requires receipt_ref".format(label))

    for task in tasks:
        if task.get("status") == "done":
            qualifying = accepted_task_evidence(root, str(task.get("task_id")), "E2")
            if not qualifying:
                errors.append("task {}: done requires accepted E2 or stronger evidence".format(task.get("task_id")))
            missing_refs = sorted(set(task.get("evidence_refs", [])) - evidence_ids)
            if missing_refs:
                errors.append("task {}: unknown evidence refs {}".format(task.get("task_id"), missing_refs))

    decisions = load_records(control / "decisions", "decision", errors)
    decision_ids = {str(item.get("decision_id")) for item in decisions if item.get("decision_id")}
    for item in decisions:
        label = "decision {}".format(item.get("decision_id", item.get("__path")))
        required(item, ("decision_id", "title", "status", "context", "decision", "rationale", "created_by"), label, errors)
        if item.get("status") not in DECISION_STATES:
            errors.append("{}: unknown status {!r}".format(label, item.get("status")))
        if item.get("status") == "superseded" and item.get("superseded_by") not in decision_ids:
            errors.append("{}: superseded decision requires a known superseded_by".format(label))

    handoffs = load_records(control / "handoffs", "handoff", errors)
    for item in handoffs:
        label = "handoff {}".format(item.get("handoff_id", item.get("__path")))
        required(
            item,
            ("handoff_id", "project_id", "from_actor", "to_actor", "goal", "completed", "next_actions", "runtime_identity"),
            label,
            errors,
        )
        if item.get("project_id") != manifest.get("project_id"):
            errors.append("{}: project_id does not match manifest".format(label))
        validate_runtime_identity(item.get("runtime_identity"), label, errors)

    receipts = load_records(control / "receipts", "receipt", errors)
    receipt_ids = {str(item.get("receipt_id")) for item in receipts if item.get("receipt_id")}
    for item in receipts:
        label = "receipt {}".format(item.get("receipt_id", item.get("__path")))
        required(
            item,
            ("receipt_id", "producer", "consumer", "artifact", "acceptance_status", "evidence_refs", "created_at"),
            label,
            errors,
        )
        artifact = item.get("artifact")
        if not isinstance(artifact, dict) or not all(artifact.get(key) for key in ("commit", "sha256", "protocol_version")):
            errors.append("{}: artifact requires commit, sha256, and protocol_version".format(label))

    for item in evidence:
        if item.get("grade") == "E3" and item.get("receipt_ref") not in receipt_ids:
            errors.append("evidence {}: receipt_ref is unknown".format(item.get("evidence_id")))

    inbox = load_records(control / "inbox", "change request", errors)
    for item in inbox:
        label = "change request {}".format(item.get("request_id", item.get("__path")))
        required(item, ("request_id", "operation", "entity_type", "entity_id", "patch", "status", "runtime_identity"), label, errors)
        validate_runtime_identity(item.get("runtime_identity"), label, errors)

    events = load_records(control / "events", "event", errors)
    for item in events:
        if item.get("adapter_event_id"):
            label = "adapter event {}".format(item.get("adapter_event_id"))
            required(
                item,
                ("adapter_event_id", "adapter", "normalized_event", "session_id", "runtime_identity", "payload", "occurred_at"),
                label,
                errors,
            )
            if item.get("adapter") not in {"codex", "claude-code", "deepseek-harness"}:
                errors.append("{}: unknown adapter {!r}".format(label, item.get("adapter")))
        else:
            label = "event {}".format(item.get("event_id", item.get("__path")))
            required(item, ("event_id", "event_type", "entity", "actor", "runtime_identity", "occurred_at"), label, errors)
        validate_runtime_identity(item.get("runtime_identity"), label, errors)

    return errors
