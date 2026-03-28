param(
    [Parameter(Mandatory)] [string]$Task,
    [ValidateSet('interactive_governed', 'benchmark_autonomous')] [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
    [string[]]$ApprovedSpecialistSkillIds = @(),
    [switch]$ExecuteGovernanceCleanup,
    [switch]$ApplyManagedNodeCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')

function Wait-VibeArtifactSet {
    param(
        [Parameter(Mandatory)] [string[]]$Paths,
        [int]$TimeoutSeconds = 5,
        [int]$PollMilliseconds = 100
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $missing = @($Paths | Where-Object { -not (Test-Path -LiteralPath $_) })
        if ($missing.Count -eq 0) {
            return [pscustomobject]@{
                ready = $true
                missing = @()
            }
        }

        Start-Sleep -Milliseconds $PollMilliseconds
    } while ((Get-Date) -lt $deadline)

    return [pscustomobject]@{
        ready = $false
        missing = @($Paths | Where-Object { -not (Test-Path -LiteralPath $_) })
    }
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

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}
$artifactBaseRoot = Get-VibeArtifactRoot -RepoRoot $runtime.repo_root -ArtifactRoot $ArtifactRoot
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $GovernanceScope `
    -RunId $RunId `
    -RootRunId $RootRunId `
    -ParentRunId $ParentRunId `
    -ParentUnitId $ParentUnitId `
    -InheritedRequirementDocPath $InheritedRequirementDocPath `
    -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract

$hierarchyArgs = @{
    GovernanceScope = [string]$hierarchyState.governance_scope
}
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.root_run_id)) {
    $hierarchyArgs.RootRunId = [string]$hierarchyState.root_run_id
}
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.parent_run_id)) {
    $hierarchyArgs.ParentRunId = [string]$hierarchyState.parent_run_id
}
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.parent_unit_id)) {
    $hierarchyArgs.ParentUnitId = [string]$hierarchyState.parent_unit_id
}
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.inherited_requirement_doc_path)) {
    $hierarchyArgs.InheritedRequirementDocPath = [string]$hierarchyState.inherited_requirement_doc_path
}
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.inherited_execution_plan_path)) {
    $hierarchyArgs.InheritedExecutionPlanPath = [string]$hierarchyState.inherited_execution_plan_path
}

$skeleton = & (Join-Path $PSScriptRoot 'Invoke-SkeletonCheck.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$freezeArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    ArtifactRoot = $ArtifactRoot
    ApprovedSpecialistSkillIds = $ApprovedSpecialistSkillIds
}
foreach ($key in @($hierarchyArgs.Keys)) {
    $freezeArgs[$key] = $hierarchyArgs[$key]
}
$runtimeInput = & (Join-Path $PSScriptRoot 'Freeze-RuntimeInputPacket.ps1') @freezeArgs
$interview = & (Join-Path $PSScriptRoot 'Invoke-DeepInterview.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$requirementArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    IntentContractPath = $interview.receipt_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    ArtifactRoot = $ArtifactRoot
}
foreach ($key in @($hierarchyArgs.Keys)) {
    $requirementArgs[$key] = $hierarchyArgs[$key]
}
$requirement = & (Join-Path $PSScriptRoot 'Write-RequirementDoc.ps1') @requirementArgs
$planArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    RequirementDocPath = $requirement.requirement_doc_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    ArtifactRoot = $ArtifactRoot
}
foreach ($key in @($hierarchyArgs.Keys)) {
    $planArgs[$key] = $hierarchyArgs[$key]
}
$planArgs.InheritedRequirementDocPath = $requirement.requirement_doc_path
$plan = & (Join-Path $PSScriptRoot 'Write-XlPlan.ps1') @planArgs
$executeArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    RequirementDocPath = $requirement.requirement_doc_path
    ExecutionPlanPath = $plan.execution_plan_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    ArtifactRoot = $ArtifactRoot
}
foreach ($key in @('GovernanceScope', 'RootRunId', 'ParentRunId', 'ParentUnitId')) {
    if ($hierarchyArgs.ContainsKey($key)) {
        $executeArgs[$key] = $hierarchyArgs[$key]
    }
}
$execute = & (Join-Path $PSScriptRoot 'Invoke-PlanExecute.ps1') @executeArgs
$cleanup = & (Join-Path $PSScriptRoot 'Invoke-PhaseCleanup.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot -ExecuteGovernanceCleanup:$ExecuteGovernanceCleanup -ApplyManagedNodeCleanup:$ApplyManagedNodeCleanup
$deliveryAcceptanceReportPath = Join-Path $skeleton.session_root 'delivery-acceptance-report.json'
$deliveryAcceptanceMarkdownPath = Join-Path $skeleton.session_root 'delivery-acceptance-report.md'

$artifactReadiness = Wait-VibeArtifactSet -Paths @(
    [string]$skeleton.receipt_path,
    [string]$runtimeInput.packet_path,
    [string]$interview.receipt_path,
    [string]$requirement.requirement_doc_path,
    [string]$requirement.receipt_path,
    [string]$plan.execution_plan_path,
    [string]$plan.receipt_path,
    [string]$execute.receipt_path,
    [string]$execute.execution_manifest_path,
    [string]$execute.execution_topology_path,
    [string]$execute.benchmark_proof_manifest_path,
    [string]$cleanup.receipt_path,
    [string]$deliveryAcceptanceReportPath
)

if (-not $artifactReadiness.ready) {
    throw ("Governed runtime returned before critical artifacts were durable. Missing: {0}" -f (@($artifactReadiness.missing) -join ', '))
}

$relativeArtifacts = [ordered]@{
    skeleton_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$skeleton.receipt_path)
    runtime_input_packet = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$runtimeInput.packet_path)
    intent_contract = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$interview.receipt_path)
    requirement_doc = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$requirement.requirement_doc_path)
    requirement_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$requirement.receipt_path)
    execution_plan = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$plan.execution_plan_path)
    execution_plan_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$plan.receipt_path)
    execute_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$execute.receipt_path)
    execution_manifest = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$execute.execution_manifest_path)
    execution_topology = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$execute.execution_topology_path)
    benchmark_proof_manifest = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$execute.benchmark_proof_manifest_path)
    cleanup_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$cleanup.receipt_path)
    delivery_acceptance_report = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$deliveryAcceptanceReportPath)
    delivery_acceptance_markdown = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$deliveryAcceptanceMarkdownPath)
}

