from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCODE_CONFIG_ROOT = REPO_ROOT / "config" / "opencode"


class BundledRuntimePayloadTests(unittest.TestCase):
    def test_runtime_governance_includes_governed_dependency_surfaces_in_runtime_payload_contract(self) -> None:
        """Declare runtime support roots that exist in the canonical source."""
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        directories = set(governance["packaging"]["runtime_payload"]["directories"])
        files = set(governance["packaging"]["runtime_payload"]["files"])

        self.assertIn("docs", directories)
        self.assertNotIn("references", directories)
        self.assertIn("protocols", directories)
        self.assertIn("templates", directories)
        self.assertEqual([], [path for path in directories if not (REPO_ROOT / path).is_dir()])
        self.assertIn("core/skill-contracts/v1/vibe.json", files)

    def test_runtime_governance_declares_explicit_script_and_config_manifests(self) -> None:
        """Keep script and config payloads tied to their explicit manifests."""
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
        verification_gates = set(script_manifest["role_groups"]["files"]["verification_gates"])
        self.assertTrue(
            {
                "scripts/verify/vibe-no-silent-fallback-contract-gate.ps1",
                "scripts/verify/vibe-no-self-introduced-fallback-gate.ps1",
                "scripts/verify/vibe-release-truth-consistency-gate.ps1",
            }.issubset(verification_gates)
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
        self.assertIn("config/operator-preview-contract.json", set(config_manifest["files"]))
        self.assertIn(
            "config/operator-preview-contract.json",
            set(config_manifest["role_groups"]["files"]["runtime_governance_files"]),
        )

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
        self.assertFalse(full_packaging["internal_skill_corpus"]["enabled"])
        self.assertFalse(minimal_packaging["internal_skill_corpus"]["enabled"])
        self.assertEqual([], full_packaging["internal_skill_corpus"]["resident_skill_names"])
        self.assertEqual([], minimal_packaging["internal_skill_corpus"]["resident_skill_names"])
        self.assertEqual("skills/vibe", full_packaging["canonical_vibe_payload"]["target_relpath"])
        self.assertEqual("skills/vibe", minimal_packaging["canonical_vibe_payload"]["target_relpath"])

    def test_repo_no_longer_tracks_bundled_vibe_mirror(self) -> None:
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "vibe").exists())


if __name__ == "__main__":
    unittest.main()
