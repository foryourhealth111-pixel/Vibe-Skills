# Docling Contract v2 Governance

## Purpose

Wave71 把 Docling 从第一代 output spec 升级为 contract v2。
contract v2 的重点是 schema completeness、admission filter、degraded mode、provenance continuity。

## Contract v2 Fields

输出合同必须覆盖：
- content
- pages
- artifact_bundle
- provenance
- degraded_mode
- failure_object
- admission_profile
- template posture

## Admission Filter

document plane 必须保持 artifact-first / read-only-first / isolated-runtime-required。
禁止把 Docling 扩展为 document orchestrator 或 remote crawl owner。

补充边界：
- 允许把无扩展名 OOXML/ZIP 输入作为本地 MIME 恢复问题处理；
- 不允许把这种恢复规则解释成远程 URL 扫描、自动拉取或新的联网输入权。

## Rollback

若 contract v2 不满足最小字段集合，立即退回既有 `references/docling-output-spec.md` 与 markdown/text degraded path。
