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
        $bounded.Add($text) | Out-Null
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
        [Parameter(Mandatory)] [object]$Runtime
    )

    $stagePolicy = Get-VibeMemoryStagePolicy -Runtime $Runtime -Stage 'deep_interview'
    $readPolicy = @($stagePolicy.read_actions)[0]
    $projectKeyEnv = @($readPolicy.project_key_env)
    $projectKeyName = $null
    foreach ($envName in $projectKeyEnv) {
        $value = [Environment]::GetEnvironmentVariable([string]$envName)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $projectKeyName = [string]$envName
            break
        }
    }

    return [pscustomobject]@{
        owner = 'Serena'
        status = if ($null -eq $projectKeyName) { [string]$readPolicy.status_if_missing_project_key } else { 'backend_key_available' }
        item_count = 0
        items = @()
        project_key_env = if ($null -eq $projectKeyName) { $null } else { $projectKeyName }
    }
}

function New-VibeRequirementContextPack {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [object]$SkeletonDigestAction,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $budget = Get-VibeMemoryBudgetSpec -Runtime $Runtime -Stage 'requirement_doc'
    $boundedItems = Get-VibeBoundedMemoryItems -Items @($SkeletonDigestAction.items) -Budget $budget
    $estimatedTokens = Get-VibeEstimatedTokenCount -Items @($boundedItems)
    $artifactPath = Join-Path (Get-VibeMemoryArtifactsRoot -SessionRoot $SessionRoot) 'requirement-context-pack.json'
    $artifact = [pscustomobject]@{
        stage = 'requirement_doc'
        source_stage = 'skeleton_check'
        owner = 'state_store'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        items = @($boundedItems)
        estimated_tokens = $estimatedTokens
        budget = $budget
    }
    Write-VibeJsonArtifact -Path $artifactPath -Value $artifact

    return [pscustomobject]@{
        context_path = $artifactPath
        injected_item_count = @($boundedItems).Count
        estimated_tokens = $estimatedTokens
        budget = $budget
        items = @($boundedItems)
    }
}

function New-VibeExecutionMemoryWriteAction {
    param(
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$SessionRoot
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

function Get-VibeCleanupDecisionWriteAction {
    param(
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath
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
    $combined = "$requirementText`n$planText"
    $hasExplicitDecision = $combined -match 'approved decision|decision record|adr-|## decision'

    return [pscustomobject]@{
        owner = 'Serena'
        status = if ($hasExplicitDecision) { 'backend_write_candidate' } else { 'guarded_no_write' }
        item_count = 0
        items = @()
        artifact_path = $null
        reason = if ($hasExplicitDecision) { 'explicit decision markers detected' } else { 'no explicit approved decision markers detected in frozen requirement/plan surfaces' }
    }
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
        [Parameter(Mandatory)] [object]$SkeletonDigestAction,
        [Parameter(Mandatory)] [object]$DeepInterviewReadAction,
        [Parameter(Mandatory)] [object]$RequirementContextPack,
        [Parameter(Mandatory)] [object]$ExecuteWriteAction,
        [Parameter(Mandatory)] [object]$CleanupDecisionAction,
        [Parameter(Mandatory)] [object]$CleanupFoldAction
    )

    $stages = @(
        [pscustomobject]@{
            stage = 'skeleton_check'
            read_actions = @($SkeletonDigestAction)
            context_injection = $null
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'deep_interview'
            read_actions = @($DeepInterviewReadAction)
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
            }
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'xl_plan'
            read_actions = @()
            context_injection = $null
            write_actions = @()
        },
        [pscustomobject]@{
            stage = 'plan_execute'
            read_actions = @()
            context_injection = $null
            write_actions = @($ExecuteWriteAction)
        },
        [pscustomobject]@{
            stage = 'phase_cleanup'
            read_actions = @()
            context_injection = $null
            write_actions = @($CleanupDecisionAction, $CleanupFoldAction)
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
