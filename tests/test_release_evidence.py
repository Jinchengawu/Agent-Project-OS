import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseEvidenceTest(unittest.TestCase):
    def test_real_smokes_separate_runtime_client_and_model_identity(self):
        evidence = json.loads((ROOT / "release" / "smoke-results-v0.1.json").read_text())
        self.assertTrue(evidence["synthetic_only"])
        smokes = {item["runtime"]: item for item in evidence["real_smokes"]}
        self.assertEqual(set(smokes), {"codex", "claude-code"})
        self.assertEqual({item["result"] for item in smokes.values()}, {"passed"})
        self.assertEqual(smokes["claude-code"]["model_id"], "deepseek-v4-pro")
        self.assertNotEqual(smokes["claude-code"]["runtime"], smokes["claude-code"]["model_id"])

    def test_deepseek_harness_claim_stays_keyless_preview(self):
        evidence = json.loads((ROOT / "release" / "smoke-results-v0.1.json").read_text())
        deepseek = evidence["deepseek_harness"]
        self.assertFalse(deepseek["client_installed"])
        self.assertFalse(deepseek["credential_available"])
        self.assertEqual(deepseek["status"], "preview-keyless-passed")
        self.assertEqual(deepseek["pinned_commit"], "47f943859bef60e4160492346772ded9b24f765a")


if __name__ == "__main__":
    unittest.main()
