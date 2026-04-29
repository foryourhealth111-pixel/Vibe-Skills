# Overlay Reference Index

- References root: [`../index.md`](../index.md)
- Docs root: [`../../docs/README.md`](../../docs/README.md)

## What Lives Here

`references/overlays/` 存放按 provider / role / external method 分层的参考资料。它们不是 routing source-of-truth，而是供 docs / scripts / skill distillation / operator decision 复用的 reference packs。

## Overlay Packs

| Folder | Focus |
| --- | --- |
| [`agency`](agency) | agency-style role overlays |
| [`gitnexus`](gitnexus) | GitNexus reasoning / impact / architecture references |
| [`ruc-nlpir`](ruc-nlpir) | FlashRAG / WebThinker tool overlay references |
| [`turix-cua`](turix-cua) | BrowserOps / CUA foundations and runbooks |

## Rule

- overlay pack 应只存长期可复用参考，不存一次性执行日志；
- 新增 overlay pack 时，至少在本 index 与 `references/index.md` 两处补入口。
