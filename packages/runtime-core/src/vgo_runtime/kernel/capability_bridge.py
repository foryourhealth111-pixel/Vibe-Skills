from __future__ import annotations


def _dedupe_hints(*groups: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    hints: list[str] = []
    for group in groups:
        for hint in group:
            text = str(hint)
            if not text or text in seen:
                continue
            seen.add(text)
            hints.append(text)
    return tuple(hints)


CAPABILITY_BRIDGE = (
    (
        "architecture.domain_model",
        {
            "prompt_hints": ("domain model", "ubiquitous language", "bounded context", "领域模型", "统一语言"),
            "skill_inference_hints": ("domain-modeling", "domain model", "ubiquitous language", "bounded context", "领域模型", "统一语言"),
        },
    ),
    (
        "architecture.interface_design",
        {
            "prompt_hints": ("module interface", "interface design", "service boundary", "seam design", "模块接口", "边界设计", "设计接口"),
            "skill_inference_hints": ("codebase-design", "module interface", "interface design", "deep modules", "service boundary", "seam", "模块接口", "边界设计"),
        },
    ),
    (
        "chem.activity_database",
        {
            "prompt_hints": ("chembl", "ic50", "assay", "bioactivity", "活性数据"),
            "skill_inference_hints": ("chembl", "ic50", "assay", "bioactivity", "activity data"),
        },
    ),
    (
        "chem.medchem_filtering",
        {
            "prompt_hints": ("medicinal chemistry", "drug-likeness", "lipinski", "pains", "lead optimization", "药物化学", "先导化合物", "先导优化"),
            "skill_inference_hints": ("medicinal chemistry", "drug-likeness", "lipinski", "pains", "lead optimization", "药物化学", "先导化合物", "先导优化"),
        },
    ),
    (
        "clinical.case_report",
        {
            "prompt_hints": ("clinical report", "care guidelines", "case report", "hipaa", "de-identification", "病例报告", "去标识化"),
            "skill_inference_hints": ("clinical report", "care guidelines", "case report", "hipaa", "de-identification", "病例报告", "去标识化"),
        },
    ),
    (
        "data.eda",
        {
            "prompt_hints": ("eda", "exploratory", "exploratory analysis", "exploratory data analysis", "探索", "探索性"),
            "skill_inference_hints": ("eda", "exploratory", "exploratory analysis", "exploratory data analysis"),
        },
    ),
    (
        "data.quality_check",
        {
            "prompt_hints": ("data quality", "quality check", "missing", "duplicate", "outlier", "数据质量", "缺失", "重复", "异常"),
            "skill_inference_hints": ("data quality", "quality check", "diagnostic", "missing", "duplicate", "outlier"),
        },
    ),
    (
        "debug.systematic_workflow",
        {
            "prompt_hints": ("debug systematically", "failing test", "failing tests", "stack trace", "stack traces", "debug workflow", "slow page", "slow pages", "系统化调试", "错误日志", "排查", "测试失败", "构建失败", "接口失败", "运行失败"),
            "skill_inference_hints": ("diagnose", "diagnosing-bugs", "diagnosis loop", "hard bugs", "debug", "systematic-debugging", "systematic debugging", "debugging test", "debug workflow", "failing tests", "stack traces", "slow pages", "调试"),
        },
    ),
    (
        "docs.deep_reading",
        {
            "prompt_hints": ("deep reading", "read this rfc", "long-form content", "technical rfc", "精读", "长文档", "技术文档"),
            "skill_inference_hints": ("deep-reading-analyst", "deep reading", "deep analysis", "long-form content", "technical rfc", "精读"),
        },
    ),
    (
        "runtime.feature_delivery",
        {
            "prompt_hints": (
                "build game",
                "build app",
                "build tool",
                "build service",
                "build script",
                "build cli",
                "runnable demo",
                "interactive demo",
                "shipping feature",
                "构建游戏",
                "做一个游戏",
                "做个工具",
                "可运行演示",
                "开发一个应用",
                "实现一个工具",
            ),
            "skill_inference_hints": (
                "implement a piece of work",
                "based on a prd or set of issues",
                "feature delivery",
                "shipping feature",
            ),
        },
    ),
    (
        "frontend.build",
        {
            "prompt_hints": (
                "frontend",
                "front-end",
                "react frontend",
                "next.js frontend",
                "dashboard frontend",
                "data dashboard",
                "ui app",
                "前端",
                "看板前端",
                "数据看板",
                "网页界面",
            ),
            "skill_inference_hints": (
                "frontend",
                "front-end",
                "react",
                "next.js",
                "ui app",
                "web ui",
                "前端",
                "看板前端",
            ),
        },
    ),
    (
        "deploy.preview",
        {
            "prompt_hints": (
                "preview deployment",
                "preview deploy",
                "preview environment",
                "preview env",
                "preview link",
                "部署 preview",
                "preview 部署",
                "预览部署",
                "预览环境",
            ),
            "skill_inference_hints": (
                "preview deployment",
                "preview deploy",
                "preview link",
                "preview environment",
                "部署 preview",
                "预览部署",
            ),
        },
    ),
    (
        "deploy.netlify",
        {
            "prompt_hints": ("netlify", "deploy to netlify", "部署到netlify"),
            "skill_inference_hints": ("netlify", "preview link", "deploy to netlify"),
        },
    ),
    (
        "deploy.vercel",
        {
            "prompt_hints": ("vercel", "deploy to vercel", "部署到vercel"),
            "skill_inference_hints": ("vercel", "preview deployment", "deploy to vercel"),
        },
    ),
    (
        "devops.github_actions_ci",
        {
            "prompt_hints": ("github actions", "ci failure", "ci失败", "workflow logs", "pr checks"),
            "skill_inference_hints": ("github actions", "failing github pr checks", "pr checks", "workflow logs", "ci failure"),
        },
    ),
    (
        "devops.mcp_integration",
        {
            "prompt_hints": ("mcp", "model context protocol", ".mcp.json", "mcp server", "mcp integration"),
            "skill_inference_hints": ("mcp", "model context protocol", ".mcp.json", "mcp server", "mcp integration"),
        },
    ),
    (
        "document.latex_submission",
        {
            "prompt_hints": ("latex", "latexmk", "chktex", "latexindent", "submission zip", "manuscript pdf"),
            "skill_inference_hints": ("latex", "latexmk", "chktex", "latexindent", "submission zip", "manuscript pdf"),
        },
    ),
    (
        "document.venue_template",
        {
            "prompt_hints": ("venue template", "venue-specific", "author guidelines", "page limits", "anonymity rules", "formatting requirements", "submission compliance", "neurips", "模板", "匿名投稿", "投稿格式"),
            "skill_inference_hints": ("venue-specific templates", "author guidelines", "page limits", "anonymity rules", "formatting requirements", "submission compliance", "模板", "匿名投稿"),
        },
    ),
    (
        "model.data_leakage_guard",
        {
            "prompt_hints": ("data leakage", "fit before split", "prediction time", "train-test split", "train test split", "数据泄漏"),
            "skill_inference_hints": ("data leakage", "fit before split", "prediction time", "train-test split", "train test split", "leakage"),
        },
    ),
    (
        "model.evaluation",
        {
            "prompt_hints": ("model evaluation", "evaluate model", "metrics", "cross validation", "模型评估", "交叉验证"),
            "skill_inference_hints": ("model evaluation", "metrics", "cross validation"),
        },
    ),
    (
        "model.explainability",
        {
            "prompt_hints": ("shap", "explain", "explanation", "interpretation", "importance", "解释", "可解释", "重要性"),
            "skill_inference_hints": ("shap", "model explanation", "feature importance", "explainability", "interpretation"),
        },
    ),
    (
        "model.preprocessing_pipeline",
        {
            "prompt_hints": ("data preprocessing pipeline", "preprocessing pipeline", "feature encoding", "standardize data", "validate input data", "预处理流水线", "清洗数据"),
            "skill_inference_hints": ("preprocessing pipeline", "data preprocessing pipeline", "cleaning", "encoding", "transforming", "validating input data", "input-preparation pipelines"),
        },
    ),
    (
        "model.training",
        {
            "prompt_hints": ("prediction model", "predictive model", "machine learning", "scikit-learn", "train model", "训练模型", "预测模型", "机器学习"),
            "skill_inference_hints": ("machine learning", "model training", "predictive model", "prediction model", "scikit-learn"),
        },
    ),
    (
        "observability.sentry",
        {
            "prompt_hints": ("sentry", "production error", "线上报错", "线上告警"),
            "skill_inference_hints": ("sentry", "production error", "production errors", "线上报错", "线上告警"),
        },
    ),
    (
        "presentation.deck",
        {
            "prompt_hints": ("ppt", "pptx", "slide", "slides", "deck", "presentation", "幻灯片", "演示文稿", "组会汇报", "汇报"),
            "skill_inference_hints": ("ppt", "pptx", "slides", "deck", "slide deck", "presentation deck"),
        },
    ),
    (
        "presentation.poster",
        {
            "prompt_hints": ("research poster", "academic poster", "conference poster", "poster", "海报", "学术海报"),
            "skill_inference_hints": ("research poster", "academic poster", "conference poster", "poster", "海报", "学术海报"),
        },
    ),
    (
        "presentation.pptx_poster",
        {
            "prompt_hints": ("pptx poster", "powerpoint poster", "ppt poster", "pptx 学术海报", "powerpoint pptx"),
            "skill_inference_hints": ("pptx poster", "powerpoint poster", "ppt poster", "pptx 学术海报", "powerpoint pptx"),
        },
    ),
    (
        "presentation.slidev",
        {
            "prompt_hints": ("slidev", "marp", "reveal.js", "可复现导出"),
            "skill_inference_hints": ("slidev", "marp", "reveal.js", "reproducible export", "可复现导出"),
        },
    ),
    (
        "performance.gpu_migration",
        {
            "prompt_hints": ("gpu acceleration", "cuda acceleration", "migrate to gpu", "gpu migration", "迁移到 gpu", "cuda 加速", "gpu 加速"),
            "skill_inference_hints": ("optimize-for-gpu", "gpu optimization", "cuda", "gpu acceleration", "migrate to gpu", "gpu migration", "迁移到 gpu", "cuda 加速"),
        },
    ),
    (
        "performance.regression_debugging",
        {
            "prompt_hints": ("performance regression", "slow page", "slow pages", "latency regression", "卡顿", "性能回归", "性能退化", "性能变差"),
            "skill_inference_hints": ("diagnose", "diagnosing-bugs", "performance regression", "performance regressions", "slow", "卡顿", "性能回退", "性能变差"),
        },
    ),
    (
        "planning.issue_breakdown",
        {
            "prompt_hints": ("issue breakdown", "task breakdown", "create issues", "拆分 issues", "任务拆分", "issues"),
            "skill_inference_hints": ("to-issues", "issue breakdown", "task breakdown", "create issues", "拆分 issues", "任务拆分"),
        },
    ),
    (
        "planning.prd",
        {
            "prompt_hints": ("prd", "product requirements doc", "requirements doc", "需求文档", "产品需求"),
            "skill_inference_hints": ("to-prd", "product requirements", "product requirements doc", "requirements doc", "需求文档", "产品需求"),
        },
    ),
    (
        "prototype.throwaway_validation",
        {
            "prompt_hints": ("throwaway prototype", "prototype validation", "small prototype", "spike", "原型验证", "快速原型"),
            "skill_inference_hints": ("prototype", "throwaway prototype", "spike", "design question", "原型验证", "快速原型"),
        },
    ),
    (
        "reasoning.first_principles",
        {
            "prompt_hints": ("first principles", "hidden assumption", "challenge assumptions", "第一性原理", "隐藏假设"),
            "skill_inference_hints": ("first-principles-explorer", "first principles", "challenge assumptions", "第一性原理", "隐藏假设"),
        },
    ),
    (
        "quality.test_report",
        {
            "prompt_hints": ("pytest", "coverage", "test report", "test reports", "测试报告", "失败摘要", "覆盖率", "质量门禁"),
            "skill_inference_hints": ("test reports", "test-result packaging", "pass/fail rollups", "coverage summaries", "pytest", "coverage"),
        },
    ),
    (
        "research.causal_analysis",
        {
            "prompt_hints": ("causal analysis", "causal effect", "treatment effect", "did", "synthetic control", "因果分析", "因果效应", "稳健性检验"),
            "skill_inference_hints": ("causal analysis", "causal effects", "treatment-effect", "treatment effects", "did", "synthetic control", "因果分析", "因果效应"),
        },
    ),
    (
        "research.citation_management",
        {
            "prompt_hints": ("citation management", "bibliography", "bibtex", "doi", "参考文献"),
            "skill_inference_hints": ("citation management", "bibliography", "bibtex", "doi", "参考文献"),
        },
    ),
    (
        "research.critical_appraisal",
        {
            "prompt_hints": ("critical appraisal", "critical thinking", "bias", "confounding", "批判性", "证据强度", "偏倚", "混杂"),
            "skill_inference_hints": ("critical thinking", "critical appraisal", "bias", "confounding", "证据强度", "偏倚", "混杂"),
        },
    ),
    (
        "research.deep_research",
        {
            "prompt_hints": ("webthinker", "deep research", "multi-hop", "trace.jsonl", "sources.json", "多跳浏览", "证据链"),
            "skill_inference_hints": ("webthinker", "deep research", "multi-hop", "trace.jsonl", "sources.json"),
        },
    ),
    (
        "research.evidence_retrieval",
        {
            "prompt_hints": ("flashrag", "evidence retrieval", "repo/config", "证据检索", "文件和行号"),
            "skill_inference_hints": ("flashrag", "evidence retrieval", "repo/config", "file and line"),
        },
    ),
    (
        "research.experimental_design",
        {
            "prompt_hints": ("experiment design", "study design", "quasi-experiment", "design experiments", "设计准实验", "准实验方案", "实验设计", "实验失败", "验证实验", "设计下一轮"),
            "skill_inference_hints": ("designing-experiments", "experiment design", "study design", "quasi-experiment", "quasi-experiments", "实验设计", "准实验"),
        },
    ),
    (
        "research.hypothesis_generation",
        {
            "prompt_hints": ("hypothesis generation", "testable hypothesis", "hypogenic", "generate hypotheses", "科研假设", "可检验假设", "研究假设"),
            "skill_inference_hints": ("hypothesis-generation", "testable hypotheses", "hypothesis generation", "hypogenic", "generate hypotheses", "科研假设", "可检验假设"),
        },
    ),
    (
        "research.ideation",
        {
            "prompt_hints": ("scientific ideation", "research gaps", "literature matrix", "paper-combination", "a+b", "科研构思", "头脑风暴", "研究方向", "论文组合矩阵", "研究创新点"),
            "skill_inference_hints": ("scientific ideation", "research gaps", "mechanism exploration", "research directions", "literature matrix", "paper-combination", "a+b idea"),
        },
    ),
    (
        "science.methodology_audit",
        {
            "prompt_hints": ("methodology", "evidence quality", "experimental design audit", "bias", "confounding", "统计方法", "方法学", "偏倚", "混杂"),
            "skill_inference_hints": ("scientific-critical-thinking", "methodology", "evidence quality", "experimental design", "bias", "confounding", "方法学", "偏倚", "混杂"),
        },
    ),
    (
        "research.literature_review",
        {
            "prompt_hints": ("full-text", "systematic review", "literature review", "meta-analysis", "evidence table", "biorxiv", "preprint", "preprints", "系统综述", "文献综述", "证据表", "样本量", "方法学细节"),
            "skill_inference_hints": (
                "literature-review",
                "systematic literature review",
                "meta-analysis",
                "evidence table",
                "full-text",
                "systematic review",
                "capture the findings",
                "synthesize findings",
            ),
        },
    ),
    (
        "research.literature_search",
        {
            "prompt_hints": ("pubmed", "bibtex", "literature search", "文献检索", "检索文献", "查文献", "搜文献"),
            "skill_inference_hints": (
                "pubmed",
                "bibtex",
                "citation management",
                "literature search",
                "文献检索",
                "primary sources",
                "high-trust primary sources",
                "topic researched",
                "reading legwork",
            ),
        },
    ),
    (
        "research.pubmed_search",
        {
            "prompt_hints": ("pubmed", "mesh term", "mesh terms", "pubmed mesh"),
            "skill_inference_hints": ("pubmed", "mesh term", "mesh terms", "pubmed mesh"),
        },
    ),
    (
        "research.scholar_evaluation",
        {
            "prompt_hints": ("scholareval", "rubric", "formulation", "methodology"),
            "skill_inference_hints": ("scholareval", "rubric", "formulation", "methodology"),
        },
    ),
    (
        "research.zotero_management",
        {
            "prompt_hints": ("pyzotero", "zotero library", "zotero"),
            "skill_inference_hints": ("pyzotero", "zotero library", "zotero"),
        },
    ),
    (
        "runtime.node_zombie_cleanup",
        {
            "prompt_hints": ("zombie node", "僵尸node", "node process", "node进程"),
            "skill_inference_hints": ("zombie node", "zombie node processes", "僵尸node", "node process"),
        },
    ),
    (
        "statistics.correlation",
        {
            "prompt_hints": ("correlation", "correlate", "relationship", "trend", "相关", "关联", "趋势"),
            "skill_inference_hints": ("statistical analysis", "统计分析", "correlation", "correlate"),
        },
    ),
    (
        "statistics.regression",
        {
            "prompt_hints": (
                "regression analysis",
                "linear regression",
                "logistic regression",
                "regression model",
                "回归分析",
                "线性回归",
                "逻辑回归",
                "回归模型",
            ),
            "skill_inference_hints": ("statistical analysis", "统计分析", "regression", "linear model"),
        },
    ),
    (
        "statistics.test_selection_or_result_check",
        {
            "prompt_hints": ("statistical method", "statistical test", "statistical tests", "test selection", "hypothesis test", "hypothesis tests", "power analysis", "统计方法", "统计检验", "检验选择", "结果检查"),
            "skill_inference_hints": ("statistical-analysis", "statistical analysis", "test selection", "hypothesis check", "power analysis", "统计方法", "检验选择", "假设检查"),
        },
    ),
    (
        "statistics.relationship_modeling",
        {
            "prompt_hints": ("relationship", "relation", "impact", "effect", "compare", "关系", "影响", "比较"),
            "skill_inference_hints": ("statistical analysis", "统计分析", "relationship", "relation", "impact", "effect", "compare"),
        },
    ),
    (
        "vision.error_analysis",
        {
            "prompt_hints": ("object detection", "false positive", "false negative", "small object", "mAP", "误检", "漏检", "小目标", "目标检测", "标注"),
            "skill_inference_hints": ("senior-computer-vision", "computer vision", "object detection", "mAP", "false positive", "false negative", "小目标", "目标检测"),
        },
    ),
    (
        "vision.training_strategy",
        {
            "prompt_hints": ("training strategy", "detection training", "augmentation", "mAP", "训练策略", "检测训练"),
            "skill_inference_hints": ("senior-computer-vision", "training strategy", "object detection", "YOLO", "DETR", "mAP", "训练策略"),
        },
    ),
    (
        "visualization.figure",
        {
            "prompt_hints": ("figure", "figures", "chart", "plot", "visual", "matplotlib", "tiff", "图表", "作图", "可视化", "科研绘图", "多子图", "结果图", "投稿图", "绘制", "成图"),
            "skill_inference_hints": ("figure", "chart", "plot", "graph", "visualization"),
        },
    ),
    (
        "visualization.infographic",
        {
            "prompt_hints": ("infographic", "infographics", "visual summary", "信息图"),
            "skill_inference_hints": ("infographic", "infographics", "visual summary", "信息图"),
        },
    ),
    (
        "visualization.schematic",
        {
            "prompt_hints": ("schematic", "schematics", "diagram", "diagrams", "flowchart", "flowcharts", "示意图", "流程图", "机制图"),
            "skill_inference_hints": ("schematic", "schematics", "diagram", "diagrams", "flowchart", "flowcharts", "示意图", "流程图"),
        },
    ),
    (
        "writing.reader_report",
        {
            "prompt_hints": ("reader report", "plain language summary", "ordinary reader", "普通读者", "通俗", "说人话"),
            "skill_inference_hints": (
                "reader report",
                "reader brief",
                "ordinary reader",
                "plain language summary",
                "plain-language summary",
                "plain-language summaries",
                "普通读者",
                "面向读者",
                "读者版",
                "通俗总结",
                "通俗综述",
            ),
        },
    ),
    (
        "writing.chinese_humanization",
        {
            "prompt_hints": ("去ai味", "去 ai 味", "humanize 中文", "说人话", "像真人写", "像真人", "中文润色", "中文表达"),
            "skill_inference_hints": ("qu-ai-wei", "去 ai 味", "humanize 中文", "说人话", "真人表达", "natural writing", "human-written"),
        },
    ),
    (
        "writing.manuscript_review",
        {
            "prompt_hints": ("manuscript review", "revise abstract", "revise discussion", "scientific writing", "论文润色", "审阅论文", "论文草稿", "重写摘要", "重写讨论"),
            "skill_inference_hints": ("manuscript-writing-review", "sciwrite", "manuscript review", "scientific writing", "论文润色", "审阅论文"),
        },
    ),
    (
        "writing.scientific_report",
        {
            "prompt_hints": ("scientific report", "scientific reporting", "research report", "executive summary", "quarto", "科研报告", "科研技术报告", "科学报告", "实验结果"),
            "skill_inference_hints": ("scientific-reporting", "scientific reporting", "scientific report"),
        },
    ),
)

ROUTER_CAPABILITY_HINTS = tuple(
    (capability, tuple(spec["prompt_hints"]))
    for capability, spec in CAPABILITY_BRIDGE
)

SKILL_INDEX_CAPABILITY_HINTS = tuple(
    (capability, tuple(spec["skill_inference_hints"]))
    for capability, spec in CAPABILITY_BRIDGE
)

SKILL_INDEX_INTENT_HINTS = tuple(
    (capability, _dedupe_hints(tuple(spec["skill_inference_hints"]), tuple(spec["prompt_hints"])))
    for capability, spec in CAPABILITY_BRIDGE
)
