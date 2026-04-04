param()

$ErrorActionPreference = 'Stop'

function Read-JsonFile {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$registryPath = Join-Path $repoRoot 'config\adapter-registry.json'
$failures = @()
$platformContractsByName = @{}

if (-not (Test-Path -LiteralPath $registryPath)) {
    $failures += 'missing config/adapter-registry.json'
}

$registry = $null
if ($failures.Count -eq 0) {
    try {
        $registry = Read-JsonFile -Path $registryPath
    } catch {
        $failures += "invalid config/adapter-registry.json -> $($_.Exception.Message)"
    }
}

$codexAdapter = $null
$codexProfile = $null
if ($null -ne $registry) {
    $codexAdapter = @($registry.adapters | Where-Object { [string]$_.id -eq 'codex' }) | Select-Object -First 1
    if ($null -eq $codexAdapter) {
        $failures += 'adapter-registry.json missing codex adapter entry'
    }
}

if ($null -ne $codexAdapter) {
    $hostProfilePath = Join-Path $repoRoot ([string]$codexAdapter.host_profile)
    if (-not (Test-Path -LiteralPath $hostProfilePath)) {
        $failures += "missing codex host profile: $($codexAdapter.host_profile)"
    } else {
        try {
            $codexProfile = Read-JsonFile -Path $hostProfilePath
        } catch {
            $failures += "invalid codex host profile -> $($_.Exception.Message)"
        }
    }
}

if ($null -ne $codexProfile) {
    foreach ($contractRel in @($codexProfile.supported_platform_contracts)) {
        $contractPath = Join-Path $repoRoot ([string]$contractRel)
        if (-not (Test-Path -LiteralPath $contractPath)) {
            $failures += "missing codex platform contract: $contractRel"
            continue
        }

        $name = [System.IO.Path]::GetFileNameWithoutExtension([string]$contractRel)
        if ($name -like 'platform-*') {
            $platformName = $name.Substring('platform-'.Length)
            $platformContractsByName[$platformName] = $contractPath
        }
    }
}

foreach ($required in @('windows', 'linux', 'macos')) {
    if (-not $platformContractsByName.Contains($required)) {
        $failures += "codex supported_platform_contracts missing platform-$required.json"
    }
}

if ($failures.Count -eq 0) {
    $win = Read-JsonFile -Path $platformContractsByName['windows']
    $linux = Read-JsonFile -Path $platformContractsByName['linux']
    $mac = Read-JsonFile -Path $platformContractsByName['macos']

    if ($win.status -ne 'full-authoritative') {
        $failures += 'codex windows must remain full-authoritative'
    }
    if ($linux.status -notin @('full-authoritative', 'supported-with-constraints', 'degraded-but-supported')) {
        $failures += 'codex linux must remain inside the governed platform status vocabulary'
    }
    if ($mac.status -eq 'full-authoritative') {
        $failures += 'codex macos cannot be marked full-authoritative before proof'
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[PASS] platform doctor parity gate'
