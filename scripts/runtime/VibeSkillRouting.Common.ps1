Set-StrictMode -Version Latest

function Get-VibeSkillRoutingProperty {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName,
        [AllowNull()] [object]$DefaultValue = $null
    )

    if ($null -ne $InputObject -and $InputObject.PSObject.Properties.Name -contains $PropertyName) {
        return $InputObject.$PropertyName
    }
    return $DefaultValue
}

function New-VibeSkillRoutingEntry {
    param(
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowNull()] [object]$Source = $null,
        [AllowEmptyString()] [string]$Reason = '',
        [AllowEmptyString()] [string]$State = 'candidate'
    )

    $sourceReason = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'reason' -DefaultValue '')
    $nativeEntrypoint = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'native_skill_entrypoint' -DefaultValue '')
    $skillMdPath = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'skill_md_path' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillMdPath)) {
        $skillMdPath = $nativeEntrypoint
    }
    $skillRoot = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'skill_root' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillRoot) -and -not [string]::IsNullOrWhiteSpace($skillMdPath)) {
        $skillRoot = Split-Path -Parent $skillMdPath
    }
    $dispatchPhase = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
    if ([string]::IsNullOrWhiteSpace($dispatchPhase)) {
        $dispatchPhase = 'in_execution'
    }
    $taskSlice = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'task_slice' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($taskSlice)) {
        $taskSlice = if ([string]::IsNullOrWhiteSpace($sourceReason)) { ('Use {0} for its selected specialist workflow.' -f $SkillId) } else { $sourceReason }
    }

    return [pscustomobject]@{
        skill_id = $SkillId
        skill_md_path = if ([string]::IsNullOrWhiteSpace($skillMdPath)) { $null } else { $skillMdPath }
        reason = if ([string]::IsNullOrWhiteSpace($Reason)) { $sourceReason } else { $Reason }
        task_slice = $taskSlice
        state = $State
        dispatch_phase = $dispatchPhase
        parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
        native_usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'native_usage_required' -DefaultValue $true)
        native_skill_entrypoint = if ([string]::IsNullOrWhiteSpace($nativeEntrypoint)) { $null } else { $nativeEntrypoint }
        skill_root = if ([string]::IsNullOrWhiteSpace($skillRoot)) { $null } else { $skillRoot }
        bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
        must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'must_preserve_workflow' -DefaultValue $true)
        binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
        lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'lane_policy' -DefaultValue 'native_contract')
        write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $SkillId))
        review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'review_mode' -DefaultValue 'native_contract')
        execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'execution_priority' -DefaultValue 50)
        required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'required_inputs' -DefaultValue @())
        expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'expected_outputs' -DefaultValue @())
        verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'verification_expectation' -DefaultValue 'Record selected skill usage evidence before completion.')
        progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'progressive_load_policy' -DefaultValue @())
        legacy_source = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'source' -DefaultValue '')
    }
}

function Add-VibeSkillRoutingEntry {
    param(
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[object]]$Rows,
        [Parameter(Mandatory)] [hashtable]$Seen,
        [Parameter(Mandatory)] [object]$Entry
    )

    $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $Entry -PropertyName 'skill_id' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillId) -or $Seen.ContainsKey($skillId)) {
        return
    }
    $Rows.Add($Entry) | Out-Null
    $Seen[$skillId] = $true
}

function Get-VibeWorkflowLevelFromRouteResult {
    param(
        [AllowNull()] [object]$RouteResult = $null
    )

    $grade = [string](Get-VibeSkillRoutingProperty -InputObject $RouteResult -PropertyName 'grade' -DefaultValue '')
    if ([string]::Equals($grade, 'XL', [System.StringComparison]::OrdinalIgnoreCase)) {
        return 'XL'
    }
    return 'L'
}

function Get-VibeWorkflowLevelSelectionLimit {
    param(
        [Parameter(Mandatory)] [ValidateSet('L', 'XL')] [string]$WorkflowLevel
    )

    if ($WorkflowLevel -eq 'XL') {
        return 5
    }
    return 3
}

