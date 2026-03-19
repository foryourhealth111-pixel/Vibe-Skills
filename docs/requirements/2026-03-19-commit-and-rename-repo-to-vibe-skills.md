# 2026-03-19 Commit And Rename Repo To Vibe-Skills

## Goal

先安全提交当前本地未发布改动，再将 GitHub 仓库从 `vco-skills-codex` 更名为 `Vibe-Skills`，同时保证本地脏工作区不被破坏，且更名后本地 remote 与远端仓库状态可验证。

## Deliverables

- 在安全隔离环境中提交并推送当前本地未发布改动
- 将 GitHub 仓库更名为 `Vibe-Skills`
- 更新本地 `origin` remote 指向新仓库地址
- 产出远端提交、rename、remote 更新与重定向验证证据

## Constraints

- 当前主工作区为 dirty 且与远端分叉，不能直接在原位 commit/push
- 必须先提交当前改动，再做仓库 rename
- 可以忽略外部引用，不把外部使用者兼容性作为本轮阻塞条件
- 本轮不改本地文件夹名，只改 GitHub 仓库名和 git remote

## Acceptance Criteria

- 当前 dirty 改动被打包成一个新提交并发布到远端 `main`
- GitHub 仓库名变为 `Vibe-Skills`
- 本地仓库 `origin` URL 已更新到新仓库地址
- 新仓库地址可访问，旧地址的 rename 行为得到验证

## Frozen User Intent

用户明确要求：

- 先提交刚刚修改
- 然后再进行改名
- 一定要保证安全性
- 可以不考虑外部引用

## Evidence Strategy

- 记录隔离 worktree 提交与 push 结果
- 记录 GitHub rename API 结果
- 记录本地 `git remote -v` / `git fetch` 验证结果
- 回读远端仓库信息确认新名字已生效
