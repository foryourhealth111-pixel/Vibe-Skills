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

function Set-CudaKernelOverlayStage {
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

    # Deterministic scope for gate execution.
    $policy.monitor.pack_allow = @()
    $policy.monitor.skill_allow = @()
    $policy.thresholds.trigger_signal_score_min = 0.35
    $policy.thresholds.confirm_signal_score_min = 0.5
    $policy.thresholds.high_signal_score_min = 0.72
    $policy.thresholds.negative_penalty_weight = 0.18
    $policy.thresholds.min_dimension_hits_for_overlay = 2
    $policy.thresholds.min_coverage_score_for_ready = 0.6
    $policy.thresholds.min_coverage_score_for_strict_confirm = 0.95
    $policy.strict_confirm_scope.grades = @("L", "XL")
    $policy.strict_confirm_scope.task_types = @("coding", "debug")
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\cuda-kernel-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$cudaPrompt = "Optimize CUDA kernel in kernels/hgemm.cu for model training: reduce bank conflict in shared memory, tune occupancy and block size, use tensor core wmma, run Nsight Compute with baseline-vs-optimized TFLOPS and numerical parity checks."

try {
    Write-Host "=== VCO CUDA Kernel Overlay Gate ==="

    Set-CudaKernelOverlayStage -ConfigPath $policyPath -Stage "shadow"
    $routeShadow = Invoke-Route -Prompt $cudaPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeShadow.cuda_kernel_advice) -Message "[shadow] cuda_kernel_advice exists"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable for coding"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.trigger_active -eq $true) -Message "[shadow] cuda trigger active"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.cuda_signal_score -ge 0.35) -Message "[shadow] cuda signal score captured"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.confirm_recommended -eq $true) -Message "[shadow] confirm is recommended"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.confirm_required -eq $false) -Message "[shadow] confirm is not forced"
    $results += Assert-True -Condition ($routeShadow.cuda_kernel_advice.enforcement -eq "advisory") -Message "[shadow] enforcement stays advisory"

    $shadowPack = [string]$routeShadow.selected.pack_id
    $shadowSkill = [string]$routeShadow.selected.skill
    $shadowRouteMode = [string]$routeShadow.route_mode

    Set-CudaKernelOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeSoft = Invoke-Route -Prompt $cudaPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeSoft.cuda_kernel_advice.enforcement -eq "advisory") -Message "[soft] enforcement remains advisory"
    $results += Assert-True -Condition ($routeSoft.cuda_kernel_advice.confirm_recommended -eq $true) -Message "[soft] confirm remains recommended"
    $results += Assert-True -Condition ($routeSoft.cuda_kernel_advice.confirm_required -eq $false) -Message "[soft] confirm is not hard-required"
    $results += Assert-True -Condition ($routeSoft.selected.pack_id -eq $shadowPack) -Message "[soft] selected pack unchanged"
    $results += Assert-True -Condition ($routeSoft.selected.skill -eq $shadowSkill) -Message "[soft] selected skill unchanged"
    $results += Assert-True -Condition ($routeSoft.route_mode -eq $shadowRouteMode) -Message "[soft] route mode unchanged by overlay"

    Set-CudaKernelOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeStrict = Invoke-Route -Prompt $cudaPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeStrict.cuda_kernel_advice.enforcement -eq "confirm_required") -Message "[strict] weak coverage escalates to confirm_required in advice"
    $results += Assert-True -Condition ($routeStrict.cuda_kernel_advice.confirm_required -eq $true) -Message "[strict] confirm_required flag set"
    $results += Assert-True -Condition ($routeStrict.cuda_kernel_advice.strict_scope_applied -eq $true) -Message "[strict] strict scope applied"
    $results += Assert-True -Condition ($routeStrict.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrict.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"
    $results += Assert-True -Condition ($routeStrict.route_mode -eq $shadowRouteMode) -Message "[strict] route mode unchanged by overlay"

    $routeOutsideScope = Invoke-Route -Prompt "Design a product roadmap and write PRD milestones" -Grade "L" -TaskType "planning"
    $results += Assert-True -Condition ($routeOutsideScope.cuda_kernel_advice.scope_applicable -eq $false) -Message "[strict] planning task is outside overlay scope"
    $results += Assert-True -Condition ($routeOutsideScope.cuda_kernel_advice.enforcement -eq "none") -Message "[strict] outside scope has no enforcement"

    Set-CudaKernelOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt $cudaPrompt -Grade "L" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.cuda_kernel_advice.enabled -eq $false) -Message "[off] overlay disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored cuda-kernel-overlay policy to original content."
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

Write-Host "CUDA kernel overlay gate passed."
exit 0
