param(
  [string]$CodexRoot = (Join-Path $env:USERPROFILE ".codex"),
  [ValidateSet("minimal", "full")]
  [string]$Profile = "minimal",
  [switch]$AllowHeavy,
  [switch]$NoPipUpgrade
)

$ErrorActionPreference = "Stop"

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host $Title -ForegroundColor Cyan
}

function Resolve-VendorRoot {
  param([string]$Root)
  return (Join-Path $Root "_external\\ruc-nlpir")
}

$vendorRoot = Resolve-VendorRoot -Root $CodexRoot
$venvPath = Join-Path $vendorRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\\python.exe"

Write-Section "RUC-NLPIR install (profile=$Profile)"
Write-Host "- vendorRoot: $vendorRoot"
Write-Host "- venvPath:   $venvPath"

if (-not (Test-Path -LiteralPath $vendorRoot)) {
  throw "Vendor root not found: $vendorRoot. (Expected upstream repos under this folder.)"
}

Write-Section "Python venv"
if (-not (Test-Path -LiteralPath $venvPython)) {
  Write-Host "Creating venv..."
  & python -m venv $venvPath
}
if (-not (Test-Path -LiteralPath $venvPython)) {
  throw "venv python not found after creation: $venvPython"
}
Write-Host "venv python: $venvPython" -ForegroundColor Green

if (-not $NoPipUpgrade) {
  Write-Section "Upgrade pip tooling"
  & $venvPython -m pip install --upgrade pip setuptools wheel
}

Write-Section "Install dependencies"
if ($Profile -eq "minimal") {
  # Minimal, stable deps for our wrappers (NOT full upstream stacks).
  # - bm25s enables FlashRAG-style fast BM25 retrieval (optional engine)
  # - readability-lxml helps extract readable article text in local web runners (optional)
  $packages = @(
    "openai>=2.0.0",
    "requests>=2.31.0",
    "tqdm>=4.66.0",
    "aiohttp>=3.9.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "readability-lxml>=0.8.1",
    "bm25s[core]==0.2.1"
  )
  & $venvPython -m pip install @packages
} elseif ($Profile -eq "full") {
  if (-not $AllowHeavy) {
    throw "Profile 'full' installs heavy deps (torch/vllm/transformers). Re-run with -AllowHeavy if you really want that."
  }
  $repoNames = @("FlashRAG", "WebThinker", "DeepAgent")
  foreach ($repo in $repoNames) {
    $req = Join-Path $vendorRoot "$repo\\requirements.txt"
    if (-not (Test-Path -LiteralPath $req)) {
      Write-Warning "requirements.txt missing: $req (skip)"
      continue
    }
    Write-Host "Installing $repo requirements..." -ForegroundColor Yellow
    & $venvPython -m pip install -r $req
  }
}

Write-Section "Freeze lockfile"
$lockPath = Join-Path $vendorRoot "requirements-lock.txt"
& $venvPython -m pip freeze | Set-Content -LiteralPath $lockPath -Encoding UTF8
Write-Host "Wrote: $lockPath" -ForegroundColor Green

Write-Section "Write manifest"
function Try-GitHead {
  param([string]$RepoPath)
  try {
    return (git -C $RepoPath rev-parse HEAD).Trim()
  } catch {
    return $null
  }
}

$manifestPath = Join-Path $vendorRoot "MANIFEST.json"
$manifest = [ordered]@{
  version    = 1
  created_at = (Get-Date).ToString("s")
  profile    = $Profile
  venv_python = $venvPython
  repos      = [ordered]@{
    FlashRAG  = [ordered]@{ path = (Join-Path $vendorRoot "FlashRAG");  head = (Try-GitHead (Join-Path $vendorRoot "FlashRAG")) }
    WebThinker = [ordered]@{ path = (Join-Path $vendorRoot "WebThinker"); head = (Try-GitHead (Join-Path $vendorRoot "WebThinker")) }
    DeepAgent = [ordered]@{ path = (Join-Path $vendorRoot "DeepAgent"); head = (Try-GitHead (Join-Path $vendorRoot "DeepAgent")) }
  }
}

$manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "Wrote: $manifestPath" -ForegroundColor Green

Write-Section "Done"
$preflightScript = Join-Path $CodexRoot "skills\\vibe\\scripts\\ruc-nlpir\\preflight.ps1"
Write-Host "Next: run preflight -> " -NoNewline
Write-Host ("powershell -ExecutionPolicy Bypass -File `"{0}`"" -f $preflightScript) -ForegroundColor Green
