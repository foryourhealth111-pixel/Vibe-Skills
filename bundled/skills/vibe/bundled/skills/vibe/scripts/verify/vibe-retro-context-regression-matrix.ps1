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

function Test-KeywordHit {
    param(
        [string]$TextLower,
        [string]$Keyword
    )

    if (-not $TextLower -or -not $Keyword) { return $false }
    $needle = $Keyword.ToLowerInvariant()
    if (-not $needle) { return $false }

    if ([Regex]::IsMatch($needle, "[\p{IsCJKUnifiedIdeographs}]")) {
        return $TextLower.Contains($needle)
    }

    if ([Regex]::IsMatch($needle, "[a-z0-9]")) {
        $escaped = [Regex]::Escape($needle)
        return [Regex]::IsMatch($TextLower, "(?<![a-z0-9])$escaped(?![a-z0-9])")
    }

    return $TextLower.Contains($needle)
}

function Get-ContextRetroTrigger {
    param(
        [double]$RetryCount10m,
        [double]$FallbackRate,
        [double]$ContextPressure,
        [double]$RouteStabilityPack,
        [double]$RouteStabilitySkill,
        [double]$TopGap
    )

    $reasons = New-Object System.Collections.Generic.List[string]

    if ($RetryCount10m -ge 3) { $reasons.Add("retry_spike") }
    if ($FallbackRate -ge 0.20) { $reasons.Add("fallback_frequency") }
    if ($ContextPressure -ge 0.75) { $reasons.Add("context_budget_pressure") }
    if ($RouteStabilityPack -lt 0.80) { $reasons.Add("route_instability_pack") }
    if ($RouteStabilitySkill -lt 0.70) { $reasons.Add("route_instability_skill") }
    if ($TopGap -lt 0.03) { $reasons.Add("route_ambiguity_gap") }

    return [pscustomobject]@{
        triggered = ($reasons.Count -gt 0)
        reasons   = @($reasons)
    }
}

function Get-CfClassification {
    param([string]$EvidenceText)

    $textLower = if ($EvidenceText) { $EvidenceText.ToLowerInvariant() } else { "" }

    $patterns = @(
        [pscustomobject]@{
            id = "CF-1"
            label = "Attention dilution / lost-in-middle"
            keywords = @("lost in the middle", "middle of conversation", "missed requirement in middle", "attention dilution", "context center drop", "mid-context omission")
        },
        [pscustomobject]@{
            id = "CF-2"
            label = "Context poisoning"
            keywords = @("stale context", "contradictory state", "outdated summary", "wrong old decision", "context poisoning", "state contamination")
        },
        [pscustomobject]@{
            id = "CF-3"
            label = "Observation bloat"
            keywords = @("tool output too large", "huge logs", "verbose output", "observation dominates", "observation bloat", "token-heavy logs")
        },
        [pscustomobject]@{
            id = "CF-4"
            label = "Memory mismatch"
            keywords = @("retrieval irrelevant", "missed relevant memory", "wrong retrieval", "rag mismatch", "memory mismatch", "retrieval drift")
        },
        [pscustomobject]@{
            id = "CF-5"
            label = "Tool contract ambiguity"
            keywords = @("tool schema ambiguous", "wrong parameter", "tool contract unclear", "misused tool args", "contract ambiguity", "argument mismatch")
        },
        [pscustomobject]@{
            id = "CF-6"
            label = "Evaluation blind spot"
            keywords = @("no rubric", "weak verification", "accepted without checks", "missing evaluation criteria", "evaluation blind spot", "no quality gate")
        }
    )

    $scores = @()
    foreach ($p in $patterns) {
        $hitCount = 0
        foreach ($k in $p.keywords) {
            if (Test-KeywordHit -TextLower $textLower -Keyword $k) {
                $hitCount++
            }
        }

        $denominator = [Math]::Min([double]$p.keywords.Count, 5.0)
        $score = if ($denominator -gt 0) { [Math]::Round(($hitCount / $denominator), 4) } else { 0.0 }

        $scores += [pscustomobject]@{
            id      = $p.id
            label   = $p.label
            hits    = $hitCount
            score   = $score
            order   = [array]::IndexOf(($patterns.id), $p.id)
        }
    }

    $ranked = $scores | Sort-Object @{Expression = "score"; Descending = $true}, @{Expression = "order"; Ascending = $true}
    $top = $ranked | Select-Object -First 1
    $second = $ranked | Select-Object -Skip 1 -First 1
    $gap = [Math]::Round(([double]$top.score - [double]$second.score), 4)

    $confidence = "low"
    if ([double]$top.score -ge 0.60) { $confidence = "high" }
    elseif ([double]$top.score -ge 0.30) { $confidence = "medium" }

    return [pscustomobject]@{
        top_id     = $top.id
        top_label  = $top.label
        top_score  = [double]$top.score
        top_hits   = [int]$top.hits
        second_id  = $second.id
        second_score = [double]$second.score
        score_gap  = $gap
        confidence = $confidence
        ranked     = $ranked
    }
}

