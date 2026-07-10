from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = ROOT / "SKILL.md"
INSTRUCTION_MD = ROOT / "core" / "skills" / "vibe" / "instruction.md"


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _instruction_text() -> str:
    return INSTRUCTION_MD.read_text(encoding="utf-8")


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
        "update --skills-dir <skills-dir>",
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

    assert len(text.splitlines()) <= 245
    assert "1% chance" not in text
    assert "YOU DO NOT HAVE A CHOICE" not in text
    assert "This is not negotiable" not in text


def test_vibe_skill_entry_requires_requirement_stop_reply_to_spell_out_l_xl_skills() -> None:
    text = _skill_text()

    assert "host_user_briefing" in text
    assert "selected_skill_ids" in text
    assert "workflow, selected task skills, and recommendation reason" in text
    assert "rather than echoing raw route results" in text
    assert "requirement approval and level choice in the same reply" in text
    assert "backbone of the user reply" in text
    assert "Keep the same field order" in text
    assert "Do not summarize it down to only the recommendation" in text


def test_vibe_core_instruction_locks_requirement_stop_reply_to_host_briefing() -> None:
    text = _instruction_text()

    assert "host must reuse the runtime workflow-level confirmation" in text
    assert "same field order" in text
    assert "not just the recommended level" in text

