Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-VibeMemoryArtifactsRoot {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $path = Join-Path $SessionRoot 'memory-activation'
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

function Get-VibeMemoryBudgetSpec {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage
    )

    $defaults = $Runtime.memory_retrieval_budget_policy.defaults
    $topK = [int]$defaults.top_k
    $maxTokens = [int]$defaults.max_tokens
    $maxCharsPerItem = [int]$defaults.max_chars_per_item

    if ($Runtime.memory_retrieval_budget_policy.stages.PSObject.Properties.Name -contains $Stage) {
        $stageBudget = $Runtime.memory_retrieval_budget_policy.stages.$Stage
        if ($null -ne $stageBudget.top_k) {
            $topK = [int]$stageBudget.top_k
        }
        if ($null -ne $stageBudget.max_tokens) {
            $maxTokens = [int]$stageBudget.max_tokens
        }
        if ($null -ne $stageBudget.max_chars_per_item) {
            $maxCharsPerItem = [int]$stageBudget.max_chars_per_item
        }
    }

    return [pscustomobject]@{
        top_k = $topK
        max_tokens = $maxTokens
        max_chars_per_item = $maxCharsPerItem
    }
}

function Get-VibeMemoryCanonicalOwners {
    param(
        [Parameter(Mandatory)] [object]$Runtime
    )

    $owners = $Runtime.memory_runtime_v3_policy.canonical_owners
    return [ordered]@{
        session = [string]$owners.session
        project_decision = switch ([string]$owners.project_decision) {
            'serena' { 'Serena' }
            default { [string]$owners.project_decision }
        }
        short_term_semantic = [string]$owners.short_term_semantic
        long_term_graph = switch ([string]$owners.long_term_graph) {
            'cognee' { 'Cognee' }
            default { [string]$owners.long_term_graph }
        }
    }
}

function Get-VibeMemoryDisclosureStagePolicy {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage
    )

    $defaults = $Runtime.memory_disclosure_policy.defaults
    $stagePolicy = $null
    if ($Runtime.memory_disclosure_policy.stages.PSObject.Properties.Name -contains $Stage) {
        $stagePolicy = $Runtime.memory_disclosure_policy.stages.$Stage
    }

    $level = if ($null -ne $stagePolicy -and $stagePolicy.PSObject.Properties.Name -contains 'level' -and -not [string]::IsNullOrWhiteSpace([string]$stagePolicy.level)) {
        [string]$stagePolicy.level
    } else {
        'L1_capsule_titles'
    }
    $maxCapsules = if ($null -ne $stagePolicy -and $stagePolicy.PSObject.Properties.Name -contains 'max_capsules' -and $null -ne $stagePolicy.max_capsules) {
        [int]$stagePolicy.max_capsules
    } elseif ($defaults.PSObject.Properties.Name -contains 'max_capsules' -and $null -ne $defaults.max_capsules) {
        [int]$defaults.max_capsules
    } else {
        4
    }
    $maxCharsPerCapsule = if ($null -ne $stagePolicy -and $stagePolicy.PSObject.Properties.Name -contains 'max_chars_per_capsule' -and $null -ne $stagePolicy.max_chars_per_capsule) {
        [int]$stagePolicy.max_chars_per_capsule
    } elseif ($defaults.PSObject.Properties.Name -contains 'max_chars_per_capsule' -and $null -ne $defaults.max_chars_per_capsule) {
        [int]$defaults.max_chars_per_capsule
    } else {
        360
    }

    return [pscustomobject]@{
        level = $level
        max_capsules = $maxCapsules
        max_chars_per_capsule = $maxCharsPerCapsule
    }
}

function Get-VibeMemoryStagePolicy {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage
    )

    foreach ($stagePolicy in @($Runtime.memory_stage_activation_policy.stages)) {
        if ([string]$stagePolicy.stage -eq $Stage) {
            return $stagePolicy
        }
    }

    throw "Missing memory stage policy for stage: $Stage"
}

function Get-VibeBoundedMemoryItems {
    param(
        [AllowEmptyCollection()] [string[]]$Items = @(),
        [Parameter(Mandatory)] [object]$Budget
    )

    $bounded = [System.Collections.Generic.List[string]]::new()
    $totalChars = 0
    $maxCharsTotal = [int]$Budget.max_tokens * 4
    foreach ($item in @($Items)) {
        if ([string]::IsNullOrWhiteSpace($item)) {
            continue
        }
        if ($bounded.Count -ge [int]$Budget.top_k) {
            break
        }

        $text = [string]$item
        if ($text.Length -gt [int]$Budget.max_chars_per_item) {
            $text = $text.Substring(0, [int]$Budget.max_chars_per_item).TrimEnd() + '...'
        }
        $remainingChars = $maxCharsTotal - $totalChars
        if ($remainingChars -le 0) {
            break
        }
        if ($text.Length -gt $remainingChars) {
            if ($remainingChars -le 3) {
                $text = $text.Substring(0, $remainingChars)
            } else {
                $text = $text.Substring(0, $remainingChars - 3).TrimEnd() + '...'
            }
        }
        if ([string]::IsNullOrWhiteSpace($text)) {
            break
        }
        $bounded.Add($text) | Out-Null
        $totalChars += $text.Length
    }
    return @($bounded)
}

