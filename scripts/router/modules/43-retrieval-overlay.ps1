# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-RetrievalProfileKeywordHits {
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

function Get-RetrievalProfileScore {
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
    $negativePenaltyWeight = if ($Profile.negative_penalty_weight -ne $null) { [double]$Profile.negative_penalty_weight } else { 0.65 }

    $positiveScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $positiveKeywords)
    $negativeScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $negativeKeywords)
    $rawScore = $positiveScore - ($negativeScore * $negativePenaltyWeight)
    $score = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $rawScore)), 4)

    return [pscustomobject]@{
        id = $profileId
        score = $score
        positive_score = [Math]::Round($positiveScore, 4)
        negative_score = [Math]::Round($negativeScore, 4)
        positive_hits = @(Get-RetrievalProfileKeywordHits -PromptLower $PromptLower -Keywords $positiveKeywords)
        negative_hits = @(Get-RetrievalProfileKeywordHits -PromptLower $PromptLower -Keywords $negativeKeywords)
    }
}

function Resolve-RetrievalProfileChoice {
    param(
        [string]$PromptLower,
        [object[]]$Profiles,
        [double]$MinConfidence = 0.42,
        [double]$AmbiguousGap = 0.08,
        [string]$FallbackProfileId = "composite"
    )

    $rows = @()
    foreach ($profile in @($Profiles)) {
        $rows += Get-RetrievalProfileScore -PromptLower $PromptLower -Profile $profile
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
    $selectedId = if ($top) { [string]$top.id } else { [string]$FallbackProfileId }
    if ($ambiguous -and $FallbackProfileId) {
        $selectedId = [string]$FallbackProfileId
    }

    $selectedProfile = @($Profiles | Where-Object { [string]$_.id -eq $selectedId } | Select-Object -First 1)
    if (-not $selectedProfile -and $top) {
        $selectedProfile = @($Profiles | Where-Object { [string]$_.id -eq [string]$top.id } | Select-Object -First 1)
    }

    $selectedScore = 0.0
    if ($selectedProfile) {
        $selectedRow = @($ranked | Where-Object { [string]$_.id -eq [string]$selectedProfile.id } | Select-Object -First 1)
        if ($selectedRow) {
            $selectedScore = [double]$selectedRow.score
        }
    }

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
        selected_id = if ($selectedProfile) { [string]$selectedProfile.id } else { "none" }
        selected_score = [Math]::Round([double]$selectedScore, 4)
        ranking = @($ranking)
        profile_rows = @($ranked)
    }
}

function Get-RetrievalSourcePlan {
    param(
        [object]$Profile,
        [object]$SourceRegistry
    )

    $preferredSourceIds = @()
    if ($Profile -and $Profile.default_sources) {
        $preferredSourceIds = @($Profile.default_sources)
    }

    $registryRows = @()
    if ($SourceRegistry -and $SourceRegistry.sources) {
        $registryRows = @($SourceRegistry.sources)
    }

    $sources = @()
    foreach ($sourceId in @($preferredSourceIds)) {
        $match = @($registryRows | Where-Object { [string]$_.id -eq [string]$sourceId } | Select-Object -First 1)
        if ($match) {
            $sources += [pscustomobject]@{
                id = [string]$match.id
                type = if ($match.type) { [string]$match.type } else { "general" }
                provider = if ($match.provider) { [string]$match.provider } else { "unknown" }
                quality_weight = if ($match.quality_weight -ne $null) { [double]$match.quality_weight } else { 0.5 }
                latency_tier = if ($match.latency_tier) { [string]$match.latency_tier } else { "unknown" }
            }
        }
    }

    if ($sources.Count -eq 0 -and $registryRows.Count -gt 0) {
        foreach ($fallback in @($registryRows | Select-Object -First 3)) {
            $sources += [pscustomobject]@{
                id = [string]$fallback.id
                type = if ($fallback.type) { [string]$fallback.type } else { "general" }
                provider = if ($fallback.provider) { [string]$fallback.provider } else { "unknown" }
                quality_weight = if ($fallback.quality_weight -ne $null) { [double]$fallback.quality_weight } else { 0.5 }
                latency_tier = if ($fallback.latency_tier) { [string]$fallback.latency_tier } else { "unknown" }
            }
        }
    }

    return [pscustomobject]@{
        preferred_source_ids = @($preferredSourceIds)
        sources = @($sources)
        source_count = [int]$sources.Count
    }
}

