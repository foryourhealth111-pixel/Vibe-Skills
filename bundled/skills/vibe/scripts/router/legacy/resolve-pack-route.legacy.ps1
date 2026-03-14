param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [ValidateSet("M", "L", "XL")]
    [string]$Grade = "M",
    [ValidateSet("planning", "coding", "review", "debug", "research")]
    [string]$TaskType = "planning",
    [string]$RequestedSkill
)

$ErrorActionPreference = "Stop"

function Normalize-Key {
    param([string]$InputText)
    if (-not $InputText) { return "" }
    return ($InputText.Trim().Replace("\", "/")).ToLowerInvariant()
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
    return [Regex]::IsMatch($PromptText, '^\s*(/|sc:|\$vibe\b|vibe\b)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Test-OverlayConfirmRequired {
    param([object]$Result)

    if (-not $Result) { return $false }
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

function Write-ObservabilityRouteEvent {
    param(
        [string]$PromptText,
        [object]$Result,
        [object]$ObservabilityPolicy,
        [string]$RepoRoot
    )

    if (-not $ObservabilityPolicy -or -not [bool]$ObservabilityPolicy.enabled) { return $null }
    if (-not $Result) { return $null }
    if (-not $ObservabilityPolicy.telemetry -or -not [bool]$ObservabilityPolicy.telemetry.write_jsonl) { return $null }

    $mode = if ($ObservabilityPolicy.mode) { [string]$ObservabilityPolicy.mode } else { "shadow" }
    $sampleRates = if ($ObservabilityPolicy.telemetry.sample_rates) { $ObservabilityPolicy.telemetry.sample_rates } else { $null }
    $sampleRate = 1.0
    if ($sampleRates) {
        $keys = @($sampleRates.PSObject.Properties.Name)
        if ($keys -contains $mode) {
            $sampleRate = [double]$sampleRates.$mode
        }
    }
    $sampleRate = [Math]::Max(0.0, [Math]::Min(1.0, $sampleRate))

    $forceCapture = $false
    if ($ObservabilityPolicy.telemetry.force_capture) {
        $force = $ObservabilityPolicy.telemetry.force_capture
        if ($force.route_modes -and (@($force.route_modes) -contains [string]$Result.route_mode)) {
            $forceCapture = $true
        }
        if (-not $forceCapture -and [bool]$force.overlay_confirm_required -and (Test-OverlayConfirmRequired -Result $Result)) {
            $forceCapture = $true
        }
    }

    if (-not $forceCapture -and $sampleRate -lt 1.0) {
        $draw = [double](Get-Random -Minimum 0.0 -Maximum 1.0)
        if ($draw -gt $sampleRate) {
            return $null
        }
    }

    $profilePolicy = $ObservabilityPolicy.profile_dimensions
    $userPolicy = $ObservabilityPolicy.user_dimensions

    $osText = [string][Environment]::OSVersion.Platform
    $shellText = "powershell-{0}" -f $PSVersionTable.PSVersion.Major
    $cpuBucket = Get-CpuBucket
    $locale = "unknown"
    try {
        $locale = (Get-Culture).Name
    } catch { }
    $proxyHint = [bool]($env:HTTP_PROXY -or $env:HTTPS_PROXY -or $env:ALL_PROXY)

    $envParts = @()
    if ($profilePolicy -and [bool]$profilePolicy.include_os) { $envParts += "os=$osText" }
    if ($profilePolicy -and [bool]$profilePolicy.include_shell) { $envParts += "shell=$shellText" }
    if ($profilePolicy -and [bool]$profilePolicy.include_cpu_bucket) { $envParts += "cpu=$cpuBucket" }
    if ($profilePolicy -and [bool]$profilePolicy.include_locale) { $envParts += "locale=$locale" }
    if ($profilePolicy -and [bool]$profilePolicy.include_proxy_hint) { $envParts += "proxy=$proxyHint" }
    $envProfileRaw = ($envParts -join "|")
    $envProfileId = (Get-HashHex -InputText $envProfileRaw)
    if ($envProfileId.Length -gt 12) { $envProfileId = $envProfileId.Substring(0, 12) }

    $languageMix = if ($userPolicy -and [bool]$userPolicy.include_language_mix) { Get-LanguageMixTag -PromptText $PromptText } else { "unknown" }
    $explicitCommand = if ($userPolicy -and [bool]$userPolicy.include_explicit_command_hint) { Test-ExplicitCommandHint -PromptText $PromptText } else { $false }

    $userKey = "anonymous"
    if ($userPolicy -and [bool]$userPolicy.include_user_hash) {
        $rawUser = if ($env:USERNAME) { [string]$env:USERNAME } elseif ($env:USER) { [string]$env:USER } else { "unknown-user" }
        $userKey = Get-HashHex -InputText $rawUser
        if ($userKey.Length -gt 12) { $userKey = $userKey.Substring(0, 12) }
    }

    $selectedPack = if ($Result.selected) { [string]$Result.selected.pack_id } else { "none" }
    $selectedSkill = if ($Result.selected) { [string]$Result.selected.skill } else { "none" }
    $scenarioKey = "{0}|{1}|{2}|{3}|{4}|{5}" -f [string]$Result.task_type, [string]$Result.grade, [string]$Result.route_mode, $selectedPack, $languageMix, $envProfileId

    $storePromptRaw = [bool]$ObservabilityPolicy.telemetry.store_prompt_raw
    $promptExcerptMax = [int]$ObservabilityPolicy.telemetry.prompt_excerpt_max_chars
    $promptExcerpt = $null
    if ($storePromptRaw -and $promptExcerptMax -gt 0 -and $PromptText) {
        $len = [Math]::Min($promptExcerptMax, $PromptText.Length)
        $promptExcerpt = $PromptText.Substring(0, $len)
    }

    $event = [pscustomobject]@{
        timestamp_utc = [DateTime]::UtcNow.ToString("o")
        schema_version = if ($ObservabilityPolicy.event_schema_version) { [string]$ObservabilityPolicy.event_schema_version } else { "v1" }
        mode = $mode
        scenario_key = $scenarioKey
        environment_profile_id = $envProfileId
        user_profile_id = $userKey
        language_mix = $languageMix
        explicit_command_hint = [bool]$explicitCommand
        prompt_hash = Get-HashHex -InputText ([string]$PromptText)
        prompt_excerpt = $promptExcerpt
        route = [pscustomobject]@{
            grade = [string]$Result.grade
            task_type = [string]$Result.task_type
            route_mode = [string]$Result.route_mode
            route_reason = [string]$Result.route_reason
            confidence = [double]$Result.confidence
            top1_top2_gap = [double]$Result.top1_top2_gap
            candidate_signal = [double]$Result.candidate_signal
            selected_pack = $selectedPack
            selected_skill = $selectedSkill
        }
        overlays = [pscustomobject]@{
            ai_rerank_triggered = [bool]($Result.ai_rerank_advice -and $Result.ai_rerank_advice.trigger -and $Result.ai_rerank_advice.trigger.active)
            ai_rerank_would_override = [bool]($Result.ai_rerank_advice -and $Result.ai_rerank_advice.would_override)
            ai_rerank_route_override = [bool]$Result.ai_rerank_route_override
            prompt_confirm_required = [bool]($Result.prompt_overlay_advice -and $Result.prompt_overlay_advice.confirm_required)
            data_scale_confirm_required = [bool]($Result.data_scale_advice -and $Result.data_scale_advice.confirm_required)
            quality_debt_confirm_required = [bool]($Result.quality_debt_advice -and $Result.quality_debt_advice.confirm_required)
            framework_interop_confirm_required = [bool]($Result.framework_interop_advice -and $Result.framework_interop_advice.confirm_required)
            ml_lifecycle_confirm_required = [bool]($Result.ml_lifecycle_advice -and $Result.ml_lifecycle_advice.confirm_required)
            python_clean_code_confirm_required = [bool]($Result.python_clean_code_advice -and $Result.python_clean_code_advice.confirm_required)
            system_design_confirm_required = [bool]($Result.system_design_advice -and $Result.system_design_advice.confirm_required)
            cuda_kernel_confirm_required = [bool]($Result.cuda_kernel_advice -and $Result.cuda_kernel_advice.confirm_required)
            any_confirm_required = (Test-OverlayConfirmRequired -Result $Result)
        }
    }

    $telemetryRel = if ($ObservabilityPolicy.telemetry.output_dir) { [string]$ObservabilityPolicy.telemetry.output_dir } else { "outputs/telemetry" }
    $prefix = if ($ObservabilityPolicy.telemetry.file_prefix) { [string]$ObservabilityPolicy.telemetry.file_prefix } else { "route-events" }
    $outputDir = Join-Path $RepoRoot $telemetryRel
    $fileName = "{0}-{1}.jsonl" -f $prefix, (Get-Date -Format "yyyyMMdd")
    $outputPath = Join-Path $outputDir $fileName

    try {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        ($event | ConvertTo-Json -Depth 12 -Compress) | Add-Content -LiteralPath $outputPath -Encoding UTF8
        return [pscustomobject]@{
            wrote = $true
            path = $outputPath
        }
    } catch {
        if ($ObservabilityPolicy.fallback_behavior -and [string]$ObservabilityPolicy.fallback_behavior.on_write_error -eq "continue_without_telemetry") {
            return [pscustomobject]@{
                wrote = $false
                error = $_.Exception.Message
            }
        }
        throw
    }
}

function Get-RoutingRuleForCandidate {
    param(
        [string]$Candidate,
        [object]$RoutingRules
    )

    if (-not $RoutingRules -or -not $RoutingRules.skills -or -not $Candidate) {
        return $null
    }

    $keys = @($RoutingRules.skills.PSObject.Properties.Name)
    if ($keys -contains $Candidate) {
        return $RoutingRules.skills.$Candidate
    }

    return $null
}

function Test-RuleTaskAllowed {
    param(
        [object]$Rule,
        [string]$TaskType
    )

    if (-not $Rule -or -not $Rule.task_allow) { return $true }
    $allowed = @($Rule.task_allow)
    if ($allowed.Count -eq 0) { return $true }
    return ($allowed -contains $TaskType)
}

function Get-CanonicalForTaskHit {
    param(
        [object]$Rule,
        [string]$TaskType
    )

    if (-not $Rule -or -not $Rule.canonical_for_task) { return 0.0 }
    $canonical = @($Rule.canonical_for_task)
    if ($canonical -contains $TaskType) { return 1.0 }
    return 0.0
}

function Get-PackDefaultCandidate {
    param(
        [object]$Pack,
        [string]$TaskType,
        [string[]]$PreferredCandidates,
        [string[]]$AllCandidates
    )

    if (-not $Pack -or -not $Pack.defaults_by_task) { return $null }

    $taskKeys = @($Pack.defaults_by_task.PSObject.Properties.Name)
    if (-not ($taskKeys -contains $TaskType)) { return $null }

    $defaultSkill = [string]$Pack.defaults_by_task.$TaskType
    if (-not $defaultSkill) { return $null }

    if ($PreferredCandidates -and ($PreferredCandidates -contains $defaultSkill)) {
        return $defaultSkill
    }

    if ($AllCandidates -and ($AllCandidates -contains $defaultSkill)) {
        return $defaultSkill
    }

    return $null
}

function Get-DeterministicSampleValue {
    param([string]$SeedText)

    if (-not $SeedText) { return 0.0 }
    $hash = Get-HashHex -InputText $SeedText
    if (-not $hash -or $hash.Length -lt 8) { return 0.0 }

    $hex = $hash.Substring(0, 8)
    $numeric = [Convert]::ToUInt32($hex, 16)
    $ratio = [double]$numeric / [double][uint32]::MaxValue
    return [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $ratio)), 6)
}

function Test-AiRerankScope {
    param(
        [object]$AiRerankPolicy,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode
    )

    $reasons = @()
    if (-not $AiRerankPolicy -or -not [bool]$AiRerankPolicy.enabled) {
        return [pscustomobject]@{
            applicable = $false
            reasons = @("policy_disabled")
        }
    }

    $mode = if ($AiRerankPolicy.mode) { [string]$AiRerankPolicy.mode } else { "shadow" }
    if ($mode -eq "off") {
        return [pscustomobject]@{
            applicable = $false
            reasons = @("mode_off")
        }
    }

    $scope = $AiRerankPolicy.scope
    if (-not $scope) {
        return [pscustomobject]@{
            applicable = $true
            reasons = @("scope_default")
        }
    }

    $gradeAllow = @($scope.grade_allow)
    if ($gradeAllow.Count -gt 0 -and -not ($gradeAllow -contains $Grade)) {
        $reasons += "grade_not_allowed"
    }

    $taskAllow = @($scope.task_allow)
    if ($taskAllow.Count -gt 0 -and -not ($taskAllow -contains $TaskType)) {
        $reasons += "task_not_allowed"
    }

    $routeModeAllow = @($scope.route_mode_allow)
    if ($routeModeAllow.Count -gt 0 -and -not ($routeModeAllow -contains $RouteMode)) {
        $reasons += "route_mode_not_allowed"
    }

    if ($reasons.Count -eq 0) {
        return [pscustomobject]@{
            applicable = $true
            reasons = @("scope_match")
        }
    }

    return [pscustomobject]@{
        applicable = $false
        reasons = @($reasons)
    }
}

function Get-AiRerankTrigger {
    param(
        [string]$PromptLower,
        [double]$TopGap,
        [double]$Confidence,
        [object]$AiRerankPolicy
    )

    $trigger = if ($AiRerankPolicy.trigger) { $AiRerankPolicy.trigger } else { $null }
    $maxGap = if ($trigger -and $trigger.max_top1_top2_gap -ne $null) { [double]$trigger.max_top1_top2_gap } else { 0.0 }
    $maxConfidence = if ($trigger -and $trigger.max_confidence_for_rerank -ne $null) { [double]$trigger.max_confidence_for_rerank } else { 0.0 }

    $reasons = @()
    if ($TopGap -le $maxGap) {
        $reasons += "top_gap_low"
    }
    if ($Confidence -le $maxConfidence) {
        $reasons += "confidence_low"
    }

    $matchedGroups = @()
    if ($trigger -and $trigger.confusion_groups) {
        foreach ($group in @($trigger.confusion_groups)) {
            $groupKeywords = @($group.keywords)
            if ($groupKeywords.Count -eq 0) { continue }
            $ratio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $groupKeywords
            if ($ratio -gt 0) {
                $groupId = if ($group.id) { [string]$group.id } else { "group" }
                $matchedGroups += $groupId
            }
        }
    }

    if ($matchedGroups.Count -gt 0) {
        $reasons += "confusion_group_hit"
    }

    return [pscustomobject]@{
        active = ($reasons.Count -gt 0)
        reasons = @($reasons | Select-Object -Unique)
        matched_confusion_groups = @($matchedGroups | Select-Object -Unique)
        max_top1_top2_gap = [Math]::Round($maxGap, 4)
        max_confidence_for_rerank = [Math]::Round($maxConfidence, 4)
    }
}

function Get-AiRerankSuggestionHeuristic {
    param(
        [string]$PromptLower,
        [object[]]$TopCandidates,
        [string]$RequestedCanonical,
        [object]$AiRerankPolicy
    )

    if (-not $TopCandidates -or $TopCandidates.Count -eq 0) {
        return [pscustomobject]@{
            abstained = $true
            reason = "no_top_candidates"
            pack_id = $null
            skill = $null
            confidence = 0.0
        }
    }

    if ($RequestedCanonical) {
        $requestedHit = $TopCandidates | Where-Object { $_.selected_candidate -eq $RequestedCanonical -or (@($_.candidates) -contains $RequestedCanonical) } | Select-Object -First 1
        if ($requestedHit) {
            $requestedConfidence = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, [double]$requestedHit.candidate_signal + 0.25)), 4)
            return [pscustomobject]@{
                abstained = $false
                reason = "requested_skill_signal"
                pack_id = [string]$requestedHit.pack_id
                skill = [string]$requestedHit.selected_candidate
                confidence = $requestedConfidence
            }
        }
    }

    $trigger = if ($AiRerankPolicy.trigger) { $AiRerankPolicy.trigger } else { $null }
    if ($trigger -and $trigger.confusion_groups) {
        foreach ($group in @($trigger.confusion_groups)) {
            $groupKeywords = @($group.keywords)
            if ($groupKeywords.Count -eq 0) { continue }

            $ratio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $groupKeywords
            if ($ratio -le 0) { continue }

            $preferredPack = if ($group.preferred_pack) { [string]$group.preferred_pack } else { $null }
            if (-not $preferredPack) { continue }

            $preferredCandidate = $TopCandidates | Where-Object { [string]$_.pack_id -eq $preferredPack } | Select-Object -First 1
            if ($preferredCandidate) {
                $groupConfidence = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, [double]$preferredCandidate.candidate_signal + 0.2)), 4)
                $groupId = if ($group.id) { [string]$group.id } else { "group" }
                return [pscustomobject]@{
                    abstained = $false
                    reason = "confusion_group_preferred:$groupId"
                    pack_id = [string]$preferredCandidate.pack_id
                    skill = [string]$preferredCandidate.selected_candidate
                    confidence = $groupConfidence
                }
            }
        }
    }

    return [pscustomobject]@{
        abstained = $true
        reason = "no_strong_heuristic_signal"
        pack_id = $null
        skill = $null
        confidence = 0.0
    }
}