function Get-VibeEstimatedTokenCount {
    param(
        [AllowEmptyCollection()] [string[]]$Items = @()
    )

    $charCount = 0
    foreach ($item in @($Items)) {
        $charCount += ([string]$item).Length
    }

    if ($charCount -le 0) {
        return 0
    }

    return [int][Math]::Ceiling($charCount / 4.0)
}

function Get-VibeMemoryReadActionObject {
    param(
        [Parameter(Mandatory)] [string]$Owner,
        [Parameter(Mandatory)] [object]$BackendResult
    )

    return [pscustomobject]@{
        owner = $Owner
        status = [string]$BackendResult.status
        item_count = [int]$BackendResult.item_count
        items = @($BackendResult.items)
        capsule_count = if ($BackendResult.PSObject.Properties.Name -contains 'capsule_count') { [int]$BackendResult.capsule_count } else { 0 }
        capsules = if ($BackendResult.PSObject.Properties.Name -contains 'capsules') { @($BackendResult.capsules) } else { @() }
        artifact_path = if ($BackendResult.artifact_path) { [string]$BackendResult.artifact_path } else { $null }
        project_key = if ($BackendResult.project_key) { [string]$BackendResult.project_key } else { $null }
        project_key_source = if ($BackendResult.project_key_source) { [string]$BackendResult.project_key_source } else { $null }
    }
}

function Get-VibeMemoryWriteActionObject {
    param(
        [Parameter(Mandatory)] [string]$Owner,
        [Parameter(Mandatory)] [object]$BackendResult
    )

    return [pscustomobject]@{
        owner = $Owner
        status = [string]$BackendResult.status
        item_count = [int]$BackendResult.item_count
        items = @($BackendResult.items)
        artifact_path = if ($BackendResult.artifact_path) { [string]$BackendResult.artifact_path } else { $null }
        project_key = if ($BackendResult.project_key) { [string]$BackendResult.project_key } else { $null }
        project_key_source = if ($BackendResult.project_key_source) { [string]$BackendResult.project_key_source } else { $null }
        store_path = if ($BackendResult.store_path) { [string]$BackendResult.store_path } else { $null }
    }
}

function Get-VibeLaneSearchPayload {
    param(
        [Parameter(Mandatory)] [string]$LaneId,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [object]$Budget
    )

    return [pscustomobject]@{
        lane = $LaneId
        stage = $Stage
        task = $Task
        top_k = [int]$Budget.top_k
        max_chars_per_item = [int]$Budget.max_chars_per_item
        keywords = @()
        project_key_source = $null
    }
}

function Get-VibeSearchKeywords {
    param(
        [AllowEmptyString()] [string]$Task = '',
        [AllowEmptyCollection()] [string[]]$ExtraTokens = @()
    )

    $tokens = [System.Collections.Generic.List[string]]::new()
    foreach ($match in [regex]::Matches($Task.ToLowerInvariant(), '[a-z0-9_/-]{3,}')) {
        $value = [string]$match.Value
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $tokens.Add($value) | Out-Null
        }
    }
    foreach ($token in @($ExtraTokens)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$token)) {
            $tokens.Add([string]$token) | Out-Null
        }
    }
    return @($tokens | Select-Object -Unique | Select-Object -First 12)
}

function Get-VibeCogneeReadAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage $Stage
    $payload = Get-VibeLaneSearchPayload -LaneId 'cognee' -Stage $Stage -Task $Task -Budget $budget
    $payload.keywords = @(Get-VibeSearchKeywords -Task $Task)
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'cognee' -Action 'read' -Payload $payload -SessionRoot $SessionRoot
    return Get-VibeMemoryReadActionObject -Owner 'Cognee' -BackendResult $result
}

function Get-VibeSerenaReadAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage $Stage
    $payload = Get-VibeLaneSearchPayload -LaneId 'serena' -Stage $Stage -Task $Task -Budget $budget
    $payload.keywords = @(Get-VibeSearchKeywords -Task $Task)
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'serena' -Action 'read' -Payload $payload -SessionRoot $SessionRoot
    return Get-VibeMemoryReadActionObject -Owner 'Serena' -BackendResult $result
}

