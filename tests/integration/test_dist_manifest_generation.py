from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_TOOL_PATH = REPO_ROOT / "tools" / "build" / "sync_dist_release_manifests.py"
SOURCE_CONFIG_PATH = REPO_ROOT / "config" / "distribution-manifest-sources.json"
ADAPTER_REGISTRY_PATH = REPO_ROOT / "config" / "adapter-registry.json"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_distribution_manifest_source_config_covers_expected_release_outputs() -> None:
    source_config = _load_json(SOURCE_CONFIG_PATH)
    registry = _load_json(ADAPTER_REGISTRY_PATH)

    lane_outputs = {item["output_path"] for item in source_config["lane_manifests"]}
    public_outputs = {item["output_path"] for item in source_config["public_manifests"]}
    output_paths = list(lane_outputs | public_outputs)
    registry_host_profiles = {adapter["host_profile"] for adapter in registry["adapters"]}

    assert len(output_paths) == len(lane_outputs) + len(public_outputs)

    expected_host_lane_outputs = {adapter["manifest"] for adapter in registry["adapters"]}
    actual_host_lane_outputs = {
        item["output_path"]
        for item in source_config["lane_manifests"]
        if isinstance((item.get("payload") or {}).get("host_id"), str)
    }
    assert actual_host_lane_outputs == expected_host_lane_outputs
    assert lane_outputs - actual_host_lane_outputs == {
        "dist/core/manifest.json",
        "dist/official-runtime/manifest.json",
    }

    expected_host_public_outputs = {f"dist/manifests/vibeskills-{adapter['id']}.json" for adapter in registry["adapters"]}
    actual_host_public_outputs = {
        item["output_path"]
        for item in source_config["public_manifests"]
        if ((item.get("payload") or {}).get("host_adapter_ref") in registry_host_profiles)
    }
    assert actual_host_public_outputs == expected_host_public_outputs
    assert public_outputs - actual_host_public_outputs == {
        "dist/manifests/vibeskills-core.json",
        "dist/manifests/vibeskills-generic.json",
    }


def test_distribution_manifest_sync_reproduces_checked_in_release_surfaces(tmp_path) -> None:
    sync_tool = _load_module("dist_manifest_sync", SYNC_TOOL_PATH)

    generated = sync_tool.build_dist_release_manifests(REPO_ROOT)
    for relative_path, payload in generated.items():
        checked_in = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        assert payload == checked_in

    summary = sync_tool.sync_dist_release_manifests(REPO_ROOT, output_root=tmp_path)
    assert summary["generated"] is True
    assert set(summary["generated_outputs"]) == set(generated)

    for relative_path in generated:
        assert (tmp_path / relative_path).exists(), relative_path
