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

function Assert-FileContains {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return Assert-True -Condition $false -Message "$Message (missing file: $Path)"
    }

    $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return Assert-True -Condition ([bool]($content -match $Pattern)) -Message $Message
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$bundleRoot = Join-Path $repoRoot "bundled\skills\vibe"

$mainSkill = Join-Path $repoRoot "SKILL.md"
$bundleSkill = Join-Path $bundleRoot "SKILL.md"

$mainRetro = Join-Path $repoRoot "protocols\retro.md"
$bundleRetro = Join-Path $bundleRoot "protocols\retro.md"

$mainFallback = Join-Path $repoRoot "references\fallback-chains.md"
$bundleFallback = Join-Path $bundleRoot "references\fallback-chains.md"

$mainDesignDoc = Join-Path $repoRoot "docs\context-retro-advisor-design.md"
$mainMdTemplate = Join-Path $repoRoot "templates\cer-report.md.template"
$mainJsonTemplate = Join-Path $repoRoot "templates\cer-report.json.template"
$mainJsonSchema = Join-Path $repoRoot "templates\cer-report.schema.json"
$mainRegressionScript = Join-Path $repoRoot "scripts\verify\vibe-retro-context-regression-matrix.ps1"
$mainCerCompareScript = Join-Path $repoRoot "scripts\verify\cer-compare.ps1"
$bundleMdTemplate = Join-Path $bundleRoot "templates\cer-report.md.template"
$bundleJsonTemplate = Join-Path $bundleRoot "templates\cer-report.json.template"
$bundleJsonSchema = Join-Path $bundleRoot "templates\cer-report.schema.json"

$results = @()

Write-Host "=== VCO Context Retro Advisor Smoke Checks ==="

$results += Assert-FileContains -Path $mainSkill -Pattern "Context Retro Advisor" -Message "Main SKILL includes Context Retro Advisor in LEARN phase"
$results += Assert-FileContains -Path $bundleSkill -Pattern "Context Retro Advisor" -Message "Bundled SKILL includes Context Retro Advisor in LEARN phase"
$results += Assert-FileContains -Path $mainSkill -Pattern "CER format" -Message "Main SKILL defines CER output contract"
$results += Assert-FileContains -Path $bundleSkill -Pattern "CER format" -Message "Bundled SKILL defines CER output contract"

$results += Assert-FileContains -Path $mainRetro -Pattern "Context Retro Advisor \(Agent-Skills Guided\)" -Message "Main retro protocol includes Agent-Skills guided advisor"
$results += Assert-FileContains -Path $bundleRetro -Pattern "Context Retro Advisor \(Agent-Skills Guided\)" -Message "Bundled retro protocol includes Agent-Skills guided advisor"
$results += Assert-FileContains -Path $mainRetro -Pattern "CF-1 Attention dilution / lost-in-middle" -Message "Main retro protocol includes CF taxonomy"
$results += Assert-FileContains -Path $bundleRetro -Pattern "CF-1 Attention dilution / lost-in-middle" -Message "Bundled retro protocol includes CF taxonomy"
$results += Assert-FileContains -Path $mainRetro -Pattern "Context Evidence Report \(CER\) Output Contract" -Message "Main retro protocol includes CER section"
$results += Assert-FileContains -Path $bundleRetro -Pattern "Context Evidence Report \(CER\) Output Contract" -Message "Bundled retro protocol includes CER section"
$results += Assert-FileContains -Path $mainRetro -Pattern "Default Trigger Thresholds" -Message "Main retro protocol includes trigger threshold table"
$results += Assert-FileContains -Path $bundleRetro -Pattern "Default Trigger Thresholds" -Message "Bundled retro protocol includes trigger threshold table"
$results += Assert-FileContains -Path $mainRetro -Pattern "templates/cer-report.md.template" -Message "Main retro protocol references CER markdown template"
$results += Assert-FileContains -Path $bundleRetro -Pattern "templates/cer-report.md.template" -Message "Bundled retro protocol references CER markdown template"
$results += Assert-FileContains -Path $mainRetro -Pattern "vibe-retro-context-regression-matrix.ps1" -Message "Main retro protocol references retro regression script"
$results += Assert-FileContains -Path $bundleRetro -Pattern "vibe-retro-context-regression-matrix.ps1" -Message "Bundled retro protocol references retro regression script"
$results += Assert-FileContains -Path $mainRetro -Pattern "scripts/verify/cer-compare.ps1" -Message "Main retro protocol references CER compare script"
$results += Assert-FileContains -Path $bundleRetro -Pattern "scripts/verify/cer-compare.ps1" -Message "Bundled retro protocol references CER compare script"

