from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TRUTH_GATE = REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1"


def _require_powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        pytest.skip("PowerShell executable not available in PATH")
    return powershell


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_truth_gate(session_root: Path) -> subprocess.CompletedProcess[str]:
    powershell = _require_powershell()
    return subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TRUTH_GATE),
            "-SessionRoot",
            str(session_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _write_valid_canonical_entry_artifacts(
    session_root: Path,
    *,
    entry_intent_id: str = "vibe",
    canonical_router_requested_skill: str | None = None,
    router_selected_skill: str = "systematic-debugging",
    route_task_type: str = "debug",
    requested_stage_stop: str = "phase_cleanup",
    interactive_pause: dict[str, object] | None = None,
    terminal_stage: str | None = None,
) -> None:
    canonical_router = {
        "host_id": "codex",
        "prompt": "validate proof",
        "route_script_path": "scripts/router/resolve-pack-route.ps1",
        "target_root": "/tmp/target",
        "unattended": False,
    }
    if canonical_router_requested_skill is not None:
        canonical_router["requested_skill"] = canonical_router_requested_skill

    route_snapshot = {
        "selected_pack": "vibe",
        "task_type": route_task_type,
        "route_mode": "governed",
        "route_reason": "explicit vibe invocation",
        "confirm_required": False,
        "confidence": 1.0,
        "truth_level": "authoritative",
        "degradation_state": "none",
        "non_authoritative": False,
        "fallback_active": False,
        "hazard_alert_required": False,
        "unattended_override_applied": False,
        "custom_admission_status": "not_required",
    }

    _write_json(
        session_root / "host-launch-receipt.json",
        {
            "host_id": "codex",
            "entry_id": "vibe",
            "launch_mode": "canonical-entry",
            "launcher_path": "scripts/runtime/Invoke-VibeCanonicalEntry.ps1",
            "requested_stage_stop": requested_stage_stop,
            "requested_grade_floor": "XL",
            "runtime_entrypoint": "scripts/runtime/invoke-vibe-runtime.ps1",
            "run_id": "pytest-truth-gate",
            "created_at": "2026-04-16T00:00:00Z",
            "launch_status": "verified",
        },
    )
    _write_json(
        session_root / "runtime-input-packet.json",
        {
            "entry_intent_id": entry_intent_id,
            "requested_stage_stop": requested_stage_stop,
            "interactive_pause": interactive_pause,
            "canonical_router": canonical_router,
            "route_snapshot": route_snapshot,
            "skill_routing": {
                "schema_version": "simplified_skill_routing_v1",
                "candidates": [{"skill_id": router_selected_skill}],
                "selected": [{"skill_id": router_selected_skill, "skill_md_path": "skills/systematic-debugging/SKILL.md"}],
                "rejected": [],
            },
            "work_binding": {
                "schema_version": "runtime_work_binding_v1",
                "source": "approved_dispatch",
                "task": "validate proof",
                "run_id": "pytest-truth-gate",
                "unit_count": 1,
                "status": "projected_from_approved_dispatch",
                "units": [
                    {
                        "work_unit_id": "runtime-bound-skill-1",
                        "bound_skill": router_selected_skill,
                        "task_slice": "Use systematic-debugging for bounded specialist work.",
                        "skill_md_path": "skills/systematic-debugging/SKILL.md",
                        "native_skill_entrypoint": None,
                        "dispatch_phase": "in_execution",
                        "bounded_role": "selected_skill",
                        "binding_profile": "selected_skill",
                    }
                ],
            },
            "skill_usage": {
                "state_model": "binary_used_unused",
                "used": [],
                "unused": [{"skill_id": router_selected_skill}],
                "evidence": [],
            },
            "specialist_decision": {
                "decision_state": "no_specialist_recommendations",
                "resolution_mode": "no_specialist_needed",
                "recommendation_count": 0,
                "candidate_skill_ids_reviewed": [router_selected_skill],
                "selected_skill_ids": [],
                "rejected_candidates": [],
            },
            "divergence_shadow": {
                "skill_mismatch": entry_intent_id != "vibe",
                "confirm_required": False,
                "governance_scope_mismatch": False,
                "explicit_runtime_override_applied": False,
                "explicit_runtime_override_reason": "",
            },
            "authority_flags": {
                "explicit_runtime_skill": "vibe",
            },
        },
    )
    _write_json(
        session_root / "governance-capsule.json",
        {
            "run_id": "pytest-truth-gate",
            "runtime_selected_skill": "vibe",
            "governance_scope": "root",
        },
    )
    _write_json(
        session_root / "stage-lineage.json",
        {
            "run_id": "pytest-truth-gate",
            "last_stage_name": requested_stage_stop if terminal_stage is None else terminal_stage,
            "stages": [
                {"stage_name": "skeleton_check"},
                {"stage_name": "deep_interview"},
                *([{"stage_name": "requirement_doc"}] if (terminal_stage in (None, "requirement_doc", "xl_plan", "plan_execute", "phase_cleanup")) else []),
                *(
                    [{"stage_name": "xl_plan"}]
                    if (terminal_stage if terminal_stage is not None else requested_stage_stop) in {"xl_plan", "plan_execute", "phase_cleanup"}
                    else []
                ),
                *(
                    [{"stage_name": "plan_execute"}]
                    if (terminal_stage if terminal_stage is not None else requested_stage_stop) in {"plan_execute", "phase_cleanup"}
                    else []
                ),
                *([{"stage_name": "phase_cleanup"}] if (terminal_stage if terminal_stage is not None else requested_stage_stop) == "phase_cleanup" else []),
            ],
        },
    )


def _write_retired_legacy_truth_artifacts(session_root: Path) -> None:
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["legacy_skill_routing"] = {
        "specialist_recommendations": [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "skills/systematic-debugging/SKILL.md",
            }
        ],
        "stage_assistant_hints": [],
        "specialist_dispatch": {
            "approved_dispatch": [],
            "local_specialist_suggestions": [],
            "status": "no_dispatch",
            "approved_skill_ids": [],
            "local_suggestion_skill_ids": [],
            "blocked_skill_ids": [],
            "degraded_skill_ids": [],
            "matched_skill_ids": [],
            "surfaced_skill_ids": [],
            "ghost_match_skill_ids": [],
            "escalation_required": False,
            "escalation_status": "not_required",
        },
    }
    _write_json(runtime_packet_path, runtime_packet)


