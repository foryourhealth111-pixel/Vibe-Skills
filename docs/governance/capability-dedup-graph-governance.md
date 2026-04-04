# Capability Dedup & Ownership Graph Governance

Wave46-51 把“榨取上游项目价值”从静态审计升级为**重复能力聚类 + canonical owner + landing graph**。

## Cluster Rules

- 一个 cluster 只能有一个 canonical owner。
- 上游项目只能贡献 `pattern` / `contract` / `provider-candidate` / `reference` / `quality-bar`。
- 若上游项目会制造第二 orchestrator、第二默认执行 owner 或第二 canonical truth-source，则默认拒绝吸收。

## Required Graph Fields

每个 cluster 至少记录：`cluster_id`、`problem_domain`、`canonical_owner`、`upstream_sources`、`absorbed_value`、`explicit_non_goals`、`routing_impact`、`verification_anchor`。

## Covered Clusters

当前 Wave46-51 至少覆盖：

- memory governance
- browser ops
- desktop ops
- connector admission
- skill / role-pack ecosystem
- prompt / pattern intelligence
