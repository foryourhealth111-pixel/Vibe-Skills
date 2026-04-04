from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCODE_CONFIG_ROOT = REPO_ROOT / "config" / "opencode"


class BundledRuntimePayloadTests(unittest.TestCase):
    def test_runtime_governance_excludes_narrative_surfaces_from_runtime_payload_contract(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        directories = set(governance["packaging"]["runtime_payload"]["directories"])

        self.assertNotIn("docs", directories)
        self.assertNotIn("references", directories)
        self.assertNotIn("protocols", directories)
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
        script_manifest = json.loads((REPO_ROOT / "config" / "runtime-script-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("apps/vgo-cli", set(script_manifest["directories"]))
        self.assertIn("packages/contracts", set(script_manifest["directories"]))
        self.assertIn("packages/installer-core", set(script_manifest["directories"]))
        self.assertIn("packages/runtime-core", set(script_manifest["directories"]))
        self.assertIn("scripts/verify/runtime_neutral/_bootstrap.py", set(script_manifest["files"]))
        self.assertEqual(
            {"scripts/verify/runtime_neutral/_bootstrap.py"},
            set(script_manifest["role_groups"]["files"]["compatibility_runtime_neutral_verification_support_files"]),
        )

        config_manifest = json.loads((REPO_ROOT / "config" / "runtime-config-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("config/opencode", set(config_manifest["directories"]))
        expected_opencode_files = {
            path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
            for path in sorted(OPENCODE_CONFIG_ROOT.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(expected_opencode_files, {path for path in config_manifest["files"] if path.startswith("config/opencode/")})
        self.assertEqual(expected_opencode_files, set(config_manifest["role_groups"]["files"]["opencode_preview_files"]))
        self.assertEqual([], config_manifest["role_groups"]["directories"]["managed_runtime_config_roots"])
        self.assertTrue(config_manifest["notes"]["explicit_projection_rule"])

        manifests = {entry["id"]: entry for entry in packaging["manifests"]}
        self.assertEqual("config/runtime-script-manifest.json", manifests["runtime_scripts"]["path"])
        self.assertEqual("config/runtime-config-manifest.json", manifests["runtime_configs"]["path"])
        self.assertTrue((REPO_ROOT / "config" / "runtime-script-manifest.json").exists())
        self.assertTrue((REPO_ROOT / "config" / "runtime-config-manifest.json").exists())

    def test_runtime_core_packaging_excludes_tracked_vibe_from_bundled_skill_copy(self) -> None:
        base_packaging = json.loads((REPO_ROOT / "config" / "runtime-core-packaging.json").read_text(encoding="utf-8"))
        full_packaging = json.loads((REPO_ROOT / "config" / "runtime-core-packaging.full.json").read_text(encoding="utf-8"))
        minimal_packaging = json.loads((REPO_ROOT / "config" / "runtime-core-packaging.minimal.json").read_text(encoding="utf-8"))

        self.assertIn("profiles", base_packaging)
        self.assertNotIn("copy_directories", base_packaging)
        self.assertIn("vibe", full_packaging["exclude_bundled_skill_names"])
        self.assertIn("vibe", minimal_packaging["exclude_bundled_skill_names"])
        self.assertEqual("skills/vibe", full_packaging["canonical_vibe_payload"]["target_relpath"])
        self.assertEqual("skills/vibe", minimal_packaging["canonical_vibe_payload"]["target_relpath"])

    def test_repo_no_longer_tracks_bundled_vibe_mirror(self) -> None:
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "vibe").exists())


if __name__ == "__main__":
    unittest.main()
