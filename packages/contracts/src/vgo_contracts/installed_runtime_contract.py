from __future__ import annotations

from typing import Any

DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH = "skills/vibe"
DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH = "skills/vibe/.vibeskills/install-receipt.json"
DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE = "scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE = "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE = "scripts/verify/vibe-bom-frontmatter-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE = "scripts/verify/runtime_neutral/freshness_gate.py"
DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT = "scripts/runtime/invoke-vibe-runtime.ps1"
DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION = 1


def default_installed_runtime_config() -> dict[str, Any]:
    return {
        "target_relpath": DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH,
        "receipt_relpath": DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH,
        "post_install_gate": DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE,
        "coherence_gate": DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE,
        "frontmatter_gate": DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE,
        "neutral_freshness_gate": DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE,
        "runtime_entrypoint": DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT,
        "receipt_contract_version": DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION,
        "require_nested_bundled_root": False,
    }


def default_freshness_runtime_config() -> dict[str, Any]:
    return default_installed_runtime_config()


def default_coherence_runtime_config() -> dict[str, Any]:
    return default_installed_runtime_config()


def merge_installed_runtime_config(governance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}
    merged = dict(defaults)
    for key, value in runtime.items():
        if key not in merged or value is None:
            continue
        merged[key] = value
    return merged
