import json
from pathlib import Path
import unittest

from tests.test_cli_init import run_cli


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "examples" / "federated-workspace"


class SyntheticWorkspaceTest(unittest.TestCase):
    def test_workspace_validates_and_projects_are_transitively_affected(self):
        validation = run_cli("--json", "validate", cwd=WORKSPACE)
        self.assertEqual(validation.returncode, 0, validation.stdout)
        affected = run_cli("--json", "affected", "--project-id", "contracts", cwd=WORKSPACE)
        self.assertEqual(affected.returncode, 0, affected.stderr)
        self.assertEqual(json.loads(affected.stdout)["affected"], ["client", "service"])

    def test_workspace_contains_only_synthetic_portable_references(self):
        forbidden = ("/Users/", "C:\\Users\\", "company-os", "CEO办公室")
        for path in WORKSPACE.rglob("*"):
            if path.is_file() and not any(part in {"target", "__pycache__"} for part in path.parts):
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for value in forbidden:
                    self.assertNotIn(value, text, str(path))


if __name__ == "__main__":
    unittest.main()
