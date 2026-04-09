# Vibe Discoverable Entry PR Remediation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring PR `feat/vibe-discoverable-entry` to a mergeable state by fixing real routing/runtime defects, tightening contract consistency, and proving Linux plus Windows compatibility for the new discoverable `vibe` entry surfaces.

**Architecture:** Keep `config/vibe-entry-surfaces.json` as the single public-entry contract, then make every layer consume that contract consistently: CLI bridge, Python runtime, PowerShell governed runtime, docs, and tests. The remediation sequence is ordered by risk: first fix dead or inconsistent behavior, then remove duplication, then strengthen regression coverage and CI evidence.

**Tech Stack:** Python runtime-core, PowerShell governed runtime, pytest, GitHub Actions, GitHub PR review workflow

---

## Scope

This remediation plan covers four classes of work:

1. blocking correctness defects already identified in PR review
2. design cleanup needed to restore high cohesion and lower configuration drift
3. compatibility proof work for Linux and Windows
4. PR hygiene: review responses, validation evidence, and merge-readiness checks

Out of scope:

- unrelated runtime refactors
- release packaging changes not directly touched by the discoverable-entry feature
- new user-facing features beyond the current `vibe`/`vibe-want`/`vibe-how`/`vibe-do` model

---

## File Map

### Runtime core

- Modify: `packages/runtime-core/src/vgo_runtime/router_bridge.py`
  Responsibility: CLI/Python bridge must forward discoverable-entry parameters.
- Modify: `packages/runtime-core/src/vgo_runtime/execution.py`
  Responsibility: runtime packet execution must preserve entry intent and publish early-stop metadata consistently.
- Modify: `packages/runtime-core/src/vgo_runtime/planning.py`
  Responsibility: plan objects must reflect actual executed stage sequences for early-stop flows.
- Modify: `packages/runtime-core/src/vgo_runtime/router.py`
  Responsibility: consume discoverable entry ids from shared config instead of hardcoding.
- Modify: `packages/runtime-core/src/vgo_runtime/stage_machine.py`
  Responsibility: reject malformed stop values instead of silently treating them as “run all stages”.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
  Responsibility: if needed, accept forwarded discoverable-entry parameters in Python fallback path.

### PowerShell governed runtime

- Modify: `scripts/runtime/Write-XlPlan.ps1`
  Responsibility: always enforce clamped internal grade, never let stale packet grade bypass floor.
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
  Responsibility: always execute with clamped grade, even for inherited/direct packet runs.
- Modify: `scripts/runtime/Write-RequirementDoc.ps1`
  Responsibility: normalize encoding for Windows PowerShell compatibility if BOM warning is confirmed.
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
  Responsibility: only if needed for shared helper cleanup discovered during remediation.

### Docs and contract tests

- Modify: `docs/quick-start.md`
- Modify: `docs/quick-start.en.md`
  Responsibility: use exact discoverable labels consistently.
- Modify: `tests/contract/test_runtime_packet_contract.py`
  Responsibility: roundtrip entire packet, not selected fields only.
- Modify: `tests/contract/test_adapter_descriptor_contract.py`
  Responsibility: discover adapter host profiles dynamically.
- Modify: `tests/contract/test_vibe_discoverable_entry_contract.py`
  Responsibility: assert `allow_grade_flags` for all public entries.

### Validation / CI evidence

- Inspect: `.github/workflows/vco-gates.yml`
  Responsibility: confirm Windows validation path still exercises touched PowerShell runtime surfaces.
- Possibly add or update targeted tests under:
  - `tests/integration/test_runtime_packet_execution.py`
  - `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
  - `tests/unit/test_vgo_cli_commands.py`

---

## Chunk 1: Fix Blocking Behavior Defects

### Task 1: Forward discoverable-entry parameters through the CLI bridge

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/router_bridge.py`
- Test: `tests/unit/test_vgo_cli_commands.py`

- [ ] **Step 1: Write or update the failing test for bridge forwarding**

Add assertions that the bridge forwards:

- `--entry-intent-id`
- `--requested-grade-floor`

for both:

- PowerShell invocation path
- Python fallback path

- [ ] **Step 2: Run targeted test to verify failure**

Run: `pytest tests/unit/test_vgo_cli_commands.py -q`
Expected: one or more assertions fail because `router_bridge.py` currently drops the new flags.

- [ ] **Step 3: Implement minimal forwarding**

Update `invoke_canonical_router()` to append:

- `-EntryIntentId`
- `-RequestedGradeFloor`

when values are present.

