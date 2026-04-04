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

    $color = if ($Pass) { 'Green' } else { 'Red' }
    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    Write-Host ('[{0}] {1}' -f $status, $Message) -ForegroundColor $color
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-wave64-82-closure-gate.json'
    $mdPath = Join-Path $dir 'vibe-wave64-82-closure-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)
    $lines = @(
        '# VCO Wave64-82 Closure Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failures: {0}' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )
    foreach ($assertion in $Artifact.assertions) {
        $lines += ('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)
    }
    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$assertions = [System.Collections.Generic.List[object]]::new()

$planPath = Join-Path $repoRoot 'docs\plans\2026-03-07-vco-wave64-82-execution-plan.md'
$boardPath = Join-Path $repoRoot 'config\wave64-82-planning-board.json'
$releaseReadme = Join-Path $repoRoot 'docs\releases\README.md'
$releaseCut = Join-Path $repoRoot 'scripts\governance\release-cut.ps1'
$releaseCutApplyGates = @(Get-VgoOperatorPreviewStringListProperty -RepoRoot $repoRoot -OperatorId 'release-cut' -PropertyName 'apply_gates')
$requiredAssets = @(
    'docs/memory-runtime-v3-governance.md',
    'docs/governance/browserops-scorecard-governance.md',
    'docs/governance/desktopops-replay-governance.md',
    'docs/governance/docling-contract-v2-governance.md',
    'docs/governance/connector-scorecard-governance.md',
    'docs/prompt-intelligence-productization.md',
    'docs/governance/cross-plane-task-contract-governance.md',
    'docs/governance/cross-plane-replay-governance.md',
    'docs/promotion-board-v2-governance.md',
    'docs/ops-cockpit-governance.md',
    'docs/governance/rollback-drill-governance.md',
    'docs/governance/release-train-v2-governance.md',
    'scripts/verify/vibe-memory-runtime-v3-gate.ps1',
    'scripts/verify/vibe-browserops-scorecard-gate.ps1',
    'scripts/verify/vibe-desktopops-replay-gate.ps1',
    'scripts/verify/vibe-docling-contract-v2-gate.ps1',
    'scripts/verify/vibe-connector-scorecard-gate.ps1',
    'scripts/verify/vibe-prompt-intelligence-productization-gate.ps1',
    'scripts/verify/vibe-cross-plane-task-contract-gate.ps1',
    'scripts/verify/vibe-cross-plane-replay-gate.ps1',
    'scripts/verify/vibe-promotion-scorecard-gate.ps1',
    'scripts/verify/vibe-ops-cockpit-gate.ps1',
    'scripts/verify/vibe-rollback-drill-gate.ps1',
    'scripts/verify/vibe-release-train-v2-gate.ps1'
)

Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $planPath) -Message 'wave64-82 execution plan exists' -Details $planPath
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $boardPath) -Message 'wave64-82 planning board exists' -Details $boardPath
foreach ($asset in $requiredAssets) {
    Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath (Join-Path $repoRoot $asset)) -Message ('required wave64-82 asset exists: ' + $asset) -Details $asset
}

if (Test-Path -LiteralPath $boardPath) {
    $board = Get-Content -LiteralPath $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Assertions $assertions -Pass (@($board.allowed_statuses) -contains 'completed') -Message 'planning board allows completed status'
    $waves = @($board.waves)
    Add-Assertion -Assertions $assertions -Pass ($waves.Count -eq 19) -Message 'planning board covers 19 waves (64-82)' -Details $waves.Count
    $incomplete = @($waves | Where-Object { $_.status -ne 'completed' } | ForEach-Object { [int]$_.wave })
    Add-Assertion -Assertions $assertions -Pass ($incomplete.Count -eq 0) -Message 'all waves 64-82 are marked completed' -Details $incomplete
}

if (Test-Path -LiteralPath $releaseReadme) {
    $raw = Get-Content -LiteralPath $releaseReadme -Raw -Encoding UTF8
    foreach ($keyword in @('Wave64-82', 'vibe-release-train-v2-gate.ps1', 'vibe-wave64-82-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($raw.Contains($keyword)) -Message ('release README contains ' + $keyword) -Details $keyword
    }
}

if ($releaseCutApplyGates.Count -gt 0) {
    foreach ($keyword in @('scripts/verify/vibe-memory-runtime-v3-gate.ps1', 'scripts/verify/vibe-promotion-scorecard-gate.ps1', 'scripts/verify/vibe-wave64-82-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($releaseCutApplyGates -contains $keyword) -Message ('release-cut contract includes ' + (Split-Path $keyword -Leaf)) -Details $keyword
    }
} elseif (Test-Path -LiteralPath $releaseCut) {
    $raw = Get-Content -LiteralPath $releaseCut -Raw -Encoding UTF8
    foreach ($keyword in @('vibe-memory-runtime-v3-gate.ps1', 'vibe-promotion-scorecard-gate.ps1', 'vibe-wave64-82-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($raw.Contains($keyword)) -Message ('release-cut fallback includes ' + $keyword) -Details $keyword
    }
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$gateResult = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
$artifact = [pscustomobject]@{
    gate = 'vibe-wave64-82-closure-gate'
    repo_root = $repoRoot
    gate_result = $gateResult
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [ordered]@{ total = $assertions.Count; failure_count = $failureCount }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
