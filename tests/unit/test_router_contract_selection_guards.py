from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router_contract_selection import get_pack_skill_candidates, select_pack_candidate


def _selection(prompt: str, *, requested: str | None = None) -> dict[str, object]:
    return select_pack_candidate(
        prompt_lower=prompt.casefold(),
        candidates=["subagent-driven-development"],
        task_type="coding",
        requested_canonical=requested,
        skill_keyword_index={
            "selection": {
                "weights": {"keyword_match": 0.8, "name_match": 0.2},
                "fallback_to_first_when_score_below": 0.2,
            },
            "skills": {
                "subagent-driven-development": {
                    "keywords": ["subagent", "子代理", "并行执行", "multi-agent"]
                }
            },
        },
        routing_rules={
            "skills": {
                "subagent-driven-development": {
                    "task_allow": ["planning", "coding", "review", "debug", "research"],
                    "positive_keywords": [
                        "subagent",
                        "parallel agents",
                        "multi-agent",
                        "子代理",
                        "多代理",
                        "并行执行",
                        "拆成多个代理",
                    ],
                    "negative_keywords": [],
                    "canonical_for_task": [],
                    "requires_positive_keyword_match": True,
                }
            }
        },
        pack={
            "id": "synthetic-process-pack",
            "skill_candidates": ["subagent-driven-development"],
            "defaults_by_task": {},
        },
        candidate_selection_config={
            "rule_positive_keyword_bonus": 0.2,
            "rule_negative_keyword_penalty": 0.25,
            "canonical_for_task_bonus": 0.12,
        },
    )


def test_guarded_subagent_does_not_win_generic_coding_fallback() -> None:
    selection = _selection("实现这个功能并修改代码")

    assert selection["selected"] is None
    assert selection["reason"] == "no_usable_candidate"
    assert selection["route_authority_eligible"] is False


def test_guarded_subagent_can_win_with_explicit_positive_keyword() -> None:
    selection = _selection("请用子代理并行执行这个代码修改")

    assert selection["selected"] == "subagent-driven-development"
    assert selection["reason"] == "keyword_ranked"
    assert selection["route_authority_eligible"] is True


def test_requested_subagent_bypasses_guard() -> None:
    selection = _selection("实现这个功能并修改代码", requested="subagent-driven-development")

    assert selection["selected"] == "subagent-driven-development"
    assert selection["reason"] == "requested_skill"


def test_pack_skill_candidates_prefer_unified_field_over_legacy_roles() -> None:
    pack = {
        "skill_candidates": ["primary", "assistant"],
        "route_authority_candidates": ["legacy-only-primary"],
        "stage_assistant_candidates": ["legacy-only-assistant"],
    }

    assert get_pack_skill_candidates(pack) == ["primary", "assistant"]


def test_pack_skill_candidates_fall_back_to_legacy_role_union_for_old_fixtures() -> None:
    pack = {
        "route_authority_candidates": ["primary", "shared"],
        "stage_assistant_candidates": ["assistant", "shared"],
    }

    assert get_pack_skill_candidates(pack) == ["primary", "shared", "assistant"]


def test_active_skill_candidates_do_not_need_legacy_role_fields() -> None:
    selection = select_pack_candidate(
        prompt_lower="use helper for specialized cleanup",
        candidates=["primary", "helper"],
        task_type="coding",
        requested_canonical=None,
        skill_keyword_index={
            "selection": {
                "weights": {"keyword_match": 0.8, "name_match": 0.2},
                "fallback_to_first_when_score_below": 0.2,
            },
            "skills": {
                "primary": {"keywords": ["primary"]},
                "helper": {"keywords": ["helper", "cleanup"]},
            },
        },
        routing_rules={"skills": {}},
        pack={
            "id": "synthetic-pack",
            "skill_candidates": ["primary", "helper"],
            "defaults_by_task": {},
        },
        candidate_selection_config={
            "rule_positive_keyword_bonus": 0.2,
            "rule_negative_keyword_penalty": 0.25,
            "canonical_for_task_bonus": 0.12,
        },
    )

    assert selection["selected"] == "helper"
    assert selection["ranking"][0]["legacy_role"] == "skill_candidate"
    assert selection["stage_assistant_candidates"] == []
    assert "routing_role" not in selection["ranking"][0]
