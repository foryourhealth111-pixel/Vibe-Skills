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
$summary = & (Join-Path $repoRoot 'scripts\runtime\invoke-vibe-runtime.ps1') -Task 'benchmark autonomous proof closure' -Mode benchmark_autonomous -RunId $runId -ArtifactRoot $artifactRoot

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

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'benchmark_autonomous') -Message 'benchmark proof summary preserves benchmark_autonomous mode'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.stage -eq 'runtime_input_freeze') -Message 'runtime input packet is frozen before execution'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.provenance.proof_class -eq 'structure') -Message 'runtime input packet carries structure proof class'
Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -ne 'execution-contract-prepared') -Message 'execute receipt is no longer receipt-only'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'completed') -Message 'execution manifest status is completed' -Details $executionManifest.status
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.executed_unit_count -ge 2) -Message 'benchmark executed at least two real units' -Details $executionManifest.executed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.failed_unit_count -eq 0) -Message 'benchmark execution has zero failed units' -Details $executionManifest.failed_unit_count
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.proof_class -eq 'runtime') -Message 'execution manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$executeReceipt.plan_shadow_path)) -Message 'plan-derived shadow manifest exists' -Details ([string]$executeReceipt.plan_shadow_path)
Add-Assertion -Results ([ref]$results) -Condition ([bool]$proofManifest.proof_passed) -Message 'benchmark proof manifest marks proof_passed=true'
Add-Assertion -Results ([ref]$results) -Condition ($proofManifest.proof_class -eq 'runtime') -Message 'benchmark proof manifest carries runtime proof class'
Add-Assertion -Results ([ref]$results) -Condition ($cleanupReceipt.cleanup_mode -eq 'bounded_cleanup_executed') -Message 'benchmark cleanup is materially executed by default'
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
