# Multi-Host Install Validation Sweep 需求文档

**日期**: 2026-03-26
**任务类型**: 安装可信度验证
**优先级**: 高
**执行模式**: governed, deep verification

---

## 目标（Goal）

对当前修复分支做一次多宿主、深度、可复现实验的安装验证，确认普通用户按仓库当前说明执行时，不会因为 OpenClaw 修复而影响其他宿主安装路径。

## 交付物（Deliverable）

1. 一份覆盖 `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw` 的安装验证结果
2. 自动化测试与命令级安装实验的通过/失败证明
3. 若发现问题，则包含修复与复测结果
4. 阶段结束后的清理与残余风险说明

## 约束（Constraints）

1. 以当前修复分支为基线，不回到旧主线做无意义测试
2. 以真实 install/check/bootstrap 命令为准，不只看文档和代码
3. 不把预期边界包装成“失败”
4. 不忽略 `bundled` / installed runtime 路径
5. 阶段结束后清理临时目录，并检查僵尸 node

## 验收标准（Acceptance Criteria）

1. `tests/runtime_neutral` 中与 install/check/bootstrap/freshness/coherence 直接相关的测试通过
2. `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw` 均至少完成一条真实 shell 安装/检查路径验证
3. `openclaw` 与 `windsurf` 的 installed runtime 路径验证通过
4. 若存在宿主边界或人工步骤，必须明确标为产品边界，而不是模糊写成“已完全自动化”
5. 输出结论必须区分：
   - 可以稳定安装
   - 可以安装但有明确人工步骤
   - 当前仍有风险或未证明

## 非目标（Non-Goals）

1. 不在本轮新增新的宿主
2. 不在本轮做 UI 层面的人工点击测试
3. 不在本轮解决与安装无关的功能性缺陷
