param(
  [Parameter(Mandatory = $true)]
  [string]$RepoRoot,
  [Parameter(Mandatory = $true)]
  [string]$TargetRoot,
  [Parameter(Mandatory = $true)]
  [string]$HostId,
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [switch]$Preview,
  [switch]$PurgeEmptyDirs,
  [switch]$StrictOwnedOnly
)
$ErrorActionPreference = "Stop"
. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')

$modulePath = Join-Path $RepoRoot 'packages\installer-core\src\vgo_installer\uninstall_runtime.py'
if (-not (Test-Path -LiteralPath $modulePath)) {
  throw "Missing required installer-core uninstaller module at $modulePath."
}

$pythonInvocation = Get-VgoPythonCommand
$pythonPathEntries = @(
  (Join-Path $RepoRoot 'packages\contracts\src'),
  (Join-Path $RepoRoot 'packages\installer-core\src')
)
if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
  $pythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = ($pythonPathEntries -join [System.IO.Path]::PathSeparator)

$argsList = @($pythonInvocation.prefix_arguments)
$argsList += @(
  '-m', 'vgo_installer.uninstall_runtime',
  '--repo-root', $RepoRoot,
  '--target-root', $TargetRoot,
  '--host', $HostId,
  '--profile', $Profile
)
if ($Preview) { $argsList += '--preview' }
if ($PurgeEmptyDirs) { $argsList += '--purge-empty-dirs' }
if ($StrictOwnedOnly) { $argsList += '--strict-owned-only' }

& $pythonInvocation.host_path @argsList
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
