param(
    [Parameter(Mandatory)] [string]$Task,
    [Parameter(Mandatory)] [string]$HostId,
    [Parameter(Mandatory)] [string]$EntryId,
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$RunId = '',
    [AllowEmptyString()] [string]$ArtifactRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$runtimeEntrypoint = Join-Path $PSScriptRoot 'invoke-vibe-runtime.ps1'
$launcherPath = $PSCommandPath
$previousHostId = $env:VCO_HOST_ID

try {
    $env:VCO_HOST_ID = $HostId

    $invokeArgs = @{
        Task = $Task
        Mode = 'interactive_governed'
    }
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        $invokeArgs.RunId = $RunId
    }
    if (-not [string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        $invokeArgs.ArtifactRoot = $ArtifactRoot
    }

    $result = & $runtimeEntrypoint @invokeArgs
    $payload = [pscustomobject]@{
        host_id = $HostId
        entry_id = $EntryId
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
