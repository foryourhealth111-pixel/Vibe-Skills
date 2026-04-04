# Mem0 Browser-Use Upstream Delta 2026-03-16

Date: 2026-03-16
Reviewed upstream range: `mem0 861cbb72897825cc4a51b9586219dfd52a395879..06ee1b588c01786a24c4a468166459d2cf72066b`; `browser-use 5991c7ff8677caace735bddc75cc2ef2d46ae81a..6e2add1c8139b17b01a549eea944687486724fda`
Verified remote HEAD: `mem0 06ee1b588c01786a24c4a468166459d2cf72066b`; `browser-use 6e2add1c8139b17b01a549eea944687486724fda`
Upstream repos: `mem0ai/mem0`, `browser-use/browser-use`

## Packet Purpose

This memo records the governed intake decision for the current support and evaluation delta in `mem0` and `browser-use`.

The goal is not to import two more runtimes.
The goal is to keep the VCO memory lane and BrowserOps/openworld evaluation surfaces accurate where upstream changes materially affect bounded support behavior, admission fidelity, or evaluation evidence.

## Reviewed Delta Classes

### 1. `mem0` support and admission relevant

- OpenAI-compatible embedder configuration gained `baseURL` portability.
- SQLite path handling was tightened upstream, reducing reliance on implicit working-directory assumptions.
- Structured content inside code fences was preserved more faithfully during extraction.

These are admissible because they affect how VCO documents optional backend portability and how preference payload candidates are preserved for audited admission review.

### 2. `mem0` deferred runtime and packaging changes

- TS / packaging evolution.
- OpenClaw or adjacent integration details.
- Any upstream backend expansion that would imply broader ownership.

These remain upstream implementation details for now.
VCO does not widen the memory control plane in this packet.

### 3. `browser-use` operational and evaluation relevant

- Upstream guidance now distinguishes text lookup from structural locator use more clearly.
- Earlier assumptions around `read_long_content` are no longer safe.
- Preview-model and hosted gateway behavior changed enough that prompt continuity and auth drift need explicit evidence handling.

These are admissible because they affect how VCO should write BrowserOps candidate guidance and openworld evaluation evidence, not because they authorize ownership changes.

### 4. `browser-use` deferred provider and hosted-runtime changes

- Hosted gateway configuration and auth wiring.
- Model-provider rollout details.
- Preview transport or packaging convenience changes.

These are recorded only as provider-preview metadata and remain outside VCO route authority.

## Admissible Intake

This packet admits exactly two bounded categories of change.

1. `mem0` support intake:
   - optional backend documentation for OpenAI-compatible `baseURL`
   - explicit SQLite durable-path guidance
   - verbatim preservation of fenced structured payloads during admission review
2. `browser-use` candidate-eval intake:
   - `search_page` for text lookup
   - `find_elements` for structure and attribute inspection
   - no dependency on `read_long_content`
   - prompt continuity and gateway or auth drift recorded as preview evidence only

## Deferred Intake

The following items are deferred to later packets or remain mirror-only:

- any `mem0` promotion beyond optional preference backend
- any `browser-use` promotion beyond provider candidate or openworld eval candidate
- hosted gateway adoption policy
- model transport defaults
- packaging or SDK rollout changes that do not change VCO governance surfaces

## No-Go Restatement

- `mem0` does not become canonical session state, project truth, or route memory.
- `browser-use` does not become a second orchestrator, default browser owner, or route selector.
- Gateway drift does not become control-plane drift.
- Support improvements do not authorize runtime takeover.

## Canonical Effect

After this packet:

- the VCO memory lane is more accurate about optional backend portability and payload preservation;
- the BrowserOps and openworld evaluation surfaces are more accurate about real browser-use task guidance;
- upstream metadata records the reviewed heads for both sources;
- ownership boundaries remain unchanged.
