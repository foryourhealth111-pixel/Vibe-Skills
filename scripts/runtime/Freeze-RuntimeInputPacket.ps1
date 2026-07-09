param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$EntryIntentId = '',
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$HostDecisionJson = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
    [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
    [string[]]$ApprovedSpecialistSkillIds = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeSkillUsage.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeSkillRouting.Common.ps1')

function Get-VibeRouterTaskType {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    return Get-VibeInferredTaskType -Task $Task
}

function New-VibeAdviceSnapshot {
    param(
        [string]$Name,
        [object]$Advice
    )

    if ($null -eq $Advice) {
        return $null
    }

    $snapshot = [ordered]@{
        name = $Name
    }

    foreach ($field in @('enabled', 'mode', 'enforcement', 'reason', 'preserve_routing_assignment', 'confirm_required', 'scope_applicable', 'task_applicable', 'grade_applicable')) {
        if ($Advice.PSObject.Properties.Name -contains $field) {
            $snapshot[$field] = $Advice.$field
        }
    }

    return [pscustomobject]$snapshot
}

function Get-VibeRouteAdviceFieldNames {
    param(
        [AllowNull()] [object]$RouteResult
    )

    if ($null -eq $RouteResult) {
        return @()
    }

    return @(
        @($RouteResult.PSObject.Properties) |
            Where-Object {
                $_.Name -match '_advice$' -and $null -ne $_.Value
            } |
            ForEach-Object { [string]$_.Name } |
            Sort-Object -Unique
    )
}

function Invoke-VibeFrozenRoute {
    param(
        [Parameter(Mandatory)] [string]$RouterScriptPath,
        [Parameter(Mandatory)] [string[]]$BaseArgs,
        [AllowEmptyString()] [string]$HostDecisionJson = ''
    )

    $routeArgs = @($BaseArgs)
    if (-not [string]::IsNullOrWhiteSpace([string]$HostDecisionJson)) {
        $routeArgs += @('-HostDecisionJson', [string]$HostDecisionJson)
    }

    $routeInvocation = Invoke-VgoPowerShellFile -ScriptPath $RouterScriptPath -ArgumentList $routeArgs -NoProfile
    if ([int]$routeInvocation.exit_code -ne 0) {
        throw ("Failed to freeze runtime input packet because local installed skill recommender exited with code {0}." -f [int]$routeInvocation.exit_code)
    }

    $routeJson = (@($routeInvocation.output) -join [Environment]::NewLine).Trim()
    return ($routeJson | ConvertFrom-Json)
}

function Test-VibeSingleOptionCanonicalConfirmSurface {
    param(
        [AllowNull()] [object]$RouteResult,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = ''
    )

    $resolvedEntryIntentId = Resolve-VibeControllerEntryIntentId `
        -EntryIntentId $EntryIntentId `
        -RuntimeSelectedSkill $RuntimeSelectedSkill
    if (
        -not [string]::IsNullOrWhiteSpace([string]$EntryIntentId) -and
        -not [string]::Equals(
            [string]$resolvedEntryIntentId,
            [string]$RuntimeSelectedSkill,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        return $false
    }
    if ($null -eq $RouteResult -or [string]$RouteResult.route_mode -ne 'confirm_required') {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace([string]$RuntimeSelectedSkill)) {
        return $false
    }
    if (-not ($RouteResult.PSObject.Properties.Name -contains 'selected') -or $null -eq $RouteResult.selected) {
        return $false
    }
    $selectedSkill = [string]$RouteResult.selected.skill
    if (-not [string]::Equals($selectedSkill, [string]$RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    if (-not ($RouteResult.PSObject.Properties.Name -contains 'confirm_ui') -or $null -eq $RouteResult.confirm_ui) {
        return $false
    }

    $confirmUi = $RouteResult.confirm_ui
    $options = if ($confirmUi.PSObject.Properties.Name -contains 'options' -and $null -ne $confirmUi.options) {
        @($confirmUi.options)
    } else {
        @()
    }
    if ($options.Count -ne 1) {
        return $false
    }

    $onlySkill = [string]$options[0].skill
    if (-not [string]::Equals($onlySkill, [string]$RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }

    if (-not ($confirmUi.PSObject.Properties.Name -contains 'route_decision_contract') -or $null -eq $confirmUi.route_decision_contract) {
        return $false
    }
    $contract = $confirmUi.route_decision_contract
    if (-not ($contract.PSObject.Properties.Name -contains 'preferred_payload') -or $null -eq $contract.preferred_payload) {
        return $false
    }

    return $true
}

function Resolve-VibeControllerEntryIntentId {
    param(
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = ''
    )

    if ([string]::IsNullOrWhiteSpace([string]$EntryIntentId)) {
        return ''
    }
    return [string]$EntryIntentId
}

function Get-VibeSkillMetadata {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $authority = Resolve-VibeLocalSkillAuthority `
        -RepoRoot $RepoRoot `
        -SkillId $SkillId `
        -TargetRoot $TargetRoot `
        -HostId $HostId
    if (-not [bool]$authority.valid) {
        return [pscustomobject]@{
            skill_id = $SkillId
            skill_path = $null
            skill_root = $null
            description = $null
            authority_valid = $false
            authority_reason = [string]$authority.reason
        }
    }
    $skillPath = [string]$authority.canonical_entrypoint

    $description = $null
    foreach ($line in @(Get-Content -LiteralPath $skillPath -Encoding UTF8 -TotalCount 20)) {
        if ([string]$line -match '^\s*description:\s*(.+?)\s*$') {
            $description = $Matches[1].Trim()
            break
        }
    }

    return [pscustomobject]@{
        skill_id = $SkillId
        skill_path = [System.IO.Path]::GetFullPath($skillPath)
        skill_root = [string]$authority.skill_root
        description = $description
        authority_valid = $true
        authority_reason = 'ok'
        source_root = [string]$authority.source_root
        source_kind = [string]$authority.source_kind
        source_priority = [int]$authority.source_priority
        duplicate_state = [string]$authority.duplicate_state
    }
}

function Get-VibeCustomAdmissionIndex {
    param(
        [AllowNull()] [object]$RouteResult
    )

    $index = @{}
    if ($null -eq $RouteResult) {
        return $index
    }
    if (-not ($RouteResult.PSObject.Properties.Name -contains 'custom_admission')) {
        return $index
    }

    $customAdmission = $RouteResult.custom_admission
    if ($null -eq $customAdmission) {
        return $index
    }
    if (-not ($customAdmission.PSObject.Properties.Name -contains 'admitted_candidates')) {
        return $index
    }

    foreach ($candidate in @($customAdmission.admitted_candidates)) {
        if ($null -eq $candidate) {
            continue
        }
        $skillId = if ($candidate.PSObject.Properties.Name -contains 'skill_id') { [string]$candidate.skill_id } else { '' }
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        $index[$skillId] = $candidate
    }

    return $index
}

function Resolve-VibeSpecialistWriteScopeTemplate {
    param(
        [AllowEmptyString()] [string]$Template,
        [Parameter(Mandatory)] [string]$SkillId
    )

    $value = if ([string]::IsNullOrWhiteSpace($Template)) {
        'specialist:{skill_id}'
    } else {
        [string]$Template
    }
    return $value.Replace('{skill_id}', $SkillId)
}

function Get-VibeSpecialistBindingProfile {
    param(
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [object]$Policy,
        [Parameter(Mandatory)] [object]$DispatchContract
    )

    return [pscustomobject]@{
        binding_profile = 'default'
        dispatch_phase = [string]$DispatchContract.dispatch_phase
        execution_priority = [int]$DispatchContract.execution_priority
        lane_policy = [string]$DispatchContract.lane_policy
        parallelizable_in_root_xl = [bool]$DispatchContract.parallelizable_in_root_xl
        write_scope = Resolve-VibeSpecialistWriteScopeTemplate -Template ([string]$DispatchContract.write_scope_template) -SkillId $SkillId
        review_mode = [string]$DispatchContract.review_mode
    }
}

function New-VibeSpecialistRecommendation {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$Source,
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [string]$Reason,
        [AllowNull()] [object]$PackId,
        [AllowNull()] [object]$Confidence,
        [AllowNull()] [object]$Rank,
        [Parameter(Mandatory)] [object]$DispatchContract,
        [AllowNull()] [object]$PromotionPolicy = $null,
        [AllowNull()] [object]$CustomMetadata = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $metadata = Get-VibeSkillMetadata -RepoRoot $RepoRoot -SkillId $SkillId -TargetRoot $TargetRoot -HostId $HostId
    $bindingProfile = Get-VibeSpecialistBindingProfile -SkillId $SkillId -Policy $DispatchContract.policy -DispatchContract $DispatchContract
    $customNativeSkillEntrypoint = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'native_skill_entrypoint' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.native_skill_entrypoint)) {
        [string]$CustomMetadata.native_skill_entrypoint
    } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_md_path' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_md_path)) {
        [string]$CustomMetadata.skill_md_path
    } else {
        $null
    }
    $nativeSkillEntrypoint = if ($metadata.skill_path) {
        [string]$metadata.skill_path
    } elseif (-not [string]::IsNullOrWhiteSpace([string]$customNativeSkillEntrypoint)) {
        [string]$customNativeSkillEntrypoint
    } else {
        $null
    }
    $nativeSkillDescription = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'description' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.description)) {
        [string]$CustomMetadata.description
    } elseif ($metadata.description) {
        [string]$metadata.description
    } else {
        $null
    }
    $skillRoot = if ($metadata.PSObject.Properties.Name -contains 'skill_root' -and -not [string]::IsNullOrWhiteSpace([string]$metadata.skill_root)) {
        [string]$metadata.skill_root
    } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_root' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_root)) {
        [string]$CustomMetadata.skill_root
    } elseif (-not [string]::IsNullOrWhiteSpace([string]$nativeSkillEntrypoint)) {
        [string](Split-Path -Parent $nativeSkillEntrypoint)
    } else {
        $null
    }
    $progressiveLoadPolicy = if (-not [string]::IsNullOrWhiteSpace([string]$nativeSkillEntrypoint)) {
        @(
            "Open the specialist $nativeSkillEntrypoint entrypoint first.",
            "If this specialist is disclosed only by native_skill_entrypoint, keep same-session loading path-based and do not replace it with Skill($SkillId) unless that skill name is explicitly host-visible in the current session."
        )
    } else {
        @()
    }
    $promotionMetadata = Get-VgoSkillPromotionMetadata `
        -Prompt $Task `
        -SkillMdPath $nativeSkillEntrypoint `
        -SkillRoot $skillRoot `
        -Description $nativeSkillDescription `
        -RequiredInputs @($DispatchContract.required_inputs) `
        -ExpectedOutputs @($DispatchContract.expected_outputs) `
        -VerificationExpectation ([string]$DispatchContract.verification_expectation) `
        -NativeUsageRequired ([bool]$DispatchContract.native_usage_required) `
        -MustPreserveWorkflow ([bool]$DispatchContract.must_preserve_workflow) `
        -PromotionPolicy $PromotionPolicy
    return [pscustomobject]@{
        skill_id = $SkillId
        source = $Source
        pack_id = if ($null -eq $PackId) { $null } else { [string]$PackId }
        rank = if ($null -eq $Rank) { $null } else { [int]$Rank }
        confidence = if ($null -eq $Confidence) { $null } else { [double]$Confidence }
        reason = $Reason
        task_type = $TaskType
        recommended_scope = 'bounded specialist assistance inside vibe-governed runtime'
        bounded_role = [string]$DispatchContract.bounded_role
        native_usage_required = [bool]$DispatchContract.native_usage_required
        must_preserve_workflow = [bool]$DispatchContract.must_preserve_workflow
        required_inputs = @($DispatchContract.required_inputs)
        expected_outputs = @($DispatchContract.expected_outputs)
        verification_expectation = [string]$DispatchContract.verification_expectation
        binding_profile = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'binding_profile') { [string]$CustomMetadata.binding_profile } else { [string]$bindingProfile.binding_profile }
        dispatch_phase = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$CustomMetadata.dispatch_phase } else { [string]$bindingProfile.dispatch_phase }
        execution_priority = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'execution_priority') { [int]$CustomMetadata.execution_priority } else { [int]$bindingProfile.execution_priority }
        lane_policy = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'lane_policy') { [string]$CustomMetadata.lane_policy } else { [string]$bindingProfile.lane_policy }
        parallelizable_in_root_xl = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'parallelizable_in_root_xl') { [bool]$CustomMetadata.parallelizable_in_root_xl } else { [bool]$bindingProfile.parallelizable_in_root_xl }
        write_scope = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'write_scope') { [string]$CustomMetadata.write_scope } else { [string]$bindingProfile.write_scope }
        review_mode = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'review_mode') { [string]$CustomMetadata.review_mode } else { [string]$bindingProfile.review_mode }
        native_skill_entrypoint = $nativeSkillEntrypoint
        skill_root = $skillRoot
        source_root = if ($metadata.PSObject.Properties.Name -contains 'source_root' -and -not [string]::IsNullOrWhiteSpace([string]$metadata.source_root)) { [string]$metadata.source_root } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'source_root') { [string]$CustomMetadata.source_root } else { $null }
        source_kind = if ($metadata.PSObject.Properties.Name -contains 'source_kind' -and -not [string]::IsNullOrWhiteSpace([string]$metadata.source_kind)) { [string]$metadata.source_kind } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'source_kind') { [string]$CustomMetadata.source_kind } else { $null }
        source_priority = if ($metadata.PSObject.Properties.Name -contains 'source_priority' -and $null -ne $metadata.source_priority) { [int]$metadata.source_priority } else { $null }
        duplicate_state = if ($metadata.PSObject.Properties.Name -contains 'duplicate_state') { [string]$metadata.duplicate_state } else { $null }
        local_skill_authority = if ($metadata.PSObject.Properties.Name -contains 'authority_valid') { [bool]$metadata.authority_valid } else { $false }
        local_skill_authority_reason = if ($metadata.PSObject.Properties.Name -contains 'authority_reason') { [string]$metadata.authority_reason } else { 'not_in_local_skill_index' }
        native_skill_description = $nativeSkillDescription
        visibility_class = if (-not [string]::IsNullOrWhiteSpace([string]$nativeSkillEntrypoint) -and -not [string]::IsNullOrWhiteSpace([string]$skillRoot)) { 'path_resolved' } else { 'path_unresolved' }
        usage_required = [bool]$DispatchContract.native_usage_required
        invocation_reason = $Reason
        expected_contribution = [string]$DispatchContract.bounded_role
        progressive_load_policy = @($progressiveLoadPolicy)
        promotion_eligible = [bool]$promotionMetadata.promotion_eligible
        destructive = [bool]$promotionMetadata.destructive
        destructive_reason_codes = [object[]]@($promotionMetadata.destructive_reason_codes)
        rollback_possible = [bool]$promotionMetadata.rollback_possible
        snapshot_required = [bool]$promotionMetadata.snapshot_required
        contract_complete = [bool]$promotionMetadata.contract_complete
        contract_missing_fields = [object[]]@($promotionMetadata.contract_missing_fields)
        recommended_promotion_action = [string]$promotionMetadata.recommended_promotion_action
    }
}

