# Connector Sandbox Simulation Governance

## Purpose

Wave93 introduces sandbox simulation rules for connector candidates such as Composio-style actions, Activepieces-derived templates, and MCP-discovered connectors.
The sandbox layer proves confirm discipline, replay capture, and rollback behavior before any connector is discussed as a soft candidate.

## Governance Scope

- Simulations must never become implicit installs, hidden background execution owners, or provider selectors.
- Write-capable simulations must stay sandboxed, replayable, and operator-visible.
- Simulation evidence must line up with connector admission policy, action ledger governance, and connector scorecard rules.

## Required Invariants

- `implicit_auto_install = false` remains fixed.
- `background_execution_owner = false` remains fixed.
- `sandbox_only_before_soft = true` remains fixed for write-capable classes.
- Every scenario must preserve rollback and confirm evidence before any stage increase is proposed.

## Non-Goals

- No connector marketplace or install automation is introduced.
- No connector is allowed to bypass confirmation through simulation results.

Validation is performed by `scripts/verify/vibe-connector-sandbox-simulation-gate.ps1`.
