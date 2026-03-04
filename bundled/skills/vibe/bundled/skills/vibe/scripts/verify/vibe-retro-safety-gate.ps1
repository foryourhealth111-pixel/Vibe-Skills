param()

$ErrorActionPreference = "Stop"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    Write-Host "[FAIL] $Message" -ForegroundColor Red
    return $false
}

function Invoke-CheckScript {
    param(
        [string]$ScriptPath,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        return Assert-True -Condition $false -Message "[$Name] script exists"
    }

    & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath | Out-Null
    $exitCode = $LASTEXITCODE
    return Assert-True -Condition ($exitCode -eq 0) -Message "[$Name] exit code is 0"
}

function Get-HashMap {
    param([string[]]$Paths)

    $map = @{}
    foreach ($p in $Paths) {
        if (-not (Test-Path -LiteralPath $p)) { continue }
        $map[$p] = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
    }
    return $map
}

function Assert-HashUnchanged {
    param(
        [hashtable]$Before,
        [hashtable]$After
    )

    $results = @()
    foreach ($k in $Before.Keys) {
        $beforeHash = [string]$Before[$k]
        $afterHash = [string]$After[$k]
        $results += Assert-True -Condition ($beforeHash -eq $afterHash) -Message "Protected file unchanged: $k"
    }
    return $results
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$verifyRoot = Join-Path $repoRoot "scripts\verify"
$configRoot = Join-Path $repoRoot "config"
$protocolRoot = Join-Path $repoRoot "protocols"
$referenceRoot = Join-Path $repoRoot "references"
$outputRoot = Join-Path $repoRoot "outputs\retro\compare\safety-gate"

if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

$protectedFiles = @()
$protectedFiles += Join-Path $repoRoot "SKILL.md"
$protectedFiles += (Get-ChildItem -LiteralPath $configRoot -File -Filter *.json | ForEach-Object { $_.FullName })
$protectedFiles += (Get-ChildItem -LiteralPath $protocolRoot -File -Filter *.md | ForEach-Object { $_.FullName })
$protectedFiles += (Get-ChildItem -LiteralPath $referenceRoot -File -Filter *.md | ForEach-Object { $_.FullName })

$beforeHashes = Get-HashMap -Paths $protectedFiles

$results = @()

Write-Host "=== Retro Safety Gate ==="
Write-Host "Protected files: $($protectedFiles.Count)"

$results += Invoke-CheckScript -ScriptPath (Join-Path $verifyRoot "vibe-context-retro-smoke.ps1") -Name "retro-smoke"
$results += Invoke-CheckScript -ScriptPath (Join-Path $verifyRoot "vibe-retro-context-regression-matrix.ps1") -Name "retro-regression-matrix"
$results += Invoke-CheckScript -ScriptPath (Join-Path $verifyRoot "vibe-routing-smoke.ps1") -Name "routing-smoke"
$results += Invoke-CheckScript -ScriptPath (Join-Path $verifyRoot "vibe-pack-routing-smoke.ps1") -Name "pack-routing-smoke"

$baselinePath = Join-Path $outputRoot "baseline-cer.json"
$currentPath = Join-Path $outputRoot "current-cer.json"
$deltaMdPath = Join-Path $outputRoot "delta.md"
$deltaJsonPath = Join-Path $outputRoot "delta.json"

@'
{
  "report_id": "CER-SAFETY-BASE",
  "trigger_signals": {
    "fallback_rate": 0.26,
    "context_pressure": 0.81,
    "route_stability_pack": 0.74,
    "route_stability_skill": 0.68,
    "top1_top2_gap": 0.02
  },
  "findings": [
    { "pattern": "CF-3" },
    { "pattern": "CF-5" }
  ]
}
'@ | Set-Content -LiteralPath $baselinePath -Encoding UTF8

@'
{
  "report_id": "CER-SAFETY-CURR",
  "trigger_signals": {
    "fallback_rate": 0.15,
    "context_pressure": 0.63,
    "route_stability_pack": 0.85,
    "route_stability_skill": 0.82,
    "top1_top2_gap": 0.08
  },
  "findings": [
    { "pattern": "CF-2" },
    { "pattern": "CF-3" }
  ]
}
'@ | Set-Content -LiteralPath $currentPath -Encoding UTF8

$cerCompareScript = Join-Path $verifyRoot "cer-compare.ps1"
if (Test-Path -LiteralPath $cerCompareScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $cerCompareScript `
        -BaselineCerPath $baselinePath `
        -CurrentCerPath $currentPath `
        -OutputMarkdownPath $deltaMdPath `
        -OutputJsonPath $deltaJsonPath `
        -UpdateCurrentComparison | Out-Null
    $results += Assert-True -Condition ($LASTEXITCODE -eq 0) -Message "[cer-compare] exit code is 0"
    $results += Assert-True -Condition (Test-Path -LiteralPath $deltaMdPath) -Message "[cer-compare] markdown output exists"
    $results += Assert-True -Condition (Test-Path -LiteralPath $deltaJsonPath) -Message "[cer-compare] json output exists"
} else {
    $results += Assert-True -Condition $false -Message "[cer-compare] script exists"
}

$afterHashes = Get-HashMap -Paths $protectedFiles
$results += Assert-HashUnchanged -Before $beforeHashes -After $afterHashes

$passCount = ($results | Where-Object { $_ }).Count
$failCount = ($results | Where-Object { -not $_ }).Count
$total = $results.Count

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}

Write-Host "Retro safety gate passed."
exit 0