Update the Python fallback call so `route_prompt(...)` receives equivalent parameters, either directly or via a contract-safe extension point.

- [ ] **Step 4: Run targeted test to verify pass**

Run: `pytest tests/unit/test_vgo_cli_commands.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/runtime-core/src/vgo_runtime/router_bridge.py tests/unit/test_vgo_cli_commands.py
git commit -m "fix: forward discoverable entry flags through router bridge"
```

### Task 2: Preserve packet entry intent during Python runtime execution

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/execution.py`
- Test: `tests/integration/test_runtime_packet_execution.py`

- [ ] **Step 1: Write the failing test**

Add or tighten a test where:

- `requested_skill` is omitted
- `packet.entry_intent_id` is present

and assert routing still honors the packet’s discoverable-entry intent.

- [ ] **Step 2: Run targeted test to verify failure**

Run: `pytest tests/integration/test_runtime_packet_execution.py -q`
Expected: FAIL because routing currently falls back to default `vibe`.

- [ ] **Step 3: Implement minimal routing fallback**

Change `execute_runtime_packet()` to compute:

- effective requested skill = explicit `requested_skill` if present
- otherwise `packet.entry_intent_id`

Then route using that value.

- [ ] **Step 4: Run targeted test to verify pass**

Run: `pytest tests/integration/test_runtime_packet_execution.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/runtime-core/src/vgo_runtime/execution.py tests/integration/test_runtime_packet_execution.py
git commit -m "fix: preserve entry intent in runtime packet execution"
```

### Task 3: Make early-stop Python runtime metadata truthful

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/execution.py`
- Modify: `packages/runtime-core/src/vgo_runtime/planning.py`
- Test: `tests/integration/test_runtime_packet_execution.py`

- [ ] **Step 1: Write the failing test**

Add assertions that for an early-stop packet:

- `plan["stages"]` equals the executed stage sequence
- `memory` is derived from the executed stage count
- `stage_receipts` and `final_packet.stage` stay aligned with that same sequence

- [ ] **Step 2: Run targeted test to verify failure**

Run: `pytest tests/integration/test_runtime_packet_execution.py -q`
Expected: FAIL because `plan.stages` still publishes full 6-stage topology.

- [ ] **Step 3: Implement minimal correction**

Compute one shared `executed_stages` tuple from `machine.iter_between(...)`.

Use it for:

- stage receipt loop
- plan payload stages
- memory policy stage count

Do not keep two separate notions of “planned stages” versus “executed stages” unless explicitly modeled.

- [ ] **Step 4: Run targeted test to verify pass**

Run: `pytest tests/integration/test_runtime_packet_execution.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/runtime-core/src/vgo_runtime/execution.py packages/runtime-core/src/vgo_runtime/planning.py tests/integration/test_runtime_packet_execution.py
git commit -m "fix: align early-stop runtime metadata with executed stages"
```

### Task 4: Enforce grade-floor clamp in real PowerShell execution

**Files:**
- Modify: `scripts/runtime/Write-XlPlan.ps1`
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Test: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

- [ ] **Step 1: Write or extend the failing tests**

Cover both surfaces:

- plan stage
- execute stage

using a packet or run where:

- `internal_grade` is lower
- `requested_grade_floor` is higher

and assert the resulting grade is the clamped grade, not the stale packet value.

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k 'requested_xl_grade_floor or vibe_how_shortcut' -q`
Expected: at least one assertion fails or coverage shows the stale branch still wins.

- [ ] **Step 3: Implement minimal correction**

Use:

- packet `internal_grade` only as the base grade candidate
- `Resolve-VibeGovernedGrade` as the final authority

Then set `$grade = [string]$gradeResolution.internal_grade`.

Do this consistently in both:

- `Write-XlPlan.ps1`
- `Invoke-PlanExecute.ps1`

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k 'requested_xl_grade_floor or vibe_how_shortcut or vibe_want_shortcut' -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/runtime/Write-XlPlan.ps1 scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_l_xl_native_execution_topology.py
git commit -m "fix: enforce governed grade floor in powershell runtime"
```

