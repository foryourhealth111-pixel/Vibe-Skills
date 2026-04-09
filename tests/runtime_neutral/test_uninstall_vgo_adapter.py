from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "apps" / "vgo-cli" / "src"
SHELL_ENTRYPOINT = REPO_ROOT / "uninstall.sh"
POWERSHELL_ENTRYPOINT = REPO_ROOT / "uninstall.ps1"
POWERSHELL_COMPAT_UNINSTALLER = REPO_ROOT / "scripts" / "uninstall" / "Uninstall-VgoAdapter.ps1"
COHERENCE_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-uninstall-coherence-gate.ps1"
CODEX_WRAPPER_SKILL_PATHS = [
    "skills/vibe-what-do-i-want/SKILL.md",
    "skills/vibe-how-do-we-do/SKILL.md",
    "skills/vibe-do-it/SKILL.md",
]


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


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class UnifiedUninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.target_root = self.root / "target"
        self.target_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_python_uninstall(
        self,
        *,
        host: str = "codex",
        preview: bool = False,
        purge_empty_dirs: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        env = os.environ.copy()
        python_path_entries = [str(CLI_SRC)]
        if env.get("PYTHONPATH"):
            python_path_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

        cmd = [
            sys.executable,
            "-m",
            "vgo_cli.main",
            "uninstall",
            "--repo-root",
            str(REPO_ROOT),
            "--frontend",
            "shell",
            "--target-root",
            str(self.target_root),
            "--host",
            host,
            "--profile",
            "full",
        ]
        if preview:
            cmd.append("--preview")
        if purge_empty_dirs:
            cmd.append("--purge-empty-dirs")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        return result, json.loads(result.stdout)

    def test_entrypoint_shell_preview_routes_to_python_core(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SHELL_ENTRYPOINT),
                "--host",
                "cursor",
                "--target-root",
                str(self.target_root),
                "--profile",
                "full",
                "--preview",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("cursor", payload["host_id"])
        self.assertEqual("preview-guidance", payload["install_mode"])
        self.assertEqual("preview", payload["mode"])
        self.assertEqual(str(self.target_root.resolve()), payload["target_root"])

    def test_entrypoint_powershell_preview_routes_to_python_core(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(POWERSHELL_ENTRYPOINT),
                "-HostId",
                "cursor",
                "-TargetRoot",
                str(self.target_root),
                "-Profile",
                "full",
                "-Preview",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("cursor", payload["host_id"])
        self.assertEqual("preview", payload["mode"])

    def test_powershell_compat_uninstaller_preview_routes_to_installer_core(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(POWERSHELL_COMPAT_UNINSTALLER),
                "-RepoRoot",
                str(REPO_ROOT),
                "-HostId",
                "cursor",
                "-TargetRoot",
                str(self.target_root),
                "-Profile",
                "full",
                "-Preview",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("cursor", payload["host_id"])
        self.assertEqual("preview", payload["mode"])

    def test_planner_prefers_install_ledger_and_skips_foreign_paths(self) -> None:
        managed_file = self.target_root / "commands" / "vibe.md"
        foreign_file = self.target_root / "commands" / "user.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("managed\n", encoding="utf-8")
        foreign_file.write_text("foreign\n", encoding="utf-8")
        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 1,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "created_paths": ["commands/vibe.md"],
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(managed_file.exists())
        self.assertTrue(foreign_file.exists())
        self.assertIn("ledger", payload["ownership_source"])
        self.assertIn("commands/vibe.md", payload["deleted_paths"])
        self.assertIn("commands/user.md", payload["skipped_foreign_paths"])

    def test_codex_uninstall_ledger_owns_wrapper_skill_surface(self) -> None:
        for rel in CODEX_WRAPPER_SKILL_PATHS:
            path = self.target_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("---\nname: fixture\n---\n", encoding="utf-8")

        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 2,
                "host_id": "codex",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "governed",
                "profile": "full",
                "created_paths": CODEX_WRAPPER_SKILL_PATHS,
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        _, payload = self.run_python_uninstall(host="codex")

        for rel in CODEX_WRAPPER_SKILL_PATHS:
            self.assertIn(rel, payload["deleted_paths"])
            self.assertFalse((self.target_root / rel).exists())

    def test_planner_uses_host_closure_and_mutates_shared_json_owned_only(self) -> None:
        closure_path = self.target_root / ".vibeskills" / "host-closure.json"
        wrapper_path = self.target_root / ".vibeskills" / "bin" / "cursor-specialist-wrapper.sh"
        settings_path = self.target_root / "settings.json"
        write_json(
            closure_path,
            {
                "schema_version": 1,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "specialist_wrapper": {
                    "launcher_path": str(wrapper_path.resolve()),
                    "script_path": str((wrapper_path.with_suffix(".py")).resolve()),
                },
            },
        )
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_path.write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        write_json(
            settings_path,
            {
                "editor.fontSize": 14,
                "vibeskills": {"managed": True, "host_id": "cursor"},
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse((self.target_root / ".vibeskills").exists())
        remaining = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(
            {
                "editor.fontSize": 14,
                "vibeskills": {"managed": True, "host_id": "cursor"},
            },
            remaining,
        )
        self.assertIn("host-closure", payload["ownership_source"])
        self.assertNotIn("settings.json", payload["mutated_json_paths"])

    def test_planner_treats_legacy_cleanup_candidates_as_target_relpaths(self) -> None:
        legacy_root = self.target_root / "skills" / "brainstorming"
        legacy_skill = legacy_root / "SKILL.md"
        legacy_root.mkdir(parents=True, exist_ok=True)
        legacy_skill.write_text("---\nname: brainstorming\n---\n", encoding="utf-8")
        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 2,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "runtime_roots": [],
                "compatibility_roots": [],
                "sidecar_roots": [],
                "config_rollbacks": [],
                "legacy_cleanup_candidates": ["skills/brainstorming"],
                "created_paths": [],
                "owned_tree_roots": [],
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(legacy_root.exists())
        self.assertIn("skills/brainstorming", payload["deleted_paths"])

    def test_planner_mutates_shared_json_when_ledger_marks_it_owned(self) -> None:
        ledger_path = self.target_root / ".vibeskills" / "install-ledger.json"
        settings_path = self.target_root / "settings.json"
        write_json(
            ledger_path,
            {
                "schema_version": 1,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "created_paths": [],
                "managed_json_paths": ["settings.json"],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )
        write_json(
            settings_path,
            {
                "editor.fontSize": 14,
                "vibeskills": {"managed": True, "host_id": "cursor"},
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        mutated = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual({"editor.fontSize": 14}, mutated)
        self.assertIn("settings.json", payload["mutated_json_paths"])

    def test_v2_ledger_does_not_fall_back_to_repo_inventory_for_unclaimed_surfaces(self) -> None:
        managed_command = self.target_root / "commands" / "vibe.md"
        unclaimed_config = self.target_root / "config" / "upstream-lock.json"
        managed_command.parent.mkdir(parents=True, exist_ok=True)
        unclaimed_config.parent.mkdir(parents=True, exist_ok=True)
        managed_command.write_text("managed\n", encoding="utf-8")
        unclaimed_config.write_text("{}\n", encoding="utf-8")
        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 2,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "runtime_roots": [],
                "compatibility_roots": [],
                "sidecar_roots": [],
                "config_rollbacks": [],
                "legacy_cleanup_candidates": [],
                "created_paths": [],
                "owned_tree_roots": ["commands"],
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(managed_command.exists())
        self.assertTrue(unclaimed_config.exists())
        self.assertIn("commands", payload["deleted_paths"])
        self.assertNotIn("config/upstream-lock.json", payload["deleted_paths"])

    def test_planner_uses_legacy_owned_only_fallback_for_repo_managed_surfaces(self) -> None:
        managed_skill = self.target_root / "skills" / "vibe" / "SKILL.md"
        managed_command = self.target_root / "commands" / "vibe.md"
        foreign_command = self.target_root / "commands" / "user.md"
        managed_config = self.target_root / "config" / "upstream-lock.json"
        managed_skill.parent.mkdir(parents=True, exist_ok=True)
        managed_command.parent.mkdir(parents=True, exist_ok=True)
        managed_config.parent.mkdir(parents=True, exist_ok=True)
        managed_skill.write_text("---\nname: vibe\n---\n", encoding="utf-8")
        managed_command.write_text("managed\n", encoding="utf-8")
        foreign_command.write_text("foreign\n", encoding="utf-8")
        managed_config.write_text("{}\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="claude-code")

        self.assertFalse(managed_skill.exists())
        self.assertFalse(managed_command.exists())
        self.assertFalse(managed_config.exists())
        self.assertTrue(foreign_command.exists())
        self.assertIn("legacy", payload["ownership_source"])

    def test_workspace_project_sidecar_is_not_deleted_by_host_uninstall(self) -> None:
        project_path = self.target_root / ".vibeskills" / "project.json"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            project_path,
            {
                "schema_version": 1,
                "workspace_root": str(self.target_root.resolve()),
                "workspace_sidecar_root": str((self.target_root / ".vibeskills").resolve()),
            },
        )
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertTrue(project_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_workspace_project_sidecar_downgrades_host_cleanup_to_targeted_marker_deletion(self) -> None:
        project_path = self.target_root / ".vibeskills" / "project.json"
        host_settings_path = self.target_root / ".vibeskills" / "host-settings.json"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            project_path,
            {
                "schema_version": 1,
                "workspace_root": str(self.target_root.resolve()),
                "workspace_sidecar_root": str((self.target_root / ".vibeskills").resolve()),
            },
        )
        write_json(host_settings_path, {"schema_version": 1})
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(host_settings_path.exists())
        self.assertTrue(project_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertTrue((self.target_root / ".vibeskills").exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])
        self.assertIn(".vibeskills/host-settings.json", payload["deleted_paths"])

    def test_v2_sidecar_roots_preserve_workspace_sidecar_but_remove_host_owned_marker(self) -> None:
        project_path = self.target_root / ".vibeskills" / "project.json"
        host_settings_path = self.target_root / ".vibeskills" / "host-settings.json"
        managed_host_only_path = self.target_root / ".vibeskills" / "managed-host-only.txt"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            project_path,
            {
                "schema_version": 1,
                "workspace_root": str(self.target_root.resolve()),
                "workspace_sidecar_root": str((self.target_root / ".vibeskills").resolve()),
            },
        )
        write_json(host_settings_path, {"schema_version": 1})
        managed_host_only_path.write_text("managed host marker\n", encoding="utf-8")
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")
        write_json(
            self.target_root / ".vibeskills" / "install-ledger.json",
            {
                "schema_version": 2,
                "host_id": "cursor",
                "target_root": str(self.target_root.resolve()),
                "install_mode": "preview-guidance",
                "profile": "full",
                "runtime_roots": [],
                "compatibility_roots": [],
                "sidecar_roots": [".vibeskills"],
                "config_rollbacks": [],
                "legacy_cleanup_candidates": [],
                "created_paths": [".vibeskills/host-settings.json", ".vibeskills/managed-host-only.txt"],
                "owned_tree_roots": [],
                "managed_json_paths": [],
                "generated_from_template_if_absent": [],
                "specialist_wrapper_paths": [],
                "runtime_root": "skills/vibe",
                "canonical_vibe_root": "skills/vibe",
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertTrue(project_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertFalse(host_settings_path.exists())
        self.assertFalse(managed_host_only_path.exists())
        self.assertTrue((self.target_root / ".vibeskills").exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])
        self.assertIn(".vibeskills/host-settings.json", payload["deleted_paths"])
        self.assertIn(".vibeskills/managed-host-only.txt", payload["deleted_paths"])

    def test_workspace_project_sidecar_preserves_vibeskills_when_legacy_ledger_claims_root_dir(self) -> None:
        project_path = self.target_root / ".vibeskills" / "project.json"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        ledger_path = self.target_root / ".vibeskills" / "install-ledger.json"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            project_path,
            {
                "schema_version": 1,
                "workspace_root": str(self.target_root.resolve()),
                "workspace_sidecar_root": str((self.target_root / ".vibeskills").resolve()),
            },
        )
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")
        write_json(
            ledger_path,
            {
                "created_paths": [str((self.target_root / ".vibeskills").resolve())],
                "specialist_wrapper_paths": [],
                "managed_json_paths": [],
                "merged_files": [],
                "generated_from_template_if_absent": [],
            },
        )

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertTrue(project_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertTrue((self.target_root / ".vibeskills").exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_workspace_runtime_artifacts_without_project_descriptor_are_not_deleted_by_host_uninstall(self) -> None:
        host_settings_path = self.target_root / ".vibeskills" / "host-settings.json"
        requirement_path = self.target_root / ".vibeskills" / "docs" / "requirements" / "req.md"
        host_settings_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(host_settings_path, {"schema_version": 1})
        requirement_path.parent.mkdir(parents=True, exist_ok=True)
        requirement_path.write_text("# runtime artifact\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(host_settings_path.exists())
        self.assertTrue(requirement_path.exists())
        self.assertTrue((self.target_root / ".vibeskills").exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_workspace_outputs_runtime_artifacts_without_project_descriptor_are_not_deleted_by_host_uninstall(self) -> None:
        host_settings_path = self.target_root / ".vibeskills" / "host-settings.json"
        output_path = self.target_root / ".vibeskills" / "outputs" / "runtime" / "proof.json"
        host_settings_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(host_settings_path, {"schema_version": 1})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertFalse(host_settings_path.exists())
        self.assertTrue(output_path.exists())
        self.assertTrue((self.target_root / ".vibeskills").exists())
        self.assertNotIn(".vibeskills", payload["deleted_paths"])

    def test_shared_json_parse_failure_warns_without_deleting(self) -> None:
        settings_path = self.target_root / "settings.json"
        settings_path.write_text("{not-json}\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor")

        self.assertTrue(settings_path.exists())
        self.assertFalse(payload["warnings"])

    def test_receipt_and_empty_directory_purge_are_written(self) -> None:
        managed_file = self.target_root / "commands" / "vibe.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("managed\n", encoding="utf-8")

        _, payload = self.run_python_uninstall(host="cursor", purge_empty_dirs=True)

        receipt_path = Path(payload["receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual("PASS", receipt["gate_result"])
        self.assertIn("commands/vibe.md", receipt["deleted_paths"])
        self.assertFalse((self.target_root / "commands").exists())
        self.assertTrue(receipt["empty_dirs_removed"])

    def test_coherence_gate_script_exists(self) -> None:
        self.assertTrue(COHERENCE_GATE.exists())


if __name__ == "__main__":
    unittest.main()
