from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "installed_runtime_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("installed_runtime_contract_unit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_installed_runtime_contract_uses_the_simple_install_receipt() -> None:
    module = _load_module()
    defaults = module.default_installed_runtime_config()

    assert defaults["target_relpath"] == "skills/vibe"
    assert defaults["receipt_relpath"] == "skills/vibe/.vibeskills/install-receipt.json"
    assert defaults["post_install_gate"] == "scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
    assert defaults["coherence_gate"] == "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
    assert defaults["frontmatter_gate"] == "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    assert defaults["neutral_freshness_gate"] == "scripts/verify/runtime_neutral/freshness_gate.py"
    assert defaults["runtime_entrypoint"] == "scripts/runtime/invoke-vibe-runtime.ps1"
    assert defaults["receipt_contract_version"] == 1
    assert defaults["require_nested_bundled_root"] is False
    assert "required_runtime_markers" not in defaults
    assert "shell_degraded_behavior" not in defaults


def test_merge_installed_runtime_config_does_not_restore_retired_marker_fields() -> None:
    module = _load_module()
    governance = {
        "runtime": {
            "installed_runtime": {
                "post_install_gate": "scripts/verify/custom-gate.ps1",
                "required_runtime_markers": ["retired-marker"],
                "required_runtime_marker_groups": {"retired": ["retired-marker"]},
                "shell_degraded_behavior": "warn_and_skip_authoritative_runtime_gate",
            }
        }
    }

    merged = module.merge_installed_runtime_config(governance, module.default_installed_runtime_config())

    assert merged["post_install_gate"] == "scripts/verify/custom-gate.ps1"
    assert merged["receipt_relpath"] == "skills/vibe/.vibeskills/install-receipt.json"
    assert "required_runtime_markers" not in merged
    assert "required_runtime_marker_groups" not in merged
    assert "shell_degraded_behavior" not in merged
