# Versioning Policy

[中文](VERSIONING.zh-CN.md)

Agent Project OS uses Semantic Versioning for the Python package and explicit protocol versions for persisted records.

- Package `0.x`: public CLI and adapter details may change, with migration notes.
- Package `1.x`: incompatible public CLI changes require a major release.
- Core record `protocol_version`: changes only when persisted semantics or required fields become incompatible.
- Schema filenames are immutable contracts such as `task-v1.schema.json`. A breaking record change creates `task-v2`, never silently rewrites v1 meaning.
- Adapter compatibility pins can change in a patch or minor package release without changing core protocol versions.

Readers must reject unsupported major protocol versions. Writers must emit one declared version and must not guess a downgrade. Derived indexes carry no compatibility promise because they are disposable and rebuildable.

Prerelease format uses PEP 440 in Python metadata (`0.4.0a1`) and SemVer spelling for a possible Git tag (`v0.4.0-alpha.1`). The current working candidate has no tag. Creating a tag, GitHub Release, or published package is a separate human-approved release action.