$results = @()

Write-Host "=== Context Retro Trigger Threshold Matrix ==="

$triggerCases = @(
    [pscustomobject]@{ name = "healthy"; retry = 1; fallback = 0.05; pressure = 0.45; pack = 0.95; skill = 0.90; gap = 0.22; expected = $false; expected_reason = $null },
    [pscustomobject]@{ name = "threshold_retry_eq"; retry = 3.0; fallback = 0.05; pressure = 0.45; pack = 0.95; skill = 0.90; gap = 0.22; expected = $true; expected_reason = "retry_spike" },
    [pscustomobject]@{ name = "threshold_fallback_eq"; retry = 1; fallback = 0.20; pressure = 0.45; pack = 0.95; skill = 0.90; gap = 0.22; expected = $true; expected_reason = "fallback_frequency" },
    [pscustomobject]@{ name = "threshold_pressure_eq"; retry = 1; fallback = 0.05; pressure = 0.75; pack = 0.95; skill = 0.90; gap = 0.22; expected = $true; expected_reason = "context_budget_pressure" },
    [pscustomobject]@{ name = "threshold_stability_gap_eq"; retry = 1; fallback = 0.05; pressure = 0.45; pack = 0.80; skill = 0.70; gap = 0.03; expected = $false; expected_reason = $null },
    [pscustomobject]@{ name = "threshold_pack_below"; retry = 1; fallback = 0.05; pressure = 0.45; pack = 0.79; skill = 0.90; gap = 0.22; expected = $true; expected_reason = "route_instability_pack" },
    [pscustomobject]@{ name = "threshold_skill_below"; retry = 1; fallback = 0.05; pressure = 0.45; pack = 0.95; skill = 0.69; gap = 0.22; expected = $true; expected_reason = "route_instability_skill" },
    [pscustomobject]@{ name = "threshold_gap_below"; retry = 1; fallback = 0.05; pressure = 0.45; pack = 0.95; skill = 0.90; gap = 0.029; expected = $true; expected_reason = "route_ambiguity_gap" },
    [pscustomobject]@{ name = "retry_spike"; retry = 4; fallback = 0.10; pressure = 0.50; pack = 0.92; skill = 0.88; gap = 0.15; expected = $true; expected_reason = "retry_spike" },
    [pscustomobject]@{ name = "fallback_frequency"; retry = 1; fallback = 0.28; pressure = 0.40; pack = 0.91; skill = 0.87; gap = 0.16; expected = $true; expected_reason = "fallback_frequency" },
    [pscustomobject]@{ name = "context_pressure"; retry = 2; fallback = 0.08; pressure = 0.82; pack = 0.90; skill = 0.86; gap = 0.19; expected = $true; expected_reason = "context_budget_pressure" },
    [pscustomobject]@{ name = "route_instability"; retry = 2; fallback = 0.09; pressure = 0.55; pack = 0.68; skill = 0.64; gap = 0.02; expected = $true; expected_reason = "route_instability_pack" }
)

