# 安装入口（唯一公开入口）

这是当前唯一公开安装入口。

普通用户只需要使用这一页。
这页会把你带到保留的 4 份基础安装提示词文档。

如果你是第一次安装，默认按这个顺序选就行：

1. 先选宿主
2. 再选 `安装`
3. 拿不准版本时先选 `全量版本 + 可自定义添加治理`
4. 复制对应提示词，粘贴到你的 AI 客户端里执行

## 运行时先决条件

在使用文档中列出的安装、检查、升级或一次性执行命令之前，请确保满足以下条件：

- Windows：安装 **PowerShell 7**，并确保 `pwsh` 命令已包含在系统的 `PATH` 环境变量中。
- Linux：安装 **PowerShell 7**，并确保 `pwsh` 命令已包含在系统的 `PATH` 环境变量中。
- macOS：安装 **PowerShell 7**，如果您计划使用 PowerShell 命令行界面，请确保 `pwsh` 命令已包含在系统的 `PATH` 环境变量中。
- 所有平台：对于由包装脚本（wrapper）驱动的安装界面，`python3` 或 `python` 版本必须满足 **Python 3.10 或更高版本**的要求。
- 在 Linux 和 macOS 上，Shell 入口点（entrypoints）依然可用；但若要使用完整的受控运行时环境及验证功能，则仍需依赖 PowerShell 7。


## 先选宿主、动作和版本

1. 先确认宿主：`codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode`
2. 再确认动作：
   - 第一次安装通常选：`安装`
   - 已经装过，想覆盖升级时再选：`更新`
3. 最后确认版本：
   - 安装：`全量版本 + 可自定义添加治理`
   - 安装：`仅核心框架 + 可自定义添加治理`
   - 更新：`全量版本 + 可自定义添加治理`
   - 更新：`仅核心框架 + 可自定义添加治理`

公开版本映射到：

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

对第一次安装的普通用户来说，先记住这两条就够了：

- 拿不准时先选 `安装 + 全量版本 + 可自定义添加治理`
- 只有你明确只想要轻量框架时，再选 `仅核心框架 + 可自定义添加治理`

补充说明：

- 宿主模式由 [`../../config/adapter-registry.json`](../../config/adapter-registry.json) 决定
- 同一个公开入口可能最终落到 `governed`、`preview-guidance` 或 `runtime-core` 三种模式
- `opencode` 的公开提示词仍可优先走更薄的 direct install/check，但 registry-driven 的 one-shot wrapper 也可用

## 复制对应提示词

这里保留 4 份基础提示词文档，覆盖安装 / 更新 与 full / minimal 四种场景。
第一次安装通常只会用到前两份；后两份是给更新旧版本时用的。
除这 4 份外，其他页面都不再作为公开安装提示词入口。

- [`prompts/full-version-install.md`](./prompts/full-version-install.md)
- [`prompts/framework-only-install.md`](./prompts/framework-only-install.md)
- [`prompts/full-version-update.md`](./prompts/full-version-update.md)
- [`prompts/framework-only-update.md`](./prompts/framework-only-update.md)

## 需要时再继续看

只有你遇到下面这些情况时，才需要继续往下看：

- 宿主补充说明：
  - [`openclaw-path.md`](./openclaw-path.md)
  - [`opencode-path.md`](./opencode-path.md)
- 仅核心框架命令路径：
  - [`minimal-path.md`](./minimal-path.md)
- 更多安装命令和宿主细节：
  - [`recommended-full-path.md`](./recommended-full-path.md)
  - [`../cold-start-install-paths.md`](../cold-start-install-paths.md)
  - [`manual-copy-install.md`](./manual-copy-install.md)
  - [`host-plugin-policy.md`](./host-plugin-policy.md)
- 后续接自己的 workflow / skill：
  - [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
  - [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)

## 如果安装后要卸载

安装的对称入口是仓库根目录下的 `uninstall.ps1` / `uninstall.sh`。它们与 `install.*` 使用同一组 `--host`、`--target-root`、`--profile` 参数，默认直接执行卸载，但只会清理 Vibe 自己安装或写入的内容。

- 完整规则见 [`../uninstall-governance.md`](../uninstall-governance.md)
- 如果你只想先看计划删除什么，可以加 `--preview`
- 它不会默认回滚宿主登录态、provider 凭证、插件状态或你自己维护的配置

## 关于补充配置

- 基础安装完成后即可直接使用
- 如果你还想补在线 provider、MCP、宿主本地 settings 或插件联动，这些都属于增强建议，不是基础安装的前置门槛
- 各宿主哪些内容仍由宿主侧本地维护，会在对应提示词和参考文档中如实说明

## 安装后如果要补 AI 治理在线配置，按 VCO_* 键名

常见配置路径：

- intent advice：`VCO_INTENT_ADVICE_API_KEY` + 可选 `VCO_INTENT_ADVICE_BASE_URL` + `VCO_INTENT_ADVICE_MODEL`
- vector diff embeddings（非必需）：`VCO_VECTOR_DIFF_API_KEY` + 可选 `VCO_VECTOR_DIFF_BASE_URL` + `VCO_VECTOR_DIFF_MODEL`

补充说明：

- 主路径（intent advice）必须有，否则 `vibe` 中的 advice 会报 `missing_credentials` / `missing_model`。
- vector diff 是降级能力，缺失时 diff 会直接返回普通文本片段，能继续使用主路径。
- 旧 `OPENAI_*` 不再自动回填；如果你仍手动维护，那也是手动映射到 `VCO_*` 才能被 runtime 读取。
- 详细说明见 [`configuration-guide.md`](./configuration-guide.md)

## 安装后快速检查 AI 治理是否已配置好

如果你想快速确认“路由里的 AI 治理 advice 是否已经配通”，可以在仓库根目录运行：

- Windows：
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<目标宿主根目录>" -WriteArtifacts`
- Linux / macOS：
  - `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<目标宿主根目录>" --write-artifacts`

如果你本机已经装了 PowerShell 7，也可以把 `powershell.exe` 换成 `pwsh`。

常见默认目标根目录：

- `codex` -> 默认把 `CODEX_HOME` 指到真实 `~/.codex`，这样安装后当前 Codex 能直接发现 `$vibe`；只有显式要求隔离安装时才改用 `~/.vibeskills/targets/codex`
- `claude-code` -> 默认把 `CLAUDE_HOME` 指到真实 `~/.claude`
- `cursor` -> 默认把 `CURSOR_HOME` 指到真实 `~/.cursor`
- `windsurf` -> `WINDSURF_HOME` 或真实宿主根目录 `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw`
- `opencode` -> `OPENCODE_HOME` 或真实宿主根目录 `~/.config/opencode`

结果说明：

- `ok`：AI 治理 advice 已连通
- `missing_credentials` / `missing_model`：本地配置还不完整
- `provider_rejected_request` / `provider_unreachable`：已经尝试在线调用，但当前没有成功
