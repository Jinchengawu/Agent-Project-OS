import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class ChangeRequestTest(unittest.TestCase):
    def test_submitted_task_change_requires_explicit_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=directory).returncode, 0)
            self.assertEqual(
                run_cli(
                    "task",
                    "create",
                    "--task-id",
                    "task-001",
                    "--title",
                    "Review me",
                    "--acceptance",
                    "Human accepts the proposal",
                    cwd=directory,
                ).returncode,
                0,
            )
            submitted = run_cli(
                "--json",
                "task",
                "submit",
                "--request-id",
                "request-001",
                "--task-id",
                "task-001",
                "--status",
                "ready",
                "--actor",
                "agent:codex",
                "--runtime",
                "codex",
                "--client-version",
                "1.2.3",
                "--model-id",
                "gpt-5",
                cwd=directory,
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)
            root = Path(directory)
            task_path = root / ".agent-project" / "tasks" / "task-001.json"
            request_path = root / ".agent-project" / "inbox" / "request-001.json"
            self.assertEqual(json.loads(task_path.read_text())["status"], "planned")
            request = json.loads(request_path.read_text())
            self.assertEqual(request["status"], "pending_review")
            self.assertEqual(request["runtime_identity"]["runtime"], "codex")
            self.assertEqual(request["runtime_identity"]["model_id"], "gpt-5")

            accepted = run_cli("task", "accept", "--request-id", "request-001", cwd=directory)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(json.loads(task_path.read_text())["status"], "ready")
            self.assertEqual(json.loads(request_path.read_text())["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
