from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
RETRIEVAL_TASK = (
    "请使用本地安装的 $vibe 组织并完成这个纯本地检索任务：读取 "
    r"D:\Documents\vibeskills\work\blackbox-retrieval-r1 中的三个 Markdown 文件，"
    "回答当前支持哪些导出格式、用户从哪里开始导出，以及提交支持请求时必须提供什么信息。"
    "最终只在对话中给出简洁中文答案，不要创建用户交付文件，不要修改这些输入文件；"
    "允许 Vibe 在其自身运行目录写必要的治理证据。这个任务不需要写代码、测试驱动开发、"
    "构建、UI、响应式布局、Word/PDF 或正式报告。不要使用浏览器插件，也不得安装或调用 "
    "chrome、chrome-devtools、playwright、context7、claude-flow MCP。请先按 Vibe 的需求确认停点"
    "说明 L/XL 的工作方式、模块、候选 Skills、理由、代价和交付物，等待我选择后再继续。"
)

BLACKBOX_PLAN_RETRIEVAL_TASK = (
    "请使用 $vibe 组织一个纯本地、只读检索任务。最终只需在聊天中回答三个问题：一，"
    r"D:\Documents\vibeskills\Vibe-Skills-main\docs\plans\2026-07-10-vibe-agent-led-skill-discovery-cutover-execution-plan.md "
    "规定 Vibe 在 Skill 组织中的核心职责是什么；二，"
    r"D:\Documents\vibeskills\Vibe-Skills-main\docs\plans\2026-07-12-vibe-agent-execution-handoff-control-flow-repair-plan.md "
    "规定 Agent 执行交接的控制流是什么；三，"
    r"D:\Documents\vibeskills\Vibe-Skills-main\config\forbidden-mcp-policy.json "
    "明确禁止哪些 MCP。仅允许读取这三个文件，不修改任何文件，不创建报告或额外交付物，"
    "不做代码、TDD、构建、测试、UI、交互、响应式布局、Word/PDF、外部检索，也不使用 "
    "Codex 浏览器插件，不安装、推荐或调用 chrome、chrome-devtools、playwright、context7、"
    "claude-flow MCP。请先按 Vibe 流程冻结需求，清楚说明 L/XL、模块、候选 Skills、理由、"
    "代价和聊天交付物，等我确认后再进入计划；当前不能读取这三个目标文件。"
)

RESEARCH_WORD_TASK = (
    "请使用 $vibe 组织并完成这项工作：围绕“大学生睡眠不足对学业表现与心理健康的影响，"
    "以及高校可采取的干预”做一份中文证据综述，最终交付一份结构完整、可编辑的正式 Word "
    "文档。内容需要基于可靠来源，区分证据强弱，说明局限与可操作建议，文字要自然、像专业人员"
    "写的，不要模板腔。请先按 Vibe 流程和我讨论需求、工作级别、模块与会使用的 Skills，不要"
    "跳过确认直接执行。"
)

MISSING_INPUT_ANALYSIS_TASK = (
    "请使用 $vibe 组织一个缺少必需输入的失败/阻塞场景。必需的 customer_outcomes.csv "
    "尚未提供，后续只能在文件提供后分析留存率和满意度。不得编造字段、统计、图或结论，"
    "不得宣称完成。这个任务不需要代码 TDD、UI、响应式布局或 Word 质量检查。"
)

MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK = (
    "请使用本机刚安装的 [$vibe](C:\\Users\\羽裳\\.codex\\skills\\vibe\\SKILL.md) "
    "组织一个缺少必需输入的 L 级阻塞任务。批准执行后，只允许读取 "
    "`C:\\Users\\羽裳\\Documents\\Codex\\blackbox-fixtures\\release-ff16-a\\missing\\request.md`，"
    "并检查同目录所声明的必需 CSV 是否存在。若必需输入缺失，必须把相关必需模块标为 "
    "blocked，清楚告诉我缺什么以及补齐后才能做什么；不得虚构字段、统计、图表、结论或正式报告，"
    "不得宣称完成，不得执行成功清理。不要注入代码 TDD、UI、响应式布局或 Word 制作要求，"
    "也不要发明证明文件。不要使用浏览器插件，也不得安装、调用或建议 chrome、chrome-devtools、"
    "playwright、context7、claude-flow MCP。请先进入 Vibe 的需求确认停点：解释 L/XL 工作方式、"
    "模块、候选 Skills、理由、代价、依赖、预期阻塞行为和交付物；在我确认前不要读取 request.md "
    "或检查目标 CSV。"
)

