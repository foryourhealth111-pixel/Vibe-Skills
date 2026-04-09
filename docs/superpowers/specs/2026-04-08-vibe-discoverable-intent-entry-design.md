# Vibe Discoverable Intent Entry Design

## Summary
Define a discoverable intent-entry layer for `vibe` so users can select guided shortcuts from native host skill menus without introducing a second runtime, a second router, or a `stage x grade` alias explosion.

The design keeps one governed runtime authority, one canonical runtime skill id, one fixed six-stage state machine, and one execution/cleanup contract. What changes is the host-facing presentation layer: hosts may expose a small set of human-readable intent entries that map into canonical `vibe` runtime metadata.

This design also introduces lightweight public grade overrides with `--l` and `--xl`, but those flags remain execution preferences only. They do not create new public runtime branches, they do not skip stages, and they do not justify additional menu entries.

## Problem
The current public `vibe` story is structurally clean but too opaque for new users:

- the governed runtime is exposed as a single public entry
- stage order is fixed and internal
- internal grade selection is automatic
- users must remember how to ask for clarification, planning, or execution depth in freeform language

That leaves two usability gaps:

1. users do not get a visible host-native entry surface for the most common intent modes
2. users who want lighter or heavier execution must rely on wording instead of a stable explicit override

The user's requested direction is to make the public surface more discoverable, but without regressing into:

- `vibe-m` / `vibe-l` / `vibe-xl`
- separate runtime authorities for discuss / plan / execute
- a combinatorial matrix such as `want-xl`, `how-l`, `do-xl`
- anything that makes shortcut labels more authoritative than canonical `vibe`

## Goals
- Add a small host-discoverable intent-entry surface for the governed `vibe` runtime.
- Preserve one runtime authority: `vibe`.
- Keep the six-stage runtime contract unchanged in order and ownership.
- Let shortcuts express default stop intent, not alternate runtime semantics.
- Add explicit lightweight grade overrides through `--l` and `--xl`.
- Make shortcut labels human-readable enough to appear as native host menu entries.
- Keep docs, adapters, CLI bridges, runtime packet contracts, and tests aligned on the same truth model.

## Non-Goals
- This design does not create a second router.
- This design does not create multiple public runtime authorities.
- This design does not expose `M`, `L`, and `XL` as separate public skill entries.
- This design does not permit execution to bypass `deep_interview`, `requirement_doc`, or `xl_plan`.
- This design does not require every host to materialize four separate installed skill directories.
- This design does not redesign specialist dispatch, child governance, or native MCP behavior.

## Scope Boundary
This design applies to:

- shared runtime contract metadata
- runtime input packet metadata
- runtime packet parsing and stop-stage resolution
- host discoverability metadata and adapter presentation
- user-facing docs for `README`, quick start, and `SKILL.md`
- tests that lock the shortcut contract and forbid matrix explosion

This design does not apply to:

- release packaging redesign outside the new metadata files that must be shipped
- a broader rename of `vibe` itself
- unrelated install-path or MCP wording work

## Design Options Considered

### Option A: Stage And Grade Alias Matrix
Expose public aliases for every stage and execution grade combination, such as:

- `vibe-want`
- `vibe-how`
- `vibe-do`
- `vibe-want-xl`
- `vibe-how-l`
- `vibe-do-xl`

Pros:

- very explicit
- no hidden mapping

Cons:

- public surface explodes immediately
- host menus become noisy and fragile
- grade becomes falsely coupled to stage
- users must learn too many labels
- creates pressure toward separate authorities

### Option B: Separate Runtime Authorities For Clarify / Plan / Execute
Expose `vibe-want`, `vibe-how`, and `vibe-do` as effectively separate runtime branches with their own contracts.

Pros:

- easier to describe each entry in isolation
- shortcut names feel first-class

Cons:

- violates the current governed-runtime model
- duplicates authority and truth surfaces
- increases contract drift across docs and hosts
- makes it easier for execution to diverge from frozen requirements

### Option C: One Governed Runtime With Discoverable Intent Shortcuts And Grade Flags
Keep `vibe` as the only runtime authority, and let shortcut entries compile into runtime metadata such as:

- `entry_intent_id`
- `requested_stage_stop`
- `requested_grade_floor`

Pros:

- preserves the existing runtime architecture
- gives users a host-visible menu they do not need to memorize
- keeps grade override orthogonal to stage intent
- prevents alias explosion
- keeps testing and packaging centralized

Cons:

- requires careful wording so visible shortcuts are not mistaken for new authorities
- needs contract updates where `single_user_facing_path` currently implies exactly one visible label

## Decision
Choose **Option C**.

The system should support a discoverable shortcut layer, but only as a presentation and metadata layer around canonical `vibe`.

## Core Contract

### 1. One Runtime Authority Remains Canonical
The governed runtime authority remains:

- canonical runtime skill id: `vibe`
- canonical runtime entrypoint: `scripts/runtime/invoke-vibe-runtime.ps1`
- canonical runtime selected skill: `vibe`

Shortcut entries may be visible to the user, but they must resolve into the same governed runtime authority.

### 2. Public Discoverable Entry Surface
The approved public surface is:

- display name: `Vibe`
  internal id: `vibe`
- display name: `Vibe: What Do I Want?`
  internal id: `vibe-want`
- display name: `Vibe: How Do We Do It?`
  internal id: `vibe-how`
- display name: `Vibe: Do It`
  internal id: `vibe-do`

