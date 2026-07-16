from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1
import re
from typing import Any

from .text_tokens import tokens_from_text


@dataclass(frozen=True, slots=True)
class TaskRevision:
    sequence: int
    prompt: str
    revision_mode: str
    added_deliverables: tuple[str, ...]
    removed_deliverables: tuple[str, ...]
    added_constraints: tuple[str, ...]
    removed_constraints: tuple[str, ...]
    added_completion_criteria: tuple[str, ...]
    removed_completion_criteria: tuple[str, ...]

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TaskCard:
    id: str
    goal: str
    deliverables: tuple[str, ...]
    constraints: tuple[str, ...]
    known_context: tuple[str, ...]
    unknowns: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    mode: str
    initial_goal: str
    accepted_revisions: tuple[TaskRevision, ...]

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


CLAUSE_SPLIT_PATTERN = re.compile(r"\s+(?:and|then)\s+|[.;]\s*")
LEADING_ARTICLE_PATTERN = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
MULTISPACE_PATTERN = re.compile(r"\s+")
CONTINUE_PREFIX_PATTERN = re.compile(r"^(?:continue\s+by\s+)", re.IGNORECASE)
_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")

DELIVERABLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?:produce|write|create|generate|prepare|provide)\s+(.+)$", re.IGNORECASE), "{value}"),
    (re.compile(r"^(?:add|adding|update|updating)\s+(.+)$", re.IGNORECASE), "{value}"),
    (re.compile(r"^(?:implement|build|change)\b", re.IGNORECASE), "code change"),
    (re.compile(r"^(?:fix|debug|repair)\b", re.IGNORECASE), "code change"),
    (re.compile(r"^(?:review|audit|inspect)\b", re.IGNORECASE), "review notes"),
    (re.compile(r"^(?:plan|design)\b", re.IGNORECASE), "implementation plan"),
    (re.compile(r"^(?:test|verify|prove)\b", re.IGNORECASE), "verification evidence"),
)

_ROUTER_DEBUG_CONTEXT_MARKERS = ("router", "routing", "misroute")
_ROUTER_DEBUG_MARKERS = (
    "fallback",
    "threshold",
    "confidence",
    "candidate-scoring",
    "grade-selection",
    "task-classification",
)

_TASK_TYPE_RULES = (
    ("review", ("review", "code review", "pr review", "audit", "assess", "审查", "评审", "审核", "代码评审")),
    (
        "debug",
        (
            "debug",
            "bug",
            "fix",
            "repair",
            "patch",
            "failure",
            "failing",
            "regression",
            "root cause",
            "diagnose",
            "diagnosed",
            "diagnosing",
            "diagnosis",
            "diagnostic",
            "diagnostics",
            "triage",
            "mismatch",
            "misroute",
            "inaccurate",
            "friction",
            "error",
            "issue",
            "problem",
            "错误",
            "修复",
            "调试",
            "问题",
            "失败",
            "报错",
            "排查",
            "定位",
            "根因",
            "回退",
            "回滚",
            "低置信度",
            "误路由",
        ),
    ),
    (
        "research",
        (
            "research",
            "survey",
            "literature",
            "paper",
            "investigate",
            "read",
            "analysis",
            "analyze",
            "compare",
            "调研",
            "研究",
            "检索",
            "分析",
            "比较",
            "梳理",
            "综述",
        ),
    ),
    (
        "coding",
        (
            "implement",
            "build",
            "upgrade",
            "update",
            "enhance",
            "modify",
            "change",
            "create",
            "add",
            "integrate",
            "integration",
            "install",
            "refactor",
            "runtime",
            "router",
            "routing",
            "code",
            "更新",
            "增强",
            "实现",
            "修改",
            "安装",
            "集成",
            "运行时",
            "路由",
            "工作流",
        ),
    ),
)

_EXPLICIT_NON_CODE_MARKERS = (
    "不需要写代码",
    "不需要代码",
    "不写代码",
    "不要写代码",
    "不要把写代码",
    "不要注入代码",
    "不做代码",
    "无需写代码",
    "does not require code",
    "no code",
    "without code",
)

_AFFIRMATIVE_DEBUG_MARKERS = (
    "debug",
    "fix",
    "repair",
    "patch",
    "triage",
    "diagnose",
    "diagnosed",
    "diagnosing",
    "修复",
    "调试",
    "排查",
    "定位",
)