DATA_ANALYSIS_NO_CODE_TASK = (
    "请使用已安装的 `$vibe` 组织完成一个 XL 候选的跨领域复合任务。输入目录是 "
    r"`C:\Users\羽裳\Documents\Codex\blackbox-fixtures\slice17-j\xl`，包含 "
    "`training_pilot.csv` 和 `data_dictionary.md`。最终需要完成数据质量审计、"
    "清洗决定、描述与组间统计分析、可复查可视化、谨慎解释、正式中文报告和独立质量复核；"
    "正式报告应为 Word 文档，并保留分析表和图。请先严格停在首次用户问询处：不要读取 CSV "
    "或数据字典正文，不要分析、制图或创建报告；先按模块讲清 L 级与 XL 级的具体工作流、"
    "候选本地 Skills、职责、依赖、并行条件、理由、代价和交付物，再等待我选择。"
    "不要把写代码 TDD、UI 或响应式布局要求注入这个数据分析任务。禁止安装、推荐或调用 "
    "chrome、chrome-devtools、playwright、context7、claude-flow MCP，也不要触碰 "
    r"`D:\Documents\vibeskills\work\thread_state.md`。"
)

MIXED_SCOPE_CODE_TASK = (
    "请分析需求并实现 Python 分类器，修改代码并添加单元测试；"
    "用户文档不要写代码示例。"
)

MIXED_SCOPE_DEBUG_TASK = (
    "请分析并修复 Python 分类器中的错误，更新实现并添加回归测试；"
    "用户文档不要写代码示例。"
)

SAME_CLAUSE_CODE_TASK = "请实现 Python 分类器并且用户文档不要写代码示例。"

PURE_NON_CODE_TASK = "不做代码"

RESEARCH_WITH_NEGATED_CODE_ACTIONS_TASK = (
    "分析并比较调查结果，更新中文报告；不做代码；不得安装运行时；不要修改源代码。"
)

SINGLE_ACTION_CODE_TASK = "请分析并实现 Python 分类器；用户文档不要写代码示例。"

REFACTOR_WITH_NON_CODE_DOCS_TASK = "Refactor the parser. No code examples in docs."

CHINESE_SINGLE_QUOTE_RETRIEVAL_TASK = "请分析‘路由修复说明.md’；不做代码。"

DEBUG_TASK_WITH_BARE_LEVEL_CHOICE = (
    "Please diagnose and fix the Python line counter bug with regression tests. "
    "Before execution, explain L XL modules, candidate Skills, costs, and deliverables."
)

GOVERNED_MISSING_INPUT_WITHOUT_CODE_WORDING = (
    "请严格使用本机已安装的 vibe 启动新的 canonical run；不得在同一轮进入 xl_plan。"
    "首次说明 L 和 XL 的工作流、模块、候选 Skills、依赖、代价和交付物。"
    "禁止安装或调用 chrome、playwright、context7 或 claude-flow MCP。"
    "必需的 retention_snapshot.csv 当前未提供；文件提供后才能汇总 cohort retention 并描述性比较 plan groups，"
    "缺失期间不得猜字段、计算统计、制图或生成报告。"
)

COMPOSITE_DATA_DELIVERY_WITHOUT_EXPLICIT_GRADE = (
    "请分析并比较社区培训数据，交付数据质量审计、保留原始值的清洗数据、QA 问题表、"
    "可复现脚本、汇总表、PNG 图表、中文 Markdown 报告和验证证据。"
    "请先讲清 L 级和 XL 级方案，再等待选择。"
)

SMALL_ANALYSIS_WITH_XL_PATH_SEGMENT = (
    r"请读取并分析 C:\fixtures\02-xl-workshops\input.csv，只在聊天中回答。"
    "请先说明 L 和 XL 的区别，再等待选择。"
)

