#!/usr/bin/env python3
"""Fail when public source appears to contain private paths, secrets, or private topology names."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "backups",
}
TEXT_SUFFIXES = {"", ".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".in", ".js"}
ALLOWLISTED_RULE_SOURCES = {Path("scripts/check_privacy.py"), Path("tests/test_example_workspace.py")}

RULES = {
    "macOS personal absolute path": re.compile(r"/Users/[^/\s]+/"),
    "Linux personal absolute path": re.compile(r"/home/[^/\s]+/"),
    "Windows personal absolute path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "private local topology name": re.compile(r"company-os|CEO办公室", re.IGNORECASE),
}


def main() -> int:
    findings = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", "NOTICE", ".gitignore"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        if relative in ALLOWLISTED_RULE_SOURCES:
            continue
        for label, pattern in RULES.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append("{}:{}: {}".format(relative, line, label))
    if findings:
        print("\n".join(findings))
        return 1
    print("privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
