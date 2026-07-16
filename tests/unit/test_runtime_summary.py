from __future__ import annotations

from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

from vgo_runtime.runtime_summary import (
    build_runtime_summary,
    build_runtime_summary_from_payload,
    refresh_runtime_summary_acceptance,
)


def test_build_runtime_summary_reports_artifact_paths_and_truth_owner() -> None:
    summary = build_runtime_summary(
        run_id="run-123",
        task="review code",
        artifacts={"runtime_input_packet": "runtime-input-packet.json"},
        module_assignments={"units": [{"bound_skill": "code-review"}]},
    )

    assert summary["run_id"] == "run-123"
    assert summary["task"] == "review code"
    assert summary["truth_owner"] == "python"
    assert summary["artifacts"]["runtime_input_packet"] == "runtime-input-packet.json"
    assert summary["bound_skill_ids"] == ["code-review"]
    assert "skill_usage" not in summary
    assert "used_skill_ids" not in summary


def test_build_runtime_summary_reports_completed_module_work_without_a_skill_ledger() -> None:
    summary = build_runtime_summary(
        run_id="run-123",
        task="review code",
        artifacts={"runtime_input_packet": "runtime-input-packet.json"},
        module_assignments={"units": [{"bound_skill": "code-review"}]},
        module_execution={
            "units": [
                {
                    "unit_id": "wu-1",
                    "module_id": "review",
                    "skill_id": "code-review",
                    "state": "completed",
                },
                {
                    "unit_id": "wu-2",
                    "module_id": "write",
                    "skill_id": "humanizer",
                    "state": "working",
                },
            ]
        },
    )

    assert summary["completed_module_work"] == [
        {"skill_id": "code-review", "unit_id": "wu-1", "module_id": "review"}
    ]
    assert "skill_usage" not in summary
    assert "used_skill_ids" not in summary


def test_build_runtime_summary_preserves_base_fields() -> None:
    summary = build_runtime_summary(
        run_id="run-123",
        task="review code",
        artifacts={"runtime_input_packet": "runtime-input-packet.json"},
        module_assignments={"units": [{"bound_skill": "code-review"}]},
        base_fields={"mode": "interactive_governed", "terminal_stage": "phase_cleanup"},
    )

    assert summary["mode"] == "interactive_governed"
    assert summary["terminal_stage"] == "phase_cleanup"


def test_build_runtime_summary_rejects_malformed_artifacts_contract() -> None:
    with pytest.raises(ValueError, match="artifacts must be an object"):
        build_runtime_summary(
            run_id="run-123",
            task="review code",
            artifacts=[],
            module_assignments={"units": []},
        )


def test_build_runtime_summary_rejects_non_string_artifact_value() -> None:
    with pytest.raises(ValueError, match="artifacts.runtime_input_packet must be a string or null"):
        build_runtime_summary(
            run_id="run-123",
            task="review code",
            artifacts={"runtime_input_packet": 123},
            module_assignments={"units": []},
        )


def test_build_runtime_summary_removes_retired_specialist_fields() -> None:
    summary = build_runtime_summary(
        run_id="run-123",
        task="review code",
        artifacts={"runtime_input_packet": "runtime-input-packet.json"},
        module_assignments={"units": []},
        mode="interactive_governed",
        artifact_root="outputs/runtime",
        session_root="outputs/runtime/vibe-sessions/run-123",
        hierarchy_state={"governance_scope": "root"},
    )

    assert "specialist_decision" not in summary
    assert "specialist_user_disclosure" not in summary


def test_runtime_summary_cannot_claim_completion_before_cleanup_is_admitted(
    tmp_path: Path,
) -> None:
    cleanup_receipt_path = tmp_path / "cleanup-receipt.json"
    cleanup_receipt_path.write_text(
        '{"cleanup_admitted": false, "cleanup_result": {"performed": false, "reason": "delivery_acceptance_not_passed"}}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cleanup receipt has not admitted cleanup"):
        refresh_runtime_summary_acceptance(
            {
                "run_id": "run-123",
                "task": "refresh acceptance",
                "artifacts": {},
            },
            {
                "summary": {
                    "gate_result": "PASS",
                    "completion_language_allowed": True,
                    "runtime_status": "completed",
                    "readiness_state": "fully_ready",
                    "manual_review_layer_count": 0,
                    "failing_layer_count": 0,
                }
            },
            cleanup_receipt_path=str(cleanup_receipt_path),
            delivery_acceptance_report_path=str(tmp_path / "delivery-acceptance-report.json"),
        )
