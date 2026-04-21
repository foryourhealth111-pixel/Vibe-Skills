# Prompt Asset Boost Overlay (GPT‑5.2 assisted)
#
# Purpose:
# - When a prompt-template intent is detected, generate a prompts.chat search plan
#   and a small set of "prompt overlay candidates" that the user can confirm
#   and inject into subsequent tool prompts.
#
# Boundaries:
# - Advice-only (never changes selected pack/skill by default).
# - Explicit vibe only by default (requires `$vibe` or `/vibe` prefix).
# - Designed to cooperate with `prompt_overlay_advice` rather than replace it.

function Get-PromptAssetBoostPolicyDefaults {
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
            require_prompt_signal = $true
            require_explicit_intent = $false
            max_queries = 5
            max_candidates = 3
        }
        provider = [pscustomobject]@{
            type = "openai" # openai|mock
            model = "your-model-id"
            base_url = ""
            mock_response_path = ""
            timeout_ms = 9000
            max_output_tokens = 1200
            temperature = 0.2
            top_p = 1.0
            store = $false
        }
        output = [pscustomobject]@{
            max_prompt_chars_per_candidate = 1200
        }
        safety = [pscustomobject]@{
            fallback_on_error = $true
        }
    }
}

function Get-PromptAssetBoostPolicy {
    param([object]$Policy)

    $defaults = Get-PromptAssetBoostPolicyDefaults
    if (-not $Policy) { return $defaults }

    $enabled = if ($Policy.enabled -ne $null) { [bool]$Policy.enabled } else { [bool]$defaults.enabled }
    $mode = if ($Policy.mode) { [string]$Policy.mode } else { [string]$defaults.mode }
    $activation = if ($Policy.activation) { $Policy.activation } else { $defaults.activation }
    $scope = if ($Policy.scope) { $Policy.scope } else { $defaults.scope }
    $trigger = if ($Policy.trigger) { $Policy.trigger } else { $defaults.trigger }
    $provider = if ($Policy.provider) { $Policy.provider } else { $defaults.provider }
    $output = if ($Policy.output) { $Policy.output } else { $defaults.output }
    $safety = if ($Policy.safety) { $Policy.safety } else { $defaults.safety }

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
            require_prompt_signal = if ($trigger.require_prompt_signal -ne $null) { [bool]$trigger.require_prompt_signal } else { [bool]$defaults.trigger.require_prompt_signal }
            require_explicit_intent = if ($trigger.require_explicit_intent -ne $null) { [bool]$trigger.require_explicit_intent } else { [bool]$defaults.trigger.require_explicit_intent }
            max_queries = if ($trigger.max_queries -ne $null) { [int]$trigger.max_queries } else { [int]$defaults.trigger.max_queries }
            max_candidates = if ($trigger.max_candidates -ne $null) { [int]$trigger.max_candidates } else { [int]$defaults.trigger.max_candidates }
        }
        provider = [pscustomobject]@{
            type = if ($provider.type) { [string]$provider.type } else { [string]$defaults.provider.type }
            model = if ($provider.model) { [string]$provider.model } else { [string]$defaults.provider.model }
            base_url = if ($provider.base_url) { [string]$provider.base_url } else { [string]$defaults.provider.base_url }
            mock_response_path = if ($provider.mock_response_path) { [string]$provider.mock_response_path } else { [string]$defaults.provider.mock_response_path }
            timeout_ms = if ($provider.timeout_ms -ne $null) { [int]$provider.timeout_ms } else { [int]$defaults.provider.timeout_ms }
            max_output_tokens = if ($provider.max_output_tokens -ne $null) { [int]$provider.max_output_tokens } else { [int]$defaults.provider.max_output_tokens }
            temperature = if ($provider.temperature -ne $null) { [double]$provider.temperature } else { [double]$defaults.provider.temperature }
            top_p = if ($provider.top_p -ne $null) { [double]$provider.top_p } else { [double]$defaults.provider.top_p }
            store = if ($provider.store -ne $null) { [bool]$provider.store } else { [bool]$defaults.provider.store }
        }
        output = [pscustomobject]@{
            max_prompt_chars_per_candidate = if ($output.max_prompt_chars_per_candidate -ne $null) { [int]$output.max_prompt_chars_per_candidate } else { [int]$defaults.output.max_prompt_chars_per_candidate }
        }
        safety = [pscustomobject]@{
            fallback_on_error = if ($safety.fallback_on_error -ne $null) { [bool]$safety.fallback_on_error } else { [bool]$defaults.safety.fallback_on_error }
        }
    }
}