_AFFIRMATIVE_CODING_MARKERS = (
    "implement",
    "build",
    "upgrade",
    "update",
    "enhance",
    "modify",
    "change",
    "create",
    "add",
    "integrate",
    "install",
    "refactor",
    "更新",
    "增强",
    "实现",
    "修改",
    "安装",
    "集成",
    "添加单元测试",
)

_STRONG_CODING_ACTION_MARKERS = (
    "implement",
    "build",
    "refactor",
    "实现",
    "添加单元测试",
    "修改代码",
)

_TASK_SCOPE_CLAUSE_SPLIT_PATTERN = re.compile(r"[。！？!?；;，,\r\n]+")
_INLINE_LITERAL_PATTERN = re.compile(r"`[^`\r\n]*`|“[^”\r\n]*”|‘[^’\r\n]*’")
_REQUESTED_QUOTED_ACTION_PATTERN = re.compile(
    r"请(?:完成|处理)\s*(?:“([^”\r\n]*)”|‘([^’\r\n]*)’)"
)
_OFFICE_DELIVERABLE_ACTION_PATTERN = re.compile(
    r"\b(?:create\s+(?:a\s+)?(?:word|pdf)\s+report|build\s+(?:an?\s+)?excel\s+workbook|"
    r"add\s+slides|modify\s+report)\b",
    re.IGNORECASE,
)
_PYTHON_FILE_EDIT_PATTERN = re.compile(
    r"\b(?:update|modify|change)\s+(?:the\s+)?[a-z0-9_./\\-]+\.py\b",
    re.IGNORECASE,
)
_ACTION_PATH_BOUNDARY_CHARS = frozenset("\\/_-.")
_ACTION_NEGATION_SUFFIXES = ("不要", "无需", "无须", "禁止", "不得", "不", "已")
_CHINESE_ACTION_NEGATION_PATTERN = re.compile(
    r"(?:不要|无需|无须|禁止|不得|不|已)"
    r"(?:再|擅自|直接|继续|主动|随意|自行|额外|重新|重复)?\s*$"
)
_ENGLISH_ACTION_NEGATION_PATTERN = re.compile(
    r"(?:\b(?:no|not|never|without|already|forbidden)\s*|"
    r"\b(?:don't|doesn't|didn't|can't|cannot|won't|shouldn't|mustn't)\s*|"
    r"\b(?:do|must|should)\s+not\s*)$"
)


def _marker_spans(text: str, marker: str) -> tuple[tuple[int, int], ...]:
    candidate = str(marker).strip().lower()
    if not text or not candidate:
        return ()
    if _CJK_PATTERN.search(candidate):
        return tuple((match.start(), match.end()) for match in re.finditer(re.escape(candidate), text))
    if re.search(r"[a-z0-9]", candidate):
        parts = [re.escape(piece) for piece in re.split(r"[-_\s/]+", candidate) if piece]
        if parts:
            pattern = r"(?<![a-z0-9])" + r"[-_\s/]*".join(parts) + r"(?![a-z0-9])"
            return tuple((match.start(), match.end()) for match in re.finditer(pattern, text))
    return tuple((match.start(), match.end()) for match in re.finditer(re.escape(candidate), text))


def _marker_matches(text: str, marker: str) -> bool:
    return bool(_marker_spans(text, marker))


def _signal_count(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if _marker_matches(text, marker))


def _without_explicit_non_code_clauses(text: str) -> str:
    filtered = text
    for marker in sorted(_EXPLICIT_NON_CODE_MARKERS, key=len, reverse=True):
        filtered = re.sub(
            rf"{re.escape(marker)}[^。！？!?；;\r\n]*",
            " ",
            filtered,
        )
    return filtered


