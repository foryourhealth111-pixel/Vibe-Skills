from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_phase_cleanup_refreshes_runtime_summary_from_final_acceptance(tmp_path: Path) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        pytest.skip("PowerShell executable not available in PATH")

    repo_root = tmp_path / "repo"
    runtime_dir = repo_root / "scripts" / "runtime"
    verify_dir = repo_root / "scripts" / "verify" / "runtime_neutral"
    canonical_dir = repo_root / "packages" / "runtime-core" / "src" / "vgo_runtime"
    runtime_dir.mkdir(parents=True)
    verify_dir.mkdir(parents=True)
    canonical_dir.mkdir(parents=True)
    (runtime_dir / "Invoke-PhaseCleanup.ps1").write_text(
        (REPO_ROOT / "scripts" / "runtime" / "Invoke-PhaseCleanup.ps1").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (runtime_dir / "VibeSkillRouting.Common.ps1").write_text("", encoding="utf-8")
    (canonical_dir / "canonical_entry.py").write_bytes(
        (RUNTIME_CORE_SRC / "vgo_runtime" / "canonical_entry.py").read_bytes()
    )
    (runtime_dir / "VibeRuntime.Common.ps1").write_text(
        r"""
function Get-VibeRuntimeContext {
    param([string]$ScriptPath)
    return [pscustomobject]@{
            repo_root = $env:TEST_REPO_ROOT
        runtime_modes = [pscustomobject]@{ default_mode = 'interactive_governed' }
        cleanup_policy = [pscustomobject]@{ bounded_default_modes = @() }
        proof_class_registry = [pscustomobject]@{
            artifact_class_defaults = [pscustomobject]@{ cleanup_receipt = 'proof' }
        }
    }
}
function Resolve-VibeRuntimeMode { param([string]$Mode, [string]$DefaultMode) return $Mode }
function New-VibeRunId { return 'refresh-run' }
function Ensure-VibeSessionRoot {
    param([string]$RepoRoot, [string]$RunId, [object]$Runtime, [string]$ArtifactRoot)
    New-Item -ItemType Directory -Path $ArtifactRoot -Force | Out-Null
    return $ArtifactRoot
}
    function Get-VgoPythonCommand {
        return [pscustomobject]@{ host_path = 'python.exe'; prefix_arguments = @() }
}
function Write-VibeJsonArtifact {
    param([string]$Path, [object]$Value)
    $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}
""",
        encoding="utf-8",
    )
    session_root = tmp_path / "session"
    acceptance_counter_path = session_root / "acceptance-counter.txt"
    (verify_dir / "runtime_delivery_acceptance.py").write_text(
        r"""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repo-root')
parser.add_argument('--session-root', required=True)
parser.add_argument('--write-artifacts', action='store_true')
parser.add_argument('--output-directory', required=True)
args = parser.parse_args()
output = Path(args.output_directory)
receipt = output / 'cleanup-receipt.json'
counter_path = Path(r'__COUNTER_PATH__')
evaluation_count = int(counter_path.read_text(encoding='utf-8')) + 1 if counter_path.exists() else 1
counter_path.write_text(str(evaluation_count), encoding='utf-8')
passed = evaluation_count >= 1
summary = {
    'gate_result': 'PASS' if passed else 'MANUAL_REVIEW_REQUIRED',
    'completion_language_allowed': passed,
    'runtime_status': 'completed' if passed else 'manual_review_required',
    'readiness_state': 'fully_ready' if passed else 'manual_actions_pending',
    'manual_review_layer_count': 0 if passed else 1,
    'failing_layer_count': 0,
    'forbidden_completion_hit_count': 0,
    'incomplete_layers': [],
}
report = {
    'summary': summary,
    'artifacts': {
        'cleanup_receipt_path': str(receipt),
        'runtime_input_packet_path': str(output / 'runtime-input-packet.json'),
    },
}
(output / 'delivery-acceptance-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(output / 'delivery-acceptance-report.md').write_text('# Delivery acceptance\n', encoding='utf-8')
print(json.dumps(report))
""".replace("__COUNTER_PATH__", str(acceptance_counter_path)),
        encoding="utf-8",
    )

    report_path = session_root / "delivery-acceptance-report.json"
    cleanup_path = session_root / "cleanup-receipt.json"
    summary_path = session_root / "runtime-summary.json"
    runtime_packet_path = session_root / "runtime-input-packet.json"
    write_json(runtime_packet_path, {"module_assignments": {"units": []}})
    write_json(
        report_path,
        {
            "summary": {
                "gate_result": "MANUAL_REVIEW_REQUIRED",
                "completion_language_allowed": False,
                "runtime_status": "manual_review_required",
                "readiness_state": "manual_actions_pending",
                "manual_review_layer_count": 1,
                "failing_layer_count": 0,
            },
            "artifacts": {"runtime_input_packet_path": str(runtime_packet_path)},
        },
    )
    write_json(
        summary_path,
        {
            "run_id": "refresh-run",
            "task": "refresh final acceptance",
            "truth_owner": "python",
            "status": "manual_review_required",
            "delivery_acceptance": {
                "gate_result": "MANUAL_REVIEW_REQUIRED",
                "completion_language_allowed": False,
                "readiness_state": "manual_actions_pending",
                "manual_review_layer_count": 1,
                "failing_layer_count": 0,
            },
            "artifacts": {
                "runtime_input_packet": str(runtime_packet_path),
                "cleanup_receipt": str(cleanup_path),
                "delivery_acceptance_report": str(report_path),
            },
            "artifacts_relative": {
                "runtime_input_packet": "runtime-input-packet.json",
                "cleanup_receipt": "cleanup-receipt.json",
                "delivery_acceptance_report": "delivery-acceptance-report.json",
            },
            "bound_skill_ids": [],
        },
    )

    completed = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(runtime_dir / "Invoke-PhaseCleanup.ps1"),
            "-Task",
            "refresh final acceptance",
            "-RunId",
            "refresh-run",
            "-ArtifactRoot",
            str(session_root),
        ],
        cwd=repo_root,
        env={
            **os.environ,
            "PATH": f"{Path(powershell).parent};{Path(sys.executable).parent}",
            "TEST_REPO_ROOT": str(repo_root),
            "PYTHONPATH": os.pathsep.join(
                [
                    str(RUNTIME_CORE_SRC),
                    str(REPO_ROOT / "packages" / "contracts" / "src"),
                ]
            ),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(report_path.read_text(encoding="utf-8"))
    receipt = json.loads(cleanup_path.read_text(encoding="utf-8-sig"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert acceptance_counter_path.exists() and acceptance_counter_path.read_text(encoding="utf-8") == "2", (
        completed.stdout,
        completed.stderr,
        receipt,
    )
    assert report["summary"]["gate_result"] == "PASS"
    assert receipt["cleanup_admitted"] is True
    assert receipt["delivery_acceptance"]["gate_result"] == "PASS"
    assert summary["delivery_acceptance"] == {
        "gate_result": "PASS",
        "completion_language_allowed": True,
        "runtime_status": "completed",
        "readiness_state": "fully_ready",
        "manual_review_layer_count": 0,
        "failing_layer_count": 0,
    }
    assert summary["status"] == "completed"
    assert summary["completion_language_allowed"] is True
    assert summary["artifacts"]["cleanup_receipt"] == str(cleanup_path)
    assert summary["artifacts"]["delivery_acceptance_report"] == str(report_path)
    assert summary["artifacts_relative"]["cleanup_receipt"] == "cleanup-receipt.json"
    assert summary["artifacts_relative"]["delivery_acceptance_report"] == "delivery-acceptance-report.json"
    assert json.loads(summary_path.read_text(encoding="utf-8")) == summary
