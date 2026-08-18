# Protocol and CLI

[中文](PROTOCOL.zh-CN.md)

## Repository contract

```text
AGENTS.md
.agent-project/
├── manifest.json
├── policy.json
├── tasks/
├── evidence/
├── decisions/
├── handoffs/
├── inbox/
├── receipts/
└── events/
```

Every JSON record declares `protocol_version`. Core Schema identifiers are stable URLs, while shipped Schema files work offline. A portfolio root adds `portfolio.json`; its project paths should be relative for portability.

## Command surface

```text
agent-project init
agent-project validate
agent-project project add|list|show
agent-project task create|update|submit|accept|reject
agent-project evidence add
agent-project decision propose|accept|reject|supersede
agent-project handoff create|validate
agent-project affected
agent-project adapter render|install|uninstall|doctor
agent-project index rebuild
agent-project status
```

Global `--root` selects the project/portfolio and `--json` emits machine-readable output. Every write command supports `--dry-run`. The CLI returns `0` on success, `1` for completed validation with invalid records, and `2` for command/precondition errors.

## Runtime identity

Writes may include:

```json
{
  "runtime": "codex",
  "client_version": "1.2.3",
  "model_id": "example-model",
  "provider_hint": "example-provider"
}
```

Only `runtime` and `client_version` are required. `model_id` and `provider_hint` are metadata, not authorization.

## Proposal and acceptance

`task submit` creates a change request without changing accepted task state. `task accept` verifies the request is still based on the current `updated_at`; stale proposals fail and must be resubmitted. `task reject` records a review outcome without applying the patch.

Direct `task update`, `decision accept`, and evidence `--accepted` represent a human or policy-authorized action. Client adapters should prefer inbox submission unless policy says otherwise.

## Cross-project artifact contract

A cross-project receipt identifies:

- `producer` and `consumer` project IDs;
- artifact protocol/version;
- producer Git commit;
- artifact SHA-256;
- evidence references;
- `pending`, `accepted`, or `rejected` status.

E3 evidence must cite an accepted receipt whose consumer is the current project. Portfolio validation rejects unaccepted cross-project receipts as delivery evidence.

## Privacy and merge behavior

Do not store credentials, full conversations, full terminal transcripts, or unrelated diffs. Prefer summaries plus precise file/commit/digest references. Event and receipt filenames must be unique; independent writers never append to one shared JSONL file.
