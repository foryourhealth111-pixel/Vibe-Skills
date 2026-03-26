# OpenClaw 文档支持面对齐执行计划

**日期**: 2026-03-25
**需求文档**: [2026-03-25-openclaw-doc-surface-alignment.md](../requirements/2026-03-25-openclaw-doc-surface-alignment.md)
**执行级别**: L（文档面多点收口，需要统一校验）
**执行模式**: 文档提交与推送

---

## 📋 执行概览

本计划聚焦 OpenClaw 对外文档面的统一更新，并将结果作为单独文档提交推送到当前分支。

## 🎯 阶段划分

### 阶段 1：基线确认

- 核对 GitHub 远端 `HEAD`
- 确认本地分支基线是否与远端最新一致
- 确认工作区存在其他未提交改动，避免混提

### 阶段 2：文档口径收敛

- 更新 README 与 README.zh 中的宿主支持入口
- 更新安装索引、冷启动说明、手动复制说明、高级安装路径说明
- 更新 OpenClaw 专项说明
- 更新中英文安装 / 更新提示词

### 阶段 3：验证

- 使用 `rg` 检查：
  - 旧的“四宿主”表述
  - 旧的 OpenClaw 过重防御文案
  - `openclaw` 是否已出现在所有安装提示词中
- 使用 `git diff --stat` 检查本次文档变更范围

### 阶段 4：提交与推送

- 只暂存本轮文档文件与 requirement / plan 记录
- 使用单一提交信息提交
- 推送到当前分支 `feat/openclaw-runtime-core-preview`

### 阶段 5：阶段清理

- 检查是否产生临时文件
- 检查是否产生新的 node 进程
- 保持仓库整洁，不清理不属于本轮的用户改动

## ✅ 验证命令

```bash
rg -n "四个宿主|four supported hosts|four hosts|只对四个|all four supported hosts" README.md README.zh.md docs/install docs/cold-start-install-paths.md docs/cold-start-install-paths.en.md
rg -n -F "host-native plugin closure" docs/install docs/cold-start-install-paths.md docs/cold-start-install-paths.en.md
rg -n "openclaw|OpenClaw" README.md README.zh.md docs/install docs/install/prompts docs/cold-start-install-paths.md docs/cold-start-install-paths.en.md
git diff --stat -- README.md README.zh.md docs/install docs/cold-start-install-paths.md docs/cold-start-install-paths.en.md
```

## 🔄 回滚规则

- 若提交前发现混入非文档文件，重置暂存区后重新精确暂存
- 若推送失败，保留本地提交并报告远端错误

## 🧹 清理要求

- 不保留额外临时文件
- 不创建无必要缓存
- 如无本轮新建 node 进程，记录为“无需清理”

---

**计划状态**: 已执行
