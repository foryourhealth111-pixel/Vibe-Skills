from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vibe_discoverable_entries_are_shared_and_non_explosive() -> None:
    payload = json.loads((REPO_ROOT / "config" / "vibe-entry-surfaces.json").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in payload["entries"]}

    assert set(entries) == {"vibe", "vibe-want", "vibe-how", "vibe-do"}
    assert entries["vibe"]["display_name"] == "Vibe"
    assert entries["vibe-want"]["display_name"] == "Vibe: What Do I Want?"
    assert entries["vibe-how"]["display_name"] == "Vibe: How Do We Do It?"
    assert entries["vibe-do"]["display_name"] == "Vibe: Do It"
    assert entries["vibe"]["requested_stage_stop"] == "phase_cleanup"
    assert entries["vibe-want"]["requested_stage_stop"] == "requirement_doc"
    assert entries["vibe-how"]["requested_stage_stop"] == "xl_plan"
    assert entries["vibe-do"]["requested_stage_stop"] == "phase_cleanup"
    assert entries["vibe"]["allow_grade_flags"] is True
    assert entries["vibe-want"]["allow_grade_flags"] is False
    assert entries["vibe-how"]["allow_grade_flags"] is True
    assert entries["vibe-do"]["allow_grade_flags"] is True
    assert payload["grade_flags"] == ["--l", "--xl"]
    assert payload["grade_flag_map"] == {"--l": "L", "--xl": "XL"}
    assert payload["canonical_runtime_skill"] == "vibe"
    assert payload["forbid_stage_grade_matrix"] is True
