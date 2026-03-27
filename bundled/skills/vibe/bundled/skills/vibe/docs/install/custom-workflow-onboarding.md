# 自定义工作流接入指南（governed onboarding）

这份文档只描述一个受治理接入路径：让你的工作流进入 canonical router 的可调用范围，同时不破坏路由权威。

## 先决条件

推荐先安装 lane：

- `workflow`（默认推荐）
- 或 `full`

框架版（当前真实 profile 为 `minimal`）也可接入，但你需要自行补齐工作流核心依赖，否则会出现“声明成功但调用价值不足”。

## 接入路径（唯一支持）

1. 在目标宿主目录创建工作流内容：

- `<TARGET_ROOT>/skills/custom/<name>/SKILL.md`

2. 在目标宿主目录声明 manifest：

- `<TARGET_ROOT>/config/custom-workflows.json`

3. 只让 router 读取 manifest 声明项，不依赖目录自动扫描。

## manifest 最小示例

```json
{
  "version": 1,
  "workflows": [
    {
      "id": "my-domain-flow",
      "path": "skills/custom/my-domain-flow",
      "enabled": true,
      "trigger_mode": "advisory",
      "keywords": ["实验复盘", "误差分析", "模型评估"],
      "intent_tags": ["ml", "research", "evaluation"],
      "preferred_stages": ["deep_interview", "xl_plan", "plan_execute"],
      "requires": ["vibe", "writing-plans"],
      "priority": 60,
      "non_goals": ["general chat", "tiny edit"]
    }
  ]
}
```

## trigger_mode 建议

允许值：

- `explicit_only`
- `advisory`（默认推荐）
- `auto`

建议默认 `advisory`，因为它在“可被建议”与“不抢 route authority”之间最稳。

## 如何保证“被恰到好处地调用”

- 明确 `keywords`、`intent_tags`、`non_goals`
- 在 `requires` 中声明官方依赖，不要隐式依赖
- 保持 `priority` 低于 canonical 核心路径
- 让 `explicit user choice` 永远优先

冻结优先级顺序：

1. explicit user choice
2. canonical `vibe`
3. official workflow core
4. admitted custom workflows
5. domain packs / overlays

## 常见误区

- 误区：把目录复制进去就算接入完成
- 正确：必须 manifest 声明后才可路由

- 误区：自定义 workflow 可以替代 canonical router
- 正确：自定义 workflow 只能参与，不得夺权

- 误区：声明了就等于 online readiness
- 正确：online readiness 仍取决于本地 provider / MCP / host 手工项

## 更新 / 覆盖安装注意事项

如果你后续要更新 VibeSkills，先区分两类内容：

### 1. 通常可以跟随更新继续保留的内容

只要你按受治理路径接入，自定义内容通常不会因为标准覆盖更新而直接失效：

- `<TARGET_ROOT>/skills/custom/<workflow-id>/`
- `<TARGET_ROOT>/config/custom-workflows.json`

原因是当前 router 对自定义 workflow 的读取，依赖 manifest 声明，而不是依赖官方 runtime 目录内的硬编码扫描。

### 2. 更新时容易被覆盖或重写的内容

下面这些属于官方受管面，更新时不应直接改：

- `<TARGET_ROOT>/skills/vibe/...`
- 官方 skill 目录，例如 `<TARGET_ROOT>/skills/<official-skill>/`
- 官方治理配置镜像，例如 runtime 下的 `config/`、`scripts/`、`docs/`
- 官方 `mcp/`、`rules/`、`agents/templates/`

如果你把自定义治理直接写进这些官方路径，覆盖更新后很可能被重写。

### 3. 最稳的做法

推荐把“用户自己的东西”固定放在这两层：

- 自定义 workflow 内容：`skills/custom/<id>/`
- 自定义 workflow 声明：`config/custom-workflows.json`

不要把自定义治理直接补丁到官方 runtime 内部文件。

### 4. 更新前后要检查什么

更新前建议：

- 备份 `config/custom-workflows.json`
- 备份 `skills/custom/`
- 记录当前安装版本与 profile

