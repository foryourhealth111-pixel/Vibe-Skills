# LLM Acceleration Overlay (GPT‑5.2 via OpenAI Responses API)
#
# Goals:
# - Only runs when user explicitly invokes /vibe or $vibe (prefix_detected).
# - Advice-first: safe abstain when API is unavailable.
# - Optional: promote confirm_required in soft/strict (does not change selected pack by default).

function Get-LlmAccelerationPolicyDefaults {
    return [pscustomobject]@{
        enabled = $false
        mode = "off" # off|shadow|soft|strict
        activation = [pscustomobject]@{
            explicit_vibe_only = $true
        }
        scope = [pscustomobject]@{
            grade_allow = @("M", "L", "XL")
            task_allow = @("planning", "coding", "review", "debug", "research")
            route_mode_allow = @("legacy_fallback", "confirm_required", "pack_overlay")
        }
        trigger = [pscustomobject]@{
            top_k = 3
            always_on_explicit_vibe = $false
            max_top1_top2_gap = 0.08
            max_confidence_for_llm = 0.55
        }
        provider = [pscustomobject]@{
            type = "openai" # openai|mock
            model = "gpt-5.2-codex"
            timeout_ms = 2500
            max_output_tokens = 900
            temperature = 0.2
            top_p = 1.0
            store = $false
            mock_response_path = ""
        }
        context = [pscustomobject]@{
            mode = "prompt_only" # none|prompt_only|diff_snippets_ok
            include_git_status = $true
            include_git_diff = $true
            max_git_status_lines = 80
            max_diff_chars = 9000
        }
        safety = [pscustomobject]@{
            fallback_on_error = $true
            require_candidate_in_top_k = $true
            min_override_confidence = 0.75
            allow_confirm_escalation = $true
            allow_route_override = $false
        }
        rollout = [pscustomobject]@{
            apply_in_modes = @("soft", "strict")
            max_live_apply_rate = 1.0
        }
    }
}

