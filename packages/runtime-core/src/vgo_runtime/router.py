from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
import re

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


_CJK_PATTERN = re.compile(r'[\u3400-\u9fff]')


def _marker_matches(text: str, marker: str) -> bool:
    candidate = str(marker).strip().lower()
    if not text or not candidate:
        return False
    if _CJK_PATTERN.search(candidate):
        return candidate in text
    if re.search(r'[a-z0-9]', candidate):
        parts = [re.escape(piece) for piece in re.split(r'[-_\s/]+', candidate) if piece]
        if parts:
            pattern = r'(?<![a-z0-9])' + r'[-_\s/]*'.join(parts) + r'(?![a-z0-9])'
            return re.search(pattern, text) is not None
    return candidate in text


def _signal_count(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if _marker_matches(text, marker))


_ROUTER_DEBUG_CONTEXT_MARKERS = ('router', 'routing', 'misroute')
_ROUTER_DEBUG_MARKERS = (
    'fallback',
    'threshold',
    'confidence',
    'candidate-scoring',
    'grade-selection',
    'task-classification',
)


_TASK_TYPE_RULES = (
    ('review', ('review', 'code review', 'pr review', 'audit', 'assess', '审查', '评审', '审核', '代码评审')),
        (
            'debug',
            (
                'debug',
                'bug',
            'fix',
            'repair',
            'patch',
                'failure',
                'failing',
                'regression',
                'root cause',
                'diagnos',
                'triage',
                'mismatch',
                'misroute',
                'inaccurate',
                'friction',
                'error',
            'issue',
            'problem',
            '错误',
            '修复',
            '问题',
            '失败',
            '报错',
            '排查',
            '定位',
            '根因',
            '回退',
            '回滚',
            '低置信度',
            '误路由',
        ),
    ),
    ('research', ('research', 'survey', 'literature', 'paper', 'investigate', '调研', '研究')),
        (
            'coding',
            (
                'implement',
                'build',
            'upgrade',
            'update',
            'enhance',
                'modify',
                'change',
                'create',
                'add',
                'integrate',
                'integration',
                'install',
                'extract',
                'refactor',
                'runtime',
                'router',
                'routing',
                'code',
            '更新',
            '增强',
            '执行',
            '修改',
            '安装',
            '集成',
            '运行时',
            '路由',
            '工作流',
        ),
    ),
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


@lru_cache(maxsize=1)
def load_canonical_vibe_entry_id() -> str:
    repo_root = resolve_repo_root(Path(__file__))
    payload = load_json(repo_root / 'config' / 'vibe-entry-surfaces.json')
    canonical = str(payload.get('canonical_runtime_skill') or 'vibe').strip() or 'vibe'
    return canonical


def infer_task_type(task: str) -> str:
    task_lower = str(task).lower()
    review_markers = _TASK_TYPE_RULES[0][1]
    debug_markers = _TASK_TYPE_RULES[1][1]
    research_markers = _TASK_TYPE_RULES[2][1]
    coding_markers = _TASK_TYPE_RULES[3][1]

    scores = {
        'review': _signal_count(task_lower, review_markers),
        'debug': _signal_count(task_lower, debug_markers),
        'research': _signal_count(task_lower, research_markers),
        'coding': _signal_count(task_lower, coding_markers),
    }
    if _signal_count(task_lower, _ROUTER_DEBUG_CONTEXT_MARKERS) > 0:
        scores['debug'] = max(scores['debug'], _signal_count(task_lower, _ROUTER_DEBUG_MARKERS))

    max_score = max(scores.values(), default=0)
    if max_score <= 0:
        return 'planning'
    for task_type in ('review', 'debug', 'research', 'coding'):
        if scores[task_type] == max_score:
            return task_type
    return 'planning'


def route_runtime_task(task: str, requested_skill: str | None = None) -> RuntimeRoute:
    requested_entry = str(requested_skill or '').strip() or None
    if requested_entry and requested_entry not in load_allowed_vibe_entry_ids():
        raise ValueError(f'unsupported vibe entry id: {requested_skill}')
    selected_skill = load_canonical_vibe_entry_id()
    return RuntimeRoute(
        requested_skill=requested_entry,
        router_selected_skill=selected_skill,
        runtime_selected_skill=selected_skill,
        task_type=infer_task_type(task),
    )
