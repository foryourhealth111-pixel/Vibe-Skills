param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$IntentContractPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $GovernanceScope `
    -RunId $RunId `
    -RootRunId $RootRunId `
    -ParentRunId $ParentRunId `
    -ParentUnitId $ParentUnitId `
    -InheritedRequirementDocPath $InheritedRequirementDocPath `
    -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
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
$runtimeInputPacket = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath) -and (Test-Path -LiteralPath $RuntimeInputPacketPath)) {
    Get-Content -LiteralPath $RuntimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
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
    "- Runtime input packet: $([System.IO.Path]::GetFileName($RuntimeInputPacketPath))"
)

if ($runtimeInputPacket) {
    $lines += @(
        '',
        '## Runtime Input Truth',
        "- Governance scope: $([string]$runtimeInputPacket.governance_scope)",
        "- Root run id: $([string]$runtimeInputPacket.hierarchy.root_run_id)",
        "- Selected pack: $([string]$runtimeInputPacket.route_snapshot.selected_pack)",
        "- Router-selected skill: $([string]$runtimeInputPacket.route_snapshot.selected_skill)",
        "- Runtime-selected skill: $([string]$runtimeInputPacket.authority_flags.explicit_runtime_skill)",
        "- Route mode: $([string]$runtimeInputPacket.route_snapshot.route_mode)",
        "- Route reason: $([string]$runtimeInputPacket.route_snapshot.route_reason)",
        "- Confirm required: $([bool]$runtimeInputPacket.route_snapshot.confirm_required)"
    )

    $specialistRecommendations = @($runtimeInputPacket.specialist_recommendations)
    if ($specialistRecommendations.Count -gt 0) {
        $lines += @(
            '',
            '## Specialist Recommendations',
            'These are bounded native specialist suggestions carried inside the governed `vibe` runtime. They do not replace runtime authority.'
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
    runtime_input_packet_path = $RuntimeInputPacketPath
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
