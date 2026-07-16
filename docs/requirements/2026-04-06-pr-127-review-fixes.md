# PR 127 Review Fixes Requirements

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

## Goal

Address the remaining verified review defects in PR `#127` so governed skill promotion respects policy, destructive prompts catch Windows-style paths, contract completeness rejects blank entries, and the regression tests remain isolated from shared repo state.

## Scope

- Fix specialist dispatch approval so only `auto_dispatch` recommendations can become `approved_dispatch`.
- Extend destructive prompt detection to explicit Windows and backslash-relative paths.
- Treat whitespace-only `required_inputs` and `expected_outputs` entries as missing.
- Remove in-place mutation of shared `config/skill-promotion-policy.json` from regression tests.

## Non-Goals

- Do not change the router placeholder contract model unless a new failing test proves a real behavior gap.
- Do not redesign specialist promotion states beyond the minimum needed to enforce current policy.

## Acceptance Criteria

1. A recommendation with `recommended_promotion_action = 'surface_only'` stays out of `approved_dispatch` even in root scope.
2. A destructive prompt like `delete C:\tmp\build` is classified as destructive by the governed promotion helpers used by the router.
3. Contract completeness rejects arrays that contain only blank or whitespace strings.
4. The invalid skill-promotion-policy regression test runs against isolated copied config state rather than editing the shared repo file in place.
5. Updated regression tests fail before the production fixes and pass after the fixes.

## Verification

- Run focused Python regression tests for router metadata, freeze contract behavior, and destructive runtime gating.
- If focused tests pass, run the broader runtime-neutral subset that exercises the touched files.
