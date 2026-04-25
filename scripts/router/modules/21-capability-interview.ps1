# Auto-extracted router module. Keep function bodies behavior-identical.

function Test-DeepDiscoveryScope {
    param(
        [object]$DeepDiscoveryPolicy,
        [string]$Grade,
        [string]$TaskType
    )

    if (-not $DeepDiscoveryPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            scope_applicable = $false
            reasons = @("policy_missing")
            preserve_routing_assignment = $true
        }
    }

    $enabled = if ($DeepDiscoveryPolicy.enabled -ne $null) { [bool]$DeepDiscoveryPolicy.enabled } else { $true }
    $mode = if ($DeepDiscoveryPolicy.mode) { [string]$DeepDiscoveryPolicy.mode } else { "shadow" }
    $preserveRoutingAssignment = if ($DeepDiscoveryPolicy.preserve_routing_assignment -ne $null) { [bool]$DeepDiscoveryPolicy.preserve_routing_assignment } else { $true }

    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            scope_applicable = $false
            reasons = @("policy_off")
            preserve_routing_assignment = $preserveRoutingAssignment
        }
    }

    $scope = if ($DeepDiscoveryPolicy.scope) { $DeepDiscoveryPolicy.scope } else { $null }
    $gradeAllow = if ($scope -and $scope.grade_allow) { @($scope.grade_allow) } else { @("M", "L", "XL") }
    $taskAllow = if ($scope -and $scope.task_allow) { @($scope.task_allow) } else { @("planning", "coding", "review", "debug", "research") }

    $reasons = @()
    if (-not ($gradeAllow -contains $Grade)) { $reasons += "grade_not_allowed" }
    if (-not ($taskAllow -contains $TaskType)) { $reasons += "task_not_allowed" }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        scope_applicable = ($reasons.Count -eq 0)
        reasons = if ($reasons.Count -eq 0) { @("scope_match") } else { @($reasons) }
        preserve_routing_assignment = $preserveRoutingAssignment
    }
}

function Get-DeepDiscoveryCapabilityHits {
    param(
        [string]$PromptLower,
        [object]$CapabilityCatalog,
        [string]$TaskType,
        [int]$MaxHits = 8
    )

    if (-not $CapabilityCatalog -or -not $CapabilityCatalog.capabilities) { return @() }

    $hits = @()
    foreach ($capability in @($CapabilityCatalog.capabilities)) {
        $capabilityId = if ($capability.id) { [string]$capability.id } else { "" }
        if (-not $capabilityId) { continue }

        $taskAllow = @($capability.task_allow)
        if ($taskAllow.Count -gt 0 -and -not ($taskAllow -contains $TaskType)) { continue }

        $keywords = @($capability.keywords)
        if ($keywords.Count -eq 0) { continue }

        $score = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords)
        if ($score -le 0) { continue }

        $matchedKeywords = @()
        foreach ($keyword in $keywords) {
            $keywordText = [string]$keyword
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword $keywordText) {
                $matchedKeywords += $keywordText
            }
        }

        $hits += [pscustomobject]@{
            capability_id = $capabilityId
            display_name = if ($capability.display_name) { [string]$capability.display_name } else { $capabilityId }
            score = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $score)), 4)
            matched_keyword_count = $matchedKeywords.Count
            matched_keywords = @($matchedKeywords)
            skills = @($capability.skills)
        }
    }

    return @(
        $hits |
            Sort-Object -Property @(
                @{ Expression = "score"; Descending = $true },
                @{ Expression = "matched_keyword_count"; Descending = $true },
                @{ Expression = "capability_id"; Descending = $false }
            ) |
            Select-Object -First $MaxHits
    )
}

