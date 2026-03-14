# One-Click Install Release Copy

Use this page when you want outward-facing install copy for ordinary users.

Current recommended public version: [`v2.3.40`](../releases/v2.3.40.md)

This page is intentionally simpler than the operator docs. It is built for:

- ordinary heavy AI users who want to try VibeSkills quickly
- team leads who want a low-friction "come look, come try, star first" entry
- community posts, release notes, README blocks, and onboarding messages

## One-line release copy

`VibeSkills v2.3.40` is the current recommended public version. It is not another skill list. It is a governed skills substrate that routes, composes, and verifies skills so general-purpose AI can complete tasks more reliably. Try it first, look around first, and star the repo if the direction resonates.

## Short community version

VibeSkills `v2.3.40` is now the recommended public version.

If you are a heavy AI user, this is the easiest place to start:

- one governed install path
- Windows and Linux onboarding
- `scrapling` included in the default full lane
- `Cognee` positioned as the default long-term enhancement lane
- `Composio / Activepieces` predeclared as setup-required external action lanes

This is not "everything magically auto-ready". It is the strongest repo-governed install surface we currently recommend.

Try it first. Look around first. Star first if you want to help build the universal skills substrate.

## Longer release-post version

VibeSkills `v2.3.40` is the current outward-facing recommended version.

The point of this release is not to add more random skills. The point is to make the install surface clearer and more usable for ordinary people:

- the repo-governed full lane is easier to explain
- the current recommended version is explicit
- Windows and Linux both have a visible onboarding path
- the default enhancement lanes are now easier to understand

What you should expect:

- one-shot bootstrap for the repo-owned surface
- a truthful doctor result
- clear disclosure of what is still host-managed

What you should not expect:

- fake "fully ready" claims when host plugins or provider secrets are still missing
- silent auto-provisioning of every external MCP or host plugin

If you want a practical governed AI setup instead of another loose pile of skills, start with `v2.3.40`.

## Copy this to your AI assistant

```text
Please install this repository using the strongest recommended VibeSkills path for the current platform.

Requirements:
1. Detect whether the system is Windows or Linux.
2. If Windows, prefer:
   - `pwsh -File .\scripts\bootstrap\one-shot-setup.ps1`
   - `pwsh -File .\check.ps1 -Profile full -Deep`
   - fall back to Windows PowerShell only if `pwsh` is unavailable
3. If Linux, run:
   - `bash ./scripts/bootstrap/one-shot-setup.sh`
   - `bash ./check.sh --profile full --deep`
   - and explicitly tell me whether `pwsh` is available, because Linux without `pwsh` is degraded-but-supported rather than the strongest full lane
4. Report the final `readiness_state` truthfully.
5. Do not pretend host plugins, external MCP surfaces, or provider secrets were auto-installed.
6. If the result is `manual_actions_pending`, list the remaining manual actions clearly.
7. Follow the current default policy of recommending `superpowers` and `hookify` first, without requiring all five host plugins on day one.
```

## Direct command version

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

## Reality boundary

This is the important line to keep honest in public:

- `v2.3.40` is the current recommended governed install surface
- it closes the repo-owned install lane as far as the repo can own it
- it does not auto-complete every host plugin, provider secret, or external MCP integration

That is why `manual_actions_pending` is a valid outcome for ordinary users. It means the repo-owned closure is mostly done, but host-managed surfaces still need provisioning.

## If users want more after the default path

- add provider secrets such as `OPENAI_API_KEY`
- provision the recommended host plugins, starting with `superpowers` and `hookify`
- then provision plugin-backed MCP surfaces such as `github`, `context7`, and `serena`
- treat `Composio / Activepieces` as optional external action expansions that still require setup and governance

## Related docs

- [`recommended-full-path.en.md`](./recommended-full-path.en.md)
- [`full-featured-install-prompts.en.md`](./full-featured-install-prompts.en.md)
- [`../cold-start-install-paths.en.md`](../cold-start-install-paths.en.md)
- [`../releases/v2.3.40.md`](../releases/v2.3.40.md)
