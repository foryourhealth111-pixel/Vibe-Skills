param(
  [string]$RepoRoot,
  [switch]$DryRun,
  [switch]$SyncRootVibe
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$mapPath = Join-Path $RepoRoot 'config\dependency-map.json'
if (-not (Test-Path -LiteralPath $mapPath)) {
  throw "dependency map not found: $mapPath"
}

$data = Get-Content -LiteralPath $mapPath -Raw | ConvertFrom-Json

function Copy-Compat {
  param([string]$Source, [string]$Target)
  if (-not (Test-Path -LiteralPath $Source)) {
    Write-Warning "missing source: $Source"
    return
  }
  if ($DryRun) {
    Write-Host "[DRYRUN] $Source -> $Target"
    return
  }
  $targetDir = Join-Path $RepoRoot $Target
  if (Test-Path -LiteralPath $targetDir) {
    Remove-Item -LiteralPath $targetDir -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetDir) | Out-Null
  Copy-Item -LiteralPath $Source -Destination $targetDir -Recurse -Force
  Write-Host "Synced: $Target"
}

foreach ($it in $data.items) {
  Copy-Compat -Source $it.source -Target $it.target
}

if ($SyncRootVibe -and -not $DryRun) {
  $vibeRoot = Join-Path $RepoRoot 'bundled\skills\vibe'
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'SKILL.md') -Destination (Join-Path $RepoRoot 'SKILL.md') -Force
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'protocols\*') -Destination (Join-Path $RepoRoot 'protocols') -Recurse -Force
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'references\*') -Destination (Join-Path $RepoRoot 'references') -Recurse -Force
  Write-Host "Synced root vibe compatibility files"
}