function New-VibeSkillSelectionCandidateRecord {
    param(
        [Parameter(Mandatory)] [object]$Candidate
    )

    $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_id' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillId)) {
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill' -DefaultValue '')
    }
    if ([string]::IsNullOrWhiteSpace($skillId)) {
        return $null
    }

    return [pscustomobject]@{
        skill_id = $skillId
        score = [double](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'score' -DefaultValue 0.0)
        matched_tokens = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_tokens' -DefaultValue @())
        matched_capabilities = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_capabilities' -DefaultValue @())
        description = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'description' -DefaultValue '')
        native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'native_skill_entrypoint' -DefaultValue $null
        skill_md_path = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'native_skill_entrypoint' -DefaultValue $null
        skill_root = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_root' -DefaultValue $null
        source_root = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'source_root' -DefaultValue $null
        source_kind = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'source_kind' -DefaultValue $null
        reason = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'candidate_selection_reason' -DefaultValue '')
    }
}

function New-VibeSkillSelectionRecord {
    param(
        [Parameter(Mandatory)] [object]$Candidate,
        [Parameter(Mandatory)] [ValidateSet('candidate', 'selected', 'rejected')] [string]$SelectionState,
        [AllowEmptyString()] [string]$SelectionReason = '',
        [AllowNull()] [int]$SelectionRank = $null
    )

    return [pscustomobject]@{
        skill_id = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_id' -DefaultValue '')
        score = [double](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'score' -DefaultValue 0.0)
        matched_tokens = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_tokens' -DefaultValue @())
        matched_capabilities = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_capabilities' -DefaultValue @())
        description = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'description' -DefaultValue '')
        native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'native_skill_entrypoint' -DefaultValue $null
        skill_md_path = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_md_path' -DefaultValue $null
        skill_root = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_root' -DefaultValue $null
        source_root = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'source_root' -DefaultValue $null
        source_kind = Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'source_kind' -DefaultValue $null
        selection_state = $SelectionState
        selection_reason = [string]$SelectionReason
        selection_rank = if ($null -eq $SelectionRank) { $null } else { [int]$SelectionRank }
    }
}

