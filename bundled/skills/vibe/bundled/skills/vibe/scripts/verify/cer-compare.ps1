param(
    [Parameter(Mandatory = $true)]
    [string]$BaselineCerPath,
    [Parameter(Mandatory = $true)]
    [string]$CurrentCerPath,
    [string]$OutputMarkdownPath,
    [string]$OutputJsonPath,
    [switch]$UpdateCurrentComparison
)

$ErrorActionPreference = "Stop"

function Get-NestedValue {
    param(
        [object]$Object,
        [string[]]$Path,
        [object]$Default = $null
    )

    $cursor = $Object
    foreach ($part in $Path) {
        if ($null -eq $cursor) { return $Default }
        $prop = $cursor.PSObject.Properties[$part]
        if ($null -eq $prop) { return $Default }
        $cursor = $prop.Value
    }
    if ($null -eq $cursor) { return $Default }
    return $cursor
}

function Get-DoubleValue {
    param(
        [object]$Object,
        [string[]]$Path
    )
    $v = Get-NestedValue -Object $Object -Path $Path -Default 0
    return [double]$v
}

function Get-PatternSet {
    param([object]$Cer)
    $set = New-Object System.Collections.Generic.HashSet[string]
    $findings = Get-NestedValue -Object $Cer -Path @("findings") -Default @()
    foreach ($f in $findings) {
        $p = [string](Get-NestedValue -Object $f -Path @("pattern") -Default "")
        if ($p) { [void]$set.Add($p) }
    }
    return $set
}

function Get-StabilityScore {
    param([object]$Cer)
    $pack = Get-DoubleValue -Object $Cer -Path @("trigger_signals", "route_stability_pack")
    $skill = Get-DoubleValue -Object $Cer -Path @("trigger_signals", "route_stability_skill")
    return [Math]::Round((($pack + $skill) / 2.0), 4)
}

function Get-ReportId {
    param([object]$Cer, [string]$Fallback)
    $id = [string](Get-NestedValue -Object $Cer -Path @("report_id") -Default "")
    if ($id) { return $id }
    return $Fallback
}

function Write-Utf8File {
    param(
        [string]$Path,
        [string]$Content
    )
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $Content | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Set-NotePropertySafe {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Value
    )

    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force
    } else {
        $Object.$Name = $Value
    }
}

$baselineRaw = Get-Content -LiteralPath $BaselineCerPath -Raw -Encoding UTF8
$currentRaw = Get-Content -LiteralPath $CurrentCerPath -Raw -Encoding UTF8

$baselineCer = $baselineRaw | ConvertFrom-Json
$currentCer = $currentRaw | ConvertFrom-Json

$baselineId = Get-ReportId -Cer $baselineCer -Fallback (Split-Path -Leaf $BaselineCerPath)
$currentId = Get-ReportId -Cer $currentCer -Fallback (Split-Path -Leaf $CurrentCerPath)

$baselineFallback = Get-DoubleValue -Object $baselineCer -Path @("trigger_signals", "fallback_rate")
$currentFallback = Get-DoubleValue -Object $currentCer -Path @("trigger_signals", "fallback_rate")
$fallbackDelta = [Math]::Round(($currentFallback - $baselineFallback), 6)

$baselineStability = Get-StabilityScore -Cer $baselineCer
$currentStability = Get-StabilityScore -Cer $currentCer
$stabilityDelta = [Math]::Round(($currentStability - $baselineStability), 6)

$baselinePressure = Get-DoubleValue -Object $baselineCer -Path @("trigger_signals", "context_pressure")
$currentPressure = Get-DoubleValue -Object $currentCer -Path @("trigger_signals", "context_pressure")
$pressureDelta = [Math]::Round(($currentPressure - $baselinePressure), 6)

$baselineGap = Get-DoubleValue -Object $baselineCer -Path @("trigger_signals", "top1_top2_gap")
$currentGap = Get-DoubleValue -Object $currentCer -Path @("trigger_signals", "top1_top2_gap")
$gapDelta = [Math]::Round(($currentGap - $baselineGap), 6)

$baseSet = Get-PatternSet -Cer $baselineCer
$currentSet = Get-PatternSet -Cer $currentCer

$added = @()
$removed = @()
$common = @()

foreach ($p in $currentSet) {
    if ($baseSet.Contains($p)) { $common += $p } else { $added += $p }
}
foreach ($p in $baseSet) {
    if (-not $currentSet.Contains($p)) { $removed += $p }
}

$added = $added | Sort-Object
$removed = $removed | Sort-Object
$common = $common | Sort-Object

