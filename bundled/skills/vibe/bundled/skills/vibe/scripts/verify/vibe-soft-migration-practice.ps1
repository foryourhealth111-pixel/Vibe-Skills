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

$results = @()
Write-Host "=== Canonical Routing Practice Tests ==="

# Case 1: canonical code-review request routes through code-quality pack.
Write-Host "[INFO] Case 1: code-review canonical"
$c1 = Invoke-Route -Prompt "run code review and security scan" -Grade "M" -TaskType "review" -RequestedSkill "code-review"
$results += Assert-True -Condition ($c1.alias.alias_hit -eq $false) -Message "code-review is canonical (no alias hit)"
$results += Assert-True -Condition ($c1.alias.canonical -eq "code-review") -Message "code-review canonical remains code-review"
$results += Assert-True -Condition ($c1.selected.pack_id -eq "code-quality") -Message "code-review chooses code-quality pack"
$results += Assert-True -Condition ($c1.route_mode -eq "pack_overlay") -Message "code-review uses pack overlay"

# Case 2: canonical xlsx request routes through docs-media pack.
Write-Host "[INFO] Case 2: xlsx canonical"
$c2 = Invoke-Route -Prompt "process xlsx spreadsheet and export results" -Grade "M" -TaskType "coding" -RequestedSkill "xlsx"
$results += Assert-True -Condition ($c2.alias.alias_hit -eq $false) -Message "xlsx is canonical (no alias hit)"
$results += Assert-True -Condition ($c2.alias.canonical -eq "xlsx") -Message "xlsx canonical remains xlsx"
$results += Assert-True -Condition ($c2.selected.pack_id -eq "docs-media") -Message "xlsx chooses docs-media pack"
$results += Assert-True -Condition ($c2.route_mode -eq "pack_overlay") -Message "xlsx uses pack overlay"

# Case 3: low-signal prompt falls back to legacy matrix.
Write-Host "[INFO] Case 3: low-signal fallback"
$c3 = Invoke-Route -Prompt "help me with this" -Grade "M" -TaskType "research"
$results += Assert-True -Condition ($c3.route_mode -eq "legacy_fallback") -Message "low-signal prompt falls back to legacy matrix"
$results += Assert-True -Condition ([double]$c3.confidence -lt [double]$c3.thresholds.fallback_to_legacy_below) -Message "low-signal confidence below fallback threshold"

# Case 4: grade boundary blocks docs-media for XL.
Write-Host "[INFO] Case 4: grade boundary"
$c4 = Invoke-Route -Prompt "xlsx docx parallel processing" -Grade "XL" -TaskType "coding" -RequestedSkill "xlsx"
$results += Assert-True -Condition ($c4.selected.pack_id -ne "docs-media") -Message "docs-media blocked for XL by grade boundary"

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

Write-Host "Canonical routing practice tests passed."
exit 0
