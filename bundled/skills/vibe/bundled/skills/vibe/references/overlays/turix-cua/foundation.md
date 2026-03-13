# VCO Overlay — TuriX‑CUA 基底（Computer Use / UI Automation）

## Overlay Contract（advice-only）

- 本 overlay 只提供 **“何时用 Computer Use Agent（CUA）”** 的决策树与交付规范，不改变 VCO 的路由、协议与工具选择。
- 目标：在“必须真实操作 UI / 浏览器”的场景里，用更合适的执行路径换取时间（允许更高 API 消耗）。
- 若 CUA 不可用（OS/权限/依赖/网络）：**不阻塞**；自动回退到 `playwright` / `requests` / `curl` 等确定性方案继续推进。

## CUA 是什么（与 Playwright 的差异）

- **Playwright**：DOM/selector 级自动化（更快、更确定、更适合 CI 与回归）；适合“页面结构稳定、可用选择器定位”的任务。
- **CUA（Computer Use Agent）**：像真人一样操作屏幕（看截图、移动鼠标、点击、键盘输入）；适合“选择器不稳定/强交互/反爬/2FA/需要视觉判断”的任务，但更慢、更难在 CI 复现。

> 建议把 CUA 视为“最后一公里 UI 执行器”，而不是通用爬虫或 API 调用器。

## 决策树（先选路径，再写执行计划）

1) **能不用 UI 就不用 UI**
   - 有公开 API / 可直接 HTTP 请求 → 优先走 API（最快、最稳、可回归）

2) **需要浏览器但可稳定选中元素**
   - 能用 selector/xpath/role 定位 → 优先 `Playwright`

3) **必须真实 UI（适合 CUA）**
   - 典型信号：登录流程 + 2FA、验证码、人机验证、复杂拖拽、Web 组件极不稳定、需要“看见”某个状态（例如按钮禁用/弹窗/错误提示）
   - 才选择 `TuriX‑CUA`

## 运行边界（重要）

- **平台差异**：上游 `TuriX‑CUA` 默认是 `mac_agent_env`（依赖屏幕录制权限、`pyobjc/pycocoa` 等）。
  - 在 Windows 环境：默认不把 CUA 作为强依赖，优先 Playwright；如需 CUA，建议使用 Mac runner/远程机。
- **安全停止**：执行 UI automation 时必须有“强制停止热键/kill 开关”，并把它写进运行说明。

## 交付物（固定格式，便于复用/验收）

- `CUA Decision`
  - Chosen path: `API` / `Playwright` / `CUA`
  - Why: 3 条以内（给出 UI 约束证据）
  - Fallback: 若失败如何退化（例如 `CUA → Playwright → API`）
- `Execution Artifacts`
  - Screenshots（关键步骤前/后）
  - Step log（动作序列 + 失败点）
  - Output files（下载/生成文件路径）

## 推荐组合（避免冲突）

- UI/流程类任务：`TuriX‑CUA` + `agency-testing`（任何阶段都可推荐，用于补齐回归集/验收点）
- 代码改动类任务：`GitNexus 基底` + `agency-testing`（证据底座 + QA 兜底）

## 上游参考

- `https://github.com/TurixAI/TuriX-CUA`（MIT）

