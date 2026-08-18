# Agent Project OS protocol reference

The normative interchange contracts live in the repository-level `schemas/` directory. The CLI implements an offline, standard-library validator for the same cross-record invariants.

Accepted entity state is stored one JSON object per file in `tasks/`, `evidence/`, `decisions/`, and `handoffs/`. Agent proposals live in `inbox/`. Immutable audit events and acceptance receipts use one record per file to reduce merge conflicts.

Portfolio state records only project identity, ownership, lifecycle, repository location, verification commands, dependency edges, and provided or consumed interfaces. It must not copy a project's domain state.
