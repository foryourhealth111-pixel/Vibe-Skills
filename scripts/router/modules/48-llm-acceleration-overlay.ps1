# LLM Acceleration Overlay (structured advice via compatible provider APIs)
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
            type = "openai" # openai|openai-compatible|anthropic|anthropic-compatible|mock
            model = ""
            model_env = "VCO_INTENT_ADVICE_MODEL"
            base_url = ""
            base_url_env_candidates = @("VCO_INTENT_ADVICE_BASE_URL")
            api_key_env = "VCO_INTENT_ADVICE_API_KEY"
            timeout_ms = 2500
            max_output_tokens = 900
            temperature = 0.2
            top_p = 1.0
            store = $false
            mock_response_path = ""
        }
        enhancements = [pscustomobject]@{
            diff_digest = [pscustomobject]@{
                enabled = $false
                min_diff_chars = 1800
                max_digest_chars = 1200
                model = ""
                max_output_tokens = 520
                temperature = 0.1
                timeout_ms = 8000
                replace_diff_in_context = $true
                include_raw_diff_in_context = $false
            }
            committee = [pscustomobject]@{
                enabled = $false
                members = 3
                min_success_members = 2
                member_temperatures = @()
                member_max_output_tokens = 1400
                member_timeout_ms = 12000
                judge_enabled = $true
                judge_temperature = 0.05
                judge_max_output_tokens = 1600
                judge_timeout_ms = 12000
            }
            confirm_question_booster = [pscustomobject]@{
                enabled = $false
                only_when_confirm_required = $true
                max_questions = 3
                max_output_tokens = 340
                temperature = 0.1
                timeout_ms = 6000
            }
        }
        context = [pscustomobject]@{
            mode = "prompt_only" # none|prompt_only|diff_snippets_ok
            include_git_status = $true
            include_git_diff = $true
            max_git_status_lines = 80
            max_diff_chars = 9000
            git_diff_task_allow = @("coding", "debug", "review")
            vector_diff = [pscustomobject]@{
                enabled = $false
                embedding_model = ""
                embedding_model_env = "VCO_VECTOR_DIFF_MODEL"
                embedding_provider = [pscustomobject]@{
                    type = "openai" # openai|openai-compatible
                    base_url = ""
                    base_url_env_candidates = @("VCO_VECTOR_DIFF_BASE_URL")
                    endpoint_path = ""
                    api_key_env = "VCO_VECTOR_DIFF_API_KEY"
                    timeout_ms = 6000
                }
                min_diff_chars_for_vector = 6000
                max_chunks = 12
                chunk_max_chars = 1400
                max_selected_chunks = 3
                cache_relpath = "outputs/runtime/llm-accel-vector-cache.jsonl"
                max_cache_entries = 250
                max_cache_file_kb = 8192
            }
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

function Get-VcoFirstNonEmptyEnvValue {
    param([string[]]$Names)

    foreach ($name in @($Names)) {
        if (-not $name) { continue }
        $value = [Environment]::GetEnvironmentVariable([string]$name)
        if (-not [string]::IsNullOrWhiteSpace([string]$value)) {
            return [string]$value
        }
    }

    return $null
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
    $enhancements = if ($Policy.enhancements) { $Policy.enhancements } else { $defaults.enhancements }
    $context = if ($Policy.context) { $Policy.context } else { $defaults.context }
    $safety = if ($Policy.safety) { $Policy.safety } else { $defaults.safety }
    $rollout = if ($Policy.rollout) { $Policy.rollout } else { $defaults.rollout }
    $vectorDiff = if ($context -and $context.vector_diff) { $context.vector_diff } else { $defaults.context.vector_diff }
    $embeddingProvider = if ($vectorDiff -and $vectorDiff.embedding_provider) { $vectorDiff.embedding_provider } else { $defaults.context.vector_diff.embedding_provider }
    $diffDigest = if ($enhancements -and $enhancements.diff_digest) { $enhancements.diff_digest } else { $defaults.enhancements.diff_digest }
    $committee = if ($enhancements -and $enhancements.committee) { $enhancements.committee } else { $defaults.enhancements.committee }
    $confirmBoost = if ($enhancements -and $enhancements.confirm_question_booster) { $enhancements.confirm_question_booster } else { $defaults.enhancements.confirm_question_booster }

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
            model = if ($provider.model) { [string]$provider.model } else {
                $modelEnvName = if ($provider.model_env) { [string]$provider.model_env } else { [string]$defaults.provider.model_env }
                $modelFromEnv = Get-VcoFirstNonEmptyEnvValue -Names @($modelEnvName)
                if ($modelFromEnv) { [string]$modelFromEnv } else { [string]$defaults.provider.model }
            }
            model_env = if ($provider.model_env) { [string]$provider.model_env } else { [string]$defaults.provider.model_env }
            base_url = if ($provider.base_url) { [string]$provider.base_url } else {
                $baseUrlEnvCandidates = if ($provider.base_url_env_candidates) { @($provider.base_url_env_candidates) } else { @($defaults.provider.base_url_env_candidates) }
                $baseUrlFromEnv = Get-VcoFirstNonEmptyEnvValue -Names $baseUrlEnvCandidates
                if ($baseUrlFromEnv) { [string]$baseUrlFromEnv } else { [string]$defaults.provider.base_url }
            }
            base_url_env_candidates = if ($provider.base_url_env_candidates) { @($provider.base_url_env_candidates) } else { @($defaults.provider.base_url_env_candidates) }
            api_key_env = if ($provider.api_key_env) { [string]$provider.api_key_env } else { [string]$defaults.provider.api_key_env }
            timeout_ms = if ($provider.timeout_ms -ne $null) { [int]$provider.timeout_ms } else { [int]$defaults.provider.timeout_ms }
            max_output_tokens = if ($provider.max_output_tokens -ne $null) { [int]$provider.max_output_tokens } else { [int]$defaults.provider.max_output_tokens }
            temperature = if ($provider.temperature -ne $null) { [double]$provider.temperature } else { [double]$defaults.provider.temperature }
            top_p = if ($provider.top_p -ne $null) { [double]$provider.top_p } else { [double]$defaults.provider.top_p }
            store = if ($provider.store -ne $null) { [bool]$provider.store } else { [bool]$defaults.provider.store }
            mock_response_path = if ($provider.mock_response_path) { [string]$provider.mock_response_path } else { [string]$defaults.provider.mock_response_path }
        }
        enhancements = [pscustomobject]@{
            diff_digest = [pscustomobject]@{
                enabled = if ($diffDigest.enabled -ne $null) { [bool]$diffDigest.enabled } else { [bool]$defaults.enhancements.diff_digest.enabled }
                min_diff_chars = if ($diffDigest.min_diff_chars -ne $null) { [int]$diffDigest.min_diff_chars } else { [int]$defaults.enhancements.diff_digest.min_diff_chars }
                max_digest_chars = if ($diffDigest.max_digest_chars -ne $null) { [int]$diffDigest.max_digest_chars } else { [int]$defaults.enhancements.diff_digest.max_digest_chars }
                model = if ($diffDigest.model -ne $null) { [string]$diffDigest.model } else { [string]$defaults.enhancements.diff_digest.model }
                max_output_tokens = if ($diffDigest.max_output_tokens -ne $null) { [int]$diffDigest.max_output_tokens } else { [int]$defaults.enhancements.diff_digest.max_output_tokens }
                temperature = if ($diffDigest.temperature -ne $null) { [double]$diffDigest.temperature } else { [double]$defaults.enhancements.diff_digest.temperature }
                timeout_ms = if ($diffDigest.timeout_ms -ne $null) { [int]$diffDigest.timeout_ms } else { [int]$defaults.enhancements.diff_digest.timeout_ms }
                replace_diff_in_context = if ($diffDigest.replace_diff_in_context -ne $null) { [bool]$diffDigest.replace_diff_in_context } else { [bool]$defaults.enhancements.diff_digest.replace_diff_in_context }
                include_raw_diff_in_context = if ($diffDigest.include_raw_diff_in_context -ne $null) { [bool]$diffDigest.include_raw_diff_in_context } else { [bool]$defaults.enhancements.diff_digest.include_raw_diff_in_context }
            }
            committee = [pscustomobject]@{
                enabled = if ($committee.enabled -ne $null) { [bool]$committee.enabled } else { [bool]$defaults.enhancements.committee.enabled }
                members = if ($committee.members -ne $null) { [int]$committee.members } else { [int]$defaults.enhancements.committee.members }
                min_success_members = if ($committee.min_success_members -ne $null) { [int]$committee.min_success_members } else { [int]$defaults.enhancements.committee.min_success_members }
                member_temperatures = if ($committee.member_temperatures) { @($committee.member_temperatures) } else { @($defaults.enhancements.committee.member_temperatures) }
                member_max_output_tokens = if ($committee.member_max_output_tokens -ne $null) { [int]$committee.member_max_output_tokens } else { [int]$defaults.enhancements.committee.member_max_output_tokens }
                member_timeout_ms = if ($committee.member_timeout_ms -ne $null) { [int]$committee.member_timeout_ms } else { [int]$defaults.enhancements.committee.member_timeout_ms }
                judge_enabled = if ($committee.judge_enabled -ne $null) { [bool]$committee.judge_enabled } else { [bool]$defaults.enhancements.committee.judge_enabled }
                judge_temperature = if ($committee.judge_temperature -ne $null) { [double]$committee.judge_temperature } else { [double]$defaults.enhancements.committee.judge_temperature }
                judge_max_output_tokens = if ($committee.judge_max_output_tokens -ne $null) { [int]$committee.judge_max_output_tokens } else { [int]$defaults.enhancements.committee.judge_max_output_tokens }
                judge_timeout_ms = if ($committee.judge_timeout_ms -ne $null) { [int]$committee.judge_timeout_ms } else { [int]$defaults.enhancements.committee.judge_timeout_ms }
            }
            confirm_question_booster = [pscustomobject]@{
                enabled = if ($confirmBoost.enabled -ne $null) { [bool]$confirmBoost.enabled } else { [bool]$defaults.enhancements.confirm_question_booster.enabled }
                only_when_confirm_required = if ($confirmBoost.only_when_confirm_required -ne $null) { [bool]$confirmBoost.only_when_confirm_required } else { [bool]$defaults.enhancements.confirm_question_booster.only_when_confirm_required }
                max_questions = if ($confirmBoost.max_questions -ne $null) { [int]$confirmBoost.max_questions } else { [int]$defaults.enhancements.confirm_question_booster.max_questions }
                max_output_tokens = if ($confirmBoost.max_output_tokens -ne $null) { [int]$confirmBoost.max_output_tokens } else { [int]$defaults.enhancements.confirm_question_booster.max_output_tokens }
                temperature = if ($confirmBoost.temperature -ne $null) { [double]$confirmBoost.temperature } else { [double]$defaults.enhancements.confirm_question_booster.temperature }
                timeout_ms = if ($confirmBoost.timeout_ms -ne $null) { [int]$confirmBoost.timeout_ms } else { [int]$defaults.enhancements.confirm_question_booster.timeout_ms }
            }
        }
        context = [pscustomobject]@{
            mode = if ($context.mode) { [string]$context.mode } else { [string]$defaults.context.mode }
            include_git_status = if ($context.include_git_status -ne $null) { [bool]$context.include_git_status } else { [bool]$defaults.context.include_git_status }
            include_git_diff = if ($context.include_git_diff -ne $null) { [bool]$context.include_git_diff } else { [bool]$defaults.context.include_git_diff }
            max_git_status_lines = if ($context.max_git_status_lines -ne $null) { [int]$context.max_git_status_lines } else { [int]$defaults.context.max_git_status_lines }
            max_diff_chars = if ($context.max_diff_chars -ne $null) { [int]$context.max_diff_chars } else { [int]$defaults.context.max_diff_chars }
            git_diff_task_allow = if ($context -and ($context.PSObject.Properties.Name -contains 'git_diff_task_allow')) { @($context.git_diff_task_allow) } else { @($defaults.context.git_diff_task_allow) }
            vector_diff = [pscustomobject]@{
                enabled = if ($vectorDiff -and $vectorDiff.enabled -ne $null) { [bool]$vectorDiff.enabled } else { [bool]$defaults.context.vector_diff.enabled }
                embedding_model = if ($vectorDiff -and $vectorDiff.embedding_model) { [string]$vectorDiff.embedding_model } else {
                    $embeddingModelEnv = if ($vectorDiff -and $vectorDiff.embedding_model_env) { [string]$vectorDiff.embedding_model_env } else { [string]$defaults.context.vector_diff.embedding_model_env }
                    $embeddingModelFromEnv = Get-VcoFirstNonEmptyEnvValue -Names @($embeddingModelEnv)
                    if ($embeddingModelFromEnv) { [string]$embeddingModelFromEnv } else { [string]$defaults.context.vector_diff.embedding_model }
                }
                embedding_model_env = if ($vectorDiff -and $vectorDiff.embedding_model_env) { [string]$vectorDiff.embedding_model_env } else { [string]$defaults.context.vector_diff.embedding_model_env }
                embedding_provider = [pscustomobject]@{
                    type = if ($embeddingProvider -and $embeddingProvider.type) { [string]$embeddingProvider.type } else { [string]$defaults.context.vector_diff.embedding_provider.type }
                    base_url = if ($embeddingProvider -and $embeddingProvider.base_url) { [string]$embeddingProvider.base_url } else {
                        $embeddingBaseUrlEnvCandidates = if ($embeddingProvider -and $embeddingProvider.base_url_env_candidates) { @($embeddingProvider.base_url_env_candidates) } else { @($defaults.context.vector_diff.embedding_provider.base_url_env_candidates) }
                        $embeddingBaseUrlFromEnv = Get-VcoFirstNonEmptyEnvValue -Names $embeddingBaseUrlEnvCandidates
                        if ($embeddingBaseUrlFromEnv) { [string]$embeddingBaseUrlFromEnv } else { [string]$defaults.context.vector_diff.embedding_provider.base_url }
                    }
                    base_url_env_candidates = if ($embeddingProvider -and $embeddingProvider.base_url_env_candidates) { @($embeddingProvider.base_url_env_candidates) } else { @($defaults.context.vector_diff.embedding_provider.base_url_env_candidates) }
                    endpoint_path = if ($embeddingProvider -and $embeddingProvider.endpoint_path) { [string]$embeddingProvider.endpoint_path } else { [string]$defaults.context.vector_diff.embedding_provider.endpoint_path }
                    api_key_env = if ($embeddingProvider -and $embeddingProvider.api_key_env) { [string]$embeddingProvider.api_key_env } else { [string]$defaults.context.vector_diff.embedding_provider.api_key_env }
                    timeout_ms = if ($embeddingProvider -and $embeddingProvider.timeout_ms -ne $null) { [int]$embeddingProvider.timeout_ms } else { [int]$defaults.context.vector_diff.embedding_provider.timeout_ms }
                }
                min_diff_chars_for_vector = if ($vectorDiff -and $vectorDiff.min_diff_chars_for_vector -ne $null) { [int]$vectorDiff.min_diff_chars_for_vector } else { [int]$defaults.context.vector_diff.min_diff_chars_for_vector }
                max_chunks = if ($vectorDiff -and $vectorDiff.max_chunks -ne $null) { [int]$vectorDiff.max_chunks } else { [int]$defaults.context.vector_diff.max_chunks }
                chunk_max_chars = if ($vectorDiff -and $vectorDiff.chunk_max_chars -ne $null) { [int]$vectorDiff.chunk_max_chars } else { [int]$defaults.context.vector_diff.chunk_max_chars }
                max_selected_chunks = if ($vectorDiff -and $vectorDiff.max_selected_chunks -ne $null) { [int]$vectorDiff.max_selected_chunks } else { [int]$defaults.context.vector_diff.max_selected_chunks }
                cache_relpath = if ($vectorDiff -and $vectorDiff.cache_relpath) { [string]$vectorDiff.cache_relpath } else { [string]$defaults.context.vector_diff.cache_relpath }
                max_cache_entries = if ($vectorDiff -and $vectorDiff.max_cache_entries -ne $null) { [int]$vectorDiff.max_cache_entries } else { [int]$defaults.context.vector_diff.max_cache_entries }
                max_cache_file_kb = if ($vectorDiff -and $vectorDiff.max_cache_file_kb -ne $null) { [int]$vectorDiff.max_cache_file_kb } else { [int]$defaults.context.vector_diff.max_cache_file_kb }
            }
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

function Get-VcoTextSha256Hex {
    param([string]$Text)

    if ($null -eq $Text) { return $null }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }

    return ([System.BitConverter]::ToString($hashBytes)).Replace("-", "").ToLowerInvariant()
}

function Get-VcoEvenlySpacedIndices {
    param(
        [int]$Count,
        [int]$MaxItems
    )

    if ($Count -le 0 -or $MaxItems -le 0) { return @() }
    if ($Count -le $MaxItems) { return @(0..($Count - 1)) }

    $indices = @()
    $step = ([double]$Count / [double]$MaxItems)
    for ($i = 0; $i -lt $MaxItems; $i++) {
        $idx = [int][Math]::Floor($i * $step)
        if ($idx -ge $Count) { $idx = $Count - 1 }
        $indices += $idx
    }

    return @($indices | Select-Object -Unique)
}

function Split-VcoGitDiffIntoVectorChunks {
    param(
        [string]$DiffText,
        [int]$MaxChunks,
        [int]$ChunkMaxChars
    )

    if (-not $DiffText) { return @() }

    $maxChunksSafe = [Math]::Max(1, [int]$MaxChunks)
    $chunkMaxSafe = [Math]::Max(200, [int]$ChunkMaxChars)

    $lines = @(([string]$DiffText) -split "`n")
    $fileHeader = @()
    $current = @()
    $chunks = @()

    foreach ($line in $lines) {
        if ($line -match '^diff --git ') {
            if ($current.Count -gt 0) {
                $chunks += ($current -join "`n")
                $current = @()
            }
            $fileHeader = @($line)
            continue
        }

        if ($line -match '^(index |--- |\+\+\+ |new file mode|deleted file mode|similarity index|rename from|rename to|Binary files )') {
            $fileHeader += $line
            continue
        }

        if ($line -match '^@@') {
            if ($current.Count -gt 0) {
                $chunks += ($current -join "`n")
            }

            $current = @()
            if ($fileHeader.Count -gt 0) { $current += $fileHeader }
            $current += $line
            continue
        }

        if ($current.Count -gt 0) {
            $current += $line
        } else {
            if ($line) { $fileHeader += $line }
        }
    }

    if ($current.Count -gt 0) { $chunks += ($current -join "`n") }
    if ($chunks.Count -eq 0 -and $fileHeader.Count -gt 0) { $chunks += ($fileHeader -join "`n") }

    $clean = @()
    foreach ($chunk in $chunks) {
        if (-not $chunk) { continue }
        $text = ([string]$chunk).TrimEnd()
        if (-not $text) { continue }
        if ($text.Length -gt $chunkMaxSafe) { $text = $text.Substring(0, $chunkMaxSafe) }
        $clean += $text
    }

    if ($clean.Count -le $maxChunksSafe) { return @($clean) }

    $indices = Get-VcoEvenlySpacedIndices -Count $clean.Count -MaxItems $maxChunksSafe
    $selected = @()
    foreach ($i in $indices) {
        if ($i -ge 0 -and $i -lt $clean.Count) {
            $selected += $clean[$i]
        }
    }

    return @($selected)
}

function Get-VcoVectorCachePath {
    param(
        [string]$VcoRepoRoot,
        [string]$CacheRelPath
    )

    if (-not $VcoRepoRoot -or -not $CacheRelPath) { return $null }

    if ([System.IO.Path]::IsPathRooted($CacheRelPath)) {
        return $CacheRelPath
    }

    return (Join-Path $VcoRepoRoot $CacheRelPath)
}

function Read-VcoVectorCache {
    param(
        [string]$CachePath,
        [int]$MaxEntries
    )

    $table = @{}
    if (-not $CachePath) { return $table }
    if (-not (Test-Path -LiteralPath $CachePath)) { return $table }

    try {
        $tail = [Math]::Max(1, [int]$MaxEntries)
        $lines = @(Get-Content -LiteralPath $CachePath -Tail $tail -ErrorAction Stop)
        foreach ($line in $lines) {
            if (-not $line) { continue }

            $obj = $null
            try { $obj = ($line | ConvertFrom-Json) } catch { }
            if (-not $obj) { continue }

            $model = if ($obj.model) { [string]$obj.model } else { $null }
            $sha = if ($obj.sha256) { [string]$obj.sha256 } else { $null }
            $embedding = $obj.embedding

            if ($model -and $sha -and $embedding) {
                $key = "{0}|{1}" -f $model, $sha
                $table[$key] = @($embedding)
            }
        }
    } catch { }

    return $table
}

function Append-VcoVectorCacheEntries {
    param(
        [string]$CachePath,
        [object[]]$Entries,
        [int]$MaxEntries,
        [int]$MaxFileKb
    )

    if (-not $CachePath -or -not $Entries -or $Entries.Count -eq 0) { return }

    try {
        $dir = Split-Path -Parent $CachePath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }

        foreach ($entry in $Entries) {
            $line = ($entry | ConvertTo-Json -Depth 20 -Compress)
            Add-Content -LiteralPath $CachePath -Value $line -Encoding UTF8
        }

        $maxEntriesSafe = [Math]::Max(10, [int]$MaxEntries)
        $maxKbSafe = [Math]::Max(64, [int]$MaxFileKb)

        $needTrim = $false
        try {
            $kb = [double]((Get-Item -LiteralPath $CachePath).Length) / 1024.0
            if ($kb -gt $maxKbSafe) { $needTrim = $true }
        } catch { }

        if ($needTrim) {
            $keep = @(Get-Content -LiteralPath $CachePath -Tail $maxEntriesSafe)
            $keep | Set-Content -LiteralPath $CachePath -Encoding UTF8
        }
    } catch { }
}

