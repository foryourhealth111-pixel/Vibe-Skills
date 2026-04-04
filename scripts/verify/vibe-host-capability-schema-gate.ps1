param()

$ErrorActionPreference = 'Stop'

function Read-JsonFile {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Split-MarkdownTableCells {
    param([Parameter(Mandatory)] [string]$Line)

    $cells = @()
    foreach ($part in ($Line -split '\|')) {
        $trimmed = $part.Trim()
        if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
            $cells += $trimmed
        }
    }
    return $cells
}

function Get-HostCapabilityMatrixRows {
    param([Parameter(Mandatory)] [string]$Path)

    $rows = @()
    if (-not (Test-Path -LiteralPath $Path)) {
        return $rows
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    $inHostMatrix = $false
    foreach ($line in $lines) {
        $trimmed = [string]$line
        if ($trimmed -eq '## Host Matrix') {
            $inHostMatrix = $true
            continue
        }

        if (-not $inHostMatrix) {
            continue
        }

        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            if ($rows.Count -gt 0) {
                break
            }
            continue
        }

        if (-not $trimmed.TrimStart().StartsWith('|')) {
            if ($rows.Count -gt 0) {
                break
            }
            continue
        }

        if ((($trimmed -replace '[\|\-\s]', '') -eq '')) {
            continue
        }

        $cells = Split-MarkdownTableCells -Line $trimmed
        if ($cells.Count -eq 0 -or [string]$cells[0] -eq 'Host') {
            continue
        }

        $rows += [PSCustomObject]@{
            host_name = [string]$cells[0]
            status = if ($cells.Count -ge 2) { ([string]$cells[1]) -replace '`', '' } else { '' }
            runtime_role = if ($cells.Count -ge 3) { ([string]$cells[2]) -replace '`', '' } else { '' }
            raw = $trimmed
        }
    }

    return $rows
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$adapterRoot = Join-Path $repoRoot 'adapters'
$docsPath = Join-Path $repoRoot 'docs\universalization\host-capability-matrix.md'
$registryPath = Join-Path $repoRoot 'config\adapter-registry.json'
$requiredKeys = @(
    'adapter_id',
    'host_name',
    'status',
    'runtime_role',
    'settings_surface',
    'host_managed_surfaces',
    'capabilities',
    'degrade_contract',
    'source_evidence',
    'supported_platform_contracts'
)
$allowedStatuses = @('supported-with-constraints', 'preview', 'not-yet-proven', 'advisory-only')
$allowedRuntimeRoles = @('official-runtime-adapter', 'host-adapter-supported', 'host-adapter-preview', 'contract-consumer')

$failures = @()
$registry = $null
$registryProfiles = @{}
$discoveredProfiles = @{}
$discoveredHostNames = @{}
$matrixRowsByHost = @{}

if (-not (Test-Path -LiteralPath $docsPath)) {
    $failures += 'missing docs/universalization/host-capability-matrix.md'
} else {
    foreach ($row in @(Get-HostCapabilityMatrixRows -Path $docsPath)) {
        $hostName = [string]$row.host_name
        if (-not $matrixRowsByHost.Contains($hostName)) {
            $matrixRowsByHost[$hostName] = @()
        }
        $matrixRowsByHost[$hostName] += ,$row
    }

    foreach ($hostName in $matrixRowsByHost.Keys) {
        if (@($matrixRowsByHost[$hostName]).Count -gt 1) {
            $failures += "duplicate host capability matrix rows for $hostName"
        }
    }
}

if (-not (Test-Path -LiteralPath $registryPath)) {
    $failures += 'missing config/adapter-registry.json'
} else {
    try {
        $registry = Read-JsonFile -Path $registryPath
    } catch {
        $failures += "invalid config/adapter-registry.json -> $($_.Exception.Message)"
    }
}

if ($null -ne $registry) {
    foreach ($adapter in @($registry.adapters)) {
        $registryProfiles[[string]$adapter.host_profile] = $adapter
    }
}

$profileFiles = @(Get-ChildItem -Path $adapterRoot -Recurse -Filter 'host-profile.json' | Sort-Object FullName)
if ($profileFiles.Count -eq 0) {
    $failures += 'no host-profile.json files found under adapters/'
}

foreach ($file in $profileFiles) {
    $fullPath = [string]$file.FullName
    $relativePath = [string]([System.IO.Path]::GetRelativePath($repoRoot, $fullPath)).Replace('\', '/')
    $discoveredProfiles[$relativePath] = $true

    $json = $null
    try {
        $json = Read-JsonFile -Path $fullPath
    } catch {
        $failures += "invalid json: $relativePath -> $($_.Exception.Message)"
        continue
    }

    foreach ($key in $requiredKeys) {
        if ($json.PSObject.Properties.Name -notcontains $key) {
            $failures += "missing key '$key' in $relativePath"
        }
    }

    if ($allowedStatuses -notcontains [string]$json.status) {
        $failures += "unexpected status in ${relativePath}: $($json.status)"
    }
    if ($allowedRuntimeRoles -notcontains [string]$json.runtime_role) {
        $failures += "unexpected runtime_role in ${relativePath}: $($json.runtime_role)"
    }
    if (@($json.source_evidence).Count -lt 1) {
        $failures += "source_evidence must be non-empty in $relativePath"
    }

    $hostName = [string]$json.host_name
    if ([string]::IsNullOrWhiteSpace($hostName)) {
        $failures += "host_name must be non-empty in $relativePath"
    } elseif ($discoveredHostNames.Contains($hostName)) {
        $failures += "duplicate host_name across profiles: $hostName"
    } else {
        $discoveredHostNames[$hostName] = $relativePath
    }

    foreach ($platformContract in @($json.supported_platform_contracts)) {
        if ([string]::IsNullOrWhiteSpace([string]$platformContract)) {
            continue
        }
        $platformPath = Join-Path $repoRoot ([string]$platformContract)
        if (-not (Test-Path -LiteralPath $platformPath)) {
            $failures += "missing platform contract '$platformContract' referenced by ${relativePath}"
        }
    }

    if ($registryProfiles.Contains($relativePath)) {
        $adapter = $registryProfiles[$relativePath]
        if ([string]$json.adapter_id -ne [string]$adapter.id) {
            $failures += "adapter_id mismatch between registry and $relativePath"
        }
        if ([string]$json.status -ne [string]$adapter.status) {
            $failures += "status mismatch between registry and $relativePath"
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($hostName)) {
        if (-not $matrixRowsByHost.Contains($hostName)) {
            $failures += "host capability matrix row missing for $hostName"
        } else {
            $rows = @($matrixRowsByHost[$hostName])
            if ($rows.Count -ne 1) {
                $failures += "host capability matrix must contain exactly one row for $hostName"
            } else {
                $row = $rows[0]
                if ([string]$row.status -ne [string]$json.status) {
                    $failures += "host capability matrix status mismatch for $hostName"
                }
                if ([string]$row.runtime_role -ne [string]$json.runtime_role) {
                    $failures += "host capability matrix runtime_role mismatch for $hostName"
                }
            }
        }
    }
}

foreach ($relativePath in $registryProfiles.Keys) {
    if (-not $discoveredProfiles.Contains($relativePath)) {
        $failures += "registry host_profile missing on disk: $relativePath"
    }
}

foreach ($hostName in $matrixRowsByHost.Keys) {
    if (-not $discoveredHostNames.Contains($hostName)) {
        $failures += "host capability matrix row has no discovered host profile: $hostName"
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[PASS] host capability schema gate'
