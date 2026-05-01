Set-StrictMode -Off
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

# Alias for compatibility with VibeExecution.Common.ps1 which calls Get-VibeHostAdapterIdentityProjection
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

function Get-VibeRuntimeSelectedSkillExecutionProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    if (
        $null -eq $RuntimeInputPacket -or
        -not (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'skill_routing') -or
        $null -eq $RuntimeInputPacket.skill_routing -or
        -not (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.skill_routing -PropertyName 'selected')
    ) {
        return $null
    }

    $selectedSkillExecution = [object[]]@($RuntimeInputPacket.skill_routing.selected)
    $specialistDecision = if (
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'specialist_decision') -and
        $null -ne $RuntimeInputPacket.specialist_decision
    ) {
        $RuntimeInputPacket.specialist_decision
    } else {
        $null
    }
    $blockedSkillIds = if (
        $null -ne $specialistDecision -and
        (Test-VibeObjectHasProperty -InputObject $specialistDecision -PropertyName 'blocked_skill_ids') -and
        $null -ne $specialistDecision.blocked_skill_ids
    ) {
        @($specialistDecision.blocked_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @()
    }
    $degradedSkillIds = if (
        $null -ne $specialistDecision -and
        (Test-VibeObjectHasProperty -InputObject $specialistDecision -PropertyName 'degraded_skill_ids') -and
        $null -ne $specialistDecision.degraded_skill_ids
    ) {
        @($specialistDecision.degraded_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @()
    }
    $nonExecutableSkillIds = @(@($blockedSkillIds) + @($degradedSkillIds)) | Select-Object -Unique
    $directSelectedSkillExecution = [object[]]@($selectedSkillExecution | Where-Object {
            $skillId = [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
            [string]::IsNullOrWhiteSpace($skillId) -or ($skillId -notin @($nonExecutableSkillIds))
        })
    $blockedSkillExecution = [object[]]@($selectedSkillExecution | Where-Object {
            $skillId = [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
            -not [string]::IsNullOrWhiteSpace($skillId) -and ($skillId -in @($blockedSkillIds))
        })
    $degradedSkillExecution = [object[]]@($selectedSkillExecution | Where-Object {
            $skillId = [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
            -not [string]::IsNullOrWhiteSpace($skillId) -and ($skillId -in @($degradedSkillIds))
        })
    if (@($selectedSkillExecution).Count -eq 0 -and $null -eq $specialistDecision) {
        return $null
    }

    $selectedSkillIds = @($directSelectedSkillExecution | ForEach-Object {
        [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_id' -DefaultValue '')
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    return [pscustomobject]@{
        selected_skill_execution = [object[]]@($directSelectedSkillExecution)
        blocked_skill_execution = [object[]]@($blockedSkillExecution)
        degraded_skill_execution = [object[]]@($degradedSkillExecution)
        selected_skill_ids = @($selectedSkillIds)
        blocked_skill_ids = @($blockedSkillIds)
        degraded_skill_ids = @($degradedSkillIds)
        surfaced_skill_ids = @($selectedSkillIds)
        matched_skill_ids = @($selectedSkillIds)
        ghost_match_skill_ids = @()
        escalation_required = $false
        escalation_status = 'not_required'
        status = 'derived_from_skill_routing_selected'
        source = 'skill_routing.selected'
    }
}

function Get-VibeRuntimeSpecialistRecommendations {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    if (
        $null -ne $RuntimeInputPacket -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'skill_routing') -and
        $null -ne $RuntimeInputPacket.skill_routing -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.skill_routing -PropertyName 'selected')
    ) {
        $selected = [object[]]@($RuntimeInputPacket.skill_routing.selected)
        if (@($selected).Count -gt 0) {
            return $selected
        }
    }

    if (
        $null -ne $RuntimeInputPacket -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'skill_routing') -and
        $null -ne $RuntimeInputPacket.skill_routing -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.skill_routing -PropertyName 'candidates')
    ) {
        return [object[]]@($RuntimeInputPacket.skill_routing.candidates)
    }

    return @()
}

function Get-VibeRuntimeStageAssistantHints {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null
    )

    return @()
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

function Get-VibeHostSkillExecutionContract {
    param(
        [AllowNull()] [object]$Policy = $null
    )

    $dispatchPolicy = $null
    if ($null -ne $Policy -and (Test-VibeObjectHasProperty -InputObject $Policy -PropertyName 'host_skill_execution_contract')) {
        $dispatchPolicy = $Policy.host_skill_execution_contract
    }

    $selectionModes = if (
        $null -ne $dispatchPolicy -and
        (Test-VibeObjectHasProperty -InputObject $dispatchPolicy -PropertyName 'selection_modes') -and
        $null -ne $dispatchPolicy.selection_modes
    ) {
        @(Get-VibeNormalizedStringList -Values $dispatchPolicy.selection_modes)
    } else {
        @('inherit_runtime_default', 'curated_only')
    }
    if (@($selectionModes).Count -eq 0) {
        $selectionModes = @('inherit_runtime_default', 'curated_only')
    }

    $defaultSelectionMode = if (
        $null -ne $dispatchPolicy -and
        (Test-VibeObjectHasProperty -InputObject $dispatchPolicy -PropertyName 'default_selection_mode') -and
        -not [string]::IsNullOrWhiteSpace([string]$dispatchPolicy.default_selection_mode)
    ) {
        [string]$dispatchPolicy.default_selection_mode
    } else {
        'inherit_runtime_default'
    }
    if ($defaultSelectionMode -notin $selectionModes) {
        $defaultSelectionMode = 'inherit_runtime_default'
    }

    return [pscustomobject]@{
        enabled = if ($null -ne $dispatchPolicy -and (Test-VibeObjectHasProperty -InputObject $dispatchPolicy -PropertyName 'enabled')) { [bool]$dispatchPolicy.enabled } else { $true }
        scope = if ($null -ne $dispatchPolicy -and (Test-VibeObjectHasProperty -InputObject $dispatchPolicy -PropertyName 'scope') -and -not [string]::IsNullOrWhiteSpace([string]$dispatchPolicy.scope)) { [string]$dispatchPolicy.scope } else { 'root_only' }
        selection_modes = @($selectionModes)
        default_selection_mode = [string]$defaultSelectionMode
    }
}

function Resolve-VibeHostSpecialistDispatchDecision {
    param(
        [AllowNull()] [object]$HostDecision = $null,
        [AllowNull()] [object[]]$Recommendations = @(),
        [AllowEmptyString()] [string]$GovernanceScope = '',
        [AllowNull()] [object]$Policy = $null
    )

    $contract = Get-VibeHostSkillExecutionContract -Policy $Policy
    if (-not [bool]$contract.enabled) {
        return $null
    }
    if ($null -eq $HostDecision -or -not (Test-VibeObjectHasProperty -InputObject $HostDecision -PropertyName 'specialist_dispatch_decision')) {
        return $null
    }

    $decision = Get-VibePropertySafe -InputObject $HostDecision -PropertyName 'specialist_dispatch_decision'
    if ($null -eq $decision) {
        return $null
    }
    if (-not (Test-VibeStructuredObject -InputObject $decision)) {
        throw 'structured host specialist dispatch decision must be a JSON object'
    }
    if ([string]$contract.scope -eq 'root_only' -and -not [string]::Equals([string]$GovernanceScope, 'root', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'structured host specialist dispatch decision is currently supported only in root governance scope'
    }

    $selectionMode = if (
        (Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'selection_mode') -and
        -not [string]::IsNullOrWhiteSpace([string](Get-VibePropertySafe -InputObject $decision -PropertyName 'selection_mode'))
    ) {
        [string](Get-VibePropertySafe -InputObject $decision -PropertyName 'selection_mode')
    } else {
        [string]$contract.default_selection_mode
    }
    if ($selectionMode -notin @($contract.selection_modes)) {
        throw ('structured host specialist dispatch decision selection_mode `{0}` is not supported' -f $selectionMode)
    }

    $approvedSkillIds = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'approved_skill_ids') { $decision.approved_skill_ids } else { @() }))
    $deferredSkillIds = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'deferred_skill_ids') { $decision.deferred_skill_ids } else { @() }))
    $rejectedSkillIds = @(Get-VibeNormalizedStringList -Values $(if (Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'rejected_skill_ids') { $decision.rejected_skill_ids } else { @() }))

    $duplicateSkillIds = @(
        @($approvedSkillIds | Where-Object { $_ -in $deferredSkillIds }) +
        @($approvedSkillIds | Where-Object { $_ -in $rejectedSkillIds }) +
        @($deferredSkillIds | Where-Object { $_ -in $rejectedSkillIds })
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
    if (@($duplicateSkillIds).Count -gt 0) {
        throw ('structured host specialist dispatch decision contains duplicate skill ids across decision lists: {0}' -f [string]::Join(', ', @($duplicateSkillIds)))
    }

    $surfacedSkillIds = @($Recommendations | ForEach-Object {
        if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $explicitSkillIds = @(@($approvedSkillIds) + @($deferredSkillIds) + @($rejectedSkillIds) | Select-Object -Unique)
    $unknownSkillIds = @($explicitSkillIds | Where-Object { $_ -notin $surfacedSkillIds })
    if (@($unknownSkillIds).Count -gt 0) {
        $approvedSkillIds = @($approvedSkillIds | Where-Object { $_ -in $surfacedSkillIds })
        $deferredSkillIds = @($deferredSkillIds | Where-Object { $_ -in $surfacedSkillIds })
        $rejectedSkillIds = @($rejectedSkillIds | Where-Object { $_ -in $surfacedSkillIds })
    }
    $effectiveSelectionMode = if (@($unknownSkillIds).Count -gt 0 -and @($explicitSkillIds).Count -gt 0) {
        'curated_only'
    } else {
        [string]$selectionMode
    }
    $validExplicitSkillIds = @(@($approvedSkillIds) + @($deferredSkillIds) + @($rejectedSkillIds) | Select-Object -Unique)
    $requiresRecuration = (@($unknownSkillIds).Count -gt 0 -and @($validExplicitSkillIds).Count -eq 0 -and [string]$effectiveSelectionMode -eq 'curated_only')
    $reconciliationState = if (@($unknownSkillIds).Count -eq 0) {
        'current'
    } elseif ($requiresRecuration) {
        'stale_recuration_required'
    } else {
        'partial_reconciled'
    }

    return [pscustomobject]@{
        protocol_version = if ((Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'protocol_version') -and -not [string]::IsNullOrWhiteSpace([string]$decision.protocol_version)) { [string]$decision.protocol_version } else { 'v1' }
        derived_by = if ((Test-VibeObjectHasProperty -InputObject $decision -PropertyName 'derived_by') -and -not [string]::IsNullOrWhiteSpace([string]$decision.derived_by)) { [string]$decision.derived_by } else { 'host' }
        selection_mode = [string]$effectiveSelectionMode
        requested_selection_mode = [string]$selectionMode
        approved_skill_ids = @($approvedSkillIds)
        deferred_skill_ids = @($deferredSkillIds)
        rejected_skill_ids = @($rejectedSkillIds)
        surfaced_skill_ids = @($surfacedSkillIds)
        stale_skill_ids = @($unknownSkillIds)
        reconciliation_state = [string]$reconciliationState
        requires_recuration = [bool]$requiresRecuration
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
        '- These phases guide specialist ordering inside `plan_execute`; they do not create a second runtime, second plan, or second approval ladder.'
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

function Get-VibeHostSpecialistDispatchDecisionMarkdownLines {
    param(
        [AllowNull()] [object]$Decision = $null
    )

    if ($null -eq $Decision) {
        return @()
    }

    return @(
        '- Host specialist curation remains bounded to the surfaced recommendation ids from the current governed run.',
        '- Runtime validation remains authoritative for blocked and degraded specialist outcomes.',
        ('- Selection mode: {0}' -f [string]$Decision.selection_mode),
        ('- Reconciliation state: {0}' -f $(if ((Test-VibeObjectHasProperty -InputObject $Decision -PropertyName 'reconciliation_state') -and -not [string]::IsNullOrWhiteSpace([string]$Decision.reconciliation_state)) { [string]$Decision.reconciliation_state } else { 'current' })),
        ('- Requires re-curation: {0}' -f $(if (Test-VibeObjectHasProperty -InputObject $Decision -PropertyName 'requires_recuration') { [bool]$Decision.requires_recuration } else { $false })),
        ('- Approved skill ids: {0}' -f $(if (@($Decision.approved_skill_ids).Count -gt 0) { [string]::Join(', ', @($Decision.approved_skill_ids)) } else { 'none' })),
        ('- Deferred skill ids: {0}' -f $(if (@($Decision.deferred_skill_ids).Count -gt 0) { [string]::Join(', ', @($Decision.deferred_skill_ids)) } else { 'none' })),
        ('- Rejected skill ids: {0}' -f $(if (@($Decision.rejected_skill_ids).Count -gt 0) { [string]::Join(', ', @($Decision.rejected_skill_ids)) } else { 'none' })),
        ('- Dropped stale skill ids: {0}' -f $(if ((Test-VibeObjectHasProperty -InputObject $Decision -PropertyName 'stale_skill_ids') -and @($Decision.stale_skill_ids).Count -gt 0) { [string]::Join(', ', @($Decision.stale_skill_ids)) } else { 'none' }))
    )
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

    $routeSnapshot = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'route_snapshot'
    $authorityFlags = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'authority_flags'
    $divergenceShadow = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'divergence_shadow'

    return [pscustomobject]@{
        router_selected_skill = Get-VibeNestedPropertySafe -InputObject $routeSnapshot -PropertyPath @('selected_skill') -DefaultValue $null
        runtime_selected_skill = Get-VibeNestedPropertySafe -InputObject $authorityFlags -PropertyPath @('explicit_runtime_skill') -DefaultValue $DefaultRuntimeSkill
        skill_mismatch = Get-VibeNestedPropertySafe -InputObject $divergenceShadow -PropertyPath @('skill_mismatch') -DefaultValue $false
        confirm_required = Get-VibeNestedPropertySafe -InputObject $routeSnapshot -PropertyPath @('confirm_required') -DefaultValue $false
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
        specialist_consultation_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\specialist-consultation-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        skill_promotion_policy = if (Test-Path -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json')) { Get-Content -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json } else { Get-VgoSkillPromotionPolicyDefaults }
        execution_topology_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-topology-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        native_specialist_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\native-specialist-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        execution_runtime_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-runtime-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
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
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath($RepoRoot)
}

function Get-VibeWorkspaceSidecarRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceRoot -RepoRoot $RepoRoot) '.vibeskills'))
}

function Get-VibeWorkspaceProjectDescriptorPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot) 'project.json'))
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

