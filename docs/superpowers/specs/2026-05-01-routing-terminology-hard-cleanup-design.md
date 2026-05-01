# Routing Terminology Hard Cleanup Design

Date: 2026-05-01

## Goal

Apply a high-intensity but safe cleanup to routing terminology, retired fields,
historical documentation, tests, and verification gates without degrading the
current Vibe runtime.

The current routing model remains:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused
```

This cleanup is the "C-Safe" path: remove more historical routing debt than the
old-format compatibility retirement did, but split the work into guarded layers
so each step can be verified and stopped independently.

## Problem

The current root routing path is much cleaner after old-format compatibility
retirement:

- New root runtime packets no longer emit `legacy_skill_routing`.
- Current generated requirement docs and XL plans do not emit
  `## Specialist Consultation`.
- Current runtime scan reports `Current runtime old-format fallbacks: 0`.
- The six governed stages remain unchanged.

The project is still harder to understand than it should be because retired
terms remain in several places:

- Historical governance notes still describe old migration states as if a
  reader might treat them as current design.
- Some current behavior tests still construct or read old execution vocabulary
  outside a clearly marked retired-behavior boundary.
- `specialist_dispatch` remains in execution and child-runtime surfaces. Some
  of that naming describes current execution internals, but some test and
  packet surfaces still make it look like a current routing field.
- The current scan prevents old-format fallback from returning, but it does not
  yet prove that current docs, current behavior tests, and child-runtime packet
  contracts are free from retired vocabulary.

The user goal is not only "the tests pass"; it is to make the project less
black-boxed and easier to reason about during future development.

## Required Outcome

After this cleanup, the project should be able to answer these questions with
repository evidence:

1. Current docs teach only the current routing and usage model.
2. Historical docs are either marked as historical/retired or removed when they
   no longer provide decision value.
3. Current root runtime packets do not emit retired routing fields:
   `legacy_skill_routing`, `specialist_recommendations`,
   `stage_assistant_hints`, or old root `specialist_dispatch`.
4. Current behavior tests do not read retired fields as normal runtime
   contract.
5. Retired fields appear only in retired-behavior tests, historical fixtures,
   archived docs, or explicitly allowed execution-internal code.
6. Any remaining `specialist_dispatch` naming is documented as execution
   internals only, not routing authority.
7. Verification gates can prevent retired terminology from silently returning
   to current docs, current runtime, or current behavior tests.
8. The six governed stages, pack routing, skill usage evidence, and install
   packaging behavior do not regress.

## Non-Goals

This cleanup must not:

- Change the six governed stages:
  `skeleton_check`, `deep_interview`, `requirement_doc`, `xl_plan`,
  `plan_execute`, `phase_cleanup`.
- Change canonical `vibe` entry behavior.
- Change `skill_routing.selected` semantics.
- Change `skill_usage.used`, `skill_usage.unused`, or `skill_usage.evidence`
  semantics.
- Rebuild the router or pack-routing scorer.
- Delete bundled skills or prune packs as part of this slice.
- Change native execution behavior, hidden-subprocess policy, or host adapter
  behavior.
- Preserve old session or old artifact readability.
- Globally rename every internal `specialist_dispatch` identifier in one pass.
  Deep internal renames are allowed only when a smaller step has tests and a
  clear output-contract benefit.

## Current Field Layers

The current system should use these layers.

### Routing Layer

Allowed current routing fields:

```text
skill_candidates
skill_routing
skill_routing.candidates
skill_routing.selected
skill_routing.rejected
```

Meaning:

- `candidate`: considered by routing, not a use claim.
- `selected`: chosen into the governed work surface, not a use claim.
- `rejected`: considered but not selected.

### Usage Layer

Allowed current usage fields:

```text
skill_usage
skill_usage.used
skill_usage.unused
skill_usage.evidence
```

Meaning:

- `used`: materially shaped an artifact.
- `unused`: loaded, selected, or considered but did not shape an artifact.
- `evidence`: stage, artifact, and impact proof for material use.

### Execution Layer

Preferred current execution vocabulary:

```text
skill_execution_units
approved_skill_execution
execution_skill_outcomes
selected_skill_execution
```

This layer may temporarily keep internal `specialist_dispatch` function names
or lane names only where they are execution internals derived from
`skill_routing.selected`.

Current outputs should not present `specialist_dispatch` as a routing contract
field. Where a public artifact still exposes that name, the implementation plan
must either migrate it to the preferred vocabulary or explicitly classify it as
an execution-internal compatibility surface with a follow-up gate.

### Retired Layer

These fields and sections are retired current-routing concepts:

```text
legacy_skill_routing
specialist_recommendations
stage_assistant_hints
specialist_dispatch as root routing packet field
## Specialist Consultation
discussion_specialist_consultation
planning_specialist_consultation
approved_consultation
consulted_units
discussion_consultation
planning_consultation
route owner
primary skill
secondary skill
consultation expert
auxiliary expert
stage assistant
```

They may appear only in:

- Retired-behavior tests proving old fields are ignored.
- Historical fixtures.
- Archived historical docs marked as historical/retired.
- Narrow scan allowlists with an explicit reason.

## Cleanup Phases

### Phase 1: Establish Current Runtime Field Contract

Create or update a governance document for current runtime fields, such as:

```text
docs/governance/current-runtime-field-contract.md
```

The document should define:

- The allowed routing layer.
- The allowed usage layer.
- The preferred execution layer vocabulary.
- The retired layer.
- The rule that selected skills are joined into work through
  `skill_routing.selected`, while material use is proved only by
  `skill_usage.used` plus evidence.

