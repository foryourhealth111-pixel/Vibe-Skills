# OpenClaw 文档支持面对齐需求文档

**日期**: 2026-03-25
**任务类型**: 文档治理 - OpenClaw 安装与使用说明对齐
**优先级**: 高
**执行模式**: 文档范围冻结，truth-first 收口

---

## 🎯 目标（Goal）

基于 GitHub 最新版本，对 README、安装说明和安装提示词中的 OpenClaw 支持文案进行统一更新，保证公开口径简洁、准确、一致。

## 📦 交付物（Deliverable）

1. 更新后的 README / README.zh
2. 更新后的安装索引、冷启动说明、手动复制说明、高级安装路径说明
3. 更新后的 OpenClaw 专项说明文档
4. 更新后的中英文安装 / 更新提示词
5. 一次仅包含本轮文档改动的 Git 提交

## 🔒 约束条件（Constraints）

1. 必须以 GitHub 当前最新 `HEAD` 为基线，不基于落后版本写文案
2. 只提交本轮文档改动，不夹带尚未验证的运行时代码改动
3. OpenClaw 口径统一为：
   - `preview`
   - `runtime-core-preview`
   - `runtime-core`
4. 默认目标根目录统一写为 `OPENCLAW_HOME` 或 `~/.openclaw`
5. 安装路径统一写为 attach / copy / bundle
6. 删除或弱化冗余的“宿主登录 / 账号 / provider / plugin closure”式表述

## ✅ 验收标准（Acceptance Criteria）

1. 所有公开安装入口都已补上 `openclaw`
2. README 与安装文档口径一致
3. 安装提示词中英文版本都已包含 OpenClaw 宿主选项
4. 不再残留“四宿主”旧文案
5. 不再残留过重的 OpenClaw 防御式表述
6. 只提交文档文件与本次 requirement / plan 记录

## 🚫 非目标（Non-Goals）

1. 不修改 OpenClaw 运行时代码实现
2. 不在这次提交里合并适配器、脚本、测试等未完成改动
3. 不扩展新的宿主支持范围

## 🤔 假设（Assumptions）

1. 当前分支里的大量运行时改动属于另一批工作，不应混入本次文档提交
2. 用户当前优先要的是公开文档与安装提示词可直接对外使用
3. 文档验证以全文检索和差异检查为主，不需要运行代码测试

---

**需求冻结时间**: 2026-03-25
**批准状态**: 已批准
