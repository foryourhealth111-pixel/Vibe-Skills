# GPT‑5.2 × VCO：LLM Acceleration Overlay 设计（/vibe 显式启用）

日期：2026-03-04  
状态：Draft（本次提交会落地实现 + gate + 文档同步）

---

## 1. 背景与目标

VCO 当前的路由体系以 **deterministic + rule/threshold/overlay** 为主（pack scoring → post-route overlays → confirm UI），稳定、可解释、可离线。但在真实工程协作里仍有两个痛点：

1. **模糊需求的澄清成本**：用户描述不完整时，靠 heuristic 可能进入 confirm_required，但确认问题不够“对症”，导致多轮来回。
2. **跨域/跨 pack 的误路由**：当 top1/top2 gap 小、或者关键词重叠时，纯规则重排难以“理解真实意图”。

本设计引入一个新的路由增强层：**LLM Acceleration Overlay**。

### 目标（Goals）

- 在不破坏 VCO 现有稳定性的前提下，引入 GPT‑5.2（优先 `gpt-5.2-codex`）做“认知增强”：
  - 生成更好的 **确认问题（confirm questions）**
  - 对 top‑K 路由候选做 **语义重排建议（rerank advice）**
  - 生成 **意图契约补全（intent contract enrichment）** 与 “缺口（unknowns）”
  - 在任何阶段都可输出 **测试/质量建议（QA advisory）**（满足“测试部门可在任何阶段推荐”）
- 支持“烧 API 换时间”的策略（并行/推测/复核），但**只在显式 `/vibe` 或 `$vibe` 前缀时启用**。
- 默认 **advice-first**：即便 LLM 运行失败，也不影响核心路由；并且不默认替换 pack/skill 选择。

### 非目标（Non‑Goals）

- 不把 LLM 变成新的“主路由器”（不引入第二控制平面）。
- 不要求一定联网、不要求一定存在 `OPENAI_API_KEY`（无 key 时必须安全 abstain）。
- 不把 GitNexus/agency‑agents 的 overlay 逻辑强耦合进 router（它们仍是 prompt overlay advice/手动注入路径；未来可由 LLM 仅做推荐，不做强制）。

---

## 2. 总体原则

### 2.1 控制平面确定性，LLM 认知增强

- **Core routing**（pack scoring + thresholds + deterministic overlays）仍是唯一“真值”来源。
- LLM overlay 只输出：
  - `llm_acceleration_advice`（结构化 JSON，包含建议、置信度、原因）
  - 可选的 `route_mode` 提升建议（例如：把 `pack_overlay` → `confirm_required`，但默认不替换 `selected`）

### 2.2 显式 /vibe 才启用

- 仅当 `promptNormalization.prefix_detected == true` 才执行 LLM acceleration。
- 普通对话/非 /vibe 任务：零额外 API 调用，保持“隐式 S 级、零开销”的体验。

### 2.3 “烧 API 换时间”是配置化策略

通过 `config/llm-acceleration-policy.json` 提供 **Speed Profile**：

- `balanced`：单次调用，低延迟、低成本、稳定。
- `max_speed`：允许并行子任务（例如 rerank + confirm + QA guard），并在 `confirm_required` 场景启用推测（speculation）。

> 备注：并行/推测属于“更快得到更好建议”，不是“更激进改变路由”。

---

## 3. 路由接入点与数据流

### 3.1 接入点（Router hook）

位置：`scripts/router/resolve-pack-route.ps1` 的 pack scoring 之后（已拿到 `ranked/topGap/confidence/routeMode`），在 confirm UI 生成之前。

理由：
- 能拿到 top‑K 候选（LLM 能做 rerank）
- 能拿到已存在的 overlay 信号（LLM 可补充确认问题）
- 不影响 pack scoring 的 determinism

### 3.2 数据流（Data flow）

1. prompt normalization（拿到 `prefix_detected`）
2. pack scoring 得到 `ranked` + `confidence` + `top1_top2_gap`
3. 若满足 gating：
   - 采集上下文（按策略：prompt + topK + 选填 git diff/status）
   - 调用 OpenAI Responses API（Structured Output，JSON schema 严格）
   - 产出 `llm_acceleration_advice`
4. 根据 `mode`：
   - `shadow`：只写入 advice
   - `soft`：允许将 `route_mode` 提升为 confirm_required（不替换 selected）
   - `strict`：在 allowlist + topK + 置信度阈值下，允许替换 selected（可选，默认关闭）

---

## 4. 配置设计：`llm-acceleration-policy.json`

关键字段（概念级）：

- `enabled / mode`：`off | shadow | soft | strict`
- `activation.explicit_vibe_only = true`
- `provider.type = openai | mock`
- `models.primary = gpt-5.2-codex`（可配置）
- `context.mode = diff_snippets_ok`
  - `include_git_status`（bool）
  - `include_git_diff`（bool）
  - `max_diff_chars`（截断）
- `speed_profile`：`balanced|max_speed`
- `safety`：
  - `fallback_on_error = true`
  - `require_candidate_in_top_k = true`
  - `min_override_confidence`（strict 用）
- `telemetry`：
  - `emit_probe_events`（输出到 route-probe）
  - `include_latency_ms`

---

## 5. OpenAI 接入设计（Responses API）

实现一个最小可复用客户端模块：

- 输入：`model + input + response_format(json_schema strict) + timeout_ms`
- 输出：解析后的对象；失败则返回 `abstained + reason`
- 无 `OPENAI_API_KEY`：直接 abstain（不抛异常，不影响路由）

---

## 6. 验证与门禁

新增 gate：`scripts/verify/vibe-llm-acceleration-overlay-gate.ps1`

- **不依赖真实 API**：使用 `provider.type=mock` 或在无 key 下验证 abstain 路径。
- 断言：
  - overlay advice 字段存在且可解析
  - `explicit_vibe_only` 生效（非 /vibe 不触发）
  - mode=shadow 时不改变 selected/route_mode

并将配置加入 parity gate（main vs bundled）。

---

## 7. Rollout（推荐）

1. 默认：`mode=shadow`（只建议，不改路由）
2. 观察稳定性（misroute/confirm 率）
3. 小流量 `soft`（仅升级 confirm_required，不替换 selected）
4. 最后才考虑 `strict`（需 allowlist + 高置信度）

---

## 8. 与现有生态（agency‑agents / GitNexus）的关系

- `agency‑agents`：补齐部门/岗位视角（工程/设计/产品/市场/PM/测试/XR），以 prompt overlay 的方式注入。
- `GitNexus`：补齐代码理解与影响面证据方法（同样以 overlay 或 MCP 工具增强）。
- LLM acceleration overlay **不替代** 这些能力；它只会：
  - 在需要时推荐“应该注入哪些 overlay”
  - 帮你把确认问题问得更准确、更少轮次

