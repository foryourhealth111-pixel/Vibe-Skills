Set-StrictMode -Version Latest

. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'vibe-governance-helpers.ps1')

function Resolve-VgoAdapterRegistryPath {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $resolvedRoot = Resolve-VgoRepoRoot -StartPath $RepoRoot
    $configPath = Join-Path $resolvedRoot 'config\adapter-registry.json'
    if (Test-Path -LiteralPath $configPath) {
        return [pscustomobject]@{
            root = [System.IO.Path]::GetFullPath($resolvedRoot)
            registry_path = [System.IO.Path]::GetFullPath($configPath)
        }
    }

    $legacyPath = Join-Path $resolvedRoot 'adapters\index.json'
    if (Test-Path -LiteralPath $legacyPath) {
        return [pscustomobject]@{
            root = [System.IO.Path]::GetFullPath($resolvedRoot)
            registry_path = [System.IO.Path]::GetFullPath($legacyPath)
        }
    }

    throw "VGO adapter registry not found under repo root or ancestors: $RepoRoot"
}

function Resolve-VgoAdapterRegistry {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $resolution = Resolve-VgoAdapterRegistryPath -RepoRoot $RepoRoot
    return [pscustomobject]@{
        root = [string]$resolution.root
        registry = Get-VgoAdapterRegistryPayload -StartPath $resolution.root
        registry_path = [string]$resolution.registry_path
        source = 'vibe-governance-helpers'
    }
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
        foreach ($alias in $Registry.aliases.PSObject.Properties) {
            if ($alias.Name.Trim().ToLowerInvariant() -eq $normalized) {
                return [string]$alias.Value
            }
        }
    }

    return $normalized
}

function Read-VgoOptionalJson {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$RelativePath
    )

    if ([string]::IsNullOrWhiteSpace($RelativePath)) {
        return $null
    }

    $resolvedPath = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $resolvedPath)) {
        return $null
    }

    return Get-Content -LiteralPath $resolvedPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-VgoAdapterDescriptor {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$HostId = ''
    )

    $registryResolution = Resolve-VgoAdapterRegistry -RepoRoot $RepoRoot
    $registryRoot = [string]$registryResolution.root
    $entry = Resolve-VgoAdapterEntry -StartPath $registryRoot -HostId $HostId

    $hostProfilePath = if ([string]::IsNullOrWhiteSpace([string]$entry.host_profile)) { $null } else { Join-Path $registryRoot ([string]$entry.host_profile) }
    $settingsMapPath = if ([string]::IsNullOrWhiteSpace([string]$entry.settings_map)) { $null } else { Join-Path $registryRoot ([string]$entry.settings_map) }
    $closurePath = if ([string]::IsNullOrWhiteSpace([string]$entry.closure)) { $null } else { Join-Path $registryRoot ([string]$entry.closure) }
    $manifestPath = if ([string]::IsNullOrWhiteSpace([string]$entry.manifest)) { $null } else { Join-Path $registryRoot ([string]$entry.manifest) }

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
        host_profile = Read-VgoOptionalJson -RepoRoot $registryRoot -RelativePath ([string]$entry.host_profile)
        settings_map = Read-VgoOptionalJson -RepoRoot $registryRoot -RelativePath ([string]$entry.settings_map)
        closure = Read-VgoOptionalJson -RepoRoot $registryRoot -RelativePath ([string]$entry.closure)
    }
}
