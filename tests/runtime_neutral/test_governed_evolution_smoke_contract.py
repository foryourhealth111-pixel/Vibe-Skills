from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "verify" / "vibe-governed-evolution-smoke.ps1"


def test_governed_evolution_runtime_smoke_script_exists() -> None:
    assert SMOKE_SCRIPT.exists()


def test_governed_evolution_runtime_smoke_script_keeps_artifact_chain_checks() -> None:
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    required_markers = [
        "failure-patterns.json",
        "pitfall-events.json",
        "atomic-skill-call-chain.json",
        "proposal-layer.json",
        "warning-cards.json",
        "preflight-checklist.json",
        "remediation-notes.json",
        "candidate-composite-skill-draft.json",
        "threshold-policy-suggestion.json",
        "application-readiness-report.json",
        "application-readiness-report.md",
    ]

    for marker in required_markers:
        assert marker in text
