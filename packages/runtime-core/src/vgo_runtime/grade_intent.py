from __future__ import annotations

import re


_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def _marker_matches(text: str, marker: str) -> bool:
    candidate = str(marker).strip().lower()
    if not text or not candidate:
        return False
    if _CJK_PATTERN.search(candidate):
        return candidate in text
    if re.search(r"[a-z0-9]", candidate):
        parts = [re.escape(piece) for piece in re.split(r"[-_\s/]+", candidate) if piece]
        if parts:
            pattern = r"(?<![a-z0-9])" + r"[-_\s/]*".join(parts) + r"(?![a-z0-9])"
            return re.search(pattern, text) is not None
    return candidate in text


def _signal_count(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if _marker_matches(text, marker))


def suggest_internal_grade(task_type: str, task: str | None = None) -> str:
    normalized = str(task_type).strip().lower() or "planning"
    task_lower = str(task or "").strip().lower()
    xl_markers = (
        "multi-agent",
        "parallel",
        "wave",
        "batch",
        "无人值守",
        "autonomous",
        "benchmark",
        "end-to-end",
        "e2e",
        "cross-host",
        "multi-host",
        "host-native",
        "install to runtime",
        "runtime to install",
        "from install to runtime",
        "从安装到运行",
        "全链路",
        "端到端",
    )
    xl_patterns = (
        r"front.*back",
        r"install.*runtime",
        r"runtime.*install",
    )
    composite_delivery_marker_groups = (
        ("data quality audit", "quality audit", "数据质量审计", "数据审计", "质量审计"),
        ("cleaned data", "clean data", "清洗数据"),
        ("reproducible script", "analysis script", "script", "脚本"),
        ("summary table", "analysis table", "汇总表", "分析表"),
        ("png chart", "chart", "plot", "图表"),
        ("markdown report", "word report", "report", "报告"),
        ("verification evidence", "validation evidence", "验证证据"),
    )
    planning_markers = (
        "design",
        "plan",
        "architecture",
        "refactor",
        "migrate",
        "governance",
        "install",
        "integrate",
        "integration",
        "router",
        "routing",
        "runtime",
        "workflow",
        "contract",
        "regression",
        "verification",
        "threshold",
        "confidence",
        "classification",
        "candidate scoring",
        "heuristic",
        "windows",
        "规划",
        "设计",
        "治理",
        "安装",
        "运行时",
        "路由",
        "工作流",
        "契约",
        "回归",
        "验证",
        "阈值",
        "置信度",
        "分类",
        "评分",
    )
    planning_priority_markers = (
        "quality gate",
        "freshness gate",
        "prd",
        "backlog",
        "roadmap",
        "acceptance criteria",
        "user story",
        "用户故事",
        "验收标准",
    )

    workflow_choice_pattern = (
        r"(?<![a-z0-9])(?:"
        r"l(?:\s*级)?(?:\s*(?:/|\||or|and|vs\.?|与|和|或|还是)\s*|\s+)xl(?:\s*级)?"
        r"|xl(?:\s*级)?(?:\s*(?:/|\||or|and|vs\.?|与|和|或|还是)\s*|\s+)l(?:\s*级)?"
        r")(?![a-z0-9])"
    )
    workflow_choice_seen = re.search(workflow_choice_pattern, task_lower) is not None
    task_without_workflow_choice = re.sub(workflow_choice_pattern, " ", task_lower)
    task_without_workflow_choice = re.sub(
        r"(?<![a-z0-9])xl[_-]plan(?![a-z0-9])",
        " ",
        task_without_workflow_choice,
    )
    task_without_non_escalation = re.sub(
        r"(?:不要|请勿)\s*(?:升级|升到|提升)(?:\s*到|\s*为)?\s*xl(?:\s*级)?",
        " ",
        task_without_workflow_choice,
    )
    if re.search(
        r"(?<![a-z0-9\\/_\-.])xl(?![a-z0-9\\/_\-.])",
        task_without_non_escalation.rstrip("."),
    ):
        return "XL"
    task_for_xl_signals = re.sub(
        r"\bdo\s+not\s+use\b[^.!?;。！？；\r\n]*",
        " ",
        task_lower,
    )
    if task_for_xl_signals and (
        any(_marker_matches(task_for_xl_signals, marker) for marker in xl_markers)
        or any(re.search(pattern, task_for_xl_signals) for pattern in xl_patterns)
    ):
        return "XL"
    if normalized == "research":
        composite_task = re.sub(
            r"\bdo\s+not\s+(?:produce|generate)\b[^.!?;。！？；\r\n]*",
            " ",
            task_lower,
        )
        composite_task = re.sub(
            r"(?<![a-z0-9])(?:script\.md|chart\.png|report\.md)(?![a-z0-9])",
            " ",
            composite_task,
        )
        composite_delivery_count = sum(
            1
            for markers in composite_delivery_marker_groups
            if any(_marker_matches(composite_task, marker) for marker in markers)
        )
        if composite_delivery_count >= 3:
            return "XL"
    explicit_l_request_seen = re.search(
        r"(?:按|采用|使用|保持)\s*l(?:\s*级)?(?:\s*处理)?",
        task_without_non_escalation,
    ) is not None
    if workflow_choice_seen or explicit_l_request_seen:
        return "L"
    if normalized in {"coding", "debug", "review", "research"}:
        return "L"
    if task_lower and (
        _signal_count(task_lower, planning_markers) >= 2
        or any(_marker_matches(task_lower, marker) for marker in planning_priority_markers)
    ):
        return "L"
    if task and len(str(task)) > 180:
        return "L"
    return "M"
