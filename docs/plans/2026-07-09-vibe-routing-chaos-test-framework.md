# Vibe Routing Chaos Test Framework

## Goal

Build a reusable test framework for the long-running `vibe` routing disease:

- irrelevant skills enter the shortlist
- obvious task modules are missing from the shortlist or selected set
- control words leak into task routing
- weak textual hints are treated like real capability proof
- the user-facing governed flow compresses the route into something that hides the real failure

This framework is for shared mechanism failures, not one-off prompt patching.

## The General Disease Class

The current router mixes different truth strengths too early:

1. real user task intent
2. control-plane hints such as `planning` or workflow grade
3. explicit skill capability declarations
4. weak textual coincidence from metadata or headings

Once these are collapsed into one ranking stream, low-confidence noise can:

- enter the public shortlist
- distort the selected skill set
- make complex tasks look single-skill
- create cross-domain routing collisions

The framework below tests those shared failure modes directly.

## Test Layers

### Layer A — Deterministic Route Contract

Use `route_prompt` / `resolve-pack-route.ps1` against fixed prompts.

Purpose:

- catch shortlist noise
- catch missing module coverage
- catch control-word leakage
- catch low-confidence cross-domain matches

This layer should stay in the default regression lane because it is fast and failure-first.

### Layer B — Governed Runtime Stop Contract

Use `Freeze-RuntimeInputPacket.ps1` and `invoke-vibe-runtime.ps1` through the `requirement_doc` stop.

Purpose:

- verify the shortlist and selected skill set survive into governed runtime artifacts
- verify `host_user_briefing` and requirement docs expose the curated set instead of hiding it
- verify `L` and `XL` scheme outputs stay aligned with the route truth

This layer should stay focused and touched-surface only when the failure being tested depends on governed runtime projection.

### Layer C — Live Clean-Context Agent Audit

Use a fresh subagent as a black-box tester.

Purpose:

- test real host-facing behavior with a clean context
- confirm the live agent sees the same shortlist problems users see
- catch failures that packet-level tests miss, especially requirement-stop messaging and route collapse

This layer is an optional audit, not a default regression set, because it depends on live agent execution.

## Black-Box Subagent Protocol

For one case:

1. Spawn one fresh subagent with `fork_context=false`.
2. Give it exactly one task prompt ending with `$vibe`.
3. Ask it to stop at the first governed requirement boundary and report what workflow level and skills it surfaced.
4. Capture:
   - final host-facing reply
   - `runtime-input-packet.json`
   - `host_user_briefing`
   - selected skill ids
   - public shortlist ids
5. Score the case against the assertions below.
6. Close the subagent immediately after the audit.

The subagent is a tester, not an implementer. It should not continue into execution once the routing behavior has been observed.

## Assertion Families

Every case should declare which of these it is testing:

1. `shortlist_quality`
   Public shortlist should not contain obvious cross-domain intruders.

2. `module_coverage`
   Multi-module tasks should expose the major required skill families, not collapse to one narrow lane.

3. `control_task_isolation`
   Task type or workflow control words should not dominate routing when the task text already carries user intent.

4. `evidence_discipline`
   Weak textual evidence should not outrank explicit capability or clear task-fit evidence.

5. `host_surface_coherence`
   User-facing governed disclosure should reflect the curated selected set and make route failure visible instead of hiding it.

## Case Contract Requirements

Every audit case now carries three reusable comparison fields so the same case can power route probes, governed-stop checks, and future scoring automation:

1. `expected_core_families`
   The task modules that should be visible if routing is sane.

2. `known_bad_shortlist_examples`
   Concrete off-target skills that already showed up in local probes or that should count as obvious route drift.

3. `missing_module_contract`
   The minimum coverage rule for the case. The current contract uses:
   - `coverage_source`: evaluate against the selected set plus the public shortlist
   - `minimum_expected_family_hits`: minimum number of expected families that must be visible
   - `critical_family_groups`: grouped must-have families where each group needs at least one visible hit
   - `failure_examples`: human-readable examples of what under-routing looks like

This keeps the framework focused on shared routing disease rather than vague “wrong skill” complaints.

## Ten Audit Cases

The first five remain the base wave that already showed bad behavior.
The second five extend coverage into architecture, manuscript audit, CV error analysis, long-document reasoning, and CPU/GPU pipeline triage using the current local `.agents` skill inventory.