function Get-VibeRufloReadAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$Grade
    )

    if ($Grade -ne 'XL') {
        return [pscustomobject]@{
            owner = 'ruflo'
            status = 'out_of_scope_serial_lane'
            item_count = 0
            items = @()
            artifact_path = $null
        }
    }

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage 'plan_execute'
    $payload = Get-VibeLaneSearchPayload -LaneId 'ruflo' -Stage 'plan_execute' -Task $Task -Budget $budget
    $payload.keywords = @(Get-VibeSearchKeywords -Task $Task -ExtraTokens @('handoff', 'milestone', 'xl'))
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'ruflo' -Action 'read' -Payload $payload -SessionRoot $SessionRoot
    return Get-VibeMemoryReadActionObject -Owner 'ruflo' -BackendResult $result
}

function Get-VibeMemoryDisclosureLevel {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Stage
    )

    return [string](Get-VibeMemoryDisclosureStagePolicy -Runtime $Runtime -Stage $Stage).level
}

function Get-VibeStableShortHash {
    param(
        [Parameter(Mandatory)] [string]$Text
    )

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha256.ComputeHash($bytes)
    } finally {
        $sha256.Dispose()
    }

    $hex = [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
    return $hex.Substring(0, 16)
}

function ConvertTo-VibeMemoryTimestampString {
    param(
        [AllowNull()] [object]$Value
    )

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [datetime]) {
        return $Value.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $parsed = [datetime]::MinValue
    if ([datetime]::TryParse($text, [ref]$parsed)) {
        return $parsed.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }

    return $text
}

function Get-VibeActionCapsuleCandidates {
    param(
        [Parameter(Mandatory)] [object]$Action,
        [Parameter(Mandatory)] [string]$Stage
    )

    $artifactPath = if ($Action.PSObject.Properties.Name -contains 'artifact_path' -and -not [string]::IsNullOrWhiteSpace([string]$Action.artifact_path)) {
        [string]$Action.artifact_path
    } else {
        $null
    }
    $actionItems = @($Action.items)
    $backendCapsules = if ($Action.PSObject.Properties.Name -contains 'capsules') { @($Action.capsules) } else { @() }
    $candidates = [System.Collections.Generic.List[object]]::new()

    if (@($backendCapsules).Count -gt 0) {
        for ($index = 0; $index -lt @($backendCapsules).Count; $index++) {
            $backendCapsule = $backendCapsules[$index]
            $summaryLines = [System.Collections.Generic.List[string]]::new()
            $primaryLine = $null
            if ($index -lt $actionItems.Count -and -not [string]::IsNullOrWhiteSpace([string]$actionItems[$index])) {
                $primaryLine = [string]$actionItems[$index]
            } elseif (-not [string]::IsNullOrWhiteSpace([string]$backendCapsule.summary)) {
                $primaryLine = [string]$backendCapsule.summary
            } else {
                $primaryLine = ('{0} memory capsule' -f [string]$Action.owner)
            }
            $summaryLines.Add($primaryLine) | Out-Null

            $backendSummary = [string]$backendCapsule.summary
            if (-not [string]::IsNullOrWhiteSpace($backendSummary) -and $backendSummary -ne $primaryLine -and $summaryLines.Count -lt 3) {
                $summaryLines.Add($backendSummary) | Out-Null
            }

            $title = [string]$primaryLine
            if ($title.Length -gt 140) {
                $title = $title.Substring(0, 140).TrimEnd() + '...'
            }

            $capsuleId = if (-not [string]::IsNullOrWhiteSpace([string]$backendCapsule.capsule_id)) {
                [string]$backendCapsule.capsule_id
            } else {
                Get-VibeStableShortHash -Text ('{0}|{1}|{2}' -f $Stage, [string]$Action.owner, $title)
            }

            $candidates.Add([pscustomobject]@{
                capsule_id = $capsuleId
                owner = if (-not [string]::IsNullOrWhiteSpace([string]$backendCapsule.owner)) { [string]$backendCapsule.owner } else { [string]$Action.owner }
                lane = if (-not [string]::IsNullOrWhiteSpace([string]$backendCapsule.lane)) { [string]$backendCapsule.lane } else { $null }
                kind = if (-not [string]::IsNullOrWhiteSpace([string]$backendCapsule.kind)) { [string]$backendCapsule.kind } else { $null }
                updated_at = ConvertTo-VibeMemoryTimestampString -Value $backendCapsule.updated_at
                title = $title
                why_now = ('Matched {0} memory for {1}.' -f [string]$Action.owner, $Stage)
                expansion_ref = if ($artifactPath) { ('{0}#{1}' -f $artifactPath, $capsuleId) } else { ('inline:{0}' -f $capsuleId) }
                summary_lines = @($summaryLines)
            }) | Out-Null
        }
        return @($candidates)
    }

    $summaryLines = [System.Collections.Generic.List[string]]::new()
    foreach ($item in $actionItems) {
        $text = [string]$item
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }
        if ($summaryLines.Count -ge 3) {
            break
        }
        $summaryLines.Add($text) | Out-Null
    }

    if ($summaryLines.Count -eq 0) {
        return @()
    }

    $title = [string]$summaryLines[0]
    if ($title.Length -gt 140) {
        $title = $title.Substring(0, 140).TrimEnd() + '...'
    }

    $capsuleId = Get-VibeStableShortHash -Text ('{0}|{1}|{2}' -f $Stage, [string]$Action.owner, $title)
    $candidates.Add([pscustomobject]@{
        capsule_id = $capsuleId
        owner = [string]$Action.owner
        lane = $null
        kind = 'fallback_digest'
        updated_at = $null
        title = $title
        why_now = ('Matched {0} memory for {1}.' -f [string]$Action.owner, $Stage)
        expansion_ref = if ($artifactPath) { ('{0}#{1}' -f $artifactPath, $capsuleId) } else { ('inline:{0}' -f $capsuleId) }
        summary_lines = @($summaryLines)
    }) | Out-Null
    return @($candidates)
}