function Resolve-VibeNativeSpecialistWorkingRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$SessionRoot = '',
        [AllowEmptyString()] [string]$RequirementDocPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanPath = '',
        [AllowEmptyString()] [string]$SourceArtifactPath = ''
    )

    $preferArtifactWorkspace = (
        (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/runtime/Invoke-VibeCanonicalEntry.ps1') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $RepoRoot 'config/version-governance.json') -PathType Leaf)
    )
    $orderedCandidates = if ($preferArtifactWorkspace) {
        @(
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $RequirementDocPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $ExecutionPlanPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $SourceArtifactPath),
            $SessionRoot,
            $RepoRoot
        )
    } else {
        @(
            $RepoRoot,
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $RequirementDocPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $ExecutionPlanPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $SourceArtifactPath),
            $SessionRoot
        )
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @($orderedCandidates)) {
        if ([string]::IsNullOrWhiteSpace([string]$candidate)) {
            continue
        }

        $resolvedCandidate = [System.IO.Path]::GetFullPath([string]$candidate)
        if (-not (Test-Path -LiteralPath $resolvedCandidate)) {
            continue
        }
        if (-not $candidates.Contains($resolvedCandidate)) {
            $candidates.Add($resolvedCandidate) | Out-Null
        }
    }

    foreach ($candidate in @($candidates)) {
        if (Test-VibeWritableDirectory -Path $candidate) {
            return $candidate
        }
    }

    if ($candidates.Count -gt 0) {
        return [string]$candidates[0]
    }

    return [System.IO.Path]::GetFullPath($RepoRoot)
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
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = '',
        [AllowEmptyString()] [string]$RouterTargetRoot = ''
    )

    $workspaceRoot = Get-VibeWorkspaceRoot -RepoRoot $RepoRoot
    $workspaceSidecarRoot = Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot
    $projectDescriptorPath = Get-VibeWorkspaceProjectDescriptorPath -RepoRoot $RepoRoot
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
        [AllowNull()] [object]$Runtime = $null
    )

    $storage = New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -Runtime $Runtime
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

function Get-VibeSpecialistDecisionSidecarPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return Join-Path $SessionRoot 'specialist-decision.json'
}

function Get-VibeSpecialistExecutionSidecarPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return Join-Path $SessionRoot 'specialist-execution.json'
}

