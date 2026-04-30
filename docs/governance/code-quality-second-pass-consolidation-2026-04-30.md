# code-quality 第二轮收敛记录

日期：2026-04-30

## 结论

`code-quality` 第二轮继续保持简化路由模型：

```text
candidate skill -> selected skill -> used / unused
```

本轮不恢复阶段助手、辅助专家、咨询态、主技能/次技能。当前 `stage_assistant_candidates = 0`。

## 当前直接 route owner

| skill | 负责的问题 |
|---|---|
| `code-reviewer` | 新鲜代码审查、PR review、质量和可维护性检查 |
| `requesting-code-review` | 准备发起代码审查，整理 review request |
| `receiving-code-review` | 收到 CodeRabbit/GitHub/人工评审意见后逐条判断和处理 |
| `security-reviewer` | 安全审计、OWASP、secret、auth、injection、权限风险 |
| `systematic-debugging` | bug、失败测试、构建失败、异常行为、根因定位 |
| `windows-hook-debugging` | Windows hook、Git Bash、WSL、cannot execute binary file |
| `tdd-guide` | TDD、先写失败测试、红绿重构 |
| `generating-test-reports` | 测试报告、coverage summary、JUnit/test summary |
| `verification-before-completion` | 收尾前确认测试、验收证据、完成声明前验证 |
| `deslop` | 清理 AI 生成代码废话注释、冗余防御式检查、模板噪声 |

## 旧目录处理

| skill | 处理 |
|---|---|
| `code-review` | 可复用 style guide 和 checker 已迁移到 `code-reviewer`，旧目录删除。 |
| `debugging-strategies` | 与 `systematic-debugging` 重叠，旧目录删除。 |
| `code-review-excellence` | 与 `code-reviewer` 重叠，旧目录删除。 |
| `error-resolver` | 资产重，保留目录；本轮不作为活跃直接路由 owner。 |

## 验证计划

实现完成后运行以下命令。最终验证输出在执行阶段更新到本记录。

```text
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_final_stage_assistant_removal.py -q
```

```text
.\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1
```

```text
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

```text
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

```text
.\scripts\verify\vibe-pack-routing-smoke.ps1
```

```text
.\scripts\verify\vibe-offline-skills-gate.ps1
```

## 边界

本记录证明的是 routing/config/bundled skill cleanup，不证明这些 skills 已经在某个真实 Vibe 任务中被物质使用。
