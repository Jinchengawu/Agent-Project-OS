# Agent Project OS Method

[中文](METHOD.zh-CN.md)

Agent Project OS is a local-first operating method for long-lived, AI-assisted engineering. It is designed for individual developers and one-person teams using multiple models and clients.

## The operating rule

> Repositories preserve facts and policy. Agents propose structured changes. A deterministic CLI validates them. The control plane is rebuilt from engineering evidence. Humans retain final authority.

The organization shape is `Founder → Agent CEO → PMO → accountable project PM → engineering Agents`, with Agent HR operating beside PMO to review roles, capabilities, Prompt/Skill releases, evaluations, promotion, rollback, and retirement. This pyramid is the product's organization layer; the existing Task/Evidence/Decision/Handoff protocol is its Project Kernel.

## Principles

1. **Local-first.** Core operation requires no cloud service or database.
2. **Repo-native.** Git-tracked files are the portable source of truth. Chat, client task state, and model memory are context, not accepted state.
3. **Federated.** Each project owns its domain state. The organization registry records identity, priority, ownership, lifecycle, PM assignment, relationships, interfaces, supervision, and verification commands—never a copied task ledger.
4. **Evidence-gated.** A claim, artifact, deterministic verification, consumer acceptance, and external outcome are different facts (E0–E4).
5. **Human authority.** Irreversible actions, production, permissions, funds, and public release require explicit human approval.
6. **Runtime-neutral.** Runtime, client version, model ID, and provider hint are separate identities.
7. **Adapter-based.** Client-specific instructions, hooks, plugins, worktrees, and agent teams remain outside the core protocol.
8. **Rebuildable control plane.** CEO/PMO/HR views and indexes are projections. Delete them and rebuild them from project files, organization records, Git, verification evidence, and acceptance receipts.

## Three state boundaries

- **Proposed:** an Agent change request in `inbox/` awaiting policy or human review.
- **Accepted:** current entity files under `tasks/`, `evidence/`, `decisions/`, `handoffs/`, and `receipts/`.
- **Observed outcome:** E4 evidence from the external world. It must not be inferred from code completion or deployment alone.

This separation prevents a generated claim from becoming organizational truth simply because a client displayed “completed.”

## Operating loop

1. CEO and PMO orient from the organization registry, priorities, due supervision, accepted child-PM reports, and the exception queue.
2. Each accountable PM orients from its project's `AGENTS.md`, manifest, task, evidence, accepted decisions, and latest handoff.
3. Define one outcome and acceptance criteria; calculate affected projects before an interface change.
4. Isolate overlapping code work by branch/worktree when supported.
5. Submit or apply the smallest structured state change allowed by policy.
6. Run deterministic verification, record the actual evidence grade, and obtain consumer acceptance when required.
7. Submit a bounded project report; PMO accepts or rejects it without copying project state.
8. Agent HR evaluates capability assets and proposes versioned upgrades through independent review.
9. Rebuild the CEO/PMO/HR projection and hand off remaining work.

## What this method does not do

It does not run models, replace Git hosting or issue trackers, provide a sandbox, grant unattended production or promotion authority, implement RBAC/cloud sync, or require feature parity across clients. The local dashboard consumes the protocol but cannot become a second source of truth.
