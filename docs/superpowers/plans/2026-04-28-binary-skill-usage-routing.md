# Binary Skill Usage Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a binary `used` / `unused` skill usage truth layer so routed skills are only reported as used after full `SKILL.md` load evidence and six-stage artifact impact evidence exist.

**Architecture:** Keep the public six-stage runtime unchanged. Add a focused `VibeSkillUsage.Common.ps1` helper for full skill loading, usage snapshots, artifact-impact promotion, and session-root persistence; wire it into runtime freeze, requirement, plan, execution, and delivery acceptance without rewriting router scoring.

**Tech Stack:** PowerShell runtime scripts, Python runtime-neutral tests, JSON artifacts, Markdown runtime artifacts, pytest.

---

## File Structure

- Create: `scripts/runtime/VibeSkillUsage.Common.ps1`
  - Owns binary skill usage helpers.
  - Resolves skill entrypoints, reads full `SKILL.md`, computes SHA256, creates `skill_usage`, promotes loaded skills to used when artifact evidence exists, writes/reads `skill-usage.json`.
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
  - Dot-sources `VibeSkillUsage.Common.ps1`.
  - Builds initial `skill_usage` from `route_snapshot.selected_skill`, `specialist_recommendations`, and `stage_assistant_hints`.
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
  - Adds optional `SkillUsage` parameter to `New-VibeRuntimeInputPacketProjection`.
  - Emits `skill_usage` into `runtime-input-packet.json`.
- Modify: `config/runtime-input-packet-policy.json`
  - Adds `skill_usage` to `required_fields`.
- Modify: `scripts/runtime/Write-RequirementDoc.ps1`
  - Reads current `skill_usage`, records `requirement_doc` artifact impact, writes `skill-usage.json`, and includes a concise `## Skill Usage` section.
- Modify: `scripts/runtime/Write-XlPlan.ps1`
  - Reads `skill-usage.json`, records `xl_plan` artifact impact, persists the updated snapshot, and includes a `## Binary Skill Usage Plan` section.
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
  - Reads `skill-usage.json`, records `plan_execute` impact when execution completes, includes the snapshot in `execution-manifest.json` and `phase-execute.json`.
- Modify: `scripts/runtime/Invoke-PhaseCleanup.ps1`
  - Reads `skill-usage.json` and includes final binary usage counts in `cleanup-receipt.json`.
- Modify: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
  - Validates `skill_usage` and refuses usage truth from old routing, hint, consultation, or dispatch fields.
- Modify: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
  - New focused tests for helper functions and freeze-stage runtime integration.
- Modify: `tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py`
  - New runtime-neutral tests for requirement/plan/execution propagation.
- Modify: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
  - Adds delivery-acceptance gate tests for binary skill usage.

---

### Task 1: Add Binary Skill Usage Helper With Failing Tests

**Files:**
- Create: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- Create: `scripts/runtime/VibeSkillUsage.Common.ps1`

- [ ] **Step 1: Write failing helper contract tests**

Create `tests/runtime_neutral/test_binary_skill_usage_contract.py` with:

```python
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
SKILL_USAGE_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeSkillUsage.Common.ps1"


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
    result = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class BinarySkillUsageContractTests(unittest.TestCase):
    def test_full_skill_load_records_hash_path_line_and_byte_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            skill_dir = root / "bundled" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            skill_text = "---\nname: demo-skill\ndescription: demo\n---\n# Demo\nUse the demo workflow.\n"
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(skill_text, encoding="utf-8", newline="\n")
            expected_hash = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$record = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(root))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check'; "
                "$record | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual("demo-skill", payload["skill_id"])
            self.assertEqual("loaded_full_skill_md", payload["load_status"])
            self.assertEqual(str(skill_path.resolve()), payload["skill_md_path"])
            self.assertEqual(expected_hash, payload["skill_md_sha256"])
            self.assertEqual("skeleton_check", payload["loaded_at_stage"])
            self.assertGreaterEqual(int(payload["loaded_byte_count"]), len(skill_text))
            self.assertEqual(6, int(payload["loaded_line_count"]))

    def test_artifact_impact_promotes_loaded_skill_to_used_and_removes_unused_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            skill_dir = root / "bundled" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Demo\nUse it.\n", encoding="utf-8", newline="\n")

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                f". {ps_quote(str(SKILL_USAGE_COMMON))}; "
                f"$loaded = New-VibeSkillUsageLoadedSkill -RepoRoot {ps_quote(str(root))} -SkillId 'demo-skill' -LoadedAtStage 'skeleton_check'; "
                "$usage = New-VibeInitialSkillUsage -LoadedSkills @($loaded) -TouchedSkills @([pscustomobject]@{ skill_id = 'demo-skill'; reason = 'loaded_but_no_artifact_impact' }); "
                "$usage = Update-VibeSkillUsageArtifactImpact -SkillUsage $usage -SkillId 'demo-skill' -Stage 'xl_plan' -ArtifactRef 'xl_plan.md' -ImpactSummary 'Plan follows the loaded demo skill workflow.'; "
                "$usage | ConvertTo-Json -Depth 20 "
                "}"
            )

            self.assertEqual(["demo-skill"], payload["used_skills"])
            self.assertEqual([], payload["unused_skills"])
            self.assertEqual("demo-skill", payload["evidence"][0]["skill_id"])
            self.assertEqual("xl_plan", payload["evidence"][0]["stage"])
            self.assertEqual("xl_plan.md", payload["evidence"][0]["artifact_ref"])
            self.assertIn("loaded demo skill workflow", payload["evidence"][0]["impact_summary"])
```

