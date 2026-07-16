param(
    [Parameter(Mandatory)] [string]$Task,
    [Parameter(Mandatory)] [string]$HostId,
    [Parameter(Mandatory)] [string]$EntryId,
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$RunId = '',
    [AllowEmptyString()] [string]$WorkspaceRoot = '',
    [AllowEmptyString()] [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$HostDecisionJson = '',
    [AllowEmptyString()] [string]$ModuleExecutionJsonFile = '',
    [AllowEmptyString()] [string]$BridgeOutputJsonPath = ''
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
$helperPath = Join-Path $repoRoot 'scripts\common\vibe-governance-helpers.ps1'
$launcherPath = $PSCommandPath
$previousHostId = $env:VCO_HOST_ID

function Get-PreferredPythonInvocation {
    if (Test-Path -LiteralPath $helperPath) {
        . $helperPath
        if (Get-Command Get-VgoPythonCommand -ErrorAction SilentlyContinue) {
            return Get-VgoPythonCommand
        }
    }

    foreach ($candidate in @(
        [pscustomobject]@{ name = 'python3'; prefix_arguments = @() },
        [pscustomobject]@{ name = 'python'; prefix_arguments = @() },
        [pscustomobject]@{ name = 'py'; prefix_arguments = @('-3') }
    )) {
        $command = Get-Command ([string]$candidate.name) -ErrorAction SilentlyContinue
        if ($command) {
            return [pscustomobject]@{
                host_path = $command.Source
                prefix_arguments = @($candidate.prefix_arguments)
            }
        }
    }

    throw 'Python 3.10+ is required to launch the canonical runtime entry.'
}

function Write-Utf8Json {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Payload,
        [int]$Depth = 20
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth $Depth
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $utf8NoBom)
}

function New-CanonicalRunId {
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $suffix = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "$timestamp-$suffix"
}

function Resolve-CanonicalArtifactRoot {
    param(
        [Parameter(Mandatory)] [string]$BaseRoot,
        [AllowEmptyString()] [string]$ArtifactRoot
    )

    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        return [System.IO.Path]::GetFullPath((Join-Path $BaseRoot '.vibeskills'))
    }
    if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) {
        return [System.IO.Path]::GetFullPath($ArtifactRoot)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $BaseRoot $ArtifactRoot))
}

function Resolve-CanonicalSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$ArtifactRoot,
        [Parameter(Mandatory)] [string]$RunId
    )

    return [System.IO.Path]::GetFullPath((Join-Path $ArtifactRoot (Join-Path 'outputs\runtime\vibe-sessions' $RunId)))
}