$deliveryAcceptanceReport = if (Test-Path -LiteralPath $deliveryAcceptanceReportPath) {
    Get-Content -LiteralPath $deliveryAcceptanceReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}

$summary = [pscustomobject]@{
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    task = $Task
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    artifact_root = $artifactBaseRoot
    session_root = $skeleton.session_root
    session_root_relative = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$skeleton.session_root)
    hierarchy = [pscustomobject]@{
        root_run_id = [string]$hierarchyState.root_run_id
        parent_run_id = if ($null -eq $hierarchyState.parent_run_id) { $null } else { [string]$hierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $hierarchyState.parent_unit_id) { $null } else { [string]$hierarchyState.parent_unit_id }
        inherited_requirement_doc_path = if ($null -eq $hierarchyState.inherited_requirement_doc_path) { $null } else { [string]$hierarchyState.inherited_requirement_doc_path }
        inherited_execution_plan_path = if ($null -eq $hierarchyState.inherited_execution_plan_path) { $null } else { [string]$hierarchyState.inherited_execution_plan_path }
    }
    stage_order = @(
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup'
    )
    artifacts = [pscustomobject]@{
        skeleton_receipt = $skeleton.receipt_path
        runtime_input_packet = $runtimeInput.packet_path
        intent_contract = $interview.receipt_path
        requirement_doc = $requirement.requirement_doc_path
        requirement_receipt = $requirement.receipt_path
        execution_plan = $plan.execution_plan_path
        execution_plan_receipt = $plan.receipt_path
        execute_receipt = $execute.receipt_path
        execution_manifest = $execute.execution_manifest_path
        execution_topology = $execute.execution_topology_path
        benchmark_proof_manifest = $execute.benchmark_proof_manifest_path
        cleanup_receipt = $cleanup.receipt_path
        delivery_acceptance_report = $deliveryAcceptanceReportPath
        delivery_acceptance_markdown = $deliveryAcceptanceMarkdownPath
    }
    delivery_acceptance = if ($deliveryAcceptanceReport) {
        [pscustomobject]@{
            gate_result = [string]$deliveryAcceptanceReport.summary.gate_result
            completion_language_allowed = [bool]$deliveryAcceptanceReport.summary.completion_language_allowed
            readiness_state = [string]$deliveryAcceptanceReport.summary.readiness_state
            manual_review_layer_count = [int]$deliveryAcceptanceReport.summary.manual_review_layer_count
            failing_layer_count = [int]$deliveryAcceptanceReport.summary.failing_layer_count
        }
    } else {
        $null
    }
    artifacts_relative = [pscustomobject]$relativeArtifacts
}

$summaryPath = Join-Path $skeleton.session_root 'runtime-summary.json'
Write-VibeJsonArtifact -Path $summaryPath -Value $summary

[pscustomobject]@{
    run_id = $RunId
    mode = $Mode
    session_root = $skeleton.session_root
    summary_path = $summaryPath
    summary = $summary
}
