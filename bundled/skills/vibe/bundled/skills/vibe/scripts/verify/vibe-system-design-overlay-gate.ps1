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
        [string]$TaskType
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
    $json = & $resolver -Prompt $Prompt -Grade $Grade -TaskType $TaskType
    return ($json | ConvertFrom-Json)
}

function Set-SystemDesignOverlayStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("off", "shadow", "soft", "strict")]
        [string]$Stage
    )

    $policy = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

    switch ($Stage) {
        "off" {
            $policy.enabled = $false
            $policy.mode = "off"
        }
        "shadow" {
            $policy.enabled = $true
            $policy.mode = "shadow"
        }
        "soft" {
            $policy.enabled = $true
            $policy.mode = "soft"
        }
        "strict" {
            $policy.enabled = $true
            $policy.mode = "strict"
        }
    }

    # Force deterministic thresholds for this gate.
    $policy.thresholds.trigger_signal_score_min = 0.35
    $policy.thresholds.confirm_signal_score_min = 0.45
    $policy.thresholds.high_signal_score_min = 0.7
    $policy.thresholds.suppress_penalty_weight = 0.2
    $policy.thresholds.min_dimension_hits_for_overlay = 2
    $policy.thresholds.min_coverage_score_for_ready = 0.7
    $policy.thresholds.min_coverage_score_for_strict_confirm = 0.92
    $policy.strict_confirm_scope.grades = @("L", "XL")
    $policy.strict_confirm_scope.task_types = @("planning", "review")
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\system-design-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$architecturePrompt = "Design an order platform architecture with 20000 rps, p95 latency < 150ms, consistency tradeoffs, caching, sharding, replication, async queue retry, failover, and observability alerts."

try {
    Write-Host "=== VCO System Design Overlay Gate ==="

    Set-SystemDesignOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $architecturePrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($null -ne $routeShadow.system_design_advice) -Message "[shadow] system_design_advice exists"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable for planning"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.trigger_active -eq $true) -Message "[shadow] architecture trigger active"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.architecture_signal_score -ge 0.35) -Message "[shadow] architecture signal score captured"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.confirm_recommended -eq $true) -Message "[shadow] confirm is recommended"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"
    $results += Assert-True -Condition ($routeShadow.system_design_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-SystemDesignOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $architecturePrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeSoft.system_design_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.system_design_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.system_design_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-SystemDesignOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $architecturePrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeStrict.system_design_advice.enforcement -eq "confirm_required") -Message "[strict] architecture risk escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.system_design_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.system_design_advice.strict_scope_applied -eq $true) -Message "[strict] strict scope applied"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeOutsideScope = Invoke-Route -Prompt "Implement user login endpoint and add unit tests" -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOutsideScope.system_design_advice.scope_applicable -eq $false) -Message "[strict] coding task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.system_design_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-SystemDesignOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $architecturePrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeOff.system_design_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored system-design-overlay policy to original content."
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

Write-Host "System design overlay gate passed."
exit 0
