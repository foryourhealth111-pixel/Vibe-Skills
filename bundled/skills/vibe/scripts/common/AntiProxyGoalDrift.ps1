Set-StrictMode -Version Latest

function Get-VgoAntiProxyGoalDriftPolicy {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $path = Join-Path $RepoRoot 'config\anti-proxy-goal-drift-policy.json'
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Anti-proxy-goal-drift policy missing: $path"
    }

    return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-VgoTierRank {
    param([AllowNull()] [string]$Tier)

    switch ($Tier) {
        'Tier A' { return 3 }
        'Tier B' { return 2 }
        'Tier C' { return 1 }
        default { return 0 }
    }
}

function Test-VgoValuePresent {
    param([AllowNull()] [object]$Value)

    if ($null -eq $Value) { return $false }
    if ($Value -is [string]) { return (-not [string]::IsNullOrWhiteSpace($Value)) }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        return (@($Value).Count -gt 0)
    }
    return $true
}

function Get-VgoMinimumTierForSurface {
    param(
        [Parameter(Mandatory)] [psobject]$Policy,
        [AllowNull()] [string]$SurfaceClass
    )

    if ([string]::IsNullOrWhiteSpace($SurfaceClass)) {
        return $null
    }

    $prop = $Policy.surface_minimum_tiers.PSObject.Properties[$SurfaceClass]
    if ($null -eq $prop) {
        return $null
    }

    return [string]$prop.Value
}

function Get-VgoProofCaseCount {
    param([AllowNull()] [object]$Bundle)

    if ($null -eq $Bundle) { return 0 }
    if ($Bundle.PSObject.Properties.Name -contains 'cases') {
        return @($Bundle.cases).Count
    }
    return 0
}

function Get-VgoRequiredProofCaseCount {
    param(
        [Parameter(Mandatory)] [psobject]$Policy,
        [AllowNull()] [string]$Tier,
        [AllowNull()] [string]$CompletionState
    )

    if ([string]::IsNullOrWhiteSpace($Tier) -or [string]::IsNullOrWhiteSpace($CompletionState)) {
        return 0
    }

    $tierPolicy = $Policy.proof_bundle_minimums.PSObject.Properties[$Tier]
    if ($null -eq $tierPolicy) { return 0 }
    $statePolicy = $tierPolicy.Value.PSObject.Properties[$CompletionState]
    if ($null -eq $statePolicy) { return 0 }
    return [int]$statePolicy.Value
}

function Test-VgoGeneralizedScope {
    param([AllowNull()] [string]$IntendedScope)

    if ([string]::IsNullOrWhiteSpace($IntendedScope)) { return $false }
    $normalized = $IntendedScope.Trim().ToLowerInvariant()
    return @('generalized', 'class_level', 'reusable', 'shared', 'systemic') -contains $normalized
}

function Test-VgoScenarioSpecificScope {
    param([AllowNull()] [string]$IntendedScope)

    if ([string]::IsNullOrWhiteSpace($IntendedScope)) { return $false }
    $normalized = $IntendedScope.Trim().ToLowerInvariant()
    return @('scenario_specific', 'scenario-local', 'scenario_local', 'bounded_local') -contains $normalized
}

function Get-VgoProxySignalTokens {
    param([AllowNull()] [object]$Signals)

    $tokens = @()
    foreach ($signal in @($Signals)) {
        if ([string]::IsNullOrWhiteSpace([string]$signal)) { continue }
        $tokens += ([string]$signal).Trim().ToLowerInvariant()
    }
    return $tokens
}