更新时建议：

- 尽量保持原 profile 不变
- 如果要从 `full/workflow` 降到框架版（`minimal`），先检查你的 custom workflow 的 `requires`

更新后必须：

- 重新跑一次 `check --deep`
- 确认没有 `custom_manifest_invalid`
- 确认没有 `custom_dependencies_missing`

### 5. 最常见的“不是被删了，而是依赖断了”

很多用户会误以为更新把自定义治理删掉了，实际更常见的是：

- custom workflow 目录还在
- manifest 还在
- 但你切换了 profile，导致 `requires` 依赖不再满足

例如你原来依赖 `writing-plans`、`systematic-debugging`，后来又把安装版本降成“仅核心框架”，那它就可能被 doctor/check 判定为依赖缺失，而不是被路由静默吸收。

### 6. 一句话升级原则

想让自定义治理在更新后尽量稳定：

- 自定义内容放 `skills/custom`
- 自定义声明放 `config/custom-workflows.json`
- 不直接改官方 runtime / 官方 skill
- 更新后立即重新执行 `check --deep`

## 用户接入提示词模板

可给用户一段固定提示词，用于让助手按治理方式协助接入：

```text
请把我的工作流按 VibeSkills 受治理方式接入，不要新建第二套路由。
目标宿主：codex、claude-code、cursor、windsurf、openclaw 或 opencode。
请执行：
1) 检查 lane 是否为 workflow/full，不满足就给迁移建议；
2) 在 <TARGET_ROOT>/skills/custom/<workflow-id>/ 生成 SKILL.md 草案；
3) 在 <TARGET_ROOT>/config/custom-workflows.json 增加 manifest 声明（trigger_mode 默认 advisory）；
4) 校验 requires/keywords/non_goals 是否完整；
5) 运行 check/doctor 并用 truth-first 口径报告结果。
不要让我把任何 API key、URL、model 粘贴到聊天里。
```

## 用户升级提示词模板

### 全量安装 + 自定义治理的升级提示词

```text
请帮我更新当前的 VibeSkills。
目标宿主：codex、claude-code、cursor、windsurf、openclaw 或 opencode。
当前公开版本：全量版本 + 可自定义添加治理。
请执行：
1) 先检查 `skills/custom/` 和 `config/custom-workflows.json` 是否存在；
2) 先提醒我哪些内容通常可保留，哪些官方受管路径改动可能被覆盖；
3) 这次更新按 `full` 处理，不要误降成框架版（`minimal`）；
4) 更新后运行 `check --deep`；
5) 用 truth-first 口径告诉我：
   - custom workflow 是否仍在
   - manifest 是否仍有效
   - 默认 workflow core 是否仍齐备
   - 是内容丢失还是依赖断裂
   - 下一步修复建议
不要让我把任何 API key、URL、model 粘贴到聊天里。
```

### 仅框架 + 自定义治理的升级提示词

```text
请帮我更新当前的 VibeSkills。
目标宿主：codex、claude-code、cursor、windsurf、openclaw 或 opencode。
当前公开版本：仅核心框架 + 可自定义添加治理。
请执行：
1) 先检查 `skills/custom/` 和 `config/custom-workflows.json` 是否存在；
2) 先提醒我哪些内容通常可保留，哪些官方受管路径改动可能被覆盖；
3) 这次更新按框架版对应的真实 profile `minimal` 处理；
4) 更新后运行 `check --deep`；
5) 用 truth-first 口径告诉我：
   - custom workflow 是否仍在
   - manifest 是否仍有效
   - 当前是否仍是治理框架底座模式
   - 是内容丢失还是依赖断裂
   - 下一步修复建议
不要让我把任何 API key、URL、model 粘贴到聊天里。
```

## Online 配置提醒（不要伪装完成）

如果你要启用治理 AI online layer，用户必须本地补齐常见键名：

- OpenAI-compatible：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`


未配置时只能说“本地安装完成，但治理 AI online 能力未就绪”。
