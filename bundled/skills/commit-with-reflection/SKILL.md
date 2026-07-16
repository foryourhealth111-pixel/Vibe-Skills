---
name: commit-with-reflection
description: "Git提交与调试反思报告生成技能。用于分析开发过程中的错误、调试步骤和解决方案,生成结构化的中文反思报告,并创建包含报告引用的Git提交。显式请求词:反思提交、智能提交、生成调试报告、commit with reflection。"
---

# Git提交与反思报告技能 (Commit with Reflection)

自动化Git提交并生成深度调试反思报告的技能。将AI编码过程中的错误、调试经验和解决方案转化为结构化的知识文档,保存在GitHub仓库中供长期参考和学习。

## 何时使用此技能 (When to Use)

在以下情况下使用此技能:

- 用户说:"反思提交"、"智能提交"、"生成调试报告"
- 用户说:"commit with reflection"、"reflective commit"
- 完成了包含多次调试迭代的功能开发
- 修复了复杂的bug并希望记录解决过程
- 重构代码时遇到并解决了架构问题
- 希望将本次开发经验转化为可复用的知识

**相关信号（用于人工判断或路由参考）**:
- 检测到会话中出现了错误消息
- 对同一文件进行了3次以上的修改迭代
- Git diff显示添加了调试相关代码(console.log, try-catch等)

## 不适用场景 (Not For)

此技能不适用于:

- 简单的文字修改或格式调整(无错误发生)
- 仅添加注释或文档的提交
- 初始化项目或添加依赖包
- 用户明确要求"简单提交"或"快速提交"

**必需输入**:
- 至少有一个修改过的文件(git status显示变更)
- 会话中包含开发过程的上下文(如果无错误,会询问是否仍要生成报告)

## 快速参考 (Quick Reference)

### 核心工作流

**阶段1: 上下文收集**
```bash
# 获取Git状态
git status

# 获取所有变更
git diff

# 分析会话历史提取:
# - 错误消息和堆栈跟踪
# - 调试步骤和迭代
# - 解决方案和修复
```

**阶段2: 生成反思报告**
```
1. 读取统一模板
   - 优先使用: project-root/docs/workflows/templates/unified-template.md
   - 回退使用: ~/.claude/skills/shared-templates/unified-workflow-report.md

2. 分析内容:
   - 错误分类(语法/类型/逻辑/架构/集成)
   - 严重程度评级(严重/重要/次要)
   - 根本原因分析
   - 预防策略制定
   - 经验提炼和模式识别

3. 填充模板
   - 报告类型设为: reflection
   - 重点填充: 错误分析、根本原因、经验总结章节

报告格式:
docs/workflows/YYYY-MM/DD_reflection_[type]_[desc].md
```

**阶段3: 创建Git提交**
```bash
# 创建报告目录
mkdir -p docs/workflows/$(date +%Y-%m)

# 生成并保存报告
echo "$REPORT" > docs/workflows/...

# 提交所有变更
git add .
git commit -m "type: description

遇到错误: N
调试迭代: N

详见反思报告: docs/workflows/...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**阶段4: 更新索引**
```bash
# 自动更新 docs/workflows/INDEX.md
# 包含:
# - 按日期/类型/错误类型分类
# - 统计信息
# - 搜索标签
```

### 报告模板结构

```markdown
# 开发反思报告

**日期**: 2026-02-15 14:30:00
**提交类型**: feature | bugfix | refactor | docs
**会话时长**: 45 分钟
**修改文件数**: 5 个文件

## 1. 概述
简要描述本次修改的内容和目的

## 2. 修改内容
### 修改的文件
- `client/src/components/Feature.tsx` - 实现新功能
- `server/routers.ts` - 添加API端点

### 主要变更
- 添加了用户认证功能
- 修复了CORS跨域问题

## 3. 遇到的错误
### 错误 1: TypeScript类型错误
**严重程度**: 重要
**错误信息**: Property 'userId' does not exist on type 'User'
**上下文**: 在访问用户对象属性时
**解决方案**: 更新User接口定义,添加userId字段

## 4. 根本原因分析
### 为什么会出现这个错误?
- 直接原因: 接口定义不完整
- 深层原因: 数据库schema与TypeScript类型不同步
- 促成因素: 缺少类型检查的自动化流程

### 是什么导致编写时出现这个错误?
- 假设: 认为接口已经包含所有字段
- 知识盲区: 不了解数据库最新的schema变更
- 忽略的模式: 没有先检查现有类型定义

## 5. 调试过程
### 调查步骤
1. 检查TypeScript错误提示
2. 查看User接口定义
3. 对比数据库schema
4. 更新接口并验证

