Set-StrictMode -Off
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$skillRoutingCommon = Join-Path $PSScriptRoot 'VibeSkillRouting.Common.ps1'
if (Test-Path -LiteralPath $skillRoutingCommon -PathType Leaf) {
    . $skillRoutingCommon
}

Set-StrictMode -Off

function global:Get-VibeHostAdapterIdentityProjection {
    param(
        [AllowNull()] [object]$HostAdapter,
        [AllowEmptyString()] [string]$RequestedPropertyName = 'requested_id',
        [AllowEmptyString()] [string]$EffectivePropertyName = 'id',
        [AllowEmptyString()] [string]$FallbackHostId = ''
    )
    return New-VibeHostAdapterIdentityProjection -HostAdapter $HostAdapter -RequestedPropertyName $RequestedPropertyName -EffectivePropertyName $EffectivePropertyName -FallbackHostId $FallbackHostId
}

function Get-VibeHostAdapterEntry {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$HostId = ''
    )

    return Resolve-VgoAdapterEntry -StartPath $RepoRoot -HostId $HostId
}

function Resolve-VibeHostTargetRoot {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    if ($null -eq $HostAdapter -or $null -eq $HostAdapter.default_target_root) {
        return $null
    }

    $targetSpec = $HostAdapter.default_target_root
    $envName = if ($targetSpec.PSObject.Properties.Name -contains 'env') { [string]$targetSpec.env } else { '' }
    $rel = if ($targetSpec.PSObject.Properties.Name -contains 'rel') { [string]$targetSpec.rel } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $envValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            return [System.IO.Path]::GetFullPath($envValue)
        }
    }
    if ([string]::IsNullOrWhiteSpace($rel)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($rel)) {
        return [System.IO.Path]::GetFullPath($rel)
    }
    $homeDir = Resolve-VgoHomeDirectory
    return [System.IO.Path]::GetFullPath((Join-Path $homeDir $rel))
}

function Get-VibeRelativePathCompat {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)

    if ($baseFull -eq $targetFull) {
        return '.'
    }

    if ($baseFull.Substring(0, 1).ToUpperInvariant() -ne $targetFull.Substring(0, 1).ToUpperInvariant()) {
        return $targetFull
    }

    $baseWithSeparator = $baseFull.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $baseUri = New-Object System.Uri($baseWithSeparator)
    $targetUri = New-Object System.Uri($targetFull)
    $relative = [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString())
    return $relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Test-VibeObjectHasProperty {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName
    )

    if ($null -eq $InputObject -or [string]::IsNullOrWhiteSpace($PropertyName)) {
        return $false
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        return $InputObject.Contains($PropertyName)
    }

    $propertyNames = @($InputObject.PSObject.Properties | ForEach-Object { [string]$_.Name })
    return ($propertyNames -contains $PropertyName)
}

function Test-VibeStructuredObject {
    param(
        [AllowNull()] [object]$InputObject
    )

    if ($null -eq $InputObject) {
        return $false
    }
    if ($InputObject -is [string] -or $InputObject -is [System.ValueType]) {
        return $false
    }
    if ($InputObject -is [System.Array] -or $InputObject -is [System.Collections.IList]) {
        return $false
    }

    return (
        ($InputObject -is [System.Management.Automation.PSCustomObject]) -or
        ($InputObject -is [System.Collections.IDictionary])
    )
}

function Get-VibePropertySafe {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Contains($PropertyName)) {
            return $InputObject[$PropertyName]
        }
        return $DefaultValue
    }

    if (-not (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName $PropertyName)) {
        return $DefaultValue
    }

    try {
        return $InputObject.$PropertyName
    } catch {
        return $DefaultValue
    }
}

function Get-VibeSafeArrayCount {
    param(
        [AllowNull()] [object]$InputObject
    )
    
    if ($null -eq $InputObject) {
        return 0
    }
    
    try {
        # Handle arrays and collections
        if ($InputObject -is [System.Collections.ICollection]) {
            return [int]$InputObject.Count
        }
        # Handle objects with Count property
        if (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName 'Count') {
            return [int]$InputObject.Count
        }
        # Handle objects with Length property
        if (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName 'Length') {
            return [int]$InputObject.Length
        }
        # Treat scalar as count 1
        return 1
    } catch {
        return 0
    }
}

function Get-VibeNestedPropertySafe {
    param(
        [AllowNull()] [object]$InputObject,
        [AllowNull()] [string[]]$PropertyPath,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }
    
    # Handle null or empty PropertyPath
    if ($null -eq $PropertyPath) {
        return $InputObject
    }
    
    # Safely get Count (handles Set-StrictMode)
    $pathCount = 0
    try {
        # Use @() to handle null/undefined PropertyPath safely
        $pathCount = @($PropertyPath).Count
    } catch {
        return $DefaultValue
    }
    
    if ($pathCount -eq 0) {
        return $InputObject
    }

    $current = $InputObject
    foreach ($prop in $PropertyPath) {
        if ($null -eq $current) {
            return $DefaultValue
        }
        if (-not (Test-VibeObjectHasProperty -InputObject $current -PropertyName $prop)) {
            return $DefaultValue
        }
        try {
            $current = $current.$prop
        } catch {
            return $DefaultValue
        }
    }

    return $current
}

function Get-VibeWorkflowLevelConfirmationDetailValue {
    param(
        [AllowNull()] [object]$WorkflowLevelConfirmation = $null,
        [Parameter(Mandatory)] [string]$LevelName,
        [Parameter(Mandatory)] [string]$PropertyName
    )

    $levelDetails = Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'level_details' -DefaultValue $null
    if (-not (Test-VibeStructuredObject -InputObject $levelDetails)) {
        return $null
    }

    $levelRecord = Get-VibePropertySafe -InputObject $levelDetails -PropertyName $LevelName -DefaultValue $null
    if (-not (Test-VibeStructuredObject -InputObject $levelRecord)) {
        return $null
    }

    $value = Get-VibePropertySafe -InputObject $levelRecord -PropertyName $PropertyName -DefaultValue $null
    if ($null -eq $value) {
        return $null
    }

    return [string]$value
}

function Get-VibeWorkflowLevelConfirmationLines {
    param(
        [AllowNull()] [object]$WorkflowLevelConfirmation = $null
    )

    if ($null -eq $WorkflowLevelConfirmation) {
        return @('No workflow level confirmation was recorded in the intent contract.')
    }

    $lines = @(
        "- User-visible: $([bool](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'user_visible' -DefaultValue $false))"
    )

    $recommendedLevel = [string](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'recommended_level' -DefaultValue '')
    if (-not [string]::IsNullOrWhiteSpace($recommendedLevel)) {
        $lines += ('- Recommended level: {0}' -f $recommendedLevel)
    }

    $recommendationReason = [string](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'recommendation_reason' -DefaultValue '')
    if (-not [string]::IsNullOrWhiteSpace($recommendationReason)) {
        $lines += ('- Recommendation reason: {0}' -f $recommendationReason)
    }

    $decisionImportance = [string](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'decision_importance' -DefaultValue '')
    if (-not [string]::IsNullOrWhiteSpace($decisionImportance)) {
        $lines += ('- Why this decision matters: {0}' -f $decisionImportance)
    }

    $lines += '- Before asking the user to choose L or XL, explain each task-specific workflow and list its task-specific candidate skill names. Label those names as candidates that are not yet selected or used.'

    $levels = Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'levels' -DefaultValue $null
    foreach ($levelName in @('L', 'XL')) {
        $levelSummary = [string](Get-VibePropertySafe -InputObject $levels -PropertyName $levelName -DefaultValue '')
        if (-not [string]::IsNullOrWhiteSpace($levelSummary)) {
            $lines += ('- {0}: {1}' -f $levelName, $levelSummary)
        }

        foreach ($detail in @(
                @{ property = 'workflow'; label = 'workflow' },
                @{ property = 'skills'; label = 'skills' },
                @{ property = 'why_this_fit'; label = 'rationale' },
                @{ property = 'confirm_reply'; label = 'confirm reply' }
            )) {
            $detailValue = Get-VibeWorkflowLevelConfirmationDetailValue `
                -WorkflowLevelConfirmation $WorkflowLevelConfirmation `
                -LevelName $levelName `
                -PropertyName ([string]$detail.property)
            if (-not [string]::IsNullOrWhiteSpace($detailValue)) {
                $lines += ('- {0} {1}: {2}' -f $levelName, [string]$detail.label, $detailValue)
            }
        }
    }

    $question = [string](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'question' -DefaultValue '')
    if (-not [string]::IsNullOrWhiteSpace($question)) {
        $lines += ('- Question: {0}' -f $question)
    }

    $selectionPrompt = [string](Get-VibePropertySafe -InputObject $WorkflowLevelConfirmation -PropertyName 'selection_prompt' -DefaultValue '')
    if (-not [string]::IsNullOrWhiteSpace($selectionPrompt)) {
        $lines += ('- Selection prompt: {0}' -f $selectionPrompt)
    }

    return @($lines)
}

function New-VibeSkillSearchGuideProjection {
    param(
        [AllowEmptyString()] [string]$RepoRoot = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $skillRoots = [System.Collections.Generic.List[object]]::new()
    $resolvedHostId = if ([string]::IsNullOrWhiteSpace($HostId)) { 'codex' } else { $HostId.Trim().ToLowerInvariant() }
    if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) {
        $skillRoots.Add([pscustomobject]@{
                kind = 'host_local'
                path = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
            }) | Out-Null
        if ($resolvedHostId -eq 'codex') {
            $pluginCacheRoot = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $TargetRoot) '.codex\plugins\cache'))
            if (Test-Path -LiteralPath $pluginCacheRoot -PathType Container) {
                $skillRoots.Add([pscustomobject]@{
                        kind = 'host_plugin_cache'
                        path = $pluginCacheRoot
                    }) | Out-Null
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        $skillRoots.Add([pscustomobject]@{
                kind = 'repo_core'
                path = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot 'core\skills'))
            }) | Out-Null
        $skillRoots.Add([pscustomobject]@{
                kind = 'repo_bundled'
                path = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot 'bundled\skills'))
            }) | Out-Null
    }

    return [pscustomobject]@{
        schema_version = 'skill_search_guide_v1'
        skill_roots = @($skillRoots.ToArray())
        search_protocol = @(
            '先拆任务，再拆模块',
            '会按模块搜索本地 skills',
            '每个模块单独搜索本地 skills',
            '会先看候选 skill 名和短描述，再打开并阅读候选 `SKILL.md`',
            '每个模块最多保留 3 个候选，避免上下文污染',
            '以候选 `SKILL.md` 的真实用途为准，不按词面碰撞判断'
        )
        selection_rules = @(
            '会给出 `L` / `XL` 两套 skills 组织方案，并说明每个 skill 的职责',
            '优先选择真正负责该模块的 owner，不选只沾边的 helper',
            '一个 skill 可以覆盖多个模块',
            'explicit_only skills 只有在用户明确点名时才可入选',
            '不得跨越候选 skill 声明的负边界或适用限制',
            '没有 owner 时必须报缺口，不得伪装覆盖',
            '没有 owner 的模块会明确标出缺口'
        )
        disclosure_rules = @(
            'requirement 阶段公开搜索办法，并在请用户选择前由 Agent 分别给出 L / XL 的具体工作流和候选 skill 名称；这些名称必须标为尚未正式选定或使用，不得公开程序候选排名或预选结果',
            'xl_plan 阶段公开模块、候选、最终采用和缺口',
            'execute 阶段公开本次实际启用的 skills'
        )
        workflow_level_contract = [pscustomobject]@{
            levels = @('L', 'XL')
            L = '先讲清模块，再组织较轻量的串行方案'
            XL = '先讲清模块，再组织更完整的分波次方案'
        }
    }
}

function Get-VibeSkillSearchGuideLines {
    param(
        [AllowNull()] [object]$SkillSearchGuide = $null
    )

    $resolvedGuide = if ($null -ne $SkillSearchGuide) {
        $SkillSearchGuide
    } else {
        New-VibeSkillSearchGuideProjection
    }

    $searchProtocol = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $resolvedGuide -PropertyName 'search_protocol' -DefaultValue @()))
    $selectionRules = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $resolvedGuide -PropertyName 'selection_rules' -DefaultValue @()))
    $disclosureRules = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $resolvedGuide -PropertyName 'disclosure_rules' -DefaultValue @()))

    $lines = @()
    foreach ($line in @($searchProtocol + $selectionRules + $disclosureRules)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$line)) {
            $lines += ('- {0}' -f [string]$line)
        }
    }

    if (@($lines).Count -gt 0) {
        return @($lines)
    }

    return @(
        '- 先拆任务，再拆模块',
        '- 会按模块搜索本地 skills',
        '- 每个模块单独搜索本地 skills',
        '- 会先看候选 skill 名和短描述，再打开并阅读候选 `SKILL.md`',
        '- 会给出 `L` / `XL` 两套 skills 组织方案，并说明每个 skill 的职责',
        '- 没有 owner 的模块会明确标出缺口'
    )
}

function Get-VibeWorkflowLevelSkillSelectionLines {
    param(
        [string[]]$SelectedSkillIds = @(),
        [AllowNull()] [object]$SkillSelection = $null
    )

    return @(Get-VibeSkillSearchGuideLines)
}

function Get-VibeSelectedTaskSkillIds {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$ModuleAssignments = $null
    )

    return [object[]]@(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $RuntimeInputPacket -ModuleAssignments $ModuleAssignments)
}

function Get-VibeModuleAssignmentsBoundSkillIds {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$ModuleAssignments = $null
    )

    $resolvedModuleAssignments = if ($null -ne $ModuleAssignments) {
        $ModuleAssignments
    } elseif (
        $null -ne $RuntimeInputPacket -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'module_assignments')
    ) {
        $RuntimeInputPacket.module_assignments
    } else {
        $null
    }

    if (
        $null -eq $resolvedModuleAssignments -or
        -not (Test-VibeObjectHasProperty -InputObject $resolvedModuleAssignments -PropertyName 'units') -or
        $null -eq $resolvedModuleAssignments.units
    ) {
        return @()
    }

    return [object[]]@(
        @($resolvedModuleAssignments.units | ForEach-Object {
                [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'bound_skill' -DefaultValue '')
            } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    )
}

function Get-VibePrimaryBoundSkillId {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$ModuleAssignments = $null,
        [AllowEmptyString()] [string]$FallbackSkillId = ''
    )

    $selectedTaskSkillIds = @(Get-VibeSelectedTaskSkillIds -RuntimeInputPacket $RuntimeInputPacket -ModuleAssignments $ModuleAssignments)
    if (@($selectedTaskSkillIds).Count -ge 1) {
        return [string]$selectedTaskSkillIds[0]
    }

    return $FallbackSkillId
}

function Get-VibeRuntimeStageAssistantHints {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    return @()
}

function New-VibeRuntimeModuleAssignmentsProjection {
    param(
        [AllowEmptyString()] [string]$Task = '',
        [AllowEmptyString()] [string]$RunId = '',
        [AllowNull()] [object[]]$SelectedSkillRecords = @(),
        [bool]$OrganizationProvided = $false
    )

    $selectedRows = @($SelectedSkillRecords)

    $units = New-Object System.Collections.Generic.List[object]
    $ordinal = 0
    foreach ($selectedRow in @($selectedRows)) {
        $skillId = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'skill_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }

        $ordinal += 1
        $workUnitId = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'work_unit_id' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($workUnitId)) {
            $workUnitId = ('runtime-bound-skill-{0}' -f $ordinal)
        }
        $taskSlice = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'task_slice' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($taskSlice)) {
            $taskSlice = ('Use {0} for bounded specialist work.' -f $skillId)
        }

        $units.Add(
            [pscustomobject]@{
                work_unit_id = $workUnitId
                bound_skill = $skillId
                phase_id = Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'phase_id' -DefaultValue $null
                reason = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'reason' -DefaultValue '')
                task_slice = $taskSlice
                skill_md_path = Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'skill_md_path' -DefaultValue $null
                skill_entrypoint = Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'skill_entrypoint' -DefaultValue $null
                dispatch_phase = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'dispatch_phase' -DefaultValue 'in_execution')
                parallelizable_in_root_xl = [bool](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'parallelizable_in_root_xl' -DefaultValue $false)
                skill_root = Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'skill_root' -DefaultValue $null
                bounded_role = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'bounded_role' -DefaultValue 'selected_skill')
                must_preserve_workflow = [bool](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'must_preserve_workflow' -DefaultValue $true)
                binding_profile = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'binding_profile' -DefaultValue 'selected_skill')
                lane_policy = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'lane_policy' -DefaultValue 'agent_module_handoff')
                write_scope = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'write_scope' -DefaultValue ('specialist:{0}' -f $skillId))
                review_mode = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'review_mode' -DefaultValue 'module_acceptance')
                execution_priority = [int](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'execution_priority' -DefaultValue 50)
                required_inputs = [object[]]@(Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'required_inputs' -DefaultValue @())
                expected_outputs = [object[]]@(Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'expected_outputs' -DefaultValue @())
                verification_expectation = [string](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'verification_expectation' -DefaultValue 'Verify the assigned module acceptance criteria before completion.')
                progressive_load_policy = [object[]]@(Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'progressive_load_policy' -DefaultValue @())
                destructive = [bool](Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'destructive' -DefaultValue $false)
                destructive_reason_codes = [object[]]@(Get-VibePropertySafe -InputObject $selectedRow -PropertyName 'destructive_reason_codes' -DefaultValue @())
            }
        ) | Out-Null
    }

    $resolvedRunId = if ([string]::IsNullOrWhiteSpace($RunId)) { $null } else { [string]$RunId }
    $resolvedTask = if ([string]::IsNullOrWhiteSpace($Task)) { $null } else { [string]$Task }
    $resolvedUnits = [object[]]@($units.ToArray())
    $resolvedUnitCount = @($resolvedUnits).Count
    $resolvedStatus = if ($resolvedUnitCount -eq 0) {
        'no_bound_skills'
    } else {
        'projected_from_agent_skill_organization'
    }
    $resolvedSource = if ($OrganizationProvided) { 'agent_skill_organization' } else { $null }

    return [pscustomobject]@{
        schema_version = 'runtime_module_assignments_v1'
        source = $resolvedSource
        run_id = $resolvedRunId
        task = $resolvedTask
        unit_count = $resolvedUnitCount
        status = $resolvedStatus
        units = $resolvedUnits
    }
}

function New-VibeModuleWorkPlan {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [object]$AgentSkillOrganization,
        [Parameter(Mandatory)] [string]$RequirementDocPath
    )

    $gapReasonByModuleId = @{}
    foreach ($uncoveredModule in @($AgentSkillOrganization.uncovered_modules)) {
        $gapReasonByModuleId[[string]$uncoveredModule.module_id] = [string]$uncoveredModule.reason
    }
    $uncoveredModuleIds = @($gapReasonByModuleId.Keys)
    $modules = @(
        @($AgentSkillOrganization.modules) | ForEach-Object {
            $moduleId = [string]$_.module_id
            [pscustomobject]@{
                module_id = $moduleId
                goal = [string]$_.goal
                required = [bool](Get-VibePropertySafe -InputObject $_ -PropertyName 'required' -DefaultValue $true)
                depends_on = [object[]]@(Get-VibePropertySafe -InputObject $_ -PropertyName 'depends_on' -DefaultValue @())
                execution_mode = [string]$_.execution_mode
                write_scope = [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'write_scope' -DefaultValue '')
                expected_outputs = [object[]]@(Get-VibePropertySafe -InputObject $_ -PropertyName 'expected_outputs' -DefaultValue @())
                verification = [object[]]@(Get-VibePropertySafe -InputObject $_ -PropertyName 'verification' -DefaultValue @())
                gap_reason = if ($gapReasonByModuleId.ContainsKey($moduleId)) { [string]$gapReasonByModuleId[$moduleId] } else { $null }
                acceptance_criteria = [object[]]@($_.acceptance_criteria)
            }
        }
    )
    $moduleById = @{}
    foreach ($module in @($modules)) {
        $moduleById[[string]$module.module_id] = $module
    }
    foreach ($module in @($modules)) {
        foreach ($dependencyId in @($module.depends_on)) {
            if (-not $moduleById.ContainsKey([string]$dependencyId)) {
                throw ('module `{0}` depends on unknown module `{1}`' -f [string]$module.module_id, [string]$dependencyId)
            }
        }
    }

    $moduleStages = @{}
    while ($moduleStages.Count -lt @($modules).Count) {
        $resolvedAny = $false
        foreach ($module in @($modules)) {
            $moduleId = [string]$module.module_id
            if ($moduleStages.ContainsKey($moduleId)) {
                continue
            }
            $dependencyIds = @($module.depends_on | ForEach-Object { [string]$_ })
            if (@($dependencyIds | Where-Object { -not $moduleStages.ContainsKey($_) }).Count -gt 0) {
                continue
            }
            $moduleStages[$moduleId] = if (@($dependencyIds).Count -eq 0) {
                1
            } else {
                1 + [int](@($dependencyIds | ForEach-Object { [int]$moduleStages[$_] } | Measure-Object -Maximum).Maximum)
            }
            $resolvedAny = $true
        }
        if (-not $resolvedAny) {
            throw 'module dependency graph contains a cycle'
        }
    }

    $workUnits = @(
        @($AgentSkillOrganization.selected_skills) | ForEach-Object {
            $selectedSkill = $_
            foreach ($moduleAssignment in @($selectedSkill.module_assignments)) {
                $moduleId = [string]$moduleAssignment.module_id
                $role = [string]$moduleAssignment.role
                [pscustomobject]@{
                    unit_id = ('{0}--{1}--{2}' -f [string]$moduleId, [string]$selectedSkill.skill_id, $role)
                    module_id = [string]$moduleId
                    skill_id = [string]$selectedSkill.skill_id
                    role = $role
                    responsibility = [string]$moduleAssignment.responsibility
                    write_scope = [string]$moduleAssignment.write_scope
                    depends_on_unit_ids = [object[]]@()
                    expected_outputs = [object[]]@($moduleAssignment.expected_outputs)
                    verification = [object[]]@($moduleAssignment.verification)
                }
            }
        }
        @($modules | Where-Object { [string]$_.execution_mode -eq 'agent_direct' } | ForEach-Object {
            [pscustomobject]@{
                unit_id = ('{0}--agent--owner' -f [string]$_.module_id)
                module_id = [string]$_.module_id
                skill_id = $null
                role = 'owner'
                responsibility = [string]$_.goal
                write_scope = [string]$_.write_scope
                depends_on_unit_ids = [object[]]@()
                expected_outputs = [object[]]@($_.expected_outputs)
                verification = [object[]]@($_.verification)
            }
        })
    )
    foreach ($workUnit in @($workUnits)) {
        $moduleId = [string]$workUnit.module_id
        $module = $moduleById[$moduleId]
        $dependencyUnitIds = @(
            foreach ($dependencyId in @($module.depends_on)) {
                @($workUnits | Where-Object { [string]$_.module_id -eq [string]$dependencyId } | ForEach-Object { [string]$_.unit_id })
            }
            if ([string]$workUnit.role -eq 'owner') {
                @($workUnits | Where-Object { [string]$_.module_id -eq $moduleId -and [string]$_.role -eq 'support' } | ForEach-Object { [string]$_.unit_id })
            } elseif ([string]$workUnit.role -eq 'verifier') {
                @($workUnits | Where-Object { [string]$_.module_id -eq $moduleId -and [string]$_.role -eq 'owner' } | ForEach-Object { [string]$_.unit_id })
            }
        ) | Sort-Object -Unique
        $workUnit.depends_on_unit_ids = [object[]]@($dependencyUnitIds)
    }

    $unitStages = @{}
    while ($unitStages.Count -lt @($workUnits).Count) {
        $resolvedAny = $false
        foreach ($workUnit in @($workUnits)) {
            $unitId = [string]$workUnit.unit_id
            if ($unitStages.ContainsKey($unitId)) {
                continue
            }
            $dependencyUnitIds = @($workUnit.depends_on_unit_ids | ForEach-Object { [string]$_ })
            if (@($dependencyUnitIds | Where-Object { -not $unitStages.ContainsKey($_) }).Count -gt 0) {
                continue
            }
            $stageOrder = if (@($dependencyUnitIds).Count -eq 0) {
                [int]$moduleStages[[string]$workUnit.module_id]
            } else {
                1 + [int](@($dependencyUnitIds | ForEach-Object { [int]$unitStages[$_] } | Measure-Object -Maximum).Maximum)
            }
            $unitStages[$unitId] = $stageOrder
            $workUnit | Add-Member -NotePropertyName stage_order -NotePropertyValue $stageOrder -Force
            $workUnit | Add-Member -NotePropertyName phase_id -NotePropertyValue ('module-stage-{0}' -f $stageOrder) -Force
            $resolvedAny = $true
        }
        if (-not $resolvedAny) {
            throw 'module work unit dependency graph contains a cycle or unknown unit'
        }
    }

    $requirementDigest = (Get-FileHash -LiteralPath $RequirementDocPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $organizationJson = $AgentSkillOrganization | ConvertTo-Json -Depth 100 -Compress
    $organizationBytes = [System.Text.Encoding]::UTF8.GetBytes($organizationJson)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $organizationDigest = ([System.BitConverter]::ToString($sha256.ComputeHash($organizationBytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }

    return [pscustomobject]@{
        schema_version = 'module_work_plan_v1'
        source_run_id = $RunId
        requirement_digest = $requirementDigest
        organization_digest = $organizationDigest
        workflow_level = [string]$AgentSkillOrganization.workflow_level
        modules = [object[]]$modules
        work_units = [object[]]$workUnits
    }
}

function ConvertTo-VibeComparableWriteScope {
    param(
        [Parameter(Mandatory)] [string]$WriteScope
    )

    $normalized = $WriteScope.Trim().Replace('\', '/')
    foreach ($suffix in @('/**', '/*')) {
        if ($normalized.EndsWith($suffix, [System.StringComparison]::Ordinal)) {
            $normalized = $normalized.Substring(0, $normalized.Length - $suffix.Length)
            break
        }
    }
    return $normalized.TrimEnd('/').ToLowerInvariant()
}

function Test-VibeWriteScopeConflict {
    param(
        [Parameter(Mandatory)] [string]$Left,
        [Parameter(Mandatory)] [string]$Right
    )

    $leftScope = ConvertTo-VibeComparableWriteScope -WriteScope $Left
    $rightScope = ConvertTo-VibeComparableWriteScope -WriteScope $Right
    if ($leftScope -ceq $rightScope) {
        return $true
    }
    if (-not ($leftScope.Contains('/') -and $rightScope.Contains('/'))) {
        return $false
    }
    return (
        $leftScope.StartsWith($rightScope + '/', [System.StringComparison]::Ordinal) -or
        $rightScope.StartsWith($leftScope + '/', [System.StringComparison]::Ordinal)
    )
}

function New-VibeModuleWorkWaves {
    param(
        [Parameter(Mandatory)] [object]$ModuleWorkPlan,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$Units
    )

    $waves = New-Object System.Collections.Generic.List[object]
    foreach ($stageOrder in @($ModuleWorkPlan.work_units | ForEach-Object { [int]$_.stage_order } | Sort-Object -Unique)) {
        $stageUnits = @($Units | Where-Object {
                $unitId = [string]$_.unit_id
                $plannedUnit = @($ModuleWorkPlan.work_units | Where-Object { [string]$_.unit_id -eq $unitId } | Select-Object -First 1)
                @($plannedUnit).Count -gt 0 -and [int]$plannedUnit[0].stage_order -eq [int]$stageOrder
            })
        $remainingUnits = @($stageUnits)
        $waveIndex = 0
        while ($remainingUnits.Count -gt 0) {
            if ([string]$ModuleWorkPlan.workflow_level -ne 'XL' -or $remainingUnits.Count -eq 1) {
                $unit = $remainingUnits[0]
                $waves.Add([pscustomobject]@{
                        wave_id = ('module-stage-{0}-{1}' -f $stageOrder, [string]$unit.unit_id)
                        execution_mode = 'sequential'
                        unit_ids = [object[]]@([string]$unit.unit_id)
                    }) | Out-Null
                $remainingUnits = @($remainingUnits | Select-Object -Skip 1)
                continue
            }

            $parallelUnits = New-Object System.Collections.Generic.List[object]
            foreach ($candidate in @($remainingUnits)) {
                if ($parallelUnits.Count -ge 2) {
                    break
                }
                $writeScopeConflict = @($parallelUnits | Where-Object {
                        Test-VibeWriteScopeConflict `
                            -Left ([string]$_.write_scope) `
                            -Right ([string]$candidate.write_scope)
                    }).Count -gt 0
                if (-not $writeScopeConflict) {
                    $parallelUnits.Add($candidate) | Out-Null
                }
            }
            if ($parallelUnits.Count -gt 1) {
                $waves.Add([pscustomobject]@{
                        wave_id = ('module-stage-{0}-parallel-{1}' -f $stageOrder, $waveIndex)
                        execution_mode = 'bounded_parallel'
                        unit_ids = [object[]]@($parallelUnits | ForEach-Object { [string]$_.unit_id })
                    }) | Out-Null
                $parallelUnitIds = @($parallelUnits | ForEach-Object { [string]$_.unit_id })
                $remainingUnits = @($remainingUnits | Where-Object { [string]$_.unit_id -notin $parallelUnitIds })
                $waveIndex++
                continue
            }

            $unit = $remainingUnits[0]
            $waves.Add([pscustomobject]@{
                    wave_id = ('module-stage-{0}-{1}' -f $stageOrder, [string]$unit.unit_id)
                    execution_mode = 'sequential'
                    unit_ids = [object[]]@([string]$unit.unit_id)
                }) | Out-Null
            $remainingUnits = @($remainingUnits | Select-Object -Skip 1)
        }
    }

    return [object[]]$waves.ToArray()
}

function New-VibeAgentExecutionHandoff {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [object]$ModuleWorkPlan,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ModulePlanDispatch,
        [Parameter(Mandatory)] [string]$ModuleExecutionPath,
        [Parameter(Mandatory)] [string]$WorkspaceRoot,
        [Parameter(Mandatory)] [string]$ArtifactRoot,
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $dispatchByUnitId = @{}
    foreach ($dispatch in @($ModulePlanDispatch)) {
        $workUnitId = [string](Get-VibePropertySafe -InputObject $dispatch -PropertyName 'work_unit_id' -DefaultValue '')
        if (-not [string]::IsNullOrWhiteSpace($workUnitId)) {
            $dispatchByUnitId[$workUnitId] = $dispatch
        }
    }

    $units = [object[]]@(
        foreach ($workUnit in @($ModuleWorkPlan.work_units)) {
            $unitId = [string]$workUnit.unit_id
            $dispatch = if ($dispatchByUnitId.ContainsKey($unitId)) { $dispatchByUnitId[$unitId] } else { $null }
            [pscustomobject]@{
                unit_id = $unitId
                module_id = [string]$workUnit.module_id
                skill_id = if ($null -eq $workUnit.skill_id) { $null } else { [string]$workUnit.skill_id }
                role = [string]$workUnit.role
                skill_entrypoint = if ($null -eq $dispatch) { $null } else { Get-VibePropertySafe -InputObject $dispatch -PropertyName 'skill_entrypoint' -DefaultValue $null }
                responsibility = [string]$workUnit.responsibility
                expected_outputs = [object[]]@($workUnit.expected_outputs)
                verification = [object[]]@($workUnit.verification)
                depends_on_unit_ids = [object[]]@($workUnit.depends_on_unit_ids)
                write_scope = [string]$workUnit.write_scope
            }
        }
    )
    $moduleWorkPlanDigest = (Get-FileHash -LiteralPath (Join-Path (Split-Path -Parent $ModuleExecutionPath) 'module-work-plan.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    $codeTaskTddEvidenceRequirements = [object[]]@(
        Get-VibePropertySafe -InputObject $ModuleWorkPlan -PropertyName 'code_task_tdd_evidence_requirements' -DefaultValue @()
    )
    $codeTaskTddExceptions = [object[]]@(
        Get-VibePropertySafe -InputObject $ModuleWorkPlan -PropertyName 'code_task_tdd_exceptions' -DefaultValue @()
    )
    $hasCodeTaskTddEvidenceContract = [bool](
        @($codeTaskTddEvidenceRequirements).Count -gt 0 -or
        @($codeTaskTddExceptions).Count -gt 0
    )
    $resultContractUnits = [object[]]@(
        foreach ($unit in @($units)) {
            [pscustomobject]@{
                unit_id = [string]$unit.unit_id
                module_id = [string]$unit.module_id
                skill_id = if ($null -eq $unit.skill_id) { $null } else { [string]$unit.skill_id }
                role = [string]$unit.role
                required_result_fields = [object[]]@(
                    'unit_id',
                    'module_id',
                    'skill_id',
                    'role',
                    'state',
                    'result_summary',
                    'evidence_paths',
                    'verification_results'
                )
            }
        }
    )
    $resultContractModules = [object[]]@(
        foreach ($module in @($ModuleWorkPlan.modules)) {
            [pscustomobject]@{
                module_id = [string]$module.module_id
                required = [bool]$module.required
                execution_mode = [string]$module.execution_mode
                gap_reason = if ($null -eq $module.gap_reason) { $null } else { [string]$module.gap_reason }
                acceptance_criteria = [object[]]@($module.acceptance_criteria)
                required_result_fields = [object[]]@(
                    'module_id',
                    'required',
                    'execution_mode',
                    'gap_reason',
                    'state',
                    'criterion_results'
                )
            }
        }
    )
    $submissionTemplate = [pscustomobject]@{
        schema_version = 'module_execution_v1'
        source_run_id = $RunId
        module_work_plan_digest = $moduleWorkPlanDigest
        units = [object[]]@(
            foreach ($unit in @($resultContractUnits)) {
                [pscustomobject]@{
                    unit_id = [string]$unit.unit_id
                    module_id = [string]$unit.module_id
                    skill_id = if ($null -eq $unit.skill_id) { $null } else { [string]$unit.skill_id }
                    role = [string]$unit.role
                    state = $null
                    result_summary = ''
                    evidence_paths = [object[]]@()
                    verification_results = [object[]]@()
                }
            }
        )
        modules = [object[]]@(
            foreach ($module in @($resultContractModules)) {
                [pscustomobject]@{
                    module_id = [string]$module.module_id
                    required = [bool]$module.required
                    execution_mode = [string]$module.execution_mode
                    gap_reason = if ($null -eq $module.gap_reason) { $null } else { [string]$module.gap_reason }
                    state = $null
                    criterion_results = [object[]]@(
                        foreach ($criterion in @($module.acceptance_criteria)) {
                            [pscustomobject]@{
                                criterion_id = [string]$criterion.criterion_id
                                state = $null
                                details = ''
                            }
                        }
                    )
                }
            }
        )
    }
    if ($hasCodeTaskTddEvidenceContract) {
        $submissionTemplate | Add-Member -NotePropertyName 'tdd_evidence' -NotePropertyValue ([pscustomobject]@{
                state = $null
                evidence_paths = [object[]]@()
                red_phase_evidence_paths = [object[]]@()
                green_phase_evidence_paths = [object[]]@()
                refactor_phase_evidence_paths = [object[]]@()
                covered_code_task_tdd_evidence_requirements = [object[]]@()
                covered_code_task_tdd_exceptions = [object[]]@()
                notes = ''
            })
    }
    $requiredTopLevelFields = [System.Collections.Generic.List[object]]::new()
    foreach ($field in @('schema_version', 'source_run_id', 'module_work_plan_digest', 'units', 'modules')) {
        $requiredTopLevelFields.Add($field) | Out-Null
    }
    if ($hasCodeTaskTddEvidenceContract) {
        $requiredTopLevelFields.Add('tdd_evidence') | Out-Null
    }
    $resultContract = [pscustomobject]@{
        schema_version = 'module_execution_v1'
        source_run_id = $RunId
        module_work_plan_digest = $moduleWorkPlanDigest
        required_top_level_fields = [object[]]$requiredTopLevelFields.ToArray()
        terminal_states = [object[]]@('completed', 'failed', 'blocked')
        criterion_terminal_states = [object[]]@('passing', 'failing', 'blocked')
        criterion_result_required_fields = [object[]]@('criterion_id', 'state')
        units = $resultContractUnits
        modules = $resultContractModules
        submission_template = $submissionTemplate
    }
    if ($hasCodeTaskTddEvidenceContract) {
        $resultContract | Add-Member -NotePropertyName 'tdd_evidence' -NotePropertyValue ([pscustomobject]@{
                terminal_states = [object[]]@('passing', 'failing', 'blocked')
                required_result_fields = [object[]]@(
                    'state',
                    'evidence_paths',
                    'red_phase_evidence_paths',
                    'green_phase_evidence_paths',
                    'refactor_phase_evidence_paths',
                    'covered_code_task_tdd_evidence_requirements',
                    'covered_code_task_tdd_exceptions',
                    'notes'
                )
                required_code_task_tdd_evidence_requirements = [object[]]@($codeTaskTddEvidenceRequirements)
                required_code_task_tdd_exceptions = [object[]]@($codeTaskTddExceptions)
            })
    }
    $waves = @(New-VibeModuleWorkWaves -ModuleWorkPlan $ModuleWorkPlan -Units @($units))

    return [pscustomobject]@{
        schema_version = 'agent_execution_handoff_v1'
        source_run_id = $RunId
        status = 'agent_action_required'
        control_owner = 'agent'
        workflow_level = [string]$ModuleWorkPlan.workflow_level
        module_execution_path = $ModuleExecutionPath
        result_contract = $resultContract
        return_command = 'py -3 -m vgo_cli.main canonical-entry --repo-root "{0}" --workspace-root "{1}" --artifact-root "{2}" --prompt "Continue after Agent module execution" --continue-from-run-id "{3}" --module-execution-json-file "{4}"' -f $RepoRoot, $WorkspaceRoot, $ArtifactRoot, $RunId, $ModuleExecutionPath
        waves = [object[]]$waves
        units = $units
    }
}

function New-VibeAgentExecutionHandoffBriefing {
    param(
        [Parameter(Mandatory)] [object]$Handoff
    )

    $lines = @(
        'The approved plan is ready for the current Agent to execute.',
        '- Continue in this Agent turn. Do not ask the user for another approval.',
        '- Vibe organizes modules and skills; the Agent executes the module work.',
        '- Read each listed `SKILL.md`, follow its workflow for the assigned module, and write the result to `module-execution.json`.',
        '- Use `result_contract` from `agent-execution-handoff.json` as the exact schema, plan digest, unit binding, module list, and terminal-state contract for that file.',
        '- Copy `result_contract.submission_template` into `module-execution.json`, preserve every frozen binding, and replace only the empty result fields.',
        '- Each criterion result must keep its frozen `criterion_id` and use `state` exactly as `passing`, `failing`, or `blocked`.',
        '- After every module reaches a terminal result, return through canonical `vibe` using the handoff command.',
        '- If canonical rejects the result before cleanup, correct the same file and reuse the same return command; do not create a second handoff.',
        ''
    )
    if (Test-VibeObjectHasProperty -InputObject $Handoff.result_contract -PropertyName 'tdd_evidence') {
        $lines += @(
            '- This code task also requires `tdd_evidence` inside the same `module-execution.json` file.',
            '- Fill its structured red/green evidence and frozen coverage fields before canonical return; do not create a separate `tdd-evidence.json` sidecar.',
            ''
        )
    }
    foreach ($unit in @($Handoff.units)) {
        $skillId = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'skill_id' -DefaultValue '')
        $entrypoint = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'skill_entrypoint' -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            $lines += ('- Complete module `{0}` directly in the current Agent.' -f [string]$unit.module_id)
        } else {
            $lines += ('- Use `{0}` for module `{1}`.' -f $skillId, [string]$unit.module_id)
            $lines += ('  Read: `{0}`' -f $entrypoint)
        }
        $lines += ('  Work: {0}' -f [string]$unit.responsibility)
        $lines += ('  Expected outputs: {0}' -f (@($unit.expected_outputs) -join '; '))
        $lines += ('  Verify: {0}' -f (@($unit.verification) -join '; '))
    }
    $lines += @(
        '',
        ('- Module result file: `{0}`' -f [string]$Handoff.module_execution_path),
        ('- Return to Vibe after the module work is terminal: `{0}`' -f [string]$Handoff.return_command)
    )

    return [pscustomobject]@{
        enabled = $true
        mode = 'agent_execution_handoff'
        status = 'agent_action_required'
        control_owner = 'agent'
        segment_count = 1
        segments = @(
            [pscustomobject]@{
                segment_id = 'agent_execution_handoff'
                stage = 'plan_execute'
                category = 'execution'
                truth_layer = 'module_execution'
                status = 'agent_action_required'
                gate_status = $null
                skill_count = @($Handoff.units | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.skill_id) }).Count
                skills = @($Handoff.units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
                rendered_text = (@($lines) -join "`n")
            }
        )
        rendered_text = (@($lines) -join "`n")
    }
}

