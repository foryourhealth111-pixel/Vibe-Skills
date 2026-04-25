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
    requested_stage_stop: str = "phase_cleanup",
    interactive_pause: dict[str, object] | None = None,
    terminal_stage: str | None = None,
) -> None:
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
            "canonical_router": {
                "host_id": "codex",
                "prompt": "validate proof",
                "requested_skill": canonical_router_requested_skill,
                "route_script_path": "scripts/router/resolve-pack-route.ps1",
                "target_root": "/tmp/target",
                "task_type": "debug",
                "unattended": False,
            },
            "route_snapshot": {
                "selected_pack": "vibe",
                "selected_skill": router_selected_skill,
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
            },
            "specialist_recommendations": [
                {
                    "skill_id": router_selected_skill,
                    "native_skill_entrypoint": "skills/systematic-debugging/SKILL.md",
                }
            ],
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
            "divergence_shadow": {
                "skill_mismatch": entry_intent_id != "vibe",
                "router_selected_skill": router_selected_skill,
                "runtime_selected_skill": "vibe",
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
            "specialist_recommendations": [],
        },
    )

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "route_snapshot" in combined
    assert "specialist_dispatch" in combined
    assert "divergence_shadow" in combined


def test_truth_gate_reports_missing_route_snapshot_without_unbound_selected_skill_crash(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet.pop("route_snapshot")
    _write_json(runtime_packet_path, runtime_packet)

    result = _run_truth_gate(session_root)

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "route_snapshot" in combined
    assert "cannot be retrieved because it has not been set" not in combined
    assert "selectedSkill" not in combined


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
    runtime_packet["specialist_recommendations"] = []
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


def test_truth_gate_accepts_verified_canonical_entry_session(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] host-launch-receipt.json exists" in result.stdout
    assert "[PASS] runtime packet includes route_snapshot" in result.stdout


def test_truth_gate_accepts_presentational_entry_intent_with_canonical_authority(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(
        session_root,
        entry_intent_id="vibe-how-do-we-do",
        requested_stage_stop="xl_plan",
    )

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] runtime packet canonical_router keeps routing authority on canonical vibe" in result.stdout
    assert "[PASS] runtime packet preserves entry_intent_id independently from router authority" in result.stdout
    assert "[PASS] runtime packet route_snapshot records routed specialist truth" in result.stdout
