from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "common" / "runtime_contracts.py"


def test_runtime_contracts_cli_emits_installed_runtime_defaults() -> None:
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "installed-runtime-config", "--mode", "installed"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["target_relpath"] == "skills/vibe"
    assert payload["frontmatter_gate"] == "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    assert payload["neutral_freshness_gate"] == "scripts/verify/runtime_neutral/freshness_gate.py"
    assert payload["runtime_entrypoint"] == "scripts/runtime/invoke-vibe-runtime.ps1"


def test_runtime_contracts_cli_emits_coherence_defaults() -> None:
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "installed-runtime-config", "--mode", "coherence"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["receipt_relpath"] == "skills/vibe/.vibeskills/install-receipt.json"
    assert payload["coherence_gate"] == "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
    assert "required_runtime_markers" not in payload
    assert "shell_degraded_behavior" not in payload
