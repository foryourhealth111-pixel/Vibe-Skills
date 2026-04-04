# Docling Upstream Delta 2026-03-16

Date: 2026-03-16
Reviewed upstream range: `752f81b3dd451208fb59297ea5ef7917cb4fc891..6238aa35d00a86aa3812d7930ee34a0626cf8ee8`
Upstream repo: `docling-project/docling`

## Packet Purpose

This memo records the first governed intake decision for the current `docling` upstream delta.

The goal is not to mirror upstream behavior wholesale.
The goal is to keep the VCO document-plane contract accurate where upstream changes materially affect what VCO can admit, normalize, benchmark, and classify.

## Reviewed Delta Classes

### 1. Contract-relevant

- Extensionless Office/OpenXML inputs can now be recovered from generic ZIP carriers by local container inspection.

This is contract-relevant because VCO previously allowed `docx` / `pptx` / `xlsx` but did not explicitly document the bounded case where the file arrives without a usable extension.

### 2. Benchmark and failure-taxonomy relevant

- Table structure changes now include additional prediction and validation logic, plus a V2 path.
- OCR behavior changed in engine-level ONNXRuntime threading/configuration.
- Ground-truth fixtures were broadly refreshed upstream.

These changes are evidence that benchmark expectations and failure classes should explicitly track MIME-detection gaps and table-structure regressions.
They are not sufficient grounds to change the VCO control plane.

### 3. Deferred runtime/provider changes

- VLLM CUDA graph mode and related runtime/provider options.
- KServe transport and other inference-runtime details.
- General backend or packaging evolution that does not change the VCO contract surface.

These remain upstream implementation details for now.
VCO does not absorb them into document-plane governance in this packet.

## Admissible Intake

This packet admits exactly three things:

1. The input contract now explicitly allows extensionless OOXML/ZIP artifacts when local container inspection can positively recover the concrete Office MIME.
2. The benchmark corpus now requires a dedicated extensionless OOXML case and stronger table-sensitive cases.
3. The failure taxonomy now tracks `mime_detection_gap` and `table_structure_regression`.

## Deferred Intake

The following items are deferred to later benchmark or provider packets:

- any quality re-baselining for table extraction
- any OCR engine preference or tuning rule
- any provider/runtime option exposure
- any change to default runtime enablement

## No-Go Restatement

- `docling` does not become a second document orchestrator.
- MIME recovery does not authorize remote URL probing or crawl behavior.
- Upstream runtime knobs do not become VCO governance knobs merely because they exist upstream.
- Benchmark drift does not rewrite the document-plane owner.

## Canonical Effect

After this packet:

- the VCO document-plane contract is more accurate about bounded OOXML intake;
- the benchmark surface is stricter about input normalization and table regressions;
- the failure taxonomy is better aligned to the reviewed upstream delta;
- the provider policy remains unchanged.
