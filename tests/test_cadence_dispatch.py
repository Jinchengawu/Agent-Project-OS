import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class CadenceDispatchTest(unittest.TestCase):
    def _organization_with_project(self, root):
        project_root = root / "projects" / "service"
        project_root.mkdir(parents=True)
        self.assertEqual(run_cli("init", "--project-id", "service", "--name", "Service", cwd=project_root).returncode, 0)
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
        self.assertEqual(
            run_cli(
                "project", "add",
                "--project-id", "service",
                "--path", "projects/service",
                "--owner", "human:founder",
                "--verification", "python -m unittest",
                "--supervision", "weekly",
                "--next-due-at", "2026-08-18T00:00:00Z",
                cwd=root,
            ).returncode,
            0,
        )
        self.assertEqual(
            run_cli(
                "project", "assign-pm",
                "--assignment-id", "assignment-service-pm",
                "--project-id", "service",
                "--pm-agent-id", "agent:service-pm",
                cwd=root,
            ).returncode,
            0,
        )

    def test_cadence_plan_is_idempotent_and_records_bounded_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._organization_with_project(root)
            arguments = (
                "--json", "cadence", "plan",
                "--run-id", "cadence-week-34",
                "--window-start", "2026-08-18T00:00:00Z",
                "--window-end", "2026-08-25T00:00:00Z",
                "--as-of", "2026-08-18T01:00:00Z",
            )
            first = run_cli(*arguments, cwd=root)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["run"]["actions"][0]["project_id"], "service")

            repeated = run_cli(*arguments, cwd=root)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["run"]["run_id"], "cadence-week-34")
            self.assertEqual(len(list((root / ".agent-project" / "cadence").glob("cadence-run-*.json"))), 1)

            failed = run_cli(
                "cadence", "record",
                "--run-id", "cadence-week-34",
                "--action-id", "supervision-service-2026-08-18T00-00-00Z",
                "--result", "failed",
                "--result-ref", "event:transient-timeout",
                cwd=root,
            )
            self.assertEqual(failed.returncode, 0, failed.stderr)
            recovered = run_cli(
                "cadence", "record",
                "--run-id", "cadence-week-34",
                "--action-id", "supervision-service-2026-08-18T00-00-00Z",
                "--result", "succeeded",
                "--result-ref", "dispatch:service-week-34",
                cwd=root,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            closed = run_cli(
                "cadence", "close",
                "--run-id", "cadence-week-34",
                "--outcome", "completed",
                cwd=root,
            )
            self.assertEqual(closed.returncode, 0, closed.stderr)

    def test_dispatch_renders_three_client_entries_without_launching_clients(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._organization_with_project(root)
            self.assertEqual(
                run_cli(
                    "supervision", "dispatch",
                    "--dispatch-id", "dispatch-service-001",
                    "--project-id", "service",
                    "--objective", "Reconcile current evidence",
                    "--expected-output", "Child PM report",
                    "--acceptance", "Report references project commit",
                    "--due-at", "2026-08-19T00:00:00Z",
                    cwd=root,
                ).returncode,
                0,
            )
            for adapter in ("codex", "claude-code", "deepseek-harness"):
                rendered = run_cli(
                    "--json", "adapter", "render-dispatch",
                    "--adapter", adapter,
                    "--dispatch-id", "dispatch-service-001",
                    cwd=root,
                )
                self.assertEqual(rendered.returncode, 0, rendered.stderr)
                path = root / json.loads(rendered.stdout)["path"]
                self.assertTrue(path.is_file())
                self.assertIn("dispatch-service-001", path.read_text(encoding="utf-8"))

    def test_accepted_monthly_report_advances_local_calendar_across_dst(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_root = root / "projects" / "service"
            project_root.mkdir(parents=True)
            self.assertEqual(run_cli("init", "--project-id", "service", "--name", "Service", cwd=project_root).returncode, 0)
            self.assertEqual(run_cli(
                "org", "init", "--organization-id", "studio", "--name", "Studio",
                "--founder", "human:founder", "--ceo-agent-id", "agent:ceo", "--pmo-agent-id", "agent:pmo",
                cwd=root,
            ).returncode, 0)
            self.assertEqual(run_cli(
                "project", "add", "--project-id", "service", "--path", "projects/service",
                "--owner", "human:founder", "--verification", "python -m unittest",
                "--supervision", "monthly", "--timezone", "America/New_York",
                "--next-due-at", "2026-10-31T13:00:00Z", cwd=root,
            ).returncode, 0)
            self.assertEqual(run_cli(
                "project", "assign-pm", "--assignment-id", "assignment-service",
                "--project-id", "service", "--pm-agent-id", "agent:service-pm", cwd=root,
            ).returncode, 0)
            self.assertEqual(run_cli(
                "supervision", "dispatch", "--dispatch-id", "dispatch-monthly", "--project-id", "service",
                "--objective", "Monthly review", "--expected-output", "Report", "--acceptance", "Commit",
                "--due-at", "2026-10-31T13:00:00Z", cwd=root,
            ).returncode, 0)
            self.assertEqual(run_cli(
                "supervision", "submit", "--report-id", "report-monthly", "--dispatch-id", "dispatch-monthly",
                "--summary", "Green", "--project-commit", "abc123", "--reported-status", "waiting_review",
                "--next-acceptance", "Next monthly review", "--submitted-by", "agent:service-pm", cwd=root,
            ).returncode, 0)
            self.assertEqual(run_cli(
                "supervision", "accept", "--review-id", "review-monthly", "--report-id", "report-monthly",
                "--reviewed-by", "agent:pmo", "--reviewed-at", "2026-10-31T14:00:00Z", cwd=root,
            ).returncode, 0)
            shown = run_cli("--json", "project", "show", "--project-id", "service", cwd=root)
            self.assertEqual(
                json.loads(shown.stdout)["project"]["supervision"]["next_due_at"],
                "2026-11-30T14:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
