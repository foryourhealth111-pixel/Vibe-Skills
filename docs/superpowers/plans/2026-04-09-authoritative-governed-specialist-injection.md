# Authoritative Governed Specialist Injection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make routed specialist skills participate as real governed specialists by injecting authoritative skill path information into root and specialist execution surfaces, and by failing or degrading name-only specialist execution that lacks that proof.

**Architecture:** Extend specialist dispatch freeze metadata so approved specialists carry authoritative path-based execution truth, then thread that truth into the root execution brief, specialist prompt assembly, and execution integrity gates. Tighten tests so success requires real prompt injection evidence rather than adapter stubs that merely return success JSON.

**Tech Stack:** PowerShell runtime scripts, Python runtime-neutral tests, governed runtime artifacts, Codex native specialist adapter simulation

---

## File Map

**Create:**
- `docs/superpowers/plans/2026-04-09-authoritative-governed-specialist-injection.md`

**Modify:**
- `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `scripts/runtime/VibeExecution.Common.ps1`
- `scripts/runtime/Write-XlPlan.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`

**Reference:**
- `docs/superpowers/specs/2026-04-09-authoritative-governed-specialist-injection-design.md`
- `scripts/common/vibe-governance-helpers.ps1`

## Chunk 1: Red Tests For Authoritative Injection

### Task 1: Add prompt-content assertions for live native specialist execution

**Files:**
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

- [ ] **Step 1: Write a failing test that inspects live specialist prompt content**

Add assertions to the live native specialist execution test so each executed specialist prompt must contain:

```python
self.assertIn("native_skill_entrypoint:", prompt)
self.assertIn("skill_root:", prompt)
self.assertIn("usage_required: true", prompt)
self.assertIn("must_preserve_workflow: true", prompt)
```

- [ ] **Step 2: Run the targeted test to verify it fails for the current implementation**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k "live_native_lane_when_adapter_enabled" -v
```

Expected: FAIL because the current prompt only includes `$skill-id` and generic bounded-lane text.

- [ ] **Step 3: Add a second failing test for non-host-visible path-resolved specialists**

Add a test that:

- runs a governed task that surfaces at least one specialist not visible in the current session
- inspects the resulting specialist prompt
- asserts the prompt contains the real `native_skill_entrypoint` and `skill_root`
- asserts the execution manifest does not treat path-resolved specialists as valid if those prompt fields are absent

- [ ] **Step 4: Run the new non-host-visible specialist test and verify it fails**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k "non_host_visible" -v
```

Expected: FAIL because current prompt generation does not include the authoritative path fields.

## Chunk 2: Freeze Complete Specialist Injection Metadata

### Task 2: Extend specialist dispatch descriptors with authoritative injection fields

**Files:**
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`

- [ ] **Step 1: Add descriptor fields needed for authoritative injection**

Extend `New-VibeSpecialistRecommendation` to populate:

- `skill_root`
- `visibility_class`
- `usage_required`
- `invocation_reason`
- `expected_contribution`
- `progressive_load_policy`

The implementation should derive `skill_root` from `native_skill_entrypoint` when the path exists.

- [ ] **Step 2: Keep promotion and dispatch behavior compatible with existing gates**

Ensure the new fields do not break:

- approval versus local suggestion splitting
- degradation for incomplete contracts
- child-governed approval inheritance

- [ ] **Step 3: Add or update exact assertions in tests for frozen dispatch metadata**

Expand the existing frozen specialist metadata test to assert the new descriptor fields exist for approved dispatch entries.

