from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ManagedSkillInventory:
    required_runtime_skills: tuple[str, ...]
    required_workflow_skills: tuple[str, ...]
    optional_workflow_skills: tuple[str, ...]

    @property
    def required_skill_names(self) -> tuple[str, ...]:
        return self.required_runtime_skills + self.required_workflow_skills

    @property
    def desired_managed_skill_names(self) -> tuple[str, ...]:
        return self.required_skill_names + self.optional_workflow_skills


def canonical_vibe_skill_name(packaging: dict) -> str:
    relpath = str(
        packaging.get('canonical_vibe_payload', {}).get('target_relpath')
        or packaging.get('canonical_vibe_mirror', {}).get('target_relpath')
        or 'skills/vibe'
    )
    return Path(relpath).name


def _normalize_skill_names(values: object) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in values or []:
        name = str(raw).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return tuple(normalized)


def load_managed_skill_inventory(packaging: dict) -> ManagedSkillInventory:
    inventory = packaging.get('managed_skill_inventory')
    if not isinstance(inventory, dict):
        raise SystemExit('Runtime-core packaging manifest missing managed_skill_inventory contract.')

    canonical_vibe = canonical_vibe_skill_name(packaging)
    required_runtime = list(_normalize_skill_names(inventory.get('required_runtime_skills')))
    if canonical_vibe not in required_runtime:
        required_runtime.insert(0, canonical_vibe)

    required_runtime_tuple = tuple(required_runtime)
    required_workflow_tuple = tuple(
        name for name in _normalize_skill_names(inventory.get('required_workflow_skills'))
        if name not in required_runtime_tuple
    )
    optional_workflow_tuple = tuple(
        name for name in _normalize_skill_names(inventory.get('optional_workflow_skills'))
        if name not in required_runtime_tuple and name not in required_workflow_tuple
    )

    return ManagedSkillInventory(
        required_runtime_skills=required_runtime_tuple,
        required_workflow_skills=required_workflow_tuple,
        optional_workflow_skills=optional_workflow_tuple,
    )
