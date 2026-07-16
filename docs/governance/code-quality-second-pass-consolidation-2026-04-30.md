# code-quality 第二轮收敛记录

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

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

## 配置清理

`config/batch-e-alias-whitelist.json` 是旧 Batch E alias 审计快照，文件自身标注为 audit-only / historical snapshot，且没有 runtime、脚本、测试或分发 manifest 消费。本轮删除该 active config 下的历史 JSON，避免旧 `code-review` canonical 名继续出现在活跃配置目录中。

保留的 `config/settings.template.claude.json` 中仍有 `code-review@claude-plugins-official`，这是 Claude 官方插件名，不是 Vibe bundled skill id。

## 验证结果

```text
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_final_stage_assistant_removal.py -q
..................                                                       [100%]
18 passed in 1.14s
```

```text
.\scripts\verify\vibe-code-quality-pack-consolidation-audit-gate.ps1
[PASS] vibe-code-quality-pack-consolidation-audit-gate passed
summary:
  code_quality_skill_count: 16
  target_route_authority_count: 10
  target_stage_assistant_count: 0
  delete_now_count: 4
  move_out_count: 0
  merge_delete_after_migration_count: 1
  defer_migration_count: 1
```

```text
.\scripts\verify\vibe-skill-index-routing-audit.ps1
=== Summary ===
Total assertions: 436
Passed: 436
Failed: 0
Skill-index routing audit passed.
```

```text
.\scripts\verify\vibe-pack-regression-matrix.ps1
=== Summary ===
Total assertions: 317
Passed: 317
Failed: 0
Pack regression matrix checks passed.
```

```text
.\scripts\verify\vibe-pack-routing-smoke.ps1
=== Summary ===
Total assertions: 958
Passed: 958
Failed: 0
Pack routing smoke checks passed.
```

```text
.\scripts\verify\vibe-offline-skills-gate.ps1
skills_root=F:\vibe\Vibe-Skills\bundled\skills
required_skills=169
canonical_required_skills=1
present_skills=296
lock_skills=296
skip_hash=False
[PASS] offline skill closure gate passed.
```

```text
rg -n -P "(?<!receiving-)(?<!requesting-)\bcode-review\b|\bdebugging-strategies\b|\bcode-review-excellence\b" config scripts bundled
config\settings.template.claude.json:18:    "code-review@claude-plugins-official": true,
```

```text
rg -n -P "\berror-resolver\b" config scripts bundled
config\skills-lock.json:537:      "name": "error-resolver",
config\skills-lock.json:538:      "relative_path": "bundled/skills/error-resolver",
```

## 边界

本记录证明的是 routing/config/bundled skill cleanup，不证明这些 skills 已经在某个真实 Vibe 任务中被物质使用。
