# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-HeartbeatPolicyValue {
    param(
        [object]$Container,
        [string]$Key,
        [object]$DefaultValue
    )

    if (-not $Container) { return $DefaultValue }
    $keys = @($Container.PSObject.Properties.Name)
    if ($keys -contains $Key) {
        return $Container.$Key
    }
    return $DefaultValue
}

function Get-HeartbeatGradePolicy {
    param(
        [object]$HeartbeatPolicy,
        [string]$Grade
    )

    if (-not $HeartbeatPolicy -or -not $HeartbeatPolicy.policy_by_grade) { return $null }
    $gradePolicies = $HeartbeatPolicy.policy_by_grade
    $gradeKeys = @($gradePolicies.PSObject.Properties.Name)
    if ($gradeKeys -contains $Grade) {
        return $gradePolicies.$Grade
    }
    return $null
}

function Get-HeartbeatStallAssessment {
    param(
        [double]$SilenceSec,
        [double]$NoStateChangeSec,
        [double]$SoftStallSec,
        [double]$HardStallSec,
        [double]$MaxNoStateChangeSec
    )

    $safeHard = if ($HardStallSec -gt 0) { $HardStallSec } else { 1.0 }
    $safeNoState = if ($MaxNoStateChangeSec -gt 0) { $MaxNoStateChangeSec } else { 1.0 }
    $silenceScore = [Math]::Min(1.0, [Math]::Max(0.0, ($SilenceSec / $safeHard)))
    $noStateScore = [Math]::Min(1.0, [Math]::Max(0.0, ($NoStateChangeSec / $safeNoState)))
    $stallScore = [Math]::Round([Math]::Max($silenceScore, $noStateScore), 4)

    $hardStall = (($HardStallSec -le 0 -and $SilenceSec -ge 0) -or ($SilenceSec -ge $HardStallSec))
    if (-not $hardStall -and $MaxNoStateChangeSec -gt 0) {
        $hardStall = ($NoStateChangeSec -ge $MaxNoStateChangeSec)
    } elseif (-not $hardStall -and $MaxNoStateChangeSec -le 0 -and $NoStateChangeSec -ge 0) {
        $hardStall = $true
    }

    $suspectStall = $false
    if (-not $hardStall) {
        if ($SoftStallSec -le 0) {
            $suspectStall = ($SilenceSec -ge 0)
        } else {
            $suspectStall = ($SilenceSec -ge $SoftStallSec)
        }
    }

    return [pscustomobject]@{
        stall_score = [double]$stallScore
        suspect_stall = [bool]$suspectStall
        hard_stall = [bool]$hardStall
    }
}

