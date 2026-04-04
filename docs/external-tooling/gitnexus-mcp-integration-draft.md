# GitNexus MCP 接入草案（VCO 生态）

> 本文是“接入设计草案”，目标是把 GitNexus 变成 VCO 可选的底层工具能力（MCP），在不改变 VCO 路由/协议的前提下增强代码理解与变更感知。

## 0. 结论（推荐方案）

- **推荐接入方式**：`stdio MCP server`（本地进程），由编辑器/运行时（Claude Code / Cursor 等）按需拉起。
- **推荐安装方式**（降低 supply-chain 漂移）：优先 **固定版本** + `npm install -g gitnexus@<PINNED_VERSION>`，MCP 配置里用 `gitnexus mcp`。
- **推荐运行模式**：`shadow / preferred`（可用就用；不可用自动 fallback，不阻塞交付）。
- **强制模式**（required）不建议默认启用：只在“高风险重构 / 上线前强审”场景临时启用。

## 1. 目标与非目标

### 1.1 目标（Goals）

1) 把 GitNexus 作为 **“代码理解/变更感知底座”** 接入，让 VCO 在需要时能调用：
   - `context`（符号 360° 上下文）
   - `impact`（影响面 / blast radius）
   - `detect_changes`（diff → processes）
   - `rename`（图谱辅助重命名）
   - `query/cypher`（图谱检索/查询）

2) 满足 VCO 的治理边界：
   - **advice-first**：不改变路由/协议，只增强证据与交付物。
   - **P5 证据化**：任何影响面/回归结论最好能用 GitNexus 结果佐证（不可用时 fallback）。
   - **不阻塞**：GitNexus 不可用时，不影响工程实现与测试推进。

3) 适配你的 overlay 体系：
   - GitNexus 是“更底层的基础设施”，可与 `agency-testing` / `agency-engineering` 常见组合。

### 1.2 非目标（Non-goals）

- 不改动 VCO 的 pack router / hooks / 插件源码（保持 “生态骨架” 纯配置 + 文档 + 脚本）。
- 不把 GitNexus 作为“唯一真相”：它是强提示与证据抓手，最终放行仍由 VCO 的 V2/V3 验证闭环决定。

## 2. 关键约束与风险（硬闸门）

### 2.1 许可证（必须先确认）

- GitNexus 许可证为 **PolyForm Noncommercial**（见上游仓库 LICENSE）。
- 如果 VCO 生态用于商业用途/对外服务/付费交付：需要先确认是否合规，否则应准备替代方案（自研图谱、或可商用替代品）。

> 上游仓库：`https://github.com/abhigyanpatwari/GitNexus`（LICENSE 以其为准）。

### 2.2 安全与隐私（最小治理）

- `npx ...@latest` 有供应链风险与版本漂移风险。建议：
  - 固定版本（pin）；
  - 或全局安装（`npm install -g`）后用可执行文件启动；
  - 关键环境可以做包审计/镜像缓存。
- 数据暴露面：
  - GitNexus 工具返回的上下文更结构化、更全面；若把这些输出再发给外部服务/模型，会扩大泄露面。
  - 建议先定义“可外发的证据最小集”（例如只发符号名/路径/摘要，不发业务密钥/完整代码块）。

## 3. 架构方案（Options）

### Option A（推荐）：全局 MCP 配置（多 repo 共享）

- 思路：在编辑器/运行时的全局 MCP 配置里注册 `gitnexus` server。
- 优点：
  - GitNexus 自带 multi-repo registry（适合“一个 server 服务多个索引仓库”）；
  - 不绑定某个项目目录；更符合“底层能力”定位。
- 缺点：
  - 需要你在本机的 MCP 配置层面动手；团队分发需要额外治理。

### Option B：VCO 插件内 `.mcp.json`（如果你把 VCO 做成 Claude Code plugin）

> 适用前提：你把本仓库（或其中的 `vibe` 技能目录）打包为 Claude Code 插件目录（有 plugin.json / `${CLAUDE_PLUGIN_ROOT}`）。