function Get-VibeRouteCandidateRows {
    param(
        [AllowNull()] [object]$RouteResult = $null,
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = ''
    )

    $rows = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    $candidateRows = @()
    if ($null -ne $RouteResult -and $RouteResult.PSObject.Properties.Name -contains 'candidates' -and $null -ne $RouteResult.candidates) {
        $candidateRows = @($RouteResult.candidates)
    }

    foreach ($candidate in $candidateRows) {
        $record = New-VibeSkillSelectionCandidateRecord -Candidate $candidate
        if ($null -eq $record) {
            continue
        }
        $skillId = [string]$record.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        if (-not [string]::IsNullOrWhiteSpace($RuntimeSelectedSkill) -and [string]::Equals($skillId, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        if ($seen.ContainsKey($skillId)) {
            continue
        }
        $rows.Add($record) | Out-Null
        $seen[$skillId] = $true
    }

    return [object[]]$rows.ToArray()
}

function Get-VibeSkillSelectionCoverageKeys {
    param(
        [Parameter(Mandatory)] [object]$Candidate
    )

    $keys = New-Object System.Collections.Generic.List[string]
    $seen = @{}

    foreach ($capability in @([object[]](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_capabilities' -DefaultValue @()))) {
        $normalized = [string]$capability
        if ([string]::IsNullOrWhiteSpace($normalized)) {
            continue
        }
        $key = 'cap:' + $normalized.Trim().ToLowerInvariant()
        if ($seen.ContainsKey($key)) {
            continue
        }
        $keys.Add($key) | Out-Null
        $seen[$key] = $true
    }

    if ($keys.Count -eq 0) {
        foreach ($token in @([object[]](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_tokens' -DefaultValue @()))) {
            $normalized = [string]$token
            if ([string]::IsNullOrWhiteSpace($normalized)) {
                continue
            }
            $key = 'token:' + $normalized.Trim().ToLowerInvariant()
            if ($seen.ContainsKey($key)) {
                continue
            }
            $keys.Add($key) | Out-Null
            $seen[$key] = $true
        }
    }

    if ($keys.Count -eq 0) {
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'skill_id' -DefaultValue '')
        if (-not [string]::IsNullOrWhiteSpace($skillId)) {
            $keys.Add('skill:' + $skillId.Trim().ToLowerInvariant()) | Out-Null
        }
    }

    return [string[]]$keys.ToArray()
}

function Test-VibeSkillSelectionRequiresExplicitRequest {
    param(
        [Parameter(Mandatory)] [object]$Candidate
    )

    $description = [string](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'description' -DefaultValue '')
    return $description -match 'Use only when the user explicitly asks for it\.?'
}

function Test-VibeSkillSelectionHasUsableTaskEvidence {
    param(
        [Parameter(Mandatory)] [object]$Candidate,
        [bool]$IsPrimary = $false
    )

    if ($IsPrimary) {
        return $true
    }

    $matchedCapabilities = @(
        @([object[]](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_capabilities' -DefaultValue @())) |
        ForEach-Object { [string]$_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if (@($matchedCapabilities).Count -gt 0) {
        return $true
    }

    $matchedTokens = @(
        @([object[]](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'matched_tokens' -DefaultValue @())) |
        ForEach-Object { [string]$_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
    )
    $score = [double](Get-VibeSkillRoutingProperty -InputObject $Candidate -PropertyName 'score' -DefaultValue 0.0)

    if (@($matchedTokens).Count -ge 3) {
        return $true
    }
    if (@($matchedTokens).Count -ge 2 -and $score -ge 0.6) {
        return $true
    }

    return $false
}

function New-VibeSkillSelectionFromRouteResult {
    param(
        [AllowNull()] [object]$RouteResult = $null,
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = '',
        [AllowEmptyString()] [string]$WorkflowLevelOverride = ''
    )

    $workflowLevel = if ([string]::IsNullOrWhiteSpace($WorkflowLevelOverride)) {
        Get-VibeWorkflowLevelFromRouteResult -RouteResult $RouteResult
    } else {
        $override = [string]$WorkflowLevelOverride
        if ($override -notin @('L', 'XL')) {
            throw "Unsupported workflow level override: $override"
        }
        $override
    }
    $selectionLimit = Get-VibeWorkflowLevelSelectionLimit -WorkflowLevel $workflowLevel
    $candidateRows = @(Get-VibeRouteCandidateRows -RouteResult $RouteResult -RuntimeSelectedSkill $RuntimeSelectedSkill)
    $selectedRows = New-Object System.Collections.Generic.List[object]
    $rejectedRows = New-Object System.Collections.Generic.List[object]
    $selectedCoverage = @{}

    $routeSelected = if ($null -ne $RouteResult -and $RouteResult.PSObject.Properties.Name -contains 'selected' -and $null -ne $RouteResult.selected) {
        [string](Get-VibeSkillRoutingProperty -InputObject $RouteResult.selected -PropertyName 'skill' -DefaultValue '')
    } else {
        ''
    }

    foreach ($candidate in $candidateRows) {
        $skillId = [string]$candidate.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }

        if ($selectedRows.Count -ge $selectionLimit) {
            $rejectedRows.Add((New-VibeSkillSelectionRecord -Candidate $candidate -SelectionState 'rejected' -SelectionReason 'selection_limit_reached')) | Out-Null
            continue
        }

        $coverageKeys = @(Get-VibeSkillSelectionCoverageKeys -Candidate $candidate)
        $addsCoverage = $selectedRows.Count -eq 0
        foreach ($key in $coverageKeys) {
            if (-not $selectedCoverage.ContainsKey($key)) {
                $addsCoverage = $true
                break
            }
        }

        $requiresExplicitRequest = Test-VibeSkillSelectionRequiresExplicitRequest -Candidate $candidate
        $isRoutePrimary = -not [string]::IsNullOrWhiteSpace($routeSelected) -and [string]::Equals($skillId, $routeSelected, [System.StringComparison]::OrdinalIgnoreCase)
        if ($requiresExplicitRequest -and -not $isRoutePrimary) {
            $rejectedRows.Add((New-VibeSkillSelectionRecord -Candidate $candidate -SelectionState 'rejected' -SelectionReason 'requires_explicit_request')) | Out-Null
            continue
        }

        $hasUsableTaskEvidence = Test-VibeSkillSelectionHasUsableTaskEvidence `
            -Candidate $candidate `
            -IsPrimary ($selectedRows.Count -eq 0)
        if (-not $hasUsableTaskEvidence) {
            $rejectedRows.Add((New-VibeSkillSelectionRecord -Candidate $candidate -SelectionState 'rejected' -SelectionReason 'insufficient_task_evidence')) | Out-Null
            continue
        }

        if (-not $addsCoverage) {
            $rejectedRows.Add((New-VibeSkillSelectionRecord -Candidate $candidate -SelectionState 'rejected' -SelectionReason 'coverage_already_selected')) | Out-Null
            continue
        }

        foreach ($key in $coverageKeys) {
            $selectedCoverage[$key] = $true
        }
        $selectionReason = if ($selectedRows.Count -eq 0) {
            'primary_route_candidate'
        } else {
            'adds_new_task_coverage'
        }
        $selectedRows.Add((New-VibeSkillSelectionRecord -Candidate $candidate -SelectionState 'selected' -SelectionReason $selectionReason -SelectionRank ($selectedRows.Count + 1))) | Out-Null
    }

    return [pscustomobject]@{
        schema_version = 'skill_selection_v1'
        workflow_level = $workflowLevel
        selection_limit = $selectionLimit
        primary_skill_id = if ($selectedRows.Count -ge 1) { [string]$selectedRows[0].skill_id } else { $null }
        candidate_skill_ids = [object[]]@($candidateRows | ForEach-Object { [string]$_.skill_id })
        selected_skill_ids = [object[]]@($selectedRows | ForEach-Object { [string]$_.skill_id })
        rejected_candidate_skill_ids = [object[]]@($rejectedRows | ForEach-Object { [string]$_.skill_id })
        candidates = [object[]]@($candidateRows | ForEach-Object { New-VibeSkillSelectionRecord -Candidate $_ -SelectionState 'candidate' -SelectionReason 'route_candidate' })
        selected = [object[]]$selectedRows.ToArray()
        rejected = [object[]]$rejectedRows.ToArray()
    }
}

function New-VibeWorkflowLevelSkillSelectionSchemes {
    param(
        [AllowNull()] [object]$RouteResult = $null,
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = ''
    )

    $candidateRows = @(Get-VibeRouteCandidateRows -RouteResult $RouteResult -RuntimeSelectedSkill $RuntimeSelectedSkill)
    $lSelection = New-VibeSkillSelectionFromRouteResult `
        -RouteResult $RouteResult `
        -RuntimeSelectedSkill $RuntimeSelectedSkill `
        -WorkflowLevelOverride 'L'
    $xlSelection = New-VibeSkillSelectionFromRouteResult `
        -RouteResult $RouteResult `
        -RuntimeSelectedSkill $RuntimeSelectedSkill `
        -WorkflowLevelOverride 'XL'

    $lSelectedSkillIds = @($lSelection.selected_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $xlSelectedSkillIds = @($xlSelection.selected_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $xlReason = if (@($xlSelectedSkillIds).Count -gt @($lSelectedSkillIds).Count) {
        'XL keeps the broader usable skill set so the plan can open extra bounded lanes after freeze.'
    } else {
        'XL keeps the same usable skill set here because the screened shortlist did not surface more bounded skills with enough task evidence yet; the workflow still stays on the heavier XL coordination contract.'
    }

    return [pscustomobject]@{
        shortlist_skill_ids = [object[]]@($candidateRows | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        shortlist_size = @($candidateRows).Count
        levels = [pscustomobject]@{
            L = [pscustomobject]@{
                workflow_level = 'L'
                selection_limit = [int]$lSelection.selection_limit
                primary_skill_id = if ([string]::IsNullOrWhiteSpace([string]$lSelection.primary_skill_id)) { $null } else { [string]$lSelection.primary_skill_id }
                selected_skill_ids = [object[]]@($lSelectedSkillIds)
                reason = 'L keeps the smallest usable skill set on one serial governed lane.'
            }
            XL = [pscustomobject]@{
                workflow_level = 'XL'
                selection_limit = [int]$xlSelection.selection_limit
                primary_skill_id = if ([string]::IsNullOrWhiteSpace([string]$xlSelection.primary_skill_id)) { $null } else { [string]$xlSelection.primary_skill_id }
                selected_skill_ids = [object[]]@($xlSelectedSkillIds)
                reason = $xlReason
            }
        }
    }
}

function New-VibeSkillRoutingFromLegacy {
    param(
        [AllowEmptyString()] [string]$RouterSelectedSkill = '',
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Recommendations = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$StageAssistantHints = @(),
        [AllowNull()] [object]$SpecialistDispatch = $null
    )

    $candidateRows = New-Object System.Collections.Generic.List[object]
    $selectedRows = New-Object System.Collections.Generic.List[object]
    $rejectedRows = New-Object System.Collections.Generic.List[object]
    $candidateSeen = @{}
    $selectedSeen = @{}
    $rejectedSeen = @{}

    foreach ($recommendation in @($Recommendations)) {
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $recommendation -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        Add-VibeSkillRoutingEntry -Rows $candidateRows -Seen $candidateSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $recommendation -State 'candidate')
    }

    foreach ($hint in @($StageAssistantHints)) {
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $hint -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        Add-VibeSkillRoutingEntry -Rows $candidateRows -Seen $candidateSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $hint -State 'candidate')
    }

    $approvedDispatch = @()
    if ($null -ne $SpecialistDispatch -and $SpecialistDispatch.PSObject.Properties.Name -contains 'approved_dispatch') {
        $approvedDispatch = @($SpecialistDispatch.approved_dispatch)
    }

    foreach ($dispatch in $approvedDispatch) {
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $dispatch -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        Add-VibeSkillRoutingEntry -Rows $candidateRows -Seen $candidateSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $dispatch -State 'candidate')
        Add-VibeSkillRoutingEntry -Rows $selectedRows -Seen $selectedSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $dispatch -State 'selected')
    }

    if (-not [string]::IsNullOrWhiteSpace($RouterSelectedSkill) -and -not $selectedSeen.ContainsKey($RouterSelectedSkill)) {
        $matching = @($Recommendations | Where-Object { [string](Get-VibeSkillRoutingProperty -InputObject $_ -PropertyName 'skill_id' -DefaultValue '') -eq $RouterSelectedSkill } | Select-Object -First 1)
        $source = if (@($matching).Count -gt 0) { $matching[0] } else { $null }
        Add-VibeSkillRoutingEntry -Rows $candidateRows -Seen $candidateSeen -Entry (New-VibeSkillRoutingEntry -SkillId $RouterSelectedSkill -Source $source -Reason 'router selected skill' -State 'candidate')
    }

    foreach ($candidate in @($candidateRows.ToArray())) {
        $skillId = [string]$candidate.skill_id
        if (-not $selectedSeen.ContainsKey($skillId)) {
            Add-VibeSkillRoutingEntry -Rows $rejectedRows -Seen $rejectedSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $candidate -Reason 'not_selected' -State 'rejected')
        }
    }

    return [pscustomobject]@{
        schema_version = 'simplified_skill_routing_v1'
        candidates = [object[]]$candidateRows.ToArray()
        selected = [object[]]$selectedRows.ToArray()
        rejected = [object[]]$rejectedRows.ToArray()
    }
}

function Get-VibeSkillRoutingSelected {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$SkillRouting = $null
    )

    $routing = if ($null -ne $SkillRouting) {
        $SkillRouting
    } elseif ($null -ne $RuntimeInputPacket -and $RuntimeInputPacket.PSObject.Properties.Name -contains 'skill_routing') {
        $RuntimeInputPacket.skill_routing
    } else {
        $null
    }

    if ($null -ne $routing -and $routing.PSObject.Properties.Name -contains 'selected') {
        $selected = @($routing.selected)
        if (@($selected).Count -gt 0) {
            return $selected
        }
    }

    if (
        $null -ne $RuntimeInputPacket -and
        $RuntimeInputPacket.PSObject.Properties.Name -contains 'work_binding' -and
        $null -ne $RuntimeInputPacket.work_binding -and
        $RuntimeInputPacket.work_binding.PSObject.Properties.Name -contains 'units'
    ) {
        return [object[]]@($RuntimeInputPacket.work_binding.units | ForEach-Object {
            $unit = $_
            $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'bound_skill' -DefaultValue '')
            if ([string]::IsNullOrWhiteSpace($skillId)) {
                return
            }

            $nativeUsageRequired = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'native_usage_required' -DefaultValue $true)
            [pscustomobject]@{
                skill_id = $skillId
                work_unit_id = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'work_unit_id' -DefaultValue '')
                phase_id = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'phase_id' -DefaultValue $null
                reason = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'reason' -DefaultValue '')
                task_slice = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'task_slice' -DefaultValue '')
                native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'native_skill_entrypoint' -DefaultValue $null
                skill_md_path = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'skill_md_path' -DefaultValue $null
                dispatch_phase = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
                parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
                native_usage_required = $nativeUsageRequired
                usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'usage_required' -DefaultValue $nativeUsageRequired)
                skill_root = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'skill_root' -DefaultValue $null
                bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
                must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'must_preserve_workflow' -DefaultValue $true)
                binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
                lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'lane_policy' -DefaultValue 'native_contract')
                write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $skillId))
                review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'review_mode' -DefaultValue 'native_contract')
                execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'execution_priority' -DefaultValue 50)
                required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'required_inputs' -DefaultValue @())
                expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'expected_outputs' -DefaultValue @())
                verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'verification_expectation' -DefaultValue 'Record selected skill usage evidence before completion.')
                progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'progressive_load_policy' -DefaultValue @())
            }
        } | Where-Object { $null -ne $_ })
    }

    return @()
}

