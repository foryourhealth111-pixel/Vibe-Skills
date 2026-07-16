Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-VibeMemoryBackendAdaptersConfig {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    if ($null -eq $Runtime -or $null -eq $Runtime.PSObject -or -not ($Runtime.PSObject.Properties.Name -contains 'memory_backend_adapters')) {
        return $null
    }

    return $Runtime.memory_backend_adapters
}

function Get-VibeMemoryBackendDriverConfig {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    $memoryBackendAdapters = Get-VibeMemoryBackendAdaptersConfig -Runtime $Runtime
    if ($null -eq $memoryBackendAdapters -or $null -eq $memoryBackendAdapters.PSObject -or -not ($memoryBackendAdapters.PSObject.Properties.Name -contains 'driver')) {
        return $null
    }

    return $memoryBackendAdapters.driver
}

function Test-VibeMemoryTruthyEnvironmentValue {
    param(
        [AllowEmptyString()] [string]$Value = ''
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    return $Value.Trim().ToLowerInvariant() -in @('1', 'true', 'yes', 'on')
}

function Get-VibeMemoryWorkspaceRoot {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    if (
        $Runtime.PSObject.Properties.Name -contains 'workspace_root' -and
        -not [string]::IsNullOrWhiteSpace([string]$Runtime.workspace_root)
    ) {
        return [System.IO.Path]::GetFullPath([string]$Runtime.workspace_root)
    }
    return [System.IO.Path]::GetFullPath([string]$Runtime.repo_root)
}

function Resolve-VibeMemoryBackendRoot {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    $memoryBackendAdapters = Get-VibeMemoryBackendAdaptersConfig -Runtime $Runtime
    $rootEnvName = if (
        $null -ne $memoryBackendAdapters -and
        $null -ne $memoryBackendAdapters.PSObject -and
        $memoryBackendAdapters.PSObject.Properties.Name -contains 'backend_root_env' -and
        -not [string]::IsNullOrWhiteSpace([string]$memoryBackendAdapters.backend_root_env)
    ) {
        [string]$memoryBackendAdapters.backend_root_env
    } else {
        'VIBE_MEMORY_BACKEND_ROOT'
    }
    $rootOverride = [Environment]::GetEnvironmentVariable($rootEnvName)
    if (-not [string]::IsNullOrWhiteSpace($rootOverride)) {
        return [System.IO.Path]::GetFullPath($rootOverride)
    }

    return Get-VibeMemoryWorkspaceRoot -Runtime $Runtime
}

function Get-VibeMemoryLaneConfig {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$LaneId
    )

    $memoryBackendAdapters = Get-VibeMemoryBackendAdaptersConfig -Runtime $Runtime
    $lanes = if (
        $null -ne $memoryBackendAdapters -and
        $null -ne $memoryBackendAdapters.PSObject -and
        $memoryBackendAdapters.PSObject.Properties.Name -contains 'lanes'
    ) {
        $memoryBackendAdapters.lanes
    } else {
        $null
    }
    if ($null -eq $lanes -or -not ($lanes.PSObject.Properties.Name -contains $LaneId)) {
        throw "Missing memory backend lane config for: $LaneId"
    }

    return $lanes.$LaneId
}

function Resolve-VibeMemoryProjectKey {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$LaneId
    )

    $lane = Get-VibeMemoryLaneConfig -Runtime $Runtime -LaneId $LaneId
    foreach ($envName in @($lane.project_key_env)) {
        $value = [Environment]::GetEnvironmentVariable([string]$envName)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return [pscustomobject]@{
                project_key = [string]$value
                source = [string]$envName
            }
        }
    }

    if ([string]$lane.project_key_fallback -eq 'repo_slug') {
        $repoDir = Split-Path -Leaf (Get-VibeMemoryWorkspaceRoot -Runtime $Runtime)
        return [pscustomobject]@{
            project_key = $repoDir
            source = 'repo_slug'
        }
    }

    return [pscustomobject]@{
        project_key = $null
        source = $null
    }
}

