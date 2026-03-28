# Vibe Memory Runtime Activation Closure Plan

## Execution Summary
The repository already has the right owner-boundary model for memory. The smallest coherent path is not to widen memory authority. It is to convert the current governance-only memory plane into a stage-aware runtime activation model with strict write admission, retrieval gating, prompt-budget controls, and fallback-safe runtime hooks. The design goal is to keep memory useful, sparse, and auditable.

## Frozen Inputs
- Requirement doc: [2026-03-28-vibe-memory-runtime-activation-closure.md](../requirements/2026-03-28-vibe-memory-runtime-activation-closure.md)
- Current reality:
  - `state_store` is the only reliably active default memory lane
  - `Serena`, `ruflo`, and `Cognee` are mostly defined in governance and protocol surfaces, not yet fully wired into normal `vibe` runtime execution
  - `knowledge-steward` and `deepagent-memory-fold` are real skills, but they are explicit or keyword-triggered rather than systematically stage-bound
  - `memory-runtime-v3` remains `shadow` and `advisory_first_post_route_only`
- Invariants that must stay unchanged:
  - canonical router remains route authority
  - `vibe` remains runtime authority
  - memory stays post-route and subordinate to runtime governance
  - canonical owners remain `state_store`, `Serena`, `ruflo`, and `Cognee`

## Internal Grade Decision
- Grade: XL
- The work spans runtime integration, config contracts, test harnesses, rollout policy, prompt-budget rules, operator documentation, and failure proof.
- The design must coordinate router metadata, runtime stages, retro surfaces, and benchmark evaluation without creating a parallel control plane.

## Design Overview

### Design Principle 1: Memory Must Be Stage-Bound
Memory activation should depend on the runtime stage, not on generic availability.

Required behavior:
- `skeleton_check`: light background recall only
- `deep_interview`: minimum decision recall only
- `requirement_doc`: citeable acceptance-relevant recall only
- `xl_plan`: planning-relevant recall only
- `plan_execute`: bounded milestone and handoff memory only
- `phase_cleanup`: persistence and fold cleanup only

### Design Principle 2: Write Admission Must Be Narrower Than Recall
The system must reject most candidate writes.
Memory quality comes from selective persistence, not from large-volume storage.

Required write shapes:
- `state_store`: run-local progress and artifacts
- `Serena`: explicit approved project decisions only
- `ruflo`: short-horizon milestone cards and handoff cards only
- `Cognee`: entities and relations only
- `knowledge-steward`: explicit user-requested durable capture only
- `deepagent-memory-fold`: structured compaction object only

### Design Principle 3: Retrieval Must Be Budgeted
Memory should return cards, not transcripts.
Every recall lane requires:
- trigger condition
- top-k cap
- token budget
- replacement vs append semantics

### Design Principle 4: Fallback Must Preserve Continuity
Backend outages must not break `vibe`.
The runtime must degrade to:
- `state_store`
- local session artifacts
- requirement/plan/handoff outputs

### Design Principle 5: Intelligence Must Be Proven, Not Assumed
A memory lane is intelligent only if it:
- reduces repeated clarification or lost context
- improves handoff continuity
- avoids irrelevant recall
- stays within prompt budget

## Target Architecture

### A. Stage-Aware Memory Trigger Matrix
Add one canonical trigger matrix document and config contract that maps memory actions to `vibe` stages.

Expected stage actions:

#### `skeleton_check`
- Read:
  - `Serena` decision digest: allowed
  - `Cognee` small relationship digest: allowed
- Write: none
- Budget:
  - max 3 decision cards
  - max 1 graph digest block
- Failure behavior:
  - fallback to local docs and `state_store`

#### `deep_interview`
- Read:
  - `Serena` only if the same project already has approved conventions
- Write: none
- Budget:
  - max 2 decision cards
- Goal:
  - avoid re-asking settled project conventions