### Case 1 — Chinese ML Training Over-Routing

- id: `ml_snake_demo_noise`
- prompt:
  `构建贪吃蛇游戏 训练机器学习模型 在游戏中虚拟训练 AI 玩贪吃蛇 可运行演示`
- grade: `L`
- task_type: `planning`
- dimensions:
  - `shortlist_quality`
  - `control_task_isolation`
  - `evidence_discipline`
- expected core families:
  - `model.training`
  - `interactive_demo_or_game`
- known bad shortlist examples:
  - `diagnosing-bugs`
  - `optimize-for-gpu`
  - `scientific-critical-thinking`
  - `algernom-building-analysis-pools`
- missing-module judgment:
  fail if the surfaced set never exposes both a training lane and a demo or game lane.

### Case 2 — Software Regression Misread As Statistical Regression

- id: `perf_regression_debug_collision`
- prompt:
  `React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause`
- grade: `L`
- task_type: `debug`
- dimensions:
  - `shortlist_quality`
  - `evidence_discipline`
- expected core families:
  - `debug.systematic_workflow`
  - `performance_debugging`
- known bad shortlist examples:
  - `statistical-analysis`
  - `scientific-critical-thinking`
- missing-module judgment:
  fail if the surfaced set never exposes both a debugging lane and a performance lane.

### Case 3 — Public-Database Review Composite Under-Coverage

- id: `public_db_review_composite`
- prompt:
  `做脓毒症公共数据库研究：检索 full-text 文献，提取样本量和 effect size，做统计比较，再写通俗综述并整理成汇报`
- grade: `XL`
- task_type: `research`
- dimensions:
  - `module_coverage`
  - `host_surface_coherence`
- expected core families:
  - `research.literature_search`
  - `research.literature_review`
  - `statistics.regression_or_relationship_modeling`
  - `writing.reader_report`
  - `presentation.deck`
- known bad shortlist examples:
  - `humanizer`
- missing-module judgment:
  fail if the surfaced set does not visibly cover literature work, statistics, reader-facing writing, and presentation.

### Case 4 — Frontend Delivery No-Match Collapse

- id: `frontend_preview_test_report_gap`
- prompt:
  `做一个可用的数据看板前端，接着部署 preview，再根据 pytest 和 coverage 输出生成测试报告`
- grade: `XL`
- task_type: `coding`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
- expected core families:
  - `frontend_build`
  - `preview_deployment`
  - `quality.test_report`
- known bad shortlist examples:
  - `algernom-building-analysis-pools`
  - `algernom-building-data-pools`
  - `algernom-building-journal-pools`
  - `algernom-building-problem-pools`
- missing-module judgment:
  fail if front-end build, preview, and report packaging do not all appear in the surfaced story.

### Case 5 — ML Delivery Bundle With Visualization And Slides

- id: `ml_report_figure_deck_bundle`
- prompt:
  `完成一个机器学习实验交付：训练 baseline，做 figure，整理 scientific report，并输出组会 slides`
- grade: `XL`
- task_type: `research`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `host_surface_coherence`
- expected core families:
  - `model.training`
  - `visualization.figure`
  - `writing.scientific_report`
  - `presentation.deck`
- known bad shortlist examples:
  - `setup-matt-pocock-skills`
- missing-module judgment:
  fail if the surfaced set hides any of training, figure work, report writing, or slides.

### Case 6 — Architecture To PRD Bundle Collapse

- id: `architecture_prd_issue_bundle`
- prompt:
  `接手一个已经变得臃肿的 Python 服务：先抽象领域模型和边界，再重设计模块接口，做一个小型原型验证，再把方案整理成 PRD 和可拆分 issues。`
- grade: `XL`
- task_type: `coding`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `host_surface_coherence`
- expected core families:
  - `architecture.domain_model`
  - `architecture.interface_design`
  - `prototype.throwaway_validation`
  - `planning.prd`
  - `planning.issue_breakdown`
- known bad shortlist examples:
  - `optimize-for-gpu`
  - `scikit-learn`
  - `statistical-analysis`
- missing-module judgment:
  fail if the surfaced set collapses to implementation or planning output only and does not visibly include architecture plus prototype work.