### 迭代过程
- 尝试 1: 直接添加类型断言 - 不可靠
- 尝试 2: 更新接口定义 - 成功

### 耗时统计
- 调查: 10 分钟
- 实现: 15 分钟
- 测试: 5 分钟

## 6. 经验总结
### 核心洞察
1. 类型定义应该与数据库schema保持同步
2. 类型断言只是临时方案,不能解决根本问题

### 预防策略
- 策略 1: 使用代码生成工具从schema自动生成类型
- 策略 2: 在修改schema后立即更新TypeScript类型

### 识别的最佳实践
- 实践 1: 先检查现有类型定义再编写代码
- 实践 2: 使用严格的TypeScript配置

## 7. 知识提炼
### 可复用模式
- 模式 1: Schema-first开发流程
- 模式 2: 类型安全的数据访问层

### 应避免的反模式
- 反模式 1: 使用any类型绕过类型检查
- 反模式 2: 类型断言掩盖真实问题

### 类似任务检查清单
- [ ] 检查数据库schema是否最新
- [ ] 验证TypeScript类型定义完整性
- [ ] 运行类型检查(tsc --noEmit)
- [ ] 测试所有数据访问路径

## 8. 测试与验证
### 测试用例
- 测试 1: 用户登录流程 - 通过
- 测试 2: 获取用户信息 - 通过

### 验证步骤
1. 运行TypeScript编译检查
2. 执行单元测试
3. 手动测试关键功能

## 9. 参考资料
- 相关提交: abc123, def456
- 文档: docs/api/user-authentication.md
- 外部资源: TypeScript官方文档

## 10. 指标
- 总错误数: 3
- 严重错误数: 1
- 调试迭代次数: 5
- 成功率: 80%
- 代码变动: +120 -45 行

