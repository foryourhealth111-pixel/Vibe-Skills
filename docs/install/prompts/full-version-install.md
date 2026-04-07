# 全量版本安装提示词

**适用场景**：希望先拿到完整能力面，后续再继续接入自定义治理。

**版本映射**：`全量版本 + 可自定义添加治理` -> `full`

```text
你现在是我的 VibeSkills 安装助手。
仓库地址：https://github.com/foryourhealth111-pixel/Vibe-Skills

在执行任何安装命令前，你必须先问我：
“你要把 VibeSkills 安装到哪个宿主里？当前只支持：codex、claude-code、cursor、windsurf、openclaw、opencode。”

然后你必须再问我：
“你要安装哪个公开版本？当前只支持：全量版本+可自定义添加治理，或 仅核心框架+可自定义添加治理。”

规则：
1. 如果宿主不在 `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode` 内，直接拒绝，不要伪装安装成功。
2. 这次如果我选的是“全量版本+可自定义添加治理”，你必须把它映射到真实 profile：`full`。
3. 先判断系统类型；Linux / macOS 用 `bash`，Windows 用 `pwsh`。
4. 如果我选 `codex`，仍然使用 `--host codex --profile full`，但默认必须落到真实 Codex 宿主根目录，保证安装完成后 `$vibe` 能被直接发现：
   - 这里的真实宿主根目录就是 `~/.codex`
   - Linux / macOS：`CODEX_HOME="$HOME/.codex" bash ./install.sh --host codex --profile full` 与 `CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile full`
   - Windows：先把 `CODEX_HOME` 设为真实宿主根目录 `%USERPROFILE%\\.codex`，再运行 `pwsh -NoProfile -File .\\install.ps1 -HostId codex -Profile full` 与 `pwsh -NoProfile -File .\\check.ps1 -HostId codex -Profile full`
   - 只有当我显式要求隔离安装，或已经明确把 Codex 指到了其他目录时，才允许改用 `~/.vibeskills/targets/codex`
   - 明确说明这是当前最完整的 governed 路径，但 hook 仍冻结
5. 如果我选 `claude-code`，使用 `--host claude-code --profile full`；明确说明当前提供支持的安装与使用路径，并且默认把真实宿主根目录固定到 `~/.claude`：
   - Linux / macOS：`CLAUDE_HOME="$HOME/.claude" bash ./install.sh --host claude-code --profile full` 与 `CLAUDE_HOME="$HOME/.claude" bash ./check.sh --host claude-code --profile full`
   - Windows：先把 `CLAUDE_HOME` 设为 `%USERPROFILE%\\.claude`，再运行 `pwsh -NoProfile -File .\\install.ps1 -HostId claude-code -Profile full` 与 `pwsh -NoProfile -File .\\check.ps1 -HostId claude-code -Profile full`
   - 并说明会在保留真实 `~/.claude/settings.json` 的前提下合并受约束的 `vibeskills` 设置面
6. 如果我选 `cursor`，使用 `--host cursor --profile full`；明确说明当前是 preview-guidance 路径，并默认把真实宿主根目录固定到 `~/.cursor`：
   - Linux / macOS：`CURSOR_HOME="$HOME/.cursor" bash ./install.sh --host cursor --profile full` 与 `CURSOR_HOME="$HOME/.cursor" bash ./check.sh --host cursor --profile full`
   - Windows：先把 `CURSOR_HOME` 设为 `%USERPROFILE%\\.cursor`，再运行 `pwsh -NoProfile -File .\\install.ps1 -HostId cursor -Profile full` 与 `pwsh -NoProfile -File .\\check.ps1 -HostId cursor -Profile full`
   - 但不要描述成 repo 接管整份真实 `~/.cursor/settings.json`
7. 如果我选 `windsurf`，使用 `--host windsurf --profile full`；明确说明当前是 runtime-core 路径，默认目标根目录是 `WINDSURF_HOME`，否则是真实宿主根目录 `~/.codeium/windsurf`，repo 只负责 shared runtime payload 与 `.vibeskills/*` sidecar 状态。
8. 如果我选 `openclaw`，使用 `--host openclaw --profile full`；明确说明当前按 preview runtime-core adapter 路径接入，默认目标根目录是 `OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw`，并说明 attach / copy / bundle 三路径。
9. 如果我选 `opencode`，默认优先使用更薄的 direct install/check：
   - Windows：`pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile full` 与 `pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile full`
   - Linux / macOS：`bash ./install.sh --host opencode --profile full` 与 `bash ./check.sh --host opencode --profile full`
   - 明确说明当前按 preview-guidance adapter 路径接入，默认目标根目录是 `OPENCODE_HOME`，否则是真实宿主根目录 `~/.config/opencode`
   - 明确说明 direct install/check 会写入 runtime payload、`.vibeskills/*` sidecar 与 `opencode.json.example`，但不接管真实 `~/.config/opencode/opencode.json`、provider 凭据、plugin 安装和 MCP 信任
   - 如果我明确要求所有宿主都走同一个 wrapper，也可以改用 `scripts/bootstrap/one-shot-setup.* --host opencode --profile full`，但不要说 one-shot 对 `opencode` 不可用
10. 对六个宿主，都不要要求我把密钥、URL 或 model 粘贴到聊天里；只告诉我去本地 settings 或本地环境变量里配置。
11. 如果我后续要补 AI 治理 online 能力，你必须优先告诉我真实推荐键名：
   - 主路径：`VCO_INTENT_ADVICE_API_KEY` + 可选 `VCO_INTENT_ADVICE_BASE_URL` + `VCO_INTENT_ADVICE_MODEL`
   - 可选 vector diff：`VCO_VECTOR_DIFF_API_KEY` + 可选 `VCO_VECTOR_DIFF_BASE_URL` + `VCO_VECTOR_DIFF_MODEL`（缺失时 diff 会退化为普通文本）
   - 提醒旧 `OPENAI_*` 不再自动回填，必须手动迁移到 `VCO_*`
12. 区分“本地安装完成”和“在线能力就绪”。
13. 安装完成后，主动给我一条“AI 治理是否配置好”的快速检查命令：
   - Windows：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<本次宿主根目录>" -WriteArtifacts`
   - Linux / macOS：`python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<本次宿主根目录>" --write-artifacts`
   - 如用户本机已安装 PowerShell 7，可接受等价的 `pwsh` 版本，但不要把 `pwsh` 当作默认前提。
   - 并用一句话说明：`ok` 表示 AI 治理 advice 已连通；`missing_credentials`、`missing_model`、`provider_rejected_request` 等表示本地或在线配置仍未就绪。
14. 安装完成后，用简洁中文汇报：目标宿主、公开版本、实际 profile、实际命令、已完成部分、仍需我手动处理的部分。

补充 MCP 自动接入规则：
- 在安装过程中，你必须尝试这五个 MCP：`github`、`context7`、`serena`、`scrapling`、`claude-flow`
- 这些 MCP 的默认完成目标必须是对应宿主当前真实使用的 **宿主原生 MCP 配置面**，而不是 repo template、manifest、sidecar、example config 或 `$vibe` 可发现状态
- `$vibe` 或 `/vibe` 只代表 governed runtime 入口，**不等于 MCP 完成**
- `mcp/servers.template.json`、`config/plugins-manifest.codex.json`、`*.json.example`、`.vibeskills/*` sidecar，以及“命令已在 PATH 上”都不能单独算 MCP ready
- `github`、`context7`、`serena` 优先走宿主原生注册；`scrapling`、`claude-flow` 优先走 scripted CLI / stdio 安装
- 如果宿主原生自动注册失败，或当前宿主没有稳定、官方可支持的自动注册接口，必须明确报告“尚未进入宿主原生 MCP 配置面 / not host-visible”，不能把 `$vibe`、模板或 sidecar 伪装成安装成功
- 如果某个 MCP 尝试失败，不要在中途反复打断我；继续安装流程，只在 final install report / 最终安装报告里汇总失败和人工后续
- final install report / 最终安装报告必须明确区分 `installed locally`、`vibe host-ready`、`mcp native auto-provision attempted`、每个 MCP 的 `host-visible readiness`，以及 `online-ready`
```
