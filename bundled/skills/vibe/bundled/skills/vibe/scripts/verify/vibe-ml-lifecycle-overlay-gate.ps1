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

function Set-MlLifecycleOverlayStage {
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

    # Force deterministic external-analyzer behavior for this gate.
    $policy.external_analyzer.enabled = $true
    $policy.external_analyzer.command = "definitely-missing-mlflow-cli"
    $policy.external_analyzer.invoke_mode = "manual_only"
    $policy.external_analyzer.run_in_modes = @("soft", "strict")
    $policy.external_analyzer.signal_score_min = 0.45
    $policy.thresholds.confirm_signal_score_min = 0.45
    $policy.thresholds.high_signal_score_min = 0.7
    $policy.thresholds.missing_artifact_ratio_for_confirm = 0.25
    $policy.strict_confirm_scope.grades = @("L", "XL")
    $policy.strict_confirm_scope.task_types = @("planning", "coding", "review")
    $policy.strict_confirm_scope.stages = @("evaluate", "deploy", "iterate")
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\ml-lifecycle-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$lifecyclePrompt = "machine learning deploy model to production service with canary rollout and drift monitoring, complete model evaluation and metrics check before release"

try {
    Write-Host "=== VCO ML Lifecycle Overlay Gate ==="

    Set-MlLifecycleOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $lifecyclePrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeShadow.ml_lifecycle_advice) -Message "[shadow] ml_lifecycle_advice exists"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable in data-ml coding"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.lifecycle_signal_score -ge 0.45) -Message "[shadow] lifecycle signal captured"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.stage_detected -eq "deploy") -Message "[shadow] deploy stage detected"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.confirm_recommended -eq $true) -Message "[shadow] confirm is recommended for deploy lifecycle risk"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"
    $results += Assert-True -Condition ($routeShadow.ml_lifecycle_advice.external_analyzer.status -eq "skipped_mode") -Message "[shadow] external analyzer skipped by mode"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-MlLifecycleOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $lifecyclePrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeSoft.ml_lifecycle_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.ml_lifecycle_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.ml_lifecycle_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.ml_lifecycle_advice.external_analyzer.status -eq "tool_unavailable") -Message "[soft] missing analyzer is reported as tool_unavailable"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-MlLifecycleOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $lifecyclePrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.ml_lifecycle_advice.enforcement -eq "confirm_required") -Message "[strict] lifecycle risk escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.ml_lifecycle_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.ml_lifecycle_advice.missing_artifacts.Count -gt 0) -Message "[strict] missing lifecycle artifacts detected"
    $results += Assert-True -Condition ($routeStrict.ml_lifecycle_advice.external_analyzer.status -eq "tool_unavailable") -Message "[strict] missing analyzer still degrades gracefully"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeOutsideScope = Invoke-Route -Prompt "debug null pointer in UI form component" -Grade "L" -TaskType "debug"
    $results += Assert-True -Condition ($routeOutsideScope.ml_lifecycle_advice.scope_applicable -eq $false) -Message "[strict] debug task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.ml_lifecycle_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-MlLifecycleOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $lifecyclePrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.ml_lifecycle_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored ml-lifecycle-overlay policy to original content."
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

Write-Host "ML lifecycle overlay gate passed."
exit 0