CHINESE_DEBUG_TASK = "请调试 Python 分类器；用户文档不要写代码示例。"

MODIFIED_NEGATION_TASK = (
    "请分析调查结果并写中文报告；不做代码；不得擅自安装运行时；"
    "不要再修改源代码；Don't install packages."
)

ADD_UNIT_TEST_TASK = "请分析并添加单元测试；用户文档不要写代码示例。"

MODIFY_CODE_TASK = "请分析并修改代码；用户文档不要写代码示例。"

ENGLISH_DIAGNOSE_TASK = "Please diagnose the parser."

CHINESE_FILENAME_RETRIEVAL_TASK = (
    "请严格使用已安装的 $vibe 组织这个纯本地、只读的检索与对照回答任务。"
    "只允许读取 `C:\\Users\\羽裳\\Documents\\Codex\\blackbox-fixtures\\release-02aa-a\\retrieval` "
    "下的三个文件：`问题.md`、`路由修复说明.md`、`支持政策.md`。最终只在聊天中回答，"
    "不创建业务文件。请先讲清 L 级和 XL 级分别怎样工作，再等待我选择。"
    "这个任务明确不做代码、不做 TDD、不做构建、不做 UI 或响应式布局；"
    "文件名里的“修复”只是要读取的主题，不是代码开发要求。禁止安装、推荐或调用 "
    "chrome、chrome-devtools、playwright、context7、claude-flow MCP。"
)

EXPLICIT_XL_CANDIDATE_WITH_LEVEL_CHOICE_TASK = (
    "请组织一个 XL 候选的只读研究任务，最终只在聊天中给出分析。"
    "请先讲清 L 级和 XL 级分别怎样工作，再等待我选择。"
    "这个任务不做代码、不做 TDD、不做 UI 或响应式布局。"
)


