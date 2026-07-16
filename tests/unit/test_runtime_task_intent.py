from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

import vgo_runtime.task_intent as task_intent_module
from vgo_runtime.kernel.task_card import infer_task_type as kernel_infer_task_type
from vgo_runtime.governance import choose_internal_grade
from vgo_runtime.task_intent import infer_task_type


LOCAL_RETRIEVAL_TASK = (
    "请使用本地安装的 $vibe 组织并完成这个纯本地检索任务：读取 "
    "D:\\Documents\\vibeskills\\work\\blackbox-retrieval-r1 中的三个 Markdown 文件，"
    "回答当前支持哪些导出格式、用户从哪里开始导出，以及提交支持请求时必须提供什么信息。"
    "最终只在对话中给出简洁中文答案，不要创建用户交付文件，不要修改这些输入文件；"
    "允许 Vibe 在其自身运行目录写必要的治理证据。这个任务不需要写代码、测试驱动开发、"
    "构建、UI、响应式布局、Word/PDF 或正式报告。不要使用浏览器插件，也不得安装或调用 "
    "chrome、chrome-devtools、playwright、context7、claude-flow MCP。"
)

RESEARCH_WORD_TASK = (
    "请使用 $vibe 组织并完成这项工作：围绕“大学生睡眠不足对学业表现与心理健康的影响，"
    "以及高校可采取的干预”做一份中文证据综述，最终交付一份结构完整、可编辑的正式 Word "
    "文档。内容需要基于可靠来源，区分证据强弱，说明局限与可操作建议，文字要自然、像专业人员"
    "写的，不要模板腔。请先按 Vibe 流程和我讨论需求、工作级别、模块与会使用的 Skills，不要"
    "跳过确认直接执行。"
)

