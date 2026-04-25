from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
for src in (RUNTIME_CORE_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

import vgo_runtime.canonical_entry as canonical_entry


def _require_powershell() -> None:
    if not (shutil.which("pwsh") or shutil.which("powershell")):
        pytest.skip("PowerShell executable not available in PATH")


@pytest.mark.parametrize("host_id", ["codex", "claude-code", "opencode"])
@pytest.mark.parametrize(
    ("entry_id", "requested_stage_stop", "requested_grade_floor"),
    [
        ("vibe-what-do-i-want", "requirement_doc", None),
        ("vibe-how-do-we-do", "xl_plan", "XL"),
    ],
)
def test_real_canonical_entry_honors_wrapper_bounded_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host_id: str,
    entry_id: str,
    requested_stage_stop: str,
    requested_grade_floor: str | None,
) -> None:
    _require_powershell()
    monkeypatch.setenv("VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION", "1")
    monkeypatch.setenv("VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION", "0")

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id=host_id,
        entry_id=entry_id,
        prompt=f"Verify bounded stop for {host_id} {entry_id}",
        requested_stage_stop=requested_stage_stop,
        requested_grade_floor=requested_grade_floor,
        artifact_root=tmp_path / host_id / entry_id,
    )

    stage_lineage = json.loads(Path(result.artifacts["stage_lineage"]).read_text(encoding="utf-8"))
    runtime_packet = json.loads(Path(result.artifacts["runtime_input_packet"]).read_text(encoding="utf-8"))

    assert stage_lineage["last_stage_name"] == requested_stage_stop
    assert runtime_packet["entry_intent_id"] == entry_id
    assert runtime_packet["requested_stage_stop"] == requested_stage_stop
    if requested_grade_floor is None:
        assert runtime_packet["requested_grade_floor"] is None
    else:
        assert runtime_packet["requested_grade_floor"] == requested_grade_floor

    cleanup_receipt = result.session_root / "cleanup-receipt.json"
    execute_receipt = result.session_root / "phase-execute.json"
    plan_receipt = result.session_root / "execution-plan-receipt.json"
    requirement_receipt = result.session_root / "requirement-doc-receipt.json"

    assert requirement_receipt.exists()
    if requested_stage_stop == "requirement_doc":
        assert not plan_receipt.exists()
        assert not execute_receipt.exists()
        assert not cleanup_receipt.exists()
    elif requested_stage_stop == "xl_plan":
        assert plan_receipt.exists()
        assert not execute_receipt.exists()
        assert not cleanup_receipt.exists()