---
**生成工具**: Claude Sonnet 4.5
**技能**: commit-with-reflection v1.0
```

### 错误检测逻辑

```javascript
// 判断是否需要生成反思报告
function needsReflectionReport(context) {
  // 条件1: 发现错误消息
  const hasErrors = context.errors.length > 0;

  // 条件2: 多次迭代(>3次修改同一文件)
  const hasIterations = context.iterations > 3;

  // 条件3: 添加了调试代码
  const hasDebuggingCode = context.diff.includes('console.log') ||
                           context.diff.includes('try {') ||
                           context.diff.includes('catch (');

  // 条件4: 用户明确请求
  const userRequested = context.userMessage.includes('反思') ||
                        context.userMessage.includes('调试报告');

  return hasErrors || hasIterations || hasDebuggingCode || userRequested;
}
```

### 提交类型判断

```javascript
// 根据变更内容判断提交类型
function determineCommitType(context) {
  const { files, diff, errors } = context;

  // 新增功能
  if (diff.includes('export function') || diff.includes('export const')) {
    return 'feature';
  }

  // 错误修复
  if (errors.length > 0 || diff.includes('fix:')) {
    return 'bugfix';
  }

  // 重构
  if (diff.includes('refactor:') || hasStructuralChanges(diff)) {
    return 'refactor';
  }

  // 文档
  if (files.every(f => f.endsWith('.md'))) {
    return 'docs';
  }

  return 'feature'; // 默认
}
```

## 示例 (Examples)

### 示例 1: 功能开发中的类型错误

**输入**:
- 用户: "反思提交"
- 会话包含: 3个TypeScript类型错误,5次迭代修复
- 修改文件: 4个.tsx文件, 1个.ts文件

**执行步骤**:
1. 运行`git status`和`git diff`收集变更
2. 从会话历史提取3个错误及其解决过程
3. 分析根本原因: 接口定义不完整
4. 生成报告: `docs/reflections/2026-02/15_feature_user-auth.md`
5. 创建提交并引用报告
6. 更新`docs/reflections/INDEX.md`

**预期输出**:
- 生成完整的中文反思报告(10个章节)
- Git提交包含报告引用
- 索引文件自动更新
- 用户收到确认消息: "已创建反思报告并提交代码"

### 示例 2: 简单修改(无错误)

**输入**:
- 用户: "提交代码"
- 会话无错误消息
- 修改文件: 1个README.md

**执行步骤**:
1. 检测到无错误发生
2. 询问用户: "未检测到错误,是否仍要生成反思报告?"
3. 用户选择"否"
4. 创建标准Git提交(无报告)

**预期输出**:
- 标准Git提交消息
- 不生成反思报告
- 不更新索引

### 示例 3: 复杂重构

**输入**:
- 用户: "生成调试报告并提交"
- 会话包含: 架构调整,2个集成问题,8次迭代
- 修改文件: 12个文件

**执行步骤**:
1. 收集所有变更和错误信息
2. 识别为重构类型(refactor)
3. 分析架构层面的根本原因
4. 提炼可复用的重构模式
5. 生成报告: `docs/reflections/2026-02/15_refactor_api-layer.md`
6. 创建提交并更新索引

**预期输出**:
- 包含架构洞察的反思报告
- 识别的重构模式和反模式
- 详细的预防策略检查清单

## 参考资料 (References)

### 本地文档
- `references/index.md` - 参考资料导航
- `references/error-taxonomy.md` - 错误分类体系
- `references/best-practices.md` - 反思报告最佳实践
- `references/report-schema.md` - 报告结构规范

### 模板文件
- `assets/template-chinese.md` - 中文报告完整模板
- `assets/template-feature.md` - 功能开发专用模板
- `assets/template-bugfix.md` - 错误修复专用模板
- `assets/template-refactor.md` - 重构专用模板

### 脚本工具
- `scripts/update-index.js` - 索引更新脚本
- `scripts/validate-report.js` - 报告格式验证
- `scripts/extract-errors.js` - 错误提取工具

### 示例报告
- `examples/feature-example.md` - 功能开发示例
- `examples/bugfix-example.md` - 错误修复示例
- `examples/refactor-example.md` - 重构示例

## 维护信息 (Maintenance)

- **数据来源**: 基于项目commit历史分析和反思报告最佳实践
- **最后更新**: 2026-02-15
- **版本**: v2.0 (统一模板集成)
- **已知限制**:
  - 仅支持中文报告生成
  - 需要Git仓库环境
  - 依赖会话历史完整性
  - 错误检测基于启发式规则,可能有误判

## 统一模板集成 (Unified Template Integration)

### 概述

从v2.0开始，commit-with-reflection使用与autonomous-builder相同的统一报告模板，确保两个技能生成的报告格式一致。

### 模板位置

优先级顺序：
1. **项目本地模板**: `docs/workflows/templates/unified-template.md`
2. **全局共享模板**: `~/.claude/skills/shared-templates/unified-workflow-report.md`

### 模板特性

统一模板包含12个章节：
1. 概述
2. 用户需求与提示词
3. 工作流记录
4. 修改内容
5. 遇到的错误
6. 根本原因分析
7. 调试过程
8. 经验总结
9. 知识提炼
10. 测试与验证
11. 参考资料
12. 指标

### 报告类型标识

commit-with-reflection生成的报告设置：
- `{REPORT_TYPE}`: "reflection"
- 文件名格式: `DD_reflection_[type]_[desc].md`

### 与autonomous-builder的区别

| 特性 | autonomous-builder | commit-with-reflection |
|------|-------------------|----------------------|
| 报告类型 | workflow | reflection |
| 触发时机 | 每个feature完成后 | 用户手动触发 |
| 重点章节 | 工作流记录、决策点 | 错误分析、经验总结 |
| 用户提示词 | 自动记录 | 从会话提取 |
| 工作流步骤 | 详细记录 | 简化记录 |

### 配置

在项目的`.claude-workflows.yaml`中配置：

```yaml
skills:
  commit-with-reflection:
    unified_template: true
    output_dir: "docs/workflows"
    language: "zh-CN"
```

## 工作流详解 (Detailed Workflow)

### 阶段 1: 上下文收集

```
1. 执行Git命令
   - git status: 获取修改文件列表
   - git diff: 获取具体变更内容
   - git log -1: 获取最近提交信息

2. 分析会话历史
   - 提取所有错误消息(Error:, TypeError:, etc.)
   - 识别调试步骤(尝试、修复、验证)
   - 统计迭代次数(同一文件的修改次数)
   - 计算会话时长

3. 构建上下文对象
   {
     files: ['file1.ts', 'file2.tsx'],
     diff: '完整的git diff输出',
     errors: [
       {
         message: '错误消息',
         type: '错误类型',
         context: '代码上下文',
         solution: '解决方案'
       }
     ],
     iterations: 5,
     duration: 45, // 分钟
     hasDebugging: true
   }

4. 判断是否需要报告
   if (needsReflectionReport(context)) {
     继续生成报告
   } else {
     询问用户是否仍要生成
   }
```

### 阶段 2: 报告生成

```
1. 错误分析
   for each error in context.errors:
     - 分类: 语法/类型/逻辑/架构/集成
     - 评级: 严重/重要/次要
     - 提取代码上下文
     - 识别解决方案
     - 分析根本原因