function Get-LlmAccelerationPolicy {
    param([object]$Policy)

    $defaults = Get-LlmAccelerationPolicyDefaults
    if (-not $Policy) { return $defaults }

    $enabled = if ($Policy.enabled -ne $null) { [bool]$Policy.enabled } else { [bool]$defaults.enabled }
    $mode = if ($Policy.mode) { [string]$Policy.mode } else { [string]$defaults.mode }
    $activation = if ($Policy.activation) { $Policy.activation } else { $defaults.activation }
    $scope = if ($Policy.scope) { $Policy.scope } else { $defaults.scope }
    $trigger = if ($Policy.trigger) { $Policy.trigger } else { $defaults.trigger }
    $provider = if ($Policy.provider) { $Policy.provider } else { $defaults.provider }
    $context = if ($Policy.context) { $Policy.context } else { $defaults.context }
    $safety = if ($Policy.safety) { $Policy.safety } else { $defaults.safety }
    $rollout = if ($Policy.rollout) { $Policy.rollout } else { $defaults.rollout }

    return [pscustomobject]@{
        enabled = $enabled
        mode = $mode
        activation = [pscustomobject]@{
            explicit_vibe_only = if ($activation.explicit_vibe_only -ne $null) { [bool]$activation.explicit_vibe_only } else { [bool]$defaults.activation.explicit_vibe_only }
        }
        scope = [pscustomobject]@{
            grade_allow = if ($scope.grade_allow) { @($scope.grade_allow) } else { @($defaults.scope.grade_allow) }
            task_allow = if ($scope.task_allow) { @($scope.task_allow) } else { @($defaults.scope.task_allow) }
            route_mode_allow = if ($scope.route_mode_allow) { @($scope.route_mode_allow) } else { @($defaults.scope.route_mode_allow) }
        }
        trigger = [pscustomobject]@{
            top_k = if ($trigger.top_k -ne $null) { [int]$trigger.top_k } else { [int]$defaults.trigger.top_k }
            always_on_explicit_vibe = if ($trigger.always_on_explicit_vibe -ne $null) { [bool]$trigger.always_on_explicit_vibe } else { [bool]$defaults.trigger.always_on_explicit_vibe }
            max_top1_top2_gap = if ($trigger.max_top1_top2_gap -ne $null) { [double]$trigger.max_top1_top2_gap } else { [double]$defaults.trigger.max_top1_top2_gap }
            max_confidence_for_llm = if ($trigger.max_confidence_for_llm -ne $null) { [double]$trigger.max_confidence_for_llm } else { [double]$defaults.trigger.max_confidence_for_llm }
        }
        provider = [pscustomobject]@{
            type = if ($provider.type) { [string]$provider.type } else { [string]$defaults.provider.type }
            model = if ($provider.model) { [string]$provider.model } else { [string]$defaults.provider.model }
            timeout_ms = if ($provider.timeout_ms -ne $null) { [int]$provider.timeout_ms } else { [int]$defaults.provider.timeout_ms }
            max_output_tokens = if ($provider.max_output_tokens -ne $null) { [int]$provider.max_output_tokens } else { [int]$defaults.provider.max_output_tokens }
            temperature = if ($provider.temperature -ne $null) { [double]$provider.temperature } else { [double]$defaults.provider.temperature }
            top_p = if ($provider.top_p -ne $null) { [double]$provider.top_p } else { [double]$defaults.provider.top_p }
            store = if ($provider.store -ne $null) { [bool]$provider.store } else { [bool]$defaults.provider.store }
            mock_response_path = if ($provider.mock_response_path) { [string]$provider.mock_response_path } else { [string]$defaults.provider.mock_response_path }
        }
        context = [pscustomobject]@{
            mode = if ($context.mode) { [string]$context.mode } else { [string]$defaults.context.mode }
            include_git_status = if ($context.include_git_status -ne $null) { [bool]$context.include_git_status } else { [bool]$defaults.context.include_git_status }
            include_git_diff = if ($context.include_git_diff -ne $null) { [bool]$context.include_git_diff } else { [bool]$defaults.context.include_git_diff }
            max_git_status_lines = if ($context.max_git_status_lines -ne $null) { [int]$context.max_git_status_lines } else { [int]$defaults.context.max_git_status_lines }
            max_diff_chars = if ($context.max_diff_chars -ne $null) { [int]$context.max_diff_chars } else { [int]$defaults.context.max_diff_chars }
        }
        safety = [pscustomobject]@{
            fallback_on_error = if ($safety.fallback_on_error -ne $null) { [bool]$safety.fallback_on_error } else { [bool]$defaults.safety.fallback_on_error }
            require_candidate_in_top_k = if ($safety.require_candidate_in_top_k -ne $null) { [bool]$safety.require_candidate_in_top_k } else { [bool]$defaults.safety.require_candidate_in_top_k }
            min_override_confidence = if ($safety.min_override_confidence -ne $null) { [double]$safety.min_override_confidence } else { [double]$defaults.safety.min_override_confidence }
            allow_confirm_escalation = if ($safety.allow_confirm_escalation -ne $null) { [bool]$safety.allow_confirm_escalation } else { [bool]$defaults.safety.allow_confirm_escalation }
            allow_route_override = if ($safety.allow_route_override -ne $null) { [bool]$safety.allow_route_override } else { [bool]$defaults.safety.allow_route_override }
        }
        rollout = [pscustomobject]@{
            apply_in_modes = if ($rollout.apply_in_modes) { @($rollout.apply_in_modes) } else { @($defaults.rollout.apply_in_modes) }
            max_live_apply_rate = if ($rollout.max_live_apply_rate -ne $null) { [double]$rollout.max_live_apply_rate } else { [double]$defaults.rollout.max_live_apply_rate }
        }
    }
}

function Test-LlmAccelerationScope {
    param(
        [object]$Policy,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode
    )

    $resolved = Get-LlmAccelerationPolicy -Policy $Policy
    if (-not $resolved.enabled) {
        return [pscustomobject]@{ enabled = $false; mode = "off"; scope_applicable = $false; reasons = @("policy_disabled") }
    }

    $mode = if ($resolved.mode) { [string]$resolved.mode } else { "off" }
    if ($mode -eq "off") {
        return [pscustomobject]@{ enabled = $false; mode = "off"; scope_applicable = $false; reasons = @("mode_off") }
    }

    $reasons = @()

    if ($resolved.activation.explicit_vibe_only) {
        $prefixDetected = [bool]($PromptNormalization -and $PromptNormalization.prefix_detected)
        if (-not $prefixDetected) {
            $reasons += "explicit_vibe_only"
        }
    }

    if ($resolved.scope.grade_allow.Count -gt 0 -and -not ($resolved.scope.grade_allow -contains $Grade)) { $reasons += "grade_not_allowed" }
    if ($resolved.scope.task_allow.Count -gt 0 -and -not ($resolved.scope.task_allow -contains $TaskType)) { $reasons += "task_not_allowed" }
    if ($resolved.scope.route_mode_allow.Count -gt 0 -and -not ($resolved.scope.route_mode_allow -contains $RouteMode)) { $reasons += "route_mode_not_allowed" }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        scope_applicable = ($reasons.Count -eq 0)
        reasons = if ($reasons.Count -eq 0) { @("scope_match") } else { @($reasons) }
    }
}

