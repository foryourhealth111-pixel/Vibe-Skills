from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

from vgo_runtime.runtime_truth import (
    build_runtime_truth_packet,
    build_runtime_truth_packet_from_payload,
    main,
)
import pytest


def test_build_runtime_truth_packet_prefers_work_binding_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={"units": [{"work_unit_id": "wu-1", "bound_skill": "code-review"}]},
        specialist_decision={"approved_skill_ids": ["code-review"]},
    )

    assert payload["stage"] == "runtime_input_freeze"
    assert payload["run_id"] == "run-123"
    assert payload["task"] == "review code"
    assert payload["work_binding"]["units"][0]["bound_skill"] == "code-review"
    assert payload["specialist_decision"]["approved_skill_ids"] == ["code-review"]
    assert payload["skill_routing"] == {
        "schema_version": "simplified_skill_routing_v1",
        "candidates": [],
        "rejected": [],
    }


def test_build_runtime_truth_packet_keeps_extra_fields_without_overriding_python_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={"units": [{"bound_skill": "code-review"}]},
        specialist_decision={"approved_skill_ids": ["code-review"]},
        base_fields={
            "stage": "powershell-owned",
            "run_id": "wrong-run",
            "task": "wrong task",
            "host_id": "codex",
            "work_binding": {"units": []},
            "specialist_decision": {"approved_skill_ids": []},
        },
    )

    assert payload["stage"] == "runtime_input_freeze"
    assert payload["run_id"] == "run-123"
    assert payload["task"] == "review code"
    assert payload["host_id"] == "codex"
    assert payload["work_binding"]["units"][0]["bound_skill"] == "code-review"
    assert payload["specialist_decision"]["approved_skill_ids"] == ["code-review"]
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_omits_selected_and_keeps_routing_projection_fields() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={
            "units": [
                {
                    "work_unit_id": "wu-1",
                    "bound_skill": "code-review",
                    "task_slice": "Review the code path",
                }
            ]
        },
        specialist_decision={"approved_skill_ids": ["code-review"]},
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": [{"skill_id": "code-review"}],
            "selected": [{"skill_id": "wrong-skill"}],
            "rejected": [],
        },
    )

    assert payload["skill_routing"] == {
        "schema_version": "simplified_skill_routing_v1",
        "candidates": [{"skill_id": "code-review"}],
        "rejected": [],
    }
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_preserves_skill_selection_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={"units": []},
        specialist_decision={"approved_skill_ids": []},
        base_fields={
            "skill_selection": {
                "schema_version": "skill_selection_v1",
                "workflow_level": "L",
                "selection_limit": 3,
                "primary_skill_id": "research",
                "candidate_skill_ids": ["research", "humanizer", "paper-writer"],
                "selected_skill_ids": ["research", "humanizer", "paper-writer"],
                "rejected_candidate_skill_ids": [],
            }
        },
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": [{"skill_id": "research"}],
            "selected": [{"skill_id": "wrong-skill"}],
            "rejected": [],
        },
    )

    assert payload["skill_selection"] == {
        "schema_version": "skill_selection_v1",
        "workflow_level": "L",
        "selection_limit": 3,
        "primary_skill_id": "research",
        "candidate_skill_ids": ["research", "humanizer", "paper-writer"],
        "selected_skill_ids": ["research", "humanizer", "paper-writer"],
        "rejected_candidate_skill_ids": [],
    }
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_derives_skill_usage_from_work_results_not_selected_mirrors(tmp_path: Path) -> None:
    artifact_path = tmp_path / "01-review-notes.md"
    artifact_path.write_text("review evidence\n", encoding="utf-8")
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={
            "units": [
                {
                    "work_unit_id": "wu-1",
                    "bound_skill": "code-review",
                }
            ]
        },
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
        specialist_decision={"approved_skill_ids": ["code-review"]},
        base_fields={
            "skill_usage": {
                "used": [{"skill_id": "wrong-skill", "work_unit_id": "wu-1"}],
                "unused": [],
                "evidence": [{"skill_id": "wrong-skill", "artifact": "legacy.md"}],
            },
            "selected_skill_execution": [{"skill_id": "wrong-skill"}],
            "skill_execution_lock": [{"skill_id": "wrong-skill"}],
        },
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": [{"skill_id": "code-review"}],
            "selected": [{"skill_id": "wrong-skill"}],
            "rejected": [],
        },
    )

    assert payload["skill_usage"] == {
        "bound": [{"skill_id": "code-review", "work_unit_id": "wu-1"}],
        "used": [{"skill_id": "code-review", "work_unit_id": "wu-1"}],
        "unused": [],
        "evidence": [
            {
                "skill_id": "code-review",
                "work_unit_id": "wu-1",
                "artifact": str(artifact_path),
                "stage": "plan_execute",
                "impact": "kernel work-unit artifact evidence recorded the skill use",
            }
        ],
    }


def test_build_runtime_truth_packet_marks_selected_skill_unused_without_artifact_evidence() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        work_binding={
            "units": [
                {
                    "work_unit_id": "wu-1",
                    "bound_skill": "code-review",
                }
            ]
        },
        work_results={
            "work_results": [
                {
                    "work_unit_id": "wu-1",
                    "used_skill": "code-review",
                    "artifact_paths": [],
                    "proof_artifact_paths": [],
                }
            ]
        },
        specialist_decision={"approved_skill_ids": ["code-review"]},
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": [{"skill_id": "code-review"}],
            "selected": [{"skill_id": "code-review"}],
            "rejected": [],
        },
    )

    assert payload["skill_usage"] == {
        "bound": [{"skill_id": "code-review", "work_unit_id": "wu-1"}],
        "used": [],
        "unused": [{"skill_id": "code-review", "work_unit_id": "wu-1"}],
        "evidence": [],
    }


