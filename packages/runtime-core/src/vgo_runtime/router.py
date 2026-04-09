from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path

from .router_contract_support import load_json, resolve_repo_root


@dataclass(frozen=True, slots=True)
class RuntimeRoute:
    requested_skill: str | None
    router_selected_skill: str
    runtime_selected_skill: str
    task_type: str
    confirm_required: bool = False

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


_TASK_TYPE_RULES = (
    ('review', ('review', '审查', '评审')),
    ('debug', ('debug', 'bug', '错误', '修复')),
    ('research', ('research', '调研', '研究')),
    ('coding', ('implement', 'build', 'upgrade', '更新', '增强', '执行', 'extract', 'refactor', 'runtime', 'core', 'code')),
)


@lru_cache(maxsize=1)
def load_allowed_vibe_entry_ids() -> frozenset[str]:
    repo_root = resolve_repo_root(Path(__file__))
    payload = load_json(repo_root / 'config' / 'vibe-entry-surfaces.json')
    entries = payload.get('entries') or []
    allowed = frozenset(
        str(entry.get('id') or '').strip()
        for entry in entries
        if str(entry.get('id') or '').strip()
    )
    if not allowed:
        raise RuntimeError('config/vibe-entry-surfaces.json does not define any discoverable vibe entry ids')
    return allowed


def infer_task_type(task: str) -> str:
    task_lower = str(task).lower()
    for task_type, markers in _TASK_TYPE_RULES:
        if any(marker.lower() in task_lower for marker in markers):
            return task_type
    return 'planning'


def route_runtime_task(task: str, requested_skill: str | None = None) -> RuntimeRoute:
    selected_skill = str(requested_skill or 'vibe').strip() or 'vibe'
    if selected_skill not in load_allowed_vibe_entry_ids():
        raise ValueError(f'unsupported vibe entry id: {requested_skill}')
    return RuntimeRoute(
        requested_skill=requested_skill,
        router_selected_skill=selected_skill,
        runtime_selected_skill='vibe',
        task_type=infer_task_type(task),
    )