def _affirmative_signal_count(text: str, markers: tuple[str, ...]) -> int:
    action_text = _INLINE_LITERAL_PATTERN.sub(" ", text)
    action_markers = _AFFIRMATIVE_DEBUG_MARKERS + _AFFIRMATIVE_CODING_MARKERS
    for match in _REQUESTED_QUOTED_ACTION_PATTERN.finditer(text):
        content = next(group for group in match.groups() if group is not None).strip()
        starts_with_action = any(
            any(start == 0 for start, _ in _marker_spans(content, marker))
            for marker in action_markers
        )
        if starts_with_action and not re.search(r"\.[a-z0-9]{1,10}$", content, re.IGNORECASE):
            action_text += f" {content}"
    action_text = _OFFICE_DELIVERABLE_ACTION_PATTERN.sub(" ", action_text)

    def is_affirmative(marker: str) -> bool:
        for start, end in _marker_spans(action_text, marker):
            if start > 0 and action_text[start - 1] in _ACTION_PATH_BOUNDARY_CHARS:
                continue
            if end < len(action_text) and action_text[end] in _ACTION_PATH_BOUNDARY_CHARS:
                continue
            if marker == "安装" and end < len(action_text) and action_text[end] == "的":
                continue
            prefix = action_text[:start].rstrip()
            if any(prefix.endswith(suffix) for suffix in _ACTION_NEGATION_SUFFIXES):
                continue
            if _CHINESE_ACTION_NEGATION_PATTERN.search(prefix):
                continue
            if _ENGLISH_ACTION_NEGATION_PATTERN.search(prefix):
                continue
            return True
        return False

    return sum(1 for marker in markers if is_affirmative(marker))


def infer_task_type(task: str | None) -> str:
    task_lower = str(task or "").lower()
    review_markers = _TASK_TYPE_RULES[0][1]
    debug_markers = _TASK_TYPE_RULES[1][1]
    debug_context_markers = tuple(
        marker for marker in debug_markers if marker not in _AFFIRMATIVE_DEBUG_MARKERS
    )
    research_markers = _TASK_TYPE_RULES[2][1]
    coding_markers = _TASK_TYPE_RULES[3][1]
    task_without_literals = _INLINE_LITERAL_PATTERN.sub(" ", task_lower)
    affirmative_debug_score = _affirmative_signal_count(task_lower, _AFFIRMATIVE_DEBUG_MARKERS)

    scores = {
        "review": _signal_count(task_lower, review_markers),
        "debug": max(
            _signal_count(task_without_literals, debug_context_markers),
            affirmative_debug_score,
        ),
        "research": _signal_count(task_lower, research_markers),
        "coding": _affirmative_signal_count(task_lower, _AFFIRMATIVE_CODING_MARKERS),
    }
    if _signal_count(task_without_literals, _ROUTER_DEBUG_CONTEXT_MARKERS) > 0:
        scores["debug"] = max(
            scores["debug"],
            _signal_count(task_without_literals, _ROUTER_DEBUG_MARKERS),
        )
    if (
        scores["coding"] > 0
        and scores["coding"] == scores["research"]
        and (
            _affirmative_signal_count(task_lower, _STRONG_CODING_ACTION_MARKERS) > 0
            or _PYTHON_FILE_EDIT_PATTERN.search(task_lower) is not None
        )
    ):
        scores["coding"] += 1
    if affirmative_debug_score > 0:
        scores["debug"] = max(scores["debug"], scores["coding"], affirmative_debug_score)
    explicit_non_code = _signal_count(task_lower, _EXPLICIT_NON_CODE_MARKERS) > 0
    if explicit_non_code:
        scoped_text = _without_explicit_non_code_clauses(task_lower)
        scores["coding"] = _affirmative_signal_count(
            scoped_text,
            _AFFIRMATIVE_CODING_MARKERS,
        )
        scores["debug"] = _affirmative_signal_count(
            scoped_text,
            _AFFIRMATIVE_DEBUG_MARKERS,
        )
        if (
            scores["coding"] > 0
            and scores["coding"] == scores["research"]
            and (
                _affirmative_signal_count(scoped_text, _STRONG_CODING_ACTION_MARKERS) > 0
                or _PYTHON_FILE_EDIT_PATTERN.search(scoped_text) is not None
            )
        ):
            scores["coding"] += 1
        if scores["debug"] > 0:
            scores["debug"] = max(scores["debug"], scores["coding"])
        if scores["debug"] > 0 and _signal_count(scoped_text, _ROUTER_DEBUG_CONTEXT_MARKERS) > 0:
            scores["debug"] = max(
                scores["debug"],
                _signal_count(scoped_text, _ROUTER_DEBUG_MARKERS),
            )

    max_score = max(scores.values(), default=0)
    if max_score <= 0:
        return "planning"
    for task_type in ("review", "debug", "research", "coding"):
        if scores[task_type] == max_score:
            return task_type
    return "planning"


def _normalize_text_list(values: Any, *, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"task card field {field_name!r} must be a list of strings")
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            raise ValueError(f"task card field {field_name!r} cannot contain empty values")
        normalized.append(text)
    return tuple(normalized)


def _build_task_id(goal: str) -> str:
    digest = sha1(goal.encode("utf-8")).hexdigest()[:10]
    return f"task-{digest}"


