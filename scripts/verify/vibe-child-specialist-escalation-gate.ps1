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

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$results = @()

$policyText = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8
foreach ($token in @('specialist_dispatch', 'local_specialist_suggestions', 'escalation_required', 'advisory_until_root_approval', 'auto_absorb_gate')) {
    Add-Assertion -Results ([ref]$results) -Condition ($policyText.Contains($token)) -Message ("runtime input policy contains specialist escalation token: {0}" -f $token)
}

$teamText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\team.md') -Raw -Encoding UTF8
$stableDocText = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\root-child-vibe-hierarchy-governance.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($teamText.Contains('advisory until the governed plan chooses to dispatch it')) -Message 'team protocol keeps specialist recommendation advisory-first'
Add-Assertion -Results ([ref]$results) -Condition ($stableDocText.Contains('same-round auto-approve safe suggestions')) -Message 'stable hierarchy doc documents root-governed same-round absorb path'

$runId = "child-specialist-escalation-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\child-specialist-escalation-{0}" -f $runId)

$rootSummary = & $runtimeEntryPath `
    -Task 'Root specialist dispatch seed for child escalation gate.' `
    -Mode benchmark_autonomous `
    -GovernanceScope root `
    -RunId ("{0}-root" -f $runId) `
    -ArtifactRoot $artifactRoot

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $rootSummary) -Message 'root specialist escalation probe returned summary payload'
$hasRootSummary = ($null -ne $rootSummary) -and ($rootSummary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasRootSummary -Message 'root specialist escalation probe has summary object'

$approvedForChild = @()
if ($hasRootSummary) {
    $rootRuntimeInputPacket = Get-Content -LiteralPath $rootSummary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.governance_scope -eq 'root') -Message 'root specialist escalation probe is in root scope'
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'root specialist escalation probe keeps vibe authority'

    $rootApprovedDispatch = if ($rootRuntimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch') {
        @($rootRuntimeInputPacket.specialist_dispatch.approved_dispatch)
    } elseif ($rootRuntimeInputPacket.PSObject.Properties.Name -contains 'approved_specialist_dispatch') {
        @($rootRuntimeInputPacket.approved_specialist_dispatch)
    } else {
        @()
    }
    if (@($rootApprovedDispatch).Count -gt 0) {
        $firstSkillId = [string]$rootApprovedDispatch[0].skill_id
        if (-not [string]::IsNullOrWhiteSpace($firstSkillId)) {
            $approvedForChild = @($firstSkillId)
        }
    }
}

$childSummary = $null
if ($hasRootSummary) {
    $childSummary = & $runtimeEntryPath `
        -Task 'Child specialist escalation advisory smoke.' `
        -Mode benchmark_autonomous `
        -GovernanceScope child `
        -RunId ("{0}-child" -f $runId) `
        -RootRunId ([string]$rootSummary.summary.run_id) `
        -ParentRunId ([string]$rootSummary.summary.run_id) `
        -ParentUnitId 'child-specialist-escalation-unit' `
        -InheritedRequirementDocPath ([string]$rootSummary.summary.artifacts.requirement_doc) `
        -InheritedExecutionPlanPath ([string]$rootSummary.summary.artifacts.execution_plan) `
        -ApprovedSpecialistSkillIds $approvedForChild `
        -ArtifactRoot $artifactRoot
}

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $childSummary) -Message 'child specialist escalation probe returned summary payload'
$hasChildSummary = ($null -ne $childSummary) -and ($childSummary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasChildSummary -Message 'child specialist escalation probe has summary object'

$approvedDispatch = @()
$localSuggestions = @()
$childClaims = @()
if ($hasChildSummary) {
    $runtimeInputPacket = Get-Content -LiteralPath $childSummary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionManifest = Get-Content -LiteralPath $childSummary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

    $specialistDispatch = if ($runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch') {
        $runtimeInputPacket.specialist_dispatch
    } else {
        $null
    }

    $approvedDispatch = if ($null -ne $specialistDispatch -and $specialistDispatch.PSObject.Properties.Name -contains 'approved_dispatch') {
        @($specialistDispatch.approved_dispatch)
    } elseif ($runtimeInputPacket.PSObject.Properties.Name -contains 'approved_specialist_dispatch') {
        @($runtimeInputPacket.approved_specialist_dispatch)
    } else {
        @()
    }

    $localSuggestions = if ($null -ne $specialistDispatch -and $specialistDispatch.PSObject.Properties.Name -contains 'local_specialist_suggestions') {
        @($specialistDispatch.local_specialist_suggestions)
    } elseif ($runtimeInputPacket.PSObject.Properties.Name -contains 'local_specialist_suggestions') {
        @($runtimeInputPacket.local_specialist_suggestions)
    } else {
        @()
    }

    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.governance_scope -eq 'child') -Message 'specialist escalation smoke runs in child scope'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'specialist escalation smoke keeps vibe runtime authority'
    Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.authority_flags.allow_completion_claim) -Message 'child runtime input packet disallows final completion claim'
    Add-Assertion -Results ([ref]$results) -Condition ($null -ne $specialistDispatch) -Message 'runtime packet exposes specialist dispatch surface'

    if ($null -ne $specialistDispatch) {
        Add-Assertion -Results ([ref]$results) -Condition ([string]$specialistDispatch.status -eq 'advisory_until_root_approval') -Message 'child specialist suggestions remain advisory until root approval'
        if (@($localSuggestions).Count -gt 0) {
            Add-Assertion -Results ([ref]$results) -Condition ([bool]$specialistDispatch.escalation_required) -Message 'child local specialist suggestions require escalation'
            Add-Assertion -Results ([ref]$results) -Condition ([string]$specialistDispatch.escalation_status -eq 'root_approval_required') -Message 'child local specialist escalation status is root_approval_required'
        }
    }

    $approvedSkillIds = @($approvedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    foreach ($entry in $localSuggestions) {
        $skillId = if ($entry.PSObject.Properties.Name -contains 'skill_id') { [string]$entry.skill_id } else { 'unknown-skill' }
        Add-Assertion -Results ([ref]$results) -Condition (-not ($approvedSkillIds -contains $skillId)) -Message ("local specialist suggestion is not approved global dispatch: {0}" -f $skillId)
    }

    Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.governance_scope -eq 'child') -Message 'execution manifest is marked child scope'
    Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$executionManifest.authority.completion_claim_allowed) -Message 'child execution manifest cannot issue final completion claim'
    Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.route_runtime_alignment.runtime_selected_skill -eq 'vibe') -Message 'execution manifest keeps explicit vibe authority'
    $specialistAccounting = if ($executionManifest.PSObject.Properties.Name -contains 'specialist_accounting') { $executionManifest.specialist_accounting } else { $null }
    if ($null -ne $specialistAccounting -and $specialistAccounting.PSObject.Properties.Name -contains 'auto_absorb_gate') {
        Add-Assertion -Results ([ref]$results) -Condition ([bool]$specialistAccounting.auto_absorb_gate.enabled) -Message 'child execution manifest exposes enabled same-round auto-absorb gate'
        if ($specialistAccounting.auto_absorb_gate.receipt_path) {
            Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$specialistAccounting.auto_absorb_gate.receipt_path)) -Message 'same-round auto-absorb gate emits receipt'
        }
    }

    $childClaims = if ($executionManifest.PSObject.Properties.Name -contains 'child_completion_claims') { @($executionManifest.child_completion_claims) } else { @() }
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    runtime_summary_path = if ($null -ne $childSummary -and ($childSummary.PSObject.Properties.Name -contains 'summary_path')) { $childSummary.summary_path } else { $null }
    approved_dispatch_count = @($approvedDispatch).Count
    local_suggestion_count = @($localSuggestions).Count
    child_claim_count = @($childClaims).Count
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-child-specialist-escalation'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-child-specialist-escalation-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-child-specialist-escalation-gate failed with $failureCount failing assertion(s)."
}

$report
