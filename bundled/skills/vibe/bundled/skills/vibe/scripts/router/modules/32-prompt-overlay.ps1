# Auto-extracted router module. Keep function bodies behavior-identical.

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


