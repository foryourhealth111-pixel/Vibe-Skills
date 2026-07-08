from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "3.2.0"
EXPECTED_UPDATED = "2026-07-08"
EXPECTED_BASE_COMMIT = "7c6ac63"
EXPECTED_ACTOR = "羽裳"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ReleaseV320SurfaceTests(unittest.TestCase):
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

        changelog_text = (REPO_ROOT / "references/changelog.md").read_text(encoding="utf-8")
        self.assertIn(f"## v{EXPECTED_VERSION} ({EXPECTED_UPDATED})", changelog_text)
        self.assertIn(f"docs/releases/v{EXPECTED_VERSION}.md", changelog_text)

        release_readme_text = (REPO_ROOT / "docs/releases/README.md").read_text(encoding="utf-8")
        self.assertIn(f"[`v{EXPECTED_VERSION}.md`](v{EXPECTED_VERSION}.md)", release_readme_text)

        release_note_text = (REPO_ROOT / "docs/releases" / f"v{EXPECTED_VERSION}.md").read_text(encoding="utf-8")
        self.assertIn(f"# VCO Release v{EXPECTED_VERSION}", release_note_text)
        self.assertIn(f"- Date: {EXPECTED_UPDATED}", release_note_text)
        self.assertIn(f"- Commit(base): {EXPECTED_BASE_COMMIT}", release_note_text)

        ledger_lines = [
            json.loads(line)
            for line in (REPO_ROOT / "references/release-ledger.jsonl").read_text(encoding="utf-8").splitlines()
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

    def test_dist_release_manifests_point_at_v320(self) -> None:
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
