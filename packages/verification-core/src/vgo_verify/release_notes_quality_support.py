from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._io import utc_now, write_text
from ._repo import resolve_repo_root


REQUIRED_HEADINGS = ["## Highlights", "## Validation Notes", "## Migration Notes"]


def load_governance(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / "config" / "version-governance.json").read_text(encoding="utf-8-sig"))


def default_release_note_path(repo_root: Path) -> Path:
    governance = load_governance(repo_root)
    version = str((governance.get("release") or {}).get("version") or "").strip()
    if not version:
        raise RuntimeError("release.version is missing from config/version-governance.json")
    return repo_root / "docs" / "releases" / f"v{version}.md"


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    json_path = output_root / "vibe-release-notes-quality-gate.json"
    md_path = output_root / "vibe-release-notes-quality-gate.md"
    write_text(json_path, json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# Vibe Release Notes Quality Gate",
        "",
        f"- Gate Result: **{artifact['summary']['gate_result']}**",
        f"- Notes Checked: `{artifact['summary']['note_count']}`",
        f"- Failing Notes: `{artifact['summary']['failing_note_count']}`",
        "",
        "## Notes",
        "",
    ]
    for item in artifact["notes"]:
        lines.append(f"- `{item['path']}` passes=`{item['passes']}`")
        if item["todo_lines"]:
            lines.append(f"  todo_lines={item['todo_lines']}")
        if item["duplicate_headings"]:
            lines.append(f"  duplicate_headings={item['duplicate_headings']}")
        if item["missing_headings"]:
            lines.append(f"  missing_headings={item['missing_headings']}")
    write_text(md_path, "\n".join(lines) + "\n")
