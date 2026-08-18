# Security Policy

[中文](SECURITY.zh-CN.md)

## Supported versions

Security fixes are provided for the latest released minor version. Before the first stable release, only the latest prerelease is supported.

## Reporting

Do not open a public issue for a suspected vulnerability, credential leak, path traversal, unsafe adapter install/uninstall behavior, or approval-gate bypass. Use the private security-reporting channel configured on the eventual public repository. Until that channel exists, do not transmit sensitive details; contact a maintainer first and request a private route.

Include the affected version, platform, minimal reproduction, impact, and whether real credentials or private project data were exposed. Remove secrets, absolute personal paths, chat transcripts, and unrelated terminal output.

## Security boundary

Agent Project OS does not sandbox models or tools. It records policy and evidence but cannot replace operating-system permissions, client sandboxes, credential isolation, code review, or human approval. User-level adapter installation is opt-in and must never be enabled implicitly.
