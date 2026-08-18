# Operations, Migration, and Recovery

[中文](OPERATIONS.zh-CN.md)

## Recoverable legacy migration

Initialize the organization beside an existing `portfolio.json`, then preview and run:

```sh
agent-project migrate portfolio-v1 --dry-run --json
agent-project migrate portfolio-v1 --json
```

The command requires an empty `project-registry.json`, copies legacy project relationships with a default weekly supervision policy and `P2` priority, then moves the old file to `.agent-project/migrations/portfolio-v1.archived.json`. Validation rejects a new registry and live legacy portfolio being dual-written. Restore by moving the archived file back only after removing the new registry through an explicitly approved rollback.

## Rebuildable projections

```sh
agent-project index rebuild --json
agent-project dashboard build --as-of 2026-08-18T01:00:00Z --json
```

`.agent-project/index.sqlite3`, `index/dashboard.json`, and `index/dashboard.html` are disposable. The dashboard is read-only and shows priority, owner, PM, latest report acceptance, blockers, next acceptance, due supervision, CEO exceptions, and Agent release versions.

## Private shadow comparison

`agent-project shadow compare --snapshot /path/to/local-snapshot.json --json` reads a user-owned JSON snapshot and prints differences. It does not import, rewrite, or persist the external data. Private path mappings, business names, and snapshots stay outside the public repository. A stable migration requires two complete supervision cycles with no material disagreement before any single-source cutover is proposed.

## Recovery posture

- Git records are the recovery source; SQLite and dashboard files may be deleted.
- Cadence retries are bounded and terminal runs cannot be reopened silently.
- Agent rollback requires a digest-valid prior release.
- `portfolio.json` migration is archived, not erased.
- Tags, GitHub Releases, package publication, private-project cutover, and expansion beyond a pilot each need separate human approval.