### Case 7 — Existing Manuscript Audit Versus Fresh Research Confusion

- id: `manuscript_review_audit_rewrite`
- prompt:
  `审阅一篇已有的医学机器学习论文草稿：检查实验设计和统计方法是否站得住脚，指出证据薄弱处，重写摘要和讨论，让中文表达更像真人。`
- grade: `L`
- task_type: `research`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `evidence_discipline`
- expected core families:
  - `writing.manuscript_review`
  - `science.methodology_audit`
  - `statistics.test_selection_or_result_check`
  - `writing.chinese_humanization`
- known bad shortlist examples:
  - `algernom-building-problem-pools`
  - `optimize-for-gpu`
  - `scikit-learn`
- missing-module judgment:
  fail if the surfaced set contains only critique or only polish, instead of both audit and rewrite support.

### Case 8 — CV Error Analysis With Figure Output

- id: `cv_error_analysis_figure_bundle`
- prompt:
  `分析一个目标检测项目为什么小目标 mAP 很差：需要从误检漏检模式、数据标注、训练策略和评估口径找原因，最后整理成图和技术结论。`
- grade: `XL`
- task_type: `research`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `evidence_discipline`
- expected core families:
  - `vision.error_analysis`
  - `vision.training_strategy`
  - `science.methodology_audit`
  - `visualization.figure`
- known bad shortlist examples:
  - `context-keeper`
  - `algernom-building-analysis-pools`
  - `algernom-building-data-pools`
  - `algernom-building-journal-pools`
- missing-module judgment:
  fail if the surfaced set cannot show CV analysis together with audit and figure output.

### Case 9 — Long RFC Reading Misread As Diagnosis

- id: `rfc_decision_brief_bundle`
- prompt:
  `精读一份很长的技术 RFC 和配套设计文档，提炼核心论证和隐藏假设，用第一性原理挑战方案，再输出一份给中文团队看的说人话决策备忘录。`
- grade: `L`
- task_type: `research`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `control_task_isolation`
- expected core families:
  - `docs.deep_reading`
  - `reasoning.first_principles`
  - `writing.reader_report`
  - `writing.chinese_humanization`
- known bad shortlist examples:
  - `diagnose`
  - `statistical-analysis`
  - `algernom-building-analysis-pools`
- missing-module judgment:
  fail if the surfaced set treats the task like debugging or abstract analysis and never exposes both reading and briefing support.

### Case 10 — CPU/GPU Pipeline Triage Under-Coverage

- id: `cpu_gpu_pipeline_triage`
- prompt:
  `排查一个本地 pandas + scikit-learn 分析流水线为什么又慢又吃 CPU：先区分是算法问题还是工程实现问题，再判断哪些步骤值得迁移到 GPU，并给出验证计划。`
- grade: `XL`
- task_type: `debug`
- dimensions:
  - `module_coverage`
  - `shortlist_quality`
  - `evidence_discipline`
- expected core families:
  - `debug.systematic_workflow`
  - `model.training_or_sklearn_pipeline`
  - `performance.gpu_migration`
  - `experiment.validation_plan`
- known bad shortlist examples:
  - `long-context`
  - `accelerate`
  - `megatron-core`
- missing-module judgment:
  fail if the surfaced set only tells an ML or acceleration story and never exposes diagnosis plus GPU migration together.

## Execution Policy

Run the ten cases in this order:

1. `ml_snake_demo_noise`
2. `perf_regression_debug_collision`
3. `public_db_review_composite`
4. `frontend_preview_test_report_gap`
5. `ml_report_figure_deck_bundle`
6. `architecture_prd_issue_bundle`
7. `manuscript_review_audit_rewrite`
8. `cv_error_analysis_figure_bundle`
9. `rfc_decision_brief_bundle`
10. `cpu_gpu_pipeline_triage`

The first two are mechanism probes for shared disease classes.
Cases three through five test the original multi-module failure family.
Cases six through ten widen the audit surface to architecture, document reasoning, scientific review, CV analysis, and performance triage.

## Success Criteria

The framework is useful only if it can distinguish these outcomes:

- over-routing noise
- under-routing or missing module coverage
- control-plane leakage
- weak-evidence dominance
- host-surface collapse

If a case only says “wrong skill” without revealing which shared mechanism failed, the case is too weak and should be rewritten.