function Resolve-VibeMemoryBackendCommand {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    $driver = Get-VibeMemoryBackendDriverConfig -Runtime $Runtime
    $command = if (
        $null -ne $driver -and
        $null -ne $driver.PSObject -and
        $driver.PSObject.Properties.Name -contains 'command' -and
        -not [string]::IsNullOrWhiteSpace([string]$driver.command)
    ) {
        [string]$driver.command
    } else {
        '${VGO_PYTHON}'
    }
    return Resolve-VgoPythonCommandSpec -Command $command
}

function Resolve-VibeMemoryBackendLane {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$LaneId
    )

    $lane = Get-VibeMemoryLaneConfig -Runtime $Runtime -LaneId $LaneId
    $disableEnvName = if ($lane.PSObject.Properties.Name -contains 'disable_env') { [string]$lane.disable_env } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($disableEnvName) -and (Test-VibeMemoryTruthyEnvironmentValue -Value ([Environment]::GetEnvironmentVariable($disableEnvName)))) {
        return [pscustomobject]@{
            enabled = $false
            reason = "memory_backend_disabled:$LaneId"
            lane = $lane
            command_spec = $null
            store_path = $null
            project_key = $null
            project_key_source = $null
        }
    }

    $projectKeyResolution = Resolve-VibeMemoryProjectKey -Runtime $Runtime -LaneId $LaneId
    $commandSpec = Resolve-VibeMemoryBackendCommand -Runtime $Runtime
    $backendRoot = Resolve-VibeMemoryBackendRoot -Runtime $Runtime
    $storePath = [System.IO.Path]::GetFullPath((Join-Path $backendRoot ([string]$lane.store_relpath)))

    return [pscustomobject]@{
        enabled = [bool]$lane.default_enabled
        reason = 'memory_backend_ready'
        lane = $lane
        command_spec = $commandSpec
        store_path = $storePath
        project_key = if ($projectKeyResolution.project_key) { [string]$projectKeyResolution.project_key } else { $null }
        project_key_source = if ($projectKeyResolution.source) { [string]$projectKeyResolution.source } else { $null }
    }
}

