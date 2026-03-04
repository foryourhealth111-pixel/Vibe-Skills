# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-ExplorationKeywordHits {
    param(
        [string]$PromptLower,
        [string[]]$Keywords,
        [int]$Limit = 8
    )

    if (-not $PromptLower -or -not $Keywords -or $Keywords.Count -eq 0) {
        return @()
    }

    $hits = @()
    foreach ($keyword in @($Keywords)) {
        if (-not $keyword) { continue }
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$keyword)) {
            $hits += [string]$keyword
        }
    }

    return @($hits | Select-Object -Unique | Select-Object -First $Limit)
}

function Get-ExplorationIntentScore {
    param(
        [string]$PromptLower,
        [object]$Profile
    )

    if (-not $Profile) {
        return [pscustomobject]@{
            id = "unknown"
            score = 0.0
            positive_score = 0.0
            negative_score = 0.0
            positive_hits = @()
            negative_hits = @()
        }
    }

    $profileId = if ($Profile.id) { [string]$Profile.id } else { "unknown" }
    $positiveKeywords = @($Profile.positive_keywords)
    $negativeKeywords = @($Profile.negative_keywords)
    $negativePenaltyWeight = if ($Profile.negative_penalty_weight -ne $null) { [double]$Profile.negative_penalty_weight } else { 0.6 }

    $positiveScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $positiveKeywords)
    $negativeScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $negativeKeywords)
    $rawScore = $positiveScore - ($negativeScore * $negativePenaltyWeight)
    $score = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $rawScore)), 4)

    return [pscustomobject]@{
        id = $profileId
        score = $score
        positive_score = [Math]::Round($positiveScore, 4)
        negative_score = [Math]::Round($negativeScore, 4)
        positive_hits = @(Get-ExplorationKeywordHits -PromptLower $PromptLower -Keywords $positiveKeywords)
        negative_hits = @(Get-ExplorationKeywordHits -PromptLower $PromptLower -Keywords $negativeKeywords)
    }
}

function Resolve-ExplorationIntentChoice {
    param(
        [string]$PromptLower,
        [object[]]$Profiles,
        [double]$MinConfidence = 0.44,
        [double]$AmbiguousGap = 0.10,
        [string]$FallbackIntent = "execute"
    )

    $rows = @()
    foreach ($profile in @($Profiles)) {
        $rows += Get-ExplorationIntentScore -PromptLower $PromptLower -Profile $profile
    }

    $ranked = @(
        $rows | Sort-Object -Property @(
            @{ Expression = "score"; Descending = $true },
            @{ Expression = "id"; Descending = $false }
        )
    )

    $top = if ($ranked.Count -gt 0) { $ranked[0] } else { $null }
    $second = if ($ranked.Count -gt 1) { $ranked[1] } else { $null }
    $topScore = if ($top) { [double]$top.score } else { 0.0 }
    $topGap = if ($second) { [double]$top.score - [double]$second.score } else { [double]$topScore }
    $topGap = [Math]::Round([Math]::Max(0.0, $topGap), 4)

    $ambiguous = ($topScore -lt $MinConfidence) -or ($topGap -lt $AmbiguousGap)
    $selectedId = if ($top) { [string]$top.id } else { [string]$FallbackIntent }
    if ($ambiguous -and $FallbackIntent) {
        $selectedId = [string]$FallbackIntent
    }

    $selectedRow = @($ranked | Where-Object { [string]$_.id -eq $selectedId } | Select-Object -First 1)
    $selectedScore = if ($selectedRow) { [double]$selectedRow.score } else { 0.0 }

    $ranking = @(
        $ranked | Select-Object -First 6 | ForEach-Object {
            [pscustomobject]@{
                id = [string]$_.id
                score = [double]$_.score
                positive_score = [double]$_.positive_score
                negative_score = [double]$_.negative_score
            }
        }
    )

    return [pscustomobject]@{
        top_id = if ($top) { [string]$top.id } else { "none" }
        top_score = [Math]::Round([double]$topScore, 4)
        top_gap = [double]$topGap
        ambiguous = [bool]$ambiguous
        selected_id = $selectedId
        selected_score = [Math]::Round([double]$selectedScore, 4)
        ranking = @($ranking)
        profile_rows = @($ranked)
    }
}

