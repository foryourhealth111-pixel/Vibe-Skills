from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DIR = REPO_ROOT / "docs" / "governance"


def read_doc(name: str) -> str:
    return (GOVERNANCE_DIR / name).read_text(encoding="utf-8")


def test_current_routing_contract_frames_route_chain_as_compatibility_only() -> None:
    text = read_doc("current-routing-contract.md")

    assert "It is not the main runtime truth contract." in text
    assert "[`current-runtime-field-contract.md`](current-runtime-field-contract.md)" in text
    assert "requirement: skill_search_guide" in text
    assert "plan truth: agent_skill_organization" in text
    assert "The retained router is a compatibility candidate audit." in text
    assert "Those fields do not choose task skills, bind work, stop stage progression, or" in text
    assert "A route candidate becomes executable only after the Agent" in text
    assert "Require `module_assignments` skill ids to match the organization's selected skill ids." in text
    assert "Treat uncovered modules as explicit gaps; do not fabricate coverage." in text
    assert "skill_routing.selected -> skill_usage.used" not in text


def test_runtime_field_contract_puts_work_truth_before_compatibility_chain() -> None:
    text = read_doc("current-runtime-field-contract.md")

    assert "## Canonical Truth Chain" in text
    assert "plan truth: agent_skill_organization -> module-work-plan.json" in text
    assert "handoff truth: module-work-plan.json -> agent-execution-handoff.json" in text
    assert "execution truth: agent-execution-handoff.json -> module-execution.json" in text
    assert "acceptance truth: module-execution.json -> delivery-acceptance-report.json" in text
    assert "## Compatibility Audit Fields" in text
    assert "They are audit mirrors only." in text
    assert "must not populate `agent_skill_organization`, bind work, or" in text


def test_governance_readme_points_to_work_truth_before_routing_history() -> None:
    text = read_doc("README.md")

    current_index = text.index("current runtime truth and routing compatibility contracts")
    current_fields_index = text.index(
        "[`current-runtime-field-contract.md`](current-runtime-field-contract.md)"
    )
    current_route_index = text.index("[`current-routing-contract.md`](current-routing-contract.md)")
    history_index = text.index(
        "[`historical-routing-terminology.md`](historical-routing-terminology.md)"
    )

    assert current_index < current_fields_index < current_route_index < history_index
    assert current_index < current_fields_index < history_index
    assert "specialist-dispatch-governance.md" not in text


def test_docs_root_readme_points_current_runtime_to_work_truth_contracts() -> None:
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    current_runtime_index = text.index("## Current Runtime")
    current_runtime_section = text[current_runtime_index:].split("## Governance", 1)[0]

    runtime_protocol_index = current_runtime_section.index("[`../protocols/runtime.md`](../protocols/runtime.md)")
    field_contract_index = current_runtime_section.index(
        "[`governance/current-runtime-field-contract.md`](./governance/current-runtime-field-contract.md)"
    )
    routing_contract_index = current_runtime_section.index(
        "[`governance/current-routing-contract.md`](./governance/current-routing-contract.md)"
    )

    assert runtime_protocol_index < field_contract_index < routing_contract_index
    assert "[`governance/specialist-dispatch-governance.md`](./governance/specialist-dispatch-governance.md)" not in current_runtime_section


def test_docs_root_readme_keeps_delivery_acceptance_out_of_current_runtime_entrypoints() -> None:
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    current_runtime_section = text[text.index("## Current Runtime"):].split("## Governance", 1)[0]
    governance_section = text[text.index("## Governance"):].split("## Cross-Layer Handoff", 1)[0]

    delivery_acceptance_link = (
        "[`governance/vibe-governed-project-delivery-acceptance-governance.md`]"
        "(./governance/vibe-governed-project-delivery-acceptance-governance.md)"
    )

    assert delivery_acceptance_link not in current_runtime_section
    assert delivery_acceptance_link in governance_section


