param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [ValidateSet("codex", "claude-code", "cursor", "windsurf", "openclaw", "opencode")]
  [string]$HostId = "codex",
  [string]$TargetRoot = '',
  [switch]$InstallExternal,
  [switch]$StrictOffline,
  [switch]$RequireClosedReady,
  [switch]$AllowExternalSkillFallback,
  [switch]$SkipRuntimeFreshnessGate
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliMain = Join-Path $RepoRoot 'apps\vgo-cli\src\vgo_cli\main.py'
$legacyScript = Join-Path $RepoRoot 'scripts\install\Install-VgoAdapter.ps1'

# Invoke-InstalledRuntimeFreshnessGate semantics are delegated to vgo_cli.main.

function Get-PreferredPythonInvocation {
  $helperPath = Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1'
  if (Test-Path -LiteralPath $helperPath) {
    . $helperPath
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
$cliLaunchWarning = $null
if (Test-Path -LiteralPath $cliMain) {
  try {
    $pythonInvocation = Get-PreferredPythonInvocation
  } catch {
    $cliLaunchWarning = $_.Exception.Message
  }
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
    'install',
    '--repo-root', $RepoRoot,
    '--frontend', 'powershell',
    '--profile', $Profile,
    '--host', $HostId
  )
  if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) { $argsList += @('--target-root', $TargetRoot) }
  if ($InstallExternal) { $argsList += '--install-external' }
  if ($StrictOffline) { $argsList += '--strict-offline' }
  if ($RequireClosedReady) { $argsList += '--require-closed-ready' }
  if ($AllowExternalSkillFallback) { $argsList += '--allow-external-skill-fallback' }
  if ($SkipRuntimeFreshnessGate) { $argsList += '--skip-runtime-freshness-gate' }

  & $pythonInvocation.host_path @argsList
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  exit 0
}

if (-not [string]::IsNullOrWhiteSpace($cliLaunchWarning)) {
  Write-Warning "Unable to launch vgo-cli via Python host; falling back to legacy PowerShell installer dispatch. $cliLaunchWarning"
} else {
  Write-Warning "Missing vgo-cli entrypoint at $cliMain; falling back to legacy PowerShell installer dispatch."
}
if ($InstallExternal) { Write-Warning 'Legacy PowerShell fallback ignores -InstallExternal because vgo-cli is unavailable.' }
if ($StrictOffline) { Write-Warning 'Legacy PowerShell fallback ignores -StrictOffline because vgo-cli is unavailable.' }
if ($SkipRuntimeFreshnessGate) { Write-Warning 'Legacy PowerShell fallback ignores -SkipRuntimeFreshnessGate because vgo-cli is unavailable.' }
$legacyHost = (Get-Process -Id $PID).Path
$legacyHostLeaf = [System.IO.Path]::GetFileName($legacyHost).ToLowerInvariant()
$legacyArgs = @('-NoProfile')
if ($legacyHostLeaf.StartsWith('powershell')) {
  $legacyArgs += @('-ExecutionPolicy', 'Bypass')
}
$legacyArgs += @('-File', $legacyScript, '-RepoRoot', $RepoRoot, '-HostId', $HostId, '-Profile', $Profile)
if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) { $legacyArgs += @('-TargetRoot', $TargetRoot) }
if ($RequireClosedReady) { $legacyArgs += '-RequireClosedReady' }
if ($AllowExternalSkillFallback) { $legacyArgs += '-AllowExternalSkillFallback' }
& $legacyHost @legacyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output ""
Write-Output "Installation complete."