function Get-VibeStageAssistantHints {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [object]$RouteResult,
        [Parameter(Mandatory)] [string]$RuntimeSelectedSkill,
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [object]$Policy,
        [AllowNull()] [object]$PromotionPolicy = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $limit = 4
    if ($Policy.PSObject.Properties.Name -contains 'specialist_recommendation_limit' -and $Policy.specialist_recommendation_limit -ne $null) {
        $limit = [int]$Policy.specialist_recommendation_limit
    }
    $dispatchContract = if ($Policy.PSObject.Properties.Name -contains 'skill_execution_contract' -and $null -ne $Policy.skill_execution_contract) {
        $Policy.skill_execution_contract
    } else {
        [pscustomobject]@{
            bounded_role = 'specialist_assist'
            native_usage_required = $true
            must_preserve_workflow = $true
            dispatch_phase = 'in_execution'
            execution_priority = 50
            lane_policy = 'inherit_grade'
            parallelizable_in_root_xl = $true
            write_scope_template = 'specialist:{skill_id}'
            review_mode = 'native_contract'
            required_inputs = @(
                'bounded specialist subtask contract',
                'frozen requirement context',
                'relevant source files or domain artifacts'
            )
            expected_outputs = @(
                'bounded specialist findings or code changes',
                'verification notes aligned with the specialist skill'
            )
            verification_expectation = 'Preserve the specialist skill''s native workflow, boundaries, and validation style.'
        }
    }
    $dispatchContractForHint = [pscustomobject]@{
        bounded_role = [string]$dispatchContract.bounded_role
        native_usage_required = [bool]$dispatchContract.native_usage_required
        must_preserve_workflow = [bool]$dispatchContract.must_preserve_workflow
        dispatch_phase = [string]$dispatchContract.dispatch_phase
        execution_priority = [int]$dispatchContract.execution_priority
        lane_policy = [string]$dispatchContract.lane_policy
        parallelizable_in_root_xl = [bool]$dispatchContract.parallelizable_in_root_xl
        write_scope_template = [string]$dispatchContract.write_scope_template
        review_mode = [string]$dispatchContract.review_mode
        required_inputs = @($dispatchContract.required_inputs)
        expected_outputs = @($dispatchContract.expected_outputs)
        verification_expectation = [string]$dispatchContract.verification_expectation
        policy = $Policy
    }

    # Current route output omits retired sibling-role candidate lists. Old runtime
    # packets remain readable through VibeRuntime.Common.ps1 compatibility helpers.
    return @()
}

