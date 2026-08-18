# Capability Packs and Governance Integrations

[中文](GOVERNANCE-PACKS.zh-CN.md)

Agent Project OS includes runtime-neutral CEO/PMO and Agent HR governance. External capability repositories may supply concrete roles, Skills, Prompts, and evaluation content without becoming a second truth source.

## AI-PMO Capability Pack

An AI-PMO-style repository owns concrete PMO/HR role definitions, Skills, Prompts, evaluation sets, and their release history. Agent Project OS owns the neutral organization, report, evaluation, promotion, and cadence contracts. Integration uses released Schema/CLI versions, paths, Git identifiers, SHA-256, validation results, and acceptance receipts.

Neither side may copy project task ledgers into a separate canonical store, silently accept project work, or convert report generation into E3/E4 evidence.

## AI-Work-Watcher Bridge

A workflow-observation bridge may observe prompt/task structure and propose improvements. It owns neither task state nor acceptance authority. It should store redacted observations separately and submit project changes through the normal inbox contract.

The bridge name and interface are generic; legacy product names and private repository internals are not part of this public project.

## Integration rule

```text
Agent Project OS Schema/CLI -> versioned governance interface -> capability pack
capability pack -> asset release / evaluation evidence -> Agent HR review path
```

No source code is copied between packages. Compatibility is declared by protocol/package versions and verified with contract tests.
