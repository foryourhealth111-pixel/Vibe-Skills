# Frontmatter & UTF-8 BOM Governance

## Why This Exists

`SKILL.md` 不是普通 Markdown；它是运行态入口文件。对这类文件来说，YAML frontmatter 是否从**字节 0**开始，是加载能否成功的边界条件。

如果文件前面被写入 UTF-8 BOM（十六进制 `EF BB BF`），很多解析器在字节 0 看不到真正的 `---`，会把文件判定为“缺少 YAML frontmatter”。

## Stop-Ship Rule

以下任一情况都视为 stop-ship：

- frontmatter-sensitive 文件带有 UTF-8 BOM；
- 文件首行文本虽为 `---`，但字节 0 并不是 `0x2D`；
- canonical / installed 两类必备副本中任一 `SKILL.md` 违反 byte-0 frontmatter 约束；
- install/runtime 兼容生成路径若被 materialize，其 `SKILL.md` 同样必须满足 byte-0 frontmatter 约束；缺失本身不构成失败。

## Protected Files

- canonical root: `SKILL.md`
- installed runtime root: `${TARGET_ROOT}/skills/vibe/SKILL.md`
- installed/runtime generated compatibility root (if materialized): `${TARGET_ROOT}/skills/vibe/bundled/skills/vibe/SKILL.md`

## Authoring Rule

PowerShell 写入 frontmatter-sensitive 文件时，必须使用 UTF-8 no-BOM：

- `Write-VgoUtf8NoBomText`
- `Append-VgoUtf8NoBomText`
- 或 `[System.Text.UTF8Encoding]::new($false)`

不要依赖不同 PowerShell 版本对 `-Encoding UTF8` 的历史行为。

## Repository-wide Text Rule

根 `.gitattributes` 是仓库级的 line-ending contract：`*.md`, `*.json`, `*.jsonl`, `*.yml`, `*.yaml`, `*.ps1`, `*.sh` 等治理文本统一按 LF 管理。

这条规则与 UTF-8 no-BOM 是互补关系：

- `.gitattributes` 负责让 canonical / installed，以及任何被 materialize 的兼容副本的文本换行保持稳定；
- no-BOM 负责让 frontmatter-sensitive 文件在 byte 0 直接可见 `---`。

不要把 `core.autocrlf` 当作 parser safety contract。
## Relationship to Runtime Freshness

BOM/frontmatter integrity 不是 freshness 的替代，而是 freshness 的前置条件：

- freshness 证明“副本与 canonical 一致”；
- BOM gate 证明“一致的内容仍然可被解析器正确加载”。

两者必须同时成立，运行态才真正健康。
