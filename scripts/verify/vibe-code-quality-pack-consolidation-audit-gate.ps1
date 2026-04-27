[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
} else {
    $RepoRoot = (Resolve-Path $RepoRoot).Path
}

$runnerPath = Join-Path $RepoRoot 'scripts/verify/runtime_neutral/code_quality_pack_consolidation_audit.py'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Code-quality pack consolidation audit runner missing: $runnerPath"
}

. (Join-Path $RepoRoot 'scripts/common/vibe-governance-helpers.ps1')
$pythonInvocation = Get-VgoPythonCommand

$runnerArgs = @(
    $runnerPath,
    '--repo-root', $RepoRoot
)
if ($WriteArtifacts) {
    $runnerArgs += '--write-artifacts'
}
if ($OutputDirectory) {
    $runnerArgs += @('--output-directory', $OutputDirectory)
}

& $pythonInvocation.host_path @($pythonInvocation.prefix_arguments) @runnerArgs
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "vibe-code-quality-pack-consolidation-audit-gate failed with exit code $exitCode"
}

Write-Host '[PASS] vibe-code-quality-pack-consolidation-audit-gate passed' -ForegroundColor Green
