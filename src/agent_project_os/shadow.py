"""Read-only comparison against a user-supplied external control-plane snapshot."""

from pathlib import Path
from typing import Any, Dict, List

from .organization import load_registry, registry_projects
from .records import read_json
from .workforce import list_agents
from .projections import organization_snapshot


def compare_snapshot(root: Path, snapshot_path: Path) -> Dict[str, Any]:
    snapshot = read_json(snapshot_path)
    external_projects = {str(item.get("project_id")): item for item in snapshot.get("projects", [])}
    current_snapshot = organization_snapshot(root, str(snapshot.get("as_of") or "9999-12-31T23:59:59Z"))
    current_projects = {str(item.get("project_id")): item for item in current_snapshot["projects"]}
    external_agents = {str(item.get("agent_id")): item for item in snapshot.get("agents", [])}
    current_agents = {str(item.get("agent_id")): item for item in list_agents(root)}
    differences: List[Dict[str, Any]] = []
    for project_id in sorted(set(external_projects) | set(current_projects)):
        if project_id not in external_projects:
            differences.append({"kind": "project", "id": project_id, "field": "presence", "external": "missing", "current": "present"})
            continue
        if project_id not in current_projects:
            differences.append({"kind": "project", "id": project_id, "field": "presence", "external": "present", "current": "missing"})
            continue
        for field in ("owner", "priority", "lifecycle", "pm_agent_id", "report_status", "blockers", "next_acceptance"):
            if field in external_projects[project_id] and external_projects[project_id].get(field) != current_projects[project_id].get(field):
                differences.append({"kind": "project", "id": project_id, "field": field, "external": external_projects[project_id].get(field), "current": current_projects[project_id].get(field)})
    for agent_id in sorted(set(external_agents) | set(current_agents)):
        if agent_id not in external_agents or agent_id not in current_agents:
            differences.append({"kind": "agent", "id": agent_id, "field": "presence", "external": "present" if agent_id in external_agents else "missing", "current": "present" if agent_id in current_agents else "missing"})
            continue
        for field in ("lifecycle", "active_release_id"):
            if field in external_agents[agent_id] and external_agents[agent_id].get(field) != current_agents[agent_id].get(field):
                differences.append({"kind": "agent", "id": agent_id, "field": field, "external": external_agents[agent_id].get(field), "current": current_agents[agent_id].get(field)})
    return {
        "status": "match" if not differences else "different",
        "projects_compared": len(set(external_projects) | set(current_projects)),
        "agents_compared": len(set(external_agents) | set(current_agents)),
        "differences": differences,
    }
