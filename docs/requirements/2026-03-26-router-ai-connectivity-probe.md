# Router AI 连通性探针需求文档

**日期**: 2026-03-26
**对应议题**: `#33`
**任务类型**: 可观测性补齐 / 用户诊断入口
**优先级**: 高
**执行模式**: truth-first，先补齐诊断边界与状态模型，再落地实现

---

## 目标（Goal）

为 Vibe 路由中的 AI 意图分析 / advice 层提供一个用户可直接运行、结果可读、结论诚实的连通性测试入口，让用户知道自己当前是：

1. 已成功连通 AI advice provider
2. 已配置但当前不会触发
3. 缺少关键配置而处于 offline degrade
4. provider 可达但模型/请求不被接受
5. `vector_diff` / embeddings 子能力未配置或不可用

## 交付物（Deliverable）

1. 一条用户可直接运行的 Router AI Connectivity Probe 入口
2. 一份清晰、有限、可验证的状态模型
3. 终端摘要输出 + JSON / Markdown artifact
4. 覆盖 mock、offline、scope gating、provider failure、vector diff 的测试矩阵
5. 安装 / 配置文档中的诊断说明

## 问题陈述（Problem Statement）

当前仓库已经有：

1. `bootstrap doctor` 风格的 readiness 诊断
2. `llm_acceleration_advice` 及 provider-assisted 路由 advice 层
3. provider 缺失时的 offline degrade 契约

但普通用户仍然无法直接回答下面的问题：

1. “我现在的 AI 路由 advice 到底有没有配通？”
2. “是完全没配，还是当前不触发，还是已经静默退化？”
3. “`vector_diff` 这类增强子能力有没有通？”

Issue `#33` 需要补的是这层可观测性，而不是新增第二套路由系统。

## 约束（Constraints）

1. 不能引入第二控制平面
2. 不能修改 canonical router 的最终选择
3. 不能把 probe 结果写回正式路由配置
4. 不能把 `/vibe` prefix gating 误报成 provider 故障
5. 不能把 AI advice 未连通夸大为“整个 Vibe-Skills 不可用”
6. 必须区分“本地配置存在”与“在线 advice 可调用”
7. 必须保留 offline degrade 的诚实边界

## 验收标准（Acceptance Criteria）

1. 用户运行一次 probe 命令即可得到简洁结论与下一步建议
2. Probe 至少能区分以下状态：
   - `disabled_by_policy`
   - `prefix_required`
   - `scope_not_applicable`
   - `missing_credentials`
   - `missing_model`
   - `provider_unreachable`
   - `provider_rejected_request`
   - `parse_error`
   - `ok`
   - `vector_diff_not_configured`
   - `vector_diff_unavailable`
   - `vector_diff_ok`
3. Probe 不改变 route result，不提升 confirm_required，不做 pack override
4. 无真实 API 时，mock / fixture 测试能稳定通过
5. 有真实 API 时，可进行 opt-in live proof，并把 live 与 mock 结果分离记录
6. 文档明确说明：
   - 这是 router AI advice probe
   - 不是整个宿主在线能力总探针
   - 不是 host 登录 / MCP / plugin 全面健康检查

## 非目标（Non-Goals）

1. 不新建新的 AI rerank / route engine
2. 不重写 `llm_acceleration` 设计
3. 不扩展为全量 host / plugin / MCP 平台总医生
4. 不修改 install/check 的公共 truth 声明
5. 不把 `context_manager.py` 之类示例模块接入生产主链

## 用户可见结果要求（User-Facing Outcome）

用户必须能够在终端直接读懂类似结果：

1. `Router AI advice: online and responding`
2. `Router AI advice: offline degrade active (missing_openai_api_key)`
3. `Router AI advice: configured but current scope requires /vibe`
4. `Vector diff embeddings: not configured`
5. `Vector diff embeddings: provider reachable but request failed`

## 质量定义（Quality Definition）

### 稳定性（Stability）

1. 相同 fixture 输入得到相同状态输出
2. probe 不依赖隐式全局状态才能给出分类
3. mock 路径与 live 路径使用同一状态模型
4. probe 执行失败时返回结构化失败，不 silent fallback

### 可用性（Usability）

1. 一条命令可运行
2. 输出短、可读、有 next step
3. JSON / Markdown artifact 便于 issue 贴证据
4. 不要求用户先理解内部 router 模块

### 智能性（Intelligence）

这里的“智能性”不指更强的生成能力，而指：

1. 能正确区分 gating、配置缺失、provider 不通、request 被拒、parse 失败
2. 能在不篡改路由 truth 的前提下给出最接近真实原因的分类
3. 能把 `vector_diff` 子能力与主 advice provider 分开说明

## 证明要求（Proof Requirements）

必须提供三类证明：

1. **稳定性证明**
   - fixture / mock regression tests
   - no-route-mutation assertions
   - artifact schema stability
2. **可用性证明**
   - 终端示例输出
   - Markdown artifact 示例
   - 文档中的最小运行示例
3. **智能性证明**
   - 状态分类矩阵
   - 失败原因覆盖表
   - live optional proof 与 mock proof 对照

## 文档固化要求（Documentation Freeze）

本议题完成后，至少需要固化：

1. 需求文档
2. 执行计划
3. probe 使用说明
4. probe 输出状态说明
5. 测试矩阵与证明口径
