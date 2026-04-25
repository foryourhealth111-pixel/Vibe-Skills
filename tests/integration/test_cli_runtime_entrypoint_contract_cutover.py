from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_HOSTS = ("codex", "claude-code", "opencode")


def _resolve_python() -> str:
    python_bin = shutil.which("python3") or shutil.which("python")
    if not python_bin:
        raise RuntimeError("python interpreter not available")
    return python_bin


def _require_powershell() -> None:
    if not (shutil.which("pwsh") or shutil.which("powershell")):
        pytest.skip("PowerShell executable not available in PATH")


def _run_cli_canonical_entry(*, host_id: str, artifact_root: Path) -> dict[str, object]:
    python_bin = _resolve_python()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(REPO_ROOT / "apps" / "vgo-cli" / "src"),
            str(REPO_ROOT / "packages" / "runtime-core" / "src"),
            str(REPO_ROOT / "packages" / "contracts" / "src"),
            str(REPO_ROOT / "packages" / "installer-core" / "src"),
        ]
    )
    env["VCO_HOST_ID"] = host_id
    env["VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION"] = "1"
    env["VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION"] = "0"

    run_id = f"pytest-cli-canonical-{host_id}-{uuid.uuid4().hex[:8]}"
    command = [
        python_bin,
        "-m",
        "vgo_cli.main",
        "canonical-entry",
        "--repo-root",
        str(REPO_ROOT),
        "--host-id",
        host_id,
        "--entry-id",
        "vibe",
        "--prompt",
        "Validate canonical runtime proof contract for this supported host. $vibe",
        "--requested-stage-stop",
        "phase_cleanup",
        "--run-id",
        run_id,
        "--artifact-root",
        str(artifact_root),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    return json.loads(completed.stdout)


def test_cli_canonical_entry_proves_runtime_backed_truth_for_supported_hosts() -> None:
    _require_powershell()
    for host_id in SUPPORTED_HOSTS:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = _run_cli_canonical_entry(
                host_id=host_id,
                artifact_root=Path(tempdir) / "canonical-entry-cutover",
            )

            receipt_path = Path(payload["host_launch_receipt_path"])
            assert receipt_path.exists(), host_id
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert receipt["host_id"] == host_id, host_id
            assert receipt["entry_id"] == "vibe", host_id
            assert receipt["launch_status"] == "verified", host_id

            artifacts = payload.get("artifacts") or {}
            runtime_packet_path = Path(artifacts["runtime_input_packet"])
            governance_capsule_path = Path(artifacts["governance_capsule"])
            stage_lineage_path = Path(artifacts["stage_lineage"])
            assert runtime_packet_path.exists(), host_id
            assert governance_capsule_path.exists(), host_id
            assert stage_lineage_path.exists(), host_id

            runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
            assert "route_snapshot" in runtime_packet, host_id
            assert runtime_packet["route_snapshot"]["selected_skill"] == "vibe", host_id
            assert "specialist_dispatch" in runtime_packet, host_id
            assert "specialist_recommendations" in runtime_packet, host_id
            specialist_decision = runtime_packet.get("specialist_decision") or {}
            no_specialist_resolved = (
                specialist_decision.get("decision_state") == "no_specialist_recommendations"
                and specialist_decision.get("resolution_mode") in {"no_matching_specialist", "no_specialist_needed"}
            )
            assert len(runtime_packet["specialist_recommendations"]) >= 1 or no_specialist_resolved, host_id
