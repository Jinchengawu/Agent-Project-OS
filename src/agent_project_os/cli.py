"""Command line interface for Agent Project OS."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, Optional

from . import __version__
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
from .adapters import ADAPTERS, doctor as adapter_doctor, render_adapters, render_dispatch_entry, uninstall_adapters
from .cadence import close_run, plan_run, record_attempt
from .migration import migrate_portfolio_v1
from .organization import (
    active_pm_assignment,
    add_registered_project,
    assign_project_pm,
    build_portfolio_review,
    create_dispatch,
    due_projects,
    has_organization,
    init_organization,
    load_organization,
    load_registry,
    registry_projects,
    report_review,
    review_report,
    submit_report,
    validate_organization,
)
from .workforce import (
    add_agent,
    add_evaluation,
    add_role,
    assign_role,
    build_workforce_review,
    change_agent_lifecycle,
    get_agent,
    list_agents,
    promote_upgrade,
    propose_upgrade,
    rollback_agent,
)
from .projections import build_dashboard, rebuild_organization_index
from .shadow import compare_snapshot


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
    if has_organization(root):
        errors = validate_organization(root)
    else:
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
    if has_organization(root):
        record = add_registered_project(
            root,
            args.project_id,
            args.path,
            args.owner,
            args.project_priority,
            args.lifecycle,
            args.repository,
            args.depends_on or [],
            args.provides or [],
            args.consumes or [],
            args.verification,
            args.supervision,
            args.timezone,
            args.next_due_at,
            args.dry_run,
        )
        emit({"status": "planned" if args.dry_run else "added", "project": record, "message": "added {}".format(args.project_id)}, args.json)
        return 0
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
    projects = registry_projects(load_registry(root)) if has_organization(root) else projects_by_id(load_portfolio(root))
    if args.project_command == "show":
        if args.project_id not in projects:
            raise ValueError("unknown project: {}".format(args.project_id))
        payload: Dict[str, Any] = {"status": "ok", "project": projects[args.project_id]}
    else:
        payload = {"status": "ok", "projects": [projects[key] for key in sorted(projects)]}
    emit(payload, args.json)
    return 0


def cmd_org_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = init_organization(
        root,
        args.organization_id,
        args.name,
        args.founder,
        args.ceo_agent_id,
        args.pmo_agent_id,
        args.dry_run,
    )
    emit(
        {
            "status": "planned" if args.dry_run else "created",
            **result,
            "message": "initialized organization {}".format(args.organization_id),
        },
        args.json,
    )
    return 0


def cmd_org_read(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    errors = validate_organization(root)
    payload = {
        "status": "invalid" if errors else "ok",
        "organization": load_organization(root),
        "project_count": len(registry_projects(load_registry(root))),
        "errors": errors,
        "message": "organization validation failed" if errors else "organization is valid",
    }
    emit(payload, args.json)
    return 1 if errors else 0


def cmd_project_assign_pm(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    assignment = assign_project_pm(
        root,
        args.assignment_id,
        args.project_id,
        args.pm_agent_id,
        args.assigned_by,
        args.dry_run,
    )
    emit(
        {
            "status": "planned" if args.dry_run else "assigned",
            "assignment": assignment,
            "message": "assigned PM to {}".format(args.project_id),
        },
        args.json,
    )
    return 0


def cmd_supervision_due(args: argparse.Namespace) -> int:
    due = due_projects(Path(args.root).resolve(), args.as_of)
    emit({"status": "ok", "as_of": args.as_of, "due": due, "message": "{} due projects".format(len(due))}, args.json)
    return 0


def cmd_supervision_dispatch(args: argparse.Namespace) -> int:
    dispatch = create_dispatch(
        Path(args.root).resolve(),
        args.dispatch_id,
        args.project_id,
        args.objective,
        args.expected_output,
        args.acceptance,
        args.due_at,
        args.issued_by,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "issued", "dispatch": dispatch, "message": "issued {}".format(args.dispatch_id)}, args.json)
    return 0


def cmd_supervision_submit(args: argparse.Namespace) -> int:
    report = submit_report(
        Path(args.root).resolve(),
        args.report_id,
        args.dispatch_id,
        args.summary,
        args.project_commit,
        args.reported_status,
        args.next_acceptance,
        args.evidence_ref or [],
        args.blocker or [],
        args.submitted_by,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "submitted", "report": report, "message": "submitted {}".format(args.report_id)}, args.json)
    return 0


def cmd_supervision_review(args: argparse.Namespace) -> int:
    outcome = "accepted" if args.supervision_command == "accept" else "rejected"
    review = review_report(
        Path(args.root).resolve(),
        args.review_id,
        args.report_id,
        outcome,
        args.reviewed_by,
        args.note,
        args.reviewed_at,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else outcome, "review": review, "message": "{} {}".format(outcome, args.report_id)}, args.json)
    return 0


def cmd_portfolio_review(args: argparse.Namespace) -> int:
    review = build_portfolio_review(Path(args.root).resolve(), args.review_id, args.as_of, args.dry_run)
    emit({"status": "planned" if args.dry_run else "created", "review": review, "message": "created portfolio review"}, args.json)
    return 0


def cmd_role_add(args: argparse.Namespace) -> int:
    role = add_role(
        Path(args.root).resolve(),
        args.role_id,
        args.name,
        args.purpose,
        args.authority,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "created", "role": role, "message": "created role {}".format(args.role_id)}, args.json)
    return 0


def cmd_role_assign(args: argparse.Namespace) -> int:
    assignment = assign_role(
        Path(args.root).resolve(),
        args.assignment_id,
        args.agent_id,
        args.role_id,
        args.scope,
        args.project_id,
        args.assigned_by,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "assigned", "assignment": assignment, "message": "assigned role {}".format(args.role_id)}, args.json)
    return 0


def cmd_agent_add(args: argparse.Namespace) -> int:
    agent = add_agent(
        Path(args.root).resolve(),
        args.agent_id,
        args.name,
        args.role_id,
        args.release_id,
        args.asset_path,
        args.asset_commit,
        args.asset_sha256,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "created", "agent": agent, "message": "created agent {}".format(args.agent_id)}, args.json)
    return 0


def cmd_agent_read(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if args.agent_command == "show":
        payload = {"status": "ok", "agent": get_agent(root, args.agent_id)}
    else:
        payload = {"status": "ok", "agents": list_agents(root)}
    emit(payload, args.json)
    return 0


def cmd_agent_evaluate(args: argparse.Namespace) -> int:
    evaluation = add_evaluation(
        Path(args.root).resolve(),
        args.evaluation_id,
        args.agent_id,
        args.reviewer,
        args.score,
        args.outcome,
        args.evidence_ref,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "created", "evaluation": evaluation, "message": "created evaluation {}".format(args.evaluation_id)}, args.json)
    return 0


def cmd_agent_propose_upgrade(args: argparse.Namespace) -> int:
    proposal = propose_upgrade(
        Path(args.root).resolve(),
        args.proposal_id,
        args.agent_id,
        args.release_id,
        args.asset_path,
        args.asset_commit,
        args.asset_sha256,
        args.evaluation_id,
        args.proposed_by,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "proposed", "proposal": proposal, "message": "proposed {}".format(args.proposal_id)}, args.json)
    return 0


def cmd_agent_promote(args: argparse.Namespace) -> int:
    proposal = promote_upgrade(Path(args.root).resolve(), args.proposal_id, args.approved_by, args.dry_run)
    emit({"status": "planned" if args.dry_run else "promoted", "proposal": proposal, "message": "promoted {}".format(args.proposal_id)}, args.json)
    return 0


def cmd_agent_rollback(args: argparse.Namespace) -> int:
    result = rollback_agent(Path(args.root).resolve(), args.agent_id, args.approved_by, args.reason, args.dry_run)
    emit({"status": "planned" if args.dry_run else "rolled_back", "rollback": result, "message": "rolled back {}".format(args.agent_id)}, args.json)
    return 0


def cmd_agent_lifecycle(args: argparse.Namespace) -> int:
    lifecycle = "paused" if args.agent_command == "pause" else "retired"
    agent = change_agent_lifecycle(Path(args.root).resolve(), args.agent_id, lifecycle, args.approved_by, args.reason, args.dry_run)
    emit({"status": "planned" if args.dry_run else lifecycle, "agent": agent, "message": "{} {}".format(lifecycle, args.agent_id)}, args.json)
    return 0


def cmd_workforce_review(args: argparse.Namespace) -> int:
    review = build_workforce_review(Path(args.root).resolve(), args.review_id, args.dry_run)
    emit({"status": "planned" if args.dry_run else "created", "review": review, "message": "created workforce review"}, args.json)
    return 0


def cmd_cadence_plan(args: argparse.Namespace) -> int:
    run = plan_run(
        Path(args.root).resolve(),
        args.run_id,
        args.window_start,
        args.window_end,
        args.as_of,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "ok", "run": run, "message": "cadence plan {}".format(args.run_id)}, args.json)
    return 0


def cmd_cadence_record(args: argparse.Namespace) -> int:
    run = record_attempt(
        Path(args.root).resolve(),
        args.run_id,
        args.action_id,
        args.result,
        args.result_ref,
        args.dry_run,
    )
    emit({"status": "planned" if args.dry_run else "recorded", "run": run, "message": "recorded cadence attempt"}, args.json)
    return 0


def cmd_cadence_close(args: argparse.Namespace) -> int:
    run = close_run(Path(args.root).resolve(), args.run_id, args.outcome, args.dry_run)
    emit({"status": "planned" if args.dry_run else args.outcome, "run": run, "message": "closed cadence run"}, args.json)
    return 0


def cmd_adapter_dispatch(args: argparse.Namespace) -> int:
    result = render_dispatch_entry(Path(args.root).resolve(), args.adapter, args.dispatch_id, args.dry_run)
    emit({"status": "planned" if args.dry_run else "rendered", **result, "message": "rendered dispatch entry"}, args.json)
    return 0


def cmd_migrate_portfolio(args: argparse.Namespace) -> int:
    result = migrate_portfolio_v1(Path(args.root).resolve(), args.dry_run)
    emit({"status": "planned" if args.dry_run else "migrated", **result, "message": "migrated portfolio-v1"}, args.json)
    return 0


def cmd_dashboard_build(args: argparse.Namespace) -> int:
    result = build_dashboard(Path(args.root).resolve(), args.as_of, args.dry_run)
    emit({"status": "planned" if args.dry_run else "built", **result, "message": "built read-only dashboard"}, args.json)
    return 0


def cmd_shadow_compare(args: argparse.Namespace) -> int:
    result = compare_snapshot(Path(args.root).resolve(), Path(args.snapshot).resolve())
    emit({**result, "message": "shadow snapshot {}".format(result["status"])}, args.json)
    return 0 if result["status"] == "match" else 1


def cmd_affected(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    portfolio = load_registry(root) if has_organization(root) else load_portfolio(root)
    errors = validate_organization(root) if has_organization(root) else validate_portfolio(root)
    if errors:
        raise ValueError("portfolio is invalid: {}".format("; ".join(errors)))
    affected = affected_projects(portfolio, args.project_id)
    emit({"status": "ok", "source": args.project_id, "affected": affected, "message": ", ".join(affected) if affected else "no affected projects"}, args.json)
    return 0


def cmd_index_rebuild(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    errors = validate_organization(root) if has_organization(root) else validate_portfolio(root)
    if errors:
        raise ValueError("portfolio is invalid: {}".format("; ".join(errors)))
    summary = rebuild_organization_index(root, args.dry_run) if has_organization(root) else rebuild_index(root, args.dry_run)
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
    if has_organization(root):
        organization = load_organization(root)
        projects = registry_projects(load_registry(root))
        errors = validate_organization(root)
        payload = {
            "status": "invalid" if errors else "ok",
            "kind": "organization",
            "organization_id": organization.get("organization_id"),
            "projects": {key: projects[key].get("lifecycle") for key in sorted(projects)},
            "accountable_pms": {
                key: (active_pm_assignment(root, key) or {}).get("agent_id") for key in sorted(projects)
            },
            "errors": errors,
            "message": "{} projects".format(len(projects)),
        }
    elif portfolio_path(root).exists():
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
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--root", default=".", help="Project or portfolio root. Defaults to the current directory.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Initialize a repo-native Agent Project OS project.")
    init.add_argument("--project-id", required=True)
    init.add_argument("--name", required=True)
    add_write_options(init)
    init.set_defaults(handler=cmd_init)

    org = commands.add_parser("org", help="Manage the Founder/CEO/PMO organization control plane.")
    org_commands = org.add_subparsers(dest="org_command", required=True)
    org_init = org_commands.add_parser("init")
    org_init.add_argument("--organization-id", required=True)
    org_init.add_argument("--name", required=True)
    org_init.add_argument("--founder", required=True)
    org_init.add_argument("--ceo-agent-id", required=True)
    org_init.add_argument("--pmo-agent-id", required=True)
    add_write_options(org_init)
    org_init.set_defaults(handler=cmd_org_init)
    for org_action in ("status", "validate"):
        org_read = org_commands.add_parser(org_action)
        org_read.set_defaults(handler=cmd_org_read)

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
    project_add.add_argument("--project-priority", choices=("P0", "P1", "P2", "P3"), default="P2")
    project_add.add_argument("--lifecycle", choices=("planned", "active", "paused", "maintenance", "retired"), default="active")
    project_add.add_argument("--repository")
    project_add.add_argument("--depends-on", action="append")
    project_add.add_argument("--provides", action="append")
    project_add.add_argument("--consumes", action="append")
    project_add.add_argument("--verification", action="append", required=True)
    project_add.add_argument("--supervision", choices=("daily", "weekly", "monthly"), default="weekly")
    project_add.add_argument("--timezone", default="UTC")
    project_add.add_argument("--next-due-at")
    add_write_options(project_add)
    project_add.set_defaults(handler=cmd_project_add)
    project_list = project_commands.add_parser("list")
    project_list.set_defaults(handler=cmd_project_read)
    project_show = project_commands.add_parser("show")
    project_show.add_argument("--project-id", required=True)
    project_show.set_defaults(handler=cmd_project_read)
    project_assign_pm = project_commands.add_parser("assign-pm")
    project_assign_pm.add_argument("--assignment-id", required=True)
    project_assign_pm.add_argument("--project-id", required=True)
    project_assign_pm.add_argument("--pm-agent-id", required=True)
    project_assign_pm.add_argument("--assigned-by", default="human:founder")
    add_write_options(project_assign_pm)
    project_assign_pm.set_defaults(handler=cmd_project_assign_pm)

    supervision = commands.add_parser("supervision", help="Issue and review periodic child-PM supervision work.")
    supervision_commands = supervision.add_subparsers(dest="supervision_command", required=True)
    supervision_due = supervision_commands.add_parser("due")
    supervision_due.add_argument("--as-of", required=True)
    supervision_due.set_defaults(handler=cmd_supervision_due)
    supervision_dispatch = supervision_commands.add_parser("dispatch")
    supervision_dispatch.add_argument("--dispatch-id", required=True)
    supervision_dispatch.add_argument("--project-id", required=True)
    supervision_dispatch.add_argument("--objective", required=True)
    supervision_dispatch.add_argument("--expected-output", action="append", required=True)
    supervision_dispatch.add_argument("--acceptance", action="append", required=True)
    supervision_dispatch.add_argument("--due-at", required=True)
    supervision_dispatch.add_argument("--issued-by", default="agent:pmo")
    add_write_options(supervision_dispatch)
    supervision_dispatch.set_defaults(handler=cmd_supervision_dispatch)
    supervision_submit = supervision_commands.add_parser("submit")
    supervision_submit.add_argument("--report-id", required=True)
    supervision_submit.add_argument("--dispatch-id", required=True)
    supervision_submit.add_argument("--summary", required=True)
    supervision_submit.add_argument("--project-commit", required=True)
    supervision_submit.add_argument("--reported-status", choices=("planned", "ready", "in_progress", "blocked", "waiting_review", "done", "paused", "cancelled"), required=True)
    supervision_submit.add_argument("--next-acceptance", required=True)
    supervision_submit.add_argument("--evidence-ref", action="append")
    supervision_submit.add_argument("--blocker", action="append")
    supervision_submit.add_argument("--submitted-by", required=True)
    add_write_options(supervision_submit)
    supervision_submit.set_defaults(handler=cmd_supervision_submit)
    for supervision_action in ("accept", "reject"):
        supervision_review = supervision_commands.add_parser(supervision_action)
        supervision_review.add_argument("--review-id", required=True)
        supervision_review.add_argument("--report-id", required=True)
        supervision_review.add_argument("--reviewed-by", default="agent:pmo")
        supervision_review.add_argument("--reviewed-at")
        supervision_review.add_argument("--note", default="")
        add_write_options(supervision_review)
        supervision_review.set_defaults(handler=cmd_supervision_review)

    portfolio = commands.add_parser("portfolio", help="Build accepted organization-level portfolio reviews.")
    portfolio_commands = portfolio.add_subparsers(dest="portfolio_command", required=True)
    portfolio_review = portfolio_commands.add_parser("review")
    portfolio_review.add_argument("--review-id", required=True)
    portfolio_review.add_argument("--as-of", required=True)
    add_write_options(portfolio_review)
    portfolio_review.set_defaults(handler=cmd_portfolio_review)

    role = commands.add_parser("role", help="Manage runtime-neutral Agent role definitions.")
    role_commands = role.add_subparsers(dest="role_command", required=True)
    role_add = role_commands.add_parser("add")
    role_add.add_argument("--role-id", required=True)
    role_add.add_argument("--name", required=True)
    role_add.add_argument("--purpose", required=True)
    role_add.add_argument("--authority", action="append", required=True)
    add_write_options(role_add)
    role_add.set_defaults(handler=cmd_role_add)
    role_assign = role_commands.add_parser("assign")
    role_assign.add_argument("--assignment-id", required=True)
    role_assign.add_argument("--agent-id", required=True)
    role_assign.add_argument("--role-id", required=True)
    role_assign.add_argument("--scope", choices=("organization", "project"), default="organization")
    role_assign.add_argument("--project-id")
    role_assign.add_argument("--assigned-by", default="human:founder")
    add_write_options(role_assign)
    role_assign.set_defaults(handler=cmd_role_assign)

    agent = commands.add_parser("agent", help="Manage Agent HR registry, evaluations, releases, and lifecycle.")
    agent_commands = agent.add_subparsers(dest="agent_command", required=True)
    agent_add = agent_commands.add_parser("add")
    agent_add.add_argument("--agent-id", required=True)
    agent_add.add_argument("--name", required=True)
    agent_add.add_argument("--role-id", action="append", required=True)
    agent_add.add_argument("--release-id")
    agent_add.add_argument("--asset-path")
    agent_add.add_argument("--asset-commit")
    agent_add.add_argument("--asset-sha256")
    add_write_options(agent_add)
    agent_add.set_defaults(handler=cmd_agent_add)
    agent_list = agent_commands.add_parser("list")
    agent_list.set_defaults(handler=cmd_agent_read)
    agent_show = agent_commands.add_parser("show")
    agent_show.add_argument("--agent-id", required=True)
    agent_show.set_defaults(handler=cmd_agent_read)
    agent_evaluate = agent_commands.add_parser("evaluate")
    agent_evaluate.add_argument("--evaluation-id", required=True)
    agent_evaluate.add_argument("--agent-id", required=True)
    agent_evaluate.add_argument("--reviewer", required=True)
    agent_evaluate.add_argument("--score", type=int, required=True)
    agent_evaluate.add_argument("--outcome", choices=("passed", "failed"), required=True)
    agent_evaluate.add_argument("--evidence-ref", action="append", required=True)
    add_write_options(agent_evaluate)
    agent_evaluate.set_defaults(handler=cmd_agent_evaluate)
    agent_upgrade = agent_commands.add_parser("propose-upgrade")
    agent_upgrade.add_argument("--proposal-id", required=True)
    agent_upgrade.add_argument("--agent-id", required=True)
    agent_upgrade.add_argument("--release-id", required=True)
    agent_upgrade.add_argument("--asset-path", required=True)
    agent_upgrade.add_argument("--asset-commit", required=True)
    agent_upgrade.add_argument("--asset-sha256", required=True)
    agent_upgrade.add_argument("--evaluation-id", required=True)
    agent_upgrade.add_argument("--proposed-by", required=True)
    add_write_options(agent_upgrade)
    agent_upgrade.set_defaults(handler=cmd_agent_propose_upgrade)
    agent_promote = agent_commands.add_parser("promote")
    agent_promote.add_argument("--proposal-id", required=True)
    agent_promote.add_argument("--approved-by", required=True)
    add_write_options(agent_promote)
    agent_promote.set_defaults(handler=cmd_agent_promote)
    agent_rollback = agent_commands.add_parser("rollback")
    agent_rollback.add_argument("--agent-id", required=True)
    agent_rollback.add_argument("--approved-by", required=True)
    agent_rollback.add_argument("--reason", required=True)
    add_write_options(agent_rollback)
    agent_rollback.set_defaults(handler=cmd_agent_rollback)
    for lifecycle_action in ("pause", "retire"):
        agent_lifecycle = agent_commands.add_parser(lifecycle_action)
        agent_lifecycle.add_argument("--agent-id", required=True)
        agent_lifecycle.add_argument("--approved-by", required=True)
        agent_lifecycle.add_argument("--reason", required=True)
        add_write_options(agent_lifecycle)
        agent_lifecycle.set_defaults(handler=cmd_agent_lifecycle)

    workforce = commands.add_parser("workforce", help="Build Agent HR review projections.")
    workforce_commands = workforce.add_subparsers(dest="workforce_command", required=True)
    workforce_review = workforce_commands.add_parser("review")
    workforce_review.add_argument("--review-id", required=True)
    add_write_options(workforce_review)
    workforce_review.set_defaults(handler=cmd_workforce_review)

    cadence = commands.add_parser("cadence", help="Plan deterministic supervision runs for external schedulers.")
    cadence_commands = cadence.add_subparsers(dest="cadence_command", required=True)
    cadence_due = cadence_commands.add_parser("due")
    cadence_due.add_argument("--as-of", required=True)
    cadence_due.set_defaults(handler=cmd_supervision_due)
    cadence_plan = cadence_commands.add_parser("plan")
    cadence_plan.add_argument("--run-id", required=True)
    cadence_plan.add_argument("--window-start", required=True)
    cadence_plan.add_argument("--window-end", required=True)
    cadence_plan.add_argument("--as-of", required=True)
    add_write_options(cadence_plan)
    cadence_plan.set_defaults(handler=cmd_cadence_plan)
    cadence_record = cadence_commands.add_parser("record")
    cadence_record.add_argument("--run-id", required=True)
    cadence_record.add_argument("--action-id", required=True)
    cadence_record.add_argument("--result", choices=("succeeded", "failed"), required=True)
    cadence_record.add_argument("--result-ref", required=True)
    add_write_options(cadence_record)
    cadence_record.set_defaults(handler=cmd_cadence_record)
    cadence_close = cadence_commands.add_parser("close")
    cadence_close.add_argument("--run-id", required=True)
    cadence_close.add_argument("--outcome", choices=("completed", "failed", "paused"), required=True)
    add_write_options(cadence_close)
    cadence_close.set_defaults(handler=cmd_cadence_close)

    migrate = commands.add_parser("migrate", help="Run recoverable protocol migrations.")
    migrate_commands = migrate.add_subparsers(dest="migrate_command", required=True)
    migrate_portfolio = migrate_commands.add_parser("portfolio-v1")
    add_write_options(migrate_portfolio)
    migrate_portfolio.set_defaults(handler=cmd_migrate_portfolio)

    dashboard = commands.add_parser("dashboard", help="Build a disposable read-only local organization dashboard.")
    dashboard_commands = dashboard.add_subparsers(dest="dashboard_command", required=True)
    dashboard_build = dashboard_commands.add_parser("build")
    dashboard_build.add_argument("--as-of", required=True)
    add_write_options(dashboard_build)
    dashboard_build.set_defaults(handler=cmd_dashboard_build)

    shadow = commands.add_parser("shadow", help="Compare a read-only external snapshot without importing private state.")
    shadow_commands = shadow.add_subparsers(dest="shadow_command", required=True)
    shadow_compare = shadow_commands.add_parser("compare")
    shadow_compare.add_argument("--snapshot", required=True)
    shadow_compare.set_defaults(handler=cmd_shadow_compare)

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
    adapter_dispatch = adapter_commands.add_parser("render-dispatch")
    adapter_dispatch.add_argument("--adapter", choices=ADAPTERS, required=True)
    adapter_dispatch.add_argument("--dispatch-id", required=True)
    add_write_options(adapter_dispatch)
    adapter_dispatch.set_defaults(handler=cmd_adapter_dispatch)
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
