param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [ValidateSet("codex", "claude-code", "cursor", "windsurf", "openclaw")]
  [string]$HostId = "codex",
  [string]$TargetRoot = '',
  [switch]$InstallExternal,
  [switch]$StrictOffline,
  [switch]$AllowExternalSkillFallback,
  [switch]$SkipRuntimeFreshnessGate
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')
. (Join-Path $RepoRoot 'scripts\common\Resolve-VgoAdapter.ps1')
$HostId = Resolve-VgoHostId -HostId $HostId
$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId
$Adapter = Resolve-VgoAdapterDescriptor -RepoRoot $RepoRoot -HostId $HostId

function Test-CanonicalRepoExecution {
  param([string]$RepoRoot)
  return (Test-VgoCanonicalRepoExecution -StartPath $RepoRoot)
}
function Get-PreferredPythonCommand {
  foreach ($candidate in @('python', 'python3')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
      return $candidate
    }
  }
  return $null
}
function Get-InstallGovernance {
  param([string]$RepoRoot)
  $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
  if (-not (Test-Path -LiteralPath $governancePath)) {
    throw "version-governance config not found: $governancePath"
  }
  try {
    return Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    throw ("Failed to parse version-governance.json: " + $_.Exception.Message)
  }
}
function Get-InstalledRuntimeConfig {
  param([psobject]$Governance)
  $defaults = [ordered]@{
    target_relpath = 'skills/vibe'
    receipt_relpath = 'skills/vibe/outputs/runtime-freshness-receipt.json'
    post_install_gate = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
    frontmatter_gate = 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
  }
  $runtimeConfig = $null
  if ($null -ne $Governance -and $Governance.PSObject.Properties.Name -contains 'runtime' -and $null -ne $Governance.runtime) {
    if ($Governance.runtime.PSObject.Properties.Name -contains 'installed_runtime') {
      $runtimeConfig = $Governance.runtime.installed_runtime
    }
  }
  if ($null -eq $runtimeConfig) {
    return [pscustomobject]$defaults
  }
  $merged = [ordered]@{}
  foreach ($key in $defaults.Keys) {
    if ($runtimeConfig.PSObject.Properties.Name -contains $key -and $null -ne $runtimeConfig.$key -and -not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.$key)) {
      $merged[$key] = $runtimeConfig.$key
    } else {
      $merged[$key] = $defaults[$key]
    }
  }
  return [pscustomobject]$merged
}
function Invoke-InstalledRuntimeFreshnessGate {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot,
    [switch]$SkipGate
  )
  if ($SkipGate) {
    Write-Warning 'Skipping runtime freshness gate by request.'
    return
  }
  if (-not (Test-CanonicalRepoExecution -RepoRoot $RepoRoot)) {
    Write-Warning 'Runtime freshness gate requires running install.ps1 from the canonical repo root; skipping because no outer .git root was found.'
    return
  }
  $governance = Get-InstallGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $gateRel = [string]$runtimeConfig.post_install_gate
  if ([string]::IsNullOrWhiteSpace($gateRel)) {
    $gateRel = 'scripts\verify\vibe-installed-runtime-freshness-gate.ps1'
  }
  $gatePath = Join-Path $RepoRoot $gateRel
  if (-not (Test-Path -LiteralPath $gatePath)) {
    throw "runtime freshness gate script missing: $gatePath"
  }
  $receiptRel = [string]$runtimeConfig.receipt_relpath
  $global:LASTEXITCODE = 0
  & $gatePath -TargetRoot $TargetRoot -WriteReceipt
  $gateExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
  if ($gateExitCode -ne 0) {
    throw 'Runtime freshness gate failed after install.'
  }
  if (-not [string]::IsNullOrWhiteSpace($receiptRel)) {
    $receiptPath = Join-Path $TargetRoot $receiptRel
    if (-not (Test-Path -LiteralPath $receiptPath)) {
      throw "Runtime freshness receipt missing after install: $receiptPath"
    }
  }

  $frontmatterGateRel = [string]$runtimeConfig.frontmatter_gate
  if (-not [string]::IsNullOrWhiteSpace($frontmatterGateRel)) {
    $frontmatterGatePath = Join-Path $RepoRoot $frontmatterGateRel
    if (-not (Test-Path -LiteralPath $frontmatterGatePath)) {
      throw "frontmatter gate script missing: $frontmatterGatePath"
    }
    $global:LASTEXITCODE = 0
    & $frontmatterGatePath -TargetRoot $TargetRoot
    $frontmatterExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($frontmatterExitCode -ne 0) {
      throw 'Frontmatter BOM gate failed after install.'
    }
  }
}
function Copy-DirContent {
  param(
    [string]$Source,
    [string]$Destination
  )
  if (-not (Test-Path -LiteralPath $Source)) { return }
  $sourceFull = [System.IO.Path]::GetFullPath($Source)
  $destinationFull = [System.IO.Path]::GetFullPath($Destination)
  if ($sourceFull -eq $destinationFull) {
    Write-Host "Skip self-copy: $sourceFull"
    return
  }
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}
function Ensure-SkillPresent {
  param(
    [string]$Name,
    [bool]$Required,
    [string[]]$FallbackSources = @(),
    [string]$TargetRoot,
    [bool]$AllowExternalSkillFallback,
    [System.Collections.Generic.List[string]]$ExternalFallbackUsed,
    [System.Collections.Generic.List[string]]$MissingRequiredSkills
  )
  if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $TargetRoot = $script:TargetRoot
  }
  if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    throw 'Ensure-SkillPresent requires TargetRoot.'
  }
  if ([string]::IsNullOrWhiteSpace($Name)) {
    throw 'Ensure-SkillPresent requires Name.'
  }
  $targetSkillMd = Join-Path $TargetRoot ("skills\" + $Name + "\SKILL.md")
  if (Test-Path -LiteralPath $targetSkillMd) { return }
  if ($AllowExternalSkillFallback) {
    foreach ($src in $FallbackSources) {
      if ([string]::IsNullOrWhiteSpace($src)) { continue }
      if (Test-Path -LiteralPath $src) {
        Write-Warning "Using external fallback source for skill '$Name': $src"
        Copy-DirContent -Source $src -Destination (Join-Path $TargetRoot ("skills\" + $Name))
        $ExternalFallbackUsed.Add($Name) | Out-Null
        break
      }
    }
  }
  if (-not (Test-Path -LiteralPath $targetSkillMd)) {
    if ($Required) {
      $MissingRequiredSkills.Add($Name) | Out-Null
      Write-Warning "Missing required vendored skill: $Name"
    } else {
      Write-Warning "Missing optional vendored skill: $Name"
    }
  }
}
function Sync-VibeCanonicalToTarget {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot
  )
  $governance = Get-InstallGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $canonicalRoot = Join-Path $RepoRoot ([string]$governance.source_of_truth.canonical_root)
  $mirrorFiles = @($governance.packaging.mirror.files)
  $mirrorDirs = @($governance.packaging.mirror.directories)
  $targetRel = [string]$runtimeConfig.target_relpath
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    $targetRel = 'skills\vibe'
  }
  $targetVibeRoot = Join-Path $TargetRoot $targetRel
  foreach ($rel in $mirrorFiles) {
    $src = Join-Path $canonicalRoot $rel
    $dst = Join-Path $targetVibeRoot $rel
    if (-not (Test-Path -LiteralPath $src)) { continue }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
  }
  foreach ($dir in $mirrorDirs) {
    $srcDir = Join-Path $canonicalRoot $dir
    $dstDir = Join-Path $targetVibeRoot $dir
    if (-not (Test-Path -LiteralPath $srcDir)) { continue }
    if (Test-Path -LiteralPath $dstDir) {
      Remove-Item -LiteralPath $dstDir -Recurse -Force
    }
    Copy-DirContent -Source $srcDir -Destination $dstDir
  }
}
Write-Host "=== VCO Adapter Installer ===" -ForegroundColor Cyan
Write-Host "Host   : $HostId"
Write-Host "Mode   : $($Adapter.install_mode)"
Write-Host "Profile: $Profile"
Write-Host "Target : $TargetRoot"
Write-Host "StrictOffline: $StrictOffline"
Write-Host "AllowExternalSkillFallback: $AllowExternalSkillFallback"
Write-Host "SkipRuntimeFreshnessGate: $SkipRuntimeFreshnessGate"
$installGovernance = Get-InstallGovernance -RepoRoot $RepoRoot
$installRuntimeConfig = Get-InstalledRuntimeConfig -Governance $installGovernance
$targetVibeRel = [string]$installRuntimeConfig.target_relpath
if ([string]::IsNullOrWhiteSpace($targetVibeRel)) {
  $targetVibeRel = 'skills\vibe'
}

