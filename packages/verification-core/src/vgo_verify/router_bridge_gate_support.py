from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root


def write_artifacts(repo_root: Path, artifact: dict[str, Any]) -> None:
    output_dir = repo_root / "outputs" / "verify"
    write_text(output_dir / "runtime-neutral-router-bridge-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# Runtime-Neutral Router Bridge Gate",
        "",
        f"- Gate Result: **{artifact['gate_result']}**",
        f"- Failures: {artifact['summary']['failures']}",
        "",
        "## Results",
        "",
    ]
    for row in artifact["results"]:
        lines.append(
            f"- `{row['id']}` -> mode=`{row['route_mode']}` pack=`{row['selected_pack']}` skill=`{row['selected_skill']}`"
        )
    lines.append("")
    write_text(output_dir / "runtime-neutral-router-bridge-gate.md", "\n".join(lines))
