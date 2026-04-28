Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeExecution.Common.ps1')

function ConvertTo-VibeSpecialistConsultationBucketLimits {
    param(
        [AllowNull()] [object]$BucketLimits = $null
    )

    $resolved = @{}
    if ($null -eq $BucketLimits) {
        return $resolved
    }

    if ($BucketLimits -is [System.Collections.IDictionary]) {
        foreach ($key in @($BucketLimits.Keys)) {
            $name = if ($null -eq $key) { '' } else { [string]$key }
            if ([string]::IsNullOrWhiteSpace($name)) {
                continue
            }
            $limit = [int]$BucketLimits[$key]
            if ($limit -le 0) {
                continue
            }
            $resolved[$name.Trim().ToLowerInvariant()] = $limit
        }
        return $resolved
    }

    foreach ($property in @($BucketLimits.PSObject.Properties)) {
        if ($null -eq $property) {
            continue
        }

        $name = if ([string]::IsNullOrWhiteSpace([string]$property.Name)) { '' } else { [string]$property.Name }
        if ([string]::IsNullOrWhiteSpace($name)) {
            continue
        }

        $limit = [int]$property.Value
        if ($limit -le 0) {
            continue
        }
        $resolved[$name.Trim().ToLowerInvariant()] = $limit
    }

    return $resolved
}

function Get-VibeSpecialistConsultationPolicy {
    param(
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = if ($null -ne $Policy) { $Policy } else { $null }
    $allowedWindows = if (
        $null -ne $resolvedPolicy -and
        (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'allowed_windows') -and
        $null -ne $resolvedPolicy.allowed_windows
    ) {
        @($resolvedPolicy.allowed_windows | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @('discussion', 'planning')
    }
    $windowPrompts = if (
        $null -ne $resolvedPolicy -and
        (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'window_prompts') -and
        $null -ne $resolvedPolicy.window_prompts
    ) {
        $resolvedPolicy.window_prompts
    } else {
        [pscustomobject]@{
            discussion = 'Consult this specialist before the requirement doc is frozen.'
            planning = 'Consult this specialist before the execution plan is frozen.'
        }
    }

    $consultationMode = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'mode') -and -not [string]::IsNullOrWhiteSpace([string]$resolvedPolicy.mode)) {
        [string]$resolvedPolicy.mode
    } else {
        'direct_current_session_route'
    }
    $modeOverride = [Environment]::GetEnvironmentVariable('VGO_SPECIALIST_CONSULTATION_MODE')
    if (-not [string]::IsNullOrWhiteSpace($modeOverride)) {
        $consultationMode = [string]$modeOverride
    }
    $consultationMode = $consultationMode.Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($consultationMode)) {
        $consultationMode = 'direct_current_session_route'
    }
    if ($consultationMode -eq 'host_subprocess') {
        $consultationMode = 'direct_current_session_route'
    }
    if ($consultationMode -ne 'direct_current_session_route') {
        throw ("Unsupported specialist consultation mode: {0}" -f $consultationMode)
    }

    $selectionMode = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'selection_mode') -and -not [string]::IsNullOrWhiteSpace([string]$resolvedPolicy.selection_mode)) {
        [string]$resolvedPolicy.selection_mode
    } else {
        'flat_ranked'
    }
    $selectionMode = $selectionMode.Trim().ToLowerInvariant()
    $allowedSelectionModes = @('flat_ranked', 'bucketed_with_backfill')
    if ($selectionMode -notin $allowedSelectionModes) {
        throw ("Unsupported specialist consultation selection mode: {0}" -f $selectionMode)
    }

    $bucketLimits = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'bucket_limits')) {
        ConvertTo-VibeSpecialistConsultationBucketLimits -BucketLimits $resolvedPolicy.bucket_limits
    } else {
        @{}
    }

    return [pscustomobject]@{
        enabled = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'enabled')) { [bool]$resolvedPolicy.enabled } else { $false }
        version = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'version')) { [int]$resolvedPolicy.version } else { 1 }
        policy_id = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'policy_id') -and -not [string]::IsNullOrWhiteSpace([string]$resolvedPolicy.policy_id)) { [string]$resolvedPolicy.policy_id } else { 'specialist-consultation-v1' }
        mode = $consultationMode
        max_consults_per_window = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'max_consults_per_window')) { [int]$resolvedPolicy.max_consults_per_window } else { 2 }
        selection_mode = $selectionMode
        bucket_limits = $bucketLimits
        allowed_windows = @($allowedWindows)
        require_contract_complete = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_contract_complete')) { [bool]$resolvedPolicy.require_contract_complete } else { $true }
        require_native_workflow = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_native_workflow')) { [bool]$resolvedPolicy.require_native_workflow } else { $true }
        require_native_usage_required = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_native_usage_required')) { [bool]$resolvedPolicy.require_native_usage_required } else { $true }
        require_entrypoint_path = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_entrypoint_path')) { [bool]$resolvedPolicy.require_entrypoint_path } else { $true }
        progressive_disclosure_enabled = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'progressive_disclosure_enabled')) { [bool]$resolvedPolicy.progressive_disclosure_enabled } else { $true }
        defer_unapproved_to_execution = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'defer_unapproved_to_execution')) { [bool]$resolvedPolicy.defer_unapproved_to_execution } else { $true }
        freeze_gate_enabled = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'freeze_gate_enabled')) { [bool]$resolvedPolicy.freeze_gate_enabled } else { $true }
        require_outcome_coverage_for_approved_skills = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_outcome_coverage_for_approved_skills')) { [bool]$resolvedPolicy.require_outcome_coverage_for_approved_skills } else { $true }
        require_disclosure_coverage_for_approved_skills = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_disclosure_coverage_for_approved_skills')) { [bool]$resolvedPolicy.require_disclosure_coverage_for_approved_skills } else { $true }
        require_non_empty_summary_for_live_results = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_non_empty_summary_for_live_results')) { [bool]$resolvedPolicy.require_non_empty_summary_for_live_results } else { $true }
        require_consultation_notes_for_live_results = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_consultation_notes_for_live_results')) { [bool]$resolvedPolicy.require_consultation_notes_for_live_results } else { $true }
        require_adoption_notes_for_live_results = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_adoption_notes_for_live_results')) { [bool]$resolvedPolicy.require_adoption_notes_for_live_results } else { $true }
        require_verification_notes_for_live_results = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'require_verification_notes_for_live_results')) { [bool]$resolvedPolicy.require_verification_notes_for_live_results } else { $true }
        fail_freeze_on_live_degraded_results = if ($null -ne $resolvedPolicy -and (Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'fail_freeze_on_live_degraded_results')) { [bool]$resolvedPolicy.fail_freeze_on_live_degraded_results } else { $true }
        window_prompts = $windowPrompts
    }
}

