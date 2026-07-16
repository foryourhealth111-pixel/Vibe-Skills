from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "coherence_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_coherence_gate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CoherenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "verify").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "governance").mkdir(parents=True, exist_ok=True)

        governance = {
            "runtime": {
                "installed_runtime": {
                    "target_relpath": "skills/vibe",
                    "receipt_relpath": "skills/vibe/.vibeskills/install-receipt.json",
                    "post_install_gate": "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
                    "coherence_gate": "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
                    "receipt_contract_version": 1,
                }
            }
        }
        (self.root / "config" / "version-governance.json").write_text(
            json.dumps(governance, indent=2) + "\n", encoding="utf-8"
        )
        (self.root / "docs" / "version-packaging-governance.md").write_text(
            "release only governs repo parity\nexecution-context lock\n", encoding="utf-8"
        )
        (self.root / "docs" / "runtime-freshness-install-sop.md").write_text(
            "receipt contract\ndoes not require the installed folder to be a full repository mirror\n", encoding="utf-8"
        )
        (self.root / "install.ps1").write_text(
            "param([string]$SkillsDir = '')\n"
            "vgo_cli.main', 'install', '--repo-root'\n"
            "if ($SkillsDir) { '--skills-dir' }\n",
            encoding="utf-8",
        )
        (self.root / "install.sh").write_text(
            "python -m vgo_cli.main install --repo-root \"${SCRIPT_DIR}\" \"$@\"\n",
            encoding="utf-8",
        )
        (self.root / "check.ps1").write_text(
            "param([string]$SkillsDir = '')\n"
            "vgo_cli.main', 'check', '--repo-root'\n"
            "if ($SkillsDir) { '--skills-dir' }\n",
            encoding="utf-8",
        )
        (self.root / "check.sh").write_text(
            "python -m vgo_cli.main check --repo-root \"${SCRIPT_DIR}\" \"$@\"\n",
            encoding="utf-8",
        )
        (self.root / "update.ps1").write_text(
            "param([string]$SkillsDir = '')\n"
            "vgo_cli.main', 'update', '--repo-root'\n"
            "if ($SkillsDir) { '--skills-dir' }\n",
            encoding="utf-8",
        )
        (self.root / "update.sh").write_text(
            "python -m vgo_cli.main update --repo-root \"${SCRIPT_DIR}\" \"$@\"\n",
            encoding="utf-8",
        )
        (self.root / "uninstall.ps1").write_text(
            "param([string]$SkillsDir = '')\n"
            "vgo_cli.main', 'uninstall', '--repo-root'\n"
            "if ($SkillsDir) { '--skills-dir' }\n",
            encoding="utf-8",
        )
        (self.root / "uninstall.sh").write_text(
            "python -m vgo_cli.main uninstall --repo-root \"${SCRIPT_DIR}\" \"$@\"\n",
            encoding="utf-8",
        )
        (self.root / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1").write_text(
            "$receipt = @{ receipt_version = 1; gate_result = 'PASS' }\n", encoding="utf-8"
        )
        (self.root / "scripts" / "verify" / "vibe-release-install-runtime-coherence-gate.ps1").write_text(
            "Write-Host 'coherence'\n", encoding="utf-8"
        )
        (self.root / "scripts" / "verify" / "vibe-bom-frontmatter-gate.ps1").write_text(
            "Write-Host 'bom'\n", encoding="utf-8"
        )
        (self.root / "scripts" / "governance" / "sync-bundled-vibe.ps1").write_text(
            "Write-Host 'sync'\n", encoding="utf-8"
        )
        self.target_root = self.root / "target"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_missing_receipt_warns_but_contract_passes(self) -> None:
        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual(1, len(artifact["warnings"]))

    def test_bad_receipt_fails_contract(self) -> None:
        receipt_path = self.target_root / "skills" / "vibe" / ".vibeskills" / "install-receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text('{"gate_result":"FAIL","receipt_version":0}\n', encoding="utf-8")

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("FAIL", artifact["gate_result"])

    def test_simplified_wrappers_do_not_need_old_freshness_calls(self) -> None:
        (self.root / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1").write_text(
            "Write-Host 'freshness'\n", encoding="utf-8"
        )

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])


if __name__ == "__main__":
    unittest.main()
