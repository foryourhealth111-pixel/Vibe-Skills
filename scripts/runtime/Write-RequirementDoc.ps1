param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$IntentContractPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$MemoryContextPath = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
    [AllowEmptyString()] [string]$DelegationEnvelopePath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeSkillRouting.Common.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

function Add-VibeMarkdownSection {
    param(
        [Parameter(Mandatory)] [ref]$Lines,
        [Parameter(Mandatory)] [string]$Heading,
        [AllowEmptyCollection()] [string[]]$BodyLines = @()
    )

    $filteredBodyLines = @($BodyLines | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if (@($filteredBodyLines).Count -eq 0) {
        return
    }

    $Lines.Value += @('', ('## {0}' -f $Heading))
    $Lines.Value += @($filteredBodyLines)
}

function New-VibeBulletLines {
    param([AllowEmptyCollection()] [string[]]$Items = @())

    return @(
        $Items |
            ForEach-Object { [string]$_ } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { '- ' + $_ }
    )
}

function Get-VibeDefaultCodeTaskTddEvidenceRequirements {
    return @(
        'Record failing-first evidence for the changed behavior before implementation or defect correction.',
        'Record the green rerun that proves the targeted behavior passed after implementation.',
        'Map the changed behavior to targeted verification evidence; generic suite success alone is insufficient.',
        'If automated failing-first evidence is not appropriate, freeze and honor an explicit code-task TDD exception instead of silently skipping the requirement.'
    )
}

function Get-VibeProductAcceptanceCriteria {
    param(
        [Parameter(Mandatory)] [object]$IntentContract
    )

    $criteria = @()
    foreach ($item in @($IntentContract.acceptance_criteria)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
            $criteria += [string]$item
        }
    }
    $criteria += 'The delivered output must satisfy observable behavior implied by the frozen goal and deliverable, not only internal runtime progress.'
    $criteria += 'Full completion wording is allowed only after downstream delivery truth is passing.'
    return @($criteria | Select-Object -Unique)
}

function Get-VibeCompletionLanguagePolicy {
    return @(
        'Full completion wording is allowed only when governance truth, engineering verification truth, workflow completion truth, and product acceptance truth are all passing.',
        '`completed_with_failures`, degraded execution, or pending manual actions must be reported as non-complete states.',
        'If manual spot checks remain pending, the run must be described as requiring manual review rather than fully ready.'
    )
}

function Get-VibeDeliveryTruthContractLines {
    return @(
        'Governance truth: requirement, plan, execution, and cleanup artifacts remain traceable and authoritative.',
        'Engineering verification truth: targeted verification passes or fails explicitly; silence does not count as success.',
        'Workflow completion truth: planned units, delegated lanes, and specialist outputs reconcile back into the governed plan.',
        'Product acceptance truth: observable deliverable behavior satisfies frozen acceptance criteria before full completion language is allowed.'
    )
}

function Get-VibeOptionalFrozenItems {
    param(
        [Parameter(Mandatory)] [object]$IntentContract,
        [Parameter(Mandatory)] [string[]]$PropertyNames
    )

    $items = @()
    foreach ($propertyName in @($PropertyNames)) {
        if ($null -ne $IntentContract -and $IntentContract.PSObject.Properties.Name -contains $propertyName) {
            foreach ($item in @($IntentContract.$propertyName)) {
                if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
                    $items += [string]$item
                }
            }
        }
    }

    return @($items | Select-Object -Unique)
}

