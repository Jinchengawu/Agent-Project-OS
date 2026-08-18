# Release-candidate Evidence

[中文](RELEASE-EVIDENCE.zh-CN.md)

## v0.4.0a1 local candidate — 2026-08-18

Observed local checks:

- 33 integration and contract tests pass, including CEO/PMO supervision, Agent HR promotion/rollback, cadence idempotency, migration, projections, and three-client dispatch rendering.
- All 28 Draft 2020-12 Schema documents load; every new Governance/Workforce/Cadence contract has valid, missing-field, and incompatible-version samples.
- The synthetic organization validates with three projects, five Agents, one reviewed talent upgrade, two accepted PM reports, and one CEO blocker exception.
- The scale gate rebuilds 30 projects, 50 Agents, 29 transitive downstream projects, 30 due items, and the read-only dashboard.
- `scripts/release_gate.py`, privacy, bilingual pairs, Python compile, DeepSeek Harness JavaScript syntax, source distribution, wheel build, and isolated wheel CLI smoke pass on local Python 3.11/macOS.

This is not `0.5.0b1` evidence: two complete private read-only shadow cycles have not been run. It is not `1.0.0` evidence: no private project has switched to a single source of truth. README correction is also waiting for the current Showcase Proposal approval.

## Historical v0.1 candidate — 2026-08-14

The machine-readable client smoke summary is `release/smoke-results-v0.1.json`.

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

The repository already exists from a prior explicitly approved push. This evidence does not authorize another push, tag, GitHub Release, package publication, or private migration. Those remain separate human-approved actions after the README/display review.
