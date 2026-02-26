# Auto-extracted router module. Keep function bodies behavior-identical.

function Normalize-Key {
    param([string]$InputText)
    if (-not $InputText) { return "" }
    return ($InputText.Trim().Replace("\", "/")).ToLowerInvariant()
}

function Get-RoutingPromptNormalization {
    param([string]$PromptText)

    $original = if ($PromptText) { [string]$PromptText } else { "" }
    $originalLower = $original.ToLowerInvariant()
    $normalized = $original
    $prefixDetected = $false
    $prefixToken = $null

    # Normalize only explicit VCO invocation tokens and keep user intent text unchanged.
    $prefixPattern = '^\s*(?<prefix>\$vibe|/vibe)(?![a-z0-9_])(?<trail>\s*[:：]?\s*)'
    $match = [Regex]::Match($original, $prefixPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($match.Success) {
        $prefixDetected = $true
        $prefixToken = [string]$match.Groups["prefix"].Value
        $normalized = $original.Substring($match.Length)
    }

    $normalized = $normalized.TrimStart()
    if (-not $normalized) {
        $normalized = $original.TrimStart()
    }

    return [pscustomobject]@{
        original = $original
        original_lower = $originalLower
        normalized = $normalized
        normalized_lower = $normalized.ToLowerInvariant()
        prefix_detected = $prefixDetected
        prefix_token = if ($prefixToken) { $prefixToken.ToLowerInvariant() } else { $null }
        changed = ($originalLower -ne $normalized.ToLowerInvariant())
    }
}

function Get-RoutingPromptLower {
    param([string]$PromptText)

    $normalization = Get-RoutingPromptNormalization -PromptText $PromptText
    return [string]$normalization.normalized_lower
}

function Resolve-Alias {
    param(
        [string]$Skill,
        [object]$AliasMap
    )

    if (-not $Skill) {
        return [pscustomobject]@{
            input = $null
            normalized = $null
            canonical = $null
            alias_hit = $false
        }
    }

    $normalized = Normalize-Key -InputText $Skill
    $canonical = $normalized
    $aliasHit = $false

    $keys = $AliasMap.aliases.PSObject.Properties.Name
    if ($keys -contains $normalized) {
        $canonical = [string]$AliasMap.aliases.$normalized
        $aliasHit = $true
    } else {
        $leaf = $normalized.Split("/")[-1]
        if ($keys -contains $leaf) {
            $canonical = [string]$AliasMap.aliases.$leaf
            $aliasHit = $true
        } elseif ($leaf -match "^(.+)/skill\.md$") {
            $trimmed = $Matches[1]
            if ($keys -contains $trimmed) {
                $canonical = [string]$AliasMap.aliases.$trimmed
                $aliasHit = $true
            }
        }
    }

    return [pscustomobject]@{
        input = $Skill
        normalized = $normalized
        canonical = $canonical
        alias_hit = $aliasHit
    }
}

function Test-KeywordHit {
    param(
        [string]$PromptLower,
        [string]$Keyword
    )

    if (-not $PromptLower -or -not $Keyword) { return $false }
    $needle = $Keyword.ToLowerInvariant()
    if (-not $needle) { return $false }

    # CJK terms are best handled as substring matches.
    if ([Regex]::IsMatch($needle, "[\p{IsCJKUnifiedIdeographs}]")) {
        return $PromptLower.Contains($needle)
    }

    # ASCII-like terms should match on token boundaries to reduce cross-pack noise.
    if ([Regex]::IsMatch($needle, "[a-z0-9]")) {
        $escaped = [Regex]::Escape($needle)
        return [Regex]::IsMatch($PromptLower, "(?<![a-z0-9])$escaped(?![a-z0-9])")
    }

    return $PromptLower.Contains($needle)
}

function Get-KeywordRatio {
    param(
        [string]$PromptLower,
        [string[]]$Keywords
    )

    if (-not $Keywords -or $Keywords.Count -eq 0) { return 0.0 }
    $matched = 0
    foreach ($k in $Keywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword $k) {
            $matched++
        }
    }

    if ($matched -le 0) { return 0.0 }
    $denominator = [Math]::Min([double]$Keywords.Count, 4.0)
    if ($denominator -le 0) { return 0.0 }
    return [Math]::Min(1.0, ($matched / $denominator))
}

function Get-TriggerKeywordScore {
    param(
        [string]$PromptLower,
        [string[]]$Keywords
    )

    return Get-KeywordRatio -PromptLower $PromptLower -Keywords $Keywords
}

function Get-IntentScore {
    param(
        [string]$PromptLower,
        [string]$PackId,
        [string[]]$Candidates
    )

    $score = 0.0
    $packTokens = $PackId.Split("-")
    foreach ($token in $packTokens) {
        if ($token.Length -ge 3 -and (Test-KeywordHit -PromptLower $PromptLower -Keyword $token)) {
            $score += 0.35
        }
    }

    foreach ($c in $Candidates) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword $c) {
            $score += 0.25
        }
    }

    return [Math]::Min(1.0, $score)
}