function Get-VibeOptionalSpecialistDecisionOverride {
    param(
        [AllowEmptyString()] [string]$SessionRoot
    )

    if ([string]::IsNullOrWhiteSpace($SessionRoot)) {
        return $null
    }

    $path = Get-VibeSpecialistDecisionSidecarPath -SessionRoot $SessionRoot
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }

    return [pscustomobject]@{
        path = [string]$path
        payload = (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
}

function Get-VibeSpecialistDecisionDefaultNotes {
    param(
        [AllowEmptyString()] [string]$DecisionState = '',
        [AllowEmptyString()] [string]$ResolutionMode = ''
    )

    switch ($ResolutionMode) {
        'approved_dispatch' { return 'Bounded specialist recommendations were surfaced and promoted into effective approved dispatch.' }
        'degraded' { return 'Specialist recommendations existed, but execution remained explicitly degraded before live native dispatch closed cleanly.' }
        'blocked' { return 'Specialist recommendations existed, but execution stayed blocked before live native dispatch could proceed.' }
        'local_suggestion_only' { return 'Residual local specialist suggestions remained advisory and require explicit escalation before execution.' }
        'no_specialist_needed' { return 'No bounded specialist recommendations were frozen for this run, and governed execution explicitly recorded that no specialist help was needed.' }
        'no_matching_specialist' { return 'No bounded specialist recommendations matched this run; host-led execution remains responsible for decomposition and delivery.' }
        'repo_asset_fallback' { return 'No bounded specialist recommendations were frozen for this run, and governed execution explicitly recorded a repo-asset fallback that must remain traceable.' }
        'pending_resolution' { return 'No bounded specialist recommendations were frozen for this run; execution must explicitly resolve whether no specialist was needed or a repo-asset fallback was used.' }
    }

    switch ($DecisionState) {
        'approved_dispatch' { return 'Bounded specialist recommendations were surfaced and promoted into effective approved dispatch.' }
        'degraded' { return 'Specialist recommendations existed, but execution remained explicitly degraded before live native dispatch closed cleanly.' }
        'blocked' { return 'Specialist recommendations existed, but execution stayed blocked before live native dispatch could proceed.' }
        'local_suggestion_only' { return 'Residual local specialist suggestions remained advisory and require explicit escalation before execution.' }
        default { return 'No bounded specialist recommendations were frozen for this run; execution must explicitly resolve whether no specialist was needed or a repo-asset fallback was used.' }
    }
}

function New-VibeSpecialistDecisionProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$LocalSuggestions = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$BlockedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$DegradedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [string[]]$MatchedSkillIds = @(),
        [AllowEmptyCollection()] [AllowNull()] [string[]]$SurfacedSkillIds = @(),
        [int]$RecommendationCount = -1,
        [AllowNull()] [object]$OverridePayload = $null,
        [AllowEmptyString()] [string]$OverrideSourcePath = ''
    )

    $executionSource = Get-VibeRuntimeSelectedSkillExecutionProjection -RuntimeInputPacket $RuntimeInputPacket

    $approvedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $ApprovedDispatch) -gt 0) {
        @($ApprovedDispatch)
    } elseif ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'selected_skill_execution')) {
        @($executionSource.selected_skill_execution)
    } else {
        @()
    }
    $localSuggestionArray = if ((Get-VibeSafeArrayCount -InputObject $LocalSuggestions) -gt 0) {
        @($LocalSuggestions)
    } else {
        @()
    }
    $blockedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $BlockedDispatch) -gt 0) {
        @($BlockedDispatch)
    } elseif ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'blocked_skill_execution')) {
        @($executionSource.blocked_skill_execution)
    } else {
        @()
    }
    $degradedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $DegradedDispatch) -gt 0) {
        @($DegradedDispatch)
    } elseif ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'degraded_skill_execution')) {
        @($executionSource.degraded_skill_execution)
    } else {
        @()
    }

    $approvedDispatchSkillIds = @($approvedDispatchArray | ForEach-Object {
        if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $localSuggestionSkillIds = @(
        @($localSuggestionArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    )
    $blockedSkillIds = if ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'blocked_skill_ids') -and (Get-VibeSafeArrayCount -InputObject $executionSource.blocked_skill_ids) -gt 0) {
        @($executionSource.blocked_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @($blockedDispatchArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $degradedSkillIds = if ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'degraded_skill_ids') -and (Get-VibeSafeArrayCount -InputObject $executionSource.degraded_skill_ids) -gt 0) {
        @($executionSource.degraded_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @($degradedDispatchArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $explicitMatchedSkillIds = @()
    if ($null -ne $MatchedSkillIds) {
        $explicitMatchedSkillIds = @($MatchedSkillIds | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $matchedSkillIds = @()
    if (@($explicitMatchedSkillIds).Count -gt 0) {
        $matchedSkillIds = @($explicitMatchedSkillIds)
    } elseif ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'matched_skill_ids')) {
        $matchedSkillIds = @($executionSource.matched_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $explicitSurfacedSkillIds = @()
    if ($null -ne $SurfacedSkillIds) {
        $explicitSurfacedSkillIds = @($SurfacedSkillIds | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $surfacedSkillIds = @()
    if (@($explicitSurfacedSkillIds).Count -gt 0) {
        $surfacedSkillIds = @($explicitSurfacedSkillIds)
    } elseif ($null -ne $executionSource -and (Test-VibeObjectHasProperty -InputObject $executionSource -PropertyName 'surfaced_skill_ids')) {
        $surfacedSkillIds = @($executionSource.surfaced_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $recommendationCountResolved = if ($RecommendationCount -ge 0) {
        [int]$RecommendationCount
    } elseif ($null -ne $RuntimeInputPacket) {
        @(Get-VibeRuntimeSpecialistRecommendations -RuntimeInputPacket $RuntimeInputPacket).Count
    } else {
        @($surfacedSkillIds).Count
    }

    $decisionState = if (@($approvedDispatchSkillIds).Count -gt 0) {
        'approved_dispatch'
    } elseif (@($degradedSkillIds).Count -gt 0) {
        'degraded'
    } elseif (@($blockedSkillIds).Count -gt 0) {
        'blocked'
    } elseif (@($localSuggestionSkillIds).Count -gt 0) {
        'local_suggestion_only'
    } else {
        'no_specialist_recommendations'
    }

    $resolutionMode = switch ($decisionState) {
        'approved_dispatch' { 'approved_dispatch' }
        'degraded' { 'degraded' }
        'blocked' { 'blocked' }
        'local_suggestion_only' { 'local_suggestion_only' }
        default {
            if ([int]$recommendationCountResolved -eq 0) {
                'no_matching_specialist'
            } else {
                'pending_resolution'
            }
        }
    }
    $resolutionNotes = Get-VibeSpecialistDecisionDefaultNotes -DecisionState $decisionState -ResolutionMode $resolutionMode

    $repoAssetFallback = [pscustomobject]@{
        used = $false
        asset_paths = @()
        reason = ''
        legal_basis = ''
        traceability_basis = @()
    }

    if ($null -ne $OverridePayload) {
        $overrideProvidedNotes = $false
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'decision_state') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.decision_state)) {
            $decisionState = [string]$OverridePayload.decision_state
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'resolution_mode') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.resolution_mode)) {
            $resolutionMode = [string]$OverridePayload.resolution_mode
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'notes') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.notes)) {
            $resolutionNotes = [string]$OverridePayload.notes
            $overrideProvidedNotes = $true
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'repo_asset_fallback') -and $null -ne $OverridePayload.repo_asset_fallback) {
            $repoAssetFallbackSource = $OverridePayload.repo_asset_fallback
            $repoAssetFallbackAssetPaths = if (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'asset_paths') {
                @($repoAssetFallbackSource.asset_paths | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
            $repoAssetFallbackTraceabilityBasis = if (
                (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'traceability_basis') -and
                $null -ne $repoAssetFallbackSource.traceability_basis
            ) {
                @($repoAssetFallbackSource.traceability_basis | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
            $repoAssetFallback = [pscustomobject]@{
                used = if (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'used') { [bool]$repoAssetFallbackSource.used } else { @($repoAssetFallbackAssetPaths).Count -gt 0 }
                asset_paths = @($repoAssetFallbackAssetPaths)
                reason = if ((Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string]$repoAssetFallbackSource.reason)) { [string]$repoAssetFallbackSource.reason } else { '' }
                legal_basis = if ((Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'legal_basis') -and -not [string]::IsNullOrWhiteSpace([string]$repoAssetFallbackSource.legal_basis)) { [string]$repoAssetFallbackSource.legal_basis } else { '' }
                traceability_basis = @($repoAssetFallbackTraceabilityBasis)
            }
        }
        if (-not $overrideProvidedNotes) {
            $resolutionNotes = Get-VibeSpecialistDecisionDefaultNotes -DecisionState $decisionState -ResolutionMode $resolutionMode
        }
    }

    $selectedSkillIds = @($approvedDispatchSkillIds)
    $candidateSkillIdsReviewed = @(
        @($matchedSkillIds) +
        @($surfacedSkillIds) +
        @($approvedDispatchSkillIds) +
        @($localSuggestionSkillIds) +
        @($blockedSkillIds) +
        @($degradedSkillIds)
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique
    $rejectedCandidates = @()
    if ($decisionState -eq 'no_specialist_recommendations') {
        foreach ($candidateSkillId in @($candidateSkillIdsReviewed)) {
            if (@($selectedSkillIds) -contains [string]$candidateSkillId) {
                continue
            }
            $rejectedCandidates += [pscustomobject]@{
                skill_id = [string]$candidateSkillId
                reason = 'No bounded specialist dispatch was selected for this run; host-governed execution remains responsible for the task and verification evidence.'
            }
        }
    }

    return [pscustomobject]@{
        decision_state = $decisionState
        resolution_mode = $resolutionMode
        recommendation_count = [int]$recommendationCountResolved
        candidate_skill_ids_reviewed = @($candidateSkillIdsReviewed)
        selected_skill_ids = @($selectedSkillIds)
        rejected_candidates = @($rejectedCandidates)
        matched_skill_ids = @($matchedSkillIds)
        surfaced_skill_ids = @($surfacedSkillIds)
        approved_dispatch_skill_ids = @($approvedDispatchSkillIds)
        local_suggestion_skill_ids = @($localSuggestionSkillIds)
        blocked_skill_ids = @($blockedSkillIds)
        degraded_skill_ids = @($degradedSkillIds)
        repo_asset_fallback = $repoAssetFallback
        notes = $resolutionNotes
        source = if ([string]::IsNullOrWhiteSpace($OverrideSourcePath)) { 'runtime_structural_projection' } else { 'runtime_structural_projection_plus_sidecar' }
        override_source_path = if ([string]::IsNullOrWhiteSpace($OverrideSourcePath)) { $null } else { [string]$OverrideSourcePath }
    }
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
        [AllowNull()] [object]$HostSpecialistDispatchDecision = $null,
        [AllowNull()] [object]$CodeTaskTddDecision = $null,
        [AllowNull()] [object]$HostDecision = $null,
        [AllowNull()] [object[]]$SpecialistRecommendations = @(),
        [AllowNull()] [object[]]$StageAssistantHints = @(),
        [AllowNull()] [object]$SkillUsage = $null,
        [AllowNull()] [object]$SkillRouting = $null,
        [Parameter(Mandatory)] [object]$SpecialistDispatch,
        [AllowNull()] [object[]]$OverlayDecisions = @(),
        [Parameter(Mandatory)] [object]$Policy
    )

    $confirmRequired = ([string]$RouteResult.route_mode -eq 'confirm_required')
    $selected = Get-VibePropertySafe -InputObject $RouteResult -PropertyName 'selected'
    $routerSelectedSkill = if ($null -ne $selected) { [string]$selected.skill } else { $null }

    $customAdmission = if (
        $RouteResult.PSObject.Properties.Name -contains 'custom_admission' -and
        $null -ne $RouteResult.custom_admission
    ) {
        [pscustomobject]@{
            status = [string]$RouteResult.custom_admission.status
            target_root = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'target_root') { [string]$RouteResult.custom_admission.target_root } else { $null }
            admitted_candidate_count = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'admitted_candidates') { @($RouteResult.custom_admission.admitted_candidates).Count } else { 0 }
            admitted_skill_ids = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'admitted_candidates') {
                @($RouteResult.custom_admission.admitted_candidates | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
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

    $packetSpecialistDecision = New-VibeSpecialistDecisionProjection `
        -ApprovedDispatch @($SpecialistDispatch.approved_dispatch) `
        -LocalSuggestions @($SpecialistDispatch.local_specialist_suggestions) `
        -BlockedDispatch $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked' -and $null -ne $SpecialistDispatch.blocked) { @($SpecialistDispatch.blocked) } else { @() }) `
        -DegradedDispatch $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded' -and $null -ne $SpecialistDispatch.degraded) { @($SpecialistDispatch.degraded) } else { @() }) `
        -MatchedSkillIds $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $SpecialistDispatch.matched_skill_ids) { @($SpecialistDispatch.matched_skill_ids) } else { @() }) `
        -SurfacedSkillIds $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $SpecialistDispatch.surfaced_skill_ids) { @($SpecialistDispatch.surfaced_skill_ids) } else { @() }) `
        -RecommendationCount @($SpecialistRecommendations).Count

    $specialistDispatchProjection = [pscustomobject]@{
        approved_dispatch = [object[]]@($SpecialistDispatch.approved_dispatch)
        local_specialist_suggestions = [object[]]@($SpecialistDispatch.local_specialist_suggestions)
        blocked = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked' -and $null -ne $SpecialistDispatch.blocked) { $SpecialistDispatch.blocked } else { @() }))
        degraded = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded' -and $null -ne $SpecialistDispatch.degraded) { $SpecialistDispatch.degraded } else { @() }))
        approved_skill_ids = @($SpecialistDispatch.approved_dispatch | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        local_suggestion_skill_ids = @($SpecialistDispatch.local_specialist_suggestions | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        matched_skill_ids = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $SpecialistDispatch.matched_skill_ids) { $SpecialistDispatch.matched_skill_ids } else { @() }))
        surfaced_skill_ids = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $SpecialistDispatch.surfaced_skill_ids) { $SpecialistDispatch.surfaced_skill_ids } else { @() }))
        blocked_skill_ids = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked_skill_ids' -and $null -ne $SpecialistDispatch.blocked_skill_ids) { $SpecialistDispatch.blocked_skill_ids } else { @() }))
        degraded_skill_ids = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded_skill_ids' -and $null -ne $SpecialistDispatch.degraded_skill_ids) { $SpecialistDispatch.degraded_skill_ids } else { @() }))
        ghost_match_skill_ids = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'ghost_match_skill_ids' -and $null -ne $SpecialistDispatch.ghost_match_skill_ids) { $SpecialistDispatch.ghost_match_skill_ids } else { @() }))
        promotion_outcomes = @($(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'promotion_outcomes' -and $null -ne $SpecialistDispatch.promotion_outcomes) { $SpecialistDispatch.promotion_outcomes } else { @() }))
        host_decision_applied = ($null -ne $HostSpecialistDispatchDecision)
        host_selection_mode = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'selection_mode')) { [string]$HostSpecialistDispatchDecision.selection_mode } else { $null }
        host_approved_skill_ids = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'approved_skill_ids')) { [object[]]@($HostSpecialistDispatchDecision.approved_skill_ids) } else { @() }
        host_deferred_skill_ids = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'deferred_skill_ids')) { [object[]]@($HostSpecialistDispatchDecision.deferred_skill_ids) } else { @() }
        host_rejected_skill_ids = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'rejected_skill_ids')) { [object[]]@($HostSpecialistDispatchDecision.rejected_skill_ids) } else { @() }
        host_stale_skill_ids = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'stale_skill_ids')) { [object[]]@($HostSpecialistDispatchDecision.stale_skill_ids) } else { @() }
        host_reconciliation_state = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'reconciliation_state')) { [string]$HostSpecialistDispatchDecision.reconciliation_state } else { $null }
        host_requires_recuration = if ($null -ne $HostSpecialistDispatchDecision -and (Test-VibeObjectHasProperty -InputObject $HostSpecialistDispatchDecision -PropertyName 'requires_recuration')) { [bool]$HostSpecialistDispatchDecision.requires_recuration } else { $false }
        escalation_required = Get-VibeNestedPropertySafe -InputObject $SpecialistDispatch -PropertyPath @('escalation_required') -DefaultValue $false
        escalation_status = Get-VibeNestedPropertySafe -InputObject $SpecialistDispatch -PropertyPath @('escalation_status') -DefaultValue ''
        approval_owner = Get-VibeNestedPropertySafe -InputObject $Policy -PropertyPath @('child_specialist_suggestion_contract', 'approval_owner') -DefaultValue 'root_vibe'
        status = Get-VibeNestedPropertySafe -InputObject $Policy -PropertyPath @('child_specialist_suggestion_contract', 'status') -DefaultValue 'auto_promote_when_safe_same_round'
    }

    return [pscustomobject]@{
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
        hierarchy = $HierarchyProjection
        canonical_router = [pscustomobject]@{
            role = 'internal_specialist_recommender'
            prompt = $Task
            task_type = if ([string]::IsNullOrWhiteSpace($TaskType)) { $null } else { [string]$TaskType }
            requested_skill = if ([string]::IsNullOrWhiteSpace([string]$RequestedSkill)) { $null } else { [string]$RequestedSkill }
            host_id = if ([string]::IsNullOrWhiteSpace($RouterHostId)) { $null } else { [string]$RouterHostId }
            target_root = if ([string]::IsNullOrWhiteSpace($RouterTargetRoot)) { $null } else { [string]$RouterTargetRoot }
            unattended = [bool]$Unattended
            host_decision_applied = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [bool]$RouteResult.structured_host_route_decision.applied } else { $false }
            host_decision_kind = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.decision_kind } else { $null }
            host_decision_action = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.decision_action } else { $null }
            route_script_path = if ([string]::IsNullOrWhiteSpace($RouterScriptPath)) { $null } else { [string]$RouterScriptPath }
        }
        host_adapter = (New-VibeRuntimeHostAdapterProjection -Runtime $Runtime -FallbackHostId $RouterHostId -TargetRoot $RouterTargetRoot)
        route_snapshot = [pscustomobject]@{
            selected_pack = if ($null -ne $selected) { [string]$selected.pack_id } else { $null }
            selected_skill = $routerSelectedSkill
            route_mode = [string]$RouteResult.route_mode
            route_reason = [string]$RouteResult.route_reason
            confirm_required = [bool]$confirmRequired
            confidence = if ($RouteResult.confidence -ne $null) { [double]$RouteResult.confidence } else { $null }
            truth_level = [string]$RouteResult.truth_level
            degradation_state = [string]$RouteResult.degradation_state
            non_authoritative = [bool]$RouteResult.non_authoritative
            fallback_active = [bool]$RouteResult.fallback_active
            hazard_alert_required = [bool]$RouteResult.hazard_alert_required
            unattended_override_applied = [bool]$RouteResult.unattended_override_applied
            host_decision_applied = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [bool]$RouteResult.structured_host_route_decision.applied } else { $false }
            host_decision_action = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.decision_action } else { $null }
            host_selected_skill = if ($RouteResult.PSObject.Properties.Name -contains 'structured_host_route_decision' -and $RouteResult.structured_host_route_decision) { [string]$RouteResult.structured_host_route_decision.selected_skill } else { $null }
            custom_admission_status = if ($RouteResult.PSObject.Properties.Name -contains 'custom_admission' -and $RouteResult.custom_admission) { [string]$RouteResult.custom_admission.status } else { $null }
        }
        custom_admission = $customAdmission
        continuation_context = if ($null -ne $continuationContext) { $continuationContext } else { $null }
        host_reentry_action = $hostReentryAction
        host_revision_target_stage = $hostRevisionTargetStage
        host_revision_delta = [object[]]@($hostRevisionDelta)
        host_decision = if ($null -ne $HostDecision) { $HostDecision } else { $null }
        execution_phase_decomposition = $ExecutionPhaseDecomposition
        code_task_tdd_decision = $CodeTaskTddDecision
        host_specialist_dispatch_decision = $HostSpecialistDispatchDecision
        skill_routing = if ($null -ne $SkillRouting) {
            $SkillRouting
        } else {
            [pscustomobject]@{
                schema_version = 'simplified_skill_routing_v1'
                candidates = @()
                selected = @()
                rejected = @()
            }
        }
        skill_usage = if ($null -ne $SkillUsage) {
            $SkillUsage
        } else {
            [pscustomobject]@{
                schema_version = 1
                state_model = 'binary_used_unused'
                used_skills = @()
                unused_skills = @()
                loaded_skills = @()
                evidence = @()
                unused_reasons = @()
            }
        }
        specialist_decision = $packetSpecialistDecision
        overlay_decisions = @($OverlayDecisions)
        authority_flags = $AuthorityFlagsProjection
        storage = $StorageProjection
        divergence_shadow = [pscustomobject]@{
            router_selected_skill = $routerSelectedSkill
            runtime_selected_skill = if ([string]::IsNullOrWhiteSpace($RuntimeSelectedSkill)) { $null } else { [string]$RuntimeSelectedSkill }
            skill_mismatch = [bool](-not [string]::Equals($routerSelectedSkill, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase))
            confirm_required = [bool]$confirmRequired
            explicit_runtime_override_applied = [bool](-not [string]::IsNullOrWhiteSpace($RuntimeSelectedSkill))
            explicit_runtime_override_reason = 'governed_runtime_entry'
            governance_scope_mismatch = $false
        }
        provenance = [pscustomobject]@{
            source_of_truth = 'vibe_runtime_with_internal_specialist_recommender'
            freeze_before_requirement_doc = [bool]$Policy.freeze_before_requirement_doc
            proof_class = 'structure'
        }
    }
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
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$TerminalStage = ''
    )

    if ([string]$EntryIntentId -eq 'vibe') {
        switch ([string]$TerminalStage) {
            'requirement_doc' { return @('vibe') }
            'xl_plan' { return @('vibe') }
            default { return @() }
        }
    }

    switch ([string]$TerminalStage) {
        'requirement_doc' { return @('vibe', 'vibe-how-do-we-do', 'vibe-do-it') }
        'xl_plan' { return @('vibe', 'vibe-do-it') }
        default { return @() }
    }
}