This phase should not change runtime behavior.

### Phase 2: Classify Historical Docs

Scan documentation under:

```text
docs/governance
docs/superpowers/specs
docs/superpowers/plans
README.md
SKILL.md
```

Classify each retired-term hit into one of:

- `current`: must be rewritten to current vocabulary.
- `historical`: may remain, but must clearly state it is historical,
  superseded, retired, or previous-state evidence.
- `delete_candidate`: old transition docs with no useful decision value.

Do not delete a large group of docs in the same commit that changes runtime
behavior. Documentation deletion must be isolated and reversible.

### Phase 3: Tighten Test Boundaries

Divide tests into these buckets:

```text
current behavior tests
retired behavior tests
historical fixture tests
execution-internal tests
```

Rules:

- Current behavior tests must not read `legacy_skill_routing`,
  `specialist_recommendations`, or `stage_assistant_hints`.
- Current behavior tests must not treat root packet `specialist_dispatch` as
  current routing contract.
- Retired behavior tests may construct old fields only to prove current runtime
  ignores them.
- Execution-internal tests may reference `specialist_dispatch` only when the
  value is derived from `skill_routing.selected` and the test name makes the
  execution-internal scope clear.

High-risk files to inspect first:

```text
tests/runtime_neutral/test_root_child_hierarchy_bridge.py
tests/runtime_neutral/test_runtime_contract_schema.py
tests/runtime_neutral/test_runtime_delivery_acceptance.py
tests/runtime_neutral/test_skill_promotion_destructive_gate.py
tests/runtime_neutral/test_l_xl_native_execution_topology.py
```

### Phase 4: Migrate Child Runtime and Execution Output Contracts

This is the riskiest phase and must be split into small commits.

Preferred migration path:

1. Add tests describing the desired current output vocabulary.
2. Add new output fields such as `approved_skill_execution`,
   `skill_execution_units`, or `execution_skill_outcomes`.
3. Migrate current behavior tests to the new fields.
4. Stop emitting root packet `specialist_dispatch` in current child/root
   behavior where it is still exposed as a packet contract.
5. Keep internal helpers temporarily if removing them would require a broad
   execution rewrite.

The implementation must not break:

- Child governance envelope validation.
- Same-round approved specialist execution.
- Execution manifest accounting.
- Direct-current-session routed specialist execution.
- Manual review and completion truth gates.

### Phase 5: Strengthen Scan and Gates

Extend routing cleanup scans so they can distinguish:

- Current docs.
- Current runtime files.
- Current behavior tests.
- Retired behavior tests.
- Historical docs.
- Execution-internal allowlisted code.

The scan should fail on:

```text
legacy_skill_routing in current behavior tests
specialist_recommendations in current behavior tests
stage_assistant_hints in current behavior tests
packet["specialist_dispatch"] in current behavior tests
## Specialist Consultation in current generated-doc expectations
primary skill / secondary skill / route owner in current docs
historical docs with retired terms but no historical/retired marker
```

The scan should report a clear summary:

```text
Current docs retired-term violations: 0
Current runtime retired-field fallbacks: 0
Current behavior test retired-field reads: 0
Historical docs without retired marker: 0
Execution-internal specialist_dispatch allowlist: <count>
Gate Result: PASS
```

## Verification Matrix

Each implementation phase must run the narrow tests for the touched surface.
The full cleanup is not complete until these commands pass on the branch and
again after merge to `main`:

```powershell
python -m pytest tests/runtime_neutral/test_retired_old_routing_compat.py -q
python -m pytest tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
python -m pytest tests/runtime_neutral/test_current_routing_contract_scan.py -q
python -m pytest tests/runtime_neutral/test_simplified_skill_routing_contract.py -q
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py -q
python -m pytest tests/runtime_neutral/test_governed_runtime_bridge.py -q
python -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -q
```

If Phase 4 touches child runtime or execution packet surfaces, also run:

```powershell
python -m pytest tests/runtime_neutral/test_root_child_hierarchy_bridge.py -q
python -m pytest tests/runtime_neutral/test_runtime_contract_schema.py -q
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
python -m pytest tests/runtime_neutral/test_skill_promotion_destructive_gate.py -q
```

Final gates:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1
.\scripts\verify\vibe-version-packaging-gate.ps1
.\scripts\verify\vibe-version-consistency-gate.ps1
.\scripts\verify\vibe-current-routing-contract-scan.ps1
git diff --check
git status --short --branch
```

## Safety Rules

- Work in an isolated worktree.
- Commit each phase separately.
- Do not mix runtime changes and large documentation deletion in one commit.
- Add or update tests before changing behavior.
- Treat any failure in the six-stage runtime, child governance, execution
  manifest, or pack-routing gates as a blocker.
- If a field is renamed in output, keep the change narrow and prove the new
  output from a runtime-generated artifact, not only static text.
- Do not push or deploy until the user has approved the implementation plan.

## Success Criteria

This cleanup is successful when:

- Current docs teach only the current model.
- Historical docs with retired terms are clearly marked or removed.
- Current root runtime packets do not expose retired routing fields.
- Current behavior tests no longer rely on retired packet fields.
- Any remaining `specialist_dispatch` references are limited to documented
  execution-internal surfaces or retired tests.
- Scan/gates prevent the retired terms from returning to current docs,
  current runtime, or current behavior tests.
- The current routing model remains:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused
```

- The six governed stages and pack routing gates still pass.

## Implementation Plan Boundary

The implementation plan should be written only after this spec is reviewed and
approved. It should not start by deleting many files. It should start with the
contract document and scan/test classification so later cleanup has a measurable
guardrail.
