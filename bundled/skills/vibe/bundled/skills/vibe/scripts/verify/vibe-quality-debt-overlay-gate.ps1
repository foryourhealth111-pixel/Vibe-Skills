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

function Set-QualityDebtOverlayStage {
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
    $policy.external_analyzer.command = "definitely-missing-quality-debt-cli"
    $policy.external_analyzer.invoke_mode = "manual_only"
    $policy.external_analyzer.run_in_modes = @("soft", "strict")
    $policy.external_analyzer.risk_score_min = 0.4
    $policy.thresholds.confirm_risk_score_min = 0.4
    $policy.thresholds.high_risk_score_min = 0.7
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\quality-debt-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$highRiskPrompt = "code review lint test debug fix maintainability complexity technical debt duplicate logic security risk"

try {
    Write-Host "=== VCO Quality Debt Overlay Gate ==="

    Set-QualityDebtOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $highRiskPrompt -Grade "L" -TaskType "review"
    $results += Assert-True -Condition ($null -ne $routeShadow.quality_debt_advice) -Message "[shadow] quality_debt_advice exists"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable in code-quality review"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.risk_signal_score -ge 0.4) -Message "[shadow] risk score captured"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.confirm_recommended -eq $true) -Message "[shadow] confirm is recommended for high risk"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.confirm_required -eq $false) -Message "[shadow] confirm not forced"
    $results += Assert-True -Condition ($routeShadow.quality_debt_advice.external_analyzer.status -eq "skipped_mode") -Message "[shadow] external analyzer skipped by mode"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-QualityDebtOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $highRiskPrompt -Grade "L" -TaskType "review"
    $results += Assert-True -Condition ($routeSoft.quality_debt_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.quality_debt_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.quality_debt_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.quality_debt_advice.external_analyzer.status -eq "tool_unavailable") -Message "[soft] missing analyzer is reported as tool_unavailable"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-QualityDebtOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $highRiskPrompt -Grade "L" -TaskType "review"
    $results += Assert-True -Condition ($routeStrict.quality_debt_advice.enforcement -eq "confirm_required") -Message "[strict] high risk escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.quality_debt_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.quality_debt_advice.external_analyzer.status -eq "tool_unavailable") -Message "[strict] missing analyzer still degrades gracefully"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeOutsideScope = Invoke-Route -Prompt "create architecture planning milestone document" -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeOutsideScope.quality_debt_advice.scope_applicable -eq $false) -Message "[strict] planning task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.quality_debt_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-QualityDebtOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $highRiskPrompt -Grade "L" -TaskType "review"
    $results += Assert-True -Condition ($routeOff.quality_debt_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored quality-debt-overlay policy to original content."
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

Write-Host "Quality debt overlay gate passed."
exit 0
