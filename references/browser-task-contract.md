# BrowserOps 任务契约（Browser Task Contract）

## 1. 目的

该 contract 用于把浏览器相关任务先归类为统一的 **BrowserOps task shape**，再交给 provider suggestion 层做受治理的选择。

它的职责只有两个：

1. 规范 BrowserOps 输入与输出字段。
2. 固化 BrowserOps provider plane 的关键不变量。

> 该 contract 不负责路由，不负责编排，也不负责直接执行。

## 2. 输入字段（最小集合）

进入 provider 建议层前，任务至少应能回答以下字段：

- `task_summary`：任务摘要
- `task_shape`：任务形态
- `requires_login`：是否涉及账号或敏感会话
- `needs_visual_reasoning`：是否依赖视觉布局或真实界面
- `needs_debug_panel`：是否需要 request/response、console、performance 诊断
- `external_side_effect`：是否可能造成真实外部状态变更
- `open_web_exploration`：是否属于跨站、开放式、多步浏览

## 3. 标准任务形态

| task_shape | 说明 | 首选 provider | 回退 provider |
|---|---|---|---|
| `api_call` | 可直接通过 API / HTTP 完成 | `api` | `browser-host-native` |
| `form_fill` | 登录、输入、点击、提交、下载 | `browser-host-native` | `api` |
| `dom_extraction` | 结构化抓取 DOM 文本、属性、表格 | `browser-host-native` | `api` |
| `network_debug` | 查看 request/response、console、性能 | `browser-host-native` | `api` |
| `visual_ui_workflow` | 依赖视觉布局、真实 GUI、弱结构页面 | `turix-cua` | `browser-host-native` |
| `open_web_navigation` | 开放式浏览、跨站导航、research navigation | `browser-use` | `browser-host-native` |

## 4. 输出字段（建议脚本必须返回）

建议脚本至少输出以下字段：

- `provider`
- `reason`
- `confidence`
- `confirm_required`
- `fallback_provider`

建议额外输出：

- `mode`
- `control_plane_owner`
- `considered`
- `provider_preview_note`

## 5. 风险抬升规则

出现以下任意情况时，`confirm_required` 应抬升为 `true`：

- 需要登录、账号、密码或敏感 session
- 可能触发真实状态变更（发布、支付、删除、发送、提交）
- 任务强依赖视觉 UI 或 GUI 判断
- 任务属于跨网站、多步、开放式浏览
- 同时存在多条可行 provider 路径且不确定性较高

## 6. 关键不变量

以下不变量必须始终成立：

1. VCO 是唯一控制面。
2. BrowserOps provider plane 只是建议层，不是编排层。
3. `browser-use` 只作为 provider candidate，不是新 orchestrator。
4. 任一 provider 都不得 takeover `pack selection / task decomposition / team orchestration / promotion decision`。
5. 任一 provider 建议都必须带 `fallback_provider`。
6. `browser-use` 与 `turix-cua` 默认带 `confirm_required` 偏置。
7. `provider`、`fallback_provider` 与 `considered` 不得包含 forbidden MCP id。

## 6.1 Browser-use bounded guidance

- 当任务目标是页面内文本定位时，优先使用 `search_page`。
- 当任务目标是元素结构、属性、选择器候选或节点枚举时，优先使用 `find_elements`。
- 合同层不得依赖 `read_long_content` 作为必备能力；长内容读取必须声明 `bounded extraction` 或 `fallback_provider`。
- preview-model prompt continuity 与 gateway/auth drift 只记录为 `provider_preview_note`，不改变 BrowserOps owner。

## 7. 最小验证产物

当 BrowserOps 建议被采纳时，执行侧至少应保留一种验证产物：

- 页面快照 / 截图
- request/response 记录
- 控制台 / 网络面板证据
- 最终 DOM / 文本提取结果
- 失败时的 fallback 记录
- provider preview note（如存在 gateway/auth/model drift）