function Get-WorkspaceSignalScore {
    param(
        [string]$PromptLower,
        [string]$RequestedCanonical,
        [string[]]$Candidates
    )

    if ($RequestedCanonical -and ($Candidates -contains $RequestedCanonical)) {
        return 1.0
    }

    $hits = 0
    foreach ($c in $Candidates) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword $c) {
            $hits++
        }
    }
    if ($hits -gt 0) { return 0.6 }
    return 0.0
}

function Get-CandidateNameMatchScore {
    param(
        [string]$PromptLower,
        [string]$Candidate
    )

    if (-not $Candidate) { return 0.0 }
    $variants = @(
        $Candidate,
        $Candidate.Replace("-", " "),
        $Candidate.Replace("-", ""),
        $Candidate.Replace("_", " ")
    ) | Select-Object -Unique

    foreach ($v in $variants) {
        if ($v -and (Test-KeywordHit -PromptLower $PromptLower -Keyword $v)) {
            return 1.0
        }
    }

    return 0.0
}

function Get-SkillKeywordScore {
    param(
        [string]$PromptLower,
        [string]$Candidate,
        [object]$SkillKeywordIndex
    )

    if (-not $SkillKeywordIndex -or -not $SkillKeywordIndex.skills) { return 0.0 }
    $keys = @($SkillKeywordIndex.skills.PSObject.Properties.Name)
    if (-not ($keys -contains $Candidate)) { return 0.0 }

    $entry = $SkillKeywordIndex.skills.$Candidate
    if (-not $entry -or -not $entry.keywords) { return 0.0 }

    return Get-KeywordRatio -PromptLower $PromptLower -Keywords @($entry.keywords)
}

function Get-PackSkillSignalScore {
    param(
        [string]$PromptLower,
        [string[]]$Candidates,
        [object]$SkillKeywordIndex
    )

    if (-not $Candidates -or $Candidates.Count -eq 0) { return 0.0 }

    $maxScore = 0.0
    foreach ($candidate in $Candidates) {
        $score = Get-SkillKeywordScore -PromptLower $PromptLower -Candidate $candidate -SkillKeywordIndex $SkillKeywordIndex
        if ([double]$score -gt [double]$maxScore) {
            $maxScore = [double]$score
        }
    }

    return [Math]::Min(1.0, $maxScore)
}

function Get-HashHex {
    param(
        [string]$InputText,
        [string]$Algorithm = "SHA256"
    )

    if (-not $InputText) { return "" }
    $algo = [System.Security.Cryptography.HashAlgorithm]::Create($Algorithm)
    if (-not $algo) { return "" }

    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
        $hashBytes = $algo.ComputeHash($bytes)
        return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
    } finally {
        $algo.Dispose()
    }
}

function Get-LanguageMixTag {
    param([string]$PromptText)

    if (-not $PromptText) { return "unknown" }

    $cjkHits = ([Regex]::Matches($PromptText, "[\p{IsCJKUnifiedIdeographs}]")).Count
    $latinHits = ([Regex]::Matches($PromptText, "[A-Za-z]")).Count

    if ($cjkHits -gt 0 -and $latinHits -gt 0) { return "mixed" }
    if ($cjkHits -gt 0) { return "cjk" }
    if ($latinHits -gt 0) { return "latin" }
    return "other"
}

function Get-CpuBucket {
    $cores = [Environment]::ProcessorCount
    if ($cores -le 4) { return "small" }
    if ($cores -le 8) { return "medium" }
    if ($cores -le 16) { return "large" }
    return "xlarge"
}

function Test-ExplicitCommandHint {
    param([string]$PromptText)
    if (-not $PromptText) { return $false }
    return [Regex]::IsMatch($PromptText, "^\s*(/|sc:|\$vibe\b|vibe\b)", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Test-OverlayConfirmRequired {
    param([object]$Result)

    if (-not $Result) { return $false }
    if ($Result.heartbeat_advice -and [bool]$Result.heartbeat_advice.confirm_required) { return $true }
    if ($Result.deep_discovery_advice -and [bool]$Result.deep_discovery_advice.confirm_required) { return $true }
    if ($Result.openspec_advice -and [string]$Result.openspec_advice.enforcement -eq "confirm_required") { return $true }
    if ($Result.prompt_overlay_advice -and [bool]$Result.prompt_overlay_advice.confirm_required) { return $true }
    if ($Result.data_scale_advice -and [bool]$Result.data_scale_advice.confirm_required) { return $true }
    if ($Result.quality_debt_advice -and [bool]$Result.quality_debt_advice.confirm_required) { return $true }
    if ($Result.framework_interop_advice -and [bool]$Result.framework_interop_advice.confirm_required) { return $true }
    if ($Result.ml_lifecycle_advice -and [bool]$Result.ml_lifecycle_advice.confirm_required) { return $true }
    if ($Result.python_clean_code_advice -and [bool]$Result.python_clean_code_advice.confirm_required) { return $true }
    if ($Result.system_design_advice -and [bool]$Result.system_design_advice.confirm_required) { return $true }
    if ($Result.cuda_kernel_advice -and [bool]$Result.cuda_kernel_advice.confirm_required) { return $true }
    return $false
}



