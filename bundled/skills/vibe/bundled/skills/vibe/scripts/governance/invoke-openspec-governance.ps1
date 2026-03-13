param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [ValidateSet("M", "L", "XL")]
    [string]$Grade = "M",
    [ValidateSet("planning", "coding", "review", "debug", "research")]
    [string]$TaskType = "planning",
    [string]$RequestedSkill,
    [string]$TaskId,
    [switch]$WriteArtifacts,
    [switch]$NoAutoCreateLite
)

$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-LiteCard {
    param(
        [string]$Path,
        [string]$Prompt,
        [string]$TaskId
    )

    $content = @"
# OpenSpec Lite Card: $TaskId

- goal:
- in_scope:
- out_of_scope:
- acceptance:
- risk:
- rollback:

## Prompt
$Prompt

## Result
- status: draft
- evidence:
"@

    Set-Content -LiteralPath $Path -Value $content -Encoding UTF8
}

function Write-FullSkeleton {
    param(
        [string]$SpecsDir,
        [string]$ChangesDir,
        [string]$TaskId,
        [string]$Prompt
    )

    Ensure-Directory -Path $SpecsDir
    Ensure-Directory -Path $ChangesDir

    $specReadme = Join-Path $SpecsDir "README.md"
    if (-not (Test-Path -LiteralPath $specReadme)) {
        Set-Content -LiteralPath $specReadme -Encoding UTF8 -Value @"
# OpenSpec Specs

Stable requirement truths should be stored here.
"@
    }

    $changeDir = Join-Path $ChangesDir $TaskId
    Ensure-Directory -Path $changeDir

    $files = @(
        @{ Name = "change.md"; Content = @"
# Change: $TaskId

## Why
$Prompt

## Scope
- 

## Tasks
- [ ] 
"@ },
        @{ Name = "tasks.md"; Content = @"
# Tasks for $TaskId

## Checklist
- [ ] Identify assumptions
- [ ] Break work into verifiable steps
- [ ] Link to related specs
"@ },
        @{ Name = "progress.md"; Content = @"
# Progress for $TaskId

| Date | Status | Notes |
| ---- | ------ | ----- |
"@ },
        @{ Name = "handoff.md"; Content = @"
# Handoff for $TaskId

- summary:
- blockers:
- next_steps:
"@ }
    )

    foreach ($file in $files) {
        $path = Join-Path $changeDir $file.Name
        if (-not (Test-Path -LiteralPath $path)) {
            Set-Content -LiteralPath $path -Encoding UTF8 -Value $file.Content
        }
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$configRoot = Join-Path $repoRoot "config"
$policyPath = Join-Path $configRoot "openspec-policy.json"

if (-not (Test-Path -LiteralPath $policyPath)) {
    [pscustomobject]@{
        status = "policy_missing"
        enforced = $false
        wrote_artifacts = $false
        policy_path = $policyPath
    } | ConvertTo-Json -Depth 10
    exit 0
}

$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$resolverPath = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
$routeArgs = @{
    Prompt = $Prompt
    Grade = $Grade
    TaskType = $TaskType
}
if ($RequestedSkill) {
    $routeArgs["RequestedSkill"] = $RequestedSkill
}

$route = (& $resolverPath @routeArgs) | ConvertFrom-Json
$advice = $route.openspec_advice

if (-not $advice -or -not $advice.enabled) {
    [pscustomobject]@{
        status = "disabled"
        enforced = $false
        wrote_artifacts = $false
        route_mode = $route.route_mode
        selected_pack = $route.selected.pack_id
        selected_skill = $route.selected.skill
    } | ConvertTo-Json -Depth 10
    exit 0
}

$resolvedTaskId = if ($TaskId) { $TaskId } elseif ($advice.task_id) { [string]$advice.task_id } else { "task-unknown" }
$wroteArtifacts = $false
$status = "advisory_only"
$requiredAction = "none"
$artifactPath = $null
$missingFullChangeFiles = @()
$hasChangeDir = $false

if ($advice.profile -eq "lite" -and $advice.task_applicable) {
    $artifactRel = if ($advice.recommended_artifact) {
        [string]$advice.recommended_artifact
    } else {
        "openspec/micro/$resolvedTaskId.md"
    }
    $artifactPath = Join-Path $repoRoot $artifactRel
    $artifactDir = Split-Path -Path $artifactPath -Parent
    $exists = Test-Path -LiteralPath $artifactPath

    $autoCreateLite = $false
    if ($policy.m_lite -and $policy.m_lite.auto_create -and -not $NoAutoCreateLite) {
        $autoCreateLite = $true
    }
    if ($WriteArtifacts) {
        $autoCreateLite = $true
    }

    if (-not $exists -and $autoCreateLite) {
        Ensure-Directory -Path $artifactDir
        Write-LiteCard -Path $artifactPath -Prompt $Prompt -TaskId $resolvedTaskId
        $exists = $true
        $wroteArtifacts = $true
        $status = "lite_created"
    } elseif ($exists) {
        $status = "lite_exists"
    } else {
        $status = "lite_missing"
        $requiredAction = "create_lite_card"
    }
}

if ($advice.profile -eq "full" -and $advice.task_applicable) {
    $specsDirRel = if ($policy.full -and $policy.full.specs_dir) { [string]$policy.full.specs_dir } else { "openspec/specs" }
    $changesDirRel = if ($policy.full -and $policy.full.changes_dir) { [string]$policy.full.changes_dir } else { "openspec/changes" }

    $specsDir = Join-Path $repoRoot $specsDirRel
    $changesDir = Join-Path $repoRoot $changesDirRel
    $changeTaskPath = Join-Path $changesDir $resolvedTaskId
    $artifactPath = $changeTaskPath
    $requiredChangeFiles = @("change.md", "tasks.md", "progress.md", "handoff.md")

    $hasSpecs = (Test-Path -LiteralPath $specsDir) -and ((Get-ChildItem -LiteralPath $specsDir -File -ErrorAction SilentlyContinue).Count -gt 0)
    $hasChangeDir = Test-Path -LiteralPath $changeTaskPath
    $missingFullChangeFiles = @()
    if ($hasChangeDir) {
        foreach ($requiredFile in $requiredChangeFiles) {
            $requiredPath = Join-Path $changeTaskPath $requiredFile
            if (-not (Test-Path -LiteralPath $requiredPath)) {
                $missingFullChangeFiles += $requiredFile
            }
        }
    } else {
        $missingFullChangeFiles = @($requiredChangeFiles)
    }
    $hasChange = $hasChangeDir -and ($missingFullChangeFiles.Count -eq 0)

    if ((-not $hasSpecs -or -not $hasChange) -and $WriteArtifacts) {
        Write-FullSkeleton -SpecsDir $specsDir -ChangesDir $changesDir -TaskId $resolvedTaskId -Prompt $Prompt
        $wroteArtifacts = $true
        $hasSpecs = (Test-Path -LiteralPath $specsDir) -and ((Get-ChildItem -LiteralPath $specsDir -File -ErrorAction SilentlyContinue).Count -gt 0)
        $hasChangeDir = Test-Path -LiteralPath $changeTaskPath
        $missingFullChangeFiles = @()
        if ($hasChangeDir) {
            foreach ($requiredFile in $requiredChangeFiles) {
                $requiredPath = Join-Path $changeTaskPath $requiredFile
                if (-not (Test-Path -LiteralPath $requiredPath)) {
                    $missingFullChangeFiles += $requiredFile
                }
            }
        } else {
            $missingFullChangeFiles = @($requiredChangeFiles)
        }
        $hasChange = $hasChangeDir -and ($missingFullChangeFiles.Count -eq 0)
    }

    if ($hasSpecs -and $hasChange) {
        $status = "full_ready"
    } else {
        $status = "full_missing"
        if ($missingFullChangeFiles.Count -gt 0 -and $hasChangeDir) {
            $requiredAction = "complete_full_skeleton_files"
        } else {
            $requiredAction = "create_full_spec_change"
        }
    }
}

# strict planning blocking should follow mode semantics, not the enforcement enum value.
# Backward compatibility: if older route outputs do not expose mode, treat full+required as strict-equivalent.
$strictOpenSpecMode = $false
if ($advice.mode -and ([string]$advice.mode -eq "strict")) {
    $strictOpenSpecMode = $true
} elseif ((-not $advice.mode) -and $advice.profile -eq "full" -and $advice.enforcement -eq "required") {
    $strictOpenSpecMode = $true
}

$strictPlanningBlocking = ($strictOpenSpecMode -and $TaskType -eq "planning" -and $status -eq "full_missing" -and -not $WriteArtifacts)
if ($strictPlanningBlocking) {
    if ($requiredAction -eq "complete_full_skeleton_files") {
        $requiredAction = "rerun_with_WriteArtifacts_to_complete_full_skeleton"
    } else {
        $requiredAction = "rerun_with_WriteArtifacts_to_create_full_spec_change"
    }
}

[pscustomobject]@{
    status = $status
    enforced = (($advice.enforcement -in @("confirm_required", "required")) -or $strictPlanningBlocking)
    enforcement = $advice.enforcement
    required_action = $requiredAction
    wrote_artifacts = $wroteArtifacts
    task_id = $resolvedTaskId
    artifact_path = $artifactPath
    missing_full_change_files = $missingFullChangeFiles
    route_mode = $route.route_mode
    selected_pack = $route.selected.pack_id
    selected_skill = $route.selected.skill
    openspec_advice = $advice
} | ConvertTo-Json -Depth 10
