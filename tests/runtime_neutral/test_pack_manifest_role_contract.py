from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_router_does_not_rely_on_pack_manifest_as_live_control_plane() -> None:
    runtime = (
        REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "router_contract_runtime.py"
    ).read_text(encoding="utf-8")
    architecture = (REPO_ROOT / "docs" / "architecture" / "local-agent-kernel-v2.md").read_text(encoding="utf-8")

    assert "pack-manifest.json" not in runtime
    assert "no central pack manifest for ordinary skill registration" in architecture


def test_pack_routing_smoke_labels_pack_manifest_as_compatibility_input() -> None:
    content = (REPO_ROOT / "scripts" / "verify" / "vibe-pack-routing-smoke.ps1").read_text(encoding="utf-8")

    assert "VCO Pack Compatibility Config Checks" in content
    assert "VCO Pack Router Config Checks" not in content
    assert "pack-manifest.json compatibility config exists" in content


def test_pack_routing_smoke_does_not_require_retired_live_keyword_configs() -> None:
    content = (REPO_ROOT / "scripts" / "verify" / "vibe-pack-routing-smoke.ps1").read_text(encoding="utf-8")

    assert "skill-keyword-index.json exists" not in content
    assert "skill-routing-rules.json exists" not in content


def test_pack_routing_smoke_does_not_enforce_retired_programmatic_selection_thresholds() -> None:
    content = (REPO_ROOT / "scripts" / "verify" / "vibe-pack-routing-smoke.ps1").read_text(encoding="utf-8")

    assert "fallback_to_legacy_below" not in content
    assert "enforce_confirm_on_legacy_fallback" not in content
    assert "candidate_selection." not in content
