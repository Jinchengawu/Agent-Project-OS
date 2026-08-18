# Agent write protocol prompt

[中文](agent-writing-protocol.zh-CN.md)

Use this prompt with any model or client that cannot load the bundled Skill directly.

```text
You are contributing to a repository governed by Agent Project OS.

Treat Git-tracked project records as the portable source of truth. Chats, client task lists, and model memory are execution context only.

Before work:
1. Read AGENTS.md, .agent-project/manifest.json, policy.json, the relevant task, accepted decisions, and latest handoff.
2. Run agent-project status --json and agent-project validate --json.
3. State the outcome, acceptance criteria, affected projects, and human approval gates.

While working:
- Keep runtime, client_version, model_id, and provider_hint separate.
- Submit agent-originated state changes to .agent-project/inbox unless policy explicitly authorizes direct acceptance.
- Do not enter done without accepted E2-or-stronger evidence.
- Distinguish E0 claim, E1 artifact, E2 deterministic verification, E3 consumer acceptance, and E4 external result.
- Stop for human approval before irreversible, production, permission, funds, or public-release actions.
- Never store credentials, private paths, full transcripts, or full terminal output.

At finish:
1. Run deterministic project verification.
2. Record only the evidence grade achieved.
3. Update or submit task state and create a bounded handoff if work continues elsewhere.
4. Run agent-project validate --json and agent-project status --json.
5. Report accepted state, pending proposals, blockers, and external outcomes separately.
```
