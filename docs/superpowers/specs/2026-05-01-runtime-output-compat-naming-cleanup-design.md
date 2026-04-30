# Runtime Output Compatibility Naming Cleanup Design

Date: 2026-05-01

## Goal

Clean the current runtime and router output surfaces so new route results no longer present legacy role terminology as active routing concepts.

The active model remains:

```text
skill_candidates -> selected skill -> used / unused
```

This is a runtime-output cleanup slice. It follows the previous terminology and pack-manifest simplification work. The active pack manifest is already field-minimal; this slice makes the current route outputs and runtime packet surfaces match that simpler model.

## Current Findings

The active pack manifest is already clean:

```text
pack_count: 41
bad_pack_count for route_authority_candidates/stage_assistant_candidates: 0
```

The remaining confusion is in current runtime/router output fields and compatibility helpers:

| Area | Current issue |
| --- | --- |
| Python router selection | Ranking rows still expose `legacy_role` and `route_authority_eligible`. |
| Python route result | Ranked pack rows still expose `stage_assistant_candidates` and `route_authority_eligible`. |
| PowerShell router selection | Mirrors the same legacy output fields. |
| Runtime packet freeze | Can derive `stage_assistant_hints` from `stage_assistant_candidates`. |
| Runtime readers | Still read old top-level or legacy `stage_assistant_hints`, which is valid compatibility behavior. |
| Audit tools and historical plans | Still mention old names for historical or fixture analysis; they are not this slice's active output boundary. |

These names do not appear in active `config/pack-manifest.json`, but they still make new runtime output look like the old model is alive.

## Approved Approach

Use the middle path:

1. Remove legacy names from new active route outputs.
2. Keep old artifact readers and old fixture compatibility.
3. Do not do a repo-wide historical rewrite.
4. Do not remove `legacy_skill_routing` in this slice.

This keeps risk controlled while making current runtime behavior easier to understand.

## Non-Goals

This slice must not:

- Delete skill directories.
- Continue pack pruning.
- Rename the six Vibe stages.
- Remove old artifact reader compatibility.
- Rewrite all historical `docs/superpowers/plans` files.
- Delete `legacy_skill_routing`.
- Claim a selected skill was used without `skill_usage.used` evidence.

The six governed stages remain unchanged:

```text
skeleton_check
deep_interview
requirement_doc
xl_plan
plan_execute
phase_cleanup
```

## Target Active Output

### Pack Route Rows

New active `route_prompt(...).ranked[*]` rows should expose current candidate-selection data only:

```text
pack_id
score
intent
workspace
selected_candidate
candidate_selection_reason
candidate_selection_score
candidate_relevance_score
candidate_ranking
candidate_top1_top2_gap
candidate_signal
candidate_filtered_out_by_task
custom_admission
```

These legacy fields should not appear in new active ranked pack rows:

```text
stage_assistant_candidates
route_authority_eligible
```

Internal implementation may keep temporary booleans or variables for selection math, but the public route result must not expose those names as active fields.

### Candidate Ranking Rows

New active `candidate_ranking[*]` rows should no longer expose:

```text
legacy_role
route_authority_eligible
```

The ranked candidate list should remain useful for explaining why a skill was selected, using existing score fields such as:

```text
skill
score
keyword_score
name_score
positive_score
negative_score
canonical_for_task_hit
requires_positive_keyword_match
ordinal
```

Do not add a new replacement role field unless tests prove it is necessary. The purpose is to remove old role vocabulary, not to invent another role system.

### Runtime Input Packet

New runtime packets should keep active routing and usage evidence here:

```text
skill_routing.selected
skill_usage.used
skill_usage.unused
```

New root-level runtime packets must not reintroduce:

```text
stage_assistant_hints
specialist_recommendations
specialist_dispatch
```

Existing tests already require those root-level surfaces to be absent. This slice must preserve that.

`legacy_skill_routing` may remain as the compatibility container, but new code should not derive fresh `stage_assistant_hints` from removed active route fields.

## Compatibility Boundary

Compatibility is allowed only in clearly legacy paths:

| Legacy data | Allowed behavior |
| --- | --- |
| Old pack fixtures with `route_authority_candidates` | Selection helpers may still read them only as fallback when `skill_candidates` is missing. |
| Old pack fixtures with `stage_assistant_candidates` | Selection helpers may still read them only for old-fixture compatibility. |
| Old runtime packets with top-level `stage_assistant_hints` | Runtime readers may still interpret them. |
| Old runtime packets with `legacy_skill_routing.stage_assistant_hints` | Runtime readers may still interpret them. |
| Historical audit fixtures | Audit tools may still parse old fields when their purpose is to explain old pack states. |

