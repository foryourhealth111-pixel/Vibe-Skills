# VCO Changelog

## v2.3.40 (2026-03-14)

- Closed the cross-shell runtime-freshness validation gap so a receipt written by Windows PowerShell install flow can be validated correctly by `check.sh` under bash / WSL.
- Added explicit installed-runtime upgrade hints to `check.ps1` and `check.sh` so repo pulls are no longer silently confused with installed runtime upgrades.
- Kept Linux platform truth conservative while preserving green router, routing-stability, platform-support, mirror-hygiene, and proof-bundle gates.
- Aligned the governed release surface to `2.3.40` across version governance, maintenance markers, release navigation, and public install copy.
- Detailed release notes: `docs/releases/v2.3.40.md`.

## v2.3.39 (2026-03-14)

- Closed the Linux retest regression around OpenSpec routing by adding the missing `requested_skill_whitelist` contract and hardening the router against missing-policy fields.
- Fixed the installed-runtime freshness recursion failure so default `install.ps1` and `check.ps1` can complete their freshness closure instead of blowing up through call-depth overflow.
- Stabilized governed sub-gate invocation so the no-regression umbrella gate now receives deterministic `exit_code` objects instead of leaking child output shapes.
- Hardened multiple router overlays for strict-mode safety and re-proved installed-runtime routing through a fresh isolated smoke runtime.
- Registered the regression-closure router file set in the official-runtime main-chain policy so governance can distinguish this bounded fix wave from unrelated protected-surface drift.
- Detailed release notes: `docs/releases/v2.3.39.md`.

## v2.3.38 (2026-03-14)

- Removed author-machine path leakage from governed runtime JSON surfaces by replacing hard-coded user paths in `config/dependency-map.json`, `config/upstream-corpus-manifest.json`, `config/ruc-nlpir-runtime.json`, and `config/batch-e-alias-whitelist.json` with `${CODEX_HOME}` / `${VCO_EXTERNAL_ROOT}` forms.
- Landed matching path-resolution helpers and consumer updates so config tokenization does not regress runtime behavior, including sync/bootstrap/governance flows and Linux-sensitive RUC-NLPIR preflight handling.
- Resynced canonical, bundled, and nested-bundled mirrors, then re-materialized the smoke installed runtime to prove the installed surface matches the new canonical governance state.
- Verified release readiness with zero leaked author-machine paths in the governed config surfaces plus green `vibe-upstream-corpus-manifest-gate.ps1`, `vibe-deep-extraction-pilot-gate.ps1`, `vibe-installed-runtime-freshness-gate.ps1`, and `check.ps1 -Profile full`.
- Detailed release notes: `docs/releases/v2.3.38.md`.


## v2.3.37 (2026-03-13)

- Promoted `scrapling` into the standard governed `full` install lane so the default full-profile path now carries a concrete local scraping/runtime surface instead of treating it as a purely optional afterthought.
- Updated bootstrap doctor semantics to explicitly distinguish three governed surfaces: `scrapling` as the default full-profile runtime surface, `Cognee` as the default long-term enhancement lane, and `Composio / Activepieces` as prewired but setup-required external action surfaces.
- Expanded the install and onboarding docs across README, cold-start paths, one-shot setup, and host-plugin policy so operators can see the truthful boundary between repo-owned closure and host-managed provisioning.
- Aligned the governed release surface to `2.3.37` across version governance, maintenance markers, changelog, release ledger, and release navigation.
- Detailed release notes: `docs/releases/v2.3.37.md`.


## v2.3.36 (2026-03-13)

- Hardened the install-facing narrative so `full-featured` now means governed closure of the repository-owned surface, not fake automatic readiness for all host plugins or MCP providers.
- Added bilingual host-plugin policy docs and reusable Windows/Linux full-featured install prompt bundles for operator onboarding.
- Updated `README.md`, `README.en.md`, `docs/one-shot-setup.md`, and cold-start install guides to clearly separate `minimum viable`, `recommended full-featured`, and `enterprise-governed` entry paths.
- Aligned the governed release surface to `2.3.36` across version governance, dist manifests, release notes, and runtime-neutral freshness tests.
- Detailed release notes: `docs/releases/v2.3.36.md`.


## v2.3.35 (2026-03-13)

- Reserved release cut created during release-surface iteration and superseded by `v2.3.36` before merge.
- No separate user-facing delta should be treated as shipped for `v2.3.35`.


## v2.3.34 (2026-03-13)

- Reframed the README install narrative so “full-featured” now means governed closure of the repo-owned surface, not a fake claim that the whole ecosystem is automatically ready.
- Added explicit operator-facing boundary language for host plugins, plugin-backed MCP surfaces, and provider secrets so incomplete host provisioning resolves to `manual_actions_pending` instead of ambiguous expectations.
- Added cold-start onboarding documents for three install modes: `minimum viable`, `recommended full-featured`, and `enterprise-governed`, with commands, acceptance criteria, and stop rules.
- Wired the new onboarding docs into the main README, English README, docs index, and one-shot setup guide so first-time users can enter through a deterministic path instead of guessing.
- Detailed release notes: `docs/releases/v2.3.34.md`.


## v2.3.33 (2026-03-13)

- Fixed one-shot bootstrap provider seeding so existing `settings.json` keys are reused instead of triggering misleading `OPENAI_API_KEY not provided` warnings.
- Added operator-facing bootstrap messaging that sets realistic expectations for slow `npm` installs and advisory deprecated warnings during external CLI provisioning.
- Aligned `check.ps1` with `nested_bundled` governance so optional nested mirrors no longer create false bundled-config warnings during deep doctor runs.
- Resynced canonical and bundled mirrors, regenerated `config/skills-lock.json`, and re-cut the governed release surface to `v2.3.33`.
- Detailed release notes: `docs/releases/v2.3.33.md`.


## v2.3.32 (2026-03-13)

- Added dual-platform full-setup onboarding so README now documents a governed "full-featured" install path for both Windows and Linux / macOS.
- Added `scripts/bootstrap/one-shot-setup.sh` to close the shell-native bootstrap gap with install -> settings seed -> MCP active profile materialization -> deep check.
- Updated deployment and one-shot setup docs to make the full-feature boundary explicit: what the repo can automate, and what still must be provisioned at the host/plugin/secret layer.
- Regenerated `config/skills-lock.json`, resynced canonical and bundled mirrors, and re-cut the governed release surface to `v2.3.32`.
- Detailed release notes: `docs/releases/v2.3.32.md`.


## v2.3.31 (2026-03-13)

- Completed the governed execution closure for:
  - `docs/plans/2026-03-13-distribution-governance-plan.md`
  - `docs/plans/2026-03-13-post-upstream-governance-repo-convergence-plan.md`
  - `docs/plans/2026-03-13-post-upstream-governance-developer-entry-plan.md`
- Repaired external-corpus fixture parity so `vibe-output-artifact-boundary-gate.ps1` returns green with tracked output mirrors aligned.
- Repaired third-party disclosure canonicalization so `vibe-third-party-disclosure-parity-gate.ps1` no longer misclassifies repository-local document links as undeclared upstream sources.
- Re-cut the governed version surface to `v2.3.31`, resynced canonical and bundled assets, and prepared runtime/install/remote alignment around the new release marker.
- Detailed release notes: `docs/releases/v2.3.31.md`.


## 2026-03-09 — Batch0-9 cleanup closure update

- 完成 `docs/plans/2026-03-08-repo-full-cleanup-master-plan.md` 下 Batch 0-9 的一次执行收口，并新增 tracked 报告：`docs/plans/2026-03-09-batch0-9-closure-report.md`。
- 修复 `scripts/governance/export-repo-cleanliness-inventory.ps1` 的 artifact 渲染解析错误，使 cleanliness inventory operator 可稳定执行。
- 新增 `.gitattributes`，补强 `.gitignore` / `config/index.md` / `third_party/README.md` / docs-references-scripts family spine，并把 `.gitattributes` 与 `third_party/` 纳入 `config/repo-cleanliness-policy.json` 的治理面。
- 修复 `check.sh` 的 UTF-8 BOM 风险，并完成 canonical -> bundled -> nested sync；同时复跑 installed runtime install/freshness/coherence 流程。
- 关键门禁全部通过：repo-cleanliness、output-artifact-boundary、bom-frontmatter、mirror-edit-hygiene、nested-bundled-parity、version-packaging、installed-runtime-freshness、release-install-runtime-coherence。
- 说明：这是一轮 cleanup / governance closure，不是新的 release cut；Batch 3 的 canonical workset admission / commit closure 仍保留为下一步 backlog（见 docs/plans/2026-03-09-batch0-9-closure-report.md）。