READ_ONLY_PLAN_RETRIEVAL_TASK = (
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

CHINESE_DEBUG_TASK = "请调试 Python 分类器；用户文档不要写代码示例。"

MODIFIED_NEGATION_TASK = (
    "请分析调查结果并写中文报告；不做代码；不得擅自安装运行时；"
    "不要再修改源代码；Don't install packages."
)

ADD_UNIT_TEST_TASK = "请分析并添加单元测试；用户文档不要写代码示例。"

MODIFY_CODE_TASK = "请分析并修改代码；用户文档不要写代码示例。"

ENGLISH_DIAGNOSE_TASK = "Please diagnose the parser."

GOVERNED_MISSING_INPUT_WITHOUT_CODE_WORDING = (
    "请严格使用本机已安装的 vibe 启动新的 canonical run；不得在同一轮进入 xl_plan。"
    "首次说明 L 和 XL 的工作流、模块、候选 Skills、依赖、代价和交付物。"
    "禁止安装或调用 chrome、playwright、context7 或 claude-flow MCP。"
    "必需的 retention_snapshot.csv 当前未提供；文件提供后才能汇总 cohort retention 并描述性比较 plan groups，"
    "缺失期间不得猜字段、计算统计、制图或生成报告。"
)

CHINESE_FILENAME_RETRIEVAL_TASK = (
    "请严格使用已安装的 $vibe 组织这个纯本地、只读的检索与对照回答任务。"
    "只允许读取 `C:\\Users\\羽裳\\Documents\\Codex\\blackbox-fixtures\\release-02aa-a\\retrieval` "
    "下的三个文件：`问题.md`、`路由修复说明.md`、`支持政策.md`。最终只在聊天中回答，"
    "不创建业务文件。请先讲清 L 级和 XL 级分别怎样工作，再等待我选择。"
    "这个任务明确不做代码、不做 TDD、不做构建、不做 UI 或响应式布局；"
    "文件名里的“修复”只是要读取的主题，不是代码开发要求。禁止安装、推荐或调用 "
    "chrome、chrome-devtools、playwright、context7、claude-flow MCP。"
)


def test_infer_task_type_marks_router_misroute_prompt_as_debug() -> None:
    task = "router confidence-low fallback misroute task-classification grade-selection candidate-scoring"

    assert infer_task_type(task) == "debug"


@pytest.mark.parametrize(
    "task",
    (
        "router candidate_scoring behavior",
        "router grade_selection behavior",
        "router task_classification behavior",
    ),
)
def test_infer_task_type_accepts_underscore_router_diagnostic_separators(task: str) -> None:
    assert infer_task_type(task) == "debug"


def test_infer_task_type_marks_dispatch_triage_prompt_as_debug() -> None:
    assert infer_task_type("triage runtime specialist dispatch duplication") == "debug"


def test_infer_task_type_avoids_docs_false_positive() -> None:
    assert infer_task_type("suffix cleanup in docs") == "planning"
    assert infer_task_type("codex bootstrap wording in docs") == "planning"


def test_infer_task_type_keeps_ml_pipeline_prompt_as_planning() -> None:
    assert infer_task_type("ml pipeline workflow pack artifacts for deployment") == "planning"


def test_infer_task_type_keeps_explicit_non_code_local_retrieval_as_research() -> None:
    assert infer_task_type(LOCAL_RETRIEVAL_TASK) == "research"
    assert choose_internal_grade("research", task=LOCAL_RETRIEVAL_TASK) == "L"


def test_infer_task_type_treats_evidence_review_with_word_delivery_as_research() -> None:
    assert infer_task_type(RESEARCH_WORD_TASK) == "research"


def test_infer_task_type_treats_repair_plan_filename_as_read_only_subject_matter() -> None:
    assert infer_task_type(READ_ONLY_PLAN_RETRIEVAL_TASK) == "research"
    assert choose_internal_grade("research", task=READ_ONLY_PLAN_RETRIEVAL_TASK) == "L"


def test_infer_task_type_respects_explicit_non_code_boundary_in_blocked_analysis() -> None:
    assert infer_task_type(MISSING_INPUT_ANALYSIS_TASK) == "research"


def test_infer_task_type_respects_no_code_injection_boundary_for_missing_input_gate() -> None:
    assert infer_task_type(MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK) == "planning"
    assert choose_internal_grade("planning", task=MISSING_INPUT_GATE_NO_CODE_INJECTION_TASK) == "L"


def test_infer_task_type_respects_no_code_injection_boundary_in_data_analysis() -> None:
    assert infer_task_type(DATA_ANALYSIS_NO_CODE_TASK) == "research"


def test_infer_task_type_keeps_negated_code_actions_as_non_code_analysis() -> None:
    task = "Analyze the data; no code, build, or install anything."

    assert infer_task_type(task) == "research"


def test_infer_task_type_keeps_negated_fix_actions_as_non_code_analysis() -> None:
    task = "Analyze the incident; do not fix or modify code."

    assert infer_task_type(task) == "research"


def test_infer_task_type_keeps_affirmative_code_work_outside_non_code_scope() -> None:
    assert infer_task_type(MIXED_SCOPE_CODE_TASK) == "coding"


def test_infer_task_type_keeps_affirmative_debug_work_outside_non_code_scope() -> None:
    assert infer_task_type(MIXED_SCOPE_DEBUG_TASK) == "debug"


def test_infer_task_type_keeps_code_work_before_same_clause_non_code_boundary() -> None:
    assert infer_task_type(SAME_CLAUSE_CODE_TASK) == "coding"


def test_infer_task_type_handles_pure_non_code_boundary_as_planning() -> None:
    assert infer_task_type(PURE_NON_CODE_TASK) == "planning"


def test_infer_task_type_does_not_count_negated_code_actions() -> None:
    assert infer_task_type(RESEARCH_WITH_NEGATED_CODE_ACTIONS_TASK) == "research"


def test_infer_task_type_prefers_real_code_action_over_generic_analysis() -> None:
    assert infer_task_type(SINGLE_ACTION_CODE_TASK) == "coding"


def test_infer_task_type_prefers_implementation_over_generic_analysis() -> None:
    assert infer_task_type("请分析并实现 Python 分类器") == "coding"


def test_infer_task_type_keeps_refactor_outside_non_code_docs_scope() -> None:
    assert infer_task_type(REFACTOR_WITH_NON_CODE_DOCS_TASK) == "coding"


def test_infer_task_type_ignores_debug_subject_inside_chinese_single_quotes() -> None:
    assert infer_task_type(CHINESE_SINGLE_QUOTE_RETRIEVAL_TASK) == "research"


def test_infer_task_type_recognizes_actions_inside_chinese_quotes() -> None:
    assert infer_task_type("请完成“实现 Python 分类器”") == "coding"
    assert infer_task_type("请处理“修复 parser bug”") == "debug"


def test_infer_task_type_ignores_fix_words_in_read_only_filenames() -> None:
    assert infer_task_type("请分析 `路由修复说明.md` 这个只读主题") == "research"
    assert infer_task_type("请分析‘路由修复说明.md’这个只读主题") == "research"
    assert infer_task_type("请处理‘修复说明.md’这个只读主题") != "debug"


def test_infer_task_type_recognizes_chinese_debug_action() -> None:
    assert infer_task_type(CHINESE_DEBUG_TASK) == "debug"


def test_infer_task_type_respects_modified_chinese_and_english_negation() -> None:
    assert infer_task_type(MODIFIED_NEGATION_TASK) == "research"


def test_infer_task_type_recognizes_add_unit_test_as_code_work() -> None:
    assert infer_task_type(ADD_UNIT_TEST_TASK) == "coding"


def test_infer_task_type_recognizes_modify_code_as_code_work() -> None:
    assert infer_task_type(MODIFY_CODE_TASK) == "coding"


def test_infer_task_type_recognizes_english_diagnose_action() -> None:
    assert infer_task_type(ENGLISH_DIAGNOSE_TASK) == "debug"


def test_infer_task_type_prefers_fix_over_follow_up_code_actions() -> None:
    assert infer_task_type("Fix parser, update docs, add tests.") == "debug"


def test_infer_task_type_does_not_treat_office_deliverables_as_coding() -> None:
    for task in ("Create a Word report", "Build Excel workbook", "Add slides", "Modify report"):
        assert infer_task_type(task) != "coding", task


def test_infer_task_type_treats_pdf_report_as_non_code_document_work() -> None:
    assert infer_task_type("Create a PDF report") == "planning"


def test_infer_task_type_ignores_vibe_governance_language_for_missing_input_analysis() -> None:
    assert infer_task_type(GOVERNED_MISSING_INPUT_WITHOUT_CODE_WORDING) == "research"


def test_infer_task_type_keeps_direct_code_actions_as_coding() -> None:
    assert infer_task_type("请安装运行时工作流") == "coding"
    assert infer_task_type("implement the runtime workflow") == "coding"


def test_infer_task_type_treats_python_file_update_as_coding_work() -> None:
    assert infer_task_type("Update analysis.py") == "coding"


def test_infer_task_type_ignores_debug_words_inside_referenced_chinese_filename() -> None:
    assert infer_task_type(CHINESE_FILENAME_RETRIEVAL_TASK) == "research"
    assert choose_internal_grade("research", task=CHINESE_FILENAME_RETRIEVAL_TASK) == "L"


def test_task_intent_module_delegates_to_kernel_authority() -> None:
    assert task_intent_module.infer_task_type is kernel_infer_task_type


def test_task_intent_module_is_not_documented_as_live_task_authority() -> None:
    text = Path("packages/runtime-core/src/vgo_runtime/task_intent.py").read_text(encoding="utf-8")
    assert "authoritative task understanding" not in text.lower()
