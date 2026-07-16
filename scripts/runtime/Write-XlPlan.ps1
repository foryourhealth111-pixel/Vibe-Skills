param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$RequirementDocPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$PlanMemoryContextPath = '',
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

function Get-VibeDispatchPlanLines {
    param(
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$Recommendations,
        [switch]$SuggestionMode
    )

    $lines = @()
    foreach ($recommendation in @($Recommendations)) {
        if ($SuggestionMode) {
            $lines += @(
                ('- Suggest {0}.' -f [string]$recommendation.skill_id),
                ('  Proposed phase: {0}; lane policy: {1}; write scope: {2}' -f [string]$recommendation.dispatch_phase, [string]$recommendation.lane_policy, [string]$recommendation.write_scope),
                ('  Reason: {0}' -f [string]$recommendation.reason),
                '  Escalation required: true'
            )
        } else {
            $lines += @(
                ('- Dispatch {0} as {1}.' -f [string]$recommendation.skill_id, [string]$recommendation.bounded_role),
                ('  Binding profile: {0}; dispatch phase: {1}; lane policy: {2}; parallel in XL: {3}' -f [string]$recommendation.binding_profile, [string]$recommendation.dispatch_phase, [string]$recommendation.lane_policy, [bool]$recommendation.parallelizable_in_root_xl),
                ('  Write scope: {0}; review mode: {1}; execution priority: {2}' -f [string]$recommendation.write_scope, [string]$recommendation.review_mode, [int]$recommendation.execution_priority),
                ('  Reason: {0}' -f [string]$recommendation.reason),
                ('  Required inputs: {0}' -f [string]::Join(', ', @($recommendation.required_inputs))),
                ('  Expected outputs: {0}' -f [string]::Join(', ', @($recommendation.expected_outputs))),
                ('  Verification: {0}' -f [string]$recommendation.verification_expectation)
            )
        }
        if (
            $recommendation.PSObject.Properties.Name -contains 'host_selection_action' -and
            -not [string]::IsNullOrWhiteSpace([string]$recommendation.host_selection_action)
        ) {
            $lines += ('  Host selection: {0} ({1})' -f [string]$recommendation.host_selection_action, [string]$recommendation.host_selection_mode)
        }
    }

    return @($lines)
}