$results += Assert-FileContains -Path $mainFallback -Pattern "Retro Context Expert Fallback" -Message "Main fallback chains include retro advisor fallback"
$results += Assert-FileContains -Path $bundleFallback -Pattern "Retro Context Expert Fallback" -Message "Bundled fallback chains include retro advisor fallback"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainDesignDoc) -Message "Context retro advisor design document exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainMdTemplate) -Message "CER markdown template exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainJsonTemplate) -Message "CER JSON template exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainJsonSchema) -Message "CER JSON schema exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $bundleMdTemplate) -Message "Bundled CER markdown template exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $bundleJsonTemplate) -Message "Bundled CER JSON template exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $bundleJsonSchema) -Message "Bundled CER JSON schema exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainRegressionScript) -Message "Retro regression matrix script exists"
$results += Assert-True -Condition (Test-Path -LiteralPath $mainCerCompareScript) -Message "CER compare script exists"

if (Test-Path -LiteralPath $mainCerCompareScript) {
    $smokeDir = Join-Path $repoRoot "outputs\retro\compare\smoke-temp"
    if (-not (Test-Path -LiteralPath $smokeDir)) {
        New-Item -ItemType Directory -Path $smokeDir -Force | Out-Null
    }

    $baselineCasePath = Join-Path $smokeDir "baseline-smoke.json"
    $currentCasePath = Join-Path $smokeDir "current-smoke.json"
    $deltaMdPath = Join-Path $smokeDir "delta-smoke.md"
    $deltaJsonPath = Join-Path $smokeDir "delta-smoke.json"

    @'
{
  "report_id": "CER-SMOKE-BASE",
  "trigger_signals": {
    "fallback_rate": 0.30,
    "context_pressure": 0.85,
    "route_stability_pack": 0.70,
    "route_stability_skill": 0.65,
    "top1_top2_gap": 0.02
  },
  "findings": [
    { "pattern": "CF-3" }
  ]
}
'@ | Set-Content -LiteralPath $baselineCasePath -Encoding UTF8

    @'
{
  "report_id": "CER-SMOKE-CURR",
  "trigger_signals": {
    "fallback_rate": 0.12,
    "context_pressure": 0.60,
    "route_stability_pack": 0.88,
    "route_stability_skill": 0.82,
    "top1_top2_gap": 0.09
  },
  "findings": [
    { "pattern": "CF-2" }
  ]
}
'@ | Set-Content -LiteralPath $currentCasePath -Encoding UTF8

    & $mainCerCompareScript `
        -BaselineCerPath $baselineCasePath `
        -CurrentCerPath $currentCasePath `
        -OutputMarkdownPath $deltaMdPath `
        -OutputJsonPath $deltaJsonPath `
        -UpdateCurrentComparison | Out-Null

    $results += Assert-True -Condition (Test-Path -LiteralPath $deltaMdPath) -Message "CER compare smoke writes markdown output"
    $results += Assert-True -Condition (Test-Path -LiteralPath $deltaJsonPath) -Message "CER compare smoke writes JSON output"

    if (Test-Path -LiteralPath $deltaJsonPath) {
        $deltaObj = Get-Content -LiteralPath $deltaJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $results += Assert-True -Condition ($deltaObj.status -in @("improved", "mixed", "degraded")) -Message "CER compare smoke emits valid status"
    }

    if (Test-Path -LiteralPath $currentCasePath) {
        $currentObj = Get-Content -LiteralPath $currentCasePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $hasComparison = ($null -ne $currentObj.comparison)
        $hasBaselineId = ($null -ne $currentObj.comparison.baseline_report_id) -and ([string]$currentObj.comparison.baseline_report_id -ne "")
        $patternDeltaCount = @($currentObj.comparison.pattern_delta).Count

        $results += Assert-True -Condition $hasComparison -Message "CER compare smoke updates current CER comparison block"
        $results += Assert-True -Condition $hasBaselineId -Message "CER compare smoke sets baseline_report_id"
        $results += Assert-True -Condition ($patternDeltaCount -eq 3) -Message "CER compare smoke writes 3 pattern_delta lines"
    }
}

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

Write-Host "Context retro advisor smoke checks passed."
exit 0
