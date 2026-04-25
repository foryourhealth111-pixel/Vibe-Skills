from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

import vgo_runtime.canonical_entry as canonical_entry


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_host_launch_receipt(session_root: Path, *, run_id: str, launch_status: str = "verified") -> None:
    _write_json(
        session_root / "host-launch-receipt.json",
        {
            "host_id": "codex",
            "entry_id": "vibe",
            "launch_mode": "canonical-entry",
            "launcher_path": str((session_root / "launcher.ps1").resolve()),
            "requested_stage_stop": "phase_cleanup",
            "requested_grade_floor": None,
            "runtime_entrypoint": str((session_root / "runtime.ps1").resolve()),
            "run_id": run_id,
            "created_at": "2026-04-24T00:00:00Z",
            "launch_status": launch_status,
        },
    )


def _write_valid_truth_artifacts(
    session_root: Path,
    *,
    host_id: str = "codex",
    entry_intent_id: str = "vibe",
    canonical_router_requested_skill: str | None = None,
    router_selected_skill: str = "systematic-debugging",
    requested_stage_stop: str = "phase_cleanup",
    requested_grade_floor: str | None = None,
    canonical_router_host_id: str | None = None,
    governance_runtime_selected_skill: str = "vibe",
    divergence_router_selected_skill: str | None = None,
    divergence_runtime_selected_skill: str = "vibe",
    stage_lineage_last_stage_name: str | None = None,
    stage_lineage_stages: list[dict[str, str]] | None = None,
) -> None:
    _write_json(
        session_root / "runtime-input-packet.json",
        {
            "host_id": host_id,
            "entry_intent_id": entry_intent_id,
            "requested_stage_stop": requested_stage_stop,
            "requested_grade_floor": requested_grade_floor,
            "canonical_router": {
                "host_id": host_id if canonical_router_host_id is None else canonical_router_host_id,
                "requested_skill": canonical_router_requested_skill,
            },
            "route_snapshot": {
                "selected_skill": router_selected_skill,
                "route_mode": "governed",
                "confirm_required": False,
            },
            "specialist_recommendations": [
                {
                    "skill_id": router_selected_skill,
                }
            ],
            "specialist_dispatch": {
                "approved_dispatch": [],
                "local_specialist_suggestions": [],
            },
            "divergence_shadow": {
                "router_selected_skill": (
                    router_selected_skill if divergence_router_selected_skill is None else divergence_router_selected_skill
                ),
                "runtime_selected_skill": divergence_runtime_selected_skill,
                "skill_mismatch": router_selected_skill != "vibe",
            },
        },
    )
    _write_json(session_root / "governance-capsule.json", {"runtime_selected_skill": governance_runtime_selected_skill})
    _write_json(
        session_root / "stage-lineage.json",
        {
            "last_stage_name": requested_stage_stop if stage_lineage_last_stage_name is None else stage_lineage_last_stage_name,
            "stages": [{"stage_name": requested_stage_stop}] if stage_lineage_stages is None else stage_lineage_stages,
        },
    )


def _write_bounded_return_summary(
    artifact_root: Path,
    *,
    run_id: str,
    terminal_stage: str,
    allowed_followup_entry_ids: list[str],
    reentry_token: str,
    task: str,
    intent_goal: str = "plan runtime entry hardening",
    prior_task_type: str | None = None,
) -> Path:
    session_root = artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id
    intent_contract_path = session_root / "artifacts" / "intent-contract.json"
    execution_plan_path = session_root / "artifacts" / "execution-plan.md"
    requirement_doc_path = session_root / "artifacts" / "requirement-doc.md"
    runtime_input_packet_path = session_root / "artifacts" / "runtime-input-packet.json"
    execution_plan_path.parent.mkdir(parents=True, exist_ok=True)
    execution_plan_path.write_text("# execution plan\n", encoding="utf-8")
    requirement_doc_path.write_text("# requirement doc\n", encoding="utf-8")
    _write_json(
        intent_contract_path,
        {
            "goal": intent_goal,
            "deliverable": "report",
            "execution_mode": "execute",
            "constraints": ["bounded"],
            "capabilities": ["planning"],
        },
    )
    if prior_task_type:
        _write_json(
            runtime_input_packet_path,
            {
                "canonical_router": {
                    "task_type": prior_task_type,
                }
            },
        )
    summary_path = session_root / "runtime-summary.json"
    artifacts = {
        "intent_contract": str(intent_contract_path),
        "execution_plan": str(execution_plan_path),
        "requirement_doc": str(requirement_doc_path),
    }
    if prior_task_type:
        artifacts["runtime_input_packet"] = str(runtime_input_packet_path)
    _write_json(
        summary_path,
        {
            "run_id": run_id,
            "task": task,
            "terminal_stage": terminal_stage,
            "artifacts": artifacts,
            "bounded_return_control": {
                "explicit_user_reentry_required": True,
                "source_run_id": run_id,
                "terminal_stage": terminal_stage,
                "allowed_followup_entry_ids": allowed_followup_entry_ids,
                "reentry_token": reentry_token,
            },
        },
    )
    _write_host_launch_receipt(session_root, run_id=run_id)
    return summary_path


