# Vibe Specialist Execution Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve approved Vibe specialist execution obligations across bounded re-entry so final execution cannot silently drop specialists selected in the approved plan.

**Architecture:** Add a durable `skill_execution_lock` projection to runtime packets, feed it into plan execution before current router-only selection, and make delivery acceptance account for unresolved locked specialists. Keep `skill_usage.used` as the only material-use truth; the lock is execution obligation, not usage evidence.

**Tech Stack:** PowerShell runtime scripts, Python `pytest` runtime-neutral tests, Vibe verification-core delivery acceptance module, Markdown governance docs.

---

## Scope And File Structure

This plan implements the approved spec at `docs/superpowers/specs/2026-05-05-vibe-specialist-execution-lock-design.md`.

Modify:

- `scripts/runtime/VibeRuntime.Common.ps1`: add lock helpers and previous-packet loading.
- `scripts/runtime/VibeSkillRouting.Common.ps1`: convert active locks into dispatch rows.
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`: construct `skill_execution_lock` during packet freeze.
- `scripts/runtime/Invoke-PlanExecute.ps1`: prefer active lock dispatch over current router-only selection and emit lock accounting.
- `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`: evaluate lock resolution as a delivery truth layer.
- `tests/runtime_neutral/test_skill_execution_lock_contract.py`: new focused PowerShell/Python tests for the lock model.
- `tests/runtime_neutral/test_runtime_delivery_acceptance.py`: delivery acceptance fixture and assertions for unresolved/resolved locks.
- `docs/governance/current-routing-contract.md`: document the new authority chain.
- `docs/governance/current-runtime-field-contract.md`: document runtime fields for `skill_execution_lock`.
- `docs/governance/terminology-governance.md`: define current terms.
- `tests/runtime_neutral/test_current_routing_docs_entrypoint.py`: update current model assertions.
- `tests/runtime_neutral/test_terminology_field_simplification.py`: update terminology assertions.

Do not change router ranking logic, pack manifests, or historical archived docs in this slice.

## Preflight

- [ ] **Step 1: Confirm branch and cleanliness**

Run:

```powershell
git status --short
git branch --show-current
```

Expected:

```text
pr226-followup-review-fixes
```

`git status --short` may show this plan file or task files created by the current implementation. Do not revert unrelated user changes.

- [ ] **Step 2: Run the focused baseline tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_skill_promotion_freeze_contract.py tests/runtime_neutral/test_runtime_delivery_acceptance.py::RuntimeDeliveryAcceptanceTests::test_runtime_delivery_acceptance_passes_when_current_session_specialist_execution_is_recorded -q
```

Expected:

```text
passed
```

If this fails before edits, stop and record the failing test names and messages before continuing.

---

### Task 1: Add Failing Lock Contract Tests

**Files:**

- Create: `tests/runtime_neutral/test_skill_execution_lock_contract.py`
- No runtime implementation files are modified in this task.

- [ ] **Step 1: Create the failing test file**

Create `tests/runtime_neutral/test_skill_execution_lock_contract.py` with this content:

```python
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
SKILL_ROUTING_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeSkillRouting.Common.ps1"
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps_json(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class SkillExecutionLockContractTests(unittest.TestCase):
    def test_lock_projection_preserves_previous_selected_when_current_router_differs(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$previous = [pscustomobject]@{ "
            "  run_id = 'pytest-plan-run'; "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ "
            "      skill_id = 'scientific-reporting'; "
            "      task_slice = 'write paper'; "
            "      native_skill_entrypoint = 'C:/skills/scientific-reporting/SKILL.md'; "
            "      skill_md_path = 'C:/skills/scientific-reporting/SKILL.md'; "
            "      dispatch_phase = 'post_execution'; "
            "      write_scope = 'specialist:scientific-reporting'; "
            "      verification_expectation = 'report evidence' "
            "    }) "
            "  } "
            "}; "
            "$current = [pscustomobject]@{ "
            "  selected = @([pscustomobject]@{ "
            "    skill_id = 'latex-submission-pipeline'; "
            "    task_slice = 'compile pdf'; "
            "    native_skill_entrypoint = 'C:/skills/latex-submission-pipeline/SKILL.md'; "
            "    skill_md_path = 'C:/skills/latex-submission-pipeline/SKILL.md'; "
            "    dispatch_phase = 'post_execution'; "
            "    write_scope = 'specialist:latex-submission-pipeline'; "
            "    verification_expectation = 'build pdf' "
            "  }); "
            "  candidates = @(); rejected = @() "
            "}; "
            "$lock = New-VibeSkillExecutionLockProjection "
            "-PreviousRuntimeInputPacket $previous "
            "-CurrentSkillRouting $current "
            "-SourceRunId 'pytest-plan-run' "
            "-Source 'approved_plan_reentry'; "
            "$lock | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual("v1", payload["schema_version"])
        self.assertEqual("active", payload["state"])
        self.assertEqual("approved_plan_reentry", payload["source"])
        self.assertEqual("pytest-plan-run", payload["source_run_id"])
        self.assertIn("scientific-reporting", as_list(payload["locked_skill_ids"]))
        locked_dispatch = as_list(payload["locked_dispatch"])
        self.assertEqual("scientific-reporting", locked_dispatch[0]["skill_id"])
        self.assertEqual("inherited_not_currently_surfaced", locked_dispatch[0]["reconciliation_state"])
        self.assertTrue(payload["resolution_required"])

    def test_lock_projection_prefers_explicit_host_decision(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$previous = [pscustomobject]@{ "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ skill_id = 'scientific-reporting'; task_slice = 'prior plan' }) "
            "  } "
            "}; "
            "$current = [pscustomobject]@{ "
            "  selected = @([pscustomobject]@{ skill_id = 'latex-submission-pipeline'; task_slice = 'current pdf'; dispatch_phase = 'post_execution' }); "
            "  candidates = @([pscustomobject]@{ skill_id = 'designing-experiments'; task_slice = 'explicit design'; dispatch_phase = 'pre_execution' }); "
            "  rejected = @() "
            "}; "
            "$decision = [pscustomobject]@{ approved_skill_ids = @('designing-experiments') }; "
            "$lock = New-VibeSkillExecutionLockProjection "
            "-PreviousRuntimeInputPacket $previous "
            "-CurrentSkillRouting $current "
            "-HostSpecialistDispatchDecision $decision "
            "-SourceRunId 'pytest-plan-run' "
            "-Source 'approved_plan_reentry'; "
            "$lock | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["designing-experiments"], as_list(payload["locked_skill_ids"]))
        dispatch = as_list(payload["locked_dispatch"])[0]
        self.assertEqual("designing-experiments", dispatch["skill_id"])
        self.assertEqual("host_decision", dispatch["lock_source"])
        self.assertEqual("current_surfaced", dispatch["reconciliation_state"])

    def test_convert_lock_to_dispatch_preserves_dispatch_fields(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$lock = [pscustomobject]@{ "
            "  schema_version = 'v1'; state = 'active'; resolution_required = $true; "
            "  locked_dispatch = @([pscustomobject]@{ "
            "    skill_id = 'literature-review'; "
            "    task_slice = 'review authoritative literature'; "
            "    native_skill_entrypoint = 'C:/skills/literature-review/SKILL.md'; "
            "    skill_md_path = 'C:/skills/literature-review/SKILL.md'; "
            "    dispatch_phase = 'pre_execution'; "
            "    parallelizable_in_root_xl = $true; "
            "    write_scope = 'specialist:literature-review'; "
            "    verification_expectation = 'citation notes'; "
            "    lock_source = 'previous_skill_routing_selected' "
            "  }) "
            "}; "
            "$dispatch = Convert-VibeSkillExecutionLockToDispatch -SkillExecutionLock $lock; "
            "[pscustomobject]@{ dispatch = $dispatch } | ConvertTo-Json -Depth 20 "
            "}"
        )

        dispatch = as_list(payload["dispatch"])[0]
        self.assertEqual("literature-review", dispatch["skill_id"])
        self.assertEqual("pre_execution", dispatch["dispatch_phase"])
        self.assertEqual("specialist:literature-review", dispatch["write_scope"])
        self.assertEqual("citation notes", dispatch["verification_expectation"])
        self.assertTrue(dispatch["locked_for_execution"])

    def test_freeze_inherits_previous_plan_selection_into_execution_lock(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            prior_session = artifact_root / "outputs" / "runtime" / "vibe-sessions" / "pytest-plan-run"
            prior_session.mkdir(parents=True)
            (prior_session / "runtime-input-packet.json").write_text(
                json.dumps(
                    {
                        "run_id": "pytest-plan-run",
                        "requested_stage_stop": "xl_plan",
                        "skill_routing": {
                            "schema_version": "simplified_skill_routing_v1",
                            "selected": [
                                {
                                    "skill_id": "scientific-reporting",
                                    "task_slice": "write a scientific report",
                                    "native_skill_entrypoint": "C:/skills/scientific-reporting/SKILL.md",
                                    "skill_md_path": "C:/skills/scientific-reporting/SKILL.md",
                                    "dispatch_phase": "post_execution",
                                    "write_scope": "specialist:scientific-reporting",
                                    "verification_expectation": "report evidence",
                                }
                            ],
                            "candidates": [],
                            "rejected": [],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            host_decision = {
                "decision_kind": "approval_response",
                "decision_action": "approve_plan",
                "approval_decision": "approve",
                "continuation_context": {
                    "structured_bounded_reentry": True,
                    "source_run_id": "pytest-plan-run",
                    "reentry_action": "approve_plan",
                    "prior_task_type": "research",
                    "control_only_prompt": True,
                },
            }
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(FREEZE_SCRIPT),
                    "-Task",
                    "Continue approved plan and compile the LaTeX paper.",
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    "pytest-execute-run",
                    "-ArtifactRoot",
                    str(artifact_root),
                    "-HostDecisionJson",
                    json.dumps(host_decision),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            self.assertIn("packet_path", completed.stdout)
            packet_path = next((artifact_root / "outputs" / "runtime" / "vibe-sessions" / "pytest-execute-run").rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        lock = packet["skill_execution_lock"]
        self.assertEqual("active", lock["state"])
        self.assertIn("scientific-reporting", as_list(lock["locked_skill_ids"]))
        self.assertTrue(lock["resolution_required"])
```

