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
5. 如果我选 `claude-code`，使用 `--host claude-code --profile full`；明确说明当前提供支持的安装与使用路径，并且会在保留真实 `~/.claude/settings.json` 的前提下合并受约束的 `vibeskills` 与 write-guard hook 面。
6. 如果我选 `cursor`，使用 `--host cursor --profile full`；明确说明当前是 preview-guidance 路径，不接管真实 `~/.cursor/settings.json`。
7. 如果我选 `windsurf`，使用 `--host windsurf --profile full`；明确说明当前是 runtime-core 路径，默认根目录是 `~/.codeium/windsurf`，repo 只负责 shared runtime payload 与 `.vibeskills/*` sidecar 状态。
8. 如果我选 `openclaw`，使用 `--host openclaw --profile full`；明确说明当前按 preview runtime-core adapter 路径接入，默认目标根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`，并说明 attach / copy / bundle 三路径。
9. 如果我选 `opencode`，默认优先使用更薄的 direct install/check：
   - Windows：`pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile full` 与 `pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile full`
   - Linux / macOS：`bash ./install.sh --host opencode --profile full` 与 `bash ./check.sh --host opencode --profile full`
   - 明确说明当前按 preview-guidance adapter 路径接入，默认目标根目录是 `OPENCODE_HOME`，否则是 `~/.config/opencode`
   - 明确说明 direct install/check 会写入 runtime payload、`.vibeskills/*` sidecar 与 `opencode.json.example`，但不接管真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任
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
```
