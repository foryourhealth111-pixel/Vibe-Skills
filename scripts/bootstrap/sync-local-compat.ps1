param(
  [string]$RepoRoot,
  [switch]$DryRun,
  [switch]$SyncRootVibe
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}
. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')

$mapPath = Join-Path $RepoRoot 'config\dependency-map.json'
if (-not (Test-Path -LiteralPath $mapPath)) {
  throw "dependency map not found: $mapPath"
}

$data = Get-Content -LiteralPath $mapPath -Raw | ConvertFrom-Json
$forbiddenPolicyPath = Join-Path $RepoRoot 'config\forbidden-mcp-policy.json'
if (-not (Test-Path -LiteralPath $forbiddenPolicyPath)) {
  throw "forbidden MCP policy not found: $forbiddenPolicyPath"
}
$forbiddenPolicy = Get-Content -LiteralPath $forbiddenPolicyPath -Raw | ConvertFrom-Json
$forbiddenSyncIds = @($forbiddenPolicy.forbidden_mcp_ids) + @($forbiddenPolicy.forbidden_sync_skill_ids)
$forbiddenSyncIds = @($forbiddenSyncIds | ForEach-Object { ([string]$_).ToLowerInvariant() })

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
  $sourceSegments = ([string]$it.source).Replace('\', '/').ToLowerInvariant().Split('/')
  $targetSegments = ([string]$it.target).Replace('\', '/').ToLowerInvariant().Split('/')
  foreach ($forbiddenSyncId in $forbiddenSyncIds) {
    if ($sourceSegments -contains $forbiddenSyncId -or $targetSegments -contains $forbiddenSyncId) {
      throw "dependency map contains forbidden sync id: $forbiddenSyncId"
    }
  }
  $resolvedSource = Resolve-VgoPathSpec -PathSpec ([string]$it.source)
  Copy-Compat -Source $resolvedSource -Target $it.target
}

if ($SyncRootVibe -and -not $DryRun) {
  $vibeRoot = Join-Path $RepoRoot 'bundled\skills\vibe'
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'SKILL.md') -Destination (Join-Path $RepoRoot 'SKILL.md') -Force
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'protocols\*') -Destination (Join-Path $RepoRoot 'protocols') -Recurse -Force
  Copy-Item -LiteralPath (Join-Path $vibeRoot 'references\*') -Destination (Join-Path $RepoRoot 'references') -Recurse -Force
  Write-Host "Synced root vibe compatibility files"
}
