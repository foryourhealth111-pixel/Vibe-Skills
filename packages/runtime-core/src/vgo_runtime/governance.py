from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class RuntimeGovernanceProfile:
    mode: str
    governance_scope: str = 'root_governed'
    freeze_before_requirement_doc: bool = True


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


def normalize_runtime_mode(mode: str | None) -> str:
    normalized = str(mode or 'interactive_governed').strip() or 'interactive_governed'
    if normalized != 'interactive_governed':
        raise ValueError(f'unsupported runtime mode: {mode}')
    return 'interactive_governed'


def choose_internal_grade(task_type: str, task: str | None = None) -> str:
    normalized = str(task_type).strip().lower()
    task_lower = str(task or '').strip().lower()
    xl_markers = (
        'multi-agent',
        'parallel',
        'wave',
        'batch',
        'autonomous',
        'benchmark',
        'end-to-end',
        'e2e',
        'cross-host',
        'multi-host',
        'host-native',
        'install to runtime',
        'runtime to install',
        'from install to runtime',
        '从安装到运行',
        '全链路',
        '端到端',
    )
    planning_markers = (
        'design',
        'plan',
        'architecture',
        'refactor',
        'migrate',
        'governance',
        'install',
        'integrate',
        'integration',
        'router',
        'routing',
        'runtime',
        'workflow',
        'contract',
        'regression',
        'verification',
        'threshold',
        'confidence',
        'classification',
        'candidate scoring',
        'heuristic',
        'windows',
        '规划',
        '设计',
        '治理',
        '安装',
        '运行时',
        '路由',
        '工作流',
        '契约',
        '回归',
        '验证',
        '阈值',
        '置信度',
        '分类',
        '评分',
    )
    planning_priority_markers = (
        'quality gate',
        'freshness gate',
        'prd',
        'backlog',
        'roadmap',
        'acceptance criteria',
        'user story',
        '用户故事',
        '验收标准',
    )

    if task_lower and any(_marker_matches(task_lower, marker) for marker in xl_markers):
        return 'XL'
    if normalized in {'coding', 'debug', 'review', 'research'}:
        return 'L'
    if task_lower and (
        _signal_count(task_lower, planning_markers) >= 2
        or any(_marker_matches(task_lower, marker) for marker in planning_priority_markers)
    ):
        return 'L'
    if task and len(str(task)) > 180:
        return 'L'
    return 'M'


def build_governance_profile(mode: str | None, *, governance_scope: str = 'root_governed') -> RuntimeGovernanceProfile:
    return RuntimeGovernanceProfile(
        mode=normalize_runtime_mode(mode),
        governance_scope=governance_scope or 'root_governed',
    )
