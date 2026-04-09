# Authoritative Governed Specialist Injection Design

## Summary
Define a host-generic specialist injection model for `vibe` so that router-selected specialist skills participate as real governed specialists even when they are not host-visible top-level skills.

The core change is to stop treating a routed specialist as a name-only hint and instead treat it as a run-bound governed contract with four required layers:

1. freeze a complete specialist dispatch descriptor into the runtime input packet
2. inject a root-governed specialist brief into the main `vibe` execution lane
3. inject the specialist's real `SKILL.md` entrypoint and root path into the bounded specialist prompt
4. fail or degrade execution when that injection proof is missing

This design keeps one runtime authority: `vibe`. It does not promote routed specialists into second runtimes. It makes them authoritative bounded participants under `vibe` governance.

## Problem
The current runtime already freezes specialist recommendations and may execute specialist dispatch units, but the real execution surface remains incomplete for non-host-visible skills.

The failure is not mainly in route selection. The failure is in the last-mile execution handoff.

Today the pipeline does all of the following correctly:

- canonical router runs during governed runtime startup
- `vibe` stays the runtime-selected skill
- specialist recommendations are frozen into the runtime input packet
- approved dispatch is injected into plan topology
- bounded specialist units can be executed as separate native units

But the actual prompt sent to the native specialist lane does not include the specialist's real entrypoint path or skill root. For host-visible specialists this may sometimes still work by accident because the host can resolve the name. For non-host-visible specialists it is not a sufficient invocation contract.

That means the system can currently report "specialist executed" when what actually happened is only:

- a specialist unit was launched
- the prompt named `$skill-id`
- the host received no authoritative path or content for the actual skill body

This is an execution closure gap.

## Verified Evidence
Fresh validation in this session established the following:

1. `Freeze-RuntimeInputPacket.ps1` freezes `native_skill_entrypoint` into the specialist recommendation and dispatch contract.
2. `New-VibeNativeSpecialistPrompt` does not include `native_skill_entrypoint`, `skill_root`, or any `SKILL.md` path in the prompt it writes.
3. In a live runtime simulation with native specialist execution enabled, prompts for non-host-visible routed skills still only begin with `"$skill-id"` and contain no path-based specialist source of truth.
4. Existing topology tests validate that specialist units execute and return JSON, but the fake Codex adapter used in those tests does not inspect or enforce skill prompt content. It only writes a success JSON payload after seeing `-o`.

So current tests prove "a bounded specialist unit ran." They do not prove "the routed specialist was actually injected as a usable skill contract."

## Goals
- Make routed specialists participate effectively under `vibe` governance even when they are not host-visible skills.
- Preserve `vibe` as the only runtime authority.
- Make specialist invocation host-generic by using path-based and contract-based injection rather than host menu visibility.
- Force the root lane to know which approved specialists must be used and why.
- Force specialist execution prompts to include the specialist's real entrypoint and loading instructions.
- Add proof gates that distinguish real governed specialist injection from name-only prompt hints.

## Non-Goals
- No second runtime authority besides `vibe`.
- No requirement that every routed specialist also be installed as a host-visible top-level skill.
- No dependence on Codex-only host discovery semantics.
- No redesign of the router scoring algorithm itself.
- No attempt to auto-register every routed specialist into each host's native skill menu.
- No broad prompt stuffing of every specialist reference tree at startup.

## Scope Boundary
This design covers:

- canonical router output consumption inside governed runtime
- runtime input packet specialist freeze logic
- root-lane specialist awareness during planning and execution
- bounded specialist prompt assembly
- proof and degradation rules for specialist execution closure

This design does not cover:

- host-native top-level skill registration completeness
- MCP provisioning
- provider credentials
- unrelated install/profile work

## Existing Timing Model
Routing already happens at the right time for governed execution.

When the user explicitly invokes `$vibe`, runtime authority is already fixed to `vibe`. During governed startup:

