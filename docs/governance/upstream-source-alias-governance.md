# Upstream Source Alias Governance

## Goal

Wave121 固化 upstream source 的 **canonical slug** 规则，解决 board / ledger / matrix / planning 中混用 GitHub 展示名、目录名大小写、历史别名的问题。

## Canonical Rule

- canonical slug 一律使用 `lower-kebab-case`；
- `config/upstream-source-aliases.json` 是唯一 alias registry；
- board / manifest / ledger / matrix / scorecard / cockpit 只能写 canonical slug；
- 别名只允许出现在 intake、镜像对账、历史文档迁移说明里。

## Current High-Risk Aliases

| Alias | Canonical slug | Why this matters |
|---|---|---|
| `Prompt-Engineering-Guide` | `prompt-engineering-guide` | 历史计划与 board 中混用展示名 |
| `Letta` | `letta` | memory workstream 中常以品牌名出现 |
| `Agent-S` | `agent-s` | desktop shadow 面常直接沿用 GitHub repo 名 |
| `browser_use` | `browser-use` | provider / code / file naming 中可能出现下划线变体 |

## Enforcement

`vibe-upstream-corpus-manifest-gate.ps1` 必须验证：

1. alias registry 存在；
2. manifest entries 使用 canonical slug；
3. value-ops board 的 `source_projects` 不再包含高风险展示名；
4. ledger / matrix 的行名与 manifest slug 集一致。

## Non-Goals

- 不为 alias 建第二套 source identity；
- 不因为历史文档中的展示名而回退 canonical slug；
- 不允许 alias 参与 promotion / owner / runtime decision。
