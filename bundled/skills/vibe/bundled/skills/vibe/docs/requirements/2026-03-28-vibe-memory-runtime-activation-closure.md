# Vibe Memory Runtime Activation Closure

## Summary
Close the gap between the repository's memory-governance claims and the actual `vibe` runtime behavior. The current repository already defines strong owner boundaries for `state_store`, `Serena`, `ruflo`, `Cognee`, `mem0`, and `Letta`, but most of those roles still operate as post-route governance guidance rather than as stage-bound runtime behavior with bounded write, retrieval, and injection contracts.

## Goal
Design and land a memory-runtime architecture where each canonical memory role is invoked only at the right stage, with bounded payload size, audited write admission, intelligent retrieval gates, and explicit rollback rules, so memory becomes useful without becoming a second control plane or a context-amplification source.

## Deliverable
A repository change program and documentation bundle that adds:

- a stage-aware activation model for `state_store`, `Serena`, `ruflo`, `Cognee`, `knowledge-steward`, and `deepagent-memory-fold`
- machine-readable write-admission and retrieval-budget contracts for each memory lane
- runtime integration points for memory read/write/fold actions inside the existing six-stage `vibe` lifecycle
- scenario tests and executable gates proving stability, usability, and intelligence
- operator documentation describing when memory is invoked, when it must stay silent, and how to disable or roll back each lane

## Constraints
- Preserve `VCO` as the single runtime and control plane owner.
- Preserve the canonical router as route authority.
- Do not create a second visible startup surface, second requirement surface, or second execution-plan surface.
- Do not allow any memory lane to mutate `selected.pack_id`, `selected.skill`, or grade choice.
- Preserve the current canonical owner matrix:
  - `state_store` for session truth
  - `Serena` for explicit project decisions
  - `ruflo` for short-term semantic cache
  - `Cognee` for long-term relationship memory
- Keep `episodic-memory` disabled in governed routing.
- Keep `mem0` preference-only and `Letta` contract-only.
- Prefer additive runtime hooks and bounded artifacts over a broad router/runtime rewrite.

## Acceptance Criteria
- The repository defines a stage-aware memory trigger matrix covering:
  - `skeleton_check`
  - `deep_interview`
  - `requirement_doc`
  - `xl_plan`
  - `plan_execute`
  - `phase_cleanup`
- Every memory lane has an explicit write-admission contract:
  - what can be written
  - what must not be written
  - required evidence shape
  - retention or expiry rule
- Every retrievable memory lane has an explicit retrieval contract:
  - allowed trigger conditions
  - maximum item count
  - maximum prompt-injection budget
  - fallback behavior when the backend is unavailable
- `state_store` remains the default always-on runtime memory lane.
- `Serena` is only written when the runtime has an explicit project decision surface or explicit operator approval.
- `ruflo` is only used for bounded XL milestone summaries, handoff blocks, or short-horizon semantic retrieval, never as a generic long transcript store.
- `Cognee` is only used for bounded graph retrieval or long-term ingest at approved persistence points, never as a raw transcript sink.
- `knowledge-steward` remains explicit-user-trigger only and is not silently promoted into a background auto-capture path.
- `deepagent-memory-fold` becomes a governed compaction lane that can be invoked only under documented context-pressure or handoff conditions, and its folded artifact replaces large historical context instead of being appended to it.
- The repository includes a bounded memory injection policy proving that memory recall cannot expand prompt context without limit.
- The repository includes executable tests proving:
  - stability across repeated runs
  - availability and graceful fallback when memory backends are missing
  - intelligence of retrieval choice and budgeted injection

## Primary Objective
Make memory in `vibe` useful enough to preserve continuity and decision quality, while keeping it sufficiently bounded that it cannot destabilize routing, runtime truth, or prompt size.

## Proxy Signals
- Memory recall reduces repeated clarification or lost context without increasing route drift.
- Memory writes are sparse, typed, and evidence-backed rather than transcript-dump based.
- Retrieval returns only the minimum relevant cards required for the current stage.
- Missing memory backends degrade gracefully to `state_store` and local artifacts.

## Scope
In scope:
- stage-aware memory activation design
- write-admission rules
- retrieval gating rules
- prompt-injection budget design
- context-pressure fold design
- backend fallback semantics
- executable verification and proof strategy
- repository documentation and rollout plan

Out of scope:
- replacing the canonical router
- granting memory lanes route mutation or runtime ownership
- making every memory backend mandatory for every host
- storing full raw conversation transcripts as long-term truth
- turning `knowledge-steward` into implicit background ingestion

## Completion
The work is complete when the repository can prove, with executable tests and bounded runtime contracts, that each memory lane is called at the correct time, injects only bounded information, degrades safely when unavailable, and measurably improves continuity without causing context explosion or governance drift.

## Evidence
- new or updated governance docs for stage-aware memory activation
- requirement and plan docs for rollout
- runtime integration design for read/write/fold hooks
- machine-readable budget and admission policies
- scenario corpus and gates covering stability, availability, and intelligence

## Non-Goals
- Do not treat memory backend availability as proof of useful recall.
- Do not equate more recalled text with better intelligence.
- Do not let long-term memory become a dump of unresolved thoughts or temporary state.
- Do not append folded memory on top of the original large context.
- Do not allow advisory memory suggestions to silently become execution authority.

## Autonomy Mode
interactive_governed

## Assumptions
- The current six-stage `vibe` lifecycle is sufficient to host memory activation without adding a second runtime.
- Existing `state_store` and runtime artifacts already provide a stable baseline fallback.
- The main missing layer is stage-aware runtime activation, not owner-boundary definition.
- The repository can add new config contracts, runtime hooks, and tests without breaking current router invariants.

## Evidence Inputs
- Source task: plan a full activation-closure program for the current memory system
- Current finding: governance, contracts, and gates exist; automatic stage-bound runtime invocation is still partial
- Current policy: `memory-runtime-v3` remains `shadow` and `advisory_first_post_route_only`
