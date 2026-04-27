---
name: deslop
description: Remove AI-generated code slop from a branch: unnecessary comments, redundant defensive checks, boilerplate, style drift, and type casts. Use for cleanup of AI-written code, not for broad code review, security audit, TDD, or final verification.
---

# Remove AI Code Slop

Check the diff against main and remove all AI-generated slop introduced in this branch.

## Routing Boundary

Use this skill when the user's problem is cleanup of AI-generated code noise. If the user asks for a broad correctness/maintainability review, use `code-reviewer`. If the user asks whether existing review comments should be accepted, use `receiving-code-review`.

## What to Remove

- Extra comments that a human wouldn't add or are inconsistent with the rest of the file
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted/validated codepaths)
- Casts to `any` to get around type issues
- Inline imports in Python (move to top of file with other imports)
- Any other style that is inconsistent with the file

## Process

1. Get the diff against main: `git diff main...HEAD`
2. Review each changed file for slop patterns
3. Remove identified slop while preserving legitimate changes
4. Report a 1-3 sentence summary of what was changed