function Get-VibeSpecialistConsultationBucket {
    param(
        [Parameter(Mandatory)] [object]$Recommendation
    )

    $source = if (
        (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'source') -and
        -not [string]::IsNullOrWhiteSpace([string]$Recommendation.source)
    ) {
        [string]$Recommendation.source
    } else {
        ''
    }

    if ([string]::Equals($source, 'route_stage_assistant', [System.StringComparison]::OrdinalIgnoreCase)) {
        return 'stage_assistant'
    }
    return 'primary'
}

function Get-VibeSpecialistConsultationReceiptPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot ("{0}-specialist-consultation.json" -f $WindowId)))
}

function Get-VibeSpecialistConsultationWindowDefaults {
    param(
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage
    )

    switch ($WindowId) {
        'discussion' {
            return [pscustomobject]@{
                consultation_scope = 'clarify ambiguity, sharpen requirement framing, and surface early risk before requirement freeze'
                consultation_role = 'discussion_consultant'
                consultation_reason = 'improve the ongoing discussion before the requirement doc is frozen'
                stage = if ([string]::IsNullOrWhiteSpace($Stage)) { 'deep_interview' } else { [string]$Stage }
            }
        }
        default {
            return [pscustomobject]@{
                consultation_scope = 'improve plan sequencing, verification coverage, rollback notes, and ownership boundaries before plan freeze'
                consultation_role = 'planning_consultant'
                consultation_reason = 'improve the governed plan before the execution plan is frozen'
                stage = if ([string]::IsNullOrWhiteSpace($Stage)) { 'requirement_doc' } else { [string]$Stage }
            }
        }
    }
}

function New-VibeSpecialistConsultationCandidate {
    param(
        [Parameter(Mandatory)] [object]$Recommendation,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage
    )

    $defaults = Get-VibeSpecialistConsultationWindowDefaults -WindowId $WindowId -Stage $Stage
    $entrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$Recommendation.native_skill_entrypoint)
    ) {
        [string]$Recommendation.native_skill_entrypoint
    } else {
        $null
    }
    if (-not [string]::IsNullOrWhiteSpace($entrypoint) -and [System.IO.Path]::IsPathRooted($entrypoint)) {
        $entrypoint = [System.IO.Path]::GetFullPath($entrypoint)
    }

    $consultationReason = if (
        (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'reason') -and
        -not [string]::IsNullOrWhiteSpace([string]$Recommendation.reason)
    ) {
        [string]$Recommendation.reason
    } else {
        [string]$defaults.consultation_reason
    }
    $consultationBucket = Get-VibeSpecialistConsultationBucket -Recommendation $Recommendation

    return [pscustomobject]@{
        skill_id = [string]$Recommendation.skill_id
        native_skill_entrypoint = $entrypoint
        native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$Recommendation.native_skill_description)) { [string]$Recommendation.native_skill_description } else { $null }
        consultation_reason = $consultationReason
        consultation_scope = [string]$defaults.consultation_scope
        consultation_role = [string]$defaults.consultation_role
        consultation_stage = [string]$defaults.stage
        write_scope = 'read_only'
        review_mode = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'review_mode') -and -not [string]::IsNullOrWhiteSpace([string]$Recommendation.review_mode)) { [string]$Recommendation.review_mode } else { 'consultation_only' }
        required_inputs = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'required_inputs') { [object[]]@($Recommendation.required_inputs) } else { @() }
        expected_outputs = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'expected_outputs') { [object[]]@($Recommendation.expected_outputs) } else { @() }
        verification_expectation = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'verification_expectation') -and -not [string]::IsNullOrWhiteSpace([string]$Recommendation.verification_expectation)) { [string]$Recommendation.verification_expectation } else { 'Return bounded structured specialist guidance only.' }
        native_usage_required = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'native_usage_required') { [bool]$Recommendation.native_usage_required } elseif (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'usage_required') { [bool]$Recommendation.usage_required } else { $true }
        must_preserve_workflow = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'must_preserve_workflow') { [bool]$Recommendation.must_preserve_workflow } else { $true }
        contract_complete = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'contract_complete') { [bool]$Recommendation.contract_complete } else { $false }
        contract_missing_fields = if (Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'contract_missing_fields') { [object[]]@($Recommendation.contract_missing_fields) } else { @() }
        source_reason = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string]$Recommendation.reason)) { [string]$Recommendation.reason } else { $null }
        dispatch_phase = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$Recommendation.dispatch_phase)) { [string]$Recommendation.dispatch_phase } else { $null }
        execution_priority = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'execution_priority') -and $null -ne $Recommendation.execution_priority) { [int]$Recommendation.execution_priority } else { 0 }
        rank = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'rank') -and $null -ne $Recommendation.rank) { [int]$Recommendation.rank } else { 9999 }
        confidence = if ((Test-VibeObjectHasProperty -InputObject $Recommendation -PropertyName 'confidence') -and $null -ne $Recommendation.confidence) { [double]$Recommendation.confidence } else { 0.0 }
        consultation_bucket = $consultationBucket
    }
}

