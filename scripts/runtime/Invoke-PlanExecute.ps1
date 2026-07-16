param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$RequirementDocPath = '',
    [string]$ExecutionPlanPath = '',
    [string]$ModuleWorkPlanPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$ExecutionMemoryContextPath = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeSkillRouting.Common.ps1')

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$artifactBaseRoot = Get-VibeArtifactRoot -RepoRoot $runtime.repo_root -Runtime $runtime -ArtifactRoot $ArtifactRoot
$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $artifactBaseRoot
$requirementPath = if ([string]::IsNullOrWhiteSpace($RequirementDocPath)) {
    Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $artifactBaseRoot
} else {
    [System.IO.Path]::GetFullPath($RequirementDocPath)
}
$planPath = if ([string]::IsNullOrWhiteSpace($ExecutionPlanPath)) {
    Get-VibeExecutionPlanPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $artifactBaseRoot
} else {
    [System.IO.Path]::GetFullPath($ExecutionPlanPath)
}
$runtimeInputPath = if ([string]::IsNullOrWhiteSpace($RuntimeInputPacketPath)) {
    Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $artifactBaseRoot
} else {
    [System.IO.Path]::GetFullPath($RuntimeInputPacketPath)
}
$moduleWorkPlanPath = if ([string]::IsNullOrWhiteSpace($ModuleWorkPlanPath)) {
    Join-Path $sessionRoot 'module-work-plan.json'
} else {
    [System.IO.Path]::GetFullPath($ModuleWorkPlanPath)
}

foreach ($requiredPath in @($requirementPath, $planPath, $runtimeInputPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw ("plan_execute requires source artifact: {0}" -f $requiredPath)
    }
}

$runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (
    -not (Test-VibeObjectHasProperty -InputObject $runtimeInputPacket -PropertyName 'agent_skill_organization') -or
    $null -eq $runtimeInputPacket.agent_skill_organization
) {
    throw 'plan_execute requires agent_skill_organization'
}
$runtimeStorage = Get-VibePropertySafe -InputObject $runtimeInputPacket -PropertyName 'storage' -DefaultValue $null
$workspaceRoot = [string](Get-VibePropertySafe -InputObject $runtimeStorage -PropertyName 'workspace_root' -DefaultValue '')
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) {
    throw 'plan_execute requires storage.workspace_root'
}
$workspaceRoot = [System.IO.Path]::GetFullPath($workspaceRoot)
if (-not (Test-Path -LiteralPath $moduleWorkPlanPath -PathType Leaf)) {
    throw ("plan_execute requires source artifact: {0}" -f $moduleWorkPlanPath)
}
$agentSkillOrganization = $runtimeInputPacket.agent_skill_organization
$agentSelectedSkillIds = @(
    @($agentSkillOrganization.selected_skills) |
        ForEach-Object { [string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_id' -DefaultValue '') } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
)

$moduleWorkPlan = Get-Content -LiteralPath $moduleWorkPlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$moduleWorkPlan.schema_version -cne 'module_work_plan_v1') {
    throw 'module work plan schema_version must be `module_work_plan_v1`'
}
if ([string]$moduleWorkPlan.source_run_id -cne $RunId) {
    throw 'module work plan source_run_id must match the executing run'
}
if ([string]$moduleWorkPlan.workflow_level -notin @('L', 'XL')) {
    throw 'module work plan workflow_level must be `L` or `XL`'
}
$grade = [string]$moduleWorkPlan.workflow_level

$currentRequirementDigest = (Get-FileHash -LiteralPath $requirementPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ([string]$moduleWorkPlan.requirement_digest -cne $currentRequirementDigest) {
    throw 'module work plan requirement digest mismatch'
}
$organizationJson = $agentSkillOrganization | ConvertTo-Json -Depth 100 -Compress
$organizationBytes = [System.Text.Encoding]::UTF8.GetBytes($organizationJson)
$organizationSha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $currentOrganizationDigest = ([System.BitConverter]::ToString(
        $organizationSha256.ComputeHash($organizationBytes)
    )).Replace('-', '').ToLowerInvariant()
} finally {
    $organizationSha256.Dispose()
}
if ([string]$moduleWorkPlan.organization_digest -cne $currentOrganizationDigest) {
    throw 'module work plan organization digest mismatch'
}

$hierarchy = Get-VibePropertySafe -InputObject $runtimeInputPacket -PropertyName 'hierarchy' -DefaultValue $null
$packetGovernanceScope = [string](Get-VibePropertySafe -InputObject $runtimeInputPacket -PropertyName 'governance_scope' -DefaultValue $GovernanceScope)
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $packetGovernanceScope `
    -RunId $RunId `
    -RootRunId ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'root_run_id' -DefaultValue $RootRunId)) `
    -ParentRunId ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'parent_run_id' -DefaultValue $ParentRunId)) `
    -ParentUnitId ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'parent_unit_id' -DefaultValue $ParentUnitId)) `
    -InheritedRequirementDocPath ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'inherited_requirement_doc_path' -DefaultValue $requirementPath)) `
    -InheritedExecutionPlanPath ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'inherited_execution_plan_path' -DefaultValue $planPath)) `
    -DelegationEnvelopePath ([string](Get-VibePropertySafe -InputObject $hierarchy -PropertyName 'delegation_envelope_path' -DefaultValue '')) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract

$hostAdapter = Get-VibePropertySafe -InputObject $runtimeInputPacket -PropertyName 'host_adapter' -DefaultValue $null
$executionTargetRoot = [string](Get-VibePropertySafe -InputObject $hostAdapter -PropertyName 'target_root' -DefaultValue '')
if ([string]::IsNullOrWhiteSpace($executionTargetRoot)) {
    throw 'plan_execute requires host_adapter.target_root'
}
$executionTargetRoot = [System.IO.Path]::GetFullPath($executionTargetRoot)
$effectiveHostId = [string](Get-VibePropertySafe -InputObject $hostAdapter -PropertyName 'effective_host_id' -DefaultValue 'codex')
$modulePlanDispatch = @(Convert-VibeModuleWorkPlanToDispatch `
    -ModuleWorkPlan $moduleWorkPlan `
    -RepoRoot ([System.IO.Path]::GetFullPath($runtime.repo_root)) `
    -TargetRoot $executionTargetRoot `
    -HostId $effectiveHostId)
$modulePlanSkillIds = @($modulePlanDispatch | ForEach-Object { [string]$_.skill_id } | Sort-Object -Unique)
if (($agentSelectedSkillIds -join "`n") -cne ($modulePlanSkillIds -join "`n")) {
    throw 'module work plan selected skills must match agent_skill_organization'
}

$moduleExecutionTargetPath = Join-Path $sessionRoot 'module-execution.json'
$agentExecutionHandoff = New-VibeAgentExecutionHandoff `
    -RunId $RunId `
    -ModuleWorkPlan $moduleWorkPlan `
    -ModulePlanDispatch @($modulePlanDispatch) `
    -ModuleExecutionPath $moduleExecutionTargetPath `
    -WorkspaceRoot $workspaceRoot `
    -ArtifactRoot $artifactBaseRoot `
    -RepoRoot ([System.IO.Path]::GetFullPath($runtime.repo_root))