- [ ] **Step 2: Run helper contract tests and confirm they fail**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py -q
```

Expected: fail because `scripts/runtime/VibeSkillUsage.Common.ps1` does not exist.

- [ ] **Step 3: Create the helper implementation**

Create `scripts/runtime/VibeSkillUsage.Common.ps1` with:

```powershell
Set-StrictMode -Version Latest

function Resolve-VibeSkillUsageSkillPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $candidates = @(
        (Join-Path $RepoRoot ("bundled\skills\{0}\SKILL.md" -f $SkillId)),
        (Join-Path $RepoRoot ("bundled\skills\{0}\SKILL.runtime-mirror.md" -f $SkillId))
    )
    if ([string]::Equals($SkillId, 'vibe', [System.StringComparison]::OrdinalIgnoreCase)) {
        $candidates += (Join-Path $RepoRoot 'SKILL.md')
    }
    if (Get-Command -Name Resolve-VgoInstalledSkillsRoot -ErrorAction SilentlyContinue) {
        $installedSkillsRoot = Resolve-VgoInstalledSkillsRoot -TargetRoot $TargetRoot -HostId $HostId
        $candidates += @(
            (Join-Path $installedSkillsRoot (Join-Path $SkillId 'SKILL.md')),
            (Join-Path $installedSkillsRoot (Join-Path $SkillId 'SKILL.runtime-mirror.md')),
            (Join-Path $installedSkillsRoot (Join-Path 'custom' (Join-Path $SkillId 'SKILL.md'))),
            (Join-Path $installedSkillsRoot (Join-Path 'custom' (Join-Path $SkillId 'SKILL.runtime-mirror.md')))
        )
    }

    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

function New-VibeSkillUsageLoadedSkill {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$LoadedAtStage,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $skillPath = Resolve-VibeSkillUsageSkillPath -RepoRoot $RepoRoot -SkillId $SkillId -TargetRoot $TargetRoot -HostId $HostId
    if ([string]::IsNullOrWhiteSpace([string]$skillPath)) {
        return [pscustomobject]@{
            skill_id = $SkillId
            skill_md_path = $null
            skill_md_sha256 = $null
            load_status = 'missing_skill_md'
            loaded_at_stage = $LoadedAtStage
            loaded_byte_count = 0
            loaded_line_count = 0
            unused_reason = 'not_loaded_full_skill_md'
        }
    }

    $content = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
    $hash = (Get-FileHash -LiteralPath $skillPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $lines = if ([string]::IsNullOrEmpty($content)) { @() } else { @($content -split "`r?`n") }
    if (@($lines).Count -gt 0 -and [string]$lines[-1] -eq '') {
        $lines = @($lines | Select-Object -First (@($lines).Count - 1))
    }
    $lineCount = @($lines).Count
    $byteCount = [System.Text.Encoding]::UTF8.GetByteCount($content)
    return [pscustomobject]@{
        skill_id = $SkillId
        skill_md_path = [System.IO.Path]::GetFullPath($skillPath)
        skill_md_sha256 = $hash
        load_status = 'loaded_full_skill_md'
        loaded_at_stage = $LoadedAtStage
        loaded_byte_count = [int]$byteCount
        loaded_line_count = [int]$lineCount
    }
}

function New-VibeInitialSkillUsage {
    param(
        [AllowNull()] [object[]]$LoadedSkills = @(),
        [AllowNull()] [object[]]$TouchedSkills = @()
    )

    $loaded = @($LoadedSkills | Where-Object { $null -ne $_ })
    $loadedIds = @($loaded | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $unusedRows = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    foreach ($touch in @($TouchedSkills)) {
        if ($null -eq $touch) {
            continue
        }
        $skillId = if ($touch.PSObject.Properties.Name -contains 'skill_id') { [string]$touch.skill_id } else { '' }
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seen.ContainsKey($skillId)) {
            continue
        }
        $reason = if ($touch.PSObject.Properties.Name -contains 'reason' -and -not [string]::IsNullOrWhiteSpace([string]$touch.reason)) {
            [string]$touch.reason
        } elseif ($loadedIds -contains $skillId) {
            'loaded_but_no_artifact_impact'
        } else {
            'candidate_only'
        }
        $unusedRows.Add([pscustomobject]@{ skill_id = $skillId; reason = $reason }) | Out-Null
        $seen[$skillId] = $true
    }

    foreach ($loadedSkill in $loaded) {
        $skillId = [string]$loadedSkill.skill_id
        if (-not [string]::IsNullOrWhiteSpace($skillId) -and -not $seen.ContainsKey($skillId)) {
            $unusedRows.Add([pscustomobject]@{ skill_id = $skillId; reason = 'loaded_but_no_artifact_impact' }) | Out-Null
            $seen[$skillId] = $true
        }
    }

    return [pscustomobject]@{
        schema_version = 1
        state_model = 'binary_used_unused'
        used_skills = @()
        unused_skills = [object[]]@($unusedRows.ToArray() | ForEach-Object { [string]$_.skill_id })
        loaded_skills = [object[]]@($loaded)
        evidence = @()
        unused_reasons = [object[]]$unusedRows.ToArray()
    }
}

function Update-VibeSkillUsageArtifactImpact {
    param(
        [Parameter(Mandatory)] [object]$SkillUsage,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$ArtifactRef,
        [Parameter(Mandatory)] [string]$ImpactSummary
    )

    $usedIds = @($SkillUsage.used_skills | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($usedIds -notcontains $SkillId) {
        $usedIds += $SkillId
    }
    $unusedRows = @($SkillUsage.unused_reasons | Where-Object { [string]$_.skill_id -ne $SkillId })
    $loaded = @($SkillUsage.loaded_skills)
    $loadedRecord = @($loaded | Where-Object { [string]$_.skill_id -eq $SkillId } | Select-Object -First 1)
    $evidence = @($SkillUsage.evidence)
    $evidence += [pscustomobject]@{
        skill_id = $SkillId
        stage = $Stage
        artifact_ref = $ArtifactRef
        impact_summary = $ImpactSummary
        skill_md_path = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_path } else { $null }
        skill_md_sha256 = if (@($loadedRecord).Count -gt 0) { [string]$loadedRecord[0].skill_md_sha256 } else { $null }
    }

    return [pscustomobject]@{
        schema_version = 1
        state_model = 'binary_used_unused'
        used_skills = [object[]]@($usedIds | Select-Object -Unique)
        unused_skills = [object[]]@($unusedRows | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        loaded_skills = [object[]]$loaded
        evidence = [object[]]$evidence
        unused_reasons = [object[]]$unusedRows
    }
}

function Get-VibeSkillUsagePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )
    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'skill-usage.json'))
}

