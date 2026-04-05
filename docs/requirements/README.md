# Governed Requirements

This directory stores only the frozen requirement documents that still need to stay tracked in-repo.

Historical per-run packets are no longer kept here by default once they stop carrying an active contract role.

Rules:

- one requirement document per governed run
- execution plans must trace back to the requirement document, not raw chat history
- benchmark mode must record inferred assumptions explicitly
- execution should not widen scope without updating the frozen requirement

Filename contract:

- `YYYY-MM-DD-<topic>.md`

Primary policy:

- `config/requirement-doc-policy.json`

## Current Entry

- [`2026-04-05-github-visible-docs-worklog-purge.md`](./2026-04-05-github-visible-docs-worklog-purge.md): 冻结本轮“移除 GitHub 可见 docs 工作日志面”的治理范围、保留边界和验收标准。

## Contract-Retained Baselines

- [`2026-03-28-root-child-vibe-hierarchy-governance.md`](./2026-03-28-root-child-vibe-hierarchy-governance.md): 仍被层级治理 gate 直接消费。

## Reading Boundary

- 当前 governed run 先看本节 `Current Entry`。
- 仅当 verify 或 runtime contract 仍直接消费某份需求文档时，该文档才继续留在本目录。
- 其余历史需求包默认依赖 git history 恢复，而不是继续占据 GitHub 可见 docs surface。
