# Shipped-Local Adaptation Upstream Delta 2026-03-17

Date: 2026-03-17
Reviewed sources: `superpowers`, `claude-code-settings`, `spec-kit`, `ralph-claude-code`
Verified upstream heads:

- `superpowers`: `363923f74aa9cd7b470c0aaa73dee629a8bfdc90`
- `claude-code-settings`: `d0c0d2759f8aadfba1b3361b5860024e4a7e68d4`
- `spec-kit`: `b1650f884d48eb57a9b76bfabb0b205b39099799`
- `ralph-claude-code`: `f1298b8af985a401ed67249365c8f18a8b74ef12`

## Packet Purpose

Wave B re-audits the shipped-local / distributed-local surfaces that VCO already adapts locally.
The goal is to refresh compatibility and host-policy truth without silently yielding authority back to upstream.

## Per-Source Decision Classes

### `superpowers`

Recent upstream drift is meaningful in two places:

- subagent context isolation,
- owner-aware cleanup / process exit behavior.

These improve the justification for VCO's current recommend-first posture and strengthen local guidance around delegation hygiene.
They do **not** justify handing workflow authority back to upstream.

Decision class: `admit`
Admission scope: `compatibility-and-policy-refresh-only`

### `claude-code-settings`

Recent upstream drift is mainly config / skills refinement.
That is real, but the risky question is not whether the plugin improved. The risky question is whether VCO should restore settings-layer host authority to it.
Current evidence says no.

Decision class: `defer`
Admission scope: `no-host-authority-widening`

### `spec-kit`

Recent upstream drift includes new command and extension surfaces, including `specify status` and community catalog changes.
VCO can benefit from the methodology signal, but not by turning spec-kit into a second command authority.
The correct posture remains: compatibility bridge only.

Decision class: `admit`
Admission scope: `compatibility-and-methodology-refresh-only`

### `ralph-claude-code`

Recent upstream drift focuses on loop stability: stale exit signals, productive timeout handling, and quota exhaustion detection.
This is useful operational evidence for the optional open backend, but does not justify changing VCO's baseline away from the in-repo `compat` engine.

Decision class: `metadata-only`
Admission scope: `optional-open-backend-posture-only`

## Canonical Effect

After this packet:

- shipped-local metadata records the reviewed heads and explicit decisions,
- host-plugin `required` semantics align with the published host-plugin policy,
- `superpowers` and `hookify` remain the recommend-first host surfaces,
- `claude-code-settings` and `ralph-loop` remain deferred by default,
- `spec-kit` remains methodology/reference input plus `spec-kit-vibe-compat`, not a second command plane.

## Not Admitted

This packet does not admit:

- a second router,
- a second settings authority,
- a second loop owner,
- full upstream prompt-pack vendoring,
- local runtime propagation before Wave B verification.