function Test-PromptAssetBoostScope {
    param(
        [object]$Policy,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode
    )

    $resolved = Get-PromptAssetBoostPolicy -Policy $Policy
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

    $scopeApplicable = ($reasons.Count -eq 0)

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        scope_applicable = $scopeApplicable
        reasons = @($reasons)
    }
}

function Get-PromptAssetBoostJsonSchema {
    param(
        [int]$MaxQueries = 5,
        [int]$MaxCandidates = 3,
        [int]$MaxPromptCharsPerCandidate = 1200
    )

    $qMax = [Math]::Max(1, [Math]::Min(8, [int]$MaxQueries))
    $cMax = [Math]::Max(1, [Math]::Min(3, [int]$MaxCandidates))
    $pMax = [Math]::Max(200, [Math]::Min(2000, [int]$MaxPromptCharsPerCandidate))

    return [ordered]@{
        type = "object"
        additionalProperties = $false
        required = @("search_plan", "overlay_candidates")
        properties = [ordered]@{
            search_plan = [ordered]@{
                type = "object"
                additionalProperties = $false
                required = @("queries")
                properties = [ordered]@{
                    queries = [ordered]@{
                        type = "array"
                        maxItems = $qMax
                        items = [ordered]@{ type = "string"; maxLength = 120 }
                    }
                    category_hints = [ordered]@{
                        type = "array"
                        maxItems = 4
                        items = [ordered]@{ type = "string"; maxLength = 40 }
                    }
                    tag_hints = [ordered]@{
                        type = "array"
                        maxItems = 8
                        items = [ordered]@{ type = "string"; maxLength = 40 }
                    }
                    type_hints = [ordered]@{
                        type = "array"
                        maxItems = 4
                        items = [ordered]@{ type = "string"; enum = @("TEXT", "STRUCTURED", "IMAGE", "VIDEO", "AUDIO") }
                    }
                    limit = [ordered]@{
                        type = "integer"
                        minimum = 1
                        maximum = 50
                    }
                }
            }
            overlay_candidates = [ordered]@{
                type = "array"
                maxItems = $cMax
                items = [ordered]@{
                    type = "object"
                    additionalProperties = $false
                    required = @("id", "title", "role", "prompt", "when_to_use")
                    properties = [ordered]@{
                        id = [ordered]@{ type = "string"; maxLength = 24 }
                        title = [ordered]@{ type = "string"; maxLength = 80 }
                        role = [ordered]@{ type = "string"; enum = @("system", "user") }
                        prompt = [ordered]@{ type = "string"; maxLength = $pMax }
                        when_to_use = [ordered]@{ type = "string"; maxLength = 220 }
                        variables = [ordered]@{
                            type = "array"
                            maxItems = 12
                            items = [ordered]@{ type = "string"; maxLength = 40 }
                        }
                        confidence = [ordered]@{
                            type = "number"
                            minimum = 0
                            maximum = 1
                        }
                    }
                }
            }
            confirm_questions = [ordered]@{
                type = "array"
                maxItems = 6
                items = [ordered]@{ type = "string"; maxLength = 140 }
            }
            rationale = [ordered]@{
                type = "string"
                maxLength = 480
            }
        }
    }
}

