param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [AllowEmptyString()] [string]$WorkspaceRoot = '',
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

function Resolve-VibeControllerEntryIntentId {
    param(
        [AllowEmptyString()] [string]$EntryIntentId = ''
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
        [AllowNull()] [object]$ExecutionSafetyPolicy = $null,
        [AllowNull()] [object]$CustomMetadata = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $metadata = Get-VibeSkillMetadata -RepoRoot $RepoRoot -SkillId $SkillId -TargetRoot $TargetRoot -HostId $HostId
    $bindingProfile = Get-VibeSpecialistBindingProfile -SkillId $SkillId -Policy $DispatchContract.policy -DispatchContract $DispatchContract
    $customSkillEntrypoint = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_entrypoint' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_entrypoint)) {
        [string]$CustomMetadata.skill_entrypoint
    } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_md_path' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_md_path)) {
        [string]$CustomMetadata.skill_md_path
    } else {
        $null
    }
    $skillEntrypoint = if ($metadata.skill_path) {
        [string]$metadata.skill_path
    } elseif (-not [string]::IsNullOrWhiteSpace([string]$customSkillEntrypoint)) {
        [string]$customSkillEntrypoint
    } else {
        $null
    }
    $skillDescription = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'description' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.description)) {
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
    } elseif (-not [string]::IsNullOrWhiteSpace([string]$skillEntrypoint)) {
        [string](Split-Path -Parent $skillEntrypoint)
    } else {
        $null
    }
    $progressiveLoadPolicy = if (-not [string]::IsNullOrWhiteSpace([string]$skillEntrypoint)) {
        @(
            "Read the assigned $skillEntrypoint before starting the module."
        )
    } else {
        @()
    }
    $safetyMetadata = Get-VgoSkillExecutionSafetyMetadata `
        -Prompt $Task `
        -SkillMdPath $skillEntrypoint `
        -SkillRoot $skillRoot `
        -Description $skillDescription `
        -RequiredInputs @($DispatchContract.required_inputs) `
        -ExpectedOutputs @($DispatchContract.expected_outputs) `
        -VerificationExpectation ([string]$DispatchContract.verification_expectation) `
        -MustPreserveWorkflow ([bool]$DispatchContract.must_preserve_workflow) `
        -ExecutionSafetyPolicy $ExecutionSafetyPolicy
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
        skill_entrypoint = $skillEntrypoint
        skill_md_path = $skillEntrypoint
        skill_root = $skillRoot
        source_root = if ($metadata.PSObject.Properties.Name -contains 'source_root' -and -not [string]::IsNullOrWhiteSpace([string]$metadata.source_root)) { [string]$metadata.source_root } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'source_root') { [string]$CustomMetadata.source_root } else { $null }
        source_kind = if ($metadata.PSObject.Properties.Name -contains 'source_kind' -and -not [string]::IsNullOrWhiteSpace([string]$metadata.source_kind)) { [string]$metadata.source_kind } elseif ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'source_kind') { [string]$CustomMetadata.source_kind } else { $null }
        source_priority = if ($metadata.PSObject.Properties.Name -contains 'source_priority' -and $null -ne $metadata.source_priority) { [int]$metadata.source_priority } else { $null }
        duplicate_state = if ($metadata.PSObject.Properties.Name -contains 'duplicate_state') { [string]$metadata.duplicate_state } else { $null }
        local_skill_authority = if ($metadata.PSObject.Properties.Name -contains 'authority_valid') { [bool]$metadata.authority_valid } else { $false }
        local_skill_authority_reason = if ($metadata.PSObject.Properties.Name -contains 'authority_reason') { [string]$metadata.authority_reason } else { 'not_in_local_skill_index' }
        skill_description = $skillDescription
        visibility_class = if (-not [string]::IsNullOrWhiteSpace([string]$skillEntrypoint) -and -not [string]::IsNullOrWhiteSpace([string]$skillRoot)) { 'path_resolved' } else { 'path_unresolved' }
        invocation_reason = $Reason
        expected_contribution = [string]$DispatchContract.bounded_role
        progressive_load_policy = @($progressiveLoadPolicy)
        destructive = [bool]$safetyMetadata.destructive
        destructive_reason_codes = [object[]]@($safetyMetadata.destructive_reason_codes)
        rollback_possible = [bool]$safetyMetadata.rollback_possible
        snapshot_required = [bool]$safetyMetadata.snapshot_required
        contract_required = [bool]$safetyMetadata.contract_required
        contract_complete = [bool]$safetyMetadata.contract_complete
        contract_missing_fields = [object[]]@($safetyMetadata.contract_missing_fields)
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
        [AllowNull()] [object]$ExecutionSafetyPolicy = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $limit = 4
    if ($Policy.PSObject.Properties.Name -contains 'specialist_recommendation_limit' -and $Policy.specialist_recommendation_limit -ne $null) {
        $limit = [int]$Policy.specialist_recommendation_limit
    }
    $dispatchContract = if ($Policy.PSObject.Properties.Name -contains 'module_skill_contract' -and $null -ne $Policy.module_skill_contract) {
        $Policy.module_skill_contract
    } else {
        [pscustomobject]@{
            bounded_role = 'specialist_assist'
            must_preserve_workflow = $true
            dispatch_phase = 'in_execution'
            execution_priority = 50
            lane_policy = 'inherit_grade'
            parallelizable_in_root_xl = $true
            write_scope_template = 'specialist:{skill_id}'
            review_mode = 'module_acceptance'
            required_inputs = @(
                'bounded specialist subtask contract',
                'frozen requirement context',
                'relevant source files or domain artifacts'
            )
            expected_outputs = @(
                'bounded specialist findings or code changes',
                'verification notes aligned with the specialist skill'
            )
            verification_expectation = 'Follow the assigned SKILL.md boundaries and satisfy module acceptance.'
        }
    }
    $dispatchContractForHint = [pscustomobject]@{
        bounded_role = [string]$dispatchContract.bounded_role
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

function Get-VibeModuleSkillContract {
    param(
        [Parameter(Mandatory)] [object]$Policy
    )

    if ($Policy.PSObject.Properties.Name -contains 'module_skill_contract' -and $null -ne $Policy.module_skill_contract) {
        return $Policy.module_skill_contract
    }

    return [pscustomobject]@{
        bounded_role = 'specialist_assist'
        must_preserve_workflow = $true
        dispatch_phase = 'in_execution'
        execution_priority = 50
        lane_policy = 'inherit_grade'
        parallelizable_in_root_xl = $true
        write_scope_template = 'specialist:{skill_id}'
        review_mode = 'module_acceptance'
        required_inputs = @('bounded specialist subtask contract')
        expected_outputs = @('bounded specialist result')
        verification_expectation = 'Follow the assigned SKILL.md and satisfy module acceptance.'
    }
}

function New-VibeRecommendationsFromAgentSkillOrganization {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowNull()] [object]$AgentSkillOrganization = $null,
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [object]$Policy,
        [AllowNull()] [object]$ExecutionSafetyPolicy = $null,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    if ($null -eq $AgentSkillOrganization) {
        return @()
    }

    $dispatchContract = Get-VibeModuleSkillContract -Policy $Policy
    $dispatchContractForRecommendation = [pscustomobject]@{}
    foreach ($property in @($dispatchContract.PSObject.Properties)) {
        $dispatchContractForRecommendation | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value
    }
    $dispatchContractForRecommendation | Add-Member -NotePropertyName policy -NotePropertyValue $Policy -Force

    $recommendations = New-Object System.Collections.Generic.List[object]
    foreach ($selectedSkill in @($AgentSkillOrganization.selected_skills)) {
        $skillId = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        if ([string]::Equals($skillId, [string]$Policy.explicit_runtime_skill, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw ('agent_skill_organization cannot select the governed runtime controller `{0}` as a task skill' -f $skillId)
        }
        $metadata = Get-VibeSkillMetadata -RepoRoot $RepoRoot -SkillId $skillId -TargetRoot $TargetRoot -HostId $HostId
        if (-not [bool]$metadata.authority_valid) {
            throw ('agent_skill_organization selected skill `{0}` is not available from the declared local skill roots: {1}' -f $skillId, [string]$metadata.authority_reason)
        }
        $responsibility = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'responsibility' -DefaultValue '')
        $reason = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'reason' -DefaultValue '')
        $recommendation = New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -SkillId $skillId `
            -Source 'agent_skill_organization' `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId $null `
            -Confidence 1.0 `
            -Rank ($recommendations.Count + 1) `
            -DispatchContract $dispatchContractForRecommendation `
            -ExecutionSafetyPolicy $ExecutionSafetyPolicy `
            -CustomMetadata $selectedSkill `
            -TargetRoot $TargetRoot `
            -HostId $HostId
        $recommendation | Add-Member -NotePropertyName task_slice -NotePropertyValue $responsibility -Force
        $recommendation | Add-Member -NotePropertyName organization_module_ids -NotePropertyValue @($selectedSkill.module_ids) -Force
        $recommendation | Add-Member -NotePropertyName organization_responsibility -NotePropertyValue $responsibility -Force
        $recommendations.Add($recommendation) | Out-Null
    }

    return [object[]]$recommendations.ToArray()
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$requestedArtifactRoot = $ArtifactRoot
$WorkspaceRoot = Get-VibeWorkspaceRoot -RepoRoot $runtime.repo_root -WorkspaceRoot $WorkspaceRoot
$runtime | Add-Member -NotePropertyName workspace_root -NotePropertyValue $WorkspaceRoot -Force
$artifactBaseRoot = Get-VibeArtifactRoot `
    -RepoRoot $runtime.repo_root `
    -Runtime $runtime `
    -WorkspaceRoot $WorkspaceRoot `
    -ArtifactRoot $requestedArtifactRoot
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

