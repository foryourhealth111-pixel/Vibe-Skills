Set-StrictMode -Version Latest

function Resolve-VgoAdapterRegistryPath {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $current = [System.IO.Path]::GetFullPath($RepoRoot)
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        $path = Join-Path $current 'adapters\index.json'
        if (Test-Path -LiteralPath $path) {
            return [System.IO.Path]::GetFullPath($path)
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    return $null
}

function Get-VgoEmbeddedAdapterRegistry {
    return [pscustomobject]@{
        schema_version = 1
        default_adapter_id = 'codex'
        aliases = [pscustomobject]@{
            claude = 'claude-code'
        }
        adapters = @(
            [pscustomobject]@{
                id = 'codex'
                status = 'supported-with-constraints'
                install_mode = 'governed'
                check_mode = 'governed'
                bootstrap_mode = 'governed'
                default_target_root = [pscustomobject]@{
                    env = 'CODEX_HOME'
                    rel = '.vibeskills/targets/codex'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/codex/host-profile.json'
                settings_map = 'adapters/codex/settings-map.json'
                closure = 'adapters/codex/closure.json'
                manifest = 'dist/host-codex/manifest.json'
            },
            [pscustomobject]@{
                id = 'claude-code'
                status = 'preview'
                install_mode = 'preview-guidance'
                check_mode = 'preview-guidance'
                bootstrap_mode = 'preview-guidance'
                default_target_root = [pscustomobject]@{
                    env = 'CLAUDE_HOME'
                    rel = '.vibeskills/targets/claude-code'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/claude-code/host-profile.json'
                settings_map = 'adapters/claude-code/settings-map.json'
                closure = 'adapters/claude-code/closure.json'
                manifest = 'dist/host-claude-code/manifest.json'
            },
            [pscustomobject]@{
                id = 'cursor'
                status = 'preview'
                install_mode = 'preview-guidance'
                check_mode = 'preview-guidance'
                bootstrap_mode = 'preview-guidance'
                default_target_root = [pscustomobject]@{
                    env = 'CURSOR_HOME'
                    rel = '.vibeskills/targets/cursor'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/cursor/host-profile.json'
                settings_map = 'adapters/cursor/settings-map.json'
                closure = 'adapters/cursor/closure.json'
                manifest = 'dist/host-cursor/manifest.json'
            },
            [pscustomobject]@{
                id = 'windsurf'
                status = 'preview'
                install_mode = 'runtime-core'
                check_mode = 'runtime-core'
                bootstrap_mode = 'runtime-core'
                default_target_root = [pscustomobject]@{
                    env = 'WINDSURF_HOME'
                    rel = '.vibeskills/targets/windsurf'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/windsurf/host-profile.json'
                settings_map = 'adapters/windsurf/settings-map.json'
                closure = 'adapters/windsurf/closure.json'
                manifest = 'dist/host-windsurf/manifest.json'
            },
            [pscustomobject]@{
                id = 'openclaw'
                status = 'preview'
                install_mode = 'runtime-core'
                check_mode = 'runtime-core'
                bootstrap_mode = 'runtime-core'
                default_target_root = [pscustomobject]@{
                    env = 'OPENCLAW_HOME'
                    rel = '.vibeskills/targets/openclaw'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/openclaw/host-profile.json'
                settings_map = 'adapters/openclaw/settings-map.json'
                closure = 'adapters/openclaw/closure.json'
                manifest = 'dist/host-openclaw/manifest.json'
            },
            [pscustomobject]@{
                id = 'opencode'
                status = 'preview'
                install_mode = 'preview-guidance'
                check_mode = 'preview-guidance'
                bootstrap_mode = 'preview-guidance'
                default_target_root = [pscustomobject]@{
                    env = 'OPENCODE_HOME'
                    rel = '.vibeskills/targets/opencode'
                    kind = 'isolated-home'
                }
                host_profile = 'adapters/opencode/host-profile.json'
                settings_map = 'adapters/opencode/settings-map.json'
                closure = 'adapters/opencode/closure.json'
                manifest = 'dist/host-opencode/manifest.json'
            }
        )
    }
}

function Resolve-VgoAdapterRegistry {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $registryPath = Resolve-VgoAdapterRegistryPath -RepoRoot $RepoRoot
    if (-not [string]::IsNullOrWhiteSpace($registryPath)) {
        try {
            return [pscustomobject]@{
                root = [System.IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent $registryPath)))
                registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
                registry_path = $registryPath
                source = 'filesystem'
            }
        } catch {
            throw ("Failed to parse adapters/index.json: " + $_.Exception.Message)
        }
    }

    $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
    if (Test-Path -LiteralPath $governancePath) {
        return [pscustomobject]@{
            root = [System.IO.Path]::GetFullPath($RepoRoot)
            registry = Get-VgoEmbeddedAdapterRegistry
            registry_path = $null
            source = 'embedded-fallback'
        }
    }

    throw "VGO adapter registry not found under repo root or ancestors: $RepoRoot"
}

function Resolve-VgoAdapterAlias {
    param(
        [AllowEmptyString()] [string]$HostId = '',
        [Parameter(Mandatory)] [psobject]$Registry
    )

    $resolved = $HostId
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        $resolved = if ($Registry.PSObject.Properties.Name -contains 'default_adapter_id') { [string]$Registry.default_adapter_id } else { 'codex' }
    }

    $normalized = $resolved.Trim().ToLowerInvariant()
    if ($Registry.PSObject.Properties.Name -contains 'aliases' -and $null -ne $Registry.aliases) {
        $aliases = $Registry.aliases.PSObject.Properties | ForEach-Object { @{ key = $_.Name.ToLowerInvariant(); value = [string]$_.Value } }
        foreach ($alias in $aliases) {
            if ($alias.key -eq $normalized) {
                return $alias.value
            }
        }
    }

    return $normalized
}

function Resolve-VgoAdapterDescriptor {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$HostId = ''
    )

    $registryResolution = Resolve-VgoAdapterRegistry -RepoRoot $RepoRoot
    $registryRoot = [string]$registryResolution.root
    $registry = $registryResolution.registry
    $adapterId = Resolve-VgoAdapterAlias -HostId $HostId -Registry $registry
    $entry = @($registry.adapters | Where-Object { [string]$_.id -eq $adapterId } | Select-Object -First 1)[0]
    if ($null -eq $entry) {
        throw "Unsupported VGO host id: $HostId"
    }

    $hostProfilePath = Join-Path $registryRoot ([string]$entry.host_profile)
    $settingsMapPath = if ($entry.PSObject.Properties.Name -contains 'settings_map' -and -not [string]::IsNullOrWhiteSpace([string]$entry.settings_map)) { Join-Path $registryRoot ([string]$entry.settings_map) } else { $null }
    $closurePath = if ($entry.PSObject.Properties.Name -contains 'closure' -and -not [string]::IsNullOrWhiteSpace([string]$entry.closure)) { Join-Path $registryRoot ([string]$entry.closure) } else { $null }
    $manifestPath = if ($entry.PSObject.Properties.Name -contains 'manifest' -and -not [string]::IsNullOrWhiteSpace([string]$entry.manifest)) { Join-Path $registryRoot ([string]$entry.manifest) } else { $null }

    $hostProfile = if ($hostProfilePath -and (Test-Path -LiteralPath $hostProfilePath)) { Get-Content -LiteralPath $hostProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
    $settingsMap = if ($settingsMapPath -and (Test-Path -LiteralPath $settingsMapPath)) { Get-Content -LiteralPath $settingsMapPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
    $closure = if ($closurePath -and (Test-Path -LiteralPath $closurePath)) { Get-Content -LiteralPath $closurePath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }

    return [pscustomobject]@{
        id = [string]$entry.id
        status = [string]$entry.status
        install_mode = [string]$entry.install_mode
        check_mode = [string]$entry.check_mode
        bootstrap_mode = [string]$entry.bootstrap_mode
        default_target_root = $entry.default_target_root
        host_profile_path = $hostProfilePath
        settings_map_path = $settingsMapPath
        closure_path = $closurePath
        manifest_path = $manifestPath
        host_profile = $hostProfile
        settings_map = $settingsMap
        closure = $closure
    }
}
