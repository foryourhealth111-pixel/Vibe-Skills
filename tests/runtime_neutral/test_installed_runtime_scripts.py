from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STRICT_READY_HOSTS = [
    ("claude-code", "VGO_CLAUDE_CODE_SPECIALIST_BRIDGE_COMMAND"),
    ("cursor", "VGO_CURSOR_SPECIALIST_BRIDGE_COMMAND"),
    ("windsurf", "VGO_WINDSURF_SPECIALIST_BRIDGE_COMMAND"),
    ("openclaw", "VGO_OPENCLAW_SPECIALIST_BRIDGE_COMMAND"),
    ("opencode", "VGO_OPENCODE_SPECIALIST_BRIDGE_COMMAND"),
]
MINIMAL_REQUIRED_SKILLS = {
    "vibe",
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
}


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class InstalledRuntimeScriptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.target_root = self.root / "target-a"
        self.target_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def install_shell_runtime(self, host: str = "codex", profile: str = "full") -> None:
        cmd = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            host,
            "--profile",
            profile,
            "--target-root",
            str(self.target_root),
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    def create_fake_bridge(self, name: str, host_id: str) -> Path:
        suffix = ".cmd" if os.name == "nt" else ""
        bridge_path = self.root / f"{name}{suffix}"
        if os.name == "nt":
            bridge_path.write_text(
                "@echo off\r\n"
                "setlocal EnableDelayedExpansion\r\n"
                "set OUT=\r\n"
                ":loop\r\n"
                "if \"%~1\"==\"\" goto done\r\n"
                "if /I \"%~1\"==\"--output\" (\r\n"
                "  set OUT=%~2\r\n"
                "  shift\r\n"
                "  shift\r\n"
                "  goto loop\r\n"
                ")\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "if \"%OUT%\"==\"\" exit /b 2\r\n"
                f"> \"%OUT%\" echo {{\"status\":\"completed\",\"summary\":\"{host_id} bridge executed\"}}\r\n"
                f"echo {host_id} bridge ok\r\n"
                "exit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            bridge_path.write_text(
                "#!/usr/bin/env sh\n"
                "OUT=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    --output)\n"
                "      OUT=\"$2\"\n"
                "      shift 2\n"
                "      ;;\n"
                "    *)\n"
                "      shift\n"
                "      ;;\n"
                "  esac\n"
                "done\n"
                "if [ -z \"$OUT\" ]; then\n"
                "  exit 2\n"
                "fi\n"
                f"printf '%s' '{{\"status\":\"completed\",\"summary\":\"{host_id} bridge executed\"}}' > \"$OUT\"\n"
                f"printf '{host_id} bridge ok\\n'\n",
                encoding="utf-8",
            )
            bridge_path.chmod(bridge_path.stat().st_mode | stat.S_IXUSR)
        return bridge_path

    def invoke_installed_specialist_wrapper(self, launcher_path: Path, host_id: str) -> None:
        output_path = self.root / f"{host_id}-wrapper-result.json"
        completed = subprocess.run(
            [str(launcher_path), "--output", str(output_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn(f"{host_id} bridge ok", completed.stdout)
        self.assertTrue(output_path.exists())
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual("completed", payload["status"])

    def strict_install_env(self, *, powershell: str | None = None, include_fake_bridge: tuple[str, str] | None = None) -> dict[str, str]:
        env = os.environ.copy()
        sanitized_bin = self.root / "strict-bin"
        sanitized_bin.mkdir(parents=True, exist_ok=True)
        blocked = {"claude", "claude-code", "cursor", "cursor-agent", "windsurf", "codeium", "openclaw", "opencode"}
        for candidate in Path("/bin").iterdir():
            if candidate.name in blocked:
                continue
            target = sanitized_bin / candidate.name
            if target.exists():
                continue
            try:
                target.symlink_to(candidate)
            except FileExistsError:
                continue
        env["PATH"] = str(sanitized_bin)
        for _host_id, env_name in STRICT_READY_HOSTS:
            env.pop(env_name, None)
        if include_fake_bridge is not None:
            env_name, bridge_path = include_fake_bridge
            env[env_name] = bridge_path
        return env

    def assert_nested_runtime_skill_entrypoints_sanitized(self, target_root: Path, *, require_nested: bool = True) -> None:
        nested_skills_root = target_root / "skills" / "vibe" / "bundled" / "skills"
        if require_nested:
            self.assertTrue(nested_skills_root.exists())
        elif not nested_skills_root.exists():
            return
        self.assertEqual([], sorted(nested_skills_root.glob("*/SKILL.md")))
        if not require_nested:
            return
        for name in ("vibe", "dialectic", "ralph-loop", "cancel-ralph"):
            self.assertTrue((nested_skills_root / name / "SKILL.runtime-mirror.md").exists())
        self.assertFalse((nested_skills_root / "brainstorming").exists())
        self.assertFalse((nested_skills_root / "xan").exists())

    def test_shell_install_quarantines_legacy_agents_duplicate_for_default_codex_root(self) -> None:
        home_root = self.root / "home"
        target_root = home_root / ".codex"
        duplicate_root = home_root / ".agents" / "skills" / "vibe"
        target_root.mkdir(parents=True, exist_ok=True)
        duplicate_root.mkdir(parents=True, exist_ok=True)
        (duplicate_root / "SKILL.md").write_text(
            "---\nname: vibe\ndescription: legacy duplicate\n---\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["HOME"] = str(home_root)

        cmd = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            "codex",
            "--profile",
            "full",
            "--target-root",
            str(target_root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

        self.assertIn("Quarantined duplicate Codex-discovered vibe skill", result.stdout)
        self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
        self.assertFalse(duplicate_root.exists())
        quarantined = list((home_root / ".agents" / "skills-disabled").glob("vibe.codex-duplicate-*"))
        self.assertEqual(1, len(quarantined))
        self.assertTrue((quarantined[0] / "SKILL.md").exists())

    def test_shell_install_does_not_mutate_agents_duplicate_for_custom_codex_target_root(self) -> None:
        home_root = self.root / "home"
        target_root = home_root / "custom-codex-root"
        duplicate_root = home_root / ".agents" / "skills" / "vibe"
        target_root.mkdir(parents=True, exist_ok=True)
        duplicate_root.mkdir(parents=True, exist_ok=True)
        (duplicate_root / "SKILL.md").write_text(
            "---\nname: vibe\ndescription: legacy duplicate\n---\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["HOME"] = str(home_root)

        cmd = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            "codex",
            "--profile",
            "full",
            "--target-root",
            str(target_root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

        self.assertNotIn("Quarantined duplicate Codex-discovered vibe skill", result.stdout)
        self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
        self.assertTrue(duplicate_root.exists())
        self.assertFalse((home_root / ".agents" / "skills-disabled").exists())

    def test_shell_check_fails_when_legacy_agents_duplicate_is_reintroduced(self) -> None:
        home_root = self.root / "home"
        target_root = home_root / ".codex"
        target_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["HOME"] = str(home_root)

        install_cmd = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            "codex",
            "--profile",
            "full",
            "--target-root",
            str(target_root),
        ]
        subprocess.run(install_cmd, capture_output=True, text=True, check=True, env=env)

        duplicate_root = home_root / ".agents" / "skills" / "vibe"
        duplicate_root.mkdir(parents=True, exist_ok=True)
        (duplicate_root / "SKILL.md").write_text(
            "---\nname: vibe\ndescription: legacy duplicate\n---\n",
            encoding="utf-8",
        )

        installed_root = target_root / "skills" / "vibe"
        check_cmd = [
            "bash",
            str(installed_root / "check.sh"),
            "--host",
            "codex",
            "--profile",
            "full",
            "--target-root",
            str(target_root),
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, env=env)
        self.assertNotEqual(0, check_result.returncode)
        self.assertIn("duplicate Codex-discovered vibe skill surface", check_result.stdout)
        self.assertNotIn("safe_parent_dir: command not found", check_result.stderr)

    def test_shell_install_writes_install_ledger(self) -> None:
        self.install_shell_runtime("codex")
        ledger_path = self.target_root / ".vibeskills" / "install-ledger.json"
        self.assertTrue(ledger_path.exists())
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual("codex", ledger["host_id"])
        self.assertEqual("governed", ledger["install_mode"])
        self.assertEqual("full", ledger["profile"])
        self.assertEqual(str(self.target_root.resolve()), ledger["target_root"])
        self.assertEqual(str(self.target_root.resolve()), ledger["runtime_root"])
        self.assertEqual(str((self.target_root / "skills" / "vibe").resolve()), ledger["canonical_vibe_root"])
        self.assertIn(str(self.target_root.resolve()), ledger["created_paths"])
        self.assertIn(str((self.target_root / "settings.json").resolve()), ledger["managed_json_paths"])
        self.assertIn(str((self.target_root / "settings.json").resolve()), ledger["generated_from_template_if_absent"])
        self.assertTrue(ledger["specialist_wrapper_paths"])
        for wrapper_path in ledger["specialist_wrapper_paths"]:
            self.assertTrue(Path(wrapper_path).exists(), f"wrapper missing: {wrapper_path}")

    def test_canonical_shell_install_supports_minimal_profile(self) -> None:
        target_root = self.root / "bundled-minimal-target"
        target_root.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                "bash",
                str(REPO_ROOT / "install.sh"),
                "--host",
                "codex",
                "--profile",
                "minimal",
                "--target-root",
                str(target_root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        installed_skills = {
            candidate.name
            for candidate in (target_root / "skills").iterdir()
            if candidate.is_dir()
        }
        self.assertEqual(MINIMAL_REQUIRED_SKILLS, installed_skills)
        self.assertIn("Install done.", result.stdout)
        self.assertNotIn("Runtime freshness gate requires the canonical repo root", result.stdout)

    def test_installed_shell_scripts_work_without_repo_level_adapter_registry(self) -> None:
        for profile in ("minimal", "full"):
            with self.subTest(profile=profile):
                shutil.rmtree(self.target_root)
                self.target_root.mkdir(parents=True, exist_ok=True)
                self.install_shell_runtime(profile=profile)
                self.assert_nested_runtime_skill_entrypoints_sanitized(
                    self.target_root,
                    require_nested=(profile == "full"),
                )

                installed_root = self.target_root / "skills" / "vibe"
                check_cmd = [
                    "bash",
                    str(installed_root / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    profile,
                    "--target-root",
                    str(self.target_root),
                ]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
                self.assertIn("=== VCO Adapter Health Check ===", check_result.stdout)
                self.assertNotIn("VGO adapter registry not found", check_result.stdout)
                self.assertNotIn("VGO adapter registry not found", check_result.stderr)

    def test_installed_runtime_bootstrap_supports_openclaw_without_self_deleting_source(self) -> None:
        self.install_shell_runtime(host="openclaw")

        installed_root = self.target_root / "skills" / "vibe"
        env = os.environ.copy()
        env["HOME"] = str(self.root / "home")
        env["OPENCLAW_HOME"] = str(self.target_root)
        bootstrap_cmd = [
            "bash",
            str(installed_root / "scripts" / "bootstrap" / "one-shot-setup.sh"),
            "--host",
            "openclaw",
            "--profile",
            "full",
            "--target-root",
            str(self.target_root),
        ]
        bootstrap_result = subprocess.run(bootstrap_cmd, capture_output=True, text=True, check=True, env=env)

        self.assertIn("Host                  : openclaw", bootstrap_result.stdout)
        self.assertIn("One-shot setup completed.", bootstrap_result.stdout)
        self.assertTrue((installed_root / "SKILL.md").exists())
        self.assertTrue((self.target_root / ".vibeskills" / "host-settings.json").exists())
        self.assertFalse((self.target_root / "mcp_config.json").exists())

    def test_shell_install_prunes_stale_managed_entries_without_recursive_dir_wipe(self) -> None:
        self.install_shell_runtime()

        managed_root = self.target_root / "skills" / "vibe"
        stale_file = managed_root / "config" / "stale.json"
        stale_dir = managed_root / "docs" / "obsolete-dir"
        stale_nested_file = stale_dir / "note.md"

        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_dir.mkdir(parents=True, exist_ok=True)
        stale_file.write_text("stale\n", encoding="utf-8")
        stale_nested_file.write_text("obsolete\n", encoding="utf-8")

        self.install_shell_runtime()

        self.assertFalse(stale_file.exists())
        self.assertFalse(stale_nested_file.exists())
        self.assertFalse(stale_dir.exists())

        install_script = (self.target_root / "skills" / "vibe" / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn("rm -rf", install_script)

    def test_shell_install_preserves_existing_opencode_config_without_mutation(self) -> None:
        self.target_root.mkdir(parents=True, exist_ok=True)
        settings_path = self.target_root / "opencode.json"
        settings_path.write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "mcp": {
                        "playwright": {
                            "enabled": True,
                            "type": "local",
                            "command": ["npx", "@playwright/mcp@latest"],
                        }
                    },
                    "vibeskills": {
                        "host_id": "opencode",
                        "managed": True,
                        "commands_root": str((self.target_root / "commands").resolve()),
                        "agents_root": str((self.target_root / "agents").resolve()),
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                "bash",
                str(REPO_ROOT / "install.sh"),
                "--host",
                "opencode",
                "--profile",
                "full",
                "--target-root",
                str(self.target_root),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("Install done.", result.stdout)
        preserved = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("vibeskills", preserved)
        self.assertIn("mcp", preserved)
        self.assertTrue((self.target_root / "opencode.json.example").exists())

    def test_powershell_fallback_install_writes_sidecars_and_ledger_for_openclaw(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root = self.root / "pwsh-fallback-openclaw"
        target_root.mkdir(parents=True, exist_ok=True)
        env = self.strict_install_env(powershell=powershell)

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                "openclaw",
                "-Profile",
                "full",
                "-TargetRoot",
                str(target_root),
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )

        host_settings_path = target_root / ".vibeskills" / "host-settings.json"
        closure_path = target_root / ".vibeskills" / "host-closure.json"
        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        self.assertIn("Installation complete.", result.stdout)
        self.assertTrue(host_settings_path.exists())
        self.assertTrue(closure_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertFalse((target_root / "mcp_config.json").exists())
        self.assertFalse((target_root / "global_workflows").exists())

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual("openclaw", ledger["host_id"])
        self.assertEqual("runtime-core", ledger["install_mode"])
        self.assertIn(str(host_settings_path.resolve()), ledger["managed_json_paths"])
        self.assertNotIn(str((target_root / "mcp_config.json").resolve()), ledger["managed_json_paths"])
        self.assertTrue(ledger["specialist_wrapper_paths"])

    def test_powershell_install_succeeds_without_python_on_path(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root = self.root / "pwsh-no-python-target"
        target_root.mkdir(parents=True, exist_ok=True)
        empty_bin = self.root / "empty-bin"
        empty_bin.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = str(empty_bin)

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                "codex",
                "-Profile",
                "full",
                "-TargetRoot",
                str(target_root),
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )

        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        self.assertIn("Installation complete.", result.stdout)
        self.assertTrue(ledger_path.exists())
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertIn("payload_summary", ledger)
        self.assertGreater(ledger["payload_summary"]["installed_file_count"], 0)

    def test_powershell_install_payload_summary_ignores_preexisting_foreign_host_content(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root = self.root / "pwsh-foreign-content-target"
        foreign_skill_root = target_root / "skills" / "foreign-user-skill"
        foreign_file = target_root / "host-notes.txt"
        target_root.mkdir(parents=True, exist_ok=True)
        foreign_skill_root.mkdir(parents=True, exist_ok=True)
        (foreign_skill_root / "SKILL.md").write_text("---\nname: foreign-user-skill\n---\n", encoding="utf-8")
        foreign_file.write_text("user content\n", encoding="utf-8")

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                "codex",
                "-Profile",
                "minimal",
                "-TargetRoot",
                str(target_root),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        installed_skills = {
            candidate.name
            for candidate in (target_root / "skills").iterdir()
            if candidate.is_dir()
        }

        self.assertIn("Installation complete.", result.stdout)
        self.assertIn("foreign-user-skill", installed_skills)
        self.assertNotIn("foreign-user-skill", ledger["payload_summary"]["installed_skill_names"])
        self.assertLess(
            ledger["payload_summary"]["installed_file_count"],
            sum(1 for candidate in target_root.rglob("*") if candidate.is_file()),
        )

    def test_install_powershell_entrypoints_do_not_require_as_hashtable_json_parsing(self) -> None:
        candidate_paths = [
            REPO_ROOT / "install.ps1",
            REPO_ROOT / "bundled" / "skills" / "vibe" / "install.ps1",
            REPO_ROOT / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe" / "install.ps1",
        ]
        self.assertTrue((REPO_ROOT / "install.ps1").exists())
        existing_paths = [candidate for candidate in candidate_paths if candidate.exists()]
        self.assertGreaterEqual(len(existing_paths), 1)
        for path in existing_paths:
            with self.subTest(path=path):
                self.assertNotIn("ConvertFrom-Json -AsHashtable", path.read_text(encoding="utf-8"))

    def test_powershell_fallback_install_preserves_existing_opencode_config_without_mutation(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        target_root = self.root / "pwsh-fallback-opencode"
        target_root.mkdir(parents=True, exist_ok=True)
        settings_path = target_root / "opencode.json"
        original = {
            "$schema": "https://opencode.ai/config.json",
            "mcp": {
                "playwright": {
                    "enabled": True,
                    "type": "local",
                    "command": ["npx", "@playwright/mcp@latest"],
                }
            },
            "vibeskills": {
                "host_id": "opencode",
                "managed": True,
                "commands_root": str((target_root / "commands").resolve()),
                "agents_root": str((target_root / "agents").resolve()),
            },
        }
        settings_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

        env = self.strict_install_env(powershell=powershell)
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                "opencode",
                "-Profile",
                "full",
                "-TargetRoot",
                str(target_root),
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )

        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        self.assertIn("Installation complete.", result.stdout)
        self.assertEqual(original, json.loads(settings_path.read_text(encoding="utf-8")))
        self.assertTrue((target_root / "opencode.json.example").exists())
        self.assertTrue(ledger_path.exists())

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual("opencode", ledger["host_id"])
        self.assertNotIn(str(settings_path.resolve()), ledger["managed_json_paths"])
        self.assertIn(str((target_root / ".vibeskills" / "host-settings.json").resolve()), ledger["managed_json_paths"])

    def test_shell_install_require_closed_ready_fails_without_bridge_command(self) -> None:
        for host_id, _env_name in STRICT_READY_HOSTS:
            with self.subTest(host_id=host_id):
                target_root = self.root / f"{host_id}-strict-fail"
                target_root.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(
                    [
                        "bash",
                        str(REPO_ROOT / "install.sh"),
                        "--host",
                        host_id,
                        "--profile",
                        "full",
                        "--target-root",
                        str(target_root),
                        "--require-closed-ready",
                    ],
                    capture_output=True,
                    text=True,
                    env=self.strict_install_env(),
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn("not closed_ready", result.stderr or result.stdout)
                closure_path = target_root / ".vibeskills" / "host-closure.json"
                self.assertTrue(closure_path.exists())
                closure = json.loads(closure_path.read_text(encoding="utf-8"))
                self.assertEqual("configured_offline_unready", closure["host_closure_state"])

    def test_shell_install_require_closed_ready_succeeds_with_real_bridge_command(self) -> None:
        for host_id, env_name in STRICT_READY_HOSTS:
            with self.subTest(host_id=host_id):
                target_root = self.root / f"{host_id}-strict-pass"
                target_root.mkdir(parents=True, exist_ok=True)
                bridge = self.create_fake_bridge(f"{host_id}-strict-bridge", host_id)
                env = os.environ.copy()
                env = self.strict_install_env(include_fake_bridge=(env_name, str(bridge)))
                result = subprocess.run(
                    [
                        "bash",
                        str(REPO_ROOT / "install.sh"),
                        "--host",
                        host_id,
                        "--profile",
                        "full",
                        "--target-root",
                        str(target_root),
                        "--require-closed-ready",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    env=env,
                )
                self.assertIn("Install done.", result.stdout)
                closure_path = target_root / ".vibeskills" / "host-closure.json"
                self.assertTrue(closure_path.exists())
                closure = json.loads(closure_path.read_text(encoding="utf-8"))
                self.assertEqual("closed_ready", closure["host_closure_state"])
                self.assertTrue(bool(closure["specialist_wrapper"]["ready"]))
                self.assertEqual(f"env:{env_name}", closure["specialist_wrapper"]["bridge_source"])
                launcher_path = Path(closure["specialist_wrapper"]["launcher_path"])
                self.assertTrue(launcher_path.exists())
                self.invoke_installed_specialist_wrapper(launcher_path, host_id)

    def test_installed_powershell_scripts_work_without_repo_level_adapter_registry(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        install_cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(self.target_root),
        ]
        subprocess.run(install_cmd, capture_output=True, text=True, check=True)
        self.assert_nested_runtime_skill_entrypoints_sanitized(self.target_root)

        installed_root = self.target_root / "skills" / "vibe"
        check_cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(installed_root / "check.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(self.target_root),
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        self.assertIn("=== VCO Adapter Health Check ===", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stderr)

    def test_powershell_install_quarantines_legacy_agents_duplicate_for_default_codex_root(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        home_root = self.root / "home"
        target_root = home_root / ".codex"
        duplicate_root = home_root / ".agents" / "skills" / "vibe"
        target_root.mkdir(parents=True, exist_ok=True)
        duplicate_root.mkdir(parents=True, exist_ok=True)
        (duplicate_root / "SKILL.md").write_text(
            "---\nname: vibe\ndescription: legacy duplicate\n---\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["HOME"] = str(home_root)

        install_cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(target_root),
        ]
        result = subprocess.run(install_cmd, capture_output=True, text=True, check=True, env=env)

        self.assertIn("Quarantined duplicate Codex-discovered vibe skill", result.stderr + result.stdout)
        self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
        self.assertFalse(duplicate_root.exists())
        quarantined = list((home_root / ".agents" / "skills-disabled").glob("vibe.codex-duplicate-*"))
        self.assertEqual(1, len(quarantined))
        self.assertTrue((quarantined[0] / "SKILL.md").exists())

    def test_powershell_check_fails_when_legacy_agents_duplicate_is_reintroduced(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        home_root = self.root / "home"
        target_root = home_root / ".codex"
        target_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["HOME"] = str(home_root)

        install_cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(target_root),
        ]
        subprocess.run(install_cmd, capture_output=True, text=True, check=True, env=env)

        duplicate_root = home_root / ".agents" / "skills" / "vibe"
        duplicate_root.mkdir(parents=True, exist_ok=True)
        (duplicate_root / "SKILL.md").write_text(
            "---\nname: vibe\ndescription: legacy duplicate\n---\n",
            encoding="utf-8",
        )

        installed_root = target_root / "skills" / "vibe"
        check_cmd = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(installed_root / "check.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(target_root),
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, env=env)
        self.assertNotEqual(0, check_result.returncode)
        self.assertIn("duplicate Codex-discovered vibe skill surface", check_result.stdout)

    def test_powershell_install_require_closed_ready_enforces_real_host_closure(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        host_id = "openclaw"
        env_name = "VGO_OPENCLAW_SPECIALIST_BRIDGE_COMMAND"

        failure_target = self.root / "pwsh-openclaw-strict-fail"
        failure_target.mkdir(parents=True, exist_ok=True)
        fail_result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                host_id,
                "-Profile",
                "full",
                "-TargetRoot",
                str(failure_target),
                "-RequireClosedReady",
            ],
            capture_output=True,
            text=True,
            env=self.strict_install_env(powershell=powershell),
        )
        self.assertNotEqual(0, fail_result.returncode)
        self.assertIn("not closed_ready", fail_result.stderr or fail_result.stdout)

        success_target = self.root / "pwsh-openclaw-strict-pass"
        success_target.mkdir(parents=True, exist_ok=True)
        bridge = self.create_fake_bridge("pwsh-openclaw-bridge", host_id)
        env = self.strict_install_env(powershell=powershell, include_fake_bridge=(env_name, str(bridge)))
        success_result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-HostId",
                host_id,
                "-Profile",
                "full",
                "-TargetRoot",
                str(success_target),
                "-RequireClosedReady",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        self.assertIn("Installation complete.", success_result.stdout)
        closure_path = success_target / ".vibeskills" / "host-closure.json"
        self.assertTrue(closure_path.exists())
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        self.assertEqual("closed_ready", closure["host_closure_state"])
        self.assertEqual(f"env:{env_name}", closure["specialist_wrapper"]["bridge_source"])
        launcher_path = Path(closure["specialist_wrapper"]["launcher_path"])
        self.assertTrue(launcher_path.exists())
        self.invoke_installed_specialist_wrapper(launcher_path, host_id)


if __name__ == "__main__":
    unittest.main()
