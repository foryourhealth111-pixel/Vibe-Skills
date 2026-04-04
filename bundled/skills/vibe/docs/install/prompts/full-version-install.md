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
4. 如果我选 `codex`，使用 `--host codex --profile full`；明确说明这是当前最完整的 governed 路径，但 hook 仍冻结。
5. 如果我选 `claude-code`，使用 `--host claude-code --profile full`；明确说明当前提供支持的安装与使用路径，不覆盖真实 `~/.claude/settings.json`。
6. 如果我选 `cursor`，使用 `--host cursor --profile full`；明确说明当前提供支持的安装与使用路径，也不接管真实 `~/.cursor/settings.json`。
7. 如果我选 `windsurf`，使用 `--host windsurf --profile full`；明确说明当前提供支持的安装与使用路径，且已接入 runtime adapter，默认目标根目录是 `WINDSURF_HOME` 或 `~/.vibeskills/targets/windsurf`，repo 只负责 shared runtime payload 和按需物化 `mcp_config.json` / `global_workflows/`。
8. 如果我选 `openclaw`，使用 `--host openclaw --profile full`；明确说明当前按 `preview` / `runtime-core-preview` / `runtime-core` 路径接入，默认目标根目录是 `OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`，并说明 attach / copy / bundle 三路径。
9. 如果我选 `opencode`，使用 direct install/check，不走 one-shot bootstrap：
   - Windows：`pwsh -NoProfile -File .\\install.ps1 -HostId opencode -Profile full` 与 `pwsh -NoProfile -File .\\check.ps1 -HostId opencode -Profile full`
   - Linux / macOS：`bash ./install.sh --host opencode --profile full` 与 `bash ./check.sh --host opencode --profile full`
   - 明确说明当前按 preview adapter 路径接入，默认目标根目录是 `OPENCODE_HOME` 或 `~/.vibeskills/targets/opencode`
   - 明确说明 direct install/check 会写入 skills、command/agent wrappers 与 `opencode.json.example`，但不接管真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任
10. 对六个宿主，都不要要求我把密钥、URL 或 model 粘贴到聊天里；只告诉我去本地 settings 或本地环境变量里配置。
11. 区分“本地安装完成”和“在线能力就绪”。
12. 安装完成后，用简洁中文汇报：目标宿主、公开版本、实际 profile、实际命令、已完成部分、仍需我手动处理的部分。
```