function New-VibeBoundedReturnControlProjection {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowNull()] [object]$StageLineage = $null
    )

    $resolvedEntryIntentId = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { 'vibe' } else { [string]$EntryIntentId }
    $terminalStage = Get-VibeStageLineageTerminalStage -StageLineage $StageLineage
    $allowedFollowupEntryIds = @(Get-VibeBoundedReturnFollowupEntryIds -EntryIntentId $resolvedEntryIntentId -TerminalStage $terminalStage)
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
        $renderedLines = @(
            'Bounded governed stop reached. Return control to the user now.',
            ('- terminal stage: `{0}`' -f [string]$terminalStage),
            ('- source run id: `{0}`' -f [string]$RunId),
            ('- explicit user re-entry required before later stages: `true`'),
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
        control_owner = 'user'
        source_run_id = $RunId
        source_entry_intent_id = $resolvedEntryIntentId
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
            preferred_payload = [pscustomobject]@{
                decision_kind = 'approval_response'
                decision_action = [string]$preferredDecisionAction
                approval_decision = 'approve'
            }
        }
        allowed_followup_entry_ids = @($allowedFollowupEntryIds)
        reentry_token = $token
        rendered_text = (@($renderedLines) -join "`n")
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
        [AllowEmptyString()] [string]$ReviewMode = 'native_contract'
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
        review_mode = if ([string]::IsNullOrWhiteSpace($ReviewMode)) { 'native_contract' } else { $ReviewMode }
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
        [AllowEmptyString()] [string]$ExecuteReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionManifestPath = '',
        [AllowEmptyString()] [string]$ExecutionTopologyPath = '',
        [AllowEmptyString()] [string]$ExecutionProofManifestPath = '',
        [AllowEmptyString()] [string]$SpecialistLifecycleDisclosurePath = '',
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
        execute_receipt = if ([string]::IsNullOrWhiteSpace($ExecuteReceiptPath)) { $null } else { $ExecuteReceiptPath }
        execution_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionManifestPath)) { $null } else { $ExecutionManifestPath }
        execution_topology = if ([string]::IsNullOrWhiteSpace($ExecutionTopologyPath)) { $null } else { $ExecutionTopologyPath }
        execution_proof_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionProofManifestPath)) { $null } else { $ExecutionProofManifestPath }
        specialist_lifecycle_disclosure = if ([string]::IsNullOrWhiteSpace($SpecialistLifecycleDisclosurePath)) { $null } else { $SpecialistLifecycleDisclosurePath }
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