function Split-VibeSpecialistConsultationCandidates {
    param(
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Recommendations = @(),
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [object]$Policy
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    $approved = New-Object System.Collections.Generic.List[object]
    $deferred = New-Object System.Collections.Generic.List[object]
    $blocked = New-Object System.Collections.Generic.List[object]
    $overflow = New-Object System.Collections.Generic.List[object]
    $seenSkillIds = @{}
    $bucketUsage = @{}
    $selectionMode = if ((Test-VibeObjectHasProperty -InputObject $resolvedPolicy -PropertyName 'selection_mode') -and -not [string]::IsNullOrWhiteSpace([string]$resolvedPolicy.selection_mode)) {
        [string]$resolvedPolicy.selection_mode
    } else {
        'flat_ranked'
    }
    $bucketedSelectionEnabled = (
        [string]::Equals($selectionMode, 'bucketed_with_backfill', [System.StringComparison]::OrdinalIgnoreCase) -and
        $null -ne $resolvedPolicy.bucket_limits -and
        $resolvedPolicy.bucket_limits.Count -gt 0
    )

    if (-not [bool]$resolvedPolicy.enabled -or -not (@($resolvedPolicy.allowed_windows) -contains $WindowId)) {
        return [pscustomobject]@{
            approved_consultation = @()
            deferred_to_execution = @()
            blocked = @()
        }
    }

    $sortedRecommendations = @($Recommendations | Sort-Object -Property @{ Expression = { [int]$_.rank } }, @{ Expression = { -1 * [double]$_.confidence } })
    foreach ($recommendation in @($sortedRecommendations)) {
        if ($null -eq $recommendation) {
            continue
        }

        $skillId = [string]$recommendation.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seenSkillIds.ContainsKey($skillId)) {
            continue
        }
        $seenSkillIds[$skillId] = $true
        $candidate = New-VibeSpecialistConsultationCandidate -Recommendation $recommendation -WindowId $WindowId -Stage $Stage

        $entrypointOk = -not [string]::IsNullOrWhiteSpace([string]$candidate.native_skill_entrypoint) -and [System.IO.Path]::IsPathRooted([string]$candidate.native_skill_entrypoint)
        if ($entrypointOk) {
            $entrypointOk = Test-Path -LiteralPath ([string]$candidate.native_skill_entrypoint)
        }
        if ([bool]$resolvedPolicy.require_entrypoint_path -and -not $entrypointOk) {
            $blocked.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'missing_native_skill_entrypoint'
                    native_skill_entrypoint = $candidate.native_skill_entrypoint
                }
            ) | Out-Null
            continue
        }
        if ([bool]$resolvedPolicy.require_contract_complete -and -not [bool]$candidate.contract_complete) {
            $deferred.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'contract_incomplete'
                    contract_missing_fields = @($candidate.contract_missing_fields)
                }
            ) | Out-Null
            continue
        }
        if ([bool]$resolvedPolicy.require_native_workflow -and -not [bool]$candidate.must_preserve_workflow) {
            $deferred.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'native_workflow_not_required'
                }
            ) | Out-Null
            continue
        }
        if ([bool]$resolvedPolicy.require_native_usage_required -and -not [bool]$candidate.native_usage_required) {
            $deferred.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'native_usage_not_required'
                }
            ) | Out-Null
            continue
        }
        $candidateBucket = if (
            (Test-VibeObjectHasProperty -InputObject $candidate -PropertyName 'consultation_bucket') -and
            -not [string]::IsNullOrWhiteSpace([string]$candidate.consultation_bucket)
        ) {
            [string]$candidate.consultation_bucket
        } else {
            'primary'
        }
        $candidateBucket = $candidateBucket.Trim().ToLowerInvariant()

        if ($bucketedSelectionEnabled -and $resolvedPolicy.bucket_limits.ContainsKey($candidateBucket)) {
            $bucketLimit = [int]$resolvedPolicy.bucket_limits[$candidateBucket]
            $bucketUsed = if ($bucketUsage.ContainsKey($candidateBucket)) { [int]$bucketUsage[$candidateBucket] } else { 0 }
            if ($bucketUsed -ge $bucketLimit) {
                $overflow.Add(
                    [pscustomobject]@{
                        candidate = $candidate
                        consultation_bucket = $candidateBucket
                    }
                ) | Out-Null
                continue
            }
        }
        if ($approved.Count -ge [int]$resolvedPolicy.max_consults_per_window) {
            $deferred.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'max_consults_per_window_reached'
                    consultation_bucket = $candidateBucket
                }
            ) | Out-Null
            continue
        }

        $approved.Add($candidate) | Out-Null
        $bucketUsage[$candidateBucket] = if ($bucketUsage.ContainsKey($candidateBucket)) { [int]$bucketUsage[$candidateBucket] + 1 } else { 1 }
    }

    if ($bucketedSelectionEnabled -and $approved.Count -lt [int]$resolvedPolicy.max_consults_per_window) {
        foreach ($overflowEntry in $overflow.ToArray()) {
            if ($approved.Count -ge [int]$resolvedPolicy.max_consults_per_window) {
                break
            }

            $candidate = $overflowEntry.candidate
            if ($null -eq $candidate) {
                continue
            }

            $approved.Add($candidate) | Out-Null
            $candidateBucket = if ($null -eq $overflowEntry.consultation_bucket) { 'primary' } else { [string]$overflowEntry.consultation_bucket }
            $bucketUsage[$candidateBucket] = if ($bucketUsage.ContainsKey($candidateBucket)) { [int]$bucketUsage[$candidateBucket] + 1 } else { 1 }
        }
    }

    if ($overflow.Count -gt 0) {
        $approvedSkillIndex = @{}
        foreach ($approvedItem in $approved.ToArray()) {
            if ($null -eq $approvedItem) {
                continue
            }
            $approvedSkillIndex[[string]$approvedItem.skill_id] = $true
        }

        foreach ($overflowEntry in $overflow.ToArray()) {
            $candidate = $overflowEntry.candidate
            if ($null -eq $candidate) {
                continue
            }
            if ($approvedSkillIndex.ContainsKey([string]$candidate.skill_id)) {
                continue
            }
            $deferred.Add(
                [pscustomobject]@{
                    skill_id = $candidate.skill_id
                    reason = 'max_consults_per_window_reached'
                    consultation_bucket = if ($null -eq $overflowEntry.consultation_bucket) { 'primary' } else { [string]$overflowEntry.consultation_bucket }
                }
            ) | Out-Null
        }
    }

    return [pscustomobject]@{
        approved_consultation = [object[]]$approved.ToArray()
        deferred_to_execution = [object[]]$deferred.ToArray()
        blocked = [object[]]$blocked.ToArray()
    }
}

function New-VibeSpecialistConsultationUserDisclosures {
    param(
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedConsultation = @(),
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [object]$Policy
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    if (-not [bool]$resolvedPolicy.progressive_disclosure_enabled) {
        return @()
    }

    $entries = New-Object System.Collections.Generic.List[object]
    foreach ($item in @($ApprovedConsultation)) {
        if ($null -eq $item) {
            continue
        }

        $renderedText = 'Consulting {0} now during {1} because {2}. Loaded from {3}.' -f `
            [string]$item.skill_id, `
            [string]$WindowId, `
            [string]$item.consultation_reason, `
            [string]$item.native_skill_entrypoint

        $entries.Add(
            [pscustomobject]@{
                skill_id = [string]$item.skill_id
                why_now = [string]$item.consultation_reason
                native_skill_entrypoint = [string]$item.native_skill_entrypoint
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $item -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$item.native_skill_description)) { [string]$item.native_skill_description } else { $null }
                consultation_stage = [string]$Stage
                consultation_window_id = [string]$WindowId
                rendered_text = $renderedText
            }
        ) | Out-Null
    }

    return [object[]]$entries.ToArray()
}

function ConvertTo-VibeConsultationArrayOrEmpty {
    param(
        [AllowNull()] [object]$Value
    )

    if ($null -eq $Value) {
        return @()
    }
    return [object[]]@($Value)
}

