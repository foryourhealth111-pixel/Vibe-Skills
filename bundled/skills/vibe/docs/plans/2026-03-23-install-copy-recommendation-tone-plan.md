# 安装文案推荐口径执行计划

日期：2026-03-23

## 变更范围

- `docs/install/full-featured-install-prompts*.md`
- `docs/install/one-click-install-release-copy*.md`
- `docs/install/recommended-full-path*.md`
- `docs/cold-start-install-paths*.md`
- `docs/install/host-plugin-policy*.md`
- `check.sh`
- `check.ps1`

## 执行步骤

1. 把 hook 缺失文案改成兼容性冻结说明，并明确这不是安装失败。
2. 把 MCP / `VCO_AI_PROVIDER_*` 相关描述统一为按需启用的可选增强项。
3. 将检查脚本中的 Claude preview hook/scaffold 提示从 warning 调整为 info。
4. 把同样的文案同步到当前已安装的 `~/.codex/skills/vibe` 副本。

## 验收

- 安装提示中不再把 hook 未安装写成告警口吻。
- 文档中明确区分基础安装完成与可选增强未启用。
- 已安装副本与主仓库副本的相关文案保持一致。