def _powershell() -> str:
    candidates = (
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    pytest.skip("PowerShell is required for the public runtime classification test")


def _windows_powershell() -> str:
    candidate = shutil.which("powershell.exe") or shutil.which("powershell")
    if candidate and Path(candidate).exists():
        return str(Path(candidate))
    pytest.skip("Windows PowerShell is required for the UTF-8 runtime compatibility test")


def _agent_direct_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [
            {
                "module_id": "local_retrieval",
                "goal": "Read the three approved local Markdown files and answer the three questions.",
                "candidate_skill_ids": [],
                "required": True,
                "depends_on": [],
                "execution_mode": "agent_direct",
                "write_scope": "chat:final_response",
                "expected_outputs": ["A three-part chat answer grounded in the approved files."],
                "verification": ["Check each answer against the three approved local Markdown files."],
                "acceptance_criteria": [
                    {
                        "criterion_id": "three-answers-grounded",
                        "description": "All three answers are grounded in the approved local files.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the direct retrieval module serially.",
            "XL": "Use bounded waves only when independent modules justify them.",
        },
    }


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_requirement_packet(*, task: str, tmp_path: Path, run_id: str) -> dict[str, object]:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_quote(run_id)} "
            "-RequestedStageStop requirement_doc "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    return json.loads(
        Path(payload["summary"]["artifacts"]["runtime_input_packet"]).read_text(
            encoding="utf-8"
        )
    )


def test_windows_powershell_loads_the_utf8_runtime_and_classifies_chinese() -> None:
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    command = [
        _windows_powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference = 'Stop'; "
            "$OutputEncoding = [Console]::OutputEncoding = "
            "New-Object System.Text.UTF8Encoding($false); "
            f". {_ps_quote(str(common))}; "
            "$result = Get-VibeInferredTaskType -Task '请分析并比较调查结果'; "
            "[Console]::Out.Write($result)"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "research"


def test_explicit_non_code_retrieval_stays_research_l_and_has_no_tdd_plan(
    tmp_path: Path,
) -> None:
    host_decision = json.dumps(
        {"agent_skill_organization": _agent_direct_organization()},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(RETRIEVAL_TASK)} "
            "-Mode interactive_governed "
            "-RunId retrieval-classification-contract "
            "-RequestedStageStop xl_plan "
            "-RequestedGradeFloor L "
            f"-HostDecisionJson {_ps_quote(host_decision)} "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
    execution_plan = Path(summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")

    assert runtime_packet["task"] == RETRIEVAL_TASK
    assert intent_contract["source_task"] == RETRIEVAL_TASK
    assert RETRIEVAL_TASK in requirement_doc
    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert runtime_packet["internal_grade"] == "L"
    assert "## Code Task TDD Evidence Plan" not in execution_plan
    assert "## Wave Plan" not in execution_plan


def test_research_word_request_does_not_turn_generic_execution_wording_into_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(RESEARCH_WORD_TASK)} "
            "-Mode interactive_governed "
            "-RunId research-word-classification-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert runtime_packet["internal_grade"] == "L"
    assert "## Code Task TDD Mode" not in requirement_doc
    level_skills = intent_contract["workflow_level_confirmation"]["level_details"]["L"]["skills"]
    assert "tdd" not in level_skills.lower()
    assert "不会给非代码任务附加代码开发验证流程" in level_skills


def test_read_only_plan_lookup_ignores_repair_words_inside_referenced_documents(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(BLACKBOX_PLAN_RETRIEVAL_TASK)} "
            "-Mode interactive_governed "
            "-RunId read-only-plan-retrieval-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")

    assert intent_contract["source_task"] == BLACKBOX_PLAN_RETRIEVAL_TASK
    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert runtime_packet["internal_grade"] == "L"
    assert "## Code Task TDD Mode" not in requirement_doc
    level_skills = intent_contract["workflow_level_confirmation"]["level_details"]["L"]["skills"]
    assert "tdd" not in level_skills.lower()
    assert "不会给非代码任务附加代码开发验证流程" in level_skills


def test_missing_input_analysis_does_not_treat_blocked_failure_wording_as_code_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(MISSING_INPUT_ANALYSIS_TASK)} "
            "-Mode interactive_governed "
            "-RunId missing-input-non-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert "## Code Task TDD Mode" not in requirement_doc


def test_missing_input_gate_does_not_treat_no_code_injection_wording_as_code_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK)} "
            "-Mode interactive_governed "
            "-RunId missing-input-gate-no-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")

    assert runtime_packet["task"] == MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK
    assert intent_contract["source_task"] == MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK
    assert runtime_packet["route_snapshot"]["task_type"] == "planning"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert runtime_packet["internal_grade"] == "L"
    assert "## Code Task TDD Mode" not in requirement_doc
    level_skills = intent_contract["workflow_level_confirmation"]["level_details"]["L"]["skills"]
    assert "tdd" not in level_skills.lower()
    assert "不会给非代码任务附加代码开发验证流程" in level_skills


def test_data_analysis_does_not_treat_rejected_code_tdd_scope_as_coding(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(DATA_ANALYSIS_NO_CODE_TASK)} "
            "-Mode interactive_governed "
            "-RunId data-analysis-no-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor XL "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


def test_affirmative_code_work_outside_non_code_document_scope_keeps_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(MIXED_SCOPE_CODE_TASK)} "
            "-Mode interactive_governed "
            "-RunId mixed-scope-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(
        encoding="utf-8"
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "coding"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"
    assert "## Code Task TDD Mode" in requirement_doc
    assert "## Code Task TDD Evidence Requirements" in requirement_doc


def test_affirmative_debug_work_outside_non_code_document_scope_keeps_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(MIXED_SCOPE_DEBUG_TASK)} "
            "-Mode interactive_governed "
            "-RunId mixed-scope-debug-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(
        encoding="utf-8"
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "debug"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"
    assert "## Code Task TDD Mode" in requirement_doc
    assert "## Code Task TDD Evidence Requirements" in requirement_doc


def test_code_work_before_same_clause_non_code_boundary_keeps_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(SAME_CLAUSE_CODE_TASK)} "
            "-Mode interactive_governed "
            "-RunId same-clause-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "coding"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_pure_non_code_boundary_does_not_crash_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(PURE_NON_CODE_TASK)} "
            "-Mode interactive_governed "
            "-RunId pure-non-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "planning"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


