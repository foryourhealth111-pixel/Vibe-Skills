# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-MlLifecycleOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$MlLifecycleOverlayPolicy
    )

    if (-not $MlLifecycleOverlayPolicy) {
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
            lifecycle_signal_score = 0.0
            lifecycle_likelihood = "none"
            lifecycle_keyword_hits = @()
            suppress_keyword_hits = @()
            stage_detected = "none"
            stage_scores = [pscustomobject]@{}
            stage_hits = [pscustomobject]@{}
            required_checks = @()
            artifacts_required = @()
            artifact_hits = [pscustomobject]@{}
            missing_artifacts = @()
            missing_artifact_ratio = 0.0
            deploy_readiness = "not_applicable"
            confirm_recommended = $false
            confirm_required = $false
            strict_scope_applied = $false
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
    if ($MlLifecycleOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$MlLifecycleOverlayPolicy.enabled
    }

    $mode = if ($MlLifecycleOverlayPolicy.mode) { [string]$MlLifecycleOverlayPolicy.mode } else { "off" }
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
            lifecycle_signal_score = 0.0
            lifecycle_likelihood = "none"
            lifecycle_keyword_hits = @()
            suppress_keyword_hits = @()
            stage_detected = "none"
            stage_scores = [pscustomobject]@{}
            stage_hits = [pscustomobject]@{}
            required_checks = @()
            artifacts_required = @()
            artifact_hits = [pscustomobject]@{}
            missing_artifacts = @()
            missing_artifact_ratio = 0.0
            deploy_readiness = "not_applicable"
            confirm_recommended = $false
            confirm_required = $false
            strict_scope_applied = $false
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

    $taskAllow = @("planning", "coding", "review", "research")
    if ($MlLifecycleOverlayPolicy.task_allow) {
        $taskAllow = @($MlLifecycleOverlayPolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($MlLifecycleOverlayPolicy.grade_allow) {
        $gradeAllow = @($MlLifecycleOverlayPolicy.grade_allow)
    }

    $packAllow = @("data-ml", "ai-llm")
    $skillAllow = @()
    if ($MlLifecycleOverlayPolicy.monitor) {
        if ($MlLifecycleOverlayPolicy.monitor.pack_allow) {
            $packAllow = @($MlLifecycleOverlayPolicy.monitor.pack_allow)
        }
        if ($MlLifecycleOverlayPolicy.monitor.skill_allow) {
            $skillAllow = @($MlLifecycleOverlayPolicy.monitor.skill_allow)
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
    if ($MlLifecycleOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$MlLifecycleOverlayPolicy.preserve_routing_assignment
    }

    $lifecycleKeywords = @(
        "ml pipeline",
        "training pipeline",
        "model training",
        "model evaluation",
        "baseline compare",
        "experiment tracking",
        "model registry",
        "serve model",
        "deploy model",
        "canary rollout",
        "continual learning",
        "drift monitoring",
        "retraining",
        "机器学习流水线",
        "模型训练",
        "模型评估",
        "基线对比",
        "实验追踪",
        "模型注册",
        "模型部署",
        "持续学习",
        "漂移监控",
        "再训练"
    )
    if ($MlLifecycleOverlayPolicy.lifecycle_signal_keywords) {
        $lifecycleKeywords = @($MlLifecycleOverlayPolicy.lifecycle_signal_keywords)
    }

    $suppressKeywords = @(
        "math proof",
        "paper summary only",
        "just theory",
        "only concept",
        "仅概念",
        "只要理论",
        "论文总结"
    )
    if ($MlLifecycleOverlayPolicy.suppress_keywords) {
        $suppressKeywords = @($MlLifecycleOverlayPolicy.suppress_keywords)
    }

    $stageKeywordMap = [ordered]@{
        develop = @("feature engineering", "data preprocessing", "train model", "training pipeline", "训练", "特征工程")
        evaluate = @("evaluation", "metrics", "ablation", "baseline compare", "验证", "评估", "基线")
        deploy = @("deploy", "serve", "production", "canary", "api service", "上线", "部署", "服务化")
        iterate = @("drift", "monitoring", "feedback loop", "retraining", "continual learning", "漂移", "监控", "持续学习")
    }
    if ($MlLifecycleOverlayPolicy.stage_keywords) {
        $stageKeywordMap = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.stage_keywords.PSObject.Properties.Name)) {
            $stageKeywordMap[[string]$stageName] = @($MlLifecycleOverlayPolicy.stage_keywords.$stageName)
        }
    }

    $artifactKeywordMap = [ordered]@{
        run_id = @("run_id", "run id", "mlflow run")
        evaluation_results = @("evaluation report", "evaluation_results", "metrics report", "评估报告")
        baseline_compare = @("baseline compare", "baseline comparison", "基线对比")
        data_tests = @("data tests", "great expectations", "数据校验")
        model_tests = @("model tests", "model validation", "模型测试")
        service_smoke = @("smoke test", "service smoke", "服务冒烟")
        monitoring_metrics = @("monitoring metrics", "drift dashboard", "监控指标")
        retraining_plan = @("retraining plan", "retrain policy", "再训练计划")
        dataset_version = @("dataset version", "data version", "数据版本")
    }
    if ($MlLifecycleOverlayPolicy.artifact_keywords) {
        $artifactKeywordMap = [ordered]@{}
        foreach ($artifactName in @($MlLifecycleOverlayPolicy.artifact_keywords.PSObject.Properties.Name)) {
            $artifactKeywordMap[[string]$artifactName] = @($MlLifecycleOverlayPolicy.artifact_keywords.$artifactName)
        }
    }

    $confirmSignalMin = 0.5
    $highSignalMin = 0.75
    $suppressWeight = 0.28
    $minLifecycleHitsForOverlay = 1
    $missingArtifactRatioForConfirm = 0.4
    if ($MlLifecycleOverlayPolicy.thresholds) {
        if ($MlLifecycleOverlayPolicy.thresholds.confirm_signal_score_min -ne $null) {
            $confirmSignalMin = [double]$MlLifecycleOverlayPolicy.thresholds.confirm_signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.thresholds.high_signal_score_min -ne $null) {
            $highSignalMin = [double]$MlLifecycleOverlayPolicy.thresholds.high_signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.thresholds.suppress_penalty_weight -ne $null) {
            $suppressWeight = [double]$MlLifecycleOverlayPolicy.thresholds.suppress_penalty_weight
        }
        if ($MlLifecycleOverlayPolicy.thresholds.min_lifecycle_hits_for_overlay -ne $null) {
            $minLifecycleHitsForOverlay = [int]$MlLifecycleOverlayPolicy.thresholds.min_lifecycle_hits_for_overlay
        }
        if ($MlLifecycleOverlayPolicy.thresholds.missing_artifact_ratio_for_confirm -ne $null) {
            $missingArtifactRatioForConfirm = [double]$MlLifecycleOverlayPolicy.thresholds.missing_artifact_ratio_for_confirm
        }
    }

    $signalMatches = @()
    foreach ($kw in $lifecycleKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $signalMatches += [string]$kw
        }
    }
    $suppressMatches = @()
    foreach ($kw in $suppressKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $suppressMatches += [string]$kw
        }
    }

    $signalRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $lifecycleKeywords
    $suppressRatio = Get-KeywordRatio -PromptLower $PromptLower -Keywords $suppressKeywords
    $lifecycleScore = [Math]::Max(0.0, [Math]::Min(1.0, ($signalRatio - ($suppressWeight * $suppressRatio))))
    if ($signalMatches.Count -lt $minLifecycleHitsForOverlay) {
        $lifecycleScore = 0.0
    }

    $stageScoreMap = [ordered]@{}
    $stageHitMap = [ordered]@{}
    $stageSummary = @()
    foreach ($stageName in @($stageKeywordMap.Keys)) {
        $stageKeywords = @($stageKeywordMap[$stageName])
        $hits = @()
        foreach ($kw in $stageKeywords) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $score = Get-KeywordRatio -PromptLower $PromptLower -Keywords $stageKeywords
        $stageScoreMap[[string]$stageName] = [Math]::Round([double]$score, 4)
        $stageHitMap[[string]$stageName] = @($hits)
        $stageSummary += [pscustomobject]@{
            stage = [string]$stageName
            score = [double]$score
            hits = @($hits)
        }
    }

    $topStage = $stageSummary | Sort-Object -Property @(
        @{ Expression = "score"; Descending = $true },
        @{ Expression = "stage"; Descending = $false }
    ) | Select-Object -First 1
    $stageDetected = if ($topStage -and ([double]$topStage.score -gt 0.0)) { [string]$topStage.stage } else { "none" }

    $requiredChecksByStage = [ordered]@{
        develop = @("code_tests", "data_tests")
        evaluate = @("data_tests", "model_tests", "baseline_compare")
        deploy = @("code_tests", "data_tests", "model_tests", "baseline_compare", "service_smoke")
        iterate = @("monitoring_metrics", "drift_guard", "retraining_plan")
    }
    if ($MlLifecycleOverlayPolicy.required_checks_by_stage) {
        $requiredChecksByStage = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.required_checks_by_stage.PSObject.Properties.Name)) {
            $requiredChecksByStage[[string]$stageName] = @($MlLifecycleOverlayPolicy.required_checks_by_stage.$stageName)
        }
    }

    $artifactsByStage = [ordered]@{
        develop = @("dataset_version")
        evaluate = @("run_id", "evaluation_results", "baseline_compare")
        deploy = @("run_id", "evaluation_results", "baseline_compare", "service_smoke")
        iterate = @("monitoring_metrics", "retraining_plan")
    }
    if ($MlLifecycleOverlayPolicy.artifacts_required_by_stage) {
        $artifactsByStage = [ordered]@{}
        foreach ($stageName in @($MlLifecycleOverlayPolicy.artifacts_required_by_stage.PSObject.Properties.Name)) {
            $artifactsByStage[[string]$stageName] = @($MlLifecycleOverlayPolicy.artifacts_required_by_stage.$stageName)
        }
    }

    $artifactHits = [ordered]@{}
    foreach ($artifactName in @($artifactKeywordMap.Keys)) {
        $hits = @()
        foreach ($kw in @($artifactKeywordMap[$artifactName])) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
                $hits += [string]$kw
            }
        }
        $artifactHits[[string]$artifactName] = @($hits)
    }

    $requiredChecks = @()
    $artifactsRequired = @()
    if ($stageDetected -ne "none") {
        if ($requiredChecksByStage.Contains($stageDetected)) {
            $requiredChecks = @($requiredChecksByStage[$stageDetected])
        }
        if ($artifactsByStage.Contains($stageDetected)) {
            $artifactsRequired = @($artifactsByStage[$stageDetected])
        }
    }

    $missingArtifacts = @()
    foreach ($artifactName in $artifactsRequired) {
        $hits = @()
        if ($artifactHits.Contains([string]$artifactName)) {
            $hits = @($artifactHits[[string]$artifactName])
        }
        if ($hits.Count -eq 0) {
            $missingArtifacts += [string]$artifactName
        }
    }
    $missingArtifactRatio = if ($artifactsRequired.Count -gt 0) {
        [double]$missingArtifacts.Count / [double]$artifactsRequired.Count
    } else {
        0.0
    }
    $missingArtifactRatio = [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $missingArtifactRatio)), 4)

    $deployReadiness = "not_applicable"
    if ($scopeApplicable -and ($stageDetected -in @("evaluate", "deploy", "iterate"))) {
        if (($missingArtifacts.Count -eq 0) -and ($lifecycleScore -ge $confirmSignalMin)) {
            $deployReadiness = "ready"
        } elseif (($missingArtifacts.Count -gt 0) -and ($lifecycleScore -ge $confirmSignalMin)) {
            $deployReadiness = "needs_confirmation"
        } else {
            $deployReadiness = "blocked"
        }
    }

    $lifecycleLikelihood = "none"
    if ($lifecycleScore -ge $highSignalMin) {
        $lifecycleLikelihood = "high"
    } elseif ($lifecycleScore -ge $confirmSignalMin) {
        $lifecycleLikelihood = "medium"
    } elseif ($lifecycleScore -gt 0) {
        $lifecycleLikelihood = "low"
    }

    $confirmRecommended = (
        $scopeApplicable -and
        ($lifecycleScore -ge $confirmSignalMin) -and
        (
            ($stageDetected -in @("evaluate", "deploy", "iterate")) -or
            ($missingArtifactRatio -ge $missingArtifactRatioForConfirm)
        )
    )

    $strictGrades = @("L", "XL")
    $strictTasks = @("planning", "coding", "review")
    $strictStages = @("evaluate", "deploy", "iterate")
    if ($MlLifecycleOverlayPolicy.strict_confirm_scope) {
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.grades) {
            $strictGrades = @($MlLifecycleOverlayPolicy.strict_confirm_scope.grades)
        }
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.task_types) {
            $strictTasks = @($MlLifecycleOverlayPolicy.strict_confirm_scope.task_types)
        }
        if ($MlLifecycleOverlayPolicy.strict_confirm_scope.stages) {
            $strictStages = @($MlLifecycleOverlayPolicy.strict_confirm_scope.stages)
        }
    }
    $strictScopeApplied = (
        ($strictGrades -contains $Grade) -and
        ($strictTasks -contains $TaskType) -and
        ($strictStages -contains $stageDetected)
    )

    $confirmRequired = (
        $scopeApplicable -and
        ($mode -eq "strict") -and
        $strictScopeApplied -and
        ($lifecycleScore -ge $confirmSignalMin) -and
        ($missingArtifacts.Count -gt 0)
    )

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                $enforcement = "advisory"
                if ($confirmRecommended) {
                    $reason = "soft_lifecycle_confirm_recommended"
                } else {
                    $reason = "soft_advisory"
                }
            }
            "strict" {
                if ($confirmRequired) {
                    $enforcement = "confirm_required"
                    $reason = "strict_missing_lifecycle_evidence"
                } else {
                    $enforcement = "advisory"
                    $reason = "strict_advisory"
                }
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $recommendedFollowup = $null
    if ($scopeApplicable -and ($lifecycleScore -gt 0.0)) {
        switch ($stageDetected) {
            "develop" { $recommendedFollowup = "Establish dataset versioning and run code/data checks before broad model training." }
            "evaluate" { $recommendedFollowup = "Attach run_id + evaluation report + baseline comparison before approval." }
            "deploy" { $recommendedFollowup = "Complete deployment readiness package: run_id, evaluation, baseline, and service smoke evidence." }
            "iterate" { $recommendedFollowup = "Attach monitoring metrics and retraining policy to close the continual-learning loop." }
            default { $recommendedFollowup = "Use an ML lifecycle checklist (code/data/model tests + experiment artifacts) before handoff." }
        }
    }

    $externalEnabled = $false
    $externalCommand = $null
    $externalInvokeMode = "disabled"
    $externalRunModes = @("soft", "strict")
    $externalSignalMin = $confirmSignalMin
    $manualCommandHint = $null
    if ($MlLifecycleOverlayPolicy.external_analyzer) {
        if ($MlLifecycleOverlayPolicy.external_analyzer.enabled -ne $null) {
            $externalEnabled = [bool]$MlLifecycleOverlayPolicy.external_analyzer.enabled
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.command) {
            $externalCommand = [string]$MlLifecycleOverlayPolicy.external_analyzer.command
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.invoke_mode) {
            $externalInvokeMode = [string]$MlLifecycleOverlayPolicy.external_analyzer.invoke_mode
        } elseif ($externalEnabled) {
            $externalInvokeMode = "manual_only"
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.run_in_modes) {
            $externalRunModes = @($MlLifecycleOverlayPolicy.external_analyzer.run_in_modes)
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.signal_score_min -ne $null) {
            $externalSignalMin = [double]$MlLifecycleOverlayPolicy.external_analyzer.signal_score_min
        }
        if ($MlLifecycleOverlayPolicy.external_analyzer.manual_command_hint) {
            $manualCommandHint = [string]$MlLifecycleOverlayPolicy.external_analyzer.manual_command_hint
        }
    }
    if (-not $manualCommandHint -and $externalCommand) {
        $manualCommandHint = "$externalCommand ui --host 127.0.0.1 --port 5000"
    }

    $externalStatus = "disabled"
    $externalToolAvailable = $false
    $externalShouldInvoke = $false
    if ($scopeApplicable -and $externalEnabled) {
        if (-not ($externalRunModes -contains $mode)) {
            $externalStatus = "skipped_mode"
        } elseif ($lifecycleScore -lt $externalSignalMin) {
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
        lifecycle_signal_score = [Math]::Round([double]$lifecycleScore, 4)
        lifecycle_likelihood = $lifecycleLikelihood
        lifecycle_keyword_hits = @($signalMatches)
        suppress_keyword_hits = @($suppressMatches)
        stage_detected = $stageDetected
        stage_scores = [pscustomobject]$stageScoreMap
        stage_hits = [pscustomobject]$stageHitMap
        required_checks = @($requiredChecks)
        artifacts_required = @($artifactsRequired)
        artifact_hits = [pscustomobject]$artifactHits
        missing_artifacts = @($missingArtifacts)
        missing_artifact_ratio = [double]$missingArtifactRatio
        deploy_readiness = $deployReadiness
        confirm_recommended = $confirmRecommended
        confirm_required = $confirmRequired
        strict_scope_applied = $strictScopeApplied
        should_apply_hook = ($scopeApplicable -and (($lifecycleScore -gt 0.0) -or $confirmRequired))
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


