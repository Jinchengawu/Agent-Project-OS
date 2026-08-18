import copy
import json
from pathlib import Path
import unittest


try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:  # The runtime has no third-party dependency; CI installs the test extra.
    Draft202012Validator = None
    Registry = None
    Resource = None


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
NOW = "2026-08-14T00:00:00Z"
RUNTIME = {"runtime": "codex", "client_version": "1.0", "model_id": "gpt-5"}


def valid_samples():
    return {
        "project-manifest-v1.schema.json": {
            "protocol_version": "1.0", "project_id": "demo", "name": "Demo", "owner": "human",
            "lifecycle": "active", "repository": {"url": None, "default_branch": "main"},
            "verification": ["python -m unittest"], "created_at": NOW, "updated_at": NOW,
        },
        "project-policy-v1.schema.json": {
            "protocol_version": "1.0", "acceptance": {"default": "human_review", "allow_agent_e2": True},
            "human_gates": ["production", "public_release"],
        },
        "portfolio-manifest-v1.schema.json": {
            "protocol_version": "1.0", "portfolio_id": "portfolio", "name": "Portfolio",
            "projects": [{"project_id": "demo", "owner": "human", "lifecycle": "active", "path": "projects/demo",
                          "repository": None, "depends_on": [], "provides": ["api@1"], "consumes": [],
                          "verification": ["python -m unittest"]}],
        },
        "task-v1.schema.json": {
            "protocol_version": "1.0", "task_id": "task-001", "title": "Task", "description": "",
            "status": "planned", "priority": "medium", "owner": "human", "acceptance_criteria": ["Pass"],
            "evidence_refs": [], "blocker": None, "created_at": NOW, "updated_at": NOW,
        },
        "evidence-v1.schema.json": {
            "protocol_version": "1.0", "evidence_id": "evidence-001", "task_id": "task-001", "grade": "E2",
            "kind": "validation", "summary": "Passed", "verification": {
                "command": "test", "result": "passed", "executor": "agent-project", "exit_code": 0,
                "executed_at": NOW, "duration_ms": 1, "output_sha256": "b" * 64,
            },
            "acceptance_status": "accepted", "created_by": "human", "runtime_identity": RUNTIME, "created_at": NOW,
        },
        "decision-v1.schema.json": {
            "protocol_version": "1.0", "decision_id": "decision-001", "title": "Use Git", "status": "accepted",
            "context": "Portability", "decision": "Use Git files", "rationale": "Portable", "consequences": [],
            "created_by": "human", "runtime_identity": RUNTIME, "created_at": NOW, "updated_at": NOW,
        },
        "handoff-v1.schema.json": {
            "protocol_version": "1.0", "handoff_id": "handoff-001", "project_id": "demo",
            "from_actor": "agent:codex", "to_actor": "agent:claude-code", "goal": "Continue", "completed": ["Core"],
            "in_progress": [], "blocked": [], "decision_refs": [], "evidence_refs": [], "next_actions": ["Verify"],
            "runtime_identity": RUNTIME, "created_at": NOW,
        },
        "change-request-v1.schema.json": {
            "protocol_version": "1.0", "request_id": "request-001", "operation": "update", "entity_type": "task",
            "entity_id": "task-001", "base_updated_at": NOW, "patch": {"status": "ready"},
            "status": "pending_review", "submitted_by": "agent:codex", "runtime_identity": RUNTIME,
            "created_at": NOW, "updated_at": NOW,
        },
        "acceptance-receipt-v1.schema.json": {
            "protocol_version": "1.0", "receipt_id": "receipt-001", "producer": "producer", "consumer": "consumer",
            "artifact": {"protocol_version": "api@1", "commit": "abc123", "sha256": "a" * 64},
            "acceptance_status": "accepted", "evidence_refs": ["evidence-001"], "created_at": NOW,
        },
        "activity-event-v1.schema.json": {
            "protocol_version": "1.0", "event_id": "event-001", "event_type": "task.created",
            "entity": {"type": "task", "id": "task-001"}, "actor": "human", "runtime_identity": RUNTIME,
            "payload": {}, "occurred_at": NOW,
        },
        "runtime-adapter-event-v1.schema.json": {
            "protocol_version": "1.0", "adapter_event_id": "adapter-event-001", "adapter": "codex",
            "normalized_event": "session.started", "session_id": "session-001", "runtime_identity": RUNTIME,
            "payload": {}, "occurred_at": NOW,
        },
    }


class JsonSchemaContractTest(unittest.TestCase):
    def test_schema_documents_are_draft_2020_12_json(self):
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json")):
            schema = json.loads(path.read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith(path.name))

    @unittest.skipIf(Draft202012Validator is None, "install the 'test' extra for JSON Schema conformance tests")
    def test_each_public_record_has_positive_missing_field_and_incompatible_version_samples(self):
        schemas = {path.name: json.loads(path.read_text()) for path in SCHEMA_ROOT.glob("*.schema.json")}
        registry = Registry().with_resources(
            [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
        )
        for name, sample in valid_samples().items():
            validator = Draft202012Validator(schemas[name], registry=registry)
            self.assertEqual(list(validator.iter_errors(sample)), [], name)
            missing = copy.deepcopy(sample)
            missing.pop(schemas[name]["required"][0])
            self.assertTrue(list(validator.iter_errors(missing)), "{} missing-field sample".format(name))
            incompatible = copy.deepcopy(sample)
            incompatible["protocol_version"] = "2.0"
            self.assertTrue(list(validator.iter_errors(incompatible)), "{} incompatible-version sample".format(name))

    @unittest.skipIf(Draft202012Validator is None, "install the 'test' extra for JSON Schema conformance tests")
    def test_illegal_states_and_forged_e2_e3_are_rejected(self):
        schemas = {path.name: json.loads(path.read_text()) for path in SCHEMA_ROOT.glob("*.schema.json")}
        registry = Registry().with_resources(
            [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
        )
        samples = valid_samples()
        cases = []
        task = copy.deepcopy(samples["task-v1.schema.json"])
        task["status"] = "complete"
        cases.append(("task-v1.schema.json", task))
        decision = copy.deepcopy(samples["decision-v1.schema.json"])
        decision["status"] = "approved"
        cases.append(("decision-v1.schema.json", decision))
        e2 = copy.deepcopy(samples["evidence-v1.schema.json"])
        e2.pop("verification")
        cases.append(("evidence-v1.schema.json", e2))
        e3 = copy.deepcopy(samples["evidence-v1.schema.json"])
        e3["grade"] = "E3"
        e3.pop("verification")
        cases.append(("evidence-v1.schema.json", e3))
        for name, sample in cases:
            validator = Draft202012Validator(schemas[name], registry=registry)
            self.assertTrue(list(validator.iter_errors(sample)), name)


if __name__ == "__main__":
    unittest.main()