function Get-VibeSelectedCapsuleList {
    param(
        [AllowNull()] [object]$ContextPack = $null
    )

    if (
        $null -eq $ContextPack -or
        -not ($ContextPack.PSObject.Properties.Name -contains 'selected_capsules') -or
        $null -eq $ContextPack.selected_capsules
    ) {
        return @()
    }

    return @($ContextPack.selected_capsules | Where-Object { $null -ne $_ })
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $ArtifactRoot
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $GovernanceScope `
    -RunId $RunId `
    -RootRunId $RootRunId `
    -ParentRunId $ParentRunId `
    -ParentUnitId $ParentUnitId `
    -InheritedRequirementDocPath $InheritedRequirementDocPath `
    -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
    -DelegationEnvelopePath $DelegationEnvelopePath `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
$hasFrozenIntentContract = -not [string]::IsNullOrWhiteSpace($IntentContractPath) -and (Test-Path -LiteralPath $IntentContractPath)
if ($hasFrozenIntentContract) {
    $intentContract = Get-Content -LiteralPath $IntentContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $intentContract = New-VibeIntentContractObject -Task $Task -Mode $Mode
}

$isChildScope = ([string]$hierarchyState.governance_scope -eq 'child')
$docPath = if ($isChildScope) {
    if ([string]::IsNullOrWhiteSpace([string]$hierarchyState.inherited_requirement_doc_path)) {
        throw 'Child-governed requirement stage requires InheritedRequirementDocPath.'
    }
    [string]$hierarchyState.inherited_requirement_doc_path
} else {
    Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot
}
$antiDriftDraft = New-VgoAntiProxyGoalDriftDraft -PrimaryObjective $intentContract.goal
$productAcceptanceCriteria = Get-VibeProductAcceptanceCriteria -IntentContract $intentContract
$completionLanguagePolicy = Get-VibeCompletionLanguagePolicy
$deliveryTruthContract = Get-VibeDeliveryTruthContractLines
$artifactReviewRequirements = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('artifact_review_requirements', 'artifactReviewRequirements')
$codeTaskTddEvidenceRequirements = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('code_task_tdd_evidence_requirements', 'codeTaskTddEvidenceRequirements')
$codeTaskTddExceptions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('code_task_tdd_exceptions', 'codeTaskTddExceptions')
$taskSpecificAcceptanceExtensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('task_specific_acceptance_extensions', 'taskSpecificAcceptanceExtensions')
$researchAugmentationSources = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('research_augmentation_sources', 'researchAugmentationSources')
$baselineDocumentQualityDimensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('baseline_document_quality_dimensions', 'baselineDocumentQualityDimensions')
$baselineUiQualityDimensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('baseline_ui_quality_dimensions', 'baselineUiQualityDimensions')
$manualSpotChecks = if (@($baselineUiQualityDimensions).Count -gt 0) {
    @(
        'Open the primary user-facing flow and confirm the main path works from entry to completion.',
        'Exercise one meaningful unhappy-path or validation-path interaction and record whether behavior matches the frozen requirement.'
    )
} else {
    @('None required beyond automated verification for this task unless the execution scope expands to a user-visible or interactive flow.')
}
$runtimeInputPath = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath)) {
    $RuntimeInputPacketPath
} else {
    Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
}
$runtimeInputPacket = if (-not [string]::IsNullOrWhiteSpace($runtimeInputPath) -and (Test-Path -LiteralPath $runtimeInputPath)) {
    Get-Content -LiteralPath $runtimeInputPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$codeTaskTddDecision = if (
    $hasFrozenIntentContract -and
    $intentContract.PSObject.Properties.Name -contains 'code_task_tdd_decision' -and
    $null -ne $intentContract.code_task_tdd_decision
) {
    $intentContract.code_task_tdd_decision
} elseif (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'code_task_tdd_decision' -and
    $null -ne $runtimeInputPacket.code_task_tdd_decision
) {
    $runtimeInputPacket.code_task_tdd_decision
} else {
    $null
}
$hostExplicitTddNotApplicable = (
    $codeTaskTddDecision -and
    [string]$codeTaskTddDecision.source -eq 'host_decision' -and
    [string]$codeTaskTddDecision.mode -eq 'not_applicable'
)
if ($codeTaskTddDecision -and @($codeTaskTddEvidenceRequirements).Count -gt 0 -and -not $hostExplicitTddNotApplicable) {
    $codeTaskTddDecision.mode = 'required'
    $codeTaskTddDecision.source = 'intent_contract'
    $codeTaskTddDecision.reason = 'Explicit code-task TDD evidence requirements were supplied by the intent contract.'
} elseif ($codeTaskTddDecision -and @($codeTaskTddExceptions).Count -gt 0 -and -not $hostExplicitTddNotApplicable) {
    $codeTaskTddDecision.mode = 'exception_approved'
    $codeTaskTddDecision.source = 'intent_contract'
    $codeTaskTddDecision.reason = 'Explicit code-task TDD exception requirements were supplied by the intent contract.'
}
if ($codeTaskTddDecision -and [string]$codeTaskTddDecision.mode -eq 'required' -and @($codeTaskTddEvidenceRequirements).Count -eq 0) {
    $codeTaskTddEvidenceRequirements = Get-VibeDefaultCodeTaskTddEvidenceRequirements
} elseif ($codeTaskTddDecision -and [string]$codeTaskTddDecision.mode -eq 'exception_approved') {
    $codeTaskTddEvidenceRequirements = @()
    if (@($codeTaskTddExceptions).Count -eq 0) {
        $exceptionReason = if ($codeTaskTddDecision -and -not [string]::IsNullOrWhiteSpace([string]$codeTaskTddDecision.exception)) {
            [string]$codeTaskTddDecision.exception
        } else {
            'Host approved a bounded code-task TDD exception; execution must record fallback verification evidence instead of strict red/green sequencing.'
        }
        $codeTaskTddExceptions = @($exceptionReason)
    }
} elseif ($codeTaskTddDecision -and [string]$codeTaskTddDecision.mode -eq 'not_applicable') {
    $codeTaskTddEvidenceRequirements = @()
    if ($hostExplicitTddNotApplicable) {
        $codeTaskTddExceptions = @()
    }
}
$memoryContextPack = if (-not [string]::IsNullOrWhiteSpace($MemoryContextPath) -and (Test-Path -LiteralPath $MemoryContextPath)) {
    Get-Content -LiteralPath $MemoryContextPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$lines = @("# $($intentContract.title)")
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Goal' -BodyLines @([string]$intentContract.goal)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Deliverable' -BodyLines @([string]$intentContract.deliverable)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Constraints' -BodyLines (New-VibeBulletLines -Items @($intentContract.constraints))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Acceptance Criteria' -BodyLines (New-VibeBulletLines -Items @($intentContract.acceptance_criteria))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Product Acceptance Criteria' -BodyLines (New-VibeBulletLines -Items @($productAcceptanceCriteria))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Manual Spot Checks' -BodyLines (New-VibeBulletLines -Items @($manualSpotChecks))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Completion Language Policy' -BodyLines (New-VibeBulletLines -Items @($completionLanguagePolicy))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Delivery Truth Contract' -BodyLines (New-VibeBulletLines -Items @($deliveryTruthContract))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Artifact Review Requirements' -BodyLines (New-VibeBulletLines -Items @($artifactReviewRequirements))

if ($codeTaskTddDecision -and [string]$codeTaskTddDecision.mode -ne 'not_applicable') {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Code Task TDD Mode' -BodyLines @(
        ('TDD mode: {0}' -f [string]$codeTaskTddDecision.mode),
        ('Decision source: {0}' -f [string]$codeTaskTddDecision.source),
        ('Reason: {0}' -f [string]$codeTaskTddDecision.reason)
    )
}

Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Code Task TDD Evidence Requirements' -BodyLines (New-VibeBulletLines -Items @($codeTaskTddEvidenceRequirements))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Code Task TDD Exceptions' -BodyLines (New-VibeBulletLines -Items @($codeTaskTddExceptions))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Baseline Document Quality Dimensions' -BodyLines (New-VibeBulletLines -Items @($baselineDocumentQualityDimensions))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Baseline UI Quality Dimensions' -BodyLines (New-VibeBulletLines -Items @($baselineUiQualityDimensions))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Task-Specific Acceptance Extensions' -BodyLines (New-VibeBulletLines -Items @($taskSpecificAcceptanceExtensions))
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Research Augmentation Sources' -BodyLines (New-VibeBulletLines -Items @($researchAugmentationSources))
$nonGoalLines = @(New-VibeBulletLines -Items @($intentContract.non_goals))
if (@($nonGoalLines).Count -gt 0) {
    $lines += @('', 'Non-goals:')
    $lines += @($nonGoalLines)
}
$workflowLevelConfirmation = if (
    $intentContract.PSObject.Properties.Name -contains 'workflow_level_confirmation' -and
    $null -ne $intentContract.workflow_level_confirmation
) {
    $intentContract.workflow_level_confirmation
} else {
    $null
}
if ($workflowLevelConfirmation) {
    $skillSearchGuide = if (
        $runtimeInputPacket -and
        $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_search_guide' -and
        $null -ne $runtimeInputPacket.skill_search_guide
    ) {
        $runtimeInputPacket.skill_search_guide
    } else {
        New-VibeSkillSearchGuideProjection -RepoRoot $runtime.repo_root
    }
    $skillSearchGuideLines = @()
    $workflowLevelLines = @()
    $skillSearchGuideLines += @(Get-VibeSkillSearchGuideLines -SkillSearchGuide $skillSearchGuide)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Skill Search Guide' -BodyLines @($skillSearchGuideLines)
    $workflowLevelLines += @(Get-VibeWorkflowLevelConfirmationLines -WorkflowLevelConfirmation $workflowLevelConfirmation)
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Workflow Level Confirmation' -BodyLines @($workflowLevelLines)
} else {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Workflow Level Confirmation' -BodyLines @('No workflow level confirmation was recorded in the intent contract.')
}
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Assumptions' -BodyLines (New-VibeBulletLines -Items @($intentContract.assumptions))

if ($runtimeInputPacket) {
    $entryIntentId = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'entry_intent_id' -and
        -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.entry_intent_id)
    ) {
        [string]$runtimeInputPacket.entry_intent_id
    } else {
        'vibe'
    }
    $requestedStageStop = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'requested_stage_stop' -and
        -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.requested_stage_stop)
    ) {
        [string]$runtimeInputPacket.requested_stage_stop
    } else {
        'phase_cleanup'
    }
    $requestedGradeFloor = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'requested_grade_floor' -and
        -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.requested_grade_floor)
    ) {
        [string]$runtimeInputPacket.requested_grade_floor
    } else {
        'none'
    }

    $hostReentryAction = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'continuation_context' -and
        $null -ne $runtimeInputPacket.continuation_context -and
        $runtimeInputPacket.continuation_context.PSObject.Properties.Name -contains 'reentry_action'
    ) {
        [string]$runtimeInputPacket.continuation_context.reentry_action
    } elseif (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'host_reentry_action' -and
        -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.host_reentry_action)
    ) {
        [string]$runtimeInputPacket.host_reentry_action
    } else {
        ''
    }
    $hostRevisionTargetStage = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'continuation_context' -and
        $null -ne $runtimeInputPacket.continuation_context -and
        $runtimeInputPacket.continuation_context.PSObject.Properties.Name -contains 'revision_target_stage'
    ) {
        [string]$runtimeInputPacket.continuation_context.revision_target_stage
    } elseif (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'host_revision_target_stage' -and
        -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.host_revision_target_stage)
    ) {
        [string]$runtimeInputPacket.host_revision_target_stage
    } else {
        ''
    }
    $hostRevisionDelta = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'continuation_context' -and
        $null -ne $runtimeInputPacket.continuation_context -and
        $runtimeInputPacket.continuation_context.PSObject.Properties.Name -contains 'revision_delta'
    ) {
        @(Get-VibeNormalizedStringList -Values $runtimeInputPacket.continuation_context.revision_delta)
    } elseif (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'host_revision_delta' -and
        $null -ne $runtimeInputPacket.host_revision_delta
    ) {
        @(Get-VibeNormalizedStringList -Values $runtimeInputPacket.host_revision_delta)
    } else {
        @()
    }
    if ([string]$hostReentryAction -eq 'revise' -and @($hostRevisionDelta).Count -gt 0) {
        Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Host Revision Delta' -BodyLines @(
            ('- Re-entry action: {0}' -f [string]$hostReentryAction),
            ('- Revision target stage: {0}' -f $(if ([string]::IsNullOrWhiteSpace($hostRevisionTargetStage)) { 'requirement_doc' } else { [string]$hostRevisionTargetStage })),
            @(New-VibeBulletLines -Items @($hostRevisionDelta))
        )
    }

}

$selectedMemoryCapsules = @(Get-VibeSelectedCapsuleList -ContextPack $memoryContextPack)

$childHandoffPath = $null
if ($isChildScope) {
    if (-not (Test-Path -LiteralPath $docPath)) {
        throw ("Child-governed requirement stage cannot inherit missing canonical requirement doc: {0}" -f $docPath)
    }

    $childHandoffPath = Join-Path $sessionRoot 'child-requirement-handoff.md'
    $handoffLines = @(
        "# Child Requirement Handoff",
        '',
        '- governance_scope: child',
        ('- inherited_requirement_doc: {0}' -f $docPath),
        ('- root_run_id: {0}' -f [string]$hierarchyState.root_run_id),
        ('- parent_run_id: {0}' -f [string]$hierarchyState.parent_run_id),
        ('- parent_unit_id: {0}' -f [string]$hierarchyState.parent_unit_id),
        '- canonical_write_allowed: false',
        '',
        'Child-governed lanes inherit the frozen root requirement and may not create a second canonical requirement surface.'
    )
    Write-VibeMarkdownArtifact -Path $childHandoffPath -Lines $handoffLines
} else {
    Write-VibeMarkdownArtifact -Path $docPath -Lines $lines
}

$receipt = [pscustomobject]@{
    stage = 'requirement_doc'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    requirement_doc_path = $docPath
    child_requirement_handoff_path = $childHandoffPath
    canonical_write_allowed = -not $isChildScope
    inherited_requirement_doc_path = if ($isChildScope) { $docPath } else { $null }
    runtime_input_packet_path = $runtimeInputPath
    code_task_tdd_decision = $codeTaskTddDecision
    memory_context_path = if ($memoryContextPack) { $MemoryContextPath } else { $null }
    memory_context_item_count = if ($memoryContextPack) { @($memoryContextPack.items).Count } else { 0 }
    memory_context_estimated_tokens = if ($memoryContextPack) { [int]$memoryContextPack.estimated_tokens } else { 0 }
    memory_disclosure_level = if ($memoryContextPack -and $memoryContextPack.PSObject.Properties.Name -contains 'disclosure_level') { [string]$memoryContextPack.disclosure_level } else { $null }
    memory_capsule_count = @($selectedMemoryCapsules).Count
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'requirement-doc-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    requirement_doc_path = $docPath
    receipt_path = $receiptPath
    receipt = $receipt
}
