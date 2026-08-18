import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest

from tests.test_cli_init import run_cli


class ValidationTest(unittest.TestCase):
    def test_validate_rejects_forged_e2_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=directory).returncode,
                0,
            )
            root = Path(directory)
            forged = {
                "$schema": "https://agent-project-os.org/schemas/evidence-v1.schema.json",
                "protocol_version": "1.0",
                "evidence_id": "forged-e2",
                "task_id": "missing-task",
                "grade": "E2",
                "kind": "validation",
                "summary": "Claimed without a deterministic result",
                "acceptance_status": "accepted",
                "created_by": "agent",
                "runtime_identity": {"runtime": "codex", "client_version": "1.0"},
                "created_at": "2026-08-14T00:00:00Z",
            }
            evidence_path = root / ".agent-project" / "evidence" / "forged-e2.json"
            evidence_path.write_text(json.dumps(forged), encoding="utf-8")

            result = run_cli("--json", "validate", cwd=directory)

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "invalid")
            self.assertTrue(any("requires verification" in item for item in payload["errors"]))
            self.assertTrue(any("unknown task" in item for item in payload["errors"]))

    def test_accepted_e2_cannot_be_created_from_an_unexecuted_pass_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=directory).returncode, 0)
            self.assertEqual(
                run_cli("task", "create", "--task-id", "task-001", "--title", "Verify", "--acceptance", "Pass", cwd=directory).returncode,
                0,
            )
            command = "{} -c 'raise SystemExit(0)'".format(shlex.quote(sys.executable))
            forged = run_cli(
                "--json", "evidence", "add", "--evidence-id", "evidence-001", "--task-id", "task-001",
                "--grade", "E2", "--kind", "validation", "--summary", "Claimed pass", "--command", command,
                "--result", "passed", "--accepted", cwd=directory,
            )
            self.assertEqual(forged.returncode, 2)
            self.assertIn("--run", json.loads(forged.stdout)["error"])
            self.assertFalse((Path(directory) / ".agent-project" / "evidence" / "evidence-001.json").exists())

            verified = run_cli(
                "evidence", "add", "--evidence-id", "evidence-001", "--task-id", "task-001",
                "--grade", "E2", "--kind", "validation", "--summary", "Executed pass", "--command", command,
                "--run", "--accepted", cwd=directory,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            record = json.loads((Path(directory) / ".agent-project" / "evidence" / "evidence-001.json").read_text())
            self.assertEqual(record["verification"]["executor"], "agent-project")
            self.assertEqual(record["verification"]["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