function Get-VcoCosineSimilarity {
    param(
        [object[]]$A,
        [object[]]$B
    )

    if (-not $A -or -not $B) { return 0.0 }

    $n = [Math]::Min($A.Count, $B.Count)
    if ($n -le 0) { return 0.0 }

    $dot = 0.0
    $na = 0.0
    $nb = 0.0
    for ($i = 0; $i -lt $n; $i++) {
        $ai = [double]$A[$i]
        $bi = [double]$B[$i]
        $dot += ($ai * $bi)
        $na += ($ai * $ai)
        $nb += ($bi * $bi)
    }

    if ($na -le 0.0 -or $nb -le 0.0) { return 0.0 }
    return ($dot / ([Math]::Sqrt($na) * [Math]::Sqrt($nb)))
}

function Get-VcoEmbeddingsForTextsWithCache {
    param(
        [string]$EmbeddingModel,
        [string[]]$Texts,
        [object]$PolicyResolved,
        [string]$VcoRepoRoot
    )

    if (-not $EmbeddingModel -or -not $Texts -or $Texts.Count -eq 0) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "missing_inputs"; vectors = @() }
    }

    $vectorCfg = if ($PolicyResolved -and $PolicyResolved.context -and $PolicyResolved.context.vector_diff) { $PolicyResolved.context.vector_diff } else { $null }
    $cacheRel = if ($vectorCfg -and $vectorCfg.cache_relpath) { [string]$vectorCfg.cache_relpath } else { "" }
    $maxEntries = if ($vectorCfg -and $vectorCfg.max_cache_entries -ne $null) { [int]$vectorCfg.max_cache_entries } else { 250 }
    $maxFileKb = if ($vectorCfg -and $vectorCfg.max_cache_file_kb -ne $null) { [int]$vectorCfg.max_cache_file_kb } else { 8192 }

    $cachePath = if ($cacheRel) { Get-VcoVectorCachePath -VcoRepoRoot $VcoRepoRoot -CacheRelPath $cacheRel } else { $null }
    $cache = if ($cachePath) { Read-VcoVectorCache -CachePath $cachePath -MaxEntries $maxEntries } else { @{} }

    $vectors = New-Object object[] $Texts.Count
    $missingTexts = @()
    $missingMeta = @()

    for ($i = 0; $i -lt $Texts.Count; $i++) {
        $text = [string]$Texts[$i]
        $sha = Get-VcoTextSha256Hex -Text $text
        $key = "{0}|{1}" -f $EmbeddingModel, $sha

        if ($cache.ContainsKey($key)) {
            $vectors[$i] = $cache[$key]
        } else {
            $missingTexts += $text
            $missingMeta += [pscustomobject]@{ idx = $i; sha = $sha; len = $text.Length }
        }
    }

    if ($missingTexts.Count -gt 0) {
        $timeoutMs = 2500
        $embeddingProvider = $null
        $embeddingProviderType = "openai"
        $embeddingProviderBaseUrl = ""
        $embeddingProviderBaseUrlEnvCandidates = @()
        $embeddingProviderEndpointPath = ""
        $embeddingProviderApiKeyEnv = "VCO_VECTOR_DIFF_API_KEY"
        try {
            if ($vectorCfg -and $vectorCfg.embedding_provider) { $embeddingProvider = $vectorCfg.embedding_provider }
        } catch { }
        try {
            if ($embeddingProvider -and $embeddingProvider.type) { $embeddingProviderType = [string]$embeddingProvider.type }
        } catch { }
        try {
            if ($embeddingProvider -and $embeddingProvider.base_url) { $embeddingProviderBaseUrl = [string]$embeddingProvider.base_url }
        } catch { }
        try {
            if ($embeddingProvider -and $embeddingProvider.base_url_env_candidates) { $embeddingProviderBaseUrlEnvCandidates = @($embeddingProvider.base_url_env_candidates) }
        } catch { }
        try {
            if ($embeddingProvider -and $embeddingProvider.endpoint_path) { $embeddingProviderEndpointPath = [string]$embeddingProvider.endpoint_path }
        } catch { }
        try {
            if ($embeddingProvider -and $embeddingProvider.api_key_env) { $embeddingProviderApiKeyEnv = [string]$embeddingProvider.api_key_env }
        } catch { }

        $timeoutHint = $null
        try {
            if ($embeddingProvider -and $embeddingProvider.timeout_ms -ne $null) { $timeoutHint = [int]$embeddingProvider.timeout_ms }
        } catch { }
        if ($timeoutHint -ne $null) {
            $timeoutMs = [Math]::Max(1000, [int][Math]::Min(15000, $timeoutHint))
        } else {
            try {
                $timeoutMs = [Math]::Max(1000, [int][Math]::Min(8000, [int]$PolicyResolved.provider.timeout_ms))
            } catch { }
        }

        $result = $null
        try {
            switch ($embeddingProviderType) {
                "openai" {
                    $result = Invoke-OpenAiEmbeddingsCreate `
                        -Model $EmbeddingModel `
                        -InputItems @($missingTexts) `
                        -TimeoutMs $timeoutMs `
                        -ApiKeyEnv $embeddingProviderApiKeyEnv `
                        -BaseUrl $embeddingProviderBaseUrl `
                        -BaseUrlEnvCandidates $embeddingProviderBaseUrlEnvCandidates
                }
                "openai-compatible" {
                    $result = Invoke-OpenAiEmbeddingsCreate `
                        -Model $EmbeddingModel `
                        -InputItems @($missingTexts) `
                        -TimeoutMs $timeoutMs `
                        -ApiKeyEnv $embeddingProviderApiKeyEnv `
                        -BaseUrl $embeddingProviderBaseUrl `
                        -BaseUrlEnvCandidates $embeddingProviderBaseUrlEnvCandidates
                }
                default {
                    return [pscustomobject]@{ ok = $false; abstained = $true; reason = "unknown_embedding_provider"; vectors = @() }
                }
            }
        } catch {
            return [pscustomobject]@{ ok = $false; abstained = $true; reason = "embeddings_invoke_error"; vectors = @() }
        }

        if (-not [bool]$result.ok -or [bool]$result.abstained) {
            return [pscustomobject]@{ ok = $false; abstained = $true; reason = [string]$result.reason; vectors = @() }
        }

        $returned = @($result.vectors)
        if ($returned.Count -ne $missingTexts.Count) {
            return [pscustomobject]@{ ok = $false; abstained = $true; reason = "embeddings_size_mismatch"; vectors = @() }
        }

        $entries = @()
        for ($j = 0; $j -lt $missingMeta.Count; $j++) {
            $meta = $missingMeta[$j]
            $vec = $returned[$j]
            $vectors[[int]$meta.idx] = $vec

            if ($cachePath) {
                $entries += [ordered]@{
                    ts = (Get-Date).ToString("o")
                    model = $EmbeddingModel
                    sha256 = [string]$meta.sha
                    len = [int]$meta.len
                    embedding = $vec
                }
            }
        }

        if ($cachePath -and $entries.Count -gt 0) {
            Append-VcoVectorCacheEntries -CachePath $cachePath -Entries $entries -MaxEntries $maxEntries -MaxFileKb $maxFileKb
        }
    }

    return [pscustomobject]@{ ok = $true; abstained = $false; reason = "ok"; vectors = @($vectors) }
}

