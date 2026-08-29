from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "4.1.0"
EXPECTED_UPDATED = "2026-08-29"
EXPECTED_BASE_COMMIT = "50f6749"
EXPECTED_ACTOR = "羽裳"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ReleaseV410SurfaceTests(unittest.TestCase):
    def test_authoritative_release_surface_is_aligned(self) -> None:
        governance = load_json(REPO_ROOT / "config/version-governance.json")
        self.assertEqual(governance["release"]["version"], EXPECTED_VERSION)
        self.assertEqual(governance["release"]["updated"], EXPECTED_UPDATED)

        pyproject_paths = [
            REPO_ROOT / "pyproject.toml",
            REPO_ROOT / "apps" / "vgo-cli" / "pyproject.toml",
            REPO_ROOT / "packages" / "adapter-sdk" / "pyproject.toml",
            REPO_ROOT / "packages" / "contracts" / "pyproject.toml",
            REPO_ROOT / "packages" / "installer-core" / "pyproject.toml",
            REPO_ROOT / "packages" / "runtime-core" / "pyproject.toml",
            REPO_ROOT / "packages" / "skill-catalog" / "pyproject.toml",
            REPO_ROOT / "packages" / "verification-core" / "pyproject.toml",
        ]
        for path in pyproject_paths:
            self.assertIn(f'version = "{EXPECTED_VERSION}"', path.read_text(encoding="utf-8"))

        skill_text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(f"- Version: {EXPECTED_VERSION}", skill_text)
        self.assertIn(f"- Updated: {EXPECTED_UPDATED}", skill_text)

        # Release metadata now lives in executable configuration and the
        # append-only ledger. Historical Markdown release surfaces are
        # intentionally absent from the live documentation control plane.
        ledger_path = REPO_ROOT / governance["logs"]["release_ledger_jsonl"]
        self.assertTrue(ledger_path.is_file())
        self.assertFalse((REPO_ROOT / "references/changelog.md").exists())
        self.assertFalse((REPO_ROOT / "docs/releases/README.md").exists())
        self.assertFalse((REPO_ROOT / "docs/releases" / f"v{EXPECTED_VERSION}.md").exists())

        ledger_lines = [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(
            {
                "version": EXPECTED_VERSION,
                "updated": EXPECTED_UPDATED,
                "git_head": EXPECTED_BASE_COMMIT,
                "actor": EXPECTED_ACTOR,
            },
            [
                {
                    "version": entry.get("version"),
                    "updated": entry.get("updated"),
                    "git_head": entry.get("git_head"),
                    "actor": entry.get("actor"),
                }
                for entry in ledger_lines
            ],
        )

    def test_dist_release_manifests_point_at_v410(self) -> None:
        source_config = load_json(REPO_ROOT / "config/distribution-manifest-sources.json")
        manifest_paths = [
            REPO_ROOT / item["output_path"]
            for item in source_config.get("lane_manifests", []) + source_config.get("public_manifests", [])
        ]
        for path in manifest_paths:
            manifest = load_json(path)
            self.assertEqual(manifest["source_release"]["version"], EXPECTED_VERSION, str(path))
            self.assertEqual(manifest["source_release"]["updated"], EXPECTED_UPDATED, str(path))


if __name__ == "__main__":
    unittest.main()
