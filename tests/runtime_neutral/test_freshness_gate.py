from __future__ import annotations

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


class FreshnessGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / ".git").mkdir()
        self.target_root = self.root / "target"
        self.canonical_root = self.root
        self.installed_root = self.target_root / "skills" / "vibe"
        self.script_path = self.root / "scripts" / "verify" / "runtime_neutral" / "freshness_gate.py"
        self.governance = self.make_governance()
        self.write_governance()
        self.seed_tree(self.canonical_root, canonical=True)
        self.seed_tree(self.installed_root, canonical=False)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_governance(self) -> dict:
        return {
            "release": {
                "version": "2.3.36",
                "updated": "2026-03-13",
            },
            "source_of_truth": {
                "canonical_root": ".",
                "bundled_root": "bundled/skills/vibe",
                "nested_bundled_root": "bundled/skills/vibe/bundled/skills/vibe",
            },
            "mirror_topology": {
                "canonical_target_id": "canonical",
                "targets": [
                    {"id": "canonical", "path": ".", "role": "canonical"},
                    {"id": "bundled", "path": "bundled/skills/vibe", "role": "mirror"},
                ],
            },
            "execution_context_policy": {
                "require_outer_git_root": True,
                "fail_if_script_path_is_under_mirror_root": True,
            },
            "packaging": {
                "mirror": {
                    "files": ["SKILL.md", "check.ps1", "check.sh", "install.ps1", "install.sh"],
                    "directories": ["config", "docs", "scripts"],
                },
                "allow_bundled_only": [],
                "normalized_json_ignore_keys": ["updated", "generated_at"],
            },
            "runtime": {
                "installed_runtime": {
                    "target_relpath": "skills/vibe",
                    "receipt_relpath": "skills/vibe/outputs/runtime-freshness-receipt.json",
                    "receipt_contract_version": 1,
                    "required_runtime_markers": [
                        "SKILL.md",
                        "config/version-governance.json",
                        "scripts/router/resolve-pack-route.ps1",
                        "scripts/common/vibe-governance-helpers.ps1",
                    ],
                    "require_nested_bundled_root": False,
                }
            },
        }

    def write_governance(self) -> None:
        path = self.root / "config" / "version-governance.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.governance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def sync_runtime_governance_copies(self) -> None:
        canonical_copy = json.loads(json.dumps(self.governance))
        canonical_copy["generated_at"] = "2026-03-13T00:00:00Z"
        installed_copy = json.loads(json.dumps(self.governance))
        installed_copy["generated_at"] = "2026-03-13T12:00:00Z"
        (self.canonical_root / "config").mkdir(parents=True, exist_ok=True)
        (self.installed_root / "config").mkdir(parents=True, exist_ok=True)
        (self.canonical_root / "config" / "version-governance.json").write_text(
            json.dumps(canonical_copy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.installed_root / "config" / "version-governance.json").write_text(
            json.dumps(installed_copy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def seed_tree(self, root: Path, *, canonical: bool) -> None:
        files = {
            "SKILL.md": "# vibe\n",
            "check.ps1": "Write-Host 'check'\n",
            "check.sh": "echo check\n",
            "install.ps1": "Write-Host 'install'\n",
            "install.sh": "echo install\n",
            "docs/runtime.md": "# runtime\n",
            "scripts/router/resolve-pack-route.ps1": "Write-Host 'route'\n",
            "scripts/common/vibe-governance-helpers.ps1": "Write-Host 'helpers'\n",
        }
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        if canonical:
            self.sync_runtime_governance_copies()

    def evaluate(self, *, write_artifacts: bool = False, write_receipt: bool = False):
        return self.module.evaluate_freshness(
            repo_root=self.root,
            governance=self.governance,
            canonical_root=self.canonical_root,
            target_root=self.target_root,
            script_path=self.script_path,
            write_artifacts=write_artifacts,
            write_receipt=write_receipt,
        )

    def test_freshness_pass_writes_receipt_and_artifacts(self) -> None:
        gate_pass, artifact = self.evaluate(write_artifacts=True, write_receipt=True)
        self.assertTrue(gate_pass)
        self.assertEqual("PASS", artifact["gate_result"])

        receipt_path = self.target_root / "skills" / "vibe" / "outputs" / "runtime-freshness-receipt.json"
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual("PASS", receipt["gate_result"])
        self.assertEqual("2.3.36", receipt["release"]["version"])

        artifact_path = self.root / "outputs" / "verify" / "vibe-installed-runtime-freshness-gate.json"
        self.assertTrue(artifact_path.exists())

    def test_freshness_fail_when_required_file_missing_removes_receipt(self) -> None:
        receipt_path = self.target_root / "skills" / "vibe" / "outputs" / "runtime-freshness-receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text('{"gate_result":"PASS"}\n', encoding="utf-8")
        (self.installed_root / "check.sh").unlink()

        gate_pass, artifact = self.evaluate(write_receipt=True)
        self.assertFalse(gate_pass)
        self.assertEqual("FAIL", artifact["gate_result"])
        self.assertFalse(receipt_path.exists())

    def test_allowlisted_installed_only_file_does_not_fail_directory_parity(self) -> None:
        self.governance["packaging"]["allow_bundled_only"] = ["docs/extra.md"]
        self.write_governance()
        self.sync_runtime_governance_copies()
        extra_path = self.installed_root / "docs" / "extra.md"
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        extra_path.write_text("allowed extra\n", encoding="utf-8")

        gate_pass, _ = self.evaluate()
        self.assertTrue(gate_pass)

    def test_unexpected_installed_only_file_fails_directory_parity(self) -> None:
        extra_path = self.installed_root / "docs" / "unexpected.md"
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        extra_path.write_text("unexpected\n", encoding="utf-8")

        gate_pass, artifact = self.evaluate()
        self.assertFalse(gate_pass)
        docs_entry = next(item for item in artifact["results"]["directories"] if item["path"] == "docs")
        self.assertEqual(["unexpected.md"], docs_entry["only_in_installed"])


if __name__ == "__main__":
    unittest.main()