def test_build_runtime_truth_packet_rejects_malformed_skill_routing_contract() -> None:
    with pytest.raises(ValueError, match="skill_routing.candidates must be a list"):
        build_runtime_truth_packet(
            run_id="run-123",
            task="review code",
            work_binding={"units": [{"bound_skill": "code-review"}]},
            specialist_decision={"approved_skill_ids": ["code-review"]},
            skill_routing={
                "schema_version": "simplified_skill_routing_v1",
                "candidates": "not-a-list",
                "rejected": [],
            },
        )

    with pytest.raises(ValueError, match="skill_routing.rejected must be a list"):
        build_runtime_truth_packet(
            run_id="run-123",
            task="review code",
            work_binding={"units": [{"bound_skill": "code-review"}]},
            specialist_decision={"approved_skill_ids": ["code-review"]},
            skill_routing={
                "schema_version": "simplified_skill_routing_v1",
                "candidates": [],
                "rejected": "not-a-list",
            },
        )

    with pytest.raises(ValueError, match="skill_routing.schema_version must be a non-empty string when present"):
        build_runtime_truth_packet(
            run_id="run-123",
            task="review code",
            work_binding={"units": [{"bound_skill": "code-review"}]},
            specialist_decision={"approved_skill_ids": ["code-review"]},
            skill_routing={
                "schema_version": "",
                "candidates": [],
                "rejected": [],
            },
        )


def test_build_runtime_truth_packet_from_payload_keeps_python_owned_truth_without_selected() -> None:
    payload = build_runtime_truth_packet_from_payload(
        {
            "run_id": "run-123",
            "task": "review code",
            "work_binding": {
                "units": [
                    {
                        "work_unit_id": "wu-1",
                        "bound_skill": "code-review",
                        "task_slice": "Review the code path",
                    }
                ]
            },
            "specialist_decision": {"approved_skill_ids": ["code-review"]},
            "base_fields": {
                "stage": "powershell-owned",
                "task": "wrong task",
                "host_id": "codex",
                "skill_routing": {"selected": [{"skill_id": "wrong-skill"}]},
            },
            "skill_routing": {
                "schema_version": "simplified_skill_routing_v1",
                "candidates": [{"skill_id": "code-review"}],
                "selected": [{"skill_id": "wrong-skill"}],
                "rejected": [],
            },
        }
    )

    assert payload["stage"] == "runtime_input_freeze"
    assert payload["task"] == "review code"
    assert payload["host_id"] == "codex"
    assert payload["skill_routing"] == {
        "schema_version": "simplified_skill_routing_v1",
        "candidates": [{"skill_id": "code-review"}],
        "rejected": [],
    }
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_from_payload_rejects_malformed_inputs() -> None:
    valid_payload = {
        "run_id": "run-123",
        "task": "review code",
        "work_binding": {"units": [{"bound_skill": "code-review"}]},
        "specialist_decision": {"approved_skill_ids": ["code-review"]},
    }
    cases = [
        (None, "runtime truth build payload must be an object"),
        ({**valid_payload, "run_id": ""}, "runtime truth build payload missing run_id"),
        ({**valid_payload, "task": ""}, "runtime truth build payload missing task"),
        ({**valid_payload, "work_binding": []}, "runtime truth build payload missing work_binding"),
        (
            {**valid_payload, "specialist_decision": []},
            "runtime truth build payload missing specialist_decision",
        ),
        ({**valid_payload, "work_results": []}, "work_results must be an object when present"),
        ({**valid_payload, "base_fields": []}, "base_fields must be an object when present"),
        ({**valid_payload, "skill_routing": []}, "skill_routing must be an object when present"),
    ]

    for payload, message in cases:
        with pytest.raises(ValueError, match=message):
            build_runtime_truth_packet_from_payload(payload)


def test_runtime_truth_main_writes_handoff_file_and_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_path = tmp_path / "runtime-truth-input.json"
    output_path = tmp_path / "runtime-truth-output.json"
    input_path.write_text(
        json.dumps(
            {
                "run_id": "run-123",
                "task": "review code",
                "work_binding": {"units": [{"bound_skill": "code-review"}]},
                "specialist_decision": {"approved_skill_ids": ["code-review"]},
                "base_fields": {"host_id": "codex"},
                "skill_routing": {
                    "schema_version": "simplified_skill_routing_v1",
                    "candidates": [{"skill_id": "code-review"}],
                    "selected": [{"skill_id": "wrong-skill"}],
                    "rejected": [],
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input-json-path",
            str(input_path),
            "--output-json-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    stdout = capsys.readouterr().out
    output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_payload["host_id"] == "codex"
    assert output_payload["skill_routing"] == {
        "schema_version": "simplified_skill_routing_v1",
        "candidates": [{"skill_id": "code-review"}],
        "rejected": [],
    }
    assert "selected" not in output_payload["skill_routing"]
    stdout_payload = json.loads(stdout)
    assert stdout_payload == output_payload
