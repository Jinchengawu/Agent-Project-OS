# Agent Project OS contributor instructions

This repository self-hosts Agent Project OS.

- Read `docs/METHOD.md`, `docs/PROTOCOL.md`, and the relevant organization, workforce, or cadence contract before changing public behavior. For project work, also read the task, accepted decisions, and latest handoff.
- Keep the core runtime-, client-, model-, and provider-neutral. Client-specific behavior belongs in `src/agent_project_os/adapters.py` and Adapter documentation.
- Use red-green-refactor for public behavior. Run `python -m unittest discover -s tests -p 'test_*.py'` after relevant changes.
- Run `agent-project validate`, `python scripts/check_privacy.py`, and `python scripts/check_bilingual.py` before claiming release readiness.
- Submit Agent-originated state changes to `.agent-project/inbox/` unless the human-approved task explicitly authorizes direct work.
- Do not mark a task done without accepted E2-or-stronger evidence. Do not call E2 consumer acceptance or business impact.
- Never add real personal paths, private business names, credentials, conversations, full terminal transcripts, or private project data to public source or fixtures.
- Preserve explicit human approval for irreversible actions, production, permissions, funds, remote publication, tags, and public releases.
- Preserve exactly one accountable PM per active project. Never let a project PM review its own report or let an Agent candidate, reviewer, and promotion approver collapse into the same identity.
- Do not create a GitHub repository, push, tag, or publish a package without separate human approval.
