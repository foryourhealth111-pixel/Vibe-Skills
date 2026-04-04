# Specialist Dispatch Governance

This document defines how specialist skills are used inside the governed `vibe` runtime without becoming a second runtime owner.

## Mental Model

- router finds candidate specialists
- root `vibe` freezes approved specialist dispatch
- child `vibe` executes bounded lanes
- specialists contribute native expertise

Short form:

`router suggests, root vibe approves, child vibe executes, specialists assist`

## Why This Exists

Without a governed dispatch model, specialist skills tend to fail in one of two ways:

- they stay unused even when obviously relevant
- they are called loosely and start conflicting with runtime governance

The fix is not “call more skills”.
The fix is phase-bound specialist dispatch.

## The Four Layers

### 1. Governance Layer

Owned by `vibe`.

This layer controls:

- requirement freeze
- plan freeze
- global dispatch approval
- verification
- cleanup
- final completion authority

### 2. Routing Layer

Owned by the canonical router.

This layer only suggests candidate specialists.
It does not grant execution rights.

### 3. Dispatch Layer

Owned by root `vibe`.

This layer turns suggestions into executable specialist contracts with:

- `binding_profile`
- `dispatch_phase`
- `execution_priority`
- `lane_policy`
- `parallelizable_in_root_xl`
- `write_scope`
- `review_mode`

### 4. Execution Layer

Owned by bounded lanes under `vibe`.

This layer runs the specialist using its native workflow while staying subordinate to the frozen requirement and plan.

## Phase-Bound Specialist Model

Each approved specialist belongs to one governed phase:

- `pre_execution`: planning or setup support
- `in_execution`: implementation or analysis support
- `post_execution`: deliverable or reporting support
- `verification`: review or audit support

This prevents specialist calls from appearing randomly at the end of a task.

## L / XL Behavior

### `L`

- specialist units are explicit serial steps
- no blanket fan-out
- specialist help is visible in order and remains easy to audit

### `XL`

- waves remain sequential by dependency
- specialist units may become bounded parallel lanes only when:
  - root approved them
  - the runtime is in `XL`
  - write scopes do not conflict
  - the specialist lane policy allows bounded parallel execution

If those conditions are not met, specialist units fall back to serial execution.

## Root / Child Authority

Root `vibe` may:

- freeze canonical requirement truth
- freeze canonical plan truth
- approve global specialist dispatch
- issue final completion claims

Child `vibe` may:

- inherit frozen requirement and plan context
- execute bounded approved specialist lanes
- surface new specialist suggestions as advisory requests

Child `vibe` may not:

- create a second canonical requirement surface
- create a second canonical plan surface
- self-approve new global specialist dispatch
- make the root task’s final completion claim

## Local Suggestion vs Approved Dispatch

### Approved Dispatch

Already approved by root and safe to execute.

### Local Suggestion

Detected by a child lane during work.
It stays advisory until one of two things happens:

- root explicitly approves it
- the same-round root auto-absorb gate accepts it

If it has no approved overlap and the gate cannot absorb it, it remains escalation-only.

## Conflict Prevention

The runtime prevents specialist conflicts with five rules:

1. one runtime owner
2. one canonical requirement truth
3. one canonical plan truth
4. write-scope-aware bounded parallelism only
5. explicit degraded or escalation surfaces instead of silent fallback

## What Proof Must Show

To claim this model works, runtime evidence must show:

- which specialists were recommended
- which specialists were approved
- which phase each specialist was bound to
- whether each specialist ran serially, in bounded parallel, or degraded
- whether child suggestions were auto-absorbed or escalated
- that root completion authority stayed single-owner

## Operator Rule

When a specialist is relevant, make it visible, bounded, and phase-bound.
Do not let it become invisible background magic.
Do not let it become a second governor.
