"""Command line interface for Agent Project OS."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, Optional

from .records import (
    EVIDENCE_GRADES,
    accepted_task_evidence,
    read_json,
    record_event,
    require_project,
    runtime_identity,
    utc_now,
    validate_transition,
    write_json,
)
from .validation import validate_project
from .federation import (
    affected_projects,
    load_portfolio,
    new_portfolio,
    portfolio_path,
    projects_by_id,
    rebuild_index,
    validate_portfolio,
)
from .adapters import ADAPTERS, doctor as adapter_doctor, render_adapters, uninstall_adapters


PROJECT_DIRS = (
    "tasks",
    "evidence",
    "decisions",
    "handoffs",
    "inbox",
    "receipts",
    "events",
)


def json_bytes(value: Dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def emit(payload: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(payload.get("message", payload.get("status", "ok")))


def build_init_files(project_id: str, name: str) -> Dict[str, bytes]:
    now = utc_now()
    manifest = {
        "$schema": "https://agent-project-os.org/schemas/project-manifest-v1.schema.json",
        "protocol_version": "1.0",
        "project_id": project_id,
        "name": name,
        "owner": "human",
        "lifecycle": "active",
        "repository": {"url": None, "default_branch": "main"},
        "verification": [],
        "created_at": now,
        "updated_at": now,
    }
    policy = {
        "$schema": "https://agent-project-os.org/schemas/project-policy-v1.schema.json",
        "protocol_version": "1.0",
        "acceptance": {"default": "human_review", "allow_agent_e2": True},
        "human_gates": ["irreversible", "production", "permissions", "funds", "public_release"],
    }
    agents = """# Agent Project OS\n\nThis repository uses Agent Project OS.\n\n- Treat Git-tracked project files as the portable source of truth.\n- Submit structured proposals to `.agent-project/inbox/`.\n- Do not mark work done without accepted evidence.\n- Keep irreversible, production, permission, financial, and public-release actions behind human approval.\n- Record runtime, client version, and model identity separately.\n"""
    return {
        "AGENTS.md": agents.encode("utf-8"),
        ".agent-project/manifest.json": json_bytes(manifest),
        ".agent-project/policy.json": json_bytes(policy),
    }


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    files = build_init_files(args.project_id, args.name)
    conflicts = sorted(relative for relative in files if (root / relative).exists())
    if conflicts:
        raise ValueError("refusing to overwrite existing files: {}".format(", ".join(conflicts)))
    planned = sorted(files)
    planned.extend(".agent-project/{}/".format(name) for name in PROJECT_DIRS)
    if not args.dry_run:
        for directory in PROJECT_DIRS:
            (root / ".agent-project" / directory).mkdir(parents=True, exist_ok=True)
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    emit(
        {
            "status": "planned" if args.dry_run else "created",
            "project_id": args.project_id,
            "root": str(root),
            "paths": planned,
            "message": "initialized {}".format(args.project_id),
        },
        args.json,
    )
    return 0


def task_path(root: Path, task_id: str) -> Path:
    return root / ".agent-project" / "tasks" / "{}.json".format(task_id)


def cmd_task_create(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    path = task_path(root, args.task_id)
    if path.exists():
        raise ValueError("task already exists: {}".format(args.task_id))
    now = utc_now()
    task = {
        "$schema": "https://agent-project-os.org/schemas/task-v1.schema.json",
        "protocol_version": "1.0",
        "task_id": args.task_id,
        "title": args.title,
        "description": args.description or "",
        "status": "planned",
        "priority": args.priority,
        "owner": args.owner,
        "acceptance_criteria": list(args.acceptance),
        "evidence_refs": [],
        "blocker": None,
        "created_at": now,
        "updated_at": now,
    }
    write_json(path, task, args.dry_run)
    record_event(
        root,
        "task.created",
        "task",
        args.task_id,
        args.actor,
        runtime_identity(args),
        {"status": "planned"},
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "created", "task": task, "message": "created task {}".format(args.task_id)}, args.json)
    return 0


