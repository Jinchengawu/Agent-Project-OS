# Privacy and Public-Repository Hygiene

[中文](PRIVACY.zh-CN.md)

Public records must use synthetic identities and relative paths. Never commit:

- credentials, tokens, cookies, private endpoints, or environment dumps;
- absolute personal paths or user names;
- private company/project names, tasks, financial data, or customer data;
- complete chats, prompts containing private context, terminal transcripts, or unrelated diffs;
- generated caches, local adapter backups, SQLite indexes, or client session stores.

Store the minimum evidence needed to reproduce a claim: command, result, commit, file reference, digest, and a bounded summary. A local private audit may contain real topology, but it must live outside the public repository and must never be used as a test fixture.

CI runs a conservative path/secret/name scan. A clean scan is not proof that publication is safe; a human must review the release candidate before any push, tag, or package publication.