function Test-VibeSpecialistConsultationPayloadCompleteness {
    param(
        [AllowNull()] [object]$Result,
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    $errors = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Result) {
        $errors.Add('result_missing') | Out-Null
        return [pscustomobject]@{
            passed = $false
            errors = [string[]]$errors.ToArray()
        }
    }

    $summary = if ((Test-VibeObjectHasProperty -InputObject $Result -PropertyName 'summary') -and -not [string]::IsNullOrWhiteSpace([string]$Result.summary)) {
        [string]$Result.summary
    } else {
        ''
    }
    $consultationNotes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if (Test-VibeObjectHasProperty -InputObject $Result -PropertyName 'consultation_notes') { $Result.consultation_notes } else { $null })
    $adoptionNotes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if (Test-VibeObjectHasProperty -InputObject $Result -PropertyName 'adoption_notes') { $Result.adoption_notes } else { $null })
    $verificationNotes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if (Test-VibeObjectHasProperty -InputObject $Result -PropertyName 'verification_notes') { $Result.verification_notes } else { $null })

    if ([bool]$resolvedPolicy.require_non_empty_summary_for_live_results -and [string]::IsNullOrWhiteSpace($summary)) {
        $errors.Add('missing_summary') | Out-Null
    }
    if ([bool]$resolvedPolicy.require_consultation_notes_for_live_results -and @($consultationNotes).Count -le 0) {
        $errors.Add('missing_consultation_notes') | Out-Null
    }
    if ([bool]$resolvedPolicy.require_adoption_notes_for_live_results -and @($adoptionNotes).Count -le 0) {
        $errors.Add('missing_adoption_notes') | Out-Null
    }
    if ([bool]$resolvedPolicy.require_verification_notes_for_live_results -and @($verificationNotes).Count -le 0) {
        $errors.Add('missing_verification_notes') | Out-Null
    }

    return [pscustomobject]@{
        passed = [bool]($errors.Count -eq 0)
        errors = [string[]]$errors.ToArray()
    }
}

function New-VibeSpecialistConsultationResultSchema {
    return [pscustomobject]@{
        type = 'object'
        properties = [pscustomobject]@{
            status = [pscustomobject]@{
                type = 'string'
                enum = @('completed', 'completed_with_notes', 'blocked')
            }
            summary = [pscustomobject]@{
                type = 'string'
            }
            consultation_notes = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
            adoption_notes = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
            verification_notes = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
        }
        required = @('status', 'summary', 'consultation_notes', 'adoption_notes', 'verification_notes')
        additionalProperties = $false
    }
}

function Test-VibeSpecialistConsultationResponseAgainstSchema {
    param(
        [AllowNull()] [object]$Response,
        [Parameter(Mandatory)] [object]$Schema
    )

    $errors = @()
    if ($null -eq $Response) {
        return [pscustomobject]@{
            passed = $false
            errors = @('response_missing')
        }
    }

    $responseProperties = @($Response.PSObject.Properties.Name | ForEach-Object { [string]$_ })
    $schemaProperties = @($Schema.properties.PSObject.Properties.Name | ForEach-Object { [string]$_ })

    foreach ($requiredField in @($Schema.required)) {
        if (-not ($responseProperties -contains [string]$requiredField)) {
            $errors += ("missing_required_field:{0}" -f [string]$requiredField)
        }
    }

    if (-not [bool]$Schema.additionalProperties) {
        foreach ($responseField in @($responseProperties)) {
            if (-not ($schemaProperties -contains [string]$responseField)) {
                $errors += ("unexpected_field:{0}" -f [string]$responseField)
            }
        }
    }

    foreach ($propertyName in @($schemaProperties)) {
        if (-not ($responseProperties -contains [string]$propertyName)) {
            continue
        }

        $fieldSchema = $Schema.properties.$propertyName
        $fieldValue = $Response.$propertyName
        switch ([string]$fieldSchema.type) {
            'string' {
                if ($fieldValue -isnot [string]) {
                    $errors += ("invalid_type:{0}:expected_string" -f [string]$propertyName)
                    continue
                }
                if ($fieldSchema.PSObject.Properties.Name -contains 'enum' -and @($fieldSchema.enum).Count -gt 0) {
                    $allowedValues = @($fieldSchema.enum | ForEach-Object { [string]$_ })
                    if (-not ($allowedValues -contains [string]$fieldValue)) {
                        $errors += ("invalid_enum:{0}:{1}" -f [string]$propertyName, [string]$fieldValue)
                    }
                }
            }
            'array' {
                if ($fieldValue -is [string]) {
                    $errors += ("invalid_type:{0}:expected_array" -f [string]$propertyName)
                    continue
                }
                foreach ($item in @($fieldValue)) {
                    if ($item -isnot [string]) {
                        $errors += ("invalid_array_item_type:{0}:expected_string" -f [string]$propertyName)
                        break
                    }
                }
            }
        }
    }

    return [pscustomobject]@{
        passed = [bool]($errors.Count -eq 0)
        errors = @($errors)
    }
}

function New-VibeNativeSpecialistConsultationPrompt {
    param(
        [Parameter(Mandatory)] [object]$Consultation,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$SourceArtifactPath,
        [Parameter(Mandatory)] [object]$Policy
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    $windowPrompt = if (
        $resolvedPolicy.window_prompts -and
        $resolvedPolicy.window_prompts.PSObject.Properties.Name -contains $WindowId -and
        -not [string]::IsNullOrWhiteSpace([string]$resolvedPolicy.window_prompts.$WindowId)
    ) {
        [string]$resolvedPolicy.window_prompts.$WindowId
    } else {
        [string]$Consultation.consultation_scope
    }

    $lines = @(
        ('$' + [string]$Consultation.skill_id),
        '',
        'You are a backstage specialist consultation lane running under hidden vibe governance.',
        'Vibe remains the only outward-facing speaker and the only runtime authority.',
        'Do not speak directly to the user. Return structured guidance that vibe can absorb and summarize.',
        'This consultation is read-only. Do not edit files, create patches, or widen scope.',
        ('specialist_skill_id: {0}' -f [string]$Consultation.skill_id),
        ('consultation_window_id: {0}' -f [string]$WindowId),
        ('consultation_stage: {0}' -f [string]$Stage),
        ('run_id: {0}' -f [string]$RunId),
        ('consultation_role: {0}' -f [string]$Consultation.consultation_role),
        ('consultation_scope: {0}' -f [string]$Consultation.consultation_scope),
        ('why_now: {0}' -f [string]$Consultation.consultation_reason),
        ('source_task: {0}' -f [string]$Task),
        ('source_artifact: {0}' -f [string]$SourceArtifactPath),
        '',
        'Consultation objective:',
        ('- {0}' -f $windowPrompt),
        '',
        'Required inputs:'
    )
    foreach ($item in @($Consultation.required_inputs)) {
        $lines += ('- {0}' -f [string]$item)
    }
    $lines += @(
        '',
        'Expected outputs:',
        '- consultation_notes: specialist reasoning that should shape vibe guidance right now.',
        '- adoption_notes: short notes describing how vibe should use the specialist advice in the next frozen artifact.',
        '- verification_notes: bounded notes proving the consultation stayed read-only and within workflow.'
    )
    foreach ($item in @($Consultation.expected_outputs)) {
        $lines += ('- preserve specialist expectation: {0}' -f [string]$item)
    }
    $lines += @(
        '',
        ('Verification expectation: {0}' -f [string]$Consultation.verification_expectation),
        'Return only JSON matching the provided schema.'
    )

    return ($lines -join [Environment]::NewLine)
}

function New-VibeDegradedSpecialistConsultationResult {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Consultation,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$Reason
    )

    $resultsRoot = Join-Path $SessionRoot 'consultation-results'
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $result = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_consultation'
        status = 'degraded_non_authoritative'
        verification_passed = $false
        skill_id = [string]$Consultation.skill_id
        consultation_window_id = [string]$WindowId
        consultation_stage = [string]$Stage
        live_native_execution = $false
        degraded = $true
        blocked = $false
        native_skill_entrypoint = [string]$Consultation.native_skill_entrypoint
        summary = ('Consultation was deferred because {0}.' -f [string]$Reason)
        consultation_notes = @()
        adoption_notes = @()
        verification_notes = @(('degraded_reason:{0}' -f [string]$Reason))
        observed_changed_files = @()
        response_json_path = $null
        prompt_path = $null
        schema_path = $null
        result_reason = [string]$Reason
    }
    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $result

    return [pscustomobject]@{
        category = 'degraded'
        result = $result
        result_path = $resultPath
    }
}