$agentExecutionHandoffPath = Join-Path $sessionRoot 'agent-execution-handoff.json'
Write-VibeJsonArtifact -Path $agentExecutionHandoffPath -Value $agentExecutionHandoff
$assignedSkillUnits = @($agentExecutionHandoff.units | Where-Object {
    -not [string]::IsNullOrWhiteSpace([string]$_.skill_id)
})
$assignedSkillIds = @($assignedSkillUnits | ForEach-Object { [string]$_.skill_id } | Sort-Object -Unique)
$dispatchContractIncompleteSkillIds = @(
    $modulePlanDispatch | Where-Object {
        -not [bool](Get-VibePropertySafe -InputObject $_ -PropertyName 'must_preserve_workflow' -DefaultValue $false) -or
        [string]::IsNullOrWhiteSpace([string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_entrypoint' -DefaultValue '')) -or
        [string]::IsNullOrWhiteSpace([string](Get-VibePropertySafe -InputObject $_ -PropertyName 'skill_root' -DefaultValue ''))
    } | ForEach-Object { [string]$_.skill_id } | Sort-Object -Unique
)
$moduleWorkUnitCount = @($moduleWorkPlan.work_units).Count
$assignedSkillUnitCount = @($assignedSkillUnits).Count
$dispatchIntegrity = [pscustomobject]@{
    planned_skill_ids = @($modulePlanSkillIds)
    handed_off_skill_ids = @($assignedSkillIds)
    planned_units_fully_handed_off = [bool](@($agentExecutionHandoff.units).Count -eq $moduleWorkUnitCount)
    handed_off_skills_match_plan = [bool](($assignedSkillIds -join "`n") -ceq ($modulePlanSkillIds -join "`n"))
    module_contract_complete_for_approved_dispatch = [bool](@($dispatchContractIncompleteSkillIds).Count -eq 0)
    dispatch_contract_incomplete_skill_ids = @($dispatchContractIncompleteSkillIds)
}
$dispatchIntegrity | Add-Member -NotePropertyName 'proof_passed' -NotePropertyValue ([bool](
    $dispatchIntegrity.planned_units_fully_handed_off -and
    $dispatchIntegrity.handed_off_skills_match_plan -and
    $dispatchIntegrity.module_contract_complete_for_approved_dispatch
))
if (-not [bool]$dispatchIntegrity.proof_passed) {
    throw 'Agent execution handoff does not match the approved module work plan'
}

$runtimePacketHostAdapterIdentity = Get-VibeRuntimePacketHostAdapterAlignment -RuntimeInputPacket $runtimeInputPacket
$hierarchyProjection = New-VibeHierarchyProjection -HierarchyState $hierarchyState -IncludeGovernanceScope
$authorityProjection = New-VibeExecutionAuthorityProjection -HierarchyState $hierarchyState
$moduleHandoff = [pscustomobject]@{
    status = 'agent_action_required'
    control_owner = 'agent'
    workflow_level = [string]$moduleWorkPlan.workflow_level
    module_work_unit_count = [int]$moduleWorkUnitCount
    assigned_skill_unit_count = [int]$assignedSkillUnitCount
    assigned_skill_ids = @($assignedSkillIds)
    work_units = [object[]]@($agentExecutionHandoff.units)
    waves = [object[]]@($agentExecutionHandoff.waves)
    requested_host_adapter_id = $runtimePacketHostAdapterIdentity.requested_host_id
    effective_host_adapter_id = $runtimePacketHostAdapterIdentity.effective_host_id
}
$executionManifest = [pscustomobject]@{
    stage = 'plan_execute'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    internal_grade = $grade
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    module_work_plan_path = $moduleWorkPlanPath
    runtime_input_packet_path = $runtimeInputPath
    execution_memory_context_path = if ([string]::IsNullOrWhiteSpace($ExecutionMemoryContextPath)) { $null } else { $ExecutionMemoryContextPath }
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    hierarchy = $hierarchyProjection
    authority = $authorityProjection
    module_handoff = $moduleHandoff
    dispatch_integrity = $dispatchIntegrity
    status = 'agent_action_required'
}
$executionManifestPath = Join-Path $sessionRoot 'execution-manifest.json'
Write-VibeJsonArtifact -Path $executionManifestPath -Value $executionManifest

$receipt = [pscustomobject]@{
    stage = 'plan_execute'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    internal_grade = $grade
    status = 'agent_action_required'
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    module_work_plan_path = $moduleWorkPlanPath
    runtime_input_packet_path = $runtimeInputPath
    execution_memory_context_path = if ([string]::IsNullOrWhiteSpace($ExecutionMemoryContextPath)) { $null } else { $ExecutionMemoryContextPath }
    execution_manifest_path = $executionManifestPath
    agent_execution_handoff_path = $agentExecutionHandoffPath
    agent_execution_handoff = $agentExecutionHandoff
    module_execution_path = $moduleExecutionTargetPath
    module_work_unit_count = [int]$moduleWorkUnitCount
    assigned_skill_unit_count = [int]$assignedSkillUnitCount
    assigned_skill_ids = @($assignedSkillIds)
    dispatch_integrity_proof_passed = $true
    dispatch_integrity = $dispatchIntegrity
    completion_claim_allowed = [bool]$authorityProjection.completion_claim_allowed
    verification_contract = @(
        'The current Agent must read each assigned SKILL.md before doing that module work.',
        'The current Agent must return one complete module-execution.json through canonical vibe re-entry.',
        'No completion claim is allowed before required modules reach completed, failed, or blocked.',
        'Child-governed lanes may not issue final completion claims or mutate canonical requirement or plan truth.'
    )
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$receiptPath = Join-Path $sessionRoot 'phase-execute.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    receipt_path = $receiptPath
    execution_manifest_path = $executionManifestPath
    agent_execution_handoff_path = $agentExecutionHandoffPath
    agent_execution_handoff = $agentExecutionHandoff
    module_execution_path = $moduleExecutionTargetPath
    receipt = $receipt
}
