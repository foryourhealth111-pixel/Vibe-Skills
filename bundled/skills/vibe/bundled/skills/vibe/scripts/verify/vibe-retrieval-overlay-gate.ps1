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

function Set-RetrievalOverlayStage {
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
    $policy.profile_selection.min_profile_confidence = 0.9
    $policy.profile_selection.ambiguous_gap = 0.2
    $policy.profile_selection.fallback_profile = "composite"
    $policy.profile_selection.max_query_variants_by_mode.shadow = 3
    $policy.profile_selection.max_query_variants_by_mode.soft = 4
    $policy.profile_selection.max_query_variants_by_mode.strict = 5
    $policy.coverage.min_sources_hit = 1
    $policy.coverage.min_evidence_items = 3
    $policy.coverage.max_retrieve_rounds = 2
    $policy.coverage.requery_on_low_coverage = $true
    $policy.enforcement.strict_confirm_on_low_coverage = $true
    $policy.enforcement.strict_confirm_on_ambiguous_profile = $true
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\retrieval-policy.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$literaturePrompt = "Search arxiv and pubmed papers, build citation-backed evidence summary, and compare benchmark studies."
$ambiguousPrompt = "Do end-to-end cross-domain work: research, plan, and implementation with mixed requirements."

try {
    Write-Host "=== VCO Retrieval Overlay Gate ==="

    Set-RetrievalOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $literaturePrompt -Grade "L" -TaskType "research"
    $results += Assert-True -Condition ($null -ne $routeShadow.retrieval_advice) -Message "[shadow] retrieval_advice exists"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.mode -eq "shadow") -Message "[shadow] mode is shadow"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.query_plan.max_query_variants -eq 3) -Message "[shadow] query variant budget applied"
    $results += Assert-True -Condition ($routeShadow.retrieval_advice.source_plan.source_count -ge 1) -Message "[shadow] source plan resolved"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-RetrievalOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $literaturePrompt -Grade "L" -TaskType "research"
    $results += Assert-True -Condition ($routeSoft.retrieval_advice.mode -eq "soft") -Message "[soft] mode is soft"
    $results += Assert-True -Condition ($routeSoft.retrieval_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.retrieval_advice.query_plan.max_query_variants -eq 4) -Message "[soft] query variant budget increased"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged"

    Set-RetrievalOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $ambiguousPrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeStrict.retrieval_advice.mode -eq "strict") -Message "[strict] mode is strict"
    $results += Assert-True -Condition ($routeStrict.retrieval_advice.profile_ambiguous -eq $true) -Message "[strict] ambiguous profile detected"
    $results += Assert-True -Condition ($routeStrict.retrieval_advice.confirm_required -eq $true) -Message "[strict] confirm_required set for ambiguity/coverage"
    $results += Assert-True -Condition ($routeStrict.retrieval_advice.enforcement -eq "confirm_required") -Message "[strict] enforcement escalates to confirm_required"
    $results += Assert-True -Condition ($routeStrict.retrieval_advice.query_plan.max_query_variants -eq 5) -Message "[strict] query variant budget increased"

    Set-RetrievalOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $literaturePrompt -Grade "L" -TaskType "research"
    $results += Assert-True -Condition ($routeOff.retrieval_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored retrieval-policy to original content."
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

Write-Host "Retrieval overlay gate passed."
exit 0

