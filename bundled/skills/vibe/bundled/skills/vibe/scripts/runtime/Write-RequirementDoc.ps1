param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$IntentContractPath = '',
    [string]$RuntimeInputPacketPath = '',
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
if (-not [string]::IsNullOrWhiteSpace($IntentContractPath) -and (Test-Path -LiteralPath $IntentContractPath)) {
    $intentContract = Get-Content -LiteralPath $IntentContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $intentContract = New-VibeIntentContractObject -Task $Task -Mode $Mode
}

$docPath = Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot
$antiDriftDraft = New-VgoAntiProxyGoalDriftDraft -PrimaryObjective $intentContract.goal
$runtimeInputPacket = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath) -and (Test-Path -LiteralPath $RuntimeInputPacketPath)) {
    Get-Content -LiteralPath $RuntimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$lines = @(
    "# $($intentContract.title)",
    '',
    '## Summary',
    $intentContract.goal,
    '',
    '## Goal',
    $intentContract.goal,
    '',
    '## Deliverable',
    $intentContract.deliverable,
    '',
    '## Constraints'
)
$lines += @($intentContract.constraints | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Acceptance Criteria'
)
$lines += @($intentContract.acceptance_criteria | ForEach-Object { "- $_" })
$lines += @(
    '',
    '> Fill the anti-drift fields once here. Downstream governed plan and completion surfaces should reuse them rather than restate them.',
    ''
)
$lines += @(Get-VgoAntiProxyGoalDriftRequirementLines -Packet $antiDriftDraft)
$lines += @(
    '',
    '## Non-Goals'
)
$lines += @($intentContract.non_goals | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Autonomy Mode',
    $intentContract.autonomy_mode,
    '',
    '## Assumptions'
)
$lines += @($intentContract.assumptions | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Evidence Inputs',
    "- Source task: $Task",
    "- Intent contract: $([System.IO.Path]::GetFileName((Join-Path $sessionRoot 'intent-contract.json')))",
    "- Runtime input packet: $([System.IO.Path]::GetFileName($RuntimeInputPacketPath))"
)

if ($runtimeInputPacket) {
    $lines += @(
        '',
        '## Runtime Input Truth',
        "- Selected pack: $([string]$runtimeInputPacket.route_snapshot.selected_pack)",
        "- Router-selected skill: $([string]$runtimeInputPacket.route_snapshot.selected_skill)",
        "- Runtime-selected skill: $([string]$runtimeInputPacket.authority_flags.explicit_runtime_skill)",
        "- Route mode: $([string]$runtimeInputPacket.route_snapshot.route_mode)",
        "- Route reason: $([string]$runtimeInputPacket.route_snapshot.route_reason)",
        "- Confirm required: $([bool]$runtimeInputPacket.route_snapshot.confirm_required)"
    )
}

Write-VibeMarkdownArtifact -Path $docPath -Lines $lines

$receipt = [pscustomobject]@{
    stage = 'requirement_doc'
    run_id = $RunId
    mode = $Mode
    requirement_doc_path = $docPath
    runtime_input_packet_path = $RuntimeInputPacketPath
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'requirement-doc-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    requirement_doc_path = $docPath
    receipt_path = $receiptPath
    receipt = $receipt
}