## v2.3.30 (2026-03-07)

- 完成 Wave31-33 的镜像 / 运行态治理收口：
  - `mirror_topology.targets` 成为显式 canonical 合同；新增 `vibe-nested-bundled-parity-gate.ps1`、`vibe-mirror-edit-hygiene-gate.ps1`、`vibe-release-install-runtime-coherence-gate.ps1`。
  - release / install / runtime freshness 边界被正式写入 `config/version-governance.json` 与 `docs/version-packaging-governance.md`。
- 完成 Wave34 的 upstream corpus 治理：
  - 新增 `config/upstream-corpus-manifest.json`、`references/upstream-value-ledger.md`、`docs/upstream-corpus-governance.md`，把 15 个 upstream 项目正式登记进 canonical corpus。
- 完成 Wave35-38 的能力产品化收口：
  - `docling` 固定为 document-plane canonical contract。
  - connector 生态固定为 connector admission layer，而不是新的 route owner。
  - role-pack / skill distillation 固定为治理输入层，而不是第二 orchestrator。
  - discovery / eval corpus 与 capability catalog 被纳入正式 reference / config / gate 体系。
- 完成 Wave39 的 promotion / release closure：
  - promotion board 扩展覆盖 Wave31-38 新治理条目。
  - 新增 `pilot-deep-extraction.json` / `vibe-deep-extraction-pilot-gate.ps1`，把 mirror/runtime/corpus/productization 收口指标并入 release 证据链。
  - 详细说明（release notes）：`docs/releases/v2.3.30.md`。
## v2.3.29 (2026-03-07)

- 完成 Wave19-23 的 memory / prompt absorption 收口：
  - `mem0` 固定为可选 preference backend，`Letta` 固定为 policy contract 来源，prompt intelligence 只增强资产层，不形成第二 router。
- 完成 Wave24-25 的执行平面吸收：
  - BrowserOps 以 provider governance 吸收 `browser-use`，DesktopOps 以 shadow contract 吸收 Agent-S，并保持 `advice-first / shadow-first / rollback-first`。
- 完成 Wave26-28 的治理闭环：
  - 新增 cross-plane conflict policy、promotion board 与 `pilot-*.json` 试点评估体系。
- 完成 Wave29-30 的发布收口：
  - canonical / bundled 镜像重新同步，清理退役 `*-shadow.json` pilot 旧命名。
  - `memory-runtime-v2`、`prompt-intelligence`、`browserops-provider`、`desktopops-shadow` 已由 `shadow` 显式写入 `soft`。
  - 详细说明（release notes）：`docs/releases/v2.3.29.md`。


## v2.3.28 (2026-03-05)

- TurboMax（方案 A：API 换时间）能力补齐：
  - 向量优先 diff 上下文（vector-first diff context）与缓存策略（降低上下文腐烂风险）。
  - 新增 Volc Ark embeddings provider（`doubao-embedding-vision-250615`，text-only diff chunk 相似度）。
- GPT‑5.2 LLM Acceleration Overlay（/vibe 显式启用）：
  - `diff_digest` / `committee` / `confirm_question_booster` 三件套加速（advice-first，失败自动退化）。
- prompts.chat Prompt Asset Boost：
  - 输出 prompts.chat 搜索策略 + 可注入 overlay candidates（不改路由，仅 advice）。
- 学术写作/投稿/作图/报告路由增强（解决“写报告/作图误入 docs-media”的漏触发问题）：
  - 新增 Packs：`scholarly-publishing-workflow`（投稿/返修/校样）、`science-figures-visualization`（顶刊作图）、`science-reporting`（科研/技术报告）。
  - 新增 Skills：`scholarly-publishing`、`submission-checklist`、`manuscript-as-code`、`latex-submission-pipeline`、`slides-as-code`、`scientific-reporting`（含模板与案例库索引）。
  - 路由规则补齐：学术场景正/负关键词、技能 keyword index、回归用例（grant proposal、PPT/Slidev slides-as-code）。
  - 可靠性：开启 legacy fallback 的 confirm guard，避免低信号误自动路由。
  - 详细说明（release notes）：`docs/releases/v2.3.28.md`。
- 新增 TuriX‑CUA Computer Use Overlay（advice-only）：
  - UI/浏览器流程任务提供 CUA vs Playwright vs API 决策树与 runbook（自动建议 → 你确认 → 注入）。
- 可靠性修复：
  - 修复 PowerShell 输入冲突与 SSE responses 兼容性问题（提升代理/网关兼容）。
  - 修复上游插件 repo 指针漂移（ECC → `affaan-m/everything-claude-code`；官方插件 → `anthropics/claude-plugins-official`）。
  - 新增上游版本审计脚本：`scripts/governance/audit-upstream.ps1`（支持对比本机 `installed_plugins.json`）。

## v2.3.27 (2026-02-27)

- 修复 OpenSpec strict 阻断语义漂移（`scripts/governance/invoke-openspec-governance.ps1`）：
  - `strictPlanningBlocking` 从错误的 `enforcement=="strict"` 修正为基于 `mode=="strict"` 判定。
  - 增加向后兼容：旧路由载荷若缺少 `mode`，则 `profile=full + enforcement=required` 视为 strict 等价。
  - strict + planning + full_missing 时，`required_action` 统一输出 `rerun_with_WriteArtifacts_to_*` 明确指引。
- 更新 OpenSpec 门禁断言（`scripts/verify/vibe-openspec-governance-gate.ps1`）：
  - strict 缺失场景期望改为 `required_action=rerun_with_WriteArtifacts_to_create_full_spec_change`。
- 健康检查增强，预防 main/bundled 配置漂移复发：
  - `check.ps1` / `check.sh` 新增 bundled 层 retrieval/exploration 6 个配置存在性检查。

## v2.3.26 (2026-02-27)

- OpenSpec governance gate 用例更新（`scripts/verify/vibe-openspec-governance-gate.ps1`）：
  - `M + planning` 期望改为 `profile=full` + `enforcement=required`（Governance-First）。
  - 新增 strict 缺失阻断断言：`full_missing` 时必须 `enforced=true` 且 `required_action=create_full_spec_change`。
  - 新增 `requested_skill_whitelist` 断言：白名单请求触发 `reason` 匹配 `requested_skill_bypass*`，并标记 `bypass_due_to_requested_skill=true`。
- OpenSpec 文档改为 Governance-First 口径：
  - `docs/openspec-vco-integration.md`
  - `README.md`（仅 OpenSpec 治理段落）

## v2.3.25 (2026-02-27)

- 修复 `vibe-router-contract-gate.ps1` 在模块化后长期红灯的问题：
  - 默认 gate 从“full JSON 全等”调整为“分层契约校验”（核心路由字段 + schema + 预期差异白名单）。
  - 新增 `-StrictFullJson` 取证模式，保留完整载荷全等检查能力（仅用于法证/回归定位，不作为默认阻断）。
  - 新增 `low-signal + legacy_fallback_guard` 的预期差异识别，避免将反静默兜底设计误判为回归。
- 文档同步更新：
  - `docs/router-modularization-governance.md`
  - `scripts/verify/README.md`

## v2.3.24 (2026-02-27)

- 新增版本与打包治理闭环（main + bundled 同步约束）：
  - `config/version-governance.json`
  - `scripts/governance/sync-bundled-vibe.ps1`
  - `scripts/governance/release-cut.ps1`
  - `scripts/verify/vibe-version-consistency-gate.ps1`
  - `scripts/verify/vibe-version-packaging-gate.ps1`
  - `docs/version-packaging-governance.md`
  - `references/release-ledger.jsonl`
- 安装链路加固：
  - `install.ps1` / `install.sh` 在复制 bundled 后，再按治理契约强制同步 canonical `vibe` 镜像到 runtime 目标目录，降低 main/bundled 漂移风险。
