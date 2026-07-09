from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vibe_discoverable_entries_are_shared_and_non_explosive() -> None:
    payload = json.loads((REPO_ROOT / "config" / "vibe-entry-surfaces.json").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in payload["entries"]}

    assert set(entries) == {"vibe"}
    assert entries["vibe"]["display_name"] == "Vibe"
    assert entries["vibe"]["requested_stage_stop"] == "phase_cleanup"
    assert entries["vibe"]["progressive_stage_stops"] == ["requirement_doc", "xl_plan", "phase_cleanup"]
    assert entries["vibe"]["allow_grade_flags"] is True
    assert entries["vibe"]["publicly_exposed"] is True
    assert payload["grade_flags"] == ["--l", "--xl"]
    assert payload["grade_flag_map"] == {"--l": "L", "--xl": "XL"}
    assert payload["canonical_runtime_skill"] == "vibe"
    assert payload["forbid_stage_grade_matrix"] is True
