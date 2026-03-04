# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-PythonCleanCodeAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$PythonCleanCodeOverlayPolicy
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
        paths_detected = @()
        paths_existing = @()
        python_file_signal = $false
        language_keyword_hits = @()
        principle_groups_matched = @()
        principle_group_hits = [pscustomobject]@{}
        principle_group_scores = [pscustomobject]@{}
        anti_pattern_hits = @()
        suppress_keyword_hits = @()
        python_signal_score = 0.0
        signal_likelihood = "none"
        trigger_active = $false
        confirm_recommended = $false
        confirm_required = $false
        strict_scope_applied = $false
        recommended_refactors = @()
        should_apply_hook = $false
    }

    if (-not $PythonCleanCodeOverlayPolicy) {
        return [pscustomobject]$base
    }

    $enabled = $true
    if ($PythonCleanCodeOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$PythonCleanCodeOverlayPolicy.enabled
    }
    $mode = if ($PythonCleanCodeOverlayPolicy.mode) { [string]$PythonCleanCodeOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        $base.enabled = $false
        $base.mode = "off"
        $base.reason = "policy_off"
        return [pscustomobject]$base
    }

    $taskAllow = @("coding", "review", "debug")
    if ($PythonCleanCodeOverlayPolicy.task_allow) {
        $taskAllow = @($PythonCleanCodeOverlayPolicy.task_allow)
    }
    $gradeAllow = @("M", "L", "XL")
    if ($PythonCleanCodeOverlayPolicy.grade_allow) {
        $gradeAllow = @($PythonCleanCodeOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    $skillAllow = @()
    if ($PythonCleanCodeOverlayPolicy.monitor) {
        if ($PythonCleanCodeOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($PythonCleanCodeOverlayPolicy.monitor.pack_allow)
        }
        if ($PythonCleanCodeOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($PythonCleanCodeOverlayPolicy.monitor.skill_allow)
        }
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($PythonCleanCodeOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$PythonCleanCodeOverlayPolicy.preserve_routing_assignment
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

    $probeEnabled = $true
    $extractFromPrompt = $true
    $workspaceProbeWhenNoPath = $false
    $workspaceProbeLimit = 2
    $workspaceProbeExtensions = @("py", "pyi")
    if ($PythonCleanCodeOverlayPolicy.path_probe) {
        if ($PythonCleanCodeOverlayPolicy.path_probe.enabled -ne $null) {
            $probeEnabled = [bool]$PythonCleanCodeOverlayPolicy.path_probe.enabled
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.extract_from_prompt -ne $null) {
            $extractFromPrompt = [bool]$PythonCleanCodeOverlayPolicy.path_probe.extract_from_prompt
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_when_no_path -ne $null) {
            $workspaceProbeWhenNoPath = [bool]$PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_when_no_path
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_limit -ne $null) {
            $workspaceProbeLimit = [int]$PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_limit
        }
        if ($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_extensions) {
            $workspaceProbeExtensions = @($PythonCleanCodeOverlayPolicy.path_probe.workspace_probe_extensions)
        }
    }

    $pathsDetected = @()
    if ($probeEnabled -and $extractFromPrompt) {
        $pathsDetected = Get-PathCandidatesFromPrompt -Prompt $Prompt -SupportedExtensions $workspaceProbeExtensions
    }
    $pathsExisting = @()
    if ($probeEnabled) {
        $pathsExisting = Resolve-ExistingPathCandidates `
            -PathCandidates $pathsDetected `
            -WorkspaceProbeEnabled $workspaceProbeWhenNoPath `
            -WorkspaceProbeLimit $workspaceProbeLimit `
            -WorkspaceProbeExtensions $workspaceProbeExtensions
    }

    $base.paths_detected = @($pathsDetected)
    $base.paths_existing = @($pathsExisting)
    $pythonFileSignal = (($pathsDetected.Count -gt 0) -or ($pathsExisting.Count -gt 0))
    $base.python_file_signal = $pythonFileSignal

    $languageKeywords = @(
        "python",
        ".py",
        ".pyi",
        "pytest",
        "dataclass",
        "type hints",
        "async def",
        "pep8",
        "pydantic",
        "flake8",
        "ruff",
        "mypy",
        "python文件",
        "python脚本",
        "写python",
        "重构python"
    )
    if ($PythonCleanCodeOverlayPolicy.language_keywords) {
        $languageKeywords = @($PythonCleanCodeOverlayPolicy.language_keywords)
    }

    $principleGroups = [ordered]@{
        naming = @("naming", "meaningful name", "clear name", "命名", "可读命名")
        function_design = @("single responsibility", "long function", "too many arguments", "boolean parameter", "函数过长", "参数过多", "布尔参数")
        class_design = @("solid", "class responsibility", "god object", "god class", "类职责", "大而全类")
        side_effects = @("side effect", "pure function", "immutable", "副作用", "纯函数")
        duplication = @("duplicate logic", "duplication", "dry", "重复代码", "去重逻辑")
        error_handling = @("raise", "exception handling", "error boundary", "异常处理", "错误处理")
        tests = @("pytest", "unit test", "testability", "可测试性", "单元测试")
    }
    if ($PythonCleanCodeOverlayPolicy.principle_groups) {
        $principleGroups = [ordered]@{}
        foreach ($groupName in @($PythonCleanCodeOverlayPolicy.principle_groups.PSObject.Properties.Name)) {
            $principleGroups[[string]$groupName] = @($PythonCleanCodeOverlayPolicy.principle_groups.$groupName)
        }
    }

    $antiPatternKeywords = @(
        "god class",
        "god object",
        "long function",
        "too many arguments",
        "boolean parameter",
        "magic number",
        "duplicate logic",
        "side effect",
        "spaghetti",
        "函数过长",
        "参数过多",
        "布尔参数",
        "魔法数字",
        "重复代码",
        "副作用"
    )
    if ($PythonCleanCodeOverlayPolicy.anti_pattern_keywords) {
        $antiPatternKeywords = @($PythonCleanCodeOverlayPolicy.anti_pattern_keywords)
    }

    $suppressKeywords = @(
        "generated",
        "migration",
        "vendor",
        "autogen",
        "docs only",
        "benchmark only",
        "notebook draft",
        "自动生成",
        "迁移脚本",
        "仅文档"
    )
    if ($PythonCleanCodeOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($PythonCleanCodeOverlayPolicy.suppress_keywords)
    }

    $triggerMin = 0.45
    $confirmMin = 0.6
    $highSignalMin = 0.78
    $suppressWeight = 0.25
    $minAntiHitsForConfirm = 1
    if ($PythonCleanCodeOverlayPolicy.thresholds) {
        if ($PythonCleanCodeOverlayPolicy.thresholds.trigger_signal_score_min -ne $null) {
            $triggerMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.trigger_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$PythonCleanCodeOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$PythonCleanCodeOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($PythonCleanCodeOverlayPolicy.thresholds.min_anti_pattern_hits_for_confirm -ne $null) {
            $minAntiHitsForConfirm = [int]$PythonCleanCodeOverlayPolicy.thresholds.min_anti_pattern_hits_for_confirm
        }
    }

    $languageMatches = @()
    foreach ($kw in $languageKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $languageMatches += [string]$kw
        }
    }
    $antiPatternMatches = @()
    foreach ($kw in $antiPatternKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $antiPatternMatches += [string]$kw
        }
    }
    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $groupHits = [ordered]@{}
    $groupScores = [ordered]@{}
    $matchedGroups = @()
    $principleMatches = @()
    foreach ($groupName in @($principleGroups.Keys)) {
        $keywords = @($principleGroups[$groupName])
        $hits = @()
        foreach ($kw in $keywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $keywords
        $groupHits[[string]$groupName] = @($hits)
        $groupScores[[string]$groupName] = [Math]::Round([double]$score, 4)
        if ($hits.Count -gt 0) {
            $matchedGroups += [string]$groupName
            $principleMatches += @($hits)
        }
    }

    $languageRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $languageKeywords
    $principleRatio = if ($principleMatches.Count -gt 0) { Get-KeywordRatio -PromptLower $PromptLower -Keywords @($principleMatches | Select-Object -Unique) } else { 0.0 }
    $antiPatternRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $antiPatternKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $fileSignal = if ($pythonFileSignal) { 1.0 } else { 0.0 }
    $semanticRatio = [Math]::Max([double]$principleRatio, [double]$antiPatternRatio)

    $signalScore = (0.65 * $fileSignal) + (0.20 * $languageRatio) + (0.15 * $semanticRatio) - ($suppressWeight * $suppressRatio)
    if ($pythonFileSignal -and $signalScore -lt $triggerMin) {
        $signalScore = [Math]::Max($signalScore, $triggerMin)
    }
    $signalScore = [Math]::Max(0.0, [Math]::Min(1.0, $signalScore))
    $signalScore = [Math]::Round([double]$signalScore, 4)

    $signalLikelihood = "none"
    if ($signalScore -ge $highSignalMin) {
        $signalLikelihood = "high"
    } elseif ($signalScore -ge $confirmMin) {
        $signalLikelihood = "medium"
    } elseif ($signalScore -gt 0) {
        $signalLikelihood = "low"
    }

    $triggerActive = ($scopeApplicable -and (($signalScore -ge $triggerMin) -or $pythonFileSignal))
    $confirmRecommended = (
        $triggerActive -and
        ($signalScore -ge $confirmMin) -and
        (
            ($antiPatternMatches.Count -ge $minAntiHitsForConfirm) -or
            ($matchedGroups.Count -ge 2) -or
            ($TaskType -eq "review")
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("coding", "review")
    if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope) {
        if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($PythonCleanCodeOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($PythonCleanCodeOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($PythonCleanCodeOverlayPolicy.strict_confirm_scope.task_types)
        }
    }
    $strictScopeApplied = (($strictGrades -contains $Grade) -and ($strictTasks -contains $TaskType))
    $confirmRequired = (
        $triggerActive -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        $confirmRecommended -and
        ($antiPatternMatches.Count -ge $minAntiHitsForConfirm)
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
                    $reason = "shadow_python_advisory"
                }
                "soft" {
                    $enforcement = "advisory"
                    if ($confirmRecommended) {
                        $reason = "soft_python_confirm_recommended"
                    } else {
                        $reason = "soft_python_advisory"
                    }
                }
                "strict" {
                    if ($confirmRequired) {
                        $enforcement = "confirm_required"
                        $reason = "strict_python_clean_code_confirmation"
                    } else {
                        $enforcement = "advisory"
                        $reason = "strict_python_advisory"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "unknown_mode_advisory"
                }
            }
        }
    }

    $recommendationMap = $null
    if ($PythonCleanCodeOverlayPolicy.recommendations_by_group) {
        $recommendationMap = $PythonCleanCodeOverlayPolicy.recommendations_by_group
    }
    $recommendedRefactors = @()
    if ($triggerActive) {
        $recommendationKeys = if ($recommendationMap) { @($recommendationMap.PSObject.Properties.Name) } else { @() }
        foreach ($groupName in @($matchedGroups)) {
            if ($recommendationMap -and ($recommendationKeys -contains $groupName)) {
                $recommendedRefactors += [string]$recommendationMap.$groupName
            }
        }
        if ($antiPatternMatches.Count -gt 0) {
            $recommendedRefactors += "Prioritize removing detected anti-pattern hotspots before adding new behavior."
        }
        if ($recommendedRefactors.Count -eq 0) {
            $recommendedRefactors += "Apply Python clean-code checks: naming clarity, function focus, side-effect isolation, and duplication cleanup."
        }
    }

    $base.enforcement = $enforcement
    $base.reason = $reason
    $base.language_keyword_hits = @($languageMatches)
    $base.principle_groups_matched = @($matchedGroups)
    $base.principle_group_hits = [pscustomobject]$groupHits
    $base.principle_group_scores = [pscustomobject]$groupScores
    $base.anti_pattern_hits = @($antiPatternMatches)
    $base.suppress_keyword_hits = @($suppressMatches)
    $base.python_signal_score = $signalScore
    $base.signal_likelihood = $signalLikelihood
    $base.trigger_active = $triggerActive
    $base.confirm_recommended = $confirmRecommended
    $base.confirm_required = $confirmRequired
    $base.strict_scope_applied = $strictScopeApplied
    $base.recommended_refactors = @($recommendedRefactors | Select-Object -Unique)
    $base.should_apply_hook = ($scopeApplicable -and $triggerActive)

    return [pscustomobject]$base
}


