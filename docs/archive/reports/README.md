# Historical Reports

`docs/archive/reports/` 保存已退出 `docs/` 根导航面的历史 batch、audit、rollout 与 recheck 报告。

这些文件保留审计和追溯价值，但不再承担当前 install、runtime、release、status 或 verify 的 live truth。

## Archived Report Families

- migration and cleanup reports
- routing / keyword / rollout audits
- one-off recheck or batch-closure reports

## Rules

- 这类历史报告默认只从 archive 进入，不再回堆到 `docs/` 根层。
- 如果某份报告重新成为当前 contract 或 live operator 入口，必须显式恢复到 live surface，而不是继续停留在 archive。
