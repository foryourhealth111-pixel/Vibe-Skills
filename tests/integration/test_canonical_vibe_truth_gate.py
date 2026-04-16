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


def _write_valid_canonical_entry_artifacts(session_root: Path) -> None:
    _write_json(
        session_root / "host-launch-receipt.json",
        {
            "host_id": "codex",
            "entry_id": "vibe",
            "launch_mode": "canonical-entry",
            "launcher_path": "scripts/runtime/Invoke-VibeCanonicalEntry.ps1",
            "requested_stage_stop": "phase_cleanup",
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
            "canonical_router": {
                "host_id": "codex",
                "prompt": "validate proof",
                "requested_skill": "vibe",
                "route_script_path": "scripts/router/resolve-pack-route.ps1",
                "target_root": "/tmp/target",
                "task_type": "debug",
                "unattended": False,
            },
            "route_snapshot": {
                "selected_pack": "vibe",
                "selected_skill": "vibe",
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
                    "skill_id": "systematic-debugging",
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
                "skill_mismatch": False,
                "router_selected_skill": "vibe",
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
            "last_stage_name": "phase_cleanup",
            "stages": [
                {"stage_name": "skeleton_check"},
                {"stage_name": "deep_interview"},
                {"stage_name": "requirement_doc"},
                {"stage_name": "xl_plan"},
                {"stage_name": "plan_execute"},
                {"stage_name": "phase_cleanup"},
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


def test_truth_gate_accepts_verified_canonical_entry_session(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_valid_canonical_entry_artifacts(session_root)

    result = _run_truth_gate(session_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PASS] host-launch-receipt.json exists" in result.stdout
    assert "[PASS] runtime packet includes route_snapshot" in result.stdout
