"""Recoverable migrations from legacy portfolio manifests."""

import os
from pathlib import Path
from typing import Any, Dict

from .federation import load_portfolio, portfolio_path
from .organization import load_organization, load_registry, registry_path
from .records import utc_now, write_json


def migrate_portfolio_v1(root: Path, dry_run: bool = False) -> Dict[str, Any]:
    legacy_path = portfolio_path(root)
    if not legacy_path.exists():
        raise ValueError("legacy portfolio.json not found")
    organization = load_organization(root)
    registry = load_registry(root)
    if registry.get("projects"):
        raise ValueError("project registry must be empty before portfolio-v1 migration")
    portfolio = load_portfolio(root)
    projects = []
    for item in portfolio.get("projects", []):
        migrated = dict(item)
        migrated["priority"] = "P2"
        migrated["supervision"] = {
            "cadence": "weekly",
            "timezone": "UTC",
            "next_due_at": None,
        }
        projects.append(migrated)
    registry["organization_id"] = organization["organization_id"]
    registry["projects"] = sorted(projects, key=lambda item: item["project_id"])
    registry["updated_at"] = utc_now()
    archive = root / ".agent-project" / "migrations" / "portfolio-v1.archived.json"
    if archive.exists():
        raise ValueError("portfolio-v1 migration archive already exists")
    if not dry_run:
        archive.parent.mkdir(parents=True, exist_ok=True)
    write_json(registry_path(root), registry, dry_run)
    if not dry_run:
        os.replace(str(legacy_path), str(archive))
    return {
        "migration": "portfolio-v1",
        "project_count": len(projects),
        "archive": archive.relative_to(root).as_posix(),
        "legacy_removed": not dry_run,
    }
