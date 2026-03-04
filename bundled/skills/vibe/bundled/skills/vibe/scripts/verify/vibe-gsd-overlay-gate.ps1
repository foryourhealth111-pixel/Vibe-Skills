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

function Set-OverlayStage {
    param([string]$Stage)
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $scriptPath = Join-Path $repoRoot "scripts\governance\set-gsd-overlay-rollout.ps1"
    $null = & $scriptPath -Stage $Stage -MainOnly
}

function Get-CurrentOverlayStage {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $policyPath = Join-Path $repoRoot "config\gsd-overlay.json"
    $policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json

    if (($policy.enabled -eq $false) -or ($policy.mode -eq "off")) {
        return "off"
    }

    switch ([string]$policy.mode) {
        "shadow" { return "shadow" }
        "soft" { return "soft-lxl-planning" }
        "strict" { return "strict-lxl-planning" }
        default { return "shadow" }
    }
}

$originalStage = Get-CurrentOverlayStage
$results = @()

try {
    Write-Host "=== VCO GSD Overlay Gate ==="
    Write-Host ("Original stage: {0}" -f $originalStage)

    Set-OverlayStage -Stage "soft-lxl-planning"

    $routeLPlanning = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeLPlanning.selected.pack_id -eq "orchestration-core") -Message "[soft] routing unchanged for L planning"
    $results += Assert-True -Condition ($null -ne $routeLPlanning.gsd_overlay_advice) -Message "[soft] gsd_overlay_advice exists"
    $results += Assert-True -Condition ($routeLPlanning.gsd_overlay_advice.enabled -eq $true) -Message "[soft] overlay enabled"
    $results += Assert-True -Condition ($routeLPlanning.gsd_overlay_advice.scope_applicable -eq $true) -Message "[soft] scope applicable for L planning"
    $results += Assert-True -Condition ($routeLPlanning.gsd_overlay_advice.preflight_should_apply -eq $true) -Message "[soft] preflight hook applies for L planning"
    $results += Assert-True -Condition ($routeLPlanning.gsd_overlay_advice.enforcement -eq "advisory") -Message "[soft] L planning enforcement is advisory"

    $routeXLPlanning = Invoke-Route -Prompt "plan a multi-agent refactor for data layer and integration boundaries" -Grade "XL" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeXLPlanning.gsd_overlay_advice.scope_applicable -eq $true) -Message "[soft] scope applicable for XL planning"
    $results += Assert-True -Condition ($routeXLPlanning.gsd_overlay_advice.wave_contract_should_apply -eq $true) -Message "[soft] wave contract hook applies for XL planning"
    $results += Assert-True -Condition ($routeXLPlanning.gsd_overlay_advice.enforcement -eq "confirm_required") -Message "[soft] XL planning enforcement is confirm_required"

    $routeMPlanning = Invoke-Route -Prompt "small module implementation plan without architecture change" -Grade "M" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeMPlanning.gsd_overlay_advice.scope_applicable -eq $false) -Message "[soft] M planning outside overlay scope"
    $results += Assert-True -Condition ($routeMPlanning.gsd_overlay_advice.should_apply_hook -eq $false) -Message "[soft] no hook for M planning"

    $routeLResearch = Invoke-Route -Prompt "investigate release notes and summarize findings" -Grade "L" -TaskType "research" -RequestedSkill $null
    $results += Assert-True -Condition ($routeLResearch.gsd_overlay_advice.scope_applicable -eq $false) -Message "[soft] L research outside overlay scope"
    $results += Assert-True -Condition ($routeLResearch.gsd_overlay_advice.enforcement -eq "none") -Message "[soft] non-planning enforcement is none"

    Set-OverlayStage -Stage "strict-lxl-planning"
    $routeLPlanningStrict = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeLPlanningStrict.gsd_overlay_advice.enforcement -eq "required") -Message "[strict] L planning enforcement is required"

    Set-OverlayStage -Stage "off"
    $routeOff = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "XL" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeOff.gsd_overlay_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.gsd_overlay_advice.should_apply_hook -eq $false) -Message "[off] hooks are not applied"

} finally {
    Set-OverlayStage -Stage $originalStage
    Write-Host ("Restored stage: {0}" -f $originalStage)
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

Write-Host "GSD overlay gate passed."
exit 0
