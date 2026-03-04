param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory,
    [double]$FloatTolerance = 0.000001
)

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

function Invoke-RouteScript {
    param(
        [string]$ScriptPath,
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

    $args = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if ($RequestedSkill) {
        $args["RequestedSkill"] = $RequestedSkill
    }

    $json = & $ScriptPath @args
    return ($json | ConvertFrom-Json)
}

function Compare-Float {
    param(
        [double]$Left,
        [double]$Right,
        [double]$Tolerance
    )

    return ([Math]::Abs($Left - $Right) -le $Tolerance)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$modularScript = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
$legacyScript = Join-Path $repoRoot "scripts\router\legacy\resolve-pack-route.legacy.ps1"

$results = @()
$assertions = @()

$assertions += Assert-True -Condition (Test-Path -LiteralPath $modularScript) -Message "modular router script exists"
$assertions += Assert-True -Condition (Test-Path -LiteralPath $legacyScript) -Message "legacy router script exists"
if (($assertions | Where-Object { -not $_ }).Count -gt 0) {
    exit 1
}

$cases = @(
    [pscustomobject]@{ id = "planning-en"; prompt = "create implementation plan and task breakdown"; grade = "L"; task_type = "planning"; requested_skill = $null },
    [pscustomobject]@{ id = "planning-zh"; prompt = "请输出实施计划和任务拆解"; grade = "L"; task_type = "planning"; requested_skill = $null },
    [pscustomobject]@{ id = "review-en"; prompt = "run code review and quality checks"; grade = "M"; task_type = "review"; requested_skill = $null },
    [pscustomobject]@{ id = "review-zh"; prompt = "做一次代码评审和质量检查"; grade = "M"; task_type = "review"; requested_skill = $null },
    [pscustomobject]@{ id = "debug-ci"; prompt = "debug github actions ci pipeline failure"; grade = "L"; task_type = "debug"; requested_skill = $null },
    [pscustomobject]@{ id = "research-openai"; prompt = "look up OpenAI Responses API docs"; grade = "M"; task_type = "research"; requested_skill = $null },
    [pscustomobject]@{ id = "data-ml"; prompt = "train classification model with scikit-learn and evaluate metrics"; grade = "L"; task_type = "research"; requested_skill = $null },
    [pscustomobject]@{ id = "docs-media"; prompt = "edit xlsx workbook and preserve formulas"; grade = "M"; task_type = "coding"; requested_skill = $null },
    [pscustomobject]@{ id = "low-signal"; prompt = "help me with this"; grade = "M"; task_type = "research"; requested_skill = $null },
    [pscustomobject]@{ id = "explicit-requested-skill"; prompt = "please help with roadmap"; grade = "L"; task_type = "planning"; requested_skill = "writing-plans" }
)

foreach ($case in $cases) {
    $legacy = Invoke-RouteScript -ScriptPath $legacyScript -Prompt $case.prompt -Grade $case.grade -TaskType $case.task_type -RequestedSkill $case.requested_skill
    $modular = Invoke-RouteScript -ScriptPath $modularScript -Prompt $case.prompt -Grade $case.grade -TaskType $case.task_type -RequestedSkill $case.requested_skill

    $mismatches = @()

    if ([string]$legacy.route_mode -ne [string]$modular.route_mode) { $mismatches += "route_mode" }
    if ([string]$legacy.route_reason -ne [string]$modular.route_reason) { $mismatches += "route_reason" }

    $legacyPack = if ($legacy.selected) { [string]$legacy.selected.pack_id } else { "" }
    $modularPack = if ($modular.selected) { [string]$modular.selected.pack_id } else { "" }
    if ($legacyPack -ne $modularPack) { $mismatches += "selected.pack_id" }

    $legacySkill = if ($legacy.selected) { [string]$legacy.selected.skill } else { "" }
    $modularSkill = if ($modular.selected) { [string]$modular.selected.skill } else { "" }
    if ($legacySkill -ne $modularSkill) { $mismatches += "selected.skill" }

    if (-not (Compare-Float -Left ([double]$legacy.confidence) -Right ([double]$modular.confidence) -Tolerance $FloatTolerance)) { $mismatches += "confidence" }
    if (-not (Compare-Float -Left ([double]$legacy.top1_top2_gap) -Right ([double]$modular.top1_top2_gap) -Tolerance $FloatTolerance)) { $mismatches += "top1_top2_gap" }
    if (-not (Compare-Float -Left ([double]$legacy.candidate_signal) -Right ([double]$modular.candidate_signal) -Tolerance $FloatTolerance)) { $mismatches += "candidate_signal" }

    $legacyCanonical = ($legacy | ConvertTo-Json -Depth 30 -Compress)
    $modularCanonical = ($modular | ConvertTo-Json -Depth 30 -Compress)
    $fullEqual = ($legacyCanonical -eq $modularCanonical)
    if (-not $fullEqual) { $mismatches += "full_json" }

    $results += [pscustomobject]@{
        case_id = $case.id
        grade = $case.grade
        task_type = $case.task_type
        route_mode_legacy = [string]$legacy.route_mode
        route_mode_modular = [string]$modular.route_mode
        selected_pack_legacy = $legacyPack
        selected_pack_modular = $modularPack
        selected_skill_legacy = $legacySkill
        selected_skill_modular = $modularSkill
        full_json_equal = $fullEqual
        mismatch_count = $mismatches.Count
        mismatches = @($mismatches)
    }
}

$total = $results.Count
$mismatchCases = @($results | Where-Object { $_.mismatch_count -gt 0 })
$passCount = $total - $mismatchCases.Count
$strictEqualRate = if ($total -gt 0) { [double]$passCount / [double]$total } else { 1.0 }
$gatePassed = ($mismatchCases.Count -eq 0)

Write-Host "=== VCO Router Contract Gate ==="
Write-Host ("Cases: {0}" -f $total)
Write-Host ("Exact-match cases: {0}" -f $passCount)
Write-Host ("Strict equality rate: {0:N4}" -f $strictEqualRate)
Write-Host ("Gate Result: {0}" -f $(if ($gatePassed) { "PASS" } else { "FAIL" }))

if ($mismatchCases.Count -gt 0) {
    Write-Host ""
    Write-Host "Mismatched cases:" -ForegroundColor Yellow
    foreach ($row in $mismatchCases) {
        Write-Host ("- {0}: {1}" -f $row.case_id, ($row.mismatches -join ", ")) -ForegroundColor Yellow
    }
}

$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    float_tolerance = $FloatTolerance
    metrics = [pscustomobject]@{
        total_cases = $total
        exact_match_cases = $passCount
        strict_equality_rate = [Math]::Round($strictEqualRate, 4)
        mismatch_cases = $mismatchCases.Count
    }
    thresholds = [pscustomobject]@{
        strict_equality_rate = 1.0
        mismatch_cases = 0
    }
    gate_passed = $gatePassed
    results = $results
}

if ($WriteArtifacts) {
    if (-not $OutputDirectory) {
        $OutputDirectory = Join-Path $repoRoot "outputs/verify"
    }
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

    $jsonPath = Join-Path $OutputDirectory "vibe-router-contract-gate.json"
    $mdPath = Join-Path $OutputDirectory "vibe-router-contract-gate.md"

    $report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = @()
    $lines += "# VCO Router Contract Gate"
    $lines += ""
    $lines += "- generated_at: ``$($report.generated_at)``"
    $lines += "- gate_passed: ``$($report.gate_passed)``"
    $lines += "- strict_equality_rate: ``$($report.metrics.strict_equality_rate)``"
    $lines += "- mismatch_cases: ``$($report.metrics.mismatch_cases)``"
    $lines += ""
    $lines += "## Case Summary"
    $lines += ""
    foreach ($row in $results) {
        $lines += "- ``$($row.case_id)``: mismatch_count=``$($row.mismatch_count)``"
    }

    $lines -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

    Write-Host ""
    Write-Host "Artifacts written:"
    Write-Host "- $jsonPath"
    Write-Host "- $mdPath"
}

if (-not $gatePassed) {
    exit 1
}

exit 0
