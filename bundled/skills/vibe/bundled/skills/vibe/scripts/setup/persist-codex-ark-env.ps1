param(
  [string]$CodexRoot = (Join-Path $env:USERPROFILE ".codex"),
  [string]$BaseUrl = "",
  [string]$ApiKey = "",
  [switch]$AllowEmptyApiKey
)

$ErrorActionPreference = "Stop"

function Get-NonEmptyOrNull {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
  return [string]$Value
}

$settingsPath = Join-Path $CodexRoot "settings.json"
if (-not (Test-Path -LiteralPath $settingsPath)) {
  throw "Codex settings.json not found: $settingsPath (run the installer first or create it from config/settings.template.codex.json)"
}

$resolvedBaseUrl = Get-NonEmptyOrNull -Value $BaseUrl
if (-not $resolvedBaseUrl) {
  $resolvedBaseUrl = Get-NonEmptyOrNull -Value $env:ARK_BASE_URL
}
if (-not $resolvedBaseUrl) {
  $resolvedBaseUrl = Get-NonEmptyOrNull -Value $env:VOLC_ARK_BASE_URL
}

$resolvedApiKey = Get-NonEmptyOrNull -Value $ApiKey
if (-not $resolvedApiKey) {
  $resolvedApiKey = Get-NonEmptyOrNull -Value $env:ARK_API_KEY
}

if (-not $resolvedApiKey -and (-not $AllowEmptyApiKey)) {
  throw "ARK_API_KEY is missing. Provide -ApiKey or set env:ARK_API_KEY. (We refuse to write an empty/placeholder key by default.)"
}

try {
  $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
  throw "Failed to parse settings.json as JSON: $settingsPath"
}

if (-not $settings.env) {
  $settings | Add-Member -NotePropertyName env -NotePropertyValue ([pscustomobject]@{}) -Force
}

if ($resolvedBaseUrl) {
  $settings.env | Add-Member -NotePropertyName ARK_BASE_URL -NotePropertyValue $resolvedBaseUrl -Force
}

if ($resolvedApiKey) {
  $settings.env | Add-Member -NotePropertyName ARK_API_KEY -NotePropertyValue $resolvedApiKey -Force
}

# Keep these consistent with the shipped template unless user already overrides them.
if (-not ($settings.env.PSObject.Properties.Name -contains "VCO_PROFILE")) {
  $settings.env | Add-Member -NotePropertyName VCO_PROFILE -NotePropertyValue "full" -Force
}
if (-not ($settings.env.PSObject.Properties.Name -contains "VCO_CODEX_MODE")) {
  $settings.env | Add-Member -NotePropertyName VCO_CODEX_MODE -NotePropertyValue "true" -Force
}

$settings | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $settingsPath -Encoding UTF8

Write-Host "Updated Codex settings.json env:" -ForegroundColor Green
if ($resolvedBaseUrl) { Write-Host "- ARK_BASE_URL set" }
Write-Host "- ARK_API_KEY set"