def test_negated_code_actions_do_not_inflate_public_runtime_score(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(RESEARCH_WITH_NEGATED_CODE_ACTIONS_TASK)} "
            "-Mode interactive_governed "
            "-RunId negated-code-score-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


@pytest.mark.parametrize(
    ("task", "run_id"),
    (
        (
            "Analyze the data; no code, build, or install anything.",
            "negated-code-list-contract",
        ),
        (
            "Analyze the incident; do not fix or modify code.",
            "negated-debug-list-contract",
        ),
    ),
)
def test_negated_action_lists_do_not_inject_code_tdd(
    task: str,
    run_id: str,
    tmp_path: Path,
) -> None:
    packet = _run_requirement_packet(task=task, tmp_path=tmp_path, run_id=run_id)

    assert packet["route_snapshot"]["task_type"] not in {"coding", "debug"}
    assert packet["code_task_tdd_decision"]["mode"] == "not_applicable"


def test_real_code_action_outweighs_generic_analysis_in_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(SINGLE_ACTION_CODE_TASK)} "
            "-Mode interactive_governed "
            "-RunId single-action-code-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "coding"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_refactor_outside_non_code_docs_scope_keeps_tdd_in_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(REFACTOR_WITH_NON_CODE_DOCS_TASK)} "
            "-Mode interactive_governed "
            "-RunId refactor-non-code-docs-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "coding"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_chinese_single_quoted_debug_subject_stays_research_in_public_runtime(
    tmp_path: Path,
) -> None:
    task_path = tmp_path / "task.txt"
    task_path.write_text(CHINESE_SINGLE_QUOTE_RETRIEVAL_TASK, encoding="utf-8")
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$task = Get-Content -LiteralPath {_ps_quote(str(task_path))} -Raw; "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            "-Task $task "
            "-Mode interactive_governed "
            "-RunId chinese-single-quote-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["task"] == CHINESE_SINGLE_QUOTE_RETRIEVAL_TASK
    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


def test_english_diagnose_action_keeps_tdd_in_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(ENGLISH_DIAGNOSE_TASK)} "
            "-Mode interactive_governed "
            "-RunId english-diagnose-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["task"] == ENGLISH_DIAGNOSE_TASK
    assert runtime_packet["route_snapshot"]["task_type"] == "debug"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_chinese_debug_action_keeps_tdd_in_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(CHINESE_DEBUG_TASK)} "
            "-Mode interactive_governed "
            "-RunId chinese-debug-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "debug"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_modified_chinese_and_english_negation_stays_non_code_in_public_runtime(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(MODIFIED_NEGATION_TASK)} "
            "-Mode interactive_governed "
            "-RunId modified-negation-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


@pytest.mark.parametrize(
    ("task", "run_id"),
    (
        (ADD_UNIT_TEST_TASK, "add-unit-test-contract"),
        (MODIFY_CODE_TASK, "modify-code-contract"),
        ("Update analysis.py", "python-file-update-contract"),
    ),
)
def test_single_concrete_code_action_keeps_tdd_in_public_runtime(
    tmp_path: Path,
    task: str,
    run_id: str,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_quote(run_id)} "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "coding"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "required"


def test_chinese_filename_subject_does_not_turn_retrieval_into_debug_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(CHINESE_FILENAME_RETRIEVAL_TASK)} "
            "-Mode interactive_governed "
            "-RunId chinese-filename-retrieval-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )
    requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(
        encoding="utf-8"
    )

    assert runtime_packet["task"] == CHINESE_FILENAME_RETRIEVAL_TASK
    assert intent_contract["source_task"] == CHINESE_FILENAME_RETRIEVAL_TASK
    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert runtime_packet["internal_grade"] == "L"
    assert "## Code Task TDD Mode" not in requirement_doc


