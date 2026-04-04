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
    'SKILL.md',
    'protocols/runtime.md',
    'protocols/think.md',
    'protocols/do.md',
    'protocols/team.md',
    'protocols/retro.md',
    'config/runtime-contract.json',
    'config/runtime-modes.json',
    'config/fallback-governance.json',
    'config/implementation-guardrails.json',
    'config/benchmark-execution-policy.json',
    'config/requirement-doc-policy.json',
    'config/plan-execution-policy.json',
    'config/phase-cleanup-policy.json',
    'docs/requirements/README.md',
    'templates/requirements/governed-requirement-template.md',
    'templates/plans/governed-execution-plan-template.md',
    'scripts/runtime/VibeRuntime.Common.ps1',
    'scripts/runtime/Invoke-SkeletonCheck.ps1',
    'scripts/runtime/Invoke-DeepInterview.ps1',
    'scripts/runtime/Write-RequirementDoc.ps1',
    'scripts/runtime/Write-XlPlan.ps1',
    'scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1',
    'scripts/runtime/Invoke-PlanExecute.ps1',
    'scripts/runtime/Invoke-PhaseCleanup.ps1',
    'scripts/verify/vibe-benchmark-autonomous-proof-gate.ps1',
    'scripts/verify/vibe-specialist-dispatch-closure-gate.ps1',
    'scripts/verify/vibe-no-silent-fallback-contract-gate.ps1',
    'scripts/verify/vibe-no-self-introduced-fallback-gate.ps1',
    'scripts/verify/vibe-release-truth-consistency-gate.ps1'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required governed runtime file exists: {0}" -f $relativePath) -Details $fullPath
}
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $runtimeEntryPath) -Message 'effective governed runtime entrypoint exists' -Details $runtimeEntryPath

$runtimeContract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Assertion -Results ([ref]$results) -Condition ($runtimeContract.entry_skill -eq 'vibe') -Message 'runtime contract entry skill is vibe'
Add-Assertion -Results ([ref]$results) -Condition (@($runtimeContract.stages).Count -eq 6) -Message 'runtime contract defines six fixed stages'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.no_silent_fallback) -Message 'runtime contract forbids silent fallback'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.fallback_hazard_alert_required) -Message 'runtime contract requires fallback hazard alerts'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.no_self_introduced_fallback_without_requirement_approval) -Message 'runtime contract forbids self-introduced fallback without requirement approval'

$skillText = Get-Content -LiteralPath (Join-Path $repoRoot 'SKILL.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition (
    $skillText.Contains('skeleton_check') -and
    $skillText.Contains('deep_interview') -and
    $skillText.Contains('requirement_doc') -and
    $skillText.Contains('xl_plan') -and
    $skillText.Contains('plan_execute') -and
    $skillText.Contains('phase_cleanup')
) -Message 'SKILL.md documents the fixed stage machine'

$teamText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\team.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($teamText.Contains('$vibe')) -Message 'team protocol requires subagent prompts to end with $vibe'

$runId = "contract-gate-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\governed-runtime-contract-{0}" -f $runId)
$summary = & $runtimeEntryPath -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' -Mode benchmark_autonomous -RunId $runId -ArtifactRoot $artifactRoot

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'runtime smoke summary normalizes legacy benchmark mode to interactive_governed'

$artifactPaths = @(
    $summary.summary.artifacts.skeleton_receipt,
    $summary.summary.artifacts.intent_contract,
    $summary.summary.artifacts.requirement_doc,
    $summary.summary.artifacts.execution_plan,
    $summary.summary.artifacts.execute_receipt,
    $summary.summary.artifacts.execution_manifest,
    $summary.summary.artifacts.benchmark_proof_manifest,
    $summary.summary.artifacts.cleanup_receipt
)

foreach ($artifactPath in $artifactPaths) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $artifactPath) -Message ("runtime smoke artifact exists: {0}" -f ([System.IO.Path]::GetFileName($artifactPath))) -Details $artifactPath
}

$executeReceipt = Get-Content -LiteralPath $summary.summary.artifacts.execute_receipt -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $summary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$proofManifest = Get-Content -LiteralPath $summary.summary.artifacts.benchmark_proof_manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$runtimeInputPacket = Get-Content -LiteralPath $summary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
$generatedRequirement = Get-Content -LiteralPath $summary.summary.artifacts.requirement_doc -Raw -Encoding UTF8
$generatedPlan = Get-Content -LiteralPath $summary.summary.artifacts.execution_plan -Raw -Encoding UTF8

Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -ne 'execution-contract-prepared') -Message 'runtime smoke execute receipt is not receipt-only'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'completed') -Message 'runtime smoke execution manifest completed' -Details $executionManifest.status
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.executed_unit_count -ge 2) -Message 'runtime smoke executes at least two benchmark units' -Details $executionManifest.executed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.proof_passed) -Message 'runtime smoke benchmark proof manifest is green'
Add-Assertion -Results ([ref]$results) -Condition ($generatedRequirement.Contains('## Primary Objective')) -Message 'runtime smoke requirement doc includes anti-drift primary objective section'
Add-Assertion -Results ([ref]$results) -Condition ($generatedRequirement.Contains('## Completion State')) -Message 'runtime smoke requirement doc includes anti-drift completion section'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Anti-Proxy-Goal-Drift Controls')) -Message 'runtime smoke execution plan includes anti-drift controls section'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('### Primary Objective')) -Message 'runtime smoke execution plan includes anti-drift primary objective control'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.route_snapshot.selected_skill -eq 'vibe') -Message 'runtime smoke keeps vibe as the frozen route skill for governed entry'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'runtime smoke keeps vibe as explicit runtime skill'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.divergence_shadow.skill_mismatch) -Message 'runtime smoke keeps router/runtime skill alignment for explicit governed vibe entry'
Add-Assertion -Results ([ref]$results) -Condition (@($runtimeInputPacket.specialist_recommendations).Count -ge 1) -Message 'runtime smoke freezes bounded specialist recommendations'
Add-Assertion -Results ([ref]$results) -Condition ((@($runtimeInputPacket.specialist_recommendations | ForEach-Object { [string]$_.skill_id }) -contains 'systematic-debugging')) -Message 'runtime smoke preserves systematic-debugging as a bounded specialist recommendation'
Add-Assertion -Results ([ref]$results) -Condition ($generatedRequirement.Contains('## Specialist Recommendations')) -Message 'runtime smoke requirement doc includes specialist recommendations section'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Specialist Skill Dispatch Plan')) -Message 'runtime smoke execution plan includes specialist dispatch section'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.specialist_accounting.recommendation_count -ge 1) -Message 'runtime smoke execution manifest carries specialist accounting'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.plan_shadow.specialist_dispatch_unit_count -ge 1) -Message 'runtime smoke plan shadow counts specialist dispatch units'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$executionManifest.dispatch_integrity.proof_passed) -Message 'runtime smoke specialist dispatch integrity proof passes'

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    runtime_summary_path = $summary.summary_path
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-governed-runtime-contract'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-governed-runtime-contract-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-governed-runtime-contract-gate failed with $failureCount failing assertion(s)."
}

$report
