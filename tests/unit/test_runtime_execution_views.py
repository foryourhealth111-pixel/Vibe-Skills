from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = ROOT / "packages" / "contracts" / "src"
for src in (RUNTIME_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.runtime_packet import RuntimePacket
from vgo_runtime.execution import execute_runtime_packet
from vgo_runtime.execution import build_runtime_route_view
from vgo_runtime.router import RuntimeRoute
from vgo_runtime.runtime_summary import build_runtime_summary


def test_build_runtime_route_view_preserves_canonical_router_selection_for_entry_intent_only() -> None:
    route = RuntimeRoute(
        requested_skill="vibe",
        router_selected_skill="vibe",
        runtime_selected_skill="vibe",
        task_type="planning",
    )
    packet = RuntimePacket(
        goal="plan the migration",
        stage="skeleton_check",
        entry_intent_id="vibe",
        requested_stage_stop="xl_plan",
    )

    payload = build_runtime_route_view(route, packet=packet, requested_skill=None)

    assert payload["requested_skill"] == "vibe"
    assert payload["router_selected_skill"] == "vibe"


def test_execute_runtime_packet_plan_view_does_not_repeat_kernel_payload() -> None:
    result = execute_runtime_packet(
        RuntimePacket(
            goal="design the architecture and write an implementation plan",
            stage="requirement_doc",
            requested_stage_stop="xl_plan",
        )
    )

    assert "kernel" not in result.plan


def test_runtime_summary_prefers_kernel_skill_usage_over_route_era_mirrors(tmp_path: Path) -> None:
    artifact_path = tmp_path / "01-review-notes.md"
    artifact_path.write_text("review evidence\n", encoding="utf-8")
    summary = build_runtime_summary(
        run_id="run-123",
        task="review code",
        artifacts={"runtime_input_packet": "runtime-input-packet.json"},
        work_binding={"units": [{"work_unit_id": "wu-1", "bound_skill": "code-review"}]},
        work_results={
            "work_results": [
                {
                    "work_unit_id": "wu-1",
                    "used_skill": "code-review",
                    "artifact_paths": [str(artifact_path)],
                    "proof_artifact_paths": [],
                }
            ]
        },
        base_fields={
            "skill_usage": {
                "used": [{"skill_id": "wrong-skill", "work_unit_id": "wu-1"}],
                "unused": [],
                "evidence": [{"skill_id": "wrong-skill", "artifact": "legacy.md"}],
            },
            "selected_skill_execution": [{"skill_id": "wrong-skill"}],
            "skill_execution_lock": [{"skill_id": "wrong-skill"}],
        },
    )

    assert summary["bound_skill_ids"] == ["code-review"]
    assert summary["used_skill_ids"] == ["code-review"]
    assert summary["skill_usage"]["bound"] == [{"skill_id": "code-review", "work_unit_id": "wu-1"}]
    assert summary["skill_usage"]["used"] == [{"skill_id": "code-review", "work_unit_id": "wu-1"}]
    assert summary["skill_usage"]["unused"] == []