function Get-ExplorationDomainRows {
    param(
        [string]$PromptLower,
        [object[]]$Domains,
        [double]$MinDomainConfidence = 0.28,
        [int]$MaxDomains = 3
    )

    $rows = @()
    foreach ($domain in @($Domains)) {
        if (-not $domain) { continue }
        $domainId = if ($domain.id) { [string]$domain.id } else { "unknown" }
        $keywords = @($domain.keywords)
        $score = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords)
        if ($score -lt $MinDomainConfidence) { continue }

        $rows += [pscustomobject]@{
            id = $domainId
            score = [Math]::Round([double]$score, 4)
            default_pack = if ($domain.default_pack) { [string]$domain.default_pack } else { $null }
            default_skill = if ($domain.default_skill) { [string]$domain.default_skill } else { $null }
            keyword_hits = @(Get-ExplorationKeywordHits -PromptLower $PromptLower -Keywords $keywords)
        }
    }

    $ranked = @(
        $rows | Sort-Object -Property @(
            @{ Expression = "score"; Descending = $true },
            @{ Expression = "id"; Descending = $false }
        ) | Select-Object -First ([Math]::Max(1, $MaxDomains))
    )

    return @($ranked)
}

function Get-ExplorationExecutionMode {
    param(
        [string]$IntentId,
        [object]$SelectedProfile
    )

    if ($SelectedProfile -and $SelectedProfile.execution_mode) {
        return [string]$SelectedProfile.execution_mode
    }

    switch ($IntentId) {
        "explore" { return "analysis_first" }
        "hybrid" { return "analyze_then_execute" }
        default { return "direct_execution" }
    }
}

