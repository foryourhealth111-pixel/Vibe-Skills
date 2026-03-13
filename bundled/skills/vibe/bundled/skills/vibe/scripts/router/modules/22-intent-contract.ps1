# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-DeepDiscoveryDeliverableHint {
    param([string]$PromptLower)

    $kCode = @("script", "code", "api", "service", "pipeline", "脚本", "代码", "接口", "服务")
    $kReport = @("report", "analysis", "summary", "文档", "报告", "总结", "分析")
    $kPlan = @("plan", "design", "architecture", "roadmap", "方案", "规划", "设计", "架构")

    $codeHit = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $kCode)
    $reportHit = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $kReport)
    $planHit = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords $kPlan)

    if ($codeHit -gt 0 -and $reportHit -gt 0) { return "code_plus_report" }
    if ($codeHit -gt 0 -and $planHit -gt 0) { return "plan_plus_code" }
    if ($reportHit -gt 0 -and $planHit -gt 0) { return "plan_plus_report" }
    if ($codeHit -gt 0) { return "code" }
    if ($reportHit -gt 0) { return "report" }
    if ($planHit -gt 0) { return "plan" }
    return "unknown"
}

function Get-DeepDiscoveryConstraintHints {
    param([string]$PromptLower)

    $constraints = @()
    if (Get-KeywordRatio -PromptLower $PromptLower -Keywords @("must", "必须", "strict", "严格")) { $constraints += "strict_requirement" }
    if (Get-KeywordRatio -PromptLower $PromptLower -Keywords @("today", "asap", "deadline", "今天", "尽快", "截止")) { $constraints += "timeline_constraint" }
    if (Get-KeywordRatio -PromptLower $PromptLower -Keywords @("json", "csv", "xlsx", "markdown", "pdf", "格式")) { $constraints += "output_format_constraint" }
    if (Get-KeywordRatio -PromptLower $PromptLower -Keywords @("test", "verify", "validation", "gate", "测试", "验证", "门禁")) { $constraints += "verification_constraint" }
    return @($constraints | Select-Object -Unique)
}

function Get-DeepDiscoveryExecutionModeHint {
    param([string]$PromptLower)

    $planHit = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords @("plan", "design", "brainstorm", "方案", "规划", "设计", "访谈"))
    $execHit = [double](Get-KeywordRatio -PromptLower $PromptLower -Keywords @("implement", "execute", "build", "落地", "实现", "执行"))

    if ($planHit -gt 0 -and $execHit -gt 0) { return "plan_then_execute" }
    if ($planHit -gt 0) { return "plan_only" }
    if ($execHit -gt 0) { return "execute_only" }
    return "unspecified"
}

function Get-DeepDiscoveryIntentContract {
    param(
        [string]$PromptText,
        [string]$PromptLower,
        [object]$DeepDiscoveryAdvice,
        [object]$DeepDiscoveryPolicy,
        [object]$CapabilityCatalog
    )

    $normalization = Get-RoutingPromptNormalization -PromptText $PromptText
    $goalText = if ($normalization -and $normalization.normalized) { [string]$normalization.normalized } else { [string]$PromptText }

    $deliverable = Get-DeepDiscoveryDeliverableHint -PromptLower $PromptLower
    $constraints = Get-DeepDiscoveryConstraintHints -PromptLower $PromptLower
    $executionMode = Get-DeepDiscoveryExecutionModeHint -PromptLower $PromptLower

    $capabilities = @()
    if ($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.recommended_capabilities) {
        $capabilities = @($DeepDiscoveryAdvice.recommended_capabilities | Select-Object -Unique)
    }

    $requiredFields = @("goal", "deliverable", "constraints", "capabilities")
    if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.intent_contract -and $DeepDiscoveryPolicy.intent_contract.required_fields) {
        $requiredFields = @($DeepDiscoveryPolicy.intent_contract.required_fields)
    }

    $fieldPresence = [ordered]@{
        goal = [bool]($goalText -and $goalText.Length -ge 8)
        deliverable = ($deliverable -ne "unknown")
        constraints = ($constraints.Count -gt 0)
        capabilities = ($capabilities.Count -gt 0)
    }

    $presentRequiredCount = 0
    $missingFields = @()
    foreach ($field in $requiredFields) {
        $fieldKey = [string]$field
        $value = $false
        if ($fieldPresence.Contains($fieldKey)) {
            $value = [bool]$fieldPresence[$fieldKey]
        }
        if ($value) {
            $presentRequiredCount++
        } else {
            $missingFields += $fieldKey
        }
    }

    $denominator = if ($requiredFields.Count -gt 0) { [double]$requiredFields.Count } else { 1.0 }
    $completeness = [Math]::Round(([double]$presentRequiredCount / $denominator), 4)

    return [pscustomobject]@{
        goal = $goalText
        deliverable = $deliverable
        constraints = @($constraints)
        capabilities = @($capabilities)
        execution_mode = $executionMode
        required_fields = @($requiredFields)
        missing_fields = @($missingFields)
        completeness = [double]$completeness
        field_presence = [pscustomobject]$fieldPresence
    }
}

