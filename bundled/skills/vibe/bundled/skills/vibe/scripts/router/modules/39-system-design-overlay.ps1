# Auto-extracted router module. Keep function bodies behavior-identical.

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