function New-HeartbeatContext {
    param(
        [object]$HeartbeatPolicy,
        [string]$Grade,
        [string]$TaskType
    )

    $mode = if ($HeartbeatPolicy -and $HeartbeatPolicy.mode) { [string]$HeartbeatPolicy.mode } else { "off" }
    $enabled = [bool]($HeartbeatPolicy -and $HeartbeatPolicy.enabled -ne $null -and [bool]$HeartbeatPolicy.enabled -and $mode -ne "off")
    $preserveRoutingAssignment = [bool](Get-HeartbeatPolicyValue -Container $HeartbeatPolicy -Key "preserve_routing_assignment" -DefaultValue $true)
    $timers = if ($HeartbeatPolicy) { $HeartbeatPolicy.timers } else { $null }
    $gradePolicy = Get-HeartbeatGradePolicy -HeartbeatPolicy $HeartbeatPolicy -Grade $Grade

    $scope = if ($HeartbeatPolicy) { $HeartbeatPolicy.scope } else { $null }
    $gradeAllow = if ($scope -and $scope.grade_allow) { @($scope.grade_allow) } else { @("M", "L", "XL") }
    $taskAllow = if ($scope -and $scope.task_allow) { @($scope.task_allow) } else { @("planning", "coding", "review", "debug", "research") }
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $taskApplicable = ($taskAllow -contains $TaskType)
    $scopeApplicable = [bool]($gradeApplicable -and $taskApplicable)

    $briefInterval = [int](Get-HeartbeatPolicyValue -Container $timers -Key "user_brief_interval_sec" -DefaultValue 15)
    $debugTick = [int](Get-HeartbeatPolicyValue -Container $timers -Key "debug_tick_interval_sec" -DefaultValue 5)
    $softStall = [double](Get-HeartbeatPolicyValue -Container $timers -Key "soft_stall_silence_sec" -DefaultValue 30)
    $hardStall = [double](Get-HeartbeatPolicyValue -Container $timers -Key "hard_stall_silence_sec" -DefaultValue 120)
    $maxNoState = [double](Get-HeartbeatPolicyValue -Container $timers -Key "max_no_state_change_sec" -DefaultValue 180)

    if ($gradePolicy) {
        if ($gradePolicy.brief_interval_sec -ne $null) {
            $briefInterval = [int]$gradePolicy.brief_interval_sec
        }
        if ($gradePolicy.hard_stall_silence_sec -ne $null) {
            $hardStall = [double]$gradePolicy.hard_stall_silence_sec
        }
    }

    $autoDiagnosis = if ($HeartbeatPolicy) { $HeartbeatPolicy.auto_diagnosis } else { $null }
    $noiseControl = if ($HeartbeatPolicy) { $HeartbeatPolicy.noise_control } else { $null }
    $runtimeDigest = if ($HeartbeatPolicy) { $HeartbeatPolicy.runtime_digest } else { $null }

    $runtimeDigestEnabled = [bool](Get-HeartbeatPolicyValue -Container $runtimeDigest -Key "enabled" -DefaultValue $true)
    $runtimeDigestPulseCount = [int](Get-HeartbeatPolicyValue -Container $runtimeDigest -Key "include_recent_pulses" -DefaultValue 8)
    if ($runtimeDigestPulseCount -le 0) { $runtimeDigestPulseCount = 8 }

    $now = [DateTime]::UtcNow
    return [pscustomobject]@{
        enabled = [bool]($enabled -and $scopeApplicable)
        configured_enabled = [bool]$enabled
        mode = $mode
        grade = $Grade
        task_type = $TaskType
        grade_applicable = [bool]$gradeApplicable
        task_applicable = [bool]$taskApplicable
        scope_applicable = [bool]$scopeApplicable
        preserve_routing_assignment = [bool]$preserveRoutingAssignment
        user_brief_interval_sec = [int]$briefInterval
        debug_tick_interval_sec = [int]$debugTick
        soft_stall_silence_sec = [double]$softStall
        hard_stall_silence_sec = [double]$hardStall
        max_no_state_change_sec = [double]$maxNoState
        auto_diagnosis_enabled = [bool](Get-HeartbeatPolicyValue -Container $autoDiagnosis -Key "enabled" -DefaultValue $false)
        auto_diagnosis_tail_lines = [int](Get-HeartbeatPolicyValue -Container $autoDiagnosis -Key "tail_lines" -DefaultValue 120)
        auto_diagnosis_collect_process_snapshot = [bool](Get-HeartbeatPolicyValue -Container $autoDiagnosis -Key "collect_process_snapshot" -DefaultValue $false)
        auto_diagnosis_collect_last_phase = [bool](Get-HeartbeatPolicyValue -Container $autoDiagnosis -Key "collect_last_phase" -DefaultValue $true)
        runtime_digest_enabled = [bool]$runtimeDigestEnabled
        runtime_digest_recent_pulses = [int]$runtimeDigestPulseCount
        noise_suppress_duplicate_state = [bool](Get-HeartbeatPolicyValue -Container $noiseControl -Key "suppress_duplicate_state" -DefaultValue $true)
        noise_min_delta_elapsed_sec = [double](Get-HeartbeatPolicyValue -Container $noiseControl -Key "min_delta_elapsed_sec" -DefaultValue 10)
        noise_only_emit_on_phase_or_risk_change = [bool](Get-HeartbeatPolicyValue -Container $noiseControl -Key "only_emit_on_phase_or_risk_change" -DefaultValue $true)
        lifecycle_status = if ($enabled -and $scopeApplicable) { "running" } elseif (-not $enabled) { "disabled" } else { "outside_scope" }
        current_status = if ($enabled -and $scopeApplicable) { "running" } elseif (-not $enabled) { "disabled" } else { "outside_scope" }
        current_phase = "router.init"
        pulse_count = 0
        stall_score = 0.0
        suspect_stall = $false
        hard_stall = $false
        auto_diagnosis_triggered = $false
        status_reason = if (-not $enabled) { "policy_off" } elseif (-not $scopeApplicable) { "outside_scope" } else { "healthy_running" }
        created_utc = $now.ToString("o")
        start_utc = $now.ToString("o")
        last_pulse_utc = $null
        last_stage = $null
        last_note = $null
        next_seq = 1
        pulses = (New-Object System.Collections.ArrayList)
        _start_at = $now
        _last_output_at = $now
        _last_state_change_at = $now
        _last_phase = "router.init"
        _last_signature = $null
        _last_emit_elapsed_sec = 0.0
    }
}

