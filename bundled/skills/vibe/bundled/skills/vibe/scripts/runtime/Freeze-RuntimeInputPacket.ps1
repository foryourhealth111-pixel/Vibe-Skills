param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
    [string[]]$ApprovedSpecialistSkillIds = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')

function Get-VibeRouterTaskType {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $taskLower = $Task.ToLowerInvariant()
    if ($taskLower -match 'review|审查|评审') {
        return 'review'
    }
    if ($taskLower -match 'debug|bug|错误|修复') {
        return 'debug'
    }
    if ($taskLower -match 'research|调研|研究') {
        return 'research'
    }
    if ($taskLower -match 'implement|build|upgrade|更新|增强|执行') {
        return 'coding'
    }
    return 'planning'
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

function Get-VibeSkillMetadata {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId
    )

    $skillPath = Join-Path $RepoRoot ("bundled\skills\{0}\SKILL.md" -f $SkillId)
    if (-not (Test-Path -LiteralPath $skillPath)) {
        return [pscustomobject]@{
            skill_id = $SkillId
            skill_path = $null
            description = $null
        }
    }

    $description = $null
    foreach ($line in @(Get-Content -LiteralPath $skillPath -Encoding UTF8 -TotalCount 20)) {
        if ([string]$line -match '^\s*description:\s*(.+?)\s*$') {
            $description = $Matches[1].Trim()
            break
        }
    }

    return [pscustomobject]@{
        skill_id = $SkillId
        skill_path = $skillPath
        description = $description
    }
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

    $profiles = if ($Policy.PSObject.Properties.Name -contains 'specialist_binding_profiles') {
        $Policy.specialist_binding_profiles
    } else {
        $null
    }

    $selectedProfileName = 'default'
    $selectedProfile = if ($profiles -and $profiles.PSObject.Properties.Name -contains 'default') {
        $profiles.default
    } else {
        $null
    }

    if ($profiles) {
        foreach ($profileName in @('planning', 'implementation', 'deliverable', 'verification')) {
            if (-not ($profiles.PSObject.Properties.Name -contains $profileName)) {
                continue
            }
            $profile = $profiles.$profileName
            foreach ($pattern in @($profile.match_skill_patterns)) {
                $regex = [string]$pattern
                if (-not [string]::IsNullOrWhiteSpace($regex) -and $SkillId -match $regex) {
                    $selectedProfileName = $profileName
                    $selectedProfile = $profile
                    break
                }
            }
            if ($selectedProfileName -ne 'default') {
                break
            }
        }
    }

    if ($null -eq $selectedProfile) {
        $selectedProfile = [pscustomobject]@{}
    }

    return [pscustomobject]@{
        binding_profile = $selectedProfileName
        dispatch_phase = if ($selectedProfile.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$selectedProfile.dispatch_phase } else { [string]$DispatchContract.dispatch_phase }
        execution_priority = if ($selectedProfile.PSObject.Properties.Name -contains 'execution_priority') { [int]$selectedProfile.execution_priority } else { [int]$DispatchContract.execution_priority }
        lane_policy = if ($selectedProfile.PSObject.Properties.Name -contains 'lane_policy') { [string]$selectedProfile.lane_policy } else { [string]$DispatchContract.lane_policy }
        parallelizable_in_root_xl = if ($selectedProfile.PSObject.Properties.Name -contains 'parallelizable_in_root_xl') { [bool]$selectedProfile.parallelizable_in_root_xl } else { [bool]$DispatchContract.parallelizable_in_root_xl }
        write_scope = Resolve-VibeSpecialistWriteScopeTemplate `
            -Template $(if ($selectedProfile.PSObject.Properties.Name -contains 'write_scope_template') { [string]$selectedProfile.write_scope_template } else { [string]$DispatchContract.write_scope_template }) `
            -SkillId $SkillId
        review_mode = if ($selectedProfile.PSObject.Properties.Name -contains 'review_mode') { [string]$selectedProfile.review_mode } else { [string]$DispatchContract.review_mode }
    }
}

function New-VibeSpecialistRecommendation {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$Source,
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [string]$Reason,
        [AllowNull()] [object]$PackId,
        [AllowNull()] [object]$Confidence,
        [AllowNull()] [object]$Rank,
        [Parameter(Mandatory)] [object]$DispatchContract
    )

    $metadata = Get-VibeSkillMetadata -RepoRoot $RepoRoot -SkillId $SkillId
    $bindingProfile = Get-VibeSpecialistBindingProfile -SkillId $SkillId -Policy $DispatchContract.policy -DispatchContract $DispatchContract
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
        binding_profile = [string]$bindingProfile.binding_profile
        dispatch_phase = [string]$bindingProfile.dispatch_phase
        execution_priority = [int]$bindingProfile.execution_priority
        lane_policy = [string]$bindingProfile.lane_policy
        parallelizable_in_root_xl = [bool]$bindingProfile.parallelizable_in_root_xl
        write_scope = [string]$bindingProfile.write_scope
        review_mode = [string]$bindingProfile.review_mode
        native_skill_entrypoint = if ($metadata.skill_path) { [string]$metadata.skill_path } else { $null }
        native_skill_description = if ($metadata.description) { [string]$metadata.description } else { $null }
    }
}

