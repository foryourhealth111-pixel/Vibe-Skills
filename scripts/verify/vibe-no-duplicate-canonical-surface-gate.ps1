param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\runtime\VibeRuntime.Common.ps1')

function Add-Assertion {
    param(
        [ref]$Results,
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ''
    )

    $record = [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }
    $Results.Value += $record

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        if ($Details) {
            Write-Host "       $Details" -ForegroundColor DarkRed
        }
    }
}

function Test-PathUnderDirectory {
    param(
        [Parameter(Mandatory)] [string]$CandidatePath,
        [Parameter(Mandatory)] [string]$RootPath
    )

    $candidate = [System.IO.Path]::GetFullPath($CandidatePath)
    $root = [System.IO.Path]::GetFullPath($RootPath)
    if (-not $root.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $root += [System.IO.Path]::DirectorySeparatorChar
    }
    return $candidate.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)
}

function Convert-ToNormalizedPathToken {
    param(
        [Parameter(Mandatory)] [string]$PathValue
    )

    return ([System.IO.Path]::GetFullPath($PathValue)).Replace('\', '/')
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$results = @()

$runId = "canonical-surface-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\canonical-surface-{0}" -f $runId)
$task = "Canonical surface uniqueness probe $runId"
$summary = & $runtimeEntryPath -Task $task -Mode benchmark_autonomous -GovernanceScope root -RunId $runId -ArtifactRoot $artifactRoot

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $summary) -Message 'canonical surface probe returned summary payload'
$hasSummary = ($null -ne $summary) -and ($summary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasSummary -Message 'canonical surface probe has summary object'

if ($hasSummary) {
    $requirementDocPath = [string]$summary.summary.artifacts.requirement_doc
    $executionPlanPath = [string]$summary.summary.artifacts.execution_plan
    $runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet
    $executionManifestPath = [string]$summary.summary.artifacts.execution_manifest

    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $requirementDocPath) -Message 'canonical requirement artifact exists' -Details $requirementDocPath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $executionPlanPath) -Message 'canonical execution plan artifact exists' -Details $executionPlanPath
    $requirementPathToken = Convert-ToNormalizedPathToken -PathValue $requirementDocPath
    $executionPlanPathToken = Convert-ToNormalizedPathToken -PathValue $executionPlanPath
    Add-Assertion -Results ([ref]$results) -Condition (
        $requirementPathToken.Contains('/docs/requirements/')
    ) -Message 'canonical requirement lives under docs/requirements' -Details $requirementDocPath
    Add-Assertion -Results ([ref]$results) -Condition (
        $executionPlanPathToken.Contains('/docs/plans/')
    ) -Message 'canonical execution plan lives under docs/plans' -Details $executionPlanPath

    $runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.governance_scope -eq 'root') -Message 'canonical surface probe runs in root governance scope'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_requirement_freeze) -Message 'root scope keeps requirement freeze authority'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_plan_freeze) -Message 'root scope keeps plan freeze authority'

    $stableDocText = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\root-child-vibe-hierarchy-governance.md') -Raw -Encoding UTF8
    Add-Assertion -Results ([ref]$results) -Condition ($stableDocText.Contains('one canonical requirement surface')) -Message 'stable hierarchy doc forbids duplicate requirement truth'
    Add-Assertion -Results ([ref]$results) -Condition ($stableDocText.Contains('one canonical execution-plan surface')) -Message 'stable hierarchy doc forbids duplicate execution-plan truth'

    $childRunId = "canonical-surface-child-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $childSummary = & $runtimeEntryPath `
        -Task ("Child canonical surface uniqueness probe {0}" -f $childRunId) `
        -Mode benchmark_autonomous `
        -GovernanceScope child `
        -RunId $childRunId `
        -RootRunId ([string]$summary.summary.run_id) `
        -ParentRunId ([string]$summary.summary.run_id) `
        -ParentUnitId 'canonical-surface-child-unit' `
        -InheritedRequirementDocPath $requirementDocPath `
        -InheritedExecutionPlanPath $executionPlanPath `
        -ArtifactRoot $artifactRoot

    Add-Assertion -Results ([ref]$results) -Condition ($null -ne $childSummary) -Message 'child canonical probe returned summary payload'
    $hasChildSummary = ($null -ne $childSummary) -and ($childSummary.PSObject.Properties.Name -contains 'summary')
    Add-Assertion -Results ([ref]$results) -Condition $hasChildSummary -Message 'child canonical probe has summary object'

    if ($hasChildSummary) {
        $childRequirementReceipt = Get-Content -LiteralPath $childSummary.summary.artifacts.requirement_receipt -Raw -Encoding UTF8 | ConvertFrom-Json
        $childExecutionPlanReceipt = Get-Content -LiteralPath $childSummary.summary.artifacts.execution_plan_receipt -Raw -Encoding UTF8 | ConvertFrom-Json
        $childExecutionManifest = Get-Content -LiteralPath $childSummary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

        Add-Assertion -Results ([ref]$results) -Condition ($childSummary.summary.governance_scope -eq 'child') -Message 'child canonical probe runs in child governance scope'
        Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$childRequirementReceipt.canonical_write_allowed) -Message 'child requirement stage cannot write canonical requirement surface'
        Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$childExecutionPlanReceipt.canonical_write_allowed) -Message 'child plan stage cannot write canonical plan surface'
        Add-Assertion -Results ([ref]$results) -Condition (
            [System.IO.Path]::GetFullPath([string]$childRequirementReceipt.requirement_doc_path) -eq [System.IO.Path]::GetFullPath([string]$requirementDocPath)
        ) -Message 'child requirement stage reuses root canonical requirement path'
        Add-Assertion -Results ([ref]$results) -Condition (
            [System.IO.Path]::GetFullPath([string]$childExecutionPlanReceipt.execution_plan_path) -eq [System.IO.Path]::GetFullPath([string]$executionPlanPath)
        ) -Message 'child plan stage reuses root canonical execution plan path'
        Add-Assertion -Results ([ref]$results) -Condition ($childExecutionManifest.governance_scope -eq 'child') -Message 'child execution manifest is marked as child scope'
        Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$childExecutionManifest.authority.completion_claim_allowed) -Message 'child execution manifest cannot issue final completion claims'
    }
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    runtime_summary_path = if ($null -ne $summary -and ($summary.PSObject.Properties.Name -contains 'summary_path')) { $summary.summary_path } else { $null }
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-no-duplicate-canonical-surface'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-no-duplicate-canonical-surface-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-no-duplicate-canonical-surface-gate failed with $failureCount failing assertion(s)."
}

$report
