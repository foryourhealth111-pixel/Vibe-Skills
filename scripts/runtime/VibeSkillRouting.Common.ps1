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
        Add-VibeSkillRoutingEntry -Rows $selectedRows -Seen $selectedSeen -Entry (New-VibeSkillRoutingEntry -SkillId $RouterSelectedSkill -Source $source -Reason 'router selected skill' -State 'selected')
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
        return @($routing.selected)
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