function Add-HeartbeatPulse {
    param(
        [object]$Context,
        [string]$Stage,
        [string]$Phase,
        [string]$Note,
        [object]$Data,
        [switch]$ForceEmit
    )

    if (-not $Context -or -not $Context.enabled) { return $null }

    $now = [DateTime]::UtcNow
    $phaseName = if ($Phase) { [string]$Phase } elseif ($Context.current_phase) { [string]$Context.current_phase } else { "router" }
    $phaseChanged = ($phaseName -ne [string]$Context._last_phase)
    if ($phaseChanged) {
        $Context._last_phase = $phaseName
        $Context._last_state_change_at = $now
    }

    $outputActivity = $true
    if ($Data -and $Data.PSObject.Properties.Name -contains "output_activity") {
        $outputActivity = [bool]$Data.output_activity
    }
    if ($outputActivity) {
        $Context._last_output_at = $now
    }

    $elapsedSec = [Math]::Round(($now - $Context._start_at).TotalSeconds, 3)
    $lastOutputAgoSec = [Math]::Round(($now - $Context._last_output_at).TotalSeconds, 3)
    $noStateChangeSec = [Math]::Round(($now - $Context._last_state_change_at).TotalSeconds, 3)
    $assessment = Get-HeartbeatStallAssessment `
        -SilenceSec $lastOutputAgoSec `
        -NoStateChangeSec $noStateChangeSec `
        -SoftStallSec ([double]$Context.soft_stall_silence_sec) `
        -HardStallSec ([double]$Context.hard_stall_silence_sec) `
        -MaxNoStateChangeSec ([double]$Context.max_no_state_change_sec)

    $status = "running"
    if ($assessment.hard_stall) {
        $status = "hard_stall"
    } elseif ($assessment.suspect_stall) {
        $status = "suspect_stall"
    } elseif ($Context.hard_stall -or $Context.suspect_stall) {
        $status = "recovered"
    } elseif ($phaseChanged -or $outputActivity) {
        $status = "progressing"
    }

    if ($status -eq "hard_stall" -and [string]$Context.mode -eq "strict" -and [bool]$Context.auto_diagnosis_enabled) {
        $Context.auto_diagnosis_triggered = $true
    }

    $signature = "{0}|{1}|{2}" -f $status, $phaseName, [Math]::Round([double]$assessment.stall_score, 2)
    $deltaElapsed = [Math]::Abs([double]$elapsedSec - [double]$Context._last_emit_elapsed_sec)
    $shouldSuppress = $false
    if (-not $ForceEmit -and [bool]$Context.noise_suppress_duplicate_state) {
        if ($signature -eq [string]$Context._last_signature) {
            $minDelta = [double]$Context.noise_min_delta_elapsed_sec
            if ($deltaElapsed -lt $minDelta) {
                $shouldSuppress = $true
            }
        }
    }

    if ($shouldSuppress -and [bool]$Context.noise_only_emit_on_phase_or_risk_change -and (-not $phaseChanged)) {
        $Context.current_status = $status
        $Context.current_phase = $phaseName
        $Context.stall_score = [double]$assessment.stall_score
        $Context.suspect_stall = [bool]$assessment.suspect_stall
        $Context.hard_stall = [bool]$assessment.hard_stall
        return $null
    }

    $entry = [pscustomobject]@{
        seq = [int]$Context.next_seq
        timestamp_utc = $now.ToString("o")
        stage = if ($Stage) { [string]$Stage } else { "heartbeat.tick" }
        phase = $phaseName
        status = $status
        elapsed_sec = [double]$elapsedSec
        last_output_sec_ago = [double]$lastOutputAgoSec
        no_state_change_sec = [double]$noStateChangeSec
        stall_score = [double]$assessment.stall_score
        note = if ($Note) { [string]$Note } else { "" }
        data = if ($Data) {
            try { $Data | ConvertTo-Json -Depth 12 | ConvertFrom-Json } catch { [string]$Data }
        } else { $null }
    }

    [void]$Context.pulses.Add($entry)
    $Context.next_seq = [int]$Context.next_seq + 1
    $Context.pulse_count = [int]$Context.pulse_count + 1
    $Context.current_status = $status
    $Context.current_phase = $phaseName
    $Context.stall_score = [double]$assessment.stall_score
    $Context.suspect_stall = [bool]$assessment.suspect_stall
    $Context.hard_stall = [bool]$assessment.hard_stall
    $Context.last_stage = $entry.stage
    $Context.last_note = $entry.note
    $Context.last_pulse_utc = $entry.timestamp_utc
    $Context._last_signature = $signature
    $Context._last_emit_elapsed_sec = [double]$elapsedSec

    if ($status -eq "hard_stall") {
        $Context.status_reason = "hard_stall"
    } elseif ($status -eq "suspect_stall") {
        $Context.status_reason = "suspect_stall"
    } elseif ($status -eq "recovered") {
        $Context.status_reason = "recovered_after_stall"
    } else {
        $Context.status_reason = "healthy_running"
    }

    return $entry
}

function Get-HeartbeatAdvice {
    param([object]$Context)

    if (-not $Context) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            scope_applicable = $false
            enforcement = "none"
            reason = "context_missing"
            confirm_required = $false
            preserve_routing_assignment = $true
        }
    }

    if (-not $Context.enabled) {
        return [pscustomobject]@{
            enabled = $false
            mode = [string]$Context.mode
            scope_applicable = [bool]$Context.scope_applicable
            enforcement = "none"
            reason = [string]$Context.status_reason
            confirm_required = $false
            preserve_routing_assignment = [bool]$Context.preserve_routing_assignment
            status = [string]$Context.current_status
            lifecycle_status = [string]$Context.lifecycle_status
            pulse_count = [int]$Context.pulse_count
            stall_score = [double]$Context.stall_score
            suspect_stall = [bool]$Context.suspect_stall
            hard_stall = [bool]$Context.hard_stall
            auto_diagnosis_enabled = [bool]$Context.auto_diagnosis_enabled
            auto_diagnosis_triggered = [bool]$Context.auto_diagnosis_triggered
            confidence = 0.0
        }
    }

    $enforcement = "advisory"
    $confirmRequired = $false
    if ([string]$Context.mode -eq "soft" -and ([bool]$Context.suspect_stall -or [bool]$Context.hard_stall)) {
        $enforcement = "confirm_required"
        $confirmRequired = $true
    } elseif ([string]$Context.mode -eq "strict") {
        if ([bool]$Context.hard_stall) {
            $enforcement = "required"
            $confirmRequired = $true
        } elseif ([bool]$Context.suspect_stall) {
            $enforcement = "confirm_required"
            $confirmRequired = $true
        }
    }

    $reason = if ($Context.hard_stall) { "hard_stall" } elseif ($Context.suspect_stall) { "suspect_stall" } else { "healthy_running" }
    $confidence = [Math]::Round([Math]::Min(1.0, [Math]::Max(0.1, [double]$Context.stall_score)), 4)

    return [pscustomobject]@{
        enabled = $true
        mode = [string]$Context.mode
        scope_applicable = [bool]$Context.scope_applicable
        enforcement = $enforcement
        reason = $reason
        confirm_required = [bool]$confirmRequired
        preserve_routing_assignment = [bool]$Context.preserve_routing_assignment
        status = [string]$Context.current_status
        lifecycle_status = [string]$Context.lifecycle_status
        pulse_count = [int]$Context.pulse_count
        stall_score = [double]$Context.stall_score
        suspect_stall = [bool]$Context.suspect_stall
        hard_stall = [bool]$Context.hard_stall
        user_brief_interval_sec = [int]$Context.user_brief_interval_sec
        debug_tick_interval_sec = [int]$Context.debug_tick_interval_sec
        soft_stall_silence_sec = [double]$Context.soft_stall_silence_sec
        hard_stall_silence_sec = [double]$Context.hard_stall_silence_sec
        max_no_state_change_sec = [double]$Context.max_no_state_change_sec
        auto_diagnosis_enabled = [bool]$Context.auto_diagnosis_enabled
        auto_diagnosis_triggered = [bool]$Context.auto_diagnosis_triggered
        confidence = [double]$confidence
    }
}

function Get-HeartbeatStatus {
    param([object]$Context)

    if (-not $Context) {
        return [pscustomobject]@{
            enabled = $false
            lifecycle_status = "missing"
            current_status = "missing"
            pulse_count = 0
            elapsed_sec = 0.0
        }
    }

    $elapsedSec = [Math]::Round(([DateTime]::UtcNow - $Context._start_at).TotalSeconds, 3)
    $lastOutputAgoSec = [Math]::Round(([DateTime]::UtcNow - $Context._last_output_at).TotalSeconds, 3)
    $noStateChangeSec = [Math]::Round(([DateTime]::UtcNow - $Context._last_state_change_at).TotalSeconds, 3)

    return [pscustomobject]@{
        enabled = [bool]$Context.enabled
        mode = [string]$Context.mode
        lifecycle_status = [string]$Context.lifecycle_status
        current_status = [string]$Context.current_status
        current_phase = [string]$Context.current_phase
        pulse_count = [int]$Context.pulse_count
        elapsed_sec = [double]$elapsedSec
        last_output_sec_ago = [double]$lastOutputAgoSec
        no_state_change_sec = [double]$noStateChangeSec
        stall_score = [double]$Context.stall_score
        suspect_stall = [bool]$Context.suspect_stall
        hard_stall = [bool]$Context.hard_stall
        auto_diagnosis_triggered = [bool]$Context.auto_diagnosis_triggered
        start_utc = [string]$Context.start_utc
        last_pulse_utc = [string]$Context.last_pulse_utc
        last_stage = [string]$Context.last_stage
        last_note = [string]$Context.last_note
    }
}

function Get-HeartbeatRuntimeDigest {
    param(
        [object]$Context,
        [int]$RecentPulseCount = 8
    )

    if (-not $Context -or -not $Context.runtime_digest_enabled) {
        return [pscustomobject]@{
            enabled = $false
            reason = "runtime_digest_disabled"
        }
    }
    if (-not $Context.enabled) {
        return [pscustomobject]@{
            enabled = $false
            reason = "heartbeat_disabled"
        }
    }

    $limit = if ($RecentPulseCount -gt 0) { $RecentPulseCount } else { [int]$Context.runtime_digest_recent_pulses }
    if ($limit -le 0) { $limit = 8 }
    $pulseArray = @($Context.pulses)
    $recentPulses = @($pulseArray | Select-Object -Last $limit | ForEach-Object {
            [pscustomobject]@{
                seq = [int]$_.seq
                stage = [string]$_.stage
                phase = [string]$_.phase
                status = [string]$_.status
                elapsed_sec = [double]$_.elapsed_sec
                stall_score = [double]$_.stall_score
            }
        })

    return [pscustomobject]@{
        enabled = $true
        mode = [string]$Context.mode
        lifecycle_status = [string]$Context.lifecycle_status
        current_status = [string]$Context.current_status
        current_phase = [string]$Context.current_phase
        pulse_count = [int]$Context.pulse_count
        stall_score = [double]$Context.stall_score
        suspect_stall = [bool]$Context.suspect_stall
        hard_stall = [bool]$Context.hard_stall
        auto_diagnosis_triggered = [bool]$Context.auto_diagnosis_triggered
        user_brief_interval_sec = [int]$Context.user_brief_interval_sec
        debug_tick_interval_sec = [int]$Context.debug_tick_interval_sec
        soft_stall_silence_sec = [double]$Context.soft_stall_silence_sec
        hard_stall_silence_sec = [double]$Context.hard_stall_silence_sec
        max_no_state_change_sec = [double]$Context.max_no_state_change_sec
        recent_pulses = @($recentPulses)
    }
}

function Finalize-HeartbeatContext {
    param(
        [object]$Context,
        [string]$FinalPhase = "router.final",
        [bool]$Succeeded = $true,
        [string]$Note = "router completed"
    )

    if (-not $Context) { return $null }
    if (-not $Context.enabled) {
        if ($Succeeded) {
            $Context.lifecycle_status = "completed"
        } else {
            $Context.lifecycle_status = "failed"
        }
        return Get-HeartbeatStatus -Context $Context
    }

    $null = Add-HeartbeatPulse -Context $Context -Stage "heartbeat.finalize" -Phase $FinalPhase -Note $Note -ForceEmit

    if ($Succeeded) {
        $Context.lifecycle_status = "completed"
        if (-not $Context.hard_stall -and -not $Context.suspect_stall) {
            $Context.current_status = "completed"
            $Context.status_reason = "completed"
        }
    } else {
        $Context.lifecycle_status = "failed"
        $Context.current_status = "failed"
        $Context.status_reason = "failed"
    }

    return Get-HeartbeatStatus -Context $Context
}
