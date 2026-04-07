# Install Prompt MCP Auto-Provision Design Requirement

Date: 2026-04-07
Runtime: `vibe`
Mode: `interactive_governed`

## Goal

Design a cross-host installation contract where the install assistant must attempt to provision five MCP surfaces during installation guidance without blocking users from starting VibeSkills if some attempts fail.

## Deliverable

A written design that defines:

- the install-prompt contract
- the shared MCP provision state model
- cross-host execution order for six supported hosts
- verification and reporting expectations
- rollout and risk controls

## Constraints

- Scope covers the current public hosts only: `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, `opencode`.
- The install assistant must attempt these MCP surfaces: `github`, `context7`, `serena`, `scrapling`, `claude-flow`.
- Attempts should prioritize repository-owned install/bootstrap/check flows first.
- `github`, `context7`, and `serena` should prefer host-native registration when available.
- `scrapling` and `claude-flow` should prefer CLI / stdio install paths.
- Failed MCP attempts must not block base install success.
- Failures must be summarized only in the final install report, not as repeated mid-flow interruptions.
- The design must distinguish `installed locally` from MCP readiness and from online-ready governance.

## Acceptance Criteria

- A formal spec is written under `docs/superpowers/specs/`.
- The design defines a unified status model for MCP attempts and verification.
- The design names the document, prompt, bootstrap/install/check, doctor/verify, and reporting surfaces that must change.
- The design includes a phased rollout plan and risk controls.

## Product Acceptance Criteria

- The public contract becomes “must attempt provisioning” rather than “must fully succeed or block installation”.
- The design preserves truthful host-boundary reporting.
- The final user-facing report format is explicit and consistent across hosts.

## Manual Spot Checks

- Verify the spec covers all six supported hosts.
- Verify the spec covers all five MCP surfaces.
- Verify the spec does not collapse MCP failure into overall install failure.

## Completion Language Policy

- Do not claim implementation exists.
- Claim only that the design/spec has been written and locally reviewed.

## Delivery Truth Contract

- Claims must trace to the written spec file and this session’s governed artifacts.

## Non-Goals

- Implementing the design in code in this turn
- Rewriting host capability contracts beyond the specific MCP auto-provision behavior
- Changing online governance credential policy

## Autonomy Mode

Proceed autonomously through design writing and local review, then stop for user review before any implementation planning.

## Inferred Assumptions

- The user wants one consistent install-assistant behavior across all six supported hosts.
- The design should be implementation-ready enough to hand off into a later execution plan.
