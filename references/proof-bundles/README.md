# Proof Bundles

`references/proof-bundles/` 只保留仍被 adapters、tests、replay 或 verify gates 直接消费的 machine-readable bundle。

最小 live proof surface 默认只保留：

- manifest
- operation record
- contract-required receipts

bundle README 不是默认保留项。只有当它承载 manifest 或 operation record 无法替代的 live guidance 时才继续存在。

没有活跃消费者的 duplicated verify outputs、command audit copies、receipt inventories，以及仅供人工回放的 raw shell logs，不应继续占据 live proof surface。

## Live Bundles

- `linux-full-authoritative-candidate`
- `claude-code-managed-closure-candidate`
- `openclaw-runtime-core-preview-candidate`

## Archive

- 已从 live contract 退下来的低信号补充件默认通过 git history 恢复，而不是长期保留在仓库可见面。
- 只有当某个历史 proof family 重新具备稳定检索价值时，才应重新建立专门 archive surface。

## Rule

- 没有 manifest、没有活跃消费者、且只承担历史说明作用的 proof bundle 不应继续留在 live surface。
- 对已经缩减为 manifest + operation record + receipt 的 live bundle，额外 raw logs 或重复说明叶子默认通过 git history 恢复，而不是继续长期跟踪。