#### `requirement_doc`
- Read:
  - only citeable constraints and approved decisions
- Write:
  - candidate decisions staged locally, not yet persisted to `Serena`
- Budget:
  - max 3 cited memory anchors

#### `xl_plan`
- Read:
  - `Serena` decision digest
  - bounded `Cognee` relationship digest for cross-module dependencies
- Write:
  - none to long-term stores
  - optional local `state_store` planning memo

#### `plan_execute`
- `M`:
  - use `state_store` only
- `L`:
  - use `state_store`; no default `ruflo`
- `XL`:
  - optional `ruflo` milestone cards
  - optional `ruflo` handoff summaries
  - no raw transcript storage
- Specialist lanes:
  - child lanes receive only root-approved handoff digests

#### `phase_cleanup`
- Write:
  - `Serena`: only approved decisions
  - `Cognee`: only approved entities/relations
  - `deepagent-memory-fold`: only when context-pressure or handoff criteria were met
  - `knowledge-steward`: only on explicit user request
- Read:
  - none unless required for retro comparison

### B. Write Admission Contracts
Add explicit config or reference contracts for:
- `serena-write-admission.json`
- `ruflo-card-contract.json`
- `cognee-entity-relation-contract.json`
- `memory-fold-trigger-policy.json`

Each contract must define:
- allowed payload classes
- forbidden payload classes
- required metadata
- retention policy
- rollback behavior

### C. Retrieval Budget Contracts
Add one canonical budget contract, for example:
- `config/memory-retrieval-budget-policy.json`

Minimum fields:
- stage
- lane
- `top_k`
- `max_tokens`
- `replacement_mode`
- `inject_as`
- `fallback_mode`

Required semantics:
- recall injects compact cards or digests only
- full raw stored content stays out of prompt context
- folded memory replaces old context instead of appending

### D. Runtime Integration Hooks
Add bounded runtime hook points inside the existing stage implementation:

- `Invoke-SkeletonCheck`:
  - optional pre-run recall receipts
- `Write-RequirementDoc`:
  - citeable memory anchors only
- `Write-XlPlan`:
  - bounded dependency recall only
- `Invoke-PlanExecute`:
  - XL milestone/handoff store and search
- `Invoke-PhaseCleanup`:
  - durable persistence receipts
  - optional fold receipt

Every hook must emit:
- attempted lane
- action type
- success/fallback
- payload count
- token budget used

### E. Intelligence Guardrails
Introduce runtime guardrails that block low-quality memory usage:
- no memory read if stage is out of scope
- no memory write if payload lacks required type metadata
- no recall when relevance score is below threshold
- no injection if budget would be exceeded
- no fold append on top of full historical context

### F. Proof Surface
Add one memory activation report family under:
- `outputs/runtime/vibe-sessions/<run-id>/memory-activation.json`
- `outputs/runtime/vibe-sessions/<run-id>/memory-activation.md`

Minimum fields:
- stage actions taken
- reads attempted and succeeded
- writes attempted and succeeded
- fallback events
- token budget consumption
- ignored or denied writes
- retrieval relevance scores
- fold trigger reason

## Wave Plan

### Wave 1: Freeze Stage-Aware Memory Contract
- Write stable governance doc for stage-aware activation
- Add trigger matrix and owner-boundary restatement
- Add explicit non-goals against transcript dumping and authority transfer

### Wave 2: Add Write Admission Contracts
- Add lane-specific write contracts
- Define candidate-to-approved decision flow for `Serena`
- Define XL milestone card schema for `ruflo`
- Define entity-relation ingest schema for `Cognee`

### Wave 3: Add Retrieval Budget Policy
- Add a canonical top-k and token-budget policy
- Define replacement vs append behavior
- Define per-stage allowable recall lanes

### Wave 4: Wire Runtime Hooks
- Add read hooks to `skeleton_check`, `deep_interview`, `xl_plan`
- Add write hooks to `plan_execute` and `phase_cleanup`
- Emit per-stage memory receipts

