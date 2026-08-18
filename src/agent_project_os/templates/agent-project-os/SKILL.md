---
name: agent-project-os
description: Manage long-running or cross-project AI engineering work with Agent Project OS. Use when a repository contains .agent-project, when creating or changing tasks, evidence, decisions, handoffs, acceptance receipts, or portfolio dependencies, and when work must remain portable across Codex, Claude Code, and DeepSeek Harness.
---

# Agent Project OS

Use the repository as the portable source of truth. Treat runtime chats, client task lists, and model memory as execution context, never as accepted project state.

## Start

1. Find the nearest `.agent-project/manifest.json` or portfolio `portfolio.json`.
2. Run `agent-project status --json`, then `agent-project validate --json`.
3. Read `AGENTS.md`, the project manifest, policy, relevant task, accepted decisions, and latest handoff.
4. State the task outcome, acceptance criteria, affected projects, and human approval gates before changing files.

Do not silently repair invalid records. Report the validation error and propose the smallest correction.

## Choose The Write Path

Use accepted-state commands only when the human has directly authorized that exact write:

```sh
agent-project task create --task-id task-123 --title "..." --acceptance "..."
agent-project task update --task-id task-123 --status ready
agent-project evidence add --evidence-id evidence-123 --task-id task-123 --grade E2 --kind validation --summary "..." --command "..." --run --accepted
```

For an agent-originated change that still needs review, submit to the inbox:

```sh
agent-project task submit --request-id request-123 --task-id task-123 --status waiting_review --actor agent:runtime --runtime runtime-name --client-version version
```

Never accept or reject your own proposal unless project policy explicitly grants that authority.

## Execute And Prove

- Keep task status transitions valid.
- Record blockers as `dependency`, `needs_input`, `capability`, `transient`, or `risk_gate`.
- E0 is a claim; E1 is an artifact; E2 is a deterministic verification result; E3 is consumer acceptance; E4 is an external outcome.
- Do not move a task to `done` without accepted E2-or-stronger evidence.
- Do not describe E2 as consumer acceptance or E4 as business impact.
- Keep `runtime`, `client_version`, `model_id`, and `provider_hint` separate. A client is not a model.
- Use one isolated branch/worktree per overlapping code change when the client supports it. This is an execution enhancement, not core state.

## Cross-Project Work

1. Run `agent-project affected --project-id <producer>` from the portfolio root.
2. Freeze the versioned interface before editing consumers.
3. Give each repository its own task and evidence.
4. Include producer, consumer, commit, protocol or artifact version, SHA-256, evidence references, and acceptance status in cross-project artifacts.
5. Do not wake unrelated projects and do not treat the portfolio projection as domain truth.

## Human Authority

Stop for explicit approval before irreversible actions, production changes, permission changes, spending or fund movement, and public releases. Never weaken these gates because a client offers unattended execution.

## Finish

1. Run the project's deterministic verification commands.
2. Add evidence at the grade actually achieved.
3. Update or submit the task state.
4. Create a handoff when another agent, model, client, session, or project will continue the work.
5. Run `agent-project validate --json` and `agent-project status --json`.
6. Report accepted state separately from proposals and external outcomes.