function Invoke-VibeMemoryBackendAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$LaneId,
        [Parameter(Mandatory)] [string]$Action,
        [Parameter(Mandatory)] [object]$Payload,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $laneResolution = Resolve-VibeMemoryBackendLane -Runtime $Runtime -LaneId $LaneId
    if (-not $laneResolution.enabled) {
        return [pscustomobject]@{
            ok = $false
            status = [string]$laneResolution.reason
            items = @()
            item_count = 0
            capsule_count = 0
            capsules = @()
            suppressed_count = 0
            workspace_memory_plane = $null
            artifact_path = $null
            store_path = $null
            project_key = $null
            project_key_source = $null
            backend_lane = $LaneId
        }
    }

    $driver = Get-VibeMemoryBackendDriverConfig -Runtime $Runtime
    $driverScriptRelative = if (
        $null -ne $driver -and
        $null -ne $driver.PSObject -and
        $driver.PSObject.Properties.Name -contains 'script_path' -and
        -not [string]::IsNullOrWhiteSpace([string]$driver.script_path)
    ) {
        [string]$driver.script_path
    } else {
        'scripts/runtime/memory_backend_driver.py'
    }
    $driverScript = [System.IO.Path]::GetFullPath((Join-Path ([string]$Runtime.repo_root) $driverScriptRelative))
    if (-not (Test-Path -LiteralPath $driverScript)) {
        return [pscustomobject]@{
            ok = $false
            status = 'memory_backend_driver_missing'
            items = @()
            item_count = 0
            capsule_count = 0
            capsules = @()
            suppressed_count = 0
            workspace_memory_plane = $null
            artifact_path = $null
            store_path = [string]$laneResolution.store_path
            project_key = $laneResolution.project_key
            project_key_source = $laneResolution.project_key_source
            backend_lane = $LaneId
        }
    }

    $artifactsRoot = Join-Path $SessionRoot 'memory-backend'
    New-Item -ItemType Directory -Path $artifactsRoot -Force | Out-Null
    $payloadPath = Join-Path $artifactsRoot ("{0}-{1}-request.json" -f $LaneId, $Action)
    $responsePath = Join-Path $artifactsRoot ("{0}-{1}-response.json" -f $LaneId, $Action)
    Write-VibeJsonArtifact -Path $payloadPath -Value $Payload

    $commandSpec = $laneResolution.command_spec
    $args = @($commandSpec.prefix_arguments)
    $args += @(
        $driverScript,
        '--lane', $LaneId,
        '--action', $Action,
        '--repo-root', (Get-VibeMemoryWorkspaceRoot -Runtime $Runtime),
        '--session-root', $SessionRoot,
        '--store-path', ([string]$laneResolution.store_path),
        '--payload-path', $payloadPath,
        '--response-path', $responsePath
    )
    if (-not [string]::IsNullOrWhiteSpace([string]$laneResolution.project_key)) {
        $args += @('--project-key', [string]$laneResolution.project_key)
    }

    try {
        $global:LASTEXITCODE = 0
        $stdout = @(& $commandSpec.host_path @args 2>&1)
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($exitCode -ne 0) {
            return [pscustomobject]@{
                ok = $false
                status = 'memory_backend_invocation_failed'
                items = @()
                item_count = 0
                capsule_count = 0
                capsules = @()
                suppressed_count = 0
                workspace_memory_plane = $null
                artifact_path = $null
                store_path = [string]$laneResolution.store_path
                project_key = $laneResolution.project_key
                project_key_source = $laneResolution.project_key_source
                backend_lane = $LaneId
                command_output = @($stdout | ForEach-Object { [string]$_ })
            }
        }

        if (-not (Test-Path -LiteralPath $responsePath)) {
            return [pscustomobject]@{
                ok = $false
                status = 'memory_backend_missing_response'
                items = @()
                item_count = 0
                capsule_count = 0
                capsules = @()
                suppressed_count = 0
                workspace_memory_plane = $null
                artifact_path = $null
                store_path = [string]$laneResolution.store_path
                project_key = $laneResolution.project_key
                project_key_source = $laneResolution.project_key_source
                backend_lane = $LaneId
            }
        }

        $response = Get-Content -LiteralPath $responsePath -Raw -Encoding UTF8 | ConvertFrom-Json
        return [pscustomobject]@{
            ok = [bool]($response.ok)
            status = [string]$response.status
            items = @($response.items)
            item_count = [int]$response.item_count
            capsule_count = if ($response.PSObject.Properties.Name -contains 'capsule_count') { [int]$response.capsule_count } else { 0 }
            capsules = if ($response.PSObject.Properties.Name -contains 'capsules') { @($response.capsules) } else { @() }
            suppressed_count = if ($response.PSObject.Properties.Name -contains 'suppressed_count') { [int]$response.suppressed_count } else { 0 }
            workspace_memory_plane = if ($response.PSObject.Properties.Name -contains 'workspace_memory_plane') { $response.workspace_memory_plane } else { $null }
            artifact_path = $responsePath
            store_path = [string]$response.store_path
            project_key = if ($response.project_key) { [string]$response.project_key } else { $laneResolution.project_key }
            project_key_source = if ($response.project_key_source) { [string]$response.project_key_source } else { $laneResolution.project_key_source }
            backend_lane = $LaneId
        }
    } catch {
        return [pscustomobject]@{
            ok = $false
            status = 'memory_backend_exception'
            items = @()
            item_count = 0
            capsule_count = 0
            capsules = @()
            suppressed_count = 0
            workspace_memory_plane = $null
            artifact_path = $null
            store_path = [string]$laneResolution.store_path
            project_key = $laneResolution.project_key
            project_key_source = $laneResolution.project_key_source
            backend_lane = $LaneId
            error = $_.Exception.Message
        }
    }
}