foreach ($c in $triggerCases) {
    $actual = Get-ContextRetroTrigger -RetryCount10m $c.retry -FallbackRate $c.fallback -ContextPressure $c.pressure -RouteStabilityPack $c.pack -RouteStabilitySkill $c.skill -TopGap $c.gap
    $results += Assert-True -Condition ($actual.triggered -eq $c.expected) -Message "[trigger][$($c.name)] expected=$($c.expected), actual=$($actual.triggered)"
    if ($c.expected_reason) {
        $results += Assert-True -Condition (@($actual.reasons) -contains $c.expected_reason) -Message "[trigger][$($c.name)] includes reason '$($c.expected_reason)'"
    }
}

Write-Host ""
Write-Host "=== CF Classification Stability Matrix ==="

$cfCases = @(
    [pscustomobject]@{ name = "cf1-en"; expected = "CF-1"; text = "Long chat: requirement in the middle of conversation was missed. This is a lost in the middle attention dilution case." },
    [pscustomobject]@{ name = "cf2-en"; expected = "CF-2"; text = "Agent reused outdated summary and stale context. Old decision contradicted new requirement." },
    [pscustomobject]@{ name = "cf3-en"; expected = "CF-3"; text = "Tool output too large with huge logs; verbose output dominates observation tokens." },
    [pscustomobject]@{ name = "cf4-en"; expected = "CF-4"; text = "Retrieval irrelevant and missed relevant memory. This is a RAG mismatch with wrong retrieval." },
    [pscustomobject]@{ name = "cf5-en"; expected = "CF-5"; text = "Tool schema ambiguous, wrong parameter selected, tool contract unclear." },
    [pscustomobject]@{ name = "cf6-en"; expected = "CF-6"; text = "No rubric, weak verification, accepted without checks and missing evaluation criteria." },
    [pscustomobject]@{ name = "cf1-noise"; expected = "CF-1"; text = "There are large logs too, but the dominant issue is lost in the middle and a middle of conversation omission." },
    [pscustomobject]@{ name = "cf2-noise"; expected = "CF-2"; text = "Some verification gaps exist, but the real issue is stale context and context poisoning from outdated summary." },
    [pscustomobject]@{ name = "cf3-noise"; expected = "CF-3"; text = "Retrieval had minor drift, yet huge logs and tool output too large dominate the context." },
    [pscustomobject]@{ name = "cf4-noise"; expected = "CF-4"; text = "Prompt quality is okay; memory mismatch appears because retrieval irrelevant documents replaced key evidence." },
    [pscustomobject]@{ name = "cf5-noise"; expected = "CF-5"; text = "Context is long, but failures came from tool schema ambiguous contract and wrong parameter wiring." },
    [pscustomobject]@{ name = "cf6-noise"; expected = "CF-6"; text = "Tool calls succeeded, however accepted without checks and no rubric caused an evaluation blind spot." }
)

foreach ($c in $cfCases) {
    $r1 = Get-CfClassification -EvidenceText $c.text
    $r2 = Get-CfClassification -EvidenceText $c.text

    $results += Assert-True -Condition ($r1.top_id -eq $c.expected) -Message "[cf][$($c.name)] expected=$($c.expected), actual=$($r1.top_id)"
    $results += Assert-True -Condition ($r1.top_id -eq $r2.top_id) -Message "[cf][$($c.name)] deterministic top_id"
    $results += Assert-True -Condition ($r1.score_gap -ge 0.0) -Message "[cf][$($c.name)] score gap is valid ($($r1.score_gap))"
    $results += Assert-True -Condition ($r1.confidence -in @("medium", "high")) -Message "[cf][$($c.name)] confidence >= medium (actual=$($r1.confidence))"
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

Write-Host "Context retro regression matrix passed."
exit 0