def test_explicit_xl_candidate_survives_l_xl_choice_wording(tmp_path: Path) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(EXPLICIT_XL_CANDIDATE_WITH_LEVEL_CHOICE_TASK)} "
            "-Mode interactive_governed "
            "-RunId explicit-xl-choice-contract "
            "-RequestedStageStop requirement_doc "
            "-RequestedGradeFloor L "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    runtime_packet = json.loads(
        Path(payload["summary"]["artifacts"]["runtime_input_packet"]).read_text(
            encoding="utf-8"
        )
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["internal_grade"] == "XL"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"


def test_bare_l_xl_choice_wording_does_not_raise_simple_debug_work_to_xl(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(DEBUG_TASK_WITH_BARE_LEVEL_CHOICE)} "
            "-Mode interactive_governed "
            "-RunId bare-l-xl-choice-contract "
            "-RequestedStageStop requirement_doc "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "debug"
    assert runtime_packet["internal_grade"] == "L"
    assert intent_contract["workflow_level_confirmation"]["recommended_level"] == "L"


def test_vibe_governance_language_does_not_turn_missing_input_analysis_into_code_tdd(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(GOVERNED_MISSING_INPUT_WITHOUT_CODE_WORDING)} "
            "-Mode interactive_governed "
            "-RunId governed-missing-input-contract "
            "-RequestedStageStop requirement_doc "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["internal_grade"] == "L"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert intent_contract["workflow_level_confirmation"]["recommended_level"] == "L"


def test_composite_data_delivery_recommends_xl_without_a_requested_floor(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(COMPOSITE_DATA_DELIVERY_WITHOUT_EXPLICIT_GRADE)} "
            "-Mode interactive_governed "
            "-RunId composite-data-natural-grade-contract "
            "-RequestedStageStop requirement_doc "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    runtime_packet = json.loads(
        Path(summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8")
    )
    intent_contract = json.loads(
        Path(summary["artifacts"]["intent_contract"]).read_text(encoding="utf-8")
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["internal_grade"] == "XL"
    assert runtime_packet["code_task_tdd_decision"]["mode"] == "not_applicable"
    assert intent_contract["workflow_level_confirmation"]["recommended_level"] == "XL"


def test_xl_inside_an_input_path_does_not_raise_a_small_analysis_to_xl(
    tmp_path: Path,
) -> None:
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {_ps_quote(str(RUNTIME_ENTRY))} "
            f"-Task {_ps_quote(SMALL_ANALYSIS_WITH_XL_PATH_SEGMENT)} "
            "-Mode interactive_governed "
            "-RunId xl-path-segment-grade-contract "
            "-RequestedStageStop requirement_doc "
            f"-ArtifactRoot {_ps_quote(str(tmp_path))}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(completed.stdout)
    runtime_packet = json.loads(
        Path(payload["summary"]["artifacts"]["runtime_input_packet"]).read_text(
            encoding="utf-8"
        )
    )

    assert runtime_packet["route_snapshot"]["task_type"] == "research"
    assert runtime_packet["internal_grade"] == "L"


def test_plain_implementation_without_non_code_wording_keeps_tdd(
    tmp_path: Path,
) -> None:
    packet = _run_requirement_packet(
        task="请分析并实现 Python 分类器",
        tmp_path=tmp_path,
        run_id="plain-implementation-contract",
    )

    assert packet["route_snapshot"]["task_type"] == "coding"
    assert packet["code_task_tdd_decision"]["mode"] == "required"


def test_plain_debug_with_supporting_actions_keeps_debug_tdd(tmp_path: Path) -> None:
    packet = _run_requirement_packet(
        task="Fix parser, update docs, add tests.",
        tmp_path=tmp_path,
        run_id="plain-debug-support-contract",
    )

    assert packet["route_snapshot"]["task_type"] == "debug"
    assert packet["code_task_tdd_decision"]["mode"] == "required"


@pytest.mark.parametrize(
    ("task", "run_id"),
    (
        ("Create a Word report", "office-word-report-contract"),
        ("Create a PDF report", "office-pdf-report-contract"),
        ("Build Excel workbook", "office-excel-workbook-contract"),
        ("Add slides", "office-slides-contract"),
        ("Modify report", "office-modify-report-contract"),
    ),
)
def test_office_deliverables_do_not_inject_code_tdd(
    task: str,
    run_id: str,
    tmp_path: Path,
) -> None:
    packet = _run_requirement_packet(task=task, tmp_path=tmp_path, run_id=run_id)

    assert packet["route_snapshot"]["task_type"] not in {"coding", "debug"}
    assert packet["code_task_tdd_decision"]["mode"] == "not_applicable"


@pytest.mark.parametrize(
    ("task", "expected_type", "run_id"),
    (
        ("请完成“实现 Python 分类器”", "coding", "quoted-implementation-contract"),
        ("请处理“修复 parser bug”", "debug", "quoted-debug-contract"),
    ),
)
def test_requested_actions_inside_chinese_quotes_keep_tdd(
    task: str,
    expected_type: str,
    run_id: str,
    tmp_path: Path,
) -> None:
    packet = _run_requirement_packet(task=task, tmp_path=tmp_path, run_id=run_id)

    assert packet["route_snapshot"]["task_type"] == expected_type
    assert packet["code_task_tdd_decision"]["mode"] == "required"


@pytest.mark.parametrize(
    ("task", "run_id"),
    (
        ("这项工作选 L 或 XL？", "workflow-choice-or-contract"),
        ("请按 L 级处理，不要升级到 XL", "explicit-l-no-escalation-contract"),
        (
            "Analyze the data, but do not produce script, chart, or report.",
            "negated-composite-delivery-contract",
        ),
        (
            "Analyze data, but do not generate a script, chart, or report.",
            "negated-generated-delivery-contract",
        ),
        (
            "Analyze data in script.md, chart.png, and report.md.",
            "delivery-filenames-contract",
        ),
    ),
)
def test_grade_mentions_and_rejected_deliverables_do_not_raise_work_to_xl(
    task: str,
    run_id: str,
    tmp_path: Path,
) -> None:
    packet = _run_requirement_packet(task=task, tmp_path=tmp_path, run_id=run_id)

    assert packet["internal_grade"] == "L"


def test_negated_parallelism_does_not_raise_public_runtime_to_xl(tmp_path: Path) -> None:
    packet = _run_requirement_packet(
        task="Run serially; do not use parallel or multi-agent execution.",
        tmp_path=tmp_path,
        run_id="negated-parallelism-contract",
    )

    assert packet["internal_grade"] != "XL"


def test_powershell_explicit_xl_accepts_terminal_punctuation() -> None:
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference = 'Stop'; "
            f". {_ps_quote(str(common))}; "
            "$result = Get-VibeInternalGrade -Task 'Choose XL.'; "
            "[Console]::Out.Write($result)"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    assert completed.stdout.strip() == "XL"


def test_powershell_router_diagnostics_accept_underscore_separators() -> None:
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    tasks = (
        "router candidate_scoring behavior",
        "router grade_selection behavior",
        "router task_classification behavior",
    )
    task_array = "@(" + ",".join(_ps_quote(task) for task in tasks) + ")"
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference = 'Stop'; "
            f". {_ps_quote(str(common))}; "
            f"$results = {task_array} | ForEach-Object {{ "
            "[pscustomobject]@{ task = $_; task_type = Get-VibeInferredTaskType -Task $_ } "
            "}; $results | ConvertTo-Json -Depth 5"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    rows = json.loads(completed.stdout)

    assert {row["task"]: row["task_type"] for row in rows} == {
        task: "debug" for task in tasks
    }


def test_powershell_grade_keeps_each_supported_single_xl_signal() -> None:
    common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
    tasks = (
        "无人值守",
        "install then verify runtime",
        "front/back",
        "parallel",
        "wave",
        "batch",
        "cross-host",
        "end-to-end",
    )
    task_array = "@(" + ",".join(_ps_quote(task) for task in tasks) + ")"
    command = [
        _powershell(),
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference = 'Stop'; "
            f". {_ps_quote(str(common))}; "
            f"$results = {task_array} | ForEach-Object {{ "
            "[pscustomobject]@{ task = $_; grade = Get-VibeInternalGrade -Task $_ } "
            "}; $results | ConvertTo-Json -Depth 5"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    rows = json.loads(completed.stdout)

    assert {row["task"]: row["grade"] for row in rows} == {task: "XL" for task in tasks}
