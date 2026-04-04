from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .release_notes_quality_support import REQUIRED_HEADINGS, utc_now


def evaluate_note(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    normalized = [line.strip() for line in lines]
    todo_lines = [index + 1 for index, line in enumerate(lines) if "TODO" in line.upper()]
    headings = [line.strip() for line in lines if line.startswith("## ")]
    heading_counts = Counter(headings)
    duplicate_headings = sorted([heading for heading, count in heading_counts.items() if count > 1])
    missing_headings = [heading for heading in REQUIRED_HEADINGS if heading not in heading_counts]
    return {
        "path": str(path),
        "todo_lines": todo_lines,
        "duplicate_headings": duplicate_headings,
        "missing_headings": missing_headings,
        "headings": headings,
        "headline": normalized[0] if normalized else "",
        "passes": not todo_lines and not duplicate_headings and not missing_headings,
    }


def evaluate_release_notes(repo_root: Path, note_paths: list[Path]) -> dict[str, Any]:
    checks = [evaluate_note(path) for path in note_paths]
    failing = [item for item in checks if not item["passes"]]
    return {
        "evaluated_at": utc_now(),
        "repo_root": str(repo_root),
        "required_headings": list(REQUIRED_HEADINGS),
        "summary": {
            "gate_result": "PASS" if not failing else "FAIL",
            "note_count": len(checks),
            "failing_note_count": len(failing),
            "completion_language_allowed": len(failing) == 0,
        },
        "notes": checks,
    }
