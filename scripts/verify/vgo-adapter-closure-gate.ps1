param(
    [string]$RepoRoot = '',
    [switch]$WriteArtifacts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

function Resolve-ClosureGateRegistry {
    param([Parameter(Mandatory)] [string]$RepoRoot)

    $current = [System.IO.Path]::GetFullPath($RepoRoot)
    $registryPath = $null
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        $adapterPath = Join-Path $current 'adapters\index.json'
        if (Test-Path -LiteralPath $adapterPath) {
            $registryPath = $adapterPath
            break
        }

        $configPath = Join-Path $current 'config\adapter-registry.json'
        if (Test-Path -LiteralPath $configPath) {
            $registryPath = $configPath
            break
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    if ([string]::IsNullOrWhiteSpace($registryPath)) {
        throw "VGO adapter registry not found under repo root or ancestors: $RepoRoot"
    }

    try {
        return Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw ("Failed to parse adapter registry: " + $_.Exception.Message)
    }
}

$registry = Resolve-ClosureGateRegistry -RepoRoot $RepoRoot
$failures = @()
$rows = @()

foreach ($entry in @($registry.adapters)) {
    $paths = @([string]$entry.host_profile, [string]$entry.settings_map, [string]$entry.closure, [string]$entry.manifest)
    foreach ($rel in $paths) {
        if ([string]::IsNullOrWhiteSpace($rel)) { continue }
        $full = Join-Path $RepoRoot $rel
        if (-not (Test-Path -LiteralPath $full)) {
            $failures += "missing artifact for adapter '$($entry.id)': $rel"
        }
    }
    $rows += [pscustomobject]@{
        adapter_id = [string]$entry.id
        status = [string]$entry.status
        install_mode = [string]$entry.install_mode
        check_mode = [string]$entry.check_mode
        bootstrap_mode = [string]$entry.bootstrap_mode
    }
}

$gateResult = if ($failures.Count -eq 0) { 'PASS' } else { 'FAIL' }
$gatePayload = [ordered]@{}
$gatePayload['gate'] = 'vgo-adapter-closure-gate'
$gatePayload['result'] = $gateResult
$gatePayload['adapter_count'] = @($registry.adapters).Count
$gatePayload['rows'] = @($rows)
$gatePayload['failures'] = @($failures)

if ($WriteArtifacts) {
    $outDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $outPath = Join-Path $outDir 'vgo-adapter-closure-gate.json'
    $gatePayload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outPath -Encoding UTF8
}

$gatePayload | ConvertTo-Json -Depth 10
if ($failures.Count -gt 0) { exit 1 }
