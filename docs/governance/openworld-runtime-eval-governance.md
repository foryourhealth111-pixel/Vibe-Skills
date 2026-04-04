# Openworld Runtime Evaluation Governance

## Purpose

Wave85 evaluates openworld runtime candidates such as `browser-use` and `Agent-S` with replayable, confirm-aware scenarios.
The harness exists to compare candidate surfaces against existing BrowserOps and DesktopOps governance without widening authority.

## Governance Scope

- The openworld harness is an evaluation surface, not a provider selector and not a desktop execution owner.
- Scenario evidence must align with `browserops-provider-policy.json`, `desktopops-replay-governance.md`, and the unified cross-plane task contract.
- All openworld scenarios must keep explicit `confirm_required` posture and stable replay handles.

## Required Invariants

- `takeover_forbidden = true` for all openworld candidates.
- `browser-use` and `Agent-S` stay candidate-only until scorecard, replay, rollback, and operator evidence agree.
- The harness cannot silently change provider priority or bypass operator confirmation.
- Evaluation scenarios must reference rollback plans and evidence refs, not transient screenshots alone.
- `browser-use` eval traces must distinguish `search_page` text lookup from `find_elements` structural probing.
- The harness must not assume `read_long_content`; bounded extraction or explicit fallback evidence is required instead.
- Prompt continuity and gateway/auth drift are recorded as provider-preview evidence, not as ownership changes.

## Non-Goals

- No browser or desktop candidate may become a second orchestrator.
- No live-site rollout logic is introduced in the harness.

Validation is performed by `scripts/verify/vibe-openworld-runtime-eval-gate.ps1`.