- 校验链路加固：
  - `check.ps1` / `check.sh` 新增 `version-governance` 存在性检查。
  - `check.ps1` / `check.sh` 新增 release ledger 存在性检查。
  - CI `vco-gates.yml` 新增 `vibe-version-consistency-gate.ps1` 与 `vibe-version-packaging-gate.ps1`。
  - `scripts/verify/README.md` 与 `references/index.md` 新增治理文档与 gate 入口。
- 修复 offline skills 锁稳定性问题：
  - `scripts/verify/vibe-generate-skills-lock.ps1` 与 `scripts/verify/vibe-offline-skills-gate.ps1` 改为跨平台稳定哈希（文本统一 LF 后哈希）。
  - 重新生成 `config/skills-lock.json`，移除失效条目并与当前 `bundled/skills` 对齐。

## v2.3.23 (2026-02-27)

- 新增 Exploration Overlay（探索型任务增强，默认 `soft`，保持 post-route 非侵入）：
  - 新增配置（main + bundled）：
    - `config/exploration-policy.json`
    - `config/exploration-intent-profiles.json`
    - `config/exploration-domain-map.json`
  - 新增模块：
    - `scripts/router/modules/44-exploration-overlay.ps1`
  - 路由入口接入：
    - `scripts/router/resolve-pack-route.ps1`
    - 新增阶段：`overlay.exploration`
    - 路由输出新增：`exploration_advice`
- 可观测与探针联动增强：
  - `scripts/router/modules/11-route-probe.ps1` 将 exploration 纳入 runtime state prompt 与 final_state 摘要。
  - `scripts/router/modules/22-intent-contract.ps1` 的 `runtime_state_prompt_digest` 纳入 exploration overlay。
  - `scripts/router/modules/10-observability.ps1` 纳入 exploration intent/domain/confirm 遥测字段。
  - `scripts/router/modules/00-core-utils.ps1` 的 `Test-OverlayConfirmRequired` 纳入 exploration confirm 信号。
- 新增门禁与验证链路：
  - `scripts/verify/vibe-exploration-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 exploration 配置 parity
  - `scripts/verify/vibe-pack-routing-smoke.ps1` 纳入 exploration 配置结构校验
  - `scripts/verify/vibe-routing-probe-research.ps1` 与 `scripts/verify/vibe-deep-discovery-scenarios.ps1` 更新 stage chain（含 `overlay.exploration`）
  - `scripts/verify/README.md` 新增 exploration gate 入口
- 文档与健康检查更新：
  - `docs/exploration-overlay-integration.md`
  - `docs/blackbox-probe-and-enhancement-playbook.md`、`docs/deep-discovery-mode-design.md`、`docs/retrieval-overlay-integration.md` 更新路由阶段链
  - `references/index.md` 新增 exploration 文档入口
  - `check.ps1` / `check.sh` 新增 exploration 配置存在性检查

## v2.3.22 (2026-02-27)

- 新增 Retrieval Overlay（检索策略增强，默认 `shadow`，保持 post-route 非侵入）：
  - 新增配置（main + bundled）：
    - `config/retrieval-policy.json`
    - `config/retrieval-intent-profiles.json`
    - `config/retrieval-source-registry.json`
    - `config/retrieval-rerank-weights.json`
  - 新增模块：
    - `scripts/router/modules/43-retrieval-overlay.ps1`
  - 路由入口接入：
    - `scripts/router/resolve-pack-route.ps1`
    - 新增阶段：`overlay.retrieval`
    - 路由输出新增：`retrieval_advice`
- 可观测与探针联动增强：
  - `scripts/router/modules/11-route-probe.ps1` 将 retrieval 纳入 runtime state prompt 与 final_state 摘要。
  - `scripts/router/modules/22-intent-contract.ps1` 的 `runtime_state_prompt_digest` 纳入 retrieval overlay。
  - `scripts/router/modules/10-observability.ps1` 纳入 retrieval profile/coverage/confirm 遥测字段。
  - `scripts/router/modules/00-core-utils.ps1` 的 `Test-OverlayConfirmRequired` 纳入 retrieval confirm 信号。
- 新增门禁与验证链路：
  - `scripts/verify/vibe-retrieval-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 retrieval 配置 parity
  - `scripts/verify/vibe-pack-routing-smoke.ps1` 纳入 retrieval 配置结构校验
  - `scripts/verify/vibe-routing-probe-research.ps1` 与 `scripts/verify/vibe-deep-discovery-scenarios.ps1` 更新 stage chain（含 `overlay.retrieval`）
  - `scripts/verify/README.md` 新增 retrieval gate 入口
- 文档与健康检查更新：
  - `docs/retrieval-overlay-integration.md`
  - `docs/blackbox-probe-and-enhancement-playbook.md`、`docs/deep-discovery-mode-design.md` 更新路由阶段链
  - `references/index.md` 新增 retrieval 文档入口
  - `check.ps1` / `check.sh` 新增 retrieval 配置存在性检查

## v2.3.21 (2026-02-27)

- 统一 `$vibe` 入口复检后，将 heartbeat 默认策略固定为可观测但非侵入：
  - `config/heartbeat-policy.json` -> `enabled=true`, `mode=shadow`
  - `bundled/skills/vibe/config/heartbeat-policy.json` -> `enabled=true`, `mode=shadow`
- 新增复检报告：
  - `docs/heartbeat-unified-vibe-entry-recheck-2026-02-27.md`
  - 覆盖 M/L/XL 与模糊场景的统一入口触发结果、strict 压测触发结果与门禁通过证据。

## v2.3.20 (2026-02-26)

- Heartbeat runtime V1 正式接入路由执行链（默认 `shadow`，非破坏式）：
  - 新增配置（main + bundled）：
    - `config/heartbeat-policy.json`
    - `bundled/skills/vibe/config/heartbeat-policy.json`
  - 新增模块：
    - `scripts/router/modules/12-heartbeat.ps1`
  - 路由入口接入：
    - `scripts/router/resolve-pack-route.ps1`
    - 在 `router.init`、`router.prepack`、`router.pack_scoring`、`overlay.*`、`router.final` 写入 heartbeat pulse。
  - 路由输出新增：
    - `heartbeat_advice`
    - `heartbeat_status`
    - `heartbeat_runtime_digest`
- 可观测与探针联动：
  - `scripts/router/modules/10-observability.ps1` 新增 heartbeat telemetry 摘要字段。
  - `scripts/router/modules/11-route-probe.ps1` 在 runtime state prompt 与 final_state 中加入 heartbeat guard 视图。
  - `scripts/router/modules/22-intent-contract.ps1` 的 `runtime_state_prompt_digest` 新增 heartbeat 摘要。
  - `scripts/router/modules/00-core-utils.ps1` 的 `Test-OverlayConfirmRequired` 纳入 heartbeat confirm 信号。