function Get-DeepDiscoveryCandidateFilter {
    param(
        [object[]]$Packs,
        [object]$IntentContract,
        [object]$DeepDiscoveryAdvice,
        [object]$DeepDiscoveryPolicy,
        [string]$TaskType
    )

    $mode = if ($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.mode) { [string]$DeepDiscoveryAdvice.mode } else { "off" }
    $scopeApplicable = [bool]($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.scope_applicable)
    $triggerActive = [bool]($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.trigger_active)
    $preserveRoutingAssignment = [bool]($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.preserve_routing_assignment)
    $contractCompleteness = if ($IntentContract -and $IntentContract.completeness -ne $null) { [double]$IntentContract.completeness } else { 0.0 }

    $selectionPolicy = if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.selection) { $DeepDiscoveryPolicy.selection } else { $null }
    $applyInModes = if ($selectionPolicy -and $selectionPolicy.apply_in_modes) { @($selectionPolicy.apply_in_modes) } else { @("soft", "strict") }
    $modeAllowsFilter = ($applyInModes -contains $mode)

    $minCompleteness = 0.6
    if ($DeepDiscoveryPolicy -and $DeepDiscoveryPolicy.intent_contract -and $DeepDiscoveryPolicy.intent_contract.min_completeness_for_filter -ne $null) {
        $minCompleteness = [double]$DeepDiscoveryPolicy.intent_contract.min_completeness_for_filter
    }
    $completenessPassed = ($contractCompleteness -ge $minCompleteness)

    $requiredCapabilities = if ($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.recommended_capabilities) { @($DeepDiscoveryAdvice.recommended_capabilities | Select-Object -Unique) } else { @() }
    $requiredSkills = if ($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.recommended_skills) { @($DeepDiscoveryAdvice.recommended_skills | Select-Object -Unique) } else { @() }

    $shouldConsiderFilter = $scopeApplicable -and $triggerActive -and ($requiredSkills.Count -gt 0)
    $candidatePacksCount = if ($Packs) { @($Packs).Count } else { 0 }

    $filteredPacks = @()
    $filteredCandidateCount = 0
    if ($shouldConsiderFilter -and $modeAllowsFilter -and $completenessPassed) {
        foreach ($pack in @($Packs)) {
            $packCandidates = @($pack.skill_candidates)
            if ($packCandidates.Count -eq 0) { continue }

            $matchedCandidates = @()
            foreach ($candidate in $packCandidates) {
                $candidateName = [string]$candidate
                if ($requiredSkills -contains $candidateName) {
                    $matchedCandidates += $candidateName
                }
            }

            if ($matchedCandidates.Count -le 0) { continue }
            $filteredCandidateCount += $matchedCandidates.Count

            $filteredPacks += [pscustomobject]@{
                id = [string]$pack.id
                priority = [int]$pack.priority
                grade_allow = @($pack.grade_allow)
                task_allow = @($pack.task_allow)
                trigger_keywords = @($pack.trigger_keywords)
                skill_candidates = @($matchedCandidates | Select-Object -Unique)
                defaults_by_task = $pack.defaults_by_task
            }
        }
    }

    $requireNonEmptyFilterResult = if ($selectionPolicy -and $selectionPolicy.require_non_empty_filter_result -ne $null) { [bool]$selectionPolicy.require_non_empty_filter_result } else { $true }
    $fallbackOnEmpty = if ($selectionPolicy -and $selectionPolicy.fallback_on_empty) { [string]$selectionPolicy.fallback_on_empty } else { "use_full_pack_candidates" }

    $wouldApplyFilter = $shouldConsiderFilter -and $modeAllowsFilter -and $completenessPassed -and ($filteredPacks.Count -gt 0)
    if ($requireNonEmptyFilterResult -and $filteredPacks.Count -eq 0) {
        $wouldApplyFilter = $false
    }

    $routeFilterApplied = $wouldApplyFilter -and (-not $preserveRoutingAssignment)

    $reason = "outside_scope"
    if (-not $scopeApplicable) {
        $reason = "outside_scope"
    } elseif (-not $triggerActive) {
        $reason = "trigger_inactive"
    } elseif (-not $modeAllowsFilter) {
        $reason = "mode_not_allowed"
    } elseif (-not $completenessPassed) {
        $reason = "contract_incomplete"
    } elseif ($filteredPacks.Count -le 0) {
        $reason = "no_matching_candidates"
    } elseif ($preserveRoutingAssignment) {
        $reason = "preserve_routing_assignment"
    } else {
        $reason = "filter_applied"
    }

    return [pscustomobject]@{
        enabled = [bool]($DeepDiscoveryAdvice -and $DeepDiscoveryAdvice.enabled)
        mode = $mode
        scope_applicable = $scopeApplicable
        trigger_active = $triggerActive
        mode_allows_filter = [bool]$modeAllowsFilter
        contract_completeness = [Math]::Round([double]$contractCompleteness, 4)
        min_completeness_for_filter = [Math]::Round([double]$minCompleteness, 4)
        completeness_passed = [bool]$completenessPassed
        preserve_routing_assignment = [bool]$preserveRoutingAssignment
        required_capabilities = @($requiredCapabilities)
        required_skills = @($requiredSkills)
        candidate_packs_count = [int]$candidatePacksCount
        filtered_packs_count = [int]$filteredPacks.Count
        filtered_candidate_count = [int]$filteredCandidateCount
        require_non_empty_filter_result = [bool]$requireNonEmptyFilterResult
        fallback_on_empty = $fallbackOnEmpty
        would_apply_filter = [bool]$wouldApplyFilter
        route_filter_applied = [bool]$routeFilterApplied
        reason = $reason
        filtered_pack_ids = @($filteredPacks | ForEach-Object { [string]$_.id })
        filtered_packs = @($filteredPacks)
    }
}

