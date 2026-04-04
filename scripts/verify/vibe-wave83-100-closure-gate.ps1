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
    $Assertions.Add([pscustomobject]@{ pass = [bool]$Pass; message = $Message; details = $Details }) | Out-Null
    $color = if ($Pass) { 'Green' } else { 'Red' }
    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    Write-Host ('[{0}] {1}' -f $status, $Message) -ForegroundColor $color
}

function Write-ClosureArtifacts {
    param([string]$RepoRoot, [string]$OutputDirectory, [psobject]$Artifact)
    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-wave83-100-closure-gate.json'
    $mdPath = Join-Path $dir 'vibe-wave83-100-closure-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)
    $lines = @(
        '# VCO Wave83-100 Closure Gate',
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

$boardPath = Join-Path $repoRoot 'config\wave83-100-planning-board.json'
$statusPath = Join-Path $repoRoot 'config\wave83-100-execution-status.json'
$statusDoc = Join-Path $repoRoot 'docs\plans\2026-03-07-vco-wave83-100-execution-status.md'
$manifestPath = Join-Path $repoRoot 'config\wave83-100-gate-manifest.json'
$releaseReadme = Join-Path $repoRoot 'docs\releases\README.md'
$releaseCut = Join-Path $repoRoot 'scripts\governance\release-cut.ps1'
$releaseCutApplyGates = @(Get-VgoOperatorPreviewStringListProperty -RepoRoot $repoRoot -OperatorId 'release-cut' -PropertyName 'apply_gates')
$dashboardJson = Join-Path $repoRoot 'outputs\dashboard\ops-dashboard.json'
$bundleJson = Join-Path $repoRoot 'outputs\release\release-evidence-bundle.json'
$suggestionsJson = Join-Path $repoRoot 'outputs\learn\vibe-adaptive-suggestions.json'
$reauditPath = Join-Path $repoRoot 'references\upstream-reaudit-matrix-v2.md'
$manualApplyPath = Join-Path $repoRoot 'config\manual-apply-policy.json'
$observabilityPath = Join-Path $repoRoot 'config\observability-policy.json'

foreach ($path in @($boardPath, $statusPath, $statusDoc, $manifestPath, $dashboardJson, $bundleJson, $suggestionsJson, $reauditPath, $manualApplyPath, $observabilityPath)) {
    Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $path) -Message ('required closure asset exists: ' + (Get-VgoRelativePathPortable -BasePath $repoRoot -TargetPath $path)) -Details $path
}

if (Test-Path -LiteralPath $boardPath) {
    $board = Get-Content -LiteralPath $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Assertions $assertions -Pass (@($board.allowed_statuses) -contains 'completed') -Message 'planning board allows completed status'
    $waves = @($board.waves)
    Add-Assertion -Assertions $assertions -Pass ($waves.Count -eq 18) -Message 'planning board covers 18 waves (83-100)' -Details $waves.Count
    $incomplete = @($waves | Where-Object { $_.status -ne 'completed' } | ForEach-Object { [int]$_.wave })
    Add-Assertion -Assertions $assertions -Pass ($incomplete.Count -eq 0) -Message 'all waves 83-100 are marked completed' -Details $incomplete
}

if (Test-Path -LiteralPath $statusPath) {
    $status = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Assertions $assertions -Pass ($status.overall_status -eq 'completed_wave83_100') -Message 'execution status marks Wave83-100 completed' -Details $status.overall_status
    Add-Assertion -Assertions $assertions -Pass (@($status.completed_waves).Count -eq 18) -Message 'execution status lists 18 completed waves' -Details (@($status.completed_waves).Count)
}

if (Test-Path -LiteralPath $releaseReadme) {
    $raw = Get-Content -LiteralPath $releaseReadme -Raw -Encoding UTF8
    foreach ($keyword in @('Wave83-100 Extended Gates', 'vibe-release-evidence-bundle-gate.ps1', 'vibe-manual-apply-policy-gate.ps1', 'vibe-rollout-proposal-boundedness-gate.ps1', 'vibe-upstream-reaudit-matrix-gate.ps1', 'vibe-wave83-100-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($raw.Contains($keyword)) -Message ('release README contains ' + $keyword) -Details $keyword
    }
}

if ($releaseCutApplyGates.Count -gt 0) {
    foreach ($keyword in @('scripts/verify/vibe-gate-reliability-gate.ps1', 'scripts/verify/vibe-ops-dashboard-gate.ps1', 'scripts/verify/vibe-release-evidence-bundle-gate.ps1', 'scripts/verify/vibe-wave83-100-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($releaseCutApplyGates -contains $keyword) -Message ('release-cut contract includes ' + (Split-Path $keyword -Leaf)) -Details $keyword
    }
    $wave63Gate = 'scripts/verify/vibe-deep-extraction-pilot-gate.ps1'
    $wave64Gate = 'scripts/verify/vibe-memory-runtime-v3-gate.ps1'
    $wave63Index = [array]::IndexOf($releaseCutApplyGates, $wave63Gate)
    $wave64Index = [array]::IndexOf($releaseCutApplyGates, $wave64Gate)
    Add-Assertion -Assertions $assertions -Pass ($wave63Index -ge 0 -and $wave64Index -gt $wave63Index) -Message 'release-cut contract preserves wave63-to-wave64 gate boundary' -Details ([pscustomobject]@{ wave63_index = $wave63Index; wave64_index = $wave64Index })
} elseif (Test-Path -LiteralPath $releaseCut) {
    $raw = Get-Content -LiteralPath $releaseCut -Raw -Encoding UTF8
    foreach ($keyword in @('vibe-gate-reliability-gate.ps1', 'vibe-ops-dashboard-gate.ps1', 'vibe-release-evidence-bundle-gate.ps1', 'vibe-wave83-100-closure-gate.ps1')) {
        Add-Assertion -Assertions $assertions -Pass ($raw.Contains($keyword)) -Message ('release-cut fallback includes ' + $keyword) -Details $keyword
    }
    $missingCommaPattern = 'vibe-deep-extraction-pilot-gate\.ps1"\s*[\r\n]+\s*"scripts\\verify\\vibe-memory-runtime-v3-gate\.ps1'
    Add-Assertion -Assertions $assertions -Pass (-not ($raw -match $missingCommaPattern)) -Message 'release-cut fallback no longer has missing comma break between wave63 and wave64 gates'
}

if (Test-Path -LiteralPath $manualApplyPath) {
    $manual = Get-Content -LiteralPath $manualApplyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Assertions $assertions -Pass ($manual.policy.apply_requires_explicit_flag -eq $true) -Message 'manual apply requires explicit flag'
    Add-Assertion -Assertions $assertions -Pass ($manual.policy.default_action -eq 'report_only') -Message 'manual apply default action is report_only'
    Add-Assertion -Assertions $assertions -Pass ($manual.policy.forbid_auto_promote -eq $true) -Message 'manual apply forbids auto promote'
}

if ((Test-Path -LiteralPath $observabilityPath) -and (Test-Path -LiteralPath $suggestionsJson)) {
    $observability = Get-Content -LiteralPath $observabilityPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $suggestions = Get-Content -LiteralPath $suggestionsJson -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Assertions $assertions -Pass ($suggestions.apply_policy -eq 'manual_review_required') -Message 'rollout suggestions keep manual_review_required'
    $bounds = $observability.learning.bounded_adjustments
    foreach ($row in @($suggestions.recommendations)) {
        if ($row.knob -eq 'confirm_required') {
            Add-Assertion -Assertions $assertions -Pass ([math]::Abs([double]$row.delta) -le [double]$bounds.confirm_required_max_delta) -Message 'closure confirms confirm_required bounded delta' -Details $row.delta
        }
        if ($row.knob -eq 'fallback_to_legacy_below') {
            Add-Assertion -Assertions $assertions -Pass ([math]::Abs([double]$row.delta) -le [double]$bounds.fallback_threshold_max_delta) -Message 'closure confirms fallback bounded delta' -Details $row.delta
        }
        if ($row.knob -eq 'min_top1_top2_gap') {
            Add-Assertion -Assertions $assertions -Pass ([math]::Abs([double]$row.delta) -le [double]$bounds.min_top_gap_max_delta) -Message 'closure confirms top-gap bounded delta' -Details $row.delta
        }
    }
}

if (Test-Path -LiteralPath $reauditPath) {
    $raw = Get-Content -LiteralPath $reauditPath -Raw -Encoding UTF8
    foreach ($keyword in @('promotion ceiling', 'explicit no-go', 'docling', 'agent-squad', 'awesome-vibe-coding')) {
        Add-Assertion -Assertions $assertions -Pass ($raw.ToLower().Contains($keyword.ToLower())) -Message ('re-audit matrix contains ' + $keyword) -Details $keyword
    }
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$result = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
$artifact = [pscustomobject]@{
    gate = 'vibe-wave83-100-closure-gate'
    title = 'Wave83-100 closure gate'
    repo_root = $repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = $result
    assertions = @($assertions)
    summary = [ordered]@{ total = $assertions.Count; failure_count = $failureCount }
}

if ($WriteArtifacts) {
    Write-ClosureArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
