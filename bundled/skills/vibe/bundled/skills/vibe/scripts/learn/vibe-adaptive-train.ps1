param(
    [string]$TelemetryDirectory,
    [string]$OutputJsonPath,
    [string]$OutputMarkdownPath,
    [int]$LookbackDays = 7
)

$ErrorActionPreference = "Stop"

function Resolve-DefaultPaths {
    param(
        [string]$RepoRoot,
        [object]$ObservabilityPolicy
    )

    $telemetryRel = "outputs/telemetry"
    $jsonRel = "outputs/learn/vibe-adaptive-suggestions.json"
    $mdRel = "outputs/learn/vibe-adaptive-suggestions.md"

    if ($ObservabilityPolicy -and $ObservabilityPolicy.telemetry -and $ObservabilityPolicy.telemetry.output_dir) {
        $telemetryRel = [string]$ObservabilityPolicy.telemetry.output_dir
    }
    if ($ObservabilityPolicy -and $ObservabilityPolicy.learning -and $ObservabilityPolicy.learning.output_path) {
        $jsonRel = [string]$ObservabilityPolicy.learning.output_path
        if ($jsonRel.EndsWith(".json")) {
            $mdRel = $jsonRel.Substring(0, $jsonRel.Length - 5) + ".md"
        }
    }

    return [pscustomobject]@{
        telemetry = Join-Path $RepoRoot $telemetryRel
        json = Join-Path $RepoRoot $jsonRel
        markdown = Join-Path $RepoRoot $mdRel
    }
}

function Get-GroupStats {
    param(
        [object[]]$Events,
        [double]$MinTopGap
    )

    $groups = $Events | Group-Object -Property scenario_key
    $rows = @()
    foreach ($g in $groups) {
        $items = @($g.Group)
        $count = $items.Count
        if ($count -le 0) { continue }

        $legacy = ($items | Where-Object { $_.route.route_mode -eq "legacy_fallback" }).Count
        $confirm = ($items | Where-Object { $_.route.route_mode -eq "confirm_required" }).Count
        $lowGap = ($items | Where-Object { [double]$_.route.top1_top2_gap -lt $MinTopGap }).Count
        # Avoid dotted-property Measure-Object ambiguity by projecting numeric arrays first.
        $confidenceValues = @(
            $items | ForEach-Object {
                if ($_.route -and $_.route.confidence -ne $null) {
                    [double]$_.route.confidence
                } else {
                    0.0
                }
            }
        )
        $gapValues = @(
            $items | ForEach-Object {
                if ($_.route -and $_.route.top1_top2_gap -ne $null) {
                    [double]$_.route.top1_top2_gap
                } else {
                    0.0
                }
            }
        )

        $avgConfidenceRaw = if ($confidenceValues.Count -gt 0) { ($confidenceValues | Measure-Object -Average).Average } else { 0.0 }
        $avgGapRaw = if ($gapValues.Count -gt 0) { ($gapValues | Measure-Object -Average).Average } else { 0.0 }
        $avgConfidence = [Math]::Round([double]$avgConfidenceRaw, 4)
        $avgGap = [Math]::Round([double]$avgGapRaw, 4)

        $rows += [pscustomobject]@{
            scenario_key = [string]$g.Name
            event_count = $count
            legacy_fallback_rate = [Math]::Round(($legacy / $count), 4)
            confirm_required_rate = [Math]::Round(($confirm / $count), 4)
            low_gap_rate = [Math]::Round(($lowGap / $count), 4)
            avg_confidence = $avgConfidence
            avg_top_gap = $avgGap
            environment_profile_id = [string]$items[0].environment_profile_id
            user_profile_id = [string]$items[0].user_profile_id
            task_type = [string]$items[0].route.task_type
        }
    }
    return $rows
}