function New-VibeDirectRoutedSpecialistConsultationResult {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Consultation,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage
    )

    $resultsRoot = Join-Path $SessionRoot 'consultation-results'
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $entrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $Consultation -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$Consultation.native_skill_entrypoint)
    ) {
        [string]$Consultation.native_skill_entrypoint
    } else {
        $null
    }

    $summary = if (-not [string]::IsNullOrWhiteSpace($entrypoint)) {
        ('Specialist was routed for direct current-session consultation. Load {0} in the current host session instead of launching a hidden host subprocess. Do not replace this path with Skill({1}) unless that skill name is explicitly visible in the host registry.' -f $entrypoint, [string]$Consultation.skill_id)
    } else {
        'Specialist was routed for direct current-session consultation instead of launching a hidden host subprocess.'
    }

    $result = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_consultation'
        status = 'routed_pending_current_session'
        verification_passed = $false
        skill_id = [string]$Consultation.skill_id
        consultation_window_id = [string]$WindowId
        consultation_stage = [string]$Stage
        live_native_execution = $false
        degraded = $false
        blocked = $false
        direct_route = $true
        consultation_mode = 'direct_current_session_route'
        native_skill_entrypoint = $entrypoint
        summary = $summary
        consultation_notes = @(
            'No hidden host subprocess was launched for this specialist.',
            'The current host session should load the specialist entrypoint directly and keep vibe as the only runtime authority.',
            ('Do not translate native_skill_entrypoint into Skill({0}) unless the host already exposes that skill name.' -f [string]$Consultation.skill_id)
        )
        adoption_notes = @(
            'Use the specialist path already frozen in native_skill_entrypoint for same-session loading.',
            'Do not replace vibe governance; absorb specialist guidance back into the governed artifact flow.',
            'When same-session loading is path-resolved, prefer the declared native_skill_entrypoint over a host skill-name lookup.'
        )
        verification_notes = @(
            'consultation_mode:direct_current_session_route',
            'hidden_host_subprocess:false',
            ('native_skill_entrypoint:{0}' -f $(if ([string]::IsNullOrWhiteSpace($entrypoint)) { 'missing' } else { $entrypoint }))
        )
        observed_changed_files = @()
        response_json_path = $null
        prompt_path = $null
        schema_path = $null
        result_reason = 'pending_direct_current_session_route'
    }
    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $result

    return [pscustomobject]@{
        category = 'routed'
        result = $result
        result_path = $resultPath
    }
}

