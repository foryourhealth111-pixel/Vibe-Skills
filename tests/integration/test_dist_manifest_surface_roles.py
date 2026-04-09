from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONFIG_PATH = REPO_ROOT / "config" / "distribution-manifest-sources.json"


@lru_cache(maxsize=1)
def _load_source_config() -> dict:
    return json.loads(SOURCE_CONFIG_PATH.read_text(encoding="utf-8"))


def _lane_manifests() -> list[str]:
    return [item["output_path"] for item in _load_source_config()["lane_manifests"]]


def _public_manifests() -> list[str]:
    return [item["output_path"] for item in _load_source_config()["public_manifests"]]


def _load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _flatten_strings(value: object) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        if value.strip():
            items.append(value)
    elif isinstance(value, list):
        for entry in value:
            items.extend(_flatten_strings(entry))
    elif isinstance(value, dict):
        for entry in value.values():
            items.extend(_flatten_strings(entry))
    return items


def _expected_lane_proof_surfaces(manifest: dict) -> list[str]:
    proof_surfaces: list[str] = []
    proof_surfaces.extend(_flatten_strings(manifest.get("docs") or {}))

    support = manifest.get("support") or {}
    for key in ("platform_support", "host_support"):
        entry = support.get(key) or {}
        truth = entry.get("truth_source")
        if isinstance(truth, str) and truth.strip():
            proof_surfaces.append(truth)

    for promise in manifest.get("capability_promises") or []:
        proof_surfaces.extend(_flatten_strings((promise or {}).get("evidence_paths")))

    return _ordered_unique(proof_surfaces)


def _expected_public_install_surfaces(manifest: dict) -> list[str]:
    install_surfaces: list[str] = []
    for key, value in (manifest.get("install_entrypoints") or {}).items():
        if key in {"host_managed", "notes"}:
            continue
        install_surfaces.extend(_flatten_strings(value))
    return _ordered_unique(install_surfaces)


def _expected_public_payload_surfaces(manifest: dict) -> list[str]:
    payload_surfaces: list[str] = []
    for value in (manifest.get("delivers") or {}).values():
        payload_surfaces.extend(_flatten_strings(value))
    return _ordered_unique(payload_surfaces)


def _registered_adapter_contract_surfaces(adapter: dict) -> list[str]:
    return _ordered_unique(
        [
            value
            for value in (
                adapter.get("host_profile"),
                adapter.get("settings_map"),
                adapter.get("closure"),
            )
            if isinstance(value, str) and value.strip()
        ]
    )


def _registered_public_manifest_path(adapter_id: str) -> str:
    return f"dist/manifests/vibeskills-{adapter_id}.json"


def test_lane_manifests_project_authority_entrypoints_and_boundaries() -> None:
    for relative_path in _lane_manifests():
        manifest = _load_json(relative_path)
        surface_roles = manifest["surface_roles"]

        expected_entrypoints = _ordered_unique(
            [
                value
                for value in (manifest.get("entrypoints") or {}).values()
                if isinstance(value, str) and value.strip()
            ]
        )

        assert surface_roles["notes"]["flat_projection_contract"] is True
        assert surface_roles["notes"]["projection_scope"] == "release_lane_manifest"
        assert surface_roles["runtime_authority"] == manifest["runtime_ownership"]
        assert surface_roles["repo_provided_entrypoints"] == expected_entrypoints
        assert surface_roles["proof_surfaces"] == _expected_lane_proof_surfaces(manifest)
        assert surface_roles["boundary_claims"] == manifest["non_goals"]