def cmd_task_update(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    path = task_path(root, args.task_id)
    task = read_json(path)
    previous = str(task.get("status"))
    target = args.status or previous
    validate_transition(previous, target)
    if target == "blocked" and not args.blocker_type:
        raise ValueError("blocked tasks require --blocker-type")
    if target == "done":
        qualifying_refs = accepted_task_evidence(root, args.task_id, "E2")
        if not qualifying_refs:
            raise ValueError("task cannot enter done without accepted E2 or stronger evidence")
        task["evidence_refs"] = sorted(set(task.get("evidence_refs", [])) | set(accepted_task_evidence(root, args.task_id, "E0")))
    if args.title:
        task["title"] = args.title
    task["status"] = target
    task["updated_at"] = utc_now()
    if target == "blocked":
        task["blocker"] = {"type": args.blocker_type, "summary": args.blocker_summary or ""}
    elif previous == "blocked" and target != "blocked":
        task["blocker"] = None
    write_json(path, task, args.dry_run)
    record_event(
        root,
        "task.updated",
        "task",
        args.task_id,
        args.actor,
        runtime_identity(args),
        {"from": previous, "to": target},
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "updated", "task": task, "message": "updated task {}".format(args.task_id)}, args.json)
    return 0


def cmd_task_submit(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    task = read_json(task_path(root, args.task_id))
    request_path = root / ".agent-project" / "inbox" / "{}.json".format(args.request_id)
    if request_path.exists():
        raise ValueError("change request already exists: {}".format(args.request_id))
    patch: Dict[str, Any] = {}
    if args.status:
        validate_transition(str(task.get("status")), args.status)
        patch["status"] = args.status
    if args.title:
        patch["title"] = args.title
    if args.description is not None:
        patch["description"] = args.description
    if not patch:
        raise ValueError("task submission requires at least one proposed field")
    now = utc_now()
    request = {
        "$schema": "https://agent-project-os.org/schemas/change-request-v1.schema.json",
        "protocol_version": "1.0",
        "request_id": args.request_id,
        "operation": "update",
        "entity_type": "task",
        "entity_id": args.task_id,
        "base_updated_at": task.get("updated_at"),
        "patch": patch,
        "status": "pending_review",
        "submitted_by": args.actor,
        "runtime_identity": runtime_identity(args),
        "created_at": now,
        "updated_at": now,
    }
    write_json(request_path, request, args.dry_run)
    record_event(
        root,
        "change_request.submitted",
        "change_request",
        args.request_id,
        args.actor,
        runtime_identity(args),
        {"entity_type": "task", "entity_id": args.task_id},
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "submitted", "request": request, "message": "submitted {}".format(args.request_id)}, args.json)
    return 0


def cmd_task_review(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    request_path = root / ".agent-project" / "inbox" / "{}.json".format(args.request_id)
    request = read_json(request_path)
    if request.get("entity_type") != "task" or request.get("operation") != "update":
        raise ValueError("change request is not a task update: {}".format(args.request_id))
    if request.get("status") != "pending_review":
        raise ValueError("change request is not pending review: {}".format(args.request_id))
    outcome = args.task_command
    if outcome == "accept":
        path = task_path(root, str(request.get("entity_id")))
        task = read_json(path)
        if task.get("updated_at") != request.get("base_updated_at"):
            raise ValueError("task changed after submission; resubmit against current state")
        patch = request.get("patch")
        if not isinstance(patch, dict):
            raise ValueError("change request patch must be an object")
        if "status" in patch:
            validate_transition(str(task.get("status")), str(patch["status"]))
            if patch["status"] == "done":
                qualifying_refs = accepted_task_evidence(root, str(request.get("entity_id")), "E2")
                if not qualifying_refs:
                    raise ValueError("task cannot enter done without accepted E2 or stronger evidence")
                task["evidence_refs"] = sorted(
                    set(task.get("evidence_refs", []))
                    | set(accepted_task_evidence(root, str(request.get("entity_id")), "E0"))
                )
        for field in ("status", "title", "description"):
            if field in patch:
                task[field] = patch[field]
        task["updated_at"] = utc_now()
        write_json(path, task, args.dry_run)
        request["status"] = "accepted"
    else:
        request["status"] = "rejected"
        request["review_note"] = args.reason
    request["reviewed_by"] = args.actor
    request["updated_at"] = utc_now()
    write_json(request_path, request, args.dry_run)
    record_event(
        root,
        "change_request.{}".format(request["status"]),
        "change_request",
        args.request_id,
        args.actor,
        runtime_identity(args),
        {"entity_type": "task", "entity_id": request.get("entity_id")},
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else request["status"], "request": request, "message": "{} {}".format(request["status"], args.request_id)}, args.json)
    return 0


