---
name: agent-project-os
description: Operate a local AI engineering organization with Agent Project OS. Use for project facts, CEO/PMO supervision, Agent HR releases, cadence plans, cross-project impact, or portable dispatch across Codex, Claude Code, and DeepSeek Harness.
---

# Agent Project OS

Use the repository as the portable source of truth. Treat runtime chats, client task lists, and model memory as execution context, never as accepted project state.

## Start

1. Find the nearest project `.agent-project/manifest.json` or organization `.agent-project/organization.json`.
2. Run `agent-project status --json`, then `agent-project validate --json`.
3. Read `AGENTS.md`, the project manifest, policy, relevant task, accepted decisions, and latest handoff.
4. State the task outcome, acceptance criteria, affected projects, and human approval gates before changing files.

Do not silently repair invalid records. Report the validation error and propose the smallest correction.

## Respect The Pyramid

- The Founder retains human authority. The Agent CEO owns portfolio priorities and exception decisions.
- The PMO issues bounded supervision dispatches and accepts or rejects child-PM reports.
- Each active project has exactly one accountable PM. Project tasks remain in the project repository.
- Agent HR owns runtime-neutral role, evaluation, release, promotion, rollback, pause, and retirement records. Concrete Prompt, Skill, and evaluation content remains in its owning capability repository.
- Do not let an organization report become a copied task ledger or let a dashboard become a second source of truth.

Use `agent-project supervision due`, `agent-project cadence plan`, and `agent-project portfolio review` from the organization root. External schedulers may wake a plan, but cannot bypass its approval gates.

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

Stop for explicit approval before irreversible actions, production changes, credential or permission changes, spending or fund movement, Agent promotion, destructive migration, and public releases. A candidate Agent, its independent reviewer, and the promotion approver must remain separate. Never weaken these gates because a client offers unattended execution.

## Finish

1. Run the project's deterministic verification commands.
2. Add evidence at the grade actually achieved.
3. Update or submit the task state.
4. Create a handoff when another agent, model, client, session, or project will continue the work.
5. Run `agent-project validate --json` and `agent-project status --json`.
6. Report accepted state separately from proposals and external outcomes.