- 思路：在插件根目录提供 `.mcp.json`，由插件随启用而启用 MCP server。
- 优点：
  - 配置与 VCO 绑定、可版本化、易分发；
  - “一键启用 VCO = 一键启用 GitNexus”。
- 缺点：
  - 对当前“生态骨架”而言，这需要你有插件包装层；否则只是一个文件摆在 repo 里不起作用。

### Option C：on-demand 脚本拉起（不推荐作为长期方案）

- 思路：VCO 在需要时用脚本 `npx gitnexus ...` 拉起并调用。
- 缺点：
  - MCP 不是这样用的（host 负责 lifecycle）；脚本方案更像临时 workaround。

## 4. 推荐落地：分层接入（Foundation → Optional Tool）

### 4.1 分层原则

- **Layer 0：索引（Index）**  
  - 每个 repo 需要 `gitnexus analyze`（首次 + 更新）才能产生可用数据。
- **Layer 1：工具暴露（MCP）**  
  - 通过 MCP 把 GitNexus 变成工具集合（list_repos/query/context/impact/detect_changes/rename/cypher）。
- **Layer 2：VCO 使用策略（Policy）**  
  - 定义什么时候建议调用哪些工具（例如 review 用 detect_changes，重构用 impact）。
  - 失败 fallback（rg + git diff）。
- **Layer 3：overlay（Prompt Guidance）**  
  - 我们已经有 GitNexus prompt overlay，作为“如何产出证据”的模板（advice-only）。

## 5. 运行时模式（Modes）

建议用一个简单的 policy 来表达行为（不一定要立刻做成代码；先做成约定即可）：

- `disabled`：完全不用 GitNexus（仅 overlay 文档存在）。
- `shadow`：可用就用；不可用静默 fallback；不要求用户额外动作。
- `preferred`：可用就优先使用，并在输出中标注“证据来源”；不可用会提示原因，但不阻塞。
- `required`：必须可用，否则任务停在“证据不足”；只用于高风险发布门禁/审计场景。

## 6. MCP 配置模板（stdio）

### 6.0 Codex CLI（推荐：用 `codex mcp add` 管理）

Codex CLI 自带 MCP 配置管理命令（会写入 `~/.codex/config.toml`），推荐用它来添加/移除 GitNexus：

```bash
# 添加（npx + 固定版本）
codex mcp add gitnexus -- npx -y gitnexus@<PINNED_VERSION> mcp

# 或添加（全局安装）
codex mcp add gitnexus -- gitnexus mcp

# 查看是否已添加
codex mcp list
codex mcp get gitnexus

# 移除
codex mcp remove gitnexus
```

### 6.1 用 npx（方便，但建议固定版本）

```json
{
  "mcpServers": {
    "gitnexus": {
      "command": "npx",
      "args": ["-y", "gitnexus@<PINNED_VERSION>", "mcp"]
    }
  }
}
```

### 6.2 用全局安装（推荐，降低漂移）

```bash
npm install -g gitnexus@<PINNED_VERSION>
```

```json
{
  "mcpServers": {
    "gitnexus": {
      "command": "gitnexus",
      "args": ["mcp"]
    }
  }
}
```

### 6.3 插件内 `.mcp.json`（Claude Code plugin 形态）

```json
{
  "gitnexus": {
    "command": "npx",
    "args": ["-y", "gitnexus@<PINNED_VERSION>", "mcp"]
  }
}
```

## 7. 验证与健康检查（接入后第一件事）

### 7.1 先确保 repo 被索引

在目标仓库根目录运行（一次性/更新时）：

```bash
# 全局安装（推荐）
gitnexus analyze

# 或（不装全局）固定版本
npx -y gitnexus@<PINNED_VERSION> analyze
```