function Get-AiRerankAdvice {
    param(
        [string]$PromptText,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$RequestedCanonical,
        [object[]]$Ranked,
        [double]$TopGap,
        [double]$Confidence,
        [object]$AiRerankPolicy
    )

    $mode = if ($AiRerankPolicy -and $AiRerankPolicy.mode) { [string]$AiRerankPolicy.mode } else { "off" }
    $scope = Test-AiRerankScope -AiRerankPolicy $AiRerankPolicy -Grade $Grade -TaskType $TaskType -RouteMode $RouteMode
    $enabled = [bool]($AiRerankPolicy -and [bool]$AiRerankPolicy.enabled -and $mode -ne "off")

    $triggerConfig = if ($AiRerankPolicy -and $AiRerankPolicy.trigger) { $AiRerankPolicy.trigger } else { $null }
    $topK = if ($triggerConfig -and $triggerConfig.top_k -ne $null) { [Math]::Max(1, [int]$triggerConfig.top_k) } else { 3 }

    $topCandidates = @()
    if ($Ranked) {
        $topCandidates = @($Ranked | Select-Object -First $topK)
    }

    $topRows = @()
    foreach ($candidate in $topCandidates) {
        $topRows += [pscustomobject]@{
            pack_id = [string]$candidate.pack_id
            selected_skill = [string]$candidate.selected_candidate
            score = [Math]::Round([double]$candidate.score, 4)
            candidate_signal = [Math]::Round([double]$candidate.candidate_signal, 4)
            task_allowed = [bool]$candidate.task_allowed
        }
    }

    $trigger = Get-AiRerankTrigger -PromptLower $PromptLower -TopGap $TopGap -Confidence $Confidence -AiRerankPolicy $AiRerankPolicy
    $providerType = if ($AiRerankPolicy -and $AiRerankPolicy.provider -and $AiRerankPolicy.provider.type) { [string]$AiRerankPolicy.provider.type } else { "heuristic" }
    $suggestion = [pscustomobject]@{
        abstained = $true
        reason = "not_triggered"
        pack_id = $null
        skill = $null
        confidence = 0.0
    }

    if ($enabled -and $scope.applicable -and $trigger.active) {
        if ($providerType -eq "heuristic") {
            $suggestion = Get-AiRerankSuggestionHeuristic -PromptLower $PromptLower -TopCandidates $topCandidates -RequestedCanonical $RequestedCanonical -AiRerankPolicy $AiRerankPolicy
        } else {
            $suggestion = [pscustomobject]@{
                abstained = $true
                reason = "unsupported_provider:$providerType"
                pack_id = $null
                skill = $null
                confidence = 0.0
            }
        }
    }

    $safety = if ($AiRerankPolicy -and $AiRerankPolicy.safety) { $AiRerankPolicy.safety } else { $null }
    $requireTopK = if ($safety -and $safety.require_candidate_in_top_k -ne $null) { [bool]$safety.require_candidate_in_top_k } else { $true }
    $enforceTaskAllow = if ($safety -and $safety.enforce_task_allow -ne $null) { [bool]$safety.enforce_task_allow } else { $true }
    $minRerankConfidence = if ($safety -and $safety.min_rerank_confidence -ne $null) { [double]$safety.min_rerank_confidence } else { 0.55 }
    $allowAbstain = if ($safety -and $safety.allow_abstain -ne $null) { [bool]$safety.allow_abstain } else { $true }

    $candidateInTopK = $false
    $taskAllowPassed = $false
    $confidencePassed = $false
    $constraintsPassed = $false
    $selectedSuggestionCandidate = $null
    if (-not $suggestion.abstained -and $suggestion.pack_id) {
        $selectedSuggestionCandidate = $topCandidates | Where-Object { [string]$_.pack_id -eq [string]$suggestion.pack_id } | Select-Object -First 1
        $candidateInTopK = ($null -ne $selectedSuggestionCandidate)
        $taskAllowPassed = if ($enforceTaskAllow) {
            if ($selectedSuggestionCandidate) { [bool]$selectedSuggestionCandidate.task_allowed } else { $false }
        } else {
            $true
        }
        $confidencePassed = ([double]$suggestion.confidence -ge [double]$minRerankConfidence)

        $constraintsPassed = $taskAllowPassed -and $confidencePassed
        if ($requireTopK) {
            $constraintsPassed = $constraintsPassed -and $candidateInTopK
        }
    } else {
        $candidateInTopK = $allowAbstain
        $taskAllowPassed = $allowAbstain
        $confidencePassed = $allowAbstain
        $constraintsPassed = $false
    }

    $rollout = if ($AiRerankPolicy -and $AiRerankPolicy.rollout) { $AiRerankPolicy.rollout } else { $null }
    $applyModes = if ($rollout -and $rollout.apply_in_modes) { @($rollout.apply_in_modes) } else { @("soft", "strict") }
    $applyModeAllowed = ($applyModes -contains $mode)
    $sampleRate = if ($rollout -and $rollout.max_live_apply_rate -ne $null) { [double]$rollout.max_live_apply_rate } else { 1.0 }
    $sampleRate = [Math]::Max(0.0, [Math]::Min(1.0, $sampleRate))
    $sampleSeed = "{0}|{1}|{2}|{3}|{4}" -f $PromptText, $Grade, $TaskType, $RouteMode, $mode
    $sampleValue = Get-DeterministicSampleValue -SeedText $sampleSeed
    $samplePassed = ($sampleValue -le $sampleRate)

    $preserveRoutingAssignment = if ($AiRerankPolicy -and $AiRerankPolicy.preserve_routing_assignment -ne $null) { [bool]$AiRerankPolicy.preserve_routing_assignment } else { $false }
    $primaryPack = if ($topCandidates.Count -gt 0) { [string]$topCandidates[0].pack_id } else { $null }
    $changesSelection = (-not $suggestion.abstained) -and $suggestion.pack_id -and ($primaryPack -ne [string]$suggestion.pack_id)
    $applyEligible = $enabled -and $scope.applicable -and $trigger.active -and $constraintsPassed -and $applyModeAllowed -and $samplePassed -and $changesSelection
    $shadowCompare = [bool]($rollout -and $rollout.shadow_compare_in_shadow_mode)
    $wouldOverride = $false
    if ($mode -eq "shadow" -and $shadowCompare -and $enabled -and $scope.applicable -and $trigger.active -and $constraintsPassed -and $changesSelection) {
        $wouldOverride = $true
    } elseif ($applyEligible -and $preserveRoutingAssignment) {
        $wouldOverride = $true
    }
    $routeOverrideApplied = $applyEligible -and (-not $preserveRoutingAssignment)

    return [pscustomobject]@{
        enabled = $enabled
        mode = $mode
        scope_applicable = [bool]$scope.applicable
        scope_reasons = @($scope.reasons)
        trigger = [pscustomobject]@{
            active = [bool]$trigger.active
            reasons = @($trigger.reasons)
            matched_confusion_groups = @($trigger.matched_confusion_groups)
            max_top1_top2_gap = [double]$trigger.max_top1_top2_gap
            max_confidence_for_rerank = [double]$trigger.max_confidence_for_rerank
        }
        top_candidates = @($topRows)
        provider = [pscustomobject]@{
            type = $providerType
            abstained = [bool]$suggestion.abstained
            reason = [string]$suggestion.reason
            suggested_pack = $suggestion.pack_id
            suggested_skill = $suggestion.skill
            confidence = [Math]::Round([double]$suggestion.confidence, 4)
        }
        constraints = [pscustomobject]@{
            require_candidate_in_top_k = [bool]$requireTopK
            enforce_task_allow = [bool]$enforceTaskAllow
            min_rerank_confidence = [Math]::Round([double]$minRerankConfidence, 4)
            allow_abstain = [bool]$allowAbstain
            candidate_in_top_k = [bool]$candidateInTopK
            task_allow_passed = [bool]$taskAllowPassed
            confidence_passed = [bool]$confidencePassed
            passed = [bool]$constraintsPassed
        }
        rollout = [pscustomobject]@{
            preserve_routing_assignment = [bool]$preserveRoutingAssignment
            apply_mode_allowed = [bool]$applyModeAllowed
            sample_rate = [Math]::Round([double]$sampleRate, 4)
            sample_value = [Math]::Round([double]$sampleValue, 6)
            sample_passed = [bool]$samplePassed
            apply_eligible = [bool]$applyEligible
            would_override = [bool]$wouldOverride
            route_override_applied = [bool]$routeOverrideApplied
        }
        override_target_pack = $suggestion.pack_id
        override_target_skill = $suggestion.skill
        route_override_applied = [bool]$routeOverrideApplied
        would_override = [bool]$wouldOverride
    }
}

function Get-OpenSpecTaskId {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType
    )

    $raw = "{0}|{1}|{2}" -f $Grade, $TaskType, $PromptLower
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
        $hashBytes = $sha1.ComputeHash($bytes)
        $hash = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
        if ($hash.Length -ge 12) {
            return $hash.Substring(0, 12)
        }
        return $hash
    } finally {
        $sha1.Dispose()
    }
}

function Get-OpenSpecGovernanceAdvice {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedCanonical,
        [object]$OpenSpecPolicy
    )

    if (-not $OpenSpecPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            profile = "none"
            task_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            bypass_due_to_requested_skill = $false
            preserve_routing_assignment = $true
            task_id = $null
            recommended_artifact = $null
            should_upgrade_to_full = $false
            upgrade_trigger_matches = @()
        }
    }

    $mode = if ($OpenSpecPolicy.mode) { [string]$OpenSpecPolicy.mode } else { "off" }
    if ($mode -eq "off") {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            profile = "none"
            task_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            bypass_due_to_requested_skill = $false
            preserve_routing_assignment = $true
            task_id = $null
            recommended_artifact = $null
            should_upgrade_to_full = $false
            upgrade_trigger_matches = @()
        }
    }

    $profile = "none"
    if ($OpenSpecPolicy.profile_by_grade) {
        $gradeKeys = @($OpenSpecPolicy.profile_by_grade.PSObject.Properties.Name)
        if ($gradeKeys -contains $Grade) {
            $profile = [string]$OpenSpecPolicy.profile_by_grade.$Grade
        }
    }

    $taskApplicable = $false
    if ($profile -ne "none" -and $OpenSpecPolicy.required_task_types_by_profile) {
        $profileKeys = @($OpenSpecPolicy.required_task_types_by_profile.PSObject.Properties.Name)
        if ($profileKeys -contains $profile) {
            $requiredTasks = @($OpenSpecPolicy.required_task_types_by_profile.$profile)
            $taskApplicable = ($requiredTasks -contains $TaskType)
        }
    }

    $bypassDueToRequestedSkill = $false
    if ($RequestedCanonical -and $OpenSpecPolicy.exemptions -and $OpenSpecPolicy.exemptions.requested_skill_bypass) {
        $bypassDueToRequestedSkill = $true
    }

    $taskId = Get-OpenSpecTaskId -PromptLower $PromptLower -Grade $Grade -TaskType $TaskType
    $recommendedArtifact = $null
    if ($profile -eq "lite") {
        $liteDir = if ($OpenSpecPolicy.m_lite -and $OpenSpecPolicy.m_lite.directory) {
            [string]$OpenSpecPolicy.m_lite.directory
        } else {
            "openspec/micro"
        }
        $recommendedArtifact = "{0}/{1}.md" -f $liteDir.TrimEnd("/"), $taskId
    } elseif ($profile -eq "full") {
        $changesDir = if ($OpenSpecPolicy.full -and $OpenSpecPolicy.full.changes_dir) {
            [string]$OpenSpecPolicy.full.changes_dir
        } else {
            "openspec/changes"
        }
        $recommendedArtifact = "{0}/{1}" -f $changesDir.TrimEnd("/"), $taskId
    }

    $softScopeHit = $true
    if ($OpenSpecPolicy.soft_confirm_scope) {
        $scopeGrades = @()
        $scopeTasks = @()
        if ($OpenSpecPolicy.soft_confirm_scope.grades) {
            $scopeGrades = @($OpenSpecPolicy.soft_confirm_scope.grades)
        }
        if ($OpenSpecPolicy.soft_confirm_scope.task_types) {
            $scopeTasks = @($OpenSpecPolicy.soft_confirm_scope.task_types)
        }

        if ($scopeGrades.Count -gt 0 -and -not ($scopeGrades -contains $Grade)) {
            $softScopeHit = $false
        }
        if ($scopeTasks.Count -gt 0 -and -not ($scopeTasks -contains $TaskType)) {
            $softScopeHit = $false
        }
    }

    $enforcement = "none"
    $reason = "task_not_applicable"
    if ($taskApplicable -and -not $bypassDueToRequestedSkill) {
        if ($profile -eq "lite") {
            $enforcement = "advisory"
            $reason = "m_lite_card"
        } elseif ($profile -eq "full") {
            switch ($mode) {
                "strict" {
                    $enforcement = "required"
                    $reason = "full_required_strict"
                }
                "soft" {
                    if ($softScopeHit) {
                        $enforcement = "confirm_required"
                        $reason = "full_confirm_soft"
                    } else {
                        $enforcement = "advisory"
                        $reason = "full_advisory_soft_outside_scope"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "full_advisory_shadow"
                }
            }
        } else {
            $enforcement = "advisory"
            $reason = "profile_none"
        }
    } elseif ($bypassDueToRequestedSkill) {
        $reason = "requested_skill_bypass"
    }

    $upgradeMatches = @()
    if ($profile -eq "lite" -and $OpenSpecPolicy.upgrade_triggers) {
        foreach ($trigger in @($OpenSpecPolicy.upgrade_triggers)) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$trigger)) {
                $upgradeMatches += [string]$trigger
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($OpenSpecPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$OpenSpecPolicy.preserve_routing_assignment
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        profile = $profile
        task_applicable = $taskApplicable
        enforcement = $enforcement
        reason = $reason
        bypass_due_to_requested_skill = $bypassDueToRequestedSkill
        preserve_routing_assignment = $preserveRoutingAssignment
        task_id = $taskId
        recommended_artifact = $recommendedArtifact
        should_upgrade_to_full = ($upgradeMatches.Count -gt 0)
        upgrade_trigger_matches = @($upgradeMatches)
    }
}

function Get-GsdOverlayAdvice {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [object]$GsdOverlayPolicy
    )

    if (-not $GsdOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            preflight_should_apply = $false
            wave_contract_should_apply = $false
            should_apply_hook = $false
            artifacts = [pscustomobject]@{
                brownfield_directory = $null
                assumption_artifact = $null
                wave_artifact = $null
            }
        }
    }

    $enabled = $true
    if ($GsdOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$GsdOverlayPolicy.enabled
    }

    $mode = if ($GsdOverlayPolicy.mode) { [string]$GsdOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            preflight_should_apply = $false
            wave_contract_should_apply = $false
            should_apply_hook = $false
            artifacts = [pscustomobject]@{
                brownfield_directory = $null
                assumption_artifact = $null
                wave_artifact = $null
            }
        }
    }

    $taskAllow = @("planning")
    if ($GsdOverlayPolicy.task_allow) {
        $taskAllow = @($GsdOverlayPolicy.task_allow)
    }

    $gradeAllow = @("L", "XL")
    if ($GsdOverlayPolicy.grade_allow) {
        $gradeAllow = @($GsdOverlayPolicy.grade_allow)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $scopeApplicable = ($taskApplicable -and $gradeApplicable)

    $preflightApply = $scopeApplicable

    $waveEnabled = $false
    $waveXlOnly = $true
    if ($GsdOverlayPolicy.wave_contract) {
        if ($GsdOverlayPolicy.wave_contract.enabled -ne $null) {
            $waveEnabled = [bool]$GsdOverlayPolicy.wave_contract.enabled
        }
        if ($GsdOverlayPolicy.wave_contract.xl_only -ne $null) {
            $waveXlOnly = [bool]$GsdOverlayPolicy.wave_contract.xl_only
        }
    }

    $waveTaskAllowed = ($TaskType -in @("planning", "coding"))
    $waveGradeAllowed = (($Grade -eq "XL") -or (-not $waveXlOnly))
    $waveApply = ($scopeApplicable -and $waveEnabled -and $waveTaskAllowed -and $waveGradeAllowed)

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        $confirmGrades = @("XL")
        if ($GsdOverlayPolicy.assumption_gate -and $GsdOverlayPolicy.assumption_gate.confirm_required_for) {
            $confirmGrades = @($GsdOverlayPolicy.assumption_gate.confirm_required_for)
        }

        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                if ($confirmGrades -contains $Grade) {
                    $enforcement = "confirm_required"
                    $reason = "soft_confirm_scope_hit"
                } else {
                    $enforcement = "advisory"
                    $reason = "soft_advisory_outside_confirm_grade"
                }
            }
            "strict" {
                $enforcement = "required"
                $reason = "strict_required"
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($GsdOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$GsdOverlayPolicy.preserve_routing_assignment
    }

    $brownfieldDirectory = $null
    if ($GsdOverlayPolicy.brownfield_context -and $GsdOverlayPolicy.brownfield_context.directory) {
        $brownfieldDirectory = [string]$GsdOverlayPolicy.brownfield_context.directory
    }

    $assumptionArtifact = if ($GsdOverlayPolicy.assumption_gate -and $GsdOverlayPolicy.assumption_gate.artifact) {
        [string]$GsdOverlayPolicy.assumption_gate.artifact
    } else {
        "assumptions.md"
    }

    $waveArtifact = if ($GsdOverlayPolicy.wave_contract -and $GsdOverlayPolicy.wave_contract.artifact) {
        [string]$GsdOverlayPolicy.wave_contract.artifact
    } else {
        "waves.json"
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        preflight_should_apply = $preflightApply
        wave_contract_should_apply = $waveApply
        should_apply_hook = ($preflightApply -or $waveApply)
        artifacts = [pscustomobject]@{
            brownfield_directory = $brownfieldDirectory
            assumption_artifact = $assumptionArtifact
            wave_artifact = $waveArtifact
        }
    }
}

function Get-PromptOverlayAdvice {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [object]$PromptOverlayPolicy
    )

    if (-not $PromptOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            prompt_signal_hit = $false
            doc_surface_hit = $false
            ambiguity_detected = $false
            confirm_required = $false
            should_apply_hook = $false
            should_search_prompts_first = $false
            recommended_skill = $null
            matched_intent_facets = @()
            facet_matches = [pscustomobject]@{}
            prompt_signal_matches = @()
            doc_surface_matches = @()
        }
    }

    $enabled = $true
    if ($PromptOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$PromptOverlayPolicy.enabled
    }

    $mode = if ($PromptOverlayPolicy.mode) { [string]$PromptOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            prompt_signal_hit = $false
            doc_surface_hit = $false
            ambiguity_detected = $false
            confirm_required = $false
            should_apply_hook = $false
            should_search_prompts_first = $false
            recommended_skill = $null
            matched_intent_facets = @()
            facet_matches = [pscustomobject]@{}
            prompt_signal_matches = @()
            doc_surface_matches = @()
        }
    }

    $taskAllow = @("planning", "research")
    if ($PromptOverlayPolicy.task_allow) {
        $taskAllow = @($PromptOverlayPolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($PromptOverlayPolicy.grade_allow) {
        $gradeAllow = @($PromptOverlayPolicy.grade_allow)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $scopeApplicable = ($taskApplicable -and $gradeApplicable)

    $promptSignalKeywords = @("prompt", "prompts.chat", "提示词", "system prompt")
    if ($PromptOverlayPolicy.prompt_signal_keywords) {
        $promptSignalKeywords = @($PromptOverlayPolicy.prompt_signal_keywords)
    }

    $docSurfaceKeywords = @("api reference", "official docs", "responses api", "chat completions", "model limits", "官方文档")
    if ($PromptOverlayPolicy.doc_surface_keywords) {
        $docSurfaceKeywords = @($PromptOverlayPolicy.doc_surface_keywords)
    }

    $promptSignalMatches = @()
    foreach ($kw in $promptSignalKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $promptSignalMatches += [string]$kw
        }
    }

    $docSurfaceMatches = @()
    foreach ($kw in $docSurfaceKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $docSurfaceMatches += [string]$kw
        }
    }

    $promptSignalHit = ($promptSignalMatches.Count -gt 0)
    $docSurfaceHit = ($docSurfaceMatches.Count -gt 0)

    $facetMatches = [ordered]@{}
    $matchedIntentFacets = @()
    if ($PromptOverlayPolicy.intent_facets) {
        foreach ($facetName in @($PromptOverlayPolicy.intent_facets.PSObject.Properties.Name)) {
            $hits = @()
            foreach ($kw in @($PromptOverlayPolicy.intent_facets.$facetName)) {
                if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                    $hits += [string]$kw
                }
            }

            $facetMatches[[string]$facetName] = @($hits)
            if ($hits.Count -gt 0) {
                $matchedIntentFacets += [string]$facetName
            }
        }
    }

    $explicitPromptAssetIntent = ($matchedIntentFacets.Count -gt 0)
    $ambiguityDetected = ($promptSignalHit -and $docSurfaceHit -and (-not $explicitPromptAssetIntent))

    $confirmScopeHit = $scopeApplicable
    if ($PromptOverlayPolicy.confirm_scope) {
        $scopeGrades = @()
        $scopeTasks = @()
        if ($PromptOverlayPolicy.confirm_scope.grades) {
            $scopeGrades = @($PromptOverlayPolicy.confirm_scope.grades)
        }
        if ($PromptOverlayPolicy.confirm_scope.task_types) {
            $scopeTasks = @($PromptOverlayPolicy.confirm_scope.task_types)
        }

        if ($scopeGrades.Count -gt 0 -and -not ($scopeGrades -contains $Grade)) {
            $confirmScopeHit = $false
        }
        if ($scopeTasks.Count -gt 0 -and -not ($scopeTasks -contains $TaskType)) {
            $confirmScopeHit = $false
        }
    }

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                if ($ambiguityDetected -and $confirmScopeHit) {
                    $enforcement = "confirm_required"
                    $reason = "soft_confirm_doc_collision"
                } elseif ($explicitPromptAssetIntent) {
                    $enforcement = "advisory"
                    $reason = "soft_advisory_prompt_intent"
                } elseif ($promptSignalHit) {
                    $enforcement = "advisory"
                    $reason = "soft_advisory_prompt_signal"
                } else {
                    $enforcement = "advisory"
                    $reason = "soft_advisory_scope_only"
                }
            }
            "strict" {
                if ($ambiguityDetected -and $confirmScopeHit) {
                    $enforcement = "confirm_required"
                    $reason = "strict_confirm_doc_collision"
                } elseif ($promptSignalHit) {
                    $enforcement = "required"
                    $reason = "strict_required_prompt_signal"
                } else {
                    $enforcement = "required"
                    $reason = "strict_required_scope_only"
                }
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($PromptOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$PromptOverlayPolicy.preserve_routing_assignment
    }

    $recommendedSkill = $null
    if ($explicitPromptAssetIntent) {
        $recommendedSkill = "prompt-lookup"
    } elseif ($docSurfaceHit) {
        $recommendedSkill = "documentation-lookup"
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        prompt_signal_hit = $promptSignalHit
        doc_surface_hit = $docSurfaceHit
        ambiguity_detected = $ambiguityDetected
        confirm_required = (($enforcement -eq "confirm_required") -or ($enforcement -eq "required"))
        should_apply_hook = ($scopeApplicable -and ($promptSignalHit -or $explicitPromptAssetIntent))
        should_search_prompts_first = ($scopeApplicable -and $explicitPromptAssetIntent)
        recommended_skill = $recommendedSkill
        matched_intent_facets = @($matchedIntentFacets)
        facet_matches = [pscustomobject]$facetMatches
        prompt_signal_matches = @($promptSignalMatches)
        doc_surface_matches = @($docSurfaceMatches)
    }
}

