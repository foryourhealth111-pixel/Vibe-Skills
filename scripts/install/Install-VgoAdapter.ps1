param(
    [Parameter(Mandatory)] [string]$RepoRoot,
    [Parameter(Mandatory)] [string]$TargetRoot,
    [Parameter(Mandatory)] [string]$HostId,
    [ValidateSet('minimal', 'full')] [string]$Profile = 'full',
    [switch]$RequireClosedReady,
    [switch]$AllowExternalSkillFallback
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-VgoPreferredPythonCommand {
    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command) {
            return [string]$command.Source
        }
    }
    return $null
}

$pythonInstallerCore = Join-Path $RepoRoot 'packages\installer-core\src\vgo_installer\install_runtime.py'
if (-not (Test-Path -LiteralPath $pythonInstallerCore -PathType Leaf)) {
    throw "installer-core is unavailable: $pythonInstallerCore"
}

$pythonCommand = Get-VgoPreferredPythonCommand
if ([string]::IsNullOrWhiteSpace($pythonCommand)) {
    throw 'Python 3 is required to run installer-core.'
}

$pythonPathEntries = @(
    (Join-Path $RepoRoot 'packages\contracts\src'),
    (Join-Path $RepoRoot 'packages\installer-core\src')
)
if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $pythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = ($pythonPathEntries -join [System.IO.Path]::PathSeparator)

$commandArgs = @(
    '-m', 'vgo_installer.install_runtime',
    '--repo-root', $RepoRoot,
    '--target-root', $TargetRoot,
    '--host', $HostId,
    '--profile', $Profile
)
if ([System.IO.Path]::GetFileNameWithoutExtension($pythonCommand).ToLowerInvariant() -eq 'py') {
    $commandArgs = @('-3') + $commandArgs
}
if ($RequireClosedReady) {
    $commandArgs += '--require-closed-ready'
}
if ($AllowExternalSkillFallback) {
    $commandArgs += '--allow-external-skill-fallback'
}

& $pythonCommand @commandArgs
if ($LASTEXITCODE -ne 0) {
    throw ("installer-core failed with exit code {0}." -f $LASTEXITCODE)
}
