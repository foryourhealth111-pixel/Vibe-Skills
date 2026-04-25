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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$modularScript = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
$goldenFixture = Join-Path $repoRoot "tests\replay\route\router-contract-gate-golden.json"

$results = @()
$assertions = @()

$assertions += Assert-True -Condition (Test-Path -LiteralPath $modularScript) -Message "modular router script exists"
$assertions += Assert-True -Condition (Test-Path -LiteralPath $goldenFixture) -Message "router contract golden fixture exists"
$failedAssertions = @($assertions | Where-Object { -not $_ })
if ($failedAssertions.Count -gt 0) {
    exit 1
}

$fixture = Get-Content -LiteralPath $goldenFixture -Raw -Encoding UTF8 | ConvertFrom-Json
$cases = @($fixture.cases)

foreach ($case in $cases) {
    $modular = Invoke-RouteScript -ScriptPath $modularScript -Prompt $case.prompt -Grade $case.grade -TaskType $case.task_type -RequestedSkill $case.requested_skill
    $expected = $case.expected
    $mismatches = @()

    if ([string]$expected.route_mode -ne [string]$modular.route_mode) { $mismatches += "route_mode" }
    if ([string]$expected.route_reason -ne [string]$modular.route_reason) { $mismatches += "route_reason" }

    $modularSelected = Get-SelectedRouteInfo -Route $modular
    if ([string]$expected.selected_pack -ne $modularSelected.pack_id) { $mismatches += "selected.pack_id" }
    if ([string]$expected.selected_skill -ne $modularSelected.skill) { $mismatches += "selected.skill" }

    if (-not (Compare-Float -Left ([double]$expected.confidence) -Right ([double]$modular.confidence) -Tolerance $FloatTolerance)) { $mismatches += "confidence" }
    if (-not (Compare-Float -Left ([double]$expected.top1_top2_gap) -Right ([double]$modular.top1_top2_gap) -Tolerance $FloatTolerance)) { $mismatches += "top1_top2_gap" }
    if (-not (Compare-Float -Left ([double]$expected.candidate_signal) -Right ([double]$modular.candidate_signal) -Tolerance $FloatTolerance)) { $mismatches += "candidate_signal" }

    $results += [pscustomobject]@{
        case_id = [string]$case.id
        grade = [string]$case.grade
        task_type = [string]$case.task_type
        route_mode_expected = [string]$expected.route_mode
        route_mode_modular = [string]$modular.route_mode
        selected_pack_expected = [string]$expected.selected_pack
        selected_pack_modular = $modularSelected.pack_id
        selected_skill_expected = [string]$expected.selected_skill
        selected_skill_modular = $modularSelected.skill
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

$goldenFixtureRelative = try {
    [System.IO.Path]::GetRelativePath([string]$repoRoot, [string]$goldenFixture)
} catch {
    $repoRootPrefix = ([string]$repoRoot).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if ([string]$goldenFixture -like "$repoRootPrefix*") {
        [string]$goldenFixture.Substring($repoRootPrefix.Length)
    } else {
        [string]$goldenFixture
    }
}

$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    golden_fixture = $goldenFixtureRelative
    float_tolerance = $FloatTolerance
    metrics = [pscustomobject]@{
        total_cases = $total
        exact_match_cases = $passCount
        strict_equality_rate = [Math]::Round($strictEqualRate, 4)
        incompatible_cases = $mismatchCases.Count
    }
    thresholds = [pscustomobject]@{
        strict_equality_rate = 1.0
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
    $lines += "- golden_fixture: ``$($report.golden_fixture)``"
    $lines += "- gate_passed: ``$($report.gate_passed)``"
    $lines += "- strict_equality_rate: ``$($report.metrics.strict_equality_rate)``"
    $lines += "- incompatible_cases: ``$($report.metrics.incompatible_cases)``"
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