def test_canonical_entry_writes_host_launch_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-ok"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    def fake_resolve_contract(repo_root: Path, host_id: str) -> dict[str, object]:
        assert repo_root == tmp_path.resolve()
        assert host_id == "codex"
        return {"fallback_policy": "blocked"}

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        assert kwargs["prompt"] == "plan runtime entry hardening"
        assert kwargs["requested_stage_stop"] == "requirement_doc"
        _write_valid_truth_artifacts(session_root, requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "resolve_canonical_vibe_contract", fake_resolve_contract)
    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="plan runtime entry hardening",
        requested_stage_stop="phase_cleanup",
        artifact_root=tmp_path,
    )

    receipt_path = tmp_path / "outputs" / "runtime" / "vibe-sessions" / result.run_id / "host-launch-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["host_id"] == "codex"
    assert receipt["entry_id"] == "vibe"
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_prewrites_launched_receipt_before_runtime_invocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-prewrite"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        receipt_path = session_root / "host-launch-receipt.json"
        assert receipt_path.exists()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["launch_status"] == "launched"
        assert receipt["run_id"] == run_id
        _write_valid_truth_artifacts(session_root, requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="x",
        requested_stage_stop="phase_cleanup",
        run_id=run_id,
        artifact_root=tmp_path,
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_synthesizes_default_prompt_for_empty_vibe_upgrade_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-upgrade-default-prompt"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        prompt = str(kwargs["prompt"])
        assert "Upgrade the local Vibe-Skills installation" in prompt
        assert "host codex" in prompt
        assert "shared vgo-cli upgrade flow" in prompt
        _write_valid_truth_artifacts(session_root, entry_intent_id="vibe-upgrade")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe-upgrade",
        prompt="   ",
        requested_stage_stop="phase_cleanup",
        run_id=run_id,
        artifact_root=tmp_path,
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_progresses_public_vibe_to_requirement_boundary_on_first_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-vibe-requirement-boundary"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        assert kwargs["requested_stage_stop"] == "requirement_doc"
        _write_valid_truth_artifacts(session_root, requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="implement governed runtime hardening",
        requested_stage_stop="phase_cleanup",
        run_id=run_id,
        artifact_root=tmp_path,
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["requested_stage_stop"] == "requirement_doc"
    assert receipt["launch_status"] == "verified"


def test_resolve_effective_prompt_enriches_short_vibe_do_prompt_with_prior_intent_contract(
    tmp_path: Path,
) -> None:
    previous_run = tmp_path / "outputs" / "runtime" / "vibe-sessions" / "prior-run"
    intent_contract_path = previous_run / "artifacts" / "intent-contract.json"
    execution_plan_path = previous_run / "artifacts" / "execution-plan.md"
    summary_path = previous_run / "runtime-summary.json"

    _write_json(
        intent_contract_path,
        {
            "goal": "facial recognition few-shot dataset research",
            "deliverable": "report",
            "execution_mode": "execute",
            "constraints": ["gpu-aware"],
            "capabilities": ["dataset-download", "baseline-train"],
        },
    )
    execution_plan_path.parent.mkdir(parents=True, exist_ok=True)
    execution_plan_path.write_text("# execution plan\n", encoding="utf-8")
    _write_json(
        summary_path,
        {
            "run_id": "prior-run",
            "terminal_stage": "execution_plan",
            "artifacts": {
                "intent_contract": str(intent_contract_path),
                "execution_plan": str(execution_plan_path),
            },
        },
    )
    _write_host_launch_receipt(previous_run, run_id="prior-run")

    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe-do-it",
        prompt="execute plan phase-cleanup",
        artifact_root=tmp_path,
        run_id="current-run",
    )

    assert prompt.startswith("continue-vibe-do-it ")
    assert "facial recognition few-shot dataset research" in prompt
    assert "deliverable-report" in prompt
    assert "mode-execute" in prompt
    assert "constraint-gpu-aware" in prompt
    assert "capability-dataset-download" in prompt
    assert prompt.endswith("execute plan phase-cleanup")


def test_load_continuation_context_resolves_relative_artifacts_from_session_root(tmp_path: Path) -> None:
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / "prior-run"
    intent_contract_path = session_root / "artifacts" / "intent-contract.json"
    execution_plan_path = session_root / "artifacts" / "execution-plan.md"
    summary_path = session_root / "runtime-summary.json"

    _write_json(intent_contract_path, {"goal": "relative artifact goal", "deliverable": "report"})
    execution_plan_path.parent.mkdir(parents=True, exist_ok=True)
    execution_plan_path.write_text("# execution plan\n", encoding="utf-8")
    _write_json(
        summary_path,
        {
            "run_id": "prior-run",
            "terminal_stage": "xl_plan",
            "artifacts": {
                "intent_contract": "artifacts/intent-contract.json",
                "execution_plan": "artifacts/execution-plan.md",
            },
        },
    )
    _write_host_launch_receipt(session_root, run_id="prior-run")

    continuation = canonical_entry._load_continuation_context_from_summary(
        summary_path,
        required_artifact="execution_plan",
    )

    assert continuation is not None
    assert continuation["intent_goal"] == "relative artifact goal"
    assert continuation["required_artifact"] == str(execution_plan_path)


def test_bounded_return_control_resolves_relative_artifacts_from_summary_path(tmp_path: Path) -> None:
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / "bounded-run"
    summary_path = session_root / "runtime-summary.json"
    _write_json(session_root / "artifacts" / "intent-contract.json", {"goal": "relative bounded goal"})
    _write_json(
        session_root / "artifacts" / "runtime-input-packet.json",
        {"canonical_router": {"task_type": "research"}},
    )
    summary = {
        "run_id": "bounded-run",
        "terminal_stage": "requirement_doc",
        "artifacts": {
            "intent_contract": "artifacts/intent-contract.json",
            "runtime_input_packet": "artifacts/runtime-input-packet.json",
        },
        "bounded_return_control": {
            "explicit_user_reentry_required": True,
            "source_run_id": "bounded-run",
            "terminal_stage": "requirement_doc",
            "allowed_followup_entry_ids": ["vibe"],
            "reentry_token": "token-123",  # noqa: S106 - non-secret fixture token
        },
    }

    guard = canonical_entry._coerce_bounded_return_control(summary, summary_path)

    assert guard is not None
    assert guard["intent_goal"] == "relative bounded goal"
    assert guard["prior_task_type"] == "research"


def test_resolve_effective_prompt_enriches_vibe_reentry_with_requirement_context(
    tmp_path: Path,
) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="requirement_doc",
        allowed_followup_entry_ids=["vibe"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
        intent_goal="governed runtime hardening requirement freeze",
    )

    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe",
        prompt="继续规划",
        artifact_root=tmp_path,
        run_id="current-run",
        bounded_reentry={
            "source_run_id": "prior-bounded-run",
            "terminal_stage": "requirement_doc",
            "allowed_followup_entry_ids": ["vibe"],
            "reentry_token": "token-123",
        },
        continuation_source_run_id="prior-bounded-run",
        allow_bounded_preferred_source=True,
    )

    assert prompt.startswith("continue-vibe ")
    assert "governed runtime hardening requirement freeze" in prompt
    assert "deliverable-report" in prompt
    assert prompt.endswith("继续规划")


