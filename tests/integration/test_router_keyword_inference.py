from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_SCRIPT = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"


def _resolve_powershell() -> str | None:
    return shutil.which("pwsh")


def _invoke_route(prompt: str) -> dict[str, object]:
    powershell = _resolve_powershell()
    if not powershell:
        pytest.skip("PowerShell 7 (pwsh) not found in PATH")

    completed = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROUTE_SCRIPT),
            "-Prompt",
            prompt,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


def test_router_infers_grade_and_task_type_from_keyword_style_prompt() -> None:
    route = _invoke_route(
        "debug router confidence-low fallback misroute task-classification grade-selection candidate-scoring"
    )

    assert route["task_type"] == "debug"
    assert route["grade"] == "L"


def test_router_keyword_style_prompt_does_not_fall_into_ml_or_clinical_pack() -> None:
    route = _invoke_route(
        "debug router confidence-low fallback misroute task-classification grade-selection candidate-scoring evidence"
    )

    selected = route.get("selected") or {}
    assert selected.get("pack_id") not in {"data-ml", "science-clinical-regulatory"}


def test_router_does_not_misclassify_plain_docs_cleanup_prompt() -> None:
    route = _invoke_route("suffix cleanup in docs")

    assert route["task_type"] == "planning"
    assert route["grade"] == "M"


def test_router_does_not_promote_xlsx_prompt_to_xl() -> None:
    route = _invoke_route("edit xlsx workbook and preserve formulas")

    assert route["grade"] == "M"


def test_router_keeps_clinical_grade_selection_prompt_in_clinical_pack() -> None:
    route = _invoke_route("clinical decision support grade selection evidence profile")

    selected = route.get("selected") or {}
    assert selected.get("pack_id") == "science-clinical-regulatory"
    assert selected.get("skill") == "clinical-decision-support"


def test_router_keeps_ml_pipeline_pack_prompt_in_ml_pack() -> None:
    route = _invoke_route("ml pipeline workflow pack artifacts for deployment")

    selected = route.get("selected") or {}
    assert selected.get("pack_id") == "data-ml"
    assert selected.get("skill") == "ml-pipeline-workflow"
