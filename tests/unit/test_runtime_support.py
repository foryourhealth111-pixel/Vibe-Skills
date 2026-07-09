from __future__ import annotations

from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
for candidate in (str(RUNTIME_CORE_SRC), str(CONTRACTS_SRC)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from vgo_runtime.runtime_support import resolve_host_id, resolve_target_root


def test_resolve_host_id_uses_registry_aliases_and_defaults_unknown() -> None:
    assert resolve_host_id("claude") == "claude-code"
    assert resolve_host_id("unknown-host") == "codex"


def test_resolve_host_id_reads_environment_when_explicit_host_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VCO_HOST_ID", "opencode")
    assert resolve_host_id(None) == "opencode"


def test_resolve_target_root_uses_shared_registry_projection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shared_root = tmp_path / ".agents"
    monkeypatch.setenv("VIBE_AGENTS_HOME", str(shared_root))
    assert resolve_target_root(None, "windsurf") == shared_root.resolve()
