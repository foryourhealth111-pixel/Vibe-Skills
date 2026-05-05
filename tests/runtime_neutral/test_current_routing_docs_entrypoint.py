from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DIR = REPO_ROOT / "docs" / "governance"


def read_doc(name: str) -> str:
    return (GOVERNANCE_DIR / name).read_text(encoding="utf-8")


def test_current_routing_contract_teaches_selection_execution_usage_chain() -> None:
    text = read_doc("current-routing-contract.md")

    assert (
        "skill_candidates -> skill_routing.selected -> skill_execution_lock -> "
        "selected_skill_execution -> "
        "skill_usage.used / skill_usage.unused"
    ) in text
    assert "`skill_execution_lock` | The approved-plan execution lock that preserves selected specialists across bounded re-entry. It is not a use claim." in text
    assert "skill_routing.selected -> skill_usage.used" not in text


def test_runtime_field_contract_matches_current_routing_contract_chain() -> None:
    text = read_doc("current-runtime-field-contract.md")

    assert (
        "skill_candidates -> skill_routing.selected -> skill_execution_lock -> "
        "selected_skill_execution -> "
        "skill_usage.used / skill_usage.unused"
    ) in text
    assert "`skill_execution_lock` records specialists that crossed the approved-plan boundary" in text
    assert "skill_routing.selected -> skill_usage.used" not in text


def test_governance_readme_points_to_current_routing_before_history() -> None:
    text = read_doc("README.md")

    current_index = text.index("current routing and runtime field contracts")
    current_route_index = text.index("[`current-routing-contract.md`](current-routing-contract.md)")
    current_fields_index = text.index(
        "[`current-runtime-field-contract.md`](current-runtime-field-contract.md)"
    )
    history_index = text.index(
        "[`historical-routing-terminology.md`](historical-routing-terminology.md)"
    )

    assert current_index < current_route_index < history_index
    assert current_index < current_fields_index < history_index
    assert "specialist-dispatch-governance.md" not in text