function Get-DeepDiscoveryTrigger {
    param(
        [string]$PromptLower,
        [object[]]$CapabilityHits,
        [object]$DeepDiscoveryPolicy
    )

    $triggerPolicy = if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.trigger) { $DeepDiscoveryPolicy.trigger } else { $null }
    $minTriggerScore = if ($triggerPolicy -and $triggerPolicy.min_trigger_score -ne $null) { [double]$triggerPolicy.min_trigger_score } else { 0.2 }
    $minCapabilityHits = if ($triggerPolicy -and $triggerPolicy.min_capability_hits -ne $null) { [int]$triggerPolicy.min_capability_hits } else { 1 }

    $ambiguityKeywords = if ($triggerPolicy -and $triggerPolicy.ambiguity_keywords) { Get-ArraySafe -Value $triggerPolicy.ambiguity_keywords } else { Get-ArraySafe -Value $null }
    $compositeKeywords = if ($triggerPolicy -and $triggerPolicy.composite_keywords) { Get-ArraySafe -Value $triggerPolicy.composite_keywords } else { Get-ArraySafe -Value $null }
    $executionKeywords = if ($triggerPolicy -and $triggerPolicy.execution_keywords) { Get-ArraySafe -Value $triggerPolicy.execution_keywords } else { Get-ArraySafe -Value $null }

    $ambiguityScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $ambiguityKeywords)
    $compositeScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $compositeKeywords)
    $executionScore = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $executionKeywords)
    $capabilityHitCount = if ($CapabilityHits) { @($CapabilityHits).Count } else { 0 }
    $capabilityScore = [Math]::Min(1.0, ([double]$capabilityHitCount / 3.0))

    $triggerScore =
        (0.25 * $ambiguityScore) +
        (0.45 * $compositeScore) +
        (0.20 * $executionScore) +
        (0.10 * $capabilityScore)
    $triggerScore = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $triggerScore)), 4)

    $reasons = @()
    if ($ambiguityScore -gt 0) { $reasons += "ambiguity_signal" }
    if ($compositeScore -gt 0) { $reasons += "composite_signal" }
    if ($executionScore -gt 0) { $reasons += "execution_signal" }
    if ($capabilityHitCount -ge $minCapabilityHits) { $reasons += "capability_hits" }

    $activeByScore = ($triggerScore -ge $minTriggerScore) -and ($capabilityHitCount -ge $minCapabilityHits)
    $activeByComposite = ($compositeScore -ge 0.2) -and ($capabilityHitCount -ge 1)
    $active = $activeByScore -or $activeByComposite

    if (-not $active) {
        $reasons += "below_activation_threshold"
    }

    return [pscustomobject]@{
        active = [bool]$active
        trigger_score = [double]$triggerScore
        ambiguity_score = [Math]::Round($ambiguityScore, 4)
        composite_score = [Math]::Round($compositeScore, 4)
        execution_score = [Math]::Round($executionScore, 4)
        capability_score = [Math]::Round($capabilityScore, 4)
        capability_hit_count = [int]$capabilityHitCount
        min_trigger_score = [double]$minTriggerScore
        min_capability_hits = [int]$minCapabilityHits
        reasons = @($reasons | Select-Object -Unique)
    }
}

