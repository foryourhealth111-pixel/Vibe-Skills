# OpenClaw Runtime-Core 补齐需求文档

**日期**: 2026-03-26
**任务类型**: 适配补齐与验证收口
**优先级**: 高
**执行模式**: truth-first，先补齐声明层，再验证闭环

---

## 目标（Goal）

把当前已存在但未完全收口的 OpenClaw runtime-core 适配补齐到“声明、文档、验证”一致的状态。

## 交付物（Deliverable）

1. 补齐后的 OpenClaw adapter / closure 描述
2. 补齐后的 dist manifest 与 public manifest
3. 补齐后的 universalization 矩阵文档
4. 补齐后的 verify gate 覆盖
5. 本地安装 / 检查 / 测试证明

## 约束（Constraints）

1. 不回退现有用户改动
2. 不夸大为 host-native closure
3. 只在实际验证通过的前提下更新声明
4. 阶段结束后清理临时目录与僵尸 node

## 验收标准（Acceptance Criteria）

1. `install.* --host openclaw` 与 `check.* --host openclaw --deep` 在临时目录通过
2. OpenClaw 的 closure、dist manifest、public manifest、matrix docs 口径一致
3. `vibe-dist-manifest-gate.ps1` 覆盖到 OpenClaw 与 Windsurf 的 public/runtime-core lane
4. 与本轮补齐直接相关的 runtime-neutral 测试通过

## 非目标（Non-Goals）

1. 不声称 OpenClaw 宿主原生设置面已经闭环
2. 不在本轮解决所有历史 dist 文档缺口之外的产品问题
