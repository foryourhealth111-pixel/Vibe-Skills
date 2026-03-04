param(
    [switch]$KeepFixtures
)

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

function Set-DataScaleOverlayStage {
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

    # Keep test fixture tiny while still exercising large/small decision branches.
    $policy.thresholds.medium_size_bytes = 1024
    $policy.thresholds.large_size_bytes = 4096
    $policy.thresholds.medium_estimated_rows = 50
    $policy.thresholds.large_estimated_rows = 100
    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")

    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\data-scale-overlay.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

$fixturesDir = Join-Path $repoRoot "outputs\verify\data-scale-fixtures"
New-Item -ItemType Directory -Force -Path $fixturesDir | Out-Null

$smallCsv = Join-Path $fixturesDir "small.csv"
$largeCsv = Join-Path $fixturesDir "large.csv"
$workbook = Join-Path $fixturesDir "book.xlsx"

"id,name`n1,a`n2,b`n3,c" | Set-Content -LiteralPath $smallCsv -Encoding UTF8
$chunk = "x" * 1024
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("c1,c2")
for ($i = 0; $i -lt 1200; $i++) {
    [void]$sb.AppendLine("$i,$chunk")
}
$sb.ToString() | Set-Content -LiteralPath $largeCsv -Encoding UTF8
Set-Content -LiteralPath $workbook -Value "placeholder" -Encoding UTF8

try {
    Write-Host "=== VCO Data Scale Overlay Gate ==="

    Set-DataScaleOverlayStage -ConfigPath $policyPath -Stage "shadow"

    $routeSmall = Invoke-Route -Prompt "edit spreadsheet csv at $smallCsv and normalize columns" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($null -ne $routeSmall.data_scale_advice) -Message "[shadow] data_scale_advice exists"
    $results += Assert-True -Condition ($routeSmall.data_scale_advice.enabled -eq $true) -Message "[shadow] overlay enabled"
    $results += Assert-True -Condition ($routeSmall.data_scale_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable for docs-media coding"
    $results += Assert-True -Condition ($routeSmall.data_scale_advice.recommended_skill -eq "spreadsheet") -Message "[shadow] small csv keeps spreadsheet recommendation"
    $results += Assert-True -Condition ($routeSmall.data_scale_route_override -eq $false) -Message "[shadow] no route override"

    $routeWorkbook = Invoke-Route -Prompt "update workbook at $workbook and preserve formulas" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeWorkbook.data_scale_advice.recommended_skill -eq "xlsx") -Message "[shadow] workbook path recommends xlsx"
    $results += Assert-True -Condition ($routeWorkbook.data_scale_advice.is_workbook -eq $true) -Message "[shadow] workbook extension detected"

    Set-DataScaleOverlayStage -ConfigPath $policyPath -Stage "soft"
    $routeLargeSoft = Invoke-Route -Prompt "edit spreadsheet csv at $largeCsv and dedup rows" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeLargeSoft.data_scale_advice.data_scale -eq "large") -Message "[soft] large dataset detected"
    $results += Assert-True -Condition ($routeLargeSoft.data_scale_advice.recommended_skill -eq "xan") -Message "[soft] large csv recommends xan"
    $results += Assert-True -Condition ($routeLargeSoft.data_scale_advice.confirm_required -eq $true) -Message "[soft] large csv marks confirm_required"

    Set-DataScaleOverlayStage -ConfigPath $policyPath -Stage "strict"
    $routeLargeStrict = Invoke-Route -Prompt "edit spreadsheet csv at $largeCsv and dedup rows" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeLargeStrict.data_scale_advice.enforcement -eq "required") -Message "[strict] enforcement is required"
    $results += Assert-True -Condition ($routeLargeStrict.selected.skill -eq "xan") -Message "[strict] selected skill overridden to xan"
    $results += Assert-True -Condition ($routeLargeStrict.data_scale_route_override -eq $true) -Message "[strict] data scale route override flag set"

    Set-DataScaleOverlayStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt "edit spreadsheet csv at $largeCsv and dedup rows" -Grade "M" -TaskType "coding"
    $results += Assert-True -Condition ($routeOff.data_scale_advice.enabled -eq $false) -Message "[off] overlay disabled"
} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored data-scale-overlay policy to original content."

    if (-not $KeepFixtures -and (Test-Path -LiteralPath $fixturesDir)) {
        Remove-Item -LiteralPath $fixturesDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Removed generated data-scale fixtures."
    } elseif ($KeepFixtures) {
        Write-Host "Kept generated data-scale fixtures (KeepFixtures enabled)."
    }
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

Write-Host "Data scale overlay gate passed."
exit 0
