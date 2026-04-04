from __future__ import annotations

from typing import Any


DEFAULT_INSTALLED_RUNTIME_TARGET_RELPATH = "skills/vibe"
DEFAULT_INSTALLED_RUNTIME_RECEIPT_RELPATH = "skills/vibe/outputs/runtime-freshness-receipt.json"
DEFAULT_INSTALLED_RUNTIME_POST_INSTALL_GATE = "scripts/verify/vibe-installed-runtime-freshness-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_COHERENCE_GATE = "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_FRONTMATTER_GATE = "scripts/verify/vibe-bom-frontmatter-gate.ps1"
DEFAULT_INSTALLED_RUNTIME_NEUTRAL_FRESHNESS_GATE = "scripts/verify/runtime_neutral/freshness_gate.py"
DEFAULT_INSTALLED_RUNTIME_RUNTIME_ENTRYPOINT = "scripts/runtime/invoke-vibe-runtime.ps1"
DEFAULT_INSTALLED_RUNTIME_RECEIPT_CONTRACT_VERSION = 1
DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR = "warn_and_skip_authoritative_runtime_gate"

FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT = (
    "SKILL.md",
    "config/version-governance.json",
    "scripts/router/resolve-pack-route.ps1",
    "scripts/common/vibe-governance-helpers.ps1",
)

COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT = (
    "SKILL.md",
    "config/version-governance.json",
    "install.ps1",
    "check.ps1",
    "scripts/common/vibe-governance-helpers.ps1",
    "scripts/verify/vibe-installed-runtime-freshness-gate.ps1",
    "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1",
    "scripts/runtime/invoke-vibe-runtime.ps1",
    "scripts/router/resolve-pack-route.ps1",
)


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
        "shell_degraded_behavior": DEFAULT_INSTALLED_RUNTIME_SHELL_DEGRADED_BEHAVIOR,
        "required_runtime_markers": list(COHERENCE_REQUIRED_RUNTIME_MARKERS_DEFAULT),
        "require_nested_bundled_root": False,
    }


def default_freshness_runtime_config() -> dict[str, Any]:
    defaults = default_installed_runtime_config()
    defaults["required_runtime_markers"] = list(FRESHNESS_REQUIRED_RUNTIME_MARKERS_DEFAULT)
    return defaults


def default_coherence_runtime_config() -> dict[str, Any]:
    return default_installed_runtime_config()


def merge_installed_runtime_config(governance: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    runtime = ((governance.get("runtime") or {}).get("installed_runtime")) or {}
    merged = dict(defaults)
    for key, value in runtime.items():
        if value is None:
            continue
        merged[key] = value
    if "required_runtime_markers" in defaults:
        merged["required_runtime_markers"] = list(runtime.get("required_runtime_markers") or defaults["required_runtime_markers"])
    return merged