- [ ] **Step 4: Run the metadata-focused tests**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k "specialist_binding_metadata_is_frozen" -v
```

Expected: PASS after implementation.

## Chunk 3: Inject Root Specialist Brief And Specialist Prompt Truth

### Task 3: Inject authoritative specialist brief into plan-facing root surfaces

**Files:**
- Modify: `scripts/runtime/Write-XlPlan.ps1`

- [ ] **Step 1: Extend the plan specialist section to show authoritative injection fields**

For approved specialists, include:

- `native_skill_entrypoint`
- `skill_root`
- `visibility_class`
- `usage_required`
- `expected_contribution`

- [ ] **Step 2: Keep the plan section bounded**

Do not inline entire `SKILL.md` files into the plan. Keep the plan as a brief, authoritative routing and execution summary.

- [ ] **Step 3: Run a focused test or add assertions for the plan text**

Update the existing specialist metadata test to assert that the execution plan now includes these authoritative fields.

### Task 4: Inject authoritative skill path information into specialist prompts

**Files:**
- Modify: `scripts/runtime/VibeExecution.Common.ps1`

- [ ] **Step 1: Update `New-VibeNativeSpecialistPrompt` to include authoritative injection fields**

The prompt must include:

- `native_skill_entrypoint`
- `skill_root`
- `visibility_class`
- `usage_required`
- explicit source-of-truth instructions
- progressive loading instructions for `SKILL.md`, `references/`, `scripts/`, and `assets/`

- [ ] **Step 2: Keep the prompt bounded and deterministic**

Do not inline every referenced file. The prompt should point the specialist lane at the authoritative entrypoint and root, then describe bounded progressive loading.

- [ ] **Step 3: Update degraded or blocked specialist receipts if needed**

If authoritative injection is impossible, ensure the receipt clearly records the reason rather than pretending live specialist execution succeeded.

- [ ] **Step 4: Re-run the two red tests from Chunk 1**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k "live_native_lane_when_adapter_enabled or non_host_visible" -v
```

Expected: PASS after prompt injection is wired through.

## Chunk 4: Tighten Execution Integrity Gates

### Task 5: Treat missing prompt injection proof as degraded or incomplete execution

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `scripts/runtime/VibeExecution.Common.ps1`

- [ ] **Step 1: Add prompt-injection completeness checks to execution integrity**

The execution integrity contract must require, for approved live specialist execution:

- `native_skill_entrypoint` present in dispatch
- `skill_root` present in dispatch
- specialist prompt text contains those fields

- [ ] **Step 2: Degrade execution if a path-resolved specialist runs with name-only prompt form**

If a specialist is not host-visible and its prompt lacks authoritative path injection, mark it degraded or incomplete rather than fully executed.

- [ ] **Step 3: Preserve compatibility for blocked and explicitly degraded specialist flows**

Do not regress:

- adapter-disabled degraded flows
- child escalation advisory flows
- blocked destructive specialist dispatch

- [ ] **Step 4: Add or update tests that assert degraded status when prompt proof is missing**

If easiest, create a fixture path that forces prompt proof absence and assert:

- `effective_execution_status` is degraded
- dispatch integrity fails or records incomplete injection

- [ ] **Step 5: Run the specialist integrity subset**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -k "specialist" -v
```

Expected: PASS with no false-positive live execution.

## Chunk 5: End-To-End Regression And Strict Verification

### Task 6: Run focused end-to-end verification with prompt inspection

**Files:**
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py` if more assertions are needed

- [ ] **Step 1: Run the full topology test module**

Run:

```bash
python3 -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -v
```

Expected: PASS.

- [ ] **Step 2: Run adjacent runtime-neutral suites most likely to catch regressions**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_custom_admission_bridge.py \
  tests/runtime_neutral/test_skill_promotion_destructive_gate.py \
  tests/runtime_neutral/test_native_specialist_failure_injection.py \
  -v
```

Expected: PASS.

- [ ] **Step 3: Perform one manual proof run that inspects generated prompt files**

Run a minimal runtime simulation with native specialist execution enabled, then inspect the written prompt file and verify it contains:

- `native_skill_entrypoint:`
- `skill_root:`
- `usage_required: true`

- [ ] **Step 4: Review the resulting execution manifest**

Verify the manifest distinguishes:

- genuinely live path-injected specialist execution
- degraded non-authoritative execution
- blocked specialist execution

- [ ] **Step 5: Commit the implementation**

```bash
git add tests/runtime_neutral/test_l_xl_native_execution_topology.py \
  scripts/runtime/Freeze-RuntimeInputPacket.ps1 \
  scripts/runtime/VibeExecution.Common.ps1 \
  scripts/runtime/Write-XlPlan.ps1 \
  scripts/runtime/Invoke-PlanExecute.ps1 \
  docs/superpowers/plans/2026-04-09-authoritative-governed-specialist-injection.md
git commit -m "feat: harden governed specialist injection"
```
