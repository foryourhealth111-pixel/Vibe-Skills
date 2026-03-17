param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$RequirementDocPath = '',
    [string]$ArtifactRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$grade = Get-VibeInternalGrade -Task $Task
$planPath = Get-VibeExecutionPlanPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot
$requirementPath = if (-not [string]::IsNullOrWhiteSpace($RequirementDocPath)) { $RequirementDocPath } else { Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot }
$antiDriftDraft = Get-VgoAntiProxyGoalDriftPacketFromRequirementDoc -RequirementDocPath $requirementPath

$waveLines = switch ($grade) {
    'XL' {
        @(
            '- Wave 1: skeleton, intent freeze, and requirement validation',
            '- Wave 2: implementation decomposition and bounded ownership assignment',
            '- Wave 3: verification, reconciliation, and cleanup handoff'
        )
    }
    'L' {
        @(
            '- Wave 1: design confirmation and implementation preparation',
            '- Wave 2: implementation and targeted verification',
            '- Wave 3: cleanup and residual-risk review'
        )
    }
    default {
        @(
            '- Wave 1: direct implementation with narrow verification',
            '- Wave 2: cleanup and completion evidence'
        )
    }
}

$lines = @(
    "# $(Get-VibeTitleFromTask -Task $Task)",
    '',
    '## Execution Summary',
    "Governed runtime execution plan for `vibe` in mode `$Mode`.",
    '',
    '## Frozen Inputs',
    "- Requirement doc: $([System.IO.Path]::GetFullPath($requirementPath))",
    "- Source task: $Task"
)
$lines += @('')
$lines += @(Get-VgoAntiProxyGoalDriftPlanLines -Packet $antiDriftDraft)
$lines += @(
    '',
    '## Internal Grade Decision',
    "- Grade: $grade",
    '- User-facing runtime remains fixed; grade is internal only.',
    '',
    '## Wave Plan'
)
$lines += $waveLines
$lines += @(
    '',
    '## Ownership Boundaries',
    '- One owner per artifact set.',
    '- Parallel work must use disjoint write scopes.',
    '- Subagent prompts must end with `$vibe`.',
    '',
    '## Verification Commands',
    '- Run targeted repo verification for changed surfaces.',
    '- Run runtime contract gate before claiming completion.',
    '- Re-run mirror sync and parity validation before release claims.',
    '',
    '## Rollback Plan',
    '- Revert only the governed-runtime change set if verification fails.',
    '- Do not roll back unrelated user changes.',
    '',
    '## Phase Cleanup Contract',
    '- Remove temp artifacts created by the wave.',
    '- Run node audit and cleanup when needed.',
    '- Write cleanup receipt before completion.'
)

Write-VibeMarkdownArtifact -Path $planPath -Lines $lines

$receipt = [pscustomobject]@{
    stage = 'xl_plan'
    run_id = $RunId
    mode = $Mode
    internal_grade = $grade
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'execution-plan-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    execution_plan_path = $planPath
    receipt_path = $receiptPath
    receipt = $receipt
}
