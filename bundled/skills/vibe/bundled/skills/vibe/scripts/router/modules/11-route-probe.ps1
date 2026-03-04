# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-RouteProbeAdviceSummary {
    param([object]$Advice)

    if (-not $Advice) { return $null }

    $summary = [ordered]@{}
    $interestingKeys = @(
        "enabled",
        "mode",
        "scope_applicable",
        "strict_scope_applicable",
        "scope_strategy",
        "signal_relaxed_min_score",
        "signal_relaxed_applied",
        "task_applicable",
        "grade_applicable",
        "pack_applicable",
        "skill_applicable",
        "enforcement",
        "reason",
        "confirm_required",
        "auto_override",
        "override_candidate_allowed",
        "recommended_skill",
        "confidence",
        "trigger_active",
        "trigger_score",
        "interview_required",
        "contract_completeness",
        "route_filter_applied",
        "would_apply_filter",
        "preserve_routing_assignment",
        "route_override_applied",
        "would_override",
        "override_target_pack",
        "override_target_skill",
        "profile_id",
        "profile_confidence",
        "profile_ambiguous",
        "needs_requery",
        "coverage_score",
        "status",
        "lifecycle_status",
        "pulse_count",
        "stall_score",
        "suspect_stall",
        "hard_stall",
        "auto_diagnosis_triggered",
        "user_brief_interval_sec",
        "debug_tick_interval_sec",
        "elapsed_sec"
    )

    $keys = @($Advice.PSObject.Properties.Name)
    foreach ($key in $interestingKeys) {
        if ($keys -contains $key) {
            $summary[$key] = $Advice.$key
        }
    }

    return [pscustomobject]$summary
}

function Get-RouteProbePolicyValue {
    param(
        [object]$ProbePolicy,
        [string]$Key,
        [object]$DefaultValue
    )

    if (-not $ProbePolicy) { return $DefaultValue }
    $keys = @($ProbePolicy.PSObject.Properties.Name)
    if ($keys -contains $Key) {
        return $ProbePolicy.$Key
    }
    return $DefaultValue
}

function New-RouteProbeContext {
    param(
        [switch]$ProbeSwitch,
        [string]$PromptText,
        [string]$Grade,
        [string]$TaskType,
        [string]$RepoRoot,
        [string]$ProbeLabel,
        [string]$ProbeOutputDir,
        [switch]$ProbeIncludePrompt,
        [int]$ProbePromptMaxChars = 1600,
        [object]$ProbePolicy
    )

    $enabledFromPolicy = [bool](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "enabled" -DefaultValue $false)
    $enabled = [bool]$ProbeSwitch -or $enabledFromPolicy

    if (-not $enabled) {
        return [pscustomobject]@{
            enabled = $false
        }
    }

    $resolvedOutputDir = if ($ProbeOutputDir) {
        if ([System.IO.Path]::IsPathRooted($ProbeOutputDir)) {
            $ProbeOutputDir
        } else {
            Join-Path $RepoRoot $ProbeOutputDir
        }
    } else {
        $configured = [string](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "output_dir" -DefaultValue "outputs/route-probe")
        if ([System.IO.Path]::IsPathRooted($configured)) {
            $configured
        } else {
            Join-Path $RepoRoot $configured
        }
    }

    $includePrompt = [bool]$ProbeIncludePrompt
    if (-not $ProbeIncludePrompt) {
        $includePrompt = [bool](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "include_prompt" -DefaultValue $false)
    }

    $maxCharsConfigured = [int](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "prompt_max_chars" -DefaultValue 1600)
    $promptMaxChars = if ($ProbePromptMaxChars -gt 0) { $ProbePromptMaxChars } else { $maxCharsConfigured }
    if ($promptMaxChars -le 0) { $promptMaxChars = 1600 }

    $writeJson = [bool](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "write_json" -DefaultValue $true)
    $writeMarkdown = [bool](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "write_markdown" -DefaultValue $true)
    $runtimePromptFoldOutsideScope = [bool](Get-RouteProbePolicyValue -ProbePolicy $ProbePolicy -Key "runtime_prompt_fold_outside_scope" -DefaultValue $true)

    $probeId = "routeprobe-{0}-{1}" -f (Get-Date -Format "yyyyMMdd-HHmmssfff"), ([Guid]::NewGuid().ToString("N").Substring(0, 8))
    $promptHash = Get-HashHex -InputText ([string]$PromptText)
    $promptSnippet = $null
    if ($includePrompt -and $PromptText) {
        $len = [Math]::Min($promptMaxChars, $PromptText.Length)
        $promptSnippet = $PromptText.Substring(0, $len)
    }

    return [pscustomobject]@{
        enabled = $true
        id = $probeId
        created_utc = [DateTime]::UtcNow.ToString("o")
        grade = $Grade
        task_type = $TaskType
        label = if ($ProbeLabel) { $ProbeLabel } else { "{0}-{1}" -f $TaskType, $Grade }
        output_dir = $resolvedOutputDir
        write_json = $writeJson
        write_markdown = $writeMarkdown
        runtime_prompt_fold_outside_scope = $runtimePromptFoldOutsideScope
        include_prompt = $includePrompt
        prompt_hash = $promptHash
        prompt_snippet = $promptSnippet
        prompt_length = if ($PromptText) { $PromptText.Length } else { 0 }
        next_seq = 1
        events = (New-Object System.Collections.ArrayList)
    }
}

