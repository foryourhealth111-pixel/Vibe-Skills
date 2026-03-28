[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ScenarioPath,
    [string]$RepoRoot,
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path $RepoRoot).Path
}

$runnerPath = Join-Path $RepoRoot 'scripts\verify\runtime_neutral\workflow_acceptance_runner.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "workflow acceptance runner missing: $runnerPath"
}

$resolvedScenario = (Resolve-Path $ScenarioPath).Path

$pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw 'Python is required to run vibe-workflow-acceptance-gate.'
}

$args = @(
    $runnerPath
    '--repo-root', $RepoRoot
    '--scenario', $resolvedScenario
    '--write-artifacts'
)
if ($OutputDirectory) {
    $args += @('--output-directory', $OutputDirectory)
}

& $pythonCommand.Source @args
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "vibe-workflow-acceptance-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-workflow-acceptance-gate passed' -ForegroundColor Green
