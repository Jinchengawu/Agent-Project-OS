# v0.1 Release-candidate Evidence

[中文](RELEASE-EVIDENCE.zh-CN.md)

Evidence date: 2026-08-14. The machine-readable summary is `release/smoke-results-v0.1.json`.

## Deterministic suite

- Core lifecycle, stale proposal, evidence gate, decision, handoff, federation, cycle/interface/receipt rejection, index rebuild, Adapter, privacy, and synthetic-workspace tests pass.
- Draft 2020-12 positive, missing-field, illegal-state, forged E2/E3, and incompatible-version cases run with the `test` extra.
- Adapter golden, preservation, idempotency, uninstall restoration, and normalized event validation pass.
- DeepSeek Harness bundle JavaScript passes syntax checking at the pinned preview compatibility point.

## Real client smoke

Two isolated synthetic projects completed a create → verify → E2 → done lifecycle:

| Client runtime | Client version | Actual model ID | Result |
|---|---|---|---|
| Codex | `0.147.0-alpha.6.5` | `gpt-5.6-sol` | Passed |
| Claude Code | `2.1.181` | `deepseek-v4-pro` | Passed |

The Claude Code run demonstrates the identity rule directly: the client runtime and model are separate fields.

DeepSeek Harness was not installed and no credential was available. Its keyless bundle/config/Schema/syntax path passed and the Adapter remains `preview`; no real DSH loop is claimed.

No session IDs, transcripts, prompts with private context, absolute project paths, credentials, or cost data are retained.

## Remaining human gate

This evidence does not authorize creating a public repository, pushing, tagging, or publishing a package. Those remain separate release actions after the README/display review and final human approval.