function Get-LlmAccelerationTrigger {
    param(
        [object]$PolicyResolved,
        [string]$RouteMode,
        [double]$TopGap,
        [double]$Confidence
    )

    $trigger = $PolicyResolved.trigger
    $reasons = @()

    if ([bool]$trigger.always_on_explicit_vibe) {
        $reasons += "always_on"
    } else {
        if ($RouteMode -eq "confirm_required") { $reasons += "route_mode_confirm_required" }
        if ($TopGap -le [double]$trigger.max_top1_top2_gap) { $reasons += "top_gap_low" }
        if ($Confidence -le [double]$trigger.max_confidence_for_llm) { $reasons += "confidence_low" }
    }

    return [pscustomobject]@{
        active = ($reasons.Count -gt 0)
        reasons = @($reasons | Select-Object -Unique)
        top_k = [int]$trigger.top_k
    }
}

function Get-VcoGitContextSnippet {
    param(
        [object]$PolicyResolved
    )

    $contextMode = if ($PolicyResolved -and $PolicyResolved.context -and $PolicyResolved.context.mode) { [string]$PolicyResolved.context.mode } else { "none" }
    if ($contextMode -eq "none") {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false }
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false }
    }

    $repoRoot = $null
    try {
        $repoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
    } catch { }
    if (-not $repoRoot) {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false }
    }

    $statusText = $null
    $diffText = $null
    $diffTruncated = $false

    if ([bool]$PolicyResolved.context.include_git_status) {
        try {
            $maxLines = [Math]::Max(10, [int]$PolicyResolved.context.max_git_status_lines)
            $lines = @(git status --porcelain=v1 2>$null | Select-Object -First $maxLines)
            if ($lines.Count -gt 0) { $statusText = ($lines -join "`n").TrimEnd() }
        } catch { }
    }

    if ($contextMode -eq "diff_snippets_ok" -and [bool]$PolicyResolved.context.include_git_diff) {
        try {
            $raw = (git diff --patch --unified=0 2>$null | Out-String)
            $raw = $raw.TrimEnd()
            $limit = [Math]::Max(1000, [int]$PolicyResolved.context.max_diff_chars)
            if ($raw.Length -gt $limit) {
                $diffText = $raw.Substring(0, $limit)
                $diffTruncated = $true
            } else {
                $diffText = $raw
            }
        } catch { }
    }

    return [pscustomobject]@{
        git_present = $true
        repo_root = $repoRoot
        status = $statusText
        diff = $diffText
        diff_truncated = [bool]$diffTruncated
    }
}

function Get-LlmAccelerationJsonSchema {
    $schema = [ordered]@{
        type = "object"
        additionalProperties = $false
        required = @("abstain", "confidence", "confirm_required", "confirm_questions", "rerank", "qa")
        properties = [ordered]@{
            abstain = [ordered]@{ type = "boolean" }
            confidence = [ordered]@{ type = "number"; minimum = 0; maximum = 1 }
            confirm_required = [ordered]@{ type = "boolean" }
            confirm_questions = [ordered]@{
                type = "array"
                maxItems = 3
                items = [ordered]@{ type = "string" }
            }
            rerank = [ordered]@{
                type = "object"
                additionalProperties = $false
                required = @("abstain", "suggested_pack_id", "suggested_skill", "confidence", "reason")
                properties = [ordered]@{
                    abstain = [ordered]@{ type = "boolean" }
                    suggested_pack_id = [ordered]@{ type = @("string", "null") }
                    suggested_skill = [ordered]@{ type = @("string", "null") }
                    confidence = [ordered]@{ type = "number"; minimum = 0; maximum = 1 }
                    reason = [ordered]@{ type = "string" }
                }
            }
            qa = [ordered]@{
                type = "object"
                additionalProperties = $false
                required = @("recommendations")
                properties = [ordered]@{
                    recommendations = [ordered]@{
                        type = "array"
                        maxItems = 8
                        items = [ordered]@{ type = "string" }
                    }
                    focus = [ordered]@{
                        type = "array"
                        maxItems = 6
                        items = [ordered]@{ type = "string" }
                    }
                }
            }
            notes = [ordered]@{ type = "string" }
        }
    }

    return $schema
}

