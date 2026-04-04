from __future__ import annotations

from dataclasses import dataclass

LEGACY_MODE_ALIASES = {
    'benchmark_autonomous': 'interactive_governed',
}


@dataclass(frozen=True, slots=True)
class RuntimeGovernanceProfile:
    mode: str
    governance_scope: str = 'root_governed'
    freeze_before_requirement_doc: bool = True


def normalize_runtime_mode(mode: str | None) -> str:
    normalized = str(mode or 'interactive_governed').strip() or 'interactive_governed'
    return LEGACY_MODE_ALIASES.get(normalized, normalized)


def choose_internal_grade(task_type: str) -> str:
    normalized = str(task_type).strip().lower()
    if normalized in {'coding', 'debug', 'review', 'research'}:
        return 'L'
    return 'M'


def build_governance_profile(mode: str | None, *, governance_scope: str = 'root_governed') -> RuntimeGovernanceProfile:
    return RuntimeGovernanceProfile(
        mode=normalize_runtime_mode(mode),
        governance_scope=governance_scope or 'root_governed',
    )
