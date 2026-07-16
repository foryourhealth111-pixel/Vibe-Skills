Set-StrictMode -Version Latest

function Resolve-VibeLocalSkillAuthority {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SkillId,
        [AllowEmptyString()] [string]$SkillEntrypoint = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = '',
        [switch]$RequireProvidedEntrypoint
    )

    $skillIdText = ([string]$SkillId).Trim()
    if ([string]::IsNullOrWhiteSpace($skillIdText)) {
        return [pscustomobject]@{ valid = $false; reason = 'missing_skill_id'; skill_id = $skillIdText; canonical_entrypoint = $null }
    }
    if ($skillIdText -eq 'vibe') {
        return [pscustomobject]@{ valid = $false; reason = 'controller_entry_excluded'; skill_id = $skillIdText; canonical_entrypoint = $null }
    }

    $resolvedHostId = if (Get-Command -Name Resolve-VgoHostId -ErrorAction SilentlyContinue) {
        Resolve-VgoHostId -HostId $HostId
    } elseif ([string]::IsNullOrWhiteSpace($HostId)) {
        'codex'
    } else {
        $HostId.Trim().ToLowerInvariant()
    }
    $resolvedTargetRoot = if (Get-Command -Name Resolve-VgoTargetRoot -ErrorAction SilentlyContinue) {
        Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $resolvedHostId
    } elseif ([string]::IsNullOrWhiteSpace($TargetRoot)) {
        [System.IO.Path]::GetFullPath('.')
    } else {
        [System.IO.Path]::GetFullPath($TargetRoot)
    }
    $rootCandidates = New-Object System.Collections.Generic.List[string]
    $seenRoots = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $explicitRoot = [System.IO.Path]::GetFullPath((Join-Path $resolvedTargetRoot 'skills'))
    if ($seenRoots.Add($explicitRoot)) { $rootCandidates.Add($explicitRoot) | Out-Null }
    $defaultRoots = if ($resolvedHostId -eq 'claude-code') { @('~/.claude/skills') } else { @('~/.agents/skills', '~/.codex/skills', '~/.codex/plugins/cache') }
    foreach ($rawRoot in $defaultRoots) {
        $rootText = ([string]$rawRoot).Trim()
        $homeRoot = Split-Path -Parent $resolvedTargetRoot
        $suffix = $rootText.Substring(1).TrimStart('/', '\')
        $resolvedRoot = if ($rootText.StartsWith('~/') -or $rootText.StartsWith('~\')) {
            [System.IO.Path]::GetFullPath((Join-Path $homeRoot $suffix))
        } else {
            [System.IO.Path]::GetFullPath($rootText)
        }
        if ($seenRoots.Add($resolvedRoot)) { $rootCandidates.Add($resolvedRoot) | Out-Null }
    }

    $activePath = $null
    $activeSourceRoot = $null
    $activePriority = 0
    for ($rootIndex = 0; $rootIndex -lt $rootCandidates.Count; $rootIndex++) {
        foreach ($candidatePath in @(
            (Join-Path $rootCandidates[$rootIndex] (Join-Path $skillIdText 'SKILL.md')),
            (Join-Path $rootCandidates[$rootIndex] (Join-Path 'custom' (Join-Path $skillIdText 'SKILL.md')))
        )) {
            if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
                $activePath = [System.IO.Path]::GetFullPath($candidatePath)
                $activeSourceRoot = [System.IO.Path]::GetFullPath($rootCandidates[$rootIndex])
                $activePriority = $rootIndex
                break
            }
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$activePath)) { break }

        $nestedMatches = @(Get-ChildItem -LiteralPath $rootCandidates[$rootIndex] -Filter 'SKILL.md' -File -Recurse -ErrorAction SilentlyContinue | Where-Object {
                [string]::Equals([string]$_.Directory.Name, $skillIdText, [System.StringComparison]::OrdinalIgnoreCase)
            })
        if ($nestedMatches.Count -eq 1) {
            $activePath = [System.IO.Path]::GetFullPath($nestedMatches[0].FullName)
            $activeSourceRoot = [System.IO.Path]::GetFullPath($rootCandidates[$rootIndex])
            $activePriority = $rootIndex
            break
        }
        if ($nestedMatches.Count -gt 1) {
            return [pscustomobject]@{
                valid = $false
                reason = 'ambiguous_nested_skill_id'
                skill_id = $skillIdText
                canonical_entrypoint = $null
                candidate_entrypoints = [object[]]@($nestedMatches | ForEach-Object { [System.IO.Path]::GetFullPath($_.FullName) })
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace([string]$activePath)) {
        return [pscustomobject]@{ valid = $false; reason = 'not_in_local_skill_index'; skill_id = $skillIdText; canonical_entrypoint = $null }
    }

    $providedPath = if ([string]::IsNullOrWhiteSpace($SkillEntrypoint)) { '' } else { [System.IO.Path]::GetFullPath($SkillEntrypoint) }
    if ([string]::IsNullOrWhiteSpace($providedPath) -and $RequireProvidedEntrypoint) {
        return [pscustomobject]@{
            valid = $false; reason = 'missing_skill_entrypoint'; skill_id = $skillIdText; canonical_entrypoint = $activePath
            source_root = $activeSourceRoot; source_kind = 'host_installed'; source_priority = $activePriority; active = $true; duplicate_state = 'active'
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($providedPath) -and -not [string]::Equals($providedPath, $activePath, [System.StringComparison]::OrdinalIgnoreCase)) {
        return [pscustomobject]@{
            valid = $false; reason = 'entrypoint_mismatch'; skill_id = $skillIdText; canonical_entrypoint = $activePath; provided_entrypoint = $providedPath
            source_root = $activeSourceRoot; source_kind = 'host_installed'; source_priority = $activePriority; active = $true; duplicate_state = 'active'
        }
    }
    return [pscustomobject]@{
        valid = $true; reason = 'ok'; skill_id = $skillIdText; canonical_entrypoint = $activePath; skill_entrypoint = $activePath
        skill_root = [System.IO.Path]::GetFullPath((Split-Path -Parent $activePath)); source_root = $activeSourceRoot; source_kind = 'host_installed'
        source_priority = $activePriority; active = $true; duplicate_state = 'active'
    }
}

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
    $skillEntrypoint = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'skill_entrypoint' -DefaultValue '')
    $skillMdPath = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'skill_md_path' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillMdPath)) {
        $skillMdPath = $skillEntrypoint
    }
    $skillRoot = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'skill_root' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($skillRoot) -and -not [string]::IsNullOrWhiteSpace($skillMdPath)) {
        $skillRoot = Split-Path -Parent $skillMdPath
    }
    $taskSlice = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'task_slice' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($taskSlice)) {
        $taskSlice = if ([string]::IsNullOrWhiteSpace($sourceReason)) { ('Consider {0} as a local Skill candidate; this record does not select it for execution.' -f $SkillId) } else { $sourceReason }
    }

    return [pscustomobject]@{
        skill_id = $SkillId
        skill_md_path = if ([string]::IsNullOrWhiteSpace($skillMdPath)) { $null } else { $skillMdPath }
        reason = if ([string]::IsNullOrWhiteSpace($Reason)) { $sourceReason } else { $Reason }
        task_slice = $taskSlice
        state = $State
        dispatch_phase = 'not_applicable'
        parallelizable_in_root_xl = $false
        skill_entrypoint = if ([string]::IsNullOrWhiteSpace($skillEntrypoint)) { $null } else { $skillEntrypoint }
        skill_root = if ([string]::IsNullOrWhiteSpace($skillRoot)) { $null } else { $skillRoot }
        bounded_role = 'candidate_only'
        must_preserve_workflow = $false
        binding_profile = 'candidate_only'
        lane_policy = 'none'
        write_scope = 'none'
        review_mode = 'none'
        execution_priority = 0
        required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'required_inputs' -DefaultValue @())
        expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'expected_outputs' -DefaultValue @())
        verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $Source -PropertyName 'verification_expectation' -DefaultValue 'Satisfy the module acceptance criteria.')
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