> 现实提示：`gitnexus analyze` 可能会创建一个较大的 `.gitnexus/` 目录（几百 MB 量级），并且在某些项目里会写入/更新
> `AGENTS.md` / `CLAUDE.md` / `.gitignore` / `.claude/skills/gitnexus/` 等“运行时上下文文件”。  
> 建议在一个工作分支里执行，确认 diff 后再决定是否提交这些改动（不提交也不影响 MCP 查询能力）。

### 7.2 验证 MCP server 可用（最小探针）

当 MCP 接入成功后，应能调用：

- `list_repos`（确认 registry 中至少有 1 个 repo）
- 对某个 repo 做 `context/impact/query`

> 如果 host 支持 MCP resources，也可以读 `gitnexus://repos` 作为只读探针。

### 7.3 常见失败与 fallback

- MCP 启动失败 / Node 环境缺失 → fallback：`rg` / `git diff` / 手动追踪调用点。
- repo 未 analyze / index stale → 提示运行 `gitnexus status` / `gitnexus analyze`（但不阻塞）。

### 7.4 Swift / iOS 仓库常见坑（Windows / 新版 Node）

现象：

- `gitnexus analyze` 报错：`Unsupported language: swift`

原因（常见）：

- `tree-sitter-swift` 是 GitNexus 的 optionalDependency，在某些环境下不会自动安装/不会被正确构建，导致 Swift parser 缺失。

快速修复（推荐优先试这个）：

```bash
npm install -g tree-sitter-swift@0.7.1 --no-audit --no-fund
```

然后重新索引：

```bash
gitnexus analyze --force
```

> 说明：`gitnexus analyze --help` 可查看当前版本支持的参数；某些 README 里的 flags 可能与已发布版本存在差异。

## 8. VCO 使用策略（何时调用什么）

### 8.1 `think`（方案/架构阶段）

- 目标：快速对齐边界、入口、关键流程
- 建议：
  - `query({ query: "auth", task_context: "<what you are doing>" })` 找关键流程 / 入口点
  - `READ gitnexus://repo/<name>/clusters` / `gitnexus://repo/<name>/processes` 快速拿地图
  - `context({ name: "<entrypoint_symbol>", repo?: "<name>" })` 定入口点
  - （可选）用 clusters/processes 输出 1-pager

### 8.2 `do`（实现阶段）

- 目标：避免盲改；先拿影响面再开工
- 建议：
  - `impact({ target: "<anchor>", direction: "upstream", maxDepth: 2, includeTests: true, repo?: "<name>" })` → 产出 `Impact Report`
  - 结合 `agency-engineering` 拆任务 + 结合 `agency-testing` 生成回归集

### 8.3 `review`（评审阶段）

- 目标：把 diff 变成“受影响流程”，补齐漏改与回归
- 建议：
  - `detect_changes({ scope: "compare", base_ref: "main", repo?: "<name>" })` → 产出 `Change Awareness Pack`
  - `agency-testing` 强制证据包（命令输出/截图/日志）

### 8.4 `retro`（复盘阶段）

- 目标：解释“为何漏测/漏改”，沉淀最小回归集与风险清单
- 建议：
  - 对关键事故 diff 做一次 `detect_changes`
  - 把高频受影响 process 固化为 must-run 回归套件

## 9. rollout（分阶段落地）

### Phase 0：纯文档 + 手动使用（现在即可）

- 你已拥有 GitNexus overlay 模板与统一建议脚本（prompt 层）。
- MCP 只做“可选增强”，由你手动配置 editor/runtime。

### Phase 1：最小自动化（建议下一步）

- 增加一个“setup 提示脚本”（不自动改你系统配置，只生成片段）：
  - 输出：MCP JSON 片段（npx / global install 两种）
  - 输出：verify checklist（list_repos/context/impact）

### Phase 2：VCO 策略固化（可选）

- 把“何时调用 GitNexus”固化成 policy（例如一个 `gitnexus-mcp-policy.json`）。
- 仍保持 advice-only：只输出建议与证据模板，不强制执行。

### Phase 3：高风险门禁（谨慎）

- 只在“发布前”或“重构前”临时启用 `required`，否则默认 preferred/shadow。