function Read-VibeSkillUsageArtifact {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$Fallback = $null
    )
    $path = Get-VibeSkillUsagePath -SessionRoot $SessionRoot
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    return $Fallback
}
```

- [ ] **Step 4: Run helper contract tests and confirm they pass**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit helper and tests**

Run:

```powershell
git add scripts/runtime/VibeSkillUsage.Common.ps1 tests/runtime_neutral/test_binary_skill_usage_contract.py
git commit -m "feat: add binary skill usage helpers"
```

Expected: commit includes only the new helper and its focused tests.

---

### Task 2: Emit Initial `skill_usage` In Runtime Freeze

**Files:**
- Modify: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
- Modify: `config/runtime-input-packet-policy.json`
- Test: `tests/runtime_neutral/test_bundled_stage_assistant_freeze.py`
- Test: `tests/runtime_neutral/test_runtime_contract_schema.py`

- [ ] **Step 1: Add a failing freeze integration test**

Append this test method to `BinarySkillUsageContractTests` in `tests/runtime_neutral/test_binary_skill_usage_contract.py`:

```python
    def test_runtime_freeze_emits_initial_binary_skill_usage(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-binary-skill-usage-freeze"
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"),
                "-Task",
                "Use biopython to parse FASTA and summarize sequence lengths.",
                "-Mode",
                "interactive_governed",
                "-RunId",
                run_id,
                "-ArtifactRoot",
                str(artifact_root),
            ]
            subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)

            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            selected_skill = packet["route_snapshot"]["selected_skill"]
            usage = packet["skill_usage"]

            self.assertEqual("binary_used_unused", usage["state_model"])
            self.assertIn(selected_skill, [item["skill_id"] for item in usage["loaded_skills"]])
            selected_record = next(item for item in usage["loaded_skills"] if item["skill_id"] == selected_skill)
            self.assertEqual("loaded_full_skill_md", selected_record["load_status"])
            self.assertTrue(Path(selected_record["skill_md_path"]).exists())
            self.assertRegex(selected_record["skill_md_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual([], usage["used_skills"])
            self.assertIn(selected_skill, usage["unused_skills"])
            self.assertIn(
                "loaded_but_no_artifact_impact",
                [item["reason"] for item in usage["unused_reasons"] if item["skill_id"] == selected_skill],
            )
            for hint in packet["stage_assistant_hints"]:
                self.assertIn(hint["skill_id"], usage["unused_skills"])
```

- [ ] **Step 2: Run the new freeze test and confirm it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py::BinarySkillUsageContractTests::test_runtime_freeze_emits_initial_binary_skill_usage -q
```

Expected: fail because `runtime-input-packet.json` has no `skill_usage`.

- [ ] **Step 3: Dot-source the helper in freeze**

In `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, after:

```powershell
. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
```

insert:

```powershell
. (Join-Path $PSScriptRoot 'VibeSkillUsage.Common.ps1')
```

- [ ] **Step 4: Add `SkillUsage` to the runtime packet projection**

In `scripts/runtime/VibeRuntime.Common.ps1`, add this parameter to `New-VibeRuntimeInputPacketProjection` near the existing specialist parameters:

```powershell
[AllowNull()] [object]$SkillUsage = $null,
```

In the returned packet object, after `stage_assistant_hints = @($StageAssistantHints)`, add:

```powershell
skill_usage = if ($null -ne $SkillUsage) {
    $SkillUsage
} else {
    [pscustomobject]@{
        schema_version = 1
        state_model = 'binary_used_unused'
        used_skills = @()
        unused_skills = @()
        loaded_skills = @()
        evidence = @()
        unused_reasons = @()
    }
}
```

- [ ] **Step 5: Build initial skill usage before packet projection**

In `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, after `$stageAssistantHints` is assigned and before `$packet = New-VibeRuntimeInputPacketProjection`, insert:

```powershell
$skillUsageTouched = New-Object System.Collections.Generic.List[object]
if (-not [string]::IsNullOrWhiteSpace([string]$routerSelectedSkill)) {
    $skillUsageTouched.Add([pscustomobject]@{
        skill_id = [string]$routerSelectedSkill
        reason = 'loaded_but_no_artifact_impact'
    }) | Out-Null
}
foreach ($recommendation in @($specialistRecommendations)) {
    $candidateSkillId = if ($recommendation.PSObject.Properties.Name -contains 'skill_id') { [string]$recommendation.skill_id } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($candidateSkillId)) {
        $skillUsageTouched.Add([pscustomobject]@{
            skill_id = $candidateSkillId
            reason = 'recommendation_only'
        }) | Out-Null
    }
}
foreach ($hint in @($stageAssistantHints)) {
    $hintSkillId = if ($hint.PSObject.Properties.Name -contains 'skill_id') { [string]$hint.skill_id } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($hintSkillId)) {
        $skillUsageTouched.Add([pscustomobject]@{
            skill_id = $hintSkillId
            reason = 'route_hint_only'
        }) | Out-Null
    }
}

$loadedMainSkill = if (-not [string]::IsNullOrWhiteSpace([string]$routerSelectedSkill)) {
    New-VibeSkillUsageLoadedSkill `
        -RepoRoot $runtime.repo_root `
        -SkillId ([string]$routerSelectedSkill) `
        -LoadedAtStage 'skeleton_check' `
        -TargetRoot $routerTargetRoot `
        -HostId $routerHostId
} else {
    $null
}
$skillUsage = New-VibeInitialSkillUsage `
    -LoadedSkills @($(if ($null -ne $loadedMainSkill) { $loadedMainSkill } else { @() })) `
    -TouchedSkills @($skillUsageTouched.ToArray())
```

Add this argument to the `New-VibeRuntimeInputPacketProjection` call:

```powershell
-SkillUsage $skillUsage `
```

- [ ] **Step 6: Add `skill_usage` to runtime input required fields**

In `config/runtime-input-packet-policy.json`, add `skill_usage` after `stage_assistant_hints` if the list already contains that field; otherwise add it after `specialist_dispatch`:

```json
"skill_usage",
```

Keep the JSON valid and do not remove existing required fields.

- [ ] **Step 7: Run focused freeze and schema tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_bundled_stage_assistant_freeze.py tests/runtime_neutral/test_runtime_contract_schema.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit freeze integration**

Run:

```powershell
git add scripts/runtime/Freeze-RuntimeInputPacket.ps1 scripts/runtime/VibeRuntime.Common.ps1 config/runtime-input-packet-policy.json tests/runtime_neutral/test_binary_skill_usage_contract.py
git commit -m "feat: freeze binary skill usage truth"
```

Expected: commit contains only freeze-stage binary usage changes and tests.

---

### Task 3: Record Requirement And Plan Artifact Impact

**Files:**
- Create: `tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py`
- Modify: `scripts/runtime/Write-RequirementDoc.ps1`
- Modify: `scripts/runtime/Write-XlPlan.ps1`

- [ ] **Step 1: Write failing requirement and plan flow test**

Create `tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py` with:

```python
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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


class BinarySkillUsageRuntimeFlowTests(unittest.TestCase):
    def test_requirement_and_plan_promote_loaded_skill_to_used(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-binary-skill-usage-flow"
            task = "Use biopython to parse FASTA and summarize sequence lengths."
            for script_name in (
                "Freeze-RuntimeInputPacket.ps1",
                "Invoke-SkeletonCheck.ps1",
                "Invoke-DeepInterview.ps1",
                "Write-RequirementDoc.ps1",
                "Write-XlPlan.ps1",
            ):
                command = [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "scripts" / "runtime" / script_name),
                    "-Task",
                    task,
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-ArtifactRoot",
                    str(artifact_root),
                ]
                subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)

            session_root = next(artifact_root.rglob(run_id))
            packet = json.loads((session_root / "runtime-input-packet.json").read_text(encoding="utf-8"))
            selected_skill = packet["route_snapshot"]["selected_skill"]
            usage_path = session_root / "skill-usage.json"
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            requirement_receipt = json.loads((session_root / "requirement-doc-receipt.json").read_text(encoding="utf-8"))
            plan_receipt = json.loads((session_root / "execution-plan-receipt.json").read_text(encoding="utf-8"))
            requirement_text = Path(requirement_receipt["requirement_doc_path"]).read_text(encoding="utf-8")
            plan_text = Path(plan_receipt["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertIn(selected_skill, usage["used_skills"])
            self.assertNotIn(selected_skill, usage["unused_skills"])
            stages = {row["stage"] for row in usage["evidence"] if row["skill_id"] == selected_skill}
            self.assertIn("requirement_doc", stages)
            self.assertIn("xl_plan", stages)
            self.assertIn("## Skill Usage", requirement_text)
            self.assertIn("## Binary Skill Usage Plan", plan_text)
```

- [ ] **Step 2: Run the flow test and confirm it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py -q
```

Expected: fail because `skill-usage.json` is not written and docs do not include skill usage sections.

- [ ] **Step 3: Dot-source skill usage helper in requirement and plan writers**

In both `scripts/runtime/Write-RequirementDoc.ps1` and `scripts/runtime/Write-XlPlan.ps1`, after:

```powershell
. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
```

insert:

```powershell
. (Join-Path $PSScriptRoot 'VibeSkillUsage.Common.ps1')
```

- [ ] **Step 4: Update requirement doc writer to record requirement impact**

In `scripts/runtime/Write-RequirementDoc.ps1`, after the runtime input truth block is added and before specialist recommendation sections, insert:

```powershell
$skillUsage = if ($runtimeInputPacket -and $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_usage') {
    $runtimeInputPacket.skill_usage
} else {
    $null
}
$selectedUsageSkill = if ($runtimeInputPacket -and $runtimeInputPacket.route_snapshot) {
    [string]$runtimeInputPacket.route_snapshot.selected_skill
} else {
    ''
}
if ($skillUsage -and -not [string]::IsNullOrWhiteSpace($selectedUsageSkill)) {
    $skillUsage = Update-VibeSkillUsageArtifactImpact `
        -SkillUsage $skillUsage `
        -SkillId $selectedUsageSkill `
        -Stage 'requirement_doc' `
        -ArtifactRef ([System.IO.Path]::GetFileName($docPath)) `
        -ImpactSummary ('Requirement doc adopts the loaded {0} SKILL.md as the workflow authority for downstream planning and completion evidence.' -f $selectedUsageSkill)
    $lines += @(
        '',
        '## Skill Usage',
        '- Skill usage state model: binary `used` / `unused`.',
        ('- Used skill candidate: `{0}` is promoted only because full `SKILL.md` load evidence exists and this requirement doc adopts it as workflow authority.' -f $selectedUsageSkill),
        '- Routing, hints, recommendations, consultation, and dispatch do not by themselves prove skill use.',
        '- Final completion must read `skill_usage.used_skills` and `skill_usage.evidence` before claiming a skill was used.'
    )
    Write-VibeJsonArtifact -Path (Get-VibeSkillUsagePath -SessionRoot $sessionRoot) -Value $skillUsage
}
```

Add this field to the requirement receipt object:

```powershell
skill_usage_path = if ($skillUsage) { Get-VibeSkillUsagePath -SessionRoot $sessionRoot } else { $null }
skill_usage = $skillUsage
```

- [ ] **Step 5: Update XL plan writer to record plan impact**

In `scripts/runtime/Write-XlPlan.ps1`, after `$runtimeInputPacket` is loaded and `$lines` has started, insert:

```powershell
$skillUsage = if ($runtimeInputPacket -and $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_usage') {
    Read-VibeSkillUsageArtifact -SessionRoot $sessionRoot -Fallback $runtimeInputPacket.skill_usage
} else {
    Read-VibeSkillUsageArtifact -SessionRoot $sessionRoot -Fallback $null
}
$selectedUsageSkill = if ($runtimeInputPacket -and $runtimeInputPacket.route_snapshot) {
    [string]$runtimeInputPacket.route_snapshot.selected_skill
} else {
    ''
}
```

Before `## Completion Language Rules`, add:

```powershell
if ($skillUsage -and -not [string]::IsNullOrWhiteSpace($selectedUsageSkill)) {
    $skillUsage = Update-VibeSkillUsageArtifactImpact `
        -SkillUsage $skillUsage `
        -SkillId $selectedUsageSkill `
        -Stage 'xl_plan' `
        -ArtifactRef ([System.IO.Path]::GetFileName($planPath)) `
        -ImpactSummary ('Execution plan carries the loaded {0} SKILL.md workflow authority into the planned verification and completion path.' -f $selectedUsageSkill)
    $lines += @(
        '',
        '## Binary Skill Usage Plan',
        ('- Used skill candidate: `{0}`.' -f $selectedUsageSkill),
        '- Execution must preserve the loaded skill workflow and report usage only from `skill_usage`.',
        '- `approved_dispatch`, `specialist_recommendations`, `stage_assistant_hints`, and consultation receipts remain audit data, not usage proof.'
    )
    Write-VibeJsonArtifact -Path (Get-VibeSkillUsagePath -SessionRoot $sessionRoot) -Value $skillUsage
}
```

Add this field to the execution-plan receipt object:

```powershell
skill_usage_path = if ($skillUsage) { Get-VibeSkillUsagePath -SessionRoot $sessionRoot } else { $null }
skill_usage = $skillUsage
```

- [ ] **Step 6: Run runtime flow tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py tests/runtime_neutral/test_binary_skill_usage_contract.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit requirement and plan propagation**

Run:

```powershell
git add scripts/runtime/Write-RequirementDoc.ps1 scripts/runtime/Write-XlPlan.ps1 tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py
git commit -m "feat: record skill usage in requirement and plan"
```

Expected: commit contains requirement/plan propagation and the new runtime-flow test.

---

### Task 4: Propagate Skill Usage Through Execution And Cleanup

**Files:**
- Modify: `tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py`
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `scripts/runtime/Invoke-PhaseCleanup.ps1`

- [ ] **Step 1: Add failing execution propagation test**

Append this test to `BinarySkillUsageRuntimeFlowTests`:

```python
    def test_plan_execute_and_cleanup_preserve_skill_usage_truth(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-binary-skill-usage-execute"
            task = "Use biopython to parse FASTA and summarize sequence lengths."
            for script_name in (
                "Freeze-RuntimeInputPacket.ps1",
                "Invoke-SkeletonCheck.ps1",
                "Invoke-DeepInterview.ps1",
                "Write-RequirementDoc.ps1",
                "Write-XlPlan.ps1",
                "Invoke-PlanExecute.ps1",
                "Invoke-PhaseCleanup.ps1",
            ):
                command = [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "scripts" / "runtime" / script_name),
                    "-Task",
                    task,
                    "-Mode",
                    "interactive_governed",
                    "-RunId",
                    run_id,
                    "-ArtifactRoot",
                    str(artifact_root),
                ]
                subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)

            session_root = next(artifact_root.rglob(run_id))
            usage = json.loads((session_root / "skill-usage.json").read_text(encoding="utf-8"))
            execution_manifest = json.loads((session_root / "execution-manifest.json").read_text(encoding="utf-8"))
            phase_execute = json.loads((session_root / "phase-execute.json").read_text(encoding="utf-8"))
            cleanup = json.loads((session_root / "cleanup-receipt.json").read_text(encoding="utf-8"))
            selected_skill = json.loads((session_root / "runtime-input-packet.json").read_text(encoding="utf-8"))["route_snapshot"]["selected_skill"]

            self.assertIn(selected_skill, usage["used_skills"])
            self.assertEqual(usage["used_skills"], execution_manifest["skill_usage"]["used_skills"])
            self.assertEqual(usage["used_skills"], phase_execute["skill_usage"]["used_skills"])
            self.assertEqual(usage["used_skills"], cleanup["skill_usage"]["used_skills"])
            self.assertGreaterEqual(cleanup["skill_usage_summary"]["used_skill_count"], 1)