function Get-VibeSpecialistRecommendations {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [object]$RouteResult,
        [Parameter(Mandatory)] [string]$RuntimeSelectedSkill,
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [object]$Policy
    )

    $limit = 4
    if ($Policy.PSObject.Properties.Name -contains 'specialist_recommendation_limit' -and $Policy.specialist_recommendation_limit -ne $null) {
        $limit = [int]$Policy.specialist_recommendation_limit
    }
    $dispatchContract = if ($Policy.PSObject.Properties.Name -contains 'specialist_dispatch_contract' -and $null -ne $Policy.specialist_dispatch_contract) {
        $Policy.specialist_dispatch_contract
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

        $reason = "top ranked specialist candidate from pack '{0}' via {1}" -f ([string]$ranked.pack_id), ([string]$ranked.candidate_selection_reason)
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -SkillId $skillId `
            -Source 'route_ranked' `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId ([string]$ranked.pack_id) `
            -Confidence ([double]$ranked.score) `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation)
        $seen[$skillId] = $true
    }

    foreach ($overlayField in @($Policy.overlay_fields)) {
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

        $reason = "overlay recommendation from '{0}'" -f $overlayField
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -SkillId $skillId `
            -Source ("overlay:{0}" -f $overlayField) `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId $null `
            -Confidence 0.0 `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation)
        $seen[$skillId] = $true
    }

    return @($recommendations)
}

function Split-VibeSpecialistDispatch {
    param(
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [object[]]$Recommendations,
        [string[]]$ApprovedSpecialistSkillIds = @(),
        [AllowNull()] [object]$SuggestionContract = $null
    )

    $approvedLookup = @{}
    foreach ($skillId in @($ApprovedSpecialistSkillIds)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
            $approvedLookup[[string]$skillId] = $true
        }
    }

    if ($GovernanceScope -eq 'root') {
        return [pscustomobject]@{
            approved_dispatch = @($Recommendations)
            local_specialist_suggestions = @()
            escalation_required = $false
            escalation_status = 'not_required'
        }
    }

    $approvedDispatch = @()
    $localSuggestions = @()
    foreach ($recommendation in @($Recommendations)) {
        $skillId = [string]$recommendation.skill_id
        if ($approvedLookup.ContainsKey($skillId)) {
            $approvedDispatch += $recommendation
        } else {
            $localSuggestions += $recommendation
        }
    }

    $escalationRequired = @($localSuggestions).Count -gt 0 -and (
        $null -eq $SuggestionContract -or
        -not ($SuggestionContract.PSObject.Properties.Name -contains 'escalation_required') -or
        [bool]$SuggestionContract.escalation_required
    )

    return [pscustomobject]@{
        approved_dispatch = @($approvedDispatch)
        local_specialist_suggestions = @($localSuggestions)
        escalation_required = [bool]$escalationRequired
        escalation_status = if ($escalationRequired) { 'root_approval_required' } else { 'not_required' }
    }
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$policy = $runtime.runtime_input_packet_policy
$grade = Get-VibeInternalGrade -Task $Task
$taskType = Get-VibeRouterTaskType -Task $Task
$routerScriptPath = Join-Path $runtime.repo_root ([string]$policy.router_script_path)
$requestedSkill = if ($policy.default_requested_skill) { [string]$policy.default_requested_skill } else { 'vibe' }
$unattended = $false
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $GovernanceScope `
    -RunId $RunId `
    -RootRunId $RootRunId `
    -ParentRunId $ParentRunId `
    -ParentUnitId $ParentUnitId `
    -InheritedRequirementDocPath $InheritedRequirementDocPath `
    -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
    -HierarchyContract $policy.hierarchy_contract

$routeArgs = @(
    '-Prompt', $Task,
    '-Grade', $grade,
    '-TaskType', $taskType,
    '-RequestedSkill', $requestedSkill
)
if ($unattended) {
    $routeArgs += '-Unattended'
}

$routeInvocation = Invoke-VgoPowerShellFile -ScriptPath $routerScriptPath -ArgumentList $routeArgs -NoProfile

if ([int]$routeInvocation.exit_code -ne 0) {
    throw ("Failed to freeze runtime input packet because canonical router exited with code {0}." -f [int]$routeInvocation.exit_code)
}

$routeJson = (@($routeInvocation.output) -join [Environment]::NewLine).Trim()
$routeResult = $routeJson | ConvertFrom-Json

$overlayDecisions = @()
foreach ($overlayField in @($policy.overlay_fields)) {
    if (-not ($routeResult.PSObject.Properties.Name -contains $overlayField)) {
        continue
    }
    $snapshot = New-VibeAdviceSnapshot -Name $overlayField -Advice $routeResult.$overlayField
    if ($null -ne $snapshot) {
        $overlayDecisions += $snapshot
    }
}