function New-LlmAccelerationInputText {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$RouteReason,
        [object[]]$Ranked,
        [int]$TopK,
        [object]$GitContext
    )

    $rankedTop = @()
    if ($Ranked) {
        foreach ($row in @($Ranked | Select-Object -First ([Math]::Max(1, $TopK)))) {
            $rankedTop += [ordered]@{
                pack_id = [string]$row.pack_id
                score = if ($row.score -ne $null) { [double]$row.score } else { 0.0 }
                selected_candidate = if ($row.selected_candidate) { [string]$row.selected_candidate } else { $null }
                candidate_top1_top2_gap = if ($row.candidate_top1_top2_gap -ne $null) { [double]$row.candidate_top1_top2_gap } else { 0.0 }
                candidates = @($row.candidates | Select-Object -First 12)
            }
        }
    }

    $context = [ordered]@{
        vco = [ordered]@{
            grade = $Grade
            task_type = $TaskType
            route_mode = $RouteMode
            route_reason = $RouteReason
            prompt_prefix_detected = [bool]($PromptNormalization -and $PromptNormalization.prefix_detected)
        }
        prompt = [ordered]@{
            original = $PromptText
            normalized = if ($PromptNormalization -and $PromptNormalization.normalized) { [string]$PromptNormalization.normalized } else { $PromptText }
        }
        top_candidates = $rankedTop
        git = [ordered]@{
            present = [bool]($GitContext -and $GitContext.git_present)
            status = if ($GitContext) { $GitContext.status } else { $null }
            diff = if ($GitContext) { $GitContext.diff } else { $null }
            diff_truncated = if ($GitContext) { [bool]$GitContext.diff_truncated } else { $false }
        }
    }

    $json = ($context | ConvertTo-Json -Depth 12 -Compress)

    $text = @()
    $text += "You are generating VCO LLM Acceleration advice."
    $text += ""
    $text += "Constraints:"
    $text += "- Output MUST be valid JSON that matches the provided JSON Schema."
    $text += "- If you suggest a pack/skill override, it MUST be one of the provided top_candidates pack_id and skill candidates."
    $text += "- If unsure, set abstain=true and rerank.abstain=true."
    $text += "- Always include QA recommendations (testing department can help at any stage)."
    $text += ""
    $text += "Context(JSON):"
    $text += $json

    return ($text -join "`n")
}