function Get-RetrievalRerankPlan {
    param(
        [object]$Profile,
        [object]$RerankWeights
    )

    $profileRerankMode = if ($Profile -and $Profile.rerank_mode) { [string]$Profile.rerank_mode } else { "balanced" }
    $fallbackMode = if ($RerankWeights -and $RerankWeights.fallback_mode) { [string]$RerankWeights.fallback_mode } else { "balanced" }
    $modes = if ($RerankWeights -and $RerankWeights.modes) { $RerankWeights.modes } else { $null }
    $availableModeKeys = if ($modes) { Get-ArraySafe -Value $modes.PSObject.Properties.Name } else { Get-ArraySafe -Value $null }

    $selectedMode = if ($availableModeKeys -contains $profileRerankMode) { $profileRerankMode } else { $fallbackMode }
    if (-not ($availableModeKeys -contains $selectedMode)) {
        $selectedMode = if ($availableModeKeys.Count -gt 0) { [string]$availableModeKeys[0] } else { "balanced" }
    }

    $weights = if ($modes -and ($availableModeKeys -contains $selectedMode)) { $modes.$selectedMode } else { $null }
    $semanticWeight = if ($weights -and $weights.semantic -ne $null) { [double]$weights.semantic } else { 0.45 }
    $keywordWeight = if ($weights -and $weights.keyword -ne $null) { [double]$weights.keyword } else { 0.35 }
    $authorityWeight = if ($weights -and $weights.authority -ne $null) { [double]$weights.authority } else { 0.20 }

    return [pscustomobject]@{
        mode = $selectedMode
        hybrid_enabled = $true
        weights = [pscustomobject]@{
            semantic = [Math]::Round($semanticWeight, 4)
            keyword = [Math]::Round($keywordWeight, 4)
            authority = [Math]::Round($authorityWeight, 4)
        }
    }
}

