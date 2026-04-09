# Document Failure Taxonomy Governance

## Purpose

Wave86 captures Docling-aligned document failure modes so degraded outputs can be classified, explained, and routed back to known fallback paths.
The taxonomy strengthens the document plane contract; it does not create a new document parser or a second document runtime.

## Governance Scope

- Failure classes must map back to the Docling output spec, document benchmark evidence, and provider fallback rules.
- Every failure class must identify provenance expectations and a remediation path.
- The taxonomy must preserve the `failure_object` degraded-mode contract rather than inventing a new output envelope.
- MIME-detection gaps and table-structure regressions must be representable without inventing a second fallback envelope.

## Required Invariants

- `failure_object` remains part of the approved degraded modes for the document plane.
- `provenance` and `artifact_bundle` remain required output fields even for degraded or failed runs.
- No failure class may imply a second document orchestrator or a hidden re-router.
- Remediation guidance must preserve fallback-to-shadow semantics for document transforms.
- A failure triggered by extensionless OOXML intake must still point back to bounded local MIME recovery, not remote fetch.

## Non-Goals

- No new OCR vendor or parser is admitted here.
- No benchmark score is rewritten by the taxonomy itself.

Validation is performed by `scripts/verify/vibe-document-failure-taxonomy-gate.ps1`.