function Get-VibeRecommendationPhaseId {
    param(
        [AllowNull()] [object]$Recommendation = $null
    )

    if (
        $null -eq $Recommendation -or
        -not ($Recommendation.PSObject.Properties.Name -contains 'phase_id')
    ) {
        return ''
    }

    return [string]$Recommendation.phase_id
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
$skillSearchGuide = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_search_guide' -and
    $null -ne $runtimeInputPacket.skill_search_guide
) {
    $runtimeInputPacket.skill_search_guide
} else {
    New-VibeSkillSearchGuideProjection -RepoRoot $runtime.repo_root
}
$agentSkillOrganization = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'agent_skill_organization' -and
    $null -ne $runtimeInputPacket.agent_skill_organization
) {
    $runtimeInputPacket.agent_skill_organization
} else {
    throw 'agent_skill_organization is required before xl_plan'
}
$selectedTaskSkillIds = @(Get-VibeSelectedTaskSkillIds -RuntimeInputPacket $runtimeInputPacket)
$requestedGradeFloor = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'requested_grade_floor' -and
    -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.requested_grade_floor)
) {
    [string]$runtimeInputPacket.requested_grade_floor
} else {
    ''
}
$entryIntentId = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'entry_intent_id' -and
    -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.entry_intent_id)
) {
    [string]$runtimeInputPacket.entry_intent_id
} else {
    'vibe'
}
$requestedStageStop = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'requested_stage_stop' -and
    -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.requested_stage_stop)
) {
    [string]$runtimeInputPacket.requested_stage_stop
} else {
    'phase_cleanup'
}
$requestedGradeFloorDisplay = if ([string]::IsNullOrWhiteSpace($requestedGradeFloor)) { 'none' } else { $requestedGradeFloor }
$grade = Get-VibeInternalGrade -Task $Task -RequestedGradeFloor $requestedGradeFloor
$isChildScope = ([string]$hierarchyState.governance_scope -eq 'child')
$planPath = if ($isChildScope) {
    if ([string]::IsNullOrWhiteSpace([string]$hierarchyState.inherited_execution_plan_path)) {
        throw 'Child-governed plan stage requires InheritedExecutionPlanPath.'
    }
    [string]$hierarchyState.inherited_execution_plan_path
} else {
    Get-VibeExecutionPlanPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot
}
$requirementPath = if (-not [string]::IsNullOrWhiteSpace($RequirementDocPath)) { $RequirementDocPath } else { Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot }
$antiDriftDraft = Get-VgoAntiProxyGoalDriftPacketFromRequirementDoc -RequirementDocPath $requirementPath
$requirementDocLines = if (Test-Path -LiteralPath $requirementPath) {
    @(Get-Content -LiteralPath $requirementPath -Encoding UTF8)
} else {
    @()
}
$requirementSections = Get-VgoMarkdownSectionMap -Lines $requirementDocLines
$frozenArtifactReviewRequirements = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Artifact Review Requirements')
$frozenCodeTaskTddEvidenceRequirements = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Code Task TDD Evidence Requirements' | Where-Object { -not ([string]$_).StartsWith('No code-task TDD evidence requirements were frozen', [System.StringComparison]::OrdinalIgnoreCase) })
$frozenCodeTaskTddExceptions = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Code Task TDD Exceptions' | Where-Object { -not ([string]$_).StartsWith('No code-task TDD exceptions were frozen', [System.StringComparison]::OrdinalIgnoreCase) })
$frozenBaselineDocumentQualityDimensions = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Baseline Document Quality Dimensions')
$frozenBaselineUiQualityDimensions = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Baseline UI Quality Dimensions')
$frozenTaskSpecificAcceptanceExtensions = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Task-Specific Acceptance Extensions')
$frozenResearchAugmentationSources = @(Get-VgoMarkdownSectionList -Sections $requirementSections -Heading 'Research Augmentation Sources')
$hasFrozenCodeTaskTddObligations = (@($frozenCodeTaskTddEvidenceRequirements).Count -gt 0 -or @($frozenCodeTaskTddExceptions).Count -gt 0)
$planMemoryContext = if (-not [string]::IsNullOrWhiteSpace($PlanMemoryContextPath) -and (Test-Path -LiteralPath $PlanMemoryContextPath)) {
    Get-Content -LiteralPath $PlanMemoryContextPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$moduleWorkPlanPath = Join-Path $sessionRoot 'module-work-plan.json'
$moduleWorkPlan = New-VibeModuleWorkPlan -RunId $RunId -AgentSkillOrganization $agentSkillOrganization -RequirementDocPath $requirementPath
if ($hasFrozenCodeTaskTddObligations) {
    $moduleWorkPlan | Add-Member -NotePropertyName 'code_task_tdd_evidence_requirements' -NotePropertyValue ([object[]]@($frozenCodeTaskTddEvidenceRequirements))
    $moduleWorkPlan | Add-Member -NotePropertyName 'code_task_tdd_exceptions' -NotePropertyValue ([object[]]@($frozenCodeTaskTddExceptions))
}
Write-VibeJsonArtifact -Path $moduleWorkPlanPath -Value $moduleWorkPlan
$grade = [string]$moduleWorkPlan.workflow_level
$directChatPlan = (
    @($moduleWorkPlan.modules).Count -eq 1 -and
    [string]$moduleWorkPlan.modules[0].execution_mode -eq 'agent_direct' -and
    @($moduleWorkPlan.work_units).Count -eq 1 -and
    $null -eq $moduleWorkPlan.work_units[0].skill_id
)
$executionTargetRoot = [string](Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('host_adapter', 'target_root') -DefaultValue '')
if ([string]::IsNullOrWhiteSpace($executionTargetRoot)) {
    throw 'module work plan requires host_adapter.target_root'
}
$executionTargetRoot = [System.IO.Path]::GetFullPath($executionTargetRoot)
$effectiveHostId = [string](Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('host_adapter', 'effective_host_id') -DefaultValue 'codex')
$approvedDispatch = @(Convert-VibeModuleWorkPlanToDispatch `
    -ModuleWorkPlan $moduleWorkPlan `
    -RepoRoot ([System.IO.Path]::GetFullPath($runtime.repo_root)) `
    -TargetRoot $executionTargetRoot `
    -HostId $effectiveHostId)
$executionPhaseDecomposition = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'host_decision' -and
    $null -ne $runtimeInputPacket.host_decision -and
    $runtimeInputPacket.host_decision.PSObject.Properties.Name -contains 'phase_decomposition' -and
    $null -ne $runtimeInputPacket.host_decision.phase_decomposition
) {
    $runtimeInputPacket.host_decision.phase_decomposition
} elseif (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'execution_phase_decomposition' -and
    $null -ne $runtimeInputPacket.execution_phase_decomposition
) {
    $runtimeInputPacket.execution_phase_decomposition
} else {
    $null
}
$plannedWaves = @(New-VibeModuleWorkWaves -ModuleWorkPlan $moduleWorkPlan -Units @($moduleWorkPlan.work_units))
$waveLines = @(
    for ($waveIndex = 0; $waveIndex -lt $plannedWaves.Count; $waveIndex++) {
        $wave = $plannedWaves[$waveIndex]
        $unitLabels = @(
            foreach ($unitId in @($wave.unit_ids)) {
                $unit = @($moduleWorkPlan.work_units | Where-Object { [string]$_.unit_id -eq [string]$unitId } | Select-Object -First 1)
                if (@($unit).Count -eq 0) {
                    throw ('visible wave references unknown module work unit `{0}`' -f [string]$unitId)
                }
                $worker = if ([string]::IsNullOrWhiteSpace([string]$unit[0].skill_id)) {
                    'current Agent'
                } else {
                    ('skill `{0}`' -f [string]$unit[0].skill_id)
                }
                ('`{0}` via {1} as `{2}`' -f [string]$unit[0].module_id, $worker, [string]$unit[0].role)
            }
        )
        ('- Wave {0} (`{1}`): {2}' -f ($waveIndex + 1), [string]$wave.execution_mode, ($unitLabels -join '; '))
    }
)