function ConvertFrom-VibeHostDecisionJson {
    param(
        [AllowEmptyString()] [string]$HostDecisionJson = ''
    )

    if ([string]::IsNullOrWhiteSpace($HostDecisionJson)) {
        return $null
    }

    try {
        $parsed = ($HostDecisionJson | ConvertFrom-Json -ErrorAction Stop)
    } catch {
        throw "invalid JSON in -HostDecisionJson"
    }

    if (-not (Test-VibeStructuredObject -InputObject $parsed)) {
        throw "structured host decision must be a JSON object"
    }

    return $parsed
}

function Get-VibeHostContinuationContext {
    param(
        [AllowNull()] [object]$HostDecision = $null
    )

    if (
        $null -eq $HostDecision -or
        -not (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'continuation_context')
    ) {
        return $null
    }

    $context = Get-VibePropertySafe -InputObject $HostDecision -PropertyName 'continuation_context'
    if (-not (Test-VibeStructuredObject -InputObject $context)) {
        return $null
    }

    return $context
}

function Test-VibeStructuredBoundedReentryContext {
    param(
        [AllowNull()] [object]$ContinuationContext = $null
    )

    if (
        $null -eq $ContinuationContext -or
        -not (Test-VibeObjectHasProperty -InputObject $ContinuationContext -PropertyName 'structured_bounded_reentry')
    ) {
        return $false
    }

    return [bool]$ContinuationContext.structured_bounded_reentry
}

function Copy-VibeRecordObject {
    param(
        [Parameter(Mandatory)] [object]$InputObject
    )

    $copy = [pscustomobject]@{}
    if ($InputObject -is [System.Collections.IDictionary]) {
        foreach ($key in @($InputObject.Keys)) {
            $copy | Add-Member -NotePropertyName ([string]$key) -NotePropertyValue $InputObject[$key] -Force
        }
    } else {
        foreach ($property in @($InputObject.PSObject.Properties)) {
            $copy | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value -Force
        }
    }
    return $copy
}

function New-VibeRuntimeHostDecisionProjection {
    param(
        [AllowNull()] [object]$HostDecision = $null,
        [AllowNull()] [object]$PhaseDecomposition = $null
    )

    if ($null -eq $HostDecision) {
        return $null
    }

    $projection = Copy-VibeRecordObject -InputObject $HostDecision
    foreach ($propertyName in @(
        'approval_decision',
        'decision_action',
        'decision_kind',
        'continuation_context',
        'agent_skill_organization',
        'code_task_tdd_decision',
        'code_task_tdd',
        'tdd_decision',
        'code_task_tdd_mode',
        'revision_delta'
    )) {
        if (Test-VibeObjectHasProperty -InputObject $projection -PropertyName $propertyName) {
            [void]$projection.PSObject.Properties.Remove($propertyName)
        }
    }

    if ($null -ne $PhaseDecomposition) {
        $projection | Add-Member -NotePropertyName phase_decomposition -NotePropertyValue $PhaseDecomposition -Force
    }

    if (@($projection.PSObject.Properties).Count -eq 0) {
        return $null
    }

    return $projection
}

function Get-VibeNormalizedStringList {
    param(
        [AllowNull()] [object]$Values = $null
    )

    $result = New-Object System.Collections.ArrayList
    $seen = @{}
    foreach ($value in @($Values)) {
        $text = [string]$value
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }
        if ($seen.ContainsKey($text)) {
            continue
        }
        [void]$result.Add($text)
        $seen[$text] = $true
    }
    return [string[]]$result.ToArray()
}

