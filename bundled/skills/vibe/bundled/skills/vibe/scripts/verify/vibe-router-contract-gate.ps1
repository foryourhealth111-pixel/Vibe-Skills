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

function Get-SelectedRouteInfo {
    param([object]$Route)

    $selected = $null
    if ($Route -and ($Route.PSObject.Properties.Name -contains "selected")) {
        $selected = @($Route.selected)[0]
    }

    $packId = ""
    $skill = ""
    if ($selected) {
        if ($selected.PSObject.Properties.Name -contains "pack_id") {
            $packId = [string]$selected.pack_id
        }
        if ($selected.PSObject.Properties.Name -contains "skill") {
            $skill = [string]$selected.skill
        }
    }

    return [pscustomobject]@{
        pack_id = $packId
        skill = $skill
    }
}

function Test-LegacyFallbackGuardEquivalence {
    param(
        [object]$Legacy,
        [object]$Modular,
        [double]$Tolerance
    )

    $legacySelected = Get-SelectedRouteInfo -Route $Legacy
    $modularSelected = Get-SelectedRouteInfo -Route $Modular
    $legacyPack = $legacySelected.pack_id
    $modularPack = $modularSelected.pack_id
    $legacySkill = $legacySelected.skill
    $modularSkill = $modularSelected.skill
    $confirmThreshold = if ($Modular.thresholds -and ($Modular.thresholds.PSObject.Properties.Name -contains "confirm_required") -and ($Modular.thresholds.confirm_required -ne $null)) {
        [double]$Modular.thresholds.confirm_required
    } else {
        0.45
    }
    $guardEnabled = if ($Modular.thresholds -and ($Modular.thresholds.PSObject.Properties.Name -contains "enforce_confirm_on_legacy_fallback")) {
        [bool]$Modular.thresholds.enforce_confirm_on_legacy_fallback
    } else {
        $false
    }

    $equivalent =
        ([string]$Legacy.route_mode -eq "legacy_fallback") -and
        ([string]$Modular.route_mode -eq "confirm_required") -and
        ([string]$Modular.route_reason -eq "legacy_fallback_guard") -and
        ([bool]$Modular.legacy_fallback_guard_applied) -and
        ([string]$Modular.legacy_fallback_original_reason -eq [string]$Legacy.route_reason) -and
        $guardEnabled -and
        ($legacyPack -eq $modularPack) -and
        ($legacySkill -eq $modularSkill) -and
        (Compare-Float -Left ([double]$Legacy.top1_top2_gap) -Right ([double]$Modular.top1_top2_gap) -Tolerance $Tolerance) -and
        (Compare-Float -Left ([double]$Legacy.candidate_signal) -Right ([double]$Modular.candidate_signal) -Tolerance $Tolerance) -and
        ([double]$Legacy.confidence -lt $confirmThreshold) -and
        ([double]$Modular.confidence -ge $confirmThreshold)

    return [pscustomobject]@{
        equivalent = [bool]$equivalent
        reason = if ($equivalent) { "legacy_fallback_guard_equivalent" } else { $null }
        allowed_mismatches = if ($equivalent) { @("route_mode", "route_reason", "confidence") } else { @() }
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$modularScript = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
$legacyScript = Join-Path $repoRoot "scripts\router\legacy\resolve-pack-route.legacy.ps1"

$results = @()
$assertions = @()

$assertions += Assert-True -Condition (Test-Path -LiteralPath $modularScript) -Message "modular router script exists"
$assertions += Assert-True -Condition (Test-Path -LiteralPath $legacyScript) -Message "legacy router script exists"
$failedAssertions = @($assertions | Where-Object { -not $_ })
if ($failedAssertions.Count -gt 0) {
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

    $equivalence = Test-LegacyFallbackGuardEquivalence -Legacy $legacy -Modular $modular -Tolerance $FloatTolerance
    $mismatches = @()

    if ([string]$legacy.route_mode -ne [string]$modular.route_mode -and -not ($equivalence.allowed_mismatches -contains "route_mode")) { $mismatches += "route_mode" }
    if ([string]$legacy.route_reason -ne [string]$modular.route_reason -and -not ($equivalence.allowed_mismatches -contains "route_reason")) { $mismatches += "route_reason" }

    $legacySelected = Get-SelectedRouteInfo -Route $legacy
    $modularSelected = Get-SelectedRouteInfo -Route $modular
    $legacyPack = $legacySelected.pack_id
    $modularPack = $modularSelected.pack_id
    if ($legacyPack -ne $modularPack) { $mismatches += "selected.pack_id" }

    $legacySkill = $legacySelected.skill
    $modularSkill = $modularSelected.skill
    if ($legacySkill -ne $modularSkill) { $mismatches += "selected.skill" }

    if (-not (Compare-Float -Left ([double]$legacy.confidence) -Right ([double]$modular.confidence) -Tolerance $FloatTolerance) -and -not ($equivalence.allowed_mismatches -contains "confidence")) { $mismatches += "confidence" }
    if (-not (Compare-Float -Left ([double]$legacy.top1_top2_gap) -Right ([double]$modular.top1_top2_gap) -Tolerance $FloatTolerance)) { $mismatches += "top1_top2_gap" }
    if (-not (Compare-Float -Left ([double]$legacy.candidate_signal) -Right ([double]$modular.candidate_signal) -Tolerance $FloatTolerance)) { $mismatches += "candidate_signal" }

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
        contract_equivalent = [bool]$equivalence.equivalent
        equivalence_reason = $equivalence.reason
        mismatch_count = $mismatches.Count
        mismatches = @($mismatches)
    }
}

$total = $results.Count
$mismatchCases = @($results | Where-Object { $_.mismatch_count -gt 0 })
$equivalentCases = @($results | Where-Object { $_.contract_equivalent })
$passCount = $total - $mismatchCases.Count
$exactMatchCount = @($results | Where-Object { -not $_.contract_equivalent -and $_.mismatch_count -eq 0 }).Count
$strictEqualRate = if ($total -gt 0) { [double]$exactMatchCount / [double]$total } else { 1.0 }
$contractCompatibleRate = if ($total -gt 0) { [double]$passCount / [double]$total } else { 1.0 }
$gatePassed = ($mismatchCases.Count -eq 0)

Write-Host "=== VCO Router Contract Gate ==="
Write-Host ("Cases: {0}" -f $total)
Write-Host ("Exact-match cases: {0}" -f $exactMatchCount)
Write-Host ("Equivalent cases: {0}" -f $equivalentCases.Count)
Write-Host ("Strict equality rate: {0:N4}" -f $strictEqualRate)
Write-Host ("Contract-compatible rate: {0:N4}" -f $contractCompatibleRate)
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
        exact_match_cases = $exactMatchCount
        equivalent_cases = $equivalentCases.Count
        strict_equality_rate = [Math]::Round($strictEqualRate, 4)
        contract_compatible_rate = [Math]::Round($contractCompatibleRate, 4)
        incompatible_cases = $mismatchCases.Count
    }
    thresholds = [pscustomobject]@{
        contract_compatible_rate = 1.0
        incompatible_cases = 0
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
    $lines += "- contract_compatible_rate: ``$($report.metrics.contract_compatible_rate)``"
    $lines += "- equivalent_cases: ``$($report.metrics.equivalent_cases)``"
    $lines += "- incompatible_cases: ``$($report.metrics.incompatible_cases)``"
    $lines += ""
    $lines += "## Case Summary"
    $lines += ""
    foreach ($row in $results) {
        $suffix = if ($row.contract_equivalent) { ", equivalent=``true`` ($($row.equivalence_reason))" } else { "" }
        $lines += "- ``$($row.case_id)``: mismatch_count=``$($row.mismatch_count)``$suffix"
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
