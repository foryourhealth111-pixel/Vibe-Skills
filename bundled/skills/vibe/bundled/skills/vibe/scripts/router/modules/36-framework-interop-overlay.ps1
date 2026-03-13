# Auto-extracted router module. Keep function bodies behavior-identical.

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