function New-PromptAssetBoostInputText {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [object]$PromptOverlayAdvice,
        [int]$MaxQueries,
        [int]$MaxCandidates,
        [int]$MaxPromptCharsPerCandidate
    )

    $normalized = if ($PromptNormalization -and $PromptNormalization.normalized) { [string]$PromptNormalization.normalized } else { $PromptText }

    $facetMatches = $null
    $matchedFacets = @()
    $promptSignalHit = $false
    $docSurfaceHit = $false
    try {
        if ($PromptOverlayAdvice) {
            $promptSignalHit = [bool]$PromptOverlayAdvice.prompt_signal_hit
            $docSurfaceHit = [bool]$PromptOverlayAdvice.doc_surface_hit
            $matchedFacets = @($PromptOverlayAdvice.matched_intent_facets)
            $facetMatches = $PromptOverlayAdvice.facet_matches
        }
    } catch { }

    $ctx = [ordered]@{
        vco = [ordered]@{
            grade = $Grade
            task_type = $TaskType
            route_mode = $RouteMode
            selected_pack = if ($SelectedPackId) { $SelectedPackId } else { "none" }
            selected_skill = if ($SelectedSkill) { $SelectedSkill } else { "none" }
        }
        prompt = [ordered]@{
            original = $PromptText
            normalized = $normalized
        }
        prompt_overlay_signals = [ordered]@{
            prompt_signal_hit = [bool]$promptSignalHit
            doc_surface_hit = [bool]$docSurfaceHit
            matched_intent_facets = @($matchedFacets)
            facet_matches = if ($facetMatches) { $facetMatches } else { [pscustomobject]@{} }
        }
        constraints = [ordered]@{
            max_queries = [int]$MaxQueries
            max_candidates = [int]$MaxCandidates
            max_prompt_chars_per_candidate = [int]$MaxPromptCharsPerCandidate
        }
    }

    $json = ($ctx | ConvertTo-Json -Depth 12 -Compress)

    $text = @()
    $text += "You generate prompts.chat search plans and small prompt overlay candidates."
    $text += "Return ONLY JSON that matches the JSON Schema. No markdown. No extra keys."
    $text += ""
    $text += "Guidelines:"
    $text += "- Queries should be short and directly searchable (keywords, not long sentences)."
    $text += "- Candidates must be safe to inject as a system/user prompt (no tool calls)."
    $text += "- Keep each candidate prompt concise; prefer variables like {project}, {goal}."
    $text += ""
    $text += "Context JSON:"
    $text += $json

    return ($text -join "`n")
}

