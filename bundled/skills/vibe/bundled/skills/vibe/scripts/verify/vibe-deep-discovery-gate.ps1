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

function Set-DeepDiscoveryStage {
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
            $policy.preserve_routing_assignment = $true
        }
        "shadow" {
            $policy.enabled = $true
            $policy.mode = "shadow"
            $policy.preserve_routing_assignment = $true
        }
        "soft" {
            $policy.enabled = $true
            $policy.mode = "soft"
            $policy.preserve_routing_assignment = $true
        }
        "strict" {
            $policy.enabled = $true
            $policy.mode = "strict"
            $policy.preserve_routing_assignment = $false
        }
    }

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\deep-discovery-policy.json"
$catalogPath = Join-Path $repoRoot "config\capability-catalog.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$ambiguousPrompt = "请你把这个复合任务端到端搞定：先做方案，再抓取生物数据，然后训练模型，最后给我结果。"
$specificPrompt = "请设计并实现一个可复现流程：先从UniProt抓取蛋白序列，使用scikit-learn训练分类模型，输出Python脚本、评估报告和验证步骤，并包含测试门禁。"

try {
    Write-Host "=== VCO Deep Discovery Gate ==="

    $results += Assert-True -Condition (Test-Path -LiteralPath $policyPath) -Message "deep-discovery-policy config exists"
    $results += Assert-True -Condition (Test-Path -LiteralPath $catalogPath) -Message "capability-catalog config exists"

    Set-DeepDiscoveryStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $ambiguousPrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($null -ne $routeShadow.deep_discovery_advice) -Message "[shadow] deep_discovery_advice exists"
    $results += Assert-True -Condition ($routeShadow.deep_discovery_advice.enabled -eq $true) -Message "[shadow] deep discovery enabled"
    $results += Assert-True -Condition ($routeShadow.deep_discovery_advice.trigger_active -eq $true) -Message "[shadow] trigger active on composite ambiguous prompt"
    $results += Assert-True -Condition ($routeShadow.deep_discovery_advice.interview_required -eq $true) -Message "[shadow] interview required signal emitted"
    $results += Assert-True -Condition ($routeShadow.deep_discovery_advice.confirm_required -eq $false) -Message "[shadow] confirm not forced"
    $results += Assert-True -Condition ($routeShadow.deep_discovery_route_filter_applied -eq $false) -Message "[shadow] route filter not applied"
    $shadowPack = if ($routeShadow.selected) { [string]$routeShadow.selected.pack_id } else { "none" }
    $shadowSkill = if ($routeShadow.selected) { [string]$routeShadow.selected.skill } else { "none" }

    Set-DeepDiscoveryStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $ambiguousPrompt -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeSoft.deep_discovery_advice.confirm_required -eq $true) -Message "[soft] deep discovery marks confirm_required"
    $results += Assert-True -Condition ($routeSoft.deep_discovery_route_mode_override -eq $false) -Message "[soft] preserve routing assignment keeps route_mode unchanged"
    $results += Assert-True -Condition ($routeSoft.deep_discovery_route_filter_applied -eq $false) -Message "[soft] preserve routing assignment keeps filter non-mutating"
    $results += Assert-True -Condition (($routeSoft.selected.pack_id -eq $shadowPack) -or ($routeSoft.route_mode -eq "confirm_required")) -Message "[soft] route remains stable under confirm gate"

    Set-DeepDiscoveryStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $specificPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.deep_discovery_advice.trigger_active -eq $true) -Message "[strict] trigger active for specific composite task"
    $results += Assert-True -Condition ($routeStrict.intent_contract.completeness -ge 0.6) -Message "[strict] intent contract completeness reaches filter threshold"
    $results += Assert-True -Condition ($routeStrict.deep_discovery_filter.would_apply_filter -eq $true) -Message "[strict] filter marked applicable"
    $results += Assert-True -Condition ($routeStrict.deep_discovery_route_filter_applied -eq $true) -Message "[strict] candidate filter applied to routing"
    $results += Assert-True -Condition ($routeStrict.deep_discovery_filter.filtered_packs_count -ge 1) -Message "[strict] filtered packs produced"
    $results += Assert-True -Condition ($routeStrict.deep_discovery_filter.filtered_candidate_count -ge 1) -Message "[strict] filtered candidates produced"
    $results += Assert-True -Condition ($routeStrict.selected -ne $null) -Message "[strict] route still resolves to a selected skill"

    Set-DeepDiscoveryStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $specificPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.deep_discovery_advice.enabled -eq $false) -Message "[off] deep discovery disabled"
    $results += Assert-True -Condition ($routeOff.deep_discovery_route_filter_applied -eq $false) -Message "[off] route filter not applied"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored deep-discovery policy to original content."
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

Write-Host "Deep discovery gate passed."
exit 0


