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
                    "receipt_relpath": "skills/vibe/outputs/runtime-freshness-receipt.json",
                    "post_install_gate": "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
                    "coherence_gate": "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
                    "receipt_contract_version": 1,
                    "shell_degraded_behavior": "warn_and_skip_authoritative_runtime_gate",
                    "required_runtime_markers": [
                        "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
                        "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
                    ],
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
            "receipt contract\nshell degraded behavior\n", encoding="utf-8"
        )
        (self.root / "install.ps1").write_text("Invoke-InstalledRuntimeFreshnessGate\n", encoding="utf-8")
        (self.root / "install.sh").write_text("run_runtime_freshness_gate\n", encoding="utf-8")
        (self.root / "check.ps1").write_text(
            "Invoke-RuntimeFreshnessCheck\nInvoke-RuntimeCoherenceCheck\n", encoding="utf-8"
        )
        (self.root / "check.sh").write_text(
            "run_runtime_freshness_gate\nrun_runtime_coherence_gate\nruntime-neutral\n", encoding="utf-8"
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
        verify_pkg = self.root / "packages" / "verification-core" / "src" / "vgo_verify"
        verify_pkg.mkdir(parents=True, exist_ok=True)
        (verify_pkg / "runtime_freshness.py").write_text(
            "from .runtime_freshness_support import write_freshness_receipt\n", encoding="utf-8"
        )
        (verify_pkg / "runtime_freshness_support.py").write_text(
            "def write_freshness_receipt():\n    return {\"receipt_version\": 1, \"gate_result\": \"PASS\"}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_missing_receipt_warns_but_contract_passes(self) -> None:
        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])
        self.assertEqual(1, len(artifact["warnings"]))

    def test_bad_receipt_fails_contract(self) -> None:
        receipt_path = self.target_root / "skills" / "vibe" / "outputs" / "runtime-freshness-receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text('{"gate_result":"FAIL","receipt_version":0}\n', encoding="utf-8")

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("FAIL", artifact["gate_result"])

    def test_split_freshness_gate_contract_can_live_in_support_module(self) -> None:
        (self.root / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1").write_text(
            "Write-Host 'freshness'\n", encoding="utf-8"
        )

        artifact = self.module.evaluate(self.root, self.target_root)
        self.assertEqual("PASS", artifact["gate_result"])


if __name__ == "__main__":
    unittest.main()
