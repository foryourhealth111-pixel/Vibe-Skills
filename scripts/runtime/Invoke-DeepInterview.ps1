param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$HostDecisionJson = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $ArtifactRoot
$hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $HostDecisionJson
$intentContract = New-VibeIntentContractObject -Task $Task -Mode $Mode -HostDecision $hostDecision
$receiptPath = Join-Path $sessionRoot 'intent-contract.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $intentContract

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    receipt_path = $receiptPath
    intent_contract = $intentContract
}
