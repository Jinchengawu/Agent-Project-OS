import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class WorkforceGovernanceTest(unittest.TestCase):
    def test_agent_release_requires_independent_evaluation_and_can_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                run_cli(
                    "org", "init",
                    "--organization-id", "studio",
                    "--name", "Studio",
                    "--founder", "human:founder",
                    "--ceo-agent-id", "agent:ceo",
                    "--pmo-agent-id", "agent:pmo",
                    cwd=root,
                ).returncode,
                0,
            )
            assets = root / "agent-assets"
            assets.mkdir()
            v1 = assets / "project-pm-v1.md"
            v2 = assets / "project-pm-v2.md"
            v1.write_text("Project PM v1\n", encoding="utf-8")
            v2.write_text("Project PM v2 with evidence reconciliation\n", encoding="utf-8")
            v1_sha = hashlib.sha256(v1.read_bytes()).hexdigest()
            v2_sha = hashlib.sha256(v2.read_bytes()).hexdigest()

            role = run_cli(
                "role", "add",
                "--role-id", "project-pm",
                "--name", "Project PM",
                "--purpose", "Supervise one registered project",
                "--authority", "submit_supervision_report",
                cwd=root,
            )
            self.assertEqual(role.returncode, 0, role.stderr)
            for agent_id in ("agent:project-pm", "agent:reviewer", "agent:hr-approver"):
                arguments = [
                    "agent", "add",
                    "--agent-id", agent_id,
                    "--name", agent_id,
                    "--role-id", "project-pm" if agent_id == "agent:project-pm" else "project-pm",
                ]
                if agent_id == "agent:project-pm":
                    arguments.extend([
                        "--release-id", "project-pm-v1",
                        "--asset-path", "agent-assets/project-pm-v1.md",
                        "--asset-commit", "abc111",
                        "--asset-sha256", v1_sha,
                    ])
                result = run_cli(*arguments, cwd=root)
                self.assertEqual(result.returncode, 0, result.stderr)

            evaluation = run_cli(
                "agent", "evaluate",
                "--evaluation-id", "eval-project-pm-v2",
                "--agent-id", "agent:project-pm",
                "--reviewer", "agent:reviewer",
                "--score", "4",
                "--outcome", "passed",
                "--evidence-ref", "evidence:synthetic-eval",
                cwd=root,
            )
            self.assertEqual(evaluation.returncode, 0, evaluation.stderr)

            proposed = run_cli(
                "agent", "propose-upgrade",
                "--proposal-id", "upgrade-project-pm-v2",
                "--agent-id", "agent:project-pm",
                "--release-id", "project-pm-v2",
                "--asset-path", "agent-assets/project-pm-v2.md",
                "--asset-commit", "abc222",
                "--asset-sha256", v2_sha,
                "--evaluation-id", "eval-project-pm-v2",
                "--proposed-by", "agent:project-pm",
                cwd=root,
            )
            self.assertEqual(proposed.returncode, 0, proposed.stderr)

            self_promotion = run_cli(
                "agent", "promote",
                "--proposal-id", "upgrade-project-pm-v2",
                "--approved-by", "agent:project-pm",
                cwd=root,
            )
            self.assertEqual(self_promotion.returncode, 2)
            self.assertIn("candidate, reviewer, and approver must be separate", self_promotion.stderr)

            promoted = run_cli(
                "agent", "promote",
                "--proposal-id", "upgrade-project-pm-v2",
                "--approved-by", "agent:hr-approver",
                cwd=root,
            )
            self.assertEqual(promoted.returncode, 0, promoted.stderr)
            shown = run_cli("--json", "agent", "show", "--agent-id", "agent:project-pm", cwd=root)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(json.loads(shown.stdout)["agent"]["active_release_id"], "project-pm-v2")

            rolled_back = run_cli(
                "agent", "rollback",
                "--agent-id", "agent:project-pm",
                "--approved-by", "agent:hr-approver",
                "--reason", "Synthetic regression",
                cwd=root,
            )
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
            shown = run_cli("--json", "agent", "show", "--agent-id", "agent:project-pm", cwd=root)
            self.assertEqual(json.loads(shown.stdout)["agent"]["active_release_id"], "project-pm-v1")

            review = run_cli(
                "--json", "workforce", "review",
                "--review-id", "workforce-review-001",
                cwd=root,
            )
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertEqual(json.loads(review.stdout)["review"]["agents"][0]["agent_id"], "agent:hr-approver")


if __name__ == "__main__":
    unittest.main()