function Get-VibeSkillRoutingSelectedSkillIds {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$SkillRouting = $null
    )

    return [object[]]@(Get-VibeSkillRoutingSelected -RuntimeInputPacket $RuntimeInputPacket -SkillRouting $SkillRouting | ForEach-Object {
        [string](Get-VibeSkillRoutingProperty -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
}

function Convert-VibeSkillRoutingSelectedToDispatch {
    param(
        [AllowNull()] [object]$SkillRouting = $null,
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    return [object[]]@(Get-VibeSkillRoutingSelected -RuntimeInputPacket $RuntimeInputPacket -SkillRouting $SkillRouting | ForEach-Object {
        $entry = $_
        [pscustomobject]@{
            skill_id = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_id' -DefaultValue '')
            phase_id = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'phase_id' -DefaultValue $null
            reason = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'reason' -DefaultValue '')
            task_slice = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'task_slice' -DefaultValue '')
            native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_skill_entrypoint' -DefaultValue $null
            skill_md_path = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_md_path' -DefaultValue $null
            dispatch_phase = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
            parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
            native_usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true)
            usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'usage_required' -DefaultValue (Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true))
            skill_root = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_root' -DefaultValue $null
            bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
            must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'must_preserve_workflow' -DefaultValue $true)
            binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
            lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'lane_policy' -DefaultValue 'native_contract')
            write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_id' -DefaultValue 'unknown')))
            review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'review_mode' -DefaultValue 'native_contract')
            execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'execution_priority' -DefaultValue 50)
            required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'required_inputs' -DefaultValue @())
            expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'expected_outputs' -DefaultValue @())
            verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'verification_expectation' -DefaultValue 'Record selected skill usage evidence before completion.')
            progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'progressive_load_policy' -DefaultValue @())
        }
    })
}

