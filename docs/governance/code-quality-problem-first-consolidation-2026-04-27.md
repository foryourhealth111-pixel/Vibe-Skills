# code-quality pack 问题优先收敛记录

日期：2026-04-27

## 一句话结论

这次治理不是按 skill 名字保留，而是按“用户到底在问什么问题”来分工。`code-quality` 从 16 个候选收敛到 10 个候选，并新增主路由/阶段助手分层，避免旧别名和宽泛 review/debug skill 抢路由。

## 调整前后

| 项目 | 调整前 | 调整后 |
|---|---:|---:|
| `skill_candidates` | 16 | 10 |
| `route_authority_candidates` | 0 | 9 |
| `stage_assistant_candidates` | 0 | 1 |
| 物理删除目录 | 0 | 2 |

## 保留为主路由的 skill

| skill | 负责的问题 |
|---|---|
| `code-reviewer` | 普通代码审查、PR review、质量检查、可维护性和回归风险 |
| `systematic-debugging` | bug、失败测试、构建失败、编译错误、根因定位 |
| `security-reviewer` | OWASP、secret、auth、权限、输入校验等安全风险 |
| `tdd-guide` | TDD、先写失败测试、红绿重构 |
| `generating-test-reports` | 测试报告、coverage 汇总、JUnit/test summary 包装 |
| `windows-hook-debugging` | Windows hook、Git Bash、WSL、cannot execute binary file |
| `deslop` | 清理 AI 生成代码里的废话注释、多余防御式检查、模板噪声 |
| `receiving-code-review` | 处理 CodeRabbit 或人工评审意见，逐条判断是否要改 |
| `verification-before-completion` | 收尾前确认测试、验收证据、完成声明前验证 |

## 阶段助手

| skill | 为什么不是主路由 |
|---|---|
| `requesting-code-review` | 它适合“提交前请求 review”这种流程节点，不应抢普通代码审查入口。 |

## 移出 code-quality 路由面但保留目录

| skill | 处理方式 |
|---|---|
| `code-review` | 与 `code-reviewer` 重叠，但目录里有脚本和 reference，先退出本 pack 主路由，后续再决定是否迁移资产。 |
| `debugging-strategies` | 与 `systematic-debugging` 重叠，先退出主路由，保留为显式/后续审阅内容。 |
| `error-resolver` | 与调试入口重叠，且治理判断为较高风险，先保留目录。 |
| `code-review-excellence` | 更像 review 文化/培训/标准，不应抢实际代码审查主入口。 |

## 已删除的薄别名

| skill | 删除原因 | 接管者 |
|---|---|---|
| `reviewing-code` | 只是 legacy compatibility alias，无 scripts/references/assets。 | `code-reviewer` |
| `build-error-resolver` | 只是构建错误兼容壳，无 scripts/references/assets。 | `systematic-debugging` |

## 路由边界

| 用户问题 | 现在应该命中 |
|---|---|
| `run code review and quality checks` | `code-quality / code-reviewer` |
| `收到CodeRabbit评审意见，帮我逐条判断是否要改` | `code-quality / receiving-code-review` |
| `准备收尾，确认测试通过并给出验收证据` | `code-quality / verification-before-completion` |
| `清理AI生成代码里的废话注释和多余防御式检查` | `code-quality / deslop` |
| `构建失败，TypeScript compile error，帮我定位` | `code-quality / systematic-debugging` |

## 验证方法

重点验证分三层：

| 层级 | 命令 |
|---|---|
| 问题地图审计 | `python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py -q` |
| pack 专项审计 | `powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit` |
| 路由回归 | `powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1` |
| 技能索引回归 | `powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1` |
| 离线技能完整性 | `powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1` |

## 后续建议

`code-quality` 这次先解决“主路由重复、薄别名占位、真实问题不命中”的问题。下一轮如果继续深挖，可以审阅 `code-review`、`debugging-strategies`、`error-resolver` 的可迁移资产，再决定是否把内容并入主入口或改成显式 skill。
