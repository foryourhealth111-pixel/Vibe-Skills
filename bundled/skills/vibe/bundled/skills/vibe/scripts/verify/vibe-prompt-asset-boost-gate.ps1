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

function Set-PromptAssetBoostPolicyStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("off", "shadow", "soft", "strict")]
        [string]$Stage,
        [string]$MockResponsePath
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

    $policy.activation.explicit_vibe_only = $true
    $policy.trigger.require_prompt_signal = $true
    $policy.trigger.max_candidates = 2
    $policy.trigger.max_queries = 3

    $policy.provider.type = "mock"
    $policy.provider.mock_response_path = $MockResponsePath
    $policy.provider.timeout_ms = 50
    $policy.provider.temperature = 0.0
    $policy.provider.store = $false

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\prompt-asset-boost.json"
$mockPath = "scripts/verify/fixtures/prompt-asset-boost.mock.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO Prompt Asset Boost Gate ==="

    Set-PromptAssetBoostPolicyStage -ConfigPath $policyPath -Stage "soft" -MockResponsePath $mockPath

    $routeNoPrefix = Invoke-Route -Prompt "prompts.chat code review prompt template" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeNoPrefix.prompt_asset_boost_advice) -Message "[no /vibe] prompt_asset_boost_advice exists"
    $results += Assert-True -Condition ($routeNoPrefix.prompt_asset_boost_advice.scope_applicable -eq $false) -Message "[no /vibe] explicit_vibe_only blocks scope"

    $routeWithPrefix = Invoke-Route -Prompt "/vibe prompts.chat code review prompt template" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.scope_applicable -eq $true) -Message "[/vibe] scope applicable"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.provider.api -eq "mock") -Message "[/vibe] provider mock"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.provider.abstained -eq $false) -Message "[/vibe] provider returns data"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.overlay_candidates.Count -ge 1) -Message "[/vibe] overlay_candidates populated"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.search_plan.queries.Count -ge 1) -Message "[/vibe] search_plan queries populated"
    $results += Assert-True -Condition ($routeWithPrefix.prompt_asset_boost_advice.confirm_required -eq $true) -Message "[/vibe] confirm_required when candidates exist"

    Set-PromptAssetBoostPolicyStage -ConfigPath $policyPath -Stage "off" -MockResponsePath $mockPath
    $routeOff = Invoke-Route -Prompt "/vibe prompts.chat code review prompt template" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.prompt_asset_boost_advice.enabled -eq $false) -Message "[off] overlay disabled"

} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored prompt-asset-boost policy to original content."
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

Write-Host "Prompt asset boost gate passed."
exit 0