$lines = @("# $(Get-VibeTitleFromTask -Task $Task)")
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Execution Summary' -BodyLines @(
    "Governed runtime execution plan for ``vibe`` in mode $Mode."
)
$frozenInputLines = @(
    "- Requirement doc: $([System.IO.Path]::GetFullPath($requirementPath))",
    "- Source task: $Task"
)
if ($runtimeInputPacket) {
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
            ('- Revision target stage: {0}' -f $(if ([string]::IsNullOrWhiteSpace($hostRevisionTargetStage)) { 'xl_plan' } else { [string]$hostRevisionTargetStage })),
            @(New-VibeBulletLines -Items @($hostRevisionDelta))
        )
    }
}
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Skill Search Guide' -BodyLines @(Get-VibeSkillSearchGuideLines -SkillSearchGuide $skillSearchGuide)
$moduleLines = @($agentSkillOrganization.modules | ForEach-Object {
    ('- `{0}`: {1}' -f [string]$_.module_id, [string]$_.goal)
})
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Task Modules' -BodyLines @($moduleLines)
$candidateLines = @($agentSkillOrganization.modules | ForEach-Object {
    $candidateText = if (@($_.candidate_skill_ids).Count -gt 0) {
        @($_.candidate_skill_ids | ForEach-Object { ('`{0}`' -f [string]$_) }) -join ', '
    } else {
        'none found'
    }
    ('- `{0}`: {1}' -f [string]$_.module_id, $candidateText)
})
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Candidate Skills By Module' -BodyLines @($candidateLines)
$uncoveredModuleLines = if (@($agentSkillOrganization.uncovered_modules).Count -gt 0) {
    @($agentSkillOrganization.uncovered_modules | ForEach-Object {
        ('- `{0}`: {1}' -f [string]$_.module_id, [string]$_.reason)
    })
} else {
    $directModuleIds = @(
        $agentSkillOrganization.modules |
            Where-Object { [string]$_.execution_mode -eq 'agent_direct' } |
            ForEach-Object { ('`{0}`' -f [string]$_.module_id) }
    )
    if (@($directModuleIds).Count -gt 0) {
        @(
            '- No module is blocked by a Skill gap; {0} is explicitly assigned to the current Agent without a local Skill.' -f ($directModuleIds -join ', ')
        )
    } else {
        @('- None. Every declared module is covered by an Agent-selected local Skill.')
    }
}
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Uncovered Modules' -BodyLines @($uncoveredModuleLines)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'L / XL Organization Difference' -BodyLines @(
    ('- L: {0}' -f [string]$agentSkillOrganization.workflow_level_contract.L),
    ('- XL: {0}' -f [string]$agentSkillOrganization.workflow_level_contract.XL),
    ('- Selected workflow level: `{0}`' -f [string]$agentSkillOrganization.workflow_level)
)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Frozen Inputs' -BodyLines @($frozenInputLines)
if (-not $directChatPlan) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Wave Plan' -BodyLines @($waveLines)
}
$executionPhaseLines = @(Get-VibeExecutionPhaseMarkdownLines -PhaseDecomposition $executionPhaseDecomposition)
if (@($executionPhaseLines).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Execution Phase Plan' -BodyLines @($executionPhaseLines)
}
$deliveryAcceptanceReportPath = Join-Path $sessionRoot 'delivery-acceptance-report.json'
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Delivery Acceptance Plan' -BodyLines @(
    '- Freeze downstream product acceptance inside the governed requirement doc and reuse it rather than inventing closeout claims later.',
    '- Emit a per-run delivery-acceptance report during `phase_cleanup` so runtime/process success is kept separate from project-delivery success.',
    ('- Delivery-acceptance report: {0}' -f $deliveryAcceptanceReportPath),
    '- If manual spot checks are declared in the requirement doc, final completion wording stays blocked until they are cleared or explicitly downgraded to manual review.',
    '- Release truth aggregation remains an outer-layer gate; this run emits the per-run delivery-truth report only.'
)
if (@($frozenArtifactReviewRequirements).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Artifact Review Strategy' -BodyLines @(
        '- If the frozen requirement doc declares `Artifact Review Requirements`, execution must leave behind explicit artifact-review evidence rather than relying on generic completion wording.',
        '- Artifact review may be recorded inline in `phase-execute.json` or through a dedicated `artifact-review.json` sidecar, but one of those governed surfaces must exist when direct artifact review is required.',
        '- Product acceptance stays blocked when required artifact review remains missing, partial, degraded, or manual-review-only.'
    )
}
if ($hasFrozenCodeTaskTddObligations) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Code Task TDD Evidence Plan' -BodyLines @(
        '- Reuse the frozen `Code Task TDD Evidence Requirements` section from the requirement doc rather than inventing late closeout claims.',
        '- Reuse the frozen `Code Task TDD Exceptions` section when strict failing-first sequencing is intentionally exempted.',
        '- Map each frozen requirement or exception to an implementation step, a targeted verification command, and a proof artifact.',
        '- If strict failing-first sequencing is blocked, execution must record the bounded reason and fallback evidence explicitly.'
    )
}
if (@($frozenBaselineDocumentQualityDimensions).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Baseline Document Quality Mapping' -BodyLines @(
    '- Use the frozen `Baseline Document Quality Dimensions` section in the requirement doc as the authoritative list of document-artifact quality dimensions that artifact review must cover before a document delivery can claim full completion.',
    '- Track each baseline document dimension through artifact-review annotations so the delivery-acceptance report can show which structure, formatting, completeness, reference integrity, layout stability, and output fidelity expectations were inspected.',
    '- Treat missing document-dimension coverage as a manual-review-required hit and keep this mapping separate from UI baselines and code-task TDD evidence.'
    )
}
if (@($frozenBaselineUiQualityDimensions).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Baseline UI Quality Mapping' -BodyLines @(
    '- Use the frozen `Baseline UI Quality Dimensions` section in the requirement doc as the authoritative list of dimensions that artifact review must cover before a UI delivery can claim full completion.',
    '- Track each baseline dimension through execution and artifact-review annotations so the delivery-acceptance report can show which structure, interaction, state, consistency, responsiveness, and fidelity expectations were inspected.',
    '- Treat missing dimension coverage as a manual-review-required hit and include explicit mapping steps or targeted verification units that drive reviewers to capture the evidence the requirement doc established.'
    )
}
if (@($frozenTaskSpecificAcceptanceExtensions).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Task-Specific Acceptance Mapping' -BodyLines @(
    '- Reuse frozen task-specific acceptance extensions from the requirement doc instead of inventing late closeout criteria.',
    '- Keep base delivery truth separate from task-specific expectations so each can be inspected independently during review.'
    )
}
if (@($frozenResearchAugmentationSources).Count -gt 0) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Research Augmentation Plan' -BodyLines @(
    '- Preserve any frozen research augmentation sources from the requirement doc so later reviewers can tell which external standards strengthened the brief.',
    '- Research augmentation may strengthen rough asks, but it must not replace the user-owned requirement surface.'
    )
}
$moduleWorkPlanLines = @()
foreach ($module in @($moduleWorkPlan.modules)) {
    $dependencyText = if (@($module.depends_on).Count -gt 0) {
        @($module.depends_on | ForEach-Object { ('`{0}`' -f [string]$_) }) -join ', '
    } else {
        'none'
    }
    $moduleWorkPlanLines += ('- `{0}`: {1}' -f [string]$module.module_id, [string]$module.goal)
    $moduleWorkPlanLines += ('  Required: `{0}`; dependencies: {1}; Execution mode: `{2}`' -f [bool]$module.required, $dependencyText, [string]$module.execution_mode)
    $moduleUnits = @($moduleWorkPlan.work_units | Where-Object { [string]$_.module_id -eq [string]$module.module_id })
    foreach ($unit in @($moduleUnits)) {
        $worker = if ([string]::IsNullOrWhiteSpace([string]$unit.skill_id)) { 'current Agent' } else { ('skill `{0}`' -f [string]$unit.skill_id) }
        $moduleWorkPlanLines += ('  Work: {0} as `{1}` - {2}' -f $worker, [string]$unit.role, [string]$unit.responsibility)
    }
    if (@($moduleUnits).Count -eq 0) {
        $moduleWorkPlanLines += '  Work: blocked until the declared capability gap is resolved.'
    }
    foreach ($criterion in @($module.acceptance_criteria)) {
        $moduleWorkPlanLines += ('  Acceptance: `{0}` ({1}) - {2}' -f [string]$criterion.criterion_id, [string]$criterion.verification_mode, [string]$criterion.description)
    }
}
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Module Work Plan' -BodyLines @($moduleWorkPlanLines)
if (@($approvedDispatch).Count -gt 0) {
    if ($executionPhaseDecomposition -and @($executionPhaseDecomposition.phases).Count -gt 0) {
        $declaredPhaseIds = @($executionPhaseDecomposition.phases | ForEach-Object { [string]$_.phase_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        foreach ($phase in @($executionPhaseDecomposition.phases)) {
            $targetPhaseId = [string]$phase.phase_id
            $phaseDispatches = @($approvedDispatch | Where-Object { (Get-VibeRecommendationPhaseId -Recommendation $_) -eq $targetPhaseId })
            if (@($phaseDispatches).Count -eq 0) {
                continue
            }

            $lines += @(
                '',
                ('### Phase `{0}` [{1} -> {2}] order `{3}`: {4}' -f [string]$phase.phase_id, [string]$phase.stage_type, [string]$phase.dispatch_phase, [int]$phase.stage_order, [string]$phase.stage_label)
            )
            $lines += @(Get-VibeDispatchPlanLines -Recommendations @($phaseDispatches))
        }

        $ungroupedApprovedDispatch = @($approvedDispatch | Where-Object {
            $phaseId = Get-VibeRecommendationPhaseId -Recommendation $_
            [string]::IsNullOrWhiteSpace($phaseId) -or $declaredPhaseIds -notcontains $phaseId
        })
        if (@($ungroupedApprovedDispatch).Count -gt 0) {
            $lines += @(
                '',
                '### Phase `ungrouped`: module work'
            )
            $lines += @(Get-VibeDispatchPlanLines -Recommendations @($ungroupedApprovedDispatch))
        }
    } else {
        $lines += @(Get-VibeDispatchPlanLines -Recommendations @($approvedDispatch))
    }
}
$selectedPlanMemoryCapsules = @(Get-VibeSelectedCapsuleList -ContextPack $planMemoryContext)
Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Verification Commands' -BodyLines @(
    '- Run every verification command frozen for the module work units and retain its real result.',
    '- Reconcile every module acceptance criterion against the returned execution evidence.',
    '- Review the delivery-acceptance report emitted during `phase_cleanup` before using full completion language.'
)
if (-not $directChatPlan) {
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Rollback Plan' -BodyLines @(
        '- If verification fails, revert only changes inside the approved module write scopes.',
        '- Do not roll back unrelated user changes.'
    )
    Add-VibeMarkdownSection -Lines ([ref]$lines) -Heading 'Phase Cleanup Contract' -BodyLines @(
        '- Remove temporary artifacts created by the approved module work only.',
        '- Write cleanup receipt before completion.'
    )
}

