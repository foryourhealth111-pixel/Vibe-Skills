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

function Set-AiRerankStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("off", "shadow", "soft", "strict")]
        [string]$Stage,
        [bool]$PreserveRoutingAssignment
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

    $policy.preserve_routing_assignment = $PreserveRoutingAssignment
    $policy.scope.grade_allow = @("M", "L", "XL")
    $policy.scope.task_allow = @("planning", "coding", "review", "debug", "research")
    $policy.scope.route_mode_allow = @("legacy_fallback", "confirm_required", "pack_overlay")

    $policy.trigger.top_k = 10
    $policy.trigger.max_top1_top2_gap = 1.0
    $policy.trigger.max_confidence_for_rerank = 1.0
    $policy.trigger.confusion_groups = @(
        [pscustomobject]@{
            id = "gate-review"
            preferred_pack = "science-peer-review"
            keywords = @("code review", "代码评审", "quality checks")
        }
    )

    $policy.provider.type = "heuristic"
    $policy.provider.external_command = ""

    $policy.safety.require_candidate_in_top_k = $true
    $policy.safety.enforce_task_allow = $true
    $policy.safety.min_rerank_confidence = 0.0
    $policy.safety.allow_abstain = $true
    $policy.safety.fallback_on_error = $true

    $policy.rollout.apply_in_modes = @("soft", "strict")
    $policy.rollout.shadow_compare_in_shadow_mode = $true
    $policy.rollout.max_live_apply_rate = 1.0

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\ai-rerank-policy.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$prompt = "run code review and quality checks"

try {
    Write-Host "=== VCO AI Rerank Gate ==="

    Set-AiRerankStage -ConfigPath $policyPath -Stage "off" -PreserveRoutingAssignment $true
    $routeOffBaseline = Invoke-Route -Prompt $prompt -Grade "M" -TaskType "review" -RequestedSkill $null
    $results += Assert-True -Condition ($routeOffBaseline.ai_rerank_advice.enabled -eq $false) -Message "[off] ai rerank disabled"

    Set-AiRerankStage -ConfigPath $policyPath -Stage "shadow" -PreserveRoutingAssignment $true
    $routeShadow = Invoke-Route -Prompt $prompt -Grade "M" -TaskType "review" -RequestedSkill $null
    $results += Assert-True -Condition ($null -ne $routeShadow.ai_rerank_advice) -Message "[shadow] ai_rerank_advice exists"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_advice.enabled -eq $true) -Message "[shadow] ai rerank enabled"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_advice.mode -eq "shadow") -Message "[shadow] mode is shadow"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_advice.trigger.active -eq $true) -Message "[shadow] trigger active"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_advice.provider.suggested_pack -eq "science-peer-review") -Message "[shadow] heuristic suggestion prefers configured pack"
    $results += Assert-True -Condition ($routeShadow.ai_rerank_route_override -eq $false) -Message "[shadow] route override disabled"
    $results += Assert-True -Condition ($routeShadow.selected.pack_id -eq $routeOffBaseline.selected.pack_id) -Message "[shadow] selected pack unchanged"

    Set-AiRerankStage -ConfigPath $policyPath -Stage "soft" -PreserveRoutingAssignment $true
    $routeSoftPreserve = Invoke-Route -Prompt $prompt -Grade "M" -TaskType "review" -RequestedSkill $null
    $results += Assert-True -Condition ($routeSoftPreserve.ai_rerank_advice.mode -eq "soft") -Message "[soft/preserve] mode is soft"
    $results += Assert-True -Condition ($routeSoftPreserve.ai_rerank_advice.would_override -eq $true) -Message "[soft/preserve] would_override set"
    $results += Assert-True -Condition ($routeSoftPreserve.ai_rerank_route_override -eq $false) -Message "[soft/preserve] override blocked by preserve setting"
    $results += Assert-True -Condition ($routeSoftPreserve.selected.pack_id -eq $routeOffBaseline.selected.pack_id) -Message "[soft/preserve] selected pack unchanged"

    Set-AiRerankStage -ConfigPath $policyPath -Stage "soft" -PreserveRoutingAssignment $false
    $routeSoftApply = Invoke-Route -Prompt $prompt -Grade "M" -TaskType "review" -RequestedSkill $null
    $results += Assert-True -Condition ($routeSoftApply.ai_rerank_route_override -eq $true) -Message "[soft/apply] override applied"
    $results += Assert-True -Condition ($routeSoftApply.selected.pack_id -eq "science-peer-review") -Message "[soft/apply] selected pack switched to rerank target"
    $results += Assert-True -Condition ($routeSoftApply.selected.pack_id -eq $routeSoftApply.ai_rerank_advice.override_target_pack) -Message "[soft/apply] selected pack matches override target"

    Set-AiRerankStage -ConfigPath $policyPath -Stage "off" -PreserveRoutingAssignment $true
    $routeOff = Invoke-Route -Prompt $prompt -Grade "M" -TaskType "review" -RequestedSkill $null
    $results += Assert-True -Condition ($routeOff.ai_rerank_advice.enabled -eq $false) -Message "[off] advice disabled after stage reset"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored ai-rerank policy to original content."
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

Write-Host "AI rerank gate passed."
exit 0
