"""Federated portfolio graph and disposable SQLite projection."""

import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Dict, Iterable, List, Set, Tuple

from .records import read_json, write_json
from .validation import validate_project


PORTFOLIO_SCHEMA = "https://agent-project-os.org/schemas/portfolio-manifest-v1.schema.json"


def portfolio_path(root: Path) -> Path:
    return root / "portfolio.json"


def new_portfolio(portfolio_id: str, name: str) -> Dict[str, Any]:
    return {
        "$schema": PORTFOLIO_SCHEMA,
        "protocol_version": "1.0",
        "portfolio_id": portfolio_id,
        "name": name,
        "projects": [],
    }


def load_portfolio(root: Path) -> Dict[str, Any]:
    return read_json(portfolio_path(root))


def projects_by_id(portfolio: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    projects = portfolio.get("projects")
    if not isinstance(projects, list):
        raise ValueError("portfolio projects must be an array")
    result: Dict[str, Dict[str, Any]] = {}
    for item in projects:
        if not isinstance(item, dict) or not item.get("project_id"):
            raise ValueError("portfolio project entries require project_id")
        project_id = str(item["project_id"])
        if project_id in result:
            raise ValueError("duplicate portfolio project: {}".format(project_id))
        result[project_id] = item
    return result


def detect_cycle(projects: Dict[str, Dict[str, Any]]) -> List[str]:
    visiting: Set[str] = set()
    visited: Set[str] = set()
    stack: List[str] = []

    def visit(project_id: str) -> List[str]:
        if project_id in visiting:
            start = stack.index(project_id)
            return stack[start:] + [project_id]
        if project_id in visited:
            return []
        visiting.add(project_id)
        stack.append(project_id)
        for dependency in projects[project_id].get("depends_on", []):
            if dependency in projects:
                cycle = visit(str(dependency))
                if cycle:
                    return cycle
        stack.pop()
        visiting.remove(project_id)
        visited.add(project_id)
        return []

    for project_id in sorted(projects):
        cycle = visit(project_id)
        if cycle:
            return cycle
    return []


def interface_name(value: str) -> str:
    return value.rsplit("@", 1)[0]


def validate_portfolio(root: Path) -> List[str]:
    errors: List[str] = []
    try:
        portfolio = load_portfolio(root)
        projects = projects_by_id(portfolio)
    except ValueError as error:
        return [str(error)]
    for name in ("protocol_version", "portfolio_id", "name", "projects"):
        if portfolio.get(name) in (None, ""):
            errors.append("portfolio: missing required field '{}'".format(name))
    if portfolio.get("protocol_version") != "1.0":
        errors.append("portfolio: incompatible protocol_version {!r}".format(portfolio.get("protocol_version")))

    provider_by_contract: Dict[str, List[Tuple[str, str]]] = {}
    for project_id, item in sorted(projects.items()):
        for field in ("owner", "lifecycle", "path", "depends_on", "provides", "consumes", "verification"):
            if field not in item:
                errors.append("project {}: missing required field '{}'".format(project_id, field))
        for dependency in item.get("depends_on", []):
            if dependency not in projects:
                errors.append("project {}: unknown dependency {}".format(project_id, dependency))
        project_root = (root / str(item.get("path", ""))).resolve()
        try:
            manifest = read_json(project_root / ".agent-project" / "manifest.json")
            if manifest.get("project_id") != project_id:
                errors.append("project {}: path resolves to manifest {}".format(project_id, manifest.get("project_id")))
        except ValueError as error:
            errors.append("project {}: {}".format(project_id, error))
        else:
            for project_error in validate_project(project_root):
                errors.append("project {}: {}".format(project_id, project_error))
            for receipt_path in sorted((project_root / ".agent-project" / "receipts").glob("*.json")):
                try:
                    receipt = read_json(receipt_path)
                except ValueError as error:
                    errors.append("project {}: {}".format(project_id, error))
                    continue
                producer = receipt.get("producer")
                consumer = receipt.get("consumer")
                if producer not in projects or consumer not in projects:
                    errors.append(
                        "project {}: receipt {} references unknown producer or consumer".format(
                            project_id, receipt.get("receipt_id")
                        )
                    )
                if producer != consumer and receipt.get("acceptance_status") != "accepted":
                    errors.append(
                        "project {}: unaccepted cross-project receipt {}".format(
                            project_id, receipt.get("receipt_id")
                        )
                    )
        for contract in item.get("provides", []):
            provider_by_contract.setdefault(interface_name(str(contract)), []).append((project_id, str(contract)))

    cycle = detect_cycle(projects)
    if cycle:
        errors.append("portfolio dependency cycle: {}".format(" -> ".join(cycle)))

    for project_id, item in sorted(projects.items()):
        for contract in item.get("consumes", []):
            contract = str(contract)
            if contract.startswith("external:"):
                continue
            providers = provider_by_contract.get(interface_name(contract), [])
            if not providers:
                errors.append("project {}: consumed interface has no provider: {}".format(project_id, contract))
            elif contract not in {provided for _, provided in providers}:
                errors.append(
                    "project {}: incompatible interface {}; available {}".format(
                        project_id, contract, sorted(provided for _, provided in providers)
                    )
                )
    return errors


def affected_projects(portfolio: Dict[str, Any], project_id: str) -> List[str]:
    projects = projects_by_id(portfolio)
    if project_id not in projects:
        raise ValueError("unknown project: {}".format(project_id))
    reverse: Dict[str, Set[str]] = {key: set() for key in projects}
    providers: Dict[str, Set[str]] = {}
    for source, item in projects.items():
        for dependency in item.get("depends_on", []):
            if dependency in reverse:
                reverse[str(dependency)].add(source)
        for contract in item.get("provides", []):
            providers.setdefault(str(contract), set()).add(source)
    for consumer, item in projects.items():
        for contract in item.get("consumes", []):
            for producer in providers.get(str(contract), set()):
                reverse[producer].add(consumer)
    seen: Set[str] = set()
    queue = list(sorted(reverse[project_id]))
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        queue.extend(sorted(reverse[current] - seen))
    return sorted(seen)


def rebuild_index(root: Path, dry_run: bool = False) -> Dict[str, int]:
    portfolio = load_portfolio(root)
    projects = projects_by_id(portfolio)
    rows: Dict[str, List[Tuple[Any, ...]]] = {"projects": [], "tasks": [], "evidence": [], "receipts": []}
    for project_id, item in sorted(projects.items()):
        project_root = (root / str(item["path"])).resolve()
        rows["projects"].append((project_id, str(item["path"]), str(item["lifecycle"]), str(item["owner"])))
        for path in sorted((project_root / ".agent-project" / "tasks").glob("*.json")):
            record = read_json(path)
            rows["tasks"].append((project_id, str(record.get("task_id")), str(record.get("status")), str(record.get("title"))))
        for path in sorted((project_root / ".agent-project" / "evidence").glob("*.json")):
            record = read_json(path)
            rows["evidence"].append((project_id, str(record.get("evidence_id")), str(record.get("task_id")), str(record.get("grade")), str(record.get("acceptance_status"))))
        for path in sorted((project_root / ".agent-project" / "receipts").glob("*.json")):
            record = read_json(path)
            rows["receipts"].append((project_id, str(record.get("receipt_id")), str(record.get("producer")), str(record.get("consumer")), str(record.get("acceptance_status"))))
    summary = {name: len(values) for name, values in rows.items()}
    if dry_run:
        return summary
    control = root / ".agent-project"
    control.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="index-", suffix=".sqlite3", dir=str(control), delete=False) as handle:
        temporary = Path(handle.name)
    try:
        connection = sqlite3.connect(str(temporary))
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            CREATE TABLE projects (project_id TEXT PRIMARY KEY, path TEXT, lifecycle TEXT, owner TEXT);
            CREATE TABLE tasks (project_id TEXT, task_id TEXT, status TEXT, title TEXT, PRIMARY KEY(project_id, task_id));
            CREATE TABLE evidence (project_id TEXT, evidence_id TEXT, task_id TEXT, grade TEXT, acceptance_status TEXT, PRIMARY KEY(project_id, evidence_id));
            CREATE TABLE receipts (project_id TEXT, receipt_id TEXT, producer TEXT, consumer TEXT, acceptance_status TEXT, PRIMARY KEY(project_id, receipt_id));
            """
        )
        connection.executemany("INSERT INTO projects VALUES (?, ?, ?, ?)", rows["projects"])
        connection.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?)", rows["tasks"])
        connection.executemany("INSERT INTO evidence VALUES (?, ?, ?, ?, ?)", rows["evidence"])
        connection.executemany("INSERT INTO receipts VALUES (?, ?, ?, ?, ?)", rows["receipts"])
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        os.replace(str(temporary), str(control / "index.sqlite3"))
    finally:
        if temporary.exists():
            temporary.unlink()
    return summary
