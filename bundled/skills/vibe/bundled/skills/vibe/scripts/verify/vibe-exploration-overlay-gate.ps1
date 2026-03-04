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

function Set-ExplorationOverlayStage {
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

    # Force deterministic gate behavior.
    $policy.preserve_routing_assignment = $true
    $policy.route_mode_allow = @("legacy_fallback", "confirm_required", "pack_overlay")
    $policy.task_allow = @("planning", "coding", "review", "debug", "research")
    $policy.grade_allow = @("M", "L", "XL")

    if ($Stage -eq "shadow") {
        $policy.intent_selection.min_intent_confidence = 0.18
        $policy.intent_selection.ambiguous_gap = 0.05
    } else {
        $policy.intent_selection.min_intent_confidence = 0.85
        $policy.intent_selection.ambiguous_gap = 0.30
    }

    $policy.intent_selection.fallback_intent = "execute"
    $policy.intent_selection.max_hypotheses_by_mode.shadow = 2
    $policy.intent_selection.max_hypotheses_by_mode.soft = 3
    $policy.intent_selection.max_hypotheses_by_mode.strict = 4

    $policy.domain_detection.min_domain_confidence = 0.08
    $policy.domain_detection.multi_domain_gap = 0.20
    $policy.domain_detection.max_domains = 3

    $policy.interview.soft_confirm_on_ambiguous_intent = $true
    $policy.interview.soft_confirm_on_multidomain = $true
    $policy.interview.strict_confirm_on_ambiguous_intent = $true
    $policy.interview.strict_confirm_on_multidomain = $true

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\exploration-policy.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$mixedPrompt = "end-to-end design and implementation for gene dataset and machine learning model evaluation with cross-domain explanation"

try {
    Write-Host "=== VCO Exploration Overlay Gate ==="

    Set-ExplorationOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $mixedPrompt -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeShadow.exploration_advice) -Message "[shadow] exploration_advice exists"
    $results += Assert-True -Condition ($routeShadow.exploration_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.exploration_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable"
    $results += Assert-True -Condition ($routeShadow.exploration_advice.mode -eq "shadow") -Message "[shadow] mode is shadow"
    $results += Assert-True -Condition ($routeShadow.exploration_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"
    $results += Assert-True -Condition ($routeShadow.exploration_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"
    $results += Assert-True -Condition ([string]$routeShadow.exploration_advice.intent_id -ne "none") -Message "[shadow] intent is resolved"
    $results += Assert-True -Condition ([string]$routeShadow.exploration_advice.recommended_execution_mode -ne "") -Message "[shadow] execution mode is suggested"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-ExplorationOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $mixedPrompt -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeSoft.exploration_advice.mode -eq "soft") -Message "[soft] mode is soft"
    $results += Assert-True -Condition ($routeSoft.exploration_advice.intent_ambiguous -eq $true) -Message "[soft] ambiguous intent detected"
    $results += Assert-True -Condition ($routeSoft.exploration_advice.confirm_recommended -eq $true) -Message "[soft] confirm is recommended"
    $results += Assert-True -Condition ($routeSoft.exploration_advice.confirm_required -eq $false) -Message "[soft] confirm is not forced"
    $results += Assert-True -Condition ($routeSoft.exploration_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged"

    Set-ExplorationOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $mixedPrompt -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.exploration_advice.mode -eq "strict") -Message "[strict] mode is strict"
    $results += Assert-True -Condition ($routeStrict.exploration_advice.intent_ambiguous -eq $true) -Message "[strict] ambiguous intent detected"
    $results += Assert-True -Condition ($routeStrict.exploration_advice.confirm_required -eq $true) -Message "[strict] confirm_required set for ambiguity/multi-domain"
    $results += Assert-True -Condition ($routeStrict.exploration_advice.enforcement -eq "confirm_required") -Message "[strict] enforcement escalates to confirm_required"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode remains unchanged (advice-only)"

    Set-ExplorationOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $mixedPrompt -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.exploration_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored exploration-policy to original content."
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

Write-Host "Exploration overlay gate passed."
exit 0
