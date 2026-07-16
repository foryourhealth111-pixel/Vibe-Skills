---
name: knowledge-steward
description: "AI工作经验知识库管理。适用于用户明确要求'保存到Obsidian'、'记录这个'、'save this insight'、'memo this'、'capture this'等知识沉淀场景。将对话中的提示词、模式、问题修复、想法和效率优化保存到Obsidian知识库，并自动同步到GitHub。"
---

# Knowledge Steward Skill

你的"数字记账员"——防止智力剩余价值随着电缆流失。将稍纵即逝的灵感、有效的提示词、踩过的坑和突然的顿悟转化为永久存储的知识资产，并自动备份到GitHub云端。

## When to Use This Skill

当用户想要保存以下内容时使用此技能：

- **提示词复盘**：发现某个Prompt效果惊人地好或差时
  - 触发词："保存这个提示词"、"save this prompt"、"记录这个Prompt"
- **工程排坑**：花了很长时间解决了一个Bug时
  - 触发词："记录这个Bug"、"save this bugfix"、"保存解决方案"
- **灵感闪现**：突然想到一个架构优化或设计模式时
  - 触发词："保存这个想法"、"capture this idea"、"记录这个灵感"
- **模式总结**：发现了一个可复用的代码模式或最佳实践时
  - 触发词："保存这个模式"、"save this pattern"、"记录这个实践"
- **效率优化**：找到了提升工作效率的方法时
  - 触发词："保存这个技巧"、"save this tip"、"记录这个优化"
- **工作流复盘**：分析autonomous-builder的工作流报告时
  - 触发词："分析工作流"、"复盘这个项目"、"总结开发过程"
- **架构经验提取**：从多个报告中提取架构模式时
  - 触发词："提取架构模式"、"总结设计决策"、"分析技术选型"

**通用触发词**：
- "保存到Obsidian"
- "记录这个"
- "save this insight"
- "memo this"
- "capture this"

## Not For / Boundaries

**不适用于**：
- 纯粹的对话或提问（没有需要保存的内容）
- 已经保存在其他地方的内容（除非用户明确要求）
- 敏感信息或密钥（会警告用户）

**必需输入**：
1. **标题**：如果用户没有明确标题，从内容中提取
2. **类型**：从触发词或内容推断（提示词/模式/问题修复/想法/效率优化）
3. **内容**：从对话上下文中捕获

**可选输入**：
- 额外的标签
- 自定义分析

## Quick Reference

### 使用模式

**模式1：保存提示词**
```
用户："Claude，把你刚才用的那个关于代码重构的Prompt保存下来，标记为'高效'。"
Claude：提取最近使用的提示词 → 生成分析 → 保存到 提示词/ 目录
```

**模式2：记录Bug解决方案**
```
用户："记录这个Bug的解决方案，别让我下次再踩坑。"
Claude：捕获问题描述和解决方案 → 分析根本原因 → 保存到 问题修复/ 目录
```

**模式3：捕获灵感**
```
用户："保存这个关于微服务解耦的想法。"
Claude：提取想法内容 → 生成可行性分析 → 保存到 想法/ 目录
```

**模式4：中文触发**
```
用户："保存到Obsidian：使用苏格拉底式提问来引导代码重构"
Claude：识别中文触发词 → 提取标题和内容 → 自动分类 → 保存
```

### 文件结构

保存的笔记包含：
- **YAML Frontmatter**：元数据（创建时间、类型、标签、状态）
- **标题**：清晰的描述性标题
- **背景（Context）**：当时在做什么
- **内容（Content）**：核心的提示词/代码/想法
- **分析（Analysis）**：苏格拉底式反思

### 目录组织

```
D:\Documents\ai技能外置大脑/
└── Claude_Insights/
    ├── 提示词/          # Prompts - 有效/无效的提示词
    ├── 模式/            # Patterns - 可复用的代码模式
    ├── 问题修复/        # Bugfixes - Bug解决方案
    ├── 想法/            # Ideas - 架构和设计想法
    ├── 效率优化/        # Efficiency - 提升效率的技巧
    ├── 工作流/          # Workflows - AI辅助开发工作流分析
    └── 架构决策/        # Architecture - 架构设计决策记录
```