function Convert-VibeSkillExecutionLockToDispatch {
    param(
        [AllowNull()] [object]$SkillExecutionLock = $null
    )

    if ($null -eq $SkillExecutionLock) {
        return @()
    }

    $state = [string](Get-VibeSkillRoutingProperty -InputObject $SkillExecutionLock -PropertyName 'state' -DefaultValue '')
    if (-not [string]::Equals($state, 'active', [System.StringComparison]::OrdinalIgnoreCase)) {
        return @()
    }

    $lockedDispatch = @()
    if ($SkillExecutionLock.PSObject.Properties.Name -contains 'locked_dispatch') {
        $lockedDispatch = @($SkillExecutionLock.locked_dispatch)
    }

    if (@($lockedDispatch).Count -eq 0 -and $SkillExecutionLock.PSObject.Properties.Name -contains 'locked_skill_ids') {
        $lockedDispatch = @($SkillExecutionLock.locked_skill_ids | ForEach-Object {
            $skillId = [string]$_
            if (-not [string]::IsNullOrWhiteSpace($skillId)) {
                [pscustomobject]@{ skill_id = $skillId }
            }
        })
    }

    return [object[]]@($lockedDispatch | Where-Object { $null -ne $_ } | ForEach-Object {
        $entry = $_
        $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            return
        }

        [pscustomobject]@{
            skill_id = $skillId
            phase_id = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'phase_id' -DefaultValue $null
            reason = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'reason' -DefaultValue '')
            task_slice = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'task_slice' -DefaultValue ('Resolve locked specialist execution for {0}.' -f $skillId))
            native_skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_skill_entrypoint' -DefaultValue $null
            skill_md_path = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_md_path' -DefaultValue $null
            dispatch_phase = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
            parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
            native_usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true)
            usage_required = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'usage_required' -DefaultValue (Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'native_usage_required' -DefaultValue $true))
            skill_root = Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'skill_root' -DefaultValue $null
            bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
            must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'must_preserve_workflow' -DefaultValue $true)
            binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
            lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'lane_policy' -DefaultValue 'native_contract')
            write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $skillId))
            review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'review_mode' -DefaultValue 'native_contract')
            execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'execution_priority' -DefaultValue 50)
            required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'required_inputs' -DefaultValue @())
            expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'expected_outputs' -DefaultValue @())
            verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'verification_expectation' -DefaultValue 'Resolve locked specialist execution before delivery acceptance.')
            progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'progressive_load_policy' -DefaultValue @())
            locked_for_execution = $true
            lock_source = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'lock_source' -DefaultValue 'unknown')
            reconciliation_state = [string](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'reconciliation_state' -DefaultValue 'current_surfaced')
            requires_resolution = [bool](Get-VibeSkillRoutingProperty -InputObject $entry -PropertyName 'requires_resolution' -DefaultValue $true)
        }
    })
}

