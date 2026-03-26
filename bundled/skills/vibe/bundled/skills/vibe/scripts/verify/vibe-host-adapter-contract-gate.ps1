param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$adapterRoot = Join-Path $repoRoot 'adapters'
$docsPath = Join-Path $repoRoot 'docs/universalization/host-capability-matrix.md'

$failures = @()

if (-not (Test-Path -LiteralPath $docsPath)) {
    $failures += 'missing docs/universalization/host-capability-matrix.md'
}

$checks = @(
    @{ Path = 'codex/settings-map.json'; MustExist = $true },
    @{ Path = 'claude-code/settings-map.json'; MustExist = $true },
    @{ Path = 'windsurf/settings-map.json'; MustExist = $true },
    @{ Path = 'openclaw/settings-map.json'; MustExist = $true },
    @{ Path = 'opencode/settings-map.json'; MustExist = $true },
    @{ Path = 'generic/settings-map.json'; MustExist = $true },
    @{ Path = 'codex/platform-windows.json'; MustExist = $true },
    @{ Path = 'codex/platform-linux.json'; MustExist = $true },
    @{ Path = 'codex/platform-macos.json'; MustExist = $true },
    @{ Path = 'claude-code/platform-windows.json'; MustExist = $true },
    @{ Path = 'claude-code/platform-linux.json'; MustExist = $true },
    @{ Path = 'claude-code/platform-macos.json'; MustExist = $true },
    @{ Path = 'windsurf/platform-windows.json'; MustExist = $true },
    @{ Path = 'windsurf/platform-linux.json'; MustExist = $true },
    @{ Path = 'windsurf/platform-macos.json'; MustExist = $true },
    @{ Path = 'openclaw/platform-windows.json'; MustExist = $true },
    @{ Path = 'openclaw/platform-linux.json'; MustExist = $true },
    @{ Path = 'openclaw/platform-macos.json'; MustExist = $true }
)

foreach ($check in $checks) {
    $full = Join-Path $adapterRoot $check.Path
    if ($check.MustExist -and -not (Test-Path -LiteralPath $full)) {
        $failures += "missing adapter contract file: $($check.Path)"
    }
}

$codexProfilePath = Join-Path $adapterRoot 'codex/host-profile.json'
if (Test-Path -LiteralPath $codexProfilePath) {
    $codex = Get-Content -LiteralPath $codexProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($codex.status -notin @('supported-with-constraints', 'preview', 'not-yet-proven', 'advisory-only')) {
        $failures += "unexpected codex status: $($codex.status)"
    }
    if ($codex.runtime_role -ne 'official-runtime-adapter') {
        $failures += "codex runtime_role must remain official-runtime-adapter"
    }
}

$openCodeProfilePath = Join-Path $adapterRoot 'opencode/host-profile.json'
if (Test-Path -LiteralPath $openCodeProfilePath) {
    $opencode = Get-Content -LiteralPath $openCodeProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($opencode.status -ne 'not-yet-proven') {
        $failures += "opencode must remain not-yet-proven until a real adapter exists"
    }
}

$windsurfProfilePath = Join-Path $adapterRoot 'windsurf/host-profile.json'
if (Test-Path -LiteralPath $windsurfProfilePath) {
    $windsurf = Get-Content -LiteralPath $windsurfProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($windsurf.status -ne 'preview') {
        $failures += "windsurf must remain preview until broader proof exists"
    }
    if ($windsurf.runtime_role -ne 'official-runtime-adapter') {
        $failures += "windsurf runtime_role must remain official-runtime-adapter"
    }
}

$openClawProfilePath = Join-Path $adapterRoot 'openclaw/host-profile.json'
if (Test-Path -LiteralPath $openClawProfilePath) {
    $openclaw = Get-Content -LiteralPath $openClawProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($openclaw.status -ne 'preview') {
        $failures += "openclaw must remain preview until broader proof exists"
    }
    if ($openclaw.runtime_role -ne 'official-runtime-adapter') {
        $failures += "openclaw runtime_role must remain official-runtime-adapter"
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[PASS] host adapter contract gate'