function Get-VgoAntiProxyGoalDriftAssessment {
    param(
        [Parameter(Mandatory)] [psobject]$Policy,
        [Parameter(Mandatory)] [psobject]$Packet
    )

    $requiredFields = @(
        'surface_class',
        'primary_objective',
        'non_objective_proxy_signals',
        'validation_material_role',
        'anti_proxy_goal_drift_tier',
        'intended_scope',
        'abstraction_layer_target',
        'completion_state',
        'generalization_evidence_bundle'
    )

    $missingFields = New-Object System.Collections.Generic.List[string]
    foreach ($field in $requiredFields) {
        $value = if ($Packet.PSObject.Properties.Name -contains $field) { $Packet.$field } else { $null }
        if (-not (Test-VgoValuePresent -Value $value)) {
            [void]$missingFields.Add($field)
        }
    }

    $declaredTier = if ($Packet.PSObject.Properties.Name -contains 'anti_proxy_goal_drift_tier') { [string]$Packet.anti_proxy_goal_drift_tier } else { $null }
    $surfaceClass = if ($Packet.PSObject.Properties.Name -contains 'surface_class') { [string]$Packet.surface_class } else { $null }
    $completionState = if ($Packet.PSObject.Properties.Name -contains 'completion_state') { [string]$Packet.completion_state } else { $null }
    $intendedScope = if ($Packet.PSObject.Properties.Name -contains 'intended_scope') { [string]$Packet.intended_scope } else { $null }
    $validationMaterialRole = if ($Packet.PSObject.Properties.Name -contains 'validation_material_role') { [string]$Packet.validation_material_role } else { $null }
    $signals = if ($Packet.PSObject.Properties.Name -contains 'non_objective_proxy_signals') { @($Packet.non_objective_proxy_signals) } else { @() }
    $bundle = if ($Packet.PSObject.Properties.Name -contains 'generalization_evidence_bundle') { $Packet.generalization_evidence_bundle } else { $null }

    $minimumTier = Get-VgoMinimumTierForSurface -Policy $Policy -SurfaceClass $surfaceClass
    $declaredTierRank = Get-VgoTierRank -Tier $declaredTier
    $minimumTierRank = Get-VgoTierRank -Tier $minimumTier
    $actualCaseCount = Get-VgoProofCaseCount -Bundle $bundle
    $requiredCaseCount = Get-VgoRequiredProofCaseCount -Policy $Policy -Tier $declaredTier -CompletionState $completionState
    $warningCodes = New-Object System.Collections.Generic.List[string]

    if ($missingFields.Count -gt 0) {
        [void]$warningCodes.Add('missing_required_field')
    }

    if ($minimumTierRank -gt 0 -and $declaredTierRank -gt 0) {
        if ($declaredTierRank -lt $minimumTierRank) {
            [void]$warningCodes.Add('tier_underclassified')
        } elseif ($declaredTierRank -gt $minimumTierRank) {
            [void]$warningCodes.Add('tier_overclassified')
        }
    }

    if ($requiredCaseCount -gt 0 -and $actualCaseCount -lt $requiredCaseCount) {
        [void]$warningCodes.Add('completion_proof_mismatch')
    }

    $isGeneralized = Test-VgoGeneralizedScope -IntendedScope $intendedScope
    if ($isGeneralized -and $completionState -eq 'complete' -and $actualCaseCount -le 1) {
        [void]$warningCodes.Add('generalization_overclaim')
    }

    $signalTokens = @(Get-VgoProxySignalTokens -Signals $signals)
    $containsProxyTemptation = $false
    foreach ($token in $signalTokens) {
        if ($token.Contains('sample') -or $token.Contains('demo') -or $token.Contains('test green') -or $token.Contains('current test') -or $token.Contains('single case')) {
            $containsProxyTemptation = $true
            break
        }
    }

    if ($containsProxyTemptation -and $completionState -eq 'complete' -and ($actualCaseCount -le 1 -or $validationMaterialRole -ne 'validation_only')) {
        [void]$warningCodes.Add('proxy_signal_overclaim')
    }

    $uniqueWarnings = @($warningCodes | Select-Object -Unique)

    return [pscustomobject]@{
        fixture_id = if ($Packet.PSObject.Properties.Name -contains 'fixture_id') { [string]$Packet.fixture_id } else { '' }
        surface_class = $surfaceClass
        declared_tier = $declaredTier
        minimum_tier = $minimumTier
        completion_state = $completionState
        intended_scope = $intendedScope
        validation_material_role = $validationMaterialRole
        missing_fields = @($missingFields)
        proof_case_count = $actualCaseCount
        required_proof_case_count = $requiredCaseCount
        warning_codes = @($uniqueWarnings)
        warning_count = @($uniqueWarnings).Count
        report_only = $true
        generalized_scope = [bool]$isGeneralized
        scenario_specific_scope = [bool](Test-VgoScenarioSpecificScope -IntendedScope $intendedScope)
    }
}