function Get-DeepDiscoveryFilterSummary {
    param([object]$DeepDiscoveryFilter)

    if (-not $DeepDiscoveryFilter) { return $null }

    $preview = @()
    if ($DeepDiscoveryFilter.filtered_packs) {
        foreach ($pack in @($DeepDiscoveryFilter.filtered_packs | Select-Object -First 5)) {
            $preview += [pscustomobject]@{
                pack_id = [string]$pack.id
                skill_candidates = @($pack.skill_candidates | Select-Object -First 5)
            }
        }
    }

    return [pscustomobject]@{
        enabled = [bool]$DeepDiscoveryFilter.enabled
        mode = [string]$DeepDiscoveryFilter.mode
        scope_applicable = [bool]$DeepDiscoveryFilter.scope_applicable
        trigger_active = [bool]$DeepDiscoveryFilter.trigger_active
        mode_allows_filter = [bool]$DeepDiscoveryFilter.mode_allows_filter
        contract_completeness = [double]$DeepDiscoveryFilter.contract_completeness
        min_completeness_for_filter = [double]$DeepDiscoveryFilter.min_completeness_for_filter
        completeness_passed = [bool]$DeepDiscoveryFilter.completeness_passed
        preserve_routing_assignment = [bool]$DeepDiscoveryFilter.preserve_routing_assignment
        required_capabilities = @($DeepDiscoveryFilter.required_capabilities)
        required_skills = @($DeepDiscoveryFilter.required_skills)
        candidate_packs_count = [int]$DeepDiscoveryFilter.candidate_packs_count
        filtered_packs_count = [int]$DeepDiscoveryFilter.filtered_packs_count
        filtered_candidate_count = [int]$DeepDiscoveryFilter.filtered_candidate_count
        would_apply_filter = [bool]$DeepDiscoveryFilter.would_apply_filter
        route_filter_applied = [bool]$DeepDiscoveryFilter.route_filter_applied
        reason = [string]$DeepDiscoveryFilter.reason
        filtered_pack_ids = @($DeepDiscoveryFilter.filtered_pack_ids)
        filtered_preview = @($preview)
    }
}