```

- [ ] **Step 2: Run execution propagation test and confirm it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py::BinarySkillUsageRuntimeFlowTests::test_plan_execute_and_cleanup_preserve_skill_usage_truth -q
```

Expected: fail because execution and cleanup artifacts do not include `skill_usage`.

- [ ] **Step 3: Dot-source helper in plan execution**

In `scripts/runtime/Invoke-PlanExecute.ps1`, after the existing `VibeRuntime.Common.ps1` dot-source, insert:

```powershell
. (Join-Path $PSScriptRoot 'VibeSkillUsage.Common.ps1')
```

- [ ] **Step 4: Read and update usage in plan execution**

In `scripts/runtime/Invoke-PlanExecute.ps1`, after `$runtimeInputPacket` is loaded and before `$executionManifest` is built, insert:

```powershell
$skillUsage = if ($runtimeInputPacket -and $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_usage') {
    Read-VibeSkillUsageArtifact -SessionRoot $sessionRoot -Fallback $runtimeInputPacket.skill_usage
} else {
    Read-VibeSkillUsageArtifact -SessionRoot $sessionRoot -Fallback $null
}
$selectedUsageSkill = if ($runtimeInputPacket -and $runtimeInputPacket.route_snapshot) {
    [string]$runtimeInputPacket.route_snapshot.selected_skill
} else {
    ''
}
if ($skillUsage -and -not [string]::IsNullOrWhiteSpace($selectedUsageSkill)) {
    $skillUsage = Update-VibeSkillUsageArtifactImpact `
        -SkillUsage $skillUsage `
        -SkillId $selectedUsageSkill `
        -Stage 'plan_execute' `
        -ArtifactRef 'execution-manifest.json' `
        -ImpactSummary ('Execution manifest preserves binary skill usage truth for {0}; execution cannot use routing, hints, consultation, or dispatch alone as usage proof.' -f $selectedUsageSkill)
    Write-VibeJsonArtifact -Path (Get-VibeSkillUsagePath -SessionRoot $sessionRoot) -Value $skillUsage
}
```

Add this field to `$executionManifest`:

```powershell
skill_usage = $skillUsage
```

Add this field to `$proofManifest`:

```powershell
skill_usage_path = if ($skillUsage) { Get-VibeSkillUsagePath -SessionRoot $sessionRoot } else { $null }
used_skill_count = if ($skillUsage) { @($skillUsage.used_skills).Count } else { 0 }
unused_skill_count = if ($skillUsage) { @($skillUsage.unused_skills).Count } else { 0 }
```

Add this field to `$receipt`:

```powershell
skill_usage_path = if ($skillUsage) { Get-VibeSkillUsagePath -SessionRoot $sessionRoot } else { $null }
skill_usage = $skillUsage
```

- [ ] **Step 5: Dot-source helper and include usage in cleanup**

In `scripts/runtime/Invoke-PhaseCleanup.ps1`, after the existing `VibeRuntime.Common.ps1` dot-source, insert:

```powershell
. (Join-Path $PSScriptRoot 'VibeSkillUsage.Common.ps1')
```

Before `$receipt = [pscustomobject]@{`, insert:

```powershell
$skillUsage = Read-VibeSkillUsageArtifact -SessionRoot $sessionRoot -Fallback $null
$skillUsageSummary = [pscustomobject]@{
    used_skill_count = if ($skillUsage) { @($skillUsage.used_skills).Count } else { 0 }
    unused_skill_count = if ($skillUsage) { @($skillUsage.unused_skills).Count } else { 0 }
    loaded_skill_count = if ($skillUsage) { @($skillUsage.loaded_skills).Count } else { 0 }
    evidence_count = if ($skillUsage) { @($skillUsage.evidence).Count } else { 0 }
}
```

Add these fields to `$receipt`:

```powershell
skill_usage_path = if ($skillUsage) { Get-VibeSkillUsagePath -SessionRoot $sessionRoot } else { $null }
skill_usage = $skillUsage
skill_usage_summary = $skillUsageSummary
```

- [ ] **Step 6: Run runtime flow tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py -q
```

Expected: both runtime-flow tests pass.

- [ ] **Step 7: Commit execution and cleanup propagation**

Run:

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 scripts/runtime/Invoke-PhaseCleanup.ps1 tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py
git commit -m "feat: propagate binary skill usage through execution"
```

Expected: commit contains execution/cleanup propagation and tests.

---

### Task 5: Enforce Binary Skill Usage In Delivery Acceptance

**Files:**
- Modify: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
- Modify: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`

- [ ] **Step 1: Add failing delivery acceptance tests**

In `tests/runtime_neutral/test_runtime_delivery_acceptance.py`, extend `_build_session` with a new optional parameter:

```python
        skill_usage: dict[str, object] | None = None,
```

After `write_json(runtime_input_packet_path, runtime_input_packet_payload)`, add:

```python
        if skill_usage is not None:
            write_json(session_root / "skill-usage.json", skill_usage)
```

Add these tests to `RuntimeDeliveryAcceptanceTests`:

```python
    def test_binary_skill_usage_passes_with_full_load_and_artifact_impact(self) -> None:
        session_root = self._build_session(
            skill_usage={
                "schema_version": 1,
                "state_model": "binary_used_unused",
                "used_skills": ["scanpy"],
                "unused_skills": [],
                "loaded_skills": [
                    {
                        "skill_id": "scanpy",
                        "skill_md_path": "bundled/skills/scanpy/SKILL.md",
                        "skill_md_sha256": "a" * 64,
                        "load_status": "loaded_full_skill_md",
                        "loaded_at_stage": "skeleton_check",
                    }
                ],
                "evidence": [
                    {
                        "skill_id": "scanpy",
                        "stage": "xl_plan",
                        "artifact_ref": "xl_plan.md",
                        "impact_summary": "Plan adopts the loaded scanpy workflow.",
                    }
                ],
                "unused_reasons": [],
            }
        )

        report = evaluate(REPO_ROOT, session_root)
        self.assertEqual("PASS", report["skill_usage_truth"]["state"])
        self.assertEqual(["scanpy"], report["skill_usage_truth"]["used_skill_ids"])

    def test_binary_skill_usage_fails_when_used_skill_lacks_artifact_impact(self) -> None:
        session_root = self._build_session(
            skill_usage={
                "schema_version": 1,
                "state_model": "binary_used_unused",
                "used_skills": ["scanpy"],
                "unused_skills": [],
                "loaded_skills": [
                    {
                        "skill_id": "scanpy",
                        "skill_md_path": "bundled/skills/scanpy/SKILL.md",
                        "skill_md_sha256": "b" * 64,
                        "load_status": "loaded_full_skill_md",
                        "loaded_at_stage": "skeleton_check",
                    }
                ],
                "evidence": [],
                "unused_reasons": [],
            }
        )

        report = evaluate(REPO_ROOT, session_root)
        self.assertEqual("FAIL", report["skill_usage_truth"]["state"])
        self.assertIn("missing_artifact_impact", report["skill_usage_truth"]["failure_reasons"])

    def test_approved_dispatch_without_skill_usage_does_not_count_as_used(self) -> None:
        session_root = self._build_session(
            approved_dispatch=[
                {
                    "skill_id": "scanpy",
                    "native_skill_entrypoint": "bundled/skills/scanpy/SKILL.md",
                }
            ],
            skill_usage={
                "schema_version": 1,
                "state_model": "binary_used_unused",
                "used_skills": [],
                "unused_skills": ["scanpy"],
                "loaded_skills": [],
                "evidence": [],
                "unused_reasons": [{"skill_id": "scanpy", "reason": "dispatch_without_verified_artifact_impact"}],
            },
        )

        report = evaluate(REPO_ROOT, session_root)
        self.assertEqual("PASS", report["skill_usage_truth"]["state"])
        self.assertEqual([], report["skill_usage_truth"]["used_skill_ids"])
        self.assertEqual(["scanpy"], report["skill_usage_truth"]["unused_skill_ids"])
```

- [ ] **Step 2: Run new delivery tests and confirm failures**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
```

Expected: fail because `evaluate` does not emit `skill_usage_truth`.

- [ ] **Step 3: Add skill usage validation helper in delivery acceptance runtime**

In `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`, add this helper above `evaluate_delivery_acceptance`:

```python
def _load_skill_usage(session_root: Path, runtime_input_packet: dict[str, Any], execution_manifest: dict[str, Any], execute_receipt: dict[str, Any]) -> dict[str, Any]:
    skill_usage_path = session_root / "skill-usage.json"
    if skill_usage_path.exists():
        return load_json(skill_usage_path)
    for candidate in (
        execute_receipt.get("skill_usage"),
        execution_manifest.get("skill_usage"),
        runtime_input_packet.get("skill_usage"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {
        "schema_version": 1,
        "state_model": "binary_used_unused",
        "used_skills": [],
        "unused_skills": [],
        "loaded_skills": [],
        "evidence": [],
        "unused_reasons": [],
    }


def _evaluate_skill_usage_truth(skill_usage: dict[str, Any]) -> dict[str, Any]:
    used_skill_ids = _normalize_skill_id_list(skill_usage.get("used_skills") or [])
    unused_skill_ids = _normalize_skill_id_list(skill_usage.get("unused_skills") or [])
    loaded_records = list(skill_usage.get("loaded_skills") or [])
    evidence_records = list(skill_usage.get("evidence") or [])
    failure_reasons: list[str] = []
    loaded_by_skill: dict[str, dict[str, Any]] = {}
    for record in loaded_records:
        if not isinstance(record, dict):
            continue
        skill_id = str(record.get("skill_id") or "").strip()
        if skill_id and skill_id not in loaded_by_skill:
            loaded_by_skill[skill_id] = record
    evidence_by_skill: dict[str, list[dict[str, Any]]] = {skill_id: [] for skill_id in used_skill_ids}
    for record in evidence_records:
        if not isinstance(record, dict):
            continue
        skill_id = str(record.get("skill_id") or "").strip()
        if skill_id in evidence_by_skill:
            evidence_by_skill[skill_id].append(record)

    for skill_id in used_skill_ids:
        loaded = loaded_by_skill.get(skill_id)
        if not loaded:
            failure_reasons.append("missing_full_load")
            continue
        if str(loaded.get("load_status") or "") != "loaded_full_skill_md":
            failure_reasons.append("missing_full_load")
        if not str(loaded.get("skill_md_path") or "").strip():
            failure_reasons.append("missing_skill_md_path")
        if not re.match(r"^[0-9a-f]{64}$", str(loaded.get("skill_md_sha256") or "")):
            failure_reasons.append("missing_skill_md_sha256")
        impacts = evidence_by_skill.get(skill_id) or []
        if not impacts:
            failure_reasons.append("missing_artifact_impact")
        for impact in impacts:
            if not str(impact.get("stage") or "").strip():
                failure_reasons.append("missing_impact_stage")
            if not str(impact.get("artifact_ref") or "").strip():
                failure_reasons.append("missing_impact_artifact_ref")
            if not str(impact.get("impact_summary") or "").strip():
                failure_reasons.append("missing_impact_summary")

    state = "PASS" if not failure_reasons else "FAIL"
    return {
        "state": state,
        "state_model": str(skill_usage.get("state_model") or ""),
        "used_skill_ids": used_skill_ids,
        "unused_skill_ids": unused_skill_ids,
        "loaded_skill_ids": sorted(loaded_by_skill),
        "evidence_count": len(evidence_records),
        "failure_reasons": sorted(set(failure_reasons)),
    }
```

Add `import re` near the top of the file if it is not already imported.

- [ ] **Step 4: Wire skill usage truth into the delivery report**

Inside `evaluate_delivery_acceptance`, after `runtime_input_packet`, `execution_manifest`, and `execute_receipt` are loaded, add:

```python
    skill_usage = _load_skill_usage(session_root, runtime_input_packet, execution_manifest, execute_receipt)
    skill_usage_truth = _evaluate_skill_usage_truth(skill_usage)
```

When `truth_layers` is built, add:

```python
        "skill_usage_truth": skill_usage_truth,
```

When the final report dictionary is returned, add:

```python
        "skill_usage_truth": skill_usage_truth,
```

When `failing_layer_count` or gate failure conditions are calculated, include `skill_usage_truth["state"] == "FAIL"` as a failing layer.

- [ ] **Step 5: Run delivery acceptance tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
```

Expected: all runtime delivery acceptance tests pass.

- [ ] **Step 6: Commit delivery gate**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py tests/runtime_neutral/test_runtime_delivery_acceptance.py
git commit -m "test: enforce binary skill usage truth"
```

Expected: commit contains delivery acceptance validation and tests.

---

### Task 6: Update User-Facing Wording And Run Broad Verification

**Files:**
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
- Modify: `docs/governance/binary-skill-usage-routing-2026-04-28.md`
- Test: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- Test: `tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py`
- Test: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`

- [ ] **Step 1: Add governance note**

Create `docs/governance/binary-skill-usage-routing-2026-04-28.md` with:

```markdown
# Binary Skill Usage Routing Governance Note

Date: 2026-04-28

## Decision

Skill usage has only two user-facing states:

- `used`
- `unused`

Only `skill_usage` can support a usage claim.

## Used Standard

A skill is `used` only when:

1. the full `SKILL.md` was loaded,
2. load evidence records `skill_md_path`, `skill_md_sha256`, and `load_status = loaded_full_skill_md`,
3. at least one six-stage artifact impact record exists in `skill_usage.evidence`.

## Non-Authoritative Fields

These fields remain audit data and do not prove usage:

- `specialist_recommendations`
- `stage_assistant_hints`
- `specialist_dispatch.approved_dispatch`
- consultation receipts
- `native_skill_description`

## Runtime Contract

The public six-stage runtime remains unchanged. Binary usage is an internal truth layer written through `skill-usage.json` and surfaced in final delivery acceptance.

## Completion Language

Completion reports may say a skill was used only when `skill_usage.used_skills` contains it and `skill_usage.evidence` supports it.
```

- [ ] **Step 2: Update host briefing wording to avoid old usage claims**

In `scripts/runtime/VibeRuntime.Common.ps1`, locate the user-facing lifecycle wording that says:

```powershell
'Vibe consulted these Skills during {0}; freeze gate: {1}.'
```

Change the user-facing wording so it does not imply skill usage:

```powershell
'Vibe recorded these Skills in the {0} consultation audit chain; freeze gate: {1}. Usage claims still require `skill_usage` evidence.'
```

Locate the execution disclosure wording that says:

```powershell
'Vibe approved these Skills for execution:'
```

Change it to:

```powershell
'Vibe approved these Skills for execution dispatch. Dispatch alone is not a `used` claim:'
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Run existing specialist/routing regression tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_bundled_stage_assistant_freeze.py tests/runtime_neutral/test_vibe_specialist_consultation.py tests/runtime_neutral/test_governed_runtime_bridge.py -q
```

Expected: all selected tests pass. If an existing test asserts the old wording, update the assertion to the new non-usage wording and rerun this command.

- [ ] **Step 5: Run runtime gates**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-governed-runtime-contract-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-runtime-execution-proof-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected: all gates pass.

- [ ] **Step 6: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: exit code `0`.

- [ ] **Step 7: Commit wording and governance note**

Run:

```powershell
git add scripts/runtime/VibeRuntime.Common.ps1 docs/governance/binary-skill-usage-routing-2026-04-28.md
git commit -m "docs: clarify binary skill usage truth"
```

Expected: commit contains only user-facing wording and governance note.

---

## Final Verification

After all tasks are complete, run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_binary_skill_usage_runtime_flow.py tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
python -m pytest tests/runtime_neutral/test_bundled_stage_assistant_freeze.py tests/runtime_neutral/test_vibe_specialist_consultation.py tests/runtime_neutral/test_governed_runtime_bridge.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-governed-runtime-contract-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-runtime-execution-proof-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
git diff --check
```

Expected:

- all pytest commands pass,
- all PowerShell gates pass,
- `git diff --check` exits `0`,
- generated runtime sessions include `runtime-input-packet.json.skill_usage`,
- generated runtime sessions include `skill-usage.json`,
- final delivery acceptance reports include `skill_usage_truth`,
- final user-facing wording treats recommendation, hint, consultation, and dispatch as non-authoritative for usage.
