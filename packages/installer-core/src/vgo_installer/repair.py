from __future__ import annotations

import shutil
from pathlib import Path


def prune_previously_managed_skill_dirs(
    target_root: Path | str,
    previous_managed_skill_names: set[str] | list[str] | tuple[str, ...],
    current_managed_skill_names: set[str] | list[str] | tuple[str, ...],
) -> list[Path]:
    target_root_path = Path(target_root).resolve()
    skills_root = target_root_path / 'skills'
    if not skills_root.exists():
        return []

    removed: list[Path] = []
    previous = {str(name).strip() for name in previous_managed_skill_names if str(name).strip()}
    current = {str(name).strip() for name in current_managed_skill_names if str(name).strip()}
    for name in sorted(previous - current):
        skill_root = skills_root / name
        if skill_root.is_dir():
            shutil.rmtree(skill_root)
            removed.append(skill_root)
    return removed
