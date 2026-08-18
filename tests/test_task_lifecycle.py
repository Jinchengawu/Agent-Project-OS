import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest

from tests.test_cli_init import run_cli


class TaskLifecycleTest(unittest.TestCase):
    def test_done_requires_accepted_deterministic_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=directory).returncode,
                0,
            )
            created = run_cli(
                "--json",
                "task",
                "create",
                "--task-id",
                "task-001",
                "--title",
                "Ship deterministic validation",
                "--acceptance",
                "Validation command exits zero",
                cwd=directory,
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            for state in ("ready", "in_progress", "waiting_review"):
                updated = run_cli(
                    "task",
                    "update",
                    "--task-id",
                    "task-001",
                    "--status",
                    state,
                    cwd=directory,
                )
                self.assertEqual(updated.returncode, 0, updated.stderr)

            denied = run_cli(
                "--json",
                "task",
                "update",
                "--task-id",
                "task-001",
                "--status",
                "done",
                cwd=directory,
            )
            self.assertEqual(denied.returncode, 2)
            self.assertIn("accepted E2", json.loads(denied.stdout)["error"])

            evidence = run_cli(
                "evidence",
                "add",
                "--evidence-id",
                "evidence-001",
                "--task-id",
                "task-001",
                "--grade",
                "E2",
                "--kind",
                "validation",
                "--summary",
                "Unit tests passed",
                "--command",
                "{} -c 'raise SystemExit(0)'".format(shlex.quote(sys.executable)),
                "--result",
                "passed",
                "--run",
                "--accepted",
                cwd=directory,
            )
            self.assertEqual(evidence.returncode, 0, evidence.stderr)

            completed = run_cli(
                "task",
                "update",
                "--task-id",
                "task-001",
                "--status",
                "done",
                cwd=directory,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            task = json.loads(
                (Path(directory) / ".agent-project" / "tasks" / "task-001.json").read_text()
            )
            self.assertEqual(task["status"], "done")
            self.assertEqual(task["evidence_refs"], ["evidence-001"])


if __name__ == "__main__":
    unittest.main()