Compatibility readers must prefer current fields first. Old fields are fallback input only, not active output.

## Affected Files

Expected implementation files:

- `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`
- `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
- `packages/runtime-core/src/vgo_runtime/router_contract_presentation.py`
- `scripts/router/modules/41-candidate-selection.ps1`
- `scripts/router/resolve-pack-route.ps1`
- `scripts/router/modules/46-confirm-ui.ps1`
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `scripts/runtime/VibeRuntime.Common.ps1`

Expected tests:

- `tests/unit/test_router_contract_selection_guards.py`
- `tests/runtime_neutral/test_router_bridge.py`
- `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- `tests/runtime_neutral/test_governed_runtime_bridge.py`
- A new runtime-neutral guard test for active route output shape.

Audit tools under `packages/verification-core/src/vgo_verify/*_audit.py` are out of scope unless they fail because of active output changes. Their old-field parsing is historical analysis, not current route output.

## Test Design

Add or update tests before implementation.

### Active Output Guard

Create a guard that calls `route_prompt` for representative prompts and asserts:

- `ranked[*]` has no `stage_assistant_candidates`.
- `ranked[*]` has no `route_authority_eligible`.
- `candidate_ranking[*]` has no `legacy_role`.
- `candidate_ranking[*]` has no `route_authority_eligible`.
- Existing selected pack and selected skill remain stable for known probes.

Representative probes should cover:

- `science-figures-visualization` routing to `scientific-visualization`.
- `scholarly-publishing-workflow` routing LaTeX/PDF build to `latex-submission-pipeline`.
- `data-ml` preprocessing routing to `preprocessing-data-with-automated-pipelines`.
- `code-quality` review preparation routing to `requesting-code-review`.

### Compatibility Guard

Keep old-fixture coverage proving:

- `skill_candidates` wins over old role fields when present.
- Old `route_authority_candidates` and `stage_assistant_candidates` can still be read only when a fixture lacks `skill_candidates`.
- Old runtime packets with legacy hint fields remain readable through compatibility helpers.

### Usage Evidence Guard

Preserve binary usage tests:

- `skill_routing.selected` means selected.
- `skill_usage.used` means materially used.
- `skill_usage.unused` means selected but not materially used.
- No test may infer usage from route selection, recommendation, or dispatch alone.

## Verification Plan

The implementation plan must run at least:

```powershell
python -m pytest tests/unit/test_runtime_stage_machine.py tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_governed_runtime_bridge.py -q
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

The plan should also include a direct route-output shape check that fails if new route results contain:

```text
stage_assistant_candidates
route_authority_eligible
legacy_role
```

outside explicit compatibility fixtures.

## Success Criteria

This slice is complete only when:

1. Active `config/pack-manifest.json` still has no `route_authority_candidates` or `stage_assistant_candidates`.
2. New active route results do not expose `stage_assistant_candidates`, `route_authority_eligible`, or `legacy_role`.
3. Runtime packets keep old specialist surfaces out of the root packet.
4. `legacy_skill_routing` remains available for old artifact compatibility.
5. Old fixture compatibility still passes.
6. `skill_usage.used` and `skill_usage.unused` remain the only proof of actual skill use.
7. Six-stage runtime tests pass.
8. Pack routing smoke, offline skills gate, config parity, and whitespace checks pass.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Python and PowerShell route outputs diverge | Add tests that exercise both paths where existing test harnesses allow it. |
| Confirm UI still expects `stage_assistant_candidates` | Update it to use current ranking data or compatibility helper only. |
| Freeze packet loses old artifact readability | Keep `VibeRuntime.Common.ps1` fallback readers and add compatibility tests. |
| Output cleanup accidentally changes selected skills | Include stable representative route probes before and after implementation. |
| New replacement terms recreate complexity | Do not add new role fields unless a failing test proves the need. |

## Rollout Boundary

This is a single implementation slice after spec approval. If deeper cleanup is still desired afterward, it should become a later slice:

```text
legacy audit terminology cleanup
historical plan archive cleanup
legacy_skill_routing deletion
```

Those later slices must not be bundled into this runtime-output cleanup.