function Assert-VibeTaskWriteScope {
    param(
        [Parameter(Mandatory)] [string]$WriteScope,
        [Parameter(Mandatory)] [string]$Context
    )

    $normalized = $WriteScope.Trim().Replace('\', '/').ToLowerInvariant()
    if (
        $normalized -match '(^|/)outputs/runtime/vibe-sessions(/|$)' -or
        $normalized -match '(^|/)module-execution\.json([#/]|$)'
    ) {
        throw ('{0} write_scope must describe task work, not canonical runtime artifacts' -f $Context)
    }
}

function Resolve-VibeAgentSkillOrganization {
    param(
        [AllowNull()] [object]$HostDecision = $null,
        [AllowNull()] [object]$InheritedOrganization = $null
    )

    $organization = if (
        $null -ne $HostDecision -and
        (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'agent_skill_organization')
    ) {
        Get-VibePropertySafe -InputObject $HostDecision -PropertyName 'agent_skill_organization'
    } else {
        $InheritedOrganization
    }
    if ($null -eq $organization) {
        return $null
    }
    if (-not (Test-VibeStructuredObject -InputObject $organization)) {
        throw 'agent_skill_organization must be a JSON object'
    }

    $schemaVersion = [string](Get-VibePropertySafe -InputObject $organization -PropertyName 'schema_version' -DefaultValue '')
    if ($schemaVersion -ne 'agent_skill_organization_v1') {
        throw 'agent_skill_organization.schema_version must be `agent_skill_organization_v1`'
    }
    $derivedBy = [string](Get-VibePropertySafe -InputObject $organization -PropertyName 'derived_by' -DefaultValue '')
    if ($derivedBy -ne 'agent') {
        throw 'agent_skill_organization.derived_by must be `agent`'
    }
    $workflowLevel = [string](Get-VibePropertySafe -InputObject $organization -PropertyName 'workflow_level' -DefaultValue '')
    if ($workflowLevel -notin @('L', 'XL')) {
        throw 'agent_skill_organization.workflow_level must be `L` or `XL`'
    }

    $rawModules = @($(if (Test-VibeObjectHasProperty -InputObject $organization -PropertyName 'modules') { $organization.modules } else { @() }))
    if (@($rawModules).Count -eq 0) {
        throw 'agent_skill_organization.modules must include at least one module'
    }
    $modules = New-Object System.Collections.Generic.List[object]
    $moduleIds = @{}
    foreach ($module in @($rawModules)) {
        if (-not (Test-VibeStructuredObject -InputObject $module)) {
            throw 'each agent_skill_organization module must be a JSON object'
        }
        $moduleId = [string](Get-VibePropertySafe -InputObject $module -PropertyName 'module_id' -DefaultValue '')
        $goal = [string](Get-VibePropertySafe -InputObject $module -PropertyName 'goal' -DefaultValue '')
        $executionMode = [string](Get-VibePropertySafe -InputObject $module -PropertyName 'execution_mode' -DefaultValue '')
        $moduleWriteScope = [string](Get-VibePropertySafe -InputObject $module -PropertyName 'write_scope' -DefaultValue '')
        $moduleExpectedOutputs = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $module -PropertyName 'expected_outputs' -DefaultValue @()))
        $moduleVerification = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $module -PropertyName 'verification' -DefaultValue @()))
        if ([string]::IsNullOrWhiteSpace($moduleId)) {
            throw 'each agent_skill_organization module must include module_id'
        }
        if ($moduleIds.ContainsKey($moduleId)) {
            throw ('agent_skill_organization contains duplicate module_id `{0}`' -f $moduleId)
        }
        if ([string]::IsNullOrWhiteSpace($goal)) {
            throw ('agent_skill_organization module `{0}` must include goal' -f $moduleId)
        }
        if (-not [string]::IsNullOrWhiteSpace($moduleWriteScope)) {
            Assert-VibeTaskWriteScope -WriteScope $moduleWriteScope -Context ('agent_skill_organization module `{0}`' -f $moduleId)
        }
        $acceptanceCriteria = [object[]]@(Get-VibePropertySafe -InputObject $module -PropertyName 'acceptance_criteria' -DefaultValue @())
        if (@($acceptanceCriteria).Count -eq 0) {
            throw ('agent_skill_organization module `{0}` must include at least one acceptance criterion' -f $moduleId)
        }
        $normalizedAcceptanceCriteria = New-Object System.Collections.Generic.List[object]
        $criterionIds = @{}
        foreach ($criterion in @($acceptanceCriteria)) {
            if (-not (Test-VibeStructuredObject -InputObject $criterion)) {
                throw ('agent_skill_organization module `{0}` acceptance_criteria items must be JSON objects' -f $moduleId)
            }
            $criterionId = [string](Get-VibePropertySafe -InputObject $criterion -PropertyName 'criterion_id' -DefaultValue '')
            $description = [string](Get-VibePropertySafe -InputObject $criterion -PropertyName 'description' -DefaultValue '')
            $verificationMode = [string](Get-VibePropertySafe -InputObject $criterion -PropertyName 'verification_mode' -DefaultValue '')
            if ([string]::IsNullOrWhiteSpace($criterionId)) {
                throw ('agent_skill_organization module `{0}` acceptance criterion must include criterion_id' -f $moduleId)
            }
            if ($criterionIds.ContainsKey($criterionId)) {
                throw ('agent_skill_organization module `{0}` contains duplicate acceptance criterion `{1}`' -f $moduleId, $criterionId)
            }
            if ([string]::IsNullOrWhiteSpace($description)) {
                throw ('agent_skill_organization module `{0}` acceptance criterion `{1}` must include description' -f $moduleId, $criterionId)
            }
            if ($description -match '(?i)(cleanup[-_ ]receipt|successful[-_ ]cleanup[-_ ](?:statement|status)|delivery[-_ ]acceptance[-_ ]report|completion[-_ ]language|completion[-_ ]wording|清理(?:回执|收据)|成功清理(?:声明|状态|表述)|交付验收报告|完成(?:语言|表述))') {
                throw ('post-return cleanup is not a valid module acceptance criterion; module `{0}` criterion `{1}` must be satisfiable before canonical module-result re-entry' -f $moduleId, $criterionId)
            }
            if ($verificationMode -notin @('automated', 'manual')) {
                throw ('agent_skill_organization module `{0}` acceptance criterion `{1}` verification_mode must be `automated` or `manual`' -f $moduleId, $criterionId)
            }
            $criterionIds[$criterionId] = $true
            $normalizedAcceptanceCriteria.Add([pscustomobject]@{
                    criterion_id = $criterionId
                    description = $description
                    verification_mode = $verificationMode
                }) | Out-Null
        }
        $moduleIds[$moduleId] = $true
        $modules.Add([pscustomobject]@{
                module_id = $moduleId
                goal = $goal
                candidate_skill_ids = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $module -PropertyName 'candidate_skill_ids') { $module.candidate_skill_ids } else { @() }))
                required = [bool](Get-VibePropertySafe -InputObject $module -PropertyName 'required' -DefaultValue $true)
                depends_on = [object[]]@(Get-VibePropertySafe -InputObject $module -PropertyName 'depends_on' -DefaultValue @())
                execution_mode = $executionMode
                write_scope = $moduleWriteScope
                expected_outputs = [object[]]@($moduleExpectedOutputs)
                verification = [object[]]@($moduleVerification)
                acceptance_criteria = @($normalizedAcceptanceCriteria.ToArray())
            }) | Out-Null
    }

    $selectedSkills = New-Object System.Collections.Generic.List[object]
    $selectedSkillIds = @{}
    foreach ($selectedSkill in @($(if (Test-VibeObjectHasProperty -InputObject $organization -PropertyName 'selected_skills') { $organization.selected_skills } else { @() }))) {
        if (-not (Test-VibeStructuredObject -InputObject $selectedSkill)) {
            throw 'each agent_skill_organization selected skill must be a JSON object'
        }
        $skillId = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'skill_id' -DefaultValue '')
        $responsibility = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'responsibility' -DefaultValue '')
        $reason = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'reason' -DefaultValue '')
        $assignedModuleIds = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $selectedSkill -PropertyName 'module_ids') { $selectedSkill.module_ids } else { @() }))
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            throw 'each agent_skill_organization selected skill must include skill_id'
        }
        if ($selectedSkillIds.ContainsKey($skillId)) {
            throw ('agent_skill_organization contains duplicate selected skill `{0}`' -f $skillId)
        }
        if ([string]::IsNullOrWhiteSpace($responsibility)) {
            throw ('agent_skill_organization selected skill `{0}` must include responsibility' -f $skillId)
        }
        if ([string]::IsNullOrWhiteSpace($reason)) {
            throw ('agent_skill_organization selected skill `{0}` must include reason' -f $skillId)
        }
        if (@($assignedModuleIds).Count -eq 0) {
            throw ('agent_skill_organization selected skill `{0}` must include module_ids' -f $skillId)
        }
        foreach ($moduleId in @($assignedModuleIds)) {
            if (-not $moduleIds.ContainsKey($moduleId)) {
                throw ('agent_skill_organization selected skill `{0}` references unknown module `{1}`' -f $skillId, $moduleId)
            }
            $moduleRecord = @($modules.ToArray() | Where-Object { [string]$_.module_id -eq $moduleId } | Select-Object -First 1)[0]
            if ($skillId -notin @($moduleRecord.candidate_skill_ids)) {
                throw ('agent_skill_organization selected skill `{0}` was not listed as a candidate for module `{1}`; use the directory name that directly contains the retained SKILL.md as skill_id, not the displayed or frontmatter name' -f $skillId, $moduleId)
            }
        }
        $normalizedModuleAssignments = New-Object System.Collections.Generic.List[object]
        $rawModuleAssignments = @($(if (Test-VibeObjectHasProperty -InputObject $selectedSkill -PropertyName 'module_assignments') { $selectedSkill.module_assignments } else { @() }))
        if (@($rawModuleAssignments).Count -eq 0) {
            if (@($assignedModuleIds).Count -gt 1) {
                throw ('agent_skill_organization selected skill `{0}` must include one module_assignments entry per module when assigned to multiple modules' -f $skillId)
            }
            $singleModuleId = [string]$assignedModuleIds[0]
            $singleRole = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'role' -DefaultValue 'owner')
            if ($singleRole -notin @('owner', 'support', 'verifier')) {
                throw ('agent_skill_organization selected skill `{0}` role must be `owner`, `support`, or `verifier`' -f $skillId)
            }
            $singleModuleRecord = @($modules.ToArray() | Where-Object { [string]$_.module_id -eq $singleModuleId } | Select-Object -First 1)[0]
            $singleWriteScope = [string]$(if (Test-VibeObjectHasProperty -InputObject $selectedSkill -PropertyName 'write_scope') { Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'write_scope' } else { $singleModuleRecord.write_scope })
            if ([string]::IsNullOrWhiteSpace($singleWriteScope)) {
                $singleWriteScope = 'module:{0}' -f $singleModuleId
            }
            Assert-VibeTaskWriteScope -WriteScope $singleWriteScope -Context ('agent_skill_organization selected skill `{0}`' -f $skillId)
            $singleExpectedOutputs = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $selectedSkill -PropertyName 'expected_outputs') { Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'expected_outputs' } else { $singleModuleRecord.expected_outputs }))
            if (@($singleExpectedOutputs).Count -eq 0) {
                $singleExpectedOutputs = @($responsibility)
            }
            $singleVerification = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $selectedSkill -PropertyName 'verification') { Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'verification' } else { $singleModuleRecord.verification }))
            if (@($singleVerification).Count -eq 0) {
                $singleVerification = @('Verify the module acceptance criteria.')
            }
            $normalizedModuleAssignments.Add([pscustomobject]@{
                    module_id = $singleModuleId
                    role = $singleRole
                    responsibility = $responsibility
                    write_scope = $singleWriteScope
                    expected_outputs = [object[]]@($singleExpectedOutputs)
                    verification = [object[]]@($singleVerification)
                }) | Out-Null
        } else {
            $assignmentModuleIds = @{}
            foreach ($moduleAssignment in @($rawModuleAssignments)) {
                if (-not (Test-VibeStructuredObject -InputObject $moduleAssignment)) {
                    throw ('agent_skill_organization selected skill `{0}` module_assignments entries must be JSON objects' -f $skillId)
                }
                $assignmentModuleId = [string](Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'module_id' -DefaultValue '')
                $assignmentRole = [string](Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'role' -DefaultValue '')
                $assignmentResponsibility = [string](Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'responsibility' -DefaultValue '')
                $assignmentWriteScope = [string](Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'write_scope' -DefaultValue '')
                $assignmentExpectedOutputs = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'expected_outputs' -DefaultValue @()))
                $assignmentVerification = @(Get-VibeNormalizedStringList -Values (Get-VibePropertySafe -InputObject $moduleAssignment -PropertyName 'verification' -DefaultValue @()))
                if ($assignmentModuleId -notin @($assignedModuleIds)) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment references undeclared module `{1}`' -f $skillId, $assignmentModuleId)
                }
                if ($assignmentModuleIds.ContainsKey($assignmentModuleId)) {
                    throw ('agent_skill_organization selected skill `{0}` contains duplicate module assignment `{1}`' -f $skillId, $assignmentModuleId)
                }
                if ($assignmentRole -notin @('owner', 'support', 'verifier')) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment `{1}` role must be `owner`, `support`, or `verifier`' -f $skillId, $assignmentModuleId)
                }
                if ([string]::IsNullOrWhiteSpace($assignmentResponsibility)) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment `{1}` must include responsibility' -f $skillId, $assignmentModuleId)
                }
                if ([string]::IsNullOrWhiteSpace($assignmentWriteScope)) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment `{1}` must include write_scope' -f $skillId, $assignmentModuleId)
                }
                Assert-VibeTaskWriteScope -WriteScope $assignmentWriteScope -Context ('agent_skill_organization selected skill `{0}` module assignment `{1}`' -f $skillId, $assignmentModuleId)
                if (@($assignmentExpectedOutputs).Count -eq 0) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment `{1}` must include expected_outputs' -f $skillId, $assignmentModuleId)
                }
                if (@($assignmentVerification).Count -eq 0) {
                    throw ('agent_skill_organization selected skill `{0}` module assignment `{1}` must include verification' -f $skillId, $assignmentModuleId)
                }
                $assignmentModuleIds[$assignmentModuleId] = $true
                $normalizedModuleAssignments.Add([pscustomobject]@{
                        module_id = $assignmentModuleId
                        role = $assignmentRole
                        responsibility = $assignmentResponsibility
                        write_scope = $assignmentWriteScope
                        expected_outputs = [object[]]@($assignmentExpectedOutputs)
                        verification = [object[]]@($assignmentVerification)
                    }) | Out-Null
            }
            foreach ($moduleId in @($assignedModuleIds)) {
                if (-not $assignmentModuleIds.ContainsKey([string]$moduleId)) {
                    throw ('agent_skill_organization selected skill `{0}` is missing module assignment `{1}`' -f $skillId, [string]$moduleId)
                }
            }
        }
        $selectedSkillIds[$skillId] = $true
        $selectedSkills.Add([pscustomobject]@{
                skill_id = $skillId
                module_ids = @($assignedModuleIds)
                role = [string](Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'role' -DefaultValue 'owner')
                responsibility = $responsibility
                reason = $reason
                write_scope = Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'write_scope' -DefaultValue $null
                expected_outputs = [object[]]@(Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'expected_outputs' -DefaultValue @($responsibility))
                verification = [object[]]@(Get-VibePropertySafe -InputObject $selectedSkill -PropertyName 'verification' -DefaultValue @('Verify the module acceptance criteria.'))
                module_assignments = [object[]]@($normalizedModuleAssignments.ToArray())
            }) | Out-Null
    }

    $uncoveredModules = New-Object System.Collections.Generic.List[object]
    $uncoveredModuleIds = @{}
    foreach ($uncovered in @($(if (Test-VibeObjectHasProperty -InputObject $organization -PropertyName 'uncovered_modules') { $organization.uncovered_modules } else { @() }))) {
        if (-not (Test-VibeStructuredObject -InputObject $uncovered)) {
            throw 'each agent_skill_organization uncovered module must be a JSON object'
        }
        $moduleId = [string](Get-VibePropertySafe -InputObject $uncovered -PropertyName 'module_id' -DefaultValue '')
        $reason = [string](Get-VibePropertySafe -InputObject $uncovered -PropertyName 'reason' -DefaultValue '')
        if (-not $moduleIds.ContainsKey($moduleId)) {
            throw ('agent_skill_organization uncovered module references unknown module `{0}`' -f $moduleId)
        }
        if ($uncoveredModuleIds.ContainsKey($moduleId)) {
            throw ('agent_skill_organization contains duplicate uncovered module `{0}`' -f $moduleId)
        }
        if ([string]::IsNullOrWhiteSpace($reason)) {
            throw ('agent_skill_organization uncovered module `{0}` must include reason' -f $moduleId)
        }
        $uncoveredModuleIds[$moduleId] = $true
        $uncoveredModules.Add([pscustomobject]@{
                module_id = $moduleId
                reason = $reason
            }) | Out-Null
    }

    foreach ($module in @($modules.ToArray())) {
        $moduleId = [string]$module.module_id
        $declaredExecutionMode = [string]$module.execution_mode
        if ([string]::IsNullOrWhiteSpace($declaredExecutionMode)) {
            throw ('agent_skill_organization module `{0}` must include execution_mode' -f $moduleId)
        }
        if ($declaredExecutionMode -notin @('skill_assigned', 'agent_direct', 'blocked_gap')) {
            throw ('agent_skill_organization module `{0}` has unsupported execution_mode `{1}`' -f $moduleId, $declaredExecutionMode)
        }
        $covered = @($selectedSkills.ToArray() | Where-Object { $moduleId -in @($_.module_ids) }).Count -gt 0
        $declaredUncovered = $uncoveredModuleIds.ContainsKey($moduleId)
        if ($covered -and $declaredUncovered) {
            throw ('agent_skill_organization module `{0}` cannot be both selected and uncovered' -f $moduleId)
        }
        if ($declaredExecutionMode -eq 'agent_direct' -and ($covered -or $declaredUncovered)) {
            throw ('agent_skill_organization agent_direct module `{0}` cannot select or declare a skill gap' -f $moduleId)
        }
        if ($declaredExecutionMode -eq 'agent_direct') {
            if ([string]::IsNullOrWhiteSpace([string]$module.write_scope)) {
                throw ('agent_skill_organization agent_direct module `{0}` must include write_scope' -f $moduleId)
            }
            if (@($module.expected_outputs).Count -eq 0) {
                throw ('agent_skill_organization agent_direct module `{0}` must include expected_outputs' -f $moduleId)
            }
            if (@($module.verification).Count -eq 0) {
                throw ('agent_skill_organization agent_direct module `{0}` must include verification' -f $moduleId)
            }
        }
        if ($declaredExecutionMode -eq 'skill_assigned' -and -not $covered) {
            throw ('agent_skill_organization module `{0}` declares skill_assigned but is not covered by a selected skill' -f $moduleId)
        }
        if ($declaredExecutionMode -eq 'blocked_gap' -and -not $declaredUncovered) {
            throw ('agent_skill_organization module `{0}` declares blocked_gap but is not declared uncovered' -f $moduleId)
        }
    }

    $workflowLevelContract = Get-VibePropertySafe -InputObject $organization -PropertyName 'workflow_level_contract' -DefaultValue $null
    if (-not (Test-VibeStructuredObject -InputObject $workflowLevelContract)) {
        throw 'agent_skill_organization.workflow_level_contract must be a JSON object'
    }
    $lDescription = [string](Get-VibePropertySafe -InputObject $workflowLevelContract -PropertyName 'L' -DefaultValue '')
    $xlDescription = [string](Get-VibePropertySafe -InputObject $workflowLevelContract -PropertyName 'XL' -DefaultValue '')
    if ([string]::IsNullOrWhiteSpace($lDescription) -or [string]::IsNullOrWhiteSpace($xlDescription)) {
        throw 'agent_skill_organization.workflow_level_contract must describe both L and XL'
    }

    return [pscustomobject]@{
        schema_version = 'agent_skill_organization_v1'
        derived_by = 'agent'
        workflow_level = $workflowLevel
        modules = @($modules.ToArray())
        selected_skills = @($selectedSkills.ToArray())
        uncovered_modules = @($uncoveredModules.ToArray())
        workflow_level_contract = [pscustomobject]@{
            L = $lDescription
            XL = $xlDescription
        }
    }
}

function Get-VibeExecutionPhaseContract {
    param(
        [AllowNull()] [object]$Policy = $null
    )

    $phasePolicy = $null
    if ($null -ne $Policy -and (Test-VibeObjectHasProperty -InputObject $Policy -PropertyName 'host_phase_decomposition_contract')) {
        $phasePolicy = $Policy.host_phase_decomposition_contract
    }

    $stageTypeDefaults = [ordered]@{
        discovery = [pscustomobject]@{
            dispatch_phase = 'pre_execution'
            default_stage_label = 'Discovery'
            default_execution_priority = 10
        }
        implementation = [pscustomobject]@{
            dispatch_phase = 'in_execution'
            default_stage_label = 'Implementation'
            default_execution_priority = 50
        }
        deliverable = [pscustomobject]@{
            dispatch_phase = 'post_execution'
            default_stage_label = 'Deliverable'
            default_execution_priority = 70
        }
        verification = [pscustomobject]@{
            dispatch_phase = 'verification'
            default_stage_label = 'Verification'
            default_execution_priority = 90
        }
    }

    $stageTypeLookup = [ordered]@{}
    $stageTypePolicy = if ($null -ne $phasePolicy -and (Test-VibeObjectHasProperty -InputObject $phasePolicy -PropertyName 'stage_types')) { $phasePolicy.stage_types } else { $null }
    foreach ($stageTypeName in @($stageTypeDefaults.Keys)) {
        $defaults = $stageTypeDefaults[$stageTypeName]
        $override = if ($null -ne $stageTypePolicy -and (Test-VibeObjectHasProperty -InputObject $stageTypePolicy -PropertyName $stageTypeName)) { $stageTypePolicy.$stageTypeName } else { $null }
        $stageTypeLookup[$stageTypeName] = [pscustomobject]@{
            stage_type = [string]$stageTypeName
            dispatch_phase = if ($null -ne $override -and (Test-VibeObjectHasProperty -InputObject $override -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$override.dispatch_phase)) { [string]$override.dispatch_phase } else { [string]$defaults.dispatch_phase }
            default_stage_label = if ($null -ne $override -and (Test-VibeObjectHasProperty -InputObject $override -PropertyName 'default_stage_label') -and -not [string]::IsNullOrWhiteSpace([string]$override.default_stage_label)) { [string]$override.default_stage_label } else { [string]$defaults.default_stage_label }
            default_execution_priority = if ($null -ne $override -and (Test-VibeObjectHasProperty -InputObject $override -PropertyName 'default_execution_priority') -and $null -ne $override.default_execution_priority) { [int]$override.default_execution_priority } else { [int]$defaults.default_execution_priority }
        }
    }

    $defaultStageType = if ($null -ne $phasePolicy -and (Test-VibeObjectHasProperty -InputObject $phasePolicy -PropertyName 'default_stage_type') -and -not [string]::IsNullOrWhiteSpace([string]$phasePolicy.default_stage_type)) {
        [string]$phasePolicy.default_stage_type
    } else {
        'implementation'
    }
    if (-not $stageTypeLookup.Contains($defaultStageType)) {
        $defaultStageType = 'implementation'
    }

    return [pscustomobject]@{
        enabled = if ($null -ne $phasePolicy -and (Test-VibeObjectHasProperty -InputObject $phasePolicy -PropertyName 'enabled')) { [bool]$phasePolicy.enabled } else { $true }
        max_phase_count = if ($null -ne $phasePolicy -and (Test-VibeObjectHasProperty -InputObject $phasePolicy -PropertyName 'max_phase_count') -and $null -ne $phasePolicy.max_phase_count) { [int]$phasePolicy.max_phase_count } else { 6 }
        default_stage_type = [string]$defaultStageType
        stage_types = [pscustomobject]$stageTypeLookup
    }
}

function Get-VibeExecutionPhaseTypeDefinition {
    param(
        [AllowEmptyString()] [string]$StageType = '',
        [AllowNull()] [object]$Policy = $null
    )

    $contract = Get-VibeExecutionPhaseContract -Policy $Policy
    $requestedType = [string]$StageType
    if ([string]::IsNullOrWhiteSpace($requestedType)) {
        $requestedType = [string]$contract.default_stage_type
    }
    $requestedType = $requestedType.Trim().ToLowerInvariant()
    if (-not (Test-VibeObjectHasProperty -InputObject $contract.stage_types -PropertyName $requestedType)) {
        $requestedType = [string]$contract.default_stage_type
    }

    return $contract.stage_types.$requestedType
}

function Resolve-VibeHostPhaseDecomposition {
    param(
        [AllowNull()] [object]$HostDecision = $null,
        [Parameter(Mandatory)] [string]$Task,
        [AllowNull()] [object]$Policy = $null
    )

    $contract = Get-VibeExecutionPhaseContract -Policy $Policy
    if (-not [bool]$contract.enabled) {
        return $null
    }
    if ($null -eq $HostDecision -or -not (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'phase_decomposition')) {
        return $null
    }

    $phaseDecomposition = Get-VibePropertySafe -InputObject $HostDecision -PropertyName 'phase_decomposition'
    if ($null -eq $phaseDecomposition) {
        return $null
    }
    if (-not (Test-VibeStructuredObject -InputObject $phaseDecomposition)) {
        throw 'structured host phase decomposition must be a JSON object'
    }
    if (-not (Test-VibeObjectHasProperty -InputObject $phaseDecomposition -PropertyName 'phases')) {
        throw 'structured host phase decomposition must include phases'
    }

    $rawPhases = @(Get-VibePropertySafe -InputObject $phaseDecomposition -PropertyName 'phases')
    if (@($rawPhases).Count -eq 0) {
        throw 'structured host phase decomposition must include at least one phase'
    }
    if (@($rawPhases).Count -gt [int]$contract.max_phase_count) {
        throw ('structured host phase decomposition exceeds max_phase_count `{0}`' -f [int]$contract.max_phase_count)
    }

    $normalized = @()
    $seenPhaseIds = @{}
    $phaseIndex = 0
    foreach ($phase in @($rawPhases)) {
        $phaseIndex += 1
        if (-not (Test-VibeStructuredObject -InputObject $phase)) {
            throw 'each execution phase must be a JSON object'
        }

        $typeDef = Get-VibeExecutionPhaseTypeDefinition `
            -StageType $(if (Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'stage_type') { [string]$phase.stage_type } else { '' }) `
            -Policy $Policy
        $phaseId = if ((Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'phase_id') -and -not [string]::IsNullOrWhiteSpace([string]$phase.phase_id)) {
            [string]$phase.phase_id
        } else {
            'phase-{0}' -f $phaseIndex
        }
        if ($seenPhaseIds.ContainsKey($phaseId)) {
            throw ('structured host phase decomposition contains duplicate phase_id `{0}`' -f $phaseId)
        }
        $seenPhaseIds[$phaseId] = $true

        $stageOrder = if ((Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'stage_order') -and $null -ne $phase.stage_order) {
            [int]$phase.stage_order
        } else {
            [int]($phaseIndex * 10)
        }
        $stageLabel = if ((Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'stage_label') -and -not [string]::IsNullOrWhiteSpace([string]$phase.stage_label)) {
            [string]$phase.stage_label
        } else {
            [string]$typeDef.default_stage_label
        }
        $goal = if ((Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'goal') -and -not [string]::IsNullOrWhiteSpace([string]$phase.goal)) {
            [string]$phase.goal
        } else {
            [string]$Task
        }

        $normalized += [pscustomobject]@{
            phase_id = $phaseId
            stage_order = [int]$stageOrder
            stage_type = [string]$typeDef.stage_type
            stage_label = $stageLabel
            goal = $goal
            depends_on = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'depends_on') { $phase.depends_on } else { @() }))
            artifacts_in = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'artifacts_in') { $phase.artifacts_in } else { @() }))
            artifacts_out = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'artifacts_out') { $phase.artifacts_out } else { @() }))
            acceptance_checks = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $phase -PropertyName 'acceptance_checks') { $phase.acceptance_checks } else { @() }))
            dispatch_phase = [string]$typeDef.dispatch_phase
            default_execution_priority = [int]$typeDef.default_execution_priority
        }
    }

    $orderedPhases = @(
        $normalized |
            Sort-Object `
                @{ Expression = { [int]$_.stage_order } }, `
                @{ Expression = { [string]$_.phase_id } }
    )

    return [pscustomobject]@{
        protocol_version = if ((Test-VibeObjectHasProperty -InputObject $phaseDecomposition -PropertyName 'protocol_version') -and -not [string]::IsNullOrWhiteSpace([string]$phaseDecomposition.protocol_version)) { [string]$phaseDecomposition.protocol_version } else { 'v1' }
        derived_by = if ((Test-VibeObjectHasProperty -InputObject $phaseDecomposition -PropertyName 'derived_by') -and -not [string]::IsNullOrWhiteSpace([string]$phaseDecomposition.derived_by)) { [string]$phaseDecomposition.derived_by } else { 'host' }
        mode = if ((Test-VibeObjectHasProperty -InputObject $phaseDecomposition -PropertyName 'mode') -and -not [string]::IsNullOrWhiteSpace([string]$phaseDecomposition.mode)) { [string]$phaseDecomposition.mode } elseif (@($orderedPhases).Count -gt 1) { 'multi_phase' } else { 'single_phase' }
        phase_count = @($orderedPhases).Count
        phases = @($orderedPhases)
    }
}

function Get-VibeRuntimeInputPacketFromSessionRunId {
    param(
        [AllowEmptyString()] [string]$ArtifactRoot = '',
        [AllowEmptyString()] [string]$SourceRunId = ''
    )

    if ([string]::IsNullOrWhiteSpace($ArtifactRoot) -or [string]::IsNullOrWhiteSpace($SourceRunId)) {
        return $null
    }

    $candidatePath = Join-Path (Join-Path (Join-Path (Join-Path $ArtifactRoot 'outputs') 'runtime') 'vibe-sessions') (Join-Path $SourceRunId 'runtime-input-packet.json')
    if (-not (Test-Path -LiteralPath $candidatePath)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $candidatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Normalize-VibeCodeTaskTddMode {
    param(
        [AllowNull()] [object]$Value = $null
    )

    $mode = ([string]$Value).Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($mode)) {
        return ''
    }

    switch -Regex ($mode) {
        '^(required|require|enabled|enable|on|true|yes|tdd|required_code_task_tdd)$' { return 'required' }
        '^(not_applicable|not-applicable|na|n/a|none|off|false|no|disabled|disable|skip|skipped)$' { return 'not_applicable' }
        '^(exception_approved|exception-approved|exception|exempt|exemption|approved_exception)$' { return 'exception_approved' }
        default { return '' }
    }
}

function Get-VibeCodeTaskTddDecisionFromHostDecision {
    param(
        [AllowNull()] [object]$HostDecision = $null
    )

    if ($null -eq $HostDecision) {
        return $null
    }

    $rawDecision = $null
    foreach ($propertyName in @('code_task_tdd_decision', 'code_task_tdd', 'tdd_decision')) {
        if (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName $propertyName) {
            $rawDecision = Get-VibePropertySafe -InputObject $HostDecision -PropertyName $propertyName
            break
        }
    }
    if ($null -eq $rawDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'code_task_tdd_mode')) {
        $rawDecision = [pscustomobject]@{
            mode = [string](Get-VibePropertySafe -InputObject $HostDecision -PropertyName 'code_task_tdd_mode')
        }
    }
    if ($null -eq $rawDecision) {
        return $null
    }

    if (-not (Test-VibeStructuredObject -InputObject $rawDecision)) {
        $rawDecision = [pscustomobject]@{
            mode = [string]$rawDecision
        }
    }

    $mode = Normalize-VibeCodeTaskTddMode -Value $(if (Test-VibeObjectHasProperty -InputObject $rawDecision -PropertyName 'mode') { Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'mode' } elseif (Test-VibeObjectHasProperty -InputObject $rawDecision -PropertyName 'tdd_mode') { Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'tdd_mode' } else { '' })
    if ([string]::IsNullOrWhiteSpace($mode)) {
        throw 'structured host code_task_tdd_decision must declare mode as required, not_applicable, or exception_approved'
    }

    return [pscustomobject]@{
        mode = [string]$mode
        source = 'host_decision'
        reason = if ((Test-VibeObjectHasProperty -InputObject $rawDecision -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string](Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'reason'))) { [string](Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'reason') } else { 'Host supplied an explicit structured code-task TDD decision.' }
        exception = if ((Test-VibeObjectHasProperty -InputObject $rawDecision -PropertyName 'exception') -and -not [string]::IsNullOrWhiteSpace([string](Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'exception'))) { [string](Get-VibePropertySafe -InputObject $rawDecision -PropertyName 'exception') } else { $null }
    }
}

function Resolve-VibeCodeTaskTddDecision {
    param(
        [AllowNull()] [object]$HostDecision = $null,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$Deliverable = '',
        [AllowEmptyString()] [string]$TaskType = '',
        [bool]$HeuristicRequiresTdd = $false,
        [bool]$DocumentArtifactBaseline = $false
    )

    $hostDecisionProjection = Get-VibeCodeTaskTddDecisionFromHostDecision -HostDecision $HostDecision
    if ($null -ne $hostDecisionProjection) {
        return $hostDecisionProjection
    }

    if ($DocumentArtifactBaseline) {
        return [pscustomobject]@{
            mode = 'not_applicable'
            source = 'runtime_inference'
            reason = 'Document-artifact work uses artifact review requirements instead of code-task TDD evidence.'
            exception = $null
        }
    }

    $normalizedTaskType = ([string]$TaskType).Trim().ToLowerInvariant()
    $requiresTdd = [bool]$HeuristicRequiresTdd -and $normalizedTaskType -in @('coding', 'debug', '')
    if ($requiresTdd) {
        return [pscustomobject]@{
            mode = 'required'
            source = 'runtime_inference'
            reason = 'The task includes implementation or defect-correction intent that requires code-task TDD evidence.'
            exception = $null
        }
    }

    return [pscustomobject]@{
        mode = 'not_applicable'
        source = 'runtime_inference'
        reason = 'No host decision or runtime inference required code-task TDD evidence for this task.'
        exception = $null
    }
}

