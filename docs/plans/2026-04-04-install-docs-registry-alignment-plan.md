# Install Docs Registry Alignment Plan

## Internal Grade

`L` - serial documentation correction with focused verification.

## Objective

Bring the public install documentation into line with the current registry/CLI-driven install architecture without changing runtime behavior.

## Wave Structure

### Wave 1: Freeze and Inspect

- confirm the active branch and current release baseline
- confirm the install-mode source of truth in [`config/adapter-registry.json`](../../config/adapter-registry.json)
- inspect root README, install index pages, one-shot docs, cold-start docs, command references, and public install prompts

### Wave 2: Correct Public Entry Surfaces

- update [`README.md`](../../README.md) and [`README.zh.md`](../../README.zh.md)
- update [`docs/README.md`](../README.md)
- update [`docs/install/README.md`](./README.md) and [`docs/install/README.en.md`](./README.en.md)
- update [`docs/one-shot-setup.md`](../one-shot-setup.md)
- update [`docs/cold-start-install-paths.md`](../cold-start-install-paths.md) and [`docs/cold-start-install-paths.en.md`](../cold-start-install-paths.en.md)
- update [`docs/install/recommended-full-path.md`](./recommended-full-path.md) and [`docs/install/recommended-full-path.en.md`](./recommended-full-path.en.md)
- update [`docs/install/one-click-install-release-copy.md`](./one-click-install-release-copy.md) and [`docs/install/one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)

### Wave 3: Correct Public Prompt Surfaces

- update install/update prompts so `opencode` is described as a thin direct path with an available registry-driven one-shot wrapper, rather than as one-shot-unsupported
- keep prompt wording aligned with the current host-mode truth

### Wave 4: Verify

- run `git diff --check`
- run targeted `rg` checks to make sure stale wording is gone from the corrected public surfaces
- inspect diffs for consistency before reporting completion

## Ownership Boundaries

- This wave is documentation-only.
- No install, bootstrap, or check script behavior should change.

## Verification Commands

```bash
git diff --check
```

```bash
rg -n "只覆盖 `codex` 和 `claude-code`|only covers `codex` and `claude-code`|use direct install/check instead of one-shot bootstrap|direct install/check，不走 one-shot bootstrap" README.md README.zh.md docs docs/install
```

## Completion Rules

- Report completion as a documentation-alignment pass, not as a runtime behavior change.
- Keep claims tied to the live branch state and the current adapter registry.