### Task 5: Reject malformed empty stop values in the stage machine

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/stage_machine.py`
- Add or Modify: a targeted unit test near stage-machine coverage

- [ ] **Step 1: Write the failing test**

Add a test asserting:

- `stop=None` means “run to terminal stage”
- `stop=""` raises

- [ ] **Step 2: Run targeted test to verify failure**

Run: `pytest <targeted stage-machine test path> -q`
Expected: FAIL because empty string is currently treated like no stop.

- [ ] **Step 3: Implement minimal validation**

Change `iter_between()` to:

- treat only `None` as “no stop”
- reject empty strings explicitly

- [ ] **Step 4: Run targeted test to verify pass**

Run: `pytest <targeted stage-machine test path> -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/runtime-core/src/vgo_runtime/stage_machine.py <targeted test path>
git commit -m "fix: reject malformed empty stop stages"
```

---

## Chunk 2: Restore High Cohesion and Lower Drift

### Task 6: Remove duplicated discoverable-entry id lists from Python router

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/router.py`
- Possibly modify: `packages/runtime-core/src/vgo_runtime/router_contract_support.py`
- Test: router unit/integration coverage

- [ ] **Step 1: Write the failing test**

Add a test that compares Python router allowed ids with ids loaded from `config/vibe-entry-surfaces.json`.

- [ ] **Step 2: Run targeted test to verify failure**

Run: `pytest <router test target> -q`
Expected: FAIL or missing coverage.

- [ ] **Step 3: Implement shared-config loading once**

At module init or through a helper:

- load `config/vibe-entry-surfaces.json`
- derive the allowed id set
- fail clearly if the file is missing or malformed

Do not duplicate ids in a hardcoded literal.

- [ ] **Step 4: Run targeted test to verify pass**

Run: `pytest <router test target> -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/runtime-core/src/vgo_runtime/router.py packages/runtime-core/src/vgo_runtime/router_contract_support.py <router test target>
git commit -m "refactor: derive vibe entry ids from shared contract"
```

### Task 7: Tighten contract and drift-proof tests

**Files:**
- Modify: `tests/contract/test_runtime_packet_contract.py`
- Modify: `tests/contract/test_adapter_descriptor_contract.py`
- Modify: `tests/contract/test_vibe_discoverable_entry_contract.py`

- [ ] **Step 1: Update runtime packet roundtrip test**

Assert full object equality, not field subset equality.

- [ ] **Step 2: Update adapter descriptor test**

Discover `adapters/*/host-profile.json` dynamically, assert non-empty list, then run the shared-surface assertions.

- [ ] **Step 3: Update discoverable entry contract test**

Assert `allow_grade_flags` for:

- `vibe`
- `vibe-want`
- `vibe-how`
- `vibe-do`

- [ ] **Step 4: Run targeted contract tests**

Run: `pytest tests/contract/test_runtime_packet_contract.py tests/contract/test_adapter_descriptor_contract.py tests/contract/test_vibe_discoverable_entry_contract.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/contract/test_runtime_packet_contract.py tests/contract/test_adapter_descriptor_contract.py tests/contract/test_vibe_discoverable_entry_contract.py
git commit -m "test: tighten discoverable entry contract coverage"
```

---

## Chunk 3: Documentation and Windows Compatibility Hygiene

### Task 8: Normalize discoverable labels in docs

**Files:**
- Modify: `docs/quick-start.md`
- Modify: `docs/quick-start.en.md`

- [ ] **Step 1: Update quick-start wording**

Use exact labels consistently in both lists:

- `Vibe`
- `Vibe: What Do I Want?`
- `Vibe: How Do We Do It?`
- `Vibe: Do It`

Do not mix full labels and shortened labels in the same “copy what the user sees” section.

- [ ] **Step 2: Run relevant doc sanity tests**

Run: `pytest tests/runtime_neutral/test_docs_readme_encoding.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/quick-start.md docs/quick-start.en.md
git commit -m "docs: normalize discoverable vibe labels"
```

### Task 9: Resolve PowerShell encoding compatibility warning

**Files:**
- Modify: `scripts/runtime/Write-RequirementDoc.ps1` if warning is confirmed
- Possibly inspect additional PowerShell files touched by this PR

- [ ] **Step 1: Reproduce the warning**

Run the relevant PowerShell lint or the existing Windows-oriented verify gate if available locally.

Expected: confirm whether `PSUseBOMForUnicodeEncodedFile` is still raised.

- [ ] **Step 2: If warning is real, re-encode surgically**

Resave the affected file(s) as UTF-8 with BOM only where required for Windows PowerShell 5.1 compatibility.

Do not mass-reencode the whole runtime directory.

- [ ] **Step 3: Re-run the lint/gate**

Expected: warning disappears and file contents remain unchanged semantically.

- [ ] **Step 4: Commit**

```bash
git add scripts/runtime/Write-RequirementDoc.ps1
git commit -m "fix: restore powershell bom compatibility for windows"
```

