# 自定义 Skill / Workflow 治理规则

目标：允许扩展，禁止失控。你可以接入自定义能力，但不能破坏 canonical runtime 与 canonical router。

默认推荐 lane 仍是 `workflow`，它保持治理工作流核心有效，同时允许自定义扩展逐步接入。

## 不可违反的硬规则

1. 只有一个 runtime：`vibe`
2. 只有一个 route authority：canonical router
3. 自定义内容必须 manifest 声明后才可参与路由
4. 禁止目录存在即自动生效
5. 禁止把外部仓库直接变成 live route source

## 受治理目录约定

- 内容目录：`<TARGET_ROOT>/skills/custom/<name>/`
- workflow 声明：`<TARGET_ROOT>/config/custom-workflows.json`
- custom skill 分离声明（如启用）：`<TARGET_ROOT>/config/custom-skills.json`

## 更新治理规则

### 允许用户长期持有的自定义面

下面这些路径应被视为“用户自定义治理面”，更新时优先保留：

- `skills/custom/`
- `config/custom-workflows.json`
- `config/custom-skills.json`（如启用）

### 不应直接改的官方受管面

下面这些路径属于官方受管面，覆盖更新时可能被重写：

- `skills/vibe/`
- 官方 skill 目录 `skills/<official-skill>/`
- 官方 `mcp/`
- 官方 `rules/`
- 官方 `agents/templates/`

规则：

- 允许在用户自定义路径扩展
- 不鼓励直接修改官方受管目录后再期望覆盖更新自动保留

### profile 变更治理

更新版本时，如果同时变更 profile，必须重新审查 custom workflow 的 `requires`。

特别是：

- 从 `full` 降到框架版（`minimal`）
- 从 `workflow` 降到框架版（`minimal`）

这类变更最容易造成：

- `custom_dependencies_missing`
- “看起来像路由失效，实际上是依赖断裂”

### 更新后必须做的校验

1. 重新执行 `check --deep`
2. 校验 manifest 仍然有效
3. 校验 custom workflow 的路径与 `SKILL.md` 仍然存在
4. 校验 `requires` 仍然满足

如果失败，优先按以下顺序排查：

1. `config/custom-workflows.json` 是否仍在
2. `skills/custom/<id>/SKILL.md` 是否仍在
3. `requires` 对应 skill 是否仍在当前安装版本中
4. 是否把自定义改动误写进了官方受管目录

## 路由与触发治理

- 默认 `trigger_mode`：`advisory`
- `explicit_only` 用于高风险或低频流程
- `auto` 只能在证据充分后启用

必须给出：

- `keywords`
- `intent_tags`
- `non_goals`
- `requires`

缺少这些字段时，不应进入可调用态。

## 依赖治理

自定义 workflow 不能“假定基础能力总在”。
必须通过 `requires` 明确声明依赖，例如：

- `vibe`
- `writing-plans`
- `systematic-debugging`

如果依赖缺失，doctor/check 应报告 `custom_dependencies_missing`，而不是静默降级。

## readiness 口径治理

以下状态要严格区分：

- `lane_complete`
- `lane_complete_with_optional_gaps`
- `core_install_incomplete`
- `custom_manifest_invalid`
- `custom_dependencies_missing`

未满足 provider/MCP/host 手工项时，禁止宣称 online readiness。

## Codex 与 Claude Code 边界

- Codex：官方 governed 宿主；当前不安装 hook
- Claude Code：提供支持的安装与使用路径；当前不安装 hook，也不写 `settings.vibe.preview.json`

两者都不应要求用户把 key/url/model 贴到聊天里。只允许用户在本地 `settings.json` 的 `env` 或本地环境变量配置。

## 治理 AI online layer 边界

基础在线 provider 可用，不等于治理 AI online layer 已完成。

要启用治理 AI advice 的常见在线路径，用户需本地补：

- OpenAI-compatible：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`


未配置时只能宣称“基础在线可用”或“本地安装完成”，不能宣称“治理 AI online readiness 已完成”。

## 最小验收清单

- manifest schema 校验通过
- 未声明目录不会被路由
- 显式用户选择可覆盖自动建议
- canonical `vibe` 与 workflow core 优先级稳定
- doctor 状态与实际配置一致，不夸大 readiness
