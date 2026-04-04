from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_TOOL_PATH = REPO_ROOT / "tools" / "build" / "sync_adapter_registry.py"
SOURCE_CONFIG_PATH = REPO_ROOT / "config" / "adapter-registry.json"
ADAPTER_INDEX_PATH = REPO_ROOT / "adapters" / "index.json"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_adapter_registry_source_matches_checked_in_adapter_index() -> None:
    assert json.loads(SOURCE_CONFIG_PATH.read_text(encoding="utf-8")) == json.loads(ADAPTER_INDEX_PATH.read_text(encoding="utf-8"))


def test_adapter_registry_sync_reproduces_checked_in_index(tmp_path) -> None:
    sync_tool = _load_module("adapter_registry_sync", SYNC_TOOL_PATH)
    payload = sync_tool.build_adapter_registry(REPO_ROOT)
    checked_in = json.loads(ADAPTER_INDEX_PATH.read_text(encoding="utf-8"))
    assert payload == checked_in

    summary = sync_tool.sync_adapter_registry(REPO_ROOT, output_root=tmp_path)
    assert summary["generated"] is True
    generated = json.loads((tmp_path / "adapters" / "index.json").read_text(encoding="utf-8"))
    assert generated == checked_in


def test_claude_host_profile_prefers_cli_and_installer_core_evidence() -> None:
    host_profile = json.loads((REPO_ROOT / "adapters" / "claude-code" / "host-profile.json").read_text(encoding="utf-8"))
    evidence = set(host_profile["source_evidence"])

    assert "scripts/install/install_vgo_adapter.py" not in evidence
    assert "apps/vgo-cli/src/vgo_cli/commands.py" in evidence
    assert "apps/vgo-cli/src/vgo_cli/core_bridge.py" in evidence
    assert "packages/installer-core/src/vgo_installer/install_runtime.py" in evidence
