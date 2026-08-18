import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest

from tests.test_cli_init import run_cli


class LifecycleEdgeTest(unittest.TestCase):
    def test_block_recover_cancel_and_reopen_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=root).returncode, 0)
            self.assertEqual(run_cli("task", "create", "--task-id", "task-001", "--title", "Lifecycle", "--acceptance", "Verified", cwd=root).returncode, 0)
            for state in ("ready", "in_progress"):
                self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", state, cwd=root).returncode, 0)
            blocked = run_cli(
                "task", "update", "--task-id", "task-001", "--status", "blocked",
                "--blocker-type", "dependency", "--blocker-summary", "Waiting for contract", cwd=root,
            )
            self.assertEqual(blocked.returncode, 0, blocked.stderr)
            self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", "in_progress", cwd=root).returncode, 0)
            self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", "waiting_review", cwd=root).returncode, 0)
            self.assertEqual(
                run_cli(
                    "evidence", "add", "--evidence-id", "evidence-001", "--task-id", "task-001",
                    "--grade", "E2", "--kind", "validation", "--summary", "Passed",
                    "--command", "{} -c 'raise SystemExit(0)'".format(shlex.quote(sys.executable)),
                    "--run", "--accepted", cwd=root,
                ).returncode,
                0,
            )
            self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", "done", cwd=root).returncode, 0)
            self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", "in_progress", cwd=root).returncode, 0)
            self.assertEqual(run_cli("task", "update", "--task-id", "task-001", "--status", "cancelled", cwd=root).returncode, 0)
            task = json.loads((root / ".agent-project" / "tasks" / "task-001.json").read_text())
            self.assertEqual(task["status"], "cancelled")
            self.assertIsNone(task["blocker"])

    def test_e3_evidence_requires_an_accepted_consumer_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(run_cli("init", "--project-id", "consumer", "--name", "Consumer", cwd=root).returncode, 0)
            self.assertEqual(run_cli("task", "create", "--task-id", "task-001", "--title", "Consume", "--acceptance", "Consumer accepts", cwd=root).returncode, 0)
            receipt = {
                "$schema": "https://agent-project-os.org/schemas/acceptance-receipt-v1.schema.json",
                "protocol_version": "1.0", "receipt_id": "receipt-001", "producer": "producer", "consumer": "consumer",
                "artifact": {"protocol_version": "api@1", "commit": "abc123", "sha256": "a" * 64},
                "acceptance_status": "accepted", "evidence_refs": [], "created_at": "2026-08-14T00:00:00Z",
            }
            (root / ".agent-project" / "receipts" / "receipt-001.json").write_text(json.dumps(receipt))
            added = run_cli(
                "evidence", "add", "--evidence-id", "evidence-e3", "--task-id", "task-001", "--grade", "E3",
                "--kind", "consumer_acceptance", "--summary", "Consumer accepted artifact", "--receipt-ref", "receipt-001",
                "--accepted", cwd=root,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            record = json.loads((root / ".agent-project" / "evidence" / "evidence-e3.json").read_text())
            self.assertEqual(record["receipt_ref"], "receipt-001")


if __name__ == "__main__":
    unittest.main()