if ([string]::IsNullOrWhiteSpace($requestedArtifactRoot)) {
    Initialize-VibeWorkspaceProjectDescriptor -RepoRoot $runtime.repo_root -WorkspaceRoot $WorkspaceRoot -Runtime $runtime | Out-Null
}
$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -WorkspaceRoot $WorkspaceRoot -ArtifactRoot $artifactBaseRoot
$policy = $runtime.runtime_input_packet_policy
$hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $HostDecisionJson
$continuationContext = Get-VibeHostContinuationContext -HostDecision $hostDecision
$executionPhaseDecomposition = Resolve-VibeHostPhaseDecomposition -HostDecision $hostDecision -Task $Task -Policy $policy
$effectiveRequestedStageStop = Resolve-VibeEntryRequestedStageStop `
    -RepoRoot $runtime.repo_root `
    -EntryIntentId $EntryIntentId `
    -RequestedStageStop $RequestedStageStop
$grade = Get-VibeInternalGrade -Task $Task -RequestedGradeFloor $RequestedGradeFloor
$organizationSourceRunId = if (
    $null -ne $continuationContext -and
    (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'source_run_id') -and
    -not [string]::IsNullOrWhiteSpace([string]$continuationContext.source_run_id)
) {
    [string]$continuationContext.source_run_id
} else {
    ''
}
$previousRuntimeInputPacket = Get-VibeRuntimeInputPacketFromSessionRunId `
    -ArtifactRoot $artifactBaseRoot `
    -SourceRunId $organizationSourceRunId
$inheritedAgentSkillOrganization = if (
    $null -ne $previousRuntimeInputPacket -and
    (Test-VibeObjectHasProperty -InputObject $previousRuntimeInputPacket -PropertyName 'agent_skill_organization') -and
    $null -ne $previousRuntimeInputPacket.agent_skill_organization
) {
    $previousRuntimeInputPacket.agent_skill_organization
} else {
    $null
}
$agentSkillOrganization = Resolve-VibeAgentSkillOrganization `
    -HostDecision $hostDecision `
    -InheritedOrganization $inheritedAgentSkillOrganization
if ($null -ne $agentSkillOrganization) {
    $grade = [string]$agentSkillOrganization.workflow_level
}
if ($effectiveRequestedStageStop -in @('xl_plan', 'plan_execute', 'phase_cleanup') -and $null -eq $agentSkillOrganization) {
    throw ('agent_skill_organization is required before {0}' -f $effectiveRequestedStageStop)
}
$taskType = Get-VibeRouterTaskType -Task $Task
$resolvedEntryIntentId = Resolve-VibeControllerEntryIntentId -EntryIntentId $EntryIntentId
if (
    (Test-VibeStructuredBoundedReentryContext -ContinuationContext $continuationContext) -and
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
    -WorkspaceRoot $WorkspaceRoot `
    -Runtime $runtime `
    -ArtifactRoot $requestedArtifactRoot `
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
$runtimeSelectedSkill = [string]$policy.explicit_runtime_skill
$routeCandidateFocusSkill = if ($routeResult.candidate_focus) { [string]$routeResult.candidate_focus.skill } else { $null }
$skillSearchGuide = New-VibeSkillSearchGuideProjection `
    -RepoRoot $runtime.repo_root `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId
