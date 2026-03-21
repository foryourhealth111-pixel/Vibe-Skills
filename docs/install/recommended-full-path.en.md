# Install Path: Advanced Host / Lane Reference

> Most users should start with the two main install paths:
> - [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
> - [`manual-copy-install.en.md`](./manual-copy-install.en.md)

This path is now an **advanced reference for host and lane truth**.

Its goal is not "pretend everything is fully ready". Its goal is:

- close the repo-governed surfaces as completely as possible
- run the deep doctor and coherence checks
- expose the remaining host-managed gaps honestly

In other words, this path optimizes for a **truthful, stable, low-surprise first real setup**.

## Who This Path Is For

- heavy AI users who want a stable working VibeSkills setup
- team leads who want to evaluate the governed surface before broader rollout
- users who want more than a minimum smoke test, but do not want enterprise rollout overhead yet

## What This Path Promises

This path aims to close the surfaces that the repository actually owns:

- shipped runtime payload
- bundled mirrors
- selected active MCP profile
- deep doctor / runtime coherence path
- repo-side governance assets and verification entrypoints

In the current rollout, that also means the standard full lane distinguishes three separate default surfaces:

- `scrapling`: default local runtime surface for the full profile
- `Cognee`: default long-term enhancement owner for governed graph memory
- `Composio / Activepieces`: predeclared external action surfaces that are visible by default but still setup-required

## What This Path Does Not Promise

This path does **not** honestly promise:

- automatic host plugin installation
- automatic MCP registration in the host platform
- automatic provider secret provisioning
- automatic enablement of external write-capable control planes
- magical parity across all hosts and all platforms

If those are still missing, `manual_actions_pending` is the correct result.

## Platform Truth

- Windows is still the strongest authoritative reference path.
- Linux can approach the authoritative path only when `pwsh` is available and the PowerShell gate surface can run.
- Linux without `pwsh` is still supported, but it is a degraded path, not full parity.
- Claude Code remains `preview`.
- Generic hosts remain advisory / contract-consumer territory unless separately proven.

## Recommended Commands

### Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

### Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

## What "Done" Looks Like

For the standard recommended install, "done" means:

- bootstrap succeeded
- deep doctor succeeded
- repo-governed surfaces are closed
- remaining host-managed gaps are clearly listed

Concretely:

- `scrapling` should either be callable or be reported as a direct missing default full-profile surface
- `Cognee` should appear as the declared long-term enhancement lane, not as a second session-memory owner
- `Composio / Activepieces` should appear as prewired setup-required surfaces, not as fake core-install failures

Possible truthful end states:

- `fully_ready`
- `manual_actions_pending`

The state that should block adoption is:

- `core_install_incomplete`

## How To Enhance After The Standard Recommended Install

Do not add everything at once. A safer order is:

1. add provider secrets
   Start with the keys required for the workflows you actually use.
2. verify the default local runtime lane
   In practice, confirm that `scrapling` is callable if you want the out-of-box scraping surface from the full profile.
3. keep the memory lane clean
   Treat `Cognee` as the governed long-term graph-memory owner only. Do not let it replace `state_store`.
4. add recommended host plugins
   Prioritize `superpowers` and `hookify`.
5. add plugin-backed MCP surfaces
   For example `github`, `context7`, and `serena`.
6. wire external action integrations only when you truly need them
   `Composio` and `Activepieces` stay predeclared, confirm-gated, and setup-required by design.
7. only add the remaining host plugins when doctor still points to a concrete gap
   For example `everything-claude-code`, `claude-code-settings`, and `ralph-loop`.
8. add optional CLI enhancements
   For example `claude-flow`, `xan`, and `ivy`.

## When You Should Escalate To The Enterprise-Governed Path

Move beyond the standard recommended path when you need:

- repeatable audited rollout
- fixed release/version evidence
- ownership for host-managed provisioning
- rollback-ready install governance

See:

- [`enterprise-governed-path.md`](./enterprise-governed-path.md)
- [`host-plugin-policy.en.md`](./host-plugin-policy.en.md)
- [`../cold-start-install-paths.en.md`](../cold-start-install-paths.en.md)
