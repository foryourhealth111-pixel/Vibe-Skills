# GitNexus × Codex CLI × VCO：执行清单（可复制）

> 目标：把 GitNexus 作为“代码理解/变更感知底座”接入你的 VCO 生态：  
> 1) Codex CLI 运行时可调用（MCP）；2) VCO 侧可用 advice-only overlay（自动建议 → 你确认 → 输出可注入片段）。

## 0) 先决条件（一次性确认）

- Node.js / npm 可用（`node -v`、`npm -v`）。
- 许可证合规：GitNexus 为 PolyForm Noncommercial（商用/对外服务前务必确认）。

## 1) 安装（推荐：pin 版本 + 全局安装）

```bash
# pin 版本（示例：1.3.6）
npm install -g gitnexus@1.3.6 --no-audit --no-fund

# 验证
gitnexus --version
```

### Swift / iOS 仓库（可选但常见必需）

如果你的仓库里有 `.swift` 文件，且 `gitnexus analyze` 报 `Unsupported language: swift`：

```bash
npm install -g tree-sitter-swift@0.7.1 --no-audit --no-fund
```

## 2) 将 GitNexus 注册到 Codex CLI（MCP）

```bash
# 添加 MCP server（stdio）
codex mcp add gitnexus -- gitnexus mcp

# 验证（能看到 gitnexus 条目即可）
codex mcp list
codex mcp get gitnexus
```

> 如果你之前用过 `npx -y gitnexus@... mcp` 且遇到 npm cache/lock 问题：建议直接改为全局安装 + `gitnexus mcp`。

## 3) 索引目标仓库（Index = MCP 可用的前提）

```bash
# 方式 A：在仓库根目录
gitnexus analyze

# 方式 B：从任意位置指定路径
gitnexus analyze <repo_path>
```

可选参数：

```bash
# 强制重建索引
gitnexus analyze --force

# 开启 embeddings（默认关闭；会更慢/更占用资源）
gitnexus analyze --embeddings
```

现实提示（重要）：

- `gitnexus analyze` 可能会生成 `.gitnexus/`（几百 MB 量级），并在某些项目里写入/更新：
  - `.gitignore`（例如忽略 `.gitnexus/`）
  - `AGENTS.md` / `CLAUDE.md`（插入 `<!-- gitnexus:start -->` 段落）
  - `.claude/skills/gitnexus/`（供 agent 使用的技能包）
- 建议在分支里跑一次，确认 diff 后再决定是否提交这些变更（不提交也不影响 MCP 查询能力）。

## 4) CLI 级别的最小验证（不依赖 MCP host）

```bash
# 查看已索引仓库
gitnexus list

# 搜一个概念（会返回 processes / symbols / definitions）
gitnexus query "overlay" -l 3
```

## 5) VCO：自动建议 → 确认 → 输出可注入 overlay

### 5.1 统一入口（GitNexus + 部门专家可组合，推荐）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-vco-overlays.ps1 `
  -Task "你的任务描述" `
  -Stage do

# 选择并渲染注入片段（最多选 2 个）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-vco-overlays.ps1 `
  -Task "你的任务描述" `
  -Stage do `
  -Select "1,2"
```

### 5.2 只建议 GitNexus overlay（更克制）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-gitnexus-overlays.ps1 `
  -Task "你的任务描述" `
  -Stage review
```

## 6) Codex 会话里的“烟雾测试”提示词（验证 MCP 真能被调用）

把下面这段作为你在 Codex CLI 里的任务开头（你可以替换 repo 名和目标 symbol）：

1) “请先调用 GitNexus 的 `list_repos`，确认可用 repo。”
2) “然后 READ `gitnexus://repo/<repoName>/context`，确认 index 是否 stale。”
3) “对关键符号跑 `context({ name: \"<symbol>\" })`，再跑 `impact({ target: \"<symbol>\", direction: \"upstream\" })`。”
4) “进入 review 时跑 `detect_changes({ scope: \"compare\", base_ref: \"main\" })` 生成回归集建议。”

## 7) 卸载 / 回滚（可选）

```bash
# 移除 Codex MCP server
codex mcp remove gitnexus

# 卸载 npm 全局包
npm uninstall -g gitnexus tree-sitter-swift
```
