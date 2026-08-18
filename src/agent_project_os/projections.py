"""Disposable organization query index and read-only local dashboard."""

import html
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Dict, List

from .organization import (
    active_pm_assignment,
    all_records,
    due_projects,
    load_organization,
    load_registry,
    registry_projects,
    report_review,
)
from .records import write_json
from .workforce import list_agents


def organization_snapshot(root: Path, as_of: str) -> Dict[str, Any]:
    projects = []
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    project_items = registry_projects(load_registry(root)).items()
    due = due_projects(root, as_of)
    due_by_project = {str(item["project_id"]): item for item in due}
    decision_queue = []
    for project_id, project in sorted(project_items, key=lambda item: (priority_order.get(str(item[1].get("priority")), 9), item[0])):
        assignment = active_pm_assignment(root, project_id)
        reports = [
            item for item in all_records(root / ".agent-project" / "reports")
            if item.get("project_id") == project_id
        ]
        latest = sorted(reports, key=lambda item: str(item.get("submitted_at", "")))[-1] if reports else None
        acceptance = report_review(root, str(latest["report_id"])) if latest else None
        row = {
                "project_id": project_id,
                "priority": project.get("priority"),
                "lifecycle": project.get("lifecycle"),
                "owner": project.get("owner"),
                "pm_agent_id": assignment.get("agent_id") if assignment else None,
                "report_status": acceptance.get("outcome") if acceptance else ("pending_review" if latest else "missing"),
                "blockers": latest.get("blockers", []) if latest else [],
                "next_acceptance": latest.get("next_acceptance") if latest else None,
                "due_at": due_by_project.get(project_id, {}).get("due_at"),
            }
        projects.append(row)
        if project.get("lifecycle") == "active" and (
            not assignment or row["blockers"] or row["report_status"] in {"missing", "rejected"}
        ):
            decision_queue.append({
                "project_id": project_id,
                "priority": project.get("priority"),
                "reason": "missing_pm" if not assignment else ("blocker" if row["blockers"] else row["report_status"]),
            })
    agents = [
        {
            "agent_id": item.get("agent_id"),
            "lifecycle": item.get("lifecycle"),
            "role_ids": item.get("role_ids", []),
            "active_release_id": item.get("active_release_id"),
            "candidate_release_id": item.get("candidate_release_id"),
        }
        for item in list_agents(root)
    ]
    return {
        "projection_version": "1.0",
        "organization_id": load_organization(root)["organization_id"],
        "as_of": as_of,
        "projects": projects,
        "agents": agents,
        "due": due,
        "ceo_decision_queue": decision_queue,
    }


def build_dashboard(root: Path, as_of: str, dry_run: bool = False) -> Dict[str, Any]:
    snapshot = organization_snapshot(root, as_of)
    output = root / ".agent-project" / "index"
    json_path = output / "dashboard.json"
    html_path = output / "dashboard.html"
    write_json(json_path, snapshot, dry_run)
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(str(item["project_id"])),
            html.escape(str(item["priority"])),
            html.escape(str(item["lifecycle"])),
            html.escape(str(item["owner"])),
            html.escape(str(item["pm_agent_id"] or "unassigned")),
            html.escape(str(item["report_status"])),
            html.escape(", ".join(str(value) for value in item["blockers"]) or "—"),
            html.escape(str(item["next_acceptance"] or "—")),
            html.escape(str(item["due_at"] or "—")),
        )
        for item in snapshot["projects"]
    )
    agent_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(str(item["agent_id"])),
            html.escape(str(item["lifecycle"])),
            html.escape(", ".join(str(value) for value in item["role_ids"]) or "—"),
            html.escape(str(item["active_release_id"] or "—")),
            html.escape(str(item["candidate_release_id"] or "—")),
        )
        for item in snapshot["agents"]
    )
    decision_rows = "".join(
        "<li><strong>{}</strong> · {} · {}</li>".format(
            html.escape(str(item["project_id"])),
            html.escape(str(item["priority"])),
            html.escape(str(item["reason"])),
        )
        for item in snapshot["ceo_decision_queue"]
    ) or "<li>No current exception</li>"
    document = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Project OS — {organization}</title>