function New-VibeSkillCandidateAudit {
    param(
        [AllowEmptyString()] [string]$CandidateFocusSkill = '',
        [AllowEmptyCollection()] [AllowNull()] [object[]]$Recommendations = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$StageAssistantHints = @(),
        [AllowEmptyCollection()] [AllowNull()] [string[]]$SelectedSkillIds = @(),
        [AllowNull()] [object]$SpecialistDispatch = $null
    )

    $candidateRows = New-Object System.Collections.Generic.List[object]
    $rejectedRows = New-Object System.Collections.Generic.List[object]
    $candidateSeen = @{}
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
    }

    if (-not [string]::IsNullOrWhiteSpace($CandidateFocusSkill)) {
        $matching = @($Recommendations | Where-Object { [string](Get-VibeSkillRoutingProperty -InputObject $_ -PropertyName 'skill_id' -DefaultValue '') -eq $CandidateFocusSkill } | Select-Object -First 1)
        $source = if (@($matching).Count -gt 0) { $matching[0] } else { $null }
        Add-VibeSkillRoutingEntry -Rows $candidateRows -Seen $candidateSeen -Entry (New-VibeSkillRoutingEntry -SkillId $CandidateFocusSkill -Source $source -Reason 'router candidate audit' -State 'candidate')
    }

    foreach ($candidate in @($candidateRows.ToArray())) {
        $skillId = [string]$candidate.skill_id
        if ($skillId -cin @($SelectedSkillIds)) {
            continue
        }
        Add-VibeSkillRoutingEntry -Rows $rejectedRows -Seen $rejectedSeen -Entry (New-VibeSkillRoutingEntry -SkillId $skillId -Source $candidate -Reason 'candidate_audit_only' -State 'rejected')
    }

    return [pscustomobject]@{
        schema_version = 'simplified_skill_routing_v1'
        candidates = [object[]]$candidateRows.ToArray()
        rejected = [object[]]$rejectedRows.ToArray()
    }
}