$confirmRequired = ([string]$routeResult.route_mode -eq 'confirm_required')
$runtimeSelectedSkill = [string]$policy.explicit_runtime_skill
$routerSelectedSkill = if ($routeResult.selected) { [string]$routeResult.selected.skill } else { $null }
$specialistRecommendations = @(Get-VibeSpecialistRecommendations -RepoRoot $runtime.repo_root -RouteResult $routeResult -RuntimeSelectedSkill $runtimeSelectedSkill -TaskType $taskType -Policy $policy)
$specialistDispatch = Split-VibeSpecialistDispatch `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -Recommendations @($specialistRecommendations) `
    -ApprovedSpecialistSkillIds @($ApprovedSpecialistSkillIds) `
    -SuggestionContract $policy.child_specialist_suggestion_contract
$packet = [pscustomobject]@{
    stage = 'runtime_input_freeze'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    task = $Task
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    runtime_mode = $Mode
    internal_grade = $grade
    hierarchy = [pscustomobject]@{
        governance_scope = [string]$hierarchyState.governance_scope
        root_run_id = [string]$hierarchyState.root_run_id
        parent_run_id = if ($null -eq $hierarchyState.parent_run_id) { $null } else { [string]$hierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $hierarchyState.parent_unit_id) { $null } else { [string]$hierarchyState.parent_unit_id }
        inherited_requirement_doc_path = if ($null -eq $hierarchyState.inherited_requirement_doc_path) { $null } else { [string]$hierarchyState.inherited_requirement_doc_path }
        inherited_execution_plan_path = if ($null -eq $hierarchyState.inherited_execution_plan_path) { $null } else { [string]$hierarchyState.inherited_execution_plan_path }
    }
    canonical_router = [pscustomobject]@{
        prompt = $Task
        task_type = $taskType
        requested_skill = $requestedSkill
        unattended = [bool]$unattended
        route_script_path = $routerScriptPath
    }
    route_snapshot = [pscustomobject]@{
        selected_pack = if ($routeResult.selected) { [string]$routeResult.selected.pack_id } else { $null }
        selected_skill = $routerSelectedSkill
        route_mode = [string]$routeResult.route_mode
        route_reason = [string]$routeResult.route_reason
        confirm_required = [bool]$confirmRequired
        confidence = if ($routeResult.confidence -ne $null) { [double]$routeResult.confidence } else { $null }
        truth_level = [string]$routeResult.truth_level
        degradation_state = [string]$routeResult.degradation_state
        non_authoritative = [bool]$routeResult.non_authoritative
        fallback_active = [bool]$routeResult.fallback_active
        hazard_alert_required = [bool]$routeResult.hazard_alert_required
        unattended_override_applied = [bool]$routeResult.unattended_override_applied
    }
    specialist_recommendations = @($specialistRecommendations)
    specialist_dispatch = [pscustomobject]@{
        approved_dispatch = @($specialistDispatch.approved_dispatch)
        local_specialist_suggestions = @($specialistDispatch.local_specialist_suggestions)
        approved_skill_ids = @($specialistDispatch.approved_dispatch | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        local_suggestion_skill_ids = @($specialistDispatch.local_specialist_suggestions | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        escalation_required = [bool]$specialistDispatch.escalation_required
        escalation_status = [string]$specialistDispatch.escalation_status
        approval_owner = if ($policy.child_specialist_suggestion_contract.PSObject.Properties.Name -contains 'approval_owner') { [string]$policy.child_specialist_suggestion_contract.approval_owner } else { 'root_vibe' }
        status = if ($policy.child_specialist_suggestion_contract.PSObject.Properties.Name -contains 'status') { [string]$policy.child_specialist_suggestion_contract.status } else { 'advisory_until_root_approval' }
    }
    overlay_decisions = @($overlayDecisions)
    authority_flags = [pscustomobject]@{
        runtime_entry = 'vibe'
        explicit_runtime_skill = $runtimeSelectedSkill
        router_truth_level = [string]$routeResult.truth_level
        shadow_only = [bool]$policy.shadow_only
        non_authoritative = [bool]$routeResult.non_authoritative
        allow_requirement_freeze = [bool]$hierarchyState.allow_requirement_freeze
        allow_plan_freeze = [bool]$hierarchyState.allow_plan_freeze
        allow_global_dispatch = [bool]$hierarchyState.allow_global_dispatch
        allow_completion_claim = [bool]$hierarchyState.allow_completion_claim
    }
    divergence_shadow = [pscustomobject]@{
        router_selected_skill = $routerSelectedSkill
        runtime_selected_skill = $runtimeSelectedSkill
        skill_mismatch = [bool](-not [string]::Equals($routerSelectedSkill, $runtimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase))
        confirm_required = [bool]$confirmRequired
        explicit_runtime_override_applied = [bool](-not [string]::IsNullOrWhiteSpace($runtimeSelectedSkill))
        explicit_runtime_override_reason = 'governed_runtime_entry'
        governance_scope_mismatch = $false
    }
    provenance = [pscustomobject]@{
        source_of_truth = 'canonical_router_shadow_freeze'
        freeze_before_requirement_doc = [bool]$policy.freeze_before_requirement_doc
        proof_class = 'structure'
    }
}

$packetPath = Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
Write-VibeJsonArtifact -Path $packetPath -Value $packet

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    packet_path = $packetPath
    packet = $packet
}
