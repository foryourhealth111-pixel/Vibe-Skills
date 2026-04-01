from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "uninstall.sh"


class InstalledRuntimeUninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def install_host(self, host: str, target_root: Path, *, profile: str = "full") -> None:
        subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                "--host",
                host,
                "--target-root",
                str(target_root),
                "--profile",
                profile,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def uninstall_host(self, host: str, target_root: Path, *, profile: str = "full") -> dict[str, object]:
        result = subprocess.run(
            [
                "bash",
                str(UNINSTALL_SCRIPT),
                "--host",
                host,
                "--target-root",
                str(target_root),
                "--profile",
                profile,
                "--purge-empty-dirs",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_codex_installed_runtime_uninstall_removes_managed_payload_only(self) -> None:
        target_root = self.root / "codex-root"
        self.install_host("codex", target_root)
        sentinel = target_root / "commands" / "user.md"
        sentinel.write_text("user\n", encoding="utf-8")

        payload = self.uninstall_host("codex", target_root)

        self.assertFalse((target_root / "rules").exists())
        self.assertFalse((target_root / "config" / "plugins-manifest.codex.json").exists())
        self.assertTrue(sentinel.exists())
        self.assertIn("PASS", payload["gate_result"])

    def test_codex_minimal_installed_runtime_uninstall_removes_runtime_and_foundation_catalog(self) -> None:
        target_root = self.root / "codex-minimal-root"
        self.install_host("codex", target_root, profile="minimal")
        sentinel = target_root / "commands" / "user.md"
        sentinel.write_text("user\n", encoding="utf-8")
        self.assertTrue((target_root / "skills" / "brainstorming" / "SKILL.md").exists())
        self.assertFalse((target_root / "skills" / "verification-before-completion").exists())

        payload = self.uninstall_host("codex", target_root, profile="minimal")

        self.assertFalse((target_root / "skills" / "vibe").exists())
        self.assertFalse((target_root / "skills" / "brainstorming").exists())
        self.assertTrue(sentinel.exists())
        self.assertIn("PASS", payload["gate_result"])

    def test_codex_installed_runtime_uninstall_preserves_foreign_skill_dirs(self) -> None:
        target_root = self.root / "codex-foreign-skill-root"
        self.install_host("codex", target_root, profile="full")
        foreign_skill_root = target_root / "skills" / "foreign-user-skill"
        foreign_skill_root.mkdir(parents=True, exist_ok=True)
        (foreign_skill_root / "SKILL.md").write_text("---\nname: foreign-user-skill\n---\n", encoding="utf-8")

        payload = self.uninstall_host("codex", target_root, profile="full")

        self.assertTrue((target_root / "skills").exists())
        self.assertTrue(foreign_skill_root.exists())
        self.assertTrue((foreign_skill_root / "SKILL.md").exists())
        self.assertNotIn("skills", payload["deleted_paths"])
        self.assertIn("skills/foreign-user-skill/SKILL.md", payload["skipped_foreign_paths"])
        self.assertIn("PASS", payload["gate_result"])

    def test_codex_downgrade_from_full_to_minimal_then_uninstall_uses_latest_dual_unit_ledger(self) -> None:
        target_root = self.root / "codex-downgrade-root"
        self.install_host("codex", target_root, profile="full")
        self.assertTrue((target_root / "skills" / "verification-before-completion" / "SKILL.md").exists())

        self.install_host("codex", target_root, profile="minimal")
        sentinel = target_root / "commands" / "user.md"
        recreated_full_skill = target_root / "skills" / "verification-before-completion"
        sentinel.write_text("user\n", encoding="utf-8")
        self.assertFalse(recreated_full_skill.exists())
        recreated_full_skill.mkdir(parents=True, exist_ok=True)
        (recreated_full_skill / "SKILL.md").write_text("---\nname: verification-before-completion\n---\n", encoding="utf-8")
        self.assertTrue((target_root / "skills" / "brainstorming" / "SKILL.md").exists())

        payload = self.uninstall_host("codex", target_root, profile="minimal")

        self.assertFalse((target_root / "skills" / "vibe").exists())
        self.assertFalse((target_root / "skills" / "brainstorming").exists())
        self.assertTrue((recreated_full_skill / "SKILL.md").exists())
        self.assertTrue(sentinel.exists())
        self.assertIn("PASS", payload["gate_result"])

    def test_claude_code_uninstall_removes_vibe_managed_surface(self) -> None:
        target_root = self.root / "claude-root"
        self.install_host("claude-code", target_root)
        settings_path = target_root / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("vibeskills", settings)
        sentinel = target_root / "commands" / "user.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("user\n", encoding="utf-8")

        self.uninstall_host("claude-code", target_root)

        self.assertFalse((target_root / ".vibeskills").exists())
        self.assertTrue(sentinel.exists())
        self.assertFalse(settings_path.exists())

    def test_claude_code_uninstall_preserves_preexisting_settings(self) -> None:
        target_root = self.root / "claude-root-preserve"
        settings_path = target_root / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(
                {
                    "env": {"ANTHROPIC_API_KEY": "secret"},
                    "model": "claude-sonnet-4-6",
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        self.install_host("claude-code", target_root)
        self.uninstall_host("claude-code", target_root)

        self.assertTrue(settings_path.exists())
        mutated = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual({"ANTHROPIC_API_KEY": "secret"}, mutated["env"])
        self.assertEqual("claude-sonnet-4-6", mutated["model"])
        self.assertNotIn("vibeskills", mutated)
        self.assertNotIn("hooks", mutated)

    def test_claude_code_install_preserves_user_pretooluse_hook_without_adding_managed_hook(self) -> None:
        target_root = self.root / "claude-root-user-hook-install"
        settings_path = target_root / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        user_hook_command = "node /user/keep-write-guard.js"
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": user_hook_command,
                                    }
                                ],
                                "description": "VibeSkills managed write guard",
                            }
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self.install_host("claude-code", target_root)

        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        pre_tool_use = settings["hooks"]["PreToolUse"]
        self.assertEqual(1, len(pre_tool_use))
        self.assertEqual(user_hook_command, pre_tool_use[0]["hooks"][0]["command"])
        self.assertNotIn("managed_hook_command", settings["vibeskills"])
        self.assertNotIn("managed_hook_description", settings["vibeskills"])
        self.assertFalse((target_root / "hooks").exists())

    def test_claude_code_uninstall_preserves_user_pretooluse_hook_with_same_description(self) -> None:
        target_root = self.root / "claude-root-user-hook-uninstall"
        settings_path = target_root / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        user_hook_command = "node /user/keep-write-guard.js"
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": user_hook_command,
                                    }
                                ],
                                "description": "VibeSkills managed write guard",
                            }
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self.install_host("claude-code", target_root)
        self.uninstall_host("claude-code", target_root)

        mutated = json.loads(settings_path.read_text(encoding="utf-8"))
        pre_tool_use = mutated["hooks"]["PreToolUse"]
        self.assertEqual(1, len(pre_tool_use))
        self.assertEqual(user_hook_command, pre_tool_use[0]["hooks"][0]["command"])
        self.assertNotIn("vibeskills", mutated)

    def test_claude_code_uninstall_preserves_unowned_vibeskills_sidecar(self) -> None:
        target_root = self.root / "claude-root-unowned-sidecar"
        sidecar_root = target_root / ".vibeskills"
        note_path = sidecar_root / "user-note.txt"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("keep me\n", encoding="utf-8")

        payload = self.uninstall_host("claude-code", target_root)

        self.assertTrue(sidecar_root.exists())
        self.assertTrue(note_path.exists())
        self.assertEqual(["legacy"], payload["ownership_source"])
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_cursor_uninstall_removes_vibe_managed_surface(self) -> None:
        target_root = self.root / "cursor-root"
        self.install_host("cursor", target_root)
        sentinel = target_root / "commands" / "user.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("user\n", encoding="utf-8")

        self.uninstall_host("cursor", target_root)

        self.assertFalse((target_root / ".vibeskills").exists())
        self.assertTrue(sentinel.exists())
        self.assertFalse((target_root / "settings.json").exists())

    def test_windsurf_uninstall_removes_runtime_core_preview_host_payload(self) -> None:
        target_root = self.root / "windsurf-root"
        self.install_host("windsurf", target_root)
        sentinel = target_root / "commands" / "user.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("user\n", encoding="utf-8")

        self.uninstall_host("windsurf", target_root)

        self.assertFalse((target_root / "global_workflows" / "vibe.md").exists())
        self.assertFalse((target_root / ".vibeskills").exists())
        self.assertTrue(sentinel.exists())

    def test_openclaw_uninstall_removes_runtime_core_preview_host_payload(self) -> None:
        target_root = self.root / "openclaw-root"
        self.install_host("openclaw", target_root)
        sentinel = target_root / "commands" / "user.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("user\n", encoding="utf-8")

        self.uninstall_host("openclaw", target_root)

        self.assertFalse((target_root / "global_workflows" / "vibe.md").exists())
        self.assertFalse((target_root / ".vibeskills").exists())
        self.assertTrue(sentinel.exists())

    def test_opencode_uninstall_removes_managed_payload_and_preserves_user_json(self) -> None:
        target_root = self.root / "opencode-root"
        self.install_host("opencode", target_root)
        settings_path = target_root / "opencode.json"
        settings_path.write_text(
            json.dumps(
                {
                    "vibeskills": {
                        "host_id": "opencode",
                        "managed": True,
                        "commands_root": str((target_root / "commands").resolve()),
                    },
                    "user.keep": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        sentinel = target_root / "commands" / "user.md"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("user\n", encoding="utf-8")

        self.uninstall_host("opencode", target_root)

        self.assertFalse((target_root / ".vibeskills").exists())
        self.assertFalse((target_root / "command" / "vibe.md").exists())
        self.assertFalse((target_root / "agents" / "vibe-plan.md").exists())
        self.assertFalse((target_root / "opencode.json.example").exists())
        self.assertTrue(sentinel.exists())
        self.assertTrue(settings_path.exists())
        remaining = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("vibeskills", remaining)
        self.assertTrue(remaining["user.keep"])


if __name__ == "__main__":
    unittest.main()
