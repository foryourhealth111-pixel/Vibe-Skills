param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$EntryIntentId = '',
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
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
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $skillPath = $null
    $bundledSkillRoot = Join-Path $RepoRoot ("bundled\skills\{0}" -f $SkillId)
    foreach ($candidate in @(
            (Join-Path $bundledSkillRoot 'SKILL.md'),
            (Join-Path $bundledSkillRoot 'SKILL.runtime-mirror.md')
        )) {
        if (Test-Path -LiteralPath $candidate) {
            $skillPath = $candidate
            break
        }
    }

    if (-not $skillPath) {
        $installedSkillsRoot = Resolve-VgoInstalledSkillsRoot -TargetRoot $TargetRoot -HostId $HostId
        $candidateRoots = @(
            (Join-Path $installedSkillsRoot $SkillId),
            (Join-Path (Join-Path $installedSkillsRoot 'custom') $SkillId)
        )

        foreach ($candidateRoot in $candidateRoots) {
            foreach ($candidate in @(
                    (Join-Path $candidateRoot 'SKILL.md'),
                    (Join-Path $candidateRoot 'SKILL.runtime-mirror.md')
                )) {
                if (Test-Path -LiteralPath $candidate) {
                    $skillPath = $candidate
                    break
                }
            }
            if ($skillPath) {
                break
            }
        }
    }

    if (-not $skillPath) {
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

function Resolve-VibeSpecialistSkillRoot {
    param(
        [AllowEmptyString()] [string]$NativeSkillEntrypoint = ''
    )

    if ([string]::IsNullOrWhiteSpace($NativeSkillEntrypoint)) {
        return $null
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath([string]$NativeSkillEntrypoint)
    } catch {
        return $null
    }

    return Split-Path -Parent $fullPath
}

function Resolve-VibeSpecialistVisibilityClass {
    param(
        [AllowEmptyString()] [string]$NativeSkillEntrypoint = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    if ([string]::IsNullOrWhiteSpace($NativeSkillEntrypoint)) {
        return 'missing_entrypoint'
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath([string]$NativeSkillEntrypoint)
    } catch {
        return 'missing_entrypoint'
    }

    $installedSkillsRoot = Resolve-VgoInstalledSkillsRoot -TargetRoot $TargetRoot -HostId $HostId
    if (-not [string]::IsNullOrWhiteSpace([string]$installedSkillsRoot)) {
        try {
            if (Test-VibePathWithinRoot -RootPath ([string]$installedSkillsRoot) -CandidatePath $fullPath) {
                return 'installed_surface_path_resolved'
            }
        } catch {
        }
    }

    return 'path_resolved'
}

function Get-VibeSpecialistExpectedContribution {
    param(
        [Parameter(Mandatory)] [string]$TaskType,
        [Parameter(Mandatory)] [string]$SkillId
    )

    switch ([string]$TaskType) {
        'debug' { return ("Use {0} to produce bounded root-cause analysis and verification notes." -f $SkillId) }
        'review' { return ("Use {0} to produce bounded review findings and verification notes." -f $SkillId) }
        'research' { return ("Use {0} to produce bounded research findings and source-aware notes." -f $SkillId) }
        'coding' { return ("Use {0} to produce bounded implementation help and verification notes." -f $SkillId) }
        default { return ("Use {0} to produce bounded planning or specialist guidance within the governed task." -f $SkillId) }
    }
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
    $nativeSkillEntrypoint = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_md_path' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_md_path)) {
        [string]$CustomMetadata.skill_md_path
    } elseif ($metadata.skill_path) {
        [string]$metadata.skill_path
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
    $skillRoot = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'skill_root' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.skill_root)) {
        [string]$CustomMetadata.skill_root
    } else {
        Resolve-VibeSpecialistSkillRoot -NativeSkillEntrypoint $nativeSkillEntrypoint
    }
    $visibilityClass = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'visibility_class' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.visibility_class)) {
        [string]$CustomMetadata.visibility_class
    } else {
        Resolve-VibeSpecialistVisibilityClass -NativeSkillEntrypoint $nativeSkillEntrypoint -TargetRoot $TargetRoot -HostId $HostId
    }
    $usageRequiredCandidate = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'usage_required' -and $null -ne $CustomMetadata.usage_required) {
        [bool]$CustomMetadata.usage_required
    } else {
        [bool]$DispatchContract.native_usage_required
    }
    $usageRequired = [bool]($usageRequiredCandidate -or [bool]$DispatchContract.native_usage_required)
    $progressiveLoadPolicy = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'progressive_load_policy' -and $null -ne $CustomMetadata.progressive_load_policy) {
        [object[]]@($CustomMetadata.progressive_load_policy)
    } else {
        [object[]]@(
            ('Open the specialist {0} entrypoint first.' -f [string]$nativeSkillEntrypoint),
            'Load references/ only when they are needed for the bounded task.',
            'Load scripts/ only when executable specialist support is required.',
            'Load assets/ only when the specialist workflow explicitly needs them.'
        )
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
        usage_required = [bool]$usageRequired
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
        visibility_class = $visibilityClass
        native_skill_description = $nativeSkillDescription
        invocation_reason = [string]$Reason
        expected_contribution = if ($null -ne $CustomMetadata -and $CustomMetadata.PSObject.Properties.Name -contains 'expected_contribution' -and -not [string]::IsNullOrWhiteSpace([string]$CustomMetadata.expected_contribution)) { [string]$CustomMetadata.expected_contribution } else { Get-VibeSpecialistExpectedContribution -TaskType $TaskType -SkillId $SkillId }
        progressive_load_policy = [object[]]@($progressiveLoadPolicy)
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

function Get-VibeSpecialistRecommendations {
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
    $customAdmissionIndex = Get-VibeCustomAdmissionIndex -RouteResult $RouteResult

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

        $customMetadata = if ($customAdmissionIndex.ContainsKey($skillId)) { $customAdmissionIndex[$skillId] } else { $null }
        $reason = "top ranked specialist candidate from pack '{0}' via {1}" -f ([string]$ranked.pack_id), ([string]$ranked.candidate_selection_reason)
        $recommendations += (New-VibeSpecialistRecommendation `
            -RepoRoot $RepoRoot `
            -Task $Task `
            -SkillId $skillId `
            -Source 'route_ranked' `
            -TaskType $TaskType `
            -Reason $reason `
            -PackId ([string]$ranked.pack_id) `
            -Confidence ([double]$ranked.score) `
            -Rank (@($recommendations).Count + 1) `
            -DispatchContract $dispatchContractForRecommendation `
            -PromotionPolicy $PromotionPolicy `
            -CustomMetadata $customMetadata `
            -TargetRoot $TargetRoot `
            -HostId $HostId)
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

    return @($recommendations)
}

function Split-VibeSpecialistDispatch {
    param(
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [object[]]$Recommendations,
        [string[]]$MatchedSkillIds = @(),
        [string[]]$ApprovedSpecialistSkillIds = @(),
        [AllowNull()] [object]$SuggestionContract = $null
    )

    $approvedLookup = @{}
    foreach ($skillId in @($ApprovedSpecialistSkillIds)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$skillId)) {
            $approvedLookup[[string]$skillId] = $true
        }
    }

    $approvedDispatch = @()
    $localSuggestions = @()
    $blockedDispatch = @()
    $degradedDispatch = @()
    $promotionOutcomes = @()
    foreach ($recommendation in @($Recommendations)) {
        $skillId = [string]$recommendation.skill_id
        $nativeUsageRequired = if ($recommendation.PSObject.Properties.Name -contains 'native_usage_required') { [bool]$recommendation.native_usage_required } else { $false }
        $usageRequired = if ($recommendation.PSObject.Properties.Name -contains 'usage_required') { [bool]$recommendation.usage_required } else { $nativeUsageRequired }
        if ($nativeUsageRequired -and -not $usageRequired) {
            if ($recommendation.PSObject.Properties.Name -contains 'usage_required') {
                $recommendation.usage_required = $true
            } else {
                $recommendation | Add-Member -NotePropertyName 'usage_required' -NotePropertyValue $true
            }
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

        if ([string]$recommendation.recommended_promotion_action -eq 'auto_dispatch' -and
            ($GovernanceScope -eq 'root' -or $approvedLookup.ContainsKey($skillId))) {
            $approvedDispatch += $recommendation
            $promotionOutcomes += [pscustomobject]@{
                skill_id = $skillId
                promotion_state = 'approved_dispatch'
                destructive = [bool]$recommendation.destructive
                destructive_reason_codes = @($recommendation.destructive_reason_codes)
                contract_complete = [bool]$recommendation.contract_complete
                recommended_promotion_action = [string]$recommendation.recommended_promotion_action
            }
        } else {
            $localSuggestions += $recommendation
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

    $escalationRequired = @($localSuggestions).Count -gt 0 -and (
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
$entryIntent = Resolve-VibeEntryIntentSelection `
    -Runtime $runtime `
    -EntryIntentId $EntryIntentId `
    -RequestedStageStop $RequestedStageStop `
    -RequestedGradeFloor $RequestedGradeFloor
$gradeResolution = Resolve-VibeGovernedGrade `
    -BaseGrade (Get-VibeInternalGrade -Task $Task) `
    -RequestedGradeFloor ([string]$entryIntent.requested_grade_floor) `
    -Policy $policy
$grade = [string]$gradeResolution.internal_grade
$taskType = Get-VibeRouterTaskType -Task $Task
$routerScriptPath = Join-Path $runtime.repo_root ([string]$policy.router_script_path)
$routerHostId = Resolve-VgoHostId -HostId $env:VCO_HOST_ID
$routerTargetRoot = Resolve-VgoTargetRoot -HostId $routerHostId
$storageProjection = New-VibeWorkspaceArtifactProjection `
    -RepoRoot $runtime.repo_root `
    -Runtime $runtime `
    -ArtifactRoot $ArtifactRoot `
    -RouterTargetRoot $routerTargetRoot
$requestedSkill = if ($entryIntent.canonical_runtime_skill) { [string]$entryIntent.canonical_runtime_skill } elseif ($policy.default_requested_skill) { [string]$policy.default_requested_skill } else { 'vibe' }
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
    '-RequestedSkill', $requestedSkill,
    '-HostId', $routerHostId,
    '-TargetRoot', $routerTargetRoot
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
$specialistRecommendations = @(Get-VibeSpecialistRecommendations `
    -RepoRoot $runtime.repo_root `
    -Task $Task `
    -RouteResult $routeResult `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -TaskType $taskType `
    -Policy $policy `
    -PromotionPolicy $runtime.skill_promotion_policy `
    -TargetRoot $routerTargetRoot `
    -HostId $routerHostId)
$matchedSkillIds = @()
if (-not [string]::IsNullOrWhiteSpace($routerSelectedSkill) -and -not [string]::Equals($routerSelectedSkill, $runtimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
    $matchedSkillIds += [string]$routerSelectedSkill
}
$specialistDispatch = Split-VibeSpecialistDispatch `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -Recommendations @($specialistRecommendations) `
    -MatchedSkillIds @($matchedSkillIds) `
    -ApprovedSpecialistSkillIds @($ApprovedSpecialistSkillIds) `
    -SuggestionContract $policy.child_specialist_suggestion_contract
$hierarchyProjection = New-VibeHierarchyProjection -HierarchyState $hierarchyState -IncludeGovernanceScope
$authorityFlagsProjection = New-VibeRuntimePacketAuthorityFlagsProjection `
    -HierarchyState $hierarchyState `
    -RuntimeEntry ([string]$entryIntent.entry_intent_id) `
    -ExplicitRuntimeSkill $runtimeSelectedSkill `
    -RouterTruthLevel ([string]$routeResult.truth_level) `
    -ShadowOnly ([bool]$policy.shadow_only) `
    -NonAuthoritative ([bool]$routeResult.non_authoritative)
$packet = New-VibeRuntimeInputPacketProjection `
    -RunId $RunId `
    -Task $Task `
    -Mode $Mode `
    -InternalGrade $grade `
    -EntryIntentId ([string]$entryIntent.entry_intent_id) `
    -RequestedStageStop ([string]$entryIntent.requested_stage_stop) `
    -RequestedGradeFloor ([string]$gradeResolution.requested_grade_floor) `
    -HierarchyState $hierarchyState `
    -HierarchyProjection $hierarchyProjection `
    -AuthorityFlagsProjection $authorityFlagsProjection `
    -StorageProjection $storageProjection `
    -RouteResult $routeResult `
    -Runtime $runtime `
    -TaskType $taskType `
    -RequestedSkill $requestedSkill `
    -RouterHostId $routerHostId `
    -RouterTargetRoot $routerTargetRoot `
    -Unattended ([bool]$unattended) `
    -RouterScriptPath $routerScriptPath `
    -RuntimeSelectedSkill $runtimeSelectedSkill `
    -SpecialistRecommendations @($specialistRecommendations) `
    -SpecialistDispatch $specialistDispatch `
    -OverlayDecisions @($overlayDecisions) `
    -Policy $policy

$packetPath = Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
Write-VibeJsonArtifact -Path $packetPath -Value $packet

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    packet_path = $packetPath
    packet = $packet
}
