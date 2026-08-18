import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_cli_init import run_cli


def file_hashes(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and ".agent-project/events/" not in path.as_posix():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class AdapterTest(unittest.TestCase):
    def test_render_is_idempotent_and_uninstall_restores_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=root).returncode, 0)
            original_claude = "# Existing Claude notes\n\nKeep this line.\n"
            (root / "CLAUDE.md").write_text(original_claude)
            (root / ".claude").mkdir()
            original_settings = '{\n  "permissions": {"deny": ["Read(.env)"]}\n}\n'
            (root / ".claude" / "settings.json").write_text(original_settings)

            rendered = run_cli("--json", "adapter", "render", "--adapter", "all", cwd=root)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertTrue((root / ".agents" / "skills" / "agent-project-os" / "SKILL.md").is_file())
            self.assertTrue((root / ".claude" / "skills" / "agent-project-os" / "SKILL.md").is_file())
            self.assertTrue((root / ".dsh" / "agent-project-os-bundle" / "package.json").is_file())
            claude_text = (root / "CLAUDE.md").read_text()
            self.assertIn("Keep this line.", claude_text)
            self.assertIn("@AGENTS.md", claude_text)
            settings = json.loads((root / ".claude" / "settings.json").read_text())
            self.assertEqual(settings["permissions"]["deny"], ["Read(.env)"])
            self.assertIn("SessionStart", settings["hooks"])

            first = file_hashes(root)
            rerendered = run_cli("adapter", "render", "--adapter", "all", cwd=root)
            self.assertEqual(rerendered.returncode, 0, rerendered.stderr)
            self.assertEqual(file_hashes(root), first)

            bridge = root / ".agent-project" / "adapters" / "event_bridge.py"
            event = subprocess.run(
                [
                    sys.executable,
                    str(bridge),
                    "--adapter",
                    "claude-code",
                    "--normalized-event",
                    "session.started",
                    "--runtime",
                    "claude-code",
                    "--client-version",
                    "test",
                ],
                cwd=root,
                input='{"session_id":"session-123","hook_event_name":"SessionStart"}',
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(event.returncode, 0, event.stderr)
            adapter_events = list((root / ".agent-project" / "events").glob("adapter-event-*.json"))
            self.assertEqual(len(adapter_events), 1)
            normalized = json.loads(adapter_events[0].read_text())
            self.assertEqual(normalized["runtime_identity"]["runtime"], "claude-code")
            self.assertEqual(normalized["normalized_event"], "session.started")
            validation = run_cli("--json", "validate", cwd=root)
            self.assertEqual(validation.returncode, 0, validation.stdout)

            removed = run_cli("adapter", "uninstall", "--adapter", "all", cwd=root)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertEqual((root / "CLAUDE.md").read_text(), original_claude)
            self.assertEqual((root / ".claude" / "settings.json").read_text(), original_settings)
            self.assertFalse((root / ".agents" / "skills" / "agent-project-os" / "SKILL.md").exists())
            self.assertFalse((root / ".dsh" / "agent-project-os-bundle" / "package.json").exists())

    def test_user_install_is_explicit_backed_up_and_reversible(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as user_directory:
            root = Path(directory)
            user_root = Path(user_directory)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=root).returncode, 0)
            target = user_root / ".codex" / "skills" / "agent-project-os" / "SKILL.md"
            target.parent.mkdir(parents=True)
            original = "---\nname: local-copy\ndescription: Keep me\n---\n"
            target.write_text(original)
            environment = {"AGENT_PROJECT_OS_USER_HOME": str(user_root)}

            preview = run_cli(
                "--json",
                "adapter",
                "install",
                "--adapter",
                "codex",
                "--user",
                "--dry-run",
                cwd=root,
                env_overrides=environment,
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(target.read_text(), original)

            installed = run_cli(
                "adapter",
                "install",
                "--adapter",
                "codex",
                "--user",
                cwd=root,
                env_overrides=environment,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertIn("name: agent-project-os", target.read_text())
            state_text = (root / ".agent-project" / "adapters" / "install-state.json").read_text()
            self.assertNotIn(str(user_root), state_text)
            self.assertIn("~/.codex/skills/agent-project-os/SKILL.md", state_text)

            uninstalled = run_cli(
                "adapter",
                "uninstall",
                "--adapter",
                "codex",
                "--user",
                cwd=root,
                env_overrides=environment,
            )
            self.assertEqual(uninstalled.returncode, 0, uninstalled.stderr)
            self.assertEqual(target.read_text(), original)

    def test_doctor_keeps_deepseek_harness_explicitly_preview_and_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(run_cli("init", "--project-id", "demo", "--name", "Demo", cwd=root).returncode, 0)
            self.assertEqual(run_cli("adapter", "render", "--adapter", "deepseek-harness", cwd=root).returncode, 0)
            result = run_cli("--json", "adapter", "doctor", "--adapter", "deepseek-harness", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            deepseek = json.loads(result.stdout)["adapters"]["deepseek-harness"]
            self.assertEqual(deepseek["status"], "preview")
            self.assertEqual(deepseek["pinned_commit"], "47f943859bef60e4160492346772ded9b24f765a")

    def test_adapter_golden_files(self):
        expected = {
            "CLAUDE.md": "a380c42c9aeeb3c68c5b3fadadba36694f084b763b232c449832de0d1f7e28df",
            ".claude/settings.json": "3ebd12939857b420fd3c66173a715dfc96bcc866ca3313d6d05bb572b0c3a58b",
            ".agent-project/adapters/codex.json": "80b77825b8cf728f8de47ffec13997e31fbdf61cad3736b497c9ee37a2bf1aaa",
            ".agent-project/adapters/claude-code.json": "10c1ae4158772e3124689c27c386daa45ac1f67d52b687f0c06c3fc4901c0496",
            ".agent-project/adapters/deepseek-harness.json": "9228b64b3425a69916a184c22a9a191d864750164aeb94cb0658e9f65a2bd991",
            ".dsh/agent-project-os-bundle/package.json": "8bfd52291c823b8029b9ade3b128ed1180390392e745ca841516c2454092bb55",
            ".dsh/agent-project-os-bundle/cordis.patch.yml": "cad7f70b166ae4844b3ff3db860c97dca619f127378309e9eaae4d2249676f5a",
            ".dsh/agent-project-os-bundle/index.js": "1cadf65bc5b103e72e5df8e3618f4077b7529a7ca98cd097cfcd2e9054512a71",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(run_cli("init", "--project-id", "golden", "--name", "Golden", cwd=root).returncode, 0)
            self.assertEqual(run_cli("adapter", "render", "--adapter", "all", cwd=root).returncode, 0)
            actual = {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in expected
            }
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