def _normalize_clause_text(value: str) -> str:
    collapsed = MULTISPACE_PATTERN.sub(" ", value.strip(" ,.;:"))
    without_continue = CONTINUE_PREFIX_PATTERN.sub("", collapsed)
    return LEADING_ARTICLE_PATTERN.sub("", without_continue).strip()


def _dedupe_texts(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return tuple(deduped)


def _infer_mode(goal: str) -> str:
    lowered = goal.casefold()
    if any(keyword in lowered for keyword in ("review", "audit", "inspect")):
        return "review"
    if any(keyword in lowered for keyword in ("report", "summary", "brief", "briefing")):
        return "reporting"
    if any(keyword in lowered for keyword in ("fix", "debug", "repair")):
        return "debug"
    if any(keyword in lowered for keyword in ("plan", "roadmap", "design", "architecture")):
        return "design"
    if any(keyword in lowered for keyword in ("test", "verify", "prove")):
        return "verification"
    if any(keyword in lowered for keyword in ("implement", "build", "add", "update", "change")):
        return "coding"
    return "general"


def _infer_deliverables(goal: str) -> tuple[str, ...]:
    inferred: list[str] = []
    for raw_clause in CLAUSE_SPLIT_PATTERN.split(goal):
        clause = _normalize_clause_text(raw_clause)
        if not clause:
            continue
        for pattern, template in DELIVERABLE_PATTERNS:
            match = pattern.match(clause)
            if match is None:
                continue
            if match.lastindex:
                value = _normalize_clause_text(match.group(1))
                if value:
                    inferred.append(template.format(value=value))
            else:
                inferred.append(template)
            break
    return _dedupe_texts(inferred)


def _infer_completion_criteria(*, goal: str, deliverables: tuple[str, ...], mode: str) -> tuple[str, ...]:
    criteria = [f"{deliverable} exists" for deliverable in deliverables]
    deliverable_tokens = {token for deliverable in deliverables for token in tokens_from_text(deliverable)}
    if "review" in deliverable_tokens or "notes" in deliverable_tokens:
        criteria.append("review findings are explicit")
    if "plan" in deliverable_tokens or "design" in deliverable_tokens:
        criteria.append("plan or design is concrete")
    if "report" in deliverable_tokens or "summary" in deliverable_tokens or "brief" in deliverable_tokens:
        criteria.append("report or summary is concrete")
    if "tests" in deliverable_tokens:
        criteria.append("tests cover the changed behavior")
    if "verification" in deliverable_tokens and "evidence" in deliverable_tokens:
        criteria.append("verification evidence is direct")
    lowered_goal = goal.casefold()
    if mode == "review":
        criteria.append("review findings are explicit")
    if mode == "design":
        criteria.append("plan or design is concrete")
    if mode == "debug":
        criteria.append("changed behavior is fixed")
    if "test" in lowered_goal and "report" not in deliverable_tokens and "summary" not in deliverable_tokens:
        criteria.append("tests cover the changed behavior")
    if any(keyword in lowered_goal for keyword in ("verify", "prove", "evidence")):
        criteria.append("verification evidence is direct")
    return _dedupe_texts(criteria)


def build_task_card(*, prompt: str, context: dict[str, object] | None = None) -> TaskCard:
    goal = str(prompt).strip()
    if not goal:
        raise ValueError("prompt must be a non-empty string")
    payload = context or {}
    deliverables = _normalize_text_list(payload.get("deliverables"), field_name="deliverables")
    inferred_mode = _infer_mode(goal)
    mode = str(payload.get("mode") or inferred_mode).strip() or inferred_mode
    if not deliverables:
        deliverables = _infer_deliverables(goal)
    completion_criteria = _normalize_text_list(payload.get("completion_criteria"), field_name="completion_criteria")
    if not completion_criteria:
        completion_criteria = _infer_completion_criteria(goal=goal, deliverables=deliverables, mode=mode)
    return TaskCard(
        id=_build_task_id(goal),
        goal=goal,
        deliverables=deliverables,
        constraints=_normalize_text_list(payload.get("constraints"), field_name="constraints"),
        known_context=_normalize_text_list(payload.get("known_context"), field_name="known_context"),
        unknowns=_normalize_text_list(payload.get("unknowns"), field_name="unknowns"),
        completion_criteria=completion_criteria,
        mode=mode,
        initial_goal=goal,
        accepted_revisions=(),
    )