$status = "mixed"
if (($fallbackDelta -le 0) -and ($stabilityDelta -ge 0) -and ($pressureDelta -le 0)) {
    $status = "improved"
} elseif (($fallbackDelta -ge 0.05) -or ($stabilityDelta -le -0.05) -or ($pressureDelta -ge 0.10)) {
    $status = "degraded"
}

$generatedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$summary = [pscustomobject]@{
    baseline_report_id = $baselineId
    current_report_id = $currentId
    generated_at = $generatedAt
    status = $status
    pattern_delta = [pscustomobject]@{
        added = $added
        removed = $removed
        common_count = $common.Count
    }
    fallback_rate = [pscustomobject]@{
        baseline = $baselineFallback
        current = $currentFallback
        delta = $fallbackDelta
    }
    stability = [pscustomobject]@{
        baseline = $baselineStability
        current = $currentStability
        delta = $stabilityDelta
    }
    context_pressure = [pscustomobject]@{
        baseline = $baselinePressure
        current = $currentPressure
        delta = $pressureDelta
    }
    route_gap = [pscustomobject]@{
        baseline = $baselineGap
        current = $currentGap
        delta = $gapDelta
    }
}

if (-not $OutputMarkdownPath -or -not $OutputJsonPath) {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $outDir = Join-Path $repoRoot "outputs\retro\compare"
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    if (-not $OutputMarkdownPath) {
        $OutputMarkdownPath = Join-Path $outDir ("cer-compare-" + $stamp + ".md")
    }
    if (-not $OutputJsonPath) {
        $OutputJsonPath = Join-Path $outDir ("cer-compare-" + $stamp + ".json")
    }
}

$mdLines = @(
    "# CER Compare Report"
    ""
    "Generated: `$generatedAt"
    ""
    "## Scope"
    "- Baseline: `$baselineId"
    "- Current: `$currentId"
    "- Status: **$status**"
    ""
    "## Pattern Delta"
    "- Added: " + ($(if ($added.Count -gt 0) { ($added -join ", ") } else { "(none)" }))
    "- Removed: " + ($(if ($removed.Count -gt 0) { ($removed -join ", ") } else { "(none)" }))
    "- Common count: $($common.Count)"
    ""
    "## Metric Delta"
    "| Metric | Baseline | Current | Delta |"
    "|--------|----------|---------|-------|"
    "| fallback_rate | $baselineFallback | $currentFallback | $fallbackDelta |"
    "| stability_score | $baselineStability | $currentStability | $stabilityDelta |"
    "| context_pressure | $baselinePressure | $currentPressure | $pressureDelta |"
    "| top1_top2_gap | $baselineGap | $currentGap | $gapDelta |"
    ""
    "## Interpretation"
    "- Negative `fallback_rate` delta is better."
    "- Positive `stability_score` delta is better."
    "- Negative `context_pressure` delta is better."
    "- Positive `top1_top2_gap` delta generally means better route separability."
)

$summaryJson = $summary | ConvertTo-Json -Depth 8
Write-Utf8File -Path $OutputMarkdownPath -Content ($mdLines -join "`r`n")
Write-Utf8File -Path $OutputJsonPath -Content $summaryJson

if ($UpdateCurrentComparison) {
    if (-not $currentCer.comparison) {
        $currentCer | Add-Member -MemberType NoteProperty -Name comparison -Value ([pscustomobject]@{
            baseline_report_id = ""
            pattern_delta = @()
            fallback_rate_delta = 0.0
            stability_delta = 0.0
            notes = ""
        }) -Force
    }
    Set-NotePropertySafe -Object $currentCer.comparison -Name "baseline_report_id" -Value $baselineId
    Set-NotePropertySafe -Object $currentCer.comparison -Name "pattern_delta" -Value @(
        ("added: " + ($(if ($added.Count -gt 0) { ($added -join ", ") } else { "(none)" }))),
        ("removed: " + ($(if ($removed.Count -gt 0) { ($removed -join ", ") } else { "(none)" }))),
        "common_count: $($common.Count)"
    )
    Set-NotePropertySafe -Object $currentCer.comparison -Name "fallback_rate_delta" -Value $fallbackDelta
    Set-NotePropertySafe -Object $currentCer.comparison -Name "stability_delta" -Value $stabilityDelta
    Set-NotePropertySafe -Object $currentCer.comparison -Name "notes" -Value "auto-updated by cer-compare.ps1 at $generatedAt"
    $currentUpdated = $currentCer | ConvertTo-Json -Depth 10
    Write-Utf8File -Path $CurrentCerPath -Content $currentUpdated
}

Write-Host "CER compare complete."
Write-Host "Markdown: $OutputMarkdownPath"
Write-Host "JSON: $OutputJsonPath"
Write-Host "Status: $status"

$summary
