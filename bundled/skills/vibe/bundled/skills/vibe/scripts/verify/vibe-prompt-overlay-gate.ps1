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

function Set-PromptOverlayStage {
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

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\prompt-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO Prompt Overlay Gate ==="

    Set-PromptOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt "find a prompt template for code review and improve system prompt quality" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($null -ne $routeShadow.prompt_overlay_advice) -Message "[shadow] prompt_overlay_advice exists"
    $results += Assert-True -Condition ($routeShadow.prompt_overlay_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.prompt_overlay_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable for L planning"
    $results += Assert-True -Condition ($routeShadow.prompt_overlay_advice.prompt_signal_hit -eq $true) -Message "[shadow] prompt signal detected"
    $results += Assert-True -Condition (@($routeShadow.prompt_overlay_advice.matched_intent_facets) -contains "template_seek") -Message "[shadow] template_seek facet matched"
    $results += Assert-True -Condition ($routeShadow.prompt_overlay_advice.should_search_prompts_first -eq $true) -Message "[shadow] prompts-first advisory enabled"
    $results += Assert-True -Condition ($routeShadow.prompt_overlay_advice.enforcement -eq "advisory") -Message "[shadow] enforcement advisory"

    Set-PromptOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoftAmbiguous = Invoke-Route -Prompt "openai docs chat completions responses api model limits llm agent prompt" -Grade "L" -TaskType "research" -RequestedSkill $null
    $results += Assert-True -Condition ($routeSoftAmbiguous.prompt_overlay_advice.ambiguity_detected -eq $true) -Message "[soft] ambiguity detected on prompt/doc collision"
    $results += Assert-True -Condition ($routeSoftAmbiguous.prompt_overlay_advice.confirm_required -eq $true) -Message "[soft] confirm_required set on collision"
    $results += Assert-True -Condition ($routeSoftAmbiguous.route_mode -eq "confirm_required") -Message "[soft] route mode is confirm_required for ambiguous prompt/doc request"
    $results += Assert-True -Condition ($routeSoftAmbiguous.route_reason -eq "prompt_overlay_confirm_required") -Message "[soft] route reason indicates prompt overlay override"
    $results += Assert-True -Condition ($routeSoftAmbiguous.prompt_overlay_route_override -eq $true) -Message "[soft] prompt overlay override flag set"

    $routeSoftPromptOnly = Invoke-Route -Prompt "prompts.chat improve prompt for code review checklist" -Grade "M" -TaskType "research" -RequestedSkill $null
    $results += Assert-True -Condition ($routeSoftPromptOnly.prompt_overlay_advice.ambiguity_detected -eq $false) -Message "[soft] explicit prompt intent is not ambiguous"
    $results += Assert-True -Condition ($routeSoftPromptOnly.prompt_overlay_advice.confirm_required -eq $false) -Message "[soft] explicit prompt intent does not force confirm"

    Set-PromptOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt "find prompt template for coding interview" -Grade "XL" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeOff.prompt_overlay_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.prompt_overlay_advice.should_apply_hook -eq $false) -Message "[off] no overlay hook when disabled"

} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored prompt-overlay policy to original content."
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

Write-Host "Prompt overlay gate passed."
exit 0
