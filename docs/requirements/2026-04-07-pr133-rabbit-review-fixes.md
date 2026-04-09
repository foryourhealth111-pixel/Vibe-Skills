# PR133 Rabbit Review Fixes

## Goal

Close the substantive CodeRabbit review gaps on PR #133 so the branch enforces the native-MCP-first docs contract with tests that do not allow soft false positives.

## Deliverable

- tighten the new integration test so it requires every promised keyword instead of allowing any one of them
- tighten the runtime-neutral prompt-contract guard so `/vibe` and the `not proof of mcp` disclaimer variant are handled correctly
- keep the fix limited to tests and governed planning artifacts
- update the existing PR branch with the repair

## Constraints

- do not change installer-core or install-doc behavior in this follow-up
- keep the scope to the two confirmed review findings
- do not revert unrelated work on other branches or in other worktrees

## Acceptance Criteria

- the integration test fails if any one of `template`, `manifest`, or `sidecar` disappears from the required English supporting-doc contract
- the supporting-doc guard treats both `$vibe` and `/vibe` as invocation markers and accepts the `not proof of mcp` English disclaimer variant
- targeted verification passes after the fix
- the PR branch is committed and pushed

## Product Acceptance Criteria

- future doc regressions cannot silently remove one of the required MCP non-proof keywords while leaving the tests green
- future supporting docs cannot mention `/vibe` without an MCP disclaimer and still pass the prompt-contract suite

## Manual Spot Checks

- inspect the two modified test files for explicit, readable assertions instead of permissive boolean shortcuts
- inspect the final diff to confirm the repair stays limited to tests plus governed requirement/plan artifacts

## Completion Language Policy

- do not claim the PR is repaired until the targeted verification command passes and the branch is pushed

## Delivery Truth Contract

- report the exact verification commands run
- report the commit SHA and the updated PR number after push

## Non-Goals

- rewrite the underlying install docs again
- address non-blocking CodeRabbit automation warnings unrelated to the two confirmed test issues
- change CI configuration or repository-wide review policy

## Autonomy Mode

- governed M execution: local analysis, local test repair, local verification, local PR update

## Inferred Assumptions

- the user wants the existing PR #133 repaired in place rather than replaced with a new PR
- only the two confirmed test-guard issues need implementation in this turn
