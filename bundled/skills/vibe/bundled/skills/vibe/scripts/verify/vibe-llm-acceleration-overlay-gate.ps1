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

function Set-LlmAccelerationPolicyStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("off", "shadow")]
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
    }

    $policy.activation.explicit_vibe_only = $true
    $policy.trigger.always_on_explicit_vibe = $true
    $policy.trigger.top_k = 3

    $policy.provider.type = "mock"
    $policy.provider.mock_response_path = $MockResponsePath
    $policy.provider.timeout_ms = 50
    $policy.provider.temperature = 0.0
    $policy.provider.store = $false

    $policy.context.mode = "none"
    $policy.context.include_git_status = $false
    $policy.context.include_git_diff = $false

    $policy.safety.allow_confirm_escalation = $true
    $policy.safety.allow_route_override = $false
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\llm-acceleration-policy.json"
$mockPath = "scripts/verify/fixtures/llm-acceleration.mock.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO LLM Acceleration Overlay Gate ==="

    Set-LlmAccelerationPolicyStage -ConfigPath $policyPath -Stage "shadow" -MockResponsePath $mockPath

    $routeNoPrefix = Invoke-Route -Prompt "add login form validation" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeNoPrefix.llm_acceleration_advice) -Message "[no /vibe] llm_acceleration_advice exists"
    $results += Assert-True -Condition ($routeNoPrefix.llm_acceleration_advice.scope_applicable -eq $false) -Message "[no /vibe] explicit_vibe_only blocks scope"
    $results += Assert-True -Condition ($routeNoPrefix.llm_acceleration_advice.provider.reason -eq "not_invoked") -Message "[no /vibe] provider not invoked"

    $routeWithPrefix = Invoke-Route -Prompt "/vibe add login form validation" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.scope_applicable -eq $true) -Message "[/vibe] scope applicable"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.provider.type -eq "mock") -Message "[/vibe] provider mock"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.provider.abstained -eq $false) -Message "[/vibe] provider returns data"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.abstained -eq $false) -Message "[/vibe] overlay not abstained"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.parse_error -eq $null) -Message "[/vibe] parse_error is null"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.confirm_questions.Count -ge 1) -Message "[/vibe] confirm_questions populated"
    $results += Assert-True -Condition ($routeWithPrefix.llm_acceleration_advice.qa_recommendations.Count -ge 1) -Message "[/vibe] qa recommendations populated"

    $results += Assert-True -Condition ([string]$routeWithPrefix.route_reason -ne "llm_acceleration_confirm_required") -Message "[shadow] does not promote confirm_required via route_reason"
    $results += Assert-True -Condition ([string]$routeWithPrefix.route_reason -ne "llm_acceleration_override") -Message "[shadow] does not override pack via route_reason"

    Set-LlmAccelerationPolicyStage -ConfigPath $policyPath -Stage "off" -MockResponsePath $mockPath
    $routeOff = Invoke-Route -Prompt "/vibe add login form validation" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.llm_acceleration_advice.enabled -eq $false) -Message "[off] overlay disabled"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored llm-acceleration-policy to original content."
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

Write-Host "LLM acceleration overlay gate passed."
exit 0