function Invoke-LlmAccelerationProvider {
    param(
        [object]$PolicyResolved,
        [string]$RepoRoot,
        [string]$InputText
    )

    $providerType = if ($PolicyResolved -and $PolicyResolved.provider -and $PolicyResolved.provider.type) { [string]$PolicyResolved.provider.type } else { "openai" }

    if ($providerType -eq "mock") {
        $mockRel = if ($PolicyResolved.provider.mock_response_path) { [string]$PolicyResolved.provider.mock_response_path } else { "" }
        if (-not $mockRel) {
            return [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "mock_missing_path"
                latency_ms = 0
                output_text = $null
                error = $null
            }
        }

        $path = if ([System.IO.Path]::IsPathRooted($mockRel)) { $mockRel } else { Join-Path $RepoRoot $mockRel }
        if (-not (Test-Path -LiteralPath $path)) {
            return [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "mock_file_not_found"
                latency_ms = 0
                output_text = $null
                error = $path
            }
        }

        $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        return [pscustomobject]@{
            ok = $true
            abstained = $false
            reason = "mock_ok"
            latency_ms = 0
            output_text = $raw
            error = $null
        }
    }

    $schema = Get-LlmAccelerationJsonSchema
    $textFormat = [ordered]@{
        type = "json_schema"
        name = "vco_llm_acceleration"
        strict = $true
        schema = $schema
    }

    $input = @(
        [ordered]@{
            role = "user"
            content = @(
                [ordered]@{
                    type = "input_text"
                    text = $InputText
                }
            )
        }
    )

    $instructions = "Return ONLY JSON that matches the JSON Schema. No markdown. No extra keys."

    return Invoke-OpenAiResponsesCreate `
        -Model ([string]$PolicyResolved.provider.model) `
        -Input $input `
        -TextFormat $textFormat `
        -Instructions $instructions `
        -MaxOutputTokens ([int]$PolicyResolved.provider.max_output_tokens) `
        -Temperature ([double]$PolicyResolved.provider.temperature) `
        -TopP ([double]$PolicyResolved.provider.top_p) `
        -TimeoutMs ([int]$PolicyResolved.provider.timeout_ms) `
        -Store:([bool]$PolicyResolved.provider.store)
}

function Get-DeterministicSampleValueForLlm {
    param([string]$SeedText)
    return Get-DeterministicSampleValue -SeedText $SeedText
}

function Get-LlmAccelerationAdvice {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$RouteReason,
        [object[]]$Ranked,
        [double]$TopGap,
        [double]$Confidence,
        [object]$LlmAccelerationPolicy,
        [string]$RepoRoot
    )

    $policyResolved = Get-LlmAccelerationPolicy -Policy $LlmAccelerationPolicy
    $scope = Test-LlmAccelerationScope -Policy $policyResolved -PromptNormalization $PromptNormalization -Grade $Grade -TaskType $TaskType -RouteMode $RouteMode
    $trigger = Get-LlmAccelerationTrigger -PolicyResolved $policyResolved -RouteMode $RouteMode -TopGap $TopGap -Confidence $Confidence

    $providerSummary = [pscustomobject]@{
        type = [string]$policyResolved.provider.type
        model = [string]$policyResolved.provider.model
        abstained = $true
        reason = "not_invoked"
        latency_ms = 0
        error = $null
    }

    $parsed = $null
    $parseError = $null

    if (-not [bool]$scope.scope_applicable) {
        return [pscustomobject]@{
            enabled = [bool]$scope.enabled
            mode = [string]$scope.mode
            scope_applicable = $false
            scope_reasons = @($scope.reasons)
            trigger_active = $false
            trigger_reasons = @()
            provider = $providerSummary
            abstained = $true
            reason = "outside_scope"
            confirm_required = $false
            confirm_questions = @()
            qa_recommendations = @()
            confidence = 0.0
            override_target_pack = $null
            override_target_skill = $null
            would_override = $false
            route_override_applied = $false
            parse_error = $null
        }
    }

    $topK = [Math]::Max(1, [int]$trigger.top_k)
    $gitContext = Get-VcoGitContextSnippet -PolicyResolved $policyResolved

    if ([bool]$trigger.active) {
        $inputText = New-LlmAccelerationInputText `
            -PromptText $PromptText `
            -PromptNormalization $PromptNormalization `
            -Grade $Grade `
            -TaskType $TaskType `
            -RouteMode $RouteMode `
            -RouteReason $RouteReason `
            -Ranked $Ranked `
            -TopK $topK `
            -GitContext $gitContext

        $providerResult = Invoke-LlmAccelerationProvider -PolicyResolved $policyResolved -RepoRoot $RepoRoot -InputText $inputText

        $providerSummary = [pscustomobject]@{
            type = [string]$policyResolved.provider.type
            model = [string]$policyResolved.provider.model
            abstained = [bool]$providerResult.abstained
            reason = [string]$providerResult.reason
            latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            error = if ($providerResult.error) { [string]$providerResult.error } else { $null }
        }

        if (-not [bool]$providerResult.abstained -and $providerResult.output_text) {
            try {
                $parsed = ($providerResult.output_text.Trim() | ConvertFrom-Json)
            } catch {
                $parseError = $_.Exception.Message
                $parsed = $null
            }
        }
    }

    $abstained = $true
    $reason = "no_result"
    $confirmRequired = $false
    $confirmQuestions = @()
    $qaRecommendations = @()
    $overridePack = $null
    $overrideSkill = $null
    $suggestionConfidence = 0.0

    if ($parsed) {
        $abstained = [bool]$parsed.abstain
        $reason = if ($parsed.notes) { "model_notes" } else { "model_output" }
        $confirmRequired = [bool]$parsed.confirm_required
        $confirmQuestions = @($parsed.confirm_questions | Where-Object { $_ } | Select-Object -First 3)
        $qaRecommendations = @($parsed.qa.recommendations | Where-Object { $_ } | Select-Object -First 8)

        if ($parsed.rerank -and -not [bool]$parsed.rerank.abstain) {
            $overridePack = if ($parsed.rerank.suggested_pack_id) { [string]$parsed.rerank.suggested_pack_id } else { $null }
            $overrideSkill = if ($parsed.rerank.suggested_skill) { [string]$parsed.rerank.suggested_skill } else { $null }
            $suggestionConfidence = if ($parsed.rerank.confidence -ne $null) { [double]$parsed.rerank.confidence } else { 0.0 }
            $suggestionConfidence = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.0, $suggestionConfidence)), 4)
        }
    } elseif ($parseError) {
        $reason = "parse_error"
    } elseif (-not $trigger.active) {
        $reason = "trigger_inactive"
    } elseif ($providerSummary.reason -ne "ok") {
        $reason = "provider_abstained"
    }

    $topPackIds = @()
    if ($Ranked) {
        $topPackIds = @($Ranked | Select-Object -First $topK | ForEach-Object { [string]$_.pack_id })
    }

    $constraintsPassed = $false
    if ($overridePack -and (-not $abstained)) {
        $inTopK = (-not $policyResolved.safety.require_candidate_in_top_k) -or ($topPackIds -contains $overridePack)
        $confidencePassed = ([double]$suggestionConfidence -ge [double]$policyResolved.safety.min_override_confidence)
        $constraintsPassed = $inTopK -and $confidencePassed
    }

    $mode = [string]$policyResolved.mode
    $applyModes = @($policyResolved.rollout.apply_in_modes)
    $applyModeAllowed = ($applyModes -contains $mode)
    $sampleRate = [Math]::Max(0.0, [Math]::Min(1.0, [double]$policyResolved.rollout.max_live_apply_rate))
    $sampleSeed = "{0}|{1}|{2}|{3}|{4}" -f $PromptText, $Grade, $TaskType, $RouteMode, $mode
    $sampleValue = Get-DeterministicSampleValueForLlm -SeedText $sampleSeed
    $samplePassed = ($sampleValue -le $sampleRate)

    $allowRouteOverride = [bool]$policyResolved.safety.allow_route_override
    $applyEligible = $allowRouteOverride -and $applyModeAllowed -and $samplePassed -and $constraintsPassed
    $wouldOverride = $false
    if ($mode -eq "shadow" -and $constraintsPassed) {
        $wouldOverride = $true
    } elseif ($applyEligible) {
        $wouldOverride = $true
    }

    $routeOverrideApplied = $applyEligible

    return [pscustomobject]@{
        enabled = [bool]$scope.enabled
        mode = [string]$scope.mode
        scope_applicable = $true
        scope_reasons = @($scope.reasons)
        trigger_active = [bool]$trigger.active
        trigger_reasons = @($trigger.reasons)
        provider = $providerSummary
        abstained = [bool]$abstained
        reason = [string]$reason
        confirm_required = if ([bool]$policyResolved.safety.allow_confirm_escalation) { [bool]$confirmRequired } else { $false }
        confirm_questions = @($confirmQuestions)
        qa_recommendations = @($qaRecommendations)
        confidence = [double]$suggestionConfidence
        constraints = [pscustomobject]@{
            top_k = [int]$topK
            require_candidate_in_top_k = [bool]$policyResolved.safety.require_candidate_in_top_k
            in_top_k = if ($overridePack) { [bool]($topPackIds -contains $overridePack) } else { $false }
            min_override_confidence = [double]$policyResolved.safety.min_override_confidence
            confidence_passed = ([double]$suggestionConfidence -ge [double]$policyResolved.safety.min_override_confidence)
            passed = [bool]$constraintsPassed
        }
        rollout = [pscustomobject]@{
            apply_mode_allowed = [bool]$applyModeAllowed
            sample_rate = [Math]::Round([double]$sampleRate, 4)
            sample_value = [Math]::Round([double]$sampleValue, 6)
            sample_passed = [bool]$samplePassed
            apply_eligible = [bool]$applyEligible
            would_override = [bool]$wouldOverride
            route_override_applied = [bool]$routeOverrideApplied
        }
        override_target_pack = $overridePack
        override_target_skill = $overrideSkill
        would_override = [bool]$wouldOverride
        route_override_applied = [bool]$routeOverrideApplied
        parse_error = $parseError
    }
}