function Get-VibeBoundSkillRoutingEntries {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$SkillRouting = $null
    )

    if (
        $null -ne $RuntimeInputPacket -and
        $RuntimeInputPacket.PSObject.Properties.Name -contains 'module_assignments' -and
        $null -ne $RuntimeInputPacket.module_assignments -and
        $RuntimeInputPacket.module_assignments.PSObject.Properties.Name -contains 'units'
    ) {
        return [object[]]@($RuntimeInputPacket.module_assignments.units | ForEach-Object {
            $unit = $_
            $skillId = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'bound_skill' -DefaultValue '')
            if ([string]::IsNullOrWhiteSpace($skillId)) {
                return
            }

            [pscustomobject]@{
                skill_id = $skillId
                work_unit_id = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'work_unit_id' -DefaultValue '')
                phase_id = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'phase_id' -DefaultValue $null
                reason = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'reason' -DefaultValue '')
                task_slice = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'task_slice' -DefaultValue '')
                skill_entrypoint = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'skill_entrypoint' -DefaultValue $null
                skill_md_path = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'skill_md_path' -DefaultValue $null
                dispatch_phase = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
                parallelizable_in_root_xl = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
                skill_root = Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'skill_root' -DefaultValue $null
                bounded_role = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
                must_preserve_workflow = [bool](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'must_preserve_workflow' -DefaultValue $true)
                binding_profile = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
                lane_policy = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'lane_policy' -DefaultValue 'agent_module_handoff')
                write_scope = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $skillId))
                review_mode = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'review_mode' -DefaultValue 'module_acceptance')
                execution_priority = [int](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'execution_priority' -DefaultValue 50)
                required_inputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'required_inputs' -DefaultValue @())
                expected_outputs = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'expected_outputs' -DefaultValue @())
                verification_expectation = [string](Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'verification_expectation' -DefaultValue 'Satisfy the module acceptance criteria.')
                progressive_load_policy = [object[]]@(Get-VibeSkillRoutingProperty -InputObject $unit -PropertyName 'progressive_load_policy' -DefaultValue @())
            }
        } | Where-Object { $null -ne $_ })
    }

    return @()
}

function Get-VibeBoundSkillIds {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$SkillRouting = $null
    )

    return [object[]]@(Get-VibeBoundSkillRoutingEntries -RuntimeInputPacket $RuntimeInputPacket -SkillRouting $SkillRouting | ForEach-Object {
        [string](Get-VibeSkillRoutingProperty -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
}

function Convert-VibeModuleWorkPlanToDispatch {
    param(
        [Parameter(Mandatory)] [object]$ModuleWorkPlan,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$HostId
    )

    return [object[]]@(@($ModuleWorkPlan.work_units) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.skill_id) } | ForEach-Object {
        $unit = $_
        $skillId = [string]$unit.skill_id
        $authority = Resolve-VibeLocalSkillAuthority `
            -RepoRoot $RepoRoot `
            -SkillId $skillId `
            -TargetRoot $TargetRoot `
            -HostId $HostId
        if (-not [bool]$authority.valid) {
            throw ('module work unit `{0}` cannot load skill `{1}`: {2}' -f [string]$unit.unit_id, $skillId, [string]$authority.reason)
        }

        [pscustomobject]@{
            skill_id = $skillId
            module_id = [string]$unit.module_id
            work_unit_id = [string]$unit.unit_id
            depends_on_unit_ids = [object[]]@($unit.depends_on_unit_ids)
            phase_id = [string]$unit.phase_id
            stage_order = [int]$unit.stage_order
            reason = 'approved_module_work_plan'
            task_slice = [string]$unit.responsibility
            skill_entrypoint = [string]$authority.skill_entrypoint
            skill_md_path = [string]$authority.canonical_entrypoint
            dispatch_phase = 'in_execution'
            parallelizable_in_root_xl = [bool]([string]$ModuleWorkPlan.workflow_level -eq 'XL')
            skill_root = [string]$authority.skill_root
            bounded_role = [string]$unit.role
            must_preserve_workflow = $true
            binding_profile = 'module_work_unit'
            lane_policy = 'module_dependency_contract'
            write_scope = [string]$unit.write_scope
            review_mode = if ([string]$unit.role -eq 'verifier') { 'independent_verification' } else { 'module_acceptance' }
            execution_priority = 50
            required_inputs = @()
            expected_outputs = [object[]]@($unit.expected_outputs)
            verification_expectation = (@($unit.verification) -join '; ')
            progressive_load_policy = @()
        }
    })
}

function New-VibeSkillRoutingSummary {
    param(
        [AllowNull()] [object]$SkillRouting = $null
    )

    return [pscustomobject]@{
        candidate_count = if ($null -ne $SkillRouting -and $SkillRouting.PSObject.Properties.Name -contains 'candidates') { @($SkillRouting.candidates).Count } else { 0 }
        rejected_count = if ($null -ne $SkillRouting -and $SkillRouting.PSObject.Properties.Name -contains 'rejected') { @($SkillRouting.rejected).Count } else { 0 }
    }
}
