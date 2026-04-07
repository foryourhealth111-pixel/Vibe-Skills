# PR133 Rabbit Review Fixes Execution Plan

## Internal Grade

`M` — local governed execution because the scope is a two-file test repair with direct verification.

## Waves

### Wave 1

- freeze requirement and plan artifacts
- add minimal regression checks that expose the two loose predicates
- run the targeted tests and confirm the new checks fail under the current implementation

### Wave 2

- implement the smallest test-helper refactor needed to satisfy the new regression checks
- replace permissive inline boolean shortcuts with explicit helper-backed assertions

### Wave 3

- run the targeted verification suite
- inspect the final diff for scope drift
- commit and push the repair to PR #133

## Ownership Boundaries

- tests:
  - `tests/integration/test_native_mcp_first_install_docs.py`
  - `tests/runtime_neutral/test_install_prompt_mcp_contract.py`
- governance artifacts:
  - this requirement doc
  - this execution plan

## Verification Commands

```bash
pytest -q tests/integration/test_native_mcp_first_install_docs.py tests/runtime_neutral/test_install_prompt_mcp_contract.py
pytest -q tests/runtime_neutral/test_install_prompt_mcp_contract.py tests/integration/test_native_mcp_first_install_docs.py tests/integration/test_codex_install_prompt_discoverability.py tests/integration/test_multi_host_real_host_root_docs.py
```

## Delivery Acceptance Plan

- accept only if the first command demonstrates red-green on the tightened test logic
- accept only if the second command proves the broader targeted docs-contract suite still passes
- accept only if the branch update is pushed to the existing PR branch

## Completion Language Rules

- do not say the review findings are fixed until verification passes and the push succeeds

## Rollback Rules

- if the new regression checks do not fail for the expected reason, adjust the tests before implementation
- if verification fails after the fix, stop and repair the failing test logic before any push

## Phase Cleanup Expectations

- leave behind only the requirement/plan artifacts, the minimal test fixes, verification evidence, and the resulting commit metadata
