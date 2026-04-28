# Simplified Skill Routing Design

Date: 2026-04-29

## 1. Goal

This design simplifies expert skill routing inside Vibe-Skills while keeping the public six-stage Vibe runtime unchanged:

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

The target is not only simpler reporting. The internal routing model should also become smaller, more direct, and easier to verify.

The new model is:

```text
candidate -> selected -> used / unused
```

There is no authoritative "primary skill", "secondary skill", "stage assistant", "consultation bucket", or "local suggestion" state in the new workflow.

## 2. Problem

The current expert skill path has too many overlapping states:

```text
route_authority_candidates
stage_assistant_candidates
stage_assistant_hints
specialist_recommendations
specialist_dispatch.approved_dispatch
specialist_dispatch.local_specialist_suggestions
promotion_state
consultation_bucket
primary / stage_assistant
skill_usage.used / skill_usage.unused
```

This makes the architecture hard to reason about. A skill can be recommended, hinted, consulted, approved, or dispatched without clearly entering the work. It also expands runtime JSON because several artifacts repeat similar routing data in slightly different shapes.

The user requirement is stricter:

```text
Route the skill into work, or do not route it into work.
If it enters work, prove whether it was actually used.
```

## 3. Approved Direction

Use a simplified internal authority model.

Chosen option:

```text
skill_routing.selected is the only routing-to-work authority
skill_usage.used / skill_usage.unused is the only usage authority
legacy routing fields may be read during migration but must not drive new execution decisions
```

Rejected options:

| Option | Why not |
| --- | --- |
| Only simplify final reports | It leaves the internal model tangled and keeps producing confusing JSON. |
| Delete all legacy fields in one commit | It is clean but high risk because many tests and old artifacts still reference those fields. |
| Keep candidates and dispatch but rename fields | It reduces naming noise but does not remove the conceptual overlap. |

## 4. Authoritative Data Model

Runtime routing should have one authoritative object:

