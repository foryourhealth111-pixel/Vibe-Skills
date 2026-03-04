# Auto-extracted router module. Keep function bodies behavior-identical.

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