---

## Chunk 4: Cross-Platform Proof and Non-Regression Evidence

### Task 10: Re-run the full Linux validation surface

**Files:**
- No code change required unless failures appear

- [ ] **Step 1: Run the known regression surface**

Run:

```bash
pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py \
  tests/runtime_neutral/test_governed_runtime_bridge.py \
  tests/runtime_neutral/test_runtime_contract_schema.py \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/contract/test_runtime_packet_contract.py \
  tests/contract/test_adapter_descriptor_contract.py \
  tests/integration/test_runtime_packet_execution.py \
  tests/integration/test_runtime_config_manifest_roles.py \
  tests/integration/test_version_governance_runtime_roles.py \
  tests/integration/test_cli_runtime_entrypoint_contract_cutover.py \
  tests/unit/test_adapter_registry_support.py \
  tests/unit/test_vgo_cli_commands.py \
  tests/runtime_neutral/test_docs_readme_encoding.py -q
```

Expected: all pass with no new regressions.

- [ ] **Step 2: Save results into PR notes**

Capture exact pass counts and any environment notes.

### Task 11: Prove Windows compatibility using the existing CI gate

**Files:**
- Possibly none
- Modify workflow or tests only if current Windows gate misses changed surfaces

- [ ] **Step 1: Map touched code to CI coverage**

Confirm the changed PowerShell runtime paths are meaningfully exercised by:

- `.github/workflows/vco-gates.yml`
- `scripts/verify/*.ps1`

- [ ] **Step 2: If coverage is insufficient, add a Windows-relevant verify surface**

Only add the smallest missing gate needed to exercise:

- governed PowerShell runtime early-stop paths
- grade-floor clamp behavior
- discoverable-entry config consumption

- [ ] **Step 3: Run or trigger Windows validation**

Preferred:

- let PR CI run on `windows-latest`

If local Windows execution is available, run the same verify scripts there.

- [ ] **Step 4: Record evidence**

PR description or follow-up comment must explicitly separate:

- Linux evidence
- Windows evidence
- unverified assumptions, if any remain

---

## Chunk 5: PR Review Resolution and Merge Readiness

### Task 12: Respond to Rabbit review items by severity

**Files:**
- No code target; PR review workflow

- [ ] **Step 1: Group comments**

Use four buckets:

- fixed defect
- fixed low-priority hygiene item
- valid but deferred
- not applicable / reviewer rationale incorrect

- [ ] **Step 2: Reply with technical reasoning**

For each unresolved Rabbit thread:

- link to the fix commit if implemented
- explain the precise reason if declined

Do not close threads with “done” only.

### Task 13: Update PR description to reflect the actual state

**Files:**
- PR body only

- [ ] **Step 1: Rewrite the PR body**

Must include:

- summary of discoverable entry contract
- list of corrected defects
- Linux validation evidence
- Windows validation evidence
- residual risks, if any

- [ ] **Step 2: Remove any wording that overclaims**

Do not say:

- “guaranteed no regression”
- “fully cross-platform compatible”

unless both are directly supported by evidence.

### Task 14: Final merge-readiness checklist

**Files:**
- none

- [ ] **Step 1: Confirm design goals**

Check:

- one canonical runtime authority
- no stage x grade alias explosion
- shared config is authoritative
- early-stop metadata is truthful
- public grade-floor rules are enforced at actual execution time

- [ ] **Step 2: Confirm quality bar**

Check:

- no dead public inputs
- no known metadata contradictions
- no known Windows encoding regressions
- no unresolved critical review comments

- [ ] **Step 3: Final commit**

If any PR text or minor cleanup changed after validation:

```bash
git add <relevant files>
git commit -m "chore: finalize discoverable entry remediation"
```

---

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8
9. Task 9
10. Task 10
11. Task 11
12. Task 12
13. Task 13
14. Task 14

This order is intentional:

- first eliminate user-visible broken behavior
- then eliminate semantic drift and maintenance drift
- then prove compatibility
- finally close the PR professionally

---

## Success Criteria

The PR is only considered remediated when all of the following are true:

- CLI bridge forwards discoverable-entry inputs end to end.
- Python runtime preserves `entry_intent_id` and publishes truthful early-stop metadata.
- PowerShell runtime cannot execute below the requested grade floor.
- Shared discoverable-entry config is the single source of truth for runtime admission.
- Linux regression suite passes.
- Windows gate passes or a clearly scoped remaining gap is documented.
- Rabbit critical and major findings are either fixed or rebutted with precise technical evidence.
