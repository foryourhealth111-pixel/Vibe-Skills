param()

$ErrorActionPreference = 'Stop'

function Read-JsonFile {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Find-MarkdownTableRow {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$RowStartsWith
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    foreach ($line in $lines) {
        $trimmed = [string]$line
        if ($trimmed.TrimStart().StartsWith($RowStartsWith)) {
            return $trimmed
        }
    }

    return $null
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

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$docsPath = Join-Path $repoRoot 'docs/universalization/host-capability-matrix.md'
$registryPath = Join-Path $repoRoot 'config\adapter-registry.json'

$allowedStatuses = @('supported-with-constraints', 'preview', 'not-yet-proven', 'advisory-only')
$allowedRuntimeRoles = @('official-runtime-adapter', 'host-adapter-supported', 'host-adapter-preview', 'contract-consumer')

$failures = @()

if (-not (Test-Path -LiteralPath $docsPath)) {
    $failures += 'missing docs/universalization/host-capability-matrix.md'
}

$registry = $null
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
        $adapterId = [string]$adapter.id
        $contractPaths = @(
            [string]$adapter.host_profile,
            [string]$adapter.settings_map,
            [string]$adapter.closure,
            [string]$adapter.manifest
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        foreach ($relativePath in $contractPaths) {
            $fullPath = Join-Path $repoRoot $relativePath
            if (-not (Test-Path -LiteralPath $fullPath)) {
                $failures += "missing adapter contract file: $relativePath"
            }
        }

        $profilePath = Join-Path $repoRoot ([string]$adapter.host_profile)
        if (-not (Test-Path -LiteralPath $profilePath)) {
            continue
        }

        $profile = $null
        try {
            $profile = Read-JsonFile -Path $profilePath
        } catch {
            $failures += "invalid host profile json for $adapterId -> $($_.Exception.Message)"
            continue
        }

        if ([string]$profile.adapter_id -ne $adapterId) {
            $failures += "adapter_id mismatch for $adapterId host profile"
        }
        if ([string]$profile.status -ne [string]$adapter.status) {
            $failures += "status mismatch between registry and host profile for $adapterId"
        }
        if ($allowedStatuses -notcontains [string]$profile.status) {
            $failures += "unexpected status for ${adapterId}: $($profile.status)"
        }
        if ($allowedRuntimeRoles -notcontains [string]$profile.runtime_role) {
            $failures += "unexpected runtime_role for ${adapterId}: $($profile.runtime_role)"
        }
        if ([string]::IsNullOrWhiteSpace([string]$profile.host_name)) {
            $failures += "host_name missing for $adapterId"
        }
        if (@($profile.source_evidence).Count -lt 1) {
            $failures += "source_evidence missing for $adapterId"
        }

        foreach ($platformContract in @($profile.supported_platform_contracts)) {
            if ([string]::IsNullOrWhiteSpace([string]$platformContract)) {
                continue
            }

            $platformPath = Join-Path $repoRoot ([string]$platformContract)
            if (-not (Test-Path -LiteralPath $platformPath)) {
                $failures += "missing platform contract for ${adapterId}: $platformContract"
            }
        }

        if ((Test-Path -LiteralPath $docsPath) -and -not [string]::IsNullOrWhiteSpace([string]$profile.host_name)) {
            $row = Find-MarkdownTableRow -Path $docsPath -RowStartsWith ("| {0} |" -f [string]$profile.host_name)
            if ($null -eq $row) {
                $failures += "missing host capability matrix row for $($profile.host_name)"
                continue
            }

            $cells = Split-MarkdownTableCells -Line $row
            if ($cells.Count -lt 3) {
                $failures += "host capability matrix row malformed for $($profile.host_name)"
                continue
            }

            $statusCell = ([string]$cells[1]) -replace '`', ''
            $runtimeRoleCell = ([string]$cells[2]) -replace '`', ''
            if ($statusCell -ne [string]$profile.status) {
                $failures += "host capability matrix status mismatch for $($profile.host_name)"
            }
            if ($runtimeRoleCell -ne [string]$profile.runtime_role) {
                $failures += "host capability matrix runtime_role mismatch for $($profile.host_name)"
            }
        }
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[PASS] host adapter contract gate'