1. `invoke-vibe-runtime.ps1` runs `skeleton_check`
2. `invoke-vibe-runtime.ps1` then runs `Freeze-RuntimeInputPacket.ps1`
3. `Freeze-RuntimeInputPacket.ps1` calls the canonical router with `RequestedSkill='vibe'`
4. router output is converted into route truth, overlay advice, specialist recommendations, and specialist dispatch

So router timing is not the bug. The bug is that specialist source-of-truth data is not fully carried into the execution prompt surface.

## Root Cause
The current model uses three different notions of "available specialist":

1. router candidate universe
2. frozen specialist dispatch metadata
3. actual host-executable specialist context

The first two already exist. The third is incomplete.

The missing link is an authoritative injection layer that turns routed specialist metadata into a concrete execution contract that the host can follow even when the skill is not host-visible.

## Decision
Choose an **authoritative governed specialist injection** architecture.

Under this design:

- router-selected specialists remain subordinate to `vibe`
- specialist usage is frozen as a governed dispatch contract
- root execution receives an explicit required specialist brief
- specialist lanes receive real entrypoint and root-path injection
- proof gates reject name-only specialist execution for paths that require authoritative injection

## Architecture

### 1. Specialist Dispatch Descriptor Unit
**Responsibility:** define the complete source-of-truth contract for a routed specialist inside a governed run.

The existing descriptor should be extended so that `approved_dispatch` and `local_specialist_suggestions` can carry at least:

- `skill_id`
- `skill_root`
- `native_skill_entrypoint`
- `native_skill_description`
- `visibility_class`
- `invocation_reason`
- `expected_contribution`
- `required_inputs`
- `expected_outputs`
- `verification_expectation`
- `binding_profile`
- `dispatch_phase`
- `execution_priority`
- `lane_policy`
- `parallelizable_in_root_xl`
- `write_scope`
- `review_mode`
- `must_preserve_workflow`
- `native_usage_required`
- `usage_required`
- `progressive_load_policy`

Rules:

- `usage_required` must be explicit for approved dispatch
- `native_skill_entrypoint` and `skill_root` are mandatory for authoritative live execution
- `visibility_class` must distinguish `host_visible`, `host_not_visible_path_resolved`, and degraded states

### 2. Root Specialist Brief Unit
**Responsibility:** make the root-governed lane explicitly aware of required specialists before execution begins.

The main `vibe` lane should receive a compact specialist brief that states:

- which specialists are approved
- why each specialist was selected
- what contribution each specialist must make
- whether usage is mandatory
- whether the specialist is host-visible or path-resolved only
- which skill root and entrypoint are the source of truth

This brief belongs in:

- frozen runtime packet projection
- requirement and/or plan side surfaces where appropriate
- execution topology metadata for `plan_execute`

Rules:

- the root lane must not silently ignore an approved specialist with `usage_required=true`
- if a specialist is approved but deferred, execution receipts must say why

### 3. Specialist Prompt Injection Unit
**Responsibility:** assemble a bounded specialist prompt that carries executable specialist truth, not only a symbolic name.

The bounded specialist prompt must include:

- `specialist_skill_id`
- `native_skill_entrypoint`
- `skill_root`
- `visibility_class`
- `usage_required`
- `must_preserve_workflow`
- `requirement_doc`
- `execution_plan`
- exact instruction that the named skill root and entrypoint are the specialist source of truth

For example, the prompt must move from a weak form like:

```md
$scientific-reporting
```

to an authoritative form like:

```md
$scientific-reporting

You must use the following specialist as the source of truth for this bounded task.

specialist_skill_id: scientific-reporting
native_skill_entrypoint: /.../scientific-reporting/SKILL.md
skill_root: /.../scientific-reporting
visibility_class: host_not_visible_path_resolved
usage_required: true
must_preserve_workflow: true
```

The prompt must also say how to load the specialist:

- open the `SKILL.md` entrypoint first
- progressively load `references/`, `scripts/`, and `assets/` only as needed
- remain bounded to the governed requirement and plan

Rules:

- if the specialist is not host-visible, the prompt must not rely on `$skill-id` alone
- `native_skill_entrypoint` and `skill_root` must be included in the materialized prompt text, not only in sidecar JSON

