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

$requiredFiles = @(
    'docs/root-child-vibe-hierarchy-governance.md',
    'docs/requirements/2026-03-28-root-child-vibe-hierarchy-governance.md',
    'docs/plans/2026-03-28-root-child-vibe-hierarchy-governance-plan.md',
    'tests/runtime_neutral/test_root_child_hierarchy_bridge.py'
)
foreach ($relativePath in $requiredFiles) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $relativePath)) -Message ("hierarchy required file exists: {0}" -f $relativePath)
}

$runtimeContract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Assertion -Results ([ref]$results) -Condition ($runtimeContract.entry_skill -eq 'vibe') -Message 'runtime contract entry skill remains vibe'

$policyText = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8
foreach ($token in @(
    'governance_scope',
    'hierarchy_contract',
    'child_specialist_suggestion_contract',
    'allow_requirement_freeze',
    'allow_plan_freeze',
    'allow_global_dispatch',
    'allow_completion_claim',
    'specialist_dispatch',
    'advisory_until_root_approval',
    'escalation_required',
    'auto_absorb_gate'
)) {
    Add-Assertion -Results ([ref]$results) -Condition ($policyText.Contains($token)) -Message ("runtime input policy contains hierarchy token: {0}" -f $token)
}

$runtimeText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\runtime.md') -Raw -Encoding UTF8
$teamText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\team.md') -Raw -Encoding UTF8
$stableDocText = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\root-child-vibe-hierarchy-governance.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($runtimeText.Contains('runtime-selected skill stays `vibe`')) -Message 'runtime protocol documents explicit vibe authority preservation'
Add-Assertion -Results ([ref]$results) -Condition ($teamText.Contains('`vibe` keeps final control')) -Message 'team protocol keeps vibe as final control'
Add-Assertion -Results ([ref]$results) -Condition ($stableDocText.Contains('root vibe governs, child vibe executes, specialists assist')) -Message 'stable hierarchy doc exposes root/child mental model'

$runId = "root-child-hierarchy-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\root-child-hierarchy-{0}" -f $runId)
$summary = & $runtimeEntryPath -Task 'Root child hierarchy authority smoke.' -Mode benchmark_autonomous -GovernanceScope root -RunId $runId -ArtifactRoot $artifactRoot

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $summary) -Message 'runtime smoke returned summary payload'
$hasSummary = ($null -ne $summary) -and ($summary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasSummary -Message 'runtime smoke summary object exists'

if ($hasSummary) {
    $runtimeInputPacket = Get-Content -LiteralPath $summary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionManifest = Get-Content -LiteralPath $summary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'legacy benchmark mode is normalized to interactive_governed for hierarchy smoke'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.route_snapshot.selected_skill -eq 'vibe') -Message 'root hierarchy smoke keeps vibe as frozen route skill'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'root hierarchy smoke keeps vibe as runtime authority'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.governance_scope -eq 'root') -Message 'runtime packet marks root governance scope'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_requirement_freeze) -Message 'root packet allows requirement freeze'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_plan_freeze) -Message 'root packet allows plan freeze'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_global_dispatch) -Message 'root packet allows global specialist dispatch'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeInputPacket.authority_flags.allow_completion_claim) -Message 'root packet allows final completion claim'
    $hasSpecialistDispatchSurface = ($runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch') -or ($runtimeInputPacket.PSObject.Properties.Name -contains 'approved_specialist_dispatch')
    Add-Assertion -Results ([ref]$results) -Condition $hasSpecialistDispatchSurface -Message 'runtime packet includes specialist dispatch surface'
    $hasEscalationSurface = ($runtimeInputPacket.PSObject.Properties.Name -contains 'escalation_required') -or (($runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch') -and ($runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'escalation_required'))
    Add-Assertion -Results ([ref]$results) -Condition $hasEscalationSurface -Message 'runtime packet includes escalation marker surface'

    $hasCompletionAuthority = ($executionManifest.PSObject.Properties.Name -contains 'authority')
    Add-Assertion -Results ([ref]$results) -Condition $hasCompletionAuthority -Message 'execution manifest includes authority surface'
    if ($hasCompletionAuthority) {
        Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.governance_scope -eq 'root') -Message 'execution manifest marks root governance scope'
        Add-Assertion -Results ([ref]$results) -Condition ([bool]$executionManifest.authority.completion_claim_allowed) -Message 'execution manifest allows final completion claim only for root scope'
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
        Join-Path $repoRoot 'outputs\verify\vibe-root-child-hierarchy'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-root-child-hierarchy-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-root-child-hierarchy-gate failed with $failureCount failing assertion(s)."
}

$report
