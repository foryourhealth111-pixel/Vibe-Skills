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
$policyPath = Join-Path $repoRoot "config\observability-policy.json"
$tmpRel = "outputs/verify/tmp-telemetry"
$tmpDir = Join-Path $repoRoot $tmpRel
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO Observability Gate ==="

    $policy = $originalRaw | ConvertFrom-Json
    $policy.enabled = $true
    $policy.mode = "strict"
    $policy.telemetry.output_dir = $tmpRel
    $policy.telemetry.store_prompt_raw = $false
    $policy.telemetry.prompt_excerpt_max_chars = 0
    $policy.telemetry.sample_rates.shadow = 1.0
    $policy.telemetry.sample_rates.soft = 1.0
    $policy.telemetry.sample_rates.strict = 1.0
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $policyPath -Encoding UTF8

    if (Test-Path -LiteralPath $tmpDir) {
        Remove-Item -LiteralPath $tmpDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

    $routes = @()
    $routes += Invoke-Route -Prompt "Please optimize CUDA kernel occupancy and shared memory bank conflict in kernels/hgemm.cu." -Grade "L" -TaskType "coding"
    $routes += Invoke-Route -Prompt "请帮我修一个React表单验证bug" -Grade "M" -TaskType "coding"
    $routes += Invoke-Route -Prompt "Design a scalable event-driven system and evaluate trade-offs." -Grade "L" -TaskType "planning"

    $eventFile = Join-Path $tmpDir ("route-events-{0}.jsonl" -f (Get-Date -Format "yyyyMMdd"))
    $results += Assert-True -Condition (Test-Path -LiteralPath $eventFile) -Message "telemetry file exists"

    $events = @()
    if (Test-Path -LiteralPath $eventFile) {
        $lines = Get-Content -LiteralPath $eventFile -Encoding UTF8
        foreach ($line in $lines) {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                try {
                    $events += ($line | ConvertFrom-Json)
                } catch {
                    $results += Assert-True -Condition $false -Message "event JSON line parses"
                }
            }
        }
    }

    $results += Assert-True -Condition ($events.Count -ge 3) -Message "telemetry event count >= routed samples"

    if ($events.Count -gt 0) {
        $results += Assert-True -Condition (($events | Where-Object { -not $_.prompt_hash }).Count -eq 0) -Message "events include prompt_hash"
        $results += Assert-True -Condition (($events | Where-Object { $_.prompt_excerpt }).Count -eq 0) -Message "raw prompt excerpt is disabled"
        $results += Assert-True -Condition (($events | Where-Object { -not $_.environment_profile_id }).Count -eq 0) -Message "events include environment_profile_id"
        $results += Assert-True -Condition (($events | Where-Object { -not $_.user_profile_id }).Count -eq 0) -Message "events include user_profile_id"
        $results += Assert-True -Condition (($events | Where-Object { -not $_.scenario_key }).Count -eq 0) -Message "events include scenario_key"
        $results += Assert-True -Condition (($events | Where-Object { -not $_.route.route_mode }).Count -eq 0) -Message "events include route core fields"
    }
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    if (Test-Path -LiteralPath $tmpDir) {
        Remove-Item -LiteralPath $tmpDir -Recurse -Force
    }
    Write-Host "Restored observability policy to original content."
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

Write-Host "Observability gate passed."
exit 0