- [ ] **Step 2: Run the new tests to verify they fail before implementation**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py -q
```

Expected:

```text
FAILED
```

At least one failure should mention that `New-VibeSkillExecutionLockProjection` or `Convert-VibeSkillExecutionLockToDispatch` is not recognized.

- [ ] **Step 3: Commit the failing tests**

Run:

```powershell
git add tests/runtime_neutral/test_skill_execution_lock_contract.py
git commit -m "test: add specialist execution lock contract coverage"
```

Expected:

```text
Commit succeeds and prints subject `test: add specialist execution lock contract coverage`.
```

---

### Task 2: Implement Runtime Lock Helpers

**Files:**

- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
- Test: `tests/runtime_neutral/test_skill_execution_lock_contract.py`

- [ ] **Step 1: Add lock helper functions**

In `scripts/runtime/VibeRuntime.Common.ps1`, add these functions after `Resolve-VibeHostSkillExecutionDecision`:

```powershell
function Get-VibeRuntimeInputPacketFromSessionRunId {
    param(
        [AllowEmptyString()] [string]$ArtifactRoot = '',
        [AllowEmptyString()] [string]$SourceRunId = ''
    )

    if ([string]::IsNullOrWhiteSpace($ArtifactRoot) -or [string]::IsNullOrWhiteSpace($SourceRunId)) {
        return $null
    }

    $candidatePath = Join-Path (Join-Path (Join-Path (Join-Path $ArtifactRoot 'outputs') 'runtime') 'vibe-sessions') (Join-Path $SourceRunId 'runtime-input-packet.json')
    if (-not (Test-Path -LiteralPath $candidatePath)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $candidatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-VibeSkillExecutionLockFromRuntimeInputPacket {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    if (
        $null -eq $RuntimeInputPacket -or
        -not (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'skill_execution_lock') -or
        $null -eq $RuntimeInputPacket.skill_execution_lock
    ) {
        return $null
    }

    return $RuntimeInputPacket.skill_execution_lock
}

function Test-VibeSkillExecutionLockActive {
    param(
        [AllowNull()] [object]$SkillExecutionLock = $null
    )

    if ($null -eq $SkillExecutionLock) {
        return $false
    }
    $state = if (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'state') { [string]$SkillExecutionLock.state } else { '' }
    $lockedDispatch = if (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'locked_dispatch') { @($SkillExecutionLock.locked_dispatch) } else { @() }
    $lockedSkillIds = if (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'locked_skill_ids') { @($SkillExecutionLock.locked_skill_ids) } else { @() }
    return [bool]([string]::Equals($state, 'active', [System.StringComparison]::OrdinalIgnoreCase) -and ((@($lockedDispatch).Count -gt 0) -or (@($lockedSkillIds).Count -gt 0)))
}

function Copy-VibeSkillExecutionLockDispatchRecord {
    param(
        [AllowNull()] [object]$Record = $null,
        [AllowEmptyString()] [string]$LockSource = '',
        [AllowEmptyString()] [string]$ReconciliationState = ''
    )

    if ($null -eq $Record) {
        return $null
    }
    $copy = Copy-VibeRecordObject -InputObject $Record
    $skillId = if (Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'skill_id') { [string]$copy.skill_id } else { '' }
    if ([string]::IsNullOrWhiteSpace($skillId)) {
        return $null
    }
    if (-not (Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'task_slice') -or [string]::IsNullOrWhiteSpace([string]$copy.task_slice)) {
        $copy | Add-Member -NotePropertyName task_slice -NotePropertyValue ('Resolve locked specialist execution for {0}.' -f $skillId) -Force
    }
    if (-not (Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'dispatch_phase') -or [string]::IsNullOrWhiteSpace([string]$copy.dispatch_phase)) {
        $copy | Add-Member -NotePropertyName dispatch_phase -NotePropertyValue 'in_execution' -Force
    }
    if (-not (Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'write_scope') -or [string]::IsNullOrWhiteSpace([string]$copy.write_scope)) {
        $copy | Add-Member -NotePropertyName write_scope -NotePropertyValue ('specialist:{0}' -f $skillId) -Force
    }
    if (-not (Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'verification_expectation') -or [string]::IsNullOrWhiteSpace([string]$copy.verification_expectation)) {
        $copy | Add-Member -NotePropertyName verification_expectation -NotePropertyValue 'Resolve locked specialist execution before delivery acceptance.' -Force
    }
    $copy | Add-Member -NotePropertyName locked_for_execution -NotePropertyValue $true -Force
    $copy | Add-Member -NotePropertyName lock_source -NotePropertyValue $(if ([string]::IsNullOrWhiteSpace($LockSource)) { 'unknown' } else { [string]$LockSource }) -Force
    $copy | Add-Member -NotePropertyName reconciliation_state -NotePropertyValue $(if ([string]::IsNullOrWhiteSpace($ReconciliationState)) { 'current_surfaced' } else { [string]$ReconciliationState }) -Force
    $copy | Add-Member -NotePropertyName requires_resolution -NotePropertyValue $true -Force
    return $copy
}

function New-VibeMinimalSkillExecutionLockDispatchRecord {
    param(
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$LockSource = '',
        [AllowEmptyString()] [string]$ReconciliationState = ''
    )

    return Copy-VibeSkillExecutionLockDispatchRecord `
        -Record ([pscustomobject]@{
            skill_id = [string]$SkillId
            task_slice = ('Resolve locked specialist execution for {0}.' -f [string]$SkillId)
            dispatch_phase = 'in_execution'
            write_scope = ('specialist:{0}' -f [string]$SkillId)
            verification_expectation = 'Resolve locked specialist execution before delivery acceptance.'
        }) `
        -LockSource $LockSource `
        -ReconciliationState $ReconciliationState
}

function Add-VibeSkillExecutionLockRecord {
    param(
        [Parameter(Mandatory)] [System.Collections.Generic.List[object]]$Rows,
        [Parameter(Mandatory)] [hashtable]$Seen,
        [AllowNull()] [object]$Record = $null
    )

    if ($null -eq $Record -or -not (Test-VibeObjectHasProperty -InputObject $Record -PropertyName 'skill_id')) {
        return
    }
    $skillId = [string]$Record.skill_id
    if ([string]::IsNullOrWhiteSpace($skillId) -or $Seen.ContainsKey($skillId)) {
        return
    }
    $Rows.Add($Record) | Out-Null
    $Seen[$skillId] = $true
}

function Get-VibeSkillExecutionLockCandidateRecords {
    param(
        [AllowNull()] [object]$SkillRouting = $null
    )

    if ($null -eq $SkillRouting) {
        return @()
    }
    $rows = @()
    foreach ($propertyName in @('selected', 'candidates', 'rejected')) {
        if (Test-VibeObjectHasProperty -InputObject $SkillRouting -PropertyName $propertyName) {
            $rows += @($SkillRouting.$propertyName)
        }
    }
    return @($rows | Where-Object { $null -ne $_ })
}

function New-VibeSkillExecutionLockProjection {
    param(
        [AllowNull()] [object]$PreviousRuntimeInputPacket = $null,
        [AllowNull()] [object]$CurrentSkillRouting = $null,
        [AllowNull()] [object]$HostSpecialistDispatchDecision = $null,
        [AllowEmptyString()] [string]$SourceRunId = '',
        [AllowEmptyString()] [string]$Source = 'current_skill_routing_selected'
    )

    $rows = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    $currentRecords = @(Get-VibeSkillExecutionLockCandidateRecords -SkillRouting $CurrentSkillRouting)
    $currentSkillIds = @($currentRecords | ForEach-Object {
        if (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id') { [string]$_.skill_id } else { '' }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    $hostApproved = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'approved_skill_ids')) {
        @(Get-VibeNormalizedStringList -Values $HostSpecialistDispatchDecision.approved_skill_ids)
    } else {
        @()
    }
    if (@($hostApproved).Count -gt 0) {
        foreach ($skillId in @($hostApproved)) {
            $sourceRecord = @($currentRecords | Where-Object {
                (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id') -and
                [string]::Equals([string]$_.skill_id, [string]$skillId, [System.StringComparison]::OrdinalIgnoreCase)
            } | Select-Object -First 1)
            $record = if (@($sourceRecord).Count -gt 0) {
                Copy-VibeSkillExecutionLockDispatchRecord -Record $sourceRecord[0] -LockSource 'host_decision' -ReconciliationState 'current_surfaced'
            } else {
                New-VibeMinimalSkillExecutionLockDispatchRecord -SkillId $skillId -LockSource 'host_decision' -ReconciliationState 'host_approved_not_currently_surfaced'
            }
            Add-VibeSkillExecutionLockRecord -Rows $rows -Seen $seen -Record $record
        }
    } else {
        $previousLock = Get-VibeSkillExecutionLockFromRuntimeInputPacket -RuntimeInputPacket $PreviousRuntimeInputPacket
        if (Test-VibeSkillExecutionLockActive -SkillExecutionLock $previousLock) {
            foreach ($entry in @($previousLock.locked_dispatch)) {
                $skillId = if (Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'skill_id') { [string]$entry.skill_id } else { '' }
                $state = if ($skillId -in @($currentSkillIds)) { 'current_surfaced' } else { 'inherited_not_currently_surfaced' }
                Add-VibeSkillExecutionLockRecord -Rows $rows -Seen $seen -Record (Copy-VibeSkillExecutionLockDispatchRecord -Record $entry -LockSource 'previous_skill_execution_lock' -ReconciliationState $state)
            }
        } elseif ($null -ne $PreviousRuntimeInputPacket -and (Test-VibeObjectHasProperty -InputObject $PreviousRuntimeInputPacket -PropertyName 'skill_routing') -and $null -ne $PreviousRuntimeInputPacket.skill_routing) {
            foreach ($entry in @(Get-VibeSkillRoutingSelected -RuntimeInputPacket $PreviousRuntimeInputPacket)) {
                $skillId = if (Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'skill_id') { [string]$entry.skill_id } else { '' }
                $state = if ($skillId -in @($currentSkillIds)) { 'current_surfaced' } else { 'inherited_not_currently_surfaced' }
                Add-VibeSkillExecutionLockRecord -Rows $rows -Seen $seen -Record (Copy-VibeSkillExecutionLockDispatchRecord -Record $entry -LockSource 'previous_skill_routing_selected' -ReconciliationState $state)
            }
        }
        if (@($rows.ToArray()).Count -eq 0 -and $null -ne $CurrentSkillRouting) {
            foreach ($entry in @(Get-VibeSkillRoutingSelected -SkillRouting $CurrentSkillRouting)) {
                Add-VibeSkillExecutionLockRecord -Rows $rows -Seen $seen -Record (Copy-VibeSkillExecutionLockDispatchRecord -Record $entry -LockSource 'current_skill_routing_selected' -ReconciliationState 'current_surfaced')
            }
        }
    }

    $lockedDispatch = [object[]]$rows.ToArray()
    $lockedSkillIds = [object[]]@($lockedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $state = if (@($lockedSkillIds).Count -gt 0) { 'active' } else { 'inactive' }
    return [pscustomobject]@{
        schema_version = 'v1'
        state = $state
        source = if ([string]::IsNullOrWhiteSpace($Source)) { 'current_skill_routing_selected' } else { [string]$Source }
        source_run_id = if ([string]::IsNullOrWhiteSpace($SourceRunId)) { $null } else { [string]$SourceRunId }
        locked_skill_ids = @($lockedSkillIds)
        locked_dispatch = @($lockedDispatch)
        resolution_required = [bool](@($lockedSkillIds).Count -gt 0)
        resolution_states = @('executed', 'not_applicable', 'deferred', 'failed')
    }
}

function New-VibeSkillExecutionLockSummaryProjection {
    param(
        [AllowNull()] [object]$SkillExecutionLock = $null
    )

    $active = Test-VibeSkillExecutionLockActive -SkillExecutionLock $SkillExecutionLock
    $lockedSkillIds = if ($active -and (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'locked_skill_ids')) { @($SkillExecutionLock.locked_skill_ids) } else { @() }
    return [pscustomobject]@{
        active = [bool]$active
        locked_skill_count = @($lockedSkillIds).Count
        locked_skill_ids = @($lockedSkillIds)
        source = if ($active -and (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'source')) { [string]$SkillExecutionLock.source } else { $null }
        source_run_id = if ($active -and (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'source_run_id')) { [string]$SkillExecutionLock.source_run_id } else { $null }
        resolution_required = if ($active -and (Test-VibeObjectHasProperty -InputObject $SkillExecutionLock -PropertyName 'resolution_required')) { [bool]$SkillExecutionLock.resolution_required } else { $false }
    }
}
```

- [ ] **Step 2: Run the helper tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py::SkillExecutionLockContractTests::test_lock_projection_preserves_previous_selected_when_current_router_differs tests/runtime_neutral/test_skill_execution_lock_contract.py::SkillExecutionLockContractTests::test_lock_projection_prefers_explicit_host_decision -q
```

Expected:

```text
2 passed
```

- [ ] **Step 3: Commit helper implementation**

Run:

```powershell
git add scripts/runtime/VibeRuntime.Common.ps1 tests/runtime_neutral/test_skill_execution_lock_contract.py
git commit -m "feat: add specialist execution lock helpers"
```

Expected:

```text
Commit succeeds and prints subject `feat: add specialist execution lock helpers`.
```

---

### Task 3: Add Lock-To-Dispatch Conversion

**Files:**

- Modify: `scripts/runtime/VibeSkillRouting.Common.ps1`
- Test: `tests/runtime_neutral/test_skill_execution_lock_contract.py`

- [ ] **Step 1: Add conversion helper**

In `scripts/runtime/VibeSkillRouting.Common.ps1`, add this function after `Convert-VibeSkillRoutingSelectedToDispatch`:

```powershell
function Convert-VibeSkillExecutionLockToDispatch {
    param(
        [AllowNull()] [object]$SkillExecutionLock = $null
    )

    if ($null -eq $SkillExecutionLock) {
        return @()
    }

    $state = [string](Get-VibeSkillRoutingProperty -InputObject $SkillExecutionLock -PropertyName 'state' -DefaultValue '')
    if (-not [string]::Equals($state, 'active', [System.StringComparison]::OrdinalIgnoreCase)) {
        return @()
    }

    $lockedDispatch = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $SkillExecutionLock -PropertyName 'locked_dispatch' -DefaultValue @())
    return [object[]]@($lockedDispatch | ForEach-Object {
        $entry = $_
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            return
        }
        [pscustomobject]@{
            skill_id = $skillId
            phase_id = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'phase_id' -DefaultValue $null
            reason = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'reason' -DefaultValue '')
            task_slice = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'task_slice' -DefaultValue ('Resolve locked specialist execution for {0}.' -f $skillId))
            native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_skill_entrypoint' -DefaultValue $null
            skill_md_path = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_md_path' -DefaultValue $null
            dispatch_phase = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
            parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
            native_usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true)
            usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'usage_required' -DefaultValue (Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true))
            skill_root = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_root' -DefaultValue $null
            bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
            must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'must_preserve_workflow' -DefaultValue $true)
            binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
            lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'lane_policy' -DefaultValue 'native_contract')
            write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $skillId))
            review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'review_mode' -DefaultValue 'native_contract')
            execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'execution_priority' -DefaultValue 50)
            required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'required_inputs' -DefaultValue @())
            expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'expected_outputs' -DefaultValue @())
            verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'verification_expectation' -DefaultValue 'Resolve locked specialist execution before completion.')
            progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'progressive_load_policy' -DefaultValue @())
            locked_for_execution = $true
            lock_source = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'lock_source' -DefaultValue 'skill_execution_lock')
            reconciliation_state = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'reconciliation_state' -DefaultValue 'current_surfaced')
            requires_resolution = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'requires_resolution' -DefaultValue $true)
        }
    } | Where-Object { $null -ne $_ })
}
```

- [ ] **Step 2: Run conversion tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py::SkillExecutionLockContractTests::test_convert_lock_to_dispatch_preserves_dispatch_fields -q
```