function Get-MemoryGovernanceAdvice {
    param(
        [string]$Grade,
        [string]$TaskType,
        [object]$MemoryGovernancePolicy
    )

    if (-not $MemoryGovernancePolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            primary_memory = $null
            project_decision_memory = $null
            short_term_memory = $null
            long_term_memory = $null
            disabled_systems = @()
            governance_contract = [pscustomobject]@{}
            role_boundaries = [pscustomobject]@{}
        }
    }

    $enabled = $true
    if ($MemoryGovernancePolicy.enabled -ne $null) {
        $enabled = [bool]$MemoryGovernancePolicy.enabled
    }

    $mode = if ($MemoryGovernancePolicy.mode) { [string]$MemoryGovernancePolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            primary_memory = $null
            project_decision_memory = $null
            short_term_memory = $null
            long_term_memory = $null
            disabled_systems = @()
            governance_contract = [pscustomobject]@{}
            role_boundaries = [pscustomobject]@{}
        }
    }

    $taskAllow = @("planning", "coding", "review", "debug", "research")
    if ($MemoryGovernancePolicy.task_allow) {
        $taskAllow = @($MemoryGovernancePolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($MemoryGovernancePolicy.grade_allow) {
        $gradeAllow = @($MemoryGovernancePolicy.grade_allow)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $scopeApplicable = ($taskApplicable -and $gradeApplicable)

    $taskDefaults = $null
    if ($MemoryGovernancePolicy.defaults_by_task) {
        $taskKeys = @($MemoryGovernancePolicy.defaults_by_task.PSObject.Properties.Name)
        if ($taskKeys -contains $TaskType) {
            $taskDefaults = $MemoryGovernancePolicy.defaults_by_task.$TaskType
        }
    }

    $primaryMemory = if ($taskDefaults -and $taskDefaults.primary) { [string]$taskDefaults.primary } else { "state_store" }
    $projectDecisionMemory = if ($taskDefaults -and $taskDefaults.project_decisions) { [string]$taskDefaults.project_decisions } else { "serena" }
    $shortTermMemory = if ($taskDefaults -and $taskDefaults.short_cache) { [string]$taskDefaults.short_cache } else { "ruflo" }
    $longTermMemory = if ($taskDefaults -and $taskDefaults.long_term) { [string]$taskDefaults.long_term } else { "cognee" }

    $disabledSystems = @()
    if ($MemoryGovernancePolicy.role_boundaries -and $MemoryGovernancePolicy.role_boundaries.episodic_memory) {
        $episodicBoundary = $MemoryGovernancePolicy.role_boundaries.episodic_memory
        if ($episodicBoundary.status -eq "disabled") {
            if ($episodicBoundary.canonical_name) {
                $disabledSystems += [string]$episodicBoundary.canonical_name
            } else {
                $disabledSystems += "episodic-memory"
            }
        }
    }

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                $enforcement = "advisory"
                $reason = "soft_advisory"
            }
            "strict" {
                $enforcement = "required"
                $reason = "strict_required"
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($MemoryGovernancePolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$MemoryGovernancePolicy.preserve_routing_assignment
    }

    $governanceContract = [ordered]@{
        state_store = "session_state_only"
        serena = "explicit_project_decisions_only"
        ruflo = "short_term_vector_cache_only"
        cognee = "long_term_graph_memory_only"
        "episodic-memory" = "disabled"
    }

    $roleBoundaries = [pscustomobject]@{}
    if ($MemoryGovernancePolicy.role_boundaries) {
        $roleBoundaries = $MemoryGovernancePolicy.role_boundaries
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        primary_memory = $primaryMemory
        project_decision_memory = $projectDecisionMemory
        short_term_memory = $shortTermMemory
        long_term_memory = $longTermMemory
        disabled_systems = @($disabledSystems | Select-Object -Unique)
        governance_contract = [pscustomobject]$governanceContract
        role_boundaries = $roleBoundaries
    }
}

function Get-PathCandidatesFromPrompt {
    param(
        [string]$Prompt,
        [string[]]$SupportedExtensions
    )

    $paths = @()
    if (-not $Prompt -or -not $SupportedExtensions -or $SupportedExtensions.Count -eq 0) {
        return @()
    }

    $escapedExt = @($SupportedExtensions | ForEach-Object { [Regex]::Escape(([string]$_).ToLowerInvariant()) } | Sort-Object -Unique)
    if ($escapedExt.Count -eq 0) {
        return @()
    }

    $extPattern = ($escapedExt | Sort-Object { $_.Length } -Descending) -join "|"
    $regexes = @(
        [Regex]::new('"([^"]+\.(?:' + $extPattern + '))"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase),
        [Regex]::new("'([^']+\.(?:$extPattern))'", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase),
        [Regex]::new('([^\s"'';,()]+?\.(?:' + $extPattern + '))', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    )

    foreach ($regex in $regexes) {
        $matches = $regex.Matches($Prompt)
        foreach ($m in $matches) {
            if ($m.Groups.Count -lt 2) { continue }
            $candidate = [string]$m.Groups[1].Value
            if (-not $candidate) { continue }
            $normalized = $candidate.Trim().Trim('"', "'").TrimEnd('.', ',', ';', ')', ']')
            if ($normalized) {
                $paths += $normalized
            }
        }
    }

    return @($paths | Select-Object -Unique)
}

function Resolve-ExistingPathCandidates {
    param(
        [string[]]$PathCandidates,
        [bool]$WorkspaceProbeEnabled,
        [int]$WorkspaceProbeLimit,
        [string[]]$WorkspaceProbeExtensions
    )

    $resolvedPaths = @()
    $cwd = (Get-Location).Path

    foreach ($candidate in @($PathCandidates)) {
        $raw = [Environment]::ExpandEnvironmentVariables([string]$candidate)
        if (-not $raw) { continue }

        $tries = @()
        if ([System.IO.Path]::IsPathRooted($raw)) {
            $tries += $raw
        } else {
            $tries += (Join-Path -Path $cwd -ChildPath $raw)
            $tries += $raw
        }

        foreach ($tryPath in $tries) {
            if (-not $tryPath) { continue }
            if (Test-Path -LiteralPath $tryPath -PathType Leaf) {
                $resolved = (Resolve-Path -LiteralPath $tryPath -ErrorAction SilentlyContinue).Path
                if ($resolved) {
                    $resolvedPaths += $resolved
                    break
                }
            }
        }
    }

    if ($resolvedPaths.Count -eq 0 -and $WorkspaceProbeEnabled) {
        $limit = if ($WorkspaceProbeLimit -gt 0) { $WorkspaceProbeLimit } else { 3 }
        $probeExt = @($WorkspaceProbeExtensions | ForEach-Object { [string]$_ } | Where-Object { $_ })
        if ($probeExt.Count -gt 0) {
            foreach ($ext in $probeExt) {
                $pattern = "*.$ext"
                $hits = Get-ChildItem -Path $cwd -File -Filter $pattern -ErrorAction SilentlyContinue | Select-Object -First $limit
                foreach ($h in $hits) {
                    if ($h -and $h.FullName) {
                        $resolvedPaths += [string]$h.FullName
                    }
                }
                if ($resolvedPaths.Count -ge $limit) { break }
            }
        }
    }

    return @($resolvedPaths | Select-Object -Unique)
}

function Get-DetectedExtension {
    param(
        [string]$Path,
        [string[]]$SupportedExtensions
    )

    $name = [System.IO.Path]::GetFileName([string]$Path).ToLowerInvariant()
    foreach ($ext in @($SupportedExtensions | Sort-Object { $_.Length } -Descending)) {
        $needle = "." + ([string]$ext).ToLowerInvariant()
        if ($name.EndsWith($needle)) {
            return ([string]$ext).ToLowerInvariant()
        }
    }

    return [System.IO.Path]::GetExtension($name).TrimStart('.').ToLowerInvariant()
}

function Test-WorkbookExtension {
    param([string]$Extension)
    return ($Extension -in @("xlsx", "xlsm", "xls"))
}

function Test-CsvLikeExtension {
    param([string]$Extension)
    return ($Extension -in @(
            "csv", "tsv", "tab", "psv", "ssv", "scsv",
            "csv.gz", "tsv.gz", "tab.gz", "psv.gz", "ssv.gz", "scsv.gz",
            "csv.zst", "tsv.zst", "tab.zst"
        ))
}

function Get-DelimiterHint {
    param(
        [string]$Extension,
        [string]$HeaderLine
    )

    if ($Extension -match "^(tsv|tab)(\.|$)") { return "`t" }
    if ($Extension -match "^psv(\.|$)") { return "|" }
    if ($Extension -match "^(ssv|scsv)(\.|$)") { return ";" }

    $candidates = @(",", ";", "`t", "|")
    $best = ","
    $bestCount = -1
    foreach ($d in $candidates) {
        $count = ([string]$HeaderLine).Split($d).Count
        if ($count -gt $bestCount) {
            $best = $d
            $bestCount = $count
        }
    }

    return $best
}

function Get-DelimitedFileSampleStats {
    param(
        [string]$Path,
        [string]$Extension,
        [int64]$FileSizeBytes,
        [int]$MaxLines,
        [int]$MaxChars
    )

    $result = [ordered]@{
        columns = $null
        delimiter = $null
        sample_rows = 0
        sample_bytes = 0
        estimated_rows = $null
    }

    if ($Extension -match "\.(gz|zst)$") {
        return [pscustomobject]$result
    }

    $lineCap = if ($MaxLines -gt 0) { $MaxLines } else { 200 }
    $charCap = if ($MaxChars -gt 0) { $MaxChars } else { 200000 }

    $rawLines = @()
    try {
        $rawLines = @(Get-Content -LiteralPath $Path -TotalCount $lineCap -Encoding UTF8 -ErrorAction Stop)
    } catch {
        return [pscustomobject]$result
    }

    if ($rawLines.Count -eq 0) {
        return [pscustomobject]$result
    }

    $lines = @()
    $chars = 0
    foreach ($line in $rawLines) {
        $text = [string]$line
        if (($chars + $text.Length + 1) -gt $charCap -and $lines.Count -gt 0) {
            break
        }
        $lines += $text
        $chars += ($text.Length + 1)
    }

    if ($lines.Count -eq 0) {
        return [pscustomobject]$result
    }

    $header = [string]$lines[0]
    $delimiter = Get-DelimiterHint -Extension $Extension -HeaderLine $header
    $splitPattern = [Regex]::Escape($delimiter)
    $columns = if ($header.Length -gt 0) { ([Regex]::Split($header, $splitPattern, [System.Text.RegularExpressions.RegexOptions]::None)).Count } else { 0 }
    $sampleRows = [Math]::Max(0, $lines.Count - 1)

    $sampleText = $lines -join "`n"
    $sampleBytes = [System.Text.Encoding]::UTF8.GetByteCount($sampleText)
    $estimatedRows = $null
    if ($sampleRows -gt 0 -and $sampleBytes -gt 0 -and $FileSizeBytes -gt 0) {
        $estimatedRows = [int64][Math]::Round(([double]$FileSizeBytes / [double]$sampleBytes) * [double]$sampleRows, 0)
    }

    $result.columns = $columns
    $result.delimiter = $delimiter
    $result.sample_rows = $sampleRows
    $result.sample_bytes = $sampleBytes
    $result.estimated_rows = $estimatedRows
    return [pscustomobject]$result
}

function Get-DataScaleOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$DataScaleOverlayPolicy
    )

    if (-not $DataScaleOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $enabled = $true
    if ($DataScaleOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$DataScaleOverlayPolicy.enabled
    }
    $mode = if ($DataScaleOverlayPolicy.mode) { [string]$DataScaleOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $taskAllow = @("coding", "research")
    if ($DataScaleOverlayPolicy.task_allow) {
        $taskAllow = @($DataScaleOverlayPolicy.task_allow)
    }
    $gradeAllow = @("M", "L", "XL")
    if ($DataScaleOverlayPolicy.grade_allow) {
        $gradeAllow = @($DataScaleOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.pack_allow) {
        $packAllow = @($DataScaleOverlayPolicy.monitor.pack_allow)
    }
    $skillAllow = @()
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.skill_allow) {
        $skillAllow = @($DataScaleOverlayPolicy.monitor.skill_allow)
    }
    $supportedExt = @("csv", "tsv", "tab", "psv", "ssv", "scsv", "csv.gz", "tsv.gz", "tab.gz", "psv.gz", "ssv.gz", "scsv.gz", "csv.zst", "tsv.zst", "tab.zst", "xlsx", "xlsm", "xls")
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.supported_extensions) {
        $supportedExt = @($DataScaleOverlayPolicy.monitor.supported_extensions)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($DataScaleOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$DataScaleOverlayPolicy.preserve_routing_assignment
    }

    if (-not $scopeApplicable) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $false
            enforcement = "none"
            reason = "outside_scope"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $probeEnabled = $true
    $extractFromPrompt = $true
    $workspaceProbeWhenNoPath = $false
    $workspaceProbeLimit = 3
    $workspaceProbeExtensions = @("csv", "tsv", "tab", "psv", "ssv", "scsv", "xlsx", "xlsm", "xls")
    $sampleMaxLines = 200
    $sampleMaxChars = 200000

    if ($DataScaleOverlayPolicy.path_probe) {
        if ($DataScaleOverlayPolicy.path_probe.enabled -ne $null) {
            $probeEnabled = [bool]$DataScaleOverlayPolicy.path_probe.enabled
        }
        if ($DataScaleOverlayPolicy.path_probe.extract_from_prompt -ne $null) {
            $extractFromPrompt = [bool]$DataScaleOverlayPolicy.path_probe.extract_from_prompt
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_when_no_path -ne $null) {
            $workspaceProbeWhenNoPath = [bool]$DataScaleOverlayPolicy.path_probe.workspace_probe_when_no_path
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_limit -ne $null) {
            $workspaceProbeLimit = [int]$DataScaleOverlayPolicy.path_probe.workspace_probe_limit
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_extensions) {
            $workspaceProbeExtensions = @($DataScaleOverlayPolicy.path_probe.workspace_probe_extensions)
        }
        if ($DataScaleOverlayPolicy.path_probe.read_sample_max_lines -ne $null) {
            $sampleMaxLines = [int]$DataScaleOverlayPolicy.path_probe.read_sample_max_lines
        }
        if ($DataScaleOverlayPolicy.path_probe.read_sample_max_chars -ne $null) {
            $sampleMaxChars = [int]$DataScaleOverlayPolicy.path_probe.read_sample_max_chars
        }
    }

    if (-not $probeEnabled) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "probe_disabled"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $pathsDetected = @()
    if ($extractFromPrompt) {
        $pathsDetected = Get-PathCandidatesFromPrompt -Prompt $Prompt -SupportedExtensions $supportedExt
    }
    $pathsExisting = Resolve-ExistingPathCandidates -PathCandidates $pathsDetected -WorkspaceProbeEnabled $workspaceProbeWhenNoPath -WorkspaceProbeLimit $workspaceProbeLimit -WorkspaceProbeExtensions $workspaceProbeExtensions

    if ($pathsExisting.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "no_existing_data_path"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @($pathsDetected)
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $fileAnalysis = @()
    foreach ($path in $pathsExisting) {
        $item = $null
        try {
            $item = Get-Item -LiteralPath $path -ErrorAction Stop
        } catch {
            continue
        }
        if (-not $item) { continue }

        $ext = Get-DetectedExtension -Path $item.FullName -SupportedExtensions $supportedExt
        $isWorkbook = Test-WorkbookExtension -Extension $ext
        $isCsvLike = Test-CsvLikeExtension -Extension $ext
        $isCompressed = ($ext -match "\.(gz|zst)$")

        $columns = $null
        $estimatedRows = $null
        $sampleRows = 0
        if ($isCsvLike -and -not $isCompressed) {
            $sample = Get-DelimitedFileSampleStats -Path $item.FullName -Extension $ext -FileSizeBytes ([int64]$item.Length) -MaxLines $sampleMaxLines -MaxChars $sampleMaxChars
            $columns = $sample.columns
            $estimatedRows = $sample.estimated_rows
            $sampleRows = $sample.sample_rows
        }

        $fileAnalysis += [pscustomobject]@{
            path = [string]$item.FullName
            size_bytes = [int64]$item.Length
            extension = $ext
            is_workbook = $isWorkbook
            is_csv_like = $isCsvLike
            is_compressed = $isCompressed
            columns = $columns
            estimated_rows = $estimatedRows
            sample_rows = $sampleRows
        }
    }

    if ($fileAnalysis.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "probe_failed"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @($pathsDetected)
            paths_existing = @($pathsExisting)
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $primary = $fileAnalysis | Sort-Object -Property @{ Expression = "size_bytes"; Descending = $true } | Select-Object -First 1
    $sizeBytes = [int64]$primary.size_bytes
    $estimatedRows = if ($primary.estimated_rows -ne $null) { [int64]$primary.estimated_rows } else { $null }
    $columnCount = if ($primary.columns -ne $null) { [int]$primary.columns } else { $null }
    $isWorkbook = [bool]$primary.is_workbook
    $isCsvLike = [bool]$primary.is_csv_like
    $isCompressed = [bool]$primary.is_compressed

    $mediumSize = 52428800
    $largeSize = 314572800
    $mediumRows = 500000
    $largeRows = 3000000
    $confirmMin = 0.6
    $overrideMin = 0.85

    if ($DataScaleOverlayPolicy.thresholds) {
        if ($DataScaleOverlayPolicy.thresholds.medium_size_bytes -ne $null) { $mediumSize = [int64]$DataScaleOverlayPolicy.thresholds.medium_size_bytes }
        if ($DataScaleOverlayPolicy.thresholds.large_size_bytes -ne $null) { $largeSize = [int64]$DataScaleOverlayPolicy.thresholds.large_size_bytes }
        if ($DataScaleOverlayPolicy.thresholds.medium_estimated_rows -ne $null) { $mediumRows = [int64]$DataScaleOverlayPolicy.thresholds.medium_estimated_rows }
        if ($DataScaleOverlayPolicy.thresholds.large_estimated_rows -ne $null) { $largeRows = [int64]$DataScaleOverlayPolicy.thresholds.large_estimated_rows }
        if ($DataScaleOverlayPolicy.thresholds.confirm_confidence_min -ne $null) { $confirmMin = [double]$DataScaleOverlayPolicy.thresholds.confirm_confidence_min }
        if ($DataScaleOverlayPolicy.thresholds.high_confidence_for_override -ne $null) { $overrideMin = [double]$DataScaleOverlayPolicy.thresholds.high_confidence_for_override }
    }

    $isLargeBySize = ($sizeBytes -ge $largeSize)
    $isLargeByRows = ($estimatedRows -ne $null -and $estimatedRows -ge $largeRows)
    $isMediumBySize = ($sizeBytes -ge $mediumSize)
    $isMediumByRows = ($estimatedRows -ne $null -and $estimatedRows -ge $mediumRows)

    $dataScale = "small"
    if ($isLargeBySize -or $isLargeByRows) {
        $dataScale = "large"
    } elseif ($isMediumBySize -or $isMediumByRows) {
        $dataScale = "medium"
    }

    $csvDefaultSkill = "spreadsheet"
    $csvLargeSkill = "xan"
    $workbookSkill = "xlsx"
    $workbookAnalysisSkill = "excel-analysis"
    $operationKeywords = @("join", "groupby", "dedup", "frequency", "sort", "filter", "pipeline", "aggregate", "window", "parallel", "merge", "split", "分组", "去重", "聚合", "连接", "排序", "过滤", "管道", "流式")
    if ($DataScaleOverlayPolicy.recommendations) {
        if ($DataScaleOverlayPolicy.recommendations.csv_default_skill) { $csvDefaultSkill = [string]$DataScaleOverlayPolicy.recommendations.csv_default_skill }
        if ($DataScaleOverlayPolicy.recommendations.csv_large_skill) { $csvLargeSkill = [string]$DataScaleOverlayPolicy.recommendations.csv_large_skill }
        if ($DataScaleOverlayPolicy.recommendations.workbook_skill) { $workbookSkill = [string]$DataScaleOverlayPolicy.recommendations.workbook_skill }
        if ($DataScaleOverlayPolicy.recommendations.workbook_analysis_skill) { $workbookAnalysisSkill = [string]$DataScaleOverlayPolicy.recommendations.workbook_analysis_skill }
        if ($DataScaleOverlayPolicy.recommendations.operations_preferring_xan) {
            $operationKeywords = @($DataScaleOverlayPolicy.recommendations.operations_preferring_xan)
        }
    }

    $operationPrefersXan = $false
    foreach ($kw in $operationKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $operationPrefersXan = $true
            break
        }
    }

    $recommendedSkill = $null
    $confidence = 0.0
    $reason = "no_recommendation"
    if ($isWorkbook) {
        $pivotLike = (Test-KeywordHit -PromptLower $PromptLower -Keyword "pivot") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "pivot table") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "数据透视") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "透视表")
        $recommendedSkill = if ($pivotLike) { $workbookAnalysisSkill } else { $workbookSkill }
        $confidence = 0.9
        $reason = "workbook_detected"
    } elseif ($isCsvLike) {
        if ($dataScale -eq "large") {
            $recommendedSkill = $csvLargeSkill
            $confidence = 0.9
            $reason = "csv_large_detected"
        } elseif ($dataScale -eq "medium" -and $operationPrefersXan) {
            $recommendedSkill = $csvLargeSkill
            $confidence = 0.72
            $reason = "csv_medium_operation_prefers_xan"
        } else {
            $recommendedSkill = $csvDefaultSkill
            $confidence = 0.68
            $reason = "csv_default_path"
        }
    } else {
        $reason = "unsupported_extension"
    }

    $overrideCandidateAllowed = ($recommendedSkill -and ($PackCandidates -contains $recommendedSkill))
    $enforcement = "advisory"
    $confirmRequired = $false
    $autoOverride = $false

    if ($recommendedSkill -and $overrideCandidateAllowed -and $SelectedSkill -and ($recommendedSkill -ne $SelectedSkill)) {
        switch ($mode) {
            "soft" {
                if ($confidence -ge $confirmMin) {
                    $enforcement = "confirm_required"
                    $confirmRequired = $true
                }
            }
            "strict" {
                if ($confidence -ge $overrideMin) {
                    $enforcement = "required"
                    $autoOverride = $true
                } elseif ($confidence -ge $confirmMin) {
                    $enforcement = "confirm_required"
                    $confirmRequired = $true
                }
            }
        }
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        pack_applicable = $packApplicable
        skill_applicable = $skillApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        paths_detected = @($pathsDetected)
        paths_existing = @($pathsExisting)
        probe_file_count = $fileAnalysis.Count
        probe_primary_file = [string]$primary.path
        probe_file_analysis = @($fileAnalysis)
        data_scale = $dataScale
        size_bytes = [int64]$sizeBytes
        estimated_rows = $estimatedRows
        column_count = $columnCount
        is_workbook = $isWorkbook
        is_csv_like = $isCsvLike
        is_compressed = $isCompressed
        operation_prefers_xan = $operationPrefersXan
        recommended_skill = $recommendedSkill
        confidence = [Math]::Round([double]$confidence, 4)
        confirm_required = $confirmRequired
        auto_override = $autoOverride
        override_candidate_allowed = $overrideCandidateAllowed
    }
}

function Get-QualityDebtOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$QualityDebtOverlayPolicy
    )

    if (-not $QualityDebtOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            risk_signal_score = 0.0
            debt_likelihood = "none"
            risk_keyword_hits = @()
            suppress_keyword_hits = @()
            focus_facets_matched = @()
            focus_facet_hits = [pscustomobject]@{}
            confirm_recommended = $false
            confirm_required = $false
            should_apply_hook = $false
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $enabled = $true
    if ($QualityDebtOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$QualityDebtOverlayPolicy.enabled
    }

    $mode = if ($QualityDebtOverlayPolicy.mode) { [string]$QualityDebtOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            risk_signal_score = 0.0
            debt_likelihood = "none"
            risk_keyword_hits = @()
            suppress_keyword_hits = @()
            focus_facets_matched = @()
            focus_facet_hits = [pscustomobject]@{}
            confirm_recommended = $false
            confirm_required = $false
            should_apply_hook = $false
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $taskAllow = @("coding", "review")
    if ($QualityDebtOverlayPolicy.task_allow) {
        $taskAllow = @($QualityDebtOverlayPolicy.task_allow)
    }

    $gradeAllow = @("L", "XL")
    if ($QualityDebtOverlayPolicy.grade_allow) {
        $gradeAllow = @($QualityDebtOverlayPolicy.grade_allow)
    }

    $packAllow = @("code-quality")
    $skillAllow = @()
    if ($QualityDebtOverlayPolicy.monitor) {
        if ($QualityDebtOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($QualityDebtOverlayPolicy.monitor.pack_allow)
        }
        if ($QualityDebtOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($QualityDebtOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = $true
    if ($packAllow.Count -gt 0) {
        $packApplicable = ($SelectedPackId -and ($packAllow -contains $SelectedPackId))
    }
    $skillApplicable = $true
    if ($skillAllow.Count -gt 0) {
        $skillApplicable = ($SelectedSkill -and ($skillAllow -contains $SelectedSkill))
    }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($QualityDebtOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$QualityDebtOverlayPolicy.preserve_routing_assignment
    }

    $riskKeywords = @(
        "code smell",
        "maintainability",
        "complexity",
        "technical debt",
        "duplicate logic",
        "dead code",
        "unreachable",
        "security risk",
        "regression risk",
        "lint debt",
        "test debt",
        "spaghetti",
        "refactor needed",
        "质量债务",
        "技术债",
        "可维护性",
        "复杂度",
        "重复代码",
        "死代码",
        "安全风险"
    )
    if ($QualityDebtOverlayPolicy.risk_keywords) {
        $riskKeywords = @($QualityDebtOverlayPolicy.risk_keywords)
    }

    $suppressKeywords = @("typo", "format only", "rename only", "comment only", "文档改动")
    if ($QualityDebtOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($QualityDebtOverlayPolicy.suppress_keywords)
    }

    $confirmRiskMin = 0.65
    $highRiskMin = 0.8
    $suppressWeight = 0.35
    $minRiskHitsForOverlay = 1
    if ($QualityDebtOverlayPolicy.thresholds) {
        if ($QualityDebtOverlayPolicy.thresholds.confirm_risk_score_min -ne $null) {
            $confirmRiskMin = [double]$QualityDebtOverlayPolicy.thresholds.confirm_risk_score_min
        }
        if ($QualityDebtOverlayPolicy.thresholds.high_risk_score_min -ne $null) {
            $highRiskMin = [double]$QualityDebtOverlayPolicy.thresholds.high_risk_score_min
        }
        if ($QualityDebtOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$QualityDebtOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($QualityDebtOverlayPolicy.thresholds.min_risk_hits_for_overlay -ne $null) {
            $minRiskHitsForOverlay = [int]$QualityDebtOverlayPolicy.thresholds.min_risk_hits_for_overlay
        }
    }

    $riskMatches = @()
    foreach ($kw in $riskKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $riskMatches += [string]$kw
        }
    }

    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $riskRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $riskKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $riskScore = [Math]::Max(0.0, [Math]::Min(1.0, ($riskRatio - ($suppressWeight * $suppressRatio))))
    if ($riskMatches.Count -lt $minRiskHitsForOverlay) {
        $riskScore = 0.0
    }

    $facetHits = [ordered]@{}
    $matchedFacets = @()
    if ($QualityDebtOverlayPolicy.focus_facets) {
        foreach ($facetName in @($QualityDebtOverlayPolicy.focus_facets.PSObject.Properties.Name)) {
            $hits = @()
            foreach ($kw in @($QualityDebtOverlayPolicy.focus_facets.$facetName)) {
                if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                    $hits += [string]$kw
                }
            }
            $facetHits[[string]$facetName] = @($hits)
            if ($hits.Count -gt 0) {
                $matchedFacets += [string]$facetName
            }
        }
    }

    $debtLikelihood = "none"
    if ($riskScore -ge $highRiskMin) {
        $debtLikelihood = "high"
    } elseif ($riskScore -ge $confirmRiskMin) {
        $debtLikelihood = "medium"
    } elseif ($riskScore -gt 0) {
        $debtLikelihood = "low"
    }

    $confirmRecommended = ($scopeApplicable -and ($riskScore -ge $confirmRiskMin))
    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                if ($confirmRecommended) {
                    $enforcement = "advisory"
                    $reason = "soft_high_risk_advisory"
                } else {
                    $enforcement = "advisory"
                    $reason = "soft_advisory"
                }
            }
            "strict" {
                if ($confirmRecommended) {
                    $enforcement = "confirm_required"
                    $reason = "strict_confirm_high_risk"
                } else {
                    $enforcement = "advisory"
                    $reason = "strict_advisory_low_risk"
                }
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }
    $confirmRequired = (($enforcement -eq "confirm_required") -or ($enforcement -eq "required"))

    $externalEnabled = $false
    $externalCommand = $null
    $externalInvokeMode = "disabled"
    $externalRunModes = @("soft", "strict")
    $externalRiskMin = $confirmRiskMin
    $manualCommandHint = $null
    if ($QualityDebtOverlayPolicy.external_analyzer) {
        if ($QualityDebtOverlayPolicy.external_analyzer.enabled -ne $null) {
            $externalEnabled = [bool]$QualityDebtOverlayPolicy.external_analyzer.enabled
        }
        if ($QualityDebtOverlayPolicy.external_analyzer.command) {
            $externalCommand = [string]$QualityDebtOverlayPolicy.external_analyzer.command
        }
        if ($QualityDebtOverlayPolicy.external_analyzer.invoke_mode) {
            $externalInvokeMode = [string]$QualityDebtOverlayPolicy.external_analyzer.invoke_mode
        } elseif ($externalEnabled) {
            $externalInvokeMode = "manual_only"
        }
        if ($QualityDebtOverlayPolicy.external_analyzer.run_in_modes) {
            $externalRunModes = @($QualityDebtOverlayPolicy.external_analyzer.run_in_modes)
        }
        if ($QualityDebtOverlayPolicy.external_analyzer.risk_score_min -ne $null) {
            $externalRiskMin = [double]$QualityDebtOverlayPolicy.external_analyzer.risk_score_min
        }
        if ($QualityDebtOverlayPolicy.external_analyzer.manual_command_hint) {
            $manualCommandHint = [string]$QualityDebtOverlayPolicy.external_analyzer.manual_command_hint
        }
    }
    if (-not $manualCommandHint -and $externalCommand) {
        $manualCommandHint = "$externalCommand analyze --path <repo>"
    }

    $externalStatus = "disabled"
    $externalToolAvailable = $false
    $externalShouldInvoke = $false
    if ($scopeApplicable -and $externalEnabled) {
        if (-not ($externalRunModes -contains $mode)) {
            $externalStatus = "skipped_mode"
        } elseif ($riskScore -lt $externalRiskMin) {
            $externalStatus = "risk_below_threshold"
        } elseif (-not $externalCommand) {
            $externalStatus = "command_missing"
        } else {
            $externalShouldInvoke = $true
            $commandResolved = Get-Command -Name $externalCommand -ErrorAction SilentlyContinue
            if (-not $commandResolved) {
                $externalStatus = "tool_unavailable"
            } else {
                $externalToolAvailable = $true
                switch ($externalInvokeMode) {
                    "probe_only" { $externalStatus = "tool_available_probe_only" }
                    "manual_only" { $externalStatus = "not_executed_manual_mode" }
                    "auto" { $externalStatus = "auto_mode_not_implemented" }
                    default { $externalStatus = "not_executed" }
                }
            }
        }
    }

    $recommendedFollowup = $null
    if ($scopeApplicable -and ($debtLikelihood -in @("medium", "high"))) {
        $recommendedFollowup = "Run focused quality review and debt cleanup checklist before merge."
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        pack_applicable = $packApplicable
        skill_applicable = $skillApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        risk_signal_score = [Math]::Round([double]$riskScore, 4)
        debt_likelihood = $debtLikelihood
        risk_keyword_hits = @($riskMatches)
        suppress_keyword_hits = @($suppressMatches)
        focus_facets_matched = @($matchedFacets)
        focus_facet_hits = [pscustomobject]$facetHits
        confirm_recommended = $confirmRecommended
        confirm_required = $confirmRequired
        should_apply_hook = ($scopeApplicable -and (($riskScore -gt 0.0) -or $confirmRequired))
        recommended_followup = $recommendedFollowup
        external_analyzer = [pscustomobject]@{
            enabled = $externalEnabled
            command = $externalCommand
            invoke_mode = $externalInvokeMode
            status = $externalStatus
            tool_available = $externalToolAvailable
            should_invoke = $externalShouldInvoke
            invoked = $false
            manual_command_hint = $manualCommandHint
            output_excerpt = $null
            error = $null
        }
    }
}

function Get-FrameworkInteropOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$FrameworkInteropOverlayPolicy
    )

    if (-not $FrameworkInteropOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            interop_signal_score = 0.0
            interop_likelihood = "none"
            interop_keyword_hits = @()
            suppress_keyword_hits = @()
            frameworks_matched = @()
            framework_pair_detected = $false
            detected_pairs = @()
            focus_facets_matched = @()
            focus_facet_hits = [pscustomobject]@{}
            confirm_recommended = $false
            confirm_required = $false
            should_apply_hook = $false
            recommended_profile = $null
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $enabled = $true
    if ($FrameworkInteropOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$FrameworkInteropOverlayPolicy.enabled
    }

    $mode = if ($FrameworkInteropOverlayPolicy.mode) { [string]$FrameworkInteropOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            interop_signal_score = 0.0
            interop_likelihood = "none"
            interop_keyword_hits = @()
            suppress_keyword_hits = @()
            frameworks_matched = @()
            framework_pair_detected = $false
            detected_pairs = @()
            focus_facets_matched = @()
            focus_facet_hits = [pscustomobject]@{}
            confirm_recommended = $false
            confirm_required = $false
            should_apply_hook = $false
            recommended_profile = $null
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $taskAllow = @("coding", "research")
    if ($FrameworkInteropOverlayPolicy.task_allow) {
        $taskAllow = @($FrameworkInteropOverlayPolicy.task_allow)
    }

    $gradeAllow = @("L", "XL")
    if ($FrameworkInteropOverlayPolicy.grade_allow) {
        $gradeAllow = @($FrameworkInteropOverlayPolicy.grade_allow)
    }

    $packAllow = @("data-ml")
    $skillAllow = @()
    if ($FrameworkInteropOverlayPolicy.monitor) {
        if ($FrameworkInteropOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($FrameworkInteropOverlayPolicy.monitor.pack_allow)
        }
        if ($FrameworkInteropOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($FrameworkInteropOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = $true
    if ($packAllow.Count -gt 0) {
        $packApplicable = ($SelectedPackId -and ($packAllow -contains $SelectedPackId))
    }
    $skillApplicable = $true
    if ($skillAllow.Count -gt 0) {
        $skillApplicable = ($SelectedSkill -and ($skillAllow -contains $SelectedSkill))
    }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($FrameworkInteropOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$FrameworkInteropOverlayPolicy.preserve_routing_assignment
    }

    $interopKeywords = @(
        "ivy transpile",
        "transpile",
        "framework migration",
        "cross framework",
        "port model",
        "trace_graph",
        "pytorch to tensorflow",
        "pytorch to jax",
        "tensorflow to pytorch",
        "jax to pytorch",
        "跨框架",
        "框架迁移",
        "模型迁移",
        "框架转换",
        "迁移到tensorflow",
        "迁移到jax"
    )
    if ($FrameworkInteropOverlayPolicy.interop_signal_keywords) {
        $interopKeywords = @($FrameworkInteropOverlayPolicy.interop_signal_keywords)
    }

    $suppressKeywords = @(
        "train model",
        "hyperparameter",
        "feature engineering",
        "eda",
        "clean data",
        "仅训练",
        "只调参",
        "数据清洗"
    )
    if ($FrameworkInteropOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($FrameworkInteropOverlayPolicy.suppress_keywords)
    }

    $frameworkMap = [ordered]@{
        pytorch = @("pytorch", "torch")
        tensorflow = @("tensorflow", "tf")
        jax = @("jax")
        numpy = @("numpy")
        onnx = @("onnx")
        paddle = @("paddle", "paddlepaddle")
    }
    if ($FrameworkInteropOverlayPolicy.framework_keywords) {
        $frameworkMap = [ordered]@{}
        foreach ($fwName in @($FrameworkInteropOverlayPolicy.framework_keywords.PSObject.Properties.Name)) {
            $frameworkMap[[string]$fwName] = @($FrameworkInteropOverlayPolicy.framework_keywords.$fwName)
        }
    }

    $confirmInteropMin = 0.55
    $highInteropMin = 0.75
    $suppressWeight = 0.3
    $minInteropHitsForOverlay = 1
    if ($FrameworkInteropOverlayPolicy.thresholds) {
        if ($FrameworkInteropOverlayPolicy.thresholds.confirm_interop_score_min -ne $null) {
            $confirmInteropMin = [double]$FrameworkInteropOverlayPolicy.thresholds.confirm_interop_score_min
        }
        if ($FrameworkInteropOverlayPolicy.thresholds.high_interop_score_min -ne $null) {
            $highInteropMin = [double]$FrameworkInteropOverlayPolicy.thresholds.high_interop_score_min
        }
        if ($FrameworkInteropOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$FrameworkInteropOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($FrameworkInteropOverlayPolicy.thresholds.min_interop_hits_for_overlay -ne $null) {
            $minInteropHitsForOverlay = [int]$FrameworkInteropOverlayPolicy.thresholds.min_interop_hits_for_overlay
        }
    }

    $interopMatches = @()
    foreach ($kw in $interopKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $interopMatches += [string]$kw
        }
    }

    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $frameworkHits = [ordered]@{}
    $frameworksMatched = @()
    foreach ($fw in @($frameworkMap.Keys)) {
        $hits = @()
        foreach ($kw in @($frameworkMap[$fw])) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $frameworkHits[[string]$fw] = @($hits)
        if ($hits.Count -gt 0) {
            $frameworksMatched += [string]$fw
        }
    }

    $detectedPairs = @()
    $frameworkKeys = @($frameworkMap.Keys)
    for ($i = 0; $i -lt $frameworkKeys.Count; $i++) {
        for ($j = 0; $j -lt $frameworkKeys.Count; $j++) {
            if ($i -eq $j) { continue }
            $src = [string]$frameworkKeys[$i]
            $dst = [string]$frameworkKeys[$j]
            $srcEsc = [Regex]::Escape($src)
            $dstEsc = [Regex]::Escape($dst)
            if (
                [Regex]::IsMatch($PromptLower, "$srcEsc\s*(->|to|2)\s*$dstEsc") -or
                [Regex]::IsMatch($PromptLower, "$srcEsc\s*到\s*$dstEsc") -or
                [Regex]::IsMatch($PromptLower, "from\s+$srcEsc\s+to\s+$dstEsc")
            ) {
                $detectedPairs += "$src->$dst"
            }
        }
    }
    $detectedPairs = @($detectedPairs | Select-Object -Unique)

    $interopRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $interopKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $frameworkBonus = if ($frameworksMatched.Count -ge 2) { 0.12 } elseif ($frameworksMatched.Count -eq 1) { 0.05 } else { 0.0 }
    $interopScore = [Math]::Max(0.0, [Math]::Min(1.0, (($interopRatio + $frameworkBonus) - ($suppressWeight * $suppressRatio))))
    if ($interopMatches.Count -lt $minInteropHitsForOverlay) {
        $interopScore = 0.0
    }

    $frameworkPairDetected = ($detectedPairs.Count -gt 0)
    if ((-not $frameworkPairDetected) -and ($frameworksMatched.Count -ge 2) -and ($interopScore -ge $confirmInteropMin)) {
        $frameworkPairDetected = $true
        $detectedPairs = @("multi-framework-mention")
    }

    $facetHits = [ordered]@{}
    $matchedFacets = @()
    if ($FrameworkInteropOverlayPolicy.focus_facets) {
        foreach ($facetName in @($FrameworkInteropOverlayPolicy.focus_facets.PSObject.Properties.Name)) {
            $hits = @()
            foreach ($kw in @($FrameworkInteropOverlayPolicy.focus_facets.$facetName)) {
                if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                    $hits += [string]$kw
                }
            }
            $facetHits[[string]$facetName] = @($hits)
            if ($hits.Count -gt 0) {
                $matchedFacets += [string]$facetName
            }
        }
    }

    $interopLikelihood = "none"
    if ($interopScore -ge $highInteropMin) {
        $interopLikelihood = "high"
    } elseif ($interopScore -ge $confirmInteropMin) {
        $interopLikelihood = "medium"
    } elseif ($interopScore -gt 0) {
        $interopLikelihood = "low"
    }

    $confirmRecommended = ($scopeApplicable -and $frameworkPairDetected -and ($interopScore -ge $confirmInteropMin))
    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                if ($confirmRecommended) {
                    $enforcement = "advisory"
                    $reason = "soft_interop_advisory"
                } else {
                    $enforcement = "advisory"
                    $reason = "soft_advisory"
                }
            }
            "strict" {
                if ($confirmRecommended) {
                    $enforcement = "confirm_required"
                    $reason = "strict_confirm_framework_migration"
                } else {
                    $enforcement = "advisory"
                    $reason = "strict_advisory_low_signal"
                }
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }
    $confirmRequired = (($enforcement -eq "confirm_required") -or ($enforcement -eq "required"))

    $recommendedProfile = $null
    if ($frameworkPairDetected) {
        $recommendedProfile = "ivy_transpile"
    } elseif ($interopScore -gt 0) {
        $recommendedProfile = "ivy_trace_graph"
    }

    $externalEnabled = $false
    $externalCommand = $null
    $externalInvokeMode = "disabled"
    $externalRunModes = @("soft", "strict")
    $externalInteropMin = $confirmInteropMin
    $manualCommandHint = $null
    if ($FrameworkInteropOverlayPolicy.external_analyzer) {
        if ($FrameworkInteropOverlayPolicy.external_analyzer.enabled -ne $null) {
            $externalEnabled = [bool]$FrameworkInteropOverlayPolicy.external_analyzer.enabled
        }
        if ($FrameworkInteropOverlayPolicy.external_analyzer.command) {
            $externalCommand = [string]$FrameworkInteropOverlayPolicy.external_analyzer.command
        }
        if ($FrameworkInteropOverlayPolicy.external_analyzer.invoke_mode) {
            $externalInvokeMode = [string]$FrameworkInteropOverlayPolicy.external_analyzer.invoke_mode
        } elseif ($externalEnabled) {
            $externalInvokeMode = "manual_only"
        }
        if ($FrameworkInteropOverlayPolicy.external_analyzer.run_in_modes) {
            $externalRunModes = @($FrameworkInteropOverlayPolicy.external_analyzer.run_in_modes)
        }
        if ($FrameworkInteropOverlayPolicy.external_analyzer.interop_score_min -ne $null) {
            $externalInteropMin = [double]$FrameworkInteropOverlayPolicy.external_analyzer.interop_score_min
        }
        if ($FrameworkInteropOverlayPolicy.external_analyzer.manual_command_hint) {
            $manualCommandHint = [string]$FrameworkInteropOverlayPolicy.external_analyzer.manual_command_hint
        }
    }
    if (-not $manualCommandHint -and $externalCommand) {
        $manualCommandHint = "$externalCommand -c `"import ivy; print(ivy.__version__)`""
    }

    $externalStatus = "disabled"
    $externalToolAvailable = $false
    $externalShouldInvoke = $false
    if ($scopeApplicable -and $externalEnabled) {
        if (-not ($externalRunModes -contains $mode)) {
            $externalStatus = "skipped_mode"
        } elseif ($interopScore -lt $externalInteropMin) {
            $externalStatus = "signal_below_threshold"
        } elseif (-not $externalCommand) {
            $externalStatus = "command_missing"
        } else {
            $externalShouldInvoke = $true
            $commandResolved = Get-Command -Name $externalCommand -ErrorAction SilentlyContinue
            if (-not $commandResolved) {
                $externalStatus = "tool_unavailable"
            } else {
                $externalToolAvailable = $true
                switch ($externalInvokeMode) {
                    "probe_only" { $externalStatus = "tool_available_probe_only" }
                    "manual_only" { $externalStatus = "not_executed_manual_mode" }
                    "auto" { $externalStatus = "auto_mode_not_implemented" }
                    default { $externalStatus = "not_executed" }
                }
            }
        }
    }

    $recommendedFollowup = $null
    if ($scopeApplicable -and $recommendedProfile) {
        $recommendedFollowup = "Use Ivy interop flow: identify source/target backend, transpile, run parity tests, then optionally optimize with trace_graph."
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        pack_applicable = $packApplicable
        skill_applicable = $skillApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        interop_signal_score = [Math]::Round([double]$interopScore, 4)
        interop_likelihood = $interopLikelihood
        interop_keyword_hits = @($interopMatches)
        suppress_keyword_hits = @($suppressMatches)
        frameworks_matched = @($frameworksMatched)
        framework_pair_detected = $frameworkPairDetected
        detected_pairs = @($detectedPairs)
        focus_facets_matched = @($matchedFacets)
        focus_facet_hits = [pscustomobject]$facetHits
        confirm_recommended = $confirmRecommended
        confirm_required = $confirmRequired
        should_apply_hook = ($scopeApplicable -and (($interopScore -gt 0.0) -or $confirmRequired))
        recommended_profile = $recommendedProfile
        recommended_followup = $recommendedFollowup
        external_analyzer = [pscustomobject]@{
            enabled = $externalEnabled
            command = $externalCommand
            invoke_mode = $externalInvokeMode
            status = $externalStatus
            tool_available = $externalToolAvailable
            should_invoke = $externalShouldInvoke
            invoked = $false
            manual_command_hint = $manualCommandHint
            output_excerpt = $null
            error = $null
        }
    }
}

function Get-MlLifecycleOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$MlLifecycleOverlayPolicy
    )

    if (-not $MlLifecycleOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            lifecycle_signal_score = 0.0
            lifecycle_likelihood = "none"
            lifecycle_keyword_hits = @()
            suppress_keyword_hits = @()
            stage_detected = "none"
            stage_scores = [pscustomobject]@{}
            stage_hits = [pscustomobject]@{}
            required_checks = @()
            artifacts_required = @()
            artifact_hits = [pscustomobject]@{}
            missing_artifacts = @()
            missing_artifact_ratio = 0.0
            deploy_readiness = "not_applicable"
            confirm_recommended = $false
            confirm_required = $false
            strict_scope_applied = $false
            should_apply_hook = $false
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $enabled = $true
    if ($MlLifecycleOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$MlLifecycleOverlayPolicy.enabled
    }

    $mode = if ($MlLifecycleOverlayPolicy.mode) { [string]$MlLifecycleOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            lifecycle_signal_score = 0.0
            lifecycle_likelihood = "none"
            lifecycle_keyword_hits = @()
            suppress_keyword_hits = @()
            stage_detected = "none"
            stage_scores = [pscustomobject]@{}
            stage_hits = [pscustomobject]@{}
            required_checks = @()
            artifacts_required = @()
            artifact_hits = [pscustomobject]@{}
            missing_artifacts = @()
            missing_artifact_ratio = 0.0
            deploy_readiness = "not_applicable"
            confirm_recommended = $false
            confirm_required = $false
            strict_scope_applied = $false
            should_apply_hook = $false
            recommended_followup = $null
            external_analyzer = [pscustomobject]@{
                enabled = $false
                command = $null
                invoke_mode = "disabled"
                status = "disabled"
                tool_available = $false
                should_invoke = $false
                invoked = $false
                manual_command_hint = $null
                output_excerpt = $null
                error = $null
            }
        }
    }

    $taskAllow = @("planning", "coding", "review", "research")
    if ($MlLifecycleOverlayPolicy.task_allow) {
        $taskAllow = @($MlLifecycleOverlayPolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($MlLifecycleOverlayPolicy.grade_allow) {
        $gradeAllow = @($MlLifecycleOverlayPolicy.grade_allow)
    }

    $packAllow = @("data-ml", "ai-llm")
    $skillAllow = @()
    if ($MlLifecycleOverlayPolicy.monitor) {
        if ($MlLifecycleOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($MlLifecycleOverlayPolicy.monitor.pack_allow)
        }
        if ($MlLifecycleOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($MlLifecycleOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = $true
    if ($packAllow.Count -gt 0) {
        $packApplicable = ($SelectedPackId -and ($packAllow -contains $SelectedPackId))
    }
    $skillApplicable = $true
    if ($skillAllow.Count -gt 0) {
        $skillApplicable = ($SelectedSkill -and ($skillAllow -contains $SelectedSkill))
    }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($MlLifecycleOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$MlLifecycleOverlayPolicy.preserve_routing_assignment
    }

    $lifecycleKeywords = @(
        "ml pipeline",
        "training pipeline",
        "model training",
        "model evaluation",
        "baseline compare",
        "experiment tracking",
        "model registry",
        "serve model",
        "deploy model",
        "canary rollout",
        "continual learning",
        "drift monitoring",
        "retraining",
        "机器学习流水线",
        "模型训练",
        "模型评估",
        "基线对比",
        "实验追踪",
        "模型注册",
        "模型部署",
        "持续学习",
        "漂移监控",
        "再训练"
    )
    if ($MlLifecycleOverlayPolicy.lifecycle_signal_keywords) {
        $lifecycleKeywords = @($MlLifecycleOverlayPolicy.lifecycle_signal_keywords)
    }

    $suppressKeywords = @(
        "math proof",
        "paper summary only",
        "just theory",
        "only concept",
        "仅概念",
        "只要理论",
        "论文总结"
    )
    if ($MlLifecycleOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($MlLifecycleOverlayPolicy.suppress_keywords)
    }

    $stageKeywordMap = [ordered]@{
        develop = @("feature engineering", "data preprocessing", "train model", "training pipeline", "训练", "特征工程")
        evaluate = @("evaluation", "metrics", "ablation", "baseline compare", "验证", "评估", "基线")
        deploy = @("deploy", "serve", "production", "canary", "api service", "上线", "部署", "服务化")
        iterate = @("drift", "monitoring", "feedback loop", "retraining", "continual learning", "漂移", "监控", "持续学习")
    }
    if ($MlLifecycleOverlayPolicy.stage_keywords) {
        $stageKeywordMap = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.stage_keywords.PSObject.Properties.Name)) {
            $stageKeywordMap[[string]$stageName] = @($MlLifecycleOverlayPolicy.stage_keywords.$stageName)
        }
    }

    $artifactKeywordMap = [ordered]@{
        run_id = @("run_id", "run id", "mlflow run")
        evaluation_results = @("evaluation report", "evaluation_results", "metrics report", "评估报告")
        baseline_compare = @("baseline compare", "baseline comparison", "基线对比")
        data_tests = @("data tests", "great expectations", "数据校验")
        model_tests = @("model tests", "model validation", "模型测试")
        service_smoke = @("smoke test", "service smoke", "服务冒烟")
        monitoring_metrics = @("monitoring metrics", "drift dashboard", "监控指标")
        retraining_plan = @("retraining plan", "retrain policy", "再训练计划")
        dataset_version = @("dataset version", "data version", "数据版本")
    }
    if ($MlLifecycleOverlayPolicy.artifact_keywords) {
        $artifactKeywordMap = [ordered]@{}
        foreach ($artifactName in @($MlLifecycleOverlayPolicy.artifact_keywords.PSObject.Properties.Name)) {
            $artifactKeywordMap[[string]$artifactName] = @($MlLifecycleOverlayPolicy.artifact_keywords.$artifactName)
        }
    }

    $confirmSignalMin = 0.5
    $highSignalMin = 0.75
    $suppressWeight = 0.28
    $minLifecycleHitsForOverlay = 1
    $missingArtifactRatioForConfirm = 0.4
    if ($MlLifecycleOverlayPolicy.thresholds) {
        if ($MlLifecycleOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmSignalMin = [double]$MlLifecycleOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$MlLifecycleOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$MlLifecycleOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($MlLifecycleOverlayPolicy.thresholds.min_lifecycle_hits_for_overlay -ne $null) {
            $minLifecycleHitsForOverlay = [int]$MlLifecycleOverlayPolicy.thresholds.min_lifecycle_hits_for_overlay
        }
        if ($MlLifecycleOverlayPolicy.thresholds.missing_artifact_ratio_for_confirm -ne $null) {
            $missingArtifactRatioForConfirm = [double]$MlLifecycleOverlayPolicy.thresholds.missing_artifact_ratio_for_confirm
        }
    }

    $signalMatches = @()
    foreach ($kw in $lifecycleKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $signalMatches += [string]$kw
        }
    }
    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $signalRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $lifecycleKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $lifecycleScore = [Math]::Max(0.0, [Math]::Min(1.0, ($signalRatio - ($suppressWeight * $suppressRatio))))
    if ($signalMatches.Count -lt $minLifecycleHitsForOverlay) {
        $lifecycleScore = 0.0
    }

    $stageScoreMap = [ordered]@{}
    $stageHitMap = [ordered]@{}
    $stageSummary = @()
    foreach ($stageName in @($stageKeywordMap.Keys)) {
        $stageKeywords = @($stageKeywordMap[$stageName])
        $hits = @()
        foreach ($kw in $stageKeywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $stageKeywords
        $stageScoreMap[[string]$stageName] = [Math]::Round([double]$score, 4)
        $stageHitMap[[string]$stageName] = @($hits)
        $stageSummary += [pscustomobject]@{
            stage = [string]$stageName
            score = [double]$score
            hits = @($hits)
        }
    }

    $topStage = $stageSummary | Sort-Object -Property @(
        @{ Expression = "score"; Descending = $true },
        @{ Expression = "stage"; Descending = $false }
    ) | Select-Object -First 1
    $stageDetected = if ($topStage -and ([double]$topStage.score -gt 0.0)) { [string]$topStage.stage } else { "none" }

    $requiredChecksByStage = [ordered]@{
        develop = @("code_tests", "data_tests")
        evaluate = @("data_tests", "model_tests", "baseline_compare")
        deploy = @("code_tests", "data_tests", "model_tests", "baseline_compare", "service_smoke")
        iterate = @("monitoring_metrics", "drift_guard", "retraining_plan")
    }
    if ($MlLifecycleOverlayPolicy.required_checks_by_stage) {
        $requiredChecksByStage = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.required_checks_by_stage.PSObject.Properties.Name)) {
            $requiredChecksByStage[[string]$stageName] = @($MlLifecycleOverlayPolicy.required_checks_by_stage.$stageName)
        }
    }

    $artifactsByStage = [ordered]@{
        develop = @("dataset_version")
        evaluate = @("run_id", "evaluation_results", "baseline_compare")
        deploy = @("run_id", "evaluation_results", "baseline_compare", "service_smoke")
        iterate = @("monitoring_metrics", "retraining_plan")
    }
    if ($MlLifecycleOverlayPolicy.artifacts_required_by_stage) {
        $artifactsByStage = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.artifacts_required_by_stage.PSObject.Properties.Name)) {
            $artifactsByStage[[string]$stageName] = @($MlLifecycleOverlayPolicy.artifacts_required_by_stage.$stageName)
        }
    }

    $artifactHits = [ordered]@{}
    foreach ($artifactName in @($artifactKeywordMap.Keys)) {
        $hits = @()
        foreach ($kw in @($artifactKeywordMap[$artifactName])) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $artifactHits[[string]$artifactName] = @($hits)
    }

    $requiredChecks = @()
    $artifactsRequired = @()
    if ($stageDetected -ne "none") {
        if ($requiredChecksByStage.Contains($stageDetected)) {
            $requiredChecks = @($requiredChecksByStage[$stageDetected])
        }
        if ($artifactsByStage.Contains($stageDetected)) {
            $artifactsRequired = @($artifactsByStage[$stageDetected])
        }
    }

    $missingArtifacts = @()
    foreach ($artifactName in $artifactsRequired) {
        $hits = @()
        if ($artifactHits.Contains([string]$artifactName)) {
            $hits = @($artifactHits[[string]$artifactName])
        }
        if ($hits.Count -eq 0) {
            $missingArtifacts += [string]$artifactName
        }
    }
    $missingArtifactRatio = if ($artifactsRequired.Count -gt 0) {
        [double]$missingArtifacts.Count / [double]$artifactsRequired.Count
    } else {
        0.0
    }
    $missingArtifactRatio = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $missingArtifactRatio)), 4)

    $deployReadiness = "not_applicable"
    if ($scopeApplicable -and ($stageDetected -in @("evaluate", "deploy", "iterate"))) {
        if (($missingArtifacts.Count -eq 0) -and ($lifecycleScore -ge $confirmSignalMin)) {
            $deployReadiness = "ready"
        } elseif (($missingArtifacts.Count -gt 0) -and ($lifecycleScore -ge $confirmSignalMin)) {
            $deployReadiness = "needs_confirmation"
        } else {
            $deployReadiness = "blocked"
        }
    }

    $lifecycleLikelihood = "none"
    if ($lifecycleScore -ge $highSignalMin) {
        $lifecycleLikelihood = "high"
    } elseif ($lifecycleScore -ge $confirmSignalMin) {
        $lifecycleLikelihood = "medium"
    } elseif ($lifecycleScore -gt 0) {
        $lifecycleLikelihood = "low"
    }

    $confirmRecommended = (
        $scopeApplicable -and
        ($lifecycleScore -ge $confirmSignalMin) -and
        (
            ($stageDetected -in @("evaluate", "deploy", "iterate")) -or
            ($missingArtifactRatio -ge $missingArtifactRatioForConfirm)
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("planning", "coding", "review")
    $strictStages = @("evaluate", "deploy", "iterate")
    if ($MlLifecycleOverlayPolicy.strict_confirm_scope) {
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($MlLifecycleOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($MlLifecycleOverlayPolicy.strict_confirm_scope.task_types)
        }
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.stages) {
            $strictStages = @($MlLifecycleOverlayPolicy.strict_confirm_scope.stages)
        }
    }
    $strictScopeApplied = (
        ($strictGrades -contains $Grade) -and
        ($strictTasks -contains $TaskType) -and
        ($strictStages -contains $stageDetected)
    )

    $confirmRequired = (
        $scopeApplicable -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        ($lifecycleScore -ge $confirmSignalMin) -and
        ($missingArtifacts.Count -gt 0)
    )

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                $enforcement = "advisory"
                if ($confirmRecommended) {
                    $reason = "soft_lifecycle_confirm_recommended"
                } else {
                    $reason = "soft_advisory"
                }
            }
            "strict" {
                if ($confirmRequired) {
                    $enforcement = "confirm_required"
                    $reason = "strict_missing_lifecycle_evidence"
                } else {
                    $enforcement = "advisory"
                    $reason = "strict_advisory"
                }
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $recommendedFollowup = $null
    if ($scopeApplicable -and ($lifecycleScore -gt 0.0)) {
        switch ($stageDetected) {
            "develop" { $recommendedFollowup = "Establish dataset versioning and run code/data checks before broad model training." }
            "evaluate" { $recommendedFollowup = "Attach run_id + evaluation report + baseline comparison before approval." }
            "deploy" { $recommendedFollowup = "Complete deployment readiness package: run_id, evaluation, baseline, and service smoke evidence." }
            "iterate" { $recommendedFollowup = "Attach monitoring metrics and retraining policy to close the continual-learning loop." }
            default { $recommendedFollowup = "Use an ML lifecycle checklist (code/data/model tests + experiment artifacts) before handoff." }
        }
    }

    $externalEnabled = $false
    $externalCommand = $null
    $externalInvokeMode = "disabled"
    $externalRunModes = @("soft", "strict")
    $externalSignalMin = $confirmSignalMin
    $manualCommandHint = $null
    if ($MlLifecycleOverlayPolicy.external_analyzer) {
        if ($MlLifecycleOverlayPolicy.external_analyzer.enabled -ne $null) {
            $externalEnabled = [bool]$MlLifecycleOverlayPolicy.external_analyzer.enabled
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.command) {
            $externalCommand = [string]$MlLifecycleOverlayPolicy.external_analyzer.command
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.invoke_mode) {
            $externalInvokeMode = [string]$MlLifecycleOverlayPolicy.external_analyzer.invoke_mode
        } elseif ($externalEnabled) {
            $externalInvokeMode = "manual_only"
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.run_in_modes) {
            $externalRunModes = @($MlLifecycleOverlayPolicy.external_analyzer.run_in_modes)
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.signal_score_min -ne $null) {
            $externalSignalMin = [double]$MlLifecycleOverlayPolicy.external_analyzer.signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.manual_command_hint) {
            $manualCommandHint = [string]$MlLifecycleOverlayPolicy.external_analyzer.manual_command_hint
        }
    }
    if (-not $manualCommandHint -and $externalCommand) {
        $manualCommandHint = "$externalCommand ui --host 127.0.0.1 --port 5000"
    }

    $externalStatus = "disabled"
    $externalToolAvailable = $false
    $externalShouldInvoke = $false
    if ($scopeApplicable -and $externalEnabled) {
        if (-not ($externalRunModes -contains $mode)) {
            $externalStatus = "skipped_mode"
        } elseif ($lifecycleScore -lt $externalSignalMin) {
            $externalStatus = "signal_below_threshold"
        } elseif (-not $externalCommand) {
            $externalStatus = "command_missing"
        } else {
            $externalShouldInvoke = $true
            $commandResolved = Get-Command -Name $externalCommand -ErrorAction SilentlyContinue
            if (-not $commandResolved) {
                $externalStatus = "tool_unavailable"
            } else {
                $externalToolAvailable = $true
                switch ($externalInvokeMode) {
                    "probe_only" { $externalStatus = "tool_available_probe_only" }
                    "manual_only" { $externalStatus = "not_executed_manual_mode" }
                    "auto" { $externalStatus = "auto_mode_not_implemented" }
                    default { $externalStatus = "not_executed" }
                }
            }
        }
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        pack_applicable = $packApplicable
        skill_applicable = $skillApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        lifecycle_signal_score = [Math]::Round([double]$lifecycleScore, 4)
        lifecycle_likelihood = $lifecycleLikelihood
        lifecycle_keyword_hits = @($signalMatches)
        suppress_keyword_hits = @($suppressMatches)
        stage_detected = $stageDetected
        stage_scores = [pscustomobject]$stageScoreMap
        stage_hits = [pscustomobject]$stageHitMap
        required_checks = @($requiredChecks)
        artifacts_required = @($artifactsRequired)
        artifact_hits = [pscustomobject]$artifactHits
        missing_artifacts = @($missingArtifacts)
        missing_artifact_ratio = [double]$missingArtifactRatio
        deploy_readiness = $deployReadiness
        confirm_recommended = $confirmRecommended
        confirm_required = $confirmRequired
        strict_scope_applied = $strictScopeApplied
        should_apply_hook = ($scopeApplicable -and (($lifecycleScore -gt 0.0) -or $confirmRequired))
        recommended_followup = $recommendedFollowup
        external_analyzer = [pscustomobject]@{
            enabled = $externalEnabled
            command = $externalCommand
            invoke_mode = $externalInvokeMode
            status = $externalStatus
            tool_available = $externalToolAvailable
            should_invoke = $externalShouldInvoke
            invoked = $false
            manual_command_hint = $manualCommandHint
            output_excerpt = $null
            error = $null
        }
    }
}

function Get-PythonCleanCodeAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$PythonCleanCodeOverlayPolicy
    )

    $base = [ordered]@{
        enabled = $false
        mode = "off"
        task_applicable = $false
        grade_applicable = $false
        pack_applicable = $false
        skill_applicable = $false
        scope_applicable = $false
        enforcement = "none"
        reason = "policy_missing"
        preserve_routing_assignment = $true
        paths_detected = @()
        paths_existing = @()
        python_file_signal = $false
        language_keyword_hits = @()
        principle_groups_matched = @()
        principle_group_hits = [pscustomobject]@{}
        principle_group_scores = [pscustomobject]@{}
        anti_pattern_hits = @()
        suppress_keyword_hits = @()
        python_signal_score = 0.0
        signal_likelihood = "none"
        trigger_active = $false
        confirm_recommended = $false
        confirm_required = $false
        strict_scope_applied = $false
        recommended_refactors = @()
        should_apply_hook = $false
    }

    if (-not $PythonCleanCodeOverlayPolicy) {
        return [pscustomobject]$base
    }

    $enabled = $true
    if ($PythonCleanCodeOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$PythonCleanCodeOverlayPolicy.enabled
    }
    $mode = if ($PythonCleanCodeOverlayPolicy.mode) { [string]$PythonCleanCodeOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        $base.enabled = $false
        $base.mode = "off"
        $base.reason = "policy_off"
        return [pscustomobject]$base
    }

    $taskAllow = @("coding", "review", "debug")
    if ($PythonCleanCodeOverlayPolicy.task_allow) {
        $taskAllow = @($PythonCleanCodeOverlayPolicy.task_allow)
    }
    $gradeAllow = @("M", "L", "XL")
    if ($PythonCleanCodeOverlayPolicy.grade_allow) {
        $gradeAllow = @($PythonCleanCodeOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    $skillAllow = @()
    if ($PythonCleanCodeOverlayPolicy.monitor) {
        if ($PythonCleanCodeOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($PythonCleanCodeOverlayPolicy.monitor.pack_allow)
        }
        if ($PythonCleanCodeOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($PythonCleanCodeOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($PythonCleanCodeOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$PythonCleanCodeOverlayPolicy.preserve_routing_assignment
    }

    $base.enabled = $true
    $base.mode = $mode
    $base.task_applicable = $taskApplicable
    $base.grade_applicable = $gradeApplicable
    $base.pack_applicable = $packApplicable
    $base.skill_applicable = $skillApplicable
    $base.scope_applicable = $scopeApplicable
    $base.preserve_routing_assignment = $preserveRoutingAssignment

    if (-not $scopeApplicable) {
        $base.reason = "outside_scope"
        return [pscustomobject]$base
    }

    $probeEnabled = $true
    $extractFromPrompt = $true
    $workspaceProbeWhenNoPath = $false
    $workspaceProbeLimit = 2
    $workspaceProbeExtensions = @("py", "pyi")
    if ($PythonCleanCodeOverlayPolicy.path_probe) {
        if ($PythonCleanCodeOverlayPolicy.path_probe.enabled -ne $null) {
            $probeEnabled = [bool]$PythonCleanCodeOverlayPolicy.path_probe.enabled
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.extract_from_prompt -ne $null) {
            $extractFromPrompt = [bool]$PythonCleanCodeOverlayPolicy.path_probe.extract_from_prompt
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_when_no_path -ne $null) {
            $workspaceProbeWhenNoPath = [bool]$PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_when_no_path
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_limit -ne $null) {
            $workspaceProbeLimit = [int]$PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_limit
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_extensions) {
            $workspaceProbeExtensions = @($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_extensions)
        }
    }

    $pathsDetected = @()
    if ($probeEnabled -and $extractFromPrompt) {
        $pathsDetected = Get-PathCandidatesFromPrompt -Prompt $Prompt -SupportedExtensions $workspaceProbeExtensions
    }
    $pathsExisting = @()
    if ($probeEnabled) {
        $pathsExisting = Resolve-ExistingPathCandidates `
            -PathCandidates $pathsDetected `
            -WorkspaceProbeEnabled $workspaceProbeWhenNoPath `
            -WorkspaceProbeLimit $workspaceProbeLimit `
            -WorkspaceProbeExtensions $workspaceProbeExtensions
    }

    $base.paths_detected = @($pathsDetected)
    $base.paths_existing = @($pathsExisting)
    $pythonFileSignal = (($pathsDetected.Count -gt 0) -or ($pathsExisting.Count -gt 0))
    $base.python_file_signal = $pythonFileSignal

    $languageKeywords = @(
        "python",
        ".py",
        ".pyi",
        "pytest",
        "dataclass",
        "type hints",
        "async def",
        "pep8",
        "pydantic",
        "flake8",
        "ruff",
        "mypy",
        "python文件",
        "python脚本",
        "写python",
        "重构python"
    )
    if ($PythonCleanCodeOverlayPolicy.language_keywords) {
        $languageKeywords = @($PythonCleanCodeOverlayPolicy.language_keywords)
    }

    $principleGroups = [ordered]@{
        naming = @("naming", "meaningful name", "clear name", "命名", "可读命名")
        function_design = @("single responsibility", "long function", "too many arguments", "boolean parameter", "函数过长", "参数过多", "布尔参数")
        class_design = @("solid", "class responsibility", "god object", "god class", "类职责", "大而全类")
        side_effects = @("side effect", "pure function", "immutable", "副作用", "纯函数")
        duplication = @("duplicate logic", "duplication", "dry", "重复代码", "去重逻辑")
        error_handling = @("raise", "exception handling", "error boundary", "异常处理", "错误处理")
        tests = @("pytest", "unit test", "testability", "可测试性", "单元测试")
    }
    if ($PythonCleanCodeOverlayPolicy.principle_groups) {
        $principleGroups = [ordered]@{}
        foreach ($groupName in @($PythonCleanCodeOverlayPolicy.principle_groups.PSObject.Properties.Name)) {
            $principleGroups[[string]$groupName] = @($PythonCleanCodeOverlayPolicy.principle_groups.$groupName)
        }
    }

    $antiPatternKeywords = @(
        "god class",
        "god object",
        "long function",
        "too many arguments",
        "boolean parameter",
        "magic number",
        "duplicate logic",
        "side effect",
        "spaghetti",
        "函数过长",
        "参数过多",
        "布尔参数",
        "魔法数字",
        "重复代码",
        "副作用"
    )
    if ($PythonCleanCodeOverlayPolicy.anti_pattern_keywords) {
        $antiPatternKeywords = @($PythonCleanCodeOverlayPolicy.anti_pattern_keywords)
    }

    $suppressKeywords = @(
        "generated",
        "migration",
        "vendor",
        "autogen",
        "docs only",
        "benchmark only",
        "notebook draft",
        "自动生成",
        "迁移脚本",
        "仅文档"
    )
    if ($PythonCleanCodeOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($PythonCleanCodeOverlayPolicy.suppress_keywords)
    }

    $triggerMin = 0.45
    $confirmMin = 0.6
    $highSignalMin = 0.78
    $suppressWeight = 0.25
    $minAntiHitsForConfirm = 1
    if ($PythonCleanCodeOverlayPolicy.thresholds) {
        if ($PythonCleanCodeOverlayPolicy.thresholds.trigger_signal_score_min -ne $null) {
            $triggerMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.trigger_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$PythonCleanCodeOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.min_anti_pattern_hits_for_confirm -ne $null) {
            $minAntiHitsForConfirm = [int]$PythonCleanCodeOverlayPolicy.thresholds.min_anti_pattern_hits_for_confirm
        }
    }

    $languageMatches = @()
    foreach ($kw in $languageKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $languageMatches += [string]$kw
        }
    }
    $antiPatternMatches = @()
    foreach ($kw in $antiPatternKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $antiPatternMatches += [string]$kw
        }
    }
    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $groupHits = [ordered]@{}
    $groupScores = [ordered]@{}
    $matchedGroups = @()
    $principleMatches = @()
    foreach ($groupName in @($principleGroups.Keys)) {
        $keywords = @($principleGroups[$groupName])
        $hits = @()
        foreach ($kw in $keywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords
        $groupHits[[string]$groupName] = @($hits)
        $groupScores[[string]$groupName] = [Math]::Round([double]$score, 4)
        if ($hits.Count -gt 0) {
            $matchedGroups += [string]$groupName
            $principleMatches += @($hits)
        }
    }

    $languageRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $languageKeywords
    $principleRatio = if ($principleMatches.Count -gt 0) { Get-KeywordRatio -PromptLower $PromptLower -Keywords @($principleMatches | Select-Object -Unique) } else { 0.0 }
    $antiPatternRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $antiPatternKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $fileSignal = if ($pythonFileSignal) { 1.0 } else { 0.0 }
    $semanticRatio = [Math]::Max([double]$principleRatio, [double]$antiPatternRatio)

    $signalScore = (0.65 * $fileSignal) + (0.20 * $languageRatio) + (0.15 * $semanticRatio) - ($suppressWeight * $suppressRatio)
    if ($pythonFileSignal -and $signalScore -lt $triggerMin) {
        $signalScore = [Math]::Max($signalScore, $triggerMin)
    }
    $signalScore = [Math]::Max(0.0, [Math]::Min(1.0, $signalScore))
    $signalScore = [Math]::Round([double]$signalScore, 4)

    $signalLikelihood = "none"
    if ($signalScore -ge $highSignalMin) {
        $signalLikelihood = "high"
    } elseif ($signalScore -ge $confirmMin) {
        $signalLikelihood = "medium"
    } elseif ($signalScore -gt 0) {
        $signalLikelihood = "low"
    }

    $triggerActive = ($scopeApplicable -and (($signalScore -ge $triggerMin) -or $pythonFileSignal))
    $confirmRecommended = (
        $triggerActive -and
        ($signalScore -ge $confirmMin) -and
        (
            ($antiPatternMatches.Count -ge $minAntiHitsForConfirm) -or
            ($matchedGroups.Count -ge 2) -or
            ($TaskType -eq "review")
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("coding", "review")
    if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope) {
        if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($PythonCleanCodeOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($PythonCleanCodeOverlayPolicy.strict_confirm_scope.task_types)
        }
    }
    $strictScopeApplied = (($strictGrades -contains $Grade) -and ($strictTasks -contains $TaskType))
    $confirmRequired = (
        $triggerActive -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        $confirmRecommended -and
        ($antiPatternMatches.Count -ge $minAntiHitsForConfirm)
    )

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        if (-not $triggerActive) {
            $enforcement = "advisory"
            $reason = "signal_below_threshold"
        } else {
            switch ($mode) {
                "shadow" {
                    $enforcement = "advisory"
                    $reason = "shadow_python_advisory"
                }
                "soft" {
                    $enforcement = "advisory"
                    if ($confirmRecommended) {
                        $reason = "soft_python_confirm_recommended"
                    } else {
                        $reason = "soft_python_advisory"
                    }
                }
                "strict" {
                    if ($confirmRequired) {
                        $enforcement = "confirm_required"
                        $reason = "strict_python_clean_code_confirmation"
                    } else {
                        $enforcement = "advisory"
                        $reason = "strict_python_advisory"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "unknown_mode_advisory"
                }
            }
        }
    }

    $recommendationMap = $null
    if ($PythonCleanCodeOverlayPolicy.recommendations_by_group) {
        $recommendationMap = $PythonCleanCodeOverlayPolicy.recommendations_by_group
    }
    $recommendedRefactors = @()
    if ($triggerActive) {
        $recommendationKeys = if ($recommendationMap) { @($recommendationMap.PSObject.Properties.Name) } else { @() }
        foreach ($groupName in @($matchedGroups)) {
            if ($recommendationMap -and ($recommendationKeys -contains $groupName)) {
                $recommendedRefactors += [string]$recommendationMap.$groupName
            }
        }
        if ($antiPatternMatches.Count -gt 0) {
            $recommendedRefactors += "Prioritize removing detected anti-pattern hotspots before adding new behavior."
        }
        if ($recommendedRefactors.Count -eq 0) {
            $recommendedRefactors += "Apply Python clean-code checks: naming clarity, function focus, side-effect isolation, and duplication cleanup."
        }
    }

    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.language_keyword_hits = @($languageMatches)
    $base.principle_groups_matched = @($matchedGroups)
    $base.principle_group_hits = [pscustomobject]$groupHits
    $base.principle_group_scores = [pscustomobject]$groupScores
    $base.anti_pattern_hits = @($antiPatternMatches)
    $base.suppress_keyword_hits = @($suppressMatches)
    $base.python_signal_score = $signalScore
    $base.signal_likelihood = $signalLikelihood
    $base.trigger_active = $triggerActive
    $base.confirm_recommended = $confirmRecommended
    $base.confirm_required = $confirmRequired
    $base.strict_scope_applied = $strictScopeApplied
    $base.recommended_refactors = @($recommendedRefactors | Select-Object -Unique)
    $base.should_apply_hook = ($scopeApplicable -and $triggerActive)

    return [pscustomobject]$base
}

function Get-SystemDesignOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$SystemDesignOverlayPolicy
    )

    $base = [ordered]@{
        enabled = $false
        mode = "off"
        task_applicable = $false
        grade_applicable = $false
        pack_applicable = $false
        skill_applicable = $false
        scope_applicable = $false
        enforcement = "none"
        reason = "policy_missing"
        preserve_routing_assignment = $true
        architecture_signal_score = 0.0
        architecture_likelihood = "none"
        positive_keyword_hits = @()
        negative_keyword_hits = @()
        dimension_count = 0
        dimensions_matched = @()
        dimensions_missing = @()
        dimension_hits = [pscustomobject]@{}
        dimension_scores = [pscustomobject]@{}
        coverage_score = 0.0
        coverage_ready = $false
        trigger_active = $false
        confirm_recommended = $false
        confirm_required = $false
        strict_scope_applied = $false
        recommended_artifacts = @()
        recommended_focus = @()
        recommended_followup = $null
        should_apply_hook = $false
    }

    if (-not $SystemDesignOverlayPolicy) {
        return [pscustomobject]$base
    }

    $enabled = $true
    if ($SystemDesignOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$SystemDesignOverlayPolicy.enabled
    }

    $mode = if ($SystemDesignOverlayPolicy.mode) { [string]$SystemDesignOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        $base.enabled = $false
        $base.mode = "off"
        $base.reason = "policy_off"
        return [pscustomobject]$base
    }

    $taskAllow = @("planning", "research", "review")
    if ($SystemDesignOverlayPolicy.task_allow) {
        $taskAllow = @($SystemDesignOverlayPolicy.task_allow)
    }

    $gradeAllow = @("L", "XL")
    if ($SystemDesignOverlayPolicy.grade_allow) {
        $gradeAllow = @($SystemDesignOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    $skillAllow = @()
    if ($SystemDesignOverlayPolicy.monitor) {
        if ($SystemDesignOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($SystemDesignOverlayPolicy.monitor.pack_allow)
        }
        if ($SystemDesignOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($SystemDesignOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($SystemDesignOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$SystemDesignOverlayPolicy.preserve_routing_assignment
    }

    $base.enabled = $true
    $base.mode = $mode
    $base.task_applicable = $taskApplicable
    $base.grade_applicable = $gradeApplicable
    $base.pack_applicable = $packApplicable
    $base.skill_applicable = $skillApplicable
    $base.scope_applicable = $scopeApplicable
    $base.preserve_routing_assignment = $preserveRoutingAssignment

    if (-not $scopeApplicable) {
        $base.reason = "outside_scope"
        return [pscustomobject]$base
    }

    $positiveKeywords = @(
        "system design",
        "architecture design",
        "distributed system",
        "high availability",
        "scalability",
        "throughput",
        "latency",
        "qps",
        "rps",
        "capacity planning",
        "consistency model",
        "message queue",
        "partition",
        "replication",
        "failover",
        "observability",
        "系统设计",
        "架构设计",
        "分布式系统",
        "高可用",
        "扩展性",
        "吞吐",
        "延迟",
        "容量规划",
        "一致性模型",
        "分片",
        "复制",
        "故障切换"
    )
    if ($SystemDesignOverlayPolicy.positive_keywords) {
        $positiveKeywords = @($SystemDesignOverlayPolicy.positive_keywords)
    }

    $negativeKeywords = @(
        "interview prep",
        "system design interview",
        "flashcard",
        "anki",
        "quiz only",
        "面试八股",
        "刷题",
        "背题"
    )
    if ($SystemDesignOverlayPolicy.negative_keywords) {
        $negativeKeywords = @($SystemDesignOverlayPolicy.negative_keywords)
    }

    $coverageDimensions = [ordered]@{
        requirements = @("functional requirement", "non functional requirement", "scope", "acceptance criteria", "功能需求", "非功能需求", "范围")
        nfr_latency_throughput = @("latency", "throughput", "p95", "p99", "qps", "rps", "slo", "sla", "延迟", "吞吐")
        capacity_estimate = @("capacity", "estimate", "traffic growth", "sizing", "容量估算", "流量增长")
        consistency_availability = @("consistency", "availability", "cap theorem", "eventual consistency", "quorum", "一致性", "可用性", "最终一致")
        cache_strategy = @("cache", "ttl", "cache invalidation", "cache aside", "redis", "缓存", "缓存策略")
        data_partitioning_replication = @("shard", "partition", "replication", "read replica", "multi region", "分片", "分区", "复制")
        async_backpressure = @("message queue", "stream", "backpressure", "retry", "idempotent", "消息队列", "背压", "重试", "幂等")
        failure_recovery = @("failover", "circuit breaker", "degrade", "disaster recovery", "rto", "rpo", "故障切换", "熔断", "降级", "容灾")
        observability = @("metrics", "logging", "tracing", "dashboard", "alert", "监控", "日志", "追踪", "告警")
        cost_tradeoff = @("cost", "tradeoff", "budget", "cost optimization", "tco", "成本", "权衡", "预算")
    }
    if ($SystemDesignOverlayPolicy.coverage_dimensions) {
        $coverageDimensions = [ordered]@{}
        foreach ($dimensionName in @($SystemDesignOverlayPolicy.coverage_dimensions.PSObject.Properties.Name)) {
            $coverageDimensions[[string]$dimensionName] = @($SystemDesignOverlayPolicy.coverage_dimensions.$dimensionName)
        }
    }

    $triggerMin = 0.45
    $confirmMin = 0.58
    $highSignalMin = 0.78
    $suppressWeight = 0.24
    $minDimensionHitsForOverlay = 2
    $minCoverageScoreForReady = 0.6
    $minCoverageScoreForStrictConfirm = 0.72
    if ($SystemDesignOverlayPolicy.thresholds) {
        if ($SystemDesignOverlayPolicy.thresholds.trigger_signal_score_min -ne $null) {
            $triggerMin = [double]$SystemDesignOverlayPolicy.thresholds.trigger_signal_score_min
        }
        if ($SystemDesignOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmMin = [double]$SystemDesignOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($SystemDesignOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$SystemDesignOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($SystemDesignOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$SystemDesignOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($SystemDesignOverlayPolicy.thresholds.min_dimension_hits_for_overlay -ne $null) {
            $minDimensionHitsForOverlay = [int]$SystemDesignOverlayPolicy.thresholds.min_dimension_hits_for_overlay
        }
        if ($SystemDesignOverlayPolicy.thresholds.min_coverage_score_for_ready -ne $null) {
            $minCoverageScoreForReady = [double]$SystemDesignOverlayPolicy.thresholds.min_coverage_score_for_ready
        }
        if ($SystemDesignOverlayPolicy.thresholds.min_coverage_score_for_strict_confirm -ne $null) {
            $minCoverageScoreForStrictConfirm = [double]$SystemDesignOverlayPolicy.thresholds.min_coverage_score_for_strict_confirm
        }
    }

    $positiveMatches = @()
    foreach ($kw in $positiveKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $positiveMatches += [string]$kw
        }
    }

    $negativeMatches = @()
    foreach ($kw in $negativeKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $negativeMatches += [string]$kw
        }
    }

    $dimensionHits = [ordered]@{}
    $dimensionScores = [ordered]@{}
    $dimensionsMatched = @()
    $dimensionsMissing = @()

    foreach ($dimensionName in @($coverageDimensions.Keys)) {
        $keywords = @($coverageDimensions[$dimensionName])
        $hits = @()
        foreach ($kw in $keywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords
        $dimensionHits[[string]$dimensionName] = @($hits)
        $dimensionScores[[string]$dimensionName] = [Math]::Round([double]$score, 4)
        if ($hits.Count -gt 0) {
            $dimensionsMatched += [string]$dimensionName
        } else {
            $dimensionsMissing += [string]$dimensionName
        }
    }

    $dimensionCount = @($coverageDimensions.Keys).Count
    $dimensionMatchedCount = $dimensionsMatched.Count
    $coverageScore = 0.0
    if ($dimensionCount -gt 0) {
        $coverageScore = [double]$dimensionMatchedCount / [double]$dimensionCount
    }
    $coverageScore = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $coverageScore)), 4)
    $coverageReady = ($coverageScore -ge $minCoverageScoreForReady)

    $positiveRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $positiveKeywords
    $negativeRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $negativeKeywords
    $signalScore = (0.6 * $positiveRatio) + (0.3 * $coverageScore) - ($suppressWeight * $negativeRatio)

    if (($dimensionMatchedCount -ge $minDimensionHitsForOverlay) -and ($signalScore -lt $triggerMin)) {
        $signalScore = [Math]::Max($signalScore, $triggerMin)
    }
    $signalScore = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $signalScore)), 4)

    $signalLikelihood = "none"
    if ($signalScore -ge $highSignalMin) {
        $signalLikelihood = "high"
    } elseif ($signalScore -ge $confirmMin) {
        $signalLikelihood = "medium"
    } elseif ($signalScore -gt 0) {
        $signalLikelihood = "low"
    }

    $triggerActive = ($scopeApplicable -and (($signalScore -ge $triggerMin) -or ($dimensionMatchedCount -ge $minDimensionHitsForOverlay)))
    $confirmRecommended = (
        $triggerActive -and
        (
            ($signalScore -ge $confirmMin) -or
            (-not $coverageReady) -or
            ($TaskType -eq "review")
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("planning", "review")
    if ($SystemDesignOverlayPolicy.strict_confirm_scope) {
        if ($SystemDesignOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($SystemDesignOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($SystemDesignOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($SystemDesignOverlayPolicy.strict_confirm_scope.task_types)
        }
    }
    $strictScopeApplied = (($strictGrades -contains $Grade) -and ($strictTasks -contains $TaskType))
    $confirmRequired = (
        $triggerActive -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        $confirmRecommended -and
        ($coverageScore -lt $minCoverageScoreForStrictConfirm)
    )

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        if (-not $triggerActive) {
            $enforcement = "advisory"
            $reason = "signal_below_threshold"
        } else {
            switch ($mode) {
                "shadow" {
                    $enforcement = "advisory"
                    $reason = "shadow_system_design_advisory"
                }
                "soft" {
                    $enforcement = "advisory"
                    if ($confirmRecommended) {
                        $reason = "soft_system_design_confirm_recommended"
                    } else {
                        $reason = "soft_system_design_advisory"
                    }
                }
                "strict" {
                    if ($confirmRequired) {
                        $enforcement = "confirm_required"
                        $reason = "strict_system_design_confirm_required"
                    } else {
                        $enforcement = "advisory"
                        $reason = "strict_system_design_advisory"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "unknown_mode_advisory"
                }
            }
        }
    }

    $artifactContract = @(
        "architecture-one-pager",
        "capacity-note",
        "tradeoff-matrix",
        "risk-register"
    )
    if ($SystemDesignOverlayPolicy.artifact_contract) {
        $artifactContract = @($SystemDesignOverlayPolicy.artifact_contract)
    }

    $recommendationMap = $null
    if ($SystemDesignOverlayPolicy.recommendations_by_dimension) {
        $recommendationMap = $SystemDesignOverlayPolicy.recommendations_by_dimension
    }

    $recommendedArtifacts = @()
    $recommendedFocus = @()
    if ($triggerActive) {
        $recommendedArtifacts = @($artifactContract)
        $recommendationKeys = if ($recommendationMap) { @($recommendationMap.PSObject.Properties.Name) } else { @() }
        foreach ($dimensionName in @($dimensionsMatched)) {
            if ($recommendationMap -and ($recommendationKeys -contains $dimensionName)) {
                $recommendedFocus += [string]$recommendationMap.$dimensionName
            }
        }
        if ($recommendedFocus.Count -eq 0) {
            $recommendedFocus += "Cover missing architecture dimensions before implementation: capacity, consistency, failure handling, and observability."
        }
    }

    $recommendedFollowup = $null
    if ($triggerActive) {
        $recommendedFollowup = "Before execution, complete architecture artifacts: $($artifactContract -join ', ')."
    }

    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.architecture_signal_score = $signalScore
    $base.architecture_likelihood = $signalLikelihood
    $base.positive_keyword_hits = @($positiveMatches)
    $base.negative_keyword_hits = @($negativeMatches)
    $base.dimension_count = $dimensionCount
    $base.dimensions_matched = @($dimensionsMatched)
    $base.dimensions_missing = @($dimensionsMissing)
    $base.dimension_hits = [pscustomobject]$dimensionHits
    $base.dimension_scores = [pscustomobject]$dimensionScores
    $base.coverage_score = $coverageScore
    $base.coverage_ready = $coverageReady
    $base.trigger_active = $triggerActive
    $base.confirm_recommended = $confirmRecommended
    $base.confirm_required = $confirmRequired
    $base.strict_scope_applied = $strictScopeApplied
    $base.recommended_artifacts = @($recommendedArtifacts)
    $base.recommended_focus = @($recommendedFocus | Select-Object -Unique)
    $base.recommended_followup = $recommendedFollowup
    $base.should_apply_hook = ($scopeApplicable -and ($triggerActive -or $confirmRequired))

    return [pscustomobject]$base
}

function Get-CudaKernelOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [object[]]$PackCandidates,
        [object]$CudaKernelOverlayPolicy
    )

    $base = [ordered]@{
        enabled = $false
        mode = "off"
        task_applicable = $false
        grade_applicable = $false
        pack_applicable = $false
        skill_applicable = $false
        scope_applicable = $false
        preserve_routing_assignment = $true
        enforcement = "none"
        reason = "policy_missing"
        cuda_signal_score = 0.0
        cuda_likelihood = "none"
        positive_keyword_hits = @()
        negative_keyword_hits = @()
        file_signal_hits = @()
        environment_signal_hits = @()
        dimension_count = 0
        dimensions_matched = @()
        dimensions_missing = @()
        dimension_hits = [pscustomobject]@{}
        dimension_scores = [pscustomobject]@{}
        coverage_score = 0.0
        coverage_ready = $false
        trigger_active = $false
        confirm_recommended = $false
        confirm_required = $false
        strict_scope_applied = $false
        recommended_artifacts = @()
        recommended_focus = @()
        recommended_followup = $null
        should_apply_hook = $false
        license_boundary_note = $null
    }

    if (-not $CudaKernelOverlayPolicy) {
        return [pscustomobject]$base
    }

    $enabled = $true
    if ($CudaKernelOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$CudaKernelOverlayPolicy.enabled
    }

    $mode = if ($CudaKernelOverlayPolicy.mode) { [string]$CudaKernelOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        $base.enabled = $false
        $base.mode = "off"
        $base.reason = "policy_off"
        return [pscustomobject]$base
    }

    $taskAllow = @("coding", "debug", "research")
    if ($CudaKernelOverlayPolicy.task_allow) {
        $taskAllow = @($CudaKernelOverlayPolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($CudaKernelOverlayPolicy.grade_allow) {
        $gradeAllow = @($CudaKernelOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    $skillAllow = @()
    if ($CudaKernelOverlayPolicy.monitor) {
        if ($CudaKernelOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($CudaKernelOverlayPolicy.monitor.pack_allow)
        }
        if ($CudaKernelOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($CudaKernelOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($CudaKernelOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$CudaKernelOverlayPolicy.preserve_routing_assignment
    }

    $base.enabled = $true
    $base.mode = $mode
    $base.task_applicable = $taskApplicable
    $base.grade_applicable = $gradeApplicable
    $base.pack_applicable = $packApplicable
    $base.skill_applicable = $skillApplicable
    $base.scope_applicable = $scopeApplicable
    $base.preserve_routing_assignment = $preserveRoutingAssignment

    $licenseBoundaryNote = if ($CudaKernelOverlayPolicy.license_boundary_note) {
        [string]$CudaKernelOverlayPolicy.license_boundary_note
    } else {
        "LeetCUDA upstream is GPL-3.0. Use methodology-level advisory only; avoid upstream code vendoring."
    }
    $base.license_boundary_note = $licenseBoundaryNote

    if (-not $scopeApplicable) {
        $base.reason = "outside_scope"
        return [pscustomobject]$base
    }

    $positiveKeywords = @(
        "cuda kernel", "gpu kernel", "cuda optimization", "kernel optimization", "ptx", "wmma", "mma",
        "tensor core", "shared memory", "bank conflict", "occupancy", "warp", "block size", "coalesced",
        "register pressure", "flash attention", "hgemm", "nsight compute", "nvprof", "cuda内核", "ptx优化",
        "tensor core优化", "共享内存", "bank冲突", "占用率", "核函数优化"
    )
    if ($CudaKernelOverlayPolicy.positive_keywords) {
        $positiveKeywords = @($CudaKernelOverlayPolicy.positive_keywords)
    }

    $negativeKeywords = @(
        "leetcode interview", "algorithm interview", "刷题", "面试题", "frontend css",
        "benchmarkdotnet", "csharp benchmark", "excel format"
    )
    if ($CudaKernelOverlayPolicy.negative_keywords) {
        $negativeKeywords = @($CudaKernelOverlayPolicy.negative_keywords)
    }

    $fileSignalKeywords = @(".cu", ".cuh", ".ptx", ".cubin", "nvcc", "cuda/", "kernels/", "torch.utils.cpp_extension")
    if ($CudaKernelOverlayPolicy.file_signals) {
        $fileSignalKeywords = @()
        if ($CudaKernelOverlayPolicy.file_signals.extensions) {
            $fileSignalKeywords += @($CudaKernelOverlayPolicy.file_signals.extensions)
        }
        if ($CudaKernelOverlayPolicy.file_signals.path_keywords) {
            $fileSignalKeywords += @($CudaKernelOverlayPolicy.file_signals.path_keywords)
        }
        if ($CudaKernelOverlayPolicy.file_signals.build_indicators) {
            $fileSignalKeywords += @($CudaKernelOverlayPolicy.file_signals.build_indicators)
        }
    }

    $environmentKeywords = @("nvidia-smi", "cuda", "gpu", "sm80", "sm90", "compute capability")
    if ($CudaKernelOverlayPolicy.environment_signals) {
        $environmentKeywords = @($CudaKernelOverlayPolicy.environment_signals)
    }

    $optimizationDimensions = [ordered]@{
        kernel_target = @("target kernel", "hotspot", "operator", "算子", "热点内核")
        memory_hierarchy = @("global memory", "shared memory", "l2", "bank conflict", "coalesced", "访存", "共享内存")
        tensor_core_usage = @("tensor core", "wmma", "mma", "tf32", "bf16", "fp16", "张量核")
        occupancy_parallelism = @("occupancy", "warp", "block size", "thread block", "register pressure", "占用率")
        profiling_evidence = @("nsight compute", "nsys", "nvprof", "roofline", "benchmark", "性能剖析")
        correctness_guard = @("numerical parity", "tolerance", "correctness", "unit test", "regression test", "数值一致")
        integration_fallback = @("fallback", "cpu fallback", "degrade", "feature flag", "回退路径", "降级")
        hardware_context = @("gpu model", "driver", "cuda version", "sm architecture", "显卡型号", "驱动版本")
    }
    if ($CudaKernelOverlayPolicy.optimization_dimensions) {
        $optimizationDimensions = [ordered]@{}
        foreach ($dimensionName in @($CudaKernelOverlayPolicy.optimization_dimensions.PSObject.Properties.Name)) {
            $optimizationDimensions[[string]$dimensionName] = @($CudaKernelOverlayPolicy.optimization_dimensions.$dimensionName)
        }
    }

    $triggerMin = 0.42
    $confirmMin = 0.56
    $highSignalMin = 0.78
    $negativePenaltyWeight = 0.22
    $minDimensionHitsForOverlay = 2
    $minCoverageScoreForReady = 0.55
    $minCoverageScoreForStrictConfirm = 0.75
    if ($CudaKernelOverlayPolicy.thresholds) {
        if ($CudaKernelOverlayPolicy.thresholds.trigger_signal_score_min -ne $null) {
            $triggerMin = [double]$CudaKernelOverlayPolicy.thresholds.trigger_signal_score_min
        }
        if ($CudaKernelOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmMin = [double]$CudaKernelOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($CudaKernelOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$CudaKernelOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($CudaKernelOverlayPolicy.thresholds.negative_penalty_weight -ne $null) {
            $negativePenaltyWeight = [double]$CudaKernelOverlayPolicy.thresholds.negative_penalty_weight
        }
        if ($CudaKernelOverlayPolicy.thresholds.min_dimension_hits_for_overlay -ne $null) {
            $minDimensionHitsForOverlay = [int]$CudaKernelOverlayPolicy.thresholds.min_dimension_hits_for_overlay
        }
        if ($CudaKernelOverlayPolicy.thresholds.min_coverage_score_for_ready -ne $null) {
            $minCoverageScoreForReady = [double]$CudaKernelOverlayPolicy.thresholds.min_coverage_score_for_ready
        }
        if ($CudaKernelOverlayPolicy.thresholds.min_coverage_score_for_strict_confirm -ne $null) {
            $minCoverageScoreForStrictConfirm = [double]$CudaKernelOverlayPolicy.thresholds.min_coverage_score_for_strict_confirm
        }
    }

    $positiveMatches = @()
    foreach ($kw in $positiveKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $positiveMatches += [string]$kw
        }
    }

    $negativeMatches = @()
    foreach ($kw in $negativeKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $negativeMatches += [string]$kw
        }
    }

    $fileSignalMatches = @()
    foreach ($kw in $fileSignalKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $fileSignalMatches += [string]$kw
        }
    }

    $environmentSignalMatches = @()
    foreach ($kw in $environmentKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $environmentSignalMatches += [string]$kw
        }
    }

    $dimensionHits = [ordered]@{}
    $dimensionScores = [ordered]@{}
    $dimensionsMatched = @()
    $dimensionsMissing = @()

    foreach ($dimensionName in @($optimizationDimensions.Keys)) {
        $keywords = @($optimizationDimensions[$dimensionName])
        $hits = @()
        foreach ($kw in $keywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords
        $dimensionHits[[string]$dimensionName] = @($hits)
        $dimensionScores[[string]$dimensionName] = [Math]::Round([double]$score, 4)
        if ($hits.Count -gt 0) {
            $dimensionsMatched += [string]$dimensionName
        } else {
            $dimensionsMissing += [string]$dimensionName
        }
    }

    $dimensionCount = @($optimizationDimensions.Keys).Count
    $dimensionMatchedCount = $dimensionsMatched.Count
    $coverageScore = 0.0
    if ($dimensionCount -gt 0) {
        $coverageScore = [double]$dimensionMatchedCount / [double]$dimensionCount
    }
    $coverageScore = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $coverageScore)), 4)
    $coverageReady = ($coverageScore -ge $minCoverageScoreForReady)

    $positiveRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $positiveKeywords
    $negativeRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $negativeKeywords
    $fileSignalRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $fileSignalKeywords
    $environmentRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $environmentKeywords

    $contextBoost = 0.0
    if ($SelectedPackId -eq "data-ml") {
        $contextBoost += 0.06
    } elseif ($SelectedPackId -eq "code-quality") {
        $contextBoost += 0.04
    }
    if ($PackCandidates -and (@($PackCandidates) -contains "performance-testing")) {
        $contextBoost += 0.02
    }

    $signalScore = (0.52 * $positiveRatio) + (0.24 * $coverageScore) + (0.14 * $fileSignalRatio) + (0.08 * $environmentRatio) + $contextBoost - ($negativePenaltyWeight * $negativeRatio)

    if (($dimensionMatchedCount -ge $minDimensionHitsForOverlay) -and ($fileSignalMatches.Count -gt 0) -and ($signalScore -lt $triggerMin)) {
        $signalScore = [Math]::Max($signalScore, $triggerMin)
    }
    $signalScore = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $signalScore)), 4)

    $signalLikelihood = "none"
    if ($signalScore -ge $highSignalMin) {
        $signalLikelihood = "high"
    } elseif ($signalScore -ge $confirmMin) {
        $signalLikelihood = "medium"
    } elseif ($signalScore -gt 0) {
        $signalLikelihood = "low"
    }

    $triggerActive = (
        $scopeApplicable -and (
            ($signalScore -ge $triggerMin) -or
            (($dimensionMatchedCount -ge $minDimensionHitsForOverlay) -and ($fileSignalMatches.Count -gt 0))
        )
    )

    $confirmRecommended = (
        $triggerActive -and (
            ($signalScore -ge $confirmMin) -or
            (-not $coverageReady) -or
            ($TaskType -eq "debug")
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("coding", "debug")
    if ($CudaKernelOverlayPolicy.strict_confirm_scope) {
        if ($CudaKernelOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($CudaKernelOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($CudaKernelOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($CudaKernelOverlayPolicy.strict_confirm_scope.task_types)
        }
    }
    $strictScopeApplied = (($strictGrades -contains $Grade) -and ($strictTasks -contains $TaskType))
    $confirmRequired = (
        $triggerActive -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        $confirmRecommended -and
        ($coverageScore -lt $minCoverageScoreForStrictConfirm)
    )

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        if (-not $triggerActive) {
            $enforcement = "advisory"
            $reason = "signal_below_threshold"
        } else {
            switch ($mode) {
                "shadow" {
                    $enforcement = "advisory"
                    $reason = "shadow_cuda_kernel_advisory"
                }
                "soft" {
                    $enforcement = "advisory"
                    if ($confirmRecommended) {
                        $reason = "soft_cuda_confirm_recommended"
                    } else {
                        $reason = "soft_cuda_advisory"
                    }
                }
                "strict" {
                    if ($confirmRequired) {
                        $enforcement = "confirm_required"
                        $reason = "strict_cuda_confirm_required"
                    } else {
                        $enforcement = "advisory"
                        $reason = "strict_cuda_advisory"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "unknown_mode_advisory"
                }
            }
        }
    }

    $artifactContract = @(
        "kernel-baseline-benchmark",
        "kernel-optimization-log",
        "kernel-correctness-checklist",
        "hardware-context-note"
    )
    if ($CudaKernelOverlayPolicy.artifact_contract) {
        $artifactContract = @($CudaKernelOverlayPolicy.artifact_contract)
    }

    $recommendationMap = $null
    if ($CudaKernelOverlayPolicy.recommendations_by_dimension) {
        $recommendationMap = $CudaKernelOverlayPolicy.recommendations_by_dimension
    }

    $recommendedArtifacts = @()
    $recommendedFocus = @()
    if ($triggerActive) {
        $recommendedArtifacts = @($artifactContract)
        $recommendationKeys = if ($recommendationMap) { @($recommendationMap.PSObject.Properties.Name) } else { @() }
        foreach ($dimensionName in @($dimensionsMissing)) {
            if ($recommendationMap -and ($recommendationKeys -contains $dimensionName)) {
                $recommendedFocus += [string]$recommendationMap.$dimensionName
            }
        }
        if ($recommendedFocus.Count -eq 0) {
            foreach ($dimensionName in @($dimensionsMatched)) {
                if ($recommendationMap -and ($recommendationKeys -contains $dimensionName)) {
                    $recommendedFocus += [string]$recommendationMap.$dimensionName
                }
            }
        }
        if ($recommendedFocus.Count -eq 0) {
            $recommendedFocus += "Before kernel changes, ensure profiling evidence, correctness checks, and fallback strategy are explicit."
        }
    }

    $recommendedFollowup = $null
    if ($triggerActive) {
        $recommendedFollowup = "Before execution, produce kernel optimization artifacts: $($artifactContract -join ', ')."
    }

    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.cuda_signal_score = $signalScore
    $base.cuda_likelihood = $signalLikelihood
    $base.positive_keyword_hits = @($positiveMatches)
    $base.negative_keyword_hits = @($negativeMatches)
    $base.file_signal_hits = @($fileSignalMatches)
    $base.environment_signal_hits = @($environmentSignalMatches)
    $base.dimension_count = $dimensionCount
    $base.dimensions_matched = @($dimensionsMatched)
    $base.dimensions_missing = @($dimensionsMissing)
    $base.dimension_hits = [pscustomobject]$dimensionHits
    $base.dimension_scores = [pscustomobject]$dimensionScores
    $base.coverage_score = $coverageScore
    $base.coverage_ready = $coverageReady
    $base.trigger_active = $triggerActive
    $base.confirm_recommended = $confirmRecommended
    $base.confirm_required = $confirmRequired
    $base.strict_scope_applied = $strictScopeApplied
    $base.recommended_artifacts = @($recommendedArtifacts)
    $base.recommended_focus = @($recommendedFocus | Select-Object -Unique)
    $base.recommended_followup = $recommendedFollowup
    $base.should_apply_hook = ($scopeApplicable -and ($triggerActive -or $confirmRequired))

    return [pscustomobject]$base
}

function Select-PackCandidate {
    param(
        [string]$PromptLower,
        [string[]]$Candidates,
        [string]$TaskType,
        [string]$RequestedCanonical,
        [object]$SkillKeywordIndex,
        [object]$RoutingRules,
        [object]$Pack,
        [object]$CandidateSelectionConfig
    )

    if (-not $Candidates -or $Candidates.Count -eq 0) {
        return [pscustomobject]@{
            selected = $null
            score = 0.0
            reason = "no_candidates"
            ranking = @()
            top1_top2_gap = 0.0
            filtered_out_by_task = @()
        }
    }

    if ($RequestedCanonical -and ($Candidates -contains $RequestedCanonical)) {
        return [pscustomobject]@{
            selected = $RequestedCanonical
            score = 1.0
            reason = "requested_skill"
            ranking = @(
                [pscustomobject]@{
                    skill = $RequestedCanonical
                    score = 1.0
                    keyword_score = 1.0
                    name_score = 1.0
                    positive_score = 1.0
                    negative_score = 0.0
                    canonical_for_task_hit = 1.0
                }
            )
            top1_top2_gap = 1.0
            filtered_out_by_task = @()
        }
    }

    $weightKeyword = 0.8
    $weightName = 0.2
    $fallbackMin = 0.2
    if ($SkillKeywordIndex -and $SkillKeywordIndex.selection -and $SkillKeywordIndex.selection.weights) {
        if ($SkillKeywordIndex.selection.weights.keyword_match -ne $null) {
            $weightKeyword = [double]$SkillKeywordIndex.selection.weights.keyword_match
        }
        if ($SkillKeywordIndex.selection.weights.name_match -ne $null) {
            $weightName = [double]$SkillKeywordIndex.selection.weights.name_match
        }
    }
    if ($SkillKeywordIndex -and $SkillKeywordIndex.selection -and $SkillKeywordIndex.selection.fallback_to_first_when_score_below -ne $null) {
        $fallbackMin = [double]$SkillKeywordIndex.selection.fallback_to_first_when_score_below
    }

    $positiveBonus = 0.2
    $negativePenalty = 0.25
    $canonicalBonus = 0.12
    if ($CandidateSelectionConfig) {
        if ($CandidateSelectionConfig.rule_positive_keyword_bonus -ne $null) {
            $positiveBonus = [double]$CandidateSelectionConfig.rule_positive_keyword_bonus
        }
        if ($CandidateSelectionConfig.rule_negative_keyword_penalty -ne $null) {
            $negativePenalty = [double]$CandidateSelectionConfig.rule_negative_keyword_penalty
        }
        if ($CandidateSelectionConfig.canonical_for_task_bonus -ne $null) {
            $canonicalBonus = [double]$CandidateSelectionConfig.canonical_for_task_bonus
        }
    }

    $filteredCandidates = @()
    $blockedByTask = @()
    foreach ($candidate in $Candidates) {
        $rule = Get-RoutingRuleForCandidate -Candidate $candidate -RoutingRules $RoutingRules
        if (Test-RuleTaskAllowed -Rule $rule -TaskType $TaskType) {
            $filteredCandidates += $candidate
        } else {
            $blockedByTask += $candidate
        }
    }

    $defaultCandidate = Get-PackDefaultCandidate -Pack $Pack -TaskType $TaskType -PreferredCandidates $filteredCandidates -AllCandidates $Candidates

    if ($filteredCandidates.Count -eq 0) {
        if ($defaultCandidate) {
            return [pscustomobject]@{
                selected = $defaultCandidate
                score = 0.0
                reason = "fallback_task_default_after_task_filter"
                ranking = @()
                top1_top2_gap = 0.0
                filtered_out_by_task = @($blockedByTask)
            }
        }

        return [pscustomobject]@{
            selected = $Candidates[0]
            score = 0.0
            reason = "fallback_first_candidate_after_task_filter"
            ranking = @()
            top1_top2_gap = 0.0
            filtered_out_by_task = @($blockedByTask)
        }
    }

    $scored = @()
    for ($i = 0; $i -lt $filteredCandidates.Count; $i++) {
        $candidate = [string]$filteredCandidates[$i]
        $rule = Get-RoutingRuleForCandidate -Candidate $candidate -RoutingRules $RoutingRules

        $keywordScore = Get-SkillKeywordScore -PromptLower $PromptLower -Candidate $candidate -SkillKeywordIndex $SkillKeywordIndex
        $nameScore = Get-CandidateNameMatchScore -PromptLower $PromptLower -Candidate $candidate

        $positiveScore = 0.0
        $negativeScore = 0.0
        $equivalentGroup = $null
        if ($rule) {
            $positiveScore = Get-KeywordRatio -PromptLower $PromptLower -Keywords @($rule.positive_keywords)
            $negativeScore = Get-KeywordRatio -PromptLower $PromptLower -Keywords @($rule.negative_keywords)
            if ($rule.equivalent_group) {
                $equivalentGroup = [string]$rule.equivalent_group
            }
        }

        $canonicalHit = Get-CanonicalForTaskHit -Rule $rule -TaskType $TaskType

        $score =
            ($weightKeyword * $keywordScore) +
            ($weightName * $nameScore) +
            ($positiveBonus * $positiveScore) -
            ($negativePenalty * $negativeScore) +
            ($canonicalBonus * $canonicalHit)

        $score = [Math]::Max(0.0, [Math]::Min(1.0, $score))

        $scored += [pscustomobject]@{
            skill = $candidate
            score = [Math]::Round($score, 4)
            keyword_score = [Math]::Round($keywordScore, 4)
            name_score = [Math]::Round($nameScore, 4)
            positive_score = [Math]::Round($positiveScore, 4)
            negative_score = [Math]::Round($negativeScore, 4)
            canonical_for_task_hit = [Math]::Round($canonicalHit, 4)
            equivalent_group = $equivalentGroup
            ordinal = $i
        }
    }

    $ranked = $scored | Sort-Object -Property @(
        @{ Expression = "score"; Descending = $true },
        @{ Expression = "keyword_score"; Descending = $true },
        @{ Expression = "positive_score"; Descending = $true },
        @{ Expression = "ordinal"; Descending = $false }
    )

    $top = $ranked | Select-Object -First 1
    if (-not $top) {
        $fallback = if ($defaultCandidate) { $defaultCandidate } else { $filteredCandidates[0] }
        $fallbackReason = if ($defaultCandidate) { "fallback_task_default" } else { "fallback_first_candidate" }
        return [pscustomobject]@{
            selected = $fallback
            score = 0.0
            reason = $fallbackReason
            ranking = @()
            top1_top2_gap = 0.0
            filtered_out_by_task = @($blockedByTask)
        }
    }

    $second = $ranked | Select-Object -Skip 1 -First 1
    $gap = if ($second) { [double]$top.score - [double]$second.score } else { [double]$top.score }
    $gap = [Math]::Max(0.0, [Math]::Round($gap, 4))

    if ([double]$top.score -lt $fallbackMin) {
        if ($defaultCandidate) {
            $defaultInRank = $ranked | Where-Object { $_.skill -eq $defaultCandidate } | Select-Object -First 1
            $defaultScore = if ($defaultInRank) { [double]$defaultInRank.score } else { [double]$top.score }
            return [pscustomobject]@{
                selected = $defaultCandidate
                score = $defaultScore
                reason = "fallback_task_default"
                ranking = @($ranked | Select-Object -First 3)
                top1_top2_gap = $gap
                filtered_out_by_task = @($blockedByTask)
            }
        }

        return [pscustomobject]@{
            selected = $filteredCandidates[0]
            score = [double]$top.score
            reason = "fallback_first_candidate"
            ranking = @($ranked | Select-Object -First 3)
            top1_top2_gap = $gap
            filtered_out_by_task = @($blockedByTask)
        }
    }

    return [pscustomobject]@{
        selected = [string]$top.skill
        score = [double]$top.score
        reason = "keyword_ranked"
        ranking = @($ranked | Select-Object -First 3)
        top1_top2_gap = $gap
        filtered_out_by_task = @($blockedByTask)
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "config\pack-manifest.json"))) {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
}
$configRoot = Join-Path $repoRoot "config"

$packManifestPath = Join-Path $configRoot "pack-manifest.json"
$aliasMapPath = Join-Path $configRoot "skill-alias-map.json"
$thresholdPath = Join-Path $configRoot "router-thresholds.json"
$skillKeywordIndexPath = Join-Path $configRoot "skill-keyword-index.json"
$routingRulesPath = Join-Path $configRoot "skill-routing-rules.json"
$openSpecPolicyPath = Join-Path $configRoot "openspec-policy.json"
$gsdOverlayPolicyPath = Join-Path $configRoot "gsd-overlay.json"
$promptOverlayPolicyPath = Join-Path $configRoot "prompt-overlay.json"
$memoryGovernancePolicyPath = Join-Path $configRoot "memory-governance.json"
$dataScaleOverlayPolicyPath = Join-Path $configRoot "data-scale-overlay.json"
$qualityDebtOverlayPolicyPath = Join-Path $configRoot "quality-debt-overlay.json"
$frameworkInteropOverlayPolicyPath = Join-Path $configRoot "framework-interop-overlay.json"
$mlLifecycleOverlayPolicyPath = Join-Path $configRoot "ml-lifecycle-overlay.json"
$pythonCleanCodeOverlayPolicyPath = Join-Path $configRoot "python-clean-code-overlay.json"
$systemDesignOverlayPolicyPath = Join-Path $configRoot "system-design-overlay.json"
$cudaKernelOverlayPolicyPath = Join-Path $configRoot "cuda-kernel-overlay.json"
$observabilityPolicyPath = Join-Path $configRoot "observability-policy.json"
$aiRerankPolicyPath = Join-Path $configRoot "ai-rerank-policy.json"

$packManifest = Get-Content -LiteralPath $packManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$aliasMap = Get-Content -LiteralPath $aliasMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
$thresholds = Get-Content -LiteralPath $thresholdPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillKeywordIndex = if (Test-Path -LiteralPath $skillKeywordIndexPath) {
    Get-Content -LiteralPath $skillKeywordIndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$routingRules = if (Test-Path -LiteralPath $routingRulesPath) {
    Get-Content -LiteralPath $routingRulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$openSpecPolicy = if (Test-Path -LiteralPath $openSpecPolicyPath) {
    Get-Content -LiteralPath $openSpecPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$gsdOverlayPolicy = if (Test-Path -LiteralPath $gsdOverlayPolicyPath) {
    Get-Content -LiteralPath $gsdOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$promptOverlayPolicy = if (Test-Path -LiteralPath $promptOverlayPolicyPath) {
    Get-Content -LiteralPath $promptOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$memoryGovernancePolicy = if (Test-Path -LiteralPath $memoryGovernancePolicyPath) {
    Get-Content -LiteralPath $memoryGovernancePolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$dataScaleOverlayPolicy = if (Test-Path -LiteralPath $dataScaleOverlayPolicyPath) {
    Get-Content -LiteralPath $dataScaleOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$qualityDebtOverlayPolicy = if (Test-Path -LiteralPath $qualityDebtOverlayPolicyPath) {
    Get-Content -LiteralPath $qualityDebtOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$frameworkInteropOverlayPolicy = if (Test-Path -LiteralPath $frameworkInteropOverlayPolicyPath) {
    Get-Content -LiteralPath $frameworkInteropOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$mlLifecycleOverlayPolicy = if (Test-Path -LiteralPath $mlLifecycleOverlayPolicyPath) {
    Get-Content -LiteralPath $mlLifecycleOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$pythonCleanCodeOverlayPolicy = if (Test-Path -LiteralPath $pythonCleanCodeOverlayPolicyPath) {
    Get-Content -LiteralPath $pythonCleanCodeOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$systemDesignOverlayPolicy = if (Test-Path -LiteralPath $systemDesignOverlayPolicyPath) {
    Get-Content -LiteralPath $systemDesignOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$cudaKernelOverlayPolicy = if (Test-Path -LiteralPath $cudaKernelOverlayPolicyPath) {
    Get-Content -LiteralPath $cudaKernelOverlayPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$observabilityPolicy = if (Test-Path -LiteralPath $observabilityPolicyPath) {
    try {
        Get-Content -LiteralPath $observabilityPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}
$aiRerankPolicy = if (Test-Path -LiteralPath $aiRerankPolicyPath) {
    try {
        Get-Content -LiteralPath $aiRerankPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $null
    }
} else {
    $null
}

$weights = $thresholds.weights
$rules = $thresholds.safety
$th = $thresholds.thresholds
$weightSkillSignal = if ($weights.skill_keyword_signal -ne $null) { [double]$weights.skill_keyword_signal } else { 0.25 }
$candidateSelectionConfig = if ($thresholds.candidate_selection) { $thresholds.candidate_selection } else { $null }
$minTopGap = if ($th.min_top1_top2_gap -ne $null) { [double]$th.min_top1_top2_gap } else { 0.0 }
$minCandidateSignalForConfirmOverride = if ($th.min_candidate_signal_for_confirm_override -ne $null) { [double]$th.min_candidate_signal_for_confirm_override } else { 0.0 }

$aliasResult = Resolve-Alias -Skill $RequestedSkill -AliasMap $aliasMap
$requestedCanonical = [string]$aliasResult.canonical
$promptLower = $Prompt.ToLowerInvariant()
$openSpecAdvice = Get-OpenSpecGovernanceAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -RequestedCanonical $requestedCanonical -OpenSpecPolicy $openSpecPolicy
$gsdOverlayAdvice = Get-GsdOverlayAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -GsdOverlayPolicy $gsdOverlayPolicy
$promptOverlayAdvice = Get-PromptOverlayAdvice -PromptLower $promptLower -Grade $Grade -TaskType $TaskType -PromptOverlayPolicy $promptOverlayPolicy
$memoryGovernanceAdvice = Get-MemoryGovernanceAdvice -Grade $Grade -TaskType $TaskType -MemoryGovernancePolicy $memoryGovernancePolicy

$packResults = @()
foreach ($pack in $packManifest.packs) {
    $gradeAllowed = ($pack.grade_allow -contains $Grade)
    $taskAllowed = ($pack.task_allow -contains $TaskType)

    if ($rules.enforce_grade_boundary -and -not $gradeAllowed) { continue }
    if ($rules.enforce_task_boundary -and -not $taskAllowed) { continue }

    $intent = Get-IntentScore -PromptLower $promptLower -PackId $pack.id -Candidates $pack.skill_candidates
    $trigger = Get-TriggerKeywordScore -PromptLower $promptLower -Keywords $pack.trigger_keywords
    $workspace = Get-WorkspaceSignalScore -PromptLower $promptLower -RequestedCanonical $requestedCanonical -Candidates $pack.skill_candidates
    $skillSignal = Get-PackSkillSignalScore -PromptLower $promptLower -Candidates $pack.skill_candidates -SkillKeywordIndex $skillKeywordIndex
    $prior = [double]$pack.priority / 100.0
    $conflictInverse = if ($gradeAllowed -and $taskAllowed) { 1.0 } else { 0.0 }

    $score =
        ([double]$weights.intent_match * $intent) +
        ([double]$weights.trigger_keyword_match * $trigger) +
        ([double]$weights.workspace_signal_match * $workspace) +
        ($weightSkillSignal * $skillSignal) +
        ([double]$weights.recent_success_prior * $prior) +
        ([double]$weights.conflict_penalty_inverse * $conflictInverse)

    $selection = Select-PackCandidate -PromptLower $promptLower -Candidates $pack.skill_candidates -TaskType $TaskType -RequestedCanonical $requestedCanonical -SkillKeywordIndex $skillKeywordIndex -RoutingRules $routingRules -Pack $pack -CandidateSelectionConfig $candidateSelectionConfig
    $candidateSignal = ([double]$selection.score * 0.75) + ([double]$selection.top1_top2_gap * 0.25)
    $candidateSignal = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $candidateSignal)), 4)

    $packResults += [pscustomobject]@{
        pack_id = [string]$pack.id
        score = [Math]::Round($score, 4)
        intent = [Math]::Round($intent, 4)
        trigger = [Math]::Round($trigger, 4)
        workspace = [Math]::Round($workspace, 4)
        skill_signal = [Math]::Round($skillSignal, 4)
        prior = [Math]::Round($prior, 4)
        grade_allowed = $gradeAllowed
        task_allowed = $taskAllowed
        candidates = @($pack.skill_candidates)
        selected_candidate = $selection.selected
        candidate_selection_reason = $selection.reason
        candidate_selection_score = [Math]::Round([double]$selection.score, 4)
        candidate_ranking = @($selection.ranking)
        candidate_top1_top2_gap = [Math]::Round([double]$selection.top1_top2_gap, 4)
        candidate_signal = $candidateSignal
        candidate_filtered_out_by_task = @($selection.filtered_out_by_task)
    }
}

$ranked = $packResults | Sort-Object -Property @(
    @{ Expression = "score"; Descending = $true },
    @{ Expression = "pack_id"; Descending = $false }
)
$top = $ranked | Select-Object -First 1
$confidence = if ($top) { [double]$top.score } else { 0.0 }

# Soft-migration behavior: explicit legacy/canonical skill request mapped to a pack
# is treated as a strong routing signal to avoid unnecessary legacy fallback.
if ($top -and $requestedCanonical -and ($top.candidates -contains $requestedCanonical)) {
    $confidence = [Math]::Max($confidence, ([double]$th.confirm_required + 0.05))
}

$topGap = if ($top) { [double]$top.candidate_top1_top2_gap } else { 0.0 }
$candidateSignal = if ($top) { [double]$top.candidate_signal } else { 0.0 }
$canOverrideLegacyFallback = $false
if ($top -and ($top.candidate_selection_reason -in @("keyword_ranked", "requested_skill")) -and ($candidateSignal -ge $minCandidateSignalForConfirmOverride)) {
    $canOverrideLegacyFallback = $true
}
$routeReason = ""
if (-not $top) {
    $routeMode = "legacy_fallback"
    $routeReason = "no_eligible_pack"
} elseif ($confidence -lt [double]$th.fallback_to_legacy_below) {
    if ($canOverrideLegacyFallback) {
        $routeMode = "confirm_required"
        $routeReason = "candidate_signal_override"
        $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    } else {
        $routeMode = "legacy_fallback"
        $routeReason = "confidence_below_fallback"
    }
} elseif ($topGap -lt $minTopGap) {
    $routeMode = "confirm_required"
    $routeReason = "top_candidates_too_close"
} elseif ($confidence -lt [double]$th.auto_route) {
    $routeMode = "confirm_required"
    $routeReason = "confidence_requires_confirmation"
} else {
    $routeMode = "pack_overlay"
    $routeReason = "auto_route"
}

$aiRerankAdvice = Get-AiRerankAdvice `
    -PromptText $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -RequestedCanonical $requestedCanonical `
    -Ranked $ranked `
    -TopGap $topGap `
    -Confidence $confidence `
    -AiRerankPolicy $aiRerankPolicy

$aiRerankRouteOverride = [bool]($aiRerankAdvice -and $aiRerankAdvice.route_override_applied)
$effectiveTop = $top
if ($aiRerankRouteOverride -and $aiRerankAdvice -and $aiRerankAdvice.override_target_pack) {
    $overridePackId = [string]$aiRerankAdvice.override_target_pack
    $overrideTop = $ranked | Where-Object { [string]$_.pack_id -eq $overridePackId } | Select-Object -First 1
    if ($overrideTop) {
        $effectiveTop = $overrideTop
        if ($routeMode -eq "pack_overlay") {
            $routeReason = "ai_rerank_override"
        }
    }
}

$promptOverlayRouteOverride = $false
if ($routeMode -eq "pack_overlay" -and $promptOverlayAdvice -and $promptOverlayAdvice.scope_applicable -and $promptOverlayAdvice.confirm_required) {
    $routeMode = "confirm_required"
    $routeReason = "prompt_overlay_confirm_required"
    $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
    $promptOverlayRouteOverride = $true
}

$dataScaleAdvice = Get-DataScaleOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $(if ($effectiveTop) { [string]$effectiveTop.selected_candidate } else { $null }) `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -DataScaleOverlayPolicy $dataScaleOverlayPolicy

$dataScaleRouteOverride = $false
$effectiveSelectedSkill = if ($effectiveTop) { [string]$effectiveTop.selected_candidate } else { $null }
$effectiveSelectionReason = if ($effectiveTop) { [string]$effectiveTop.candidate_selection_reason } else { $null }
$effectiveSelectionScore = if ($effectiveTop) { [double]$effectiveTop.candidate_selection_score } else { 0.0 }

if ($effectiveTop -and $dataScaleAdvice -and $dataScaleAdvice.scope_applicable -and $dataScaleAdvice.override_candidate_allowed -and $dataScaleAdvice.recommended_skill -and ($dataScaleAdvice.recommended_skill -ne $effectiveSelectedSkill)) {
    if ($dataScaleAdvice.auto_override) {
        $effectiveSelectedSkill = [string]$dataScaleAdvice.recommended_skill
        $effectiveSelectionReason = "data_scale_overlay_override"
        $effectiveSelectionScore = [Math]::Round([Math]::Max([double]$effectiveSelectionScore, [double]$dataScaleAdvice.confidence), 4)
        $dataScaleRouteOverride = $true
        if ($routeMode -eq "pack_overlay") {
            $routeReason = "data_scale_auto_override"
        }
    } elseif ($dataScaleAdvice.confirm_required -and $routeMode -eq "pack_overlay") {
        $routeMode = "confirm_required"
        $routeReason = "data_scale_confirm_required"
        $confidence = [Math]::Max($confidence, [double]$th.confirm_required)
        $dataScaleRouteOverride = $true
    }
}

$qualityDebtAdvice = Get-QualityDebtOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -QualityDebtOverlayPolicy $qualityDebtOverlayPolicy

$frameworkInteropAdvice = Get-FrameworkInteropOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -FrameworkInteropOverlayPolicy $frameworkInteropOverlayPolicy

$mlLifecycleAdvice = Get-MlLifecycleOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -MlLifecycleOverlayPolicy $mlLifecycleOverlayPolicy

$pythonCleanCodeAdvice = Get-PythonCleanCodeAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -PythonCleanCodeOverlayPolicy $pythonCleanCodeOverlayPolicy

$systemDesignAdvice = Get-SystemDesignOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -SystemDesignOverlayPolicy $systemDesignOverlayPolicy

$cudaKernelAdvice = Get-CudaKernelOverlayAdvice `
    -Prompt $Prompt `
    -PromptLower $promptLower `
    -Grade $Grade `
    -TaskType $TaskType `
    -RouteMode $routeMode `
    -SelectedPackId $(if ($effectiveTop) { [string]$effectiveTop.pack_id } else { $null }) `
    -SelectedSkill $effectiveSelectedSkill `
    -PackCandidates $(if ($effectiveTop) { @($effectiveTop.candidates) } else { @() }) `
    -CudaKernelOverlayPolicy $cudaKernelOverlayPolicy

$result = [pscustomobject]@{
    prompt = $Prompt
    grade = $Grade
    task_type = $TaskType
    route_mode = $routeMode
    route_reason = $routeReason
    confidence = [Math]::Round($confidence, 4)
    top1_top2_gap = [Math]::Round($topGap, 4)
    candidate_signal = [Math]::Round($candidateSignal, 4)
    thresholds = [pscustomobject]@{
        auto_route = [double]$th.auto_route
        confirm_required = [double]$th.confirm_required
        fallback_to_legacy_below = [double]$th.fallback_to_legacy_below
        min_top1_top2_gap = [double]$minTopGap
        min_candidate_signal_for_confirm_override = [double]$minCandidateSignalForConfirmOverride
    }
    alias = $aliasResult
    openspec_advice = $openSpecAdvice
    gsd_overlay_advice = $gsdOverlayAdvice
    prompt_overlay_advice = $promptOverlayAdvice
    memory_governance_advice = $memoryGovernanceAdvice
    prompt_overlay_route_override = $promptOverlayRouteOverride
    ai_rerank_advice = $aiRerankAdvice
    ai_rerank_route_override = $aiRerankRouteOverride
    data_scale_advice = $dataScaleAdvice
    data_scale_route_override = $dataScaleRouteOverride
    quality_debt_advice = $qualityDebtAdvice
    framework_interop_advice = $frameworkInteropAdvice
    ml_lifecycle_advice = $mlLifecycleAdvice
    python_clean_code_advice = $pythonCleanCodeAdvice
    system_design_advice = $systemDesignAdvice
    cuda_kernel_advice = $cudaKernelAdvice
    selected = if ($effectiveTop) {
        [pscustomobject]@{
            pack_id = $effectiveTop.pack_id
            skill = $effectiveSelectedSkill
            selection_reason = $effectiveSelectionReason
            selection_score = $effectiveSelectionScore
            top1_top2_gap = $effectiveTop.candidate_top1_top2_gap
            candidate_signal = $effectiveTop.candidate_signal
            filtered_out_by_task = @($effectiveTop.candidate_filtered_out_by_task)
        }
    } else {
        $null
    }
    ranked = @($ranked | Select-Object -First 3)
}

$null = Write-ObservabilityRouteEvent -PromptText $Prompt -Result $result -ObservabilityPolicy $observabilityPolicy -RepoRoot $repoRoot

$result | ConvertTo-Json -Depth 10