def test_resolve_effective_prompt_uses_structured_bounded_reentry_context_for_approval(
    tmp_path: Path,
) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="requirement_doc",
        allowed_followup_entry_ids=["vibe"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="continue-vibe generic deliverable-governed-implementation-artifacts risk-review",
        intent_goal="research ECG public datasets for diagnosis tasks",
        prior_task_type="research",
    )
    host_decision = canonical_entry._attach_bounded_continuation_context_to_host_decision(
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
        },
        bounded_reentry={
            "source_run_id": "prior-bounded-run",
            "terminal_stage": "requirement_doc",
            "allowed_followup_entry_ids": ["vibe"],
            "reentry_token": "token-123",
            "task": "continue-vibe generic deliverable-governed-implementation-artifacts risk-review",
            "intent_goal": "research ECG public datasets for diagnosis tasks",
            "intent_deliverable": "Chinese report and dataset table",
            "intent_constraints": ["public-only", "official-source-only"],
            "prior_task_type": "research",
        },
        prompt_text="批准",
    )

    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe",
        prompt="批准",
        host_decision=host_decision,
        artifact_root=tmp_path,
        run_id="current-run",
        bounded_reentry={
            "source_run_id": "prior-bounded-run",
            "terminal_stage": "requirement_doc",
            "allowed_followup_entry_ids": ["vibe"],
            "reentry_token": "token-123",
        },
        continuation_source_run_id="prior-bounded-run",
        allow_bounded_preferred_source=True,
    )

    assert prompt == (
        "research ECG public datasets for diagnosis tasks "
        "Deliverable: report. "
        "Constraints: bounded."
    )


