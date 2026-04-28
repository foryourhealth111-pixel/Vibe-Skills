# Router Surface

- Scripts root: [`../README.md`](../README.md)
- Config index: [`../../config/index.md`](../../config/index.md)

## What Lives Here

`scripts/router/` 保存 VCO 内部专家推荐面：pack / skill recommendation、legacy compatibility、以及为 specialist recommender 提供的模块化 helper。公开治理入口仍然是 `$vibe` / `/vibe`。

## Current Layout

| Path | Role |
| --- | --- |
| [`resolve-pack-route.ps1`](resolve-pack-route.ps1) | 内部专家推荐入口；产出 pack / skill recommendation、overlay advice 与 confirm-required 信息 |
| [`legacy/`](legacy) | 兼容旧 routing 路径的辅助实现 |
| [`modules/`](modules) | router 可复用模块与分析原语 |

## Rule

- router 目录解释“如何生成专家推荐结果”；公开执行、阶段治理与验证仍分别落到 `SKILL.md`、`protocols/`、`scripts/governance/` 与 `scripts/verify/`。
- 新增 router helper 时，优先补 `modules/` 级文档，而不是把说明塞进单个脚本顶部。
