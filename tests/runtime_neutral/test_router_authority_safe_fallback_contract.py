from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_MANIFEST = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
ROUTER_THRESHOLDS = json.loads((REPO_ROOT / "config" / "router-thresholds.json").read_text(encoding="utf-8-sig"))


def test_retired_router_authority_fallback_fields_are_absent() -> None:
    retired_pack_fields = {
        "authority_tier",
        "fallback_owner_pack_id",
        "fallback_owner_skill",
    }

    assert "authority" not in ROUTER_THRESHOLDS
    for pack in PACK_MANIFEST["packs"]:
        assert retired_pack_fields.isdisjoint(pack)


def test_retired_programmatic_selection_thresholds_are_absent() -> None:
    retired_thresholds = {
        "auto_route",
        "confirm_required",
        "fallback_to_legacy_below",
        "min_candidate_signal_for_confirm_override",
        "min_candidate_signal_for_auto_route",
    }

    assert "weights" not in ROUTER_THRESHOLDS
    assert "safety" not in ROUTER_THRESHOLDS
    assert "candidate_selection" not in ROUTER_THRESHOLDS
    assert retired_thresholds.isdisjoint(ROUTER_THRESHOLDS.get("thresholds", {}))
    assert ROUTER_THRESHOLDS["thresholds"] == {
        "candidate_focus": 0.45,
        "min_top1_top2_gap": 0.06,
        "min_candidate_signal_for_near_match": 0.2,
        "min_candidate_signal_for_focus": 0.6,
    }