def test_resolve_effective_prompt_keeps_prompt_when_no_prior_continuation_context(
    tmp_path: Path,
) -> None:
    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe-do-it",
        prompt="execute plan phase-cleanup",
        artifact_root=tmp_path,
        run_id="current-run",
    )

    assert prompt == "execute plan phase-cleanup"


def test_resolve_effective_prompt_ignores_bounded_preferred_summary_without_explicit_allow(
    tmp_path: Path,
) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )

    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe-do-it",
        prompt="execute plan",
        artifact_root=tmp_path,
        run_id="current-run",
        continuation_source_run_id="prior-bounded-run",
    )

    assert prompt == "execute plan"


def test_runtime_summary_path_for_run_id_rejects_invalid_path_segments(tmp_path: Path) -> None:
    assert canonical_entry._runtime_summary_path_for_run_id(tmp_path, "../escape") is None
    assert canonical_entry._runtime_summary_path_for_run_id(tmp_path, r"..\escape") is None
    assert canonical_entry._runtime_summary_path_for_run_id(tmp_path, "nested/run") is None
    assert canonical_entry._runtime_summary_path_for_run_id(tmp_path, r"nested\run") is None
    assert canonical_entry._runtime_summary_path_for_run_id(tmp_path, "C:evil") is None


def test_load_continuation_context_from_summary_ignores_non_string_artifact_paths(tmp_path: Path) -> None:
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / "prior-run"
    summary_path = session_root / "runtime-summary.json"
    _write_json(
        summary_path,
        {
            "run_id": "prior-run",
            "terminal_stage": "xl_plan",
            "artifacts": {
                "execution_plan": ["not", "a", "path"],
                "intent_contract": {"bad": "path-shape"},
            },
        },
    )
    _write_host_launch_receipt(session_root, run_id="prior-run")

    continuation = canonical_entry._load_continuation_context_from_summary(
        summary_path,
        required_artifact="execution_plan",
    )

    assert continuation is None


def test_load_continuation_context_from_summary_requires_verified_host_launch_receipt(tmp_path: Path) -> None:
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / "prior-run"
    intent_contract_path = session_root / "artifacts" / "intent-contract.json"
    execution_plan_path = session_root / "artifacts" / "execution-plan.md"
    summary_path = session_root / "runtime-summary.json"

    _write_json(intent_contract_path, {"goal": "goal", "deliverable": "report"})
    execution_plan_path.parent.mkdir(parents=True, exist_ok=True)
    execution_plan_path.write_text("# execution plan\n", encoding="utf-8")
    _write_json(
        summary_path,
        {
            "run_id": "prior-run",
            "terminal_stage": "xl_plan",
            "artifacts": {
                "intent_contract": str(intent_contract_path),
                "execution_plan": str(execution_plan_path),
            },
        },
    )
    _write_host_launch_receipt(session_root, run_id="prior-run", launch_status="launched")

    continuation = canonical_entry._load_continuation_context_from_summary(
        summary_path,
        required_artifact="execution_plan",
    )

    assert continuation is None


def test_find_latest_bounded_return_control_rejects_unverified_preferred_summary(tmp_path: Path) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    _write_host_launch_receipt(
        tmp_path / "outputs" / "runtime" / "vibe-sessions" / "prior-bounded-run",
        run_id="prior-bounded-run",
        launch_status="launched",
    )

    guard = canonical_entry._find_latest_bounded_return_control(
        artifact_root=tmp_path,
        run_id="current-run",
        preferred_run_id="prior-bounded-run",
    )

    assert guard is None


