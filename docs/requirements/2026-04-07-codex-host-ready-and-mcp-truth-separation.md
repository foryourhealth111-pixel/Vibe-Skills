# Codex Host-Ready And MCP Truth Separation

## Goal

Make the install/check flow tell the truth about two independent outcomes:

- whether `codex` can actually discover and run `$vibe` from the real host root
- whether each required MCP surface is actually installed and visible in the host's active surface

The installer must stop conflating local payload installation, CLI presence on PATH, and real host readiness.

## Deliverable

- A revised install/check truth model that reports `vibe host-ready` separately from per-MCP readiness.
- Codex-specific host-active-surface verification proving whether `$vibe` is actually live in `~/.codex`.
- Updated receipts, final reporting, and verification surfaces that never describe MCP as installed merely because a CLI exists on PATH.
- Regression tests covering the new reporting contract and Codex host-ready validation.

## Constraints

- Do not revert or overwrite unrelated in-progress work.
- Preserve the current public host list and current profile mapping behavior.
- Do not require all MCP surfaces to succeed before allowing a truthful "`$vibe` host-ready" success result.
- Do not claim host-native MCP registration exists when the installer only has a template, placeholder, or follow-up hint.
- Keep `codex` anchored to the real host root `~/.codex` unless the operator explicitly chooses isolation.

## Acceptance Criteria

- Install completion output is split into at least these surfaces:
  - `installed locally`
  - `vibe host-ready`
  - `mcp auto-provision attempted`
  - per-MCP readiness
  - `online-ready`
- For `codex`, `vibe host-ready=true` is only allowed when host-visible active surfaces agree that the governed runtime is materially discoverable from the real host root.
- For `codex`, host-ready validation must check the real host surfaces rather than only payload parity or receipt presence.
- Scripted MCP entries such as `scrapling` and `claude-flow` are not reported as host-ready merely because their commands exist on PATH; the reported state must reflect host visibility/registration semantics.
- Host-native MCP entries such as `github`, `context7`, and `serena` must remain clearly reported as pending when the installer cannot complete real host registration.
- `check` and doctor-style verification surfaces must reuse the same truth model rather than silently translating states back to generic `ready`.
- Targeted tests fail before the implementation change and pass after it.

## Product Acceptance Criteria

- A user who sees "本体安装完成" can trust that `$vibe` is actually discoverable and usable from the current Codex host.
- A user who sees an MCP listed as ready can trust that it is actually visible through the host's active surface, not merely present as a local executable.
- A user can still get a successful base installation when `$vibe` is host-ready but some MCP surfaces remain pending.

## Manual Spot Checks

- Inspect the real Codex host root under `~/.codex` and identify which files constitute the active runtime surface for `$vibe`.
- Inspect the real Codex MCP active surface and compare it against receipt states for `github`, `context7`, `serena`, `scrapling`, and `claude-flow`.
- Confirm the final install report wording distinguishes base runtime success from MCP follow-up.
- Confirm `check` and doctor output preserve the same distinction.

## Completion Language Policy

- Do not use "安装完成" as a single undifferentiated claim.
- Do not use "MCP ready" unless the state is backed by the host-visible active surface.
- Report residual manual follow-up separately from verified host-ready runtime status.

## Delivery Truth Contract

- Report the exact files used to compute `vibe host-ready`.
- Report the exact files or probes used to compute each MCP readiness state.
- Report the exact targeted test commands used to verify the new contract.
- If any status remains approximate or advisory, label it directly.

## Non-Goals

- Implementing full host-native registration for every MCP provider.
- Redesigning unrelated install flows for hosts that do not share the same contradiction.
- Blocking base installation on every pending MCP surface.

## Autonomy Mode

- Single-session governed execution with targeted verification.

## Inferred Assumptions

- The user wants the installer's success language fixed at the code and receipt layer, not only in assistant-facing prompts.
- The current `codex` success criterion is "`$vibe` can be directly discovered from the real host root".
- MCP truthfulness should be improved across shared reporting surfaces even if the immediate pain was observed in `codex`.