function Get-VibeExecutionPhaseBindingForRecord {
    param(
        [AllowNull()] [object]$PhaseDecomposition = $null,
        [AllowNull()] [object]$Record = $null
    )

    if (
        $null -eq $PhaseDecomposition -or
        -not (Test-VibeObjectHasProperty -InputObject $PhaseDecomposition -PropertyName 'phases') -or
        @($PhaseDecomposition.phases).Count -eq 0 -or
        $null -eq $Record
    ) {
        return $null
    }

    $phaseId = if ((Test-VibeObjectHasProperty -InputObject $Record -PropertyName 'phase_id') -and -not [string]::IsNullOrWhiteSpace([string]$Record.phase_id)) {
        [string]$Record.phase_id
    } else {
        $null
    }
    if (-not [string]::IsNullOrWhiteSpace($phaseId)) {
        foreach ($phase in @($PhaseDecomposition.phases)) {
            if ([string]$phase.phase_id -eq $phaseId) {
                return $phase
            }
        }
    }

    $dispatchPhase = if ((Test-VibeObjectHasProperty -InputObject $Record -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$Record.dispatch_phase)) {
        [string]$Record.dispatch_phase
    } else {
        'in_execution'
    }
    $matchingPhases = @($PhaseDecomposition.phases | Where-Object { [string]$_.dispatch_phase -eq $dispatchPhase })
    if (@($matchingPhases).Count -eq 0) {
        $matchingPhases = @($PhaseDecomposition.phases)
    }
    if (@($matchingPhases).Count -eq 0) {
        return $null
    }

    return @(
        $matchingPhases |
            Sort-Object `
                @{ Expression = { [int]$_.stage_order } }, `
                @{ Expression = { [string]$_.phase_id } }
    )[0]
}

function Add-VibeExecutionPhaseMetadataToRecords {
    param(
        [AllowNull()] [object[]]$Records = @(),
        [AllowNull()] [object]$PhaseDecomposition = $null
    )

    if ($null -eq $PhaseDecomposition -or @($Records).Count -eq 0) {
        return @($Records)
    }

    $annotated = @()
    foreach ($record in @($Records)) {
        if ($null -eq $record) {
            continue
        }

        $copy = Copy-VibeRecordObject -InputObject $record
        $phase = Get-VibeExecutionPhaseBindingForRecord -PhaseDecomposition $PhaseDecomposition -Record $copy
        if ($null -ne $phase) {
            $copy | Add-Member -NotePropertyName phase_id -NotePropertyValue ([string]$phase.phase_id) -Force
            $copy | Add-Member -NotePropertyName stage_order -NotePropertyValue ([int]$phase.stage_order) -Force
            $copy | Add-Member -NotePropertyName stage_type -NotePropertyValue ([string]$phase.stage_type) -Force
            $copy | Add-Member -NotePropertyName stage_label -NotePropertyValue ([string]$phase.stage_label) -Force
            if (-not ((Test-VibeObjectHasProperty -InputObject $copy -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$copy.dispatch_phase))) {
                $copy | Add-Member -NotePropertyName dispatch_phase -NotePropertyValue ([string]$phase.dispatch_phase) -Force
            }
        }
        $annotated += $copy
    }

    return @($annotated)
}

function Get-VibeExecutionPhaseMarkdownLines {
    param(
        [AllowNull()] [object]$PhaseDecomposition = $null
    )

    if (
        $null -eq $PhaseDecomposition -or
        -not (Test-VibeObjectHasProperty -InputObject $PhaseDecomposition -PropertyName 'phases') -or
        @($PhaseDecomposition.phases).Count -eq 0
    ) {
        return @()
    }

    $lines = @(
        '- Host execution-phase decomposition remains subordinate to the single governed requirement and plan surfaces.',
        '- These phases guide module ordering inside `plan_execute`; they do not create a second runtime, second plan, or second approval ladder.'
    )
    foreach ($phase in @($PhaseDecomposition.phases)) {
        $goal = if ([string]::IsNullOrWhiteSpace([string]$phase.goal)) { 'No explicit phase goal recorded.' } else { [string]$phase.goal }
        $dependsOn = if (@($phase.depends_on).Count -gt 0) { [string]::Join(', ', @($phase.depends_on)) } else { 'none' }
        $artifactsIn = if (@($phase.artifacts_in).Count -gt 0) { [string]::Join(', ', @($phase.artifacts_in)) } else { 'none' }
        $artifactsOut = if (@($phase.artifacts_out).Count -gt 0) { [string]::Join(', ', @($phase.artifacts_out)) } else { 'none' }
        $acceptanceChecks = if (@($phase.acceptance_checks).Count -gt 0) { [string]::Join(', ', @($phase.acceptance_checks)) } else { 'none' }
        $lines += @(
            ('- Phase `{0}` [{1} -> {2}] order `{3}`: {4}' -f [string]$phase.phase_id, [string]$phase.stage_type, [string]$phase.dispatch_phase, [int]$phase.stage_order, [string]$phase.stage_label),
            ('  Goal: {0}' -f $goal),
            ('  Depends on: {0}' -f $dependsOn),
            ('  Artifacts in: {0}' -f $artifactsIn),
            ('  Artifacts out: {0}' -f $artifactsOut),
            ('  Acceptance checks: {0}' -f $acceptanceChecks)
        )
    }

    return @($lines)
}

function New-VibeHostAdapterIdentityProjection {
    param(
        [AllowNull()] [object]$HostAdapter,
        [AllowEmptyString()] [string]$RequestedPropertyName = 'requested_id',
        [AllowEmptyString()] [string]$EffectivePropertyName = 'id',
        [AllowEmptyString()] [string]$FallbackHostId = ''
    )

    $requestedHostId = if ([string]::IsNullOrWhiteSpace($FallbackHostId)) { $null } else { [string]$FallbackHostId }
    $effectiveHostId = if ([string]::IsNullOrWhiteSpace($FallbackHostId)) { $null } else { [string]$FallbackHostId }

    if ($null -ne $HostAdapter) {
        $requestedFields = @($RequestedPropertyName, 'requested_id', 'requested_host_id', 'id', 'effective_host_id') | Select-Object -Unique
        $effectiveFields = @($EffectivePropertyName, 'id', 'effective_host_id', 'requested_id', 'requested_host_id') | Select-Object -Unique

        foreach ($field in @($requestedFields)) {
            if (Test-VibeObjectHasProperty -InputObject $HostAdapter -PropertyName $field) {
                $candidateRequestedHostId = [string]$HostAdapter.$field
                if (-not [string]::IsNullOrWhiteSpace($candidateRequestedHostId)) {
                    $requestedHostId = $candidateRequestedHostId
                    break
                }
            }
        }
        foreach ($field in @($effectiveFields)) {
            if (Test-VibeObjectHasProperty -InputObject $HostAdapter -PropertyName $field) {
                $candidateEffectiveHostId = [string]$HostAdapter.$field
                if (-not [string]::IsNullOrWhiteSpace($candidateEffectiveHostId)) {
                    $effectiveHostId = $candidateEffectiveHostId
                    break
                }
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($requestedHostId) -and -not [string]::IsNullOrWhiteSpace($effectiveHostId)) {
        $requestedHostId = [string]$effectiveHostId
    }
    if ([string]::IsNullOrWhiteSpace($effectiveHostId) -and -not [string]::IsNullOrWhiteSpace($requestedHostId)) {
        $effectiveHostId = [string]$requestedHostId
    }

    return [pscustomobject]@{
        requested_id = if ([string]::IsNullOrWhiteSpace($requestedHostId)) { $null } else { [string]$requestedHostId }
        id = if ([string]::IsNullOrWhiteSpace($effectiveHostId)) { $null } else { [string]$effectiveHostId }
        requested_host_id = if ([string]::IsNullOrWhiteSpace($requestedHostId)) { $null } else { [string]$requestedHostId }
        effective_host_id = if ([string]::IsNullOrWhiteSpace($effectiveHostId)) { $null } else { [string]$effectiveHostId }
    }
}

function New-VibeRuntimeHostAdapterProjection {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$FallbackHostId = '',
        [AllowEmptyString()] [string]$TargetRoot = ''
    )

    $hostAdapter = Get-VibePropertySafe -InputObject $Runtime -PropertyName 'host_adapter'
    $identity = New-VibeHostAdapterIdentityProjection `
        -HostAdapter $hostAdapter `
        -RequestedPropertyName 'requested_id' `
        -EffectivePropertyName 'id' `
        -FallbackHostId $FallbackHostId

    $hostSettingsPath = $null
    if ($Runtime -and (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_settings')) {
        $hostSettings = $Runtime.host_settings
        if ($null -ne $hostSettings -and (Test-VibeObjectHasProperty -InputObject $hostSettings -PropertyName 'path') -and -not [string]::IsNullOrWhiteSpace($hostSettings.path)) {
            $hostSettingsPath = [string]$hostSettings.path
        }
    }

    $hostClosurePath = $null
    if ($Runtime -and (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_closure')) {
        $hostClosure = $Runtime.host_closure
        if ($null -ne $hostClosure -and (Test-VibeObjectHasProperty -InputObject $hostClosure -PropertyName 'path') -and -not [string]::IsNullOrWhiteSpace($hostClosure.path)) {
            $hostClosurePath = [string]$hostClosure.path
        }
    }

    return [pscustomobject]@{
        requested_id = $identity.requested_id
        id = $identity.id
        requested_host_id = $identity.requested_host_id
        effective_host_id = $identity.effective_host_id
        status = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'status')) { [string]$Runtime.host_adapter.status } else { $null }
        install_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'install_mode')) { [string]$Runtime.host_adapter.install_mode } else { $null }
        check_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'check_mode')) { [string]$Runtime.host_adapter.check_mode } else { $null }
        bootstrap_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'bootstrap_mode')) { [string]$Runtime.host_adapter.bootstrap_mode } else { $null }
        target_root = if ([string]::IsNullOrWhiteSpace($TargetRoot)) { $null } else { [string]$TargetRoot }
        host_settings_path = $hostSettingsPath
        closure_path = $hostClosurePath
    }
}