def test_find_latest_bounded_return_control_skips_unverified_history_entries(tmp_path: Path) -> None:
    older_summary = _write_bounded_return_summary(
        tmp_path,
        run_id="older-verified-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-older",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    newer_summary = _write_bounded_return_summary(
        tmp_path,
        run_id="newer-unverified-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-newer",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    _write_host_launch_receipt(
        tmp_path / "outputs" / "runtime" / "vibe-sessions" / "newer-unverified-run",
        run_id="newer-unverified-run",
        launch_status="launched",
    )
    newer_summary.touch()

    guard = canonical_entry._find_latest_bounded_return_control(
        artifact_root=tmp_path,
        run_id="current-run",
    )

    assert guard is not None
    assert guard["source_run_id"] == "older-verified-run"


def test_bounded_return_helpers_ignore_non_string_intent_contract_paths(tmp_path: Path) -> None:
    summary = {
        "run_id": "prior-bounded-run",
        "task": "plan runtime entry hardening",
        "terminal_stage": "xl_plan",
        "artifacts": {
            "intent_contract": ["not", "a", "path"],
        },
        "bounded_return_control": {
            "explicit_user_reentry_required": True,
            "source_run_id": "prior-bounded-run",
            "terminal_stage": "xl_plan",
            "allowed_followup_entry_ids": ["vibe", "vibe-do-it"],
            "reentry_token": "token-123",  # noqa: S106 - non-secret fixture token
        },
    }

    guard = canonical_entry._coerce_bounded_return_control(summary)
    malformed = canonical_entry._build_malformed_bounded_return_control(summary, tmp_path / "runtime-summary.json")

    assert guard is not None
    assert guard["intent_goal"] == ""
    assert malformed["intent_goal"] == ""


def test_resolve_effective_prompt_skips_malformed_bounded_preferred_summary(tmp_path: Path) -> None:
    summary_path = _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["bounded_return_control"].pop("reentry_token")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    prompt = canonical_entry._resolve_effective_prompt(
        host_id="codex",
        entry_id="vibe-do-it",
        prompt="execute plan",
        artifact_root=tmp_path,
        run_id="current-run",
        continuation_source_run_id="prior-bounded-run",
    )

    assert prompt == "execute plan"


@pytest.mark.parametrize(
    ("artifact_root_arg", "expected_relpath", "run_id"),
    [
        (None, Path(".vibeskills"), "pytest-canonical-entry-default-artifact-root"),
        ("custom-artifacts", Path("custom-artifacts"), "pytest-canonical-entry-relative-artifact-root"),
    ],
)
def test_canonical_entry_resolves_artifact_root_via_helper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    artifact_root_arg: str | None,
    expected_relpath: Path,
    run_id: str,
) -> None:
    expected_artifact_root = (tmp_path / expected_relpath).resolve()
    session_root = expected_artifact_root / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        assert Path(str(kwargs["artifact_root"])).resolve() == expected_artifact_root
        _write_valid_truth_artifacts(session_root, requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="x",
        run_id=run_id,
        artifact_root=artifact_root_arg,
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_rejects_bounded_wrapper_reentry_without_explicit_credentials(
    tmp_path: Path,
) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )

    with pytest.raises(RuntimeError, match="forward --continue-from-run-id and --bounded-reentry-token"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe-do-it",
            prompt="execute plan",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_allows_bounded_wrapper_reentry_with_valid_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-bounded-reentry"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        prompt = str(kwargs["prompt"])
        assert prompt.startswith("continue-vibe-do-it ")
        assert "plan runtime entry hardening" in prompt
        assert Path(str(kwargs["artifact_root"])).resolve() == tmp_path.resolve()
        _write_valid_truth_artifacts(session_root, entry_intent_id="vibe-do-it")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe-do-it",
        prompt="execute plan",
        requested_stage_stop="phase_cleanup",
        run_id=run_id,
        artifact_root=tmp_path,
        continue_from_run_id="prior-bounded-run",
        bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_advances_public_vibe_to_plan_boundary_after_requirement_approval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-vibe-plan-boundary"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="requirement_doc",
        allowed_followup_entry_ids=["vibe"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
        intent_goal="governed runtime hardening requirement freeze",
    )

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        prompt = str(kwargs["prompt"])
        assert kwargs["requested_stage_stop"] == "xl_plan"
        assert prompt.startswith("continue-vibe ")
        assert "governed runtime hardening requirement freeze" in prompt
        _write_valid_truth_artifacts(session_root, requested_stage_stop="xl_plan")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe",
        prompt="继续规划",
        requested_stage_stop="phase_cleanup",
        run_id=run_id,
        artifact_root=tmp_path,
        continue_from_run_id="prior-bounded-run",
        bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
    )

    receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))
    assert receipt["requested_stage_stop"] == "xl_plan"
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_rejects_malformed_bounded_wrapper_reentry_metadata(tmp_path: Path) -> None:
    summary_path = _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["bounded_return_control"].pop("allowed_followup_entry_ids")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="bounded wrapper continuation metadata is malformed"):
        canonical_entry._validate_bounded_reentry(
            artifact_root=tmp_path,
            entry_id="vibe-do-it",
            prompt="execute plan",
            run_id="current-run",
            continue_from_run_id="prior-bounded-run",
            bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        )


