# Host Plugin Install Policy

This document answers a practical question:

which host plugins should be installed by default for `vco-skills-codex`, which should stay deferred, and which should only be added after a real gap is observed.

The short answer:

- the repo must not pretend it can auto-install every `manual-codex` plugin
- first-time operators should not install all host plugins up front
- the stable default is: close the repo-governed surfaces first, run doctor, then provision host plugins one by one based on real gaps

## Boundary First

The following plugins are currently marked as `manual-codex` in `config/plugins-manifest.codex.json`:

- `superpowers`
- `everything-claude-code`
- `claude-code-settings`
- `hookify`
- `ralph-loop`

That means:

- the repo can report whether these surfaces are still missing
- the repo can ship compatibility layers, mirrors, or fallbacks around them
- the repo cannot honestly claim that one shell command has installed them for you

So this document is not a fake automation recipe.
It is a default install policy.

## Recommended Default Policy

### Layer 1: first-time install should not require all five

For a first install of VibeSkills, do **not** treat all five host plugins as mandatory up-front.

Run:

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux / macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

If the result lands in `manual_actions_pending`, that is acceptable and truthful.

### Layer 2: for the Windows / Codex reference lane, install these first

If your goal is not just "make it run", but "get close to the author/reference environment", install these first:

- `superpowers`
- `hookify`

Why:

- `superpowers` is closer to workflow gating and development entry behavior
- `hookify` is closer to host-level hook execution and hook governance

These two give the highest value with the lowest ambiguity.

### Layer 3: keep these deferred unless a real gap remains

Do **not** install these by default on first setup:

- `everything-claude-code`
- `claude-code-settings`
- `ralph-loop`

Not because they have no value, but because:

- parts of their functional surface have already been absorbed, mirrored, or compatibility-wrapped by the repo
- they are more likely to overlap with existing fallbacks or host-local configuration
- without a concrete missing capability, they add more conflict surface than value

## Decision Table

| Plugin | Default policy | Install it when | Why not install it on day one |
| --- | --- | --- | --- |
| `superpowers` | recommended | when you want the reference Codex workflow | high value, manageable overlap |
| `hookify` | recommended | when you need host-level hook orchestration | high value, but avoid multiple hook stacks |
| `everything-claude-code` | deferred by default | when you still need its upstream-native behavior | easier to overlap with repo-absorbed capability |
| `claude-code-settings` | deferred by default | when you explicitly want its settings layer as host authority | can overlap with existing settings and fallbacks |
| `ralph-loop` | deferred by default | when you explicitly need upstream Ralph loop behavior/backend | baseline compatibility already exists in-repo |

## Suggested Install Paths

### Path A: default path for ordinary users

Use this when:

- this is your first time with VibeSkills
- you want the lowest-conflict, easiest-to-debug setup
- you accept `manual_actions_pending`

Do this:

1. install none of the five host plugins by default
2. run one-shot + deep doctor
3. only provision a plugin when doctor reports a real missing surface and you actually need that capability

### Path B: Windows / Codex reference path

Use this when:

- you are a heavy user
- you want to get close to the current reference lane

Do this:

1. install `superpowers`
2. install `hookify`
3. rerun deep doctor
4. only add `everything-claude-code`, `claude-code-settings`, or `ralph-loop` if the remaining gap clearly points to them

### Path C: gap-driven provisioning

Use this when:

- the repo already runs
- you do not want extra overlap
- you only want to fill one specific missing capability

Do this:

1. record the missing surface from doctor
2. provision only the plugin directly tied to that gap
3. rerun doctor after each plugin
4. do not install everything "for completeness"

## How To Install These Plugins

This needs to stay truthful:

**the repo does not currently provide one unified shell command to install these five `manual-codex` plugins.**

The correct flow is:

1. open your Codex host plugin / MCP / integration management surface
2. provision or enable the plugin by name
3. confirm it is actually enabled on the host, not just copied somewhere on disk
4. rerun deep doctor from the repo

So the accurate instruction is:

- `superpowers`, `everything-claude-code`, `claude-code-settings`, `hookify`, and `ralph-loop`
  must be provisioned via **Codex-native plugin / MCP tooling**
- this repo is responsible for:
  - exposing the gap
  - shipping compatibility/fallback surfaces
  - reporting the remaining manual steps in doctor output

## Scriptable Optional Enhancements

These are not part of the five host plugins above, but can be installed when needed:

### `claude-flow`

```bash
npm install -g claude-flow
```

### `xan` (recommended on Windows)

```powershell
scoop install xan
```

### `ivy`

```bash
pip install ivy
```

These are optional enhancements, not first-day prerequisites.

## Conflict Avoidance Rules

To avoid the "more installed, more chaos" trap:

1. add one host plugin at a time, then rerun doctor immediately
2. do not enable multiple overlapping hook, settings, or router stacks without a clear ownership model
3. do not mistake a hand-assembled local machine for a portable default policy
4. if the repo already ships a mirror or fallback for a capability, validate that first before adding the upstream host plugin

## Final Recommendation

If I had to set the default policy for a new operator, I would choose:

- do not require all five host plugins on first install
- recommend first: `superpowers`, `hookify`
- defer by default: `everything-claude-code`, `claude-code-settings`, `ralph-loop`
- keep the rest of MCP, CLI, and provider secrets strictly demand-driven

The goal is not to look maximally full.
The goal is:

- fewer conflicts
- clearer ownership
- easier debugging
- no dishonest claims about automation boundaries
