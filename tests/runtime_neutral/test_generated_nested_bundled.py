from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPERS = REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1"
PS_RESOLVER = REPO_ROOT / "scripts" / "common" / "Resolve-VgoAdapter.ps1"
PY_RESOLVER = REPO_ROOT / "scripts" / "common" / "resolve_vgo_adapter.py"
PY_RUNTIME_CONTRACTS = REPO_ROOT / "scripts" / "common" / "runtime_contracts.py"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"
CLI_SRC = REPO_ROOT / "apps" / "vgo-cli" / "src"
PS_INSTALLER = REPO_ROOT / "scripts" / "install" / "Install-VgoAdapter.ps1"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "governance" / "sync-bundled-vibe.ps1"
INSTALL_REQUIRED_SKILLS = (
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
)
MIRROR_DIRECTORIES = ["config", "templates", "scripts", "mcp"]
BUNDLED_RELEASE_FILES = ["README.md", "LICENSE"]
BUNDLED_RELEASE_DIRECTORIES = ["agents"]


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


class GeneratedNestedBundledTests(unittest.TestCase):
    def setUp(self) -> None:
        self.powershell = resolve_powershell()
        if self.powershell is None:
            self.skipTest("PowerShell is required for generated nested bundled tests.")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture()
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.root, capture_output=True, text=True, check=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_fixture(self) -> None:
        self._write("scripts/common/vibe-governance-helpers.ps1", HELPERS.read_text(encoding="utf-8"))
        self._write("scripts/governance/sync-bundled-vibe.ps1", SYNC_SCRIPT.read_text(encoding="utf-8"))
        shutil.copytree(CONTRACTS_SRC / "vgo_contracts", self.root / "packages" / "contracts" / "src" / "vgo_contracts", dirs_exist_ok=True)
        shutil.copytree(INSTALLER_CORE_SRC / "vgo_installer", self.root / "packages" / "installer-core" / "src" / "vgo_installer", dirs_exist_ok=True)
        self._write("config/operator-preview-contract.json", json.dumps({"contract_version": 1, "preview_output_root": "outputs/governance/preview"}, indent=2) + "\n")
        self._write(
            "config/version-governance.json",
            json.dumps(
                {
                    "release": {"version": "9.9.9", "updated": "2026-03-30", "channel": "stable", "notes": "fixture"},
                    "source_of_truth": {
                        "canonical_root": ".",
                        "bundled_root": "bundled/skills/vibe",
                        "nested_bundled_root": "bundled/skills/vibe/bundled/skills/vibe",
                    },
                    "mirror_topology": {
                        "canonical_target_id": "canonical",
                        "sync_source_target_id": "canonical",
                        "targets": [
                            {"id": "canonical", "path": ".", "role": "canonical", "required": True, "presence_policy": "required", "sync_enabled": False, "parity_policy": "authoritative"},
                            {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror", "required": True, "presence_policy": "required", "sync_enabled": True, "parity_policy": "full"},
                            {"id": "nested_bundled", "path": "bundled/skills/vibe/bundled/skills/vibe", "role": "mirror", "required": False, "presence_policy": "if_present_must_match", "sync_enabled": False, "parity_policy": "full", "materialization_mode": "release_install_only"},
                        ],
                    },
                    "execution_context_policy": {
                        "require_outer_git_root": True,
                        "fail_if_script_path_is_under_mirror_root": True,
                    },
                    "packaging": {
                        "mirror": {
                            "files": ["SKILL.md"],
                            "directories": ["config", "scripts"],
                        },
                        "target_overrides": {
                            "bundled": {
                                "files": BUNDLED_RELEASE_FILES,
                                "directories": BUNDLED_RELEASE_DIRECTORIES,
                            }
                        },
                        "allow_bundled_only": [],
                        "normalized_json_ignore_keys": ["updated", "generated_at"],
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write("SKILL.md", "---\nname: vibe\ndescription: fixture\n---\n")
        self._write("README.md", "# bundled release readme\n")
        self._write("LICENSE", "fixture license\n")
        self._write("agents/templates/debugger.md", "# debugger\n")
        self._write("config/sample.json", json.dumps({"version": 1}, indent=2) + "\n")
        self._write("scripts/sample.ps1", "Write-Host 'sample'\n")

    def _run_sync(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.root / "scripts" / "governance" / "sync-bundled-vibe.ps1"),
                *extra,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )

    def _switch_to_manifest_packaging_fixture(self) -> None:
        governance_path = self.root / "config" / "version-governance.json"
        governance = json.loads(governance_path.read_text(encoding="utf-8"))
        governance["packaging"]["mirror"]["files"] = [
            "SKILL.md",
            "config/runtime-script-manifest.json",
            "config/runtime-config-manifest.json",
        ]
        governance["packaging"]["mirror"]["directories"] = []
        governance["packaging"]["manifests"] = [
            {"id": "runtime_scripts", "path": "config/runtime-script-manifest.json"},
            {"id": "runtime_configs", "path": "config/runtime-config-manifest.json"},
        ]
        governance_path.write_text(json.dumps(governance, indent=2) + "\n", encoding="utf-8")

        self._write(
            "config/runtime-script-manifest.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "manifest_id": "runtime-scripts",
                    "files": ["scripts/runtime/fixture.ps1"],
                    "directories": [],
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "config/runtime-config-manifest.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "manifest_id": "runtime-config",
                    "files": [
                        "config/runtime-script-manifest.json",
                        "config/runtime-config-manifest.json",
                        "config/version-governance.json",
                        "config/sample.json",
                    ],
                    "directories": [],
                },
                indent=2,
            )
            + "\n",
        )
        self._write("scripts/runtime/fixture.ps1", "Write-Host 'fixture runtime'\n")
        self._write("scripts/extra.ps1", "Write-Host 'extra'\n")
        self._write("config/extra.json", json.dumps({"extra": True}, indent=2) + "\n")

    def test_default_sync_skips_creating_missing_generated_nested_target(self) -> None:
        self._run_sync("-PruneBundledExtras")

        bundled_root = self.root / "bundled" / "skills" / "vibe"
        nested_root = bundled_root / "bundled" / "skills" / "vibe"
        self.assertTrue((bundled_root / "SKILL.md").exists())
        self.assertFalse((nested_root / "SKILL.md").exists())

    def test_opt_in_sync_materializes_generated_nested_target(self) -> None:
        self._run_sync("-PruneBundledExtras", "-IncludeGeneratedCompatibilityTargets")

        bundled_root = self.root / "bundled" / "skills" / "vibe"
        nested_root = bundled_root / "bundled" / "skills" / "vibe"
        self.assertTrue((bundled_root / "SKILL.md").exists())
        self.assertTrue((nested_root / "SKILL.md").exists())
        self.assertEqual(
            (self.root / "config" / "sample.json").read_text(encoding="utf-8"),
            (nested_root / "config" / "sample.json").read_text(encoding="utf-8"),
        )

    def test_prune_removes_legacy_directories_dropped_from_mirror_contract(self) -> None:
        bundled_root = self.root / "bundled" / "skills" / "vibe"
        nested_root = bundled_root / "bundled" / "skills" / "vibe"
        legacy_roots = [bundled_root / "docs", bundled_root / "references", bundled_root / "protocols"]
        legacy_roots += [nested_root / "docs", nested_root / "references", nested_root / "protocols"]
        for legacy_root in legacy_roots:
            legacy_root.mkdir(parents=True, exist_ok=True)
            (legacy_root / "legacy.md").write_text("legacy\n", encoding="utf-8")

        self._run_sync("-PruneBundledExtras", "-IncludeGeneratedCompatibilityTargets")

        for legacy_root in legacy_roots:
            self.assertFalse(legacy_root.exists(), f"Legacy mirror directory should be pruned: {legacy_root}")

    def test_target_specific_release_surfaces_sync_only_to_bundled_target(self) -> None:
        self._run_sync("-PruneBundledExtras", "-IncludeGeneratedCompatibilityTargets")

        bundled_root = self.root / "bundled" / "skills" / "vibe"
        nested_root = bundled_root / "bundled" / "skills" / "vibe"

        self.assertTrue((bundled_root / "README.md").exists())
        self.assertTrue((bundled_root / "LICENSE").exists())
        self.assertTrue((bundled_root / "agents" / "templates" / "debugger.md").exists())

        self.assertFalse((nested_root / "README.md").exists())
        self.assertFalse((nested_root / "LICENSE").exists())
        self.assertFalse((nested_root / "agents").exists())

    def test_manifest_declared_script_and_config_subsets_sync_without_broad_directories(self) -> None:
        self._switch_to_manifest_packaging_fixture()

        self._run_sync("-PruneBundledExtras", "-IncludeGeneratedCompatibilityTargets")

        bundled_root = self.root / "bundled" / "skills" / "vibe"
        nested_root = bundled_root / "bundled" / "skills" / "vibe"

        self.assertTrue((bundled_root / "scripts" / "runtime" / "fixture.ps1").exists())
        self.assertFalse((bundled_root / "scripts" / "extra.ps1").exists())
        self.assertTrue((bundled_root / "config" / "sample.json").exists())
        self.assertFalse((bundled_root / "config" / "extra.json").exists())

        self.assertTrue((nested_root / "scripts" / "runtime" / "fixture.ps1").exists())
        self.assertFalse((nested_root / "scripts" / "extra.ps1").exists())
        self.assertTrue((nested_root / "config" / "sample.json").exists())
        self.assertFalse((nested_root / "config" / "extra.json").exists())


class InstallTimeGeneratedNestedBundledTests(unittest.TestCase):
    def setUp(self) -> None:
        self.powershell = resolve_powershell()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo_root = self.root / "repo"
        self.target_root = self.root / "target"
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.target_root.mkdir(parents=True, exist_ok=True)
        self._write_install_fixture()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_install_fixture(self) -> None:
        self._write("scripts/common/vibe-governance-helpers.ps1", HELPERS.read_text(encoding="utf-8"))
        self._write("scripts/common/Resolve-VgoAdapter.ps1", PS_RESOLVER.read_text(encoding="utf-8"))
        self._write("scripts/common/resolve_vgo_adapter.py", PY_RESOLVER.read_text(encoding="utf-8"))
        self._write("scripts/common/runtime_contracts.py", PY_RUNTIME_CONTRACTS.read_text(encoding="utf-8"))
        self._write("config/adapter-registry.json", (REPO_ROOT / "config" / "adapter-registry.json").read_text(encoding="utf-8"))
        self._write("scripts/install/Install-VgoAdapter.ps1", PS_INSTALLER.read_text(encoding="utf-8"))
        shutil.copytree(CLI_SRC / "vgo_cli", self.repo_root / "apps" / "vgo-cli" / "src" / "vgo_cli", dirs_exist_ok=True)
        shutil.copytree(CONTRACTS_SRC / "vgo_contracts", self.repo_root / "packages" / "contracts" / "src" / "vgo_contracts", dirs_exist_ok=True)
        shutil.copytree(INSTALLER_CORE_SRC / "vgo_installer", self.repo_root / "packages" / "installer-core" / "src" / "vgo_installer", dirs_exist_ok=True)
        self._write("config/upstream-lock.json", json.dumps({"lock_version": 1}, indent=2) + "\n")
        self._write(
            "config/runtime-core-packaging.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "package_id": "runtime-core",
                    "directories": ["skills", "config"],
                    "copy_directories": [{"source": "bundled/skills", "target": "skills"}],
                    "copy_files": [{"source": "config/upstream-lock.json", "target": "config/upstream-lock.json", "optional": False}],
                    "canonical_vibe_mirror": {"enabled": True, "target_relpath": "skills/vibe"},
                    "managed_skill_inventory": {
                        "required_runtime_skills": ["vibe", "dialectic", "local-vco-roles", "spec-kit-vibe-compat", "superclaude-framework-compat", "ralph-loop", "cancel-ralph", "tdd-guide", "think-harder"],
                        "required_workflow_skills": ["brainstorming", "writing-plans", "subagent-driven-development", "systematic-debugging"],
                        "optional_workflow_skills": []
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write(
            "config/version-governance.json",
            json.dumps(
                {
                    "release": {"version": "9.9.9", "updated": "2026-03-30", "channel": "stable", "notes": "fixture"},
                    "source_of_truth": {
                        "canonical_root": ".",
                        "bundled_root": "bundled/skills/vibe",
                        "nested_bundled_root": "bundled/skills/vibe/bundled/skills/vibe",
                    },
                    "mirror_topology": {
                        "canonical_target_id": "canonical",
                        "sync_source_target_id": "canonical",
                        "targets": [
                            {"id": "canonical", "path": ".", "role": "canonical", "required": True, "presence_policy": "required", "sync_enabled": False, "parity_policy": "authoritative"},
                            {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror", "required": True, "presence_policy": "required", "sync_enabled": True, "parity_policy": "full"},
                            {"id": "nested_bundled", "path": "bundled/skills/vibe/bundled/skills/vibe", "role": "mirror", "required": False, "presence_policy": "if_present_must_match", "sync_enabled": False, "parity_policy": "full", "materialization_mode": "release_install_only"},
                        ],
                    },
                    "packaging": {
                        "mirror": {
                            "files": ["SKILL.md", "check.ps1", "check.sh", "install.ps1", "install.sh"],
                            "directories": MIRROR_DIRECTORIES,
                        },
                        "allow_bundled_only": [],
                        "normalized_json_ignore_keys": ["updated", "generated_at"],
                    },
                    "runtime": {
                        "installed_runtime": {
                            "target_relpath": "skills/vibe",
                            "receipt_relpath": "skills/vibe/outputs/runtime-freshness-receipt.json",
                            "require_nested_bundled_root": False,
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )

        self._write("SKILL.md", "---\nname: vibe\ndescription: fixture\n---\n")
        self._write("check.ps1", "Write-Host 'check'\n")
        self._write("check.sh", "#!/usr/bin/env bash\necho check\n")
        self._write("install.ps1", "Write-Host 'install'\n")
        self._write("install.sh", "#!/usr/bin/env bash\necho install\n")
        self._write("config/sample.json", json.dumps({"version": 1}, indent=2) + "\n")
        self._write("templates/template.txt", "template\n")
        self._write("scripts/runtime/sample.ps1", "Write-Host 'sample'\n")
        self._write("mcp/servers.template.json", json.dumps({"servers": []}, indent=2) + "\n")

        vibe_root = self.repo_root / "bundled" / "skills" / "vibe"
        vibe_root.mkdir(parents=True, exist_ok=True)
        for rel in ("SKILL.md", "check.ps1", "check.sh", "install.ps1", "install.sh"):
            source = self.repo_root / rel
            target = vibe_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        for rel in MIRROR_DIRECTORIES:
            source = self.repo_root / rel
            target = vibe_root / rel
            if source.is_dir():
                shutil.copytree(source, target)

        self.assertFalse((vibe_root / "bundled" / "skills" / "vibe" / "SKILL.md").exists())

        for name in INSTALL_REQUIRED_SKILLS:
            skill_dir = self.repo_root / "bundled" / "skills" / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: fixture\n---\n", encoding="utf-8", newline="\n")

    def assert_generated_nested_installed(self) -> None:
        installed_root = self.target_root / "skills" / "vibe"
        nested_root = installed_root / "bundled" / "skills" / "vibe"
        self.assertTrue((installed_root / "SKILL.md").exists())
        self.assertFalse((nested_root / "SKILL.md").exists())
        self.assertTrue((nested_root / "SKILL.runtime-mirror.md").exists())
        self.assertEqual(
            (installed_root / "config" / "sample.json").read_text(encoding="utf-8"),
            (nested_root / "config" / "sample.json").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (installed_root / "scripts" / "runtime" / "sample.ps1").read_text(encoding="utf-8"),
            (nested_root / "scripts" / "runtime" / "sample.ps1").read_text(encoding="utf-8"),
        )

    def test_vgo_cli_installer_materializes_generated_nested_compatibility_root(self) -> None:
        env = os.environ.copy()
        python_path_entries = [str(self.repo_root / "apps" / "vgo-cli" / "src")]
        if env.get("PYTHONPATH"):
            python_path_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

        subprocess.run(
            [
                "python3",
                "-m",
                "vgo_cli.main",
                "install",
                "--repo-root",
                str(self.repo_root),
                "--frontend",
                "shell",
                "--host",
                "openclaw",
                "--profile",
                "minimal",
                "--target-root",
                str(self.target_root),
                "--skip-runtime-freshness-gate",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        self.assert_generated_nested_installed()

    def test_powershell_installer_prefers_installer_core_module_when_python_available(self) -> None:
        if self.powershell is None:
            self.skipTest("PowerShell is required for PowerShell installer test.")

        subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.repo_root / "scripts" / "install" / "Install-VgoAdapter.ps1"),
                "-RepoRoot",
                str(self.repo_root),
                "-TargetRoot",
                str(self.target_root),
                "-HostId",
                "openclaw",
                "-Profile",
                "minimal",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assert_generated_nested_installed()

    def test_powershell_fallback_installer_materializes_generated_nested_compatibility_root(self) -> None:
        if self.powershell is None:
            self.skipTest("PowerShell is required for fallback installer test.")

        env = os.environ.copy()
        empty_path = self.root / "no-python-path"
        empty_path.mkdir(parents=True, exist_ok=True)
        env["PATH"] = str(empty_path)
        subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.repo_root / "scripts" / "install" / "Install-VgoAdapter.ps1"),
                "-RepoRoot",
                str(self.repo_root),
                "-TargetRoot",
                str(self.target_root),
                "-HostId",
                "openclaw",
                "-Profile",
                "minimal",
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        self.assert_generated_nested_installed()
