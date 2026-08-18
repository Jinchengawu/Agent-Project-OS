"""Organization-level CEO/PMO governance over autonomous project repositories."""

import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .records import read_json, utc_now, write_json
from .validation import validate_project
from .federation import detect_cycle, interface_name


ORGANIZATION_DIRS = (
    "assignments",
    "dispatches",
    "supervision",
    "reports",
    "reviews",
    "workforce/agents",
    "workforce/roles",
    "workforce/capabilities",
    "workforce/releases",
    "workforce/evaluations",
    "workforce/upgrades",
    "workforce/reviews",
    "workforce/assignments",
    "cadence",
    "events",
)


def organization_path(root: Path) -> Path:
    return root / ".agent-project" / "organization.json"


def registry_path(root: Path) -> Path:
    return root / ".agent-project" / "project-registry.json"


def has_organization(root: Path) -> bool:
    return organization_path(root).is_file()


def load_organization(root: Path) -> Dict[str, Any]:
    return read_json(organization_path(root))


def load_registry(root: Path) -> Dict[str, Any]:
    return read_json(registry_path(root))


def registry_projects(registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    projects = registry.get("projects")
    if not isinstance(projects, list):
        raise ValueError("project registry projects must be an array")
    result: Dict[str, Dict[str, Any]] = {}
    for item in projects:
        if not isinstance(item, dict) or not isinstance(item.get("project_id"), str):
            raise ValueError("project registry contains an invalid project record")
        project_id = str(item["project_id"])
        if project_id in result:
            raise ValueError("duplicate project id: {}".format(project_id))
        result[project_id] = item
    return result


def init_organization(
    root: Path,
    organization_id: str,
    name: str,
    founder: str,
    ceo_agent_id: str,
    pmo_agent_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if organization_path(root).exists() or registry_path(root).exists():
        raise ValueError("organization already initialized")
    now = utc_now()
    organization = {
        "$schema": "https://agent-project-os.org/schemas/organization-manifest-v1.schema.json",
        "protocol_version": "1.0",
        "organization_id": organization_id,
        "name": name,
        "founder": founder,
        "executive_roles": {
            "ceo": ceo_agent_id,
            "pmo": pmo_agent_id,
        },
        "human_authority": [
            "production",
            "credentials",
            "funds",
            "permissions",
            "public_release",
            "destructive_migration",
            "agent_promotion",
        ],
        "created_at": now,
        "updated_at": now,
    }
    registry = {
        "$schema": "https://agent-project-os.org/schemas/project-registry-v1.schema.json",
        "protocol_version": "1.0",
        "organization_id": organization_id,
        "projects": [],
        "created_at": now,
        "updated_at": now,
    }
    if not dry_run:
        for directory in ORGANIZATION_DIRS:
            (root / ".agent-project" / directory).mkdir(parents=True, exist_ok=True)
    write_json(organization_path(root), organization, dry_run)
    write_json(registry_path(root), registry, dry_run)
    return {"organization": organization, "registry": registry}


def add_registered_project(
    root: Path,
    project_id: str,
    relative_path: str,
    owner: str,
    priority: str,
    lifecycle: str,
    repository: Optional[str],
    depends_on: Iterable[str],
    provides: Iterable[str],
    consumes: Iterable[str],
    verification: Iterable[str],
    supervision: str,
    supervision_timezone: str,
    next_due_at: Optional[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    registry = load_registry(root)
    projects = registry_projects(registry)
    if project_id in projects:
        raise ValueError("project already exists: {}".format(project_id))
    unknown = sorted(set(depends_on) - set(projects))
    if unknown:
        raise ValueError("unknown dependencies: {}".format(unknown))
    project_root = (root / relative_path).resolve()
    manifest = read_json(project_root / ".agent-project" / "manifest.json")
    if manifest.get("project_id") != project_id:
        raise ValueError(
            "project path manifest id is {!r}, expected {!r}".format(manifest.get("project_id"), project_id)
        )
    record = {
        "project_id": project_id,
        "owner": owner,
        "priority": priority,
        "lifecycle": lifecycle,
        "path": relative_path,
        "repository": repository,
        "depends_on": sorted(set(depends_on)),
        "provides": sorted(set(provides)),
        "consumes": sorted(set(consumes)),
        "verification": list(verification),
        "supervision": {
            "cadence": supervision,
            "timezone": supervision_timezone,
            "next_due_at": next_due_at,
        },
    }
    registry["projects"].append(record)
    registry["projects"] = sorted(registry["projects"], key=lambda item: item["project_id"])
    registry["updated_at"] = utc_now()
    write_json(registry_path(root), registry, dry_run)
    return record


def assignment_path(root: Path, assignment_id: str) -> Path:
    return root / ".agent-project" / "assignments" / "{}.json".format(assignment_id)


def all_records(directory: Path) -> List[Dict[str, Any]]:
    if not directory.exists():
        return []
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def active_pm_assignment(root: Path, project_id: str) -> Optional[Dict[str, Any]]:
    active = [
        item
        for item in all_records(root / ".agent-project" / "assignments")
        if item.get("project_id") == project_id
        and item.get("role") == "accountable_pm"
        and item.get("status") == "active"
    ]
    if len(active) > 1:
        raise ValueError("project {} must have exactly one accountable PM".format(project_id))
    return active[0] if active else None


def assign_project_pm(
    root: Path,
    assignment_id: str,
    project_id: str,
    pm_agent_id: str,
    assigned_by: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    projects = registry_projects(load_registry(root))
    if project_id not in projects:
        raise ValueError("unknown project: {}".format(project_id))
    if assignment_path(root, assignment_id).exists():
        raise ValueError("assignment already exists: {}".format(assignment_id))
    if active_pm_assignment(root, project_id):
        raise ValueError("project {} must have exactly one accountable PM".format(project_id))
    assignment = {
        "$schema": "https://agent-project-os.org/schemas/role-assignment-v1.schema.json",
        "protocol_version": "1.0",
        "assignment_id": assignment_id,
        "scope": "project",
        "project_id": project_id,
        "role": "accountable_pm",
        "agent_id": pm_agent_id,
        "status": "active",
        "assigned_by": assigned_by,
        "assigned_at": utc_now(),
    }
    write_json(assignment_path(root, assignment_id), assignment, dry_run)
    return assignment


def dispatch_path(root: Path, dispatch_id: str) -> Path:
    return root / ".agent-project" / "dispatches" / "{}.json".format(dispatch_id)


def create_dispatch(
    root: Path,
    dispatch_id: str,
    project_id: str,
    objective: str,
    expected_outputs: Iterable[str],
    acceptance_criteria: Iterable[str],
    due_at: str,
    issued_by: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    projects = registry_projects(load_registry(root))
    if project_id not in projects:
        raise ValueError("unknown project: {}".format(project_id))
    if dispatch_path(root, dispatch_id).exists():
        raise ValueError("dispatch already exists: {}".format(dispatch_id))
    organization = load_organization(root)
    allowed_issuers = {
        str(organization.get("founder")),
        str((organization.get("executive_roles") or {}).get("ceo")),
        str((organization.get("executive_roles") or {}).get("pmo")),
    }
    if issued_by not in allowed_issuers:
        raise ValueError("dispatch issuer is outside Founder/CEO/PMO authority")
    assignment = active_pm_assignment(root, project_id)
    if not assignment:
        raise ValueError("active project {} has no accountable PM".format(project_id))
    dispatch = {
        "$schema": "https://agent-project-os.org/schemas/dispatch-envelope-v1.schema.json",
        "protocol_version": "1.0",
        "dispatch_id": dispatch_id,
        "project_id": project_id,
        "assigned_to": assignment["agent_id"],
        "objective": objective,
        "expected_outputs": list(expected_outputs),
        "acceptance_criteria": list(acceptance_criteria),
        "due_at": due_at,
        "status": "issued",
        "issued_by": issued_by,
        "created_at": utc_now(),
    }
    write_json(dispatch_path(root, dispatch_id), dispatch, dry_run)
    return dispatch


def report_path(root: Path, report_id: str) -> Path:
    return root / ".agent-project" / "reports" / "{}.json".format(report_id)


def reports_for_dispatch(root: Path, dispatch_id: str) -> List[Dict[str, Any]]:
    return [
        item
        for item in all_records(root / ".agent-project" / "reports")
        if item.get("dispatch_id") == dispatch_id
    ]


def submit_report(
    root: Path,
    report_id: str,
    dispatch_id: str,
    summary: str,
    project_commit: str,
    reported_status: str,
    next_acceptance: str,
    evidence_refs: Iterable[str],
    blockers: Iterable[str],
    submitted_by: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if report_path(root, report_id).exists():
        raise ValueError("report already exists: {}".format(report_id))
    dispatch = read_json(dispatch_path(root, dispatch_id))
    if reports_for_dispatch(root, dispatch_id):
        raise ValueError("dispatch already has a submitted report: {}".format(dispatch_id))
    if submitted_by != dispatch.get("assigned_to"):
        raise ValueError("report submitter is not the accountable project PM")
    evidence_ref_list = list(evidence_refs)
    blocker_list = list(blockers)
    if reported_status == "done" and not evidence_ref_list:
        raise ValueError("reported done status requires at least one evidence reference")
    projects = registry_projects(load_registry(root))
    project = projects.get(str(dispatch["project_id"]))
    if not project:
        raise ValueError("dispatch references an unknown project")
    project_root = (root / str(project.get("path", ""))).resolve()
    commit_verification: Dict[str, Any] = {"status": "unavailable"}
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        completed = None
    if completed is not None and completed.returncode == 0:
        current_commit = completed.stdout.strip()
        if not current_commit.startswith(project_commit) and not project_commit.startswith(current_commit):
            raise ValueError("stale project report commit; current Git HEAD differs")
        commit_verification = {"status": "matched", "git_head": current_commit}
    report = {
        "$schema": "https://agent-project-os.org/schemas/child-pm-report-v1.schema.json",
        "protocol_version": "1.0",
        "report_id": report_id,
        "dispatch_id": dispatch_id,
        "project_id": dispatch["project_id"],
        "submitted_by": submitted_by,
        "summary": summary,
        "project_commit": project_commit,
        "commit_verification": commit_verification,
        "reported_status": reported_status,
        "next_acceptance": next_acceptance,
        "blockers": blocker_list,
        "evidence_refs": evidence_ref_list,
        "submitted_at": utc_now(),
    }
    write_json(report_path(root, report_id), report, dry_run)
    return report


def supervision_review_path(root: Path, review_id: str) -> Path:
    return root / ".agent-project" / "reviews" / "{}.json".format(review_id)


def report_review(root: Path, report_id: str) -> Optional[Dict[str, Any]]:
    reviews = [
        item
        for item in all_records(root / ".agent-project" / "reviews")
        if item.get("review_type") == "supervision_report" and item.get("report_id") == report_id
    ]
    if len(reviews) > 1:
        raise ValueError("report has multiple terminal reviews: {}".format(report_id))
    return reviews[0] if reviews else None


def review_report(
    root: Path,
    review_id: str,
    report_id: str,
    outcome: str,
    reviewed_by: str,
    note: str,
    reviewed_at: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if supervision_review_path(root, review_id).exists():
        raise ValueError("review already exists: {}".format(review_id))
    report = read_json(report_path(root, report_id))
    if report_review(root, report_id):
        raise ValueError("report already reviewed: {}".format(report_id))
    if reviewed_by == report.get("submitted_by"):
        raise ValueError("project PM cannot review its own supervision report")
    organization = load_organization(root)
    allowed_reviewers = {
        str(organization.get("founder")),
        str((organization.get("executive_roles") or {}).get("pmo")),
    }
    if reviewed_by not in allowed_reviewers:
        raise ValueError("supervision report requires PMO or Founder review")
    review_time = reviewed_at or utc_now()
    parse_timestamp(review_time)
    review = {
        "$schema": "https://agent-project-os.org/schemas/supervision-review-v1.schema.json",
        "protocol_version": "1.0",
        "review_id": review_id,
        "review_type": "supervision_report",
        "report_id": report_id,
        "project_id": report["project_id"],
        "outcome": outcome,
        "reviewed_by": reviewed_by,
        "note": note,
        "reviewed_at": review_time,
    }
    write_json(supervision_review_path(root, review_id), review, dry_run)
    if outcome == "accepted":
        advance_project_due(root, str(report["project_id"]), review_time, dry_run)
    return review


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid RFC 3339 timestamp: {}".format(value))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone: {}".format(value))
    return parsed.astimezone(timezone.utc)


def due_projects(root: Path, as_of: str) -> List[Dict[str, Any]]:
    moment = parse_timestamp(as_of)
    result = []
    for project_id, project in sorted(registry_projects(load_registry(root)).items()):
        if project.get("lifecycle") != "active":
            continue
        supervision = project.get("supervision") or {}
        due_at = supervision.get("next_due_at")
        if due_at and parse_timestamp(str(due_at)) <= moment:
            assignment = active_pm_assignment(root, project_id)
            result.append(
                {
                    "project_id": project_id,
                    "pm_agent_id": assignment.get("agent_id") if assignment else None,
                    "due_at": due_at,
                    "cadence": supervision.get("cadence"),
                }
            )
    return result


def next_occurrence(value: str, cadence: str, timezone_name: str) -> str:
    current = parse_timestamp(value)
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise ValueError("unknown supervision timezone: {}".format(timezone_name))
    local = current.astimezone(zone)
    if cadence == "daily":
        next_local = local + timedelta(days=1)
    elif cadence == "weekly":
        next_local = local + timedelta(days=7)
    elif cadence == "monthly":
        year = local.year + (1 if local.month == 12 else 0)
        month = 1 if local.month == 12 else local.month + 1
        day = min(local.day, calendar.monthrange(year, month)[1])
        next_local = local.replace(year=year, month=month, day=day)
    else:
        raise ValueError("unknown supervision cadence: {}".format(cadence))
    return next_local.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def advance_project_due(root: Path, project_id: str, after: str, dry_run: bool = False) -> str:
    registry = load_registry(root)
    projects = registry_projects(registry)
    if project_id not in projects:
        raise ValueError("unknown project: {}".format(project_id))
    supervision = projects[project_id].get("supervision") or {}
    cadence = str(supervision.get("cadence"))
    timezone_name = str(supervision.get("timezone") or "UTC")
    due_at = supervision.get("next_due_at") or after
    after_time = parse_timestamp(after)
    next_due = str(due_at)
    while parse_timestamp(next_due) <= after_time:
        next_due = next_occurrence(next_due, cadence, timezone_name)
    supervision["next_due_at"] = next_due
    projects[project_id]["supervision"] = supervision
    registry["projects"] = [projects[key] for key in sorted(projects)]
    registry["updated_at"] = utc_now()
    write_json(registry_path(root), registry, dry_run)
    return next_due


def portfolio_review_path(root: Path, review_id: str) -> Path:
    return root / ".agent-project" / "reviews" / "portfolio-{}.json".format(review_id)


def build_portfolio_review(root: Path, review_id: str, as_of: str, dry_run: bool = False) -> Dict[str, Any]:
    path = portfolio_review_path(root, review_id)
    if path.exists():
        raise ValueError("portfolio review already exists: {}".format(review_id))
    project_rows = []
    decision_queue = []
    project_items = registry_projects(load_registry(root)).items()
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    for project_id, project in sorted(project_items, key=lambda item: (priority_order.get(str(item[1].get("priority")), 9), item[0])):
        assignment = active_pm_assignment(root, project_id)
        project_reports = [
            item
            for item in all_records(root / ".agent-project" / "reports")
            if item.get("project_id") == project_id
        ]
        latest = sorted(project_reports, key=lambda item: str(item.get("submitted_at", "")))[-1] if project_reports else None
        review = report_review(root, str(latest["report_id"])) if latest else None
        report_status = review.get("outcome") if review else ("pending_review" if latest else "missing")
        blockers = list(latest.get("blockers", [])) if latest else []
        row = {
            "project_id": project_id,
            "owner": project.get("owner"),
            "priority": project.get("priority"),
            "pm_agent_id": assignment.get("agent_id") if assignment else None,
            "lifecycle": project.get("lifecycle"),
            "report_id": latest.get("report_id") if latest else None,
            "report_status": report_status,
            "blockers": blockers,
            "next_acceptance": latest.get("next_acceptance") if latest else None,
        }
        project_rows.append(row)
        if project.get("lifecycle") == "active" and (not assignment or report_status in {"missing", "rejected"} or blockers):
            decision_queue.append(
                {
                    "project_id": project_id,
                    "reason": "missing_pm" if not assignment else ("blocker" if blockers else report_status),
                }
            )
    review_record = {
        "$schema": "https://agent-project-os.org/schemas/portfolio-review-v1.schema.json",
        "protocol_version": "1.0",
        "review_id": review_id,
        "organization_id": load_organization(root)["organization_id"],
        "as_of": as_of,
        "projects": project_rows,
        "ceo_decision_queue": decision_queue,
        "created_at": utc_now(),
    }
    write_json(path, review_record, dry_run)
    return review_record


def validate_organization(root: Path) -> List[str]:
    errors: List[str] = []
    try:
        organization = load_organization(root)
        registry = load_registry(root)
        projects = registry_projects(registry)
    except ValueError as error:
        return [str(error)]
    if registry.get("organization_id") != organization.get("organization_id"):
        errors.append("project registry organization_id does not match organization")
    if (root / "portfolio.json").exists():
        errors.append("legacy portfolio.json and project-registry.json cannot be dual-written")
    cycle = detect_cycle(projects)
    if cycle:
        errors.append("project dependency cycle: {}".format(" -> ".join(cycle)))
    providers: Dict[str, List[str]] = {}
    for project_id, project in projects.items():
        for contract in project.get("provides", []):
            providers.setdefault(interface_name(str(contract)), []).append(str(contract))
    for project_id, project in sorted(projects.items()):
        project_root = (root / str(project.get("path", ""))).resolve()
        try:
            manifest = read_json(project_root / ".agent-project" / "manifest.json")
        except ValueError as error:
            errors.append("project {}: {}".format(project_id, error))
            continue
        if manifest.get("project_id") != project_id:
            errors.append("project {} path resolves to manifest {}".format(project_id, manifest.get("project_id")))
        errors.extend("project {}: {}".format(project_id, item) for item in validate_project(project_root))
        unknown = sorted(set(project.get("depends_on", [])) - set(projects))
        if unknown:
            errors.append("project {} has unknown dependencies {}".format(project_id, unknown))
        for contract in project.get("consumes", []):
            contract = str(contract)
            if contract.startswith("external:"):
                continue
            available = providers.get(interface_name(contract), [])
            if not available:
                errors.append("project {} consumes interface without provider: {}".format(project_id, contract))
            elif contract not in available:
                errors.append("project {} consumes incompatible interface {}; available {}".format(project_id, contract, sorted(available)))
        supervision = project.get("supervision") or {}
        timezone_name = str(supervision.get("timezone") or "UTC")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            errors.append("project {} has unknown supervision timezone {}".format(project_id, timezone_name))
        if supervision.get("next_due_at"):
            try:
                parse_timestamp(str(supervision["next_due_at"]))
            except ValueError as error:
                errors.append("project {}: {}".format(project_id, error))
        try:
            assignment = active_pm_assignment(root, project_id)
        except ValueError as error:
            errors.append(str(error))
            assignment = None
        if project.get("lifecycle") == "active" and assignment is None:
            errors.append("active project {} has no accountable PM".format(project_id))
    for assignment in all_records(root / ".agent-project" / "assignments"):
        if assignment.get("project_id") not in projects:
            errors.append("assignment {} references unknown project".format(assignment.get("assignment_id")))
    from .workforce import list_agents, validate_workforce

    known_agents = {str(item.get("agent_id")) for item in list_agents(root)}
    if known_agents:
        for assignment in all_records(root / ".agent-project" / "assignments"):
            if assignment.get("agent_id") not in known_agents:
                errors.append("assignment {} references an unregistered Agent".format(assignment.get("assignment_id")))
    for dispatch in all_records(root / ".agent-project" / "dispatches"):
        if dispatch.get("project_id") not in projects:
            errors.append("dispatch {} references unknown project".format(dispatch.get("dispatch_id")))
    for report in all_records(root / ".agent-project" / "reports"):
        try:
            dispatch = read_json(dispatch_path(root, str(report.get("dispatch_id"))))
        except ValueError:
            errors.append("report {} references unknown dispatch".format(report.get("report_id")))
            continue
        if dispatch.get("project_id") != report.get("project_id"):
            errors.append("report {} project does not match dispatch".format(report.get("report_id")))
    from .cadence import validate_cadence

    errors.extend(validate_workforce(root))
    errors.extend(validate_cadence(root))
    return errors
