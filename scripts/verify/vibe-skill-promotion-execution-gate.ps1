param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'

function Add-Assertion {
    param(
        [ref]$Results,
        [bool]$Condition,
        [string]$Message,
        [object]$Details = $null
    )

    $entry = [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }
    $Results.Value += $entry
    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }
}

function Get-ArraySafe {
    param(
        [AllowNull()] [object]$Value
    )

    if ($null -eq $Value) {
        return @()
    }
    return @($Value)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$runtimeScript = Join-Path $repoRoot 'scripts\runtime\invoke-vibe-runtime.ps1'
$outputRoot = if ($OutputDirectory) { $OutputDirectory } else { Join-Path $repoRoot 'outputs\verify\vibe-skill-promotion-execution-gate' }
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

$mlPrompt = 'Build a scikit-learn tabular classification baseline, run feature selection, and compare cross-validation metrics.'
$destructivePrompt = 'Delete the old generated artifacts, remove the obsolete branch, and overwrite the install settings to reset the environment.'

$results = @()
$cases = @(
    [pscustomobject]@{
        id = 'non_destructive_ml'
        prompt = $mlPrompt
    },
    [pscustomobject]@{
        id = 'destructive_reset'
        prompt = $destructivePrompt
    }
)

$caseReports = @()
foreach ($case in @($cases)) {
    $artifactRoot = Join-Path $outputRoot $case.id
    New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null
    $payload = & $runtimeScript -Task ([string]$case.prompt) -Mode interactive_governed -ArtifactRoot $artifactRoot
    $summary = $payload.summary
    $runtimeInput = Get-Content -LiteralPath ([string]$summary.artifacts.runtime_input_packet) -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionManifest = Get-Content -LiteralPath ([string]$summary.artifacts.execution_manifest) -Raw -Encoding UTF8 | ConvertFrom-Json
    $dispatch = $runtimeInput.specialist_dispatch
    $funnel = $executionManifest.specialist_accounting.promotion_funnel

    if ([string]$case.id -eq 'non_destructive_ml') {
        Add-Assertion -Results ([ref]$results) -Condition ((Get-ArraySafe -Value $dispatch.approved_skill_ids) -contains 'scikit-learn') -Message 'ML prompt promotes scikit-learn into approved dispatch'
        Add-Assertion -Results ([ref]$results) -Condition ((Get-ArraySafe -Value $dispatch.ghost_match_skill_ids).Count -eq 0) -Message 'ML prompt has zero ghost matches'
        Add-Assertion -Results ([ref]$results) -Condition ([int]$funnel.dispatched -ge 1) -Message 'ML prompt dispatches at least one specialist'
        Add-Assertion -Results ([ref]$results) -Condition (([int]$executionManifest.specialist_accounting.executed_specialist_unit_count + [int]$executionManifest.specialist_accounting.degraded_specialist_unit_count) -ge 1) -Message 'ML prompt resolves to executed or degraded specialist outcome'
    } else {
        Add-Assertion -Results ([ref]$results) -Condition ((Get-ArraySafe -Value $dispatch.approved_dispatch).Count -eq 0) -Message 'Destructive prompt does not auto-approve specialist dispatch'
        Add-Assertion -Results ([ref]$results) -Condition ((Get-ArraySafe -Value $dispatch.blocked_skill_ids).Count -ge 1) -Message 'Destructive prompt records explicit blocked specialist skill ids'
        Add-Assertion -Results ([ref]$results) -Condition ((Get-ArraySafe -Value $dispatch.ghost_match_skill_ids).Count -eq 0) -Message 'Destructive prompt has zero ghost matches'
        Add-Assertion -Results ([ref]$results) -Condition ([int]$funnel.blocked_due_to_destructive -ge 1) -Message 'Destructive prompt increments blocked_due_to_destructive funnel counter'
    }

    $caseReports += [pscustomobject]@{
        id = [string]$case.id
        artifact_root = $artifactRoot
        runtime_input_packet = [string]$summary.artifacts.runtime_input_packet
        execution_manifest = [string]$summary.artifacts.execution_manifest
        specialist_accounting = $executionManifest.specialist_accounting
    }
}

$failed = @($results | Where-Object { -not [bool]$_.passed })
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    gate = 'vibe-skill-promotion-execution-gate'
    passed = [bool](@($failed).Count -eq 0)
    assertion_count = @($results).Count
    failed_count = @($failed).Count
    results = @($results)
    cases = @($caseReports)
}

if ($WriteArtifacts) {
    $jsonPath = Join-Path $outputRoot 'vibe-skill-promotion-execution-gate.json'
    $mdPath = Join-Path $outputRoot 'vibe-skill-promotion-execution-gate.md'
    $report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    @(
        '# Vibe Skill Promotion Execution Gate',
        '',
        ('- passed: `{0}`' -f [bool]$report.passed),
        ('- assertion_count: `{0}`' -f [int]$report.assertion_count),
        ('- failed_count: `{0}`' -f [int]$report.failed_count)
    ) | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host "Artifacts written:"
    Write-Host "- $jsonPath"
    Write-Host "- $mdPath"
}

if (-not [bool]$report.passed) {
    exit 1
}

exit 0
