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

function Set-FrameworkInteropOverlayStage {
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
    $policy.external_analyzer.command = "definitely-missing-ivy-cli"
    $policy.external_analyzer.invoke_mode = "manual_only"
    $policy.external_analyzer.run_in_modes = @("soft", "strict")
    $policy.external_analyzer.interop_score_min = 0.4
    $policy.thresholds.confirm_interop_score_min = 0.4
    $policy.thresholds.high_interop_score_min = 0.7
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\framework-interop-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$interopPrompt = "machine learning model migration from pytorch to tensorflow with ivy transpile and trace_graph parity checks"

try {
    Write-Host "=== VCO Framework Interop Overlay Gate ==="

    Set-FrameworkInteropOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $interopPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeShadow.framework_interop_advice) -Message "[shadow] framework_interop_advice exists"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable in data-ml coding"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.interop_signal_score -ge 0.4) -Message "[shadow] interop signal captured"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.framework_pair_detected -eq $true) -Message "[shadow] framework pair detected"
    $results += Assert-True -Condition (@($routeShadow.framework_interop_advice.frameworks_matched) -contains "pytorch") -Message "[shadow] source framework detected"
    $results += Assert-True -Condition (@($routeShadow.framework_interop_advice.frameworks_matched) -contains "tensorflow") -Message "[shadow] target framework detected"
    $results += Assert-True -Condition ($routeShadow.framework_interop_advice.external_analyzer.status -eq "skipped_mode") -Message "[shadow] external analyzer skipped by mode"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-FrameworkInteropOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $interopPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeSoft.framework_interop_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.framework_interop_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.framework_interop_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.framework_interop_advice.external_analyzer.status -eq "tool_unavailable") -Message "[soft] missing analyzer is reported as tool_unavailable"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-FrameworkInteropOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $interopPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.framework_interop_advice.enforcement -eq "confirm_required") -Message "[strict] strong interop signal escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.framework_interop_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.framework_interop_advice.external_analyzer.status -eq "tool_unavailable") -Message "[strict] missing analyzer still degrades gracefully"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeOutsideScope = Invoke-Route -Prompt "create architecture planning milestone document" -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeOutsideScope.framework_interop_advice.scope_applicable -eq $false) -Message "[strict] planning task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.framework_interop_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-FrameworkInteropOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $interopPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.framework_interop_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored framework-interop-overlay policy to original content."
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

Write-Host "Framework interop overlay gate passed."
exit 0