function Build-Recommendations {
    param(
        [object[]]$GroupStats,
        [object]$Thresholds,
        [object]$ObservabilityPolicy
    )

    $current = $Thresholds.thresholds
    $minEvents = 200
    if ($ObservabilityPolicy -and $ObservabilityPolicy.learning -and $ObservabilityPolicy.learning.min_events_for_suggestion -ne $null) {
        $minEvents = [int]$ObservabilityPolicy.learning.min_events_for_suggestion
    }

    $maxDeltaConfirm = 0.03
    $maxDeltaGap = 0.03
    $maxDeltaFallback = 0.02
    if ($ObservabilityPolicy -and $ObservabilityPolicy.learning -and $ObservabilityPolicy.learning.bounded_adjustments) {
        $adj = $ObservabilityPolicy.learning.bounded_adjustments
        if ($adj.confirm_required_max_delta -ne $null) { $maxDeltaConfirm = [double]$adj.confirm_required_max_delta }
        if ($adj.min_top_gap_max_delta -ne $null) { $maxDeltaGap = [double]$adj.min_top_gap_max_delta }
        if ($adj.fallback_threshold_max_delta -ne $null) { $maxDeltaFallback = [double]$adj.fallback_threshold_max_delta }
    }

    $rec = @()
    foreach ($row in $GroupStats) {
        if ($row.event_count -lt $minEvents) { continue }

        if ($row.legacy_fallback_rate -ge 0.35 -and $row.avg_confidence -ge ([double]$current.fallback_to_legacy_below + 0.05)) {
            $delta = [Math]::Min($maxDeltaFallback, 0.02)
            $target = [Math]::Round(([double]$current.fallback_to_legacy_below - $delta), 4)
            $rec += [pscustomobject]@{
                scenario_key = $row.scenario_key
                reason = "high_legacy_fallback_with_confident_scores"
                parameter = "thresholds.fallback_to_legacy_below"
                current_value = [double]$current.fallback_to_legacy_below
                suggested_value = $target
                delta = -$delta
                apply_policy = "manual_review_required"
            }
        }

        if ($row.confirm_required_rate -ge 0.5 -and $row.avg_top_gap -ge ([double]$current.min_top1_top2_gap + 0.08)) {
            $delta = [Math]::Min($maxDeltaConfirm, 0.02)
            $target = [Math]::Round(([double]$current.confirm_required - $delta), 4)
            $rec += [pscustomobject]@{
                scenario_key = $row.scenario_key
                reason = "high_confirm_required_with_clear_top_gap"
                parameter = "thresholds.confirm_required"
                current_value = [double]$current.confirm_required
                suggested_value = $target
                delta = -$delta
                apply_policy = "manual_review_required"
            }
        }

        if ($row.low_gap_rate -ge 0.35) {
            $delta = [Math]::Min($maxDeltaGap, 0.01)
            $target = [Math]::Round(([double]$current.min_top1_top2_gap + $delta), 4)
            $rec += [pscustomobject]@{
                scenario_key = $row.scenario_key
                reason = "persistent_low_top1_top2_gap"
                parameter = "thresholds.min_top1_top2_gap"
                current_value = [double]$current.min_top1_top2_gap
                suggested_value = $target
                delta = $delta
                apply_policy = "manual_review_required"
            }
        }
    }

    return $rec
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$obsPolicyPath = Join-Path $repoRoot "config/observability-policy.json"
$routerThresholdPath = Join-Path $repoRoot "config/router-thresholds.json"
$obsPolicy = if (Test-Path -LiteralPath $obsPolicyPath) { Get-Content -LiteralPath $obsPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$thresholds = Get-Content -LiteralPath $routerThresholdPath -Raw -Encoding UTF8 | ConvertFrom-Json
$defaults = Resolve-DefaultPaths -RepoRoot $repoRoot -ObservabilityPolicy $obsPolicy

if (-not $TelemetryDirectory) { $TelemetryDirectory = $defaults.telemetry }
if (-not $OutputJsonPath) { $OutputJsonPath = $defaults.json }
if (-not $OutputMarkdownPath) { $OutputMarkdownPath = $defaults.markdown }

$cutoffDate = (Get-Date).AddDays(-1 * [Math]::Abs($LookbackDays))
$files = @()
if (Test-Path -LiteralPath $TelemetryDirectory) {
    $files = Get-ChildItem -LiteralPath $TelemetryDirectory -Filter "route-events-*.jsonl" -File | Where-Object { $_.LastWriteTime -ge $cutoffDate }
}

$events = @()
foreach ($file in $files) {
    $lines = Get-Content -LiteralPath $file.FullName -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $events += ($line | ConvertFrom-Json)
        } catch {
            continue
        }
    }
}

$groupStats = Get-GroupStats -Events $events -MinTopGap ([double]$thresholds.thresholds.min_top1_top2_gap)
$recommendations = Build-Recommendations -GroupStats $groupStats -Thresholds $thresholds -ObservabilityPolicy $obsPolicy

$summary = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    lookback_days = [int]$LookbackDays
    telemetry_directory = (Resolve-Path -LiteralPath $TelemetryDirectory -ErrorAction SilentlyContinue | ForEach-Object { $_.Path })
    files_scanned = @($files | Select-Object -ExpandProperty FullName)
    total_events = $events.Count
    scenarios = $groupStats.Count
    min_events_for_suggestion = if ($obsPolicy -and $obsPolicy.learning) { [int]$obsPolicy.learning.min_events_for_suggestion } else { 200 }
    apply_policy = if ($obsPolicy -and $obsPolicy.learning -and $obsPolicy.learning.apply_policy) { [string]$obsPolicy.learning.apply_policy } else { "manual_review_required" }
    recommendations = $recommendations
    scenario_stats = $groupStats
}

$jsonDir = Split-Path -Parent $OutputJsonPath
$mdDir = Split-Path -Parent $OutputMarkdownPath
New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
New-Item -ItemType Directory -Path $mdDir -Force | Out-Null

$summary | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutputJsonPath -Encoding UTF8

$lines = @()
$lines += "# VCO Adaptive Suggestions (Offline)"
$lines += ""
$lines += "- generated_at: ``$($summary.generated_at)``"
$lines += "- lookback_days: ``$($summary.lookback_days)``"
$lines += "- total_events: ``$($summary.total_events)``"
$lines += "- scenarios: ``$($summary.scenarios)``"
$lines += "- recommendation_count: ``$($recommendations.Count)``"
$lines += "- apply_policy: ``$($summary.apply_policy)``"
$lines += ""
$lines += "## Recommendations"
$lines += ""

if ($recommendations.Count -eq 0) {
    $lines += "- No threshold adjustments suggested for current telemetry window."
} else {
    foreach ($r in $recommendations) {
        $lines += "- scenario=``$($r.scenario_key)`` param=``$($r.parameter)`` current=``$($r.current_value)`` suggested=``$($r.suggested_value)`` reason=``$($r.reason)``"
    }
}

$lines -join "`n" | Set-Content -LiteralPath $OutputMarkdownPath -Encoding UTF8

[pscustomobject]@{
    ok = $true
    output_json = $OutputJsonPath
    output_markdown = $OutputMarkdownPath
    total_events = $events.Count
    recommendations = $recommendations.Count
} | ConvertTo-Json -Depth 10
