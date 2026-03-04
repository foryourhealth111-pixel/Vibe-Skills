param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [string]$TargetRoot = (Join-Path $env:USERPROFILE ".codex"),
  [switch]$InstallExternal,
  [switch]$StrictOffline,
  [switch]$AllowExternalSkillFallback
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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

  $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
  if (-not (Test-Path -LiteralPath $governancePath)) { return }

  try {
    $governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    Write-Warning "Failed to parse version-governance.json; skip canonical sync."
    return
  }

  $canonicalRoot = Join-Path $RepoRoot ([string]$governance.source_of_truth.canonical_root)
  $mirrorFiles = @($governance.packaging.mirror.files)
  $mirrorDirs = @($governance.packaging.mirror.directories)
  $targetVibeRoot = Join-Path $TargetRoot 'skills\vibe'

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
    Copy-DirContent -Source $srcDir -Destination $dstDir
  }
}

Write-Host "=== VCO Codex Installer ===" -ForegroundColor Cyan
Write-Host "Profile: $Profile"
Write-Host "Target : $TargetRoot"
Write-Host "StrictOffline: $StrictOffline"
Write-Host "AllowExternalSkillFallback: $AllowExternalSkillFallback"

$canonicalSkillsRoot = Split-Path -Parent $RepoRoot
$workspaceRoot = Split-Path -Parent $canonicalSkillsRoot

$paths = @(
  "skills",
  "rules",
  "hooks",
  "agents\templates",
  "mcp\profiles",
  "config",
  "commands"
)
foreach ($p in $paths) {
  New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot $p) | Out-Null
}

Copy-DirContent -Source (Join-Path $RepoRoot 'bundled\skills') -Destination (Join-Path $TargetRoot 'skills')

# Ensure unified /vibe entry uses the latest router implementation (script + modules) after install.
$vibeRouterSourceDir = Join-Path $RepoRoot 'scripts\router'
$vibeRouterTargetDir = Join-Path $TargetRoot 'skills\vibe\scripts\router'
if (Test-Path -LiteralPath $vibeRouterSourceDir) {
  Copy-DirContent -Source $vibeRouterSourceDir -Destination $vibeRouterTargetDir
}

# Enforce canonical vibe mirror files/dirs to avoid main-vs-bundled drift after install.
Sync-VibeCanonicalToTarget -RepoRoot $RepoRoot -TargetRoot $TargetRoot

$requiredCore = @('dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')
$requiredSp = @('brainstorming', 'writing-plans', 'subagent-driven-development', 'systematic-debugging')
$optionalSp = @('requesting-code-review', 'receiving-code-review', 'verification-before-completion')

$spCanonicalRoot = Join-Path $workspaceRoot 'skills'
$legacySpRoot = Join-Path $workspaceRoot 'superpowers\skills'
$spSrcRoot = Join-Path $RepoRoot 'bundled\superpowers-skills'

$externalFallbackUsed = New-Object System.Collections.Generic.List[string]
$missingRequiredSkills = New-Object System.Collections.Generic.List[string]

foreach ($name in $requiredCore) {
  Ensure-SkillPresent `
    -Name $name `
    -Required:$true `
    -FallbackSources @(
      (Join-Path $canonicalSkillsRoot $name),
      (Join-Path $spCanonicalRoot $name),
      (Join-Path $legacySpRoot $name),
      (Join-Path $spSrcRoot $name)
    ) `
    -TargetRoot $TargetRoot `
    -AllowExternalSkillFallback:$AllowExternalSkillFallback `
    -ExternalFallbackUsed $externalFallbackUsed `
    -MissingRequiredSkills $missingRequiredSkills
}

foreach ($name in $requiredSp) {
  Ensure-SkillPresent `
    -Name $name `
    -Required:$true `
    -FallbackSources @(
      (Join-Path $spCanonicalRoot $name),
      (Join-Path $legacySpRoot $name),
      (Join-Path $spSrcRoot $name),
      (Join-Path $canonicalSkillsRoot $name)
    ) `
    -TargetRoot $TargetRoot `
    -AllowExternalSkillFallback:$AllowExternalSkillFallback `
    -ExternalFallbackUsed $externalFallbackUsed `
    -MissingRequiredSkills $missingRequiredSkills
}

if ($Profile -eq 'full') {
  foreach ($name in $optionalSp) {
    Ensure-SkillPresent `
      -Name $name `
      -Required:$false `
      -FallbackSources @(
        (Join-Path $spCanonicalRoot $name),
        (Join-Path $legacySpRoot $name),
        (Join-Path $spSrcRoot $name),
        (Join-Path $canonicalSkillsRoot $name)
      ) `
      -TargetRoot $TargetRoot `
      -AllowExternalSkillFallback:$AllowExternalSkillFallback `
      -ExternalFallbackUsed $externalFallbackUsed `
      -MissingRequiredSkills $missingRequiredSkills
  }
}

Copy-DirContent -Source (Join-Path $RepoRoot 'rules') -Destination (Join-Path $TargetRoot 'rules')
Copy-DirContent -Source (Join-Path $RepoRoot 'hooks') -Destination (Join-Path $TargetRoot 'hooks')
Copy-DirContent -Source (Join-Path $RepoRoot 'agents\templates') -Destination (Join-Path $TargetRoot 'agents\templates')
Copy-DirContent -Source (Join-Path $RepoRoot 'mcp') -Destination (Join-Path $TargetRoot 'mcp')

Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\plugins-manifest.codex.json') -Destination (Join-Path $TargetRoot 'config\plugins-manifest.codex.json') -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\upstream-lock.json') -Destination (Join-Path $TargetRoot 'config\upstream-lock.json') -Force
if (Test-Path -LiteralPath (Join-Path $RepoRoot 'config\skills-lock.json')) {
  Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\skills-lock.json') -Destination (Join-Path $TargetRoot 'config\skills-lock.json') -Force
}

$settingsTarget = Join-Path $TargetRoot 'settings.json'
if (-not (Test-Path -LiteralPath $settingsTarget)) {
  Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\settings.template.codex.json') -Destination $settingsTarget -Force
  Write-Host "Created settings.json from template" -ForegroundColor Yellow
} else {
  Write-Host "settings.json already exists (kept as-is)"
}

if ($InstallExternal) {
  Write-Host "Installing optional external dependencies..."

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

  if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
      python -c "import ivy; print(ivy.__version__)" *> $null
      Write-Host "ivy Python package already installed"
    } catch {
      Write-Warning "ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints."
    }
  } else {
    Write-Warning "python not detected. Install Python + ivy (pip install ivy) if you want framework-interop analyzer hints."
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

if ($missingRequiredSkills.Count -gt 0) {
  throw ("Missing required vendored skills: " + (($missingRequiredSkills | Select-Object -Unique) -join ", "))
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

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile $Profile -TargetRoot `"$TargetRoot`""