def cmd_evidence_add(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    manifest = require_project(root)
    read_json(task_path(root, args.task_id))
    if args.grade not in EVIDENCE_GRADES:
        raise ValueError("unknown evidence grade: {}".format(args.grade))
    path = root / ".agent-project" / "evidence" / "{}.json".format(args.evidence_id)
    if path.exists():
        raise ValueError("evidence already exists: {}".format(args.evidence_id))
    now = utc_now()
    verification = {"command": args.command, "result": args.result} if args.command else None
    if args.grade == "E2":
        if not args.command:
            raise ValueError("E2 evidence requires --command")
        if not args.run:
            raise ValueError("accepted E2 evidence requires --run so agent-project executes the command")
        if args.dry_run:
            verification = {"command": args.command, "result": "not_run", "executor": "agent-project:dry-run"}
        else:
            started = time.monotonic()
            try:
                completed = subprocess.run(
                    args.command,
                    cwd=str(root),
                    shell=True,
                    check=False,
                    capture_output=True,
                    timeout=args.timeout,
                )
            except subprocess.TimeoutExpired:
                raise ValueError("E2 verification timed out after {} seconds".format(args.timeout))
            duration_ms = int((time.monotonic() - started) * 1000)
            output = completed.stdout + b"\0" + completed.stderr
            if completed.returncode != 0:
                raise ValueError("E2 verification failed with exit code {}".format(completed.returncode))
            verification = {
                "command": args.command,
                "result": "passed",
                "executor": "agent-project",
                "exit_code": completed.returncode,
                "executed_at": utc_now(),
                "duration_ms": duration_ms,
                "output_sha256": hashlib.sha256(output).hexdigest(),
            }
    evidence = {
        "$schema": "https://agent-project-os.org/schemas/evidence-v1.schema.json",
        "protocol_version": "1.0",
        "evidence_id": args.evidence_id,
        "task_id": args.task_id,
        "grade": args.grade,
        "kind": args.kind,
        "summary": args.summary,
        "verification": verification,
        "acceptance_status": "accepted" if args.accepted else "proposed",
        "created_by": args.actor,
        "runtime_identity": runtime_identity(args),
        "created_at": now,
    }
    if args.grade == "E3":
        if not args.receipt_ref:
            raise ValueError("E3 evidence requires --receipt-ref")
        receipt = read_json(root / ".agent-project" / "receipts" / "{}.json".format(args.receipt_ref))
        if receipt.get("acceptance_status") != "accepted":
            raise ValueError("E3 evidence requires an accepted receipt")
        if receipt.get("consumer") != manifest.get("project_id"):
            raise ValueError("E3 receipt consumer does not match this project")
        evidence["receipt_ref"] = args.receipt_ref
    write_json(path, evidence, args.dry_run)
    record_event(
        root,
        "evidence.added",
        "evidence",
        args.evidence_id,
        args.actor,
        runtime_identity(args),
        {"task_id": args.task_id, "grade": args.grade},
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "created", "evidence": evidence, "message": "added evidence {}".format(args.evidence_id)}, args.json)
    return 0


def decision_path(root: Path, decision_id: str) -> Path:
    return root / ".agent-project" / "decisions" / "{}.json".format(decision_id)


