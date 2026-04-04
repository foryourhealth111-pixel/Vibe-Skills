# Document Plane Benchmark Governance

## Purpose

Wave72 用 golden corpus + benchmark 统一 Docling、markitdown、pdf/docx 路由证据。
目标不是追求单工具垄断，而是形成可比较、可回退、可审计的 benchmark corpus。

## Golden Corpus

golden corpus 至少覆盖：
- born-digital PDF
- scanned PDF / OCR-heavy PDF
- docx with comments / formatting
- mixed tables / images / multi-page provenance cases
- extensionless OOXML / ZIP-carried Office attachments
- table-structure sensitive cases（merged cells / OCR-cell interaction / warnings preservation）

## Benchmark Rules

每个 case 必须记录：
- preferred tool
- fallback tool
- required fields
- degraded tolerance
- failure trigger
- whether MIME recovery is expected before normalization
