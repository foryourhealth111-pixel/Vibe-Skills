from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEEP_INTERVIEW = REPO_ROOT / "scripts" / "runtime" / "Invoke-DeepInterview.ps1"


def _powershell() -> str:
    for candidate in (
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
    ):
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    pytest.skip("PowerShell is required for the public intent-contract test")


def test_structured_host_requirement_fields_survive_intent_freeze(tmp_path: Path) -> None:
    task = (
        r"Analyze D:\fixtures\wellness.csv without modifying it; write every user deliverable "
        r"only under D:\fixtures\deliverables. Treat the synthetic data as workflow evidence, "
        "not medical evidence. Preserve module dependencies and safe parallel boundaries."
    )
    host_decision = {
        "deliverable": "A Chinese report plus traceable tables and figures under the exact output root.",
        "constraints": [
            r"Input D:\fixtures\wellness.csv is immutable.",
            r"All user deliverables stay under D:\fixtures\deliverables.",
            "Synthetic data must not be described as medical or causal evidence.",
        ],
        "acceptance_criteria": [
            "Every required module passes its frozen criterion.",
            "Tables, figures, and narrative agree with recomputed values.",
        ],
        "non_goals": ["No product UI or responsive-layout review."],
        "task_specific_acceptance_extensions": [
            "Only dependency-ready units with disjoint write scopes may run in parallel."
        ],
    }
    run_id = "intent-host-fidelity"
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(DEEP_INTERVIEW),
        "-Task",
        task,
        "-RunId",
        run_id,
        "-ArtifactRoot",
        str(tmp_path),
        "-HostDecisionJson",
        json.dumps(host_decision, ensure_ascii=False, separators=(",", ":")),
    ]
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    contract_path = (
        tmp_path
        / "outputs"
        / "runtime"
        / "vibe-sessions"
        / run_id
        / "intent-contract.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["source_task"] == task
    for field in (
        "deliverable",
        "constraints",
        "acceptance_criteria",
        "non_goals",
        "task_specific_acceptance_extensions",
    ):
        assert contract[field] == host_decision[field]
