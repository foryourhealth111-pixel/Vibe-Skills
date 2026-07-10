from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "tests" / "replay" / "route" / "vibe-routing-chaos-audit-cases.json"

NEW_CASE_IDS = {
    "architecture_prd_issue_bundle",
    "manuscript_review_audit_rewrite",
    "cv_error_analysis_figure_bundle",
    "rfc_decision_brief_bundle",
    "cpu_gpu_pipeline_triage",
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_vibe_routing_chaos_fixture_uses_v2_schema_and_keeps_second_wave_cases() -> None:
    fixture = _load_fixture()
    case_ids = {case["id"] for case in fixture["cases"]}

    assert fixture["schema_version"] == "replay.route.audit.v2"
    assert NEW_CASE_IDS.issubset(case_ids)


def test_every_audit_case_declares_coverage_oracle_fields() -> None:
    fixture = _load_fixture()

    for case in fixture["cases"]:
        oracle = case["missing_module_contract"]

        assert case["expected_core_families"]
        assert case["known_bad_shortlist_examples"]
        assert oracle["coverage_source"] == "selected_or_public_shortlist"
        assert oracle["minimum_expected_family_hits"] >= 2
        assert oracle["critical_family_groups"]
        assert oracle["failure_examples"]


def test_second_wave_cases_cover_multiskill_routing_gaps_beyond_the_first_five() -> None:
    fixture = _load_fixture()
    second_wave = [case for case in fixture["cases"] if case["id"] in NEW_CASE_IDS]

    assert len(second_wave) == 5
    assert {"coding", "research", "debug"} <= {case["task_type"] for case in second_wave}
    assert any("host_surface_coherence" in case["dimensions"] for case in second_wave)
    assert all(case["missing_module_contract"]["minimum_expected_family_hits"] >= 3 for case in second_wave)
