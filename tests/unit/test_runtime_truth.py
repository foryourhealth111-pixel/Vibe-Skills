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


def test_build_runtime_truth_packet_prefers_module_assignments_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        module_assignments={"units": [{"work_unit_id": "wu-1", "bound_skill": "code-review"}]},
    )

    assert payload["stage"] == "runtime_input_freeze"
    assert payload["run_id"] == "run-123"
    assert payload["task"] == "review code"
    assert payload["module_assignments"]["units"][0]["bound_skill"] == "code-review"
    assert "specialist_decision" not in payload
    assert "specialist_user_disclosure" not in payload
    assert payload["skill_routing"] == {
        "schema_version": "simplified_skill_routing_v1",
        "candidates": [],
        "rejected": [],
    }


def test_build_runtime_truth_packet_keeps_extra_fields_without_overriding_python_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        module_assignments={"units": [{"bound_skill": "code-review"}]},
        base_fields={
            "stage": "powershell-owned",
            "run_id": "wrong-run",
            "task": "wrong task",
            "host_id": "codex",
            "module_assignments": {"units": []},
        },
    )

    assert payload["stage"] == "runtime_input_freeze"
    assert payload["run_id"] == "run-123"
    assert payload["task"] == "review code"
    assert payload["host_id"] == "codex"
    assert payload["module_assignments"]["units"][0]["bound_skill"] == "code-review"
    assert "specialist_decision" not in payload
    assert "specialist_user_disclosure" not in payload
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_omits_selected_and_keeps_routing_projection_fields() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        module_assignments={
            "units": [
                {
                    "work_unit_id": "wu-1",
                    "bound_skill": "code-review",
                    "task_slice": "Review the code path",
                }
            ]
        },
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


def test_build_runtime_truth_packet_preserves_skill_search_guide_truth() -> None:
    payload = build_runtime_truth_packet(
        run_id="run-123",
        task="review code",
        module_assignments={"units": []},
        base_fields={
            "skill_search_guide": {
                "schema_version": "skill_search_guide_v1",
                "skill_roots": [{"kind": "host_local", "path": "C:/Users/demo/.agents/skills"}],
                "search_protocol": ["先拆任务，再拆模块", "每个模块单独搜索本地 skills"],
                "selection_rules": ["优先选真 owner，不选只沾边的 helper"],
                "disclosure_rules": ["requirement 阶段只公开搜索办法，不公开程序候选排名或预选结果"],
                "workflow_level_contract": {"levels": ["L", "XL"]},
            },
            "skill_selection": {
                "schema_version": "skill_selection_v1",
                "selected_skill_ids": ["wrong-skill"],
            },
        },
        skill_routing={
            "schema_version": "simplified_skill_routing_v1",
            "candidates": [{"skill_id": "research"}],
            "selected": [{"skill_id": "wrong-skill"}],
            "rejected": [],
        },
    )

    assert payload["skill_search_guide"] == {
        "schema_version": "skill_search_guide_v1",
        "skill_roots": [{"kind": "host_local", "path": "C:/Users/demo/.agents/skills"}],
        "search_protocol": ["先拆任务，再拆模块", "每个模块单独搜索本地 skills"],
        "selection_rules": ["优先选真 owner，不选只沾边的 helper"],
        "disclosure_rules": ["requirement 阶段只公开搜索办法，不公开程序候选排名或预选结果"],
        "workflow_level_contract": {"levels": ["L", "XL"]},
    }
    assert "skill_selection" not in payload
    assert "selected" not in payload["skill_routing"]


def test_build_runtime_truth_packet_rejects_malformed_skill_routing_contract() -> None:
    with pytest.raises(ValueError, match="skill_routing.candidates must be a list"):
        build_runtime_truth_packet(
            run_id="run-123",
            task="review code",
            module_assignments={"units": [{"bound_skill": "code-review"}]},
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
            module_assignments={"units": [{"bound_skill": "code-review"}]},
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
            module_assignments={"units": [{"bound_skill": "code-review"}]},
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
            "module_assignments": {
                "units": [
                    {
                        "work_unit_id": "wu-1",
                        "bound_skill": "code-review",
                        "task_slice": "Review the code path",
                    }
                ]
            },
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
        "module_assignments": {"units": [{"bound_skill": "code-review"}]},
    }
    cases = [
        (None, "runtime truth build payload must be an object"),
        ({**valid_payload, "run_id": ""}, "runtime truth build payload missing run_id"),
        ({**valid_payload, "task": ""}, "runtime truth build payload missing task"),
        ({**valid_payload, "module_assignments": []}, "runtime truth build payload missing module_assignments"),
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
                "module_assignments": {"units": [{"bound_skill": "code-review"}]},
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
