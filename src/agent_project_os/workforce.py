"""Agent HR registry, evaluation, release promotion, rollback, and retirement rules."""

import hashlib
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

from .records import read_json, utc_now, write_json


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def workforce_root(root: Path) -> Path:
    return root / ".agent-project" / "workforce"


def record_path(root: Path, collection: str, record_id: str) -> Path:
    return workforce_root(root) / collection / "{}.json".format(safe_id(record_id))


def records(root: Path, collection: str) -> List[Dict[str, Any]]:
    directory = workforce_root(root) / collection
    if not directory.exists():
        return []
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def find_record(root: Path, collection: str, id_field: str, record_id: str) -> Dict[str, Any]:
    for item in records(root, collection):
        if item.get(id_field) == record_id:
            return item
    raise ValueError("{} not found: {}".format(id_field.replace("_id", ""), record_id))


def verify_asset(root: Path, asset_path: str, expected_sha256: str) -> None:
    path = (root / asset_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise ValueError("agent asset must remain inside the organization repository")
    if not path.is_file():
        raise ValueError("agent asset not found: {}".format(asset_path))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError("agent asset digest mismatch for {}".format(asset_path))


def add_role(
    root: Path,
    role_id: str,
    name: str,
    purpose: str,
    authority: Iterable[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    if any(item.get("role_id") == role_id for item in records(root, "roles")):
        raise ValueError("role already exists: {}".format(role_id))
    role = {
        "$schema": "https://agent-project-os.org/schemas/role-v1.schema.json",
        "protocol_version": "1.0",
        "role_id": role_id,
        "name": name,
        "purpose": purpose,
        "authority": sorted(set(authority)),
        "status": "active",
        "created_at": utc_now(),
    }
    write_json(record_path(root, "roles", role_id), role, dry_run)
    return role


def assign_role(
    root: Path,
    assignment_id: str,
    agent_id: str,
    role_id: str,
    scope: str,
    project_id: Optional[str],
    assigned_by: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    get_agent(root, agent_id)
    find_record(root, "roles", "role_id", role_id)
    if any(item.get("assignment_id") == assignment_id for item in records(root, "assignments")):
        raise ValueError("role assignment already exists: {}".format(assignment_id))
    if scope == "project" and not project_id:
        raise ValueError("project-scoped role assignment requires --project-id")
    assignment = {
        "$schema": "https://agent-project-os.org/schemas/role-assignment-v1.schema.json",
        "protocol_version": "1.0",
        "assignment_id": assignment_id,
        "scope": scope,
        "project_id": project_id,
        "role": role_id,
        "agent_id": agent_id,
        "status": "active",
        "assigned_by": assigned_by,
        "assigned_at": utc_now(),
    }
    write_json(record_path(root, "assignments", assignment_id), assignment, dry_run)
    return assignment


def add_agent(
    root: Path,
    agent_id: str,
    name: str,
    role_ids: Iterable[str],
    release_id: Optional[str] = None,
    asset_path: Optional[str] = None,
    asset_commit: Optional[str] = None,
    asset_sha256: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if any(item.get("agent_id") == agent_id for item in records(root, "agents")):
        raise ValueError("agent already exists: {}".format(agent_id))
    known_roles = {str(item.get("role_id")) for item in records(root, "roles")}
    unknown = sorted(set(role_ids) - known_roles)
    if unknown:
        raise ValueError("unknown roles: {}".format(unknown))
    release_fields = (release_id, asset_path, asset_commit, asset_sha256)
    if any(release_fields) and not all(release_fields):
        raise ValueError("initial release requires release id, asset path, commit, and sha256")
    now = utc_now()
    agent = {
        "$schema": "https://agent-project-os.org/schemas/agent-registry-v1.schema.json",
        "protocol_version": "1.0",
        "agent_id": agent_id,
        "name": name,
        "role_ids": sorted(set(role_ids)),
        "lifecycle": "active",
        "active_release_id": release_id,
        "candidate_release_id": None,
        "created_at": now,
        "updated_at": now,
    }
    if release_id and asset_path and asset_commit and asset_sha256:
        verify_asset(root, asset_path, asset_sha256)
        if any(item.get("release_id") == release_id for item in records(root, "releases")):
            raise ValueError("release already exists: {}".format(release_id))
        release = {
            "$schema": "https://agent-project-os.org/schemas/agent-release-v1.schema.json",
            "protocol_version": "1.0",
            "release_id": release_id,
            "agent_id": agent_id,
            "status": "active",
            "asset": {"path": asset_path, "commit": asset_commit, "sha256": asset_sha256},
            "rollback_release_id": None,
            "created_at": now,
            "activated_at": now,
        }
        write_json(record_path(root, "releases", release_id), release, dry_run)
    profile = {
        "$schema": "https://agent-project-os.org/schemas/capability-profile-v1.schema.json",
        "protocol_version": "1.0",
        "profile_id": "capability-{}".format(safe_id(agent_id)),
        "agent_id": agent_id,
        "capabilities": [],
        "updated_at": now,
    }
    write_json(record_path(root, "capabilities", str(profile["profile_id"])), profile, dry_run)
    write_json(record_path(root, "agents", agent_id), agent, dry_run)
    return agent


def list_agents(root: Path) -> List[Dict[str, Any]]:
    return sorted(records(root, "agents"), key=lambda item: str(item.get("agent_id")))


def get_agent(root: Path, agent_id: str) -> Dict[str, Any]:
    return find_record(root, "agents", "agent_id", agent_id)


def save_agent(root: Path, agent: Dict[str, Any], dry_run: bool = False) -> None:
    agent["updated_at"] = utc_now()
    write_json(record_path(root, "agents", str(agent["agent_id"])), agent, dry_run)


def add_evaluation(
    root: Path,
    evaluation_id: str,
    agent_id: str,
    reviewer: str,
    score: int,
    outcome: str,
    evidence_refs: Iterable[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    get_agent(root, agent_id)
    get_agent(root, reviewer)
    if reviewer == agent_id:
        raise ValueError("agent cannot review its own evaluation")
    if any(item.get("evaluation_id") == evaluation_id for item in records(root, "evaluations")):
        raise ValueError("evaluation already exists: {}".format(evaluation_id))
    if not 1 <= score <= 5:
        raise ValueError("evaluation score must be between 1 and 5")
    evaluation = {
        "$schema": "https://agent-project-os.org/schemas/agent-evaluation-v1.schema.json",
        "protocol_version": "1.0",
        "evaluation_id": evaluation_id,
        "agent_id": agent_id,
        "reviewer": reviewer,
        "score": score,
        "outcome": outcome,
        "evidence_refs": list(evidence_refs),
        "evaluated_at": utc_now(),
    }
    write_json(record_path(root, "evaluations", evaluation_id), evaluation, dry_run)
    return evaluation


def propose_upgrade(
    root: Path,
    proposal_id: str,
    agent_id: str,
    release_id: str,
    asset_path: str,
    asset_commit: str,
    asset_sha256: str,
    evaluation_id: str,
    proposed_by: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    agent = get_agent(root, agent_id)
    if agent.get("candidate_release_id"):
        raise ValueError("agent already has a candidate release")
    if any(item.get("proposal_id") == proposal_id for item in records(root, "upgrades")):
        raise ValueError("upgrade proposal already exists: {}".format(proposal_id))
    if any(item.get("release_id") == release_id for item in records(root, "releases")):
        raise ValueError("release already exists: {}".format(release_id))
    evaluation = find_record(root, "evaluations", "evaluation_id", evaluation_id)
    if evaluation.get("agent_id") != agent_id or evaluation.get("outcome") != "passed":
        raise ValueError("candidate release requires a passed evaluation for the same agent")
    verify_asset(root, asset_path, asset_sha256)
    now = utc_now()
    release = {
        "$schema": "https://agent-project-os.org/schemas/agent-release-v1.schema.json",
        "protocol_version": "1.0",
        "release_id": release_id,
        "agent_id": agent_id,
        "status": "candidate",
        "asset": {"path": asset_path, "commit": asset_commit, "sha256": asset_sha256},
        "rollback_release_id": agent.get("active_release_id"),
        "created_at": now,
        "activated_at": None,
    }
    proposal = {
        "$schema": "https://agent-project-os.org/schemas/agent-upgrade-proposal-v1.schema.json",
        "protocol_version": "1.0",
        "proposal_id": proposal_id,
        "agent_id": agent_id,
        "candidate_release_id": release_id,
        "evaluation_id": evaluation_id,
        "proposed_by": proposed_by,
        "status": "proposed",
        "created_at": now,
        "reviewed_at": None,
        "approved_by": None,
    }
    agent["candidate_release_id"] = release_id
    write_json(record_path(root, "releases", release_id), release, dry_run)
    write_json(record_path(root, "upgrades", proposal_id), proposal, dry_run)
    save_agent(root, agent, dry_run)
    return proposal


def save_release(root: Path, release: Dict[str, Any], dry_run: bool = False) -> None:
    write_json(record_path(root, "releases", str(release["release_id"])), release, dry_run)


def promote_upgrade(root: Path, proposal_id: str, approved_by: str, dry_run: bool = False) -> Dict[str, Any]:
    proposal = find_record(root, "upgrades", "proposal_id", proposal_id)
    if proposal.get("status") != "proposed":
        raise ValueError("upgrade proposal is not awaiting approval")
    agent = get_agent(root, str(proposal["agent_id"]))
    evaluation = find_record(root, "evaluations", "evaluation_id", str(proposal["evaluation_id"]))
    candidate = str(agent["agent_id"])
    reviewer = str(evaluation["reviewer"])
    if len({candidate, reviewer, approved_by}) != 3:
        raise ValueError("candidate, reviewer, and approver must be separate")
    get_agent(root, approved_by)
    if evaluation.get("outcome") != "passed":
        raise ValueError("upgrade cannot be promoted without a passed evaluation")
    release = find_record(root, "releases", "release_id", str(proposal["candidate_release_id"]))
    verify_asset(root, str(release["asset"]["path"]), str(release["asset"]["sha256"]))
    previous_id = agent.get("active_release_id")
    if previous_id:
        previous = find_record(root, "releases", "release_id", str(previous_id))
        previous["status"] = "superseded"
        save_release(root, previous, dry_run)
    now = utc_now()
    release["status"] = "active"
    release["activated_at"] = now
    release["approved_by"] = approved_by
    proposal["status"] = "accepted"
    proposal["approved_by"] = approved_by
    proposal["reviewed_at"] = now
    agent["active_release_id"] = release["release_id"]
    agent["candidate_release_id"] = None
    save_release(root, release, dry_run)
    write_json(record_path(root, "upgrades", proposal_id), proposal, dry_run)
    save_agent(root, agent, dry_run)
    return proposal


def rollback_agent(
    root: Path,
    agent_id: str,
    approved_by: str,
    reason: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    agent = get_agent(root, agent_id)
    if approved_by == agent_id:
        raise ValueError("agent cannot approve its own rollback")
    get_agent(root, approved_by)
    current = find_record(root, "releases", "release_id", str(agent.get("active_release_id")))
    rollback_id = current.get("rollback_release_id")
    if not rollback_id:
        raise ValueError("active release has no valid rollback point")
    target = find_record(root, "releases", "release_id", str(rollback_id))
    verify_asset(root, str(target["asset"]["path"]), str(target["asset"]["sha256"]))
    current["status"] = "rolled_back"
    current["rollback_reason"] = reason
    current["rolled_back_at"] = utc_now()
    target["status"] = "active"
    target["reactivated_at"] = utc_now()
    target["reactivated_by"] = approved_by
    agent["active_release_id"] = target["release_id"]
    agent["candidate_release_id"] = None
    save_release(root, current, dry_run)
    save_release(root, target, dry_run)
    save_agent(root, agent, dry_run)
    return {"agent_id": agent_id, "from_release_id": current["release_id"], "to_release_id": target["release_id"]}


def change_agent_lifecycle(
    root: Path,
    agent_id: str,
    lifecycle: str,
    approved_by: str,
    reason: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    agent = get_agent(root, agent_id)
    if lifecycle == "retired":
        assignments = root / ".agent-project" / "assignments"
        for path in sorted(assignments.glob("*.json")) if assignments.exists() else []:
            assignment = read_json(path)
            if assignment.get("agent_id") == agent_id and assignment.get("status") == "active":
                raise ValueError("cannot retire an agent with active role assignments")
    agent["lifecycle"] = lifecycle
    agent["lifecycle_reason"] = reason
    agent["lifecycle_approved_by"] = approved_by
    save_agent(root, agent, dry_run)
    return agent


def build_workforce_review(root: Path, review_id: str, dry_run: bool = False) -> Dict[str, Any]:
    if any(item.get("review_id") == review_id for item in records(root, "reviews")):
        raise ValueError("workforce review already exists: {}".format(review_id))
    rows = [
        {
            "agent_id": agent.get("agent_id"),
            "lifecycle": agent.get("lifecycle"),
            "role_ids": agent.get("role_ids", []),
            "active_release_id": agent.get("active_release_id"),
            "candidate_release_id": agent.get("candidate_release_id"),
        }
        for agent in list_agents(root)
    ]
    review = {
        "$schema": "https://agent-project-os.org/schemas/workforce-review-v1.schema.json",
        "protocol_version": "1.0",
        "review_id": review_id,
        "agents": rows,
        "upgrade_queue": [row["agent_id"] for row in rows if row["candidate_release_id"]],
        "created_at": utc_now(),
    }
    write_json(record_path(root, "reviews", review_id), review, dry_run)
    return review


def validate_workforce(root: Path) -> List[str]:
    errors: List[str] = []
    agents = {str(item.get("agent_id")): item for item in records(root, "agents")}
    roles = {str(item.get("role_id")) for item in records(root, "roles")}
    releases = {str(item.get("release_id")): item for item in records(root, "releases")}
    for agent_id, agent in sorted(agents.items()):
        unknown = sorted(set(agent.get("role_ids", [])) - roles)
        if unknown:
            errors.append("agent {} references unknown roles {}".format(agent_id, unknown))
        owned = [item for item in releases.values() if item.get("agent_id") == agent_id]
        active = [item for item in owned if item.get("status") == "active"]
        candidate = [item for item in owned if item.get("status") == "candidate"]
        if len(active) > 1:
            errors.append("agent {} has more than one active release".format(agent_id))
        if len(candidate) > 1:
            errors.append("agent {} has more than one candidate release".format(agent_id))
        if agent.get("active_release_id") and agent.get("active_release_id") not in releases:
            errors.append("agent {} references an unknown active release".format(agent_id))
        if agent.get("candidate_release_id") and agent.get("candidate_release_id") not in releases:
            errors.append("agent {} references an unknown candidate release".format(agent_id))
    for release_id, release in sorted(releases.items()):
        if release.get("agent_id") not in agents:
            errors.append("release {} references unknown agent".format(release_id))
        try:
            verify_asset(root, str(release["asset"]["path"]), str(release["asset"]["sha256"]))
        except (KeyError, TypeError, ValueError) as error:
            errors.append("release {}: {}".format(release_id, error))
    for assignment in records(root, "assignments"):
        if assignment.get("agent_id") not in agents:
            errors.append("role assignment {} references unknown agent".format(assignment.get("assignment_id")))
        if assignment.get("role") not in roles:
            errors.append("role assignment {} references unknown role".format(assignment.get("assignment_id")))
    return errors
