from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIRROR_ROOTS = [
    REPO_ROOT / "bundled" / "skills" / "vibe",
    REPO_ROOT / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe",
]
MIRROR_PATHS = [
    Path("check.sh"),
    Path("install.sh"),
    Path("scripts/bootstrap/one-shot-setup.sh"),
    Path("scripts/common/runtime_contracts.py"),
    Path("scripts/common/vibe-governance-helpers.ps1"),
    Path("scripts/common/resolve_vgo_adapter.py"),
    Path("scripts/install/install_vgo_adapter.py"),
    Path("scripts/uninstall/uninstall_vgo_adapter.py"),
    Path("scripts/verify/runtime_neutral/freshness_gate.py"),
]


class BundledRuntimeMirrorTests(unittest.TestCase):
    def test_runtime_governance_excludes_narrative_surfaces_from_mirror_contract(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        directories = set(governance["packaging"]["mirror"]["directories"])

        self.assertNotIn("docs", directories)
        self.assertNotIn("references", directories)
        self.assertNotIn("protocols", directories)
        self.assertTrue({"templates", "mcp"}.issubset(directories))

    def test_runtime_governance_declares_explicit_script_and_config_manifests(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        packaging = governance["packaging"]
        directories = set(packaging["mirror"]["directories"])
        files = set(packaging["mirror"]["files"])

        self.assertNotIn("scripts", directories)
        self.assertNotIn("config", directories)
        self.assertIn("config/runtime-script-manifest.json", files)
        self.assertIn("config/runtime-config-manifest.json", files)

        manifests = {entry["id"]: entry for entry in packaging["manifests"]}
        self.assertEqual("config/runtime-script-manifest.json", manifests["runtime_scripts"]["path"])
        self.assertEqual("config/runtime-config-manifest.json", manifests["runtime_configs"]["path"])
        self.assertTrue((REPO_ROOT / "config" / "runtime-script-manifest.json").exists())
        self.assertTrue((REPO_ROOT / "config" / "runtime-config-manifest.json").exists())

    def test_selected_runtime_entrypoints_match_canonical(self) -> None:
        for relative_path in MIRROR_PATHS:
            canonical = (REPO_ROOT / relative_path).read_bytes()
            for mirror_root in MIRROR_ROOTS:
                mirror_path = mirror_root / relative_path
                if not mirror_path.exists():
                    continue
                self.assertEqual(
                    canonical,
                    mirror_path.read_bytes(),
                    f"Mirror drift detected for {relative_path} under {mirror_root.relative_to(REPO_ROOT)}",
                )

    def test_bundled_release_docs_do_not_reference_removed_local_doc_surfaces(self) -> None:
        bundled_root = REPO_ROOT / "bundled" / "skills" / "vibe"
        readme = (bundled_root / "README.md").read_text(encoding="utf-8")
        readme_zh = (bundled_root / "README.zh.md").read_text(encoding="utf-8")
        licenses = (bundled_root / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
        notice = (bundled_root / "NOTICE").read_text(encoding="utf-8")

        for content in (readme, readme_zh, licenses):
            self.assertNotIn("](./docs/", content)
        self.assertNotIn("](./third_party/", licenses)
        self.assertIn("[NOTICE](./NOTICE)", licenses)
        self.assertIn("config/upstream-lock.json", notice)
        self.assertNotIn("third_party/NOTICE.md", notice)


if __name__ == "__main__":
    unittest.main()