function Invoke-PromptAssetBoostProvider {
    param(
        [object]$PolicyResolved,
        [string]$RepoRoot,
        [string]$InputText,
        [object]$Schema
    )

    $providerType = if ($PolicyResolved -and $PolicyResolved.provider -and $PolicyResolved.provider.type) { [string]$PolicyResolved.provider.type } else { "openai" }

    if ($providerType -eq "mock") {
        $mockRel = if ($PolicyResolved.provider.mock_response_path) { [string]$PolicyResolved.provider.mock_response_path } else { "" }
        if (-not $mockRel) {
            return [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "mock_missing_path"
                api = "mock"
                latency_ms = 0
                output_text = $null
                error = $null
            }
        }

        $base = if ($RepoRoot) { [string]$RepoRoot } else { "" }
        $path = if ([System.IO.Path]::IsPathRooted($mockRel)) { $mockRel } else { if ($base) { Join-Path $base $mockRel } else { $mockRel } }
        if (-not (Test-Path -LiteralPath $path)) {
            return [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "mock_file_not_found"
                api = "mock"
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
            api = "mock"
            latency_ms = 0
            output_text = $raw
            error = $null
        }
    }

    if ($providerType -ne "openai") {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "unsupported_provider"
            api = "none"
            latency_ms = 0
            output_text = $null
            error = $null
        }
    }

    if (-not (Get-OpenAiApiKey)) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_openai_api_key"
            api = "none"
            latency_ms = 0
            output_text = $null
            error = $null
        }
    }

    $model = if ($PolicyResolved.provider.model) { [string]$PolicyResolved.provider.model } else { "your-model-id" }
    $baseUrl = if ($PolicyResolved.provider.base_url) { [string]$PolicyResolved.provider.base_url } else { "" }
    $timeoutMsSafe = [Math]::Max(500, [int]$PolicyResolved.provider.timeout_ms)
    $maxTokens = [int]$PolicyResolved.provider.max_output_tokens
    $temperature = [double]$PolicyResolved.provider.temperature
    $topP = [double]$PolicyResolved.provider.top_p
    $store = [bool]$PolicyResolved.provider.store

    $textFormat = [ordered]@{
        type = "json_schema"
        name = "vco_prompt_asset_boost"
        strict = $true
        schema = $Schema
    }

    $inputItems = @(
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

    $chatResponseFormat = [ordered]@{
        type = "json_schema"
        json_schema = [ordered]@{
            name = "vco_prompt_asset_boost"
            strict = $true
            schema = $Schema
        }
    }

    $chatMessages = @(
        [ordered]@{ role = "system"; content = $instructions },
        [ordered]@{ role = "user"; content = $InputText }
    )

    $preferChat = $false
    if ($baseUrl -and ($baseUrl -notmatch "openai\\.com")) { $preferChat = $true }

    $invokeResponses = {
        $r = Invoke-OpenAiResponsesCreate `
            -Model $model `
            -BaseUrl $baseUrl `
            -InputItems $inputItems `
            -TextFormat $textFormat `
            -Instructions $instructions `
            -MaxOutputTokens $maxTokens `
            -Temperature $temperature `
            -TopP $topP `
            -TimeoutMs $timeoutMsSafe `
            -Store:([bool]$store)
        $r | Add-Member -NotePropertyName api -NotePropertyValue "responses" -Force
        return $r
    }

    $invokeChat = {
        $r = Invoke-OpenAiChatCompletionsCreate `
            -Model $model `
            -BaseUrl $baseUrl `
            -Messages $chatMessages `
            -ResponseFormat $chatResponseFormat `
            -MaxTokens $maxTokens `
            -Temperature $temperature `
            -TopP $topP `
            -TimeoutMs $timeoutMsSafe
        $r | Add-Member -NotePropertyName api -NotePropertyValue "chat_completions" -Force
        return $r
    }

    $providerResult = $null
    if ($preferChat) {
        $providerResult = & $invokeChat
        if (-not ([bool]$providerResult.ok -and (-not [bool]$providerResult.abstained) -and $providerResult.output_text)) {
            $providerResult = & $invokeResponses
        }
    } else {
        $providerResult = & $invokeResponses
        if (-not ([bool]$providerResult.ok -and (-not [bool]$providerResult.abstained) -and $providerResult.output_text)) {
            if ([string]$providerResult.reason -ne "missing_openai_api_key") {
                $providerResult = & $invokeChat
            }
        }
    }

    if (-not $providerResult -or -not [bool]$providerResult.ok -or [bool]$providerResult.abstained -or (-not $providerResult.output_text)) {
        $reason = if ($providerResult -and $providerResult.reason) { [string]$providerResult.reason } else { "provider_abstained" }
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = $reason
            api = if ($providerResult -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
            latency_ms = if ($providerResult -and $providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            output_text = $null
            error = if ($providerResult -and $providerResult.error) { [string]$providerResult.error } else { $null }
        }
    }

    return [pscustomobject]@{
        ok = $true
        abstained = $false
        reason = "ok"
        api = if ($providerResult.api) { [string]$providerResult.api } else { "unknown" }
        latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
        output_text = [string]$providerResult.output_text
        error = $null
    }
}

function Get-PromptAssetBoostAdvice {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [object]$PromptOverlayAdvice,
        [object]$PromptAssetBoostPolicy,
        [string]$RepoRoot
    )

    if (-not $PromptAssetBoostPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            should_apply_hook = $false
            prompt_signal_hit = [bool]($PromptOverlayAdvice -and $PromptOverlayAdvice.prompt_signal_hit)
            explicit_intent = [bool]($PromptOverlayAdvice -and @($PromptOverlayAdvice.matched_intent_facets).Count -gt 0)
            recommended_skill = $null
            confirm_required = $false
            search_plan = $null
            overlay_candidates = @()
            provider = [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "policy_missing"
                api = "none"
                latency_ms = 0
                error = $null
            }
        }
    }

    $resolved = Get-PromptAssetBoostPolicy -Policy $PromptAssetBoostPolicy
    $scope = Test-PromptAssetBoostScope -Policy $resolved -PromptNormalization $PromptNormalization -Grade $Grade -TaskType $TaskType -RouteMode $RouteMode

    if (-not [bool]$scope.enabled -or -not [bool]$scope.scope_applicable) {
        return [pscustomobject]@{
            enabled = $false
            mode = [string]$scope.mode
            scope_applicable = $false
            enforcement = "none"
            reason = if ($scope.reasons -and $scope.reasons.Count -gt 0) { ($scope.reasons -join ",") } else { "outside_scope" }
            preserve_routing_assignment = $true
            should_apply_hook = $false
            prompt_signal_hit = [bool]($PromptOverlayAdvice -and $PromptOverlayAdvice.prompt_signal_hit)
            explicit_intent = [bool]($PromptOverlayAdvice -and @($PromptOverlayAdvice.matched_intent_facets).Count -gt 0)
            recommended_skill = $null
            confirm_required = $false
            search_plan = $null
            overlay_candidates = @()
            provider = [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "outside_scope"
                api = "none"
                latency_ms = 0
                error = $null
            }
        }
    }

    $mode = [string]$scope.mode
    $promptSignalHit = [bool]($PromptOverlayAdvice -and $PromptOverlayAdvice.prompt_signal_hit)
    $explicitIntent = [bool]($PromptOverlayAdvice -and @($PromptOverlayAdvice.matched_intent_facets).Count -gt 0)

    $triggerReasons = @()
    if ([bool]$resolved.trigger.require_prompt_signal -and (-not ($promptSignalHit -or $explicitIntent))) {
        $triggerReasons += "missing_prompt_signal"
    }
    if ([bool]$resolved.trigger.require_explicit_intent -and (-not $explicitIntent)) {
        $triggerReasons += "missing_explicit_intent"
    }

    if ($triggerReasons.Count -gt 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            scope_applicable = $true
            enforcement = "advisory"
            reason = ($triggerReasons -join ",")
            preserve_routing_assignment = $true
            should_apply_hook = $false
            prompt_signal_hit = $promptSignalHit
            explicit_intent = $explicitIntent
            recommended_skill = $null
            confirm_required = $false
            search_plan = $null
            overlay_candidates = @()
            provider = [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = ($triggerReasons -join ",")
                api = "none"
                latency_ms = 0
                error = $null
            }
        }
    }

    $enforcement = "advisory"
    $reason = "soft_advisory"
    switch ($mode) {
        "shadow" {
            $enforcement = "advisory"
            $reason = "shadow_advisory"
        }
        "soft" {
            $enforcement = "advisory"
            $reason = "soft_advisory"
        }
        "strict" {
            $enforcement = "required"
            $reason = "strict_required"
        }
        default {
            $enforcement = "advisory"
            $reason = "unknown_mode_advisory"
        }
    }

    $recommendedSkill = "prompt-lookup"
    $shouldApplyHook = $true

    if ($mode -eq "shadow") {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            scope_applicable = $true
            enforcement = $enforcement
            reason = $reason
            preserve_routing_assignment = $true
            should_apply_hook = $shouldApplyHook
            prompt_signal_hit = $promptSignalHit
            explicit_intent = $explicitIntent
            recommended_skill = $recommendedSkill
            confirm_required = $false
            search_plan = $null
            overlay_candidates = @()
            provider = [pscustomobject]@{
                ok = $false
                abstained = $true
                reason = "shadow_mode_no_provider"
                api = "none"
                latency_ms = 0
                error = $null
            }
        }
    }

    $maxQueries = [Math]::Max(1, [Math]::Min(8, [int]$resolved.trigger.max_queries))
    $maxCandidates = [Math]::Max(1, [Math]::Min(3, [int]$resolved.trigger.max_candidates))
    $maxPromptChars = [Math]::Max(200, [Math]::Min(2000, [int]$resolved.output.max_prompt_chars_per_candidate))

    $schema = Get-PromptAssetBoostJsonSchema -MaxQueries $maxQueries -MaxCandidates $maxCandidates -MaxPromptCharsPerCandidate $maxPromptChars
    $inputText = New-PromptAssetBoostInputText `
        -PromptText $PromptText `
        -PromptNormalization $PromptNormalization `
        -Grade $Grade `
        -TaskType $TaskType `
        -RouteMode $RouteMode `
        -SelectedPackId $SelectedPackId `
        -SelectedSkill $SelectedSkill `
        -PromptOverlayAdvice $PromptOverlayAdvice `
        -MaxQueries $maxQueries `
        -MaxCandidates $maxCandidates `
        -MaxPromptCharsPerCandidate $maxPromptChars

    $provider = Invoke-PromptAssetBoostProvider -PolicyResolved $resolved -RepoRoot $RepoRoot -InputText $inputText -Schema $schema

    $searchPlan = $null
    $candidates = @()
    $confirmQuestions = @()
    $rationale = $null

    if ([bool]$provider.ok -and $provider.output_text) {
        try {
            $obj = ($provider.output_text.Trim() | ConvertFrom-Json)
            if ($obj -and $obj.search_plan) { $searchPlan = $obj.search_plan }
            if ($obj -and $obj.overlay_candidates) { $candidates = @($obj.overlay_candidates) }
            if ($obj -and $obj.confirm_questions) { $confirmQuestions = @($obj.confirm_questions) }
            if ($obj -and $obj.rationale) { $rationale = [string]$obj.rationale }
        } catch {
        }
    }

    $cleanCandidates = @()
    foreach ($c in @($candidates | Select-Object -First $maxCandidates)) {
        if (-not $c) { continue }
        $prompt = if ($c.prompt) { [string]$c.prompt } else { "" }
        if ($prompt.Length -gt $maxPromptChars) { $prompt = $prompt.Substring(0, $maxPromptChars) }
        if (-not $prompt.Trim()) { continue }

        $cleanCandidates += [pscustomobject]@{
            id = if ($c.id) { [string]$c.id } else { "candidate_{0}" -f ($cleanCandidates.Count + 1) }
            title = if ($c.title) { [string]$c.title } else { "Prompt Candidate {0}" -f ($cleanCandidates.Count + 1) }
            role = if ($c.role) { [string]$c.role } else { "system" }
            prompt = $prompt.Trim()
            when_to_use = if ($c.when_to_use) { [string]$c.when_to_use } else { "" }
            variables = if ($c.variables) { Get-ArraySafe -Value $c.variables } else { Get-ArraySafe -Value $null }
            confidence = if ($c.confidence -ne $null) { [double]$c.confidence } else { 0.55 }
        }
    }

    $confirmRequired = ($cleanCandidates.Count -gt 0)

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        scope_applicable = $true
        enforcement = $enforcement
        reason = if ([bool]$provider.ok) { $reason } else { "provider_abstained" }
        preserve_routing_assignment = $true
        should_apply_hook = $shouldApplyHook
        prompt_signal_hit = $promptSignalHit
        explicit_intent = $explicitIntent
        recommended_skill = $recommendedSkill
        confirm_required = $confirmRequired
        search_plan = $searchPlan
        overlay_candidates = @($cleanCandidates)
        confirm_questions = @($confirmQuestions | Where-Object { $_ } | Select-Object -First 6)
        rationale = if ($rationale) { $rationale.Trim() } else { $null }
        provider = [pscustomobject]@{
            ok = [bool]$provider.ok
            abstained = [bool]$provider.abstained
            reason = [string]$provider.reason
            api = [string]$provider.api
            latency_ms = [int]$provider.latency_ms
            error = if ($provider.error) { [string]$provider.error } else { $null }
        }
    }
}