function Get-RouteRuntimeStatePromptDigest {
    param(
        [object]$Result,
        [string]$PromptText,
        [bool]$FoldOutsideScope = $true
    )

    if (-not $Result) { return $null }

    $overlayPropertyMap = [ordered]@{
        dialectic_team = "dialectic_team_advice"
        daily_dialectic = "daily_dialectic_advice"
        openspec = "openspec_advice"
        gsd = "gsd_overlay_advice"
        prompt = "prompt_overlay_advice"
        memory = "memory_governance_advice"
        ai_rerank = "ai_rerank_advice"
        data_scale = "data_scale_advice"
        quality_debt = "quality_debt_advice"
        framework_interop = "framework_interop_advice"
        ml_lifecycle = "ml_lifecycle_advice"
        python_clean_code = "python_clean_code_advice"
        system_design = "system_design_advice"
        cuda_kernel = "cuda_kernel_advice"
        retrieval = "retrieval_advice"
    }

    $overlayActive = @()
    $overlayFoldedCount = 0
    foreach ($entry in @($overlayPropertyMap.GetEnumerator())) {
        $overlayName = [string]$entry.Key
        $propName = [string]$entry.Value
        $advice = $Result.$propName
        if (-not $advice) { continue }

        $scopeApplicable = $false
        if ($advice.PSObject.Properties.Name -contains "scope_applicable") {
            $scopeApplicable = [bool]$advice.scope_applicable
        }
        $confirmRequired = $false
        if ($advice.PSObject.Properties.Name -contains "confirm_required") {
            $confirmRequired = [bool]$advice.confirm_required
        }
        $reason = if ($advice.PSObject.Properties.Name -contains "reason") { [string]$advice.reason } else { "n/a" }
        $outsideScope = (-not $scopeApplicable) -or ($reason -eq "outside_scope")

        if ($FoldOutsideScope -and $outsideScope -and (-not $confirmRequired)) {
            $overlayFoldedCount++
            continue
        }
        $overlayActive += ("{0}:{1}" -f $overlayName, $reason)
    }

    $deepDiscovery = $Result.deep_discovery_advice
    $intentContract = $Result.intent_contract

    return [pscustomobject]@{
        prompt_hash = Get-HashHex -InputText ([string]$PromptText)
        route = [pscustomobject]@{
            grade = [string]$Result.grade
            task_type = [string]$Result.task_type
            route_mode = [string]$Result.route_mode
            route_reason = [string]$Result.route_reason
            selected_pack = if ($Result.selected) { [string]$Result.selected.pack_id } else { "none" }
            selected_skill = if ($Result.selected) { [string]$Result.selected.skill } else { "none" }
            confidence = [double]$Result.confidence
        }
        deep_discovery = [pscustomobject]@{
            trigger_active = [bool]($deepDiscovery -and $deepDiscovery.trigger_active)
            trigger_score = if ($deepDiscovery -and $deepDiscovery.trigger_score -ne $null) { [double]$deepDiscovery.trigger_score } else { 0.0 }
            capability_hit_count = if ($deepDiscovery -and $deepDiscovery.capability_hit_count -ne $null) { [int]$deepDiscovery.capability_hit_count } else { 0 }
            confirm_required = [bool]($deepDiscovery -and $deepDiscovery.confirm_required)
            contract_completeness = if ($intentContract -and $intentContract.completeness -ne $null) { [double]$intentContract.completeness } else { 0.0 }
            route_filter_applied = [bool]$Result.deep_discovery_route_filter_applied
        }
        dialectic = [pscustomobject]@{
            team_explicit_requested = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.explicit_requested)
            team_mode_allowed = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.team_mode_allowed)
            team_mode_applied = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.should_apply_team_mode)
            team_confirm_required = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.confirm_required)
            daily_guard_scope = [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.scope_applicable)
            daily_guard_confirm_required = [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.confirm_required)
        }
        heartbeat = [pscustomobject]@{
            enabled = [bool]($Result.heartbeat_advice -and $Result.heartbeat_advice.enabled)
            mode = if ($Result.heartbeat_advice -and $Result.heartbeat_advice.mode) { [string]$Result.heartbeat_advice.mode } else { "off" }
            status = if ($Result.heartbeat_status -and $Result.heartbeat_status.current_status) { [string]$Result.heartbeat_status.current_status } else { "disabled" }
            lifecycle_status = if ($Result.heartbeat_status -and $Result.heartbeat_status.lifecycle_status) { [string]$Result.heartbeat_status.lifecycle_status } else { "disabled" }
            pulse_count = if ($Result.heartbeat_status -and $Result.heartbeat_status.pulse_count -ne $null) { [int]$Result.heartbeat_status.pulse_count } else { 0 }
            stall_score = if ($Result.heartbeat_status -and $Result.heartbeat_status.stall_score -ne $null) { [double]$Result.heartbeat_status.stall_score } else { 0.0 }
            hard_stall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.hard_stall } else { $false }
            suspect_stall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.suspect_stall } else { $false }
            confirm_required = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.confirm_required } else { $false }
            auto_diagnosis_triggered = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.auto_diagnosis_triggered } else { $false }
        }
        overlay_digest = [pscustomobject]@{
            active_overlays = @($overlayActive | Select-Object -First 8)
            folded_outside_scope_count = [int]$overlayFoldedCount
        }
    }
}


