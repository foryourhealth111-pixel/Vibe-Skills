param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Add-Assertion {
    param(
        [System.Collections.Generic.List[object]]$Assertions,
        [bool]$Pass,
        [string]$Message,
        [object]$Details = $null
    )

    $Assertions.Add([pscustomobject]@{
        pass = [bool]$Pass
        message = $Message
        details = $Details
    }) | Out-Null

    Write-Host ("[{0}] {1}" -f $(if ($Pass) { 'PASS' } else { 'FAIL' }), $Message) -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-release-truth-consistency-gate.json'
    $mdPath = Join-Path $dir 'vibe-release-truth-consistency-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Release Truth Consistency Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failure count: `{0}`' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )
    foreach ($assertion in @($Artifact.assertions)) {
        $lines += ('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)
    }
    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$assertions = [System.Collections.Generic.List[object]]::new()

$releaseReadmePath = Join-Path $repoRoot 'docs\releases\README.md'
$proofBundlePath = Join-Path $repoRoot 'docs\status\non-regression-proof-bundle.md'
$routerTruthPath = Join-Path $repoRoot 'docs\status\router-platform-truth-matrix-2026-03-15.md'
$previewContractPath = Join-Path $repoRoot 'config\operator-preview-contract.json'
$promotionBoardPath = Join-Path $repoRoot 'config\promotion-board.json'

$releaseReadme = Get-Content -LiteralPath $releaseReadmePath -Raw -Encoding UTF8
$proofBundle = Get-Content -LiteralPath $proofBundlePath -Raw -Encoding UTF8
$routerTruth = Get-Content -LiteralPath $routerTruthPath -Raw -Encoding UTF8
$previewContract = Get-Content -LiteralPath $previewContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$releaseCutOperator = $previewContract.operators.'release-cut'
$promotionBoard = Get-Content -LiteralPath $promotionBoardPath -Raw -Encoding UTF8 | ConvertFrom-Json
$releasePlane = @($promotionBoard.planes | Where-Object { [string]$_.plane_id -eq 'operator-release-train' }) | Select-Object -First 1

Add-Assertion -Assertions $assertions -Pass ($releaseReadme.Contains('fallback-truth consistency proof')) -Message 'release README documents fallback-truth consistency proof'
Add-Assertion -Assertions $assertions -Pass ($proofBundle.Contains('vibe-release-truth-consistency-gate.ps1')) -Message 'non-regression proof bundle requires release-truth consistency gate'
Add-Assertion -Assertions $assertions -Pass ($routerTruth.Contains('release-truth consistency proof')) -Message 'router platform truth matrix names release-truth consistency proof'
Add-Assertion -Assertions $assertions -Pass (@($releaseCutOperator.apply_gates) -contains 'scripts/verify/vibe-release-truth-consistency-gate.ps1') -Message 'release-cut contract includes release-truth consistency gate'
Add-Assertion -Assertions $assertions -Pass ($null -ne $releasePlane) -Message 'promotion board contains operator-release-train plane'
if ($releasePlane) {
    Add-Assertion -Assertions $assertions -Pass (@($releasePlane.required_gates) -contains 'vibe-release-truth-consistency-gate') -Message 'operator-release-train plane requires release-truth consistency gate'
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$artifact = [pscustomobject]@{
    gate = 'vibe-release-truth-consistency-gate'
    repo_root = $repoRoot
    gate_result = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [pscustomobject]@{
        failure_count = $failureCount
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