## Examples

### Example 1: 保存高效提示词

**Input**:
```
用户："Claude，保存这个提示词：'请用苏格拉底式提问引导我重构这段代码，不要直接给出答案'。这个提示词让我自己思考得更深入了。"
```

**Steps**:
1. 识别触发词："保存这个提示词"
2. 提取标题："使用苏格拉底式提问引导代码重构"
3. 确定类型：提示词
4. 捕获内容：完整的提示词文本
5. 生成标签：[提示词工程, 代码重构, 苏格拉底方法]
6. 生成分析："这个提示词有效是因为它利用了苏格拉底式对话的启发性..."
7. 调用 save_to_obsidian.py
8. 返回成功消息

**Expected Output**:
```
✓ 已保存到 Obsidian
文件：D:\Documents\ai技能外置大脑\Claude_Insights\提示词\2026-02-14_使用苏格拉底式提问引导代码重构.md
类型：提示词
标签：#提示词工程 #代码重构 #苏格拉底方法
✓ 已同步到 GitHub
```

### Example 2: 记录Bug解决方案

**Input**:
```
用户："记录这个Bug：npm install时出现ERESOLVE依赖冲突，解决方法是使用--legacy-peer-deps标志。"
```

**Steps**:
1. 识别触发词："记录这个Bug"
2. 提取标题："npm依赖冲突解决方案"
3. 确定类型：问题修复
4. 捕获内容：问题描述和解决方法
5. 生成标签：[npm, 依赖管理, 问题修复]
6. 生成分析："这个问题的根本原因是npm 7+的严格peer依赖检查..."
7. 保存到 问题修复/ 目录

**Expected Output**:
```
✓ 已保存Bug解决方案
文件：D:\Documents\ai技能外置大脑\Claude_Insights\问题修复\2026-02-14_npm依赖冲突解决方案.md
```

### Example 3: 捕获架构想法

**Input**:
```
用户："capture this idea: 使用事件溯源(Event Sourcing)来实现可审计的用户操作历史"
```

**Steps**:
1. 识别触发词："capture this idea"
2. 提取标题："使用事件溯源实现可审计的用户操作历史"
3. 确定类型：想法
4. 捕获内容：想法描述
5. 生成标签：[事件溯源, 架构设计, 审计]
6. 生成分析："这个想法的核心价值是提供完整的操作历史追溯能力..."
7. 保存到 想法/ 目录

**Expected Output**:
```
✓ 想法已保存
文件：D:\Documents\ai技能外置大脑\Claude_Insights\想法\2026-02-14_使用事件溯源实现可审计的用户操作历史.md
```

## References

- `references/index.md`: 知识管理哲学和使用指南
- `assets/note-template.md`: 笔记模板
- `assets/workflow-analysis-template.md`: 工作流分析模板
- `assets/setup-guide.md`: GitHub 同步设置指南
- `scripts/save_to_obsidian.py`: 保存脚本
- `scripts/parse_workflow_report.py`: 工作流报告解析脚本
- `scripts/distill_experience.py`: 经验提炼脚本
- `scripts/git_sync.py`: Git 同步模块
- `scripts/setup_github.py`: GitHub 设置向导
- `scripts/init_git_repos.py`: Git 仓库初始化脚本
- `scripts/sync_skill_code.py`: 技能代码同步脚本

## GitHub Sync Feature

### 功能概述

Knowledge Steward 现在支持自动将笔记同步到 GitHub，提供：
- **自动备份**：每次保存笔记时自动提交并推送到 GitHub
- **版本历史**：完整的 Git 历史记录，可追溯每次修改
- **多设备同步**：在多台设备间无缝同步知识库
- **云端存储**：安全的私有仓库存储

### 快速设置

1. **运行设置向导**：
   ```bash
   python scripts/setup_github.py
   ```

2. **初始化仓库**：
   ```bash
   python scripts/init_git_repos.py
   ```

3. **开始使用**：
   保存笔记时会自动同步到 GitHub

详细设置指南请参考 `assets/setup-guide.md`

### 配置选项

在 `config.yaml` 中配置：