function New-VibeSelectedMemoryCapsules {
    param(
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ReadActions,
        [Parameter(Mandatory)] [object]$Budget
    )

    $capsules = [System.Collections.Generic.List[object]]::new()
    $candidateGroups = @()
    foreach ($action in @($ReadActions)) {
        $group = @(Get-VibeActionCapsuleCandidates -Action $action -Stage $Stage)
        if (@($group).Count -gt 0) {
            $candidateGroups += ,$group
        }
    }

    $round = 0
    while ($capsules.Count -lt [int]$Budget.top_k) {
        $addedInRound = $false
        foreach ($group in @($candidateGroups)) {
            if ($round -lt @($group).Count) {
                $capsules.Add($group[$round]) | Out-Null
                $addedInRound = $true
                if ($capsules.Count -ge [int]$Budget.top_k) {
                    break
                }
            }
        }

        if (-not $addedInRound) {
            break
        }

        $round++
    }

    return @($capsules)
}

function New-VibeProgressiveDisclosureContextPack {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ReadActions,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$Stage,
        [Parameter(Mandatory)] [string]$ArtifactName,
        [AllowEmptyString()] [string]$SourceStage = ''
    )

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage $Stage
    $disclosurePolicy = Get-VibeMemoryDisclosureStagePolicy -Runtime $Runtime -Stage $Stage
    $capsuleBudget = [pscustomobject]@{
        top_k = [int][Math]::Min([int]$budget.top_k, [int]$disclosurePolicy.max_capsules)
        max_tokens = [int]$budget.max_tokens
        max_chars_per_item = [int][Math]::Min([int]$budget.max_chars_per_item, [int]$disclosurePolicy.max_chars_per_capsule)
    }
    $selectedCapsules = @(New-VibeSelectedMemoryCapsules -ReadActions $ReadActions -Budget $capsuleBudget)

    $items = @()
    foreach ($capsule in @($selectedCapsules)) {
        foreach ($line in @($capsule.summary_lines)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$line)) {
                $items += [string]$line
            }
        }
    }

    $boundedItems = Get-VibeBoundedMemoryItems -Items $items -Budget $capsuleBudget
    $estimatedTokens = Get-VibeEstimatedTokenCount -Items @($boundedItems)
    $artifactPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) $ArtifactName
    $artifact = [pscustomobject]@{
        stage = $Stage
        source_stage = if ([string]::IsNullOrWhiteSpace($SourceStage)) { $null } else { $SourceStage }
        owner = 'state_store'
        disclosure_level = [string]$disclosurePolicy.level
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        capsule_count = @($selectedCapsules).Count
        selected_capsules = @($selectedCapsules)
        items = @($boundedItems)
        estimated_tokens = $estimatedTokens
        budget = $capsuleBudget
    }
    Write-VibeJsonArtifact -Path $artifactPath -Value $artifact

    return [pscustomobject]@{
        context_path = $artifactPath
        disclosure_level = [string]$artifact.disclosure_level
        capsule_count = @($selectedCapsules).Count
        selected_capsules = @($selectedCapsules)
        injected_item_count = @($boundedItems).Count
        estimated_tokens = $estimatedTokens
        budget = $capsuleBudget
        items = @($boundedItems)
    }
}

function Get-VibeMemoryActivationFailures {
    param(
        [Parameter(Mandatory)] [object]$MemoryActivationReport
    )

    $fatalStatuses = @(
        'memory_backend_driver_missing',
        'memory_backend_invocation_failed',
        'memory_backend_missing_response',
        'memory_backend_exception',
        'workspace_memory_driver_missing',
        'workspace_memory_invocation_failed',
        'workspace_memory_exception'
    )
    $failures = [System.Collections.Generic.List[object]]::new()
    foreach ($stage in @($MemoryActivationReport.stages)) {
        foreach ($action in @($stage.read_actions) + @($stage.write_actions)) {
            $status = [string]$action.status
            if ($fatalStatuses -contains $status) {
                $failures.Add([pscustomobject]@{
                    stage = [string]$stage.stage
                    owner = if ($action.PSObject.Properties.Name -contains 'owner') { [string]$action.owner } else { $null }
                    status = $status
                }) | Out-Null
            }
        }
    }
    return @($failures)
}