function ConvertFrom-VgoMarkdownValue {
    param([AllowNull()] [string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ''
    }

    $value = $Text.Trim()
    if ($value.StartsWith('-')) {
        $value = $value.Substring(1).Trim()
    }
    if ($value.StartsWith('`') -and $value.EndsWith('`') -and $value.Length -ge 2) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($value -eq '_author_to_declare_') {
        return ''
    }

    return $value.Trim()
}

function Get-VgoMarkdownSectionMap {
    param([Parameter(Mandatory)] [AllowEmptyCollection()] [AllowEmptyString()] [string[]]$Lines)

    $sections = @{}
    $currentHeading = $null
    $buffer = New-Object System.Collections.Generic.List[string]

    foreach ($line in $Lines) {
        if ($line -match '^##\s+(.+?)\s*$') {
            if ($null -ne $currentHeading) {
                $sections[$currentHeading] = @($buffer)
                $buffer.Clear()
            }
            $currentHeading = $Matches[1].Trim()
            continue
        }

        if ($null -ne $currentHeading) {
            [void]$buffer.Add($line)
        }
    }

    if ($null -ne $currentHeading) {
        $sections[$currentHeading] = @($buffer)
    }

    return $sections
}

function Get-VgoMarkdownSectionScalar {
    param(
        [Parameter(Mandatory)] [hashtable]$Sections,
        [Parameter(Mandatory)] [string]$Heading
    )

    if (-not $Sections.ContainsKey($Heading)) {
        return ''
    }

    foreach ($line in @($Sections[$Heading])) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith('_')) { continue }
        return (ConvertFrom-VgoMarkdownValue -Text $trimmed)
    }

    return ''
}

function Get-VgoMarkdownSectionList {
    param(
        [Parameter(Mandatory)] [hashtable]$Sections,
        [Parameter(Mandatory)] [string]$Heading
    )

    if (-not $Sections.ContainsKey($Heading)) {
        return @()
    }

    $items = New-Object System.Collections.Generic.List[string]
    foreach ($line in @($Sections[$Heading])) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith('_')) { continue }
        if ($trimmed.StartsWith('-')) {
            $value = ConvertFrom-VgoMarkdownValue -Text $trimmed
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                [void]$items.Add($value)
            }
        }
    }

    if ($items.Count -gt 0) {
        return @($items)
    }

    $scalar = Get-VgoMarkdownSectionScalar -Sections $Sections -Heading $Heading
    if (-not [string]::IsNullOrWhiteSpace($scalar)) {
        return @($scalar)
    }

    return @()
}

function New-VgoAntiProxyGoalDriftDraft {
    param([AllowNull()] [string]$PrimaryObjective = '')

    $objective = if ([string]::IsNullOrWhiteSpace($PrimaryObjective)) {
        '_author_to_declare_'
    } else {
        $PrimaryObjective.Trim()
    }

    return [pscustomobject]@{
        primary_objective = $objective
        non_objective_proxy_signals = @(
            'single sample pass only',
            'current test green only',
            'demo success only'
        )
        validation_material_role = 'validation_only'
        anti_proxy_goal_drift_tier = 'Tier C'
        intended_scope = 'scenario_specific'
        abstraction_layer_target = '_author_to_declare_'
        completion_state = 'partial'
        generalization_evidence_bundle = @(
            'cases: []',
            'note: add independent evidence before generalized completion claims'
        )
    }
}

