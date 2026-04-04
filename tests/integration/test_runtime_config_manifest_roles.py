from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCODE_CONFIG_ROOT = REPO_ROOT / "config" / "opencode"


def _load_manifest() -> dict:
    return json.loads((REPO_ROOT / "config" / "runtime-config-manifest.json").read_text(encoding="utf-8"))


def test_runtime_config_manifest_role_groups_cover_flat_projection() -> None:
    manifest = _load_manifest()
    role_groups = manifest["role_groups"]

    file_groups = role_groups["files"]
    grouped_files = []
    for values in file_groups.values():
        grouped_files.extend(values)
    assert set(grouped_files) == set(manifest["files"])
    assert len(grouped_files) == len(set(grouped_files))

    directory_groups = role_groups["directories"]
    grouped_directories = []
    for values in directory_groups.values():
        grouped_directories.extend(values)
    assert set(grouped_directories) == set(manifest["directories"])
    assert len(grouped_directories) == len(set(grouped_directories))


def test_runtime_config_manifest_groups_separate_runtime_domains() -> None:
    manifest = _load_manifest()
    file_groups = manifest["role_groups"]["files"]

    runtime_governance = set(file_groups["runtime_governance_files"])
    router_and_discovery = set(file_groups["router_and_discovery_policy_files"])
    memory = set(file_groups["memory_policy_files"])
    overlay_and_specialist = set(file_groups["overlay_and_specialist_policy_files"])
    distribution_and_lock = set(file_groups["distribution_and_lock_files"])
    opencode_preview = set(file_groups["opencode_preview_files"])

    groups = [
        runtime_governance,
        router_and_discovery,
        memory,
        overlay_and_specialist,
        distribution_and_lock,
        opencode_preview,
    ]
    for index, current in enumerate(groups):
        for other in groups[index + 1 :]:
            assert current.isdisjoint(other)

    assert runtime_governance >= {
        "config/runtime-config-manifest.json",
        "config/runtime-script-manifest.json",
        "config/runtime-contract.json",
        "config/runtime-core-packaging.json",
        "config/version-governance.json",
    }
    assert router_and_discovery >= {
        "config/adapter-registry.json",
        "config/capability-catalog.json",
        "config/router-provider-registry.json",
        "config/router-thresholds.json",
        "config/retrieval-policy.json",
    }
    assert memory == {
        "config/memory-backend-adapters.json",
        "config/memory-governance.json",
        "config/memory-retrieval-budget-policy.json",
        "config/memory-runtime-v3-policy.json",
        "config/memory-stage-activation-policy.json",
        "config/memory-tier-router.json",
    }
    assert distribution_and_lock == {
        "config/plugins-manifest.codex.json",
        "config/settings.template.codex.json",
        "config/skills-lock.json",
        "config/upstream-lock.json",
    }
    assert opencode_preview == {
        path.as_posix().replace(str(REPO_ROOT.as_posix()) + "/", "")
        for path in sorted(OPENCODE_CONFIG_ROOT.rglob("*"))
        if path.is_file()
    }
    assert all(path.startswith("config/") for path in set().union(*groups))


def test_runtime_config_manifest_avoids_broad_directory_projection() -> None:
    manifest = _load_manifest()

    assert manifest["directories"] == []
    assert manifest["role_groups"]["directories"]["managed_runtime_config_roots"] == []
    assert manifest["role_groups"]["directories"]["preview_host_config_roots"] == []
    assert "config/opencode" not in manifest["directories"]
    assert manifest["notes"]["flat_projection_contract"]
    assert manifest["notes"]["explicit_projection_rule"]
    assert manifest["notes"]["semantic_group_rule"]
    assert manifest["notes"]["opencode_projection_rule"]
