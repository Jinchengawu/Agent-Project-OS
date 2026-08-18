#!/usr/bin/env python3
"""Check that normative English and Chinese documents stay paired."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAIRS = (
    ("CONTRIBUTING.md", "CONTRIBUTING.zh-CN.md"),
    ("CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.zh-CN.md"),
    ("SECURITY.md", "SECURITY.zh-CN.md"),
    ("docs/METHOD.md", "docs/METHOD.zh-CN.md"),
    ("docs/ARCHITECTURE.md", "docs/ARCHITECTURE.zh-CN.md"),
    ("docs/DATA-MODEL.md", "docs/DATA-MODEL.zh-CN.md"),
    ("docs/PROTOCOL.md", "docs/PROTOCOL.zh-CN.md"),
    ("docs/ADAPTERS.md", "docs/ADAPTERS.zh-CN.md"),
    ("docs/COMPATIBILITY.md", "docs/COMPATIBILITY.zh-CN.md"),
    ("docs/GOVERNANCE-PACKS.md", "docs/GOVERNANCE-PACKS.zh-CN.md"),
    ("docs/PRIVACY.md", "docs/PRIVACY.zh-CN.md"),
    ("docs/ROADMAP.md", "docs/ROADMAP.zh-CN.md"),
    ("docs/VERSIONING.md", "docs/VERSIONING.zh-CN.md"),
    ("docs/RELEASE-EVIDENCE.md", "docs/RELEASE-EVIDENCE.zh-CN.md"),
    ("docs/ORGANIZATION.md", "docs/ORGANIZATION.zh-CN.md"),
    ("docs/WORKFORCE.md", "docs/WORKFORCE.zh-CN.md"),
    ("docs/CADENCE.md", "docs/CADENCE.zh-CN.md"),
    ("docs/OPERATIONS.md", "docs/OPERATIONS.zh-CN.md"),
    ("prompts/agent-writing-protocol.md", "prompts/agent-writing-protocol.zh-CN.md"),
)


def main() -> int:
    errors = []
    for english, chinese in PAIRS:
        english_path = ROOT / english
        chinese_path = ROOT / chinese
        if not english_path.is_file():
            errors.append("missing {}".format(english))
        if not chinese_path.is_file():
            errors.append("missing {}".format(chinese))
        if english_path.is_file() and len(english_path.read_text(encoding="utf-8").strip()) < 80:
            errors.append("English document is unexpectedly short: {}".format(english))
        if chinese_path.is_file() and len(chinese_path.read_text(encoding="utf-8").strip()) < 80:
            errors.append("Chinese document is unexpectedly short: {}".format(chinese))
    if errors:
        print("\n".join(errors))
        return 1
    print("bilingual document pairs passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