def test_validate_bounded_reentry_requires_matching_prior_guard_for_explicit_credentials(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no matching bounded run could be found"):
        canonical_entry._validate_bounded_reentry(
            artifact_root=tmp_path,
            entry_id="vibe-do-it",
            prompt="execute plan",
            run_id="current-run",
            continue_from_run_id="missing-prior-run",
            bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        )


def test_validate_bounded_reentry_rejects_token_only_credentials_for_malformed_guard(tmp_path: Path) -> None:
    summary_path = _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["bounded_return_control"].pop("allowed_followup_entry_ids")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="bounded wrapper continuation metadata is malformed"):
        canonical_entry._validate_bounded_reentry(
            artifact_root=tmp_path,
            entry_id="vibe-do-it",
            prompt="execute plan",
            run_id="current-run",
            continue_from_run_id=None,
            bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        )


def test_validate_bounded_reentry_rejects_disallowed_followup_entry_for_explicit_credentials(tmp_path: Path) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )

    with pytest.raises(RuntimeError, match="is not allowed"):
        canonical_entry._validate_bounded_reentry(
            artifact_root=tmp_path,
            entry_id="vibe-do-it",
            prompt="execute plan",
            run_id="current-run",
            continue_from_run_id="prior-bounded-run",
            bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        )


def test_validate_bounded_reentry_rejects_non_continuation_prompt_when_credentials_are_explicit(tmp_path: Path) -> None:
    _write_bounded_return_summary(
        tmp_path,
        run_id="prior-bounded-run",
        terminal_stage="xl_plan",
        allowed_followup_entry_ids=["vibe", "vibe-do-it"],
        reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        task="plan runtime entry hardening",
    )

    with pytest.raises(RuntimeError, match="does not look like a bounded-wrapper continuation"):
        canonical_entry._validate_bounded_reentry(
            artifact_root=tmp_path,
            entry_id="vibe-do-it",
            prompt="hello world",
            run_id="current-run",
            continue_from_run_id="prior-bounded-run",
            bounded_reentry_token="token-123",  # noqa: S106 - non-secret fixture token
        )


def test_resolve_progressive_requested_stage_stop_does_not_wrap_after_terminal_stage() -> None:
    assert canonical_entry._resolve_progressive_requested_stage_stop(
        repo_root=REPO_ROOT,
        entry_id="vibe",
        requested_stage_stop="phase_cleanup",
        bounded_reentry={"terminal_stage": "phase_cleanup"},
    ) == "phase_cleanup"


def test_resolve_progressive_requested_stage_stop_preserves_explicit_intermediate_stop() -> None:
    assert canonical_entry._resolve_progressive_requested_stage_stop(
        repo_root=REPO_ROOT,
        entry_id="vibe",
        requested_stage_stop="xl_plan",
        bounded_reentry=None,
    ) == "xl_plan"


def test_progressive_stage_stops_do_not_fallback_to_launcher_repo_for_external_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Entry:
        progressive_stage_stops = ("requirement_doc", "xl_plan", "phase_cleanup")

    def fake_load_surface(repo_root: Path) -> object:
        if repo_root.resolve() == tmp_path.resolve():
            raise RuntimeError("external workspace has no discoverable surface")
        return type("Surface", (), {"entry_by_id": {"vibe-do-it": Entry()}})()

    monkeypatch.setattr(canonical_entry, "load_discoverable_entry_surface", fake_load_surface)

    assert canonical_entry._progressive_stage_stops(tmp_path, "vibe-do-it") == ()


def test_progressive_stage_stops_use_canonical_vibe_safe_default_for_external_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        canonical_entry,
        "load_discoverable_entry_surface",
        lambda repo_root: (_ for _ in ()).throw(RuntimeError("no discoverable surface")),
    )

    assert canonical_entry._progressive_stage_stops(tmp_path, "vibe") == (
        "requirement_doc",
        "xl_plan",
        "phase_cleanup",
    )


def test_progressive_stage_stops_surfaces_malformed_local_entry_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "vibe-entry-surfaces.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        canonical_entry,
        "load_discoverable_entry_surface",
        lambda repo_root: (_ for _ in ()).throw(RuntimeError("malformed entry surface")),
    )

    with pytest.raises(RuntimeError, match="malformed entry surface"):
        canonical_entry._progressive_stage_stops(tmp_path, "vibe")


def test_progressive_stage_stops_rejects_surface_without_canonical_vibe() -> None:
    class Surface:
        entry_by_id: dict[str, object] = {}

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(canonical_entry, "load_discoverable_entry_surface", lambda repo_root: Surface())
        with pytest.raises(RuntimeError, match="canonical vibe entry is missing"):
            canonical_entry._progressive_stage_stops(REPO_ROOT, "vibe")


def test_normalize_text_list_treats_string_as_single_item() -> None:
    assert canonical_entry._normalize_text_list("GPU only") == ["GPU only"]


