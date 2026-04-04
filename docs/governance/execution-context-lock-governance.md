# Execution Context Lock Governance

## Purpose

Wave125 hardens execution-context behavior so governance scripts always operate from the canonical repo tree and never treat compatibility paths as independent write roots.

## Core Rule

- the canonical repo tree is the only authoritative write root;
- generated compatibility paths are derived from canonical, never edited as independent sources;
- report_only modes may describe drift, but they do not change ownership;
- the operator surface must enforce execution context before writing.

## Covered Operator Surface

- `scripts/governance/release-cut.ps1`
- `scripts/common/vibe-wave-gate-runner.ps1`
- `scripts/common/vibe-governance-helpers.ps1`

## Required Behavior

1. resolve execution from canonical first;
2. record canonical target id and generated-compatibility semantics explicitly;
3. keep canonical-only and installed-runtime checks distinguishable;
4. separate report_only telemetry from apply-mode mutation.