function New-VibeSkillRoutingSummary {
    param(
        [AllowNull()] [object]$SkillRouting = $null,
        [AllowNull()] [object]$SkillUsage = $null
    )

    $usedCount = if ($null -ne $SkillUsage -and $SkillUsage.PSObject.Properties.Name -contains 'used') {
        @($SkillUsage.used).Count
    } elseif ($null -ne $SkillUsage -and $SkillUsage.PSObject.Properties.Name -contains 'used_skills') {
        @($SkillUsage.used_skills).Count
    } else {
        0
    }
    $unusedCount = if ($null -ne $SkillUsage -and $SkillUsage.PSObject.Properties.Name -contains 'unused') {
        @($SkillUsage.unused).Count
    } elseif ($null -ne $SkillUsage -and $SkillUsage.PSObject.Properties.Name -contains 'unused_skills') {
        @($SkillUsage.unused_skills).Count
    } else {
        0
    }

    return [pscustomobject]@{
        candidate_count = if ($null -ne $SkillRouting -and $SkillRouting.PSObject.Properties.Name -contains 'candidates') { @($SkillRouting.candidates).Count } else { 0 }
        selected_count = if ($null -ne $SkillRouting -and $SkillRouting.PSObject.Properties.Name -contains 'selected') { @($SkillRouting.selected).Count } else { 0 }
        rejected_count = if ($null -ne $SkillRouting -and $SkillRouting.PSObject.Properties.Name -contains 'rejected') { @($SkillRouting.rejected).Count } else { 0 }
        used_count = [int]$usedCount
        unused_count = [int]$unusedCount
    }
}
