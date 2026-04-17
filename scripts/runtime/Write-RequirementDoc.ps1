param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$IntentContractPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$MemoryContextPath = '',
    [string]$DiscussionConsultationPath = '',
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
. (Join-Path $PSScriptRoot 'VibeConsultation.Common.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

function Test-VibeTaskNeedsManualSpotChecks {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$Deliverable = ''
    )

    $text = ('{0} {1}' -f $Task, $Deliverable).ToLowerInvariant()
    return $text -match 'ui|ux|frontend|browser|page|screen|openclaw|cursor|windsurf|codex|用户|界面|交互|可视化|体验'
}

function Test-VibeTaskNeedsDocumentArtifactBaseline {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$Deliverable = ''
    )

    $text = ('{0} {1}' -f $Task, $Deliverable).ToLowerInvariant()
    $docOnlySignals = 'without changing (application )?code|without code changes|document-only'
    $documentArtifactSignals = 'readme|documentation|docx|pdf|pptx|headings|spacing|formatting|markdown|slide|slides|presentation|deck|\bdocument\b|\bdocs\b'
    $codeImplementationSignals = 'failing test|stack trace|debug|bug|fix|refactor|script|function|class|endpoint|api|component|module|backend|frontend|dashboard|page|screen|unit test|integration test|parser|exporter|renderer|pipeline|service|library|cli'

    if ($text -match $docOnlySignals) {
        return $true
    }

    if (-not ($text -match $documentArtifactSignals)) {
        return $false
    }

    return -not ($text -match $codeImplementationSignals)
}

function Test-VibeTaskNeedsCodeTaskTddEvidence {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$Deliverable = ''
    )

    $text = ('{0} {1}' -f $Task, $Deliverable).ToLowerInvariant()

    if ((Test-VibeTaskNeedsDocumentArtifactBaseline -Task $Task -Deliverable $Deliverable) -or ($text -match 'image|logo|illustration|diagram')) {
        return $false
    }

    return $text -match 'failing test|stack trace|debug|bug|fix|refactor|implement|build|feature|code|script|function|class|endpoint|api|component|module|frontend|backend|dashboard|page|screen|unit test|integration test'
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

function Get-VibeManualSpotChecks {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [object]$IntentContract
    )

    if (Test-VibeTaskNeedsManualSpotChecks -Task $Task -Deliverable ([string]$IntentContract.deliverable)) {
        return @(
            'Open the primary user-facing flow and confirm the main path works from entry to completion.',
            'Exercise one meaningful unhappy-path or validation-path interaction and record whether behavior matches the frozen requirement.'
        )
    }

    return @(
        'None required beyond automated verification for this task unless the execution scope expands to a user-visible or interactive flow.'
    )
}

function Get-VibeCompletionLanguagePolicy {
    return @(
        'Full completion wording is allowed only when governance truth, engineering verification truth, workflow completion truth, and product acceptance truth are all passing.',
        '`completed_with_failures`, degraded execution, or pending manual actions must be reported as non-complete states.',
        'If manual spot checks remain pending, the run must be described as requiring manual review rather than fully ready.'
    )
}

function Get-VibeDefaultBaselineUiQualityDimensions {
    return @(
        'Structure Completeness',
        'Interaction Feedback',
        'State Coverage',
        'Design System Consistency',
        'Responsive Stability',
        'Spec Fidelity'
    )
}

function Get-VibeDefaultBaselineDocumentQualityDimensions {
    return @(
        'Structure Integrity',
        'Formatting Consistency',
        'Content Completeness',
        'Link and Reference Integrity',
        'Layout and Asset Stability',
        'Output Fidelity'
    )
}

