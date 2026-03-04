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

function Set-PythonCleanCodeOverlayStage {
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
    $policy.thresholds.trigger_signal_score_min = 0.4
    $policy.thresholds.confirm_signal_score_min = 0.5
    $policy.thresholds.high_signal_score_min = 0.7
    $policy.thresholds.min_anti_pattern_hits_for_confirm = 1
    $policy.strict_confirm_scope.grades = @("L", "XL")
    $policy.strict_confirm_scope.task_types = @("coding", "review")
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\python-clean-code-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$pythonPrompt = "Refactor src/services/user_service.py: split long function, remove boolean parameter, reduce side effects and duplicate logic with better naming."

try {
    Write-Host "=== VCO Python Clean Code Overlay Gate ==="

    Set-PythonCleanCodeOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $pythonPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeShadow.python_clean_code_advice) -Message "[shadow] python_clean_code_advice exists"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable for coding"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.python_file_signal -eq $true) -Message "[shadow] python file signal detected"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.python_signal_score -ge 0.4) -Message "[shadow] python signal score captured"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.confirm_recommended -eq $true) -Message "[shadow] confirm is recommended"
    $results += Assert-True -Condition ($routeShadow.python_clean_code_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-PythonCleanCodeOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $pythonPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeSoft.python_clean_code_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.python_clean_code_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.python_clean_code_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-PythonCleanCodeOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $pythonPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.python_clean_code_advice.enforcement -eq "confirm_required") -Message "[strict] python anti-pattern risk escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.python_clean_code_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeNonPython = Invoke-Route -Prompt "Implement src/ui/form.ts and styles.css only for web ui alignment" -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeNonPython.python_clean_code_advice.python_file_signal -eq $false) -Message "[strict] non-python coding request does not set python file signal"
    $results += Assert-True -Condition ($routeNonPython.python_clean_code_advice.trigger_active -eq $false) -Message "[strict] non-python coding request does not activate clean-code advice"

    $routeOutsideScope = Invoke-Route -Prompt "Design architecture for service boundaries and milestones" -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeOutsideScope.python_clean_code_advice.scope_applicable -eq $false) -Message "[strict] planning task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.python_clean_code_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-PythonCleanCodeOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $pythonPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.python_clean_code_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored python-clean-code-overlay policy to original content."
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

Write-Host "Python clean-code overlay gate passed."
exit 0