function Invoke-VibeSpecialistConsultationUnit {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Consultation,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$SourceArtifactPath,
        [Parameter(Mandatory)] [object]$Policy
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    if ([string]$resolvedPolicy.mode -eq 'direct_current_session_route') {
        return New-VibeDirectRoutedSpecialistConsultationResult `
            -UnitId $UnitId `
            -Consultation $Consultation `
            -SessionRoot $SessionRoot `
            -WindowId $WindowId `
            -Stage $Stage
    }

    $adapterResolution = Resolve-VibeNativeSpecialistAdapter -ScriptPath $PSCommandPath
    if ([string]$adapterResolution.reason -eq 'direct_current_session_route') {
        return New-VibeDirectRoutedSpecialistConsultationResult `
            -UnitId $UnitId `
            -Consultation $Consultation `
            -SessionRoot $SessionRoot `
            -WindowId $WindowId `
            -Stage $Stage
    }

    if (-not [bool]$adapterResolution.live_execution_allowed -or $null -eq $adapterResolution.adapter) {
        return New-VibeDegradedSpecialistConsultationResult `
            -UnitId $UnitId `
            -Consultation $Consultation `
            -SessionRoot $SessionRoot `
            -WindowId $WindowId `
            -Stage $Stage `
            -Reason ([string]$adapterResolution.reason)
    }

    $adapter = $adapterResolution.adapter
    $nativePolicy = $adapterResolution.policy
    $logsRoot = Join-Path $SessionRoot 'consultation-logs'
    $resultsRoot = Join-Path $SessionRoot 'consultation-results'
    New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $stdoutPath = Join-Path $logsRoot ("{0}.stdout.log" -f $UnitId)
    $stderrPath = Join-Path $logsRoot ("{0}.stderr.log" -f $UnitId)
    $responsePath = Join-Path $resultsRoot ("{0}.response.json" -f $UnitId)
    $schemaPath = Join-Path $SessionRoot ("{0}.schema.json" -f $UnitId)
    $promptPath = Join-Path $SessionRoot ("{0}.prompt.md" -f $UnitId)
    $beforeGitPath = Join-Path $SessionRoot ("{0}.git-before.txt" -f $UnitId)
    $afterGitPath = Join-Path $SessionRoot ("{0}.git-after.txt" -f $UnitId)

    $schema = New-VibeSpecialistConsultationResultSchema
    Write-VibeJsonArtifact -Path $schemaPath -Value $schema
    $prompt = New-VibeNativeSpecialistConsultationPrompt `
        -Consultation $Consultation `
        -Task $Task `
        -RunId $RunId `
        -WindowId $WindowId `
        -Stage $Stage `
        -SourceArtifactPath $SourceArtifactPath `
        -Policy $Policy
    Write-VgoUtf8NoBomText -Path $promptPath -Content ($prompt + [Environment]::NewLine)

    $workingRoot = Resolve-VibeNativeSpecialistWorkingRoot `
        -RepoRoot $RepoRoot `
        -SessionRoot $SessionRoot `
        -SourceArtifactPath $SourceArtifactPath
    $codexHomeBinding = Get-VibeNativeSpecialistCodexHomeEnvironmentOverrides `
        -AdapterResolution $adapterResolution `
        -SkillRecord $Consultation `
        -RunId $RunId `
        -UnitId $UnitId
    $environmentOverrides = if ($null -ne $codexHomeBinding -and (Test-VibeObjectHasProperty -InputObject $codexHomeBinding -PropertyName 'environment_overrides')) {
        $codexHomeBinding.environment_overrides
    } else {
        $null
    }

    $beforeSnapshot = Get-VibePathStatusSnapshot -RootPath $workingRoot
    Write-VgoUtf8NoBomText -Path $beforeGitPath -Content ((@($beforeSnapshot.lines) -join [Environment]::NewLine) + [Environment]::NewLine)

    $arguments = @()
    foreach ($item in @($adapterResolution.invocation_arguments_prefix)) {
        $arguments += [string]$item
    }
    foreach ($item in @($adapter.arguments_prefix)) {
        $arguments += [string]$item
    }
    foreach ($item in @(Get-VibeNativeSpecialistRepoCheckBypassArguments -AdapterResolution $adapterResolution -WorkingRoot $workingRoot)) {
        $arguments += [string]$item
    }
    $arguments += @(
        '-C', $workingRoot,
        '--output-schema', $schemaPath,
        '-o', $responsePath,
        $prompt
    )

    $startedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    $processResult = $null
    try {
        $processResult = Invoke-VibeCapturedProcess `
            -Command ([string]$adapterResolution.command_path) `
            -Arguments $arguments `
            -WorkingDirectory $workingRoot `
            -TimeoutSeconds ([int]$nativePolicy.default_timeout_seconds) `
            -StdOutPath $stdoutPath `
            -StdErrPath $stderrPath `
            -EnvironmentOverrides $environmentOverrides
    } finally {
        if (
            $null -ne $codexHomeBinding -and
            (Test-VibeObjectHasProperty -InputObject $codexHomeBinding -PropertyName 'codex_home_root')
        ) {
            Remove-VibeNativeSpecialistCodexHomeRoot -CodexHomeRoot ([string]$codexHomeBinding.codex_home_root)
        }
    }
    $finishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')

    $afterSnapshot = Get-VibePathStatusSnapshot -RootPath $workingRoot
    Write-VgoUtf8NoBomText -Path $afterGitPath -Content ((@($afterSnapshot.lines) -join [Environment]::NewLine) + [Environment]::NewLine)

    $observedChangedFiles = Get-VibeObservedChangedPaths `
        -BeforeSnapshot $beforeSnapshot `
        -AfterSnapshot $afterSnapshot `
        -SnapshotRoot $workingRoot `
        -IgnoredPaths @($SessionRoot)

    $parsedResponse = $null
    $responseParseError = $null
    if (Test-Path -LiteralPath $responsePath) {
        try {
            $parsedResponse = Get-Content -LiteralPath $responsePath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $responseParseError = $_.Exception.Message
        }
    } else {
        $responseParseError = 'native_specialist_consultation_response_missing'
    }

    $schemaValidation = Test-VibeSpecialistConsultationResponseAgainstSchema -Response $parsedResponse -Schema $schema
    $payloadCompleteness = Test-VibeSpecialistConsultationPayloadCompleteness -Result $parsedResponse -Policy $resolvedPolicy
    $responseStatus = if ($parsedResponse -and (Test-VibeObjectHasProperty -InputObject $parsedResponse -PropertyName 'status')) { [string]$parsedResponse.status } else { '' }
    $verificationPassed = (-not [bool]$processResult.timed_out) -and ([int]$processResult.exit_code -eq 0) -and ($null -ne $parsedResponse) -and [bool]$schemaValidation.passed -and [bool]$payloadCompleteness.passed -and (@('completed', 'completed_with_notes') -contains $responseStatus) -and (@($observedChangedFiles).Count -eq 0)
    $status = if ($verificationPassed) { 'completed' } elseif ([bool]$processResult.timed_out) { 'timed_out' } else { 'failed' }

    $result = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_consultation'
        status = $status
        started_at = $startedAt
        finished_at = $finishedAt
        command = [string]$adapterResolution.command_path
        arguments = @($arguments)
        display_command = @([string]$adapterResolution.command_path) + @($arguments) -join ' '
        cwd = $workingRoot
        timeout_seconds = [int]$nativePolicy.default_timeout_seconds
        expected_exit_code = 0
        exit_code = [int]$processResult.exit_code
        timed_out = [bool]$processResult.timed_out
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        stdout_preview = @($processResult.stdout_preview)
        stderr_preview = @($processResult.stderr_preview)
        verification_passed = [bool]$verificationPassed
        skill_id = [string]$Consultation.skill_id
        consultation_window_id = [string]$WindowId
        consultation_stage = [string]$Stage
        live_native_execution = $true
        degraded = [bool](-not $verificationPassed)
        blocked = $false
        native_skill_entrypoint = [string]$Consultation.native_skill_entrypoint
        response_json_path = $responsePath
        prompt_path = $promptPath
        schema_path = $schemaPath
        git_status_before_path = $beforeGitPath
        git_status_after_path = $afterGitPath
        summary = if ($parsedResponse -and (Test-VibeObjectHasProperty -InputObject $parsedResponse -PropertyName 'summary')) { [string]$parsedResponse.summary } else { $null }
        consultation_notes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if ($parsedResponse -and (Test-VibeObjectHasProperty -InputObject $parsedResponse -PropertyName 'consultation_notes')) { $parsedResponse.consultation_notes } else { $null })
        adoption_notes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if ($parsedResponse -and (Test-VibeObjectHasProperty -InputObject $parsedResponse -PropertyName 'adoption_notes')) { $parsedResponse.adoption_notes } else { $null })
        verification_notes = ConvertTo-VibeConsultationArrayOrEmpty -Value $(if ($parsedResponse -and (Test-VibeObjectHasProperty -InputObject $parsedResponse -PropertyName 'verification_notes')) { $parsedResponse.verification_notes } else { $null })
        observed_changed_files = @($observedChangedFiles)
        response_parse_error = $responseParseError
        response_schema_errors = @($schemaValidation.errors)
        payload_gate_errors = @($payloadCompleteness.errors)
    }
    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $result

    return [pscustomobject]@{
        category = if ($verificationPassed) { 'consulted' } else { 'degraded' }
        result = $result
        result_path = $resultPath
    }
}

function New-VibeSpecialistConsultationWindowSummary {
    param(
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedConsultation = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$DeferredToExecution = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Blocked = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Degraded = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ConsultedUnits = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$RoutedUnits = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$UserDisclosures = @()
    )

    return [pscustomobject]@{
        window_id = [string]$WindowId
        stage = [string]$Stage
        approved_consultation_count = @($ApprovedConsultation).Count
        deferred_to_execution_count = @($DeferredToExecution).Count
        blocked_count = @($Blocked).Count
        degraded_count = @($Degraded).Count
        consulted_unit_count = @($ConsultedUnits).Count
        routed_unit_count = @($RoutedUnits).Count
        user_disclosure_count = @($UserDisclosures).Count
        approved_skill_ids = @($ApprovedConsultation | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        deferred_skill_ids = @($DeferredToExecution | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        blocked_skill_ids = @($Blocked | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        degraded_skill_ids = @($Degraded | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        consulted_skill_ids = @($ConsultedUnits | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        routed_skill_ids = @($RoutedUnits | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
    }
}

function Test-VibeSpecialistConsultationFreezeGate {
    param(
        [AllowNull()] [object]$Receipt = $null,
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    if ($null -eq $Receipt -or -not [bool]$resolvedPolicy.freeze_gate_enabled -or -not [bool]$Receipt.enabled) {
        return [pscustomobject]@{
            passed = $true
            errors = @()
            approved_skill_ids = @()
            consulted_skill_ids = @()
            routed_skill_ids = @()
            degraded_skill_ids = @()
            deferred_skill_ids = @()
            blocked_skill_ids = @()
            disclosed_skill_ids = @()
        }
    }

    $approvedSkillIds = @($Receipt.approved_consultation | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $consultedSkillIds = @($Receipt.consulted_units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $routedSkillIds = @($Receipt.routed_units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $degradedSkillIds = @($Receipt.degraded | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $deferredSkillIds = @($Receipt.deferred_to_execution | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $blockedSkillIds = @($Receipt.blocked | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $disclosedSkillIds = @($Receipt.user_disclosures | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    $consultedIndex = @{}
    foreach ($entry in @($Receipt.consulted_units)) {
        if ($null -ne $entry -and -not [string]::IsNullOrWhiteSpace([string]$entry.skill_id)) {
            $consultedIndex[[string]$entry.skill_id] = $entry
        }
    }
    $routedIndex = @{}
    foreach ($entry in @($Receipt.routed_units)) {
        if ($null -ne $entry -and -not [string]::IsNullOrWhiteSpace([string]$entry.skill_id)) {
            $routedIndex[[string]$entry.skill_id] = $entry
        }
    }
    $degradedIndex = @{}
    foreach ($entry in @($Receipt.degraded)) {
        if ($null -ne $entry -and -not [string]::IsNullOrWhiteSpace([string]$entry.skill_id)) {
            $degradedIndex[[string]$entry.skill_id] = $entry
        }
    }

    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($skillId in @($approvedSkillIds)) {
        $outcomeCount = 0
        if ($consultedIndex.ContainsKey($skillId)) { $outcomeCount += 1 }
        if ($routedIndex.ContainsKey($skillId)) { $outcomeCount += 1 }
        if ($degradedIndex.ContainsKey($skillId)) { $outcomeCount += 1 }
        if ($deferredSkillIds -contains $skillId) { $outcomeCount += 1 }
        if ($blockedSkillIds -contains $skillId) { $outcomeCount += 1 }

        if ([bool]$resolvedPolicy.require_outcome_coverage_for_approved_skills -and $outcomeCount -eq 0) {
            $errors.Add(("missing_outcome:{0}" -f $skillId)) | Out-Null
        }
        if ($outcomeCount -gt 1) {
            $errors.Add(("multiple_outcomes:{0}" -f $skillId)) | Out-Null
        }
        if ([bool]$resolvedPolicy.require_disclosure_coverage_for_approved_skills -and -not ($disclosedSkillIds -contains $skillId)) {
            $errors.Add(("missing_user_disclosure:{0}" -f $skillId)) | Out-Null
        }

        if ($consultedIndex.ContainsKey($skillId)) {
            $consulted = $consultedIndex[$skillId]
            if (-not [bool]$consulted.verification_passed) {
                $errors.Add(("consulted_unit_not_verified:{0}" -f $skillId)) | Out-Null
            }
            $payloadCompleteness = Test-VibeSpecialistConsultationPayloadCompleteness -Result $consulted -Policy $resolvedPolicy
            foreach ($payloadError in @($payloadCompleteness.errors)) {
                $errors.Add(("consulted_payload_incomplete:{0}:{1}" -f $skillId, [string]$payloadError)) | Out-Null
            }
        }

        if ([bool]$resolvedPolicy.fail_freeze_on_live_degraded_results -and $degradedIndex.ContainsKey($skillId)) {
            $degraded = $degradedIndex[$skillId]
            if ((Test-VibeObjectHasProperty -InputObject $degraded -PropertyName 'live_native_execution') -and [bool]$degraded.live_native_execution) {
                $errors.Add(("live_degraded_result:{0}" -f $skillId)) | Out-Null
            }
        }
    }

    foreach ($skillId in @($disclosedSkillIds)) {
        if ($skillId -notin $approvedSkillIds) {
            $errors.Add(("disclosure_without_approval:{0}" -f $skillId)) | Out-Null
        }
    }

    return [pscustomobject]@{
        passed = [bool]($errors.Count -eq 0)
        errors = [string[]]$errors.ToArray()
        approved_skill_ids = @($approvedSkillIds)
        consulted_skill_ids = @($consultedSkillIds)
        routed_skill_ids = @($routedSkillIds)
        degraded_skill_ids = @($degradedSkillIds)
        deferred_skill_ids = @($deferredSkillIds)
        blocked_skill_ids = @($blockedSkillIds)
        disclosed_skill_ids = @($disclosedSkillIds)
    }
}

function Assert-VibeSpecialistConsultationFreezeGate {
    param(
        [AllowNull()] [object]$Receipt = $null,
        [AllowNull()] [object]$Policy = $null,
        [Parameter(Mandatory)] [string]$FreezeTarget
    )

    $gate = Test-VibeSpecialistConsultationFreezeGate -Receipt $Receipt -Policy $Policy
    if (-not [bool]$gate.passed) {
        $windowId = if ($null -ne $Receipt -and (Test-VibeObjectHasProperty -InputObject $Receipt -PropertyName 'window_id') -and -not [string]::IsNullOrWhiteSpace([string]$Receipt.window_id)) {
            [string]$Receipt.window_id
        } else {
            'unknown'
        }
        throw ("specialist consultation freeze gate failed for {0} before {1}: {2}" -f $windowId, $FreezeTarget, (@($gate.errors) -join ', '))
    }

    return $gate
}

function Invoke-VibeSpecialistConsultationWindow {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [ValidateSet('discussion', 'planning')] [string]$WindowId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$SourceArtifactPath,
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Recommendations = @(),
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = Get-VibeSpecialistConsultationPolicy -Policy $Policy
    $receiptPath = Get-VibeSpecialistConsultationReceiptPath -SessionRoot $SessionRoot -WindowId $WindowId
    $defaultStage = (Get-VibeSpecialistConsultationWindowDefaults -WindowId $WindowId -Stage $Stage).stage

    if (-not [bool]$resolvedPolicy.enabled -or -not (@($resolvedPolicy.allowed_windows) -contains $WindowId)) {
        $disabledReceipt = [pscustomobject]@{
            enabled = $false
            policy_version = [int]$resolvedPolicy.version
            policy_id = [string]$resolvedPolicy.policy_id
            window_id = [string]$WindowId
            stage = [string]$defaultStage
            candidate_skill_ids = @()
            approved_consultation = @()
            deferred_to_execution = @()
            blocked = @()
            degraded = @()
            consulted_units = @()
            routed_units = @()
            user_disclosures = @()
            summary = New-VibeSpecialistConsultationWindowSummary -WindowId $WindowId -Stage $defaultStage
        }
        $disabledReceipt | Add-Member -NotePropertyName freeze_gate -NotePropertyValue (Test-VibeSpecialistConsultationFreezeGate -Receipt $disabledReceipt -Policy $resolvedPolicy)
        Write-VibeJsonArtifact -Path $receiptPath -Value $disabledReceipt
        return [pscustomobject]@{
            receipt_path = $receiptPath
            receipt = $disabledReceipt
        }
    }

    $split = Split-VibeSpecialistConsultationCandidates `
        -Recommendations @($Recommendations) `
        -WindowId $WindowId `
        -Stage $defaultStage `
        -Policy $resolvedPolicy
    $approvedConsultation = @($split.approved_consultation)
    $deferredToExecution = @($split.deferred_to_execution)
    $blocked = @($split.blocked)
    $userDisclosures = New-VibeSpecialistConsultationUserDisclosures `
        -ApprovedConsultation @($approvedConsultation) `
        -WindowId $WindowId `
        -Stage $defaultStage `
        -Policy $resolvedPolicy

    $consultedUnits = New-Object System.Collections.Generic.List[object]
    $routedUnits = New-Object System.Collections.Generic.List[object]
    $degraded = New-Object System.Collections.Generic.List[object]
    foreach ($consultation in @($approvedConsultation)) {
        $unitId = ('consult-{0}-{1}' -f [string]$WindowId, [string]$consultation.skill_id)
        $outcome = Invoke-VibeSpecialistConsultationUnit `
            -UnitId $unitId `
            -Consultation $consultation `
            -SessionRoot $SessionRoot `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -RunId $RunId `
            -WindowId $WindowId `
            -Stage $defaultStage `
            -SourceArtifactPath $SourceArtifactPath `
            -Policy $resolvedPolicy
        $entry = $outcome.result | Select-Object *, @{ Name = 'result_path'; Expression = { [string]$outcome.result_path } }
        if ([string]$outcome.category -eq 'consulted') {
            $consultedUnits.Add($entry) | Out-Null
        } elseif ([string]$outcome.category -eq 'routed') {
            $routedUnits.Add($entry) | Out-Null
        } elseif ([string]$outcome.category -eq 'degraded') {
            $degraded.Add($entry) | Out-Null
        } else {
            Write-Warning ("Unexpected specialist consultation outcome category '{0}' for window '{1}' skill '{2}'; treating as degraded." -f [string]$outcome.category, [string]$WindowId, [string]$consultation.skill_id)
            $degraded.Add($entry) | Out-Null
        }
    }

    $receipt = [pscustomobject]@{
        enabled = [bool]$resolvedPolicy.enabled
        policy_version = [int]$resolvedPolicy.version
        policy_id = [string]$resolvedPolicy.policy_id
        window_id = [string]$WindowId
        stage = [string]$defaultStage
        candidate_skill_ids = @($Recommendations | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        approved_consultation = @($approvedConsultation)
        deferred_to_execution = @($deferredToExecution)
        blocked = @($blocked)
        degraded = [object[]]$degraded.ToArray()
        consulted_units = [object[]]$consultedUnits.ToArray()
        routed_units = [object[]]$routedUnits.ToArray()
        user_disclosures = @($userDisclosures)
        summary = New-VibeSpecialistConsultationWindowSummary `
            -WindowId $WindowId `
            -Stage $defaultStage `
            -ApprovedConsultation @($approvedConsultation) `
            -DeferredToExecution @($deferredToExecution) `
            -Blocked @($blocked) `
            -Degraded @($degraded.ToArray()) `
            -ConsultedUnits @($consultedUnits.ToArray()) `
            -RoutedUnits @($routedUnits.ToArray()) `
            -UserDisclosures @($userDisclosures)
    }
    $receipt | Add-Member -NotePropertyName freeze_gate -NotePropertyValue (Test-VibeSpecialistConsultationFreezeGate -Receipt $receipt -Policy $resolvedPolicy)
    Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

    return [pscustomobject]@{
        receipt_path = $receiptPath
        receipt = $receipt
    }
}

