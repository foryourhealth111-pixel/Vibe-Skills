param(
    [Parameter(Mandatory)] [string]$Task,
    [Parameter(Mandatory)] [string]$HostId,
    [Parameter(Mandatory)] [string]$EntryId,
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$RunId = '',
    [AllowEmptyString()] [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$HostDecisionJson = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure consistent UTF-8 encoding for Unicode path compatibility (e.g., Chinese username paths)
if ($PSVersionTable.PSEdition -eq 'Desktop' -or $PSVersionTable.Platform -eq 'Win32NT') {
    # Windows PowerShell 5.x: set console encoding to UTF-8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} else {
    # PowerShell Core 7+: already defaults to UTF-8, but ensure consistency
    $OutputEncoding = [System.Text.Encoding]::UTF8
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$runtimeEntrypoint = Join-Path $PSScriptRoot 'invoke-vibe-runtime.ps1'
$launcherPath = $PSCommandPath
$previousHostId = $env:VCO_HOST_ID

try {
    $env:VCO_HOST_ID = $HostId

    $invokeArgs = @{
        Task = $Task
        Mode = 'interactive_governed'
        EntryIntentId = $EntryId
    }
    if (-not [string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        $invokeArgs.RequestedStageStop = $RequestedStageStop
    }
    if (-not [string]::IsNullOrWhiteSpace($RequestedGradeFloor)) {
        $invokeArgs.RequestedGradeFloor = $RequestedGradeFloor
    }
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        $invokeArgs.RunId = $RunId
    }
    if (-not [string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        $invokeArgs.ArtifactRoot = $ArtifactRoot
    }
    if (-not [string]::IsNullOrWhiteSpace($HostDecisionJson)) {
        $invokeArgs.HostDecisionJson = $HostDecisionJson
    }

    $result = & $runtimeEntrypoint @invokeArgs
    $payload = [pscustomobject]@{
        host_id = $HostId
        entry_id = 'vibe'
        entry_intent_id = $EntryId
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { $RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { $RequestedGradeFloor }
        launcher_path = $launcherPath
        runtime_entrypoint = $runtimeEntrypoint
        run_id = [string]$result.run_id
        session_root = [string]$result.session_root
        summary_path = [string]$result.summary_path
        summary = $result.summary
    }
    $payload | ConvertTo-Json -Depth 20
} finally {
    if ([string]::IsNullOrWhiteSpace($previousHostId)) {
        Remove-Item Env:VCO_HOST_ID -ErrorAction SilentlyContinue
    } else {
        $env:VCO_HOST_ID = $previousHostId
    }
}