function Get-VibeRuntimePacketHostAdapterAlignment {
    param(
        [AllowNull()] [object]$RuntimeInputPacket
    )

    return New-VibeHostAdapterIdentityProjection `
        -HostAdapter $(if ($null -ne $RuntimeInputPacket -and $RuntimeInputPacket.PSObject.Properties.Name -contains 'host_adapter') { $RuntimeInputPacket.host_adapter } else { $null }) `
        -RequestedPropertyName 'requested_host_id' `
        -EffectivePropertyName 'effective_host_id'
}

function New-VibeRouteRuntimeAlignmentProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket,
        [AllowEmptyString()] [string]$DefaultRuntimeSkill = 'vibe'
    )

    $hostAdapterIdentity = Get-VibeRuntimePacketHostAdapterAlignment -RuntimeInputPacket $RuntimeInputPacket

    $authorityFlags = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'authority_flags'
    $selectedTaskSkillIds = @(Get-VibeSelectedTaskSkillIds -RuntimeInputPacket $RuntimeInputPacket)
    $runtimeSelectedSkill = Get-VibeNestedPropertySafe -InputObject $authorityFlags -PropertyPath @('explicit_runtime_skill') -DefaultValue $DefaultRuntimeSkill

    return [pscustomobject]@{
        bound_skill_ids = @($selectedTaskSkillIds)
        runtime_selected_skill = $runtimeSelectedSkill
        requested_host_adapter_id = $hostAdapterIdentity.requested_host_id
        effective_host_adapter_id = $hostAdapterIdentity.effective_host_id
    }
}

function Get-VibeHostSettingsRecord {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    $targetRoot = Resolve-VibeHostTargetRoot -HostAdapter $HostAdapter
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return $null
    }

    $settingsPath = Join-Path $targetRoot '.vibeskills\host-settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) {
        return $null
    }

    try {
        $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }

    return [pscustomobject]@{
        target_root = $targetRoot
        path = $settingsPath
        data = $settings
    }
}

function Get-VibeHostClosureRecord {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    $targetRoot = Resolve-VibeHostTargetRoot -HostAdapter $HostAdapter
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return $null
    }

    $closurePath = Join-Path $targetRoot '.vibeskills\host-closure.json'
    if (-not (Test-Path -LiteralPath $closurePath -PathType Leaf)) {
        return $null
    }

    try {
        $closure = Get-Content -LiteralPath $closurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }

    return [pscustomobject]@{
        target_root = $targetRoot
        path = $closurePath
        data = $closure
    }
}

function Get-VibeRuntimeContext {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    $governanceContext = Get-VgoGovernanceContext -ScriptPath $ScriptPath -EnforceExecutionContext
    $repoRoot = $governanceContext.repoRoot
    $hostAdapter = Get-VibeHostAdapterEntry -RepoRoot $repoRoot

    return [pscustomobject]@{
        repo_root = $repoRoot
        governance_context = $governanceContext
        host_adapter = $hostAdapter
        host_settings = Get-VibeHostSettingsRecord -HostAdapter $hostAdapter
        host_closure = Get-VibeHostClosureRecord -HostAdapter $hostAdapter
        runtime_contract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_modes = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-modes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_input_packet_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        skill_execution_safety_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\skill-execution-safety-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        cleanup_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        proof_class_registry = Get-Content -LiteralPath (Join-Path $repoRoot 'config\proof-class-registry.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_governance = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-governance.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_tier_router = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-tier-router.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_runtime_v3_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-runtime-v3-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_stage_activation_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-stage-activation-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_retrieval_budget_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-retrieval-budget-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_disclosure_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-disclosure-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_ingest_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-ingest-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        workspace_memory_plane = Get-Content -LiteralPath (Join-Path $repoRoot 'config\workspace-memory-plane.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_backend_adapters = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-backend-adapters.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    }
}

function Get-VibeWorkspaceRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$WorkspaceRoot = ''
    )

    if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
        return [System.IO.Path]::GetFullPath($RepoRoot)
    }
    if ([System.IO.Path]::IsPathRooted($WorkspaceRoot)) {
        return [System.IO.Path]::GetFullPath($WorkspaceRoot)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $WorkspaceRoot))
}

function Get-VibeWorkspaceSidecarRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$WorkspaceRoot = ''
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceRoot -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot) '.vibeskills'))
}

function Get-VibeWorkspaceProjectDescriptorPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$WorkspaceRoot = ''
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot) 'project.json'))
}

function Get-VibeWorkspaceMemoryPlaneContract {
    return [pscustomobject]@{
        identity_scope = 'workspace'
        driver_contract = 'workspace_shared_memory_v1'
        logical_owners = @('state_store', 'serena', 'ruflo', 'cognee')
    }
}

function Test-VibeWritableDirectory {
    param(
        [AllowEmptyString()] [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    $candidate = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $candidate)) {
        return $false
    }

    try {
        $item = Get-Item -LiteralPath $candidate -ErrorAction Stop
        $directory = if ($item.PSIsContainer) { [string]$item.FullName } else { [string]$item.Directory.FullName }
        if ([string]::IsNullOrWhiteSpace($directory)) {
            return $false
        }

        $probePath = Join-Path $directory ('.vibe-write-probe-{0}.tmp' -f [System.Guid]::NewGuid().ToString('N'))
        [System.IO.File]::WriteAllText($probePath, '')
        Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

function Resolve-VibeGovernedArtifactRootFromPath {
    param(
        [AllowEmptyString()] [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $resolvedPath)) {
        return $null
    }

    $container = if (Test-Path -LiteralPath $resolvedPath -PathType Container) {
        $resolvedPath
    } else {
        Split-Path -Parent $resolvedPath
    }
    if ([string]::IsNullOrWhiteSpace($container)) {
        return $null
    }

    $leafName = [System.IO.Path]::GetFileName($container)
    $parent = Split-Path -Parent $container
    if (($leafName -in @('requirements', 'plans')) -and ([System.IO.Path]::GetFileName($parent) -eq 'docs')) {
        return [System.IO.Path]::GetFullPath((Split-Path -Parent $parent))
    }

    return [System.IO.Path]::GetFullPath($container)
}

function Get-VibeHostSidecarRoot {
    param(
        [AllowNull()] [object]$Runtime,
        [AllowEmptyString()] [string]$RouterTargetRoot = ''
    )

    $hostTargetRoot = if ([string]::IsNullOrWhiteSpace($RouterTargetRoot)) { $null } else { [System.IO.Path]::GetFullPath($RouterTargetRoot) }

    if ([string]::IsNullOrWhiteSpace($hostTargetRoot) -and $null -ne $Runtime) {
        if (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_settings') -and
            $null -ne $Runtime.host_settings -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_settings -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_settings.target_root)
        ) {
            $hostTargetRoot = [System.IO.Path]::GetFullPath([string]$Runtime.host_settings.target_root)
        } elseif (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_closure') -and
            $null -ne $Runtime.host_closure -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_closure -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_closure.target_root)
        ) {
            $hostTargetRoot = [System.IO.Path]::GetFullPath([string]$Runtime.host_closure.target_root)
        } elseif (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_adapter') -and
            $null -ne $Runtime.host_adapter
        ) {
            $resolvedTargetRoot = Resolve-VibeHostTargetRoot -HostAdapter $Runtime.host_adapter
            if (-not [string]::IsNullOrWhiteSpace($resolvedTargetRoot)) {
                $hostTargetRoot = [System.IO.Path]::GetFullPath($resolvedTargetRoot)
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($hostTargetRoot)) {
        return $null
    }

    return [System.IO.Path]::GetFullPath((Join-Path $hostTargetRoot '.vibeskills'))
}

function New-VibeWorkspaceArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$WorkspaceRoot = '',
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = '',
        [AllowEmptyString()] [string]$RouterTargetRoot = ''
    )

    $workspaceRoot = Get-VibeWorkspaceRoot -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot
    $workspaceSidecarRoot = Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot -WorkspaceRoot $workspaceRoot
    $projectDescriptorPath = Get-VibeWorkspaceProjectDescriptorPath -RepoRoot $RepoRoot -WorkspaceRoot $workspaceRoot
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract
    $useDefaultWorkspaceSidecar = [string]::IsNullOrWhiteSpace($ArtifactRoot)

    if ($useDefaultWorkspaceSidecar) {
        $resolvedArtifactRoot = $workspaceSidecarRoot
        $artifactRootSource = 'workspace_sidecar_default'
    } elseif ([System.IO.Path]::IsPathRooted($ArtifactRoot)) {
        $resolvedArtifactRoot = [System.IO.Path]::GetFullPath($ArtifactRoot)
        $artifactRootSource = 'explicit_override'
    } else {
        $resolvedArtifactRoot = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $ArtifactRoot))
        $artifactRootSource = 'explicit_override'
    }

    return [pscustomobject]@{
        workspace_root = $workspaceRoot
        workspace_sidecar_root = $workspaceSidecarRoot
        project_descriptor_path = $projectDescriptorPath
        artifact_root = $resolvedArtifactRoot
        artifact_root_source = $artifactRootSource
        default_workspace_sidecar_artifact_root = [bool]$useDefaultWorkspaceSidecar
        host_sidecar_root = Get-VibeHostSidecarRoot -Runtime $Runtime -RouterTargetRoot $RouterTargetRoot
        workspace_memory_identity_root = $projectDescriptorPath
        workspace_memory_identity_scope = [string]$memoryPlane.identity_scope
        workspace_memory_driver_contract = [string]$memoryPlane.driver_contract
        workspace_memory_logical_owners = [string[]]@($memoryPlane.logical_owners)
    }
}

function Initialize-VibeWorkspaceProjectDescriptor {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$WorkspaceRoot = '',
        [AllowNull()] [object]$Runtime = $null
    )

    $storage = New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot -Runtime $Runtime
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract
    $descriptorPath = [string]$storage.project_descriptor_path
    $descriptor = [pscustomobject]@{
        schema_version = 1
        brand = 'vibeskills'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        workspace_root = [string]$storage.workspace_root
        workspace_sidecar_root = [string]$storage.workspace_sidecar_root
        project_descriptor_path = [string]$storage.project_descriptor_path
        default_artifact_root = [string]$storage.workspace_sidecar_root
        relative_runtime_contract = [pscustomobject]@{
            requirement_root = 'docs/requirements'
            execution_plan_root = 'docs/plans'
            session_root = 'outputs/runtime/vibe-sessions'
        }
        memory_plane = [pscustomobject]@{
            identity_root = [string]$storage.project_descriptor_path
            identity_scope = [string]$memoryPlane.identity_scope
            driver_contract = [string]$memoryPlane.driver_contract
            logical_owners = [string[]]@($memoryPlane.logical_owners)
        }
        host_sidecar_root = if ([string]::IsNullOrWhiteSpace([string]$storage.host_sidecar_root)) { $null } else { [string]$storage.host_sidecar_root }
    }

    Write-VibeJsonArtifact -Path $descriptorPath -Value $descriptor
    return $descriptorPath
}

function New-VibeRunId {
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $suffix = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "$timestamp-$suffix"
}

function Resolve-VibeRuntimeMode {
    param(
        [AllowEmptyString()] [string]$Mode,
        [AllowEmptyString()] [string]$DefaultMode = 'interactive_governed'
    )

    if ([string]::IsNullOrWhiteSpace($Mode)) {
        return $DefaultMode
    }

    $normalized = $Mode.Trim().ToLowerInvariant()
    if ($normalized -ne 'interactive_governed') {
        throw "Unsupported vibe runtime mode: $Mode"
    }

    return 'interactive_governed'
}

function Resolve-VibeGovernanceScope {
    param(
        [AllowEmptyString()] [string]$GovernanceScope,
        [AllowEmptyString()] [string]$DefaultScope = 'root'
    )

    if ([string]::IsNullOrWhiteSpace($GovernanceScope)) {
        return $DefaultScope
    }

    $normalized = $GovernanceScope.Trim().ToLowerInvariant()
    if ($normalized -notin @('root', 'child')) {
        throw "Unsupported governance scope: $GovernanceScope"
    }

    return $normalized
}

function Get-VibeHierarchyState {
    param(
        [Parameter(Mandatory)] [AllowEmptyString()] [string]$GovernanceScope,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$RootRunId = '',
        [AllowEmptyString()] [string]$ParentRunId = '',
        [AllowEmptyString()] [string]$ParentUnitId = '',
        [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
        [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [Parameter(Mandatory)] [object]$HierarchyContract
    )

    $scope = Resolve-VibeGovernanceScope -GovernanceScope $GovernanceScope -DefaultScope ([string]$HierarchyContract.default_governance_scope)
    $authoritySource = if ($scope -eq 'child') {
        $HierarchyContract.child_authority_flags
    } else {
        $HierarchyContract.root_authority_flags
    }

    $resolvedRootRunId = if ($scope -eq 'root') {
        $RunId
    } elseif (-not [string]::IsNullOrWhiteSpace($RootRunId)) {
        $RootRunId
    } elseif (-not [string]::IsNullOrWhiteSpace($ParentRunId)) {
        $ParentRunId
    } else {
        $RunId
    }

    $resolvedParentRunId = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($ParentRunId)) {
        $ParentRunId
    } else {
        $null
    }

    return [pscustomobject]@{
        governance_scope = $scope
        root_run_id = $resolvedRootRunId
        parent_run_id = $resolvedParentRunId
        parent_unit_id = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($ParentUnitId)) { $ParentUnitId } else { $null }
        inherited_requirement_doc_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($InheritedRequirementDocPath)) { [System.IO.Path]::GetFullPath($InheritedRequirementDocPath) } else { $null }
        inherited_execution_plan_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($InheritedExecutionPlanPath)) { [System.IO.Path]::GetFullPath($InheritedExecutionPlanPath) } else { $null }
        delegation_envelope_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($DelegationEnvelopePath)) { [System.IO.Path]::GetFullPath($DelegationEnvelopePath) } else { $null }
        allow_requirement_freeze = [bool]$authoritySource.allow_requirement_freeze
        allow_plan_freeze = [bool]$authoritySource.allow_plan_freeze
        allow_global_dispatch = [bool]$authoritySource.allow_global_dispatch
        allow_completion_claim = [bool]$authoritySource.allow_completion_claim
    }
}

function New-VibeHierarchyProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState,
        [switch]$IncludeGovernanceScope
    )

    $projection = [ordered]@{}
    if ($IncludeGovernanceScope) {
        $projection.governance_scope = [string]$HierarchyState.governance_scope
    }
    $projection.root_run_id = [string]$HierarchyState.root_run_id
    $projection.parent_run_id = if ($null -eq $HierarchyState.parent_run_id) { $null } else { [string]$HierarchyState.parent_run_id }
    $projection.parent_unit_id = if ($null -eq $HierarchyState.parent_unit_id) { $null } else { [string]$HierarchyState.parent_unit_id }
    $projection.inherited_requirement_doc_path = if ($null -eq $HierarchyState.inherited_requirement_doc_path) { $null } else { [string]$HierarchyState.inherited_requirement_doc_path }
    $projection.inherited_execution_plan_path = if ($null -eq $HierarchyState.inherited_execution_plan_path) { $null } else { [string]$HierarchyState.inherited_execution_plan_path }
    $projection.delegation_envelope_path = if ((Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'delegation_envelope_path') -and $null -ne $HierarchyState.delegation_envelope_path) { [string]$HierarchyState.delegation_envelope_path } else { $null }
    return [pscustomobject]$projection
}

function New-VibeAuthorityCapabilityProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState
    )

    return [pscustomobject]@{
        allow_requirement_freeze = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_requirement_freeze') { [bool]$HierarchyState.allow_requirement_freeze } else { $false }
        allow_plan_freeze = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_plan_freeze') { [bool]$HierarchyState.allow_plan_freeze } else { $false }
        allow_global_dispatch = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_global_dispatch') { [bool]$HierarchyState.allow_global_dispatch } else { $false }
        allow_completion_claim = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_completion_claim') { [bool]$HierarchyState.allow_completion_claim } else { $false }
    }
}

function New-VibeRuntimePacketAuthorityFlagsProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState,
        [AllowEmptyString()] [string]$RuntimeEntry = 'vibe',
        [AllowEmptyString()] [string]$ExplicitRuntimeSkill = 'vibe',
        [AllowEmptyString()] [string]$RouterTruthLevel = '',
        [bool]$ShadowOnly = $false,
        [bool]$NonAuthoritative = $false
    )

    $capabilities = New-VibeAuthorityCapabilityProjection -HierarchyState $HierarchyState

    return [pscustomobject]@{
        runtime_entry = if ([string]::IsNullOrWhiteSpace($RuntimeEntry)) { $null } else { [string]$RuntimeEntry }
        explicit_runtime_skill = if ([string]::IsNullOrWhiteSpace($ExplicitRuntimeSkill)) { $null } else { [string]$ExplicitRuntimeSkill }
        router_truth_level = if ([string]::IsNullOrWhiteSpace($RouterTruthLevel)) { $null } else { [string]$RouterTruthLevel }
        shadow_only = [bool]$ShadowOnly
        non_authoritative = [bool]$NonAuthoritative
        allow_requirement_freeze = [bool]$capabilities.allow_requirement_freeze
        allow_plan_freeze = [bool]$capabilities.allow_plan_freeze
        allow_global_dispatch = [bool]$capabilities.allow_global_dispatch
        allow_completion_claim = [bool]$capabilities.allow_completion_claim
    }
}

function Get-VibeModuleExecutionPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return Join-Path $SessionRoot 'module-execution.json'
}

function New-VibeRuntimeInputPacketProjection {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$InternalGrade,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [object]$HierarchyProjection,
        [Parameter(Mandatory)] [object]$AuthorityFlagsProjection,
        [AllowNull()] [object]$StorageProjection = $null,
        [Parameter(Mandatory)] [object]$RouteResult,
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$TaskType = '',
        [AllowNull()] [string]$RequestedSkill = $null,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = '',
        [AllowEmptyString()] [string]$RequestedGradeFloor = '',
        [AllowEmptyString()] [string]$RouterHostId = '',
        [AllowEmptyString()] [string]$RouterTargetRoot = '',
        [bool]$Unattended = $false,
        [AllowEmptyString()] [string]$RouterScriptPath = '',
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = 'vibe',
        [AllowNull()] [object]$ExecutionPhaseDecomposition = $null,
        [AllowNull()] [object]$CodeTaskTddDecision = $null,
        [AllowNull()] [object]$HostDecision = $null,
        [AllowNull()] [object[]]$StageAssistantHints = @(),
        [Parameter(Mandatory)] [ValidateNotNull()] [object]$SkillSearchGuide,
        [AllowNull()] [object]$AgentSkillOrganization = $null,
        [AllowNull()] [object[]]$AgentSkillRecommendations = @(),
        [AllowNull()] [object]$SkillRouting = $null,
        [Parameter(Mandatory)] [object]$Policy
    )

    $candidateFocus = Get-VibePropertySafe -InputObject $RouteResult -PropertyName 'candidate_focus'
    $candidateFocusSkill = if ($null -ne $candidateFocus) { [string]$candidateFocus.skill } else { $null }

    $customAdmission = if (
        $RouteResult.PSObject.Properties.Name -contains 'custom_admission' -and
        $null -ne $RouteResult.custom_admission
    ) {
        [pscustomobject]@{
            status = [string]$RouteResult.custom_admission.status
            target_root = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'target_root') { [string]$RouteResult.custom_admission.target_root } else { $null }
        }
    } else {
        $null
    }
    $continuationContext = Get-VibeHostContinuationContext -HostDecision $HostDecision
    $hostReentryAction = if (
        $null -ne $continuationContext -and
        (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'reentry_action') -and
        -not [string]::IsNullOrWhiteSpace([string]$continuationContext.reentry_action)
    ) {
        [string]$continuationContext.reentry_action
    } else {
        $null
    }
    $hostRevisionTargetStage = if (
        $null -ne $continuationContext -and
        (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'revision_target_stage') -and
        -not [string]::IsNullOrWhiteSpace([string]$continuationContext.revision_target_stage)
    ) {
        [string]$continuationContext.revision_target_stage
    } else {
        $null
    }
    $hostRevisionDelta = if (
        $null -ne $continuationContext -and
        (Test-VibeObjectHasProperty -InputObject $continuationContext -PropertyName 'revision_delta')
    ) {
        @(Get-VibeNormalizedStringList -Values $continuationContext.revision_delta)
    } else {
        @()
    }

    $effectiveSkillRouting = if ($null -ne $SkillRouting) {
        $SkillRouting
    } else {
        [pscustomobject]@{
            schema_version = 'simplified_skill_routing_v1'
            candidates = @()
            rejected = @()
        }
    }
    $moduleAssignments = New-VibeRuntimeModuleAssignmentsProjection `
        -Task $Task `
        -RunId $RunId `
        -SelectedSkillRecords $(if ($null -ne $AgentSkillOrganization) { @($AgentSkillRecommendations) } else { @() }) `
        -OrganizationProvided ($null -ne $AgentSkillOrganization)
    $packetSkillRouting = [pscustomobject]@{
        schema_version = [string](Get-VibePropertySafe -InputObject $effectiveSkillRouting -PropertyName 'schema_version' -DefaultValue 'simplified_skill_routing_v1')
        candidates = [object[]]@(Get-VibePropertySafe -InputObject $effectiveSkillRouting -PropertyName 'candidates' -DefaultValue @())
        rejected = [object[]]@(Get-VibePropertySafe -InputObject $effectiveSkillRouting -PropertyName 'rejected' -DefaultValue @())
    }

    $baseFields = [pscustomobject]@{
        stage = 'runtime_input_freeze'
        run_id = $RunId
        governance_scope = Get-VibeNestedPropertySafe -InputObject $HierarchyState -PropertyPath @('governance_scope') -DefaultValue ''
        task = $Task
        entry_intent_id = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { $null } else { [string]$EntryIntentId }
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { [string]$RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { [string]$RequestedGradeFloor }
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        runtime_mode = $Mode
        internal_grade = $InternalGrade
        module_assignments = $moduleAssignments
        host_adapter = (New-VibeRuntimeHostAdapterProjection -Runtime $Runtime -FallbackHostId $RouterHostId -TargetRoot $RouterTargetRoot)
        hierarchy = $HierarchyProjection
        authority_flags = $AuthorityFlagsProjection
        provenance = [pscustomobject]@{
            source_of_truth = 'vibe_runtime_with_agent_led_skill_search'
            freeze_before_requirement_doc = [bool]$Policy.freeze_before_requirement_doc
            proof_class = 'structure'
        }
        custom_admission = $customAdmission
        continuation_context = if ($null -ne $continuationContext) { $continuationContext } else { $null }
        host_decision = New-VibeRuntimeHostDecisionProjection -HostDecision $HostDecision -PhaseDecomposition $ExecutionPhaseDecomposition
        code_task_tdd_decision = $CodeTaskTddDecision
        skill_search_guide = $SkillSearchGuide
        agent_skill_organization = if ($null -ne $AgentSkillOrganization) { $AgentSkillOrganization } else { $null }
        canonical_router = [pscustomobject]@{
            role = 'compatibility_candidate_audit'
            prompt = $Task
            host_id = if ([string]::IsNullOrWhiteSpace($RouterHostId)) { $null } else { [string]$RouterHostId }
            target_root = if ([string]::IsNullOrWhiteSpace($RouterTargetRoot)) { $null } else { [string]$RouterTargetRoot }
            unattended = [bool]$Unattended
            host_decision_applied = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [bool]$RouteResult.structured_host_route_decision.applied } else { $false }
            host_decision_kind = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.decision_kind } else { $null }
            host_decision_action = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.decision_action } else { $null }
            route_script_path = if ([string]::IsNullOrWhiteSpace($RouterScriptPath)) { $null } else { [string]$RouterScriptPath }
        }
        route_snapshot = [pscustomobject]@{
            task_type = if ([string]::IsNullOrWhiteSpace($TaskType)) { $null } else { [string]$TaskType }
            route_mode = [string]$RouteResult.route_mode
        }
        skill_routing = $packetSkillRouting
        storage = $StorageProjection
        divergence_shadow = [pscustomobject]@{
            explicit_runtime_override_applied = [bool](-not [string]::IsNullOrWhiteSpace($RuntimeSelectedSkill))
            explicit_runtime_override_reason = 'governed_runtime_entry'
            governance_scope_mismatch = $false
        }
    }

    $truthRepoRoot = if (
        (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'repo_root') -and
        -not [string]::IsNullOrWhiteSpace([string]$Runtime.repo_root)
    ) {
        [string]$Runtime.repo_root
    } else {
        Resolve-VgoRepoRoot -StartPath $PSScriptRoot
    }

    return New-VibePythonRuntimeTruthProjection `
        -RepoRoot $truthRepoRoot `
        -RunId $RunId `
        -Task $Task `
        -ModuleAssignments $moduleAssignments `
        -BaseFields $baseFields `
        -SkillRouting $packetSkillRouting
}

function New-VibeExecutionAuthorityProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState
    )

    $capabilities = New-VibeAuthorityCapabilityProjection -HierarchyState $HierarchyState

    return [pscustomobject]@{
        canonical_requirement_write_allowed = [bool]$capabilities.allow_requirement_freeze
        canonical_plan_write_allowed = [bool]$capabilities.allow_plan_freeze
        global_dispatch_allowed = [bool]$capabilities.allow_global_dispatch
        completion_claim_allowed = [bool]$capabilities.allow_completion_claim
    }
}

function Get-VibeGovernedRuntimeStageOrder {
    return @(
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup'
    )
}

function Resolve-VibeRequestedStageStop {
    param(
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    $stageOrder = @(Get-VibeGovernedRuntimeStageOrder)
    if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        return [string]$stageOrder[$stageOrder.Count - 1]
    }

    $normalized = [string]$RequestedStageStop
    if ($stageOrder -notcontains $normalized) {
        throw ("unsupported requested governed stage stop: {0}" -f $RequestedStageStop)
    }
    return $normalized
}

function Read-VibeEntrySurfaceConfig {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $configPath = Join-Path $RepoRoot 'config\vibe-entry-surfaces.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw ("vibe entry surface config not found: {0}" -f $configPath)
    }

    return Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-VibeEntryProgressiveStageStops {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$EntryIntentId = ''
    )

    if ([string]::IsNullOrWhiteSpace($EntryIntentId)) {
        return @()
    }

    $surfaceConfig = Read-VibeEntrySurfaceConfig -RepoRoot $RepoRoot
    foreach ($entry in @($surfaceConfig.entries)) {
        if ($null -eq $entry) {
            continue
        }
        $entryId = if (
            $entry.PSObject.Properties.Name -contains 'id' -and
            -not [string]::IsNullOrWhiteSpace([string]$entry.id)
        ) {
            [string]$entry.id
        } else {
            ''
        }
        if ($entryId -ne [string]$EntryIntentId) {
            continue
        }

        if (
            $entry.PSObject.Properties.Name -contains 'progressive_stage_stops' -and
            $null -ne $entry.progressive_stage_stops
        ) {
            return @(
                @($entry.progressive_stage_stops) |
                    ForEach-Object { Resolve-VibeRequestedStageStop -RequestedStageStop ([string]$_) } |
                    Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
            )
        }
        break
    }

    return @()
}

function Resolve-VibeEntryRequestedStageStop {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        return Resolve-VibeRequestedStageStop -RequestedStageStop $RequestedStageStop
    }

    if (-not [string]::IsNullOrWhiteSpace($EntryIntentId)) {
        $surfaceConfig = Read-VibeEntrySurfaceConfig -RepoRoot $RepoRoot
        foreach ($entry in @($surfaceConfig.entries)) {
            if ($null -eq $entry) {
                continue
            }
            $entryId = if (
                $entry.PSObject.Properties.Name -contains 'id' -and
                -not [string]::IsNullOrWhiteSpace([string]$entry.id)
            ) {
                [string]$entry.id
            } else {
                ''
            }
            if ($entryId -ne [string]$EntryIntentId) {
                continue
            }

            $entryProgressiveStops = @(Get-VibeEntryProgressiveStageStops -RepoRoot $RepoRoot -EntryIntentId $entryId)
            if (@($entryProgressiveStops).Count -gt 0) {
                return [string]$entryProgressiveStops[0]
            }

            $entryRequestedStop = if (
                $entry.PSObject.Properties.Name -contains 'requested_stage_stop' -and
                -not [string]::IsNullOrWhiteSpace([string]$entry.requested_stage_stop)
            ) {
                [string]$entry.requested_stage_stop
            } else {
                ''
            }
            if (-not [string]::IsNullOrWhiteSpace($entryRequestedStop)) {
                return Resolve-VibeRequestedStageStop -RequestedStageStop $entryRequestedStop
            }
            break
        }
    }

    return Resolve-VibeRequestedStageStop -RequestedStageStop ''
}

function Get-VibeNextProgressiveStageStop {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$TerminalStage = ''
    )

    $progressiveStops = @(Get-VibeEntryProgressiveStageStops -RepoRoot $RepoRoot -EntryIntentId $EntryIntentId)
    if (@($progressiveStops).Count -eq 0) {
        return ''
    }

    $normalizedTerminalStage = Resolve-VibeRequestedStageStop -RequestedStageStop $TerminalStage
    for ($index = 0; $index -lt $progressiveStops.Count; $index++) {
        if ([string]$progressiveStops[$index] -ne [string]$normalizedTerminalStage) {
            continue
        }
        if (($index + 1) -lt $progressiveStops.Count) {
            return [string]$progressiveStops[$index + 1]
        }
        break
    }

    return ''
}

function Get-VibeBoundedReturnFollowupEntryIds {
    param(
        [AllowEmptyString()] [string]$TerminalStage = ''
    )

    switch ([string]$TerminalStage) {
        'requirement_doc' { return @('vibe') }
        'xl_plan' { return @('vibe') }
        default { return @() }
    }
}

function New-VibeBoundedReturnControlProjection {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowNull()] [object]$StageLineage = $null,
        [AllowNull()] [object]$WorkflowLevelConfirmation = $null,
        [AllowNull()] [object]$SkillSearchGuide = $null
    )

    $resolvedEntryIntentId = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { 'vibe' } else { [string]$EntryIntentId }
    $terminalStage = Get-VibeStageLineageTerminalStage -StageLineage $StageLineage
    $allowedFollowupEntryIds = @(Get-VibeBoundedReturnFollowupEntryIds -TerminalStage $terminalStage)
    if (@($allowedFollowupEntryIds).Count -eq 0) {
        return $null
    }

    $nextStage = Get-VibeNextProgressiveStageStop -RepoRoot $RepoRoot -EntryIntentId $resolvedEntryIntentId -TerminalStage $terminalStage
    $approvalKind = switch ([string]$terminalStage) {
        'requirement_doc' { 'requirement_confirmation' }
        'xl_plan' { 'plan_confirmation' }
        default { 'user_reentry_confirmation' }
    }
    $allowedDecisionActions = switch ([string]$terminalStage) {
        'requirement_doc' {
            @(
                'approve',
                'approve_requirement',
                'approve_requirement_doc',
                'approve_requirements',
                'revise',
                'request_changes',
                'request_revise',
                'revise_requirement',
                'revise_requirement_doc',
                'revise_requirements'
            )
        }
        'xl_plan' {
            @(
                'approve',
                'approve_plan',
                'approve_execution_plan',
                'request_execute',
                'revise',
                'request_changes',
                'request_revise',
                'revise_plan',
                'revise_execution_plan'
            )
        }
        default { @('approve', 'revise', 'request_changes', 'request_revise') }
    }
    $preferredDecisionAction = switch ([string]$terminalStage) {
        'requirement_doc' { 'approve_requirement' }
        'xl_plan' { 'approve_plan' }
        default { 'approve' }
    }
    $recommendedWorkflowLevel = if (
        $null -ne $WorkflowLevelConfirmation -and
        (Test-VibeObjectHasProperty -InputObject $WorkflowLevelConfirmation -PropertyName 'recommended_level') -and
        -not [string]::IsNullOrWhiteSpace([string]$WorkflowLevelConfirmation.recommended_level)
    ) {
        [string]$WorkflowLevelConfirmation.recommended_level
    } else {
        $null
    }
    $forbiddenMcpPolicy = if ([string]$terminalStage -eq 'requirement_doc') {
        Read-VgoJsonFile -Path (Join-Path $RepoRoot 'config\forbidden-mcp-policy.json')
    } else {
        $null
    }
    $agentSkillOrganizationContract = if ([string]$terminalStage -eq 'requirement_doc') {
        [pscustomobject]@{
            submission_field = 'host_decision.agent_skill_organization'
            required_for_decision_actions = @(
                'approve',
                'approve_requirement',
                'approve_requirement_doc',
                'approve_requirements'
            )
            schema_version = 'agent_skill_organization_v1'
            derived_by = 'agent'
            allowed_workflow_levels = @('L', 'XL')
            required_top_level_fields = @(
                'schema_version',
                'derived_by',
                'workflow_level',
                'modules',
                'selected_skills',
                'uncovered_modules',
                'workflow_level_contract'
            )
            module_contract = [pscustomobject]@{
                required_fields = @('module_id', 'goal', 'candidate_skill_ids', 'execution_mode', 'acceptance_criteria')
                optional_fields = @('required', 'depends_on', 'write_scope', 'expected_outputs', 'verification')
                allowed_execution_modes = @('skill_assigned', 'agent_direct', 'blocked_gap')
                minimum_items = 1
                non_empty_fields = @('module_id', 'goal')
                unique_module_id_required = $true
                dependency_contract = [pscustomobject]@{
                    known_module_ids_required = $true
                    acyclic_required = $true
                }
                acceptance_criterion_contract = [pscustomobject]@{
                    required_fields = @('criterion_id', 'description', 'verification_mode')
                    allowed_verification_modes = @('automated', 'manual')
                    minimum_items = 1
                    unique_criterion_id_per_module = $true
                }
            }
            coverage_contract = [pscustomobject]@{
                rule = 'each module must use exactly one declared coverage mode'
                modes = [pscustomobject]@{
                    skill_assigned = [pscustomobject]@{
                        selected_skill_required = $true
                        uncovered_module_forbidden = $true
                    }
                    agent_direct = [pscustomobject]@{
                        selected_skill_forbidden = $true
                        uncovered_module_forbidden = $true
                        required_module_fields = @('write_scope', 'expected_outputs', 'verification')
                    }
                    blocked_gap = [pscustomobject]@{
                        selected_skill_forbidden = $true
                        uncovered_module_required = $true
                    }
                }
            }
            selected_skill_contract = [pscustomobject]@{
                required_fields = @('skill_id', 'module_ids', 'responsibility', 'reason')
                optional_fields = @('role', 'write_scope', 'expected_outputs', 'verification', 'module_assignments')
                unique_skill_id_required = $true
                known_module_ids_required = $true
                candidate_membership_required = $true
                non_empty_fields = @('skill_id', 'responsibility', 'reason')
                module_ids_minimum_items = 1
                module_assignments_required_when_multiple_modules = $true
                module_assignment_contract = [pscustomobject]@{
                    required_fields = @('module_id', 'role', 'responsibility', 'write_scope', 'expected_outputs', 'verification')
                    allowed_roles = @('owner', 'support', 'verifier')
                    one_entry_per_declared_module = $true
                    write_scope_rule = 'one concrete path or resource scope for this module assignment'
                    role_order_contract = [pscustomobject]@{
                        support_runs_before_owner = $true
                        owner_waits_for_support = $true
                        verifier_runs_after_owner = $true
                        role_must_match_temporal_position = $true
                        post_owner_review_rule = 'Use verifier, not support, for review or minimality checks that must happen after the owner finishes.'
                    }
                }
            }
            skill_identity_contract = [pscustomobject]@{
                selection_field = 'skill_id'
                authority = 'resolved_skill_entrypoint'
                match_rule = 'exact'
                display_name_is_not_selection_id = $true
                local_directory_rule = 'directory containing the retained SKILL.md under a declared local Skill root'
                nested_skill_rule = 'use the nested Skill directory name when the retained SKILL.md is nested'
            }
            uncovered_module_contract = [pscustomobject]@{
                required_fields = @('module_id', 'reason')
                unique_module_id_required = $true
                known_module_id_required = $true
            }
            workflow_level_contract = [pscustomobject]@{
                required_fields = @('L', 'XL')
                value_type = 'non_empty_string'
                purpose = 'Describe the task-specific workflow and Skill organization for both levels.'
            }
            forbidden_mcp_contract = [pscustomobject]@{
                policy_path = 'config/forbidden-mcp-policy.json'
                forbidden_mcp_ids = @($forbiddenMcpPolicy.forbidden_mcp_ids)
                id_match = [string]$forbiddenMcpPolicy.id_match
                installation = [string]$forbiddenMcpPolicy.installation
                runtime_recommendation = [string]$forbiddenMcpPolicy.runtime_recommendation
                selected_skills_must_not_require_forbidden_mcps = $true
            }
            examples = [pscustomobject]@{
                agent_direct = [pscustomobject]@{
                    schema_version = 'agent_skill_organization_v1'
                    derived_by = 'agent'
                    workflow_level = 'L'
                    modules = @(
                        [pscustomobject]@{
                            module_id = 'direct_work'
                            goal = 'Complete the module directly because no task Skill is required.'
                            candidate_skill_ids = @()
                            execution_mode = 'agent_direct'
                            required = $true
                            depends_on = @()
                            write_scope = 'outputs/direct/**'
                            expected_outputs = @('outputs/direct/result.md')
                            verification = @('Check the direct result against the frozen acceptance criteria.')
                            acceptance_criteria = @(
                                [pscustomobject]@{
                                    criterion_id = 'direct-result'
                                    description = 'The requested result is complete and accurate.'
                                    verification_mode = 'automated'
                                }
                            )
                        }
                    )
                    selected_skills = @()
                    uncovered_modules = @()
                    workflow_level_contract = [pscustomobject]@{
                        L = 'Run the single direct module serially.'
                        XL = 'If scope expands, split dependency-ready modules and keep conflicting writes serial.'
                    }
                }
                skill_assigned = [pscustomobject]@{
                    schema_version = 'agent_skill_organization_v1'
                    derived_by = 'agent'
                    workflow_level = 'L'
                    modules = @(
                        [pscustomobject]@{
                            module_id = 'skill_work'
                            goal = 'Complete the module with the selected task Skill.'
                            candidate_skill_ids = @('example-skill')
                            execution_mode = 'skill_assigned'
                            required = $true
                            depends_on = @()
                            acceptance_criteria = @(
                                [pscustomobject]@{
                                    criterion_id = 'skill-result'
                                    description = 'The Skill-owned result satisfies the module goal.'
                                    verification_mode = 'automated'
                                }
                            )
                        }
                    )
                    selected_skills = @(
                        [pscustomobject]@{
                            skill_id = 'example-skill'
                            module_ids = @('skill_work')
                            responsibility = 'Own the module work.'
                            reason = 'The Agent read this Skill contract and confirmed that it owns the module.'
                        }
                    )
                    uncovered_modules = @()
                    workflow_level_contract = [pscustomobject]@{
                        L = 'Run this Skill-owned module serially.'
                        XL = 'If scope expands, parallelize only dependency-ready modules with non-conflicting writes.'
                    }
                }
            }
        }
    } else {
        $null
    }
    $requiredAgentSuppliedFields = if ([string]$terminalStage -eq 'requirement_doc') {
        [object[]]@('agent_skill_organization')
    } else {
        [object[]]@()
    }
    $planRevisionContract = if ([string]$terminalStage -eq 'xl_plan') {
        [pscustomobject]@{
            revision_delta_required = $true
            text_delta_does_not_mutate_organization = $true
            full_organization_replacement_required_when_changed = $true
            organization_change_fields = @(
                'modules',
                'skills',
                'roles',
                'dependencies',
                'write_scopes',
                'expected_outputs',
                'verification',
                'workflow_level'
            )
            replacement_field = 'host_decision.agent_skill_organization'
        }
    } else {
        $null
    }
    $approvalPrompt = switch ([string]$terminalStage) {
        'requirement_doc' {
            'Review the frozen requirement document with the user and wait for an explicit approve/revise reply before planning. Do not auto-continue into `xl_plan` in the same assistant turn.'
        }
        'xl_plan' {
            'Review the frozen execution plan with the user and wait for an explicit approve/revise reply before execution. Do not auto-continue into `plan_execute` or `phase_cleanup` in the same assistant turn.'
        }
        default {
            'Return control to the user and wait for an explicit follow-up before continuing.'
        }
    }
    $token = [guid]::NewGuid().ToString('N')
    $forbiddenActions = @(
        'write_plan',
        'execute_task',
        'manual_workaround',
        'deliver_final_artifacts',
        'consume_reentry_token_in_same_turn'
    )
        $renderedLines = @(
            'Bounded governed stop reached. Return control to the user now.',
            ('- terminal stage: `{0}`' -f [string]$terminalStage),
            ('- source run id: `{0}`' -f [string]$RunId),
            ('- explicit user re-entry required before later stages: `true`'),
            '- assistant must stop now: `true`',
            '- Do not continue in the same assistant turn; wait for a new user approval or revision message',
            '- manual execution outside governed re-entry is forbidden',
            '- the original detailed prompt is not approval of the frozen requirement or plan',
            ('- allowed follow-up entries: `{0}`' -f (@($allowedFollowupEntryIds) -join '`, `')),
            ('- next governed stage after approval: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($nextStage)) { 'none' } else { [string]$nextStage })),
            ('- approval kind: `{0}`' -f [string]$approvalKind),
            ('- preferred structured approval action: `{0}`' -f [string]$preferredDecisionAction),
            ('- approval instruction: {0}' -f [string]$approvalPrompt),
            '- the host may translate the user''s natural-language approval into a structured decision; exact keywords are not required',
            ('- continuation token: `{0}`' -f [string]$token)
        )

    return [pscustomobject]@{
        protocol_version = 'v1'
        enabled = $true
        explicit_user_reentry_required = $true
        explicit_new_user_message_required = $true
        assistant_must_stop = $true
        same_turn_continuation_forbidden = $true
        manual_execution_forbidden = $true
        completion_allowed = $false
        original_prompt_is_not_approval = $true
        next_allowed_assistant_action = 'wait_for_new_user_approval_or_revision'
        forbidden_actions = @($forbiddenActions)
        control_owner = 'user'
        source_run_id = $RunId
        terminal_stage = [string]$terminalStage
        next_stage = if ([string]::IsNullOrWhiteSpace($nextStage)) { $null } else { [string]$nextStage }
        approval_kind = [string]$approvalKind
        approval_prompt = [string]$approvalPrompt
        host_decision_contract = [pscustomobject]@{
            protocol_version = 'v1'
            decision_kind = 'approval_response'
            decision_context = 'bounded_stage_reentry'
            pending_terminal_stage = [string]$terminalStage
            next_stage = if ([string]::IsNullOrWhiteSpace($nextStage)) { $null } else { [string]$nextStage }
            approval_kind = [string]$approvalKind
            allowed_decision_actions = @($allowedDecisionActions)
            preferred_decision_action = [string]$preferredDecisionAction
            preferred_payload_complete = [bool]([string]$terminalStage -ne 'requirement_doc')
            required_agent_supplied_fields = [object[]]$requiredAgentSuppliedFields
            preferred_payload = [pscustomobject]@{
                decision_kind = 'approval_response'
                decision_action = [string]$preferredDecisionAction
                approval_decision = 'approve'
                requested_grade_floor = if ([string]$terminalStage -eq 'requirement_doc' -and -not [string]::IsNullOrWhiteSpace([string]$recommendedWorkflowLevel)) { [string]$recommendedWorkflowLevel } else { $null }
                agent_skill_organization = $null
            }
            allowed_workflow_levels = if ([string]$terminalStage -eq 'requirement_doc') { @('L', 'XL') } else { @() }
            recommended_workflow_level = if ([string]$terminalStage -eq 'requirement_doc' -and -not [string]::IsNullOrWhiteSpace([string]$recommendedWorkflowLevel)) { [string]$recommendedWorkflowLevel } else { $null }
            agent_skill_organization_contract = $agentSkillOrganizationContract
            plan_revision_contract = $planRevisionContract
        }
        allowed_followup_entry_ids = @($allowedFollowupEntryIds)
        reentry_token = $token
        rendered_text = (@($renderedLines) -join "`n")
        skill_search_guide = if ($null -eq $SkillSearchGuide) { $null } else { $SkillSearchGuide }
        workflow_level_confirmation = if ($null -eq $WorkflowLevelConfirmation) { $null } else { $WorkflowLevelConfirmation }
    }
}

