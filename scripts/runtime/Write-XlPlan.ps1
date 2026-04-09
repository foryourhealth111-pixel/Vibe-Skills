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
. (Join-Path $PSScriptRoot 'VibeExecution.Common.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

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
$runtimeInputPacket = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath) -and (Test-Path -LiteralPath $RuntimeInputPacketPath)) {
    Get-Content -LiteralPath $RuntimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$gradeResolution = Resolve-VibeGovernedGrade `
    -BaseGrade (Get-VibeInternalGrade -Task $Task) `
    -RequestedGradeFloor $(if ($runtimeInputPacket) { [string]$runtimeInputPacket.requested_grade_floor } else { '' }) `
    -Policy $runtime.runtime_input_packet_policy
$grade = [string]$gradeResolution.internal_grade
$planMemoryContext = if (-not [string]::IsNullOrWhiteSpace($PlanMemoryContextPath) -and (Test-Path -LiteralPath $PlanMemoryContextPath)) {
    Get-Content -LiteralPath $PlanMemoryContextPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$approvedDispatch = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.approved_dispatch) } else { @() }
$localSuggestions = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.local_specialist_suggestions) } else { @() }
$executionTopology = New-VibeExecutionTopology `
    -RunId $RunId `
    -Grade $grade `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -ExecutionPolicy $runtime.execution_runtime_policy `
    -TopologyPolicy $runtime.execution_topology_policy `
    -ApprovedDispatch @($approvedDispatch)
$executionTopologyPath = Get-VibeExecutionTopologyPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
Write-VibeJsonArtifact -Path $executionTopologyPath -Value $executionTopology

$waveLines = switch ($grade) {
    'XL' {
        @(
            '- Wave 1: skeleton, intent freeze, and requirement validation',
            '- Wave 2: implementation decomposition and bounded ownership assignment',
            '- Wave 3: verification, reconciliation, and cleanup handoff'
        )
    }
    'L' {
        @(
            '- Wave 1: design confirmation and implementation preparation',
            '- Wave 2: implementation and targeted verification',
            '- Wave 3: cleanup and residual-risk review'
        )
    }
    default {
        @(
            '- Wave 1: direct implementation with narrow verification',
            '- Wave 2: cleanup and completion evidence'
        )
    }
}

$lines = @(
    "# $(Get-VibeTitleFromTask -Task $Task)",
    '',
    '## Execution Summary',
    "Governed runtime execution plan for `vibe` in mode `$Mode`.",
    '',
    '## Frozen Inputs',
    "- Requirement doc: $([System.IO.Path]::GetFullPath($requirementPath))",
    "- Runtime input packet: $RuntimeInputPacketPath",
    "- Source task: $Task"
)
$lines += @('')
if ($runtimeInputPacket) {
    $lines += @(
        "- Entry intent: $([string]$runtimeInputPacket.entry_intent_id)",
        "- Requested stop stage: $([string]$runtimeInputPacket.requested_stage_stop)",
        "- Requested grade floor: $([string]$runtimeInputPacket.requested_grade_floor)",
        "- Governance scope: $([string]$runtimeInputPacket.governance_scope)",
        "- Root run id: $([string]$runtimeInputPacket.hierarchy.root_run_id)",
        "- Frozen route pack: $([string]$runtimeInputPacket.route_snapshot.selected_pack)",
        "- Frozen route skill: $([string]$runtimeInputPacket.route_snapshot.selected_skill)",
        "- Frozen route mode: $([string]$runtimeInputPacket.route_snapshot.route_mode)",
        "- Router/runtime skill mismatch: $([bool]$runtimeInputPacket.divergence_shadow.skill_mismatch)"
    )
}
$lines += @(
    "- Execution topology companion: $executionTopologyPath"
)
$lines += @(Get-VgoAntiProxyGoalDriftPlanLines -Packet $antiDriftDraft)
$lines += @(
    '',
    '## Internal Grade Decision',
    "- Grade: $grade",
    '- User-facing runtime remains fixed; grade is internal only.',
    '- `vibe` remains the governor and final authority for execution flow.',
    '',
    '## Wave Plan'
)
$lines += $waveLines
$deliveryAcceptanceReportPath = Join-Path $sessionRoot 'delivery-acceptance-report.json'
$lines += @(
    '',
    '## Delivery Acceptance Plan',
    '- Freeze downstream product acceptance inside the governed requirement doc and reuse it rather than inventing closeout claims later.',
    '- Emit a per-run delivery-acceptance report during `phase_cleanup` so runtime/process success is kept separate from project-delivery success.',
    ('- Delivery-acceptance report: {0}' -f $deliveryAcceptanceReportPath),
    '- If manual spot checks are declared in the requirement doc, final completion wording stays blocked until they are cleared or explicitly downgraded to manual review.',
    '- Release truth aggregation remains an outer-layer gate; this run emits the per-run delivery-truth report only.'
)
$lines += @(
    '',
    '## Execution Topology Snapshot',
    "- Delegation mode: $([string]$executionTopology.delegation_mode)",
    "- Review mode: $([string]$executionTopology.review_mode)",
    "- Specialist execution mode: $([string]$executionTopology.specialist_execution_mode)",
    "- Max parallel units: $([int]$executionTopology.max_parallel_units)"
)
foreach ($topologyWave in @($executionTopology.waves)) {
    $lines += ('- Wave `{0}` has {1} executable step(s).' -f [string]$topologyWave.wave_id, @($topologyWave.steps).Count)
    foreach ($step in @($topologyWave.steps)) {
        $lines += ('  Step `{0}` -> mode `{1}`, units `{2}`.' -f [string]$step.step_id, [string]$step.execution_mode, @($step.units).Count)
    }
}
if (@($approvedDispatch).Count -gt 0 -or @($localSuggestions).Count -gt 0) {
    $lines += @(
        '',
        '## Specialist Skill Dispatch Plan',
        '- Specialist dispatch is advisory and bounded; it does not transfer runtime authority away from vibe.',
        '- Each specialist must be invoked through its native workflow, input contract, and validation style.',
        '- Specialist outputs remain subordinate to the frozen requirement and the governed plan.'
    )
        foreach ($recommendation in @($approvedDispatch)) {
            $lines += @(
                ('- Dispatch {0} as {1}.' -f [string]$recommendation.skill_id, [string]$recommendation.bounded_role),
                ('  Binding profile: {0}; dispatch phase: {1}; lane policy: {2}; parallel in XL: {3}' -f [string]$recommendation.binding_profile, [string]$recommendation.dispatch_phase, [string]$recommendation.lane_policy, [bool]$recommendation.parallelizable_in_root_xl),
                ('  Write scope: {0}; review mode: {1}; execution priority: {2}' -f [string]$recommendation.write_scope, [string]$recommendation.review_mode, [int]$recommendation.execution_priority),
                ('  Specialist source of truth: entrypoint={0}; root={1}; visibility={2}' -f [string]$recommendation.native_skill_entrypoint, [string]$recommendation.skill_root, [string]$recommendation.visibility_class),
                ('  Usage required: {0}; preserve workflow: {1}' -f [bool]$recommendation.usage_required, [bool]$recommendation.must_preserve_workflow),
                ('  Reason: {0}' -f [string]$recommendation.reason),
                ('  Expected contribution: {0}' -f [string]$recommendation.expected_contribution),
                ('  Required inputs: {0}' -f [string]::Join(', ', @($recommendation.required_inputs))),
                ('  Expected outputs: {0}' -f [string]::Join(', ', @($recommendation.expected_outputs))),
                ('  Verification: {0}' -f [string]$recommendation.verification_expectation)
            )
    }
    if (@($localSuggestions).Count -gt 0) {
        $lines += @(
            '',
            '## Child Specialist Escalation Suggestions',
            '- These suggestions are advisory only until root-governed approval updates the canonical dispatch surface.'
        )
        foreach ($recommendation in @($localSuggestions)) {
            $lines += @(
                ('- Suggest {0}.' -f [string]$recommendation.skill_id),
                ('  Proposed phase: {0}; lane policy: {1}; write scope: {2}' -f [string]$recommendation.dispatch_phase, [string]$recommendation.lane_policy, [string]$recommendation.write_scope),
                ('  Reason: {0}' -f [string]$recommendation.reason),
                '  Escalation required: true'
            )
        }
    }
}
if ($planMemoryContext -and @($planMemoryContext.items).Count -gt 0) {
    $lines += @(
        '',
        '## Memory Context',
        'Bounded stage-aware memory context injected into execution planning:'
    )
    $lines += @($planMemoryContext.items | ForEach-Object { "- $_" })
}
$lines += @(
    '',
    '## Completion Language Rules',
    '- Do not report runtime completion as downstream project delivery unless the delivery-acceptance report returns `PASS`.',
    '- `completed_with_failures`, degraded execution, or pending manual actions must downgrade completion wording.',
    '- Child-governed completion remains local-scope only and cannot justify root-level completion language.',
    '',
    '## Ownership Boundaries',
    '- One owner per artifact set.',
    '- Parallel work must use disjoint write scopes.',
    '- Subagent prompts must end with `$vibe`.',
    '- Specialist help stays bounded and native-mode; it must not become a second planner or a second runtime.',
    '',
    '## Verification Commands',
    '- Run targeted repo verification for changed surfaces.',
    '- Run runtime contract gate before claiming completion.',
    '- Review the delivery-acceptance report emitted during `phase_cleanup` before using full completion language.',
    '- Re-run mirror sync and parity validation before release claims.',
    '',
    '## Rollback Plan',
    '- Revert only the governed-runtime change set if verification fails.',
    '- Do not roll back unrelated user changes.',
    '',
    '## Phase Cleanup Contract',
    '- Remove temp artifacts created by the wave.',
    '- Run node audit and cleanup when needed.',
    '- Write cleanup receipt before completion.'
)

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
        ('- approved_specialist_dispatch_count: {0}' -f @($approvedDispatch).Count),
        ('- local_specialist_suggestion_count: {0}' -f @($localSuggestions).Count),
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
    child_execution_handoff_path = $childHandoffPath
    canonical_write_allowed = -not $isChildScope
    inherited_execution_plan_path = if ($isChildScope) { $planPath } else { $null }
    runtime_input_packet_path = $RuntimeInputPacketPath
    plan_memory_context_path = $PlanMemoryContextPath
    execution_topology_path = $executionTopologyPath
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'execution-plan-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    execution_plan_path = $planPath
    receipt_path = $receiptPath
    receipt = $receipt
}