- 新增门禁与验证链路：
  - `scripts/verify/vibe-heartbeat-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 heartbeat policy parity
  - `scripts/verify/vibe-pack-routing-smoke.ps1` 纳入 heartbeat policy 结构校验
  - `scripts/verify/README.md` 新增 heartbeat gate 入口
  - `check.ps1` / `check.sh` 新增 heartbeat policy 存在性检查

## v2.3.19 (2026-02-26)

- 新增 Heartbeat Runtime 实现文档：
  - `docs/heartbeat-runtime-integration.md`
  - 定义 VCO 执行心跳状态机、软/硬卡住判定、自动诊断动作与用户回显节奏。
- 将 Error Resolver 五步法嵌入卡住治理：
  - `CLASSIFY -> PARSE -> MATCH -> ANALYZE -> RESOLVE`
  - 明确 hard-stall 场景的 replay 记录与预防策略。
- 新增可观测与门禁建议：
  - 统一心跳事件协议、`heartbeat-policy` 配置模型、`vibe-heartbeat-gate` 验证建议。
  - 验收指标：TTFU、silent_time_total、stall_false_positive_rate、diagnosis_coverage。
- 文档索引更新：
  - `references/index.md` 新增 heartbeat 文档入口，便于快速复用与检索。

## v2.3.18 (2026-02-26)

- 新增 Deep Discovery Mode（prepack 可观测扩展链）：
  - 新增路由阶段：`deep_discovery.trigger` / `deep_discovery.interview` / `deep_discovery.contract` / `deep_discovery.filter`
  - 默认 `shadow`，不改变既有路由分配；`soft/strict` 可按策略提升确认或执行能力过滤。
- 新增配置（main + bundled）：
  - `config/deep-discovery-policy.json`
  - `config/capability-catalog.json`
- 路由输出新增关键字段：
  - `deep_discovery_advice`
  - `intent_contract`
  - `deep_discovery_filter`
  - `deep_discovery_route_filter_applied`
  - `deep_discovery_route_mode_override`
  - `runtime_state_prompt_digest`
- 可观测性增强：
  - `scripts/router/modules/10-observability.ps1` 新增 deep-discovery 遥测字段。
  - `scripts/router/modules/11-route-probe.ps1` 在 runtime state prompt 与 final_state 中加入 deep-discovery 摘要。
- 新增验证脚本：
  - `scripts/verify/vibe-deep-discovery-gate.ps1`
  - `scripts/verify/vibe-deep-discovery-scenarios.ps1`
- 验证与文档入口更新：
  - `scripts/verify/vibe-config-parity-gate.ps1`
  - `scripts/verify/vibe-pack-routing-smoke.ps1`
  - `check.ps1` / `check.sh`
  - `docs/deep-discovery-mode-design.md`
  - `docs/blackbox-probe-and-enhancement-playbook.md`
  - `references/index.md`
  - `scripts/verify/README.md`

## v2.3.17 (2026-02-26)

- 新增统一复用文档：
  - `docs/blackbox-probe-and-enhancement-playbook.md`
  - 汇总 blackbox 探测、语义增强、阈值扫描、回归门禁的模块职责、运行顺序、产物路径与常用命令。
- 语义增强脚本可复用性提升：
  - `scripts/research/mine-user-semantic-overlay-signals.ps1` 增加 `/vibe` 与 `$vibe` 前缀归一化、redacted prompt 过滤、报告渲染修复。
  - 支持将用户语义记录转化为 overlay 词汇增量并安全写回 main/bundled 配置。
- 阈值扫描稳定性与可控性提升：
  - `scripts/verify/vibe-overlay-threshold-sensitivity-scan.ps1` 修复执行稳定性问题，固定 `0.05` 步长扫描流程可复现。
  - 并列最优阈值采用保守 tie-break（优先更高阈值）以降低误触发。
- 路由模块边界修复：
  - `scripts/router/modules/34-data-scale-overlay.ps1` 在严格模式下将路径解析结果显式数组化，避免 `.Count` 访问异常。
- 文档入口同步：
  - `references/index.md`、`SKILL.md`、`scripts/verify/README.md`、`scripts/research/README.md` 增加该模块总览入口，便于下次快速定位。

## v2.3.16 (2026-02-26)

- 路由器模块化重构（零退化拆分）：
  - `scripts/router/resolve-pack-route.ps1` 从单体函数定义改为模块加载编排入口
  - 新增函数模块目录：
    - `scripts/router/modules/*.ps1`
  - 新增 legacy 基线脚本用于契约对比：
    - `scripts/router/legacy/resolve-pack-route.legacy.ps1`
- 新增零退化契约门禁：
  - `scripts/verify/vibe-router-contract-gate.ps1`
  - 对 `legacy` vs `modular` 在固定矩阵下做严格 JSON 等价校验
- 安装与运行完整性增强：
  - `install.ps1` / `install.sh` 改为同步整个 `scripts/router` 目录（脚本 + modules）
  - `check.ps1` / `check.sh` 新增 router modules 存在性检查
  - `check.ps1 -Deep` / `check.sh --deep` 纳入 contract gate
- CI 门禁升级：
  - `.github/workflows/vco-gates.yml` 纳入 `vibe-router-contract-gate.ps1`
- 新增治理文档：
  - `docs/router-modularization-governance.md`（main + bundled）
- 文档同步：
  - `SKILL.md`、`references/index.md`、`scripts/verify/README.md` 更新模块化与契约门禁入口

## v2.3.15 (2026-02-26)

- 新增 AI Rerank Overlay（B+：召回安全双阶段路由，默认 shadow 不改路由）：
  - 新增配置（main + bundled）：
    - `config/ai-rerank-policy.json`
    - `bundled/skills/vibe/config/ai-rerank-policy.json`
  - 路由器输出新增：
    - `ai_rerank_advice`
    - `ai_rerank_route_override`
  - 核心约束：
    - Top-K 约束（`require_candidate_in_top_k`）
    - task 边界约束（`enforce_task_allow`）
    - 最低置信约束（`min_rerank_confidence`）
    - rollout 采样约束（`max_live_apply_rate`）
    - `preserve_routing_assignment` 默认保护（soft/strict 下也可阻断覆盖）
  - 语义行为：
    - `shadow`：仅给建议与 `would_override`，不改选中路由
    - `soft/strict`：仅在硬约束全部通过且允许 apply 时才覆盖
- 新增验证门禁：
  - `scripts/verify/vibe-ai-rerank-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `ai-rerank-policy` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `ai-rerank-policy` 存在性检查
  - 新增 deep 模式：
    - `check.ps1 -Deep`
    - `check.sh --deep`
  - deep 模式会串行执行关键 verify gates（含 ai-rerank gate）
- CI/门禁自动化：
  - 新增 GitHub Actions：`.github/workflows/vco-gates.yml`
  - 自动执行回归与治理门禁：
    - `vibe-pack-regression-matrix`
    - `vibe-routing-stability-gate -Strict`
    - `vibe-config-parity-gate`
    - `vibe-observability-gate`
    - `vibe-ai-rerank-gate`
- 新增文档：
  - `docs/ai-rerank-overlay-integration.md`（main + bundled）
  - `scripts/verify/README.md`、`references/index.md`、`SKILL.md` 同步更新

## v2.3.14 (2026-02-26)

- 新增 Observability & Consistency Governance（严格、轻量、低上下文压力）：
  - 新增配置（main + bundled）：
    - `config/observability-policy.json`
    - `bundled/skills/vibe/config/observability-policy.json`
  - 路由器新增隐私安全遥测写入（不改变路由分配）：
    - `scripts/router/resolve-pack-route.ps1` 新增 `Write-ObservabilityRouteEvent`
    - 输出：`outputs/telemetry/route-events-YYYYMMDD.jsonl`
    - 默认仅写 `prompt_hash` 与结构化路由字段，不落地原始 prompt
  - 新增验证与学习脚本：
    - `scripts/verify/vibe-observability-gate.ps1`
    - `scripts/learn/vibe-adaptive-train.ps1`（离线建议、手动审核应用）
  - 回退治理升级：
    - `scripts/governance/publish-openspec-soft-rollout.ps1` 禁用自动回退执行
    - 发布失败时仅输出手动回退命令，要求用户显式确认后执行
  - 文档同步：
    - `docs/observability-consistency-governance.md`（main + bundled）
    - `docs/openspec-vco-integration.md` 更新为“手动确认回退”策略
    - `scripts/verify/README.md`、`references/index.md`、`check.ps1`、`check.sh` 同步更新
  - 一致性门禁：
    - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `observability-policy` main/bundled parity

## v2.3.13 (2026-02-26)

- 新增 CUDA Kernel Overlay（LeetCUDA 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/cuda-kernel-overlay.json`
    - `bundled/skills/vibe/config/cuda-kernel-overlay.json`
  - 路由器输出新增：
    - `cuda_kernel_advice`
  - 核心信号：
    - CUDA 优化语义关键词（PTX/WMMA/MMA/tensor core/shared memory/occupancy/bank conflict 等）
    - 文件与环境信号（`.cu/.ptx/nvcc/nvidia-smi`）
    - 优化维度覆盖评分（kernel target/memory hierarchy/profiling/correctness/fallback/hardware context）
    - interview/noise 语义抑制，减少误触发
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：证据不足或风险较高时给出 `confirm_recommended`
    - `strict`：严格范围内且覆盖分不足时输出 `confirm_required` advice（仍不改路由分配）
  - 许可证边界：
    - `LeetCUDA` 上游为 GPL-3.0，本仓库仅方法论 advisory 接入，不 vendoring 上游源码
- 新增验证门禁：
  - `scripts/verify/vibe-cuda-kernel-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `cuda-kernel-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `cuda-kernel-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/cuda-kernel-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 CUDA kernel overlay 说明
- 第三方与上游映射：
  - `THIRD_PARTY_LICENSES.md` 新增 `xlite-dev/LeetCUDA`
  - `config/upstream-lock.json` 新增 `xlite-dev/LeetCUDA` 锁定条目

## v2.3.12 (2026-02-26)

- 新增 System Design Overlay（system-design-primer 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/system-design-overlay.json`
    - `bundled/skills/vibe/config/system-design-overlay.json`
  - 路由器输出新增：
    - `system_design_advice`
  - 核心信号：
    - 架构语义关键词（可扩展、吞吐/延迟、一致性、分片、容灾、观测性等）
    - 架构覆盖维度评分（requirements/NFR/capacity/cache/partition/recovery/observability/cost）
    - interview-only 语义抑制，减少误触发
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：覆盖不足或风险较高时给出 `confirm_recommended`
    - `strict`：严格范围内且覆盖分不足时输出 `confirm_required` advice（仍不改路由分配）
- 新增验证门禁：
  - `scripts/verify/vibe-system-design-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `system-design-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `system-design-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/system-design-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 system-design overlay 说明

## v2.3.11 (2026-02-25)

- 新增 Python Clean Code Overlay（clean-code-python 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/python-clean-code-overlay.json`
    - `bundled/skills/vibe/config/python-clean-code-overlay.json`
  - 路由器输出新增：
    - `python_clean_code_advice`
  - 自动触发行为：
    - 优先使用 `.py/.pyi` 路径信号判定 Python 编写场景
    - 叠加 Python 语义关键词、clean-code 原则组与反模式信号
    - 通过 suppress 关键词降噪（generated/migration/vendor/docs-only 等）
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：高风险仅给出 `confirm_recommended`
    - `strict`：严格范围内且反模式证据充分时输出 `confirm_required` advice（仍不改路由分配）
- 新增验证门禁：
  - `scripts/verify/vibe-python-clean-code-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `python-clean-code-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `python-clean-code-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/python-clean-code-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 Python clean-code overlay 说明

## v2.3.10 (2026-02-25)

- 新增 ML Lifecycle Overlay（Made-With-ML 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/ml-lifecycle-overlay.json`
    - `bundled/skills/vibe/config/ml-lifecycle-overlay.json`
  - 路由器输出新增：
    - `ml_lifecycle_advice`
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：生命周期风险仅给出 `confirm_recommended`
    - `strict`：严格范围内且关键生命周期证据缺失时输出 `confirm_required` advice（仍不改路由分配）
- 新增验证门禁：
  - `scripts/verify/vibe-ml-lifecycle-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `ml-lifecycle-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `ml-lifecycle-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/ml-lifecycle-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 ML lifecycle overlay 说明

## v2.3.9 (2026-02-25)

- 新增 Framework Interop Overlay（Ivy 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/framework-interop-overlay.json`
    - `bundled/skills/vibe/config/framework-interop-overlay.json`
  - 路由器输出新增：
    - `framework_interop_advice`
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：强 interop 信号仅给出 `confirm_recommended`
    - `strict`：强 interop 信号输出 `confirm_required` advice（仍不改路由分配）
- 新增验证门禁：
  - `scripts/verify/vibe-framework-interop-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `framework-interop-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `framework-interop-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/framework-interop-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 framework-interop 说明

## v2.3.8 (2026-02-25)

- 新增 Quality Debt Overlay（fuck-u-code 增强，post-route advice-only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/quality-debt-overlay.json`
    - `bundled/skills/vibe/config/quality-debt-overlay.json`
  - 路由器输出新增：
    - `quality_debt_advice`
  - 语义行为：
    - `shadow`：仅建议，不改 selected pack/skill
    - `soft`：高风险仅给出 `confirm_recommended` 建议
    - `strict`：高风险输出 `confirm_required` advice（仍不改路由分配）
- 新增验证门禁：
  - `scripts/verify/vibe-quality-debt-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `quality-debt-overlay` main/bundled parity
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增 `quality-debt-overlay` 配置存在性检查
- 新增设计文档：
  - `docs/quality-debt-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md`、`references/tool-registry.md` 更新 quality-debt overlay 说明

## v2.3.7 (2026-02-25)

- 新增 Data Scale Overlay（基于真实文件信号的表格技能选择增强，post-route，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/data-scale-overlay.json`
    - `bundled/skills/vibe/config/data-scale-overlay.json`
  - 路由器输出新增：
    - `data_scale_advice`
    - `data_scale_route_override`
  - 语义行为：
    - `shadow`：仅建议，不改 selected skill
    - `soft`：规模/格式推荐与当前技能冲突时进入 `confirm_required`
    - `strict`：高置信可在同 pack 候选内自动覆盖到推荐技能（如 `xan`）
- 表格路由增强：
  - `docs-media` pack 新增候选 `xan`
  - `skill-keyword-index.json` 新增 `xan` 关键词
  - `skill-routing-rules.json` 新增 `xan` 规则，并收敛 `spreadsheet` 在大 CSV 意图下的负关键词
- 新增验证门禁：
  - `scripts/verify/vibe-data-scale-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `data-scale-overlay` main/bundled parity
  - `scripts/verify/README.md` 增加执行入口
- 新增设计文档：
  - `docs/data-scale-overlay-integration.md`（main + bundled）
- 文档同步：
  - `README.md`、`SKILL.md`、`references/index.md` 更新 data-scale overlay 说明与入口
- 验证结果（本地）：
  - `scripts/verify/vibe-pack-routing-smoke.ps1`：PASS
  - `scripts/verify/vibe-config-parity-gate.ps1`：PASS
  - `scripts/verify/vibe-data-scale-overlay-gate.ps1`：PASS

## v2.3.6 (2026-02-25)

- 修复统一 `/vibe` 入口安装漂移问题（关键修复）：
  - `install.ps1` 与 `install.sh` 现在会强制同步：
    - `skills/vibe/scripts/router/resolve-pack-route.ps1`
  - 避免“文档/配置已升级但本地路由脚本仍旧版”导致的新功能不触发。
- 健康检查增强：
  - `check.ps1`、`check.sh` 新增检查项：
    - `skills/vibe/scripts/router/resolve-pack-route.ps1`
    - `skills/vibe/config/memory-governance.json`

## v2.3.5 (2026-02-25)

- 新增 Memory Governance 增强层（post-route advice only，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/memory-governance.json`
    - `bundled/skills/vibe/config/memory-governance.json`
  - 路由器输出新增：
    - `memory_governance_advice`
  - 语义边界（影子模式默认）：
    - `state_store` 仅会话状态
    - `Serena` 仅显式项目决策
    - `ruflo` 仅短期会话向量缓存
    - `Cognee` 仅长期图记忆与关系检索
    - `episodic-memory` 在 VCO 治理路径中禁用
- 回退链与规则同步：
  - `references/conflict-rules.md`、`references/fallback-chains.md`、`references/tool-registry.md`
  - `protocols/retro.md` 移除 episodic-memory 活跃依赖，改为 Serena/ruflo/Cognee 分工
- 新增门禁与一致性检查：
  - 新增 `scripts/verify/vibe-memory-governance-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `memory-governance` main/bundled parity
  - `scripts/verify/README.md` 增加执行入口
- 新增设计文档：
  - `docs/memory-governance-integration.md`（main + bundled）
- `SKILL.md` 更新内联 Memory Rules 与 Rule 2 摘要，统一到五层边界模型。

## v2.3.4 (2026-02-25)

- 新增 prompts.chat Prompt 资产增强层（post-route overlay，不替代 Pack 路由）：
  - 新增配置（main + bundled）：
    - `config/prompt-overlay.json`
    - `bundled/skills/vibe/config/prompt-overlay.json`
  - 路由器输出新增：
    - `prompt_overlay_advice`
    - `prompt_overlay_route_override`
  - 语义行为：
    - prompt/doc 冲突时，在 soft/strict 策略下将 `pack_overlay` 提升为 `confirm_required`
    - 非冲突请求保持原路由行为
- 路由边界收敛（避免 prompt/doc 误路由）：
  - `prompt-lookup` 扩展 prompt-intent 正关键词并补齐 `canonical_for_task`
  - `openai-docs` / `openai-knowledge` / `documentation-lookup` 增加 prompt-intent 负关键词
  - `ai-llm` pack 增补 `prompts.chat` / `prompt refine` 触发词
- 门禁与可观测性增强：
  - 新增 `scripts/verify/vibe-prompt-overlay-gate.ps1`
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `prompt-overlay` main/bundled 一致性检查
  - `scripts/verify/README.md` 更新执行入口
- 文档更新：
  - 新增 `docs/prompt-overlay-integration.md`（main + bundled）
  - 更新 `README.md`、`SKILL.md`、`references/index.md`
  - `THIRD_PARTY_LICENSES.md`、`config/upstream-lock.json` 增加 `f/prompts.chat` 集成边界说明

## v2.3.3 (2026-02-25)

- 新增 GSD-Lite Overlay（post-route protocol hooks，不引入第二编排器）：
  - 新增配置（main + bundled）：
    - `config/gsd-overlay.json`
    - `bundled/skills/vibe/config/gsd-overlay.json`
  - 新增 rollout 切换脚本：
    - `scripts/governance/set-gsd-overlay-rollout.ps1`
    - 支持 `off|shadow|soft-lxl-planning|strict-lxl-planning`
- 协议层增强（不修改核心路由）：
  - `protocols/think.md` 新增 `B5: GSD-Lite Preflight Hook`
    - brownfield context snapshot
    - assumption preflight + mode-aware confirm
  - `protocols/team.md` 新增 `GSD-Lite Wave Contract Hook`
    - XL planning/coding 的 wave metadata 契约
- 回退链增强：
  - `references/fallback-chains.md` 新增 GSD-Lite overlay fallback 规则
  - 保证 hook 失败时回到既有 VCO 主链，不改变 selected grade/task/pack
- 验证门禁扩展：
  - `scripts/verify/vibe-config-parity-gate.ps1` 纳入 `gsd-overlay` main/bundled 一致性校验
  - `scripts/verify/vibe-gsd-overlay-gate.ps1` 新增统一入口触发语义门禁（scope + mode + enforcement）
- 路由可观测性增强（不改变路由决策）：
  - `scripts/router/resolve-pack-route.ps1` 输出新增 `gsd_overlay_advice`
- 文档更新：
  - 新增 `docs/gsd-vco-overlay-integration.md`
  - 更新 `references/index.md`、`README.md`、`scripts/verify/README.md` 对应入口

## v2.3.2 (2026-02-25)

- 接入 `open-ralph-wiggum` 作为 `ralph-loop` 的可选后端（不替代 VCO 路由层）：
  - `bundled/skills/ralph-loop/scripts/ralph-loop.ps1` 新增双引擎：
    - `compat`（默认，保留原行为）
    - `open`（`--engine open`，委托外部 `ralph` CLI）
  - open 引擎默认安全参数：
    - 未显式指定 `--agent` 时自动补 `--agent codex`
    - 默认注入 `--no-commit`（可用 `--open-allow-commit` 关闭）
  - open 引擎与 compat-only 参数做显式边界保护：
    - `--next` / `--force` / `--state-file` / `--stop` 在 open 模式下拒绝
- 安装与依赖登记：
  - `config/upstream-lock.json` 新增 `Th0rgal/open-ralph-wiggum`（optional-external-cli）
  - `config/plugins-manifest.codex.json` 新增可选 scripted 安装项 `@th0rgal/ralph-wiggum`
  - `install.ps1` / `install.sh` 在 `-InstallExternal` 时安装 `@th0rgal/ralph-wiggum`
- 协议与文档更新：
  - `protocols/team.md`：Option C 增补 dual-engine 使用边界
  - `references/fallback-chains.md`：新增 Ralph 引擎回退链（open -> compat -> manual）
  - `references/tool-registry.md`：补充 open backend 与职责边界
  - `README.md`：新增 Ralph 双引擎接入与使用说明

## v2.3.1 (2026-02-25)

- 完成 OpenSpec 治理层零冲突接入（post-route governance overlay）：
  - 路由器追加 `openspec_advice` 元数据，不改变 `selected pack/skill`
  - `scripts/router/resolve-pack-route.ps1` 增加 OpenSpec policy 读取与治理建议输出
  - 新增主/镜像策略文件：
    - `config/openspec-policy.json`
    - `bundled/skills/vibe/config/openspec-policy.json`
- 新增治理与切换脚本：
  - `scripts/governance/invoke-openspec-governance.ps1`
  - `scripts/governance/set-openspec-rollout.ps1`
  - `scripts/governance/publish-openspec-soft-rollout.ps1`（单命令发布）
- 新增治理门禁脚本：
  - `scripts/verify/vibe-openspec-governance-gate.ps1`
- OpenSpec 渐进发布语义收敛：
  - 默认 `soft-lxl-planning`（`L/XL + planning => confirm_required`）
  - 发布流程改为 `precheck -> switch -> postcheck`
  - 默认不自动回退；仅在显式 `-EnableEmergencyRollbackOnFailure` 时执行应急回退
  - 即使应急回退执行，发布脚本仍以失败退出码返回，避免掩盖问题
- 文档更新：
  - `README.md`
  - `docs/openspec-vco-integration.md`
  - `scripts/verify/README.md`
- 验证结果（本地）：
  - `vibe-pack-regression-matrix.ps1`：`54/54`
  - `vibe-routing-stability-gate.ps1 -Strict`：`PASS`
    - `route_stability=1.0000`
    - `top1_top2_gap=0.3572`
    - `fallback_rate=0.1500`
    - `misroute_rate=0.0750`
  - `vibe-openspec-governance-gate.ps1`：`42/42`

## v2.2.11 (2026-02-24)

- 新增 CER 对比工具：
  - `scripts/verify/cer-compare.ps1`
  - 输入两份 CER JSON，输出 Markdown/JSON 对比简报
  - 对比字段：`pattern_delta`、`fallback_rate_delta`、`stability_delta`、`context_pressure_delta`、`top1_top2_gap delta`
  - 支持可选 `-UpdateCurrentComparison` 回写当前 CER 的 `comparison` 字段
- retro 协议新增 Phase 5.10：
  - `protocols/retro.md` 增加 CER 跨迭代对比步骤与工具映射
- 验证与文档更新：
  - `scripts/verify/README.md` 增加 `cer-compare.ps1` 说明
  - `scripts/verify/vibe-context-retro-smoke.ps1` 增加 CER compare 引用与脚本存在性断言
  - `docs/context-retro-advisor-design.md` 增加 CER compare 验证与产物约定

## v2.2.10 (2026-02-24)

- 将 Context Retro Advisor 的触发条件从描述性规则落地为量化阈值（写入 `protocols/retro.md`）：
  - 重试峰值、回退频率、上下文预算压力、pack/skill 路由稳定性、top1-top2 路由间隔
- 新增 CER 标准模板（Markdown + JSON）与 JSON Schema：
  - `templates/cer-report.md.template`
  - `templates/cer-report.json.template`
  - `templates/cer-report.schema.json`
- 将 CER 产出挂到 retro Phase 5：
  - 生成 `outputs/retro/YYYY-MM-DD-<topic>-cer.md|json`
  - 写入 Serena memory 的 `cer-summary`
  - 可选执行 `vibe-retro-context-regression-matrix.ps1` 做回归门禁
- 新增 retro 回归矩阵脚本：
  - `scripts/verify/vibe-retro-context-regression-matrix.ps1`
  - 覆盖触发阈值固定案例与 CF-1..CF-6 分类稳定性固定案例
- 验证入口更新：
  - `scripts/verify/README.md`
  - `scripts/verify/vibe-context-retro-smoke.ps1` 增加模板/回归脚本存在性断言
- 文档更新：
  - `docs/context-retro-advisor-design.md` 增加量化阈值、CER 产物与验证计划

## v2.2.9 (2026-02-24)

- 新增 Context Retro Advisor（复盘专家层）并将 Agent-Skills-for-Context-Engineering 作为 retro 阶段的指导知识源（advisory-only，不自动改配置）：
  - `SKILL.md`：LEARN 阶段升级为 `continuous-learning-v2 + Context Retro Advisor`，新增触发条件与 CER 输出约束
  - `protocols/retro.md`：新增 Context Retro Advisor 角色、CF-1..CF-6 失败分类、CER（Context Evidence Report）输出契约
  - `references/fallback-chains.md`：新增 Retro Context Expert Fallback 链路
- 新增设计与验证资产：
  - `docs/context-retro-advisor-design.md`
  - `scripts/verify/vibe-context-retro-smoke.ps1`
  - `scripts/verify/README.md` 增补脚本说明
- 引用索引更新：
  - `references/index.md` 增加 Context Retro Advisor 设计文档入口
- main/bundled 同步更新：`SKILL.md`、`protocols/retro.md`、`references/fallback-chains.md`、`references/index.md`、`references/changelog.md`

## v2.2.8 (2026-02-24)

- 完成 Batch E 最终硬清理（final cleanup）并切换到 canonical-only 运行态：
  - `config/skill-alias-map.json` 清空为 `{}`，停止 legacy alias 运行时解析
  - `bundled/skills/vibe/config/skill-alias-map.json` 同步为 canonical-only，消除 main/bundled 漂移
- 清理 Batch E 阻断项并统一 canonical 路由：
  - `spec-kit-vibe-compat/command-map.json`：`code-review3 -> code-review`
  - `security-reviewer/SKILL.md`、`think-harder/SKILL.md`：移除 `code-review3` 依赖表述
  - `scripts/verify/vibe-soft-migration-practice.ps1`、`vibe-pack-regression-matrix.ps1`：改为 canonical RequestedSkill 场景
  - `scripts/verify/vibe-pack-routing-smoke.ps1`：修复 alias 为空场景的布尔断言
- 安装器收口为 canonical-first：
  - `install.ps1`、`install.sh` 均优先 `skills/<name>`，仅将 `superpowers/skills/<name>` 作为 fallback
- 新增最终清理报告：
  - `docs/hard-migration-batch-e-final-cleanup-report.md`
- 审计留痕策略：
  - `config/batch-e-alias-whitelist.json` 标记为 historical snapshot（仅审计留痕，不参与运行时路由）
  - `docs/hard-migration-batch-e-alias-whitelist-audit.md` 标记为已被 final cleanup report 取代
- 全套验证通过：
  - `vibe-routing-smoke.ps1`: `38/38`
  - `vibe-pack-routing-smoke.ps1`: `49/49`
  - `vibe-skill-index-routing-audit.ps1`: `93/93`
  - `vibe-keyword-precision-audit.ps1`: `982/982`
  - `vibe-pack-regression-matrix.ps1`: `24/24`
  - `vibe-soft-migration-practice.ps1`: `11/11`

## v2.2.7 (2026-02-24)

- 完成 Batch E「可删 alias 白名单生成 + 影响面审计（不删先审）」：
  - 新增 `config/batch-e-alias-whitelist.json`（28 个 alias 风险分层与分阶段删除门禁）
  - 新增 `docs/hard-migration-batch-e-alias-whitelist-audit.md`（影响面审计报告）
- 验证阶段补充编码兼容性加固（Windows PowerShell）：
  - `scripts/router/resolve-pack-route.ps1` 显式 `-Encoding UTF8` 读取 JSON 配置
  - `scripts/verify/vibe-pack-routing-smoke.ps1` 显式 `-Encoding UTF8` 读取 JSON 配置
  - `scripts/verify/vibe-routing-smoke.ps1` 显式 `-Encoding UTF8` 读取文档
- 审计结论（当前不删除）：
  - 低风险可删候选（E2，门禁后执行）：`15`
  - 中风险延后（E3）：`11`
  - 高风险延后（E4）：`2`（`code-review3`、`xlsx1`）
- 关键阻断点：
  - 验证脚本仍显式依赖 `code-review3`、`xlsx1`
  - `spec-kit-vibe-compat` 与部分 SKILL 文档仍引用 `code-review3`
  - `dependency-map.json` 仍包含 `superpowers/skills/*` 路径耦合
- Batch E 当前阶段为 audit-only，不执行 alias 删除；后续删除需通过全套路由/精度/回归验证门禁。

## v2.2.6 (2026-02-24)

- 完成 Batch C/D 硬迁移候选裁剪（pack-level candidate pruning）：
  - `data-ml`: `52 -> 25`
  - `research-design`: `45 -> 25`
  - `ai-llm`: `13 -> 11`
  - `bio-science`: `34 -> 21`
  - `docs-media`: `22 -> 16`
  - `integration-devops`: `14 -> 12`
  - Batch C/D 合计：`180 -> 110`（减少 `70`, `38.89%`）
- 保持不变：
  - grade/task 边界
  - alias 映射
  - fallback 阈值与机制
- 变更前快照：
  - `outputs/backups/pack-manifest-pre-batch-cd-20260224-225014.json`
- 新增报告：
  - `docs/hard-migration-batch-cd-pruning-report.md`
- 验证通过：
  - `vibe-routing-smoke.ps1`: `38/38`
  - `vibe-pack-routing-smoke.ps1`: `104/104`
  - `vibe-skill-index-routing-audit.ps1`: `93/93`
  - `vibe-keyword-precision-audit.ps1`: `982/982`
  - `vibe-pack-regression-matrix.ps1`: `24/24`

## v2.2.5 (2026-02-24)

- 完成 Hard Migration Batch A2（bundled overlap 清理）：
  - 删除 `skills/vibe/bundled/skills` 下 8 个与 canonical 重复目录
  - 删除 `skills/vibe/bundled/superpowers-skills` 下 7 个与 canonical 重复目录
  - 保留 `bundled/skills/vibe` 作为 bundled 入口
- 硬迁移前新增目录级备份：
  - `outputs/backups/skills-pre-hard-migration-20260224-224135.zip`
- 为避免迁移后安装流程断裂，升级安装脚本 fallback：
  - `install.ps1`、`install.sh` 改为优先 canonical 路径，缺失时回退 bundled 路径
- 新增迁移报告：
  - `docs/hard-migration-batch-a2-report.md`
- 验证通过：
  - `vibe-routing-smoke.ps1`: `38/38`
  - `vibe-pack-routing-smoke.ps1`: `104/104`
  - `vibe-skill-index-routing-audit.ps1`: `93/93`
  - `vibe-keyword-precision-audit.ps1`: `1402/1402`
  - `vibe-pack-regression-matrix.ps1`: `24/24`
  - `check.ps1` (after install): `21 passed, 0 failed`

## v2.2.4 (2026-02-24)

- 基于全局历史日志语言习惯，追加 per-skill 中文业务短语索引（仅增量，不删除旧关键词）：
  - `vibe`
  - `writing-plans`
  - `verification-quality-assurance`
  - `mcp-integration`
  - `scikit-learn`
  - `biopython`
- 处理同 pack 内选择抖动：补充 `writing-plans` 的迁移场景短语（如“先做软迁移”“验证命中稳定”）。
- main/bundled 配置已同步：
  - `config/skill-keyword-index.json`
  - `bundled/skills/vibe/config/skill-keyword-index.json`
- 全套验证通过（补丁后）：
  - `vibe-skill-index-routing-audit.ps1`: `93/93`
  - `vibe-keyword-precision-audit.ps1`: `1402/1402`
  - `vibe-pack-regression-matrix.ps1`: `24/24`
- 追加专项对比报告：
  - `outputs/routing-audit/per-skill-chinese-index-comparison-report.md`
  - 命中率（专项短语集）`8/12 -> 12/12`，无新增回归。

## v2.2.3 (2026-02-24)

- 新增 per-skill 关键词索引配置：`config/skill-keyword-index.json`
  - 面向常见中文业务短语（如“修改xlsx工作簿”“会议录音转文字”“查询OpenAI文档”“单细胞分析”“修复GitHub Actions CI”等）
  - 用于降低同 pack 内 skill 选择抖动
- 路由器升级：`scripts/router/resolve-pack-route.ps1`
  - Pack 评分新增 `skill_keyword_signal`（来自 per-skill 索引的 pack 前置信号）
  - Pack 内 skill 选择改为 keyword ranking（显式 RequestedSkill 仍最高优先）
  - 同分时优先 `keyword_score`，减少名称匹配导致的泛化偏置
- 调整配置：
  - `router-thresholds.json` 增加 `weights.skill_keyword_signal`
  - `pack-manifest.json` 进一步补全中英文 trigger（录音/说话人、差异表达/BAM/VCF、Responses API、IMRAD、准实验等）
- 新增专项验证脚本：`scripts/verify/vibe-skill-index-routing-audit.ps1`
  - 覆盖 30+ 组中英文业务短语场景
  - 校验 pack 命中、skill 命中和选择稳定性
- `vibe-pack-routing-smoke.ps1` 增加 skill-index 配置完整性断言
- main/bundled 配置保持同步（含新增 `skill-keyword-index.json`）

## v2.2.2 (2026-02-24)

- 完成迁移后关键词精度专项整治（目标：中英文命中、降互扰、全量 skill 可达）
- 路由匹配器增强：`scripts/router/resolve-pack-route.ps1`
  - 新增 `Test-KeywordHit` 统一命中函数
  - 英文关键词改为 token boundary 匹配，减少 substring 误命中
  - CJK 关键词保持 substring 匹配，提升中文稳定命中
- `config/pack-manifest.json` 为 8 个 pack 全量补齐中英文 `trigger_keywords`
- 新增全量审计脚本：`scripts/verify/vibe-keyword-precision-audit.ps1`
  - 校验每个 pack 至少包含中英关键词
  - 校验 EN/ZH pack 级路由与 top1-top2 干扰间隔
  - 校验全部 223 个候选 skill 的 EN/ZH 定向命中稳定性
- 更新回归矩阵基线：`scripts/verify/vibe-pack-regression-matrix.ps1`（bio-science fallback 断言与当前阈值一致）
- 更新验证文档入口：`scripts/verify/README.md`
- 同步 bundled 配置，保持 main/bundled 无漂移

## v2.2.1 (2026-02-24)

- 完成 Soft Migration Batch B 扩容（保留 soft migration 语义，不执行 hard delete）
- `pack-manifest.json` 扩展到 near-full canonical 覆盖，8 个 pack 候选总数提升到 223
- `router-thresholds.json` 将 `max_skill_candidates_per_pack` 从 `7` 调整到 `80`
- 同步 bundled 配置副本，避免 main/bundled 漂移：
  - `bundled/skills/vibe/config/pack-manifest.json`
  - `bundled/skills/vibe/config/router-thresholds.json`
- 新增扩容验证报告：`docs/soft-migration-batch-b-expansion-report.md`
- 四项验证脚本全通过（routing/pack smoke/practice/regression matrix）

## v2.2.0 (2026-02-24)

- 完成 Hard Migration Batch A（在软迁移验证通过后执行）
- 删除顶层重复目录：
  - `skills/code-review1`
  - `skills/code-review2`
  - `skills/code-review3`
  - `skills/code-review4`
  - `skills/xlsx1`
- 保留 canonical 目录与 alias 映射，未破坏 fallback 路径
- 新增迁移报告：`docs/hard-migration-batch-a-report.md`

## v2.1.1 (2026-02-24)

- 新增软迁移路由解析器：`scripts/router/resolve-pack-route.ps1`
- 新增软迁移实践测试：`scripts/verify/vibe-soft-migration-practice.ps1`
- 新增软迁移执行手册：`docs/soft-migration-playbook.md`
- 更新 verify README 与 references index，纳入软迁移验证入口

## v2.1.0 (2026-02-24)

- 新增 Pack Router 融合层：在 Grade×TaskType 路由后执行 pack 评分与候选 skill 选择
- 新增路由配置文件：
  - `config/pack-manifest.json`
  - `config/skill-alias-map.json`
  - `config/router-thresholds.json`
- 新增大型重构主计划：`docs/skills-consolidation-roadmap.md`
- 新增 Pack 路由 smoke 校验脚本：`scripts/verify/vibe-pack-routing-smoke.ps1`
- 更新 `SKILL.md` 与 references 文档，明确 pack 路由边界和低置信度回退到 legacy matrix

## v2.0.10 (2026-02-24)

- 将决策提问接口从 `AskUserQuestion` 重构为 runtime-neutral `user_confirm interface`
- 将状态记录从 `TodoWrite` 重构为 runtime-neutral `state_store` 抽象
- 同步更新核心文档与 bundled 副本（SKILL / protocols / references / hooks）
- 新增自动化快速自测脚本，覆盖 M/L/XL 三个 `/vibe` 路由场景与关键约束断言

## v2.0.9 (2026-02-24)

- 删除 XL 设计中的 legacy compatibility orchestration 描述，统一为 Codex native agent runtime + ruflo 协作
- team.md 移除 compatibility orchestration option，仅保留 Native+ruflo 与 Native-only 路径
- fallback-chains.md 移除 compatibility Level，XL 仅保留 Native+ruflo -> Native-only -> L-grade sequential
- conflict-rules.md Rule 1 移除 compatibility agent system 条目
- tool-registry.md 移除 compatibility orchestration 集成描述，聚焦 ruflo 与 native team runtime

## v2.0.8 (2026-02-24)

- XL 标准路径明确为 `spawn_agent` / `send_input` / `wait` / `close_agent` 与 ruflo 协作（workflow/memory/consensus）
- team.md orchestration options 调整为：A=Native+ruflo（首选），B=Native-only（ruflo 不可用）
- fallback-chains.md 的 XL 链路更新为 Native+ruflo 优先，并补充 ruflo 不可用时的 native-only 降级
- conflict-rules.md Rule 1 更新为 XL=Native+ruflo 主路径，补充 native-only 分支
- team-templates.md 全量迁移为 native agent type (`default`/`explorer`/`worker`) 与 `send_input` 通信语义
- review.md 移除 `Task tool + subagent_type` 的旧表述，改为单代理直接调用 code-reviewer

## v2.0.7 (2026-02-24)

- XL execution primary path switched to Codex native agent orchestration (`spawn_agent` / `send_input` / `wait` / `close_agent`)
- Legacy compatibility fallback path downgraded from primary XL design
- Added explicit `build-error-resolver -> error-resolver` compatibility mapping in fallback and tool-detection guidance
- Updated team protocol role mapping to native agent types (`default`, `explorer`, `worker`)

## v2.0.6 (2026-02-22)

- C1 修复 conflict-rules.md Rule 1 与 Tool Selection 矩阵矛盾——M 级从"Everything-CC agents"改为"single-agent tools（允许 sc:design/systematic-debugging 等 skill commands，禁止 subagent spawning）"
- C2 修复 L 级 Dialectic Mode 使用只读 Plan agent 的问题——改为 general-purpose agent
- C3 在 SKILL.md Section 2 Tool Selection 矩阵下方添加 Excluded tools 说明（sc:implement 禁令）

## v2.0.5 (2026-02-22)

- Quick Probe 补充中文关键词（设计/架构/重构/迁移/前后端/并行/多智能体）
- index.md 模板数量 5→6
- do.md 术语 "Fallback exception" → "Fallback provision" 与 conflict-rules.md 统一
- retro.md Phase 2 各步骤补充显式 fallback 路径

## v2.0.4 (2026-02-22)

- 新增 dialectic-design 到 specialized agents 列表
- M 级补充 Behavioral Tone 引用
- team-templates 更新为 6 模板
- team.md 新增 Dialectic Mode 完整章节

## v2.0.3 (2026-02-22)

- M 级 stage sequence 移至概览行
- scope check 改为定性+定量 OR 条件
- conflict-rules.md 补充 fallback provision
- 补充探测失败默认行为
- low-friction rule 补充分类反馈格式
- Grade Definitions 增加 Key Signal 列和冲突裁决规则

## v2.0.2 (2026-02-22)

- 修复 do.md L 级 fallback exception 与 conflict rule 的矛盾
- P3/V1 补充内联定义
- team.md 补充 ToolSearch 前置步骤
- SKILL.md M 级补充阶段顺序和影响范围超预期暂停规则

## v2.0.1 (2026-02-22)

- S grade removed (implicit), 4→3 grades, 8→5 protocols, 6→3 conflict rules
- Quick probe + user decision gate added
- Team templates added
