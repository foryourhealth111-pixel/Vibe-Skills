param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')
. (Join-Path $PSScriptRoot '..\runtime\VibeRuntime.Common.ps1')

function Add-Assertion {
    param(
        [ref]$Assertions,
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ''
    )

    $record = [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }
    $Assertions.Value += $record

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
$assertions = @()

foreach ($relativePath in @(
        'scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1',
        'scripts/common/AntiProxyGoalDrift.ps1',
        'scripts/runtime/Write-RequirementDoc.ps1',
        'scripts/runtime/Write-XlPlan.ps1',
        'templates/requirements/governed-requirement-template.md',
        'templates/plans/governed-execution-plan-template.md'
    )) {
    Add-Assertion -Assertions ([ref]$assertions) -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $relativePath)) -Message ("required compaction file exists: {0}" -f $relativePath)
}

$tempRoot = Join-Path $repoRoot (".tmp\anti-proxy-goal-drift-compaction-{0}" -f ([System.Guid]::NewGuid().ToString('N').Substring(0, 8)))
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

try {
    $requirementPath = Join-Path $tempRoot 'requirement.md'
    $requirementLines = @(
        '# Compaction Smoke',
        '',
        '## Goal',
        'Preserve route quality through shared anti-drift truth.',
        '',
        '## Primary Objective',
        'Preserve route quality through shared anti-drift truth.',
        '',
        '## Non-Objective Proxy Signals',
        '- current test green only',
        '- single sample pass only',
        '',
        '## Validation Material Role',
        'validation_only',
        '',
        '## Anti-Proxy-Goal-Drift Tier',
        'Tier B',
        '',
        '## Intended Scope',
        'shared',
        '',
        '## Abstraction Layer Target',
        'mechanism',
        '',
        '## Completion State',
        'partial',
        '',
        '## Generalization Evidence Bundle',
        '- cases: 1 replay',
        '- note: add independent route cases before generalized completion claim'
    )
    Write-VgoUtf8NoBomText -Path $requirementPath -Content (($requirementLines -join [Environment]::NewLine) + [Environment]::NewLine)

    $packet = Get-VgoAntiProxyGoalDriftPacketFromRequirementDoc -RequirementDocPath $requirementPath
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($packet.primary_objective -eq 'Preserve route quality through shared anti-drift truth.') -Message 'compaction helper reuses primary objective from requirement'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($packet.anti_proxy_goal_drift_tier -eq 'Tier B') -Message 'compaction helper reuses declared tier from requirement'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($packet.completion_state -eq 'partial') -Message 'compaction helper reuses completion state from requirement'
    Add-Assertion -Assertions ([ref]$assertions) -Condition (@($packet.non_objective_proxy_signals).Count -eq 2) -Message 'compaction helper reuses proxy-signal list from requirement'

    $planMarkdown = & (Join-Path $repoRoot 'scripts\runtime\Invoke-AntiProxyGoalDriftCompaction.ps1') -RequirementDocPath $requirementPath -EmitPlanMarkdown
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($planMarkdown.Contains('## Anti-Proxy-Goal-Drift Controls')) -Message 'compaction helper emits anti-drift controls section'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($planMarkdown.Contains('Tier B')) -Message 'compaction helper plan output carries reused tier'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($planMarkdown.Contains('mechanism')) -Message 'compaction helper plan output carries reused abstraction layer'

    $planResult = & (Join-Path $repoRoot 'scripts\runtime\Write-XlPlan.ps1') -Task 'compaction smoke task' -Mode interactive_governed -RunId 'compaction-smoke' -RequirementDocPath $requirementPath -ArtifactRoot $tempRoot
    $generatedPlan = Get-Content -LiteralPath $planResult.execution_plan_path -Raw -Encoding UTF8
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($generatedPlan.Contains('## Anti-Proxy-Goal-Drift Controls')) -Message 'Write-XlPlan includes anti-drift controls in generated plan'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($generatedPlan.Contains('Preserve route quality through shared anti-drift truth.')) -Message 'Write-XlPlan reuses requirement primary objective'
    Add-Assertion -Assertions ([ref]$assertions) -Condition ($generatedPlan.Contains('shared')) -Message 'Write-XlPlan reuses requirement intended scope'
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

$failureCount = @($assertions | Where-Object { -not $_.passed }).Count
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = ($failureCount -eq 0)
    assertion_count = @($assertions).Count
    failure_count = $failureCount
    assertions = @($assertions)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-anti-proxy-goal-drift-compaction-gate.json') -Value $report
}

if ($failureCount -gt 0) {
    throw "vibe-anti-proxy-goal-drift-compaction-gate failed with $failureCount assertion(s)."
}

$report