function Select-VcoVectorDiffSnippets {
    param(
        [object]$PolicyResolved,
        [string]$VcoRepoRoot,
        [string]$QueryText,
        [string]$DiffText
    )

    if (-not $PolicyResolved -or -not $DiffText -or -not $QueryText) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "missing_inputs"; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $cfg = $PolicyResolved.context.vector_diff
    if (-not $cfg -or -not [bool]$cfg.enabled) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "vector_diff_disabled"; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $embeddingModel = if ($cfg.embedding_model) { [string]$cfg.embedding_model } else { "text-embedding-3-small" }
    $maxChunks = [Math]::Max(1, [int]$cfg.max_chunks)
    $chunkMaxChars = [Math]::Max(200, [int]$cfg.chunk_max_chars)
    $maxSelected = [Math]::Max(1, [int]$cfg.max_selected_chunks)

    $chunks = Split-VcoGitDiffIntoVectorChunks -DiffText $DiffText -MaxChunks $maxChunks -ChunkMaxChars $chunkMaxChars
    if ($chunks.Count -eq 0) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "no_chunks"; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $texts = @([string]$QueryText) + @($chunks | ForEach-Object { [string]$_ })
    $emb = Get-VcoEmbeddingsForTextsWithCache -EmbeddingModel $embeddingModel -Texts $texts -PolicyResolved $PolicyResolved -VcoRepoRoot $VcoRepoRoot
    if (-not [bool]$emb.ok -or [bool]$emb.abstained) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = [string]$emb.reason; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $vecs = @($emb.vectors)
    if ($vecs.Count -ne $texts.Count) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "vector_count_mismatch"; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $queryVec = @($vecs[0])
    $scores = @()
    for ($i = 1; $i -lt $vecs.Count; $i++) {
        $score = Get-VcoCosineSimilarity -A $queryVec -B @($vecs[$i])
        $scores += [pscustomobject]@{ idx = ($i - 1); score = [Math]::Round([double]$score, 6) }
    }

    $top = @($scores | Sort-Object -Property score -Descending | Select-Object -First ([Math]::Min($maxSelected, $scores.Count)))
    if ($top.Count -eq 0) {
        return [pscustomobject]@{ ok = $false; abstained = $true; reason = "no_scores"; diff = $null; diff_truncated = $false; selected_chunks = 0 }
    }

    $parts = @()
    $rank = 0
    foreach ($row in $top) {
        $rank++
        $header = "[vector_diff rank={0} score={1}]" -f $rank, $row.score
        $parts += $header
        $parts += $chunks[[int]$row.idx]
        $parts += ""
    }

    $joined = ($parts -join "`n").TrimEnd()

    $limit = [Math]::Max(1000, [int]$PolicyResolved.context.max_diff_chars)
    $truncated = $false
    if ($joined.Length -gt $limit) {
        $joined = $joined.Substring(0, $limit)
        $truncated = $true
    }

    return [pscustomobject]@{
        ok = $true
        abstained = $false
        reason = "ok"
        diff = $joined
        diff_truncated = [bool]$truncated
        selected_chunks = [int]$top.Count
    }
}