function Get-VibeGovernanceArtifactContract {
    param(
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $artifacts = if (
        $null -ne $HierarchyContract -and
        $HierarchyContract.PSObject.Properties.Name -contains 'governance_artifacts' -and
        $null -ne $HierarchyContract.governance_artifacts
    ) {
        $HierarchyContract.governance_artifacts
    } else {
        $null
    }

    return [pscustomobject]@{
        capsule = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'capsule' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.capsule)) { [string]$artifacts.capsule } else { 'governance-capsule.json' }
        lineage = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'lineage' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.lineage)) { [string]$artifacts.lineage } else { 'stage-lineage.json' }
        delegation_envelope = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'delegation_envelope' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.delegation_envelope)) { [string]$artifacts.delegation_envelope } else { 'delegation-envelope.json' }
        delegation_validation = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'delegation_validation' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.delegation_validation)) { [string]$artifacts.delegation_validation } else { 'delegation-validation-receipt.json' }
    }
}

function Get-VibeGovernanceArtifactPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [ValidateSet('capsule', 'lineage', 'delegation_envelope', 'delegation_validation')] [string]$ArtifactName,
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $contract = Get-VibeGovernanceArtifactContract -HierarchyContract $HierarchyContract
    $fileName = [string]$contract.$ArtifactName
    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot $fileName))
}

function Write-VibeGovernanceCapsule {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = 'vibe',
        [AllowNull()] [string[]]$AllowedStageSequence = $(Get-VibeGovernedRuntimeStageOrder),
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $capsulePath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'capsule' -HierarchyContract $HierarchyContract
    $capsule = [pscustomobject]@{
        run_id = $RunId
        root_run_id = $RootRunId
        governance_scope = $GovernanceScope
        runtime_selected_skill = if ([string]::IsNullOrWhiteSpace($RuntimeSelectedSkill)) { 'vibe' } else { [string]$RuntimeSelectedSkill }
        state_machine_version = 'governed-runtime-v1'
        allowed_stage_sequence = @($AllowedStageSequence)
        requirement_truth_owner = if ($GovernanceScope -eq 'root') { 'root_governed' } else { 'root_governed_inherited' }
        plan_truth_owner = if ($GovernanceScope -eq 'root') { 'root_governed' } else { 'root_governed_inherited' }
        created_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $capsulePath -Value $capsule

    return [pscustomobject]@{
        path = $capsulePath
        capsule = $capsule
    }
}

function Add-VibeStageLineageEntry {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$StageName,
        [AllowEmptyString()] [string]$PreviousStageName = '',
        [AllowEmptyString()] [string]$PreviousStageReceiptPath = '',
        [AllowEmptyString()] [string]$CurrentReceiptPath = '',
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $lineagePath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'lineage' -HierarchyContract $HierarchyContract
    $document = if (Test-Path -LiteralPath $lineagePath) {
        Get-Content -LiteralPath $lineagePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        [pscustomobject]@{
            run_id = $RunId
            root_run_id = $RootRunId
            stages = @()
        }
    }

    $stages = [System.Collections.ArrayList]::new()
    foreach ($stage in @($document.stages)) {
        [void]$stages.Add($stage)
    }
    if (-not [string]::IsNullOrWhiteSpace($PreviousStageName)) {
        if ($stages.Count -eq 0) {
            throw ("Cannot record stage '{0}' before lineage contains previous stage '{1}'." -f $StageName, $PreviousStageName)
        }
        $lastStage = $stages[$stages.Count - 1]
        if ([string]$lastStage.stage_name -ne $PreviousStageName) {
            throw ("Stage lineage mismatch for '{0}'. Expected previous stage '{1}', found '{2}'." -f $StageName, $PreviousStageName, [string]$lastStage.stage_name)
        }
        if (-not [string]::IsNullOrWhiteSpace($PreviousStageReceiptPath) -and -not (Test-Path -LiteralPath $PreviousStageReceiptPath)) {
            throw ("Stage lineage prerequisite receipt missing for '{0}': {1}" -f $StageName, $PreviousStageReceiptPath)
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($CurrentReceiptPath) -and -not (Test-Path -LiteralPath $CurrentReceiptPath)) {
        throw ("Current stage receipt missing for '{0}': {1}" -f $StageName, $CurrentReceiptPath)
    }

    $entry = [pscustomobject]@{
        stage_name = $StageName
        run_id = $RunId
        root_run_id = $RootRunId
        previous_stage_name = if ([string]::IsNullOrWhiteSpace($PreviousStageName)) { $null } else { $PreviousStageName }
        previous_stage_receipt_path = if ([string]::IsNullOrWhiteSpace($PreviousStageReceiptPath)) { $null } else { [System.IO.Path]::GetFullPath($PreviousStageReceiptPath) }
        current_receipt_path = if ([string]::IsNullOrWhiteSpace($CurrentReceiptPath)) { $null } else { [System.IO.Path]::GetFullPath($CurrentReceiptPath) }
        transition_validated = $true
        validated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    [void]$stages.Add($entry)
    $document = [pscustomobject]@{
        run_id = $RunId
        root_run_id = $RootRunId
        stages = @($stages)
        last_stage_name = $StageName
        updated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $lineagePath -Value $document

    return [pscustomobject]@{
        path = $lineagePath
        lineage = $document
        entry = $entry
    }
}

function Write-VibeDelegationEnvelope {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$ParentRunId,
        [Parameter(Mandatory)] [string]$ParentUnitId,
        [Parameter(Mandatory)] [string]$ChildRunId,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$WriteScope,
        [AllowNull()] [string[]]$ApprovedSpecialists = @(),
        [AllowEmptyString()] [string]$ReviewMode = 'module_acceptance'
    )

    $envelope = [pscustomobject]@{
        root_run_id = $RootRunId
        parent_run_id = $ParentRunId
        parent_unit_id = $ParentUnitId
        child_run_id = $ChildRunId
        governance_scope = 'child_governed'
        requirement_doc_path = [System.IO.Path]::GetFullPath($RequirementDocPath)
        execution_plan_path = [System.IO.Path]::GetFullPath($ExecutionPlanPath)
        write_scope = $WriteScope
        approved_specialists = @($ApprovedSpecialists | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
        review_mode = if ([string]::IsNullOrWhiteSpace($ReviewMode)) { 'module_acceptance' } else { $ReviewMode }
        prompt_tail_required = '$vibe'
        allow_requirement_freeze = $false
        allow_plan_freeze = $false
        allow_root_completion_claim = $false
    }
    Write-VibeJsonArtifact -Path $Path -Value $envelope

    return [pscustomobject]@{
        path = [System.IO.Path]::GetFullPath($Path)
        envelope = $envelope
    }
}

function Assert-VibeDelegationEnvelope {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [AllowEmptyString()] [string]$EnvelopePath,
        [AllowNull()] [object]$HierarchyState = $null,
        [AllowNull()] [object]$LaneSpec = $null,
        [AllowEmptyString()] [string]$ExpectedWriteScope = '',
        [AllowEmptyString()] [string]$ExpectedChildRunId = '',
        [AllowEmptyString()] [string]$ExpectedParentRunId = '',
        [AllowEmptyString()] [string]$ExpectedParentUnitId = '',
        [AllowEmptyString()] [string]$ExpectedSkillId = '',
        [AllowNull()] [object]$HierarchyContract = $null
    )

    if ([string]::IsNullOrWhiteSpace($EnvelopePath) -or -not (Test-Path -LiteralPath $EnvelopePath)) {
        throw ("Child-governed runtime requires DelegationEnvelopePath and the referenced file must exist: {0}" -f $EnvelopePath)
    }

    $envelope = Get-Content -LiteralPath $EnvelopePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $writeScopeValue = if ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'write_scope') { [string]$LaneSpec.write_scope } elseif (-not [string]::IsNullOrWhiteSpace($ExpectedWriteScope)) { $ExpectedWriteScope } elseif ($envelope.PSObject.Properties.Name -contains 'write_scope') { [string]$envelope.write_scope } else { '' }
    $approvedSpecialists = if ($envelope.PSObject.Properties.Name -contains 'approved_specialists' -and $null -ne $envelope.approved_specialists) {
        @($envelope.approved_specialists | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @()
    }

    $requirementMatches = $true
    $planMatches = $true
    if ($null -ne $HierarchyState) {
        if ($HierarchyState.inherited_requirement_doc_path) {
            $requirementMatches = ([System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path) -eq [System.IO.Path]::GetFullPath([string]$HierarchyState.inherited_requirement_doc_path))
        }
        if ($HierarchyState.inherited_execution_plan_path) {
            $planMatches = ([System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path) -eq [System.IO.Path]::GetFullPath([string]$HierarchyState.inherited_execution_plan_path))
        }
    } elseif ($null -ne $LaneSpec) {
        $requirementMatches = ([System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path) -eq [System.IO.Path]::GetFullPath([string]$LaneSpec.requirement_doc_path))
        $planMatches = ([System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path) -eq [System.IO.Path]::GetFullPath([string]$LaneSpec.execution_plan_path))
    }

    $writeScopeValid = -not [string]::IsNullOrWhiteSpace([string]$envelope.write_scope)
    if (-not [string]::IsNullOrWhiteSpace($writeScopeValue)) {
        $writeScopeValid = $writeScopeValid -and ([string]$envelope.write_scope -eq $writeScopeValue)
    }

    $childRunValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedChildRunId)) {
        $ExpectedChildRunId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'run_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.run_id)) {
        [string]$LaneSpec.run_id
    } else {
        ''
    }
    $parentRunValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedParentRunId)) {
        $ExpectedParentRunId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'parent_run_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.parent_run_id)) {
        [string]$LaneSpec.parent_run_id
    } elseif ($null -ne $HierarchyState -and -not [string]::IsNullOrWhiteSpace([string]$HierarchyState.parent_run_id)) {
        [string]$HierarchyState.parent_run_id
    } else {
        ''
    }
    $parentUnitValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedParentUnitId)) {
        $ExpectedParentUnitId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'parent_unit_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.parent_unit_id)) {
        [string]$LaneSpec.parent_unit_id
    } elseif ($null -ne $HierarchyState -and -not [string]::IsNullOrWhiteSpace([string]$HierarchyState.parent_unit_id)) {
        [string]$HierarchyState.parent_unit_id
    } else {
        ''
    }
    $childRunValid = $true
    if (-not [string]::IsNullOrWhiteSpace($childRunValue)) {
        $childRunValid = ([string]$envelope.child_run_id -eq $childRunValue)
    }
    $parentRunValid = $true
    if (-not [string]::IsNullOrWhiteSpace($parentRunValue)) {
        $parentRunValid = ([string]$envelope.parent_run_id -eq $parentRunValue)
    }
    $parentUnitValid = $true
    if (-not [string]::IsNullOrWhiteSpace($parentUnitValue)) {
        $parentUnitValid = ([string]$envelope.parent_unit_id -eq $parentUnitValue)
    }

    $specialistApprovalValid = $true
    if (-not [string]::IsNullOrWhiteSpace($ExpectedSkillId)) {
        $specialistApprovalValid = ($approvedSpecialists -contains $ExpectedSkillId)
    }
    $promptTailValid = ([string]$envelope.prompt_tail_required -eq '$vibe')
    $scopeValid = ([string]$envelope.governance_scope -eq 'child_governed')
    $rootRunValid = $true
    if ($null -ne $HierarchyState -and $HierarchyState.root_run_id) {
        $rootRunValid = ([string]$envelope.root_run_id -eq [string]$HierarchyState.root_run_id)
    } elseif ($null -ne $LaneSpec -and $LaneSpec.root_run_id) {
        $rootRunValid = ([string]$envelope.root_run_id -eq [string]$LaneSpec.root_run_id)
    }

    if (-not $scopeValid) {
        throw ("Delegation envelope governance scope must be child_governed: {0}" -f [string]$envelope.governance_scope)
    }
    if (-not $promptTailValid) {
        throw 'Delegation envelope must require $vibe prompt tail discipline.'
    }
    if (-not $requirementMatches -or -not $planMatches) {
        throw 'Delegation envelope does not match inherited canonical requirement/plan truth.'
    }
    if (-not $writeScopeValid) {
        throw 'Delegation envelope must declare a non-empty matching write scope.'
    }
    if (-not $rootRunValid) {
        throw 'Delegation envelope root run id does not match the governed child context.'
    }
    if (-not $childRunValid) {
        throw 'Delegation envelope child run id does not match the governed child context.'
    }
    if (-not $parentRunValid) {
        throw 'Delegation envelope parent run id does not match the governed child context.'
    }
    if (-not $parentUnitValid) {
        throw 'Delegation envelope parent unit id does not match the governed child context.'
    }
    if (-not $specialistApprovalValid) {
        throw ("Delegation envelope does not approve specialist dispatch: {0}" -f $ExpectedSkillId)
    }

    $receiptPath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'delegation_validation' -HierarchyContract $HierarchyContract
    $receipt = [pscustomobject]@{
        child_run_id = if (-not [string]::IsNullOrWhiteSpace($childRunValue)) { $childRunValue } elseif ($envelope.PSObject.Properties.Name -contains 'child_run_id') { [string]$envelope.child_run_id } else { $null }
        root_run_id = [string]$envelope.root_run_id
        envelope_path = [System.IO.Path]::GetFullPath($EnvelopePath)
        requirement_doc_path = [System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path)
        execution_plan_path = [System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path)
        write_scope_valid = [bool]$writeScopeValid
        prompt_tail_valid = [bool]$promptTailValid
        child_run_valid = [bool]$childRunValid
        parent_run_valid = [bool]$parentRunValid
        parent_unit_valid = [bool]$parentUnitValid
        specialist_approval_valid = [bool]$specialistApprovalValid
        validated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

    return [pscustomobject]@{
        receipt_path = $receiptPath
        receipt = $receipt
        envelope = $envelope
    }
}

function New-VibeRuntimeSummaryArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$SkeletonReceiptPath,
        [Parameter(Mandatory)] [string]$RuntimeInputPacketPath,
        [Parameter(Mandatory)] [string]$GovernanceCapsulePath,
        [Parameter(Mandatory)] [string]$StageLineagePath,
        [AllowEmptyString()] [string]$IntentContractPath = '',
        [AllowEmptyString()] [string]$RequirementDocPath = '',
        [AllowEmptyString()] [string]$RequirementReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanReceiptPath = '',
        [AllowEmptyString()] [string]$ModuleWorkPlanPath = '',
        [AllowEmptyString()] [string]$ModuleExecutionPath = '',
        [AllowEmptyString()] [string]$AgentExecutionHandoffPath = '',
        [AllowEmptyString()] [string]$ExecuteReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionManifestPath = '',
        [AllowEmptyString()] [string]$HostStageDisclosurePath = '',
        [AllowEmptyString()] [string]$HostUserBriefingPath = '',
        [AllowEmptyString()] [string]$CleanupReceiptPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceReportPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceMarkdownPath = '',
        [AllowEmptyString()] [string]$MemoryActivationReportPath = '',
        [AllowEmptyString()] [string]$MemoryActivationMarkdownPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [AllowEmptyString()] [string]$DelegationValidationReceiptPath = ''
    )

    return [pscustomobject]@{
        skeleton_receipt = $SkeletonReceiptPath
        runtime_input_packet = $RuntimeInputPacketPath
        governance_capsule = $GovernanceCapsulePath
        stage_lineage = $StageLineagePath
        intent_contract = if ([string]::IsNullOrWhiteSpace($IntentContractPath)) { $null } else { $IntentContractPath }
        requirement_doc = if ([string]::IsNullOrWhiteSpace($RequirementDocPath)) { $null } else { $RequirementDocPath }
        requirement_receipt = if ([string]::IsNullOrWhiteSpace($RequirementReceiptPath)) { $null } else { $RequirementReceiptPath }
        execution_plan = if ([string]::IsNullOrWhiteSpace($ExecutionPlanPath)) { $null } else { $ExecutionPlanPath }
        execution_plan_receipt = if ([string]::IsNullOrWhiteSpace($ExecutionPlanReceiptPath)) { $null } else { $ExecutionPlanReceiptPath }
        module_work_plan = if ([string]::IsNullOrWhiteSpace($ModuleWorkPlanPath)) { $null } else { $ModuleWorkPlanPath }
        module_execution = if ([string]::IsNullOrWhiteSpace($ModuleExecutionPath)) { $null } else { $ModuleExecutionPath }
        agent_execution_handoff = if ([string]::IsNullOrWhiteSpace($AgentExecutionHandoffPath)) { $null } else { $AgentExecutionHandoffPath }
        execute_receipt = if ([string]::IsNullOrWhiteSpace($ExecuteReceiptPath)) { $null } else { $ExecuteReceiptPath }
        execution_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionManifestPath)) { $null } else { $ExecutionManifestPath }
        host_stage_disclosure = if ([string]::IsNullOrWhiteSpace($HostStageDisclosurePath)) { $null } else { $HostStageDisclosurePath }
        host_user_briefing = if ([string]::IsNullOrWhiteSpace($HostUserBriefingPath)) { $null } else { $HostUserBriefingPath }
        cleanup_receipt = if ([string]::IsNullOrWhiteSpace($CleanupReceiptPath)) { $null } else { $CleanupReceiptPath }
        delivery_acceptance_report = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceReportPath)) { $null } else { $DeliveryAcceptanceReportPath }
        delivery_acceptance_markdown = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceMarkdownPath)) { $null } else { $DeliveryAcceptanceMarkdownPath }
        memory_activation_report = if ([string]::IsNullOrWhiteSpace($MemoryActivationReportPath)) { $null } else { $MemoryActivationReportPath }
        memory_activation_markdown = if ([string]::IsNullOrWhiteSpace($MemoryActivationMarkdownPath)) { $null } else { $MemoryActivationMarkdownPath }
        delegation_envelope = if ([string]::IsNullOrWhiteSpace($DelegationEnvelopePath)) { $null } else { $DelegationEnvelopePath }
        delegation_validation_receipt = if ([string]::IsNullOrWhiteSpace($DelegationValidationReceiptPath)) { $null } else { $DelegationValidationReceiptPath }
    }
}

function New-VibeRuntimeSummaryRelativeArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [object]$Artifacts
    )

    $relativeArtifacts = [ordered]@{}
    foreach ($property in @($Artifacts.PSObject.Properties)) {
        if ($null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            $relativeArtifacts[[string]$property.Name] = $null
            continue
        }
        $relativeArtifacts[[string]$property.Name] = Get-VibeRelativePathCompat -BasePath $BasePath -TargetPath ([string]$property.Value)
    }

    return [pscustomobject]$relativeArtifacts
}

function New-VibeRuntimeSummaryMemoryActivationProjection {
    param(
        [AllowNull()] [object]$MemoryActivationReport
    )

    if ($null -eq $MemoryActivationReport) {
        return $null
    }

    $policy = Get-VibePropertySafe -InputObject $MemoryActivationReport -PropertyName 'policy'
    $summary = Get-VibePropertySafe -InputObject $MemoryActivationReport -PropertyName 'summary'

    return [pscustomobject]@{
        policy_mode = Get-VibeNestedPropertySafe -InputObject $policy -PropertyPath @('mode') -DefaultValue ''
        routing_contract = Get-VibeNestedPropertySafe -InputObject $policy -PropertyPath @('routing_contract') -DefaultValue ''
        fallback_event_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('fallback_event_count') -DefaultValue 0
        artifact_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('artifact_count') -DefaultValue 0
        budget_guard_respected = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('budget_guard_respected') -DefaultValue $false
    }
}

function New-VibeRuntimeSummaryDeliveryAcceptanceProjection {
    param(
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    if ($null -eq $DeliveryAcceptanceReport) {
        return $null
    }

    $summary = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'summary'

    return [pscustomobject]@{
        gate_result = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('gate_result') -DefaultValue ''
        completion_language_allowed = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('completion_language_allowed') -DefaultValue $false
        readiness_state = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('readiness_state') -DefaultValue ''
        manual_review_layer_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('manual_review_layer_count') -DefaultValue 0
        failing_layer_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('failing_layer_count') -DefaultValue 0
    }
}

function Get-VibeStageLineageExecutedStageOrder {
    param(
        [AllowNull()] [object]$StageLineage = $null
    )

    if ($null -eq $StageLineage) {
        return @()
    }

    $lineageSource = if ((Test-VibeObjectHasProperty -InputObject $StageLineage -PropertyName 'lineage') -and $null -ne $StageLineage.lineage) {
        $StageLineage.lineage
    } else {
        $StageLineage
    }

    $stageEntries = @()
    if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stages') -and $null -ne $lineageSource.stages) {
        $stageEntries = @($lineageSource.stages)
    } elseif ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'entries') -and $null -ne $lineageSource.entries) {
        $stageEntries = @($lineageSource.entries)
    }

    $stageNames = New-Object System.Collections.ArrayList
    foreach ($entry in @($stageEntries)) {
        if ($null -eq $entry) {
            continue
        }
        $stageName = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'stage_name') -and -not [string]::IsNullOrWhiteSpace([string]$entry.stage_name)) {
            [string]$entry.stage_name
        } elseif ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$entry.stage)) {
            [string]$entry.stage
        } else {
            ''
        }
        if (-not [string]::IsNullOrWhiteSpace($stageName)) {
            [void]$stageNames.Add($stageName)
        }
    }

    if ($stageNames.Count -eq 0) {
        $topLevelStageName = if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stage_name') -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.stage_name)) {
            [string]$lineageSource.stage_name
        } elseif ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.stage)) {
            [string]$lineageSource.stage
        } else {
            ''
        }
        if (-not [string]::IsNullOrWhiteSpace($topLevelStageName)) {
            [void]$stageNames.Add($topLevelStageName)
        }
    }

    return [string[]]$stageNames.ToArray()
}

function Get-VibeStageLineageTerminalStage {
    param(
        [AllowNull()] [object]$StageLineage = $null
    )

    if ($null -eq $StageLineage) {
        return $null
    }

    $lineageSource = if ((Test-VibeObjectHasProperty -InputObject $StageLineage -PropertyName 'lineage') -and $null -ne $StageLineage.lineage) {
        $StageLineage.lineage
    } else {
        $StageLineage
    }

    foreach ($propertyName in @('last_stage_name', 'last_stage')) {
        if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName $propertyName) -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.$propertyName)) {
            return [string]$lineageSource.$propertyName
        }
    }

    $executedStageOrder = @(Get-VibeStageLineageExecutedStageOrder -StageLineage $lineageSource)
    if ($executedStageOrder.Count -gt 0) {
        return [string]$executedStageOrder[$executedStageOrder.Count - 1]
    }

    return $null
}

function Get-VibeHostUserBriefingPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'host-user-briefing.md'))
}

function Get-VibeHostStageDisclosurePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'host-stage-disclosure.json'))
}

function Add-VibeHostStageDisclosureEvent {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$DisclosureEvent = $null
    )

    if ($null -eq $DisclosureEvent) {
        return $null
    }

    $path = Get-VibeHostStageDisclosurePath -SessionRoot $SessionRoot
    $document = if (Test-Path -LiteralPath $path) {
        Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        [pscustomobject]@{
            enabled = $false
            protocol_version = 'v1'
            mode = 'progressive_host_stage_disclosure'
            append_only = $true
            event_count = 0
            last_sequence = 0
            freeze_gate_passed = $true
            events = @()
            rendered_text = ''
        }
    }

    $events = New-Object System.Collections.ArrayList
    foreach ($existingEvent in @($document.events)) {
        [void]$events.Add($existingEvent)
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'segment_id') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.segment_id)) {
        [string]$DisclosureEvent.segment_id
    } else {
        return $null
    }
    foreach ($existingEvent in @($events)) {
        if ($existingEvent -and [string]$existingEvent.segment_id -eq $segmentId) {
            return [pscustomobject]@{
                path = $path
                disclosure = $document
                event = $existingEvent
            }
        }
    }

    $recordedEvent = [pscustomobject]@{
        sequence = [int]($events.Count + 1)
        emitted_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        event_id = [string]$DisclosureEvent.event_id
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.stage)) { [string]$DisclosureEvent.stage } else { $null }
        category = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'category') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.category)) { [string]$DisclosureEvent.category } else { $null }
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.truth_layer)) { [string]$DisclosureEvent.truth_layer } else { $null }
        status = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'status') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.status)) { [string]$DisclosureEvent.status } else { 'reported' }
        gate_status = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'gate_status') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.gate_status)) { [string]$DisclosureEvent.gate_status } else { $null }
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'skill_count')) { [int]$DisclosureEvent.skill_count } else { @($DisclosureEvent.skills).Count }
        skills = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'skills')) { @($DisclosureEvent.skills) } else { @() }
        rendered_text = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'rendered_text') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.rendered_text)) { [string]$DisclosureEvent.rendered_text } else { $null }
    }
    [void]$events.Add($recordedEvent)

    $eventArray = [object[]]$events.ToArray()
    $renderedSections = @()
    foreach ($eventEntry in @($eventArray)) {
        if ($null -eq $eventEntry -or [string]::IsNullOrWhiteSpace([string]$eventEntry.rendered_text)) {
            continue
        }
        $renderedSections += [string]$eventEntry.rendered_text
    }
    $failedConsultationEvents = @($eventArray | Where-Object { [string]$_.truth_layer -eq 'consultation' -and [string]$_.status -eq 'gate_failed' })
    $document = [pscustomobject]@{
        enabled = [bool](@($eventArray).Count -gt 0)
        protocol_version = 'v1'
        mode = 'progressive_host_stage_disclosure'
        append_only = $true
        event_count = [int]@($eventArray).Count
        last_sequence = [int]$recordedEvent.sequence
        freeze_gate_passed = [bool](@($failedConsultationEvents).Count -eq 0)
        events = $eventArray
        rendered_text = (@($renderedSections) -join "`n`n")
    }
    Write-VibeJsonArtifact -Path $path -Value $document

    return [pscustomobject]@{
        path = $path
        disclosure = $document
        event = $recordedEvent
    }
}

