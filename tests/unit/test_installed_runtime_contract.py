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


def test_installed_runtime_contract_owns_freshness_defaults() -> None:
    module = _load_module()
    defaults = module.default_freshness_runtime_config()

    assert defaults["target_relpath"] == "skills/vibe"
    assert defaults["receipt_relpath"] == "skills/vibe/outputs/runtime-freshness-receipt.json"
    assert defaults["post_install_gate"] == "scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
    assert defaults["frontmatter_gate"] == "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    assert defaults["runtime_entrypoint"] == "scripts/runtime/invoke-vibe-runtime.ps1"
    assert defaults["required_runtime_markers"] == [
        "SKILL.md",
        "config/version-governance.json",
        "scripts/router/resolve-pack-route.ps1",
        "scripts/common/vibe-governance-helpers.ps1",
    ]
    assert defaults["require_nested_bundled_root"] is False
    assert defaults["receipt_contract_version"] == 1


def test_installed_runtime_contract_owns_coherence_defaults_with_fresh_lists_copied() -> None:
    module = _load_module()
    defaults = module.default_coherence_runtime_config()
    defaults["required_runtime_markers"].append("local-only")

    fresh = module.default_coherence_runtime_config()
    assert fresh["coherence_gate"] == "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
    assert fresh["frontmatter_gate"] == "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    assert fresh["runtime_entrypoint"] == "scripts/runtime/invoke-vibe-runtime.ps1"
    assert fresh["shell_degraded_behavior"] == "warn_and_skip_authoritative_runtime_gate"
    assert "scripts/verify/vibe-installed-runtime-freshness-gate.ps1" in fresh["required_runtime_markers"]
    assert "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1" in fresh["required_runtime_markers"]
    assert "scripts/runtime/invoke-vibe-runtime.ps1" in fresh["required_runtime_markers"]
    assert "local-only" not in fresh["required_runtime_markers"]


def test_merge_installed_runtime_config_overrides_scalar_fields_and_copies_marker_lists() -> None:
    module = _load_module()
    governance = {
        "runtime": {
            "installed_runtime": {
                "post_install_gate": "scripts/verify/custom-gate.ps1",
                "required_runtime_markers": ["custom-marker"],
            }
        }
    }

    merged = module.merge_installed_runtime_config(governance, module.default_installed_runtime_config())

    assert merged["post_install_gate"] == "scripts/verify/custom-gate.ps1"
    assert merged["frontmatter_gate"] == "scripts/verify/vibe-bom-frontmatter-gate.ps1"
    assert merged["runtime_entrypoint"] == "scripts/runtime/invoke-vibe-runtime.ps1"
    assert merged["required_runtime_markers"] == ["custom-marker"]
