import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


class FederationTest(unittest.TestCase):
    def test_affected_projects_and_index_are_rebuilt_from_repo_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for project_id in ("contracts", "service", "client"):
                project_root = root / "projects" / project_id
                project_root.mkdir(parents=True)
                result = run_cli("init", "--project-id", project_id, "--name", project_id.title(), cwd=project_root)
                self.assertEqual(result.returncode, 0, result.stderr)

            add_specs = (
                ("contracts", [], ["orders@1"], []),
                ("service", ["contracts"], ["service-api@1"], ["orders@1"]),
                ("client", ["service"], [], ["service-api@1"]),
            )
            for project_id, dependencies, provides, consumes in add_specs:
                args = [
                    "project",
                    "add",
                    "--portfolio-id",
                    "demo-portfolio",
                    "--portfolio-name",
                    "Demo Portfolio",
                    "--project-id",
                    project_id,
                    "--path",
                    "projects/{}".format(project_id),
                    "--owner",
                    "human",
                    "--verification",
                    "python -m unittest",
                ]
                for value in dependencies:
                    args.extend(("--depends-on", value))
                for value in provides:
                    args.extend(("--provides", value))
                for value in consumes:
                    args.extend(("--consumes", value))
                result = run_cli(*args, cwd=root)
                self.assertEqual(result.returncode, 0, result.stderr)

            affected = run_cli("--json", "affected", "--project-id", "contracts", cwd=root)
            self.assertEqual(affected.returncode, 0, affected.stderr)
            self.assertEqual(json.loads(affected.stdout)["affected"], ["client", "service"])

            rebuilt = run_cli("--json", "index", "rebuild", cwd=root)
            self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
            first = json.loads(rebuilt.stdout)["summary"]
            index_path = root / ".agent-project" / "index.sqlite3"
            self.assertTrue(index_path.is_file())
            index_path.unlink()
            second_result = run_cli("--json", "index", "rebuild", cwd=root)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(json.loads(second_result.stdout)["summary"], first)


if __name__ == "__main__":
    unittest.main()
