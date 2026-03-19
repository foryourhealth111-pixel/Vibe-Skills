# Document Safety Remediation Proof Plan

## Purpose

This proof plan defines how the document-safety remediation is judged before stronger cleanup claims are allowed.

## Proof Families

### Stability

Prove that:

- protected documents are detected under mixed and ambiguous naming sets,
- protected assets outside tmp are retained,
- tmp-root protected assets are quarantined instead of destroyed,
- the cleanup path remains deterministic under preview runs.

Primary command:

```powershell
pwsh -File .\scripts\verify\vibe-document-asset-safety-gate.ps1 -Mode Stability -WriteArtifacts
```

### Usability

Prove that:

- preview manifests expose meaningful counts,
- retained protected assets remain visible in receipts,
- quarantine decisions remain understandable from artifacts and docs.

Primary command:

```powershell
pwsh -File .\scripts\verify\vibe-document-asset-safety-gate.ps1 -Mode Usability -WriteArtifacts
```

### Intelligence

Prove that:

- protected document classification stays document-only,
- non-protected tmp files are not quarantined as protected,
- runtime-boundary docs keep advisory layers subordinate to canonical control-plane owners.

Primary commands:

```powershell
pwsh -File .\scripts\verify\vibe-document-asset-safety-gate.ps1 -Mode Intelligence -WriteArtifacts
pwsh -File .\scripts\verify\vibe-runtime-boundary-gate.ps1 -WriteArtifacts
```

### Release-Truth Consistency

Prove that:

- claims in governance docs do not exceed the actual proof bundle,
- VCO still presents one router and one governed runtime truth.

Primary command:

```powershell
pwsh -File .\scripts\verify\vibe-release-truth-consistency-gate.ps1
```

## Exit Rule

The remediation is not promotable until all proof families above are green or explicitly classified as bounded and not-yet-promoted.