def cmd_decision_propose(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    path = decision_path(root, args.decision_id)
    if path.exists():
        raise ValueError("decision already exists: {}".format(args.decision_id))
    now = utc_now()
    decision = {
        "$schema": "https://agent-project-os.org/schemas/decision-v1.schema.json",
        "protocol_version": "1.0",
        "decision_id": args.decision_id,
        "title": args.title,
        "status": "proposed",
        "context": args.context,
        "decision": args.decision,
        "rationale": args.rationale,
        "consequences": list(args.consequence or []),
        "created_by": args.actor,
        "runtime_identity": runtime_identity(args),
        "created_at": now,
        "updated_at": now,
    }
    write_json(path, decision, args.dry_run)
    record_event(root, "decision.proposed", "decision", args.decision_id, args.actor, runtime_identity(args), {}, args.dry_run)
    emit({"status": "planned" if args.dry_run else "proposed", "decision": decision, "message": "proposed {}".format(args.decision_id)}, args.json)
    return 0


def cmd_decision_change(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    path = decision_path(root, args.decision_id)
    decision = read_json(path)
    current = decision.get("status")
    action = args.decision_command
    if action in {"accept", "reject"}:
        if current != "proposed":
            raise ValueError("only proposed decisions may be {}ed".format(action))
        target = "accepted" if action == "accept" else "rejected"
    else:
        if current != "accepted":
            raise ValueError("only accepted decisions may be superseded")
        replacement = read_json(decision_path(root, args.by))
        if replacement.get("status") != "accepted":
            raise ValueError("replacement decision must be accepted")
        target = "superseded"
        decision["superseded_by"] = args.by
    decision["status"] = target
    decision["updated_at"] = utc_now()
    decision["reviewed_by"] = args.actor
    if args.reason:
        decision["review_note"] = args.reason
    write_json(path, decision, args.dry_run)
    record_event(root, "decision.{}".format(target), "decision", args.decision_id, args.actor, runtime_identity(args), {}, args.dry_run)
    emit({"status": "planned" if args.dry_run else target, "decision": decision, "message": "{} {}".format(target, args.decision_id)}, args.json)
    return 0


def handoff_path(root: Path, handoff_id: str) -> Path:
    return root / ".agent-project" / "handoffs" / "{}.json".format(handoff_id)


def cmd_handoff_create(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    manifest = require_project(root)
    path = handoff_path(root, args.handoff_id)
    if path.exists():
        raise ValueError("handoff already exists: {}".format(args.handoff_id))
    now = utc_now()
    handoff = {
        "$schema": "https://agent-project-os.org/schemas/handoff-v1.schema.json",
        "protocol_version": "1.0",
        "handoff_id": args.handoff_id,
        "project_id": manifest.get("project_id"),
        "from_actor": args.from_actor,
        "to_actor": args.to_actor,
        "goal": args.goal,
        "completed": list(args.completed),
        "in_progress": list(args.in_progress or []),
        "blocked": list(args.blocked or []),
        "decision_refs": list(args.decision_ref or []),
        "evidence_refs": list(args.evidence_ref or []),
        "next_actions": list(args.next_action),
        "runtime_identity": runtime_identity(args),
        "created_at": now,
    }
    write_json(path, handoff, args.dry_run)
    record_event(root, "handoff.created", "handoff", args.handoff_id, args.actor, runtime_identity(args), {}, args.dry_run)
    emit({"status": "planned" if args.dry_run else "created", "handoff": handoff, "message": "created {}".format(args.handoff_id)}, args.json)
    return 0


def cmd_handoff_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    read_json(handoff_path(root, args.handoff_id))
    errors = [item for item in validate_project(root) if "handoff {}".format(args.handoff_id) in item]
    emit({"status": "invalid" if errors else "valid", "handoff_id": args.handoff_id, "errors": errors, "message": "handoff validation failed" if errors else "handoff validation passed"}, args.json)
    return 1 if errors else 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    errors = validate_portfolio(root) if portfolio_path(root).exists() else validate_project(root)
    payload = {
        "status": "invalid" if errors else "valid",
        "root": str(root),
        "errors": errors,
        "message": "validation failed" if errors else "validation passed",
    }
    emit(payload, args.json)
    return 1 if errors else 0


def cmd_project_add(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    path = portfolio_path(root)
    if path.exists():
        portfolio = load_portfolio(root)
        if args.portfolio_id and portfolio.get("portfolio_id") != args.portfolio_id:
            raise ValueError("portfolio id does not match existing manifest")
    else:
        if not args.portfolio_id or not args.portfolio_name:
            raise ValueError("new portfolio requires --portfolio-id and --portfolio-name")
        portfolio = new_portfolio(args.portfolio_id, args.portfolio_name)
    projects = projects_by_id(portfolio)
    if args.project_id in projects:
        raise ValueError("project already exists: {}".format(args.project_id))
    unknown = sorted(set(args.depends_on or []) - set(projects))
    if unknown:
        raise ValueError("unknown dependencies: {}".format(unknown))
    project_root = (root / args.path).resolve()
    manifest = read_json(project_root / ".agent-project" / "manifest.json")
    if manifest.get("project_id") != args.project_id:
        raise ValueError("project path manifest id is {!r}, expected {!r}".format(manifest.get("project_id"), args.project_id))
    record = {
        "project_id": args.project_id,
        "owner": args.owner,
        "lifecycle": args.lifecycle,
        "path": args.path,
        "repository": args.repository,
        "depends_on": sorted(set(args.depends_on or [])),
        "provides": sorted(set(args.provides or [])),
        "consumes": sorted(set(args.consumes or [])),
        "verification": list(args.verification),
    }
    portfolio["projects"].append(record)
    portfolio["projects"] = sorted(portfolio["projects"], key=lambda item: item["project_id"])
    write_json(path, portfolio, args.dry_run)
    emit({"status": "planned" if args.dry_run else "added", "project": record, "message": "added {}".format(args.project_id)}, args.json)
    return 0


def cmd_project_read(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects = projects_by_id(load_portfolio(root))
    if args.project_command == "show":
        if args.project_id not in projects:
            raise ValueError("unknown project: {}".format(args.project_id))
        payload: Dict[str, Any] = {"status": "ok", "project": projects[args.project_id]}
    else:
        payload = {"status": "ok", "projects": [projects[key] for key in sorted(projects)]}
    emit(payload, args.json)
    return 0


def cmd_affected(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    portfolio = load_portfolio(root)
    errors = validate_portfolio(root)
    if errors:
        raise ValueError("portfolio is invalid: {}".format("; ".join(errors)))
    affected = affected_projects(portfolio, args.project_id)
    emit({"status": "ok", "source": args.project_id, "affected": affected, "message": ", ".join(affected) if affected else "no affected projects"}, args.json)
    return 0


def cmd_index_rebuild(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    errors = validate_portfolio(root)
    if errors:
        raise ValueError("portfolio is invalid: {}".format("; ".join(errors)))
    summary = rebuild_index(root, args.dry_run)
    emit({"status": "planned" if args.dry_run else "rebuilt", "summary": summary, "message": "index rebuilt"}, args.json)
    return 0


def count_records(directory: Path, field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if not directory.exists():
        return counts
    for path in sorted(directory.glob("*.json")):
        value = str(read_json(path).get(field, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if portfolio_path(root).exists():
        portfolio = load_portfolio(root)
        projects = projects_by_id(portfolio)
        errors = validate_portfolio(root)
        payload = {
            "status": "invalid" if errors else "ok",
            "kind": "portfolio",
            "portfolio_id": portfolio.get("portfolio_id"),
            "projects": {key: projects[key].get("lifecycle") for key in sorted(projects)},
            "errors": errors,
            "message": "{} projects".format(len(projects)),
        }
    else:
        manifest = require_project(root)
        control = root / ".agent-project"
        errors = validate_project(root)
        payload = {
            "status": "invalid" if errors else "ok",
            "kind": "project",
            "project_id": manifest.get("project_id"),
            "tasks": count_records(control / "tasks", "status"),
            "evidence": count_records(control / "evidence", "grade"),
            "decisions": count_records(control / "decisions", "status"),
            "inbox": count_records(control / "inbox", "status"),
            "errors": errors,
            "message": "project {}".format(manifest.get("project_id")),
        }
    emit(payload, args.json)
    return 1 if payload["status"] == "invalid" else 0


def selected_adapters(value: str) -> Iterable[str]:
    return ADAPTERS if value == "all" else (value,)


def cmd_adapter_write(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    adapters = selected_adapters(args.adapter)
    if args.adapter_command == "uninstall":
        result = uninstall_adapters(root, adapters, args.user, args.dry_run)
        status = "planned" if args.dry_run else "uninstalled"
    else:
        result = render_adapters(root, adapters, args.user, args.dry_run)
        status = "planned" if args.dry_run else ("installed" if args.adapter_command == "install" else "rendered")
    emit({"status": status, **result, "message": "adapter {} complete".format(args.adapter_command)}, args.json)
    return 0


def cmd_adapter_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    require_project(root)
    adapters = selected_adapters(args.adapter)
    results = adapter_doctor(root, adapters, args.user)
    emit({"status": "ok", "adapters": results, "message": "adapter diagnostics complete"}, args.json)
    return 0


def add_write_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Show the write set without changing files.")


def add_identity_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor", default="human")
    parser.add_argument("--runtime", default="manual")
    parser.add_argument("--client-version", default="unknown")
    parser.add_argument("--model-id")
    parser.add_argument("--provider-hint")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-project")
    parser.add_argument("--root", default=".", help="Project or portfolio root. Defaults to the current directory.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Initialize a repo-native Agent Project OS project.")
    init.add_argument("--project-id", required=True)
    init.add_argument("--name", required=True)
    add_write_options(init)
    init.set_defaults(handler=cmd_init)

    validate = commands.add_parser("validate", help="Validate project records and cross-record invariants.")
    validate.set_defaults(handler=cmd_validate)

    task = commands.add_parser("task", help="Manage accepted task state and submitted changes.")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    task_create = task_commands.add_parser("create")
    task_create.add_argument("--task-id", required=True)
    task_create.add_argument("--title", required=True)
    task_create.add_argument("--description")
    task_create.add_argument("--priority", choices=("low", "medium", "high", "urgent"), default="medium")
    task_create.add_argument("--owner", default="human")
    task_create.add_argument("--acceptance", action="append", required=True)
    add_write_options(task_create)
    add_identity_options(task_create)
    task_create.set_defaults(handler=cmd_task_create)

    task_update = task_commands.add_parser("update")
    task_update.add_argument("--task-id", required=True)
    task_update.add_argument("--title")
    task_update.add_argument("--status")
    task_update.add_argument("--blocker-type", choices=("dependency", "needs_input", "capability", "transient", "risk_gate"))
    task_update.add_argument("--blocker-summary")
    add_write_options(task_update)
    add_identity_options(task_update)
    task_update.set_defaults(handler=cmd_task_update)

    task_submit = task_commands.add_parser("submit")
    task_submit.add_argument("--request-id", required=True)
    task_submit.add_argument("--task-id", required=True)
    task_submit.add_argument("--title")
    task_submit.add_argument("--description")
    task_submit.add_argument("--status")
    add_write_options(task_submit)
    add_identity_options(task_submit)
    task_submit.set_defaults(handler=cmd_task_submit)

    for review_action in ("accept", "reject"):
        task_review = task_commands.add_parser(review_action)
        task_review.add_argument("--request-id", required=True)
        task_review.add_argument("--reason", default="")
        add_write_options(task_review)
        add_identity_options(task_review)
        task_review.set_defaults(handler=cmd_task_review)

    evidence = commands.add_parser("evidence", help="Manage project evidence.")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_commands.add_parser("add")
    evidence_add.add_argument("--evidence-id", required=True)
    evidence_add.add_argument("--task-id", required=True)
    evidence_add.add_argument("--grade", required=True)
    evidence_add.add_argument("--kind", required=True)
    evidence_add.add_argument("--summary", required=True)
    evidence_add.add_argument("--command")
    evidence_add.add_argument("--receipt-ref")
    evidence_add.add_argument("--result", choices=("passed", "failed", "not_run"), default="not_run")
    evidence_add.add_argument("--run", action="store_true", help="Execute the E2 verification command in the project root.")
    evidence_add.add_argument("--timeout", type=int, default=300)
    evidence_add.add_argument("--accepted", action="store_true")
    add_write_options(evidence_add)
    add_identity_options(evidence_add)
    evidence_add.set_defaults(handler=cmd_evidence_add)

    decision = commands.add_parser("decision", help="Manage explicit project decisions.")
    decision_commands = decision.add_subparsers(dest="decision_command", required=True)
    decision_propose = decision_commands.add_parser("propose")
    decision_propose.add_argument("--decision-id", required=True)
    decision_propose.add_argument("--title", required=True)
    decision_propose.add_argument("--context", required=True)
    decision_propose.add_argument("--decision", required=True)
    decision_propose.add_argument("--rationale", required=True)
    decision_propose.add_argument("--consequence", action="append")
    add_write_options(decision_propose)
    add_identity_options(decision_propose)
    decision_propose.set_defaults(handler=cmd_decision_propose)
    for decision_action in ("accept", "reject", "supersede"):
        decision_change = decision_commands.add_parser(decision_action)
        decision_change.add_argument("--decision-id", required=True)
        decision_change.add_argument("--by")
        decision_change.add_argument("--reason", default="")
        add_write_options(decision_change)
        add_identity_options(decision_change)
        decision_change.set_defaults(handler=cmd_decision_change)

    handoff = commands.add_parser("handoff", help="Create and validate cross-agent handoffs.")
    handoff_commands = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_commands.add_parser("create")
    handoff_create.add_argument("--handoff-id", required=True)
    handoff_create.add_argument("--from-actor", required=True)
    handoff_create.add_argument("--to-actor", required=True)
    handoff_create.add_argument("--goal", required=True)
    handoff_create.add_argument("--completed", action="append", required=True)
    handoff_create.add_argument("--in-progress", action="append")
    handoff_create.add_argument("--blocked", action="append")
    handoff_create.add_argument("--decision-ref", action="append")
    handoff_create.add_argument("--evidence-ref", action="append")
    handoff_create.add_argument("--next-action", action="append", required=True)
    add_write_options(handoff_create)
    add_identity_options(handoff_create)
    handoff_create.set_defaults(handler=cmd_handoff_create)
    handoff_validate = handoff_commands.add_parser("validate")
    handoff_validate.add_argument("--handoff-id", required=True)
    handoff_validate.set_defaults(handler=cmd_handoff_validate)

    project = commands.add_parser("project", help="Manage a federated portfolio catalog.")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_add = project_commands.add_parser("add")
    project_add.add_argument("--portfolio-id")
    project_add.add_argument("--portfolio-name")
    project_add.add_argument("--project-id", required=True)
    project_add.add_argument("--path", required=True)
    project_add.add_argument("--owner", required=True)
    project_add.add_argument("--lifecycle", choices=("planned", "active", "paused", "maintenance", "retired"), default="active")
    project_add.add_argument("--repository")
    project_add.add_argument("--depends-on", action="append")
    project_add.add_argument("--provides", action="append")
    project_add.add_argument("--consumes", action="append")
    project_add.add_argument("--verification", action="append", required=True)
    add_write_options(project_add)
    project_add.set_defaults(handler=cmd_project_add)
    project_list = project_commands.add_parser("list")
    project_list.set_defaults(handler=cmd_project_read)
    project_show = project_commands.add_parser("show")
    project_show.add_argument("--project-id", required=True)
    project_show.set_defaults(handler=cmd_project_read)

    affected = commands.add_parser("affected", help="Compute transitive downstream impact from dependencies and interfaces.")
    affected.add_argument("--project-id", required=True)
    affected.set_defaults(handler=cmd_affected)

    index = commands.add_parser("index", help="Manage the disposable SQLite query projection.")
    index_commands = index.add_subparsers(dest="index_command", required=True)
    index_rebuild = index_commands.add_parser("rebuild")
    add_write_options(index_rebuild)
    index_rebuild.set_defaults(handler=cmd_index_rebuild)

    status = commands.add_parser("status", help="Render project or portfolio state from accepted repo evidence.")
    status.set_defaults(handler=cmd_status)

    adapter = commands.add_parser("adapter", help="Render, install, remove, or diagnose runtime-specific adapters.")
    adapter_commands = adapter.add_subparsers(dest="adapter_command", required=True)
    for adapter_action in ("render", "install", "uninstall"):
        adapter_write = adapter_commands.add_parser(adapter_action)
        adapter_write.add_argument("--adapter", choices=(*ADAPTERS, "all"), required=True)
        adapter_write.add_argument("--user", action="store_true", help="Target user-level configuration instead of project files.")
        add_write_options(adapter_write)
        adapter_write.set_defaults(handler=cmd_adapter_write)
    adapter_diagnostics = adapter_commands.add_parser("doctor")
    adapter_diagnostics.add_argument("--adapter", choices=(*ADAPTERS, "all"), default="all")
    adapter_diagnostics.add_argument("--user", action="store_true")
    adapter_diagnostics.set_defaults(handler=cmd_adapter_doctor)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.handler(args))
    except (OSError, ValueError) as error:
        payload = {"status": "error", "error": str(error)}
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print("error: {}".format(error), file=sys.stderr)
        return 2
