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
    'config/runtime-input-packet-policy.json',
    'config/proof-class-registry.json',
    'config/messy-real-task-corpus.json',
    'config/path-ecology-board.json',
    'config/authoritative-promotion-board.json',
    'references/proof-class-governance.md',
    'docs/governance/vco-remediation-runtime-foundation.md',
    'scripts/runtime/Freeze-RuntimeInputPacket.ps1',
    'scripts/verify/vibe-benchmark-autonomous-proof-gate.ps1'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required remediation foundation file exists: {0}" -f $relativePath) -Details $fullPath
}

$runId = "remediation-foundation-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\remediation-foundation-{0}" -f $runId)
$summary = & $runtimeEntryPath -Task 'remediation foundation runtime proof' -Mode benchmark_autonomous -RunId $runId -ArtifactRoot $artifactRoot

$runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet
$executeReceiptPath = [string]$summary.summary.artifacts.execute_receipt
$executionManifestPath = [string]$summary.summary.artifacts.execution_manifest
$proofManifestPath = [string]$summary.summary.artifacts.benchmark_proof_manifest
$cleanupReceiptPath = [string]$summary.summary.artifacts.cleanup_receipt

$runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executeReceipt = Get-Content -LiteralPath $executeReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$proofManifest = Get-Content -LiteralPath $proofManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$cleanupReceipt = Get-Content -LiteralPath $cleanupReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json

Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.stage -eq 'runtime_input_freeze') -Message 'runtime input packet stage emitted'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.provenance.proof_class -eq 'structure') -Message 'runtime input packet proof class is structure'
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath ([string]$executeReceipt.plan_shadow_path)) -Message 'plan-derived execution shadow artifact exists' -Details ([string]$executeReceipt.plan_shadow_path)
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.proof_class -eq 'runtime') -Message 'execution manifest proof class is runtime'
Add-Assertion -Results ([ref]$results) -Condition ($proofManifest.proof_class -eq 'runtime') -Message 'benchmark proof manifest proof class is runtime'
Add-Assertion -Results ([ref]$results) -Condition (@('receipt_only', 'bounded_cleanup_executed', 'destructive_cleanup_applied', 'cleanup_degraded') -contains [string]$cleanupReceipt.cleanup_mode) -Message 'cleanup receipt uses approved taxonomy' -Details ([string]$cleanupReceipt.cleanup_mode)

$pathBoard = Get-Content -LiteralPath (Join-Path $repoRoot 'config\path-ecology-board.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$promotionBoard = Get-Content -LiteralPath (Join-Path $repoRoot 'config\authoritative-promotion-board.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$corpus = Get-Content -LiteralPath (Join-Path $repoRoot 'config\messy-real-task-corpus.json') -Raw -Encoding UTF8 | ConvertFrom-Json

Add-Assertion -Results ([ref]$results) -Condition (@($pathBoard.lanes).Count -ge 5) -Message 'path ecology board covers at least five lanes'
Add-Assertion -Results ([ref]$results) -Condition (@($promotionBoard.decisions).Count -ge 4) -Message 'promotion board covers multiple promotion decisions'
Add-Assertion -Results ([ref]$results) -Condition (@($corpus.tasks).Count -ge 5) -Message 'messy task corpus includes at least five scenarios'

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
        Join-Path $repoRoot 'outputs\verify\vibe-remediation-foundation'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-remediation-foundation-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-remediation-foundation-gate failed with $failureCount failing assertion(s)."
}

$report
