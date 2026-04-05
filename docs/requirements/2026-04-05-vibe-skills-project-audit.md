# Vibe-Skills Project Audit Requirement

Date: 2026-04-05
Run ID: 20260405-vibe-skills-audit
Mode: interactive_governed
Runtime lane: root_governed

## Goal

Inspect the `Vibe-Skills` project and identify concrete project problems with evidence from the repository and executable checks.

## Deliverable

A review report that:

- lists verified problems ordered by severity
- cites repository files and, where available, test or runtime evidence
- distinguishes observed defects from architectural risks
- avoids claiming fixes were made when the task is only inspection

## Constraints

- Work against the local repository at `/home/lqf/table/table9/Vibe-Skills-main`
- Use the user-provided GitHub project only as identity confirmation unless local state is insufficient
- Do not rewrite or "clean up" unrelated code
- Prefer reproducible evidence: tests, command output, direct source inspection

## Acceptance Criteria

- At least one core execution path is inspected
- At least one verification command is run
- Findings are tied to concrete files or commands
- Uncertainties are labeled as assumptions or residual risk

## Product Acceptance Criteria

- The report is useful to a maintainer deciding what to fix next
- Findings emphasize correctness, contract drift, broken governance, missing validation, or delivery risk
- Findings are prioritized instead of presented as an undifferentiated list

## Manual Spot Checks

- Repository root, branch, and remote match the requested project
- `README.md` and CLI/runtime entrypoints are consistent with actual implementation
- A representative verification command completes and its result is captured

## Completion Language Policy

- Do not claim the project is "good", "fixed", or "passing" without evidence
- If tests are partial, say so explicitly
- If a problem is inferred rather than executed, mark it as an inference

## Delivery Truth Contract

- Review-only engagement
- No success wording about remediation
- Evidence before assertions

## Non-Goals

- Implementing fixes
- Exhaustive review of all 300+ skills
- Release readiness certification

## Autonomy Mode

interactive_governed with inferred assumptions

## Inferred Assumptions

- The local checkout is the relevant review target for the GitHub project
- "审视这个项目的问题" means a maintainership-style audit rather than feature work
- A scoped but evidence-backed review is more useful than a superficial repo tour
