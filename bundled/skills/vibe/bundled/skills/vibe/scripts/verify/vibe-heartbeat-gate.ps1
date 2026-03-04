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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\heartbeat-policy.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO Heartbeat Gate ==="

    $policy = $originalRaw | ConvertFrom-Json
    $policy.enabled = $true
    $policy.mode = "shadow"
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $policyPath -Encoding UTF8

    $shadowRoute = Invoke-Route -Prompt "Analyze and fix login form validation, then add tests." -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $shadowRoute.heartbeat_advice) -Message "shadow route contains heartbeat_advice"
    $results += Assert-True -Condition ($null -ne $shadowRoute.heartbeat_status) -Message "shadow route contains heartbeat_status"
    $results += Assert-True -Condition ($null -ne $shadowRoute.heartbeat_runtime_digest) -Message "shadow route contains heartbeat_runtime_digest"
    $results += Assert-True -Condition ([bool]$shadowRoute.heartbeat_advice.enabled) -Message "heartbeat advice enabled in shadow mode"
    $results += Assert-True -Condition ([int]$shadowRoute.heartbeat_status.pulse_count -ge 3) -Message "heartbeat pulse count collected"
    $results += Assert-True -Condition ([string]$shadowRoute.heartbeat_status.lifecycle_status -eq "completed") -Message "heartbeat lifecycle completes"
    $results += Assert-True -Condition (-not [bool]$shadowRoute.heartbeat_advice.confirm_required) -Message "healthy shadow route does not require confirm"

    $policyStrict = $originalRaw | ConvertFrom-Json
    $policyStrict.enabled = $true
    $policyStrict.mode = "strict"
    $policyStrict.timers.soft_stall_silence_sec = 0
    $policyStrict.timers.hard_stall_silence_sec = 0
    $policyStrict.timers.max_no_state_change_sec = 0
    $policyStrict.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policyStrict | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $policyPath -Encoding UTF8

    $strictRoute = Invoke-Route -Prompt "Design a robust distributed job orchestration plan and include fallback steps." -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ([bool]$strictRoute.heartbeat_status.hard_stall) -Message "strict route enters hard_stall under zero-threshold stress"
    $results += Assert-True -Condition ([bool]$strictRoute.heartbeat_advice.confirm_required) -Message "strict hard_stall requires confirmation"
    $results += Assert-True -Condition ([bool]$strictRoute.heartbeat_advice.auto_diagnosis_triggered) -Message "strict hard_stall triggers auto-diagnosis flag"
    $results += Assert-True -Condition ([string]$strictRoute.route_mode -ne "") -Message "routing output remains available in strict heartbeat stress case"

    $policyOff = $originalRaw | ConvertFrom-Json
    $policyOff.enabled = $false
    $policyOff.mode = "off"
    $policyOff.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policyOff | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $policyPath -Encoding UTF8

    $offRoute = Invoke-Route -Prompt "Review my API error handling strategy and propose improvements." -Grade "M" -TaskType "review"
    $results += Assert-True -Condition (-not [bool]$offRoute.heartbeat_advice.enabled) -Message "heartbeat disabled when policy is off"
    $results += Assert-True -Condition (-not [bool]$offRoute.heartbeat_status.enabled) -Message "heartbeat status marked disabled when policy is off"
    $results += Assert-True -Condition (-not [bool]$offRoute.heartbeat_runtime_digest.enabled) -Message "heartbeat runtime digest disabled when policy is off"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored heartbeat policy to original content."
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

Write-Host "Heartbeat gate passed."
exit 0