### 4. Progressive Specialist Loading Unit
**Responsibility:** prevent prompt bloat while still making path-resolved specialists usable.

The runtime should inject in layers:

1. descriptor metadata
2. `SKILL.md` entrypoint path
3. explicit instruction to load the entrypoint
4. progressive loading hints for `references/`, `scripts/`, and `assets/`

The runtime should not inline every specialist file by default. It should establish the authoritative location and loading contract first, then allow bounded progressive reads.

### 5. Dispatch Closure Proof Unit
**Responsibility:** distinguish real specialist injection from name-only execution.

Two proof surfaces are required.

**Prompt assembly proof**
- specialist prompt must contain `native_skill_entrypoint`
- specialist prompt must contain `skill_root`
- specialist prompt must contain `usage_required: true` when applicable

**Execution closure proof**
- executed specialist must be a subset of approved dispatch
- approved dispatch must have complete native contract
- for path-resolved specialists, the execution prompt must reference the actual entrypoint path
- if not, execution must degrade to non-authoritative status

Rules:

- do not mark live native specialist execution as successful if authoritative prompt injection is missing
- do not let name-only prompt forms satisfy dispatch closure for non-host-visible specialists

## Host-Generic Model
This design is intentionally not Codex-only.

The host-independent rule is:

> A routed specialist is executable under `vibe` if the runtime can provide an authoritative skill entrypoint path and bounded loading contract, regardless of whether the host exposes that skill as a top-level menu item.

That keeps the design portable across:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

Host-native visibility remains useful, but it is no longer the primary execution truth for governed specialist participation.

## Failure And Degradation Rules
The runtime must degrade rather than pretend success when:

- `native_skill_entrypoint` is missing
- `skill_root` is missing
- specialist prompt lacks authoritative injection fields
- the skill path exists in descriptor metadata but is not passed into the prompt
- a non-host-visible specialist is invoked by symbolic name only

Expected degraded status examples:

- `degraded_non_authoritative`
- `blocked_missing_specialist_source_of_truth`
- `blocked_missing_prompt_injection`

Exact status naming can be decided during implementation, but the distinction must be explicit in receipts and execution manifests.

## Implementation Touchpoints
The likely change set is:

- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `scripts/runtime/VibeExecution.Common.ps1`
- `scripts/runtime/Write-XlPlan.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`
- `scripts/common/vibe-governance-helpers.ps1`
- runtime-neutral topology and promotion tests
- new closure-gate tests for prompt injection proof

## Verification Strategy
Fresh verification must prove both contract freeze and execution closure.

### Required tests
- prompt assembly test: specialist prompt contains `native_skill_entrypoint`, `skill_root`, and `usage_required`
- non-host-visible specialist test: path-resolved specialist does not pass with name-only prompt form
- closure-gate test: execution degrades if authoritative prompt injection fields are missing
- positive test: live native specialist execution succeeds when the prompt includes real entrypoint and root-path injection

### Required smoke evidence
- inspect the materialized prompt file written for specialist execution
- assert prompt content, not only result JSON presence
- ensure fake host adapters fail if required specialist injection fields are absent

## Risks
- prompt size may grow if the injection format is too verbose
- implementation may accidentally duplicate specialist data across root and child lanes without clear ownership
- some legacy tests may assume that symbolic `$skill-id` is sufficient and will need to be tightened

## Open Questions
- whether root-lane specialist brief should live only in execution artifacts or also appear explicitly in the requirement doc
- whether `skill_root` should always be stored literally or sometimes derived from `native_skill_entrypoint`
- exact degraded status names for non-authoritative specialist execution

## Recommendation
Implement this as a runtime hardening feature, not as a prompt-style tweak.

The key architectural move is to convert specialist participation from:

- symbolic recommendation

into:

- authoritative injected governed specialist contract

That is the smallest design that closes the verified gap without creating a second runtime authority or requiring every routed specialist to become a host-visible top-level skill.
