from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.stage_stop import (
    extract_terminal_stage,
    resolve_progressive_stage_stop_source,
    resolve_stage_stop,
    resolve_terminal_stage,
    suggest_stage_stop,
)


def test_suggest_stage_stop_defaults_to_canonical_phase_cleanup() -> None:
    assert suggest_stage_stop("vibe") == "phase_cleanup"
    assert suggest_stage_stop("non-public-entry") == "phase_cleanup"


def test_resolve_stage_stop_prefers_explicit_request() -> None:
    decision = resolve_stage_stop(" xl_plan ", "phase_cleanup", default_source="kernel_suggested")

    assert decision.requested_stage_stop == "xl_plan"
    assert decision.effective_requested_stage_stop == "xl_plan"
    assert decision.stage_stop_source == "requested"


def test_resolve_stage_stop_uses_default_source_when_request_missing() -> None:
    decision = resolve_stage_stop(None, "phase_cleanup", default_source="entry_surface_default")

    assert decision.requested_stage_stop is None
    assert decision.effective_requested_stage_stop == "phase_cleanup"
    assert decision.stage_stop_source == "entry_surface_default"


def test_resolve_progressive_stage_stop_source_distinguishes_adjusted_and_default() -> None:
    assert (
        resolve_progressive_stage_stop_source(
            requested_stage_stop="phase_cleanup",
            effective_requested_stage_stop="requirement_doc",
        )
        == "progressive_adjusted"
    )
    assert (
        resolve_progressive_stage_stop_source(
            requested_stage_stop="xl_plan",
            effective_requested_stage_stop="xl_plan",
        )
        == "requested"
    )
    assert (
        resolve_progressive_stage_stop_source(
            requested_stage_stop=None,
            effective_requested_stage_stop="requirement_doc",
        )
        == "progressive_default"
    )


def test_extract_terminal_stage_supports_known_lineage_shapes() -> None:
    assert extract_terminal_stage({"last_stage_name": "xl_plan"}) == "xl_plan"
    assert extract_terminal_stage({"stages": [{"stage_name": "phase_cleanup"}]}) == "phase_cleanup"
    assert extract_terminal_stage({"entries": [{"stage": "requirement_doc"}]}) == "requirement_doc"


def test_resolve_terminal_stage_falls_back_from_lineage_to_summary_then_default() -> None:
    assert (
        resolve_terminal_stage(
            stage_lineage_payload={},
            summary={"terminal_stage": "xl_plan"},
            fallback_terminal_stage="phase_cleanup",
        )
        == "xl_plan"
    )
    assert (
        resolve_terminal_stage(
            stage_lineage_payload={},
            summary={},
            fallback_terminal_stage="phase_cleanup",
        )
        == "phase_cleanup"
    )
    assert (
        resolve_terminal_stage(
            stage_lineage_payload={},
            summary={},
            fallback_terminal_stage=None,
        )
        == "unknown"
    )