function Get-RetrievalOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$RetrievalPolicy,
        [object]$RetrievalIntentProfiles,
        [object]$RetrievalSourceRegistry,
        [object]$RetrievalRerankWeights
    )

    if (-not $RetrievalPolicy) {
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
            profile_id = "none"
            profile_confidence = 0.0
            profile_top_gap = 0.0
            profile_ambiguous = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $enabled = if ($RetrievalPolicy.enabled -ne $null) { [bool]$RetrievalPolicy.enabled } else { $true }
    $mode = if ($RetrievalPolicy.mode) { [string]$RetrievalPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            route_mode_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            profile_id = "none"
            profile_confidence = 0.0
            profile_top_gap = 0.0
            profile_ambiguous = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $taskAllow = @($RetrievalPolicy.task_allow)
    $gradeAllow = @($RetrievalPolicy.grade_allow)
    $routeModeAllow = @($RetrievalPolicy.route_mode_allow)

    $taskApplicable = if ($taskAllow.Count -gt 0) { $taskAllow -contains $TaskType } else { $true }
    $gradeApplicable = if ($gradeAllow.Count -gt 0) { $gradeAllow -contains $Grade } else { $true }
    $routeModeApplicable = if ($routeModeAllow.Count -gt 0) { $routeModeAllow -contains $RouteMode } else { $true }
    $scopeApplicable = $taskApplicable -and $gradeApplicable -and $routeModeApplicable

    if (-not $scopeApplicable) {
        $scopeReason = if (-not $taskApplicable) {
            "task_out_of_scope"
        } elseif (-not $gradeApplicable) {
            "grade_out_of_scope"
        } else {
            "route_mode_out_of_scope"
        }

        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = [bool]$taskApplicable
            grade_applicable = [bool]$gradeApplicable
            route_mode_applicable = [bool]$routeModeApplicable
            scope_applicable = $false
            enforcement = "none"
            reason = $scopeReason
            preserve_routing_assignment = $true
            profile_id = "none"
            profile_confidence = 0.0
            profile_top_gap = 0.0
            profile_ambiguous = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $profiles = if ($RetrievalIntentProfiles -and $RetrievalIntentProfiles.profiles) { Get-ArraySafe -Value $RetrievalIntentProfiles.profiles } else { Get-ArraySafe -Value $null }
    if ($profiles.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = [bool]$taskApplicable
            grade_applicable = [bool]$gradeApplicable
            route_mode_applicable = [bool]$routeModeApplicable
            scope_applicable = $false
            enforcement = "none"
            reason = "profiles_missing"
            preserve_routing_assignment = $true
            profile_id = "none"
            profile_confidence = 0.0
            profile_top_gap = 0.0
            profile_ambiguous = $false
            confirm_recommended = $false
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
            route_override_applied = $false
            recommended_skill = $null
            confidence = 0.0
        }
    }

    $profileSelection = if ($RetrievalPolicy.profile_selection) { $RetrievalPolicy.profile_selection } else { $null }
    $minProfileConfidence = if ($profileSelection -and $profileSelection.min_profile_confidence -ne $null) { [double]$profileSelection.min_profile_confidence } else { 0.42 }
    $ambiguousGap = if ($profileSelection -and $profileSelection.ambiguous_gap -ne $null) { [double]$profileSelection.ambiguous_gap } else { 0.08 }
    $fallbackProfileId = if ($profileSelection -and $profileSelection.fallback_profile) { [string]$profileSelection.fallback_profile } else { "composite" }

    $profileChoice = Resolve-RetrievalProfileChoice `
        -PromptLower $PromptLower `
        -Profiles $profiles `
        -MinConfidence $minProfileConfidence `
        -AmbiguousGap $ambiguousGap `
        -FallbackProfileId $fallbackProfileId

    $selectedProfile = @($profiles | Where-Object { [string]$_.id -eq [string]$profileChoice.selected_id } | Select-Object -First 1)
    if (-not $selectedProfile) {
        $selectedProfile = @($profiles | Select-Object -First 1)
    }

    $profileRows = @($profileChoice.profile_rows)
    $selectedProfileRow = @($profileRows | Where-Object { [string]$_.id -eq [string]$selectedProfile.id } | Select-Object -First 1)
    $selectedPositiveHits = if ($selectedProfileRow -and $selectedProfileRow.PSObject.Properties.Name -contains 'positive_hits') { Get-ArraySafe -Value $selectedProfileRow.positive_hits } else { Get-ArraySafe -Value $null }
    $selectedNegativeHits = if ($selectedProfileRow -and $selectedProfileRow.PSObject.Properties.Name -contains 'negative_hits') { Get-ArraySafe -Value $selectedProfileRow.negative_hits } else { Get-ArraySafe -Value $null }

    $modeBudget = 3
    if ($profileSelection -and $profileSelection.max_query_variants_by_mode) {
        $budgetTable = $profileSelection.max_query_variants_by_mode
        $budgetKeys = @($budgetTable.PSObject.Properties.Name)
        if ($budgetKeys -contains $mode) {
            $modeBudget = [int]$budgetTable.$mode
        }
    }
    if ($modeBudget -le 0) { $modeBudget = 3 }

    $profileBudget = if ($selectedProfile.max_query_variants -ne $null) { [int]$selectedProfile.max_query_variants } else { $modeBudget }
    if ($profileBudget -le 0) { $profileBudget = $modeBudget }
    $maxQueryVariants = [Math]::Max(1, [Math]::Min($modeBudget, $profileBudget))

    $queryTemplates = @($selectedProfile.query_templates)
    $selectedTemplates = if ($queryTemplates.Count -gt 0) {
        @($queryTemplates | Select-Object -First $maxQueryVariants)
    } else {
        @("Use profile-guided query decomposition with focused keywords")
    }
    $expansionTerms = @($selectedProfile.query_expansion_terms | Select-Object -First 8)

    $sourcePlan = Get-RetrievalSourcePlan -Profile $selectedProfile -SourceRegistry $RetrievalSourceRegistry
    $rerankPlan = Get-RetrievalRerankPlan -Profile $selectedProfile -RerankWeights $RetrievalRerankWeights

    $coverage = if ($RetrievalPolicy.coverage) { $RetrievalPolicy.coverage } else { $null }
    $minSourcesHit = if ($coverage -and $coverage.min_sources_hit -ne $null) { [int]$coverage.min_sources_hit } else { 1 }
    $minEvidenceItems = if ($coverage -and $coverage.min_evidence_items -ne $null) { [int]$coverage.min_evidence_items } else { 3 }
    $maxRetrieveRounds = if ($coverage -and $coverage.max_retrieve_rounds -ne $null) { [int]$coverage.max_retrieve_rounds } else { 2 }
    $requeryOnLowCoverage = if ($coverage -and $coverage.requery_on_low_coverage -ne $null) { [bool]$coverage.requery_on_low_coverage } else { $true }

    $predictedSourceHits = [int]$sourcePlan.source_count
    $predictedEvidenceItems = [int]($maxQueryVariants * [Math]::Max(1, $predictedSourceHits))
    $sourceCoverage = if ($minSourcesHit -gt 0) {
        [Math]::Min(1.0, ([double]$predictedSourceHits / [double]$minSourcesHit))
    } else {
        1.0
    }
    $evidenceCoverage = if ($minEvidenceItems -gt 0) {
        [Math]::Min(1.0, ([double]$predictedEvidenceItems / [double]$minEvidenceItems))
    } else {
        1.0
    }
    $coverageScore = [Math]::Round(([double]$sourceCoverage * 0.55) + ([double]$evidenceCoverage * 0.45), 4)
    $lowCoverage = ($coverageScore -lt 0.65)
    $needsRequery = [bool]($requeryOnLowCoverage -and ($lowCoverage -or [bool]$profileChoice.ambiguous))

    $candidatePool = @()
    if ($SelectedSkill) { $candidatePool += [string]$SelectedSkill }
    if ($PackCandidates) { $candidatePool += @($PackCandidates | ForEach-Object { [string]$_ }) }
    $candidatePool = @($candidatePool | Where-Object { $_ } | Select-Object -Unique)

    $recommendedSkill = $null
    $profileRecommendedSkills = @($selectedProfile.recommended_skills)
    if ($profileRecommendedSkills.Count -gt 0 -and $candidatePool.Count -gt 0) {
        foreach ($skill in @($profileRecommendedSkills)) {
            if ($candidatePool -contains [string]$skill) {
                $recommendedSkill = [string]$skill
                break
            }
        }
    }
    if (-not $recommendedSkill -and $profileRecommendedSkills.Count -gt 0) {
        $recommendedSkill = [string]$profileRecommendedSkills[0]
    }
    if (-not $recommendedSkill -and $SelectedSkill) {
        $recommendedSkill = [string]$SelectedSkill
    }

    $recommendedPacks = @($selectedProfile.recommended_packs)
    $selectedPackInProfile = if ($SelectedPackId -and $recommendedPacks.Count -gt 0) {
        ($recommendedPacks -contains [string]$SelectedPackId)
    } else {
        $true
    }

    $enforcementPolicy = if ($RetrievalPolicy.enforcement) { $RetrievalPolicy.enforcement } else { $null }
    $strictConfirmOnLowCoverage = if ($enforcementPolicy -and $enforcementPolicy.strict_confirm_on_low_coverage -ne $null) { [bool]$enforcementPolicy.strict_confirm_on_low_coverage } else { $true }
    $strictConfirmOnAmbiguousProfile = if ($enforcementPolicy -and $enforcementPolicy.strict_confirm_on_ambiguous_profile -ne $null) { [bool]$enforcementPolicy.strict_confirm_on_ambiguous_profile } else { $true }

    $confirmRecommended = [bool]($profileChoice.ambiguous -or $needsRequery -or (-not $selectedPackInProfile))
    $confirmRequired = $false
    $enforcement = "advisory"
    $reason = "retrieval_scope_match"

    switch ($mode) {
        "shadow" {
            $enforcement = "advisory"
            $reason = if ($confirmRecommended) { "shadow_retrieval_confirm_recommended" } else { "shadow_retrieval_advisory" }
        }
        "soft" {
            $enforcement = "advisory"
            $reason = if ($confirmRecommended) { "soft_retrieval_confirm_recommended" } else { "soft_retrieval_advisory" }
        }
        "strict" {
            $mustConfirm = ($strictConfirmOnLowCoverage -and $needsRequery) -or ($strictConfirmOnAmbiguousProfile -and [bool]$profileChoice.ambiguous)
            if ($mustConfirm) {
                $confirmRequired = $true
                $enforcement = "confirm_required"
                $reason = "strict_retrieval_confirm_required"
            } else {
                $enforcement = "advisory"
                $reason = "strict_retrieval_advisory"
            }
        }
        default {
            $enforcement = "advisory"
            $reason = "retrieval_scope_match"
        }
    }

    $profileConfidence = [double]$profileChoice.selected_score
    $confidence = [Math]::Round((($profileConfidence * 0.6) + ($coverageScore * 0.4)), 4)
    $preserveRoutingAssignment = if ($RetrievalPolicy.preserve_routing_assignment -ne $null) { [bool]$RetrievalPolicy.preserve_routing_assignment } else { $true }

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
        profile_id = if ($selectedProfile) { [string]$selectedProfile.id } else { "none" }
        profile_confidence = [Math]::Round($profileConfidence, 4)
        profile_top_gap = [double]$profileChoice.top_gap
        profile_ambiguous = [bool]$profileChoice.ambiguous
        profile_min_confidence = [Math]::Round([double]$minProfileConfidence, 4)
        profile_ranking = @($profileChoice.ranking)
        profile_matched_positive_keywords = @($selectedPositiveHits)
        profile_matched_negative_keywords = @($selectedNegativeHits)
        query_plan = [pscustomobject]@{
            max_query_variants = [int]$maxQueryVariants
            decomposition_strategy = if ($selectedProfile -and $selectedProfile.decomposition_strategy) { [string]$selectedProfile.decomposition_strategy } else { "single_query" }
            templates_selected = @($selectedTemplates)
            query_expansion_terms = @($expansionTerms)
        }
        source_plan = [pscustomobject]@{
            preferred_source_ids = @($sourcePlan.preferred_source_ids)
            sources = @($sourcePlan.sources)
            source_count = [int]$sourcePlan.source_count
        }
        rerank_plan = $rerankPlan
        coverage_gate = [pscustomobject]@{
            min_sources_hit = [int]$minSourcesHit
            min_evidence_items = [int]$minEvidenceItems
            max_retrieve_rounds = [int]$maxRetrieveRounds
            predicted_source_hits = [int]$predictedSourceHits
            predicted_evidence_items = [int]$predictedEvidenceItems
            coverage_score = [double]$coverageScore
            needs_requery = [bool]$needsRequery
        }
        coverage_score = [double]$coverageScore
        needs_requery = [bool]$needsRequery
        recommended_packs = @($recommendedPacks)
        selected_pack_in_profile = [bool]$selectedPackInProfile
        recommended_skill = $recommendedSkill
        confirm_recommended = [bool]$confirmRecommended
        confirm_required = [bool]$confirmRequired
        auto_override = $false
        override_candidate_allowed = $false
        route_override_applied = $false
        confidence = [double]$confidence
    }
}
