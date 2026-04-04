# BrowserOps provider 治理接入（VCO / Wave24）

## 1. 文档目的

Wave24 的目标不是把 `browser-use` 作为新的 agent runtime 或新的 orchestrator 接进 VCO，而是把它吸收到 **BrowserOps provider candidate 平面**，与现有 `api / playwright / chrome-devtools / turix-cua` 一起接受统一治理。

这份文档只解决一个问题：

- 在浏览器相关任务里，VCO 应如何给出 **单一控制面下的 provider 建议**。
- 如何在不引入第二编排器、不引入第二执行 owner 的前提下，吸收 `browser-use` 的开放式浏览价值。
- 如何保持 **advice-first / shadow-first / rollback-first** 的治理风格。

## 2. 定位结论（必须保持不变）

### 2.1 BrowserOps 的唯一控制面

- VCO 仍是唯一控制面、唯一路由入口、唯一 pack 选择者。
- BrowserOps 只负责在既有浏览器执行能力之间给出 **provider suggestion**。
- BrowserOps provider plane 不得获得任务拆解权、团队编排权、promotion 决策权。

### 2.2 `browser-use` 的吸收位置

`browser-use` 在 VCO 中的定位必须固定为：

- **BrowserOps provider candidate**
- **开放式网页浏览 / 多步导航 / research navigation 候选执行面**
- **建议层能力来源**，不是默认执行 owner
- **受 `confirm_required` 与 fallback 约束的候选 provider**

> 结论：`browser-use` 不是新 orchestrator，不是第二条路由面，不得 takeover。

## 3. 治理边界

### 3.1 明确允许

允许 `browser-use` 被吸收为：

- provider recommendation 的候选项
- 开放式浏览任务的 shadow / advice 能力来源
- 与 `playwright` 形成“探索式导航 -> 可回退到确定性脚本”的补强关系

### 3.2 明确禁止

以下行为在 BrowserOps plane 中一律禁止：

- 把 `browser-use` 升格为第二 orchestrator
- 绕过 VCO 主路由直接接管任务
- 夺取 `selected pack / selected skill / selected protocol` 的决定权
- 在没有 `fallback_provider` 的情况下直接成为默认执行面
- 在未显式确认时 takeover 高风险网页动作

## 4. provider 优先级与场景矩阵

### 4.1 通用优先级

默认优先级固定为：

`api -> playwright -> chrome-devtools -> turix-cua -> browser-use`

含义如下：

1. **优先结构化接口**：能走 API 就不先走浏览器。
2. **优先确定性自动化**：能用 `playwright` 稳定完成，就不先走开放式 agent 浏览。
3. **调试与执行分离**：`chrome-devtools` 主要用于诊断，不作为默认业务执行面。
4. **视觉/开放式路径后置**：`turix-cua` 与 `browser-use` 都必须处于 confirm 偏置下。

### 4.2 场景映射

| 任务形态 | 首选 provider | 次选 / 回退 | 说明 |
|---|---|---|---|
| API / GraphQL / HTTP / 结构化抓取 | `api` | `playwright` | 优先低成本、可验证路径 |
| 登录 / 表单 / 点击 / DOM 抽取 | `playwright` | `chrome-devtools` | 默认确定性浏览器基线 |
| request/response / console / 性能调试 | `chrome-devtools` | `playwright` | 以诊断为主，不抢业务执行 |
| 真实界面 / 视觉依赖 / 弱结构页面 | `turix-cua` | `playwright` | 必须保留 confirm_required |
| 开放式浏览 / 跨站导航 / research navigation | `browser-use` | `playwright` | 只作为 provider candidate，不能 takeover |

## 5. advice-first / shadow-first 运行规则

### 5.1 advice-first

`scripts/overlay/suggest-browserops-provider.ps1` 只输出：

- `provider`
- `reason`
- `confidence`
- `confirm_required`
- `fallback_provider`

它不会：

- 修改 VCO 路由结果
- 直接执行 provider
- 直接改变 pack / protocol / team 选择

### 5.2 shadow-first

`browser-use` 与 `turix-cua` 默认都处于 shadow 偏置：

- 先建议
- 再确认
- 再执行
- 执行失败时必须自动回退到 `playwright` 或人工 SOP

### 5.3 rollback-first

任何 BrowserOps 候选 provider 都必须具备：

- `fallback_provider`
- `verification_artifact`
- `confirm_required` 判断
- 明确的“为什么不走 API / 为什么不走 Playwright”说明

## 5.4 Browser-use operational guidance intake

本轮上游吸收只允许进入 guidance / eval 层，不允许进入 ownership 层：

- 文本查找优先使用 `search_page`，因为它对应开放页面中的文本定位语义。
- 结构、属性、候选元素枚举优先使用 `find_elements`，而不是把结构探测伪装成全文搜索。
- 不得假设 `read_long_content` 一定存在；长页面内容必须走 bounded extraction、分页提取，或显式回退到 `playwright` / 人工 SOP。
- preview model 默认保持 upstream Browser Use system prompt 连续性；若要覆盖，必须留下显式 operator evidence。
- Vercel gateway、auth、model-surface 漂移只作为 provider-preview evidence 记录，不得被解释为 BrowserOps owner 迁移。

## 6. 关键资产

- Policy：`config/browserops-provider-policy.json`
- Contract：`references/browser-task-contract.md`
- Suggestion script：`scripts/overlay/suggest-browserops-provider.ps1`
- Gate：`scripts/verify/vibe-browserops-gate.ps1`

## 7. 与现有资产的关系

### 7.1 与 `docs/design/turix-cua-overlay.md` 的关系

- `turix-cua-overlay` 负责 **overlay 视角增强**。
- BrowserOps provider plane 负责 **provider 候选治理**。
- 两者是组合关系，不是替代关系。

### 7.2 与 Wave19-23 的关系

- 本文延续 `单一控制面 / 单层单责 / 后置治理优先` 的总纲。
- 与 memory / prompt / letta / mem0 一样，`browser-use` 只吸收其高价值部分，不引入平行 runtime。

## 8. 验证方式

```powershell
pwsh -File .\scripts\verify\vibe-browserops-gate.ps1
```

门禁应至少验证：

- policy 中明确禁止第二 orchestrator 与 provider takeover
- `browser-use` 仅为 provider candidate
- provider 优先级与适用场景一致
- suggest 脚本能输出 `provider / reason / confidence / confirm_required`
- contract 中保留 fallback 与不变量约束

## 9. 完成定义（Definition of Done）

满足以下条件才视为 Wave24 BrowserOps provider 治理落地完成：

- `browser-use` 已被纳入 BrowserOps provider candidate 平面
- 文档中明确 `browser-use` 不是新 orchestrator
- policy 中有优先级、场景、禁止 takeover 的结构化表达
- suggest 脚本可稳定输出建议 provider、理由、置信度、确认要求
- gate 可以验证 policy 与 contract 的关键不变量