function New-HostLaunchReceiptPayload {
    param(
        [Parameter(Mandatory)] [string]$HostId,
        [Parameter(Mandatory)] [string]$LauncherPath,
        [AllowEmptyString()] [string]$RequestedStageStop,
        [AllowEmptyString()] [string]$RequestedGradeFloor,
        [Parameter(Mandatory)] [string]$RuntimeEntrypoint,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$LaunchStatus
    )

    return [pscustomobject]@{
        host_id = $HostId
        entry_id = 'vibe'
        launch_mode = 'canonical-entry'
        launcher_path = $LauncherPath
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { $RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { $RequestedGradeFloor }
        runtime_entrypoint = $RuntimeEntrypoint
        run_id = $RunId
        created_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        launch_status = $LaunchStatus
    }
}

function Assert-CanonicalTruthArtifacts {
    param([Parameter(Mandatory)] [string]$SessionRoot)

    $required = @(
        'runtime-input-packet.json',
        'governance-capsule.json',
        'stage-lineage.json'
    )
    $missing = @(
        $required |
            Where-Object { -not (Test-Path -LiteralPath (Join-Path $SessionRoot $_) -PathType Leaf) }
    )
    if ($missing.Count -gt 0) {
        throw ('Missing required Python-built runtime artifacts under session_root: {0}' -f ($missing -join ', '))
    }
}

try {
    $env:VCO_HOST_ID = $HostId
    $resolvedRunId = if ([string]::IsNullOrWhiteSpace($RunId)) { New-CanonicalRunId } else { $RunId }
    $resolvedWorkspaceRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
        if ([System.IO.Path]::IsPathRooted($WorkspaceRoot)) {
            [System.IO.Path]::GetFullPath($WorkspaceRoot)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $repoRoot $WorkspaceRoot))
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        Resolve-CanonicalArtifactRoot -BaseRoot $repoRoot -ArtifactRoot $ArtifactRoot
    } else {
        [System.IO.Path]::GetFullPath($repoRoot)
    }
    $resolvedArtifactRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot) -and -not [string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        $resolvedWorkspaceRoot
    } else {
        Resolve-CanonicalArtifactRoot -BaseRoot $resolvedWorkspaceRoot -ArtifactRoot $ArtifactRoot
    }
    $sessionRoot = Resolve-CanonicalSessionRoot -ArtifactRoot $resolvedArtifactRoot -RunId $resolvedRunId
    $summaryPath = Join-Path $sessionRoot 'runtime-summary.json'
    $receiptPath = Join-Path $sessionRoot 'host-launch-receipt.json'

    $invokeArgs = @{
        Task = $Task
        Mode = 'interactive_governed'
        EntryIntentId = $EntryId
        RunId = $resolvedRunId
        WorkspaceRoot = $resolvedWorkspaceRoot
        ArtifactRoot = $resolvedArtifactRoot
    }
    if (-not [string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        $invokeArgs.RequestedStageStop = $RequestedStageStop
    }
    if (-not [string]::IsNullOrWhiteSpace($RequestedGradeFloor)) {
        $invokeArgs.RequestedGradeFloor = $RequestedGradeFloor
    }
    if (-not [string]::IsNullOrWhiteSpace($HostDecisionJson)) {
        $invokeArgs.HostDecisionJson = $HostDecisionJson
    }
    if (-not [string]::IsNullOrWhiteSpace($ModuleExecutionJsonFile)) {
        $invokeArgs.ModuleExecutionJsonFile = $ModuleExecutionJsonFile
    }

    $launchedReceipt = New-HostLaunchReceiptPayload `
        -HostId $HostId `
        -LauncherPath $launcherPath `
        -RequestedStageStop $RequestedStageStop `
        -RequestedGradeFloor $RequestedGradeFloor `
        -RuntimeEntrypoint $runtimeEntrypoint `
        -RunId $resolvedRunId `
        -LaunchStatus 'launched'
    Write-Utf8Json -Path $receiptPath -Payload $launchedReceipt

    try {
        $result = & $runtimeEntrypoint @invokeArgs
        if ($null -eq $result) {
            throw 'runtime entrypoint returned no payload'
        }

        if ($result.PSObject.Properties.Name -contains 'run_id' -and -not [string]::IsNullOrWhiteSpace([string]$result.run_id)) {
            $resolvedRunId = [string]$result.run_id
        }
        if ($result.PSObject.Properties.Name -contains 'session_root' -and -not [string]::IsNullOrWhiteSpace([string]$result.session_root)) {
            $sessionRoot = [System.IO.Path]::GetFullPath([string]$result.session_root)
        } else {
            $sessionRoot = Resolve-CanonicalSessionRoot -ArtifactRoot $resolvedArtifactRoot -RunId $resolvedRunId
        }
        if ($result.PSObject.Properties.Name -contains 'summary_path' -and -not [string]::IsNullOrWhiteSpace([string]$result.summary_path)) {
            $summaryPath = [System.IO.Path]::GetFullPath([string]$result.summary_path)
        } else {
            $summaryPath = Join-Path $sessionRoot 'runtime-summary.json'
        }
        $receiptPath = Join-Path $sessionRoot 'host-launch-receipt.json'

        Assert-CanonicalTruthArtifacts -SessionRoot $sessionRoot

        $verifiedReceipt = New-HostLaunchReceiptPayload `
            -HostId $HostId `
            -LauncherPath $launcherPath `
            -RequestedStageStop $RequestedStageStop `
            -RequestedGradeFloor $RequestedGradeFloor `
            -RuntimeEntrypoint $runtimeEntrypoint `
            -RunId $resolvedRunId `
            -LaunchStatus 'verified'
        Write-Utf8Json -Path $receiptPath -Payload $verifiedReceipt
    } catch {
        $failedReceipt = New-HostLaunchReceiptPayload `
            -HostId $HostId `
            -LauncherPath $launcherPath `
            -RequestedStageStop $RequestedStageStop `
            -RequestedGradeFloor $RequestedGradeFloor `
            -RuntimeEntrypoint $runtimeEntrypoint `
            -RunId $resolvedRunId `
            -LaunchStatus 'failed'
        Write-Utf8Json -Path $receiptPath -Payload $failedReceipt
        throw
    }

    $payload = [pscustomobject]@{
        host_id = $HostId
        entry_id = 'vibe'
        entry_intent_id = $EntryId
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { $RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { $RequestedGradeFloor }
        launcher_path = $launcherPath
        runtime_entrypoint = $runtimeEntrypoint
        run_id = $resolvedRunId
        session_root = $sessionRoot
        summary_path = $summaryPath
        host_launch_receipt_path = $receiptPath
        launch_mode = 'canonical-entry'
        summary = $result.summary
    }
    if (-not [string]::IsNullOrWhiteSpace($BridgeOutputJsonPath)) {
        Write-Utf8Json -Path $BridgeOutputJsonPath -Payload $payload -Depth 20
    } else {
        $payload | ConvertTo-Json -Depth 20
    }
} finally {
    if ([string]::IsNullOrWhiteSpace($previousHostId)) {
        Remove-Item Env:VCO_HOST_ID -ErrorAction SilentlyContinue
    } else {
        $env:VCO_HOST_ID = $previousHostId
    }
}