function Get-DeepDiscoveryInterviewAdvice {
    param(
        [string]$PromptText,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [object]$DeepDiscoveryPolicy,
        [object]$CapabilityCatalog
    )

    $scope = Test-DeepDiscoveryScope -DeepDiscoveryPolicy $DeepDiscoveryPolicy -Grade $Grade -TaskType $TaskType
    $capabilityHits = Get-DeepDiscoveryCapabilityHits -PromptLower $PromptLower -CapabilityCatalog $CapabilityCatalog -TaskType $TaskType
    $trigger = Get-DeepDiscoveryTrigger -PromptLower $PromptLower -CapabilityHits $capabilityHits -DeepDiscoveryPolicy $DeepDiscoveryPolicy

    $mode = if ($scope.mode) { [string]$scope.mode } else { "off" }
    $maxQuestions = 3
    $questionTemplates = @()
    if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.interview) {
        if ($DeepDiscoveryPolicy.interview.max_questions -ne $null) {
            $maxQuestions = [Math]::Max(1, [int]$DeepDiscoveryPolicy.interview.max_questions)
        }
        if ($DeepDiscoveryPolicy.interview.question_templates) {
            $questionTemplates = @($DeepDiscoveryPolicy.interview.question_templates)
        }
    }
    if ($questionTemplates.Count -eq 0) {
        $questionTemplates = @(
            "What final deliverable shape do you want for this task (script, report, document, page, or runnable workflow)?",
            "What are the top two capability areas you want me to prioritize: {capabilities}?",
            "Do you want me to confirm the plan first, or execute directly from the current description?"
        )
    }

    $capabilityNames = @($capabilityHits | ForEach-Object { [string]$_.display_name })
    $capabilityNameText = if ($capabilityNames.Count -gt 0) { ($capabilityNames -join " / ") } else { "Requirement clarification and planning / Implementation and execution" }

    $questions = @()
    foreach ($template in $questionTemplates) {
        if ($questions.Count -ge $maxQuestions) { break }
        $question = ([string]$template).Replace("{capabilities}", $capabilityNameText)
        if ($question) { $questions += $question }
    }

    if ($questions.Count -lt $maxQuestions -and $CapabilityCatalog -and $CapabilityCatalog.default_interview_questions) {
        foreach ($item in @($CapabilityCatalog.default_interview_questions)) {
            if ($questions.Count -ge $maxQuestions) { break }
            $question = if ($item.prompt) { [string]$item.prompt } else { "" }
            if ($question -and -not ($questions -contains $question)) {
                $questions += $question
            }
        }
    }

    $recommendedCapabilities = @($capabilityHits | ForEach-Object { [string]$_.capability_id } | Select-Object -Unique)
    $recommendedSkills = @($capabilityHits | ForEach-Object { @($_.skills) } | Where-Object { $_ } | Select-Object -Unique)

    $scopeApplicable = [bool]$scope.scope_applicable
    $interviewRequired = $scopeApplicable -and ([bool]$trigger.active -or ($recommendedCapabilities.Count -gt 0))

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        if ($mode -eq "shadow") {
            $enforcement = "advisory"
            $reason = if ($trigger.active) { "shadow_discovery_signal" } else { "shadow_scope_only" }
        } elseif ($mode -in @("soft", "strict")) {
            if ($trigger.active) {
                $enforcement = "confirm_required"
                $reason = "deep_discovery_interview_required"
            } else {
                $enforcement = "advisory"
                $reason = "scope_match_no_trigger"
            }
        } else {
            $enforcement = "advisory"
            $reason = "unknown_mode_advisory"
        }
    }

    $minCompletenessForConfirmRequired = 0.45
    if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.intent_contract -and $DeepDiscoveryPolicy.intent_contract.min_completeness_for_confirm_required -ne $null) {
        $minCompletenessForConfirmRequired = [double]$DeepDiscoveryPolicy.intent_contract.min_completeness_for_confirm_required
    }

    return [pscustomobject]@{
        enabled = [bool]$scope.enabled
        mode = $mode
        scope_applicable = $scopeApplicable
        scope_reasons = @($scope.reasons)
        preserve_routing_assignment = [bool]$scope.preserve_routing_assignment
        trigger_active = [bool]$trigger.active
        trigger_score = [double]$trigger.trigger_score
        trigger_details = $trigger
        capability_hit_count = [int]$recommendedCapabilities.Count
        capability_hits = @($capabilityHits)
        recommended_capabilities = @($recommendedCapabilities)
        recommended_skills = @($recommendedSkills)
        interview_required = [bool]$interviewRequired
        interview_questions = @($questions | Select-Object -First $maxQuestions)
        max_questions = [int]$maxQuestions
        min_completeness_for_confirm_required = [double]$minCompletenessForConfirmRequired
        enforcement = $enforcement
        reason = $reason
        confirm_required = ($enforcement -eq "confirm_required")
        should_apply_hook = [bool]$interviewRequired
    }
}

