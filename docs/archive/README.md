# Archive

`docs/archive/` 保存仍需要保留在仓库中的历史材料索引。

仓库不再默认长期追踪全部历史叶子文件。
当前策略是保留 archive 入口、必要索引，以及少量仍有 repo 内消费者的保留件；更深的历史叶子主要通过 git history 恢复，而不是继续占据 live repo surface。

## Start Here

- [`releases/README.md`](./releases/README.md): 已归档的旧版 release notes
- [`status/README.md`](./status/README.md): 历史状态日志的最小归档契约；默认依赖 git history 恢复，不再长期跟踪整批叶子文件
- [`config/README.md`](./config/README.md): 已退出 live `config/` 根层的历史治理板与 wave boards
- [`root-docs/README.md`](./root-docs/README.md): 已退出 `docs/` 根导航面的历史专题、backlog、旧矩阵与专题 playbook
- [`reports/README.md`](./reports/README.md): 已退出 live root 的历史 batch / audit / rollout reports

## Rules

- 历史材料默认从本目录进入，不再回堆到 live README 首页。
- archive 保留 recoverability，不保留 active ownership。
- 当某类 archive 叶子文件已经零消费者且只剩历史追溯价值时，允许直接依赖 git history，而不是继续长期跟踪整批 leaf 文件。
- 对 machine-readable 历史快照，默认优先保留极少数仍被 archive 交叉引用的文件，其余直接依赖 git history。
- 如果某个历史文件重新成为当前 contract 入口，必须明确恢复到 live 目录，而不是继续从 archive 充当当前真相。
