import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_project_os.cli import main


def call(root, *arguments):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(["--root", str(root), *arguments])
    return code, stdout.getvalue(), stderr.getvalue()


class ScaleGateTest(unittest.TestCase):
    def test_thirty_projects_and_fifty_agents_rebuild_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(call(
                root, "org", "init", "--organization-id", "scale-lab", "--name", "Scale Lab",
                "--founder", "human:founder", "--ceo-agent-id", "agent:ceo", "--pmo-agent-id", "agent:pmo",
            )[0], 0)
            self.assertEqual(call(
                root, "role", "add", "--role-id", "project-pm", "--name", "Project PM",
                "--purpose", "Supervise one project", "--authority", "submit_supervision_report",
            )[0], 0)
            for index in range(50):
                agent_id = "agent:scale-{:02d}".format(index)
                self.assertEqual(call(
                    root, "agent", "add", "--agent-id", agent_id, "--name", "Scale {:02d}".format(index),
                    "--role-id", "project-pm",
                )[0], 0)
            for index in range(30):
                project_id = "project-{:02d}".format(index)
                project_root = root / "projects" / project_id
                project_root.mkdir(parents=True)
                self.assertEqual(call(project_root, "init", "--project-id", project_id, "--name", project_id)[0], 0)
                add = [
                    "project", "add", "--project-id", project_id, "--path", "projects/{}".format(project_id),
                    "--owner", "human:founder", "--verification", "python -m unittest",
                    "--next-due-at", "2026-08-18T00:00:00Z",
                ]
                if index:
                    add.extend(["--depends-on", "project-{:02d}".format(index - 1)])
                self.assertEqual(call(root, *add)[0], 0)
                self.assertEqual(call(
                    root, "project", "assign-pm", "--assignment-id", "assignment-{}".format(project_id),
                    "--project-id", project_id, "--pm-agent-id", "agent:scale-{:02d}".format(index),
                )[0], 0)

            status, output, error = call(root, "--json", "org", "validate")
            self.assertEqual(status, 0, output + error)
            affected, output, error = call(root, "--json", "affected", "--project-id", "project-00")
            self.assertEqual(affected, 0, output + error)
            self.assertEqual(len(json.loads(output)["affected"]), 29)
            self.assertEqual(call(root, "dashboard", "build", "--as-of", "2026-08-18T01:00:00Z")[0], 0)
            dashboard = json.loads((root / ".agent-project" / "index" / "dashboard.json").read_text())
            self.assertEqual(len(dashboard["projects"]), 30)
            self.assertEqual(len(dashboard["agents"]), 50)
            self.assertEqual(len(dashboard["due"]), 30)


if __name__ == "__main__":
    unittest.main()