function New-VibeHostUserBriefingProjection {
    param(
        [AllowNull()] [object]$BoundedReturnControl = $null,
        [AllowNull()] [object]$DeliveryAcceptanceReport = $null
    )

    $segments = New-Object System.Collections.Generic.List[object]
    $renderedSections = @()

    $deliverySummary = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'summary'
    $deliveryExecutionContext = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'execution_context'
    if ($null -ne $DeliveryAcceptanceReport -and $null -ne $deliverySummary) {
        $completionAllowed = [bool](Get-VibePropertySafe -InputObject $deliverySummary -PropertyName 'completion_language_allowed' -DefaultValue $false)
        $gateResult = [string](Get-VibePropertySafe -InputObject $deliverySummary -PropertyName 'gate_result' -DefaultValue 'UNKNOWN')
        $moduleTruth = Get-VibeNestedPropertySafe -InputObject $DeliveryAcceptanceReport -PropertyPath @('truth_results', 'module_acceptance_truth') -DefaultValue $null
        $moduleState = [string](Get-VibePropertySafe -InputObject $moduleTruth -PropertyName 'state' -DefaultValue 'not_applicable')
        $moduleNotes = [string](Get-VibePropertySafe -InputObject $moduleTruth -PropertyName 'notes' -DefaultValue '')
        $taskLines = @(
            $(if ($completionAllowed) { 'Task is complete.' } else { 'Task is not complete.' }),
            ('- Module acceptance: `{0}`' -f $moduleState),
            ('- Delivery gate: `{0}`' -f $gateResult)
        )
        if (-not [string]::IsNullOrWhiteSpace($moduleNotes)) {
            $taskLines += ('- {0}' -f $moduleNotes)
        }
        $taskSegment = [pscustomobject]@{
            segment_id = 'task_module_status'
            stage = 'phase_cleanup'
            category = 'completion'
            truth_layer = 'module_acceptance_truth'
            status = $moduleState
            gate_status = $gateResult
            rendered_text = (@($taskLines) -join "`n")
        }
        $segments.Add($taskSegment) | Out-Null
        $renderedSections += [string]$taskSegment.rendered_text
    }
    $moduleWorkContinuationPending = [bool](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('module_work_continuation_pending') -DefaultValue $false)
    if ($moduleWorkContinuationPending) {
        $deliveryGateResult = [string](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('gate_result') -DefaultValue '')
        $deliveryReadinessState = [string](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('readiness_state') -DefaultValue '')
        $deliveryCompletionAllowed = [bool](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('completion_language_allowed') -DefaultValue $false)
        $sourceRunId = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('run_id') -DefaultValue '')
        $sessionRoot = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('session_root') -DefaultValue '')
        $effectiveExecutionStatus = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('module_work_status') -DefaultValue '')
        $moduleExecutionPath = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('module_execution_path') -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($moduleExecutionPath) -and -not [string]::IsNullOrWhiteSpace($sessionRoot)) {
            $moduleExecutionPath = Get-VibeModuleExecutionPath -SessionRoot $sessionRoot
        }
        $pendingModuleWorkUnitIds = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'pending_module_work_unit_ids') -and
            $null -ne $deliveryExecutionContext.pending_module_work_unit_ids
        ) {
            @($deliveryExecutionContext.pending_module_work_unit_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $assignedModuleSkillIds = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'assigned_module_skill_ids') -and
            $null -ne $deliveryExecutionContext.assigned_module_skill_ids
        ) {
            @($deliveryExecutionContext.assigned_module_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $rawPendingModuleWorkUnits = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'pending_module_work_units') -and
            $null -ne $deliveryExecutionContext.pending_module_work_units
        ) {
            @($deliveryExecutionContext.pending_module_work_units)
        } else {
            @()
        }
        $requiredUnits = New-Object System.Collections.Generic.List[object]
        foreach ($unit in $rawPendingModuleWorkUnits) {
            if ($null -eq $unit) {
                continue
            }
            $requiredUnits.Add([pscustomobject]@{
                unit_id = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'unit_id')
                skill_id = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'skill_id')
                skill_entrypoint = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'skill_entrypoint')
                result_path = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'result_path')
            }) | Out-Null
        }
        $requiredUnitArray = [object[]]$requiredUnits.ToArray()
        $pythonLauncher = if ([System.IO.Path]::DirectorySeparatorChar -eq '\') { 'py -3' } else { 'python3' }
        $refreshCommandHint = if (-not [string]::IsNullOrWhiteSpace($sessionRoot)) {
            '{0} scripts/verify/runtime_neutral/runtime_delivery_acceptance.py --session-root "{1}" --write-artifacts' -f $pythonLauncher, $sessionRoot
        } else {
            '{0} scripts/verify/runtime_neutral/runtime_delivery_acceptance.py --session-root <session_root> --write-artifacts' -f $pythonLauncher
        }
        $executionHandoffContract = [pscustomobject]@{
            protocol_version = 'v1'
            decision_kind = 'module_execution_update'
            decision_context = 'module_work'
            source_run_id = if ([string]::IsNullOrWhiteSpace($sourceRunId)) { $null } else { $sourceRunId }
            session_root = if ([string]::IsNullOrWhiteSpace($sessionRoot)) { $null } else { $sessionRoot }
            module_execution_path = if ([string]::IsNullOrWhiteSpace($moduleExecutionPath)) { $null } else { $moduleExecutionPath }
            verification_refresh_command = [string]$refreshCommandHint
            allowed_unit_states = @('pending', 'working', 'completed', 'failed', 'blocked')
            pending_module_work_unit_ids = @($pendingModuleWorkUnitIds)
            assigned_module_skill_ids = @($assignedModuleSkillIds)
            required_units = $requiredUnitArray
            preferred_payload = [pscustomobject]@{
                schema_version = 'module_execution_v1'
                source_run_id = if ([string]::IsNullOrWhiteSpace($sourceRunId)) { $null } else { $sourceRunId }
                units = @(
                    foreach ($requiredUnit in $requiredUnitArray) {
                        [pscustomobject]@{
                            unit_id = [string](Get-VibePropertySafe -InputObject $requiredUnit -PropertyName 'unit_id')
                            skill_id = [string](Get-VibePropertySafe -InputObject $requiredUnit -PropertyName 'skill_id')
                            module_id = '<approved module id>'
                            role = 'owner'
                            state = 'completed'
                            result_summary = '<observable result produced for this module>'
                            evidence_paths = @('<existing module evidence path>')
                            verification_results = @()
                        }
                    }
                )
            }
        }
        $incompleteLayers = if (
            $deliverySummary -and
            (Test-VibeObjectHasProperty -InputObject $deliverySummary -PropertyName 'incomplete_layers') -and
            $null -ne $deliverySummary.incomplete_layers
        ) {
            @($deliverySummary.incomplete_layers | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $continuationLines = @(
            'Module work is still pending under governed vibe.',
            ('- gate_result: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($deliveryGateResult)) { 'unknown' } else { $deliveryGateResult })),
            ('- readiness_state: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($deliveryReadinessState)) { 'unknown' } else { $deliveryReadinessState })),
            ('- completion_language_allowed: `{0}`' -f $deliveryCompletionAllowed),
            ('- source_run_id: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($sourceRunId)) { 'unknown' } else { $sourceRunId })),
            ('- module_work_status: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($effectiveExecutionStatus)) { 'unknown' } else { $effectiveExecutionStatus })),
            ('- pending_work_unit_ids: `{0}`' -f $(if (@($pendingModuleWorkUnitIds).Count -gt 0) { @($pendingModuleWorkUnitIds) -join '`, `' } else { 'none recorded' })),
            ('- assigned_skill_ids: `{0}`' -f $(if (@($assignedModuleSkillIds).Count -gt 0) { @($assignedModuleSkillIds) -join '`, `' } else { 'none recorded' })),
            ('- module_execution_path: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($moduleExecutionPath)) { 'unknown' } else { $moduleExecutionPath })),
            '- approved module work has not produced all required observable results yet.',
            '- next required action: complete each pending module work unit, record its result in `module-execution.json`, then refresh governed verification before claiming completion.',
            ('- verification refresh command: `{0}`' -f [string]$refreshCommandHint)
        )
        if (@($incompleteLayers).Count -gt 0) {
            $continuationLines += ('- blocking truth layers: `{0}`' -f (@($incompleteLayers) -join '`, `'))
        }
        $continuationSegment = [pscustomobject]@{
            segment_id = 'execution_handoff'
            stage = 'phase_cleanup'
            category = 'execution'
            truth_layer = 'workflow_completion_truth'
            status = 'current_session_continuation_required'
            gate_status = $deliveryGateResult
            skill_count = @($assignedModuleSkillIds).Count
            skills = @($assignedModuleSkillIds)
            rendered_text = (@($continuationLines) -join "`n")
            host_decision_contract = $executionHandoffContract
        }
        $segments.Add($continuationSegment) | Out-Null
        $renderedSections += 'Governed runtime handoff status:'
        $renderedSections += @('', [string]$continuationSegment.rendered_text)
    }

    if (
        $null -ne $BoundedReturnControl -and
        (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'enabled') -and
        [bool]$BoundedReturnControl.enabled
    ) {
        $allowedFollowupEntryIds = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'allowed_followup_entry_ids') -and
            $null -ne $BoundedReturnControl.allowed_followup_entry_ids
        ) {
            @($BoundedReturnControl.allowed_followup_entry_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $nextStage = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'next_stage') -and
            -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.next_stage)
        ) {
            [string]$BoundedReturnControl.next_stage
        } else {
            $null
        }
        $approvalKind = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'approval_kind') -and
            -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.approval_kind)
        ) {
            [string]$BoundedReturnControl.approval_kind
        } else {
            'user_reentry_confirmation'
        }
        $approvalPrompt = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'approval_prompt') -and
            -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.approval_prompt)
        ) {
            [string]$BoundedReturnControl.approval_prompt
        } else {
            'Return control to the user and wait for an explicit follow-up before continuing.'
        }
        $hostDecisionContract = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'host_decision_contract') -and
            $null -ne $BoundedReturnControl.host_decision_contract
        ) {
            $BoundedReturnControl.host_decision_contract
        } else {
            $null
        }
        $preferredDecisionAction = if (
            $hostDecisionContract -and
            $hostDecisionContract.PSObject.Properties.Name -contains 'preferred_decision_action' -and
            -not [string]::IsNullOrWhiteSpace([string]$hostDecisionContract.preferred_decision_action)
        ) {
            [string]$hostDecisionContract.preferred_decision_action
        } else {
            'approve'
        }
        $workflowLevelConfirmationLines = @()
        if (
            [string]$BoundedReturnControl.terminal_stage -eq 'requirement_doc' -and
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'workflow_level_confirmation') -and
            $null -ne $BoundedReturnControl.workflow_level_confirmation
        ) {
            $workflowLevelConfirmationLines = @(Get-VibeWorkflowLevelConfirmationLines -WorkflowLevelConfirmation $BoundedReturnControl.workflow_level_confirmation)
        }
        $skillSearchGuide = if (
            (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'skill_search_guide') -and
            $null -ne $BoundedReturnControl.skill_search_guide
        ) {
            $BoundedReturnControl.skill_search_guide
        } else {
            $null
        }
        $boundedLines = switch ([string]$BoundedReturnControl.terminal_stage) {
            'requirement_doc' {
                @(
                    '当前已停在需求确认阶段。',
                    '- 请先确认这份需求是否准确；如果需要修改，请直接说明。确认后再进入执行计划。'
                )
            }
            'xl_plan' {
                @(
                    '当前已停在执行计划确认阶段。',
                    '- 请先确认这份计划是否可以执行；如果需要调整，请直接说明。确认后才会进入执行阶段。'
                )
            }
            default {
                @(
                    '当前已停在需要用户确认的阶段。',
                    '- 请先确认是否继续；如果需要修改，请直接说明。'
                )
            }
        }
        if (
            [string]$BoundedReturnControl.terminal_stage -eq 'requirement_doc' -and
            $hostDecisionContract -and
            (Test-VibeObjectHasProperty -InputObject $hostDecisionContract -PropertyName 'agent_skill_organization_contract') -and
            $null -ne $hostDecisionContract.agent_skill_organization_contract
        ) {
            $boundedLines += '- 用户确认需求后、重新进入 canonical Vibe 之前，Agent 必须先按 `bounded_return_control.host_decision_contract.agent_skill_organization_contract` 构造 `host_decision.agent_skill_organization`；不要通过失败重试或读取运行时源码猜字段。'
            $boundedLines += '- 组织 skills 时，不得选择需要安装、推荐或调用 `forbidden_mcp_contract.forbidden_mcp_ids` 中任一 MCP server 的 Skill。'
            $boundedLines += '- Use the directory name that directly contains the retained `SKILL.md` as `skill_id` in `candidate_skill_ids` and `selected_skills[].skill_id`.'
            $boundedLines += '- Do not submit a displayed Skill name or frontmatter `name` as `skill_id`; a nested retained `SKILL.md` uses its own containing directory name.'
        }
        if (@($workflowLevelConfirmationLines).Count -gt 0) {
            $boundedLines += '- 先说明 Agent 会如何找和组织 skills，再解释 L / XL 级别差异：'
            $boundedLines += @(Get-VibeSkillSearchGuideLines -SkillSearchGuide $skillSearchGuide | ForEach-Object { "  $_" })
            $boundedLines += @($workflowLevelConfirmationLines | ForEach-Object { "  $_" })
        }
        $boundedSegment = [pscustomobject]@{
            segment_id = 'bounded_return_control'
            stage = if ((Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'terminal_stage') -and -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.terminal_stage)) { [string]$BoundedReturnControl.terminal_stage } else { $null }
            category = 'runtime_control'
            truth_layer = 'runtime_control'
            status = 'return_control_required'
            gate_status = $null
            skill_count = 0
            skills = @()
            rendered_text = (@($boundedLines) -join "`n")
            control_owner = if ((Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'control_owner') -and -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.control_owner)) { [string]$BoundedReturnControl.control_owner } else { 'user' }
            source_run_id = if ((Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'source_run_id') -and -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.source_run_id)) { [string]$BoundedReturnControl.source_run_id } else { $null }
            reentry_token = if ((Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'reentry_token') -and -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.reentry_token)) { [string]$BoundedReturnControl.reentry_token } else { $null }
            terminal_stage = if ((Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'terminal_stage') -and -not [string]::IsNullOrWhiteSpace([string]$BoundedReturnControl.terminal_stage)) { [string]$BoundedReturnControl.terminal_stage } else { $null }
            next_stage = $nextStage
            approval_kind = $approvalKind
            approval_prompt = $approvalPrompt
            host_decision_contract = $hostDecisionContract
            allowed_followup_entry_ids = @($allowedFollowupEntryIds)
        }
        $segments.Add($boundedSegment) | Out-Null
        if (@($renderedSections).Count -eq 0) {
            $renderedSections += 'Governed runtime host briefing:'
        }
        $renderedSections += @('', [string]$boundedSegment.rendered_text)
    }

    $segmentArray = [object[]]$segments.ToArray()
    if (@($segmentArray).Count -eq 0) {
        return $null
    }

    $hasBoundedReturnControl = (
        $null -ne $BoundedReturnControl -and
        (Test-VibeObjectHasProperty -InputObject $BoundedReturnControl -PropertyName 'enabled') -and
        [bool]$BoundedReturnControl.enabled
    )
    $executionHandoffSegments = @($segmentArray | Where-Object { [string]$_.segment_id -eq 'execution_handoff' })
    $hasExecutionHandoffOnly = (
        @($executionHandoffSegments).Count -gt 0 -and
        @($executionHandoffSegments).Count -eq @($segmentArray).Count
    )
    $failedConsultationSegments = @($segmentArray | Where-Object { [string]$_.category -eq 'consultation' -and [string]$_.status -eq 'gate_failed' })
    $freezeGatePassed = [bool](@($failedConsultationSegments).Count -eq 0)

    return [pscustomobject]@{
        enabled = [bool](@($segmentArray).Count -gt 0)
        mode = if ($hasExecutionHandoffOnly -and -not $hasBoundedReturnControl) {
            'execution_handoff_host_briefing'
        } elseif ($hasBoundedReturnControl) {
            'bounded_return_host_briefing'
        } else {
            'host_user_briefing'
        }
        freeze_gate_passed = $freezeGatePassed
        segment_count = @($segmentArray).Count
        segments = $segmentArray
        rendered_text = (@($renderedSections) -join "`n")
    }
}

function New-VibeRuntimeSummaryProjection {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$ArtifactRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [object]$Artifacts,
        [Parameter(Mandatory)] [object]$RelativeArtifacts,
        [AllowNull()] [object]$StageLineage = $null,
        [AllowNull()] [object]$StorageProjection = $null,
        [AllowNull()] [object]$MemoryActivationReport,
        [AllowNull()] [object]$DeliveryAcceptanceReport,
        [AllowNull()] [object]$HostStageDisclosure = $null,
        [AllowNull()] [object]$HostUserBriefing = $null,
        [AllowNull()] [object]$BoundedReturnControl = $null
    )

    return [pscustomobject]@{
        run_id = $RunId
        governance_scope = [string]$HierarchyState.governance_scope
        mode = $Mode
        task = $Task
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        artifact_root = $ArtifactRoot
        session_root = $SessionRoot
        session_root_relative = Get-VibeRelativePathCompat -BasePath $ArtifactRoot -TargetPath $SessionRoot
        hierarchy = New-VibeHierarchyProjection -HierarchyState $HierarchyState
        stage_order = @(Get-VibeGovernedRuntimeStageOrder)
        executed_stage_order = @(Get-VibeStageLineageExecutedStageOrder -StageLineage $StageLineage)
        terminal_stage = Get-VibeStageLineageTerminalStage -StageLineage $StageLineage
        artifacts = $Artifacts
        storage = $StorageProjection
        memory_activation = New-VibeRuntimeSummaryMemoryActivationProjection -MemoryActivationReport $MemoryActivationReport
        delivery_acceptance = New-VibeRuntimeSummaryDeliveryAcceptanceProjection -DeliveryAcceptanceReport $DeliveryAcceptanceReport
        host_stage_disclosure = $HostStageDisclosure
        host_user_briefing = $HostUserBriefing
        bounded_return_control = $BoundedReturnControl
        artifacts_relative = $RelativeArtifacts
    }
}

function New-VibePythonRuntimeTruthProjection {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [object]$ModuleAssignments,
        [Parameter(Mandatory)] [object]$BaseFields,
        [AllowNull()] [object]$SkillRouting = $null
    )

    $pythonInvocation = Get-VgoPythonCommand
    $scriptPath = Join-Path $RepoRoot 'packages\runtime-core\src\vgo_runtime\canonical_entry.py'
    $runtimeCoreSrc = Join-Path $RepoRoot 'packages\runtime-core\src'
    $contractsSrc = Join-Path $RepoRoot 'packages\contracts\src'
    $inputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("vgo-runtime-truth-" + [System.Guid]::NewGuid().ToString("N") + ".json")
    $outputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("vgo-runtime-truth-" + [System.Guid]::NewGuid().ToString("N") + ".out.json")
    $previousPythonPath = $env:PYTHONPATH

    try {
        Write-VibeJsonArtifact -Path $inputPath -Value ([pscustomobject]@{
            run_id = $RunId
            task = $Task
            module_assignments = $ModuleAssignments
            base_fields = $BaseFields
            skill_routing = $SkillRouting
        })

        $pythonPathEntries = @($runtimeCoreSrc, $contractsSrc)
        if (-not [string]::IsNullOrWhiteSpace($previousPythonPath)) {
            $pythonPathEntries += $previousPythonPath
        }
        $env:PYTHONPATH = ($pythonPathEntries -join [System.IO.Path]::PathSeparator)
        $pythonArgs = @($pythonInvocation.prefix_arguments)
        $pythonArgs += @(
            $scriptPath,
            '--build-runtime-truth-input-json', $inputPath,
            '--output-json-path', $outputPath
        )
        $commandOutput = & $pythonInvocation.host_path @pythonArgs 2>&1
        $commandExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($commandExitCode -ne 0) {
            throw ("Python runtime truth builder exited with code {0}: {1}" -f $commandExitCode, ((@($commandOutput) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine))
        }

        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            throw ("Python runtime truth builder did not write its UTF-8 handoff file: {0}" -f $outputPath)
        }

        $packetText = [System.IO.File]::ReadAllText(
            $outputPath,
            [System.Text.UTF8Encoding]::new($false)
        ).Trim()
        if ([string]::IsNullOrWhiteSpace($packetText)) {
            throw 'Python runtime truth builder returned empty output.'
        }

        return ($packetText | ConvertFrom-Json)
    } finally {
        if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONPATH = $previousPythonPath
        }
        if (Test-Path -LiteralPath $inputPath) {
            Remove-Item -LiteralPath $inputPath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path -LiteralPath $outputPath) {
            Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function ConvertTo-VibeSlug {
    param(
        [AllowEmptyString()] [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return 'task'
    }

    $normalized = $Text.ToLowerInvariant()
    $normalized = [regex]::Replace($normalized, '[^a-z0-9]+', '-')
    $normalized = $normalized.Trim('-')
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return 'task'
    }

    if ($normalized.Length -gt 64) {
        return $normalized.Substring(0, 64).Trim('-')
    }

    return $normalized
}

function Get-VibeTitleFromTask {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $flat = ($Task -replace '\s+', ' ').Trim()
    if ($flat.Length -le 80) {
        return $flat
    }

    return ($flat.Substring(0, 80).Trim() + '...')
}

function Get-VibeArtifactRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$WorkspaceRoot = '',
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $resolvedWorkspaceRoot = if (
        [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and
        $null -ne $Runtime -and
        (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'workspace_root') -and
        -not [string]::IsNullOrWhiteSpace([string]$Runtime.workspace_root)
    ) {
        [string]$Runtime.workspace_root
    } else {
        $WorkspaceRoot
    }
    return [string](New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -WorkspaceRoot $resolvedWorkspaceRoot -Runtime $Runtime -ArtifactRoot $ArtifactRoot).artifact_root
}

function Get-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$WorkspaceRoot = '',
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -Runtime $Runtime -WorkspaceRoot $WorkspaceRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("outputs\runtime\vibe-sessions\{0}" -f $RunId)))
}

function Ensure-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$WorkspaceRoot = '',
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -Runtime $Runtime -WorkspaceRoot $WorkspaceRoot -ArtifactRoot $ArtifactRoot
    New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null
    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        $resolvedWorkspaceRoot = if (
            [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and
            $null -ne $Runtime -and
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'workspace_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.workspace_root)
        ) {
            [string]$Runtime.workspace_root
        } else {
            $WorkspaceRoot
        }
        Initialize-VibeWorkspaceProjectDescriptor -RepoRoot $RepoRoot -WorkspaceRoot $resolvedWorkspaceRoot -Runtime $Runtime | Out-Null
    }
    return $sessionRoot
}

function Write-VibeJsonArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 20
    Write-VgoUtf8NoBomText -Path $Path -Content $json
}

function Write-VibeMarkdownArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [AllowEmptyString()] [string[]]$Lines
    )

    Write-VgoUtf8NoBomText -Path $Path -Content (($Lines -join [Environment]::NewLine) + [Environment]::NewLine)
}

function Get-VibeTaskSignalCount {
    param(
        [Parameter(Mandatory)] [string]$TaskLower,
        [AllowEmptyCollection()] [string[]]$Patterns
    )

    $hits = 0
    foreach ($pattern in @($Patterns)) {
        if (-not [string]::IsNullOrWhiteSpace($pattern) -and (Test-VibeTaskSignalHit -TaskLower $TaskLower -Pattern $pattern)) {
            $hits++
        }
    }

    return $hits
}