function Get-VcoGitContextSnippet {
    param(
        [object]$PolicyResolved,
        [string]$VcoRepoRoot,
        [string]$QueryText,
        [string]$TaskType
    )

    $contextMode = if ($PolicyResolved -and $PolicyResolved.context -and $PolicyResolved.context.mode) { [string]$PolicyResolved.context.mode } else { "none" }
    if ($contextMode -eq "none") {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false; diff_mode = "none"; diff_selected_chunks = 0; diff_vector_reason = $null }
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false; diff_mode = "none"; diff_selected_chunks = 0; diff_vector_reason = $null }
    }

    $gitRepoRoot = $null
    try {
        $gitRepoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
    } catch { }
    if (-not $gitRepoRoot) {
        return [pscustomobject]@{ git_present = $false; repo_root = $null; status = $null; diff = $null; diff_truncated = $false; diff_mode = "none"; diff_selected_chunks = 0; diff_vector_reason = $null }
    }

    $statusText = $null
    $diffText = $null
    $diffTruncated = $false
    $diffMode = "none"
    $diffSelectedChunks = 0
    $diffVectorReason = $null

    if ([bool]$PolicyResolved.context.include_git_status) {
        try {
            $maxLines = [Math]::Max(10, [int]$PolicyResolved.context.max_git_status_lines)
            $lines = @(git status --porcelain=v1 2>$null | Select-Object -First $maxLines)
            if ($lines.Count -gt 0) { $statusText = ($lines -join "`n").TrimEnd() }
        } catch { }
    }

    $diffTaskAllow = @()
    if ($PolicyResolved.context.PSObject.Properties.Name -contains 'git_diff_task_allow') {
        $diffTaskAllow = @($PolicyResolved.context.git_diff_task_allow)
    }
    $taskAllowsDiff = ($diffTaskAllow.Count -eq 0) -or ($diffTaskAllow -contains $TaskType)

    if (-not $taskAllowsDiff) {
        $diffMode = "skipped_task_type"
    }

    if ($contextMode -eq "diff_snippets_ok" -and [bool]$PolicyResolved.context.include_git_diff -and $taskAllowsDiff) {
        try {
            $raw = (git diff --patch --unified=0 2>$null | Out-String)
            $raw = $raw.TrimEnd()
            $diffMode = "full"

            $vectorCfg = if ($PolicyResolved.context.vector_diff) { $PolicyResolved.context.vector_diff } else { $null }
            $vectorEnabled = [bool]($vectorCfg -and $vectorCfg.enabled)
            $minChars = if ($vectorCfg -and $vectorCfg.min_diff_chars_for_vector -ne $null) { [int]$vectorCfg.min_diff_chars_for_vector } else { 0 }

            if ($vectorEnabled -and $raw -and $raw.Length -ge $minChars -and $QueryText) {
                $embProv = $null
                $embProvType = "openai"
                try {
                    if ($vectorCfg -and $vectorCfg.embedding_provider) { $embProv = $vectorCfg.embedding_provider }
                } catch { }
                try {
                    if ($embProv -and $embProv.type) { $embProvType = [string]$embProv.type }
                } catch { }

                $keyOk = $false
                $keyReason = $null
                $embeddingApiKeyEnv = "VCO_VECTOR_DIFF_API_KEY"
                try {
                    if ($embProv -and $embProv.api_key_env) { $embeddingApiKeyEnv = [string]$embProv.api_key_env }
                } catch { }

                switch ($embProvType) {
                    "openai" {
                        if (Get-OpenAiApiKey -EnvName $embeddingApiKeyEnv) { $keyOk = $true } else { $keyReason = "missing_vector_diff_api_key" }
                    }
                    "openai-compatible" {
                        if (Get-OpenAiApiKey -EnvName $embeddingApiKeyEnv) { $keyOk = $true } else { $keyReason = "missing_vector_diff_api_key" }
                    }
                    default {
                        $keyReason = "unknown_embedding_provider"
                    }
                }

                if ($keyOk) {
                    $vec = Select-VcoVectorDiffSnippets -PolicyResolved $PolicyResolved -VcoRepoRoot $VcoRepoRoot -QueryText $QueryText -DiffText $raw
                    if ([bool]$vec.ok -and (-not [bool]$vec.abstained) -and $vec.diff) {
                        $diffText = [string]$vec.diff
                        $diffTruncated = [bool]$vec.diff_truncated
                        $diffMode = "vector_selected"
                        $diffSelectedChunks = [int]$vec.selected_chunks
                        $diffVectorReason = "ok"
                    } else {
                        $diffVectorReason = if ($vec -and $vec.reason) { [string]$vec.reason } else { "vector_abstained" }
                    }
                } else {
                    $diffVectorReason = $keyReason
                }
            }

            if (-not $diffText) {
                $limit = [Math]::Max(1000, [int]$PolicyResolved.context.max_diff_chars)
                if ($raw.Length -gt $limit) {
                    $diffText = $raw.Substring(0, $limit)
                    $diffTruncated = $true
                    $diffMode = "head_truncate"
                } else {
                    $diffText = $raw
                    $diffMode = "full"
                }
            }
        } catch { }
    }

    return [pscustomobject]@{
        git_present = $true
        repo_root = $gitRepoRoot
        status = $statusText
        diff = $diffText
        diff_truncated = [bool]$diffTruncated
        diff_mode = [string]$diffMode
        diff_selected_chunks = [int]$diffSelectedChunks
        diff_vector_reason = $diffVectorReason
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

    $gitDiffRaw = $null
    $gitDiffDigest = $null
    $gitDiffDigestUsed = $false
    if ($GitContext -and $GitContext.PSObject) {
        if ($GitContext.PSObject.Properties.Name -contains 'diff_raw' -and $GitContext.diff_raw) {
            $gitDiffRaw = $GitContext.diff_raw
        }
        if ($GitContext.PSObject.Properties.Name -contains 'diff_digest' -and $GitContext.diff_digest) {
            $gitDiffDigest = $GitContext.diff_digest
        }
        if ($GitContext.PSObject.Properties.Name -contains 'diff_digest_used' -and ($GitContext.diff_digest_used -ne $null)) {
            $gitDiffDigestUsed = [bool]$GitContext.diff_digest_used
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
            repo_root = if ($GitContext) { $GitContext.repo_root } else { $null }
            status = if ($GitContext) { $GitContext.status } else { $null }
            diff = if ($GitContext) { $GitContext.diff } else { $null }
            diff_raw = $gitDiffRaw
            diff_digest = $gitDiffDigest
            diff_digest_used = $gitDiffDigestUsed
            diff_truncated = if ($GitContext) { [bool]$GitContext.diff_truncated } else { $false }
            diff_mode = if ($GitContext) { $GitContext.diff_mode } else { $null }
            diff_selected_chunks = if ($GitContext) { $GitContext.diff_selected_chunks } else { 0 }
            diff_vector_reason = if ($GitContext) { $GitContext.diff_vector_reason } else { $null }
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

function Get-LlmDiffDigestJsonSchema {
    $schema = [ordered]@{
        type = "object"
        additionalProperties = $false
        required = @("digest")
        properties = [ordered]@{
            digest = [ordered]@{ type = "string" }
        }
    }

    return $schema
}

function New-LlmDiffDigestInputText {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [object]$GitContext,
        [int]$MaxDigestChars
    )

    $maxChars = [Math]::Max(200, [int]$MaxDigestChars)
    $ctx = [ordered]@{
        vco = [ordered]@{
            grade = $Grade
            task_type = $TaskType
        }
        prompt = [ordered]@{
            original = $PromptText
            normalized = if ($PromptNormalization -and $PromptNormalization.normalized) { [string]$PromptNormalization.normalized } else { $PromptText }
        }
        git = [ordered]@{
            present = [bool]($GitContext -and $GitContext.git_present)
            status = if ($GitContext) { $GitContext.status } else { $null }
            diff = if ($GitContext) { $GitContext.diff } else { $null }
            diff_mode = if ($GitContext) { $GitContext.diff_mode } else { $null }
            diff_truncated = if ($GitContext) { [bool]$GitContext.diff_truncated } else { $false }
            diff_selected_chunks = if ($GitContext) { [int]$GitContext.diff_selected_chunks } else { 0 }
        }
        constraints = [ordered]@{
            max_digest_chars = $maxChars
        }
    }

    $json = ($ctx | ConvertTo-Json -Depth 12 -Compress)

    $text = @()
    $text += "You are generating a compact Git diff digest for VCO TurboMax."
    $text += ""
    $text += "Constraints:"
    $text += "- Output MUST be valid JSON that matches the provided JSON Schema."
    $text += "- Keep digest under {0} characters." -f $maxChars
    $text += "- Do NOT include large raw diff excerpts; summarize intent, impact, and risk instead."
    $text += "- Include: key files/areas changed, high-level intent, risk/edge cases, suggested tests."
    $text += ""
    $text += "Context(JSON):"
    $text += $json

    return ($text -join "`n")
}

function Get-LlmAdviceProviderTypeNormalized {
    param([object]$PolicyResolved)

    $providerType = if ($PolicyResolved -and $PolicyResolved.provider -and $PolicyResolved.provider.type) { [string]$PolicyResolved.provider.type } else { "openai" }
    return $providerType.Trim().ToLowerInvariant()
}

function Get-LlmAdviceProviderApiKeyEnvName {
    param([object]$PolicyResolved)

    if ($PolicyResolved -and $PolicyResolved.provider -and $PolicyResolved.provider.api_key_env) {
        return [string]$PolicyResolved.provider.api_key_env
    }
    return "VCO_INTENT_ADVICE_API_KEY"
}

function Test-LlmAdviceProviderIsOpenAiFamily {
    param([string]$ProviderType)
    return @("openai", "openai-compatible") -contains ([string]$ProviderType).Trim().ToLowerInvariant()
}

function Test-LlmAdviceProviderIsAnthropicFamily {
    param([string]$ProviderType)
    return @("anthropic", "anthropic-compatible") -contains ([string]$ProviderType).Trim().ToLowerInvariant()
}

function Test-LlmAdviceProviderRequiresRemoteCredential {
    param([string]$ProviderType)
    $normalized = ([string]$ProviderType).Trim().ToLowerInvariant()
    if ($normalized -eq "mock") { return $false }
    return (Test-LlmAdviceProviderIsOpenAiFamily -ProviderType $normalized) -or (Test-LlmAdviceProviderIsAnthropicFamily -ProviderType $normalized)
}

function Test-LlmAdviceShouldTryAnthropicFallback {
    param(
        [string]$ProviderType,
        [string]$BaseUrl
    )

    if (-not (Test-LlmAdviceProviderIsOpenAiFamily -ProviderType $ProviderType)) { return $false }
    if (-not $BaseUrl) { return $false }

    $normalizedBaseUrl = ([string]$BaseUrl).Trim().ToLowerInvariant()
    if (-not $normalizedBaseUrl) { return $false }
    if ($normalizedBaseUrl -eq "https://api.openai.com" -or $normalizedBaseUrl -eq "https://api.openai.com/v1") { return $false }
    if ($normalizedBaseUrl -match "openai\.com") { return $false }
    return $true
}

function Invoke-LlmStructuredJsonProvider {
    param(
        [object]$PolicyResolved,
        [string]$Model,
        [string]$BaseUrl,
        [int]$TimeoutMs,
        [int]$MaxOutputTokens,
        [double]$Temperature,
        [double]$TopP,
        [bool]$Store,
        [object]$ResponsesInputItems,
        [object]$ResponsesTextFormat,
        [object[]]$ChatMessages,
        [object]$ChatResponseFormat,
        [object[]]$AnthropicMessages,
        [string]$SystemInstructions
    )

    $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $PolicyResolved
    $adviceApiKeyEnv = Get-LlmAdviceProviderApiKeyEnvName -PolicyResolved $PolicyResolved
    $adviceBaseUrlEnvCandidates = if ($PolicyResolved.provider.base_url_env_candidates) { @($PolicyResolved.provider.base_url_env_candidates) } else { @("VCO_INTENT_ADVICE_BASE_URL") }
    $timeoutMsSafe = [Math]::Max(500, [int]$TimeoutMs)
    $anthropicVersion = if ($PolicyResolved.provider.anthropic_version) { [string]$PolicyResolved.provider.anthropic_version } else { "2023-06-01" }

    $invokeAnthropic = {
        $r = Invoke-AnthropicMessagesCreate `
            -Model $Model `
            -BaseUrl $BaseUrl `
            -ApiKeyEnv $adviceApiKeyEnv `
            -BaseUrlEnvCandidates $adviceBaseUrlEnvCandidates `
            -Messages $AnthropicMessages `
            -System $SystemInstructions `
            -MaxTokens $MaxOutputTokens `
            -Temperature $Temperature `
            -TopP $TopP `
            -TimeoutMs $timeoutMsSafe `
            -AnthropicVersion $anthropicVersion
        $r | Add-Member -NotePropertyName api -NotePropertyValue "anthropic_messages" -Force
        return $r
    }

    if (Test-LlmAdviceProviderIsAnthropicFamily -ProviderType $providerType) {
        return (& $invokeAnthropic)
    }

    if (-not (Test-LlmAdviceProviderIsOpenAiFamily -ProviderType $providerType)) {
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

    $preferChat = $false
    if ($BaseUrl -and ($BaseUrl -notmatch "openai\.com")) {
        $preferChat = $true
    }

    $invokeResponses = {
        $r = Invoke-OpenAiResponsesCreate `
            -Model $Model `
            -BaseUrl $BaseUrl `
            -ApiKeyEnv $adviceApiKeyEnv `
            -BaseUrlEnvCandidates $adviceBaseUrlEnvCandidates `
            -InputItems $ResponsesInputItems `
            -TextFormat $ResponsesTextFormat `
            -Instructions $SystemInstructions `
            -MaxOutputTokens $MaxOutputTokens `
            -Temperature $Temperature `
            -TopP $TopP `
            -TimeoutMs $timeoutMsSafe `
            -Store:([bool]$Store)
        $r | Add-Member -NotePropertyName api -NotePropertyValue "responses" -Force
        return $r
    }

    $invokeChat = {
        $r = Invoke-OpenAiChatCompletionsCreate `
            -Model $Model `
            -BaseUrl $BaseUrl `
            -ApiKeyEnv $adviceApiKeyEnv `
            -BaseUrlEnvCandidates $adviceBaseUrlEnvCandidates `
            -Messages $ChatMessages `
            -ResponseFormat $ChatResponseFormat `
            -MaxTokens $MaxOutputTokens `
            -Temperature $Temperature `
            -TopP $TopP `
            -TimeoutMs $timeoutMsSafe
        $r | Add-Member -NotePropertyName api -NotePropertyValue "chat_completions" -Force
        return $r
    }

    $primary = $null
    $fallback = $null

    if ($preferChat) {
        $primary = & $invokeChat
        if ([bool]$primary.ok -and (-not [bool]$primary.abstained) -and $primary.output_text) { return $primary }
        if ([string]$primary.reason -eq "missing_intent_advice_api_key") { return $primary }

        $fallback = & $invokeResponses
        if ([bool]$fallback.ok -and (-not [bool]$fallback.abstained) -and $fallback.output_text) { return $fallback }
        if ([string]$fallback.reason -eq "missing_intent_advice_api_key") { return $fallback }
    } else {
        $primary = & $invokeResponses
        if ([bool]$primary.ok -and (-not [bool]$primary.abstained) -and $primary.output_text) { return $primary }
        if ([string]$primary.reason -eq "missing_intent_advice_api_key") { return $primary }

        $fallback = & $invokeChat
        if ([bool]$fallback.ok -and (-not [bool]$fallback.abstained) -and $fallback.output_text) { return $fallback }
        if ([string]$fallback.reason -eq "missing_intent_advice_api_key") { return $fallback }
    }

    if (Test-LlmAdviceShouldTryAnthropicFallback -ProviderType $providerType -BaseUrl $BaseUrl) {
        $anthropic = & $invokeAnthropic
        if ([bool]$anthropic.ok -and (-not [bool]$anthropic.abstained) -and $anthropic.output_text) { return $anthropic }
        return $anthropic
    }

    if ($fallback) { return $fallback }
    return $primary
}

function Invoke-LlmDiffDigestProvider {
    param(
        [object]$PolicyResolved,
        [string]$RepoRoot,
        [string]$InputText,
        [int]$MaxDigestChars
    )

    $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $PolicyResolved
    $adviceApiKeyEnv = Get-LlmAdviceProviderApiKeyEnvName -PolicyResolved $PolicyResolved

    if ((Test-LlmAdviceProviderRequiresRemoteCredential -ProviderType $providerType) -and (-not (Get-OpenAiApiKey -EnvName $adviceApiKeyEnv))) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_intent_advice_api_key"
            api = "none"
            latency_ms = 0
            digest = $null
            error = $null
        }
    }

    $digestCfg = $null
    try { $digestCfg = $PolicyResolved.enhancements.diff_digest } catch { }

    $model = [string]$PolicyResolved.provider.model
    try {
        if ($digestCfg -and $digestCfg.model) { $model = [string]$digestCfg.model }
    } catch { }

    $maxTokens = [int]$PolicyResolved.provider.max_output_tokens
    $temperature = [double]$PolicyResolved.provider.temperature
    $timeoutMs = [int]$PolicyResolved.provider.timeout_ms

    try {
        if ($digestCfg -and $digestCfg.max_output_tokens -ne $null) { $maxTokens = [int]$digestCfg.max_output_tokens }
    } catch { }
    try {
        if ($digestCfg -and $digestCfg.temperature -ne $null) { $temperature = [double]$digestCfg.temperature }
    } catch { }
    try {
        if ($digestCfg -and $digestCfg.timeout_ms -ne $null) { $timeoutMs = [int]$digestCfg.timeout_ms }
    } catch { }

    $schema = Get-LlmDiffDigestJsonSchema

    $textFormat = [ordered]@{
        type = "json_schema"
        name = "vco_diff_digest"
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

    $chatResponseFormat = [ordered]@{
        type = "json_schema"
        json_schema = [ordered]@{
            name = "vco_diff_digest"
            strict = $true
            schema = $schema
        }
    }

    $chatMessages = @(
        [ordered]@{ role = "system"; content = $instructions },
        [ordered]@{ role = "user"; content = $InputText }
    )
    $baseUrl = if ($PolicyResolved.provider.base_url) { [string]$PolicyResolved.provider.base_url } else { "" }
    $anthropicMessages = @(
        [ordered]@{
            role = "user"
            content = @(
                [ordered]@{
                    type = "text"
                    text = $InputText
                }
            )
        }
    )

    $providerResult = Invoke-LlmStructuredJsonProvider `
        -PolicyResolved $PolicyResolved `
        -Model $model `
        -BaseUrl $baseUrl `
        -TimeoutMs $timeoutMs `
        -MaxOutputTokens $maxTokens `
        -Temperature $temperature `
        -TopP ([double]$PolicyResolved.provider.top_p) `
        -Store ([bool]$PolicyResolved.provider.store) `
        -ResponsesInputItems $input `
        -ResponsesTextFormat $textFormat `
        -ChatMessages $chatMessages `
        -ChatResponseFormat $chatResponseFormat `
        -AnthropicMessages $anthropicMessages `
        -SystemInstructions $instructions

    if (-not $providerResult -or -not [bool]$providerResult.ok -or [bool]$providerResult.abstained -or (-not $providerResult.output_text)) {
        $reason = if ($providerResult -and $providerResult.reason) { [string]$providerResult.reason } else { "provider_abstained" }
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = $reason
            api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
            latency_ms = if ($providerResult -and $providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            digest = $null
            error = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'error' -and $providerResult.error) { [string]$providerResult.error } else { $null }
        }
    }

    $digest = $null
    try {
        $obj = ($providerResult.output_text.Trim() | ConvertFrom-Json)
        if ($obj -and $obj.digest) { $digest = [string]$obj.digest }
    } catch { }

    if (-not $digest) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "digest_parse_error"
            api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
            latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            digest = $null
            error = $null
        }
    }

    $limit = [Math]::Max(200, [int]$MaxDigestChars)
    if ($digest.Length -gt $limit) { $digest = $digest.Substring(0, $limit) }

    return [pscustomobject]@{
        ok = $true
        abstained = $false
        reason = "ok"
        api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
        latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
        digest = $digest.Trim()
        error = $null
    }
}

function Get-LlmConfirmQuestionBoosterJsonSchema {
    $schema = [ordered]@{
        type = "object"
        additionalProperties = $false
        required = @("confirm_questions")
        properties = [ordered]@{
            confirm_questions = [ordered]@{
                type = "array"
                maxItems = 3
                items = [ordered]@{ type = "string" }
            }
        }
    }

    return $schema
}

function New-LlmConfirmQuestionBoosterInputText {
    param(
        [string]$PromptText,
        [object]$PromptNormalization,
        [string]$Grade,
        [string]$TaskType,
        [string[]]$ExistingConfirmQuestions,
        [int]$MaxQuestions
    )

    $maxQ = [Math]::Max(1, [Math]::Min(3, [int]$MaxQuestions))
    $ctx = [ordered]@{
        vco = [ordered]@{
            grade = $Grade
            task_type = $TaskType
        }
        prompt = [ordered]@{
            original = $PromptText
            normalized = if ($PromptNormalization -and $PromptNormalization.normalized) { [string]$PromptNormalization.normalized } else { $PromptText }
        }
        existing_confirm_questions = @($ExistingConfirmQuestions | Where-Object { $_ } | Select-Object -First 5)
        constraints = [ordered]@{
            max_questions = $maxQ
        }
    }

    $json = ($ctx | ConvertTo-Json -Depth 8 -Compress)

    $text = @()
    $text += "You are improving confirm_questions for a user request."
    $text += ""
    $text += "Rules:"
    $text += "- Return ONLY JSON that matches the JSON Schema. No markdown. No extra keys."
    $text += "- Provide <= {0} questions." -f $maxQ
    $text += "- Questions must be short, high-signal, and non-redundant."
    $text += "- Prefer questions that enable immediate execution (repo/path, expected output, constraints, and acceptance criteria)."
    $text += ""
    $text += "Context(JSON):"
    $text += $json

    return ($text -join "`n")
}

function Invoke-LlmConfirmQuestionBoosterProvider {
    param(
        [object]$PolicyResolved,
        [string]$RepoRoot,
        [string]$InputText,
        [int]$MaxQuestions
    )

    $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $PolicyResolved

    $cfg = $null
    try { $cfg = $PolicyResolved.enhancements.confirm_question_booster } catch { }
    $maxTokens = 340
    $temperature = 0.1
    $timeoutMsSafe = [int]$PolicyResolved.provider.timeout_ms
    try { if ($cfg -and $cfg.max_output_tokens -ne $null) { $maxTokens = [int]$cfg.max_output_tokens } } catch { }
    try { if ($cfg -and $cfg.temperature -ne $null) { $temperature = [double]$cfg.temperature } } catch { }
    try { if ($cfg -and $cfg.timeout_ms -ne $null) { $timeoutMsSafe = [int]$cfg.timeout_ms } } catch { }

    $maxTokens = [Math]::Max(80, [int]$maxTokens)
    $temperature = [Math]::Max(0.0, [Math]::Min(1.0, [double]$temperature))
    $timeoutMsSafe = [Math]::Max(500, [int]$timeoutMsSafe)

    $schema = Get-LlmConfirmQuestionBoosterJsonSchema
    $textFormat = [ordered]@{
        type = "json_schema"
        name = "vco_confirm_question_booster"
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

    $chatResponseFormat = [ordered]@{
        type = "json_schema"
        json_schema = [ordered]@{
            name = "vco_confirm_question_booster"
            strict = $true
            schema = $schema
        }
    }

    $chatMessages = @(
        [ordered]@{ role = "system"; content = $instructions },
        [ordered]@{ role = "user"; content = $InputText }
    )
    $baseUrl = if ($PolicyResolved.provider.base_url) { [string]$PolicyResolved.provider.base_url } else { "" }
    $anthropicMessages = @(
        [ordered]@{
            role = "user"
            content = @(
                [ordered]@{
                    type = "text"
                    text = $InputText
                }
            )
        }
    )

    $providerResult = Invoke-LlmStructuredJsonProvider `
        -PolicyResolved $PolicyResolved `
        -Model ([string]$PolicyResolved.provider.model) `
        -BaseUrl $baseUrl `
        -TimeoutMs $timeoutMsSafe `
        -MaxOutputTokens $maxTokens `
        -Temperature $temperature `
        -TopP ([double]$PolicyResolved.provider.top_p) `
        -Store ([bool]$PolicyResolved.provider.store) `
        -ResponsesInputItems $input `
        -ResponsesTextFormat $textFormat `
        -ChatMessages $chatMessages `
        -ChatResponseFormat $chatResponseFormat `
        -AnthropicMessages $anthropicMessages `
        -SystemInstructions $instructions

    if (-not $providerResult -or -not [bool]$providerResult.ok -or [bool]$providerResult.abstained -or (-not $providerResult.output_text)) {
        $reason = if ($providerResult -and $providerResult.reason) { [string]$providerResult.reason } else { "provider_abstained" }
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = $reason
            api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
            latency_ms = if ($providerResult -and $providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            confirm_questions = @()
            error = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'error' -and $providerResult.error) { [string]$providerResult.error } else { $null }
        }
    }

    $questions = @()
    try {
        $obj = ($providerResult.output_text.Trim() | ConvertFrom-Json)
        if ($obj -and $obj.confirm_questions) {
            $questions = @($obj.confirm_questions | Where-Object { $_ } | Select-Object -First ([Math]::Max(1, [Math]::Min(3, [int]$MaxQuestions))))
        }
    } catch { }

    if (-not $questions -or $questions.Count -eq 0) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "confirm_questions_parse_error"
            api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
            latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
            confirm_questions = @()
            error = $null
        }
    }

    return [pscustomobject]@{
        ok = $true
        abstained = $false
        reason = "ok"
        api = if ($providerResult -and $providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) { [string]$providerResult.api } else { "unknown" }
        latency_ms = if ($providerResult.latency_ms -ne $null) { [int]$providerResult.latency_ms } else { 0 }
        confirm_questions = @($questions)
        error = $null
    }
}

function New-LlmAccelerationProviderPolicyOverride {
    param(
        [object]$PolicyResolved,
        [double]$Temperature,
        [int]$MaxOutputTokens,
        [int]$TimeoutMs
    )

    $prov = $PolicyResolved.provider
    return [pscustomobject]@{
        provider = [pscustomobject]@{
            type = if ($prov.type) { [string]$prov.type } else { "openai" }
            model = if ($prov.model) { [string]$prov.model } else { "" }
            base_url = if ($prov.base_url) { [string]$prov.base_url } else { "" }
            anthropic_version = if ($prov.anthropic_version) { [string]$prov.anthropic_version } else { "" }
            timeout_ms = [Math]::Max(500, [int]$TimeoutMs)
            max_output_tokens = [Math]::Max(200, [int]$MaxOutputTokens)
            temperature = [Math]::Max(0.0, [Math]::Min(1.0, [double]$Temperature))
            top_p = if ($prov.top_p -ne $null) { [double]$prov.top_p } else { 1.0 }
            store = if ($prov.store -ne $null) { [bool]$prov.store } else { $false }
            mock_response_path = if ($prov.mock_response_path) { [string]$prov.mock_response_path } else { "" }
            api_key_env = if ($prov.api_key_env) { [string]$prov.api_key_env } else { "VCO_INTENT_ADVICE_API_KEY" }
            base_url_env_candidates = if ($prov.base_url_env_candidates) { @($prov.base_url_env_candidates) } else { @("VCO_INTENT_ADVICE_BASE_URL") }
        }
    }
}

function Get-LlmAccelerationCommitteeMemberFocus {
    param([int]$MemberIndex)

    switch ($MemberIndex) {
        1 { return "Focus on rerank quality: only suggest overrides when clearly better and within top_candidates; be conservative." }
        2 { return "Focus on clarification: generate the minimal set of confirm_questions (<=3) that would remove ambiguity fast." }
        3 { return "Focus on QA/testing: propose the most valuable tests/checks for this stage; keep them actionable." }
        default { return "Be balanced: rerank only if needed; ask good confirm questions; include QA recommendations." }
    }
}

function New-LlmAccelerationJudgeInputText {
    param(
        [string]$BaseInputText,
        [object[]]$MemberParsedOutputs
    )

    $rows = @()
    $i = 0
    foreach ($m in @($MemberParsedOutputs)) {
        $i++
        if (-not $m) { continue }
        $rows += [ordered]@{
            member = $i
            output = $m
        }
    }

    $json = ($rows | ConvertTo-Json -Depth 12 -Compress)

    $text = @()
    $text += "You are judging committee outputs for VCO LLM Acceleration."
    $text += ""
    $text += "Goal:"
    $text += "- Produce the single best final JSON output (must match the JSON Schema)."
    $text += ""
    $text += "Rules:"
    $text += "- If suggesting a pack/skill override, it MUST be one of the provided top_candidates pack_id and skill candidates."
    $text += "- Prefer fewer, higher-signal confirm_questions (<=3)."
    $text += "- Always include QA recommendations."
    $text += "- If uncertain, abstain."
    $text += ""
    $text += "Original input:"
    $text += $BaseInputText
    $text += ""
    $text += "Committee outputs(JSON):"
    $text += $json

    return ($text -join "`n")
}

function Invoke-LlmAccelerationProviderCommittee {
    param(
        [object]$PolicyResolved,
        [string]$RepoRoot,
        [string]$InputText
    )

    $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $PolicyResolved
    if (-not ((Test-LlmAdviceProviderIsOpenAiFamily -ProviderType $providerType) -or (Test-LlmAdviceProviderIsAnthropicFamily -ProviderType $providerType))) {
        return (Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText)
    }

    $cfg = $null
    try { $cfg = $PolicyResolved.enhancements.committee } catch { }
    $enabled = [bool]($cfg -and $cfg.enabled)
    if (-not $enabled) {
        return (Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText)
    }

    $members = 3
    $minSuccess = 2
    $memberTemps = @()
    $memberMaxTokens = [int]$PolicyResolved.provider.max_output_tokens
    $memberTimeout = [int]$PolicyResolved.provider.timeout_ms
    $judgeEnabled = $true
    $judgeTemp = 0.05
    $judgeMaxTokens = [int]$PolicyResolved.provider.max_output_tokens
    $judgeTimeout = [int]$PolicyResolved.provider.timeout_ms

    try { if ($cfg.members -ne $null) { $members = [int]$cfg.members } } catch { }
    try { if ($cfg.min_success_members -ne $null) { $minSuccess = [int]$cfg.min_success_members } } catch { }
    try { if ($cfg.member_temperatures) { $memberTemps = @($cfg.member_temperatures) } } catch { }
    try { if ($cfg.member_max_output_tokens -ne $null) { $memberMaxTokens = [int]$cfg.member_max_output_tokens } } catch { }
    try { if ($cfg.member_timeout_ms -ne $null) { $memberTimeout = [int]$cfg.member_timeout_ms } } catch { }
    try { if ($cfg.judge_enabled -ne $null) { $judgeEnabled = [bool]$cfg.judge_enabled } } catch { }
    try { if ($cfg.judge_temperature -ne $null) { $judgeTemp = [double]$cfg.judge_temperature } } catch { }
    try { if ($cfg.judge_max_output_tokens -ne $null) { $judgeMaxTokens = [int]$cfg.judge_max_output_tokens } } catch { }
    try { if ($cfg.judge_timeout_ms -ne $null) { $judgeTimeout = [int]$cfg.judge_timeout_ms } } catch { }

    $membersSafe = [Math]::Max(1, [Math]::Min(6, [int]$members))
    if ($membersSafe -le 1) {
        return (Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText)
    }

    $minSuccessSafe = [Math]::Max(1, [Math]::Min($membersSafe, [int]$minSuccess))

    if (-not $memberTemps -or $memberTemps.Count -lt $membersSafe) {
        $base = [double]$PolicyResolved.provider.temperature
        $memberTemps = @()
        for ($i = 0; $i -lt $membersSafe; $i++) {
            $memberTemps += [Math]::Min(1.0, [Math]::Max(0.0, ($base + ($i * 0.1))))
        }
    }

    $memberParsed = @()
    $memberResults = @()
    $totalLatency = 0

    for ($i = 0; $i -lt $membersSafe; $i++) {
        $temp = [double]$memberTemps[$i]
        $focus = Get-LlmAccelerationCommitteeMemberFocus -MemberIndex ($i + 1)
        $memberInput = $InputText + "`n`n[committee_member {0}] {1}" -f ($i + 1), $focus
        $policyOverride = New-LlmAccelerationProviderPolicyOverride -PolicyResolved $PolicyResolved -Temperature $temp -MaxOutputTokens $memberMaxTokens -TimeoutMs $memberTimeout

        $r = Invoke-LlmAccelerationProvider -PolicyResolved $policyOverride -RepoRoot $RepoRoot -InputText $memberInput
        $memberResults += $r
        try { if ($r -and $r.latency_ms -ne $null) { $totalLatency += [int]$r.latency_ms } } catch { }

        if ($r -and [bool]$r.ok -and (-not [bool]$r.abstained) -and $r.output_text) {
            try {
                $obj = ($r.output_text.Trim() | ConvertFrom-Json)
                if ($obj) { $memberParsed += $obj }
            } catch { }
        }
    }

    if ($memberParsed.Count -lt $minSuccessSafe) {
        $single = Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText
        $single | Add-Member -NotePropertyName committee_used -NotePropertyValue $false -Force
        $single | Add-Member -NotePropertyName committee_reason -NotePropertyValue "insufficient_success_members" -Force
        return $single
    }

    if (-not $judgeEnabled) {
        $chosen = $memberResults | Where-Object { $_ -and [bool]$_.ok -and (-not [bool]$_.abstained) -and $_.output_text } | Select-Object -First 1
        if (-not $chosen) { $chosen = Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText }
        $chosen | Add-Member -NotePropertyName committee_used -NotePropertyValue $true -Force
        $chosen | Add-Member -NotePropertyName committee_members -NotePropertyValue $membersSafe -Force
        $chosen | Add-Member -NotePropertyName committee_successes -NotePropertyValue $memberParsed.Count -Force
        $chosen | Add-Member -NotePropertyName committee_judge_used -NotePropertyValue $false -Force
        return $chosen
    }

    $judgeInput = New-LlmAccelerationJudgeInputText -BaseInputText $InputText -MemberParsedOutputs $memberParsed
    $judgePolicy = New-LlmAccelerationProviderPolicyOverride -PolicyResolved $PolicyResolved -Temperature $judgeTemp -MaxOutputTokens $judgeMaxTokens -TimeoutMs $judgeTimeout
    $judgeResult = Invoke-LlmAccelerationProvider -PolicyResolved $judgePolicy -RepoRoot $RepoRoot -InputText $judgeInput
    try { if ($judgeResult -and $judgeResult.latency_ms -ne $null) { $totalLatency += [int]$judgeResult.latency_ms } } catch { }

    if ($judgeResult -and [bool]$judgeResult.ok -and (-not [bool]$judgeResult.abstained) -and $judgeResult.output_text) {
        $judgeResult | Add-Member -NotePropertyName committee_used -NotePropertyValue $true -Force
        $judgeResult | Add-Member -NotePropertyName committee_members -NotePropertyValue $membersSafe -Force
        $judgeResult | Add-Member -NotePropertyName committee_successes -NotePropertyValue $memberParsed.Count -Force
        $judgeResult | Add-Member -NotePropertyName committee_judge_used -NotePropertyValue $true -Force
        $judgeResult | Add-Member -NotePropertyName latency_ms_total -NotePropertyValue $totalLatency -Force
        return $judgeResult
    }

    $fallback = $memberResults | Where-Object { $_ -and [bool]$_.ok -and (-not [bool]$_.abstained) -and $_.output_text } | Select-Object -First 1
    if (-not $fallback) { $fallback = Invoke-LlmAccelerationProvider -PolicyResolved $PolicyResolved -RepoRoot $RepoRoot -InputText $InputText }
    $fallback | Add-Member -NotePropertyName committee_used -NotePropertyValue $true -Force
    $fallback | Add-Member -NotePropertyName committee_members -NotePropertyValue $membersSafe -Force
    $fallback | Add-Member -NotePropertyName committee_successes -NotePropertyValue $memberParsed.Count -Force
    $fallback | Add-Member -NotePropertyName committee_judge_used -NotePropertyValue $false -Force
    $fallback | Add-Member -NotePropertyName committee_reason -NotePropertyValue "judge_abstained" -Force
    $fallback | Add-Member -NotePropertyName latency_ms_total -NotePropertyValue $totalLatency -Force
    return $fallback
}

	function Invoke-LlmAccelerationProvider {
	    param(
	        [object]$PolicyResolved,
	        [string]$RepoRoot,
	        [string]$InputText
	    )

	    $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $PolicyResolved

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

	    $model = [string]$PolicyResolved.provider.model
	    $timeoutMs = [int]$PolicyResolved.provider.timeout_ms

	    $chatResponseFormat = [ordered]@{
	        type = "json_schema"
	        json_schema = [ordered]@{
	            name = "vco_llm_acceleration"
	            strict = $true
	            schema = $schema
	        }
	    }

	    $chatMessages = @(
	        [ordered]@{ role = "system"; content = $instructions },
	        [ordered]@{ role = "user"; content = $InputText }
	    )
        $baseUrl = if ($PolicyResolved.provider.base_url) { [string]$PolicyResolved.provider.base_url } else { "" }
        $anthropicMessages = @(
            [ordered]@{
                role = "user"
                content = @(
                    [ordered]@{
                        type = "text"
                        text = $InputText
                    }
                )
            }
        )

        return (Invoke-LlmStructuredJsonProvider `
            -PolicyResolved $PolicyResolved `
            -Model $model `
            -BaseUrl $baseUrl `
            -TimeoutMs $timeoutMs `
            -MaxOutputTokens ([int]$PolicyResolved.provider.max_output_tokens) `
            -Temperature ([double]$PolicyResolved.provider.temperature) `
            -TopP ([double]$PolicyResolved.provider.top_p) `
            -Store ([bool]$PolicyResolved.provider.store) `
            -ResponsesInputItems $input `
            -ResponsesTextFormat $textFormat `
            -ChatMessages $chatMessages `
            -ChatResponseFormat $chatResponseFormat `
            -AnthropicMessages $anthropicMessages `
            -SystemInstructions $instructions)
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
        api = "none"
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

    if ([bool]$trigger.active) {
        $providerType = Get-LlmAdviceProviderTypeNormalized -PolicyResolved $policyResolved
        $providerInvokable = $true

        $adviceApiKeyEnv = Get-LlmAdviceProviderApiKeyEnvName -PolicyResolved $policyResolved
        if ((Test-LlmAdviceProviderRequiresRemoteCredential -ProviderType $providerType) -and (-not (Get-OpenAiApiKey -EnvName $adviceApiKeyEnv))) {
            $providerInvokable = $false
            $providerSummary = [pscustomobject]@{
                type = [string]$policyResolved.provider.type
                api = "none"
                model = [string]$policyResolved.provider.model
                abstained = $true
                reason = "missing_intent_advice_api_key"
                latency_ms = 0
                error = $null
            }
        }

        if (-not $providerInvokable) {
            # Safe abstain: do not waste time on git/diff context if provider is unavailable.
        } else {
            $queryText = if ($PromptNormalization -and $PromptNormalization.normalized) { [string]$PromptNormalization.normalized } else { [string]$PromptText }
            $gitContext = Get-VcoGitContextSnippet -PolicyResolved $policyResolved -VcoRepoRoot $RepoRoot -QueryText $queryText -TaskType $TaskType

            # TurboMax: optionally digest diff once, then feed digest (not raw diff) into downstream LLM calls.
            $diffDigestMeta = [pscustomobject]@{ used = $false; reason = "disabled"; latency_ms = 0; api = "none"; chars = 0 }
            try {
                $dd = $policyResolved.enhancements.diff_digest
                $ddEnabled = [bool]($dd -and $dd.enabled)
                $minChars = if ($dd -and $dd.min_diff_chars -ne $null) { [int]$dd.min_diff_chars } else { 0 }
                $maxChars = if ($dd -and $dd.max_digest_chars -ne $null) { [int]$dd.max_digest_chars } else { 1200 }
                $replace = if ($dd -and $dd.replace_diff_in_context -ne $null) { [bool]$dd.replace_diff_in_context } else { $true }
                $includeRaw = if ($dd -and $dd.include_raw_diff_in_context -ne $null) { [bool]$dd.include_raw_diff_in_context } else { $false }

                if ($ddEnabled -and $gitContext -and $gitContext.diff -and ([string]$gitContext.diff).Length -ge $minChars) {
                    $diffTextBefore = [string]$gitContext.diff
                    $digestInput = New-LlmDiffDigestInputText `
                        -PromptText $PromptText `
                        -PromptNormalization $PromptNormalization `
                        -Grade $Grade `
                        -TaskType $TaskType `
                        -GitContext $gitContext `
                        -MaxDigestChars $maxChars

                    $digestResult = Invoke-LlmDiffDigestProvider -PolicyResolved $policyResolved -RepoRoot $RepoRoot -InputText $digestInput -MaxDigestChars $maxChars
                    if ([bool]$digestResult.ok -and (-not [bool]$digestResult.abstained) -and $digestResult.digest) {
                        $gitContext | Add-Member -NotePropertyName diff_digest -NotePropertyValue ([string]$digestResult.digest) -Force
                        $gitContext | Add-Member -NotePropertyName diff_digest_used -NotePropertyValue $true -Force

                        if ($includeRaw) {
                            $gitContext | Add-Member -NotePropertyName diff_raw -NotePropertyValue $diffTextBefore -Force
                        }

                        if ($replace) {
                            $gitContext | Add-Member -NotePropertyName diff -NotePropertyValue ("[diff_digest]`n{0}" -f [string]$digestResult.digest) -Force
                        }

                        $diffDigestMeta = [pscustomobject]@{
                            used = $true
                            reason = "ok"
                            latency_ms = [int]$digestResult.latency_ms
                            api = if ($digestResult -and $digestResult.PSObject.Properties.Name -contains 'api' -and $digestResult.api) { [string]$digestResult.api } else { "unknown" }
                            chars = ([string]$digestResult.digest).Length
                        }
                    } else {
                        $diffDigestMeta = [pscustomobject]@{
                            used = $false
                            reason = if ($digestResult -and $digestResult.reason) { [string]$digestResult.reason } else { "abstained" }
                            latency_ms = if ($digestResult -and $digestResult.latency_ms -ne $null) { [int]$digestResult.latency_ms } else { 0 }
                            api = if ($digestResult -and $digestResult.PSObject.Properties.Name -contains 'api' -and $digestResult.api) { [string]$digestResult.api } else { "unknown" }
                            chars = 0
                        }
                    }
                } else {
                    $diffDigestMeta = [pscustomobject]@{ used = $false; reason = "not_applicable"; latency_ms = 0; api = "none"; chars = 0 }
                }
            } catch {
                $diffDigestMeta = [pscustomobject]@{ used = $false; reason = "digest_error"; latency_ms = 0; api = "none"; chars = 0 }
            }

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

        $providerResult = Invoke-LlmAccelerationProviderCommittee -PolicyResolved $policyResolved -RepoRoot $RepoRoot -InputText $inputText

        $latencyMs = 0
        try {
            if ($providerResult -and $providerResult.latency_ms_total -ne $null) {
                $latencyMs = [int]$providerResult.latency_ms_total
            } elseif ($providerResult -and $providerResult.latency_ms -ne $null) {
                $latencyMs = [int]$providerResult.latency_ms
            }
        } catch { }

        $providerApi = "unknown"
        $providerError = $null
        $committeeUsed = $false
        $committeeMembers = 0
        $committeeSuccesses = 0
        $committeeJudgeUsed = $false
        if ($providerResult -and $providerResult.PSObject) {
            if ($providerResult.PSObject.Properties.Name -contains 'api' -and $providerResult.api) {
                $providerApi = [string]$providerResult.api
            }
            if ($providerResult.PSObject.Properties.Name -contains 'error' -and $providerResult.error) {
                $providerError = [string]$providerResult.error
            }
            if ($providerResult.PSObject.Properties.Name -contains 'committee_used' -and ($providerResult.committee_used -ne $null)) {
                $committeeUsed = [bool]$providerResult.committee_used
            }
            if ($providerResult.PSObject.Properties.Name -contains 'committee_members' -and ($providerResult.committee_members -ne $null)) {
                $committeeMembers = [int]$providerResult.committee_members
            }
            if ($providerResult.PSObject.Properties.Name -contains 'committee_successes' -and ($providerResult.committee_successes -ne $null)) {
                $committeeSuccesses = [int]$providerResult.committee_successes
            }
            if ($providerResult.PSObject.Properties.Name -contains 'committee_judge_used' -and ($providerResult.committee_judge_used -ne $null)) {
                $committeeJudgeUsed = [bool]$providerResult.committee_judge_used
            }
        }

        $diffContextMode = $null
        $diffContextTruncated = $false
        $diffContextSelectedChunks = 0
        $diffContextVectorReason = $null
        if ($gitContext -and $gitContext.PSObject) {
            if ($gitContext.PSObject.Properties.Name -contains 'diff_mode' -and $gitContext.diff_mode) {
                $diffContextMode = [string]$gitContext.diff_mode
            }
            if ($gitContext.PSObject.Properties.Name -contains 'diff_truncated' -and ($gitContext.diff_truncated -ne $null)) {
                $diffContextTruncated = [bool]$gitContext.diff_truncated
            }
            if ($gitContext.PSObject.Properties.Name -contains 'diff_selected_chunks' -and ($gitContext.diff_selected_chunks -ne $null)) {
                $diffContextSelectedChunks = [int]$gitContext.diff_selected_chunks
            }
            if ($gitContext.PSObject.Properties.Name -contains 'diff_vector_reason' -and $gitContext.diff_vector_reason) {
                $diffContextVectorReason = [string]$gitContext.diff_vector_reason
            }
        }

        $providerSummary = [pscustomobject]@{
            type = [string]$policyResolved.provider.type
            api = $providerApi
            model = [string]$policyResolved.provider.model
            abstained = [bool]$providerResult.abstained
            reason = [string]$providerResult.reason
            latency_ms = $latencyMs
            error = $providerError
            committee_used = $committeeUsed
            committee_members = $committeeMembers
            committee_successes = $committeeSuccesses
            committee_judge_used = $committeeJudgeUsed
            diff_digest = $diffDigestMeta
            diff_context = [pscustomobject]@{
                mode = $diffContextMode
                truncated = $diffContextTruncated
                selected_chunks = $diffContextSelectedChunks
                vector_reason = $diffContextVectorReason
            }
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

    # TurboMax: confirm question booster (extra small call; replaces confirm_questions only when beneficial).
    $confirmBoostMeta = [pscustomobject]@{ used = $false; reason = "disabled"; latency_ms = 0; api = "none"; questions = 0 }
    try {
        $cb = $policyResolved.enhancements.confirm_question_booster
        $cbEnabled = [bool]($cb -and $cb.enabled)
        $onlyWhenConfirm = if ($cb -and ($cb.only_when_confirm_required -ne $null)) { [bool]$cb.only_when_confirm_required } else { $true }
        $maxQ = if ($cb -and ($cb.max_questions -ne $null)) { [int]$cb.max_questions } else { 3 }
        $maxQ = [Math]::Max(1, [Math]::Min(3, $maxQ))

        $shouldBoost = $cbEnabled -and $parsed -and (-not $parseError)
        if ($onlyWhenConfirm) { $shouldBoost = $shouldBoost -and [bool]$confirmRequired }

        if ($shouldBoost) {
            $boostInput = New-LlmConfirmQuestionBoosterInputText `
                -PromptText $PromptText `
                -PromptNormalization $PromptNormalization `
                -Grade $Grade `
                -TaskType $TaskType `
                -ExistingConfirmQuestions $confirmQuestions `
                -MaxQuestions $maxQ

            $boostResult = Invoke-LlmConfirmQuestionBoosterProvider -PolicyResolved $policyResolved -RepoRoot $RepoRoot -InputText $boostInput -MaxQuestions $maxQ
            if ($boostResult -and [bool]$boostResult.ok -and (-not [bool]$boostResult.abstained) -and $boostResult.confirm_questions -and $boostResult.confirm_questions.Count -gt 0) {
                $confirmQuestions = @($boostResult.confirm_questions | Where-Object { $_ } | Select-Object -First $maxQ)
                $confirmBoostMeta = [pscustomobject]@{
                    used = $true
                    reason = "ok"
                    latency_ms = if ($boostResult.latency_ms -ne $null) { [int]$boostResult.latency_ms } else { 0 }
                    api = if ($boostResult -and $boostResult.PSObject.Properties.Name -contains 'api' -and $boostResult.api) { [string]$boostResult.api } else { "unknown" }
                    questions = $confirmQuestions.Count
                }
            } else {
                $confirmBoostMeta = [pscustomobject]@{
                    used = $false
                    reason = if ($boostResult -and $boostResult.reason) { [string]$boostResult.reason } else { "abstained" }
                    latency_ms = if ($boostResult -and $boostResult.latency_ms -ne $null) { [int]$boostResult.latency_ms } else { 0 }
                    api = if ($boostResult -and $boostResult.PSObject.Properties.Name -contains 'api' -and $boostResult.api) { [string]$boostResult.api } else { "unknown" }
                    questions = 0
                }
            }
        } else {
            $confirmBoostMeta = [pscustomobject]@{ used = $false; reason = "not_applicable"; latency_ms = 0; api = "none"; questions = 0 }
        }
    } catch {
        $confirmBoostMeta = [pscustomobject]@{ used = $false; reason = "boost_error"; latency_ms = 0; api = "none"; questions = 0 }
    }
    try { $providerSummary | Add-Member -NotePropertyName confirm_question_booster -NotePropertyValue $confirmBoostMeta -Force } catch { }

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
