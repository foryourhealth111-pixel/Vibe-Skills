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

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
    $confirmUiState = Join-Path (Join-Path $repoRoot "outputs\\runtime") "confirm-ui-state.json"
    if (Test-Path -LiteralPath $confirmUiState) {
        Remove-Item -LiteralPath $confirmUiState -Force -ErrorAction SilentlyContinue
    }

    $routeArgs = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if ($RequestedSkill) {
        $routeArgs["RequestedSkill"] = $RequestedSkill
    }

    $json = & $resolver @routeArgs
    return ($json | ConvertFrom-Json)
}

$cases = @(
    [pscustomobject]@{ Name = "orchestration planning EN"; Prompt = "create implementation plan and task breakdown with milestones"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "orchestration planning ZH"; Prompt = "请给我实施计划和任务拆解"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "code-quality review canonical"; Prompt = "run code review and security scan"; Grade = "M"; TaskType = "review"; RequestedSkill = "code-review"; ExpectedPack = "code-quality"; ExpectedSkill = "code-review"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "code-quality debug"; Prompt = "do root cause debugging for failing tests"; Grade = "M"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "code-quality"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "data-ml coding"; Prompt = "build machine learning model with scikit-learn feature engineering and training"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "data-ml"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "data-ml research ZH"; Prompt = "使用scikit-learn做分类训练并交叉验证"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "data-ml"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "bio-science research"; Prompt = "single-cell scRNA analysis with scanpy clustering and marker genes"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "bio-science"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "docs-media coding canonical"; Prompt = "process xlsx workbook and preserve formulas"; Grade = "M"; TaskType = "coding"; RequestedSkill = "xlsx"; ExpectedPack = "docs-media"; ExpectedSkill = "xlsx"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "docs-media research transcribe"; Prompt = "请把会议录音转文字并区分说话人"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "docs-media"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "integration-devops debug"; Prompt = "debug github actions ci failure and inspect sentry errors"; Grade = "L"; TaskType = "debug"; RequestedSkill = $null; ExpectedPack = "integration-devops"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "ai-llm research"; Prompt = "query OpenAI official docs for Responses API and model limits"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "ai-llm"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "research-design planning"; Prompt = "design quasi-experimental methodology with DiD and ITS"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },

    [pscustomobject]@{ Name = "aios-core planning"; Prompt = "create PRD and user story backlog with quality gate"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "aios-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },

    [pscustomobject]@{ Name = "low-signal fallback"; Prompt = "help me with this"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; AllowedModes = @("legacy_fallback", "confirm_required") },

    [pscustomobject]@{ Name = "docs-media blocked in XL"; Prompt = "xlsx and docx parallel processing"; Grade = "XL"; TaskType = "coding"; RequestedSkill = "xlsx"; ExpectedPack = $null; AllowedModes = @("legacy_fallback", "confirm_required"); BlockedPack = "docs-media" },

    [pscustomobject]@{ Name = "gap-driven confirm"; Prompt = "review code quality and perform security audit"; Grade = "M"; TaskType = "review"; RequestedSkill = $null; ExpectedPack = "code-quality"; AllowedModes = @("confirm_required") }
)

$results = @()

Write-Host "=== VCO Pack Regression Matrix ==="
foreach ($case in $cases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType -RequestedSkill $case.RequestedSkill

    $results += Assert-True -Condition ($case.AllowedModes -contains $route.route_mode) -Message "[$($case.Name)] route mode '$($route.route_mode)' is allowed"

    if ($case.ExpectedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -eq $case.ExpectedPack) -Message "[$($case.Name)] selected pack is $($case.ExpectedPack)"
    }

    if ($case.ExpectedSkill) {
        $results += Assert-True -Condition ($route.selected.skill -eq $case.ExpectedSkill) -Message "[$($case.Name)] selected skill is $($case.ExpectedSkill)"
    }

    if ($case.BlockedPack) {
        $results += Assert-True -Condition ($route.selected.pack_id -ne $case.BlockedPack) -Message "[$($case.Name)] blocked pack $($case.BlockedPack) not selected"
    }

    $results += Assert-True -Condition ($route.top1_top2_gap -ge 0) -Message "[$($case.Name)] top1_top2_gap is non-negative"

    if ($case.Name -eq "low-signal fallback") {
        if ($route.legacy_fallback_guard_applied) {
            $results += Assert-True -Condition ($route.route_mode -eq "confirm_required") -Message "[$($case.Name)] legacy fallback guard maps to confirm_required"
            $results += Assert-True -Condition ($route.legacy_fallback_original_reason -in @("confidence_below_fallback", "no_eligible_pack")) -Message "[$($case.Name)] legacy fallback original reason recorded"
        } else {
            $results += Assert-True -Condition ([double]$route.confidence -lt [double]$route.thresholds.fallback_to_legacy_below) -Message "[$($case.Name)] confidence below fallback threshold"
        }
    }
}

# Determinism check: same input, same output.
$detA = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-review"
$detB = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-review"
$results += Assert-True -Condition ($detA.selected.pack_id -eq $detB.selected.pack_id) -Message "[determinism] selected pack is stable"
$results += Assert-True -Condition ($detA.route_mode -eq $detB.route_mode) -Message "[determinism] route mode is stable"
$results += Assert-True -Condition ($detA.confidence -eq $detB.confidence) -Message "[determinism] confidence is stable"
$results += Assert-True -Condition ($detA.top1_top2_gap -eq $detB.top1_top2_gap) -Message "[determinism] top1_top2_gap is stable"

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

Write-Host "Pack regression matrix checks passed."
exit 0
