# Optional Governance Integrations

[中文](GOVERNANCE-PACKS.zh-CN.md)

Agent Project OS Core is intentionally sufficient for a single repository. Optional packages may consume its stable interfaces without becoming a second truth source.

## AI-PMO Governance Pack

An AI-PMO-style pack may add portfolio reporting, subordinate project reports, E0–E4 gates, blocker reconciliation, and portfolio acceptance. It integrates through released Schema versions, `agent-project --json`, Git identifiers, validation results, and acceptance receipts.

It must not copy project task ledgers into a separate canonical store, silently accept project work, or convert a report-generation event into E3/E4 evidence.

## AI-Work-Watcher Bridge

A workflow-observation bridge may observe prompt/task structure and propose improvements. It owns neither task state nor acceptance authority. It should store redacted observations separately and submit project changes through the normal inbox contract.

The bridge name and interface are generic; legacy product names and private repository internals are not part of this public project.

## Integration rule

```text
Core Schema/CLI -> versioned evidence interface -> optional pack
optional pack -> change request / receipt -> Core review path
```

No source code is copied between packages. Compatibility is declared by protocol/package versions and verified with contract tests.