function Get-ExplorationOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$ExplorationPolicy,
        [object]$ExplorationIntentProfiles,
        [object]$ExplorationDomainMap
    )

    if (-not $ExplorationPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            route_mode_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            intent_id = "none"
            intent_confidence = 0.0
            intent_top_gap = 0.0
            intent_ambiguous = $false
            dominant_domain = "none"
            multi_domain = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $enabled = if ($ExplorationPolicy.enabled -ne $null) { [bool]$ExplorationPolicy.enabled } else { $true }
    $mode = if ($ExplorationPolicy.mode) { [string]$ExplorationPolicy.mode } else { "soft" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            route_mode_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "mode_off"
            preserve_routing_assignment = $true
            intent_id = "none"
            intent_confidence = 0.0
            intent_top_gap = 0.0
            intent_ambiguous = $false
            dominant_domain = "none"
            multi_domain = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $taskAllow = @($ExplorationPolicy.task_allow)
    $gradeAllow = @($ExplorationPolicy.grade_allow)
    $routeModeAllow = @($ExplorationPolicy.route_mode_allow)

    $taskApplicable = if ($taskAllow.Count -gt 0) { $taskAllow -contains $TaskType } else { $true }
    $gradeApplicable = if ($gradeAllow.Count -gt 0) { $gradeAllow -contains $Grade } else { $true }
    $routeModeApplicable = if ($routeModeAllow.Count -gt 0) { $routeModeAllow -contains $RouteMode } else { $true }
    $scopeApplicable = $taskApplicable -and $gradeApplicable -and $routeModeApplicable

    if (-not $scopeApplicable) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = [bool]$taskApplicable
            grade_applicable = [bool]$gradeApplicable
            route_mode_applicable = [bool]$routeModeApplicable
            scope_applicable = $false
            enforcement = "advisory"
            reason = "outside_scope"
            preserve_routing_assignment = $true
            intent_id = "none"
            intent_confidence = 0.0
            intent_top_gap = 0.0
            intent_ambiguous = $false
            dominant_domain = "none"
            multi_domain = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $profiles = if ($ExplorationIntentProfiles -and $ExplorationIntentProfiles.profiles) { @($ExplorationIntentProfiles.profiles) } else { @() }
    if ($profiles.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = [bool]$taskApplicable
            grade_applicable = [bool]$gradeApplicable
            route_mode_applicable = [bool]$routeModeApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "missing_intent_profiles"
            preserve_routing_assignment = $true
            intent_id = "none"
            intent_confidence = 0.0
            intent_top_gap = 0.0
            intent_ambiguous = $false
            dominant_domain = "none"
            multi_domain = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $intentSelection = if ($ExplorationPolicy.intent_selection) { $ExplorationPolicy.intent_selection } else { $null }
    $minIntentConfidence = if ($intentSelection -and $intentSelection.min_intent_confidence -ne $null) { [double]$intentSelection.min_intent_confidence } else { 0.44 }
    $ambiguousGap = if ($intentSelection -and $intentSelection.ambiguous_gap -ne $null) { [double]$intentSelection.ambiguous_gap } else { 0.10 }
    $fallbackIntent = if ($intentSelection -and $intentSelection.fallback_intent) { [string]$intentSelection.fallback_intent } else { "execute" }

    $intentChoice = Resolve-ExplorationIntentChoice `
        -PromptLower $PromptLower `
        -Profiles $profiles `
        -MinConfidence $minIntentConfidence `
        -AmbiguousGap $ambiguousGap `
        -FallbackIntent $fallbackIntent

    $selectedIntentId = if ($intentChoice.selected_id) { [string]$intentChoice.selected_id } else { $fallbackIntent }
    $selectedIntentProfile = @($profiles | Where-Object { [string]$_.id -eq $selectedIntentId } | Select-Object -First 1)
    if (-not $selectedIntentProfile) {
        $selectedIntentProfile = @($profiles | Where-Object { [string]$_.id -eq [string]$intentChoice.top_id } | Select-Object -First 1)
    }

    $domainDetection = if ($ExplorationPolicy.domain_detection) { $ExplorationPolicy.domain_detection } else { $null }
    $minDomainConfidence = if ($domainDetection -and $domainDetection.min_domain_confidence -ne $null) { [double]$domainDetection.min_domain_confidence } else { 0.28 }
    $multiDomainGap = if ($domainDetection -and $domainDetection.multi_domain_gap -ne $null) { [double]$domainDetection.multi_domain_gap } else { 0.09 }
    $maxDomains = if ($domainDetection -and $domainDetection.max_domains -ne $null) { [int]$domainDetection.max_domains } else { 3 }

    $domains = if ($ExplorationDomainMap -and $ExplorationDomainMap.domains) { @($ExplorationDomainMap.domains) } else { @() }
    $domainRows = @(Get-ExplorationDomainRows -PromptLower $PromptLower -Domains $domains -MinDomainConfidence $minDomainConfidence -MaxDomains $maxDomains)

    $dominantDomain = if ($domainRows.Count -gt 0) { [string]$domainRows[0].id } else { "none" }
    $dominantDomainScore = if ($domainRows.Count -gt 0) { [double]$domainRows[0].score } else { 0.0 }
    $multiDomain = $false
    if ($domainRows.Count -ge 2) {
        $domainGap = [double]$domainRows[0].score - [double]$domainRows[1].score
        if ($domainGap -lt $multiDomainGap) {
            $multiDomain = $true
        }
    }

    $executionMode = Get-ExplorationExecutionMode -IntentId $selectedIntentId -SelectedProfile $selectedIntentProfile

    $maxHypothesesByMode = if ($intentSelection -and $intentSelection.max_hypotheses_by_mode) { $intentSelection.max_hypotheses_by_mode } else { $null }
    $hypothesisBudget = 3
    if ($maxHypothesesByMode) {
        $modeKeys = @($maxHypothesesByMode.PSObject.Properties.Name)
        if ($modeKeys -contains $mode) {
            $hypothesisBudget = [int]$maxHypothesesByMode.$mode
        }
    }

    $outputContract = if ($ExplorationPolicy.output_contract) { $ExplorationPolicy.output_contract } else { $null }
    $outputSections = if ($outputContract -and $outputContract.sections) {
        @($outputContract.sections)
    } else {
        @("phenomenon", "mechanism", "meaning", "next_steps")
    }

    $interview = if ($ExplorationPolicy.interview) { $ExplorationPolicy.interview } else { $null }
    $softConfirmOnAmbiguous = if ($interview -and $interview.soft_confirm_on_ambiguous_intent -ne $null) { [bool]$interview.soft_confirm_on_ambiguous_intent } else { $true }
    $softConfirmOnMultidomain = if ($interview -and $interview.soft_confirm_on_multidomain -ne $null) { [bool]$interview.soft_confirm_on_multidomain } else { $true }
    $strictConfirmOnAmbiguous = if ($interview -and $interview.strict_confirm_on_ambiguous_intent -ne $null) { [bool]$interview.strict_confirm_on_ambiguous_intent } else { $true }
    $strictConfirmOnMultidomain = if ($interview -and $interview.strict_confirm_on_multidomain -ne $null) { [bool]$interview.strict_confirm_on_multidomain } else { $true }

    $intentAmbiguous = [bool]$intentChoice.ambiguous
    $confirmRecommended = $false
    $confirmRequired = $false
    $enforcement = "advisory"
    $reason = "soft_advisory"

    if ($mode -eq "shadow") {
        $reason = "shadow_observe_only"
    } elseif ($mode -eq "strict") {
        $reason = "strict_advisory"
        if ($intentAmbiguous -and $strictConfirmOnAmbiguous) {
            $confirmRequired = $true
            $enforcement = "confirm_required"
            $reason = "strict_confirm_required_ambiguous_intent"
        } elseif ($multiDomain -and $strictConfirmOnMultidomain) {
            $confirmRequired = $true
            $enforcement = "confirm_required"
            $reason = "strict_confirm_required_multidomain"
        }
    } else {
        if ($intentAmbiguous -and $softConfirmOnAmbiguous) {
            $confirmRecommended = $true
            $reason = "soft_confirm_recommended_ambiguous_intent"
        } elseif ($multiDomain -and $softConfirmOnMultidomain) {
            $confirmRecommended = $true
            $reason = "soft_confirm_recommended_multidomain"
        }
    }

    $preserveRoutingAssignment = if ($ExplorationPolicy.preserve_routing_assignment -ne $null) { [bool]$ExplorationPolicy.preserve_routing_assignment } else { $true }

    $recommendedSkill = $null
    if ($domainRows.Count -gt 0 -and $domainRows[0].default_skill) {
        $candidateSkill = [string]$domainRows[0].default_skill
        if ($PackCandidates -and $PackCandidates.Count -gt 0) {
            if ($PackCandidates -contains $candidateSkill) {
                $recommendedSkill = $candidateSkill
            }
        } else {
            $recommendedSkill = $candidateSkill
        }
    }

    $overallConfidence = [double]([Math]::Min(1.0, [Math]::Max(0.0, (([double]$intentChoice.selected_score * 0.7) + ($dominantDomainScore * 0.3)))) )
    $overallConfidence = [Math]::Round($overallConfidence, 4)

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = [bool]$taskApplicable
        grade_applicable = [bool]$gradeApplicable
        route_mode_applicable = [bool]$routeModeApplicable
        scope_applicable = $true
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = [bool]$preserveRoutingAssignment
        intent_id = $selectedIntentId
        intent_confidence = [Math]::Round([double]$intentChoice.selected_score, 4)
        intent_top_gap = [Math]::Round([double]$intentChoice.top_gap, 4)
        intent_ambiguous = [bool]$intentAmbiguous
        intent_ranking = @($intentChoice.ranking)
        domain_hits = @($domainRows)
        dominant_domain = $dominantDomain
        multi_domain = [bool]$multiDomain
        recommended_execution_mode = $executionMode
        hypothesis_budget = [int]$hypothesisBudget
        recommended_output_sections = @($outputSections)
        include_action_plan = if ($outputContract -and $outputContract.include_action_plan -ne $null) { [bool]$outputContract.include_action_plan } else { $true }
        include_validation_plan = if ($outputContract -and $outputContract.include_validation_plan -ne $null) { [bool]$outputContract.include_validation_plan } else { $true }
        confirm_recommended = [bool]$confirmRecommended
        confirm_required = [bool]$confirmRequired
        auto_override = $false
        override_candidate_allowed = $false
        route_override_applied = $false
        recommended_skill = $recommendedSkill
        confidence = [double]$overallConfidence
    }
}