function Add-RouteProbeEvent {
    param(
        [object]$Context,
        [string]$Stage,
        [object]$Data,
        [string]$Note
    )

    if (-not $Context -or -not $Context.enabled) { return }

    $snapshot = $null
    if ($null -ne $Data) {
        try {
            $snapshot = ($Data | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
        } catch {
            $snapshot = [string]$Data
        }
    }

    $entry = [pscustomobject]@{
        seq = [int]$Context.next_seq
        timestamp_utc = [DateTime]::UtcNow.ToString("o")
        stage = $Stage
        note = $Note
        data = $snapshot
    }

    [void]$Context.events.Add($entry)
    $Context.next_seq = [int]$Context.next_seq + 1
}

function Get-RouteProbeProtocolHint {
    param(
        [string]$Grade,
        [string]$TaskType
    )

    if ($Grade -eq "XL") { return "protocols/team.md" }
    if ($Grade -eq "L") {
        if ($TaskType -in @("planning", "research")) { return "protocols/think.md" }
        if ($TaskType -in @("coding", "debug")) { return "protocols/do.md" }
        return "protocols/review.md"
    }

    if ($TaskType -eq "planning") { return "M-flow: think-harder + sc:design" }
    if ($TaskType -eq "coding") { return "M-flow: tdd-guide + code-reviewer" }
    if ($TaskType -eq "debug") { return "M-flow: systematic-debugging" }
    if ($TaskType -eq "research") { return "M-flow: sc:research or deep-research" }
    return "M-flow: code-reviewer + security-reviewer"
}

function Get-RouteRuntimeStatePrompt {
    param(
        [string]$PromptText,
        [object]$Result,
        [bool]$FoldOutsideScope = $true
    )

    $selectedPack = if ($Result.selected) { [string]$Result.selected.pack_id } else { "none" }
    $selectedSkill = if ($Result.selected) { [string]$Result.selected.skill } else { "none" }
    $protocolHint = Get-RouteProbeProtocolHint -Grade ([string]$Result.grade) -TaskType ([string]$Result.task_type)

    $overlayLines = @()
    $foldedOverlays = @()
    $overlaySpecs = @(
        @{ Name = "deep_discovery"; Advice = $Result.deep_discovery_advice },
        @{ Name = "dialectic_team"; Advice = $Result.dialectic_team_advice },
        @{ Name = "daily_dialectic"; Advice = $Result.daily_dialectic_advice },
        @{ Name = "openspec"; Advice = $Result.openspec_advice },
        @{ Name = "gsd"; Advice = $Result.gsd_overlay_advice },
        @{ Name = "prompt"; Advice = $Result.prompt_overlay_advice },
        @{ Name = "memory"; Advice = $Result.memory_governance_advice },
        @{ Name = "ai_rerank"; Advice = $Result.ai_rerank_advice },
        @{ Name = "data_scale"; Advice = $Result.data_scale_advice },
        @{ Name = "quality_debt"; Advice = $Result.quality_debt_advice },
        @{ Name = "framework_interop"; Advice = $Result.framework_interop_advice },
        @{ Name = "ml_lifecycle"; Advice = $Result.ml_lifecycle_advice },
        @{ Name = "python_clean_code"; Advice = $Result.python_clean_code_advice },
        @{ Name = "system_design"; Advice = $Result.system_design_advice },
        @{ Name = "cuda_kernel"; Advice = $Result.cuda_kernel_advice },
        @{ Name = "retrieval"; Advice = $Result.retrieval_advice }
    )

    foreach ($overlaySpec in $overlaySpecs) {
        $advice = $overlaySpec.Advice
        if (-not $advice) { continue }
        $digest = Get-RouteProbeAdviceSummary -Advice $advice
        if (-not $digest) { continue }

        $mode = if ($digest.PSObject.Properties.Name -contains "mode") { [string]$digest.mode } else { "n/a" }
        $scope = if ($digest.PSObject.Properties.Name -contains "scope_applicable") { [bool]$digest.scope_applicable } else { $false }
        $enforcement = if ($digest.PSObject.Properties.Name -contains "enforcement") { [string]$digest.enforcement } else { "none" }
        $reason = if ($digest.PSObject.Properties.Name -contains "reason") { [string]$digest.reason } else { "n/a" }
        $recommended = if ($digest.PSObject.Properties.Name -contains "recommended_skill" -and $digest.recommended_skill) { [string]$digest.recommended_skill } else { "" }
        $confirmRequired = if ($digest.PSObject.Properties.Name -contains "confirm_required") { [bool]$digest.confirm_required } else { $false }
        $autoOverride = if ($digest.PSObject.Properties.Name -contains "auto_override") { [bool]$digest.auto_override } else { $false }
        $routeOverrideApplied = if ($digest.PSObject.Properties.Name -contains "route_override_applied") { [bool]$digest.route_override_applied } else { $false }
        $wouldOverride = if ($digest.PSObject.Properties.Name -contains "would_override") { [bool]$digest.would_override } else { $false }
        $isOutsideScope = (-not $scope) -or ($reason -eq "outside_scope")
        $isActionable = $confirmRequired -or $autoOverride -or $routeOverrideApplied -or $wouldOverride -or [bool]$recommended
        if ($FoldOutsideScope -and $isOutsideScope -and -not $isActionable) {
            $foldedOverlays += ("{0}({1})" -f $overlaySpec.Name, $reason)
            continue
        }
        $recommendedSuffix = if ($recommended) { " | recommended_skill=$recommended" } else { "" }
        $overlayLines += ("- {0}: mode={1} scope={2} enforcement={3} reason={4}{5}" -f $overlaySpec.Name, $mode, $scope, $enforcement, $reason, $recommendedSuffix)
    }

    if ($foldedOverlays.Count -gt 0) {
        $overlayLines += ("- [folded] {0} outside-scope overlays hidden: {1}" -f $foldedOverlays.Count, ($foldedOverlays -join ", "))
    }

    if ($overlayLines.Count -eq 0) {
        $overlayLines += "- none"
    }

    $heartbeatMode = if ($Result.heartbeat_advice -and $Result.heartbeat_advice.mode) { [string]$Result.heartbeat_advice.mode } else { "off" }
    $heartbeatStatus = if ($Result.heartbeat_status -and $Result.heartbeat_status.current_status) { [string]$Result.heartbeat_status.current_status } else { "disabled" }
    $heartbeatLifecycle = if ($Result.heartbeat_status -and $Result.heartbeat_status.lifecycle_status) { [string]$Result.heartbeat_status.lifecycle_status } else { "disabled" }
    $heartbeatPulseCount = if ($Result.heartbeat_status -and $Result.heartbeat_status.pulse_count -ne $null) { [int]$Result.heartbeat_status.pulse_count } else { 0 }
    $heartbeatStallScore = if ($Result.heartbeat_status -and $Result.heartbeat_status.stall_score -ne $null) { [double]$Result.heartbeat_status.stall_score } else { 0.0 }
    $heartbeatHardStall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.hard_stall } else { $false }
    $heartbeatSuspectStall = if ($Result.heartbeat_status) { [bool]$Result.heartbeat_status.suspect_stall } else { $false }
    $heartbeatConfirmRequired = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.confirm_required } else { $false }

    $stateLines = @(
        "[VCO Runtime State Prompt]",
        ("Input task: {0}" -f $PromptText),
        ("Route decision: grade={0}, task_type={1}, route_mode={2}, route_reason={3}" -f $Result.grade, $Result.task_type, $Result.route_mode, $Result.route_reason),
        ("Selected route: pack={0}, skill={1}, confidence={2}, top1_top2_gap={3}" -f $selectedPack, $selectedSkill, $Result.confidence, $Result.top1_top2_gap),
        ("Deep discovery: trigger_active={0}, trigger_score={1}, contract_completeness={2}, route_filter_applied={3}" -f `
            [bool]($Result.deep_discovery_advice -and $Result.deep_discovery_advice.trigger_active), `
            $(if ($Result.deep_discovery_advice -and $Result.deep_discovery_advice.trigger_score -ne $null) { [double]$Result.deep_discovery_advice.trigger_score } else { 0.0 }), `
            $(if ($Result.intent_contract -and $Result.intent_contract.completeness -ne $null) { [double]$Result.intent_contract.completeness } else { 0.0 }), `
            [bool]$Result.deep_discovery_route_filter_applied),
        ("Dialectic governance: team_explicit_requested={0}, team_mode={1}, daily_guard_scope={2}, daily_guard_confirm_required={3}" -f `
            [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.explicit_requested), `
            [bool]($Result.dialectic_team_advice -and $Result.dialectic_team_advice.should_apply_team_mode), `
            [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.scope_applicable), `
            [bool]($Result.daily_dialectic_advice -and $Result.daily_dialectic_advice.confirm_required)),
        ("Execution protocol hint: {0}" -f $protocolHint),
        "Quality contract: enforce P5 evidence, V2 completion gate, and V3 pipeline for coding tasks.",
        "Memory contract: state_store=session, Serena=decisions, ruflo=short cache, Cognee=long-term graph, episodic-memory=disabled.",
        ("Heartbeat guard: mode={0}, status={1}, lifecycle={2}, pulse_count={3}, stall_score={4}, suspect_stall={5}, hard_stall={6}, confirm_required={7}" -f `
            $heartbeatMode, $heartbeatStatus, $heartbeatLifecycle, $heartbeatPulseCount, $heartbeatStallScore, $heartbeatSuspectStall, $heartbeatHardStall, $heartbeatConfirmRequired),
        "Overlay injections:",
        ($overlayLines -join "`n"),
        ("Execution handoff: Route this task to skill '{0}' under pack '{1}' and follow protocol '{2}'." -f $selectedSkill, $selectedPack, $protocolHint)
    )

    return ($stateLines -join "`n")
}