function Get-VibeInteractiveSkillExecutionDisclosurePolicy {
    param(
        [AllowNull()] [object]$RuntimeInputPacketPolicy
    )

    $policy = $null
    if ($null -ne $RuntimeInputPacketPolicy -and (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacketPolicy -PropertyName 'interactive_skill_execution_disclosure')) {
        $policy = $RuntimeInputPacketPolicy.interactive_skill_execution_disclosure
    }

    return [pscustomobject]@{
        enabled = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'enabled')) { [bool]$policy.enabled } else { $false }
        stage = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$policy.stage)) { [string]$policy.stage } else { 'plan_execute' }
        mode = 'selected_skill_execution_pre_execution_unified_once'
        timing = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'timing') -and -not [string]::IsNullOrWhiteSpace([string]$policy.timing)) { [string]$policy.timing } else { 'before_execution' }
        scope = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'scope') -and -not [string]::IsNullOrWhiteSpace([string]$policy.scope)) { [string]$policy.scope } else { 'selected_skill_execution_only' }
        aggregation = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'aggregation') -and -not [string]::IsNullOrWhiteSpace([string]$policy.aggregation)) { [string]$policy.aggregation } else { 'unified_once' }
        path_source = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'path_source') -and -not [string]::IsNullOrWhiteSpace([string]$policy.path_source)) { [string]$policy.path_source } else { 'native_skill_entrypoint' }
        require_entrypoint_path = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'require_entrypoint_path')) { [bool]$policy.require_entrypoint_path } else { $true }
        include_description = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'include_description')) { [bool]$policy.include_description } else { $true }
        header = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'header') -and -not [string]::IsNullOrWhiteSpace([string]$policy.header)) { [string]$policy.header } else { 'Pre-execution skill disclosure:' }
    }
}

function New-VibeSpecialistUserDisclosureProjection {
    param(
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedDispatch = @(),
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = if ($null -ne $Policy) { $Policy } else { Get-VibeInteractiveSkillExecutionDisclosurePolicy }
    if (-not [bool]$resolvedPolicy.enabled) {
        return $null
    }

    $routedSkills = New-Object System.Collections.Generic.List[object]
    $seenSkillIds = @{}
    foreach ($dispatch in @($ApprovedDispatch)) {
        if ($null -eq $dispatch) {
            continue
        }

        $skillId = [string]$dispatch.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seenSkillIds.ContainsKey($skillId)) {
            continue
        }

        $entrypointRaw = if (Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'native_skill_entrypoint') { [string]$dispatch.native_skill_entrypoint } else { '' }
        $entrypoint = $null
        $entrypointMissing = $false
        $entrypointPathInvalid = $false
        $entrypointPathState = 'resolved'
        if ([string]::IsNullOrWhiteSpace($entrypointRaw)) {
            $entrypointMissing = $true
            $entrypointPathState = 'missing'
        } elseif (-not [System.IO.Path]::IsPathRooted($entrypointRaw)) {
            $entrypointPathInvalid = $true
            $entrypointPathState = 'invalid'
        } else {
            $entrypoint = [System.IO.Path]::GetFullPath($entrypointRaw)
        }

        $seenSkillIds[$skillId] = $true
        $routedSkills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                native_skill_entrypoint = if ([string]::IsNullOrWhiteSpace($entrypoint)) { $null } else { $entrypoint }
                native_skill_entrypoint_raw = if ([string]::IsNullOrWhiteSpace($entrypointRaw)) { $null } else { $entrypointRaw }
                entrypoint_path_state = $entrypointPathState
                entrypoint_missing = $entrypointMissing
                entrypoint_path_invalid = $entrypointPathInvalid
                entrypoint_requirement_satisfied = if ([bool]$resolvedPolicy.require_entrypoint_path) { -not $entrypointMissing -and -not $entrypointPathInvalid } else { $true }
                native_skill_description = if ([bool]$resolvedPolicy.include_description -and (Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.native_skill_description)) { [string]$dispatch.native_skill_description } else { $null }
                dispatch_phase = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.dispatch_phase)) { [string]$dispatch.dispatch_phase } else { $null }
                write_scope = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'write_scope') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.write_scope)) { [string]$dispatch.write_scope } else { $null }
                review_mode = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'review_mode') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.review_mode)) { [string]$dispatch.review_mode } else { $null }
            }
        )
    }

    if ($routedSkills.Count -eq 0) {
        return $null
    }

    $renderedLines = @([string]$resolvedPolicy.header)
    foreach ($entry in $routedSkills) {
        $renderedLines += ('- {0} -> {1}' -f [string]$entry.skill_id, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $entry))
    }

    return [pscustomobject]@{
        enabled = [bool]$resolvedPolicy.enabled
        stage = [string]$resolvedPolicy.stage
        mode = [string]$resolvedPolicy.mode
        timing = [string]$resolvedPolicy.timing
        scope = [string]$resolvedPolicy.scope
        aggregation = [string]$resolvedPolicy.aggregation
        path_source = [string]$resolvedPolicy.path_source
        routed_skill_count = [int]$routedSkills.Count
        routed_skills = [object[]]$routedSkills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function Get-VibeSpecialistEntrypointDisplayText {
    param(
        [AllowNull()] [object]$SkillRecord = $null
    )

    if ($null -eq $SkillRecord) {
        return 'path unavailable'
    }

    $resolvedEntrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint)
    ) {
        [string]$SkillRecord.native_skill_entrypoint
    } else {
        $null
    }
    if (-not [string]::IsNullOrWhiteSpace($resolvedEntrypoint)) {
        return $resolvedEntrypoint
    }

    $rawEntrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint_raw') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint_raw)
    ) {
        [string]$SkillRecord.native_skill_entrypoint_raw
    } elseif (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint)
    ) {
        [string]$SkillRecord.native_skill_entrypoint
    } else {
        $null
    }

    $entrypointMissing = if ((Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'entrypoint_missing')) { [bool]$SkillRecord.entrypoint_missing } else { $false }
    $entrypointPathInvalid = if ((Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'entrypoint_path_invalid')) { [bool]$SkillRecord.entrypoint_path_invalid } else { $false }
    if ($entrypointPathInvalid -and -not [string]::IsNullOrWhiteSpace($rawEntrypoint)) {
        return ('{0} (invalid entrypoint path)' -f $rawEntrypoint)
    }
    if ($entrypointMissing) {
        return 'path unavailable (missing entrypoint path)'
    }
    if (-not [string]::IsNullOrWhiteSpace($rawEntrypoint)) {
        return $rawEntrypoint
    }

    return 'path unavailable'
}

function Get-VibeSpecialistLifecycleDisclosurePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'specialist-lifecycle-disclosure.json'))
}

function New-VibeSpecialistRoutingLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket
    )

    $specialistRecommendations = @(Get-VibeRuntimeSpecialistRecommendations -RuntimeInputPacket $RuntimeInputPacket)
    if ($null -eq $RuntimeInputPacket -or @($specialistRecommendations).Count -eq 0) {
        return $null
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @('Discussion-chain routed Skills:')
    foreach ($recommendation in @($specialistRecommendations)) {
        if ($null -eq $recommendation) {
            continue
        }

        $skillId = [string]$recommendation.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        $entrypoint = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.native_skill_entrypoint)) { [string]$recommendation.native_skill_entrypoint } else { $null }
        if (-not [string]::IsNullOrWhiteSpace($entrypoint) -and [System.IO.Path]::IsPathRooted($entrypoint)) {
            $entrypoint = [System.IO.Path]::GetFullPath($entrypoint)
        }
        $whyNow = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.reason)) { [string]$recommendation.reason } else { 'routed as a relevant specialist candidate for the governed discussion and planning chain' }

        $skills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                why_now = $whyNow
                source = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'source') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.source)) { [string]$recommendation.source } else { $null }
                native_skill_entrypoint = $entrypoint
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.native_skill_description)) { [string]$recommendation.native_skill_description } else { $null }
                state = 'routed'
            }
        ) | Out-Null
        $renderedLines += ('- {0}: {1} ({2})' -f $skillId, $whyNow, $(if ([string]::IsNullOrWhiteSpace($entrypoint)) { 'path unavailable' } else { $entrypoint }))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = 'discussion_routing'
        truth_layer = 'routing'
        stage = if ((Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$RuntimeInputPacket.stage)) { [string]$RuntimeInputPacket.stage } else { 'runtime_input_freeze' }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistConsultationLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$ConsultationReceipt
    )

    if ($null -eq $ConsultationReceipt -or -not [bool]$ConsultationReceipt.enabled) {
        return $null
    }

    $windowId = if ((Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'window_id') -and -not [string]::IsNullOrWhiteSpace([string]$ConsultationReceipt.window_id)) {
        [string]$ConsultationReceipt.window_id
    } else {
        $null
    }
    if ($windowId -notin @('discussion', 'planning')) {
        throw 'Enabled specialist consultation receipts must declare window_id as discussion or planning.'
    }
    $consultedUnits = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'consulted_units') -and
        $null -ne $ConsultationReceipt.consulted_units
    ) {
        @($ConsultationReceipt.consulted_units)
    } else {
        @()
    }
    $routedUnits = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'routed_units') -and
        $null -ne $ConsultationReceipt.routed_units
    ) {
        @($ConsultationReceipt.routed_units)
    } else {
        @()
    }
    $consultedCount = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'summary') -and
        $null -ne $ConsultationReceipt.summary -and
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt.summary -PropertyName 'consulted_unit_count')
    ) {
        [int]$ConsultationReceipt.summary.consulted_unit_count
    } else {
        @($consultedUnits).Count
    }
    $routedCount = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'summary') -and
        $null -ne $ConsultationReceipt.summary -and
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt.summary -PropertyName 'routed_unit_count')
    ) {
        [int]$ConsultationReceipt.summary.routed_unit_count
    } else {
        @($routedUnits).Count
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @(if ($routedCount -gt 0 -and $consultedCount -eq 0) {
        ('Specialist consultation routing during {0}:' -f $windowId)
    } elseif ($consultedCount -gt 0 -and $routedCount -eq 0) {
        ('Specialist consultation during {0}:' -f $windowId)
    } else {
        ('Recorded specialist consultation chain during {0}:' -f $windowId)
    })
    foreach ($disclosure in @($ConsultationReceipt.user_disclosures)) {
        if ($null -eq $disclosure) {
            continue
        }

        $consultedUnit = $null
        foreach ($candidate in @($consultedUnits)) {
            if ($null -ne $candidate -and [string]$candidate.skill_id -eq [string]$disclosure.skill_id) {
                $consultedUnit = $candidate
                break
            }
        }
        $routedUnit = $null
        foreach ($candidate in @($routedUnits)) {
            if ($null -ne $candidate -and [string]$candidate.skill_id -eq [string]$disclosure.skill_id) {
                $routedUnit = $candidate
                break
            }
        }

        $skills.Add(
            [pscustomobject]@{
                skill_id = [string]$disclosure.skill_id
                why_now = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'why_now') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.why_now)) { [string]$disclosure.why_now } else { $null }
                native_skill_entrypoint = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.native_skill_entrypoint)) { [string]$disclosure.native_skill_entrypoint } else { $null }
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.native_skill_description)) { [string]$disclosure.native_skill_description } else { $null }
                state = if ($consultedUnit -and (Test-VibeObjectHasProperty -InputObject $consultedUnit -PropertyName 'status')) {
                    [string]$consultedUnit.status
                } elseif ($routedUnit -and (Test-VibeObjectHasProperty -InputObject $routedUnit -PropertyName 'status')) {
                    [string]$routedUnit.status
                } else {
                    'consultation_disclosed'
                }
                summary = if ($consultedUnit -and (Test-VibeObjectHasProperty -InputObject $consultedUnit -PropertyName 'summary')) {
                    [string]$consultedUnit.summary
                } elseif ($routedUnit -and (Test-VibeObjectHasProperty -InputObject $routedUnit -PropertyName 'summary')) {
                    [string]$routedUnit.summary
                } else {
                    $null
                }
            }
        ) | Out-Null
        $renderedLines += ('- {0}: {1} ({2})' -f [string]$disclosure.skill_id, [string]$disclosure.why_now, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $disclosure))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = ('{0}_consultation' -f $windowId)
        truth_layer = 'consultation'
        stage = if ((Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$ConsultationReceipt.stage)) { [string]$ConsultationReceipt.stage } else { $windowId }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistExecutionLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$ExecutionManifest = $null
    )

    if ($null -eq $SpecialistUserDisclosure) {
        return $null
    }

    $executedSkillIds = @()
    if ($null -ne $ExecutionManifest -and (Test-VibeObjectHasProperty -InputObject $ExecutionManifest -PropertyName 'specialist_accounting') -and $null -ne $ExecutionManifest.specialist_accounting) {
        foreach ($unit in @($ExecutionManifest.specialist_accounting.executed_skill_execution_units)) {
            if ($null -eq $unit) {
                continue
            }
            if ((Test-VibeObjectHasProperty -InputObject $unit -PropertyName 'skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$unit.skill_id)) {
                $executedSkillIds += [string]$unit.skill_id
            } elseif ((Test-VibeObjectHasProperty -InputObject $unit -PropertyName 'specialist_skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$unit.specialist_skill_id)) {
                $executedSkillIds += [string]$unit.specialist_skill_id
            }
        }
        $executedSkillIds = @($executedSkillIds | Select-Object -Unique)
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @('Execution-chain specialist disclosure:')
    foreach ($entry in @($SpecialistUserDisclosure.routed_skills)) {
        if ($null -eq $entry) {
            continue
        }
        $skillId = [string]$entry.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        $state = if ($executedSkillIds -contains $skillId) { 'executed' } else { 'disclosed_for_execution' }
        $skills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                why_now = 'approved for execution-time specialist dispatch under governed vibe'
                native_skill_entrypoint = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_entrypoint)) { [string]$entry.native_skill_entrypoint } else { $null }
                native_skill_entrypoint_raw = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_entrypoint_raw') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_entrypoint_raw)) { [string]$entry.native_skill_entrypoint_raw } else { $null }
                entrypoint_path_state = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_path_state') -and -not [string]::IsNullOrWhiteSpace([string]$entry.entrypoint_path_state)) { [string]$entry.entrypoint_path_state } else { 'resolved' }
                entrypoint_missing = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_missing')) { [bool]$entry.entrypoint_missing } else { $false }
                entrypoint_path_invalid = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_path_invalid')) { [bool]$entry.entrypoint_path_invalid } else { $false }
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_description)) { [string]$entry.native_skill_description } else { $null }
                state = $state
            }
        ) | Out-Null
        $renderedLines += ('- {0}: approved for execution ({1})' -f $skillId, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $entry))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = 'execution_dispatch'
        truth_layer = 'execution'
        stage = if ((Test-VibeObjectHasProperty -InputObject $SpecialistUserDisclosure -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$SpecialistUserDisclosure.stage)) { [string]$SpecialistUserDisclosure.stage } else { 'plan_execute' }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistLifecycleDisclosureProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$DiscussionConsultationReceipt = $null,
        [AllowNull()] [object]$PlanningConsultationReceipt = $null,
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$ExecutionManifest = $null
    )

    $layers = New-Object System.Collections.Generic.List[object]
    foreach ($candidate in @(
        (New-VibeSpecialistRoutingLifecycleLayerProjection -RuntimeInputPacket $RuntimeInputPacket),
        (New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $DiscussionConsultationReceipt),
        (New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $PlanningConsultationReceipt),
        (New-VibeSpecialistExecutionLifecycleLayerProjection -SpecialistUserDisclosure $SpecialistUserDisclosure -ExecutionManifest $ExecutionManifest)
    )) {
        if ($null -ne $candidate) {
            $layers.Add($candidate) | Out-Null
        }
    }

    $layerArray = [object[]]$layers.ToArray()
    $skillIds = @()
    $renderedSections = @()
    foreach ($layer in @($layerArray)) {
        foreach ($skill in @($layer.skills)) {
            if ($null -ne $skill -and -not [string]::IsNullOrWhiteSpace([string]$skill.skill_id)) {
                $skillIds += [string]$skill.skill_id
            }
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$layer.rendered_text)) {
            $renderedSections += [string]$layer.rendered_text
        }
    }
    $skillIds = @($skillIds | Select-Object -Unique)
    $hasConsultationLayer = @($layerArray | Where-Object { [string]$_.truth_layer -eq 'consultation' }).Count -gt 0
    $renderedIntro = if ($hasConsultationLayer) {
        @(
            'Legacy specialist lifecycle disclosure.',
            'Old routing, consultation, and execution records remain readable. Usage claims still require `skill_usage.used` evidence.'
        )
    } else {
        @(
            'Skill routing and usage evidence.',
            'This disclosure records selected skills and material-use evidence. A selected skill is not a `used` claim; material use requires `skill_usage.used` plus `skill_usage.evidence`.'
        )
    }

    return [pscustomobject]@{
        enabled = [bool](@($layerArray).Count -gt 0)
        truth_model = if ($hasConsultationLayer) {
            'legacy_routing_consultation_execution_separated'
        } else {
            'skill_routing_usage_evidence'
        }
        layer_count = @($layerArray).Count
        skill_count = @($skillIds).Count
        skill_ids = @($skillIds)
        layers = $layerArray
        rendered_text = (@($renderedIntro) + @($renderedSections) -join "`n`n")
    }
}

