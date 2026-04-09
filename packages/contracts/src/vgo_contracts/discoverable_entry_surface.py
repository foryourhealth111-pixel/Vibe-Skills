from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


DISCOVERABLE_ENTRY_SURFACE_RELPATH = Path('config') / 'vibe-entry-surfaces.json'


@dataclass(frozen=True, slots=True)
class DiscoverableEntry:
    id: str
    display_name: str
    requested_stage_stop: str
    allow_grade_flags: bool


@dataclass(frozen=True, slots=True)
class DiscoverableEntrySurface:
    canonical_runtime_skill: str
    entries: tuple[DiscoverableEntry, ...]
    grade_flags: list[str]
    grade_flag_map: dict[str, str]
    forbid_stage_grade_matrix: bool

    @property
    def entry_by_id(self) -> dict[str, DiscoverableEntry]:
        return {entry.id: entry for entry in self.entries}

    @property
    def projected_skill_names(self) -> list[str]:
        return [entry.id for entry in self.entries]


def resolve_discoverable_entry_surface_path(start_path: str | Path) -> Path:
    current = Path(start_path).resolve()
    if current.is_file():
        current = current.parent

    while True:
        candidate = current / DISCOVERABLE_ENTRY_SURFACE_RELPATH
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent

    raise RuntimeError(f'VGO discoverable entry surface not found from start path: {start_path}')


def load_discoverable_entry_surface(start_path: str | Path) -> DiscoverableEntrySurface:
    payload = json.loads(resolve_discoverable_entry_surface_path(start_path).read_text(encoding='utf-8-sig'))
    entries = tuple(
        DiscoverableEntry(
            id=str(entry['id']).strip(),
            display_name=str(entry['display_name']).strip(),
            requested_stage_stop=str(entry['requested_stage_stop']).strip(),
            allow_grade_flags=bool(entry['allow_grade_flags']),
        )
        for entry in payload.get('entries') or []
    )
    return DiscoverableEntrySurface(
        canonical_runtime_skill=str(payload.get('canonical_runtime_skill') or 'vibe').strip() or 'vibe',
        entries=entries,
        grade_flags=[str(flag).strip() for flag in payload.get('grade_flags') or [] if str(flag).strip()],
        grade_flag_map={
            str(flag).strip(): str(grade).strip()
            for flag, grade in (payload.get('grade_flag_map') or {}).items()
            if str(flag).strip() and str(grade).strip()
        },
        forbid_stage_grade_matrix=bool(payload.get('forbid_stage_grade_matrix')),
    )
