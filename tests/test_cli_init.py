import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, cwd, env_overrides=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "agent_project_os", *args],
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


class InitCommandTest(unittest.TestCase):
    def test_init_creates_repo_native_project_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(
                "--json",
                "init",
                "--project-id",
                "demo-app",
                "--name",
                "Demo App",
                cwd=directory,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "created")
            root = Path(directory)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / ".agent-project" / "manifest.json").is_file())
            for name in (
                "tasks",
                "evidence",
                "decisions",
                "handoffs",
                "inbox",
                "receipts",
                "events",
            ):
                self.assertTrue((root / ".agent-project" / name).is_dir())


if __name__ == "__main__":
    unittest.main()