function Write-RouteProbeArtifact {
    param(
        [object]$Context,
        [string]$PromptText,
        [object]$Result
    )

    if (-not $Context -or -not $Context.enabled) { return $null }

    $promptForRuntime = if ($Context.include_prompt) {
        $PromptText
    } else {
        "[prompt-redacted; prompt_hash={0}]" -f $Context.prompt_hash
    }

    $runtimeStatePrompt = Get-RouteRuntimeStatePrompt `
        -PromptText $promptForRuntime `
        -Result $Result `
        -FoldOutsideScope ([bool]$Context.runtime_prompt_fold_outside_scope)
    $selectedPack = if ($Result.selected) { [string]$Result.selected.pack_id } else { "none" }
    $selectedSkill = if ($Result.selected) { [string]$Result.selected.skill } else { "none" }

    $safeLabel = if ($Context.label) { [Regex]::Replace([string]$Context.label, "[^a-zA-Z0-9\-_]+", "-").Trim("-") } else { "trace" }
    if (-not $safeLabel) { $safeLabel = "trace" }
    $baseName = "{0}-{1}" -f $Context.id, $safeLabel

    $payload = [ordered]@{
        probe_id = $Context.id
        created_utc = $Context.created_utc
        label = $Context.label
        request = [ordered]@{
            grade = $Context.grade
            task_type = $Context.task_type
            prompt_hash = $Context.prompt_hash
            prompt_length = $Context.prompt_length
            prompt_included = $Context.include_prompt
            prompt = $Context.prompt_snippet
        }
        events = @($Context.events)
        final_state = [ordered]@{
            route_mode = $Result.route_mode
            route_reason = $Result.route_reason
            confidence = $Result.confidence
            top1_top2_gap = $Result.top1_top2_gap
            selected_pack = $selectedPack
            selected_skill = $selectedSkill
            deep_discovery_trigger_active = [bool]($Result.deep_discovery_advice -and $Result.deep_discovery_advice.trigger_active)
            deep_discovery_trigger_score = if ($Result.deep_discovery_advice -and $Result.deep_discovery_advice.trigger_score -ne $null) { [double]$Result.deep_discovery_advice.trigger_score } else { 0.0 }
            deep_discovery_contract_completeness = if ($Result.intent_contract -and $Result.intent_contract.completeness -ne $null) { [double]$Result.intent_contract.completeness } else { 0.0 }
            deep_discovery_route_filter_applied = [bool]$Result.deep_discovery_route_filter_applied
            deep_discovery_route_mode_override = [bool]$Result.deep_discovery_route_mode_override
            ai_rerank_route_override = $Result.ai_rerank_route_override
            prompt_overlay_route_override = $Result.prompt_overlay_route_override
            data_scale_route_override = $Result.data_scale_route_override
            retrieval_profile_id = if ($Result.retrieval_advice -and $Result.retrieval_advice.profile_id) { [string]$Result.retrieval_advice.profile_id } else { "none" }
            retrieval_profile_confidence = if ($Result.retrieval_advice -and $Result.retrieval_advice.profile_confidence -ne $null) { [double]$Result.retrieval_advice.profile_confidence } else { 0.0 }
            retrieval_profile_ambiguous = if ($Result.retrieval_advice) { [bool]$Result.retrieval_advice.profile_ambiguous } else { $false }
            retrieval_needs_requery = if ($Result.retrieval_advice -and $Result.retrieval_advice.coverage_gate) { [bool]$Result.retrieval_advice.coverage_gate.needs_requery } else { $false }
            retrieval_confirm_required = if ($Result.retrieval_advice) { [bool]$Result.retrieval_advice.confirm_required } else { $false }
            heartbeat_mode = if ($Result.heartbeat_advice -and $Result.heartbeat_advice.mode) { [string]$Result.heartbeat_advice.mode } else { "off" }
            heartbeat_status = if ($Result.heartbeat_status -and $Result.heartbeat_status.current_status) { [string]$Result.heartbeat_status.current_status } else { "disabled" }
            heartbeat_lifecycle_status = if ($Result.heartbeat_status -and $Result.heartbeat_status.lifecycle_status) { [string]$Result.heartbeat_status.lifecycle_status } else { "disabled" }
            heartbeat_pulse_count = if ($Result.heartbeat_status -and $Result.heartbeat_status.pulse_count -ne $null) { [int]$Result.heartbeat_status.pulse_count } else { 0 }
            heartbeat_stall_score = if ($Result.heartbeat_status -and $Result.heartbeat_status.stall_score -ne $null) { [double]$Result.heartbeat_status.stall_score } else { 0.0 }
            heartbeat_confirm_required = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.confirm_required } else { $false }
            heartbeat_auto_diagnosis_triggered = if ($Result.heartbeat_advice) { [bool]$Result.heartbeat_advice.auto_diagnosis_triggered } else { $false }
        }
        runtime_state_prompt = $runtimeStatePrompt
    }

    $jsonPath = $null
    $markdownPath = $null
    New-Item -ItemType Directory -Path $Context.output_dir -Force | Out-Null

    if ($Context.write_json) {
        $jsonPath = Join-Path $Context.output_dir ("{0}.json" -f $baseName)
        $payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    }

    if ($Context.write_markdown) {
        $markdownPath = Join-Path $Context.output_dir ("{0}.md" -f $baseName)
        $md = @(
            ("# Route Probe {0}" -f $Context.id),
            "",
            ("- Label: {0}" -f $Context.label),
            ("- Grade/Task: {0}/{1}" -f $Context.grade, $Context.task_type),
            ("- Prompt hash: {0}" -f $Context.prompt_hash),
            ("- Route: {0} ({1})" -f $Result.route_mode, $Result.route_reason),
            ("- Selected: pack={0}, skill={1}" -f $selectedPack, $selectedSkill),
            "",
            "## Runtime State Prompt",
            '```text',
            $runtimeStatePrompt,
            '```',
            "",
            "## Events",
            "| Seq | Stage | Note |",
            "| --- | --- | --- |"
        )

        foreach ($event in @($Context.events)) {
            $note = if ($event.note) { [string]$event.note } else { "" }
            $md += ("| {0} | {1} | {2} |" -f $event.seq, $event.stage, $note.Replace("|", "\|"))
        }

        $md -join "`n" | Set-Content -LiteralPath $markdownPath -Encoding UTF8
    }

    return [pscustomobject]@{
        enabled = $true
        probe_id = $Context.id
        output_dir = $Context.output_dir
        json_path = $jsonPath
        markdown_path = $markdownPath
        runtime_state_prompt = $runtimeStatePrompt
    }
}

