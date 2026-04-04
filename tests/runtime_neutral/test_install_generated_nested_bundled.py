from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
CLI_SRC = REPO_ROOT / "apps" / "vgo-cli" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"

REQUIRED_CORE = [
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat",
    "superclaude-framework-compat",
    "ralph-loop",
    "cancel-ralph",
    "tdd-guide",
    "think-harder",
]
REQUIRED_WORKFLOW = [
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
]
MIRROR_DIRECTORIES = ["config", "templates", "scripts", "mcp"]


class InstallGeneratedNestedBundledTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo_root = self.root / "fixture-repo"
        self.target_root = self.root / "target"
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.target_root.mkdir(parents=True, exist_ok=True)
        self._write_fixture()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_skill(self, root: Path, name: str) -> None:
        skill_root = root / name
        skill_root.mkdir(parents=True, exist_ok=True)
        (skill_root / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture\n---\n",
            encoding="utf-8",
            newline="\n",
        )

    def _write_fixture(self) -> None:
        shutil.copy2(INSTALL_SCRIPT, self.repo_root / "install.sh")
        self._write("config/adapter-registry.json", (REPO_ROOT / "config" / "adapter-registry.json").read_text(encoding="utf-8"))
        shutil.copytree(CLI_SRC / "vgo_cli", self.repo_root / "apps" / "vgo-cli" / "src" / "vgo_cli", dirs_exist_ok=True)
        shutil.copytree(CONTRACTS_SRC / "vgo_contracts", self.repo_root / "packages" / "contracts" / "src" / "vgo_contracts", dirs_exist_ok=True)
        shutil.copytree(INSTALLER_CORE_SRC / "vgo_installer", self.repo_root / "packages" / "installer-core" / "src" / "vgo_installer", dirs_exist_ok=True)

        self._write("SKILL.md", "---\nname: vibe\ndescription: fixture canonical\n---\n")
        self._write("check.sh", "#!/usr/bin/env bash\nexit 0\n")
        self._write("docs/fixture.md", "fixture docs\n")
        self._write("references/fixture.md", "fixture refs\n")
        self._write("protocols/fixture.md", "fixture protocols\n")
        self._write("templates/fixture.md", "fixture templates\n")
        self._write("mcp/fixture.json", json.dumps({"name": "fixture"}, indent=2) + "\n")
        self._write("scripts/runtime/fixture.ps1", "Write-Host 'fixture'\n")
        self._write("config/upstream-lock.json", json.dumps({"version": 1}, indent=2) + "\n")
        self._write("config/plugins-manifest.codex.json", json.dumps({"schema_version": 1, "plugins": []}, indent=2) + "\n")
        self._write("config/settings.template.codex.json", json.dumps({"version": 1}, indent=2) + "\n")
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
                            "files": ["SKILL.md", "check.sh"],
                            "directories": MIRROR_DIRECTORIES,
                        }
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

        bundled_skills_root = self.repo_root / "bundled" / "skills"
        vibe_root = bundled_skills_root / "vibe"
        self._write_skill(bundled_skills_root, "vibe")
        for name in REQUIRED_CORE + REQUIRED_WORKFLOW:
            self._write_skill(bundled_skills_root, name)

        for rel in ("SKILL.md", "check.sh"):
            source = self.repo_root / rel
            target = vibe_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for rel in MIRROR_DIRECTORIES:
            source = self.repo_root / rel
            target = vibe_root / rel
            if source.is_dir():
                shutil.copytree(source, target)

        nested_baseline = bundled_skills_root / "vibe" / "bundled" / "skills" / "vibe"
        self.assertFalse(nested_baseline.exists())

    def test_shell_install_materializes_nested_compatibility_with_topology_only_governance(self) -> None:
        governance_path = self.repo_root / "config" / "version-governance.json"
        governance = json.loads(governance_path.read_text(encoding="utf-8"))
        governance.pop("source_of_truth", None)
        governance_path.write_text(json.dumps(governance, indent=2) + "\n", encoding="utf-8")

        result = subprocess.run(
            [
                "bash",
                str(self.repo_root / "install.sh"),
                "--host",
                "codex",
                "--profile",
                "minimal",
                "--target-root",
                str(self.target_root),
                "--skip-runtime-freshness-gate",
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("Install done.", result.stdout)

        installed_root = self.target_root / "skills" / "vibe"
        nested_root = installed_root / "bundled" / "skills" / "vibe"
        self.assertTrue(installed_root.exists())
        self.assertTrue(nested_root.exists())
        self.assertFalse((nested_root / "SKILL.md").exists())
        self.assertTrue((nested_root / "SKILL.runtime-mirror.md").exists())

    def test_shell_install_materializes_nested_compatibility_without_repo_nested_baseline(self) -> None:
        self.assertFalse((self.repo_root / "scripts" / "install" / "install_vgo_adapter.py").exists())

        result = subprocess.run(
            [
                "bash",
                str(self.repo_root / "install.sh"),
                "--host",
                "codex",
                "--profile",
                "minimal",
                "--target-root",
                str(self.target_root),
                "--skip-runtime-freshness-gate",
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("Install done.", result.stdout)

        installed_root = self.target_root / "skills" / "vibe"
        nested_root = installed_root / "bundled" / "skills" / "vibe"
        self.assertTrue(installed_root.exists())
        self.assertTrue(nested_root.exists())
        self.assertFalse((nested_root / "SKILL.md").exists())
        self.assertTrue((nested_root / "SKILL.runtime-mirror.md").exists())
        self.assertFalse((installed_root / "docs").exists())
        self.assertFalse((installed_root / "references").exists())
        self.assertFalse((installed_root / "protocols").exists())
        self.assertEqual(
            (installed_root / "config" / "version-governance.json").read_text(encoding="utf-8"),
            (nested_root / "config" / "version-governance.json").read_text(encoding="utf-8"),
        )
        self.assertFalse((self.repo_root / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe").exists())