$childHandoffPath = $null
if ($isChildScope) {
    if (-not (Test-Path -LiteralPath $planPath)) {
        throw ("Child-governed plan stage cannot inherit missing canonical execution plan: {0}" -f $planPath)
    }

    $childHandoffPath = Join-Path $sessionRoot 'child-execution-handoff.md'
    $handoffLines = @(
        "# Child Execution Handoff",
        '',
        '- governance_scope: child',
        ('- inherited_execution_plan: {0}' -f $planPath),
        ('- root_run_id: {0}' -f [string]$hierarchyState.root_run_id),
        ('- parent_run_id: {0}' -f [string]$hierarchyState.parent_run_id),
        ('- parent_unit_id: {0}' -f [string]$hierarchyState.parent_unit_id),
        '- canonical_write_allowed: false',
        ('- assigned_skill_work_unit_count: {0}' -f @($approvedDispatch).Count),
        '',
        'Child-governed lanes inherit the frozen root plan and may not create a second canonical execution-plan surface.'
    )
    Write-VibeMarkdownArtifact -Path $childHandoffPath -Lines $handoffLines
} else {
    Write-VibeMarkdownArtifact -Path $planPath -Lines $lines
}

$receipt = [pscustomobject]@{
    stage = 'xl_plan'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    internal_grade = $grade
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    module_work_plan_path = $moduleWorkPlanPath
    child_execution_handoff_path = $childHandoffPath
    canonical_write_allowed = -not $isChildScope
    inherited_execution_plan_path = if ($isChildScope) { $planPath } else { $null }
    runtime_input_packet_path = $runtimeInputPath
    plan_memory_context_path = $PlanMemoryContextPath
    plan_memory_disclosure_level = if ($planMemoryContext -and $planMemoryContext.PSObject.Properties.Name -contains 'disclosure_level') { [string]$planMemoryContext.disclosure_level } else { $null }
    plan_memory_capsule_count = @($selectedPlanMemoryCapsules).Count
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'execution-plan-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    execution_plan_path = $planPath
    module_work_plan_path = $moduleWorkPlanPath
    receipt_path = $receiptPath
    receipt = $receipt
}
