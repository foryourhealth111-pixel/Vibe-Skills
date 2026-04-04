param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
    [string]$HostId = "codex",
  [string]$TargetRoot = '',
  [switch]$Preview,
  [switch]$PurgeEmptyDirs,
  [switch]$StrictOwnedOnly
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$helperPath = Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1'
$cliMain = Join-Path $RepoRoot 'apps\vgo-cli\src\vgo_cli\main.py'

if (Test-Path -LiteralPath $helperPath) {
  . $helperPath
  $HostId = Resolve-VgoHostId -HostId $HostId
}

function Get-PreferredPythonInvocation {
  if (Get-Command Get-VgoPythonCommand -ErrorAction SilentlyContinue) {
    try {
      return Get-VgoPythonCommand
    } catch {
    }
  }

  $absoluteCandidates = @(
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    '/opt/local/bin/python3',
    'C:\Python311\python.exe',
    'C:\Python310\python.exe'
  )
  if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $absoluteCandidates += @(
      (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
      (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe')
    )
  }

  foreach ($candidatePath in $absoluteCandidates) {
    if (-not [string]::IsNullOrWhiteSpace($candidatePath) -and (Test-Path -LiteralPath $candidatePath)) {
      return [pscustomobject]@{ host_path = $candidatePath; prefix_arguments = @() }
    }
  }

  foreach ($candidate in @('python3', 'python', 'py')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return [pscustomobject]@{ host_path = $command.Source; prefix_arguments = @() }
    }
  }
  throw 'Python 3.10+ is required to launch vgo-cli.'
}

$pythonInvocation = $null
if (Test-Path -LiteralPath $cliMain) {
  $pythonInvocation = Get-PreferredPythonInvocation
}

if ($null -ne $pythonInvocation) {
  $pythonPathEntries = @((Join-Path $RepoRoot 'apps\vgo-cli\src'))
  if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $pythonPathEntries += $env:PYTHONPATH
  }
  $env:PYTHONPATH = ($pythonPathEntries -join [System.IO.Path]::PathSeparator)

  $argsList = @($pythonInvocation.prefix_arguments)
  $argsList += @(
    '-m', 'vgo_cli.main',
    'uninstall',
    '--repo-root', $RepoRoot,
    '--frontend', 'powershell',
    '--profile', $Profile,
    '--host', $HostId
  )
  if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) { $argsList += @('--target-root', $TargetRoot) }
  if ($Preview) { $argsList += '--preview' }
  if ($PurgeEmptyDirs) { $argsList += '--purge-empty-dirs' }
  if ($StrictOwnedOnly) { $argsList += '--strict-owned-only' }

  & $pythonInvocation.host_path @argsList
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  exit 0
}

throw "Missing required vgo-cli entrypoint at $cliMain. The PowerShell uninstall wrapper no longer falls back to legacy uninstall scripts."
