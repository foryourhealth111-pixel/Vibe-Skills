from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = ROOT / "SKILL.md"


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def test_vibe_skill_entry_preserves_canonical_runtime_anchors() -> None:
    text = _skill_text()

    required = [
        "$vibe",
        "/vibe",
        "scripts/router/resolve-pack-route.ps1",
        "py -3 -m vgo_cli.main canonical-entry",
        "--host-decision-json-file",
        "--continue-from-run-id",
        "--bounded-reentry-token",
        "revision_delta",
        "vibe-upgrade",
        "protocols/runtime.md",
        "core/skill-contracts/v1/vibe.json",
    ]
    for needle in required:
        assert needle in text

    for artifact in (
        "host-launch-receipt.json",
        "runtime-input-packet.json",
        "governance-capsule.json",
        "stage-lineage.json",
    ):
        assert artifact in text

    for stage in (
        "skeleton_check",
        "deep_interview",
        "requirement_doc",
        "xl_plan",
        "plan_execute",
        "phase_cleanup",
    ):
        assert stage in text


def test_vibe_skill_entry_stays_sop_sized_and_avoids_overtriggering_language() -> None:
    text = _skill_text()

    assert len(text.splitlines()) <= 240
    assert "1% chance" not in text
    assert "YOU DO NOT HAVE A CHOICE" not in text
    assert "This is not negotiable" not in text

