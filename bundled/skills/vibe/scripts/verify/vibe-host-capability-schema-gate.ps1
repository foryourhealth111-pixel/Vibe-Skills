param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$adapterRoot = Join-Path $repoRoot 'adapters'
$requiredProfiles = @(
    'codex/host-profile.json',
    'claude-code/host-profile.json',
    'windsurf/host-profile.json',
    'openclaw/host-profile.json',
    'opencode/host-profile.json',
    'generic/host-profile.json'
)
$requiredKeys = @(
    'adapter_id',
    'host_name',
    'status',
    'runtime_role',
    'settings_surface',
    'host_managed_surfaces',
    'capabilities',
    'degrade_contract'
)

$failures = @()

foreach ($rel in $requiredProfiles) {
    $path = Join-Path $adapterRoot $rel
    if (-not (Test-Path -LiteralPath $path)) {
        $failures += "missing profile: $rel"
        continue
    }

    try {
        $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $failures += "invalid json: $rel -> $($_.Exception.Message)"
        continue
    }

    foreach ($key in $requiredKeys) {
        if ($json.PSObject.Properties.Name -notcontains $key) {
            $failures += "missing key '$key' in $rel"
        }
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[PASS] host capability schema gate'
