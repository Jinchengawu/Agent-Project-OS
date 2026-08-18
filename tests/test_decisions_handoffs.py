import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class DecisionAndHandoffTest(unittest.TestCase):
    def test_decision_supersession_and_handoff_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=directory).returncode, 0)
            for decision_id, title in (("decision-001", "Use files"), ("decision-002", "Use Git files")):
                proposed = run_cli(
                    "decision",
                    "propose",
                    "--decision-id",
                    decision_id,
                    "--title",
                    title,
                    "--context",
                    "Portable project state is required",
                    "--decision",
                    title,
                    "--rationale",
                    "The repository remains portable",
                    cwd=directory,
                )
                self.assertEqual(proposed.returncode, 0, proposed.stderr)
                accepted = run_cli("decision", "accept", "--decision-id", decision_id, cwd=directory)
                self.assertEqual(accepted.returncode, 0, accepted.stderr)

            superseded = run_cli(
                "decision",
                "supersede",
                "--decision-id",
                "decision-001",
                "--by",
                "decision-002",
                cwd=directory,
            )
            self.assertEqual(superseded.returncode, 0, superseded.stderr)
            root = Path(directory)
            first = json.loads((root / ".agent-project" / "decisions" / "decision-001.json").read_text())
            self.assertEqual(first["status"], "superseded")
            self.assertEqual(first["superseded_by"], "decision-002")

            handoff = run_cli(
                "handoff",
                "create",
                "--handoff-id",
                "handoff-001",
                "--from-actor",
                "agent:codex",
                "--to-actor",
                "agent:claude-code",
                "--goal",
                "Continue adapter verification",
                "--completed",
                "Core validation passes",
                "--next-action",
                "Run Claude golden tests",
                "--runtime",
                "codex",
                "--client-version",
                "1.2.3",
                cwd=directory,
            )
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            validated = run_cli("--json", "handoff", "validate", "--handoff-id", "handoff-001", cwd=directory)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertEqual(json.loads(validated.stdout)["status"], "valid")


if __name__ == "__main__":
    unittest.main()
