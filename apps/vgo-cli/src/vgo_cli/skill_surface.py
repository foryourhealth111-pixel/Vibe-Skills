from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from .errors import CliError


def resolve_codex_duplicate_skill_root(target_root: Path, host_id: str) -> Path | None:
    if host_id != 'codex' or target_root.name.lower() != '.codex':
        return None
    parent = target_root.parent
    if parent == target_root:
        return None
    return parent / '.agents' / 'skills' / 'vibe'


def is_vibe_skill_dir(root: Path) -> bool:
    skill_md = root / 'SKILL.md'
    if not skill_md.exists():
        return False
    return 'name: vibe' in skill_md.read_text(encoding='utf-8', errors='ignore')


def quarantine_codex_duplicate_skill_surface(target_root: Path, host_id: str) -> None:
    duplicate_root = resolve_codex_duplicate_skill_root(target_root, host_id)
    if duplicate_root is None or not duplicate_root.is_dir():
        return
    target_skill_root = target_root / 'skills' / 'vibe'
    if not target_skill_root.is_dir():
        return
    if duplicate_root.resolve() == target_skill_root.resolve():
        return
    if not is_vibe_skill_dir(duplicate_root):
        raise CliError(
            f"Duplicate Codex-discovered skill surface exists at '{duplicate_root}', but it is not a recognizable vibe skill copy."
        )
    quarantine_root = duplicate_root.parent.parent / 'skills-disabled'
    quarantine_root.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now().strftime('%Y%m%dT%H%M%S')
    quarantine_path = quarantine_root / f'vibe.codex-duplicate-{suffix}'
    shutil.move(str(duplicate_root), str(quarantine_path))
    print(f'[WARN] Quarantined duplicate Codex-discovered vibe skill: {duplicate_root} -> {quarantine_path}')
