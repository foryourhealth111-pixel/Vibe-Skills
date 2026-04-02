param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts,
    [switch]$WriteReceipt
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $TargetRoot = Resolve-VgoTargetRoot
}

$runnerPath = Join-Path $PSScriptRoot 'runtime_neutral\freshness_gate.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "runtime-neutral freshness gate missing: $runnerPath"
}

$pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw 'Python is required to run vibe-installed-runtime-freshness-gate.'
}

$args = @(
    $runnerPath,
    '--target-root', $TargetRoot
)
if ($WriteArtifacts) {
    $args += '--write-artifacts'
}
if ($WriteReceipt) {
    $args += '--write-receipt'
}

& $pythonCommand.Source @args
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "vibe-installed-runtime-freshness-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-installed-runtime-freshness-gate passed' -ForegroundColor Green