<style>body{{font:15px system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;color:#172033}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:.7rem;border-bottom:1px solid #d8deea}}.note{{padding:1rem;background:#f3f6fb}}</style>
<h1>{organization}</h1><p class="note">Read-only rebuildable projection. Git records remain the source of truth. As of {as_of}.</p>
<p>{project_count} projects · {agent_count} agents · {due_count} supervision items due · {decision_count} CEO exceptions</p>
<h2>Projects</h2><table><thead><tr><th>Project</th><th>Priority</th><th>Lifecycle</th><th>Owner</th><th>PM</th><th>Report</th><th>Blockers</th><th>Next acceptance</th><th>Due</th></tr></thead><tbody>{rows}</tbody></table>
<h2>CEO decision queue</h2><ul>{decision_rows}</ul>
<h2>Agent workforce</h2><table><thead><tr><th>Agent</th><th>Lifecycle</th><th>Roles</th><th>Active release</th><th>Candidate</th></tr></thead><tbody>{agent_rows}</tbody></table>
</html>
""".format(
        organization=html.escape(str(snapshot["organization_id"])),
        as_of=html.escape(as_of),
        project_count=len(snapshot["projects"]),
        agent_count=len(snapshot["agents"]),
        due_count=len(snapshot["due"]),
        decision_count=len(snapshot["ceo_decision_queue"]),
        rows=rows,
        decision_rows=decision_rows,
        agent_rows=agent_rows,
    )
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
        html_path.write_text(document, encoding="utf-8")
    return {
        "project_count": len(snapshot["projects"]),
        "agent_count": len(snapshot["agents"]),
        "due_count": len(snapshot["due"]),
        "decision_count": len(snapshot["ceo_decision_queue"]),
        "json_path": json_path.relative_to(root).as_posix(),
        "html_path": html_path.relative_to(root).as_posix(),
    }


def rebuild_organization_index(root: Path, dry_run: bool = False) -> Dict[str, int]:
    registry = registry_projects(load_registry(root))
    assignments = all_records(root / ".agent-project" / "assignments")
    reports = all_records(root / ".agent-project" / "reports")
    agents = list_agents(root)
    summary = {
        "projects": len(registry),
        "assignments": len(assignments),
        "reports": len(reports),
        "agents": len(agents),
    }
    if dry_run:
        return summary
    control = root / ".agent-project"
    control.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="organization-index-", suffix=".sqlite3", dir=str(control), delete=False) as handle:
        temporary = Path(handle.name)
    try:
        connection = sqlite3.connect(str(temporary))
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            CREATE TABLE projects (project_id TEXT PRIMARY KEY, lifecycle TEXT, owner TEXT, path TEXT);
            CREATE TABLE assignments (assignment_id TEXT PRIMARY KEY, project_id TEXT, agent_id TEXT, role TEXT, status TEXT);
            CREATE TABLE reports (report_id TEXT PRIMARY KEY, project_id TEXT, dispatch_id TEXT, submitted_at TEXT);
            CREATE TABLE agents (agent_id TEXT PRIMARY KEY, lifecycle TEXT, active_release_id TEXT, candidate_release_id TEXT);
            """
        )
        connection.executemany(
            "INSERT INTO projects VALUES (?, ?, ?, ?)",
            [(key, str(value.get("lifecycle")), str(value.get("owner")), str(value.get("path"))) for key, value in sorted(registry.items())],
        )
        connection.executemany(
            "INSERT INTO assignments VALUES (?, ?, ?, ?, ?)",
            [(str(item.get("assignment_id")), str(item.get("project_id")), str(item.get("agent_id")), str(item.get("role")), str(item.get("status"))) for item in assignments],
        )
        connection.executemany(
            "INSERT INTO reports VALUES (?, ?, ?, ?)",
            [(str(item.get("report_id")), str(item.get("project_id")), str(item.get("dispatch_id")), str(item.get("submitted_at"))) for item in reports],
        )
        connection.executemany(
            "INSERT INTO agents VALUES (?, ?, ?, ?)",
            [(str(item.get("agent_id")), str(item.get("lifecycle")), item.get("active_release_id"), item.get("candidate_release_id")) for item in agents],
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        os.replace(str(temporary), str(control / "index.sqlite3"))
    finally:
        if temporary.exists():
            temporary.unlink()
    return summary