$adapterInstallerPath = Join-Path $RepoRoot 'scripts\install\Install-VgoAdapter.ps1'
if (-not (Test-Path -LiteralPath $adapterInstallerPath)) {
  throw "Adapter installer script missing: $adapterInstallerPath"
}
$adapterInstallResult = & $adapterInstallerPath -RepoRoot $RepoRoot -TargetRoot $TargetRoot -HostId $HostId -Profile $Profile -AllowExternalSkillFallback:$AllowExternalSkillFallback
$adapterInstallReceipt = $null
if ($adapterInstallResult) {
  try {
    $adapterInstallReceipt = ($adapterInstallResult | Out-String) | ConvertFrom-Json
  } catch {
    $adapterInstallReceipt = $null
  }
}
$externalFallbackUsed = New-Object System.Collections.Generic.List[string]
if ($null -ne $adapterInstallReceipt -and $adapterInstallReceipt.PSObject.Properties.Name -contains 'external_fallback_used') {
  foreach ($name in @($adapterInstallReceipt.external_fallback_used)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$name)) {
      $externalFallbackUsed.Add([string]$name) | Out-Null
    }
  }
}

if ($InstallExternal) {
  if ($Adapter.install_mode -ne 'governed') {
    Write-Warning "InstallExternal is currently only applied to the governed Codex lane. Skipping external install for host '$HostId'."
  } else {
    Write-Host "Installing optional external dependencies..."
  $pythonCommand = Get-PreferredPythonCommand
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $temp = Join-Path $env:TEMP ("superclaude-" + [guid]::NewGuid().ToString("N"))
    try {
      git clone --depth 1 https://github.com/SuperClaude-Org/SuperClaude_Framework.git $temp | Out-Null
      $dest = Join-Path $TargetRoot 'commands\sc'
      if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
      if (Test-Path -LiteralPath (Join-Path $temp 'commands\sc')) {
        Copy-Item -LiteralPath (Join-Path $temp 'commands\sc') -Destination $dest -Recurse -Force
      } elseif (Test-Path -LiteralPath (Join-Path $temp 'sc')) {
        Copy-Item -LiteralPath (Join-Path $temp 'sc') -Destination $dest -Recurse -Force
      }
      Write-Host "Installed SuperClaude commands"
    } catch {
      Write-Warning "Failed to install SuperClaude commands: $($_.Exception.Message)"
    } finally {
      if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
    }
  }
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    try {
      npm install -g claude-flow | Out-Null
      Write-Host "Installed claude-flow"
    } catch {
      Write-Warning "Failed to install claude-flow"
    }
    try {
      npm install -g @th0rgal/ralph-wiggum | Out-Null
      Write-Host "Installed open-ralph-wiggum (@th0rgal/ralph-wiggum)"
    } catch {
      Write-Warning "Failed to install open-ralph-wiggum"
    }
  }
  if ($pythonCommand) {
    if (-not (Get-Command scrapling -ErrorAction SilentlyContinue)) {
      try {
        & $pythonCommand -m pip install 'scrapling[ai]' | Out-Null
        if (Get-Command scrapling -ErrorAction SilentlyContinue) {
          Write-Host "Installed scrapling[ai]"
        } else {
          Write-Warning "scrapling[ai] package install completed, but the scrapling CLI is still not callable from PATH. Ensure your Python scripts directory is exported before relying on the default scrapling MCP surface."
        }
      } catch {
        Write-Warning "Failed to install scrapling[ai]. Install manually (python -m pip install `"scrapling[ai]`") to enable the default scrapling MCP surface."
      }
    } else {
      Write-Host "scrapling already installed"
    }
  } else {
    Write-Warning "python/python3 not detected. Install Python + scrapling[ai] (python -m pip install `"scrapling[ai]`") to enable the default scrapling MCP surface."
  }
  if (-not (Get-Command xan -ErrorAction SilentlyContinue)) {
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
      try {
        scoop install xan | Out-Null
        Write-Host "Installed xan (via scoop)"
      } catch {
        Write-Warning "Failed to install xan via scoop"
      }
    } else {
      Write-Warning "xan CLI not detected. Install manually (Windows: scoop install xan) to enable large CSV acceleration."
    }
  } else {
    Write-Host "xan already installed"
  }
  if ($pythonCommand) {
    try {
      & $pythonCommand -c "import ivy; print(ivy.__version__)" *> $null
      Write-Host "ivy Python package already installed"
    } catch {
      Write-Warning "ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints."
    }
  } else {
    Write-Warning "python/python3 not detected. Install Python + ivy (pip install ivy) if you want framework-interop analyzer hints."
  }
  if (-not (Get-Command fuck-u-code -ErrorAction SilentlyContinue)) {
    Write-Warning "fuck-u-code CLI not detected. Install manually if you want external quality-debt analyzer hints (quality-debt-overlay remains functional without it)."
  } else {
    Write-Host "fuck-u-code already installed"
  }
  try {
    $manifest = Get-Content -LiteralPath (Join-Path $RepoRoot 'config\plugins-manifest.codex.json') -Raw | ConvertFrom-Json
    Write-Host "Codex-only mode: plugin auto-install commands are disabled."
    foreach ($plugin in $manifest.core) {
      $mode = if ($plugin.PSObject.Properties.Name -contains 'install_mode') { $plugin.install_mode } else { 'manual-codex' }
      $hint = if ($plugin.PSObject.Properties.Name -contains 'install_hint') { $plugin.install_hint } else { 'Provision manually in your Codex environment.' }
      Write-Host ("[MANUAL] {0} ({1}) - {2}" -f $plugin.name, $mode, $hint)
    }
  } catch {
    Write-Warning "Failed to process plugin manifest"
  }
  }
}
if ($StrictOffline) {
  $offlineGate = Join-Path $RepoRoot 'scripts\verify\vibe-offline-skills-gate.ps1'
  if (-not (Test-Path -LiteralPath $offlineGate)) {
    throw "StrictOffline requested, but offline gate script is missing: $offlineGate"
  }
  & $offlineGate `
    -SkillsRoot (Join-Path $TargetRoot 'skills') `
    -PackManifestPath (Join-Path $RepoRoot 'config\pack-manifest.json') `
    -SkillsLockPath (Join-Path $RepoRoot 'config\skills-lock.json')
  if ($LASTEXITCODE -ne 0) {
    throw "StrictOffline validation failed (vibe-offline-skills-gate)."
  }
  if ($externalFallbackUsed.Count -gt 0) {
    throw ("StrictOffline rejected external fallback usage: " + (($externalFallbackUsed | Select-Object -Unique) -join ", "))
  }
} elseif ($externalFallbackUsed.Count -gt 0) {
  Write-Warning ("External fallback skills were used (non-reproducible install): " + (($externalFallbackUsed | Select-Object -Unique) -join ", "))
}
Invoke-InstalledRuntimeFreshnessGate -RepoRoot $RepoRoot -TargetRoot $TargetRoot -SkipGate:$SkipRuntimeFreshnessGate
Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile $Profile -TargetRoot `"$TargetRoot`""
