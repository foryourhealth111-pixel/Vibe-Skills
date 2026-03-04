# Auto-extracted router module. Keep function bodies behavior-identical.

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


