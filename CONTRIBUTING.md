# Contributing to Agent Project OS

[中文](CONTRIBUTING.zh-CN.md)

Agent Project OS accepts small, evidence-backed changes that preserve the runtime-neutral core.

## Before changing code

1. Read `AGENTS.md`, `docs/METHOD.md`, `docs/PROTOCOL.md`, and the relevant accepted decisions.
2. Create one task with explicit acceptance criteria.
3. Keep client behavior inside `agent_project_os.adapters`; do not add Codex, Claude, DeepSeek, model, or provider fields to a core Schema.
4. Keep private paths, business data, credentials, conversations, and unrelated command output out of fixtures and reports.

## Development

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m unittest discover -s tests -p 'test_*.py'
agent-project validate
```

Use a red-green-refactor loop for public behavior. Add positive and negative cases for Schema changes. Adapter changes require golden-file, preservation, idempotency, uninstall, and normalization coverage.

## Pull requests

Explain the outcome, protocol impact, compatibility impact, deterministic verification, and human-review needs. Do not call work complete solely because an agent produced a patch. If English or Chinese normative documentation changes, update its paired document in the same change.

By contributing, you agree that your contribution is licensed under Apache-2.0.
