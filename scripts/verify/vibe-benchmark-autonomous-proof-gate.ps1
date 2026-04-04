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
    'config/benchmark-execution-policy.json',
    'scripts/runtime/Invoke-PlanExecute.ps1',
    'tests/runtime_neutral/test_governed_runtime_bridge.py'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required benchmark proof file exists: {0}" -f $relativePath) -Details $fullPath
}

$runId = "benchmark-proof-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\benchmark-proof-{0}" -f $runId)
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$summary = & $runtimeEntryPath -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' -Mode benchmark_autonomous -RunId $runId -ArtifactRoot $artifactRoot

$executeReceiptPath = [string]$summary.summary.artifacts.execute_receipt
$executionManifestPath = [string]$summary.summary.artifacts.execution_manifest
$proofManifestPath = [string]$summary.summary.artifacts.benchmark_proof_manifest
$cleanupReceiptPath = [string]$summary.summary.artifacts.cleanup_receipt
$runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet

foreach ($path in @($runtimeInputPacketPath, $executeReceiptPath, $executionManifestPath, $proofManifestPath, $cleanupReceiptPath)) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $path) -Message ("benchmark artifact exists: {0}" -f ([System.IO.Path]::GetFileName($path))) -Details $path
}

$runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executeReceipt = Get-Content -LiteralPath $executeReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$proofManifest = Get-Content -LiteralPath $proofManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$cleanupReceipt = Get-Content -LiteralPath $cleanupReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'benchmark proof summary normalizes legacy benchmark mode to interactive_governed'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.stage -eq 'runtime_input_freeze') -Message 'runtime input packet is frozen before execution'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.runtime_mode -eq 'interactive_governed') -Message 'runtime input packet records interactive_governed as the effective mode'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.canonical_router.unattended) -Message 'legacy benchmark mode no longer drives unattended router execution'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.provenance.proof_class -eq 'structure') -Message 'runtime input packet carries structure proof class'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.route_snapshot.selected_skill -eq 'vibe') -Message 'runtime input packet keeps vibe as the frozen route skill for governed entry'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'runtime input packet keeps vibe as runtime authority'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.divergence_shadow.skill_mismatch) -Message 'runtime input packet keeps router/runtime alignment for explicit governed vibe entry'
Add-Assertion -Results ([ref]$results) -Condition (@($runtimeInputPacket.specialist_recommendations).Count -ge 1) -Message 'runtime input packet carries specialist recommendations'
Add-Assertion -Results ([ref]$results) -Condition ((@($runtimeInputPacket.specialist_recommendations | ForEach-Object { [string]$_.skill_id }) -contains 'systematic-debugging')) -Message 'runtime input packet carries systematic-debugging as bounded specialist recommendation'
Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -ne 'execution-contract-prepared') -Message 'execute receipt is no longer receipt-only'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'completed') -Message 'execution manifest status is completed' -Details $executionManifest.status
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.executed_unit_count -ge 2) -Message 'benchmark executed at least two real units' -Details $executionManifest.executed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.failed_unit_count -eq 0) -Message 'benchmark execution has zero failed units' -Details $executionManifest.failed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.proof_class -eq 'runtime') -Message 'execution manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$executeReceipt.plan_shadow_path)) -Message 'plan-derived shadow manifest exists' -Details ([string]$executeReceipt.plan_shadow_path)
Add-Assertion -Results ([ref]$results) -Condition ([int]$executeReceipt.specialist_recommendation_count -ge 1) -Message 'execute receipt carries specialist recommendation count'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executeReceipt.specialist_dispatch_unit_count -ge 1) -Message 'execute receipt carries specialist dispatch unit count'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.specialist_accounting.recommendation_count -ge 1) -Message 'execution manifest carries specialist accounting'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.specialist_accounting.dispatch_unit_count -ge 1) -Message 'execution manifest carries specialist dispatch accounting'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$executionManifest.route_runtime_alignment.skill_mismatch) -Message 'execution manifest preserves governed vibe alignment while still carrying specialist accounting'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$executionManifest.dispatch_integrity.proof_passed) -Message 'execution manifest specialist dispatch integrity proof passes'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.proof_passed) -Message 'benchmark proof manifest marks proof_passed=true'
Add-Assertion -Results ([ref]$results) -Condition ($proofManifest.proof_class -eq 'runtime') -Message 'benchmark proof manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition ([int]$proofManifest.specialist_recommendation_count -ge 1) -Message 'benchmark proof manifest carries specialist recommendation count'
Add-Assertion -Results ([ref]$results) -Condition ([int]$proofManifest.specialist_dispatch_unit_count -ge 1) -Message 'benchmark proof manifest carries specialist dispatch count'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.dispatch_integrity_proof_passed) -Message 'benchmark proof manifest carries dispatch integrity proof result'
Add-Assertion -Results ([ref]$results) -Condition ($cleanupReceipt.cleanup_mode -eq 'receipt_only') -Message 'legacy benchmark mode now uses interactive_governed cleanup defaults'
Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$cleanupReceipt.default_bounded_cleanup_applied) -Message 'legacy benchmark mode no longer applies bounded cleanup by default'
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
        Join-Path $repoRoot 'outputs\verify\vibe-benchmark-autonomous-proof'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-benchmark-autonomous-proof-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-benchmark-autonomous-proof-gate failed with $failureCount failing assertion(s)."
}

$report