def test_structured_revise_decision_does_not_authorize_bounded_reentry() -> None:
    assert not canonical_entry._structured_host_decision_allows_bounded_reentry(
        {
            "decision_kind": "approval_response",
            "decision_action": "revise_requirement",
            "approval_decision": "revise",
        },
        bounded_return_control={"terminal_stage": "requirement_doc"},
    )


def test_canonical_entry_marks_receipt_failed_when_runtime_invocation_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-runtime-failure"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        raise RuntimeError("runtime exploded")

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="runtime exploded"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            run_id=run_id,
            artifact_root=tmp_path,
        )

    receipt = json.loads((session_root / "host-launch-receipt.json").read_text(encoding="utf-8"))
    assert receipt["launch_status"] == "failed"


def test_canonical_entry_rejects_non_blocked_fallback_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "allow"},
    )

    with pytest.raises(RuntimeError, match="unsupported fallback policy"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            artifact_root=tmp_path,
        )


def test_canonical_entry_requires_minimum_truth_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-missing"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked"},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_json(session_root / "runtime-input-packet.json", {"host_id": "codex"})
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="Missing required runtime artifacts"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            artifact_root=tmp_path,
        )


def test_canonical_entry_fails_when_runtime_packet_disagrees_with_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-mismatch"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked"},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(session_root, host_id="claude-code", requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="host_id mismatch"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_preserves_canonical_receipt_for_presentational_entry_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-presentational"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )
    monkeypatch.setattr(
        canonical_entry,
        "load_allowed_vibe_entry_ids",
        lambda: frozenset({"vibe", "vibe-how-do-we-do"}),
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            entry_intent_id="vibe-how-do-we-do",
            requested_stage_stop="xl_plan",
            requested_grade_floor="XL",
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    result = canonical_entry.launch_canonical_vibe(
        repo_root=tmp_path,
        host_id="codex",
        entry_id="vibe-how-do-we-do",
        prompt="x",
        requested_stage_stop="xl_plan",
        requested_grade_floor="XL",
        artifact_root=tmp_path,
    )

    receipt = json.loads((result.host_launch_receipt_path).read_text(encoding="utf-8"))
    assert receipt["entry_id"] == "vibe"
    assert receipt["launch_status"] == "verified"


def test_canonical_entry_rejects_incomplete_truth_packets_before_verifying(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-incomplete-truth"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )
    monkeypatch.setattr(
        canonical_entry,
        "load_allowed_vibe_entry_ids",
        lambda: frozenset({"vibe"}),
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_json(
            session_root / "runtime-input-packet.json",
            {"host_id": "codex", "requested_stage_stop": "requirement_doc"},
        )
        _write_json(session_root / "governance-capsule.json", {"runtime_selected_skill": "vibe"})
        _write_json(
            session_root / "stage-lineage.json",
            {"last_stage_name": "requirement_doc", "stages": [{"stage_name": "requirement_doc"}]},
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="canonical truth"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_unsupported_presentational_entry_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )
    monkeypatch.setattr(
        canonical_entry,
        "load_allowed_vibe_entry_ids",
        lambda: frozenset({"vibe", "vibe-how-do-we-do"}),
    )

    with pytest.raises(RuntimeError, match="unsupported canonical vibe entry id"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="not-a-real-entry",
            prompt="x",
            artifact_root=tmp_path,
        )


def test_extract_terminal_stage_reads_current_stage_lineage_schema() -> None:
    terminal = canonical_entry._extract_terminal_stage(
        {
            "last_stage_name": "xl_plan",
            "stages": [{"stage_name": "requirement_doc"}, {"stage_name": "xl_plan"}],
        }
    )

    assert terminal == "xl_plan"


def test_canonical_entry_rejects_when_runtime_packet_drops_requested_stop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-dropped-stop"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            entry_intent_id="vibe-how-do-we-do",
            requested_stage_stop="phase_cleanup",
        )
        runtime_packet_path = session_root / "runtime-input-packet.json"
        runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
        runtime_packet["requested_stage_stop"] = None
        _write_json(runtime_packet_path, runtime_packet)
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="runtime packet dropped requested_stage_stop"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe-how-do-we-do",
            prompt="x",
            requested_stage_stop="xl_plan",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_when_runtime_packet_drops_requested_grade_floor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-dropped-grade"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            entry_intent_id="vibe-how-do-we-do",
            requested_stage_stop="xl_plan",
            requested_grade_floor="XL",
        )
        runtime_packet_path = session_root / "runtime-input-packet.json"
        runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
        runtime_packet["requested_grade_floor"] = None
        _write_json(runtime_packet_path, runtime_packet)
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="runtime packet dropped requested_grade_floor"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe-how-do-we-do",
            prompt="x",
            requested_stage_stop="xl_plan",
            requested_grade_floor="XL",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_empty_canonical_router_host_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-empty-router-host"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(session_root, canonical_router_host_id="", requested_stage_stop="requirement_doc")
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="canonical_router host_id"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_empty_governance_capsule_runtime_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-empty-governance-runtime"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            governance_runtime_selected_skill="",
            requested_stage_stop="requirement_doc",
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="governance capsule must keep vibe"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_empty_divergence_runtime_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-empty-divergence-runtime"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            divergence_runtime_selected_skill="",
            requested_stage_stop="requirement_doc",
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="divergence_shadow must keep vibe"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_empty_divergence_router_skill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-empty-divergence-router"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            divergence_router_selected_skill="",
            requested_stage_stop="requirement_doc",
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="divergence_shadow router_selected_skill"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_canonical_entry_rejects_stage_lineage_without_terminal_stage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = "pytest-canonical-entry-missing-terminal-stage"
    session_root = tmp_path / "outputs" / "runtime" / "vibe-sessions" / run_id

    monkeypatch.setattr(
        canonical_entry,
        "resolve_canonical_vibe_contract",
        lambda repo_root, host_id: {"fallback_policy": "blocked", "allow_skill_doc_fallback": False},
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            requested_stage_stop="requirement_doc",
            stage_lineage_last_stage_name="",
            stage_lineage_stages=[],
        )
        return {
            "run_id": run_id,
            "session_root": str(session_root),
            "summary_path": str(session_root / "runtime-summary.json"),
            "summary": {"run_id": run_id},
        }

    monkeypatch.setattr(canonical_entry, "invoke_vibe_runtime_entrypoint", fake_invoke_runtime)

    with pytest.raises(RuntimeError, match="stage-lineage missing terminal stage"):
        canonical_entry.launch_canonical_vibe(
            repo_root=tmp_path,
            host_id="codex",
            entry_id="vibe",
            prompt="x",
            requested_stage_stop="phase_cleanup",
            artifact_root=tmp_path,
        )


def test_bridge_forwards_entry_intent_stop_and_grade_to_runtime(tmp_path: Path) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        pytest.skip("PowerShell executable not available in PATH")

    bridge_dir = tmp_path / "scripts" / "runtime"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = bridge_dir / "Invoke-VibeCanonicalEntry.ps1"
    bridge_path.write_text(
        (REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake_runtime_path = bridge_dir / "invoke-vibe-runtime.ps1"
    fake_runtime_path.write_text(
        """
param(
  [string]$Task,
  [string]$Mode,
  [string]$EntryIntentId = '',
  [string]$RequestedStageStop = '',
  [string]$RequestedGradeFloor = '',
  [string]$RunId = '',
  [string]$ArtifactRoot = ''
)
[pscustomobject]@{
  run_id = $RunId
  session_root = [string](Join-Path $PSScriptRoot 'session')
  summary_path = [string](Join-Path $PSScriptRoot 'summary.json')
  summary = [pscustomobject]@{
    received = [pscustomobject]@{
      EntryIntentId = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { $null } else { $EntryIntentId }
      RequestedStageStop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { $RequestedStageStop }
      RequestedGradeFloor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { $RequestedGradeFloor }
    }
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(bridge_path),
            "-Task",
            "demo",
            "-HostId",
            "codex",
            "-EntryId",
            "vibe-how-do-we-do",
            "-RequestedStageStop",
            "xl_plan",
            "-RequestedGradeFloor",
            "XL",
            "-RunId",
            "run-42",
            "-ArtifactRoot",
            str(tmp_path / "artifacts"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["summary"]["received"] == {
        "EntryIntentId": "vibe-how-do-we-do",
        "RequestedStageStop": "xl_plan",
        "RequestedGradeFloor": "XL",
    }


def test_canonical_entry_main_emits_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    result_payload = canonical_entry.CanonicalLaunchResult(
        run_id="run-1",
        session_root=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1",
        summary_path=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1" / "runtime-summary.json",
        host_launch_receipt_path=tmp_path / "outputs" / "runtime" / "vibe-sessions" / "run-1" / "host-launch-receipt.json",
        launch_mode="canonical-entry",
        summary={},
        artifacts={},
    )

    monkeypatch.setattr(canonical_entry, "launch_canonical_vibe", lambda **kwargs: result_payload)

    code = canonical_entry.main(
        [
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "hello",
        ]
    )

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "run-1"
    assert output["host_launch_receipt_path"].endswith("host-launch-receipt.json")