Expected:

```text
1 passed
```

- [ ] **Step 3: Commit conversion helper**

Run:

```powershell
git add scripts/runtime/VibeSkillRouting.Common.ps1
git commit -m "feat: convert specialist execution locks to dispatch"
```

Expected:

```text
Commit succeeds and prints subject `feat: convert specialist execution locks to dispatch`.
```

---

### Task 4: Create Lock During Runtime Packet Freeze

**Files:**

- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- Test: `tests/runtime_neutral/test_skill_execution_lock_contract.py`

- [ ] **Step 1: Load previous runtime packet before packet projection**

In `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, after the multiline assignment that starts with `$hostSpecialistDispatchDecision = Resolve-VibeHostSkillExecutionDecision`, add:

```powershell
$lockSourceRunId = if (
    $null -ne $continuationContext -and
    (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'source_run_id') -and
    -not [string]::IsNullOrWhiteSpace([string]$continuationContext.source_run_id)
) {
    [string]$continuationContext.source_run_id
} else {
    ''
}
$previousRuntimeInputPacket = Get-VibeRuntimeInputPacketFromSessionRunId `
    -ArtifactRoot $ArtifactRoot `
    -SourceRunId $lockSourceRunId
```

- [ ] **Step 2: Construct lock after current `$skillRouting` is built**

In `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, immediately after the multiline assignment that starts with `$skillRouting = New-VibeSkillRoutingFromLegacy`, add:

```powershell
$lockSource = if (-not [string]::IsNullOrWhiteSpace($lockSourceRunId)) {
    'approved_plan_reentry'
} else {
    'current_skill_routing_selected'
}
$skillExecutionLock = New-VibeSkillExecutionLockProjection `
    -PreviousRuntimeInputPacket $previousRuntimeInputPacket `
    -CurrentSkillRouting $skillRouting `
    -HostSpecialistDispatchDecision $hostSpecialistDispatchDecision `
    -SourceRunId $lockSourceRunId `
    -Source $lockSource
```

- [ ] **Step 3: Pass the lock into the runtime packet projection**

In the `New-VibeRuntimeInputPacketProjection` call in `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, add:

```powershell
    -SkillExecutionLock $skillExecutionLock `
```

- [ ] **Step 4: Add the projection parameter and output field**

In `New-VibeRuntimeInputPacketProjection` in `scripts/runtime/VibeRuntime.Common.ps1`, add a parameter:

```powershell
[AllowNull()] [object]$SkillExecutionLock = $null,
```

Then add this field in the returned packet object near `skill_routing`:

```powershell
skill_execution_lock = if ($null -ne $SkillExecutionLock) { $SkillExecutionLock } else { $null }
skill_execution_lock_summary = New-VibeSkillExecutionLockSummaryProjection -SkillExecutionLock $SkillExecutionLock
```

- [ ] **Step 5: Run freeze inheritance test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py::SkillExecutionLockContractTests::test_freeze_inherits_previous_plan_selection_into_execution_lock -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Run existing freeze contract tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_skill_promotion_freeze_contract.py tests/runtime_neutral/test_structured_bounded_reentry_continuation.py -q
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit freeze integration**

Run:

```powershell
git add scripts/runtime/Freeze-RuntimeInputPacket.ps1 scripts/runtime/VibeRuntime.Common.ps1 tests/runtime_neutral/test_skill_execution_lock_contract.py
git commit -m "feat: freeze specialist execution lock across reentry"
```

Expected:

```text
Commit succeeds and prints subject `feat: freeze specialist execution lock across reentry`.
```

---

### Task 5: Prefer Lock Dispatch During Plan Execution

**Files:**

- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Test: `tests/runtime_neutral/test_skill_execution_lock_contract.py`
- Test: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

- [ ] **Step 1: Add plan-execute lock contract test**

Append this test method to `SkillExecutionLockContractTests` in `tests/runtime_neutral/test_skill_execution_lock_contract.py`:

```python
    def test_lock_dispatch_is_preferred_over_current_router_selection_projection(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$runtimePacket = [pscustomobject]@{ "
            "  skill_execution_lock = [pscustomobject]@{ "
            "    schema_version = 'v1'; state = 'active'; resolution_required = $true; "
            "    locked_dispatch = @([pscustomobject]@{ "
            "      skill_id = 'scientific-reporting'; task_slice = 'locked report'; dispatch_phase = 'post_execution'; "
            "      write_scope = 'specialist:scientific-reporting'; verification_expectation = 'report evidence' "
            "    }) "
            "  }; "
            "  skill_routing = [pscustomobject]@{ "
            "    selected = @([pscustomobject]@{ skill_id = 'latex-submission-pipeline'; task_slice = 'current pdf'; dispatch_phase = 'post_execution' }) "
            "  } "
            "}; "
            "$lockDispatch = Convert-VibeSkillExecutionLockToDispatch -SkillExecutionLock $runtimePacket.skill_execution_lock; "
            "$currentDispatch = Convert-VibeSkillRoutingSelectedToDispatch -RuntimeInputPacket $runtimePacket -SkillRouting $runtimePacket.skill_routing; "
            "[pscustomobject]@{ lock_dispatch = $lockDispatch; current_dispatch = $currentDispatch } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["scientific-reporting"], [item["skill_id"] for item in as_list(payload["lock_dispatch"])])
        self.assertEqual(["latex-submission-pipeline"], [item["skill_id"] for item in as_list(payload["current_dispatch"])])
```

- [ ] **Step 2: Change plan execution dispatch source order**

In `scripts/runtime/Invoke-PlanExecute.ps1`, after `$skillRouting` is resolved and before the current `$selectedSkills = @(Convert-VibeSkillRoutingSelectedToDispatch -RuntimeInputPacket $runtimeInputPacket -SkillRouting $skillRouting)` assignment, add:

```powershell
$skillExecutionLock = Get-VibeSkillExecutionLockFromRuntimeInputPacket -RuntimeInputPacket $runtimeInputPacket
$lockSelectedSkills = @(Convert-VibeSkillExecutionLockToDispatch -SkillExecutionLock $skillExecutionLock)
$hasActiveSkillExecutionLock = Test-VibeSkillExecutionLockActive -SkillExecutionLock $skillExecutionLock
```

Replace:

```powershell
$selectedSkills = @(Convert-VibeSkillRoutingSelectedToDispatch -RuntimeInputPacket $runtimeInputPacket -SkillRouting $skillRouting)
```

with:

```powershell
$selectedSkills = if ($hasActiveSkillExecutionLock -and @($lockSelectedSkills).Count -gt 0) {
    @($lockSelectedSkills)
} else {
    @(Convert-VibeSkillRoutingSelectedToDispatch -RuntimeInputPacket $runtimeInputPacket -SkillRouting $skillRouting)
}
```

Replace:

```powershell
$hasCanonicalSelectedSkills = $null -ne $skillRouting -and $skillRouting.PSObject.Properties.Name -contains 'selected' -and @($skillRouting.selected).Count -gt 0
```

with:

```powershell
$hasCanonicalSelectedSkills = (
    ($hasActiveSkillExecutionLock -and @($selectedSkills).Count -gt 0) -or
    ($null -ne $skillRouting -and $skillRouting.PSObject.Properties.Name -contains 'selected' -and @($skillRouting.selected).Count -gt 0)
)
```

Inside the `$specialistDispatchResolution = [pscustomobject]@{` block used when `$hasCanonicalSelectedSkills` is true, replace:

```powershell
reason = 'skill_routing_selected_is_authority'
```

with:

```powershell
reason = if ($hasActiveSkillExecutionLock) { 'skill_execution_lock_is_authority' } else { 'skill_routing_selected_is_authority' }
```

- [ ] **Step 3: Emit lock accounting into execution manifest**

Before the `$executionManifest = [pscustomobject]@{` assignment, compute:

```powershell
$lockedSkillIds = if ($hasActiveSkillExecutionLock -and $skillExecutionLock.PSObject.Properties.Name -contains 'locked_skill_ids') { @($skillExecutionLock.locked_skill_ids) } else { @() }
$executedLockedSkillIds = @($verifiedSpecialistUnits | ForEach-Object {
    if ($_.PSObject.Properties.Name -contains 'skill_id') { [string]$_.skill_id } else { '' }
} | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -in @($lockedSkillIds) } | Select-Object -Unique)
$failedLockedSkillIds = @($failedLiveSpecialistUnits | ForEach-Object {
    if ($_.PSObject.Properties.Name -contains 'skill_id') { [string]$_.skill_id } else { '' }
} | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -in @($lockedSkillIds) } | Select-Object -Unique)
$resolvedLockedSkillIds = @(@($executedLockedSkillIds) + @($failedLockedSkillIds) | Select-Object -Unique)
$unresolvedLockedSkillIds = @($lockedSkillIds | Where-Object { $_ -notin @($resolvedLockedSkillIds) })
$specialistLockResolution = [pscustomobject]@{
    active = [bool]$hasActiveSkillExecutionLock
    locked_skill_ids = @($lockedSkillIds)
    executed_skill_ids = @($executedLockedSkillIds)
    not_applicable_skill_ids = @()
    deferred_skill_ids = @()
    failed_skill_ids = @($failedLockedSkillIds)
    unresolved_skill_ids = @($unresolvedLockedSkillIds)
    delivery_blocking = [bool](@($unresolvedLockedSkillIds).Count -gt 0 -or @($failedLockedSkillIds).Count -gt 0)
}
```

Add these fields to `specialist_accounting` in the execution manifest:

```powershell
skill_execution_lock = $skillExecutionLock
skill_execution_lock_active = [bool]$hasActiveSkillExecutionLock
skill_execution_lock_summary = New-VibeSkillExecutionLockSummaryProjection -SkillExecutionLock $skillExecutionLock
specialist_lock_resolution = $specialistLockResolution
```

Also add top-level:

```powershell
skill_execution_lock = $skillExecutionLock
specialist_lock_resolution = $specialistLockResolution
```

- [ ] **Step 4: Run focused plan-execute tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py tests/runtime_neutral/test_l_xl_native_execution_topology.py::NativeExecutionTopologyTests::test_approved_specialist_dispatch_requires_executable_native_units -q
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit plan-execute integration**

Run:

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_skill_execution_lock_contract.py
git commit -m "feat: prefer specialist execution lock in plan execute"
```

Expected:

```text
Commit succeeds and prints subject `feat: prefer specialist execution lock in plan execute`.
```

---

### Task 6: Enforce Lock Resolution In Delivery Acceptance

**Files:**

- Modify: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
- Modify: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`

- [ ] **Step 1: Extend delivery acceptance test fixture**

In `RuntimeDeliveryAcceptanceTests._build_session` in `tests/runtime_neutral/test_runtime_delivery_acceptance.py`, add parameters:

```python
        skill_execution_lock: dict[str, object] | None = None,
        specialist_lock_resolution: dict[str, object] | None = None,
```

After `execution_manifest_payload` is initialized, add:

```python
        if specialist_lock_resolution is not None:
            execution_manifest_payload["specialist_lock_resolution"] = specialist_lock_resolution
```

After `runtime_input_packet_payload` is initialized, add:

```python
        if skill_execution_lock is not None:
            runtime_input_packet_payload["skill_execution_lock"] = skill_execution_lock
```

- [ ] **Step 2: Add delivery acceptance tests**

Append these tests to `RuntimeDeliveryAcceptanceTests`:

```python
    def test_runtime_delivery_acceptance_fails_when_locked_specialist_is_unresolved(self) -> None:
        skill_path = "/tmp/scientific-reporting/SKILL.md"
        session_root = self._build_session(
            approved_dispatch=[
                {
                    "skill_id": "scientific-reporting",
                    "native_skill_entrypoint": skill_path,
                }
            ],
            phase_execute_specialist_user_disclosure={
                "scope": "selected_skill_execution_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "scientific-reporting",
                        "native_skill_entrypoint": skill_path,
                        "entrypoint_requirement_satisfied": True,
                    }
                ],
            },
            skill_execution_lock={
                "schema_version": "v1",
                "state": "active",
                "locked_skill_ids": ["scientific-reporting"],
                "locked_dispatch": [{"skill_id": "scientific-reporting", "native_skill_entrypoint": skill_path}],
                "resolution_required": True,
            },
            specialist_lock_resolution={
                "active": True,
                "locked_skill_ids": ["scientific-reporting"],
                "executed_skill_ids": [],
                "not_applicable_skill_ids": [],
                "deferred_skill_ids": [],
                "failed_skill_ids": [],
                "unresolved_skill_ids": ["scientific-reporting"],
                "delivery_blocking": True,
            },
            phase_execute_specialist_decision={
                "decision_state": "approved_dispatch",
                "resolution_mode": "approved_dispatch",
                "approved_dispatch_skill_ids": ["scientific-reporting"],
            },
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("FAIL", report["summary"]["gate_result"])
        self.assertIn("specialist_lock_resolution_truth", report["truth_results"])
        self.assertEqual("failing", report["truth_results"]["specialist_lock_resolution_truth"]["state"])
        self.assertIn("scientific-reporting", report["execution_context"]["specialist_lock_unresolved_skill_ids"])

    def test_runtime_delivery_acceptance_passes_when_locked_specialist_is_executed(self) -> None:
        skill_path = "/tmp/scientific-reporting/SKILL.md"
        session_root = self._build_session(
            run_id="pytest-specialist-lock-pass",
            approved_dispatch=[
                {
                    "skill_id": "scientific-reporting",
                    "native_skill_entrypoint": skill_path,
                }
            ],
            phase_execute_specialist_user_disclosure={
                "scope": "selected_skill_execution_only",
                "timing": "before_execution",
                "path_source": "native_skill_entrypoint",
                "routed_skills": [
                    {
                        "skill_id": "scientific-reporting",
                        "native_skill_entrypoint": skill_path,
                        "entrypoint_requirement_satisfied": True,
                    }
                ],
            },
            specialist_accounting={
                "selected_skill_execution": [
                    {
                        "skill_id": "scientific-reporting",
                        "native_skill_entrypoint": skill_path,
                    }
                ],
                "selected_skill_execution_count": 1,
                "effective_execution_status": "direct_current_session_routed",
                "direct_routed_skill_execution_units": [
                    {
                        "unit_id": "unit-1",
                        "skill_id": "scientific-reporting",
                        "result_path": "specialist-results/scientific-reporting.json",
                    }
                ],
            },
            skill_execution_lock={
                "schema_version": "v1",
                "state": "active",
                "locked_skill_ids": ["scientific-reporting"],
                "locked_dispatch": [{"skill_id": "scientific-reporting", "native_skill_entrypoint": skill_path}],
                "resolution_required": True,
            },
            specialist_lock_resolution={
                "active": True,
                "locked_skill_ids": ["scientific-reporting"],
                "executed_skill_ids": ["scientific-reporting"],
                "not_applicable_skill_ids": [],
                "deferred_skill_ids": [],
                "failed_skill_ids": [],
                "unresolved_skill_ids": [],
                "delivery_blocking": False,
            },
            phase_execute_specialist_decision={
                "decision_state": "approved_dispatch",
                "resolution_mode": "approved_dispatch",
                "approved_dispatch_skill_ids": ["scientific-reporting"],
            },
            sidecar_specialist_execution={
                "protocol_version": "v1",
                "source_run_id": "pytest-specialist-lock-pass",
                "resolution_mode": "current_session_host_execution",
                "evidence_paths": ["/tmp/pytest-specialist-lock-pass.md"],
                "units": [
                    {
                        "unit_id": "unit-1",
                        "skill_id": "scientific-reporting",
                        "resolution_state": "executed",
                        "native_skill_entrypoint": skill_path,
                        "evidence_paths": ["/tmp/pytest-scientific-reporting.txt"],
                    }
                ],
            },
        )

        report = evaluate(REPO_ROOT, session_root)

        self.assertEqual("PASS", report["summary"]["gate_result"])
        self.assertEqual("passing", report["truth_results"]["specialist_lock_resolution_truth"]["state"])
        self.assertEqual([], report["execution_context"]["specialist_lock_unresolved_skill_ids"])
```

- [ ] **Step 3: Run tests and confirm they fail before evaluator changes**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py::RuntimeDeliveryAcceptanceTests::test_runtime_delivery_acceptance_fails_when_locked_specialist_is_unresolved tests/runtime_neutral/test_runtime_delivery_acceptance.py::RuntimeDeliveryAcceptanceTests::test_runtime_delivery_acceptance_passes_when_locked_specialist_is_executed -q
```

Expected:

```text
FAILED
```

The failure should show missing `specialist_lock_resolution_truth` or missing execution context fields.

- [ ] **Step 4: Add delivery evaluator logic**

In `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`, add helper functions near the existing specialist helper section:

```python
def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = [value]
    result: list[str] = []
    for item in raw_values:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _load_skill_execution_lock(runtime_packet: dict[str, object], execution_manifest: dict[str, object]) -> dict[str, object]:
    manifest_lock = execution_manifest.get("skill_execution_lock")
    if isinstance(manifest_lock, dict):
        return manifest_lock
    accounting = execution_manifest.get("specialist_accounting")
    if isinstance(accounting, dict):
        accounting_lock = accounting.get("skill_execution_lock")
        if isinstance(accounting_lock, dict):
            return accounting_lock
    packet_lock = runtime_packet.get("skill_execution_lock")
    if isinstance(packet_lock, dict):
        return packet_lock
    return {}


def _load_specialist_lock_resolution(execution_manifest: dict[str, object]) -> dict[str, object]:
    manifest_resolution = execution_manifest.get("specialist_lock_resolution")
    if isinstance(manifest_resolution, dict):
        return manifest_resolution
    accounting = execution_manifest.get("specialist_accounting")
    if isinstance(accounting, dict):
        accounting_resolution = accounting.get("specialist_lock_resolution")
        if isinstance(accounting_resolution, dict):
            return accounting_resolution
    return {}


def _evaluate_specialist_lock_resolution(
    skill_execution_lock: dict[str, object],
    specialist_lock_resolution: dict[str, object],
) -> tuple[str, list[str], dict[str, list[str]]]:
    state = str(skill_execution_lock.get("state") or "").strip().lower()
    locked_skill_ids = _normalize_string_list(skill_execution_lock.get("locked_skill_ids"))
    active = state == "active" and bool(locked_skill_ids)
    if not active:
        return "passing", ["No active specialist execution lock was present."], {
            "locked": [],
            "executed": [],
            "not_applicable": [],
            "deferred": [],
            "failed": [],
            "unresolved": [],
        }

    executed = _normalize_string_list(specialist_lock_resolution.get("executed_skill_ids"))
    not_applicable = _normalize_string_list(specialist_lock_resolution.get("not_applicable_skill_ids"))
    deferred = _normalize_string_list(specialist_lock_resolution.get("deferred_skill_ids"))
    failed = _normalize_string_list(specialist_lock_resolution.get("failed_skill_ids"))
    explicitly_unresolved = _normalize_string_list(specialist_lock_resolution.get("unresolved_skill_ids"))
    resolved = set(executed) | set(not_applicable) | set(deferred) | set(failed)
    unresolved = [skill_id for skill_id in locked_skill_ids if skill_id not in resolved]
    for skill_id in explicitly_unresolved:
        if skill_id not in unresolved:
            unresolved.append(skill_id)

    if failed:
        return "failing", [f"Locked specialist execution failed for: {', '.join(failed)}."], {
            "locked": locked_skill_ids,
            "executed": executed,
            "not_applicable": not_applicable,
            "deferred": deferred,
            "failed": failed,
            "unresolved": unresolved,
        }
    if unresolved:
        return "failing", [f"Locked specialist execution is unresolved for: {', '.join(unresolved)}."], {
            "locked": locked_skill_ids,
            "executed": executed,
            "not_applicable": not_applicable,
            "deferred": deferred,
            "failed": failed,
            "unresolved": unresolved,
        }
    if deferred:
        return "manual_review_required", [f"Locked specialist execution was deferred for: {', '.join(deferred)}."], {
            "locked": locked_skill_ids,
            "executed": executed,
            "not_applicable": not_applicable,
            "deferred": deferred,
            "failed": failed,
            "unresolved": unresolved,
        }
    return "passing", ["All locked specialist execution obligations were resolved."], {
        "locked": locked_skill_ids,
        "executed": executed,
        "not_applicable": not_applicable,
        "deferred": deferred,
        "failed": failed,
        "unresolved": unresolved,
    }
```

In `evaluate`, after `runtime_packet` and `execution_manifest` are loaded, call:

```python
skill_execution_lock = _load_skill_execution_lock(runtime_packet, execution_manifest)
specialist_lock_resolution = _load_specialist_lock_resolution(execution_manifest)
specialist_lock_state, specialist_lock_notes, specialist_lock_lists = _evaluate_specialist_lock_resolution(
    skill_execution_lock,
    specialist_lock_resolution,
)
```

Add a truth layer:

```python
"specialist_lock_resolution_truth": {
    "state": _normalize_truth_state(specialist_lock_state),
    "evidence": [],
    "notes": " ".join(specialist_lock_notes).strip(),
},
```

Add execution context fields:

```python
"specialist_lock_active": bool(specialist_lock_lists["locked"]),
"specialist_lock_skill_ids": specialist_lock_lists["locked"],
"specialist_lock_executed_skill_ids": specialist_lock_lists["executed"],
"specialist_lock_not_applicable_skill_ids": specialist_lock_lists["not_applicable"],
"specialist_lock_deferred_skill_ids": specialist_lock_lists["deferred"],
"specialist_lock_failed_skill_ids": specialist_lock_lists["failed"],
"specialist_lock_unresolved_skill_ids": specialist_lock_lists["unresolved"],
```

- [ ] **Step 5: Run delivery acceptance lock tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py::RuntimeDeliveryAcceptanceTests::test_runtime_delivery_acceptance_fails_when_locked_specialist_is_unresolved tests/runtime_neutral/test_runtime_delivery_acceptance.py::RuntimeDeliveryAcceptanceTests::test_runtime_delivery_acceptance_passes_when_locked_specialist_is_executed -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Run delivery acceptance suite**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit delivery acceptance enforcement**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py tests/runtime_neutral/test_runtime_delivery_acceptance.py
git commit -m "feat: enforce specialist execution lock resolution"
```

Expected:

```text
Commit succeeds and prints subject `feat: enforce specialist execution lock resolution`.
```

---

### Task 7: Update Current Routing Documentation

**Files:**

- Modify: `docs/governance/current-routing-contract.md`
- Modify: `docs/governance/current-runtime-field-contract.md`
- Modify: `docs/governance/terminology-governance.md`
- Modify: `tests/runtime_neutral/test_current_routing_docs_entrypoint.py`
- Modify: `tests/runtime_neutral/test_terminology_field_simplification.py`
- Modify: `tests/runtime_neutral/test_current_routing_contract_cleanup.py`

- [ ] **Step 1: Update current routing docs assertions first**

In `tests/runtime_neutral/test_current_routing_docs_entrypoint.py`, replace the chain assertions with:

```python
    assert (
        "skill_candidates -> skill_routing.selected -> skill_execution_lock -> "
        "selected_skill_execution -> skill_usage.used / skill_usage.unused"
    ) in text
    assert "`skill_execution_lock` | The approved-plan execution lock that preserves selected specialists across bounded re-entry. It is not a use claim." in text
```

In the runtime field test in the same file, assert:

```python
    assert (
        "skill_candidates -> skill_routing.selected -> skill_execution_lock -> "
        "selected_skill_execution -> skill_usage.used / skill_usage.unused"
    ) in text
    assert "`skill_execution_lock` records specialists that crossed the approved-plan boundary" in text
```

In `tests/runtime_neutral/test_terminology_field_simplification.py`, replace the active model assertion with:

```python
    assert "skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage" in text
    assert "`skill_execution_lock`" in text
```

In `tests/runtime_neutral/test_current_routing_contract_cleanup.py`, update the expected model string to:

```python
"skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused"
```

- [ ] **Step 2: Run doc tests and confirm they fail**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_docs_entrypoint.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
```

Expected:

```text
FAILED
```

Failures should point to missing `skill_execution_lock` text in docs.

- [ ] **Step 3: Update `current-routing-contract.md`**

In `docs/governance/current-routing-contract.md`, change the current chain to:

```text
skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused
```

Add or update the field table row:

```markdown
| `skill_execution_lock` | The approved-plan execution lock that preserves selected specialists across bounded re-entry. It is not a use claim. |
```

Add this paragraph near the field definitions:

```markdown
`skill_execution_lock` exists because bounded re-entry reruns the router. Once a plan is approved, selected specialists become execution obligations and must be executed, marked not applicable, deferred, or failed before delivery acceptance can pass. The lock does not prove material skill use; `skill_usage.used` remains the only material-use truth.
```

- [ ] **Step 4: Update `current-runtime-field-contract.md`**

In `docs/governance/current-runtime-field-contract.md`, change the current chain to:

```text
skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused
```

Add this field definition:

```markdown
### `skill_execution_lock`

`skill_execution_lock` records specialists that crossed the approved-plan boundary and therefore require execution resolution. It contains `locked_skill_ids`, `locked_dispatch`, `source_run_id`, and `resolution_required`. It is an execution-obligation field, not a material-use field.
```

- [ ] **Step 5: Update `terminology-governance.md`**

In `docs/governance/terminology-governance.md`, change the active model sentence to:

```text
skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage
```

Add this term row:

```markdown
| `skill_execution_lock` | Current execution-obligation field that preserves approved specialists across bounded re-entry; not evidence of material skill use. |
```

- [ ] **Step 6: Run doc tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_docs_entrypoint.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit docs**

Run:

```powershell
git add docs/governance/current-routing-contract.md docs/governance/current-runtime-field-contract.md docs/governance/terminology-governance.md tests/runtime_neutral/test_current_routing_docs_entrypoint.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_current_routing_contract_cleanup.py
git commit -m "docs: document specialist execution lock contract"
```

Expected:

```text
Commit succeeds and prints subject `docs: document specialist execution lock contract`.
```

---

### Task 8: Run Full Verification Slice And Install Check

**Files:**

- No new source files.
- Verification covers files changed by Tasks 1-7.

- [ ] **Step 1: Run focused Python tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_skill_promotion_freeze_contract.py tests/runtime_neutral/test_structured_bounded_reentry_continuation.py tests/runtime_neutral/test_runtime_delivery_acceptance.py tests/runtime_neutral/test_current_routing_docs_entrypoint.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run runtime check script**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\check.ps1
```

Expected:

```text
failed 0
```

or an equivalent summary showing zero failing checks.

- [ ] **Step 3: Verify final git state**

Run:

```powershell
git status --short
git log -6 --oneline
```

Expected:

```text
```

`git status --short` should be empty after all task commits. `git log -6 --oneline` should show the specialist execution lock commits.

- [ ] **Step 4: Report implementation evidence**

In the final implementation report, include:

```text
Changed files:
- scripts/runtime/VibeRuntime.Common.ps1
- scripts/runtime/VibeSkillRouting.Common.ps1
- scripts/runtime/Freeze-RuntimeInputPacket.ps1
- scripts/runtime/Invoke-PlanExecute.ps1
- packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py
- tests/runtime_neutral/test_skill_execution_lock_contract.py
- tests/runtime_neutral/test_runtime_delivery_acceptance.py
- docs/governance/current-routing-contract.md
- docs/governance/current-runtime-field-contract.md
- docs/governance/terminology-governance.md

Verification:
- python -m pytest tests/runtime_neutral/test_skill_execution_lock_contract.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_skill_promotion_freeze_contract.py tests/runtime_neutral/test_structured_bounded_reentry_continuation.py tests/runtime_neutral/test_runtime_delivery_acceptance.py tests/runtime_neutral/test_current_routing_docs_entrypoint.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
- powershell -ExecutionPolicy Bypass -File .\check.ps1
```

Do not claim the installed Codex runtime has changed unless a separate deployment step explicitly installs this branch into `C:\Users\羽裳\.codex`.

---

## Implementation Notes For Workers

- Keep `skill_usage.used` unchanged. The lock is not a use claim.
- Preserve current `skill_routing.selected` for audit even when execution uses the lock.
- Prefer additive fields over renaming existing fields in this slice.
- Keep old runtime packets readable when `skill_execution_lock` is absent.
- Do not update historical docs unless a current test requires a narrow current-model note.
- If an exact test name differs from this plan because the upstream file changed, use `python -m pytest <file> -k "<term>" -q` to locate the nearest existing focused test, then record the actual test name in the implementation report.
