param(
  [string]$CodexRoot = '',
  [string]$OutPath = "",
  [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$CodexRoot = Resolve-VgoTargetRoot -TargetRoot $CodexRoot

function Get-NonEmptyOrNull {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
  return [string]$Value
}

function Resolve-DefaultOutPath {
  param([string]$ExplicitOutPath)
  $p = Get-NonEmptyOrNull -Value $ExplicitOutPath
  if ($p) { return $p }
  # Default: write a GitHub-safe template into the VCO repo config folder
  $repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\\..")).Path
  return (Join-Path $repoRoot "config\\settings.template.codex.json")
}

function Redact-EnvValue {
  param(
    [string]$Key,
    [string]$Value
  )

  if (-not $Key) { return $Value }
  $k = $Key.ToUpperInvariant()

  if ($k -eq "OPENAI_API_KEY") { return "<REQUIRED>" }

  # Conservative generic redaction (avoid leaking unexpected credentials)
  if ($k -match "(_KEY|TOKEN|SECRET|PASSWORD|PASSWD)$") {
    return "<REDACTED>"
  }

  return $Value
}

$settingsPath = Join-Path $CodexRoot "settings.json"
if (-not (Test-Path -LiteralPath $settingsPath)) {
  throw "Codex settings.json not found: $settingsPath"
}

try {
  $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
  throw "Failed to parse settings.json as JSON: $settingsPath"
}

if (-not $settings.env) {
  throw "settings.json missing .env object: $settingsPath"
}

$outPath = Resolve-DefaultOutPath -ExplicitOutPath $OutPath

if ((Test-Path -LiteralPath $outPath) -and (-not $Overwrite)) {
  throw "OutPath already exists: $outPath (pass -Overwrite to replace)"
}

# Build a sanitized copy (preserve structure, redact env values)
$sanitized = [ordered]@{}
foreach ($prop in @($settings.PSObject.Properties.Name)) {
  if ($prop -ne "env") {
    $sanitized[$prop] = $settings.$prop
  }
}

$sanitizedEnv = [ordered]@{}
foreach ($p in @($settings.env.PSObject.Properties)) {
  $name = [string]$p.Name
  $value = [string]$p.Value
  $sanitizedEnv[$name] = Redact-EnvValue -Key $name -Value $value
}
$sanitized["env"] = $sanitizedEnv

$json = ($sanitized | ConvertTo-Json -Depth 50)
New-Item -ItemType Directory -Path (Split-Path -Parent $outPath) -Force | Out-Null
$json | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host "Wrote sanitized settings template:" -ForegroundColor Green
Write-Host ("- {0}" -f $outPath)
Write-Host "Note: secrets were redacted; safe to commit/push." -ForegroundColor Green