```json
{
  "skill_routing": {
    "candidates": [],
    "selected": [],
    "rejected": []
  }
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `candidates` | Skills the router considered relevant to the user task. |
| `selected` | Skills chosen to enter the actual six-stage work. |
| `rejected` | Considered skills that will not enter the work. |

Each selected skill must carry only the data needed to join work:

```json
{
  "skill_id": "scikit-learn",
  "skill_md_path": "bundled/skills/scikit-learn/SKILL.md",
  "reason": "handles classical ML model training for this task",
  "task_slice": "train and evaluate the baseline model"
}
```

The usage object remains separate and only records proof:

```json
{
  "skill_usage": {
    "used": [],
    "unused": []
  }
}
```

`used` means the selected skill's full `SKILL.md` was loaded and the workflow shaped at least one six-stage artifact.

`unused` means the skill did not satisfy the used standard. Valid reasons include:

```text
not_selected
selected_but_not_loaded
selected_but_skill_md_load_failed
selected_but_no_artifact_impact
```

## 5. Deprecated Internal Concepts

The following fields and identities are no longer authoritative in the new model:

```text
specialist_recommendations
specialist_dispatch.approved_dispatch
specialist_dispatch.local_specialist_suggestions
stage_assistant_hints
consultation_bucket
promotion_state
primary / stage_assistant
route_authority_candidates
stage_assistant_candidates
```

Migration rule:

```text
Old fields may be read only to populate or validate skill_routing during migration.
They must not decide execution once skill_routing.selected exists.
They must not support a final used claim.
```

Pack configuration should also converge:

```text
route_authority_candidates + stage_assistant_candidates -> skill_candidates
```

If a skill cannot enter work as a selected skill, it should not remain as a routed skill. It should be merged into a stronger skill, moved to documentation/reference material, or removed in a later cleanup.

## 6. Runtime Flow

The simplified runtime flow is:

```text
1. Router builds skill_routing.candidates.
2. Router chooses skill_routing.selected and records rejected candidates.
3. Requirement and plan stages bind each selected skill to a task_slice.
4. Execute stage loads the full SKILL.md for every selected skill.
5. Runtime records load hash and artifact impact evidence.
6. Final reporting reads only skill_usage.used / skill_usage.unused.
```

Selected skills are not suggestions. A selected skill must be attempted:

```text
selected -> load full SKILL.md -> bind to task_slice -> record used or unused
```

Failure is explicit:

```json
{
  "skill_id": "example-skill",
  "status": "unused",
  "reason": "selected_but_skill_md_load_failed"
}
```

If loading succeeds but the work does not use the skill workflow:

```json
{
  "skill_id": "example-skill",
  "status": "unused",
  "reason": "selected_but_no_artifact_impact"
}
```

## 7. JSON Output Shape

`runtime-input-packet.json` should carry route selection, not repeated specialist dispatch structures:

```json
{
  "skill_routing": {
    "candidates": [
      {
        "skill_id": "scikit-learn",
        "reason": "classical ML model training"
      }
    ],
    "selected": [
      {
        "skill_id": "scikit-learn",
        "skill_md_path": "bundled/skills/scikit-learn/SKILL.md",
        "task_slice": "train and evaluate baseline model"
      }
    ],
    "rejected": [
      {
        "skill_id": "plotly",
        "reason": "visualization not required for this task"
      }
    ]
  }
}
```

`skill-usage.json` should carry final proof:

```json
{
  "used": [
    {
      "skill_id": "scikit-learn",
      "skill_md_path": "bundled/skills/scikit-learn/SKILL.md",
      "skill_md_sha256": "...",
      "evidence": [
        {
          "stage": "plan_execute",
          "artifact_path": "outputs/.../execution-manifest.json",
          "impact": "training and verification followed the selected skill workflow"
        }
      ]
    }
  ],
  "unused": [
    {
      "skill_id": "plotly",
      "reason": "not_selected"
    }
  ]
}
```

`execution-manifest.json` should reference the authoritative artifacts instead of copying full routing state:

```json
{
  "skill_routing_summary": {
    "candidate_count": 3,
    "selected_count": 1,
    "used_count": 1,
    "unused_count": 2
  },
  "skill_routing_path": ".../runtime-input-packet.json",
  "skill_usage_path": ".../skill-usage.json"
}
```

Legacy data, if still emitted during migration, must be isolated under an explicitly non-authoritative object such as:

```json
{
  "legacy_skill_routing": {
    "specialist_recommendations": [],
    "specialist_dispatch": {}
  }
}
```

New runtime code must not make execution decisions from `legacy_skill_routing`.

## 8. Verification Requirements

Tests and gates must protect three rules.

First, legacy routing fields are not authority:

```text
specialist_recommendations
stage_assistant_hints
specialist_dispatch.approved_dispatch
local_specialist_suggestions
```

None of these can make a skill `used`.

Second, every selected skill must attempt full `SKILL.md` loading:

```text
selected skill without skill_md_sha256 -> fail
```

Third, every used skill must have artifact impact evidence:

```text
used skill without evidence -> fail
```

Core regression expectations:

| Scenario | Expected result |
| --- | --- |
| Skill appears only in legacy dispatch | Not selected, not used. |
| Skill appears in `skill_routing.selected` but cannot load `SKILL.md` | `unused` with load failure reason. |
| Skill loads but has no artifact impact | `unused` with no-impact reason. |
| Skill is selected, fully loaded, and shapes a six-stage artifact | `used`. |

## 9. Migration Plan Shape

Implementation should be staged:

1. Add `skill_routing` as the new authority while keeping legacy reading for compatibility.
2. Convert runtime planning and execution to read `skill_routing.selected`.
3. Convert usage accounting to derive `used / unused` from selected skills.
4. Reduce manifest duplication to summaries and artifact paths.
5. Move old routing fields under `legacy_skill_routing` or stop emitting them once tests no longer need them.
6. Update pack manifests from `route_authority_candidates` / `stage_assistant_candidates` toward `skill_candidates`.

The first implementation pass should focus on runtime authority and JSON shrinkage. Physical skill deletion and pack-by-pack pruning remain separate cleanup work.

## 10. Non-Goals

This design does not:

- Change the public six-stage Vibe runtime.
- Change canonical `$vibe` / `/vibe` launch behavior.
- Delete skill directories as part of the routing model change.
- Remove all old tests in one pass.
- Claim that legacy artifacts from previous runs already follow the new model.

## 11. Acceptance Criteria

The cleanup is complete when:

- New runtime authority is `skill_routing.selected`.
- Final skill usage authority is `skill_usage.used / skill_usage.unused`.
- New execution decisions no longer depend on stage assistants, consultation buckets, local suggestions, or approved dispatch.
- Runtime JSON exposes concise summaries instead of repeated specialist structures.
- Tests prove that legacy fields cannot make a skill used.
- Tests prove that selected skills must load full `SKILL.md` and record artifact impact before becoming used.
