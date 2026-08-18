import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_init import run_cli


def project_record(project_id, depends_on=None, provides=None, consumes=None):
    return {
        "project_id": project_id,
        "owner": "human",
        "lifecycle": "active",
        "path": "projects/{}".format(project_id),
        "repository": None,
        "depends_on": depends_on or [],
        "provides": provides or [],
        "consumes": consumes or [],
        "verification": ["python -m unittest"],
    }


class FederationFailureTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for project_id in ("producer", "consumer"):
            project_root = self.root / "projects" / project_id
            project_root.mkdir(parents=True)
            result = run_cli("init", "--project-id", project_id, "--name", project_id.title(), cwd=project_root)
            self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self):
        self.temporary.cleanup()

    def write_portfolio(self, projects):
        portfolio = {
            "$schema": "https://agent-project-os.org/schemas/portfolio-manifest-v1.schema.json",
            "protocol_version": "1.0",
            "portfolio_id": "demo",
            "name": "Demo",
            "projects": projects,
        }
        (self.root / "portfolio.json").write_text(json.dumps(portfolio))

    def validation_errors(self):
        result = run_cli("--json", "validate", cwd=self.root)
        self.assertEqual(result.returncode, 1, result.stdout)
        return json.loads(result.stdout)["errors"]

    def test_rejects_cycle_unknown_dependency_and_interface_version_mismatch(self):
        self.write_portfolio(
            [
                project_record("producer", ["consumer"], ["orders@1"]),
                project_record("consumer", ["producer"], consumes=["orders@2"]),
            ]
        )
        errors = self.validation_errors()
        self.assertTrue(any("dependency cycle" in error for error in errors))
        self.assertTrue(any("incompatible interface" in error for error in errors))

        self.write_portfolio([project_record("producer", ["missing"]), project_record("consumer")])
        errors = self.validation_errors()
        self.assertTrue(any("unknown dependency missing" in error for error in errors))

    def test_rejects_unaccepted_cross_project_receipt(self):
        self.write_portfolio(
            [
                project_record("producer", provides=["orders@1"]),
                project_record("consumer", ["producer"], consumes=["orders@1"]),
            ]
        )
        receipt = {
            "$schema": "https://agent-project-os.org/schemas/acceptance-receipt-v1.schema.json",
            "protocol_version": "1.0",
            "receipt_id": "receipt-001",
            "producer": "producer",
            "consumer": "consumer",
            "artifact": {
                "protocol_version": "orders@1",
                "commit": "abc123",
                "sha256": "a" * 64,
            },
            "acceptance_status": "pending",
            "evidence_refs": [],
            "created_at": "2026-08-14T00:00:00Z",
        }
        path = self.root / "projects" / "consumer" / ".agent-project" / "receipts" / "receipt-001.json"
        path.write_text(json.dumps(receipt))

        errors = self.validation_errors()
        self.assertTrue(any("unaccepted cross-project receipt" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
