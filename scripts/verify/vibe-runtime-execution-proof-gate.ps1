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
$results = @()

$requiredFiles = @(
    'config/execution-runtime-policy.json',
    'scripts/runtime/Invoke-PlanExecute.ps1',
    'tests/runtime_neutral/test_governed_runtime_bridge.py'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required execution proof file exists: {0}" -f $relativePath) -Details $fullPath
}

$runId = "execution-proof-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\execution-proof-{0}" -f $runId)
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$summary = & $runtimeEntryPath -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' -Mode interactive_governed -RunId $runId -ArtifactRoot $artifactRoot

$executeReceiptPath = [string]$summary.summary.artifacts.execute_receipt
$executionManifestPath = [string]$summary.summary.artifacts.execution_manifest
$proofManifestPath = [string]$summary.summary.artifacts.execution_proof_manifest
$cleanupReceiptPath = [string]$summary.summary.artifacts.cleanup_receipt
$runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet

foreach ($path in @($runtimeInputPacketPath, $executeReceiptPath, $executionManifestPath, $proofManifestPath, $cleanupReceiptPath)) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $path) -Message ("execution artifact exists: {0}" -f ([System.IO.Path]::GetFileName($path))) -Details $path
}

$runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executeReceipt = Get-Content -LiteralPath $executeReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$proofManifest = Get-Content -LiteralPath $proofManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$cleanupReceipt = Get-Content -LiteralPath $cleanupReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'execution proof summary runs in interactive_governed mode'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.stage -eq 'runtime_input_freeze') -Message 'runtime input packet is frozen before execution'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.runtime_mode -eq 'interactive_governed') -Message 'runtime input packet records interactive_governed mode'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.canonical_router.unattended) -Message 'interactive_governed keeps router unattended flag disabled'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.provenance.proof_class -eq 'structure') -Message 'runtime input packet carries structure proof class'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.route_snapshot.selected_skill -eq 'vibe') -Message 'runtime input packet keeps vibe as the frozen route skill for governed entry'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'runtime input packet keeps vibe as runtime authority'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.divergence_shadow.skill_mismatch) -Message 'runtime input packet keeps router/runtime alignment for explicit governed vibe entry'
$specialistDecision = if ($runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_decision') { $runtimeInputPacket.specialist_decision } else { $null }
$noSpecialistResolved = (
    $null -ne $specialistDecision -and
    $specialistDecision.PSObject.Properties.Name -contains 'decision_state' -and
    $specialistDecision.PSObject.Properties.Name -contains 'resolution_mode' -and
    [string]$specialistDecision.decision_state -eq 'no_specialist_recommendations' -and
    [string]$specialistDecision.resolution_mode -in @('no_matching_specialist', 'no_specialist_needed')
)
$specialistRecommendationIds = @($runtimeInputPacket.specialist_recommendations | ForEach-Object { [string]$_.skill_id })
Add-Assertion -Results ([ref]$results) -Condition ((@($specialistRecommendationIds).Count -ge 1) -or $noSpecialistResolved) -Message 'runtime input packet carries specialist recommendations or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition ((@($specialistRecommendationIds) -contains 'systematic-debugging') -or $noSpecialistResolved) -Message 'runtime input packet carries systematic-debugging or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -ne 'execution-contract-prepared') -Message 'execute receipt is no longer receipt-only'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'completed') -Message 'execution manifest status is completed' -Details $executionManifest.status
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.executed_unit_count -ge 2) -Message 'runtime execution runs at least two real units' -Details $executionManifest.executed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.failed_unit_count -eq 0) -Message 'runtime execution has zero failed units' -Details $executionManifest.failed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.proof_class -eq 'runtime') -Message 'execution manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$executeReceipt.plan_shadow_path)) -Message 'plan-derived shadow manifest exists' -Details ([string]$executeReceipt.plan_shadow_path)
Add-Assertion -Results ([ref]$results) -Condition (([int]$executeReceipt.specialist_recommendation_count -ge 1) -or $noSpecialistResolved) -Message 'execute receipt carries specialist recommendation count or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition (([int]$executeReceipt.specialist_dispatch_unit_count -ge 1) -or $noSpecialistResolved) -Message 'execute receipt carries specialist dispatch unit count or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition (($null -ne $executionManifest.specialist_accounting) -and (([int]$executionManifest.specialist_accounting.recommendation_count -ge 1) -or $noSpecialistResolved)) -Message 'execution manifest carries specialist accounting'
Add-Assertion -Results ([ref]$results) -Condition (($null -ne $executionManifest.specialist_accounting) -and (([int]$executionManifest.specialist_accounting.dispatch_unit_count -ge 1) -or $noSpecialistResolved)) -Message 'execution manifest carries specialist dispatch accounting'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$executionManifest.route_runtime_alignment.skill_mismatch) -Message 'execution manifest preserves governed vibe alignment while still carrying specialist accounting'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$executionManifest.dispatch_integrity.proof_passed) -Message 'execution manifest specialist dispatch integrity proof passes'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.proof_passed) -Message 'execution proof manifest marks proof_passed=true'
Add-Assertion -Results ([ref]$results) -Condition ($proofManifest.proof_class -eq 'runtime') -Message 'execution proof manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition (([int]$proofManifest.specialist_recommendation_count -ge 1) -or $noSpecialistResolved) -Message 'execution proof manifest carries specialist recommendation count or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition (([int]$proofManifest.specialist_dispatch_unit_count -ge 1) -or $noSpecialistResolved) -Message 'execution proof manifest carries specialist dispatch count or no-specialist resolution'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.dispatch_integrity_proof_passed) -Message 'execution proof manifest carries dispatch integrity proof result'
Add-Assertion -Results ([ref]$results) -Condition ($cleanupReceipt.cleanup_mode -eq 'receipt_only') -Message 'interactive_governed uses receipt-only cleanup defaults here'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$cleanupReceipt.default_bounded_cleanup_applied) -Message 'interactive_governed does not apply bounded cleanup by default'
Add-Assertion -Results ([ref]$results) -Condition ($cleanupReceipt.proof_class -eq 'runtime') -Message 'cleanup receipt carries runtime proof class'

foreach ($resultPath in @($proofManifest.result_paths)) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $resultPath) -Message ("result receipt exists: {0}" -f ([System.IO.Path]::GetFileName($resultPath))) -Details $resultPath
    if (-not (Test-Path -LiteralPath $resultPath)) {
        continue
    }

    $result = Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Results ([ref]$results) -Condition ($result.status -eq 'completed') -Message ("unit completed: {0}" -f [string]$result.unit_id) -Details $result.status
    Add-Assertion -Results ([ref]$results) -Condition ([int]$result.exit_code -eq 0) -Message ("unit exit code is zero: {0}" -f [string]$result.unit_id) -Details $result.exit_code
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$result.stdout_path)) -Message ("stdout log exists: {0}" -f [string]$result.unit_id) -Details ([string]$result.stdout_path)
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$result.stderr_path)) -Message ("stderr log exists: {0}" -f [string]$result.unit_id) -Details ([string]$result.stderr_path)
}

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
        Join-Path $repoRoot 'outputs\verify\vibe-runtime-execution-proof'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-runtime-execution-proof-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-runtime-execution-proof-gate failed with $failureCount failing assertion(s)."
}

$report