function Test-VibeTaskSignalHit {
    param(
        [Parameter(Mandatory)] [string]$TaskLower,
        [Parameter(Mandatory)] [string]$Pattern
    )

    if ([string]::IsNullOrWhiteSpace($TaskLower) -or [string]::IsNullOrWhiteSpace($Pattern)) {
        return $false
    }

    $needle = $Pattern.ToLowerInvariant()
    if ([Regex]::IsMatch($needle, '[\p{IsCJKUnifiedIdeographs}]')) {
        return $TaskLower.Contains($needle)
    }

    $looksLikeSimpleStemPattern = $needle.Contains('*') -and [Regex]::IsMatch($needle, '^[a-z0-9]+\*?([-_\s/]+[a-z0-9]+\*?)*$')
    if ($looksLikeSimpleStemPattern) {
        $tokens = @([Regex]::Split($needle, '[-_\s/]+') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        $tokenPatterns = @()
        foreach ($token in $tokens) {
            $isStem = $token.EndsWith('*')
            $stem = if ($isStem) { $token.TrimEnd('*') } else { $token }
            if ([string]::IsNullOrWhiteSpace($stem)) {
                return $false
            }
            if ($isStem -and $stem.Length -lt 4) {
                return $false
            }
            $escapedStem = [Regex]::Escape($stem)
            if ($isStem) {
                $tokenPatterns += ($escapedStem + '[a-z0-9]*')
            } else {
                $tokenPatterns += $escapedStem
            }
        }
        $boundaryPattern = '(?<![a-z0-9])' + ($tokenPatterns -join '[-_\s/]*') + '(?![a-z0-9])'
        return [Regex]::IsMatch($TaskLower, $boundaryPattern)
    }

    $looksLikeRegex = [Regex]::IsMatch($needle, '[\[\]\(\)\.\*\+\?\|\\]')
    if ($looksLikeRegex) {
        return ($TaskLower -match $needle)
    }

    if ([Regex]::IsMatch($needle, '[a-z0-9]')) {
        $tokens = @([Regex]::Split($needle, '[-_\s/]+') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($tokens.Count -gt 0) {
            $escapedTokens = @($tokens | ForEach-Object { [Regex]::Escape($_) })
            $boundaryPattern = '(?<![a-z0-9])' + ($escapedTokens -join '[-_\s/]*') + '(?![a-z0-9])'
            return [Regex]::IsMatch($TaskLower, $boundaryPattern)
        }
    }

    return $TaskLower.Contains($needle)
}

function Get-VibeTaskTextWithoutExplicitNonCodeClauses {
    param(
        [Parameter(Mandatory)] [string]$TaskLower,
        [AllowEmptyCollection()] [string[]]$ExplicitNonCodePatterns
    )

    $filtered = $TaskLower
    foreach ($pattern in @($ExplicitNonCodePatterns | Sort-Object Length -Descending)) {
        if (-not [string]::IsNullOrWhiteSpace($pattern)) {
            $filtered = [Regex]::Replace(
                $filtered,
                ([Regex]::Escape($pattern) + '[^。！？!?；;\r\n]*'),
                ' '
            )
        }
    }
    return $filtered
}

function Get-VibeAffirmativeTaskSignalCount {
    param(
        [Parameter(Mandatory)] [string]$TaskLower,
        [AllowEmptyCollection()] [string[]]$Patterns
    )

    $actionText = [Regex]::Replace($TaskLower, '`[^`\r\n]*`|“[^”\r\n]*”|\u2018[^\u2019\r\n]*\u2019', ' ')
    $actionText = [Regex]::Replace(
        $actionText,
        '\b(?:no|never|without|(?:do|must|should)\s+not|don''t|doesn''t|didn''t|can''t|cannot|won''t|shouldn''t|mustn''t)\b[^.!?;。！？；\r\n]*',
        ' '
    )
    $quotedActionPatterns = @(
        'debug', 'fix', 'repair', 'patch', 'triage', 'diagnose', 'diagnosed', 'diagnosing',
        '修复', '调试', '排查', '定位',
        'implement', 'build', 'upgrade', 'update', 'enhance', 'modify', 'change', 'create',
        'add', 'integrate', 'install', 'refactor',
        '更新', '增强', '实现', '修改', '安装', '集成', '添加单元测试'
    )
    $quotedActionRegex = '请(?:完成|处理)\s*(?:“(?<double>[^”\r\n]*)”|\u2018(?<single>[^\u2019\r\n]*)\u2019)'
    foreach ($quotedActionMatch in [Regex]::Matches($TaskLower, $quotedActionRegex)) {
        $content = if ($quotedActionMatch.Groups['double'].Success) {
            [string]$quotedActionMatch.Groups['double'].Value
        } else {
            [string]$quotedActionMatch.Groups['single'].Value
        }
        $content = $content.Trim()
        $startsWithAction = $false
        foreach ($quotedActionPattern in $quotedActionPatterns) {
            if ([Regex]::IsMatch($quotedActionPattern, '[\p{IsCJKUnifiedIdeographs}]')) {
                if ($content.StartsWith($quotedActionPattern, [System.StringComparison]::Ordinal)) {
                    $startsWithAction = $true
                    break
                }
            } elseif ([Regex]::IsMatch($content, ('^' + [Regex]::Escape($quotedActionPattern) + '(?=$|[^a-z0-9])'))) {
                $startsWithAction = $true
                break
            }
        }
        if ($startsWithAction -and -not [Regex]::IsMatch($content, '\.[a-z0-9]{1,10}$')) {
            $actionText += (' ' + $content)
        }
    }
    $actionText = [Regex]::Replace(
        $actionText,
        '\b(?:create\s+(?:a\s+)?(?:word|pdf)\s+report|build\s+(?:an?\s+)?excel\s+workbook|add\s+slides|modify\s+report)\b',
        ' ',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    $hits = 0
    $negativeSuffixes = @('不要', '无需', '无须', '禁止', '不得', '不', '已')
    foreach ($pattern in @($Patterns)) {
        if ([string]::IsNullOrWhiteSpace($pattern)) {
            continue
        }
        $needle = $pattern.ToLowerInvariant()
        $matchPattern = if ([Regex]::IsMatch($needle, '[\p{IsCJKUnifiedIdeographs}]')) {
            [Regex]::Escape($needle)
        } else {
            '(?<![a-z0-9])' + [Regex]::Escape($needle) + '(?![a-z0-9])'
        }
        $affirmative = $false
        foreach ($match in [Regex]::Matches($actionText, $matchPattern)) {
            $before = if ($match.Index -gt 0) { [string]$actionText[$match.Index - 1] } else { '' }
            $afterIndex = $match.Index + $match.Length
            $after = if ($afterIndex -lt $actionText.Length) { [string]$actionText[$afterIndex] } else { '' }
            if (
                (-not [string]::IsNullOrEmpty($before) -and '\/_-.'.Contains($before)) -or
                (-not [string]::IsNullOrEmpty($after) -and '\/_-.'.Contains($after))
            ) {
                continue
            }
            if ($needle -eq '安装' -and $after -eq '的') {
                continue
            }
            $prefix = $actionText.Substring(0, $match.Index).TrimEnd()
            $negated = $false
            foreach ($suffix in $negativeSuffixes) {
                if ($prefix.EndsWith($suffix, [System.StringComparison]::Ordinal)) {
                    $negated = $true
                    break
                }
            }
            if (
                $negated -or
                [Regex]::IsMatch($prefix, '(?:不要|无需|无须|禁止|不得|不|已)(?:再|擅自|直接|继续|主动|随意|自行|额外|重新|重复)?\s*$') -or
                [Regex]::IsMatch($prefix, '(?:\b(?:no|not|never|without|already|forbidden)\s*|\b(?:don''t|doesn''t|didn''t|can''t|cannot|won''t|shouldn''t|mustn''t)\s*|\b(?:do|must|should)\s+not\s*)$')
            ) {
                continue
            }
            $affirmative = $true
            break
        }
        if ($affirmative) {
            $hits++
        }
    }
    return $hits
}

function Get-VibeInferredTaskType {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $taskLower = $Task.ToLowerInvariant()
    $routerDiagnosticContextPatterns = @(
        'router',
        'routing',
        'misroute'
    )
    $routerDiagnosticPatterns = @(
        'fallback',
        'threshold',
        'confidence',
        'candidate[-_ ]scor',
        'grade[-_ ]selection',
        'task[-_ ]classification'
    )
    $reviewPatterns = @(
        'review',
        'code review',
        'pr review',
        'audit',
        'assess',
        '审查',
        '评审',
        '审核',
        '代码评审'
    )
    $debugPatterns = @(
        'debug',
        'bug',
        'fix',
        'repair',
        'patch',
        'issue',
        'problem',
        'failure',
        'failing',
        'regression',
        'root cause',
        'diagnos*',
        'triage',
        'mismatch',
        'misroute',
        'inaccurate',
        'friction',
        'error',
        '错误',
        '修复',
        '调试',
        '问题',
        '失败',
        '报错',
        '排查',
        '定位',
        '根因',
        '回退',
        '回滚',
        '低置信度',
        '误路由'
    )
    $researchPatterns = @(
        'research',
        'survey',
        'literature',
        'paper',
        'investigate',
        'read',
        'analysis',
        'analyze',
        'compare',
        '调研',
        '研究',
        '检索',
        '分析',
        '比较',
        '梳理',
        '综述'
    )
    $codingPatterns = @(
        'implement',
        'build',
        'upgrade',
        'update',
        'enhance',
        'modify',
        'change',
        'create',
        'add',
        'integrate',
        'integration',
        'install',
        'refactor',
        'runtime',
        'router',
        'routing',
        '更新',
        '增强',
        '实现',
        '修改',
        '安装',
        '集成',
        '运行时',
        '路由',
        '工作流'
    )
    $explicitNonCodePatterns = @(
        '不需要写代码',
        '不需要代码',
        '不写代码',
        '不要写代码',
        '不要把写代码',
        '不要注入代码',
        '不做代码',
        '无需写代码',
        'does not require code',
        'no code',
        'without code'
    )
    $affirmativeDebugPatterns = @(
        'debug',
        'fix',
        'repair',
        'patch',
        'triage',
        'diagnose',
        'diagnosed',
        'diagnosing',
        '修复',
        '调试',
        '排查',
        '定位'
    )
    $affirmativeCodingPatterns = @(
        'implement',
        'build',
        'upgrade',
        'update',
        'enhance',
        'modify',
        'change',
        'create',
        'add',
        'integrate',
        'install',
        'refactor',
        '更新',
        '增强',
        '实现',
        '修改',
        '安装',
        '集成',
        '添加单元测试'
    )
    $debugContextPatterns = @(
        $debugPatterns | Where-Object { $_ -notin $affirmativeDebugPatterns }
    )
    $strongCodingActionPatterns = @(
        'implement',
        'build',
        'refactor',
        '实现',
        '添加单元测试',
        '修改代码'
    )
    $taskWithoutLiterals = [Regex]::Replace($taskLower, '`[^`\r\n]*`|“[^”\r\n]*”|\u2018[^\u2019\r\n]*\u2019', ' ')
    $affirmativeDebugScore = Get-VibeAffirmativeTaskSignalCount -TaskLower $taskLower -Patterns $affirmativeDebugPatterns
    $reviewScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $reviewPatterns
    $debugScore = [Math]::Max(
        (Get-VibeTaskSignalCount -TaskLower $taskWithoutLiterals -Patterns $debugContextPatterns),
        $affirmativeDebugScore
    )
    $researchScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $researchPatterns
    $codingScore = Get-VibeAffirmativeTaskSignalCount -TaskLower $taskLower -Patterns $affirmativeCodingPatterns
    $explicitNonCode = (Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $explicitNonCodePatterns) -gt 0
    $routerContextScore = Get-VibeTaskSignalCount -TaskLower $taskWithoutLiterals -Patterns $routerDiagnosticContextPatterns
    if ($routerContextScore -gt 0) {
        $routerDebugScore = Get-VibeTaskSignalCount -TaskLower $taskWithoutLiterals -Patterns $routerDiagnosticPatterns
        if ($routerDebugScore -gt $debugScore) {
            $debugScore = $routerDebugScore
        }
    }
    if (
        $codingScore -gt 0 -and
        $codingScore -eq $researchScore -and
        (
            (Get-VibeAffirmativeTaskSignalCount -TaskLower $taskLower -Patterns $strongCodingActionPatterns) -gt 0 -or
            [Regex]::IsMatch($taskLower, '\b(?:update|modify|change)\s+(?:the\s+)?[a-z0-9_./\\-]+\.py\b')
        )
    ) {
        $codingScore++
    }
    if ($affirmativeDebugScore -gt 0) {
        $debugScore = [Math]::Max($debugScore, [Math]::Max($codingScore, $affirmativeDebugScore))
    }
    if ($explicitNonCode) {
        $scopedTaskLower = Get-VibeTaskTextWithoutExplicitNonCodeClauses `
            -TaskLower $taskLower `
            -ExplicitNonCodePatterns $explicitNonCodePatterns
        $codingScore = Get-VibeAffirmativeTaskSignalCount -TaskLower $scopedTaskLower -Patterns $affirmativeCodingPatterns
        $debugScore = Get-VibeAffirmativeTaskSignalCount -TaskLower $scopedTaskLower -Patterns $affirmativeDebugPatterns
        if (
            $codingScore -gt 0 -and
            $codingScore -eq $researchScore -and
            (
                (Get-VibeAffirmativeTaskSignalCount -TaskLower $scopedTaskLower -Patterns $strongCodingActionPatterns) -gt 0 -or
                [Regex]::IsMatch($scopedTaskLower, '\b(?:update|modify|change)\s+(?:the\s+)?[a-z0-9_./\\-]+\.py\b')
            )
        ) {
            $codingScore++
        }
        if ($debugScore -gt 0) {
            $debugScore = [Math]::Max($debugScore, $codingScore)
        }
        $scopedRouterContextScore = Get-VibeTaskSignalCount -TaskLower $scopedTaskLower -Patterns $routerDiagnosticContextPatterns
        if ($debugScore -gt 0 -and $scopedRouterContextScore -gt 0) {
            $debugScore = [Math]::Max(
                $debugScore,
                (Get-VibeTaskSignalCount -TaskLower $scopedTaskLower -Patterns $routerDiagnosticPatterns)
            )
        }
    }
    $scores = [ordered]@{
        review = $reviewScore
        debug = $debugScore
        research = $researchScore
        coding = $codingScore
    }

    $maxScore = ($scores.Values | Measure-Object -Maximum).Maximum
    if ($null -eq $maxScore -or [double]$maxScore -le 0) {
        return 'planning'
    }

    foreach ($taskType in @('review', 'debug', 'research', 'coding')) {
        if ([double]$scores[$taskType] -eq [double]$maxScore) {
            return $taskType
        }
    }

    return 'planning'
}

function Get-VibeInternalGrade {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$RequestedGradeFloor = ''
    )

    $grade = ''
    $taskLower = $Task.ToLowerInvariant()
    $inferredTaskType = Get-VibeInferredTaskType -Task $Task
    $xlPatterns = @(
        'multi-agent',
        'parallel',
        'wave',
        'batch',
        '无人值守',
        'autonomous',
        'benchmark',
        'front.*back',
        'end-to-end',
        '\be2e\b',
        'cross-host',
        'multi-host',
        'host-native',
        'install.*runtime',
        'runtime.*install',
        'from install to runtime',
        '从安装到运行',
        '全链路',
        '端到端'
    )
    $compositeDeliveryPatternGroups = [object[]]@(
        [string[]]@('data quality audit', 'quality audit', '数据质量审计', '数据审计', '质量审计'),
        [string[]]@('cleaned data', 'clean data', '清洗数据'),
        [string[]]@('reproducible script', 'analysis script', 'script', '脚本'),
        [string[]]@('summary table', 'analysis table', '汇总表', '分析表'),
        [string[]]@('png chart', 'chart', 'plot', '图表'),
        [string[]]@('markdown report', 'word report', 'report', '报告'),
        [string[]]@('verification evidence', 'validation evidence', '验证证据')
    )
    $planningPatterns = @(
        'design',
        'plan',
        'architecture',
        'refactor',
        'migrate',
        'research',
        'governance',
        'debug',
        'bug',
        'fix',
        'repair',
        'patch',
        'review',
        'code review',
        'implement',
        'build',
        'upgrade',
        'update',
        'modify',
        'change',
        'install',
        'integrat',
        'router',
        'routing',
        'runtime',
        'workflow',
        'contract',
        'gate',
        'regression',
        'verification',
        'threshold',
        'confidence',
        'classification',
        'candidate[-_ ]scor',
        'heuristic',
        'windows',
        '访谈',
        '规划',
        '设计',
        '治理',
        '修复',
        '修改',
        '安装',
        '调试',
        '评审',
        '运行时',
        '路由',
        '工作流',
        '契约',
        '回归',
        '验证',
        '阈值',
        '置信度',
        '分类',
        '评分'
    )
    $planningPriorityPatterns = @(
        'quality gate',
        'freshness gate',
        'prd',
        'backlog',
        'roadmap',
        'acceptance criteria',
        'user story',
        '用户故事',
        '验收标准'
    )
    $workflowChoicePattern = '(?<![a-z0-9])(?:l(?:\s*级)?(?:\s*(?:/|\||or|and|vs\.?|与|和|或|还是)\s*|\s+)xl(?:\s*级)?|xl(?:\s*级)?(?:\s*(?:/|\||or|and|vs\.?|与|和|或|还是)\s*|\s+)l(?:\s*级)?)(?![a-z0-9])'
    $workflowChoiceSeen = [Regex]::IsMatch($taskLower, $workflowChoicePattern)
    $taskWithoutWorkflowChoice = [Regex]::Replace($taskLower, $workflowChoicePattern, ' ')
    $taskWithoutWorkflowChoice = [Regex]::Replace($taskWithoutWorkflowChoice, '(?<![a-z0-9])xl[_-]plan(?![a-z0-9])', ' ')
    $taskWithoutNonEscalation = [Regex]::Replace(
        $taskWithoutWorkflowChoice,
        '(?:不要|请勿)\s*(?:升级|升到|提升)(?:\s*到|\s*为)?\s*xl(?:\s*级)?',
        ' '
    )

    if ([Regex]::IsMatch($taskWithoutNonEscalation.TrimEnd('.'), '(?<![a-z0-9\\/_\-.])xl(?![a-z0-9\\/_\-.])')) {
        $grade = 'XL'
    }

    $taskForXlSignals = [Regex]::Replace(
        $taskLower,
        '\bdo\s+not\s+use\b[^.!?;。！？；\r\n]*',
        ' '
    )
    foreach ($pattern in $xlPatterns) {
        if (-not $grade -and (Test-VibeTaskSignalHit -TaskLower $taskForXlSignals -Pattern $pattern)) {
            $grade = 'XL'
            break
        }
    }

    if (-not $grade -and $inferredTaskType -eq 'research') {
        $compositeTask = [Regex]::Replace(
            $taskLower,
            '\bdo\s+not\s+(?:produce|generate)\b[^.!?;。！？；\r\n]*',
            ' '
        )
        $compositeTask = [Regex]::Replace(
            $compositeTask,
            '(?<![a-z0-9])(?:script\.md|chart\.png|report\.md)(?![a-z0-9])',
            ' '
        )
        $compositeDeliverySignalCount = 0
        foreach ($patternGroup in $compositeDeliveryPatternGroups) {
            if ((Get-VibeTaskSignalCount -TaskLower $compositeTask -Patterns ([string[]]$patternGroup)) -gt 0) {
                $compositeDeliverySignalCount++
            }
        }
        if ($compositeDeliverySignalCount -ge 3) {
            $grade = 'XL'
        }
    }

    $explicitLRequestSeen = [Regex]::IsMatch(
        $taskWithoutNonEscalation,
        '(?:按|采用|使用|保持)\s*l(?:\s*级)?(?:\s*处理)?'
    )
    if (-not $grade -and ($workflowChoiceSeen -or $explicitLRequestSeen)) {
        $grade = 'L'
    }

    if (-not $grade -and $inferredTaskType -in @('coding', 'debug', 'review', 'research')) {
        $grade = 'L'
    }

    if (-not $grade) {
        $planningSignalCount = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $planningPatterns
        $planningPrioritySignalCount = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $planningPriorityPatterns
        if ($planningSignalCount -ge 2 -or $planningPrioritySignalCount -gt 0) {
            $grade = 'L'
        }
    }

    if (-not $grade -and $Task.Length -gt 180) {
        $grade = 'L'
    }

    if (-not $grade) {
        $grade = 'M'
    }

    $requestedFloor = [string]$RequestedGradeFloor
    if (-not [string]::IsNullOrWhiteSpace($requestedFloor)) {
        $normalizedFloor = $requestedFloor.Trim().ToUpperInvariant()
        $rank = @{
            'M' = 0
            'L' = 1
            'XL' = 2
        }
        if (-not $rank.ContainsKey($normalizedFloor)) {
            throw ("unsupported requested grade floor: {0}" -f $RequestedGradeFloor)
        }
        if ($rank[$normalizedFloor] -gt $rank[$grade]) {
            $grade = $normalizedFloor
        }
    }

    return $grade
}

function New-VibeIntentContractObject {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Mode,
        [AllowNull()] [object]$HostDecision = $null
    )

    $Mode = Resolve-VibeRuntimeMode -Mode $Mode
    $title = Get-VibeTitleFromTask -Task $Task
    $grade = Get-VibeInternalGrade -Task $Task
    $recommendedWorkflowLevel = if ([string]$grade -eq 'XL') { 'XL' } else { 'L' }
    $workflowLevelRecommendationReason = if ($recommendedWorkflowLevel -eq 'XL') {
        '当前任务看起来更像高协调成本交付：需要先冻结需求和计划，再把多技能或多产物工作拆成分波次执行，避免执行中途再回头重排分工。'
    } else {
        '当前任务更像单主线交付：先冻结需求和计划，再让 Agent 按模块组织一个较轻量的 skills 方案，通常比一开始就上分波次协作更省沟通成本。'
    }
    $taskType = Get-VibeInferredTaskType -Task $Task
    $signalText = $Task.ToLowerInvariant()
    $explicitArtifactReviewRequirements = Get-VibeNormalizedStringList -Values $(if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'artifact_review_requirements')) { $HostDecision.artifact_review_requirements } else { @() })
    $baselineDocumentQualityDimensions = if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'baseline_document_quality_dimensions')) {
        $explicitBaselineDocumentQualityDimensions = Get-VibeNormalizedStringList -Values $HostDecision.baseline_document_quality_dimensions
        @($explicitBaselineDocumentQualityDimensions)
    } else {
        @()
    }
    $artifactReviewRequirements = if (@($explicitArtifactReviewRequirements).Count -gt 0) {
        @($explicitArtifactReviewRequirements)
    } else {
        @()
    }
    $baselineUiQualityDimensions = if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'baseline_ui_quality_dimensions')) {
        $explicitBaselineUiQualityDimensions = Get-VibeNormalizedStringList -Values $HostDecision.baseline_ui_quality_dimensions
        @($explicitBaselineUiQualityDimensions)
    } else {
        @()
    }
    $assumptions = @()
    $assumptions += 'Interactive clarification is allowed if unresolved ambiguity materially changes the requested outcome.'
    $workflowLevelSkills = if ($taskType -in @('coding', 'debug')) {
        '会先按模块搜索本地 skills、阅读候选 `SKILL.md`，再给出较轻量的 L 级组织方案；涉及代码改动或缺陷修复时，会补充 `tdd` 这类 failure-first 验证 skill，但不默认拆成多代理。'
    } else {
        '会先按模块搜索本地 skills、阅读候选 `SKILL.md`，再给出较轻量的 L 级组织方案；不会给非代码任务附加代码开发验证流程。'
    }
    $codeTaskTddDecision = Resolve-VibeCodeTaskTddDecision `
        -HostDecision $HostDecision `
        -Task $Task `
        -TaskType $taskType `
        -HeuristicRequiresTdd ($taskType -in @('coding', 'debug')) `
        -DocumentArtifactBaseline (@($baselineDocumentQualityDimensions).Count -gt 0)
    $deliverable = if (
        $null -ne $HostDecision -and
        (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'deliverable') -and
        -not [string]::IsNullOrWhiteSpace([string]$HostDecision.deliverable)
    ) {
        [string]$HostDecision.deliverable
    } else {
        'The user-requested outcome described in the full goal, with supporting evidence appropriate to that outcome'
    }
    $constraints = if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'constraints')) {
        @(Get-VibeNormalizedStringList -Values $HostDecision.constraints)
    } else {
        @(
            'Do not bypass the fixed six-stage governed runtime.',
            'Do not widen scope silently beyond the frozen requirement document.'
        )
    }
    $acceptanceCriteria = if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'acceptance_criteria')) {
        @(Get-VibeNormalizedStringList -Values $HostDecision.acceptance_criteria)
    } else {
        @(
            'Requirement document is frozen before execution.',
            'Execution plan exists before task execution.',
            'Verification evidence exists before completion claims.',
            'Phase cleanup receipt is produced.'
        )
    }
    $nonGoals = if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'non_goals')) {
        @(Get-VibeNormalizedStringList -Values $HostDecision.non_goals)
    } else {
        @(
            'Do not create separate M/L/XL entry commands.',
            'Do not introduce a second router or control plane.'
        )
    }
    $taskSpecificAcceptanceExtensions = Get-VibeNormalizedStringList -Values $(if ($null -ne $HostDecision -and (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'task_specific_acceptance_extensions')) { $HostDecision.task_specific_acceptance_extensions } else { @() })
    return [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        title = $title
        goal = $Task
        deliverable = $deliverable
        constraints = @($constraints)
        acceptance_criteria = @($acceptanceCriteria)
        non_goals = @($nonGoals)
        artifact_review_requirements = @($artifactReviewRequirements)
        baseline_document_quality_dimensions = @($baselineDocumentQualityDimensions)
        baseline_ui_quality_dimensions = @($baselineUiQualityDimensions)
        task_specific_acceptance_extensions = @($taskSpecificAcceptanceExtensions)
        code_task_tdd_decision = $codeTaskTddDecision
        workflow_level_confirmation = [pscustomobject]@{
            enabled = $true
            user_visible = $true
            required_for_levels = @('L', 'XL')
            recommended_level = [string]$recommendedWorkflowLevel
            recommendation_reason = $workflowLevelRecommendationReason
            question = '先确认任务级别：这次任务走 L 级还是 XL 级？'
            decision_importance = 'L 和 XL 会直接改变后续的协作深度、是否进入分波次执行，以及证据和回归边界的强度。'
            levels = [pscustomobject]@{
                L = 'L 级适合多步骤但主要串行的工作：会确认需求和计划，证据要求完整，但一般由一个主流程推进。'
                XL = 'XL 级适合研究交付、多产物、多技能协作或风险更高的任务：会有更严格的需求冻结、计划冻结、分阶段执行、证据清单和收尾检查。'
            }
            level_details = [pscustomobject]@{
                L = [pscustomobject]@{
                    workflow = '先冻结需求和计划，再由一个主流程串行推进 Agent 组织出的方案。'
                    skills = $workflowLevelSkills
                    why_this_fit = '适合仍然是一个主交付物、依赖链较短、并行收益不高的任务，可以把沟通成本压低，同时保留完整的冻结与验证边界。'
                    confirm_reply = '如果你认可这个较轻量但证据完整的流程，请回复：`走 L 级`。'
                }
                XL = [pscustomobject]@{
                    workflow = '先冻结需求和计划，再把 Agent 组织出的方案拆成分波次执行；只有在依赖安全时才允许小步并行，最后统一回到验证和收尾。'
                    skills = '会先按模块组织更完整的本地 Skills；确需多代理时，由当前 Agent 依据已冻结计划分波次协调，不额外假定一个协调 Skill。'
                    why_this_fit = '适合多产物、多技能协作、研究交付或高风险改动，因为它能先讲清分工、阶段边界和证据清单，再进入执行。'
                    confirm_reply = '如果你希望先把分工和波次讲清楚，再进入更重的执行流程，请回复：`走 XL 级`。'
                }
            }
            selection_prompt = '请根据上面的说明选择并确认这次任务级别。'
        }
        risk_tolerance = 'moderate'
        autonomy_mode = $Mode
        open_questions = @()
        inference_notes = @(
            'This contract was derived from the raw task text.',
            'Interactive mode may still surface explicit clarification questions outside the script path.'
        )
        assumptions = @($assumptions)
        internal_grade = $grade
        source_task = $Task
    }
}

function Get-VibeRequirementDocPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\requirements\{0}-{1}.md" -f $date, $slug)))
}

function Get-VibeExecutionPlanPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\plans\{0}-{1}-execution-plan.md" -f $date, $slug)))
}

function Get-VibeRuntimeInputPacketPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $sessionRoot 'runtime-input-packet.json'))
}
