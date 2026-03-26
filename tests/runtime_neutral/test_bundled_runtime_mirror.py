from __future__ import annotations

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
    Path("scripts/common/vibe-governance-helpers.ps1"),
    Path("scripts/common/resolve_vgo_adapter.py"),
]


class BundledRuntimeMirrorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
