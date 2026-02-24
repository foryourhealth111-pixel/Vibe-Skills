---
name: local-vco-roles
description: Codex-local role pack for dialectic multi-agent reviews, designed to be compatible with the local vibe skill.
---

# local-vco-roles

Codex-local role pack for dialectic multi-agent reviews, designed to be compatible with the local `vibe` skill.

## When to Use

Use this skill when:
1. You run `/vibe` and need a stable role set for dialectic review.
2. You want reproducible multi-role analysis using Codex native team orchestration style.
3. You need standardized outputs across team-lead / bug / architecture / integration / usability roles.

## Vibe Compatibility Contract (Must Follow)

1. Grade handshake:
- M/L: do NOT force XL multi-agent orchestration.
- XL: native team workflow is allowed (`spawn_agent` / `send_input` / `wait` / `close_agent`).

2. Rule-1 boundary:
- Never mix multiple agent systems for the same task.
- Follow `vibe` conflict rules first.

3. Command priority:
- User explicit command > `vibe` routing > this role pack defaults.

4. Output severity:
- Always use `CRITICAL > HIGH > MEDIUM > LOW`.

5. Staged confirmation:
- Keep major confirmation points aligned with `vibe` team protocol.

6. Memory behavior:
- Default state tracking via runtime-neutral state_store-style task state.
- Optional enhancements (if available) must not become hard dependencies.

## Role Prompt Library

- Team lead: `references/role-prompts/team-lead.md`
- Bug analyst: `references/role-prompts/bug-analyst.md`
- Architecture critic: `references/role-prompts/arch-critic.md`
- Integration analyst: `references/role-prompts/integration-analyst.md`
- Usability analyst: `references/role-prompts/usability-analyst.md`

## Recommended XL Workflow

1. Read `references/vibe-compatibility.md`.
2. Create 5 tasks (lead + 4 analysts).
3. Assign each role using the prompt files above.
4. Collect results and aggregate by severity.
5. Produce one merged decision set (`keep / simplify / remove`).

## Optional Utility

- Run scaffold helper: `scripts/new-run.ps1 -Topic <name>`

