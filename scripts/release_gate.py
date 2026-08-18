#!/usr/bin/env python3
"""Run the deterministic v0.1 release-candidate gate."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    print("+ {}".format(" ".join(args)))
    subprocess.run(args, cwd=str(ROOT), check=True)


def main() -> int:
    if importlib.util.find_spec("jsonschema") is None:
        print("release gate requires the test extra: python -m pip install -e '.[test]'", file=sys.stderr)
        return 2
    environment_path = str(ROOT / "src")
    os.environ["PYTHONPATH"] = environment_path + os.pathsep + os.environ.get("PYTHONPATH", "")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
    run(sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts")
    run(sys.executable, "-m", "agent_project_os", "--root", str(ROOT), "validate")
    run(sys.executable, "-m", "agent_project_os", "--root", str(ROOT / "examples" / "federated-workspace"), "validate")
    run(sys.executable, "scripts/check_privacy.py")
    run(sys.executable, "scripts/check_bilingual.py")
    node = shutil.which("node")
    if not node:
        print("node is required for the DeepSeek Harness keyless syntax gate", file=sys.stderr)
        return 2
    run(node, "--check", ".dsh/agent-project-os-bundle/index.js")
    print("release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
