from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER_MODULE_PATH = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"


def load_installer_module():
    spec = importlib.util.spec_from_file_location("install_vgo_adapter", INSTALLER_MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BundledRuntimePayloadTests(unittest.TestCase):
    def test_runtime_core_and_skill_catalog_manifests_are_separated(self) -> None:
        runtime_packaging = json.loads(
            (REPO_ROOT / "config" / "runtime-core-packaging.json").read_text(encoding="utf-8")
        )
        catalog_packaging = json.loads(
            (REPO_ROOT / "config" / "skill-catalog-packaging.json").read_text(encoding="utf-8")
        )

        self.assertIn("profile_manifests", runtime_packaging)
        self.assertEqual("skill-catalog", catalog_packaging["package_id"])
        self.assertEqual("bundled/skills", catalog_packaging["catalog_root"])

    def test_runtime_governance_excludes_narrative_surfaces_from_runtime_payload_contract(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        directories = set(governance["packaging"]["runtime_payload"]["directories"])

        self.assertNotIn("docs", directories)
        self.assertNotIn("references", directories)
        self.assertNotIn("protocols", directories)
        self.assertNotIn("hooks", directories)
        self.assertTrue({"templates", "mcp"}.issubset(directories))

    def test_runtime_governance_declares_explicit_script_and_config_manifests(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        packaging = governance["packaging"]
        directories = set(packaging["runtime_payload"]["directories"])
        files = set(packaging["runtime_payload"]["files"])

        self.assertNotIn("scripts", directories)
        self.assertNotIn("config", directories)
        self.assertIn("config/runtime-script-manifest.json", files)
        self.assertIn("config/runtime-config-manifest.json", files)

        manifests = {entry["id"]: entry for entry in packaging["manifests"]}
        self.assertEqual("config/runtime-script-manifest.json", manifests["runtime_scripts"]["path"])
        self.assertEqual("config/runtime-config-manifest.json", manifests["runtime_configs"]["path"])
        self.assertTrue((REPO_ROOT / "config" / "runtime-script-manifest.json").exists())
        self.assertTrue((REPO_ROOT / "config" / "runtime-config-manifest.json").exists())
        self.assertNotIn("config/skill-catalog-packaging.json", files)
        self.assertNotIn("config/skill-catalog-profiles.json", files)
        self.assertNotIn("config/skill-catalog-groups.json", files)

    def test_runtime_required_markers_exclude_catalog_manifests(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        required_markers = set(governance["runtime"]["installed_runtime"]["required_runtime_markers"])

        self.assertNotIn("config/skill-catalog-packaging.json", required_markers)
        self.assertNotIn("config/skill-catalog-profiles.json", required_markers)
        self.assertNotIn("config/skill-catalog-groups.json", required_markers)
        self.assertNotIn("hooks/write-guard.js", required_markers)

    def test_python_safe_relative_contract_path_rejects_windows_drive_qualified_values(self) -> None:
        installer = load_installer_module()

        with self.assertRaises(SystemExit):
            installer.safe_relative_contract_path(
                "C:outside.json",
                default="config/skill-catalog-packaging.json",
                field_name="profiles_manifest",
            )

    def test_python_installer_resolves_catalog_manifest_via_runtime_core_contract(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir)
            config_root = repo_root / "config"
            alt_root = repo_root / "alt"
            config_root.mkdir(parents=True, exist_ok=True)
            alt_root.mkdir(parents=True, exist_ok=True)

            (config_root / "runtime-core-packaging.json").write_text(
                json.dumps({"catalog_packaging_manifest": "alt/catalog-packaging.json"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (alt_root / "catalog-packaging.json").write_text(
                json.dumps({"package_id": "skill-catalog", "catalog_root": "bundled/skills"}, indent=2) + "\n",
                encoding="utf-8",
            )

            base_root, resolved = installer.resolve_catalog_packaging_manifest_path(repo_root)
            self.assertEqual(repo_root, base_root)
            self.assertEqual(alt_root / "catalog-packaging.json", resolved)
            catalog_packaging, catalog_base_root = installer.load_skill_catalog_packaging(repo_root)
            self.assertEqual(repo_root, catalog_base_root)
            self.assertEqual("skill-catalog", catalog_packaging["package_id"])

    def test_runtime_core_packaging_excludes_tracked_vibe_from_bundled_skill_copy(self) -> None:
        full_packaging = json.loads((REPO_ROOT / "config" / "runtime-core-packaging.full.json").read_text(encoding="utf-8"))
        minimal_packaging = json.loads((REPO_ROOT / "config" / "runtime-core-packaging.minimal.json").read_text(encoding="utf-8"))

        self.assertIn("vibe", full_packaging["exclude_bundled_skill_names"])
        self.assertIn("vibe", minimal_packaging["exclude_bundled_skill_names"])
        self.assertEqual("skills/vibe", full_packaging["canonical_vibe_payload"]["target_relpath"])
        self.assertEqual("skills/vibe", minimal_packaging["canonical_vibe_payload"]["target_relpath"])
        self.assertFalse(full_packaging["copy_bundled_skills"])
        self.assertFalse(minimal_packaging["copy_bundled_skills"])

    def test_python_desired_runtime_managed_skill_names_include_allowlisted_skills(self) -> None:
        installer = load_installer_module()

        managed = installer.desired_runtime_managed_skill_names(
            {
                "canonical_vibe_payload": {"target_relpath": "skills/vibe"},
                "skills_allowlist": ["brainstorming", "custom-skill", "brainstorming"],
            }
        )

        self.assertIn("vibe", managed)
        self.assertIn("brainstorming", managed)
        self.assertIn("custom-skill", managed)
        self.assertEqual(len(managed), len(set(managed)))

    def test_python_previous_ledger_skill_names_must_be_leaf_names_before_prune(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            with self.assertRaises(SystemExit):
                installer.derive_managed_skill_names_from_ledger(
                    target_root,
                    {"managed_runtime_skill_names": ["../../outside"]},
                )

    def test_python_previous_ledger_canonical_vibe_root_must_be_safe_before_prune(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            with self.assertRaises(SystemExit):
                installer.derive_managed_skill_names_from_ledger(
                    target_root,
                    {"canonical_vibe_root": ".."},
                )

    def test_python_load_existing_install_ledger_treats_malformed_payload_as_absent(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            ledger_path = target_root / ".vibeskills" / "install-ledger.json"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text("{\n", encoding="utf-8")

            self.assertIsNone(installer.load_existing_install_ledger(target_root))

    def test_python_runtime_core_packaging_normalizes_blank_catalog_profile(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir)
            config_root = repo_root / "config"
            config_root.mkdir(parents=True, exist_ok=True)
            (config_root / "runtime-core-packaging.json").write_text(
                json.dumps({"profile_manifests": {"full": "config/runtime-core-packaging.full.json"}}, indent=2) + "\n",
                encoding="utf-8",
            )
            (config_root / "runtime-core-packaging.full.json").write_text(
                json.dumps({"profile": "full", "catalog_profile": "   "}, indent=2) + "\n",
                encoding="utf-8",
            )

            packaging = installer.load_runtime_core_packaging(repo_root, "full")

            self.assertEqual("default-full", packaging["catalog_profile"])

    def test_repo_no_longer_tracks_bundled_vibe_mirror(self) -> None:
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "vibe").exists())


if __name__ == "__main__":
    unittest.main()