function New-VibeSpecialistConsultationRuntimeProjection {
    param(
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Receipts = @()
    )

    $windows = New-Object System.Collections.Generic.List[object]
    foreach ($receipt in @($Receipts)) {
        if ($null -eq $receipt) {
            continue
        }
        $windows.Add(
            [pscustomobject]@{
                window_id = [string]$receipt.window_id
                stage = [string]$receipt.stage
                approved_consultation_count = if ($receipt.summary) { [int]$receipt.summary.approved_consultation_count } else { 0 }
                consulted_unit_count = if ($receipt.summary) { [int]$receipt.summary.consulted_unit_count } else { 0 }
                routed_unit_count = if ($receipt.summary) { [int]$receipt.summary.routed_unit_count } else { 0 }
                user_disclosure_count = if ($receipt.summary) { [int]$receipt.summary.user_disclosure_count } else { 0 }
                approved_skill_ids = if ($receipt.summary) { [object[]]@($receipt.summary.approved_skill_ids) } else { @() }
                consulted_skill_ids = if ($receipt.summary) { [object[]]@($receipt.summary.consulted_skill_ids) } else { @() }
                routed_skill_ids = if ($receipt.summary) { [object[]]@($receipt.summary.routed_skill_ids) } else { @() }
                deferred_skill_ids = if ($receipt.summary) { [object[]]@($receipt.summary.deferred_skill_ids) } else { @() }
                degraded_skill_ids = if ($receipt.summary) { [object[]]@($receipt.summary.degraded_skill_ids) } else { @() }
                freeze_gate_passed = if ($receipt.PSObject.Properties.Name -contains 'freeze_gate') { [bool]$receipt.freeze_gate.passed } else { $true }
                freeze_gate_error_count = if ($receipt.PSObject.Properties.Name -contains 'freeze_gate') { @($receipt.freeze_gate.errors).Count } else { 0 }
            }
        ) | Out-Null
    }

    $windowArray = [object[]]$windows.ToArray()
    return [pscustomobject]@{
        enabled = [bool](@($windowArray).Count -gt 0)
        window_count = @($windowArray).Count
        approved_consultation_count = [int]((@($windowArray | ForEach-Object { [int]$_.approved_consultation_count }) | Measure-Object -Sum).Sum)
        consulted_unit_count = [int]((@($windowArray | ForEach-Object { [int]$_.consulted_unit_count }) | Measure-Object -Sum).Sum)
        routed_unit_count = [int]((@($windowArray | ForEach-Object { [int]$_.routed_unit_count }) | Measure-Object -Sum).Sum)
        user_disclosure_count = [int]((@($windowArray | ForEach-Object { [int]$_.user_disclosure_count }) | Measure-Object -Sum).Sum)
        freeze_gate_passed = [bool](@($windowArray | Where-Object { -not [bool]$_.freeze_gate_passed }).Count -eq 0)
        freeze_gate_error_count = [int]((@($windowArray | ForEach-Object { [int]$_.freeze_gate_error_count }) | Measure-Object -Sum).Sum)
        windows = $windowArray
    }
}
