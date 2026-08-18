import copy
import json
from pathlib import Path
import unittest


try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:
    Draft202012Validator = None
    Registry = None
    Resource = None


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
NOW = "2026-08-18T00:00:00Z"


def governance_samples():
    supervision = {"cadence": "weekly", "timezone": "UTC", "next_due_at": NOW}
    asset = {"path": "agents/pm.md", "commit": "abc123", "sha256": "a" * 64}
    return {
        "organization-manifest-v1.schema.json": {
            "protocol_version": "1.0", "organization_id": "studio", "name": "Studio",
            "founder": "human:founder", "executive_roles": {"ceo": "agent:ceo", "pmo": "agent:pmo"},
            "human_authority": ["production"], "created_at": NOW, "updated_at": NOW,
        },
        "project-registry-v1.schema.json": {
            "protocol_version": "1.0", "organization_id": "studio", "projects": [{
                "project_id": "demo", "owner": "human:founder", "priority": "P2", "lifecycle": "active",
                "path": "projects/demo", "repository": None, "depends_on": [], "provides": [],
                "consumes": [], "verification": ["python -m unittest"], "supervision": supervision,
            }], "created_at": NOW, "updated_at": NOW,
        },
        "role-assignment-v1.schema.json": {
            "protocol_version": "1.0", "assignment_id": "assignment-demo", "scope": "project",
            "project_id": "demo", "role": "accountable_pm", "agent_id": "agent:pm", "status": "active",
            "assigned_by": "human:founder", "assigned_at": NOW,
        },
        "supervision-policy-v1.schema.json": {
            "protocol_version": "1.0", "policy_id": "supervision-demo", **supervision,
        },
        "dispatch-envelope-v1.schema.json": {
            "protocol_version": "1.0", "dispatch_id": "dispatch-demo", "project_id": "demo",
            "assigned_to": "agent:pm", "objective": "Reconcile evidence", "expected_outputs": ["Report"],
            "acceptance_criteria": ["Commit referenced"], "due_at": NOW, "status": "issued",
            "issued_by": "agent:pmo", "created_at": NOW,
        },
        "child-pm-report-v1.schema.json": {
            "protocol_version": "1.0", "report_id": "report-demo", "dispatch_id": "dispatch-demo",
            "project_id": "demo", "submitted_by": "agent:pm", "summary": "Green", "project_commit": "abc123",
            "commit_verification": {"status": "unavailable"},
            "reported_status": "waiting_review", "next_acceptance": "Consumer accepts", "blockers": [],
            "evidence_refs": ["evidence:demo"], "submitted_at": NOW,
        },
        "supervision-review-v1.schema.json": {
            "protocol_version": "1.0", "review_id": "review-demo", "review_type": "supervision_report",
            "report_id": "report-demo", "project_id": "demo", "outcome": "accepted",
            "reviewed_by": "agent:pmo", "note": "Coherent", "reviewed_at": NOW,
        },
        "portfolio-review-v1.schema.json": {
            "protocol_version": "1.0", "review_id": "portfolio-demo", "organization_id": "studio",
            "as_of": NOW, "projects": [], "ceo_decision_queue": [], "created_at": NOW,
        },
        "role-v1.schema.json": {
            "protocol_version": "1.0", "role_id": "project-pm", "name": "Project PM",
            "purpose": "Supervise a project", "authority": ["report"], "status": "active", "created_at": NOW,
        },
        "agent-registry-v1.schema.json": {
            "protocol_version": "1.0", "agent_id": "agent:pm", "name": "PM", "role_ids": ["project-pm"],
            "lifecycle": "active", "active_release_id": "pm-v1", "candidate_release_id": None,
            "created_at": NOW, "updated_at": NOW,
        },
        "capability-profile-v1.schema.json": {
            "protocol_version": "1.0", "profile_id": "capability-agent-pm", "agent_id": "agent:pm",
            "capabilities": [], "updated_at": NOW,
        },
        "agent-release-v1.schema.json": {
            "protocol_version": "1.0", "release_id": "pm-v1", "agent_id": "agent:pm", "status": "active",
            "asset": asset, "rollback_release_id": None, "created_at": NOW, "activated_at": NOW,
        },
        "agent-evaluation-v1.schema.json": {
            "protocol_version": "1.0", "evaluation_id": "eval-pm", "agent_id": "agent:pm",
            "reviewer": "agent:reviewer", "score": 4, "outcome": "passed",
            "evidence_refs": ["evidence:eval"], "evaluated_at": NOW,
        },
        "agent-upgrade-proposal-v1.schema.json": {
            "protocol_version": "1.0", "proposal_id": "upgrade-pm", "agent_id": "agent:pm",
            "candidate_release_id": "pm-v2", "evaluation_id": "eval-pm", "proposed_by": "agent:pm",
            "status": "proposed", "created_at": NOW, "reviewed_at": None, "approved_by": None,
        },
        "workforce-review-v1.schema.json": {
            "protocol_version": "1.0", "review_id": "workforce-demo", "agents": [],
            "upgrade_queue": [], "created_at": NOW,
        },
        "cadence-run-v1.schema.json": {
            "protocol_version": "1.0", "run_id": "cadence-demo", "organization_id": "studio",
            "window_start": NOW, "window_end": "2026-08-19T00:00:00Z", "as_of": NOW,
            "dedupe_key": "b" * 64, "status": "planned", "actions": [], "created_at": NOW, "updated_at": NOW,
        },
    }


@unittest.skipIf(Draft202012Validator is None, "install the test extra for JSON Schema checks")
class GovernanceSchemaTest(unittest.TestCase):
    def test_each_governance_record_accepts_valid_and_rejects_missing_or_incompatible_version(self):
        schemas = {path.name: json.loads(path.read_text()) for path in SCHEMA_ROOT.glob("*.schema.json")}
        registry = Registry().with_resources(
            [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
        )
        for name, sample in governance_samples().items():
            validator = Draft202012Validator(schemas[name], registry=registry)
            self.assertEqual(list(validator.iter_errors(sample)), [], name)
            missing = copy.deepcopy(sample)
            missing.pop(schemas[name]["required"][0])
            self.assertTrue(list(validator.iter_errors(missing)), name)
            incompatible = copy.deepcopy(sample)
            incompatible["protocol_version"] = "2.0"
            self.assertTrue(list(validator.iter_errors(incompatible)), name)

    def test_governance_schema_samples_cover_every_new_public_contract(self):
        expected = {
            "organization-manifest-v1.schema.json", "project-registry-v1.schema.json",
            "role-assignment-v1.schema.json", "supervision-policy-v1.schema.json",
            "dispatch-envelope-v1.schema.json", "child-pm-report-v1.schema.json",
            "supervision-review-v1.schema.json", "portfolio-review-v1.schema.json",
            "role-v1.schema.json", "agent-registry-v1.schema.json", "capability-profile-v1.schema.json",
            "agent-release-v1.schema.json", "agent-evaluation-v1.schema.json",
            "agent-upgrade-proposal-v1.schema.json", "workforce-review-v1.schema.json",
            "cadence-run-v1.schema.json",
        }
        self.assertEqual(set(governance_samples()), expected)


if __name__ == "__main__":
    unittest.main()
