from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

import vgo_runtime.canonical_entry as canonical_entry


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_valid_truth_artifacts(
    session_root: Path,
    *,
    host_id: str = "codex",
    entry_intent_id: str = "vibe",
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
                "requested_skill": entry_intent_id,
            },
            "route_snapshot": {
                "selected_skill": router_selected_skill,
                "route_mode": "governed",
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
        assert kwargs["requested_stage_stop"] == "phase_cleanup"
        _write_valid_truth_artifacts(session_root)
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
        _write_valid_truth_artifacts(session_root)
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
        _write_valid_truth_artifacts(session_root, host_id="claude-code")
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
        lambda: frozenset({"vibe", "vibe-how"}),
    )

    def fake_invoke_runtime(**kwargs: object) -> dict[str, object]:
        _write_valid_truth_artifacts(
            session_root,
            entry_intent_id="vibe-how",
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
        entry_id="vibe-how",
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
            {"host_id": "codex", "requested_stage_stop": "phase_cleanup"},
        )
        _write_json(session_root / "governance-capsule.json", {"runtime_selected_skill": "vibe"})
        _write_json(
            session_root / "stage-lineage.json",
            {"last_stage_name": "phase_cleanup", "stages": [{"stage_name": "phase_cleanup"}]},
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
        lambda: frozenset({"vibe", "vibe-how"}),
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
            entry_intent_id="vibe-how",
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
            entry_id="vibe-how",
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
            entry_intent_id="vibe-how",
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
            entry_id="vibe-how",
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
        _write_valid_truth_artifacts(session_root, canonical_router_host_id="")
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
        _write_valid_truth_artifacts(session_root, governance_runtime_selected_skill="")
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
        _write_valid_truth_artifacts(session_root, divergence_runtime_selected_skill="")
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
        _write_valid_truth_artifacts(session_root, divergence_router_selected_skill="")
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
            "vibe-how",
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
        "EntryIntentId": "vibe-how",
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
