# Auto-extracted router module. Keep function bodies behavior-identical.

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