function Get-VibeSpecialistRecommendations {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [object]$RouteResult,
        [Parameter(Mandatory)] [string]$RuntimeSelectedSkill,
        [AllowEmptyString()] [string]$RouterSelectedSkill = '',
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [object]$Policy,
        [AllowNull()] [object]$PromotionPolicy = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $limit = 4
    if ($Policy.PSObject.Properties.Name -contains 'specialist_recommendation_limit' -and $Policy.specialist_recommendation_limit -ne $null) {
        $limit = [int]$Policy.specialist_recommendation_limit
    }
    $minimumRecommendationConfidence = 0.0
    if ($Policy.PSObject.Properties.Name -contains 'minimum_specialist_recommendation_confidence' -and $Policy.minimum_specialist_recommendation_confidence -ne $null) {
        $minimumRecommendationConfidence = [double]$Policy.minimum_specialist_recommendation_confidence
    }
    $dispatchContract = if ($Policy.PSObject.Properties.Name -contains 'skill_execution_contract' -and $null -ne $Policy.skill_execution_contract) {
        $Policy.skill_execution_contract
    } else {
        [pscustomobject]@{
            bounded_role = 'specialist_assist'
            native_usage_required = $true
            must_preserve_workflow = $true
            dispatch_phase = 'in_execution'
            execution_priority = 50
            lane_policy = 'inherit_grade'
            parallelizable_in_root_xl = $true
            write_scope_template = 'specialist:{skill_id}'
            review_mode = 'native_contract'
            required_inputs = @('bounded specialist subtask contract')
            expected_outputs = @('bounded specialist result')
            verification_expectation = 'Preserve the specialist skill native workflow.'
        }
    }

    $dispatchContractForRecommendation = [pscustomobject]@{}
    foreach ($property in @($dispatchContract.PSObject.Properties)) {
        $dispatchContractForRecommendation | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value
    }
    $dispatchContractForRecommendation | Add-Member -NotePropertyName policy -NotePropertyValue $Policy -Force

    $recommendations = @()
    $seen = @{}
    $customAdmissionIndex = Get-VibeCustomAdmissionIndex -RouteResult $RouteResult
    $isXlRoute = (
        $RouteResult.PSObject.Properties.Name -contains 'grade' -and
        [string]::Equals([string]$RouteResult.grade, 'XL', [System.StringComparison]::OrdinalIgnoreCase)
    )

    foreach ($ranked in @($RouteResult.ranked)) {
        if (@($recommendations).Count -ge $limit) {
            break
        }

        $skillId = $null
        if ($ranked.PSObject.Properties.Name -contains 'selected_candidate') {
            $skillId = [string]$ranked.selected_candidate
        }
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        if ([string]::Equals($skillId, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        if ($seen.ContainsKey($skillId)) {
            continue
        }

        $rankedConfidence = if ($ranked.PSObject.Properties.Name -contains 'score' -and $ranked.score -ne $null) { [double]$ranked.score } else { 0.0 }
        $candidateSelectionReason = if ($ranked.PSObject.Properties.Name -contains 'candidate_selection_reason') { [string]$ranked.candidate_selection_reason } else { '' }
        $candidateSelectionScore = if ($ranked.PSObject.Properties.Name -contains 'candidate_selection_score' -and $ranked.candidate_selection_score -ne $null) {
            [double]$ranked.candidate_selection_score
        } else {
            $rankedConfidence
        }
        $hasCustomAdmissionMetadata = (
            $ranked.PSObject.Properties.Name -contains 'custom_admission' -and
            $null -ne $ranked.custom_admission
        )
        if (
            -not $hasCustomAdmissionMetadata -and
            $candidateSelectionReason -match 'fallback' -and
            ($rankedConfidence -lt $minimumRecommendationConfidence -or $candidateSelectionScore -lt $minimumRecommendationConfidence)
        ) {
            continue
        }

        $rankedMetadata = [pscustomobject]@{
            skill_md_path = if ($ranked.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$ranked.native_skill_entrypoint } else { '' }
            native_skill_entrypoint = if ($ranked.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$ranked.native_skill_entrypoint } else { '' }
            skill_root = if ($ranked.PSObject.Properties.Name -contains 'skill_root') { [string]$ranked.skill_root } else { '' }
            description = if ($ranked.PSObject.Properties.Name -contains 'description') { [string]$ranked.description } else { '' }
            source_root = if ($ranked.PSObject.Properties.Name -contains 'source_root') { [string]$ranked.source_root } else { '' }
            source_kind = if ($ranked.PSObject.Properties.Name -contains 'source_kind') { [string]$ranked.source_kind } else { '' }
        }
        $customMetadata = if ($customAdmissionIndex.ContainsKey($skillId)) { $customAdmissionIndex[$skillId] } else { $rankedMetadata }
        $reason = "top ranked local installed specialist candidate via {0}" -f $candidateSelectionReason
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -SkillId $skillId `
            -Source 'route_ranked' `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId ([string]$ranked.pack_id) `
            -Confidence $rankedConfidence `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation `
            -PromotionPolicy $PromotionPolicy `
            -CustomMetadata $customMetadata `
            -TargetRoot $TargetRoot `
            -HostId $HostId)
        $seen[$skillId] = $true

        if (-not $isXlRoute -or -not ($ranked.PSObject.Properties.Name -contains 'candidate_ranking')) {
            continue
        }

        $selectedCandidateScore = if ($ranked.PSObject.Properties.Name -contains 'candidate_selection_score') { [double]$ranked.candidate_selection_score } else { 0.0 }
        foreach ($sibling in @($ranked.candidate_ranking)) {
            if (@($recommendations).Count -ge $limit) {
                break
            }
            $siblingSkillId = if ($sibling.PSObject.Properties.Name -contains 'skill') { [string]$sibling.skill } else { '' }
            if ([string]::IsNullOrWhiteSpace($siblingSkillId)) {
                continue
            }
            if ([string]::Equals($siblingSkillId, $skillId, [System.StringComparison]::OrdinalIgnoreCase) -or [string]::Equals($siblingSkillId, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
            if ($seen.ContainsKey($siblingSkillId)) {
                continue
            }
            $siblingScore = if ($sibling.PSObject.Properties.Name -contains 'score') { [double]$sibling.score } else { 0.0 }
            if ($siblingScore -lt 0.2) {
                continue
            }
            if ($selectedCandidateScore -gt 0.0 -and (($selectedCandidateScore - $siblingScore) -gt 0.1)) {
                continue
            }

            $siblingMetadata = [pscustomobject]@{
                skill_md_path = if ($sibling.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$sibling.native_skill_entrypoint } else { '' }
                native_skill_entrypoint = if ($sibling.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$sibling.native_skill_entrypoint } else { '' }
                skill_root = if ($sibling.PSObject.Properties.Name -contains 'skill_root') { [string]$sibling.skill_root } else { '' }
                description = if ($sibling.PSObject.Properties.Name -contains 'description') { [string]$sibling.description } else { '' }
                source_root = if ($sibling.PSObject.Properties.Name -contains 'source_root') { [string]$sibling.source_root } else { '' }
                source_kind = if ($sibling.PSObject.Properties.Name -contains 'source_kind') { [string]$sibling.source_kind } else { '' }
            }
            $customMetadata = if ($customAdmissionIndex.ContainsKey($siblingSkillId)) { $customAdmissionIndex[$siblingSkillId] } else { $siblingMetadata }
            $reason = "additional XL ranked local installed specialist candidate"
            $recommendations += (New-VibeSpecialistRecommendation `
                -RepoRoot $RepoRoot `
                -Task $Task `
                -SkillId $siblingSkillId `
                -Source 'route_ranked_sibling' `
                -TaskType $TaskType `
                -Reason $reason `
                -PackId ([string]$ranked.pack_id) `
                -Confidence $siblingScore `
                -Rank (@($recommendations).Count + 1) `
                -DispatchContract $dispatchContractForRecommendation `
                -PromotionPolicy $PromotionPolicy `
                -CustomMetadata $customMetadata `
                -TargetRoot $TargetRoot `
                -HostId $HostId)
            $seen[$siblingSkillId] = $true
        }
    }

    foreach ($overlayField in @(Get-VibeRouteAdviceFieldNames -RouteResult $RouteResult)) {
        if (@($recommendations).Count -ge $limit) {
            break
        }
        if (-not ($RouteResult.PSObject.Properties.Name -contains $overlayField)) {
            continue
        }
        $advice = $RouteResult.$overlayField
        if ($null -eq $advice) {
            continue
        }
        if (-not ($advice.PSObject.Properties.Name -contains 'recommended_skill')) {
            continue
        }
        $skillId = [string]$advice.recommended_skill
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        if ([string]::Equals($skillId, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        if ($seen.ContainsKey($skillId)) {
            continue
        }

        $customMetadata = if ($customAdmissionIndex.ContainsKey($skillId)) { $customAdmissionIndex[$skillId] } else { $null }
        $reason = "overlay recommendation from '{0}'" -f $overlayField
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -SkillId $skillId `
            -Source ("overlay:{0}" -f $overlayField) `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId $null `
            -Confidence 0.0 `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation `
            -PromotionPolicy $PromotionPolicy `
            -CustomMetadata $customMetadata `
            -TargetRoot $TargetRoot `
            -HostId $HostId)
        $seen[$skillId] = $true
    }

    if (-not [string]::IsNullOrWhiteSpace($RouterSelectedSkill) -and
        -not [string]::Equals($RouterSelectedSkill, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $seen.ContainsKey($RouterSelectedSkill) -and
        @($recommendations).Count -lt $limit) {
        $routeSelectedMetadata = if ($RouteResult.PSObject.Properties.Name -contains 'selected' -and $null -ne $RouteResult.selected) {
            [pscustomobject]@{
                skill_md_path = if ($RouteResult.selected.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$RouteResult.selected.native_skill_entrypoint } else { '' }
                native_skill_entrypoint = if ($RouteResult.selected.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$RouteResult.selected.native_skill_entrypoint } else { '' }
                skill_root = if ($RouteResult.selected.PSObject.Properties.Name -contains 'skill_root') { [string]$RouteResult.selected.skill_root } else { '' }
                description = if ($RouteResult.selected.PSObject.Properties.Name -contains 'description') { [string]$RouteResult.selected.description } else { '' }
                source_root = if ($RouteResult.selected.PSObject.Properties.Name -contains 'source_root') { [string]$RouteResult.selected.source_root } else { '' }
                source_kind = if ($RouteResult.selected.PSObject.Properties.Name -contains 'source_kind') { [string]$RouteResult.selected.source_kind } else { '' }
            }
        } else {
            $null
        }
        $customMetadata = if ($customAdmissionIndex.ContainsKey($RouterSelectedSkill)) { $customAdmissionIndex[$RouterSelectedSkill] } else { $routeSelectedMetadata }
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -SkillId $RouterSelectedSkill `
            -Source 'route_selected' `
            -TaskType $TaskType `
            -Reason 'local installed skill recommender selected a bounded specialist candidate for governed execution' `
            -PackId $null `
            -Confidence 0.0 `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation `
            -PromotionPolicy $PromotionPolicy `
            -CustomMetadata $customMetadata `
            -TargetRoot $TargetRoot `
            -HostId $HostId)
        $seen[$RouterSelectedSkill] = $true
    }

    return @($recommendations)
}

function Split-VibeSpecialistDispatch {
    param(
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [AllowEmptyCollection()] [object[]]$Recommendations = @(),
        [string[]]$MatchedSkillIds = @(),
        [string[]]$ApprovedSpecialistSkillIds = @(),
        [AllowNull()] [object]$HostSpecialistDispatchDecision = $null,
        [AllowNull()] [object]$SuggestionContract = $null,
        [AllowEmptyString()] [string]$RepoRoot = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $approvedLookup = @{}
    foreach ($skillId in @($ApprovedSpecialistSkillIds)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
            $approvedLookup[[string]$skillId] = $true
        }
    }
    $hostApprovedLookup = @{}
    $hostDeferredLookup = @{}
    $hostRejectedLookup = @{}
    $hostSelectionMode = if (
        $null -ne $HostSpecialistDispatchDecision -and
        $HostSpecialistDispatchDecision.PSObject.Properties.Name -contains 'selection_mode' -and
        -not [string]::IsNullOrWhiteSpace([string]$HostSpecialistDispatchDecision.selection_mode)
    ) {
        [string]$HostSpecialistDispatchDecision.selection_mode
    } else {
        ''
    }
    if ($null -ne $HostSpecialistDispatchDecision) {
        $approvedSkillIds = if ($HostSpecialistDispatchDecision.PSObject.Properties.Name -contains 'approved_skill_ids') {
            @($HostSpecialistDispatchDecision.approved_skill_ids)
        } else {
            @()
        }
        foreach ($skillId in $approvedSkillIds) {
            if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
                $hostApprovedLookup[[string]$skillId] = $true
            }
        }
        $deferredSkillIds = if ($HostSpecialistDispatchDecision.PSObject.Properties.Name -contains 'deferred_skill_ids') {
            @($HostSpecialistDispatchDecision.deferred_skill_ids)
        } else {
            @()
        }
        foreach ($skillId in $deferredSkillIds) {
            if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
                $hostDeferredLookup[[string]$skillId] = $true
            }
        }
        $rejectedSkillIds = if ($HostSpecialistDispatchDecision.PSObject.Properties.Name -contains 'rejected_skill_ids') {
            @($HostSpecialistDispatchDecision.rejected_skill_ids)
        } else {
            @()
        }
        foreach ($skillId in $rejectedSkillIds) {
            if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
                $hostRejectedLookup[[string]$skillId] = $true
            }
        }
    }

    $approvedDispatch = @()
    $localSuggestions = @()
    $blockedDispatch = @()
    $degradedDispatch = @()
    $promotionOutcomes = @()
    $enforceLocalAuthority = -not [string]::IsNullOrWhiteSpace([string]$RepoRoot)
    foreach ($recommendation in @($Recommendations)) {
        $skillId = [string]$recommendation.skill_id
        $nativeSkillEntrypoint = if (
            $recommendation.PSObject.Properties.Name -contains 'native_skill_entrypoint' -and
            -not [string]::IsNullOrWhiteSpace([string]$recommendation.native_skill_entrypoint)
        ) {
            [string]$recommendation.native_skill_entrypoint
        } elseif (
            $recommendation.PSObject.Properties.Name -contains 'skill_md_path' -and
            -not [string]::IsNullOrWhiteSpace([string]$recommendation.skill_md_path)
        ) {
            [string]$recommendation.skill_md_path
        } else {
            ''
        }
        if ($enforceLocalAuthority) {
            $authority = Resolve-VibeLocalSkillAuthority `
                -RepoRoot $RepoRoot `
                -SkillId $skillId `
                -NativeSkillEntrypoint $nativeSkillEntrypoint `
                -TargetRoot $TargetRoot `
                -HostId $HostId `
                -RequireProvidedEntrypoint
            if (-not [bool]$authority.valid) {
                $record = Copy-VibeRecordObject -InputObject $recommendation
                $record | Add-Member -NotePropertyName degrade_reason -NotePropertyValue ([string]$authority.reason) -Force
                $record | Add-Member -NotePropertyName canonical_native_skill_entrypoint -NotePropertyValue $authority.canonical_entrypoint -Force
                $degradedDispatch += $record
                $promotionOutcomes += [pscustomobject]@{
                    skill_id = $skillId
                    promotion_state = 'degraded'
                    degrade_reason = [string]$authority.reason
                    destructive = [bool]$recommendation.destructive
                    destructive_reason_codes = @($recommendation.destructive_reason_codes)
                    contract_complete = [bool]$recommendation.contract_complete
                    recommended_promotion_action = [string]$recommendation.recommended_promotion_action
                }
                continue
            }
            $nativeSkillEntrypoint = [string]$authority.canonical_entrypoint
        }
        $nativeEntrypointFileName = if ([string]::IsNullOrWhiteSpace($nativeSkillEntrypoint)) { '' } else { [System.IO.Path]::GetFileName($nativeSkillEntrypoint) }
        if (
            [string]::IsNullOrWhiteSpace($nativeSkillEntrypoint) -or
            $nativeEntrypointFileName -notin @('SKILL.md', 'SKILL.runtime-mirror.md') -or
            -not (Test-Path -LiteralPath $nativeSkillEntrypoint -PathType Leaf)
        ) {
            $record = Copy-VibeRecordObject -InputObject $recommendation
            $record | Add-Member -NotePropertyName degrade_reason -NotePropertyValue 'missing_native_entrypoint' -Force
            $degradedDispatch += $record
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'degraded'
                degrade_reason = 'missing_native_entrypoint'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
            continue
        }
        if ([bool]$recommendation.destructive -or [string]$recommendation.recommended_promotion_action -eq 'require_confirmation') {
            $blockedDispatch += $recommendation
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'blocked'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
            continue
        }
        if ([string]$recommendation.recommended_promotion_action -eq 'degrade_missing_contract') {
            $degradedDispatch += $recommendation
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'degraded'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
            continue
        }

        $hostSelectionAction = ''
        if ($hostApprovedLookup.ContainsKey($skillId)) {
            $hostSelectionAction = 'approve'
        } elseif ($hostDeferredLookup.ContainsKey($skillId)) {
            $hostSelectionAction = 'defer'
        } elseif ($hostRejectedLookup.ContainsKey($skillId)) {
            $hostSelectionAction = 'reject'
        } elseif ([string]$hostSelectionMode -eq 'curated_only') {
            $hostSelectionAction = 'curated_only_unspecified'
        }

        $record = Copy-VibeRecordObject -InputObject $recommendation
        if ($enforceLocalAuthority) {
            $record | Add-Member -NotePropertyName native_skill_entrypoint -NotePropertyValue $nativeSkillEntrypoint -Force
            $record | Add-Member -NotePropertyName skill_md_path -NotePropertyValue $nativeSkillEntrypoint -Force
        }
        if (-not [string]::IsNullOrWhiteSpace($hostSelectionAction)) {
            $record | Add-Member -NotePropertyName host_selection_applied -NotePropertyValue $true -Force
            $record | Add-Member -NotePropertyName host_selection_mode -NotePropertyValue $hostSelectionMode -Force
            $record | Add-Member -NotePropertyName host_selection_action -NotePropertyValue $hostSelectionAction -Force
        }

        if (
            [string]$hostSelectionAction -eq 'approve' -and
            [string]$recommendation.recommended_promotion_action -eq 'auto_dispatch'
        ) {
            $approvedDispatch += $record
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'approved_dispatch'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
        } elseif (
            [string]$hostSelectionAction -in @('defer', 'reject', 'curated_only_unspecified')
        ) {
            $localSuggestions += $record
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'local_suggestion'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
        } elseif ([string]$recommendation.recommended_promotion_action -eq 'auto_dispatch' -and
            ($GovernanceScope -eq 'root' -or $approvedLookup.ContainsKey($skillId))) {
            $approvedDispatch += $record
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'approved_dispatch'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
        } else {
            $localSuggestions += $record
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'local_suggestion'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
        }
    }

    $escalationRequired = $null -eq $HostSpecialistDispatchDecision -and @($localSuggestions).Count -gt 0 -and (
        $null -eq $SuggestionContract -or
        -not ($SuggestionContract.PSObject.Properties.Name -contains 'escalation_required') -or
        [bool]$SuggestionContract.escalation_required
    )

    $matchedSkillIdsClean = [object[]]@($MatchedSkillIds | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
    $surfacedSkillIds = [object[]]@($Recommendations | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $resolvedSkillIds = @(
        @($approvedDispatch | ForEach-Object { [string]$_.skill_id }) +
        @($blockedDispatch | ForEach-Object { [string]$_.skill_id }) +
        @($degradedDispatch | ForEach-Object { [string]$_.skill_id }) +
        @($localSuggestions | ForEach-Object { [string]$_.skill_id })
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
    $ghostMatchSkillIds = [object[]]@($matchedSkillIdsClean | Where-Object { $_ -notin $resolvedSkillIds })

    return [pscustomobject]@{
        approved_dispatch = [object[]]@($approvedDispatch)
        local_specialist_suggestions = [object[]]@($localSuggestions)
        blocked = [object[]]@($blockedDispatch)
        degraded = [object[]]@($degradedDispatch)
        matched_skill_ids = [object[]]@($matchedSkillIdsClean)
        surfaced_skill_ids = [object[]]@($surfacedSkillIds)
        blocked_skill_ids = [object[]]@($blockedDispatch | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        degraded_skill_ids = [object[]]@($degradedDispatch | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        ghost_match_skill_ids = [object[]]@($ghostMatchSkillIds)
        promotion_outcomes = [object[]]@($promotionOutcomes)
        escalation_required = [bool]$escalationRequired
        escalation_status = if ($escalationRequired) { 'root_approval_required' } else { 'not_required' }
    }
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $ArtifactRoot
$policy = $runtime.runtime_input_packet_policy
$hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $HostDecisionJson
$continuationContext = Get-VibeHostContinuationContext -HostDecision $hostDecision
$executionPhaseDecomposition = Resolve-VibeHostPhaseDecomposition -HostDecision $hostDecision -Task $Task -Policy $policy
$effectiveRequestedStageStop = Resolve-VibeEntryRequestedStageStop `
    -RepoRoot $runtime.repo_root `
    -EntryIntentId $EntryIntentId `
    -RequestedStageStop $RequestedStageStop
$grade = Get-VibeInternalGrade -Task $Task -RequestedGradeFloor $RequestedGradeFloor
$taskType = Get-VibeRouterTaskType -Task $Task
$resolvedEntryIntentId = Resolve-VibeControllerEntryIntentId `
    -EntryIntentId $EntryIntentId `
    -RuntimeSelectedSkill ([string]$policy.explicit_runtime_skill)
if (
    (Test-VibeStructuredBoundedReentryContext -ContinuationContext $continuationContext) -and
    (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'control_only_prompt') -and
    [bool]$continuationContext.control_only_prompt -and
    (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'prior_task_type') -and
    -not [string]::IsNullOrWhiteSpace([string]$continuationContext.prior_task_type)
) {
    $taskType = [string]$continuationContext.prior_task_type
}
$routerScriptPath = Join-Path $runtime.repo_root 'scripts/router/resolve-pack-route.ps1'
$routerHostId = Resolve-VgoHostId -HostId $env:VCO_HOST_ID
$routerTargetRoot = Resolve-VgoTargetRoot -HostId $routerHostId
$storageProjection = New-VibeWorkspaceArtifactProjection `
    -RepoRoot $runtime.repo_root `
    -Runtime $runtime `
    -ArtifactRoot $ArtifactRoot `
    -RouterTargetRoot $routerTargetRoot
$controllerEntryIntentIds = @(
    [string]$policy.explicit_runtime_skill
) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
$requestedSkill = if (
    -not [string]::IsNullOrWhiteSpace($resolvedEntryIntentId) -and
    [string]$resolvedEntryIntentId -notin @($controllerEntryIntentIds)
) {
    [string]$resolvedEntryIntentId
} else {
    ''
}
$unattended = $false
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $GovernanceScope `
    -RunId $RunId `
    -RootRunId $RootRunId `
    -ParentRunId $ParentRunId `
    -ParentUnitId $ParentUnitId `
    -InheritedRequirementDocPath $InheritedRequirementDocPath `
    -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
    -DelegationEnvelopePath $DelegationEnvelopePath `
    -HierarchyContract $policy.hierarchy_contract

$routeArgs = @(
    '-Prompt', $Task,
    '-Grade', $grade,
    '-TaskType', $taskType,
    '-HostId', $routerHostId,
    '-TargetRoot', $routerTargetRoot
)
if (-not [string]::IsNullOrWhiteSpace([string]$requestedSkill)) {
    $routeArgs += @('-RequestedSkill', [string]$requestedSkill)
}
if ($unattended) {
    $routeArgs += '-Unattended'
}

$routeResult = Invoke-VibeFrozenRoute -RouterScriptPath $routerScriptPath -BaseArgs $routeArgs -HostDecisionJson $HostDecisionJson

if (
    [string]::IsNullOrWhiteSpace([string]$HostDecisionJson) -and
    (Test-VibeSingleOptionCanonicalConfirmSurface -RouteResult $routeResult -EntryIntentId $EntryIntentId -RuntimeSelectedSkill ([string]$policy.explicit_runtime_skill))
) {
    $preferredPayload = $routeResult.confirm_ui.route_decision_contract.preferred_payload
    $syntheticHostDecisionJson = $preferredPayload | ConvertTo-Json -Depth 20 -Compress
    $hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $syntheticHostDecisionJson
    $continuationContext = Get-VibeHostContinuationContext -HostDecision $hostDecision
    if (
        (Test-VibeStructuredBoundedReentryContext -ContinuationContext $continuationContext) -and
        (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'control_only_prompt') -and
        [bool]$continuationContext.control_only_prompt -and
        (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'prior_task_type') -and
        -not [string]::IsNullOrWhiteSpace([string]$continuationContext.prior_task_type)
    ) {
        $taskType = [string]$continuationContext.prior_task_type
        for ($routeArgIndex = 0; $routeArgIndex -lt (@($routeArgs).Count - 1); $routeArgIndex++) {
            if ([string]::Equals([string]$routeArgs[$routeArgIndex], '-TaskType', [System.StringComparison]::OrdinalIgnoreCase)) {
                $routeArgs[$routeArgIndex + 1] = $taskType
                break
            }
        }
    }
    $routeResult = Invoke-VibeFrozenRoute -RouterScriptPath $routerScriptPath -BaseArgs $routeArgs -HostDecisionJson $syntheticHostDecisionJson
    $executionPhaseDecomposition = Resolve-VibeHostPhaseDecomposition -HostDecision $hostDecision -Task $Task -Policy $policy
}

$confirmRequired = ([string]$routeResult.route_mode -eq 'confirm_required')
$runtimeSelectedSkill = [string]$policy.explicit_runtime_skill
$routerSelectedSkill = if ($routeResult.selected) { [string]$routeResult.selected.skill } else { $null }
$specialistRecommendations = @(Get-VibeSpecialistRecommendations `
    -RepoRoot $runtime.repo_root `
    -Task $Task `
    -RouteResult $routeResult `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -RouterSelectedSkill $routerSelectedSkill `
    -TaskType $taskType `
    -Policy $policy `
    -PromotionPolicy $runtime.skill_promotion_policy `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId)
$stageAssistantHints = @(Get-VibeStageAssistantHints `
    -RepoRoot $runtime.repo_root `
    -Task $Task `
    -RouteResult $routeResult `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -TaskType $taskType `
    -Policy $policy `
    -PromotionPolicy $runtime.skill_promotion_policy `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId)
$specialistRecommendations = @(Add-VibeExecutionPhaseMetadataToRecords `
    -Records @($specialistRecommendations) `
    -PhaseDecomposition $executionPhaseDecomposition)
$stageAssistantHints = @(Add-VibeExecutionPhaseMetadataToRecords `
    -Records @($stageAssistantHints) `
    -PhaseDecomposition $executionPhaseDecomposition)
$skillUsageTouched = New-Object System.Collections.Generic.List[object]
if (-not [string]::IsNullOrWhiteSpace([string]$routerSelectedSkill)) {
    $skillUsageTouched.Add([pscustomobject]@{
        skill_id = [string]$routerSelectedSkill
        reason = 'loaded_but_no_artifact_impact'
    }) | Out-Null
}
foreach ($recommendation in @($specialistRecommendations)) {
    $candidateSkillId = if ($recommendation.PSObject.Properties.Name -contains 'skill_id') { [string]$recommendation.skill_id } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($candidateSkillId)) {
        $skillUsageTouched.Add([pscustomobject]@{
            skill_id = $candidateSkillId
            reason = 'recommendation_only'
        }) | Out-Null
    }
}
foreach ($hint in @($stageAssistantHints)) {
    $hintSkillId = if ($hint.PSObject.Properties.Name -contains 'skill_id') { [string]$hint.skill_id } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($hintSkillId)) {
        $skillUsageTouched.Add([pscustomobject]@{
            skill_id = $hintSkillId
            reason = 'route_hint_only'
        }) | Out-Null
    }
}

$hostSpecialistDispatchDecision = Resolve-VibeHostSkillExecutionDecision `
    -HostDecision $hostDecision `
    -Recommendations @($specialistRecommendations) `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -Policy $policy
$lockSourceRunId = if (
    $null -ne $continuationContext -and
    (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'source_run_id') -and
    -not [string]::IsNullOrWhiteSpace([string]$continuationContext.source_run_id)
) {
    [string]$continuationContext.source_run_id
} else {
    ''
}
$previousRuntimeInputPacket = Get-VibeRuntimeInputPacketFromSessionRunId `
    -ArtifactRoot $ArtifactRoot `
    -SourceRunId $lockSourceRunId
$codeTaskTddDecision = Resolve-VibeCodeTaskTddDecision `
    -HostDecision $hostDecision `
    -Task $Task `
    -TaskType $taskType `
    -HeuristicRequiresTdd ($taskType -in @('coding', 'debug')) `
    -DocumentArtifactBaseline $false
$matchedSkillIds = @()
if (-not [string]::IsNullOrWhiteSpace($routerSelectedSkill) -and -not [string]::Equals($routerSelectedSkill, $runtimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
    $matchedSkillIds += [string]$routerSelectedSkill
}
$specialistDispatch = Split-VibeSpecialistDispatch `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -Recommendations @($specialistRecommendations) `
    -MatchedSkillIds @($matchedSkillIds) `
    -ApprovedSpecialistSkillIds @($ApprovedSpecialistSkillIds) `
    -HostSpecialistDispatchDecision $hostSpecialistDispatchDecision `
    -SuggestionContract $policy.child_specialist_suggestion_contract `
    -RepoRoot $runtime.repo_root `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId
$skillRouting = New-VibeSkillRoutingFromLegacy `
    -RouterSelectedSkill ([string]$routerSelectedSkill) `
    -Recommendations @($specialistRecommendations) `
    -StageAssistantHints @($stageAssistantHints) `
    -SpecialistDispatch $specialistDispatch
$lockSource = if (-not [string]::IsNullOrWhiteSpace($lockSourceRunId)) {
    'approved_plan_reentry'
} else {
    'current_skill_routing_selected'
}
$skillExecutionLock = New-VibeSkillExecutionLockProjection `
    -PreviousRuntimeInputPacket $previousRuntimeInputPacket `
    -CurrentSkillRouting $skillRouting `
    -HostSpecialistDispatchDecision $hostSpecialistDispatchDecision `
    -SourceRunId $lockSourceRunId `
    -Source $lockSource `
    -RepoRoot $runtime.repo_root `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId
$selectedSkillLoads = @()
foreach ($selectedSkill in @(Get-VibeSkillRoutingSelected -SkillRouting $skillRouting)) {
    $selectedSkillId = [string]$selectedSkill.skill_id
    if ([string]::IsNullOrWhiteSpace($selectedSkillId)) {
        continue
    }
    $selectedSkillLoads += New-VibeSkillUsageLoadedSkill `
        -RepoRoot $runtime.repo_root `
        -SkillId $selectedSkillId `
        -LoadedAtStage 'skeleton_check' `
        -TargetRoot $routerTargetRoot `
        -HostId $routerHostId
}
$routingTouchedSkills = @(
    @($skillRouting.selected | ForEach-Object { [pscustomobject]@{ skill_id = [string]$_.skill_id; reason = 'selected_but_no_artifact_impact' } }) +
    @($skillRouting.candidates | ForEach-Object { [pscustomobject]@{ skill_id = [string]$_.skill_id; reason = 'not_selected' } })
)
$skillUsage = New-VibeInitialSkillUsage `
    -LoadedSkills @($selectedSkillLoads) `
    -TouchedSkills @($routingTouchedSkills + @($skillUsageTouched.ToArray()))
$hierarchyProjection = New-VibeHierarchyProjection -HierarchyState $hierarchyState -IncludeGovernanceScope
$authorityFlagsProjection = New-VibeRuntimePacketAuthorityFlagsProjection `
    -HierarchyState $hierarchyState `
    -RuntimeEntry 'vibe' `
    -ExplicitRuntimeSkill $runtimeSelectedSkill `
    -RouterTruthLevel ([string]$routeResult.truth_level) `
    -ShadowOnly ([bool]$policy.shadow_only) `
    -NonAuthoritative ([bool]$routeResult.non_authoritative)
$packet = New-VibeRuntimeInputPacketProjection `
    -RunId $RunId `
    -Task $Task `
    -Mode $Mode `
    -InternalGrade $grade `
    -HierarchyState $hierarchyState `
    -HierarchyProjection $hierarchyProjection `
    -AuthorityFlagsProjection $authorityFlagsProjection `
    -StorageProjection $storageProjection `
    -RouteResult $routeResult `
    -Runtime $runtime `
    -TaskType $taskType `
    -RequestedSkill $requestedSkill `
    -EntryIntentId $EntryIntentId `
    -RequestedStageStop $effectiveRequestedStageStop `
    -RequestedGradeFloor $RequestedGradeFloor `
    -RouterHostId $routerHostId `
    -RouterTargetRoot $routerTargetRoot `
    -Unattended ([bool]$unattended) `
    -RouterScriptPath $routerScriptPath `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -ExecutionPhaseDecomposition $executionPhaseDecomposition `
    -HostSpecialistDispatchDecision $hostSpecialistDispatchDecision `
    -CodeTaskTddDecision $codeTaskTddDecision `
    -HostDecision $hostDecision `
    -SpecialistRecommendations @($specialistRecommendations) `
    -StageAssistantHints @($stageAssistantHints) `
    -SkillUsage $skillUsage `
    -SkillRouting $skillRouting `
    -SkillExecutionLock $skillExecutionLock `
    -SpecialistDispatch $specialistDispatch `
    -Policy $policy

$packetPath = Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
Write-VibeJsonArtifact -Path $packetPath -Value $packet

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    packet_path = $packetPath
    packet = $packet
    route_result = $routeResult
}