def test_release_lane_manifests_prefer_wrapper_and_core_installer_evidence() -> None:
    cases = {
        "dist/host-claude-code/manifest.json": {
            "apps/vgo-cli/src/vgo_cli/commands.py",
            "apps/vgo-cli/src/vgo_cli/core_bridge.py",
            "packages/installer-core/src/vgo_installer/install_runtime.py",
        },
        "dist/host-windsurf/manifest.json": {
            "install.ps1",
            "apps/vgo-cli/src/vgo_cli/commands.py",
            "apps/vgo-cli/src/vgo_cli/core_bridge.py",
            "packages/installer-core/src/vgo_installer/install_runtime.py",
        },
        "dist/host-openclaw/manifest.json": {
            "install.ps1",
            "apps/vgo-cli/src/vgo_cli/commands.py",
            "apps/vgo-cli/src/vgo_cli/core_bridge.py",
            "packages/installer-core/src/vgo_installer/install_runtime.py",
        },
    }
    forbidden = {
        "scripts/install/install_vgo_adapter.py",
        "scripts/install/Install-VgoAdapter.ps1",
    }

    for relative_path, expected in cases.items():
        proof_surfaces = set(_load_json(relative_path)["surface_roles"]["proof_surfaces"])
        assert forbidden.isdisjoint(proof_surfaces), relative_path
        assert expected.issubset(proof_surfaces), relative_path


def test_public_manifests_project_runtime_role_surfaces_and_boundaries() -> None:
    for relative_path in _public_manifests():
        manifest = _load_json(relative_path)
        surface_roles = manifest["surface_roles"]

        expected_host_managed = manifest.get("host_managed_surfaces")
        if expected_host_managed is None:
            expected_host_managed = (manifest.get("install_entrypoints") or {}).get("host_managed") or []

        expected_reference_surfaces: list[str] = []
        entry_manifest = manifest.get("entry_manifest")
        if isinstance(entry_manifest, str) and entry_manifest.strip():
            expected_reference_surfaces.append(entry_manifest)

        assert surface_roles["notes"]["flat_projection_contract"] is True
        assert surface_roles["notes"]["projection_scope"] == "public_distribution_manifest"
        assert surface_roles["runtime_authority"] == {
            "runtime_role": manifest["runtime_role"],
            "status": manifest["status"],
            "host_adapter_ref": manifest.get("host_adapter_ref"),
        }
        assert surface_roles["truth_surfaces"] == manifest["truth_sources"]
        assert surface_roles["repo_provided_install_surfaces"] == _expected_public_install_surfaces(manifest)
        assert surface_roles["repo_provided_payload_surfaces"] == _expected_public_payload_surfaces(manifest)
        assert surface_roles["repo_provided_reference_surfaces"] == expected_reference_surfaces
        assert surface_roles["host_managed_surfaces"] == expected_host_managed
        assert surface_roles["boundary_claims"] == manifest["anti_overclaim"]


def test_release_facing_dist_manifests_do_not_embed_internal_runtime_payload_roles() -> None:
    internal_runtime_keys = {
        "runtime_payload_roles",
        "runtime_config_payload_roles",
        "runtime_core_payload_roles",
        "governance_runtime_roles",
    }

    for relative_path in _lane_manifests() + _public_manifests():
        manifest = _load_json(relative_path)
        assert internal_runtime_keys.isdisjoint(manifest), relative_path


def test_registered_host_release_manifests_carry_adapter_contract_surfaces() -> None:
    registry = _load_json("config/adapter-registry.json")

    for adapter in registry["adapters"]:
        expected_contract_surfaces = set(_registered_adapter_contract_surfaces(adapter))
        lane_manifest = _load_json(adapter["manifest"])
        public_manifest = _load_json(_registered_public_manifest_path(adapter["id"]))

        assert lane_manifest["host_id"] == adapter["id"]
        assert public_manifest["host_adapter_ref"] == adapter["host_profile"]
        assert public_manifest["status"] == adapter["status"]
        assert expected_contract_surfaces.issubset(set(lane_manifest["surface_roles"]["proof_surfaces"]))
        assert expected_contract_surfaces.issubset(set(public_manifest["surface_roles"]["truth_surfaces"]))

        entry_manifest = public_manifest.get("entry_manifest")
        if isinstance(entry_manifest, str) and entry_manifest.strip():
            assert entry_manifest == adapter["manifest"]


