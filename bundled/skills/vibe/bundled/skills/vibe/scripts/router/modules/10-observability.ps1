# Auto-extracted router module. Keep function bodies behavior-identical.

function Write-ObservabilityRouteEvent {
    param(
        [string]$PromptText,
        [object]$Result,
        [object]$ObservabilityPolicy,
        [string]$RepoRoot
    )

    if (-not $ObservabilityPolicy -or -not [bool]$ObservabilityPolicy.enabled) { return $null }
    if (-not $Result) { return $null }
    if (-not $ObservabilityPolicy.telemetry -or -not [bool]$ObservabilityPolicy.telemetry.write_jsonl) { return $null }

    $mode = if ($ObservabilityPolicy.mode) { [string]$ObservabilityPolicy.mode } else { "shadow" }
    $sampleRates = if ($ObservabilityPolicy.telemetry.sample_rates) { $ObservabilityPolicy.telemetry.sample_rates } else { $null }
    $sampleRate = 1.0
    if ($sampleRates) {
        $keys = @($sampleRates.PSObject.Properties.Name)
        if ($keys -contains $mode) {
            $sampleRate = [double]$sampleRates.$mode
        }
    }
    $sampleRate = [Math]::Max(0.0, [Math]::Min(1.0, $sampleRate))

    $forceCapture = $false
    if ($ObservabilityPolicy.telemetry.force_capture) {
        $force = $ObservabilityPolicy.telemetry.force_capture
        if ($force.route_modes -and (@($force.route_modes) -contains [string]$Result.route_mode)) {
            $forceCapture = $true
        }
        if (-not $forceCapture -and [bool]$force.overlay_confirm_required -and (Test-OverlayConfirmRequired -Result $Result)) {
            $forceCapture = $true
        }
    }

    if (-not $forceCapture -and $sampleRate -lt 1.0) {
        $draw = [double](Get-Random -Minimum 0.0 -Maximum 1.0)
        if ($draw -gt $sampleRate) {
            return $null
        }
    }

    $profilePolicy = $ObservabilityPolicy.profile_dimensions
    $userPolicy = $ObservabilityPolicy.user_dimensions

    $osText = [string][Environment]::OSVersion.Platform
    $shellText = "powershell-{0}" -f $PSVersionTable.PSVersion.Major
    $cpuBucket = Get-CpuBucket
    $locale = "unknown"
    try {
        $locale = (Get-Culture).Name
    } catch { }
    $proxyHint = [bool]($env:HTTP_PROXY -or $env:HTTPS_PROXY -or $env:ALL_PROXY)

    $envParts = @()
    if ($profilePolicy -and [bool]$profilePolicy.include_os) { $envParts += "os=$osText" }
    if ($profilePolicy -and [bool]$profilePolicy.include_shell) { $envParts += "shell=$shellText" }
    if ($profilePolicy -and [bool]$profilePolicy.include_cpu_bucket) { $envParts += "cpu=$cpuBucket" }
    if ($profilePolicy -and [bool]$profilePolicy.include_locale) { $envParts += "locale=$locale" }
    if ($profilePolicy -and [bool]$profilePolicy.include_proxy_hint) { $envParts += "proxy=$proxyHint" }
    $envProfileRaw = ($envParts -join "|")
    $envProfileId = (Get-HashHex -InputText $envProfileRaw)
    if ($envProfileId.Length -gt 12) { $envProfileId = $envProfileId.Substring(0, 12) }

    $languageMix = if ($userPolicy -and [bool]$userPolicy.include_language_mix) { Get-LanguageMixTag -PromptText $PromptText } else { "unknown" }
    $explicitCommand = if ($userPolicy -and [bool]$userPolicy.include_explicit_command_hint) { Test-ExplicitCommandHint -PromptText $PromptText } else { $false }

    $userKey = "anonymous"
    if ($userPolicy -and [bool]$userPolicy.include_user_hash) {
        $rawUser = if ($env:USERNAME) { [string]$env:USERNAME } elseif ($env:USER) { [string]$env:USER } else { "unknown-user" }
        $userKey = Get-HashHex -InputText $rawUser
        if ($userKey.Length -gt 12) { $userKey = $userKey.Substring(0, 12) }
    }

    $selectedPack = if ($Result.selected) { [string]$Result.selected.pack_id } else { "none" }
    $selectedSkill = if ($Result.selected) { [string]$Result.selected.skill } else { "none" }
    $scenarioKey = "{0}|{1}|{2}|{3}|{4}|{5}" -f [string]$Result.task_type, [string]$Result.grade, [string]$Result.route_mode, $selectedPack, $languageMix, $envProfileId

    $storePromptRaw = [bool]$ObservabilityPolicy.telemetry.store_prompt_raw
    $promptExcerptMax = [int]$ObservabilityPolicy.telemetry.prompt_excerpt_max_chars
    $promptExcerpt = $null
    if ($storePromptRaw -and $promptExcerptMax -gt 0 -and $PromptText) {
        $len = [Math]::Min($promptExcerptMax, $PromptText.Length)
        $promptExcerpt = $PromptText.Substring(0, $len)
    }

    $event = [pscustomobject]@{
        timestamp_utc = [DateTime]::UtcNow.ToString("o")
        schema_version = if ($ObservabilityPolicy.event_schema_version) { [string]$ObservabilityPolicy.event_schema_version } else { "v1" }
        mode = $mode
        scenario_key = $scenarioKey
        environment_profile_id = $envProfileId
        user_profile_id = $userKey
        language_mix = $languageMix
        explicit_command_hint = [bool]$explicitCommand
        prompt_hash = Get-HashHex -InputText ([string]$PromptText)
        prompt_excerpt = $promptExcerpt
        route = [pscustomobject]@{
            grade = [string]$Result.grade
            task_type = [string]$Result.task_type
            route_mode = [string]$Result.route_mode
            route_reason = [string]$Result.route_reason
            confidence = [double]$Result.confidence
            top1_top2_gap = [double]$Result.top1_top2_gap
            candidate_signal = [double]$Result.candidate_signal
            selected_pack = $selectedPack
            selected_skill = $selectedSkill
            deep_discovery_route_filter_applied = [bool]$Result.deep_discovery_route_filter_applied
            deep_discovery_route_mode_override = [bool]$Result.deep_discovery_route_mode_override
            heartbeat_status = if ($Result.heartbeat_status) { [string]$Result.heartbeat_status.current_status } else { "disabled" }
            heartbeat_pulse_count = if ($Result.heartbeat_status -and $Result.heartbeat_status.pulse_count -ne $null) { [int]$Result.heartbeat_status.pulse_count } else { 0 }
            heartbeat_stall_score = if ($Result.heartbeat_status -and $Result.heartbeat_status.stall_score -ne $null) { [double]$Result.heartbeat_status.stall_score } else { 0.0 }
        }
        overlays = [pscustomobject]@{
            deep_discovery_triggered = [bool]($Result.deep_discovery_advice -and $Result.deep_discovery_advice.trigger_active)
            deep_discovery_confirm_required = [bool]($Result.deep_discovery_advice -and $Result.deep_discovery_advice.confirm_required)
            deep_discovery_route_filter_applied = [bool]$Result.deep_discovery_route_filter_applied
            ai_rerank_triggered = [bool]($Result.ai_rerank_advice -and $Result.ai_rerank_advice.trigger -and $Result.ai_rerank_advice.trigger.active)
            ai_rerank_would_override = [bool]($Result.ai_rerank_advice -and $Result.ai_rerank_advice.would_override)
            ai_rerank_route_override = [bool]$Result.ai_rerank_route_override
            prompt_confirm_required = [bool]($Result.prompt_overlay_advice -and $Result.prompt_overlay_advice.confirm_required)
            data_scale_confirm_required = [bool]($Result.data_scale_advice -and $Result.data_scale_advice.confirm_required)
            quality_debt_confirm_required = [bool]($Result.quality_debt_advice -and $Result.quality_debt_advice.confirm_required)
            framework_interop_confirm_required = [bool]($Result.framework_interop_advice -and $Result.framework_interop_advice.confirm_required)
            ml_lifecycle_confirm_required = [bool]($Result.ml_lifecycle_advice -and $Result.ml_lifecycle_advice.confirm_required)
            python_clean_code_confirm_required = [bool]($Result.python_clean_code_advice -and $Result.python_clean_code_advice.confirm_required)
            system_design_confirm_required = [bool]($Result.system_design_advice -and $Result.system_design_advice.confirm_required)
            cuda_kernel_confirm_required = [bool]($Result.cuda_kernel_advice -and $Result.cuda_kernel_advice.confirm_required)
            retrieval_confirm_required = [bool]($Result.retrieval_advice -and $Result.retrieval_advice.confirm_required)
            retrieval_profile_id = if ($Result.retrieval_advice -and $Result.retrieval_advice.profile_id) { [string]$Result.retrieval_advice.profile_id } else { "none" }
            retrieval_needs_requery = [bool]($Result.retrieval_advice -and $Result.retrieval_advice.coverage_gate -and $Result.retrieval_advice.coverage_gate.needs_requery)
            heartbeat_confirm_required = [bool]($Result.heartbeat_advice -and $Result.heartbeat_advice.confirm_required)
            dialectic_team_explicit_requested = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.explicit_requested)
            dialectic_team_mode_allowed = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.team_mode_allowed)
            dialectic_team_should_apply = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.should_apply_team_mode)
            dialectic_team_confirm_required = [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.confirm_required)
            dialectic_team_route_override = [bool]$Result.dialectic_team_route_override
            daily_dialectic_scope_applicable = [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.scope_applicable)
            daily_dialectic_confirm_required = [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.confirm_required)
            any_confirm_required = (Test-OverlayConfirmRequired -Result $Result)
        }
        heartbeat = [pscustomobject]@{
            enabled = [bool]($Result.heartbeat_advice -and $Result.heartbeat_advice.enabled)
            mode = if ($Result.heartbeat_advice) { [string]$Result.heartbeat_advice.mode } else { "off" }
            enforcement = if ($Result.heartbeat_advice) { [string]$Result.heartbeat_advice.enforcement } else { "none" }
            reason = if ($Result.heartbeat_advice) { [string]$Result.heartbeat_advice.reason } else { "policy_off" }
            status = if ($Result.heartbeat_status) { [string]$Result.heartbeat_status.current_status } else { "disabled" }
            lifecycle_status = if ($Result.heartbeat_status) { [string]$Result.heartbeat_status.lifecycle_status } else { "disabled" }
            pulse_count = if ($Result.heartbeat_status -and $Result.heartbeat_status.pulse_count -ne $null) { [int]$Result.heartbeat_status.pulse_count } else { 0 }
            stall_score = if ($Result.heartbeat_status -and $Result.heartbeat_status.stall_score -ne $null) { [double]$Result.heartbeat_status.stall_score } else { 0.0 }
            suspect_stall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.suspect_stall } else { $false }
            hard_stall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.hard_stall } else { $false }
            auto_diagnosis_triggered = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.auto_diagnosis_triggered } else { $false }
        }
    }

    $telemetryRel = if ($ObservabilityPolicy.telemetry.output_dir) { [string]$ObservabilityPolicy.telemetry.output_dir } else { "outputs/telemetry" }
    $prefix = if ($ObservabilityPolicy.telemetry.file_prefix) { [string]$ObservabilityPolicy.telemetry.file_prefix } else { "route-events" }
    $outputDir = Join-Path $RepoRoot $telemetryRel
    $fileName = "{0}-{1}.jsonl" -f $prefix, (Get-Date -Format "yyyyMMdd")
    $outputPath = Join-Path $outputDir $fileName

    try {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        ($event | ConvertTo-Json -Depth 12 -Compress) | Add-Content -LiteralPath $outputPath -Encoding UTF8
        return [pscustomobject]@{
            wrote = $true
            path = $outputPath
        }
    } catch {
        if ($ObservabilityPolicy.fallback_behavior -and [string]$ObservabilityPolicy.fallback_behavior.on_write_error -eq "continue_without_telemetry") {
            return [pscustomobject]@{
                wrote = $false
                error = $_.Exception.Message
            }
        }
        throw
    }
}