function Get-VibeSpecialistLifecycleDisclosureMarkdownLines {
    param(
        [AllowNull()] [object]$LifecycleDisclosure = $null,
        [AllowEmptyCollection()] [string[]]$IncludeLayerIds = @()
    )

    if ($null -eq $LifecycleDisclosure -or -not [bool]$LifecycleDisclosure.enabled) {
        return @()
    }

    $allowedLayerIds = @($IncludeLayerIds | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    $hasConsultationLayer = @($LifecycleDisclosure.layers | Where-Object { [string]$_.truth_layer -eq 'consultation' }).Count -gt 0
    $lines = if ($hasConsultationLayer) {
        @(
            '## Legacy Specialist Lifecycle Disclosure',
            'This legacy disclosure keeps old routing, consultation, and execution records readable. Usage claims still require `skill_usage.used` evidence.'
        )
    } else {
        @(
            '## Skill Routing And Usage Evidence',
            'This disclosure records selected skills and material-use evidence. A selected skill is not a `used` claim; material use requires `skill_usage.used` plus `skill_usage.evidence`.'
        )
    }
    foreach ($layer in @($LifecycleDisclosure.layers)) {
        if ($allowedLayerIds.Count -gt 0 -and -not ($allowedLayerIds -contains [string]$layer.layer_id)) {
            continue
        }
        $lines += @(
            '',
            ('### {0}' -f [string]$layer.layer_id)
        )
        foreach ($skill in @($layer.skills)) {
            $lines += @(
                ('- Skill: {0}' -f [string]$skill.skill_id),
                ('  State: {0}' -f [string]$skill.state),
                ('  Why now: {0}' -f [string]$skill.why_now),
                ('  Loaded from: {0}' -f (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $skill))
            )
        }
    }

    return @($lines)
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

function New-VibeHostUserBriefingSegmentProjection {
    param(
        [AllowNull()] [object]$LifecycleLayer = $null,
        [AllowNull()] [object]$ConsultationReceipt = $null
    )

    if ($null -eq $LifecycleLayer) {
        return $null
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'layer_id') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.layer_id)) {
        [string]$LifecycleLayer.layer_id
    } else {
        return $null
    }

    $segmentLines = @()
    $category = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.truth_layer)) {
        [string]$LifecycleLayer.truth_layer
    } else {
        'informational'
    }
    $status = 'informational'
    $gateStatus = $null

    switch ($segmentId) {
        'discussion_routing' {
            $segmentLines += 'Vibe routed these Skills into the discussion/planning chain:'
        }
        'execution_dispatch' {
            $category = 'execution'
            $status = 'execution_disclosure'
            $segmentLines += 'Selected skills are available for execution. This is not a `used` claim; final use must come from `skill_usage.used` and evidence.'
        }
        default {
            if ($segmentId -match '^(discussion|planning)_consultation$') {
                $windowId = [string]$Matches[1]
                $freezeGate = Get-VibePropertySafe -InputObject $ConsultationReceipt -PropertyName 'freeze_gate'
                if ($freezeGate) {
                    $gateStatus = if ([bool]$freezeGate.passed) { 'passed' } else { 'failed' }
                    $status = if ([bool]$freezeGate.passed) { 'gate_passed' } else { 'gate_failed' }
                } else {
                    $gateStatus = 'not_applicable'
                    $status = 'gate_unknown'
                }
                $category = 'consultation'
                $consultedUnits = if (
                    $ConsultationReceipt -and
                    (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'consulted_units') -and
                    $null -ne $ConsultationReceipt.consulted_units
                ) {
                    @($ConsultationReceipt.consulted_units)
                } else {
                    @()
                }
                $routedUnits = if (
                    $ConsultationReceipt -and
                    (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'routed_units') -and
                    $null -ne $ConsultationReceipt.routed_units
                ) {
                    @($ConsultationReceipt.routed_units)
                } else {
                    @()
                }
                $summary = Get-VibePropertySafe -InputObject $ConsultationReceipt -PropertyName 'summary'
                $consultedCount = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('consulted_unit_count') -DefaultValue @($consultedUnits).Count
                $routedCount = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('routed_unit_count') -DefaultValue @($routedUnits).Count
                if ($routedCount -gt 0 -and $consultedCount -eq 0) {
                    $segmentLines += ('Vibe routed these Skills for legacy consultation disclosure during {0}; freeze gate: {1}. Usage claims still require `skill_usage` evidence.' -f $windowId, $gateStatus)
                } elseif ($consultedCount -gt 0 -and $routedCount -eq 0) {
                    $segmentLines += ('Vibe recorded these Skills in the {0} consultation audit chain; freeze gate: {1}. Usage claims still require `skill_usage` evidence.' -f $windowId, $gateStatus)
                } else {
                    $segmentLines += ('Vibe recorded these Skills in the {0} consultation chain; freeze gate: {1}.' -f $windowId, $gateStatus)
                }
            } else {
                $segmentLines += ('Vibe reported specialist activity for {0}:' -f $segmentId)
            }
        }
    }

    foreach ($skill in @($LifecycleLayer.skills)) {
        if ($null -eq $skill) {
            continue
        }
        $skillId = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$skill.skill_id)) {
            [string]$skill.skill_id
        } else {
            continue
        }
        $state = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'state') -and -not [string]::IsNullOrWhiteSpace([string]$skill.state)) { [string]$skill.state } else { 'reported' }
        $entrypoint = Get-VibeSpecialistEntrypointDisplayText -SkillRecord $skill
        $whyNow = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'why_now') -and -not [string]::IsNullOrWhiteSpace([string]$skill.why_now)) { [string]$skill.why_now } else { 'no additional rationale recorded' }
        $segmentLines += ('- {0} [{1}] from {2}' -f $skillId, $state, $entrypoint)
        $segmentLines += ('  Why: {0}' -f $whyNow)
        if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'summary') -and -not [string]::IsNullOrWhiteSpace([string]$skill.summary)) {
            $segmentLines += ('  Summary: {0}' -f [string]$skill.summary)
        }
    }

    $segmentText = @($segmentLines) -join "`n"
    return [pscustomobject]@{
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.stage)) { [string]$LifecycleLayer.stage } else { $null }
        category = $category
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.truth_layer)) { [string]$LifecycleLayer.truth_layer } else { $category }
        status = $status
        gate_status = $gateStatus
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'skill_count')) { [int]$LifecycleLayer.skill_count } else { @($LifecycleLayer.skills).Count }
        skills = @($LifecycleLayer.skills)
        rendered_text = $segmentText
    }
}

