from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.governance import choose_internal_grade
import vgo_runtime.runtime_bridge as runtime_bridge
from vgo_runtime.task_intent import infer_task_type


COMPOSITE_DATA_DELIVERY_TASK = (
    "请分析并比较社区培训数据，交付数据质量审计、保留原始值的清洗数据、QA 问题表、"
    "可复现脚本、汇总表、PNG 图表、中文 Markdown 报告和验证证据。"
    "请先讲清 L 级和 XL 级方案，再等待选择。"
)


def test_runtime_bridge_prefers_python_owner_before_powershell_bridge(
    monkeypatch,
    capsys,
) -> None:
    recorded: dict[str, object] = {}

    monkeypatch.setattr(runtime_bridge, "resolve_powershell_host", lambda: "pwsh")

    def fake_route_prompt(**kwargs):
        recorded["route_prompt"] = kwargs
        return {"driver": "python-owner"}

    def fail_invoke(*args, **kwargs):
        raise AssertionError("powershell bridge should not own the happy path")

    monkeypatch.setattr(runtime_bridge, "route_prompt", fake_route_prompt)
    monkeypatch.setattr(runtime_bridge, "invoke_canonical_router", fail_invoke)

    exit_code = runtime_bridge.main(["--prompt", "plan this task"])

    assert exit_code == 0
    assert recorded["route_prompt"] == {
        "prompt": "plan this task",
        "grade": "M",
        "task_type": "planning",
        "requested_skill": None,
        "entry_intent_id": None,
        "requested_grade_floor": None,
        "target_root": None,
        "host_id": None,
        "repo_root": ROOT,
    }
    assert json.loads(capsys.readouterr().out) == {"driver": "python-owner"}


def test_runtime_bridge_uses_powershell_only_as_fallback_for_owner_failure(
    monkeypatch,
    capsys,
) -> None:
    recorded = {"route_prompt": 0, "bridge": 0}

    monkeypatch.setattr(runtime_bridge, "resolve_powershell_host", lambda: "pwsh")

    def fail_route_prompt(**kwargs):
        recorded["route_prompt"] += 1
        raise RuntimeError("python owner failed")

    def fake_invoke(args, shell):
        recorded["bridge"] += 1
        assert shell == "pwsh"
        assert args.prompt == "route with fallback"
        return {"driver": "powershell-fallback"}

    monkeypatch.setattr(runtime_bridge, "route_prompt", fail_route_prompt)
    monkeypatch.setattr(runtime_bridge, "invoke_canonical_router", fake_invoke)

    exit_code = runtime_bridge.main(["--prompt", "route with fallback"])

    assert exit_code == 0
    assert recorded == {"route_prompt": 1, "bridge": 1}
    assert json.loads(capsys.readouterr().out) == {"driver": "powershell-fallback"}


def test_docs_cleanup_prompts_stay_small_planning_work() -> None:
    for prompt in ("suffix cleanup in docs", "codex bootstrap wording in docs"):
        assert infer_task_type(prompt) == "planning"
        assert choose_internal_grade("planning", task=prompt) == "M"


def test_router_debug_prompt_resolves_to_debug_at_l() -> None:
    task = "router confidence-low fallback misroute task-classification grade-selection candidate-scoring"

    assert infer_task_type(task) == "debug"
    assert choose_internal_grade("planning", task=task) == "L"


def test_install_rollout_prompt_resolves_to_xl() -> None:
    task = "cross-host install to runtime end-to-end verification workflow"

    assert choose_internal_grade("planning", task=task) == "XL"


@pytest.mark.parametrize(
    "task",
    (
        "这项工作选 L 或 XL？",
        "Should this task use L and XL?",
        "Should this task use L vs XL?",
        "这项工作用 XL 还是 L？",
    ),
)
def test_workflow_choice_questions_stay_at_l(task: str) -> None:
    assert choose_internal_grade("planning", task=task) == "L"


def test_explicit_l_with_xl_non_escalation_stays_at_l() -> None:
    task = "请按 L 级处理，不要升级到 XL"

    assert choose_internal_grade("planning", task=task) == "L"


@pytest.mark.parametrize("task", ("Choose XL", "Choose XL."))
def test_explicit_xl_accepts_terminal_punctuation(task: str) -> None:
    assert choose_internal_grade("planning", task=task) == "XL"


def test_xl_inside_a_path_is_not_a_grade_declaration() -> None:
    task = r"Open D:\work\02-xl-workshops\notes.md"

    assert choose_internal_grade("planning", task=task) == "M"


def test_serial_execution_with_negated_parallelism_is_not_xl() -> None:
    task = "Run serially; do not use parallel or multi-agent execution."

    assert choose_internal_grade("planning", task=task) != "XL"


def test_composite_data_delivery_recommends_xl_without_an_explicit_grade() -> None:
    assert infer_task_type(COMPOSITE_DATA_DELIVERY_TASK) == "research"
    assert choose_internal_grade("research", task=COMPOSITE_DATA_DELIVERY_TASK) == "XL"


@pytest.mark.parametrize(
    "task",
    (
        "Analyze the data, but do not produce script, chart, or report.",
        "Analyze data, but do not generate a script, chart, or report.",
    ),
)
def test_negated_delivery_categories_do_not_make_research_xl(task: str) -> None:
    assert choose_internal_grade("research", task=task) == "L"


def test_delivery_like_file_names_do_not_make_research_xl() -> None:
    task = "Review script.md, chart.png, and report.md references."

    assert choose_internal_grade("research", task=task) == "L"


def test_explicit_xl_candidate_survives_workflow_choice_wording_in_python() -> None:
    task = "请先说明 L 和 XL 的区别；这项工作本身是明确的 XL 候选。"

    assert choose_internal_grade("research", task=task) == "XL"


@pytest.mark.parametrize(
    "task",
    (
        pytest.param("无人值守", id="unattended"),
        pytest.param("install then verify runtime", id="install-runtime"),
        pytest.param("front/back", id="front-back"),
        pytest.param("parallel", id="parallel"),
        pytest.param("wave", id="wave"),
        pytest.param("batch", id="batch"),
        pytest.param("cross-host", id="cross-host"),
        pytest.param("end-to-end", id="end-to-end"),
    ),
)
def test_python_grade_matches_powershell_single_xl_signals(task: str) -> None:
    assert choose_internal_grade("planning", task=task) == "XL"
