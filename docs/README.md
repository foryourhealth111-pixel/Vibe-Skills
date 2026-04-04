# VCO 文档索引

`docs/` 只负责长期说明、当前状态入口和执行计划导航，不承担运行时真相本身。

## Start Here

- [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)：面向普通用户的唯一公开安装入口
- [`install/README.md`](./install/README.md)：安装索引；说明公开入口、宿主模式与补充文档之间的关系
- [`cold-start-install-paths.md`](./cold-start-install-paths.md)：当前六个公开宿主的冷启动路径与 truth-first 边界

| 你要做什么 | 入口 |
| --- | --- |
| 安装或试用 | [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md) |
| 看懂宿主模式和命令参考 | [`install/README.md`](./install/README.md) |
| 判断自己该走哪条冷启动路径 | [`cold-start-install-paths.md`](./cold-start-install-paths.md) |
| 查看当前状态 | [`status/README.md`](./status/README.md) |
| 跟踪当前执行计划 | [`plans/README.md`](./plans/README.md) |
| 理解变更规则 | [`developer-change-governance.md`](./developer-change-governance.md) |
| 理解系统结构 | [`architecture.md`](./architecture.md) |

## Current Runtime

- 主技能合同：[`../SKILL.md`](../SKILL.md)
- 运行时协议：[`../protocols/runtime.md`](../protocols/runtime.md)
- 多代理协议：[`../protocols/team.md`](../protocols/team.md)
- 当前 live summary：[`status/current-state.md`](./status/current-state.md)
- 最小 proof contract：[`status/non-regression-proof-bundle.md`](./status/non-regression-proof-bundle.md)

## Governance

- 文档结构规则：[`docs-information-architecture.md`](./docs-information-architecture.md)
- 打包与兼容拓扑：[`version-packaging-governance.md`](./version-packaging-governance.md)
- 清洁度规则：[`repo-cleanliness-governance.md`](./repo-cleanliness-governance.md)
- 安装一致性 SOP：[`runtime-freshness-install-sop.md`](./runtime-freshness-install-sop.md)
- 可观测性规则：[`observability-consistency-governance.md`](./observability-consistency-governance.md)

## Cross-Layer Handoff

- 机器可读配置：[`../config/index.md`](../config/index.md)
- 脚本入口：[`../scripts/README.md`](../scripts/README.md)
- 长期 reference：[`../references/index.md`](../references/index.md)
- release 记录：[`releases/README.md`](./releases/README.md)

## Rules

- 根目录 `docs/*.md` 只放长期文档，不把 dated plans 或 batch reports 升格为长期合同。
- 安装口径以 [`install/README.md`](./install/README.md)、[`cold-start-install-paths.md`](./cold-start-install-paths.md) 与 [`../config/adapter-registry.json`](../config/adapter-registry.json) 对齐，不在多个入口页手写互相冲突的宿主模式说明。
- 当前状态以 [`status/current-state.md`](./status/current-state.md) 和 `outputs/verify/**` 为准，不在索引页手工维护状态表。
- 新增长期入口时更新本页；dated 材料只更新对应子目录 `README.md`。
