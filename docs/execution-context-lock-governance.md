# Execution Context Lock Governance

## Purpose

Wave125 hardens execution-context behavior so governance scripts always operate from the canonical repo tree, then mirror outward intentionally.

## Core Rule

- the canonical repo tree is the only authoritative write root;
- mirror targets are synchronized from canonical, never edited as independent sources;
- report_only modes may describe drift, but they do not change ownership;
- the operator surface must enforce execution context before writing.

## Covered Operator Surface

- `scripts/governance/sync-bundled-vibe.ps1`
- `scripts/governance/release-cut.ps1`
- `scripts/common/vibe-wave-gate-runner.ps1`
- `scripts/common/vibe-governance-helpers.ps1`

## Required Behavior

1. resolve execution from canonical first;
2. record canonical target id and sync source target id explicitly;
3. keep mirror targets visible for parity and freshness gates;
4. separate report_only telemetry from apply-mode mutation.