function Get-VgoAntiProxyGoalDriftPacketFromRequirementDoc {
    param([Parameter(Mandatory)] [string]$RequirementDocPath)

    if (-not (Test-Path -LiteralPath $RequirementDocPath)) {
        throw "Requirement doc not found: $RequirementDocPath"
    }

    $lines = Get-Content -LiteralPath $RequirementDocPath -Encoding UTF8
    $sections = Get-VgoMarkdownSectionMap -Lines $lines
    $goal = Get-VgoMarkdownSectionScalar -Sections $sections -Heading 'Goal'
    $draft = New-VgoAntiProxyGoalDriftDraft -PrimaryObjective $goal

    $primaryObjective = Get-VgoMarkdownSectionScalar -Sections $sections -Heading 'Primary Objective'
    if (-not [string]::IsNullOrWhiteSpace($primaryObjective)) {
        $draft.primary_objective = $primaryObjective
    }

    $signals = @(Get-VgoMarkdownSectionList -Sections $sections -Heading 'Non-Objective Proxy Signals')
    if ($signals.Count -gt 0) {
        $draft.non_objective_proxy_signals = $signals
    }

    foreach ($pair in @(
            @{ heading = 'Validation Material Role'; property = 'validation_material_role' },
            @{ heading = 'Anti-Proxy-Goal-Drift Tier'; property = 'anti_proxy_goal_drift_tier' },
            @{ heading = 'Intended Scope'; property = 'intended_scope' },
            @{ heading = 'Abstraction Layer Target'; property = 'abstraction_layer_target' },
            @{ heading = 'Completion State'; property = 'completion_state' }
        )) {
        $value = Get-VgoMarkdownSectionScalar -Sections $sections -Heading $pair.heading
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $draft.($pair.property) = $value
        }
    }

    $bundle = @(Get-VgoMarkdownSectionList -Sections $sections -Heading 'Generalization Evidence Bundle')
    if ($bundle.Count -gt 0) {
        $draft.generalization_evidence_bundle = $bundle
    }

    return $draft
}

function Get-VgoAntiProxyGoalDriftRequirementLines {
    param([Parameter(Mandatory)] [psobject]$Packet)

    $lines = @(
        '## Primary Objective',
        $Packet.primary_objective,
        '',
        '## Non-Objective Proxy Signals'
    )
    $lines += @($Packet.non_objective_proxy_signals | ForEach-Object { "- $_" })
    $lines += @(
        '',
        '## Validation Material Role',
        $Packet.validation_material_role,
        '',
        '## Anti-Proxy-Goal-Drift Tier',
        $Packet.anti_proxy_goal_drift_tier,
        '',
        '## Intended Scope',
        $Packet.intended_scope,
        '',
        '## Abstraction Layer Target',
        $Packet.abstraction_layer_target,
        '',
        '## Completion State',
        $Packet.completion_state,
        '',
        '## Generalization Evidence Bundle'
    )
    $lines += @($Packet.generalization_evidence_bundle | ForEach-Object { "- $_" })
    return $lines
}

function Get-VgoAntiProxyGoalDriftPlanLines {
    param([Parameter(Mandatory)] [psobject]$Packet)

    $lines = @(
        '## Anti-Proxy-Goal-Drift Controls',
        'Prefill from the frozen requirement doc where available. Only diverge with explicit justification.',
        '',
        '### Primary Objective',
        $Packet.primary_objective,
        '',
        '### Non-Objective Proxy Signals'
    )
    $lines += @($Packet.non_objective_proxy_signals | ForEach-Object { "- $_" })
    $lines += @(
        '',
        '### Validation Material Role',
        $Packet.validation_material_role,
        '',
        '### Declared Tier',
        $Packet.anti_proxy_goal_drift_tier,
        '',
        '### Intended Scope',
        $Packet.intended_scope,
        '',
        '### Abstraction Layer Target',
        $Packet.abstraction_layer_target,
        '',
        '### Completion State Target',
        $Packet.completion_state,
        '',
        '### Generalization Evidence Plan',
        '- Reuse the requirement-declared proof boundary as the starting point.'
    )
    $lines += @($Packet.generalization_evidence_bundle | ForEach-Object { "- $_" })
    return $lines
}