def test_truth_gate_rejects_missing_launch_receipt(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    (session_root / "host-launch-receipt.json").unlink()

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "host-launch-receipt.json" in combined
    assert "reading SKILL.md alone is not canonical vibe entry" in combined


def test_truth_gate_rejects_missing_runtime_packet_proof_fields(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    _write_json(
        session_root / "runtime-input-packet.json",
        {
            "canonical_router": {"host_id": "codex"},
            "legacy_skill_routing": {"specialist_recommendations": []},
        },
    )

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "route_snapshot" in combined
    assert "work_binding" in combined
    assert "specialist_decision" in combined


def test_truth_gate_rejects_missing_specialist_decision(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("specialist_decision", None)
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "specialist_decision" in combined


def test_truth_gate_accepts_missing_route_snapshot_packet_summary(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("route_snapshot")
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet route_snapshot stays optional compatibility control summary" in result.stdout


def test_truth_gate_accepts_missing_canonical_router_compatibility_mirror(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("canonical_router", None)
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet canonical_router stays optional compatibility mirror" in result.stdout


def test_truth_gate_rejects_missing_entry_intent_id(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("entry_intent_id")
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "runtime packet preserves entry_intent_id independently from router authority" in combined


def test_truth_gate_enforces_confirm_required_skeleton_stop_without_requested_stage_stop(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(
        session_root,
        requested_stage_stop="",
        terminal_stage="phase_cleanup",
    )
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["route_snapshot"]["confirm_required"] = True
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "confirm-required routing stops before governed stage progression" in combined


def test_truth_gate_accepts_explicit_no_specialist_decision(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["specialist_decision"] = {
        "decision_state": "no_specialist_recommendations",
        "resolution_mode": "no_specialist_needed",
        "recommendation_count": 0,
        "candidate_skill_ids_reviewed": [],
        "selected_skill_ids": [],
        "rejected_candidates": [],
    }
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr


def test_truth_gate_accepts_explicit_degraded_specialist_decision(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["work_binding"]["units"] = []
    runtime_packet["specialist_decision"] = {
        "decision_state": "degraded",
        "resolution_mode": "degraded",
        "recommendation_count": 1,
        "candidate_skill_ids_reviewed": ["gpt-image"],
        "selected_skill_ids": [],
        "surfaced_skill_ids": ["gpt-image"],
        "degraded_skill_ids": ["gpt-image"],
        "rejected_candidates": [],
    }
    runtime_packet["skill_routing"]["selected"] = []
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr


def test_truth_gate_accepts_verified_canonical_entry_session(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] host-launch-receipt.json exists" in result.stdout
    assert "[PASS] runtime packet route_snapshot stays an optional compatibility control summary" in result.stdout


def test_truth_gate_accepts_current_skill_routing_without_legacy_fields(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet skill_routing stays an optional compatibility shell" in result.stdout
    assert "[PASS] runtime packet includes work_binding" in result.stdout
    assert "[PASS] runtime packet exposes kernel-native work_binding" in result.stdout


def test_truth_gate_accepts_fallback_skill_usage_shape(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["skill_usage"] = {
        "state_model": "binary_used_unused",
        "used_skills": [],
        "unused_skills": [{"skill_id": "systematic-debugging"}],
        "evidence": [],
    }
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet skill_usage includes used/unused or used_skills/unused_skills" in result.stdout


def test_truth_gate_rejects_missing_skill_usage_truth_artifact(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("skill_usage", None)
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode != 0
    assert "[FAIL] runtime packet includes skill_usage truth artifact" in result.stdout


def test_truth_gate_accepts_canonical_entry_intent_with_canonical_authority(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(
        session_root,
        entry_intent_id="vibe",
        requested_stage_stop="xl_plan",
    )

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet canonical_router stays an optional compatibility host-launch mirror" in result.stdout
    assert "[PASS] runtime packet preserves entry_intent_id independently from router authority" in result.stdout


def test_truth_gate_accepts_legacy_canonical_router_requested_skill_when_work_truth_is_intact(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(
        session_root,
        canonical_router_requested_skill="scientific-reporting",
    )

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet canonical_router stays an optional compatibility host-launch mirror" in result.stdout


def test_truth_gate_accepts_missing_route_snapshot_task_type_when_work_truth_is_intact(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["route_snapshot"]["task_type"] = ""
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet route_snapshot stays an optional compatibility control summary" in result.stdout


def test_truth_gate_accepts_missing_route_snapshot_selected_skill_when_skill_routing_preserves_selection(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["route_snapshot"]["selected_skill"] = ""
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet skill_routing stays an optional compatibility shell" in result.stdout
    assert "[PASS] runtime packet route_snapshot selected_skill stays a removable optional compatibility summary" in result.stdout


def test_truth_gate_accepts_missing_skill_routing_when_work_binding_preserves_selection(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("skill_routing", None)
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet includes work_binding" in result.stdout
    assert "[PASS] runtime packet records work_binding, no-specialist resolution, or degraded specialist evidence" in result.stdout
    assert "[PASS] runtime packet skill_routing stays optional compatibility mirror" in result.stdout


def test_truth_gate_accepts_missing_divergence_shadow_compatibility_mirror(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("divergence_shadow", None)
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet divergence_shadow stays optional compatibility shadow" in result.stdout
