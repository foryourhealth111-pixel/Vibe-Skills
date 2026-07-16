from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "freshness_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_freshness_gate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FreshnessGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.target_root = Path(self.tempdir.name)
        self.installed_root = self.target_root / "skills" / "vibe"
        self.installed_root.mkdir(parents=True)
        (self.installed_root / "SKILL.md").write_text("# vibe\n", encoding="utf-8")
        runtime_path = self.installed_root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        runtime_path.parent.mkdir(parents=True)
        runtime_path.write_text("Write-Host runtime\n", encoding="utf-8")
        self.receipt_path = self.installed_root / ".vibeskills" / "install-receipt.json"
        self.receipt_path.parent.mkdir(parents=True)
        self.write_receipt()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_receipt(self, *, files: list[dict[str, str]] | None = None) -> None:
        owned = files or [
            {"path": "SKILL.md", "sha256": sha256(self.installed_root / "SKILL.md")},
            {
                "path": "scripts/runtime/invoke-vibe-runtime.ps1",
                "sha256": sha256(self.installed_root / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"),
            },
        ]
        self.receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "receipt_kind": "vibe-skill-install",
                    "skill_id": "vibe",
                    "install_root": str(self.installed_root.resolve()),
                    "files": owned,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def test_receipt_owned_files_and_hashes_pass(self) -> None:
        gate_pass, artifact = self.module.evaluate_freshness(self.target_root, write_artifacts=True)

        self.assertTrue(gate_pass)
        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual(2, artifact["results"]["verified_file_count"])
        self.assertTrue((self.installed_root / "outputs" / "verify" / "installed-runtime-freshness.json").is_file())

    def test_missing_receipt_owned_file_fails(self) -> None:
        (self.installed_root / "SKILL.md").unlink()

        gate_pass, artifact = self.module.evaluate_freshness(self.target_root)

        self.assertFalse(gate_pass)
        self.assertIn("missing receipt-owned file: SKILL.md", artifact["results"]["failures"])

    def test_changed_receipt_owned_file_fails(self) -> None:
        (self.installed_root / "SKILL.md").write_text("changed\n", encoding="utf-8")

        gate_pass, artifact = self.module.evaluate_freshness(self.target_root)

        self.assertFalse(gate_pass)
        self.assertIn("hash mismatch: SKILL.md", artifact["results"]["failures"])

    def test_receipt_path_cannot_escape_the_installed_root(self) -> None:
        outside = self.target_root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        self.write_receipt(files=[{"path": "../../../outside.txt", "sha256": sha256(outside)}])

        gate_pass, artifact = self.module.evaluate_freshness(self.target_root)

        self.assertFalse(gate_pass)
        self.assertIn(
            "receipt path escapes installed runtime: ../../../outside.txt",
            artifact["results"]["failures"],
        )


if __name__ == "__main__":
    unittest.main()