def test_delivery_acceptance_governance_page_uses_work_first_truth_lead() -> None:
    text = read_doc("vibe-governed-project-delivery-acceptance-governance.md")

    assert (
        "The current work truth is `module-work-plan.json -> agent-execution-handoff.json\n"
        "-> module-execution.json -> delivery-acceptance-report.json`."
    ) in text
    assert (
        "skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage"
    ) not in text


def test_runtime_protocol_sets_work_truth_reading_order_before_routing_compatibility() -> None:
    text = (REPO_ROOT / "protocols" / "runtime.md").read_text(encoding="utf-8")

    assert "When you need to explain a run or inspect artifacts, use this reading order:" in text
    assert "start with `current-runtime-field-contract.md` plus the run's work artifacts" in text
    assert "for most normal runs, stop there and read the work truth" in text
    assert "read `current-routing-contract.md` only if you still need the compatibility candidate-audit chain" in text


def test_runtime_protocol_hands_module_work_to_the_current_agent() -> None:
    text = (REPO_ROOT / "protocols" / "runtime.md").read_text(encoding="utf-8")

    assert "`plan_execute` compiles `module-work-plan.json` into `agent-execution-handoff.json`" in text
    assert "The current Agent reads every assigned `skill_entrypoint`" in text
    assert "writes the complete result to `module-execution.json`" in text
    assert "returns it through canonical `vibe` re-entry for acceptance" in text
    assert "`agent_action_required`" in text

    for retired_claim in (
        "native_skill_entrypoint",
        "`L` runs serial native units",
        "bounded native units",
        "actually executing Skills",
        "`module_skill_dispatch`",
        "execution-manifest operational accounting",
        "execution-manifest skill execution accounting",
        "execution receipts, cleanup receipts",
        "execution locks",
    ):
        assert retired_claim not in text


def test_retired_router_exact_golden_gate_is_absent_from_current_surfaces() -> None:
    assert not (REPO_ROOT / "scripts" / "verify" / "vibe-router-contract-gate.ps1").exists()
    assert not (
        REPO_ROOT / "tests" / "replay" / "route" / "router-contract-gate-golden.json"
    ).exists()

    current_surfaces = [
        "docs/contributor-default-runbooks.md",
        "docs/developer-change-governance.md",
        "docs/operator-default-runbooks.md",
        "docs/status/non-regression-proof-bundle.md",
        "docs/status/protected-capability-baseline.md",
        "docs/governance/router-modularization-governance.md",
        "docs/architecture/legacy-topology-audit.md",
        "references/change-proof-matrix.md",
        "scripts/verify/README.md",
        "scripts/verify/gate-family-index.md",
        "tests/replay/README.md",
        "tests/replay/route/README.md",
    ]
    for relative_path in current_surfaces:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "vibe-router-contract-gate.ps1" not in text, relative_path
        assert "router-contract-gate-golden.json" not in text, relative_path


def test_retired_selected_route_mirror_is_absent_from_current_runtime_surfaces() -> None:
    current_surfaces = [
        "config/current-routing-debt-erasure.json",
        "config/kernel-boundary-demotion-matrix.json",
        "docs/governance/current-routing-contract.md",
        "docs/governance/current-runtime-field-contract.md",
        "packages/runtime-core/src/vgo_runtime/canonical_entry.py",
        "scripts/runtime/VibeRuntime.Common.ps1",
        "scripts/verify/vibe-canonical-entry-truth-gate.ps1",
        "scripts/verify/vibe-no-silent-fallback-contract-gate.ps1",
        "scripts/verify/vibe-runtime-execution-proof-gate.ps1",
    ]
    for relative_path in current_surfaces:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "skill_routing.selected" not in text, relative_path
        assert "compatibility.skill_routing.selected" not in text, relative_path
        assert "derived_from_skill_routing_selected" not in text, relative_path

    canonical_entry = (REPO_ROOT / "packages/runtime-core/src/vgo_runtime/canonical_entry.py").read_text(
        encoding="utf-8"
    )
    assert "_skill_routing_selected_skill_ids" not in canonical_entry