def test_generic_public_release_manifest_carries_generic_adapter_contract_surfaces() -> None:
    expected_contract_surfaces = {
        "adapters/generic/host-profile.json",
        "adapters/generic/settings-map.json",
        "adapters/generic/closure.json",
        "config/runtime-core-packaging.json",
    }

    generic_public = _load_json("dist/manifests/vibeskills-generic.json")
    assert generic_public["host_adapter_ref"] == "adapters/generic/host-profile.json"
    assert expected_contract_surfaces.issubset(set(generic_public["surface_roles"]["truth_surfaces"]))


def test_opencode_release_manifests_cover_all_preview_wrapper_surfaces() -> None:
    expected_preview_surfaces = {
        "config/opencode/commands/vibe.md",
        "config/opencode/commands/vibe-implement.md",
        "config/opencode/commands/vibe-review.md",
        "config/opencode/agents/vibe-plan.md",
        "config/opencode/agents/vibe-implement.md",
        "config/opencode/agents/vibe-review.md",
        "config/opencode/opencode.json.example",
    }

    host_manifest = _load_json("dist/host-opencode/manifest.json")
    public_manifest = _load_json("dist/manifests/vibeskills-opencode.json")

    host_proof_surfaces = set(host_manifest["surface_roles"]["proof_surfaces"])
    public_install_surfaces = set(public_manifest["surface_roles"]["repo_provided_install_surfaces"])

    assert expected_preview_surfaces.issubset(host_proof_surfaces)
    assert expected_preview_surfaces.issubset(public_install_surfaces)


def test_claude_release_manifests_carry_concrete_managed_settings_proof_surfaces() -> None:
    expected_truth_surfaces = {
        "config/settings.template.claude.json",
        "adapters/claude-code/host-profile.json",
        "adapters/claude-code/settings-map.json",
        "adapters/claude-code/closure.json",
        "tests/runtime_neutral/test_claude_preview_scaffold.py",
    }

    host_manifest = _load_json("dist/host-claude-code/manifest.json")
    public_manifest = _load_json("dist/manifests/vibeskills-claude-code.json")

    host_proof_surfaces = set(host_manifest["surface_roles"]["proof_surfaces"])
    public_truth_surfaces = set(public_manifest["surface_roles"]["truth_surfaces"])

    assert expected_truth_surfaces.issubset(host_proof_surfaces)
    assert expected_truth_surfaces.issubset(public_truth_surfaces)


def test_codex_release_manifests_carry_codex_specific_contract_surfaces() -> None:
    codex_expected_lane = {
        "config/settings.template.codex.json",
        "config/plugins-manifest.codex.json",
        "mcp/servers.template.json",
        "adapters/codex/host-profile.json",
        "adapters/codex/settings-map.json",
        "adapters/codex/closure.json",
    }
    codex_expected_public = codex_expected_lane | {
        "adapters/codex/platform-windows.json",
        "adapters/codex/platform-linux.json",
        "adapters/codex/platform-macos.json",
    }

    codex_lane = _load_json("dist/host-codex/manifest.json")
    codex_public = _load_json("dist/manifests/vibeskills-codex.json")

    assert codex_expected_lane.issubset(set(codex_lane["surface_roles"]["proof_surfaces"]))
    assert codex_expected_public.issubset(set(codex_public["surface_roles"]["truth_surfaces"]))


def test_codex_command_templates_are_labeled_as_compatibility_shims() -> None:
    for rel in (
        "commands/vibe.md",
        "commands/vibe-what-do-i-want.md",
        "commands/vibe-how-do-we-do.md",
        "commands/vibe-do-it.md",
    ):
        assert "compatibility shim" in _read_text(rel).lower(), rel


def test_vibe_wrapper_skill_templates_declare_canonical_vibe_delegation() -> None:
    for rel in (
        "bundled/skills/vibe-what-do-i-want/SKILL.md",
        "bundled/skills/vibe-how-do-we-do/SKILL.md",
        "bundled/skills/vibe-do-it/SKILL.md",
        "bundled/skills/vibe-upgrade/SKILL.md",
    ):
        text = _read_text(rel).lower()
        assert "canonical `vibe`" in text or "canonical vibe" in text, rel
        assert "only governed runtime authority" in text, rel
