from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path


CONTRACTS_SRC = Path(__file__).resolve().parents[4] / "packages" / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in os.sys.path:
    os.sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.discoverable_entry_surface import DiscoverableEntrySurface, load_discoverable_entry_surface


@lru_cache(maxsize=1)
def load_runtime_entry_surface() -> DiscoverableEntrySurface:
    return load_discoverable_entry_surface(Path(__file__))


def _normalize_task_type(task_type: str | None) -> str:
    return str(task_type or "").strip().lower() or "planning"


def _normalize_entry_id(entry_id: str | None) -> str | None:
    normalized = str(entry_id or "").strip()
    return normalized or None


def _entry_for_id(entry_id: str | None):
    normalized = _normalize_entry_id(entry_id)
    if normalized is None:
        return None
    return load_runtime_entry_surface().entry_by_id.get(normalized)


def resolve_runtime_task_type(
    task_type: str | None,
    *,
    requested_entry_id: str | None = None,
    selected_skill: str | None = None,
) -> str:
    normalized_task_type = _normalize_task_type(task_type)
    entry = _entry_for_id(requested_entry_id) or _entry_for_id(selected_skill)
    if entry is None:
        return normalized_task_type
    return normalized_task_type


def suggest_stage_stop(entry_id: str | None) -> str:
    entry = _entry_for_id(entry_id)
    if entry is None:
        return "phase_cleanup"
    return entry.requested_stage_stop