### Wave 5: Add Context-Pressure Compaction
- Define fold trigger conditions
- Add a bounded call path for `deepagent-memory-fold`
- Guarantee fold artifact replaces historical context in continuation flows

### Wave 6: Add Scenario Corpus
Create scenarios for:
- no-backend baseline
- Serena-only decision reuse
- XL milestone continuity with `ruflo`
- long-term relationship reuse with `Cognee`
- context-pressure fold continuation
- missing-backend fallback
- low-relevance recall rejection
- write-admission rejection

### Wave 7: Add Gates And Benchmarks
- runtime activation gate
- retrieval budget gate
- fold replacement gate
- fallback integrity gate
- repeated-run flake gate

### Wave 8: Release Truth And Operator Docs
- add operator runbook
- add release-facing truth gate for memory claims
- forbid README language that overstates automatic persistence or recall beyond tested reality

## Detailed Test Program

### 1. Owner Boundary Tests
- `state_store` stays session-only
- `Serena` does not accept raw transcripts
- `ruflo` does not become long-term store
- `Cognee` does not ingest arbitrary transcript blocks
- `mem0` and `Letta` do not gain canonical owner status

### 2. Stage Trigger Tests
- each stage invokes only permitted lanes
- out-of-scope stages do not read or write memory
- write actions are deferred until approved persistence points

### 3. Retrieval Quality Tests
- high-relevance cards are recalled
- low-relevance cards are rejected
- no more than configured top-k are injected
- token budget never exceeds policy cap

### 4. Fallback Tests
- missing Serena backend falls back to local docs and `state_store`
- missing `ruflo` keeps XL execution viable
- missing `Cognee` does not break startup
- fold unavailable degrades to local handoff artifacts

### 5. Compaction Tests
- fold triggers only at allowed conditions
- fold artifact includes working/tool/evidence/decision/resume sections
- fold replaces large historical context rather than appending to it

### 6. Continuity Tests
- repeated clarification rate decreases when approved decisions exist
- XL handoff retains blocker/next-step continuity
- resumed session can continue from folded memory with bounded context

### 7. Anti-Explosion Tests
- transcript-size write attempts are rejected
- oversized recall is truncated or denied
- duplicate recalls are deduplicated before injection
- cumulative memory injection stays under a global stage budget

### 8. Operator Usability Tests
- activation report is readable and actionable
- denied-write reasons are explicit
- fallback status is operator-visible
- release wording aligns with actual tested capability

## Proof Strategy

### Stability Proof
- repeated-run matrix for each scenario
- flake accounting for repeated recall and fallback behavior
- failure injection for missing backends and denied writes

Target proof:
- memory activation does not destabilize the runtime
- stage actions remain deterministic enough to audit

### Availability Proof
- no-backend baseline still succeeds using `state_store`
- partial-backend availability produces bounded degraded behavior
- runtime artifacts remain sufficient for continuation without external memory services

### Intelligence Proof
- compare runs with and without bounded memory recall
- measure:
  - repeated clarification count
  - handoff completeness
  - irrelevant recall count
  - budget overrun count
  - route drift count

Target proof:
- recall is relevant more often than noisy
- useful continuity improves without widening authority or prompt size

## Rollback Rules
- Any owner-boundary violation:
  - disable the offending lane
  - revert to `shadow`
- Any repeated irrelevant recall or budget overrun:
  - reduce top-k and token caps
  - disable the stage hook if needed
- Any runtime instability:
  - fall back to `state_store` plus local artifacts only

## Success Criteria
This plan succeeds when the repository can prove all of the following at once:

- memory activation is stage-aware rather than always-on
- each lane preserves its intended role
- memory recall is bounded and relevance-aware
- context compaction reduces context size instead of increasing it
- external backend failures do not break `vibe`
- repository documentation and release wording match the tested runtime truth