function Assert-VibeMemoryActivationHealthy {
    param(
        [Parameter(Mandatory)] [object]$MemoryActivationReport,
        [AllowEmptyString()] [string]$ReportPath = ''
    )

    $failures = @(Get-VibeMemoryActivationFailures -MemoryActivationReport $MemoryActivationReport)
    if (@($failures).Count -le 0) {
        return
    }

    $formatted = @($failures | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace([string]$_.owner)) {
            ('{0}:{1}' -f [string]$_.stage, [string]$_.status)
        } else {
            ('{0}:{1}:{2}' -f [string]$_.stage, [string]$_.owner, [string]$_.status)
        }
    }) -join ', '
    $reportSuffix = if ([string]::IsNullOrWhiteSpace($ReportPath)) { '' } else { " report=$ReportPath" }
    throw ("workspace memory activation failed hard under governed runtime: {0}{1}" -f $formatted, $reportSuffix)
}

function New-VibePlanMemoryContextPack {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ReadActions,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [string]$Stage = 'xl_plan',
        [string]$ArtifactName = 'plan-context-pack.json'
    )

    return New-VibeProgressiveDisclosureContextPack `
        -Runtime $Runtime `
        -ReadActions $ReadActions `
        -SessionRoot $SessionRoot `
        -Stage $Stage `
        -ArtifactName $ArtifactName
}

function Get-VibeDecisionCandidates {
    param(
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [AllowEmptyString()] [string]$Task = ''
    )

    $texts = @()
    foreach ($path in @($RequirementDocPath, $ExecutionPlanPath)) {
        if (Test-Path -LiteralPath $path) {
            $texts += @(Get-Content -LiteralPath $path -Encoding UTF8)
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($Task)) {
        $texts += $Task
    }

    $candidates = [System.Collections.Generic.List[object]]::new()
    foreach ($line in @($texts)) {
        $trimmed = ([string]$line).Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        if ($trimmed -match '(?i)approved decision|decision record|adr-|## decision') {
            $summary = $trimmed -replace '^[#\-\*\s]+', ''
            $keywords = Get-VibeSearchKeywords -Task $summary
            $candidates.Add([pscustomobject]@{
                summary = $summary
                evidence_paths = @($RequirementDocPath, $ExecutionPlanPath)
                keywords = @($keywords)
            }) | Out-Null
        }
    }
    return @($candidates | Select-Object -Unique -First 3)
}

function Get-VibeCogneeRelationCandidates {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$ExecutionManifestPath
    )

    $taskSlug = ConvertTo-VibeSlug -Text $Task
    $keywords = Get-VibeSearchKeywords -Task $Task -ExtraTokens @($taskSlug)
    return @(
        [pscustomobject]@{
            source = $taskSlug
            relation = 'specified_by'
            target = [System.IO.Path]::GetFileName($RequirementDocPath)
            evidence_paths = @($RequirementDocPath)
            keywords = @($keywords)
        },
        [pscustomobject]@{
            source = $taskSlug
            relation = 'planned_in'
            target = [System.IO.Path]::GetFileName($ExecutionPlanPath)
            evidence_paths = @($ExecutionPlanPath)
            keywords = @($keywords)
        },
        [pscustomobject]@{
            source = $taskSlug
            relation = 'executed_as'
            target = [System.IO.Path]::GetFileName($ExecutionManifestPath)
            evidence_paths = @($ExecutionManifestPath)
            keywords = @($keywords)
        }
    )
}

function Get-VibeRufloCardCandidates {
    param(
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Grade
    )

    if ($Grade -ne 'XL') {
        return @()
    }

    $manifest = Get-Content -LiteralPath $ExecutionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $summary = 'XL handoff for {0}: executed {1} units with {2} failures.' -f $RunId, [int]$manifest.executed_unit_count, [int]$manifest.failed_unit_count
    return @(
        [pscustomobject]@{
            scope = 'xl'
            summary = $summary
            items = @(
                ('execution_status:{0}' -f [string]$manifest.status),
                ('delegation_mode:{0}' -f [string]$manifest.execution_topology.delegation_mode),
                ('specialist_execution_status:{0}' -f [string]$manifest.specialist_accounting.effective_execution_status)
            )
            evidence_paths = @($ExecutionManifestPath)
            keywords = @(Get-VibeSearchKeywords -Task $Task -ExtraTokens @('xl', 'handoff', 'milestone'))
        }
    )
}

function New-VibeSkeletonMemoryDigest {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [object]$Skeleton,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage 'skeleton_check'
    $receipt = $Skeleton.receipt
    $missingPaths = @($receipt.required_paths | Where-Object { -not [bool]$_.exists } | ForEach-Object { [string]$_.path })
    $requirementDocs = @($receipt.existing_requirement_docs | Select-Object -First 5)
    $planDocs = @($receipt.existing_plan_docs | Select-Object -First 5)

    $items = @()
    $items += ('Task focus: {0}' -f $Task)
    $items += ('Git branch: {0}' -f [string]$receipt.git_branch)
    if (@($missingPaths).Count -gt 0) {
        $items += 'Missing runtime prerequisites: ' + (@($missingPaths) -join ', ')
    } else {
        $items += 'All required governed runtime prerequisite paths are present.'
    }
    if (@($requirementDocs).Count -gt 0) {
        $items += 'Existing requirement docs: ' + (@($requirementDocs) -join ', ')
    } else {
        $items += 'Existing requirement docs: none'
    }
    if (@($planDocs).Count -gt 0) {
        $items += 'Existing plan docs: ' + (@($planDocs) -join ', ')
    } else {
        $items += 'Existing plan docs: none'
    }

    $boundedItems = Get-VibeBoundedMemoryItems -Items $items -Budget $budget
    $artifactPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'skeleton-local-digest.json'
    $artifact = [pscustomobject]@{
        stage = 'skeleton_check'
        owner = 'state_store'
        status = 'fallback_local_digest'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        source_receipt_path = [string]$Skeleton.receipt_path
        items = @($boundedItems)
        budget = $budget
    }
    Write-VibeJsonArtifact -Path $artifactPath -Value $artifact

    return [pscustomobject]@{
        owner = 'state_store'
        status = 'fallback_local_digest'
        item_count = @($boundedItems).Count
        items = @($boundedItems)
        artifact_path = $artifactPath
        budget = $budget
    }
}

function Get-VibeDeepInterviewMemoryReadAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $stagePolicy = Get-VibeMemoryStagePolicy -Runtime $Runtime -Stage 'deep_interview'
    $readAction = Get-VibeSerenaReadAction -Runtime $Runtime -Stage 'deep_interview' -Task $Task -SessionRoot $SessionRoot
    if ($readAction.status -eq 'memory_backend_ready') {
        $readAction.status = [string]@($stagePolicy.read_actions)[0].status_if_missing_project_key
    }
    if ($readAction.status -eq 'backend_read_empty' -and -not $readAction.project_key_source) {
        $readAction.status = [string]@($stagePolicy.read_actions)[0].status_if_missing_project_key
    }
    if ($readAction.PSObject.Properties.Name -contains 'project_key_source') {
        $readAction | Add-Member -NotePropertyName project_key_env -NotePropertyValue $readAction.project_key_source -Force
    }
    return $readAction
}

function New-VibeRequirementContextPack {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ReadActions,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return New-VibeProgressiveDisclosureContextPack `
        -Runtime $Runtime `
        -ReadActions $ReadActions `
        -SessionRoot $SessionRoot `
        -Stage 'requirement_doc' `
        -ArtifactName 'requirement-context-pack.json' `
        -SourceStage 'bounded_memory_recall'
}

function New-VibeExecutionMemoryWriteAction {
    param(
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Grade
    )

    $manifest = Get-Content -LiteralPath $ExecutionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $items = @(
        ('Execution status: {0}' -f [string]$manifest.status),
        ('Executed units: {0}; failures: {1}' -f [int]$manifest.executed_unit_count, [int]$manifest.failed_unit_count),
        ('Specialist execution status: {0}' -f [string]$manifest.specialist_accounting.effective_execution_status)
    )
    $artifactPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'execution-handoff-card.json'
    $artifact = [pscustomobject]@{
        stage = 'plan_execute'
        owner = 'state_store'
        status = 'fallback_local_artifact'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        source_execution_manifest = $ExecutionManifestPath
        items = @($items)
    }
    Write-VibeJsonArtifact -Path $artifactPath -Value $artifact

    return [pscustomobject]@{
        owner = 'state_store'
        status = 'fallback_local_artifact'
        item_count = @($items).Count
        items = @($items)
        artifact_path = $artifactPath
    }
}

function New-VibeRufloExecutionWriteAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Grade
    )

    if ($Grade -ne 'XL') {
        return [pscustomobject]@{
            owner = 'ruflo'
            status = 'out_of_scope_serial_lane'
            item_count = 0
            items = @()
            artifact_path = $null
            store_path = $null
        }
    }

    $cards = Get-VibeRufloCardCandidates -ExecutionManifestPath $ExecutionManifestPath -RunId $RunId -Task $Task -Grade $Grade
    $payload = [pscustomobject]@{
        run_id = $RunId
        task = $Task
        cards = @($cards)
    }
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'ruflo' -Action 'write' -Payload $payload -SessionRoot $SessionRoot
    return Get-VibeMemoryWriteActionObject -Owner 'ruflo' -BackendResult $result
}

function Get-VibeCleanupDecisionWriteAction {
    param(
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowEmptyString()] [string]$Task = ''
    )

    $requirementText = if (Test-Path -LiteralPath $RequirementDocPath) {
        Get-Content -LiteralPath $RequirementDocPath -Raw -Encoding UTF8
    } else {
        ''
    }
    $planText = if (Test-Path -LiteralPath $ExecutionPlanPath) {
        Get-Content -LiteralPath $ExecutionPlanPath -Raw -Encoding UTF8
    } else {
        ''
    }
    $decisions = Get-VibeDecisionCandidates -RequirementDocPath $RequirementDocPath -ExecutionPlanPath $ExecutionPlanPath -Task $Task
    if (@($decisions).Count -eq 0) {
        return [pscustomobject]@{
            owner = 'Serena'
            status = 'guarded_no_write'
            item_count = 0
            items = @()
            artifact_path = $null
            reason = 'no explicit approved decision markers detected in frozen requirement/plan surfaces'
        }
    }

    $payload = [pscustomobject]@{
        decisions = @($decisions)
    }
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'serena' -Action 'write' -Payload $payload -SessionRoot $SessionRoot
    $writeAction = Get-VibeMemoryWriteActionObject -Owner 'Serena' -BackendResult $result
    $writeAction | Add-Member -NotePropertyName reason -NotePropertyValue 'explicit decision markers detected' -Force
    return $writeAction
}

function Get-VibeCogneeCleanupWriteAction {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $relations = Get-VibeCogneeRelationCandidates `
        -Task $Task `
        -RequirementDocPath $RequirementDocPath `
        -ExecutionPlanPath $ExecutionPlanPath `
        -ExecutionManifestPath $ExecutionManifestPath
    $payload = [pscustomobject]@{
        task = $Task
        relations = @($relations)
    }
    $result = Invoke-VibeMemoryBackendAction -Runtime $Runtime -LaneId 'cognee' -Action 'write' -Payload $payload -SessionRoot $SessionRoot
    return Get-VibeMemoryWriteActionObject -Owner 'Cognee' -BackendResult $result
}

function New-VibeCleanupMemoryFold {
    param(
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$CleanupReceiptPath,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $manifest = Get-Content -LiteralPath $ExecutionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $fold = [pscustomobject]@{
        stage = 'phase_cleanup'
        fold_kind = 'deepagent_memory_fold_local'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        working_memory = @(
            ('Requirement doc: {0}' -f $RequirementDocPath),
            ('Execution plan: {0}' -f $ExecutionPlanPath),
            ('Runtime status: {0}' -f [string]$manifest.status)
        )
        tool_memory = @(
            ('Execution manifest: {0}' -f $ExecutionManifestPath),
            ('Cleanup receipt: {0}' -f $CleanupReceiptPath)
        )
        evidence_anchors = @(
            $RequirementDocPath,
            $ExecutionPlanPath,
            $ExecutionManifestPath,
            $CleanupReceiptPath
        )
    }
    $artifactPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'phase-cleanup-memory-fold.json'
    Write-VibeJsonArtifact -Path $artifactPath -Value $fold

    return [pscustomobject]@{
        owner = 'state_store'
        status = 'generated_local_fold'
        item_count = @($fold.working_memory).Count + @($fold.tool_memory).Count
        items = @($fold.working_memory + $fold.tool_memory)
        artifact_path = $artifactPath
    }
}

function New-VibeMemoryActivationReport {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$SkeletonReadActions,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$DeepInterviewReadActions,
        [Parameter(Mandatory)] [object]$RequirementContextPack,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$XlPlanReadActions,
        [Parameter(Mandatory)] [object]$PlanContextPack,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$PlanExecuteReadActions,
        [Parameter(Mandatory)] [object]$PlanExecuteContextPack,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$PlanExecuteWriteActions,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$CleanupWriteActions,
        [Parameter(Mandatory)] [object]$CleanupFoldAction
    )

    $stages = @(
        [pscustomobject]@{
            stage = 'skeleton_check'
            read_actions = @($SkeletonReadActions)
            context_injection = $null
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'deep_interview'
            read_actions = @($DeepInterviewReadActions)
            context_injection = $null
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'requirement_doc'
            read_actions = @()
            context_injection = [pscustomobject]@{
                injected_item_count = [int]$RequirementContextPack.injected_item_count
                estimated_tokens = [int]$RequirementContextPack.estimated_tokens
                budget = $RequirementContextPack.budget
                artifact_path = [string]$RequirementContextPack.context_path
                disclosure_level = [string]$RequirementContextPack.disclosure_level
                capsule_count = [int]$RequirementContextPack.capsule_count
                selected_capsules = @($RequirementContextPack.selected_capsules)
            }
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'xl_plan'
            read_actions = @($XlPlanReadActions)
            context_injection = [pscustomobject]@{
                injected_item_count = [int]$PlanContextPack.injected_item_count
                estimated_tokens = [int]$PlanContextPack.estimated_tokens
                budget = $PlanContextPack.budget
                artifact_path = [string]$PlanContextPack.context_path
                disclosure_level = [string]$PlanContextPack.disclosure_level
                capsule_count = [int]$PlanContextPack.capsule_count
                selected_capsules = @($PlanContextPack.selected_capsules)
            }
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'plan_execute'
            read_actions = @($PlanExecuteReadActions)
            context_injection = [pscustomobject]@{
                injected_item_count = [int]$PlanExecuteContextPack.injected_item_count
                estimated_tokens = [int]$PlanExecuteContextPack.estimated_tokens
                budget = $PlanExecuteContextPack.budget
                artifact_path = [string]$PlanExecuteContextPack.context_path
                disclosure_level = [string]$PlanExecuteContextPack.disclosure_level
                capsule_count = [int]$PlanExecuteContextPack.capsule_count
                selected_capsules = @($PlanExecuteContextPack.selected_capsules)
            }
            write_actions = @($PlanExecuteWriteActions)
        },
        [pscustomobject]@{
            stage = 'phase_cleanup'
            read_actions = @()
            context_injection = $null
            write_actions = @(
                if (@($CleanupWriteActions).Count -gt 0) { $CleanupWriteActions[0] }
                $CleanupFoldAction
                if (@($CleanupWriteActions).Count -gt 1) { @($CleanupWriteActions | Select-Object -Skip 1) }
            )
        }
    )

    $artifactPaths = [System.Collections.Generic.List[string]]::new()
    $fallbackEventCount = 0
    $budgetGuardRespected = $true
    foreach ($stage in @($stages)) {
        foreach ($readAction in @($stage.read_actions)) {
            if ($readAction.PSObject.Properties.Name -contains 'artifact_path' -and -not [string]::IsNullOrWhiteSpace([string]$readAction.artifact_path)) {
                $artifactPaths.Add([string]$readAction.artifact_path) | Out-Null
            }
            if ([string]$readAction.status -match 'fallback|deferred|guarded|generated') {
                $fallbackEventCount += 1
            }
            if ($readAction.PSObject.Properties.Name -contains 'budget' -and $readAction.PSObject.Properties.Name -contains 'items') {
                if (@($readAction.items).Count -gt [int]$readAction.budget.top_k) {
                    $budgetGuardRespected = $false
                }
            }
        }

        if ($null -ne $stage.context_injection) {
            if (-not [string]::IsNullOrWhiteSpace([string]$stage.context_injection.artifact_path)) {
                $artifactPaths.Add([string]$stage.context_injection.artifact_path) | Out-Null
            }
            if ([int]$stage.context_injection.estimated_tokens -gt [int]$stage.context_injection.budget.max_tokens) {
                $budgetGuardRespected = $false
            }
        }

        foreach ($writeAction in @($stage.write_actions)) {
            if ($writeAction.PSObject.Properties.Name -contains 'artifact_path' -and -not [string]::IsNullOrWhiteSpace([string]$writeAction.artifact_path)) {
                $artifactPaths.Add([string]$writeAction.artifact_path) | Out-Null
            }
            if ([string]$writeAction.status -match 'fallback|deferred|guarded|generated') {
                $fallbackEventCount += 1
            }
        }
    }

    $owners = Get-VibeMemoryCanonicalOwners -Runtime $Runtime
    $report = [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        policy = [pscustomobject]@{
            mode = [string]$Runtime.memory_runtime_v3_policy.mode
            routing_contract = [string]$Runtime.memory_runtime_v3_policy.routing_contract
            canonical_owners = [pscustomobject]$owners
        }
        stages = @($stages)
        summary = [pscustomobject]@{
            stage_count = @($stages).Count
            fallback_event_count = $fallbackEventCount
            artifact_count = @($artifactPaths | Select-Object -Unique).Count
            budget_guard_respected = [bool]$budgetGuardRespected
        }
    }

    $reportPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'memory-activation-report.json'
    $markdownPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'memory-activation-report.md'
    Write-VibeJsonArtifact -Path $reportPath -Value $report
    Write-VibeMarkdownArtifact -Path $markdownPath -Lines @(
        '# Memory Activation Report',
        '',
        ('- run_id: `{0}`' -f $RunId),
        ('- mode: `{0}`' -f [string]$Runtime.memory_runtime_v3_policy.mode),
        ('- routing_contract: `{0}`' -f [string]$Runtime.memory_runtime_v3_policy.routing_contract),
        ('- fallback_event_count: `{0}`' -f [int]$report.summary.fallback_event_count),
        ('- artifact_count: `{0}`' -f [int]$report.summary.artifact_count),
        ('- budget_guard_respected: `{0}`' -f [bool]$report.summary.budget_guard_respected),
        ''
    )

    return [pscustomobject]@{
        report = $report
        report_path = $reportPath
        markdown_path = $markdownPath
    }
}