function Get-VibeDefaultDocumentArtifactReviewRequirements {
    return @(
        'Review the touched document artifact directly against each frozen baseline document quality dimension.',
        'Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.',
        'For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.'
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
if (-not [string]::IsNullOrWhiteSpace($IntentContractPath) -and (Test-Path -LiteralPath $IntentContractPath)) {
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
$manualSpotChecks = Get-VibeManualSpotChecks -Task $Task -IntentContract $intentContract
$completionLanguagePolicy = Get-VibeCompletionLanguagePolicy
$deliveryTruthContract = Get-VibeDeliveryTruthContractLines
$artifactReviewRequirements = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('artifact_review_requirements', 'artifactReviewRequirements')
$codeTaskTddEvidenceRequirements = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('code_task_tdd_evidence_requirements', 'codeTaskTddEvidenceRequirements')
$codeTaskTddExceptions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('code_task_tdd_exceptions', 'codeTaskTddExceptions')
$taskSpecificAcceptanceExtensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('task_specific_acceptance_extensions', 'taskSpecificAcceptanceExtensions')
$researchAugmentationSources = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('research_augmentation_sources', 'researchAugmentationSources')
$baselineDocumentQualityDimensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('baseline_document_quality_dimensions', 'baselineDocumentQualityDimensions')
$baselineUiQualityDimensions = Get-VibeOptionalFrozenItems -IntentContract $intentContract -PropertyNames @('baseline_ui_quality_dimensions', 'baselineUiQualityDimensions')
if (@($codeTaskTddEvidenceRequirements).Count -eq 0 -and (Test-VibeTaskNeedsCodeTaskTddEvidence -Task $Task -Deliverable ([string]$intentContract.deliverable))) {
    $codeTaskTddEvidenceRequirements = Get-VibeDefaultCodeTaskTddEvidenceRequirements
}
if (@($baselineDocumentQualityDimensions).Count -eq 0 -and (Test-VibeTaskNeedsDocumentArtifactBaseline -Task $Task -Deliverable ([string]$intentContract.deliverable))) {
    $baselineDocumentQualityDimensions = Get-VibeDefaultBaselineDocumentQualityDimensions
}
if (@($artifactReviewRequirements).Count -eq 0 -and @($baselineDocumentQualityDimensions).Count -gt 0) {
    $artifactReviewRequirements = Get-VibeDefaultDocumentArtifactReviewRequirements
}
if (@($baselineUiQualityDimensions).Count -eq 0 -and (Test-VibeTaskNeedsManualSpotChecks -Task $Task -Deliverable ([string]$intentContract.deliverable))) {
    $baselineUiQualityDimensions = Get-VibeDefaultBaselineUiQualityDimensions
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
$memoryContextPack = if (-not [string]::IsNullOrWhiteSpace($MemoryContextPath) -and (Test-Path -LiteralPath $MemoryContextPath)) {
    Get-Content -LiteralPath $MemoryContextPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$discussionConsultation = if (-not [string]::IsNullOrWhiteSpace($DiscussionConsultationPath)) {
    if (-not (Test-Path -LiteralPath $DiscussionConsultationPath)) {
        throw ("Discussion consultation receipt not found: {0}" -f $DiscussionConsultationPath)
    }
    Get-Content -LiteralPath $DiscussionConsultationPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
if ($discussionConsultation) {
    $discussionFreezeGate = Assert-VibeSpecialistConsultationFreezeGate `
        -Receipt $discussionConsultation `
        -Policy $runtime.specialist_consultation_policy `
        -FreezeTarget 'requirement_doc'
    if ($discussionConsultation.PSObject.Properties.Name -contains 'freeze_gate') {
        $discussionConsultation.freeze_gate = $discussionFreezeGate
    } else {
        $discussionConsultation | Add-Member -NotePropertyName freeze_gate -NotePropertyValue $discussionFreezeGate
    }
}
$stageLifecycleDisclosure = New-VibeSpecialistLifecycleDisclosureProjection `
    -RuntimeInputPacket $runtimeInputPacket `
    -DiscussionConsultationReceipt $discussionConsultation
$lines = @(
    "# $($intentContract.title)",
    '',
    '## Summary',
    $intentContract.goal,
    '',
    '## Goal',
    $intentContract.goal,
    '',
    '## Deliverable',
    $intentContract.deliverable,
    '',
    '## Constraints'
)
$lines += @($intentContract.constraints | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Acceptance Criteria'
)
$lines += @($intentContract.acceptance_criteria | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Product Acceptance Criteria'
)
$lines += @($productAcceptanceCriteria | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Manual Spot Checks'
)
$lines += @($manualSpotChecks | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Completion Language Policy'
)
$lines += @($completionLanguagePolicy | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Delivery Truth Contract'
)
$lines += @($deliveryTruthContract | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Artifact Review Requirements'
)
if (@($artifactReviewRequirements).Count -gt 0) {
    $lines += @($artifactReviewRequirements | ForEach-Object { "- $_" })
} else {
    $lines += 'No additional artifact review requirements were frozen for this run.'
}
$lines += @(
    '',
    '## Code Task TDD Evidence Requirements'
)
if (@($codeTaskTddEvidenceRequirements).Count -gt 0) {
    $lines += @($codeTaskTddEvidenceRequirements | ForEach-Object { "- $_" })
} else {
    $lines += 'No code-task TDD evidence requirements were frozen for this run.'
}
$lines += @(
    '',
    '## Code Task TDD Exceptions'
)
if (@($codeTaskTddExceptions).Count -gt 0) {
    $lines += @($codeTaskTddExceptions | ForEach-Object { "- $_" })
} else {
    $lines += 'No code-task TDD exceptions were frozen for this run.'
}
$lines += @(
    '',
    '## Baseline Document Quality Dimensions'
)
if (@($baselineDocumentQualityDimensions).Count -gt 0) {
    $lines += @($baselineDocumentQualityDimensions | ForEach-Object { "- $_" })
} else {
    $lines += 'No baseline document quality dimensions were frozen for this run.'
}
$lines += @(
    '',
    '## Baseline UI Quality Dimensions'
)
if (@($baselineUiQualityDimensions).Count -gt 0) {
    $lines += @($baselineUiQualityDimensions | ForEach-Object { "- $_" })
} else {
    $lines += 'No baseline UI quality dimensions were frozen for this run.'
}
$lines += @(
    '',
    '## Task-Specific Acceptance Extensions'
)
if (@($taskSpecificAcceptanceExtensions).Count -gt 0) {
    $lines += @($taskSpecificAcceptanceExtensions | ForEach-Object { "- $_" })
} else {
    $lines += 'No additional task-specific acceptance extensions were frozen for this run.'
}
$lines += @(
    '',
    '## Research Augmentation Sources'
)
if (@($researchAugmentationSources).Count -gt 0) {
    $lines += @($researchAugmentationSources | ForEach-Object { "- $_" })
} else {
    $lines += 'No research augmentation sources were frozen for this run.'
}
$lines += @(
    '',
    '> Fill the anti-drift fields once here. Downstream governed plan and completion surfaces should reuse them rather than restate them.',
    ''
)
$lines += @(Get-VgoAntiProxyGoalDriftRequirementLines -Packet $antiDriftDraft)
$lines += @(
    '',
    '## Non-Goals'
)
$lines += @($intentContract.non_goals | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Autonomy Mode',
    $intentContract.autonomy_mode,
    '',
    '## Assumptions'
)
$lines += @($intentContract.assumptions | ForEach-Object { "- $_" })
$lines += @(
    '',
    '## Evidence Inputs',
    "- Source task: $Task",
    "- Intent contract: $([System.IO.Path]::GetFileName((Join-Path $sessionRoot 'intent-contract.json')))",
    "- Runtime input packet: $([System.IO.Path]::GetFileName($runtimeInputPath))"
)

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

    $lines += @(
        '',
        '## Runtime Input Truth',
        "- Governance scope: $([string]$runtimeInputPacket.governance_scope)",
        "- Root run id: $([string]$runtimeInputPacket.hierarchy.root_run_id)",
        "- Entry intent: $entryIntentId",
        "- Requested stop stage: $requestedStageStop",
        "- Requested grade floor: $requestedGradeFloor",
        "- Selected pack: $([string]$runtimeInputPacket.route_snapshot.selected_pack)",
        "- Router-selected skill: $([string]$runtimeInputPacket.route_snapshot.selected_skill)",
        "- Runtime-selected skill: $([string]$runtimeInputPacket.authority_flags.explicit_runtime_skill)",
        "- Route mode: $([string]$runtimeInputPacket.route_snapshot.route_mode)",
        "- Route reason: $([string]$runtimeInputPacket.route_snapshot.route_reason)",
        "- Confirm required: $([bool]$runtimeInputPacket.route_snapshot.confirm_required)"
    )

    $specialistDecision = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_decision' -and
        $null -ne $runtimeInputPacket.specialist_decision
    ) {
        $runtimeInputPacket.specialist_decision
    } else {
        $null
    }
    if ($specialistDecision) {
        $lines += @(
            '',
            '## Specialist Decision',
            '- Governed `vibe` must explicitly record whether specialist execution is happening, stayed advisory, or remained unresolved before closeout.',
            ('- Decision state: {0}' -f [string]$specialistDecision.decision_state),
            ('- Resolution mode: {0}' -f [string]$specialistDecision.resolution_mode),
            ('- Notes: {0}' -f [string]$specialistDecision.notes)
        )
        if ([string]$specialistDecision.resolution_mode -eq 'repo_asset_fallback') {
            $lines += @(
                ('- Repo-asset fallback used: {0}' -f [bool]$specialistDecision.repo_asset_fallback.used),
                ('- Repo-asset fallback assets: {0}' -f [string]::Join(', ', @($specialistDecision.repo_asset_fallback.asset_paths))),
                ('- Repo-asset fallback reason: {0}' -f [string]$specialistDecision.repo_asset_fallback.reason),
                ('- Repo-asset fallback legal basis: {0}' -f [string]$specialistDecision.repo_asset_fallback.legal_basis),
                ('- Repo-asset fallback traceability basis: {0}' -f [string]::Join(', ', @($specialistDecision.repo_asset_fallback.traceability_basis)))
            )
        } elseif ([string]$specialistDecision.resolution_mode -eq 'pending_resolution') {
            $lines += '- If execution later relies on repo-local assets instead of a dedicated specialist skill, phase execute must record `specialist-decision.json` with the asset paths, fallback reason, legal basis, and traceability basis before closure.'
        }
    }

    $specialistRecommendations = @($runtimeInputPacket.specialist_recommendations)
    if ($specialistRecommendations.Count -gt 0) {
        $lines += @(
            '',
            '## Specialist Recommendations',
            'These are mandatory bounded native specialist recommendations carried inside the governed `vibe` runtime. Eligible recommendations should auto-promote into bounded dispatch while `vibe` remains the only runtime authority.',
            'If execution reaches non-empty effective `approved_dispatch`, governed `vibe` must emit one unified pre-execution disclosure that lists only actually executing Skills and each real `native_skill_entrypoint`.'
        )
        foreach ($recommendation in $specialistRecommendations) {
            $lines += @(
                "- Skill: $([string]$recommendation.skill_id)",
                "  Source: $([string]$recommendation.source); pack: $([string]$recommendation.pack_id); rank: $([string]$recommendation.rank); confidence: $([string]$recommendation.confidence)",
                "  Role: $([string]$recommendation.bounded_role); native usage required: $([bool]$recommendation.native_usage_required); preserve workflow: $([bool]$recommendation.must_preserve_workflow)",
                "  Binding: profile=$([string]$recommendation.binding_profile); phase=$([string]$recommendation.dispatch_phase); lane policy=$([string]$recommendation.lane_policy); parallel in XL=$([bool]$recommendation.parallelizable_in_root_xl)",
                "  Write scope: $([string]$recommendation.write_scope); review mode: $([string]$recommendation.review_mode); execution priority: $([int]$recommendation.execution_priority)",
                "  Reason: $([string]$recommendation.reason)",
                "  Required inputs: $([string]::Join(', ', @($recommendation.required_inputs)))",
                "  Expected outputs: $([string]::Join(', ', @($recommendation.expected_outputs)))",
                "  Verification expectation: $([string]$recommendation.verification_expectation)"
            )
        }
    }
}

if ($discussionConsultation -and [bool]$discussionConsultation.enabled) {
    $lines += @(
        '',
        '## Specialist Consultation',
        'These are specialists resolved for discussion-time handling under governed `vibe` before this requirement doc was frozen. Depending on policy, they may be consulted live or routed for direct current-session loading.'
    )
    foreach ($disclosure in @($discussionConsultation.user_disclosures)) {
        $lines += @(
            ('- Consulted Skill: {0}' -f [string]$disclosure.skill_id),
            ('  Why now: {0}' -f [string]$disclosure.why_now),
            ('  Loaded from: {0}' -f [string]$disclosure.native_skill_entrypoint)
        )
        $consultedUnit = $null
        foreach ($candidate in @($discussionConsultation.consulted_units)) {
            if ([string]$candidate.skill_id -eq [string]$disclosure.skill_id) {
                $consultedUnit = $candidate
                break
            }
        }
        if ($consultedUnit) {
            $lines += @(
                ('  Consultation status: {0}' -f [string]$consultedUnit.status),
                ('  Summary: {0}' -f [string]$consultedUnit.summary)
            )
            foreach ($note in @($consultedUnit.adoption_notes)) {
                $lines += ('  Adopted into requirement: {0}' -f [string]$note)
            }
        }
    }
    if (@($discussionConsultation.deferred_to_execution).Count -gt 0) {
        $lines += @(
            '',
            'Deferred specialist follow-up stayed separate from execution truth and remains advisory until execution-time dispatch.'
        )
        foreach ($item in @($discussionConsultation.deferred_to_execution)) {
            $lines += ('- Deferred to execution: {0} ({1})' -f [string]$item.skill_id, [string]$item.reason)
        }
    }
    if (@($discussionConsultation.degraded).Count -gt 0) {
        foreach ($item in @($discussionConsultation.degraded)) {
            $lines += ('- Consultation degraded: {0} ({1})' -f [string]$item.skill_id, [string]$item.result_reason)
        }
    }
}

$lifecycleLines = Get-VibeSpecialistLifecycleDisclosureMarkdownLines `
    -LifecycleDisclosure $stageLifecycleDisclosure `
    -IncludeLayerIds @('discussion_routing', 'discussion_consultation')
if (@($lifecycleLines).Count -gt 0) {
    $lines += @('', @($lifecycleLines))
}

$selectedMemoryCapsules = @(Get-VibeSelectedCapsuleList -ContextPack $memoryContextPack)
if ($memoryContextPack -and ((@($memoryContextPack.items).Count -gt 0) -or (@($selectedMemoryCapsules).Count -gt 0))) {
    $lines += @(
        '',
        '## Memory Context',
        'Bounded stage-aware memory context injected into requirement freezing:',
        ('- Disclosure level: {0}' -f [string]$memoryContextPack.disclosure_level)
    )
    if (@($selectedMemoryCapsules).Count -gt 0) {
        foreach ($capsule in @($selectedMemoryCapsules)) {
            $lines += @(
                ('- Capsule [{0}] {1}' -f [string]$capsule.capsule_id, [string]$capsule.title),
                ('  Owner: {0}' -f [string]$capsule.owner),
                ('  Why now: {0}' -f [string]$capsule.why_now),
                ('  Expansion Ref: {0}' -f [string]$capsule.expansion_ref)
            )
            $lines += @($capsule.summary_lines | ForEach-Object { '  Summary: ' + [string]$_ })
        }
    } else {
        $lines += @($memoryContextPack.items | ForEach-Object { "- $_" })
    }
}

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
    discussion_consultation_path = if ($discussionConsultation) { $DiscussionConsultationPath } else { $null }
    discussion_consultation_count = if ($discussionConsultation) { @($discussionConsultation.consulted_units).Count } else { 0 }
    discussion_consultation_user_disclosure_count = if ($discussionConsultation) { @($discussionConsultation.user_disclosures).Count } else { 0 }
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
