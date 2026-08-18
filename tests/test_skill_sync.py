from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillSyncTest(unittest.TestCase):
    def test_project_skill_matches_packaged_adapter_template(self):
        project_skill = ROOT / ".agents" / "skills" / "agent-project-os" / "SKILL.md"
        packaged_skill = ROOT / "src" / "agent_project_os" / "templates" / "agent-project-os" / "SKILL.md"
        self.assertEqual(project_skill.read_bytes(), packaged_skill.read_bytes())
        self.assertTrue(project_skill.read_text().startswith("---\nname: agent-project-os\n"))


if __name__ == "__main__":
    unittest.main()