```yaml
git:
  enabled: true          # 启用 Git 同步
  auto_sync: true        # 自动同步

repositories:
  knowledge_base:
    url: "https://github.com/username/knowledge-base.git"
    enabled: true
    auto_pull: true      # 推送前自动拉取（多设备同步）
```

### 临时禁用同步

使用 `--no-sync` 标志：
```bash
python scripts/save_to_obsidian.py --title "..." --type "..." --content "..." --no-sync
```

### 手动同步技能代码

```bash
python scripts/sync_skill_code.py
```

### 故障排除

- 查看日志：`logs/git_sync.log`
- 测试配置：`python scripts/git_sync.py --test-config`
- 检查 Git：`python scripts/git_sync.py --check-git`

## Plugin 智能发现与自动使用 (ToolSearch Auto-Discovery)

### 核心原则

Knowledge Steward 在执行任务时，**必须主动使用 ToolSearch** 发现并调用可用的 MCP 插件工具，以增强知识管理能力。

### 启动时自动发现

```
ON SKILL ACTIVATION:

1. 使用 ToolSearch 探测可用插件:
   - ToolSearch("github") → 发现 GitHub 相关工具（issue、PR、文件操作）
   - ToolSearch("serena") → 发现代码分析工具（符号查找、引用分析）

2. 根据当前任务类型选择插件:
   - 保存代码模式 → 使用 Serena 分析符号和引用关系
   - GitHub 同步 → 使用 GitHub MCP 工具直接操作仓库
   - 查找文档 → 先确认版本，再使用官方 primary docs
```

### 任务-插件智能映射

| 任务场景 | ToolSearch 查询 | 用途 |
|----------|----------------|------|
| 保存代码模式/架构经验 | `ToolSearch("+serena symbol")` | 分析代码符号结构，提取精确的模式描述 |
| GitHub 同步笔记 | `ToolSearch("+github file")` | 直接通过 MCP 创建/更新 GitHub 文件 |
| 创建 GitHub Issue 追踪 | `ToolSearch("+github issue")` | 为重要知识点创建追踪 Issue |
| 查询库文档补充知识 | 本地依赖信息与官方 primary docs | 查询第三方库文档，丰富知识条目 |
| 浏览器截图保存 | `ToolSearch("+playwright screenshot")` | 截取网页内容作为知识附件 |
| IDE 代码诊断 | `ToolSearch("getDiagnostics")` | 获取代码诊断信息辅助问题修复记录 |

### 使用流程

```
保存知识条目时:

1. 分析内容类型（提示词/模式/Bug修复/想法/效率优化）

2. 根据类型调用 ToolSearch 发现增强工具:
   IF 类型 == "模式" OR "架构经验":
     → ToolSearch("+serena find_symbol")
     → 使用 Serena 分析相关代码符号，提取精确的代码结构描述

   IF 类型 == "问题修复":
     → ToolSearch("getDiagnostics")
     → 获取当前代码诊断信息，补充到修复记录中

   IF 需要 GitHub 同步:
     → ToolSearch("+github create_or_update_file")
     → 直接通过 MCP 推送文件到 GitHub，无需本地 git 命令

   IF 需要查询库文档:
     → 先确认本地依赖版本，再查询官方 primary docs
     → 只用已核实的资料丰富知识条目；无法核实时明确标注

3. 将插件获取的信息整合到笔记内容中

4. 保存并同步
```

### 注意事项

- ToolSearch 返回的工具**立即可用**，无需再次 select
- 关键词搜索已加载工具后，**不要**重复用 `select:` 加载
- 优先使用 MCP 工具而非 Bash 命令（如用 GitHub MCP 代替 `git push`）
- 如果 ToolSearch 未找到相关工具，回退到原有的脚本方式

## Maintenance

- **Sources**: 基于用户需求文档和Claude Code Skills规范
- **Last updated**: 2026-02-16
- **Version**: 3.0 (添加 ToolSearch 插件智能发现)
- **Known limits**:
  - 需要Python 3.6+环境
  - 需要Obsidian vault路径可访问
  - 需要Git安装（用于GitHub同步）
  - 标签生成基于简单的关键词提取，可能不够精确
  - 分析生成基于预设模板，可能需要用户后续编辑
  - GitHub 同步需要网络连接