2. 经验提炼
   - 识别核心洞察(为什么会出错)
   - 制定预防策略(如何避免)
   - 提取可复用模式
   - 识别反模式
   - 生成检查清单

3. 填充模板
   - 使用 assets/template-chinese.md
   - 根据提交类型选择专用模板
   - 填充所有10个章节
   - 确保中文格式正确

4. 生成文件名
   格式: YYYY-MM/DD_[type]_[short-desc].md
   示例: 2026-02/15_feature_user-auth.md
```

### 阶段 3: Git提交

```
1. 确保目录存在
   mkdir -p docs/reflections/$(date +%Y-%m)

2. 写入报告文件
   REPORT_PATH="docs/reflections/2026-02/15_feature_desc.md"
   echo "$REPORT_CONTENT" > "$REPORT_PATH"

3. 暂存所有变更
   git add .

4. 生成提交消息
   COMMIT_MSG="feature: 实现用户认证功能

添加了JWT token验证和用户登录API端点。

遇到错误: 3
调试迭代: 5

详见反思报告: docs/reflections/2026-02/15_feature_user-auth.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

5. 创建提交
   git commit -m "$COMMIT_MSG"
```

### 阶段 4: 索引更新

```
1. 扫描所有报告
   reports = scanDirectory('docs/reflections/')

2. 提取元数据
   for each report:
     - 日期
     - 类型
     - 错误数量
     - 标签
     - 文件路径

3. 生成索引结构
   index = {
     lastUpdated: '2026-02-15 14:30:00',
     totalReports: 15,
     byType: {
       feature: 8,
       bugfix: 5,
       refactor: 2
     },
     byDate: [...],
     byErrorType: {...},
     byFile: {...},
     tags: ['PDF', 'React', 'TypeScript', ...]
   }

4. 渲染INDEX.md
   使用中文模板生成索引文件

5. 提交索引更新
   git add docs/reflections/INDEX.md
   git commit --amend --no-edit
```

## 质量保证 (Quality Assurance)

### 报告质量检查

生成的报告必须满足:

1. **完整性**: 包含所有10个必需章节
2. **准确性**: 错误信息和解决方案准确无误
3. **深度**: 根本原因分析有洞察力
4. **实用性**: 预防策略具体可执行
5. **可读性**: 中文表达清晰流畅
6. **格式**: Markdown格式正确,代码块完整

### 自动验证

```bash
# 验证报告格式
node scripts/validate-report.js docs/reflections/2026-02/15_feature_desc.md

# 检查项:
# - 是否包含所有必需章节
# - 日期格式是否正确
# - 代码块是否闭合
# - 中文编码是否为UTF-8
# - 文件名是否符合规范
```

### 人工审查

建议定期审查反思报告:
- 每周回顾本周的所有报告
- 识别重复出现的错误模式
- 更新预防策略
- 完善检查清单

## 故障排除 (Troubleshooting)

### 问题 1: 未检测到错误但确实有错误

**原因**: 错误消息格式不标准或被截断

**解决方案**:
- 手动触发: 明确说"生成调试报告"
- 检查会话历史是否完整
- 确认错误消息包含关键词(Error, TypeError等)

### 问题 2: 报告生成但内容空洞

**原因**: 会话历史不包含足够的调试细节

**解决方案**:
- 在调试过程中提供更多上下文
- 描述尝试的解决方案
- 说明为什么某些方案不work

### 问题 3: Git提交失败

**原因**: 工作目录不是Git仓库或有冲突

**解决方案**:
```bash
# 检查Git状态
git status

# 解决冲突
git add .
git commit -m "..."

# 如果需要,手动创建报告
```

### 问题 4: 中文乱码

**原因**: 文件编码不是UTF-8

**解决方案**:
```bash
# 检查文件编码
file -i docs/reflections/**/*.md

# 转换为UTF-8
iconv -f GBK -t UTF-8 file.md > file_utf8.md
```

## 扩展和定制 (Extensions)

### 添加新的错误类型

编辑 `references/error-taxonomy.md`:

```markdown
### 新错误类型: 性能问题

**特征**:
- 响应时间过长
- 内存占用过高
- CPU使用率异常

**常见原因**:
- 未优化的数据库查询
- 内存泄漏
- 无限循环

**预防策略**:
- 使用性能分析工具
- 设置性能监控
- 编写性能测试
```

### 自定义报告模板

创建新模板 `assets/template-custom.md`:

```markdown
# 自定义反思报告

## 特定章节
...

## 其他章节
...
```

在SKILL.md中引用:

```javascript
if (context.customType) {
  template = 'assets/template-custom.md';
}
```

### 集成CI/CD

在 `.github/workflows/reflection.yml`:

```yaml
name: Validate Reflection Reports

