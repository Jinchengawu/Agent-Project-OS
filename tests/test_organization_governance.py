import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class OrganizationGovernanceTest(unittest.TestCase):
    def test_ceo_pmo_project_pm_report_acceptance_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_root = root / "projects" / "service"
            project_root.mkdir(parents=True)
            self.assertEqual(
                run_cli("init", "--project-id", "service", "--name", "Service", cwd=project_root).returncode,
                0,
            )

            initialized = run_cli(
                "--json",
                "org",
                "init",
                "--organization-id",
                "studio",
                "--name",
                "Studio",
                "--founder",
                "human:founder",
                "--ceo-agent-id",
                "agent:ceo",
                "--pmo-agent-id",
                "agent:pmo",
                cwd=root,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            registered = run_cli(
                "project",
                "add",
                "--project-id",
                "service",
                "--path",
                "projects/service",
                "--owner",
                "human:founder",
                "--verification",
                "python -m unittest",
                "--supervision",
                "weekly",
                "--next-due-at",
                "2026-08-18T00:00:00Z",
                cwd=root,
            )
            self.assertEqual(registered.returncode, 0, registered.stderr)

            assigned = run_cli(
                "project",
                "assign-pm",
                "--assignment-id",
                "assignment-service-pm",
                "--project-id",
                "service",
                "--pm-agent-id",
                "agent:service-pm",
                cwd=root,
            )
            self.assertEqual(assigned.returncode, 0, assigned.stderr)
            duplicate = run_cli(
                "project",
                "assign-pm",
                "--assignment-id",
                "assignment-service-pm-2",
                "--project-id",
                "service",
                "--pm-agent-id",
                "agent:other-pm",
                cwd=root,
            )
            self.assertEqual(duplicate.returncode, 2)
            self.assertIn("exactly one accountable PM", duplicate.stderr)

            dispatched = run_cli(
                "supervision",
                "dispatch",
                "--dispatch-id",
                "dispatch-service-week-34",
                "--project-id",
                "service",
                "--objective",
                "Report current delivery evidence and blockers",
                "--expected-output",
                "A bounded child PM report",
                "--acceptance",
                "References current project commit",
                "--due-at",
                "2026-08-19T00:00:00Z",
                cwd=root,
            )
            self.assertEqual(dispatched.returncode, 0, dispatched.stderr)

            submitted = run_cli(
                "supervision",
                "submit",
                "--report-id",
                "report-service-week-34",
                "--dispatch-id",
                "dispatch-service-week-34",
                "--summary",
                "Validation is green; awaiting consumer review.",
                "--project-commit",
                "abc1234",
                "--reported-status",
                "waiting_review",
                "--next-acceptance",
                "Consumer accepts service contract",
                "--evidence-ref",
                "evidence:service-e2",
                "--submitted-by",
                "agent:service-pm",
                cwd=root,
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)
            report = json.loads(
                (root / ".agent-project" / "reports" / "report-service-week-34.json").read_text()
            )
            self.assertNotIn("tasks", report)
            self.assertNotIn("task_ledger", report)

            accepted = run_cli(
                "supervision",
                "accept",
                "--review-id",
                "review-service-week-34",
                "--report-id",
                "report-service-week-34",
                "--reviewed-by",
                "agent:pmo",
                "--note",
                "Evidence pointer and next acceptance are coherent.",
                cwd=root,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            review = run_cli(
                "--json",
                "portfolio",
                "review",
                "--review-id",
                "portfolio-review-week-34",
                "--as-of",
                "2026-08-19T01:00:00Z",
                cwd=root,
            )
            self.assertEqual(review.returncode, 0, review.stderr)
            payload = json.loads(review.stdout)
            self.assertEqual(payload["review"]["projects"][0]["project_id"], "service")
            self.assertEqual(payload["review"]["projects"][0]["report_status"], "accepted")
            self.assertEqual(payload["review"]["ceo_decision_queue"], [])

            validated = run_cli("--json", "org", "validate", cwd=root)
            self.assertEqual(validated.returncode, 0, validated.stdout)


if __name__ == "__main__":
    unittest.main()