function New-VibeHostStageDisclosureEventProjection {
    param(
        [AllowNull()] [object]$Segment = $null
    )

    if ($null -eq $Segment) {
        return $null
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'segment_id') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.segment_id)) {
        [string]$Segment.segment_id
    } else {
        return $null
    }

    $hasRoutedConsultation = $false
    $hasCompletedConsultation = $false
    foreach ($skill in @($Segment.skills)) {
        if ($null -eq $skill -or -not (Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'state')) {
            continue
        }
        $state = [string]$skill.state
        if ($state -match '(^|_)routed($|_)') {
            $hasRoutedConsultation = $true
        }
        if ($state -in @('completed', 'completed_with_notes', 'consulted')) {
            $hasCompletedConsultation = $true
        }
    }

    $eventId = switch ($segmentId) {
        'discussion_routing' { 'discussion_routing_frozen' }
        'discussion_consultation' {
            if ($hasCompletedConsultation -and -not $hasRoutedConsultation) {
                'discussion_consultation_completed'
            } elseif ($hasRoutedConsultation -and -not $hasCompletedConsultation) {
                'discussion_consultation_routed'
            } else {
                'discussion_consultation_reported'
            }
        }
        'planning_consultation' {
            if ($hasCompletedConsultation -and -not $hasRoutedConsultation) {
                'planning_consultation_completed'
            } elseif ($hasRoutedConsultation -and -not $hasCompletedConsultation) {
                'planning_consultation_routed'
            } else {
                'planning_consultation_reported'
            }
        }
        'execution_dispatch' { 'execution_dispatch_confirmed' }
        default { ('{0}_reported' -f $segmentId) }
    }

    return [pscustomobject]@{
        event_id = $eventId
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.stage)) { [string]$Segment.stage } else { $null }
        category = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'category') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.category)) { [string]$Segment.category } else { $null }
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.truth_layer)) { [string]$Segment.truth_layer } else { $null }
        status = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'status') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.status)) { [string]$Segment.status } else { 'reported' }
        gate_status = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'gate_status') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.gate_status)) { [string]$Segment.gate_status } else { $null }
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'skill_count')) { [int]$Segment.skill_count } else { @($Segment.skills).Count }
        skills = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'skills')) { @($Segment.skills) } else { @() }
        rendered_text = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'rendered_text') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.rendered_text)) { [string]$Segment.rendered_text } else { $null }
    }
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
        [AllowNull()] [object]$LifecycleDisclosure = $null,
        [AllowNull()] [object]$DiscussionConsultationReceipt = $null,
        [AllowNull()] [object]$PlanningConsultationReceipt = $null,
        [AllowNull()] [object]$BoundedReturnControl = $null,
        [AllowNull()] [object]$DeliveryAcceptanceReport = $null
    )

    $segments = New-Object System.Collections.Generic.List[object]
    $renderedSections = @()

    $deliverySummary = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'summary'
    $deliveryExecutionContext = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'execution_context'
    $specialistHostContinuationPending = [bool](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('specialist_host_continuation_pending') -DefaultValue $false)
    if ($specialistHostContinuationPending) {
        $deliveryGateResult = [string](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('gate_result') -DefaultValue '')
        $deliveryReadinessState = [string](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('readiness_state') -DefaultValue '')
        $deliveryCompletionAllowed = [bool](Get-VibeNestedPropertySafe -InputObject $deliverySummary -PropertyPath @('completion_language_allowed') -DefaultValue $false)
        $sourceRunId = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('run_id') -DefaultValue '')
        $sessionRoot = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('session_root') -DefaultValue '')
        $effectiveExecutionStatus = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('specialist_effective_execution_status') -DefaultValue '')
        $sidecarPath = [string](Get-VibeNestedPropertySafe -InputObject $deliveryExecutionContext -PropertyPath @('specialist_execution_sidecar_path') -DefaultValue '')
        if ([string]::IsNullOrWhiteSpace($sidecarPath) -and -not [string]::IsNullOrWhiteSpace($sessionRoot)) {
            $sidecarPath = Get-VibeSpecialistExecutionSidecarPath -SessionRoot $sessionRoot
        }
        $directRoutedUnitIds = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'direct_routed_skill_execution_unit_ids') -and
            $null -ne $deliveryExecutionContext.direct_routed_skill_execution_unit_ids
        ) {
            @($deliveryExecutionContext.direct_routed_skill_execution_unit_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $directRoutedSkillIds = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'direct_routed_skill_execution_skill_ids') -and
            $null -ne $deliveryExecutionContext.direct_routed_skill_execution_skill_ids
        ) {
            @($deliveryExecutionContext.direct_routed_skill_execution_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        } else {
            @()
        }
        $rawDirectRoutedUnits = if (
            $deliveryExecutionContext -and
            (Test-VibeObjectHasProperty -InputObject $deliveryExecutionContext -PropertyName 'direct_routed_skill_execution_units') -and
            $null -ne $deliveryExecutionContext.direct_routed_skill_execution_units
        ) {
            @($deliveryExecutionContext.direct_routed_skill_execution_units)
        } else {
            @()
        }
        $requiredUnits = New-Object System.Collections.Generic.List[object]
        foreach ($unit in $rawDirectRoutedUnits) {
            if ($null -eq $unit) {
                continue
            }
            $requiredUnits.Add([pscustomobject]@{
                unit_id = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'unit_id')
                skill_id = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'skill_id')
                native_skill_entrypoint = [string](Get-VibePropertySafe -InputObject $unit -PropertyName 'native_skill_entrypoint')
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
            decision_kind = 'specialist_execution_resolution'
            decision_context = 'execution_handoff'
            source_run_id = if ([string]::IsNullOrWhiteSpace($sourceRunId)) { $null } else { $sourceRunId }
            session_root = if ([string]::IsNullOrWhiteSpace($sessionRoot)) { $null } else { $sessionRoot }
            sidecar_path = if ([string]::IsNullOrWhiteSpace($sidecarPath)) { $null } else { $sidecarPath }
            verification_refresh_command = [string]$refreshCommandHint
            allowed_resolution_states = @('executed', 'degraded', 'blocked')
            direct_routed_unit_ids = @($directRoutedUnitIds)
            direct_routed_skill_ids = @($directRoutedSkillIds)
            required_units = $requiredUnitArray
            preferred_payload = [pscustomobject]@{
                protocol_version = 'v1'
                source_run_id = if ([string]::IsNullOrWhiteSpace($sourceRunId)) { $null } else { $sourceRunId }
                resolution_mode = 'current_session_host_execution'
                units = @(
                    foreach ($requiredUnit in $requiredUnitArray) {
                        [pscustomobject]@{
                            unit_id = [string](Get-VibePropertySafe -InputObject $requiredUnit -PropertyName 'unit_id')
                            skill_id = [string](Get-VibePropertySafe -InputObject $requiredUnit -PropertyName 'skill_id')
                            resolution_state = 'executed'
                            native_skill_entrypoint = [string](Get-VibePropertySafe -InputObject $requiredUnit -PropertyName 'native_skill_entrypoint')
                            evidence_paths = @('<host evidence path>')
                            notes = ''
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
            'Execution handoff is still pending under governed vibe.',
            ('- gate_result: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($deliveryGateResult)) { 'unknown' } else { $deliveryGateResult })),
            ('- readiness_state: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($deliveryReadinessState)) { 'unknown' } else { $deliveryReadinessState })),
            ('- completion_language_allowed: `{0}`' -f $deliveryCompletionAllowed),
            ('- source_run_id: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($sourceRunId)) { 'unknown' } else { $sourceRunId })),
            ('- specialist_effective_execution_status: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($effectiveExecutionStatus)) { 'unknown' } else { $effectiveExecutionStatus })),
            ('- direct_routed_unit_ids: `{0}`' -f $(if (@($directRoutedUnitIds).Count -gt 0) { @($directRoutedUnitIds) -join '`, `' } else { 'none recorded' })),
            ('- direct_routed_skill_ids: `{0}`' -f $(if (@($directRoutedSkillIds).Count -gt 0) { @($directRoutedSkillIds) -join '`, `' } else { 'none recorded' })),
            ('- specialist_execution_sidecar_path: `{0}`' -f $(if ([string]::IsNullOrWhiteSpace($sidecarPath)) { 'unknown' } else { $sidecarPath })),
            '- approved specialist execution has not been formally resolved inside the governed runtime yet.',
            '- next required action: load each disclosed `native_skill_entrypoint` in the current host session, execute the bounded specialist work there, write `specialist-execution.json`, then refresh governed verification before claiming completion.',
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
            skill_count = @($directRoutedSkillIds).Count
            skills = @($directRoutedSkillIds)
            rendered_text = (@($continuationLines) -join "`n")
            host_decision_contract = $executionHandoffContract
        }
        $segments.Add($continuationSegment) | Out-Null
        $renderedSections += 'Governed runtime handoff status:'
        $renderedSections += @('', [string]$continuationSegment.rendered_text)
    }

    if ($null -ne $LifecycleDisclosure -and [bool]$LifecycleDisclosure.enabled) {
        $consultationReceiptIndex = @{}
        foreach ($receipt in @($DiscussionConsultationReceipt, $PlanningConsultationReceipt)) {
            if ($null -eq $receipt) {
                continue
            }
            $windowId = if ((Test-VibeObjectHasProperty -InputObject $receipt -PropertyName 'window_id') -and -not [string]::IsNullOrWhiteSpace([string]$receipt.window_id)) {
                [string]$receipt.window_id
            } else {
                $null
            }
            if (-not [string]::IsNullOrWhiteSpace($windowId)) {
                $consultationReceiptIndex[$windowId] = $receipt
            }
        }

        $renderedSections += 'Specialist activity under governed vibe:'
        foreach ($layer in @($LifecycleDisclosure.layers)) {
            if ($null -eq $layer) {
                continue
            }
            $windowId = $null
            if ((Test-VibeObjectHasProperty -InputObject $layer -PropertyName 'layer_id') -and [string]$layer.layer_id -match '^(discussion|planning)_consultation$') {
                $windowId = [string]$Matches[1]
            }
            $receipt = if (-not [string]::IsNullOrWhiteSpace($windowId) -and $consultationReceiptIndex.ContainsKey($windowId)) { $consultationReceiptIndex[$windowId] } else { $null }
            $segment = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $layer -ConsultationReceipt $receipt
            if ($null -eq $segment) {
                continue
            }
            $segments.Add($segment) | Out-Null
            $renderedSections += @('', [string]$segment.rendered_text)
        }
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
        $boundedLines = @(
            'Bounded governed stop reached. Return control to the user now.',
            ('- terminal stage: `{0}`' -f [string]$BoundedReturnControl.terminal_stage),
            ('- source run id: `{0}`' -f [string]$BoundedReturnControl.source_run_id),
            ('- allowed follow-up entries: `{0}`' -f (@($allowedFollowupEntryIds) -join '`, `')),
            ('- next governed stage after approval: `{0}`' -f $(if ($nextStage) { $nextStage } else { 'none' })),
            ('- approval kind: `{0}`' -f [string]$approvalKind),
            ('- preferred structured approval action: `{0}`' -f [string]$preferredDecisionAction),
            ('- approval instruction: {0}' -f [string]$approvalPrompt),
            '- do not continue in the same assistant turn; wait for a new user message before consuming re-entry credentials',
            ('- if you intentionally continue, forward `--continue-from-run-id {0}` and `--bounded-reentry-token {1}` from the latest runtime summary' -f [string]$BoundedReturnControl.source_run_id, [string]$BoundedReturnControl.reentry_token)
        )
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

    $hasLifecycleDisclosure = ($null -ne $LifecycleDisclosure -and [bool]$LifecycleDisclosure.enabled)
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
        mode = if ($hasExecutionHandoffOnly -and -not $hasLifecycleDisclosure -and -not $hasBoundedReturnControl) {
            'execution_handoff_host_briefing'
        } elseif ($hasLifecycleDisclosure) {
            if ($hasBoundedReturnControl) {
                'progressive_host_user_briefing'
            } else {
                'progressive_specialist_host_briefing'
            }
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
        [AllowNull()] [object]$SpecialistDecision = $null,
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$SpecialistConsultation = $null,
        [AllowNull()] [object]$SpecialistLifecycleDisclosure = $null,
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
        specialist_decision = $SpecialistDecision
        specialist_user_disclosure = $SpecialistUserDisclosure
        specialist_consultation = $SpecialistConsultation
        specialist_lifecycle_disclosure = $SpecialistLifecycleDisclosure
        host_stage_disclosure = $HostStageDisclosure
        host_user_briefing = $HostUserBriefing
        bounded_return_control = $BoundedReturnControl
        artifacts_relative = $RelativeArtifacts
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
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    return [string](New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -Runtime $Runtime -ArtifactRoot $ArtifactRoot).artifact_root
}

function Get-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -Runtime $Runtime -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("outputs\runtime\vibe-sessions\{0}" -f $RunId)))
}

function Ensure-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -Runtime $Runtime -ArtifactRoot $ArtifactRoot
    New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null
    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        Initialize-VibeWorkspaceProjectDescriptor -RepoRoot $RepoRoot -Runtime $Runtime | Out-Null
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
        'candidate[- ]scor',
        'grade[- ]selection',
        'task[- ]classification'
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
        '调研',
        '研究'
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
        'runtime',
        'router',
        'routing',
        '更新',
        '增强',
        '执行',
        '修改',
        '安装',
        '集成',
        '运行时',
        '路由',
        '工作流'
    )
    $reviewScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $reviewPatterns
    $debugScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $debugPatterns
    $researchScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $researchPatterns
    $codingScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $codingPatterns
    $routerContextScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $routerDiagnosticContextPatterns
    if ($routerContextScore -gt 0) {
        $routerDebugScore = Get-VibeTaskSignalCount -TaskLower $taskLower -Patterns $routerDiagnosticPatterns
        if ($routerDebugScore -gt $debugScore) {
            $debugScore = $routerDebugScore
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
        'xl',
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
        'candidate[- ]scor',
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

    foreach ($pattern in $xlPatterns) {
        if (Test-VibeTaskSignalHit -TaskLower $taskLower -Pattern $pattern) {
            $grade = 'XL'
            break
        }
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
        [Parameter(Mandatory)] [string]$Mode
    )

    $Mode = Resolve-VibeRuntimeMode -Mode $Mode
    $title = Get-VibeTitleFromTask -Task $Task
    $grade = Get-VibeInternalGrade -Task $Task
    $assumptions = @()
    $assumptions += 'Interactive clarification is allowed if unresolved ambiguity materially changes implementation.'
    return [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        title = $title
        goal = $title
        deliverable = 'Governed implementation artifacts, verification evidence, and cleanup receipts'
        constraints = @(
            'Do not bypass the fixed six-stage governed runtime.',
            'Do not widen scope silently beyond the frozen requirement document.'
        )
        acceptance_criteria = @(
            'Requirement document is frozen before execution.',
            'Execution plan exists before implementation.',
            'Verification evidence exists before completion claims.',
            'Phase cleanup receipt is produced.'
        )
        non_goals = @(
            'Do not treat M/L/XL as user-facing entry branches.',
            'Do not introduce a second router or control plane.'
        )
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

function Get-VibeExecutionTopologyPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $sessionRoot 'execution-topology.json'))
}
