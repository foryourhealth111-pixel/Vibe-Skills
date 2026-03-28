[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$ReportPath,
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

$runnerPath = Join-Path $RepoRoot 'scripts\verify\runtime_neutral\release_truth_gate.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "release truth runner missing: $runnerPath"
}

$pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw 'Python is required to run vibe-release-truth-gate.'
}

$args = @(
    $runnerPath
    '--repo-root', $RepoRoot
    '--write-artifacts'
)
foreach ($path in $ReportPath) {
    $args += @('--report', (Resolve-Path $path).Path)
}
if ($OutputDirectory) {
    $args += @('--output-directory', $OutputDirectory)
}

& $pythonCommand.Source @args
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "vibe-release-truth-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-release-truth-gate passed' -ForegroundColor Green
