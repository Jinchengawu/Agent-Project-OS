import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tests.test_cli_init import run_cli


class MigrationProjectionTest(unittest.TestCase):
    def test_legacy_portfolio_migrates_once_without_dual_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_root = root / "projects" / "demo"
            project_root.mkdir(parents=True)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=project_root).returncode, 0)
            self.assertEqual(
                run_cli(
                    "project", "add",
                    "--portfolio-id", "legacy",
                    "--portfolio-name", "Legacy",
                    "--project-id", "demo",
                    "--path", "projects/demo",
                    "--owner", "human:founder",
                    "--verification", "python -m unittest",
                    cwd=root,
                ).returncode,
                0,
            )
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
            migrated = run_cli("--json", "migrate", "portfolio-v1", cwd=root)
            self.assertEqual(migrated.returncode, 0, migrated.stderr)
            self.assertFalse((root / "portfolio.json").exists())
            self.assertTrue((root / ".agent-project" / "migrations" / "portfolio-v1.archived.json").is_file())
            listed = run_cli("--json", "project", "list", cwd=root)
            self.assertEqual(json.loads(listed.stdout)["projects"][0]["project_id"], "demo")
            repeated = run_cli("migrate", "portfolio-v1", cwd=root)
            self.assertEqual(repeated.returncode, 2)

    def test_dashboard_and_sqlite_are_disposable_rebuildable_projections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_root = root / "projects" / "demo"
            project_root.mkdir(parents=True)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=project_root).returncode, 0)
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
                    "--project-id", "demo",
                    "--path", "projects/demo",
                    "--owner", "human:founder",
                    "--verification", "python -m unittest",
                    "--next-due-at", "2026-08-18T00:00:00Z",
                    cwd=root,
                ).returncode,
                0,
            )
            self.assertEqual(
                run_cli(
                    "project", "assign-pm",
                    "--assignment-id", "assignment-demo",
                    "--project-id", "demo",
                    "--pm-agent-id", "agent:demo-pm",
                    cwd=root,
                ).returncode,
                0,
            )
            built = run_cli("--json", "dashboard", "build", "--as-of", "2026-08-18T01:00:00Z", cwd=root)
            self.assertEqual(built.returncode, 0, built.stderr)
            first = (root / ".agent-project" / "index" / "dashboard.json").read_bytes()
            shutil.rmtree(root / ".agent-project" / "index")
            rebuilt = run_cli("dashboard", "build", "--as-of", "2026-08-18T01:00:00Z", cwd=root)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
            self.assertEqual((root / ".agent-project" / "index" / "dashboard.json").read_bytes(), first)

            indexed = run_cli("--json", "index", "rebuild", cwd=root)
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            self.assertTrue((root / ".agent-project" / "index.sqlite3").is_file())
            snapshot = {
                "projects": [{"project_id": "demo", "owner": "human:founder", "lifecycle": "active"}],
                "agents": [],
            }
            snapshot_path = root / "synthetic-shadow.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            compared = run_cli("--json", "shadow", "compare", "--snapshot", str(snapshot_path), cwd=root)
            self.assertEqual(compared.returncode, 0, compared.stdout)
            self.assertEqual(json.loads(compared.stdout)["status"], "match")


if __name__ == "__main__":
    unittest.main()