on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate reports
        run: |
          node scripts/validate-report.js docs/reflections/**/*.md
```

## 最佳实践建议 (Best Practices)

1. **及时记录**: 在调试过程中记录关键步骤,不要事后回忆
2. **深入分析**: 不要满足于表面原因,挖掘深层次的根本原因
3. **具体策略**: 预防策略要具体可执行,不要泛泛而谈
4. **定期回顾**: 每周回顾反思报告,识别模式和趋势
5. **持续改进**: 根据反思报告更新开发流程和检查清单
6. **知识共享**: 将有价值的反思报告分享给团队成员
7. **模式库建设**: 积累常见错误模式和解决方案库

## Plugin 智能发现与自动使用 (ToolSearch Auto-Discovery)

### 核心原则

commit-with-reflection 在执行任务时，**必须主动使用 ToolSearch** 发现并调用可用的 MCP 插件工具，以增强反思报告的深度和准确性。

### 启动时自动发现

```
ON SKILL ACTIVATION:

1. 使用 ToolSearch 探测可用插件:
   - ToolSearch("getDiagnostics") → 发现 IDE 诊断工具
   - ToolSearch("+serena symbol") → 发现代码符号分析工具
   - ToolSearch("+github") → 发现 GitHub 操作工具

2. 将发现的工具记录到工作上下文中，后续步骤直接调用
```

### 各阶段插件使用

**阶段1: 上下文收集 - 增强版**

```
原有流程:
  git status → git diff → 分析会话历史

增强流程 (使用 ToolSearch):
  1. ToolSearch("getDiagnostics")
     → 获取 IDE 诊断信息（类型错误、lint 警告等）
     → 补充到错误列表中，比纯文本分析更精确

  2. ToolSearch("+serena get_symbols_overview")
     → 分析修改文件的符号结构
     → 理解代码变更的架构影响

  3. ToolSearch("+serena find_referencing_symbols")
     → 查找被修改符号的所有引用
     → 评估变更的影响范围
```

**阶段2: 报告生成 - 增强版**

```
原有流程:
  分析错误 → 提炼经验 → 填充模板

增强流程 (使用 ToolSearch):
  1. IF 涉及第三方库问题:
     → 先确认本地依赖版本，再查询官方 primary docs
     → 只把已核实的正确用法补充到报告中

  2. IF 需要代码结构分析:
     → ToolSearch("+serena find_symbol")
     → 获取精确的符号定义和关系图

  3. IF 需要截图记录:
     → ToolSearch("+playwright screenshot")
     → 截取应用状态作为报告附件
```

**阶段3: Git提交 - 增强版**

```
原有流程:
  git add → git commit

增强流程 (使用 ToolSearch):
  1. IF 需要创建 GitHub Issue 追踪:
     → ToolSearch("+github create_issue")
     → 为重要的 Bug 修复创建追踪 Issue

  2. IF 需要推送到远程:
     → ToolSearch("+github push_files")
     → 通过 MCP 直接推送，无需本地 git push
```

### 任务-插件智能映射

| 反思报告阶段 | ToolSearch 查询 | 用途 |
|-------------|----------------|------|
| 错误分析 | `ToolSearch("getDiagnostics")` | 获取精确的 IDE 诊断信息 |
| 代码结构分析 | `ToolSearch("+serena symbol")` | 分析修改的代码符号和引用关系 |
| 库文档查询 | 本地依赖信息与官方 primary docs | 查询第三方库正确用法 |
| GitHub Issue | `ToolSearch("+github issue")` | 创建 Bug 追踪 Issue |
| 应用截图 | `ToolSearch("+playwright screenshot")` | 截取应用状态作为报告附件 |
| 代码执行验证 | `ToolSearch("executeCode")` | 执行代码片段验证修复效果 |

### 注意事项

- ToolSearch 返回的工具**立即可用**，无需再次 select
- 关键词搜索已加载工具后，**不要**重复用 `select:` 加载
- 优先使用 MCP 工具而非 Bash 命令
- 如果 ToolSearch 未找到相关工具，回退到原有方式
- 插件增强是**可选的**，核心流程不依赖插件可用性

## 版本历史 (Version History)

### v1.0 (2026-02-15)
- 初始版本
- 支持中文报告生成
- 自动错误检测
- Git提交集成
- 索引自动更新
- 支持feature/bugfix/refactor/docs四种类型

### v2.0 (2026-02-15)
- 统一模板集成
- 与autonomous-builder共享报告格式

### v3.0 (2026-02-16)
- 添加 ToolSearch 插件智能发现
- 自动使用 MCP 插件增强报告质量
