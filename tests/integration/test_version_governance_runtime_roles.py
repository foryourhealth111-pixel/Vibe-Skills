from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "contracts" / "src" / "vgo_contracts" / "governance_runtime_roles.py"


def _load_governance() -> dict:
    return json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))


def _load_contract_module():
    spec = importlib.util.spec_from_file_location("governance_runtime_roles_integration", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _flatten(groups: dict[str, list[str]]) -> list[str]:
    items: list[str] = []
    for values in groups.values():
        items.extend(values)
    return items


def test_runtime_payload_roles_cover_runtime_payload_projection() -> None:
    governance = _load_governance()
    contracts = _load_contract_module()
    runtime_payload = governance["packaging"]["runtime_payload"]
    role_groups = governance["packaging"]["runtime_payload_roles"]

    grouped_files = _flatten(role_groups["files"])
    grouped_directories = _flatten(role_groups["directories"])

    assert role_groups == contracts.derive_runtime_payload_roles(runtime_payload)
    assert set(grouped_files) == set(runtime_payload["files"])
    assert len(grouped_files) == len(set(grouped_files))
    assert set(grouped_directories) == set(runtime_payload["directories"])
    assert len(grouped_directories) == len(set(grouped_directories))
    assert role_groups["notes"]["flat_projection_contract"]


def test_required_runtime_marker_groups_cover_flat_marker_projection() -> None:
    governance = _load_governance()
    contracts = _load_contract_module()
    runtime = governance["runtime"]["installed_runtime"]

    groups = runtime["required_runtime_marker_groups"]
    grouped_markers = _flatten(groups)
    projection = contracts.derive_required_runtime_marker_projection(runtime["required_runtime_markers"])

    assert groups == projection["required_runtime_marker_groups"]
    assert runtime["required_runtime_marker_notes"] == projection["required_runtime_marker_notes"]
    assert set(grouped_markers) == set(runtime["required_runtime_markers"])
    assert len(grouped_markers) == len(set(grouped_markers))
    assert runtime["required_runtime_marker_notes"]["flat_projection_contract"]


def test_required_runtime_marker_groups_keep_owners_separate_from_compatibility() -> None:
    governance = _load_governance()
    groups = governance["runtime"]["installed_runtime"]["required_runtime_marker_groups"]

    semantic_owners = set(groups["semantic_owners"])
    runtime_support = set(groups["runtime_entrypoints_and_support"])
    verification_surfaces = set(groups["verification_surfaces"])
    router_and_compat = set(groups["router_and_compatibility_surfaces"])

    assert semantic_owners.isdisjoint(runtime_support)
    assert semantic_owners.isdisjoint(verification_surfaces)
    assert semantic_owners.isdisjoint(router_and_compat)

    assert "apps/vgo-cli/src/vgo_cli/main.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/errors.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/hosts.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/process.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/install_support.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/workspace.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/commands.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/repo.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/external.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/output.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/install_gates.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/installer_bridge.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/skill_surface.py" in semantic_owners
    assert "apps/vgo-cli/src/vgo_cli/core_bridge.py" in semantic_owners
    assert "packages/installer-core/src/vgo_installer/install_runtime.py" in semantic_owners
    assert "packages/runtime-core/src/vgo_runtime/router_bridge.py" in semantic_owners

    assert "scripts/runtime/Invoke-SkeletonCheck.ps1" in runtime_support
    assert "scripts/runtime/Invoke-DeepInterview.ps1" in runtime_support
    assert "scripts/runtime/Write-RequirementDoc.ps1" in runtime_support
    assert "scripts/runtime/Write-XlPlan.ps1" in runtime_support
    assert "scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1" in runtime_support
    assert "scripts/runtime/Invoke-DelegatedLaneUnit.ps1" in runtime_support
    assert "scripts/runtime/Invoke-PhaseCleanup.ps1" in runtime_support
    assert "scripts/runtime/VibeExecution.Common.ps1" in runtime_support
    assert "scripts/runtime/VibeMemoryActivation.Common.ps1" in runtime_support

    assert "scripts/router/invoke-pack-route.py" in router_and_compat
    assert "scripts/router/runtime_neutral/router_contract.py" in router_and_compat
    assert "scripts/verify/runtime_neutral/router_bridge_gate.py" in router_and_compat
    assert "scripts/verify/vibe-installed-runtime-freshness-gate.ps1" in verification_surfaces
    assert "scripts/verify/vibe-release-install-runtime-coherence-gate.ps1" in verification_surfaces

    assert all(path.startswith(("apps/", "packages/")) for path in semantic_owners)


def test_required_runtime_markers_include_discoverable_entry_contract() -> None:
    governance = _load_governance()
    runtime = governance["runtime"]["installed_runtime"]
    manifest = json.loads((REPO_ROOT / "config" / "runtime-config-manifest.json").read_text(encoding="utf-8"))

    assert "config/vibe-entry-surfaces.json" in runtime["required_runtime_markers"]
    assert "config/vibe-entry-surfaces.json" in runtime["required_runtime_marker_groups"]["governance_and_manifests"]
    assert "config/vibe-entry-surfaces.json" in manifest["files"]


def test_source_of_truth_declares_explicit_official_self_repo_metadata() -> None:
    governance = _load_governance()
    source_of_truth = governance["source_of_truth"]
    official_repo = source_of_truth["official_self_repo"]

    assert source_of_truth["canonical_root"] == "."
    assert official_repo == {
        "repo_url": "https://github.com/foryourhealth111-pixel/Vibe-Skills.git",
        "default_branch": "main",
        "canonical_root": ".",
    }
