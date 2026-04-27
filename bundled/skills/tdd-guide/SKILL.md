---
name: tdd-guide
description: Test-first development route for TDD, writing failing tests first, RED -> GREEN -> REFACTOR, and behavior-changing feature/bug/refactor work. Do not use for already-failing test root-cause debugging, test-report packaging, or final completion evidence.
---

# tdd-guide (Codex Compatibility)

Use this skill for all feature work, bug fixes, and refactors that change behavior.

## Routing Boundary

Use this skill when the user wants to build or change behavior through tests:
- TDD / test-driven development
- write failing tests first
- test-first implementation
- RED -> GREEN -> REFACTOR

Do not use it when tests are already failing and the user wants root cause; route that to `systematic-debugging`. Do not use it when the user only wants a test/coverage report; route that to `generating-test-reports`.

## Core Rule

No production code before a failing test.

## Workflow

1. RED
- Write one failing test for one behavior.
- Confirm the failure is expected.

2. GREEN
- Implement the minimal code to pass.
- Re-run tests and keep scope narrow.

3. REFACTOR
- Improve structure/naming without changing behavior.
- Keep all tests green.

4. COVERAGE
- Verify coverage target (recommended >=80% for lines/functions/branches).
- Add missing tests for edge/error paths.

## Minimum Test Set

- Unit: public functions and core logic.
- Integration: API/data/service boundaries.
- E2E: critical user path only when relevant.

## Required Edge Cases

- Null/undefined input
- Empty values
- Invalid types
- Boundary values
- Error paths (network/DB/file)
- Concurrency-sensitive behavior

## Vibe Integration

- Primary coding skill in M-grade flow.
- Compatible fallback target for `everything-claude-code:tdd-guide`.
- For richer TDD patterns, combine with `test-driven-development`.