The display names exist for host discoverability.
The internal ids exist for machine-readable routing and validation.

### 3. Shortcut Semantics Are Stop Targets, Not Alternate Stage Machines
Each shortcut defines a default stop target from the same canonical start:

- `vibe`
  semantics: default governed runtime behavior
  stop target: `phase_cleanup`
- `vibe-want`
  semantics: clarify goals, constraints, success criteria
  stop target: `deep_interview`
- `vibe-how`
  semantics: produce frozen requirement and plan
  stop target: `xl_plan`
- `vibe-do`
  semantics: execute through the full governed flow
  stop target: `phase_cleanup`

Rules:

- every shortcut still starts at `skeleton_check`
- shortcuts do not skip earlier required stages
- stop target means `run until this stage is completed, then return`
- `vibe-do` cannot bypass `deep_interview`, `requirement_doc`, or `xl_plan`

### 4. Grade Flags Stay Lightweight And Orthogonal
The approved public grade overrides are:

- `--l`
- `--xl`

They mean:

- `--l`: request an execution-grade floor of `L`
- `--xl`: request an execution-grade floor of `XL`

They do not mean:

- a new public entrypoint
- a new runtime mode
- permission to skip clarification or planning
- a second router decision

If no public grade flag is provided, runtime grade selection remains automatic.

### 5. Grade Flags Apply Only Where Execution Planning Exists
To keep semantics honest:

- `vibe-how` may record a grade floor into the frozen planning packet because it produces a plan
- `vibe-do` may record and execute a grade floor
- canonical `vibe` may record a grade floor
- `vibe-want` should reject public grade flags because it stops before requirement freeze and plan generation

This keeps `What Do I Want?` focused on intent clarification rather than execution tuning.

### 6. Priority And Conflict Rules
The user may choose:

- zero or one shortcut id
- zero or one grade flag

The system must reject:

- more than one shortcut in the same invocation
- more than one grade flag in the same invocation
- unsupported combinations such as `--l --xl`
- any public alias not in the approved allowlist

Canonical precedence:

1. explicit shortcut selection
2. explicit grade flag
3. canonical runtime authority resolution to `vibe`

Even when a shortcut is explicit, `runtime_selected_skill` must remain `vibe`.

### 7. Display Names Are Presentation Metadata, Not Install Truth
The discoverable labels are host-facing presentation only.

They must not imply:

- separate installed skill roots
- separate requirement surfaces
- separate plan surfaces
- separate release versioning
- separate runtime entry scripts

The installed runtime should remain materially single-authority even if a host renders multiple cards or menu entries.

### 8. Host Discoverability Model
Host adapters may expose the four approved entries through native discoverability surfaces such as:

- skill pickers
- slash-command menus
- quick-action lists
- guided launcher cards

But those entries must be generated from shared metadata, not copied as independent runtime implementations.

Required host behavior:

- every discoverable entry points back to canonical `vibe`
- host-visible label text may vary only cosmetically if the host has formatting constraints
- internal ids and stop targets must remain stable across hosts
- no host may add extra `grade x stage` public entries on its own

### 9. Contract Precision Must Replace The Old Over-Broad Invariant
The existing runtime contract says `single_user_facing_path: true`.

That wording is now too coarse because the user should see multiple discoverable labels while the system still preserves one runtime authority.

The contract should be refined into separate truths:

- `single_runtime_authority: true`
- `discoverable_intent_entries_allowed: true`
- `discoverable_entries_are_presentational: true`
- `grade_alias_matrix_forbidden: true`

The old invariant may be removed or reinterpreted only if tests remain explicit about the new truth model.

### 10. Runtime Packet Extensions
The governed runtime packet should be extended with optional public-entry metadata:

- `entry_intent_id`
- `requested_stage_stop`
- `requested_grade_floor`

These fields should be optional and must preserve current behavior when absent.

They exist to make shortcut intent explicit in:

- runtime receipts
- requirement docs
- plan docs
- execution verification

### 11. Forbidden Expansions
The following outcomes are explicitly forbidden:

- `vibe-m`, `vibe-l`, `vibe-xl`
- `vibe-want-l`, `vibe-want-xl`, `vibe-how-l`, `vibe-do-xl`
- per-host shortcut names that invent new semantics
- a second runtime-selected skill other than `vibe`
- skipping `requirement_doc` or `xl_plan` for `vibe-do`
- redefining shortcut presentation as proof of alternate runtime ownership

## Acceptance Criteria
- Shared contract metadata defines exactly four discoverable entries with stable ids and display names.
- The runtime packet can represent shortcut intent and public grade floor without breaking existing callers.
- The runtime still executes only the canonical six-stage machine.
- `vibe-want` stops after `deep_interview`.
- `vibe-how` stops after `xl_plan`.
- `vibe` and `vibe-do` continue to full governed completion through `phase_cleanup`.
- `--l` and `--xl` are the only public grade flags.
- Multiple grade flags are rejected.
- No tests or docs imply a second runtime authority.
- Host docs present the shortcuts as discoverable entry surfaces, not separate runtimes.

## Rollout Notes
- Start by locking the contract in tests before changing runtime behavior.
- Ship shared metadata before adapter-specific presentation changes so every host consumes the same source of truth.
- Keep backward compatibility for plain `/vibe`, `$vibe`, and `vibe`.
- Do not claim native host discoverability is complete on a host until the adapter contract and docs actually surface it.
