param(
  [string]$CodexRoot = '',
  [string]$RuntimeConfigPath = "",
  [ValidateSet("lite", "upstream")]
  [string]$Mode = "lite",
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host $Title -ForegroundColor Cyan
}

function Get-NonEmptyOrNull {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
  return [string]$Value
}

function Resolve-RuntimeConfigPath {
  param([string]$ExplicitPath, [string]$Root)
  $p = Get-NonEmptyOrNull -Value $ExplicitPath
  if ($p) { return (Resolve-VgoPathSpec -PathSpec $p -TargetRoot $Root) }
  return (Join-Path $Root "skills\\vibe\\config\\ruc-nlpir-runtime.json")
}

function Test-EnvSet {
  param([string]$Name)
  $v = Get-NonEmptyOrNull -Value (Get-Item -Path "env:$Name" -ErrorAction SilentlyContinue).Value
  return [bool]$v
}

function Try-GitHead {
  param([string]$RepoPath)
  try {
    return (git -C $RepoPath rev-parse HEAD).Trim()
  } catch {
    return $null
  }
}

if ([string]::IsNullOrWhiteSpace($CodexRoot)) {
  $CodexRoot = Resolve-VgoTargetRoot
}
$runtimePath = Resolve-RuntimeConfigPath -ExplicitPath $RuntimeConfigPath -Root $CodexRoot
if (-not (Test-Path -LiteralPath $runtimePath)) {
  throw "Runtime config not found: $runtimePath"
}

try {
  $runtime = Get-Content -LiteralPath $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
  throw "Failed to parse runtime JSON: $runtimePath"
}

Write-Section "RUC-NLPIR preflight (mode=$Mode)"
Write-Host "- runtime: $runtimePath"

Write-Section "Vendored upstream repos"
$repoOk = $true
$repoNames = @($runtime.repos.PSObject.Properties.Name | Sort-Object)
foreach ($name in $repoNames) {
  $repo = $runtime.repos.$name
  if (-not $repo) {
    Write-Host ("- {0}: missing in runtime config" -f $name) -ForegroundColor Red
    $repoOk = $false
    continue
  }
  $path = Resolve-VgoPathSpec -PathSpec ([string]$repo.path) -TargetRoot $CodexRoot
  $expected = $repo.expected_commit
  if (-not (Test-Path -LiteralPath $path)) {
    Write-Host ("- {0}: MISSING ({1})" -f $name, $path) -ForegroundColor Red
    $repoOk = $false
    continue
  }
  $head = Try-GitHead -RepoPath $path
  if ($head -and $expected -and ($head -ne $expected)) {
    Write-Host ("- {0}: OK (HEAD={1}, expected={2}) [DIFF]" -f $name, $head, $expected) -ForegroundColor Yellow
  } else {
    Write-Host ("- {0}: OK" -f $name) -ForegroundColor Green
    if ($head) { Write-Host "  - HEAD: $head" }
  }
}

Write-Section "Python runtime"
$venvPythonSpec = if ($IsWindows) { [string]$runtime.python.venv_python_win } else { [string]$runtime.python.venv_python_unix }
if ([string]::IsNullOrWhiteSpace($venvPythonSpec)) {
  $venvPythonSpec = [string]$runtime.python.venv_python_win
}
$venvPython = Resolve-VgoPathSpec -PathSpec $venvPythonSpec -TargetRoot $CodexRoot
$venvOk = $false
if ($venvPython -and (Test-Path -LiteralPath $venvPython)) {
  $venvOk = $true
  Write-Host "- venv python: OK ($venvPython)" -ForegroundColor Green
} else {
  Write-Host "- venv python: MISSING ($venvPython)" -ForegroundColor Yellow
}

Write-Section "LLM endpoint"
$apiKeyEnv = $runtime.llm.api_key_env
$apiKeySet = $false
if ($apiKeyEnv) { $apiKeySet = Test-EnvSet -Name $apiKeyEnv }

$baseUrl = $null
foreach ($cand in @($runtime.llm.base_url_env_candidates)) {
  if (Test-EnvSet -Name $cand) {
    $baseUrl = (Get-Item -Path "env:$cand").Value
    break
  }
}
if (-not $baseUrl) { $baseUrl = $runtime.llm.base_url_default }

$model = $null
if ($runtime.llm.model_env -and (Test-EnvSet -Name $runtime.llm.model_env)) {
  $model = (Get-Item -Path ("env:" + $runtime.llm.model_env)).Value
}
if (-not $model) { $model = $runtime.llm.model_default }

Write-Host "- base_url: $baseUrl"
Write-Host "- model:    $model"
if ($apiKeyEnv) {
  if ($apiKeySet) {
    Write-Host ("- {0}: set" -f $apiKeyEnv) -ForegroundColor Green
  } else {
    Write-Host ("- {0}: MISSING" -f $apiKeyEnv) -ForegroundColor Yellow
  }
}

Write-Section "Optional search keys (only needed for local/offline runners)"
$search = $runtime.web.search_keys_env
if ($search) {
  foreach ($k in $search.PSObject.Properties) {
    $envName = [string]$k.Value
    if (-not $envName) { continue }
    $set = Test-EnvSet -Name $envName
    $color = if ($set) { "Green" } else { "DarkGray" }
    Write-Host ("- {0}: {1}" -f $envName, ($(if ($set) { "set" } else { "not set" }))) -ForegroundColor $color
  }
}

Write-Section "Recommendation"
if (-not $venvOk) {
  Write-Host "- Create an isolated venv manually for the vendored runtime (auto-install script removed)." -ForegroundColor Yellow
  Write-Host "- Then install only the minimal packages you actually need into that venv." -ForegroundColor Yellow
}
if (-not $apiKeySet) {
  Write-Host "- Set LLM key via env var: $apiKeyEnv (do NOT paste secrets into files or CLI history)."
}
if ($Mode -eq "upstream") {
  if (-not $repoOk) {
    $vendorRoot = Resolve-VgoPathSpec -PathSpec ([string]$runtime.vendor_root) -TargetRoot $CodexRoot
    Write-Host "- Upstream repos missing; re-clone into $vendorRoot" -ForegroundColor Yellow
  }
  if (-not $venvOk) {
    Write-Host "- Upstream mode expects isolated venv; install it first." -ForegroundColor Yellow
  }
}

if ($Strict) {
  if (-not $repoOk) { exit 2 }
  if (-not $apiKeySet) { exit 2 }
  if ($Mode -eq "upstream" -and -not $venvOk) { exit 2 }
}

exit 0