$agentRecommendations = @(New-VibeRecommendationsFromAgentSkillOrganization `
    -RepoRoot $runtime.repo_root `
    -Task $Task `
    -AgentSkillOrganization $agentSkillOrganization `
    -TaskType $taskType `
    -Policy $policy `
    -ExecutionSafetyPolicy $runtime.skill_execution_safety_policy `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId)
$agentRecommendations = @(Add-VibeExecutionPhaseMetadataToRecords `
    -Records @($agentRecommendations) `
    -PhaseDecomposition $executionPhaseDecomposition)
$stageAssistantHints = @(Get-VibeStageAssistantHints `
    -RepoRoot $runtime.repo_root `
    -Task $Task `
    -RouteResult $routeResult `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -TaskType $taskType `
    -Policy $policy `
    -ExecutionSafetyPolicy $runtime.skill_execution_safety_policy `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId)
$stageAssistantHints = @(Add-VibeExecutionPhaseMetadataToRecords `
    -Records @($stageAssistantHints) `
    -PhaseDecomposition $executionPhaseDecomposition)
$codeTaskTddDecision = Resolve-VibeCodeTaskTddDecision `
    -HostDecision $hostDecision `
    -Task $Task `
    -TaskType $taskType `
    -HeuristicRequiresTdd ($taskType -in @('coding', 'debug')) `
    -DocumentArtifactBaseline $false
$selectedSkillIds = if ($null -eq $agentSkillOrganization) {
    @()
} else {
    @($agentSkillOrganization.selected_skills | ForEach-Object { [string]$_.skill_id })
}
$skillRouting = New-VibeSkillCandidateAudit `
    -CandidateFocusSkill ([string]$routeCandidateFocusSkill) `
    -Recommendations @($agentRecommendations) `
    -StageAssistantHints @($stageAssistantHints) `
    -SelectedSkillIds @($selectedSkillIds)
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
    -CodeTaskTddDecision $codeTaskTddDecision `
    -HostDecision $hostDecision `
    -StageAssistantHints @($stageAssistantHints) `
    -SkillSearchGuide $skillSearchGuide `
    -AgentSkillOrganization $agentSkillOrganization `
    -AgentSkillRecommendations @($agentRecommendations) `
    -SkillRouting $skillRouting `
    -Policy $policy

$packetPath = Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $artifactBaseRoot
Write-VibeJsonArtifact -Path $packetPath -Value $packet

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    packet_path = $packetPath
    packet = $packet
    route_result = $routeResult
}
