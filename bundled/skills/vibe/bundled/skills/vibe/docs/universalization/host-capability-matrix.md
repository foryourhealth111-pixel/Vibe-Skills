# Host Capability Matrix

> Scope: execution contract for universalization, not marketing language.

## Purpose

This matrix freezes the difference between:

- official runtime ownership
- preview scaffold support
- runtime-core-only neutral lanes
- advisory-only contract consumption

It prevents the project from collapsing all hosts into a fake "one runtime fits all" story.

## Status Vocabulary

| Status | Meaning |
| --- | --- |
| `supported-with-constraints` | repo has real host evidence and a bounded support claim, but some surfaces remain host-managed |
| `preview` | adapter contract exists and scaffold/check proof exists, but full host closure is still incomplete |
| `not-yet-proven` | host is named in the migration target, but there is no verified host-native runtime contract yet |
| `advisory-only` | host may consume canonical contracts or runtime-core payload, but the repo makes no host closure claim |

## Host Matrix

| Host | Status | Runtime Role | Settings Contract | Plugin/MCP Contract | Release Closure | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Codex | `supported-with-constraints` | official-runtime-adapter | repo template + materialization exist | host-managed but documented | strongest current path | current reference lane |
| Claude Code | `preview` | host-adapter-preview | repo scaffold exists | mostly host-managed | preview-scaffold | install/check can scaffold and verify preview truth |
| Cursor | `preview` | host-adapter-preview | preview guidance only | mostly host-managed | preview-scaffold | shared entrypoints exist, but host-native closure is not claimed |
| Windsurf | `preview` | official-runtime-adapter | runtime-core host-root install/check exists | host-managed beyond runtime-core payload | runtime-core-preview | documented host root with shared runtime-core payload only |
| OpenClaw | `preview` | official-runtime-adapter | runtime-core host-root install/check exists | host-managed beyond runtime-core payload | runtime-core-preview | attach / copy / bundle are supported, but host-native closure is not claimed |
| OpenCode | `not-yet-proven` | future-host-adapter | neutral runtime-core only | none yet | runtime-core-only | no host-native closure yet |
| Generic Host | `advisory-only` | contract-consumer | neutral runtime-core only | host-defined | runtime-core-only | canonical skill truth can be consumed without host promise |

## Capability Guidance

### Codex

- Strongest current evidence for settings, install, health-check, and governed runtime payload.
- Still depends on host-managed plugin provisioning and credential provisioning.

### Claude Code

- The repo can now scaffold preview settings + hooks and run preview health checks.
- This is still not a full Claude Code closure claim.

### Cursor

- The repo can expose preview guidance and truthful check surfaces through the shared install/check entrypoints.
- Cursor-native settings, plugin enablement, MCP registration, and provider credentials remain host-managed.

### Windsurf

- The repo can install and verify a shared runtime-core payload into `WINDSURF_HOME` or `~/.codeium/windsurf`.
- Supported wording is locked to `preview` with `runtime-core-preview` closure, not host-native closure.
- Attach / copy / bundle are valid delivery paths, but login, provider access, plugin provisioning, and native settings surfaces remain host-managed.

### OpenClaw

- The repo can install and verify a shared runtime-core payload into `OPENCLAW_HOME` or `~/.openclaw`.
- Supported wording is locked to `preview` with `runtime-core-preview` closure, not host-native closure.
- Attach / copy / bundle are valid delivery paths, but login, provider access, plugin provisioning, and native settings surfaces remain host-managed.

### OpenCode

- The repo can only install neutral runtime-core payload into a non-host target root.
- Host-native settings, plugin, and MCP semantics remain unproven.

### Generic Host

- Useful when the user wants canonical skills and runtime-core only.
- Must never be described as an official runtime or a host-native closure lane.

## Promotion Rule

No adapter may be promoted above its current status unless all of the following exist:

1. host profile
2. settings map
3. platform contracts
4. replay-backed verification
5. install isolation proof
6. wording parity between docs and measured support
