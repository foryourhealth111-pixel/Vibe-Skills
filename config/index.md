# Config Index

`config/` 保存会被脚本直接消费的 machine-readable contracts。规则说明在 `docs/`，这里放的是执行事实。

## Start Here

| File | Purpose |
| --- | --- |
| [`pack-manifest.json`](pack-manifest.json) | pack routing 主入口 |
| [`router-thresholds.json`](router-thresholds.json) | routing threshold / confidence contract |
| [`skill-alias-map.json`](skill-alias-map.json) | 旧 skill 名兼容映射 |
| [`version-governance.json`](version-governance.json) | canonical-only packaging 与 generated compatibility contract |
| [`repo-cleanliness-policy.json`](repo-cleanliness-policy.json) | repo cleanliness 分类规则 |
| [`outputs-boundary-policy.json`](outputs-boundary-policy.json) | `outputs/**` 与 fixtures 边界 |
| [`official-runtime-main-chain-policy.json`](official-runtime-main-chain-policy.json) | official runtime 主链冻结规则 |
| [`promotion-board.json`](promotion-board.json) | capability promotion board |
| [`bundled-skill-tier-policy.json`](bundled-skill-tier-policy.json) | bundled payload tiering precondition for later slimming |

## Families

- Routing core: `pack-manifest.json`, `router-thresholds.json`, `skill-alias-map.json`
- Runtime / packaging: `version-governance.json`, `frontmatter-integrity-policy.json`, `execution-context-status.json`, `bundled-skill-tier-policy.json`
- Cleanliness / outputs: `repo-cleanliness-policy.json`, `outputs-boundary-policy.json`
- Boards / lifecycle: `promotion-board.json`, `capability-catalog.json`
- Upstream / distribution: `upstream-lock.json`, `upstream-corpus-manifest.json`, `distribution-tiers.json`

## Reading Order

1. 先看 [`version-governance.json`](version-governance.json)、[`repo-cleanliness-policy.json`](repo-cleanliness-policy.json)、[`outputs-boundary-policy.json`](outputs-boundary-policy.json)。
2. 再看 [`pack-manifest.json`](pack-manifest.json)、[`router-thresholds.json`](router-thresholds.json)、[`skill-alias-map.json`](skill-alias-map.json)。
3. 需要 rollout / admission 时再进入 boards。
4. 历史 wave boards / scorecards / archived governance-board snapshots 进入 [`../docs/archive/config/README.md`](../docs/archive/config/README.md)。

## Rules

- 新增 config 时更新本页，并补至少一条 docs 或 scripts 锚点。
- 不把 receipt、telemetry 或 dashboard 数据写进 `config/`。
- packaging / install / release contract 改动后必须复跑对应 gates。
