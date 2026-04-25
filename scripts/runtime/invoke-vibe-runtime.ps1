param(
    [Parameter(Mandatory)] [string]$Task,
    [ValidateSet('interactive_governed')] [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$EntryIntentId = '',
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$HostDecisionJson = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = '',
    [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
    [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
    [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
    [string[]]$ApprovedSpecialistSkillIds = @(),
    [switch]$ExecuteGovernanceCleanup,
    [switch]$ApplyManagedNodeCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure consistent UTF-8 encoding for Unicode path compatibility (e.g., Chinese username paths)
if ($PSVersionTable.PSEdition -eq 'Desktop' -or $PSVersionTable.Platform -eq 'Win32NT') {
    # Windows PowerShell 5.x: set console encoding to UTF-8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} else {
    # PowerShell Core 7+: already defaults to UTF-8, but ensure consistency
    $OutputEncoding = [System.Text.Encoding]::UTF8
}

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeConsultation.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeMemoryBackends.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeMemoryActivation.Common.ps1')

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

function Complete-VibeGovernedRuntimeStop {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$ArtifactBaseRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [object]$StorageProjection,
        [Parameter(Mandatory)] [object]$Skeleton,
        [Parameter(Mandatory)] [object]$RuntimeInput,
        [Parameter(Mandatory)] [object]$GovernanceCapsule,
        [Parameter(Mandatory)] [object]$StageLineage,
        [AllowNull()] [object]$Interview = $null,
        [AllowNull()] [object]$Requirement = $null,
        [AllowNull()] [object]$Plan = $null,
        [AllowNull()] [object]$Execute = $null,
        [AllowNull()] [object]$Cleanup = $null,
        [AllowNull()] [object]$DiscussionConsultation = $null,
        [AllowNull()] [object]$PlanningConsultation = $null,
        [AllowNull()] [object]$HostStageDisclosure = $null,
        [AllowEmptyString()] [string]$HostStageDisclosurePath = '',
        [AllowNull()] [object]$HostUserBriefing = $null,
        [AllowEmptyString()] [string]$HostUserBriefingPath = '',
        [AllowNull()] [object]$BoundedReturnControl = $null,
        [AllowNull()] [object]$MemoryActivationReport = $null,
        [AllowEmptyString()] [string]$MemoryActivationReportPath = '',
        [AllowEmptyString()] [string]$MemoryActivationMarkdownPath = '',
        [AllowNull()] [object]$DeliveryAcceptanceReport = $null,
        [AllowEmptyString()] [string]$DeliveryAcceptanceReportPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceMarkdownPath = '',
        [AllowNull()] [object]$ExecutionManifestDocument = $null,
        [AllowNull()] [object]$SpecialistLifecycleDisclosure = $null,
        [AllowEmptyString()] [string]$SpecialistLifecycleDisclosurePath = '',
        [AllowNull()] [object]$DelegationValidation = $null
    )

    $interviewReceiptPath = if (
        $Interview -and
        $Interview.PSObject.Properties.Name -contains 'receipt_path' -and
        -not [string]::IsNullOrWhiteSpace([string]$Interview.receipt_path)
    ) {
        [string]$Interview.receipt_path
    } else {
        ''
    }
    $requirementDocPath = if (
        $Requirement -and
        $Requirement.PSObject.Properties.Name -contains 'requirement_doc_path' -and
        -not [string]::IsNullOrWhiteSpace([string]$Requirement.requirement_doc_path)
    ) {
        [string]$Requirement.requirement_doc_path
    } else {
        ''
    }
    $requirementReceiptPath = if (
        $Requirement -and
        $Requirement.PSObject.Properties.Name -contains 'receipt_path' -and
        -not [string]::IsNullOrWhiteSpace([string]$Requirement.receipt_path)
    ) {
        [string]$Requirement.receipt_path
    } else {
        ''
    }

    $criticalArtifactPaths = @(
        [string]$Skeleton.receipt_path,
        [string]$RuntimeInput.packet_path,
        [string]$GovernanceCapsule.path,
        [string]$StageLineage.path,
        $interviewReceiptPath,
        $requirementDocPath,
        $requirementReceiptPath,
        $(if ($Plan) { [string]$Plan.execution_plan_path } else { '' }),
        $(if ($Plan) { [string]$Plan.receipt_path } else { '' }),
        $(if ($Execute) { [string]$Execute.receipt_path } else { '' }),
        $(if ($Execute) { [string]$Execute.execution_manifest_path } else { '' }),
        $(if ($Execute) { [string]$Execute.execution_topology_path } else { '' }),
        $(if ($Execute) { [string]$Execute.execution_proof_manifest_path } else { '' }),
        $(if ($DiscussionConsultation) { [string]$DiscussionConsultation.receipt_path } else { '' }),
        $(if ($PlanningConsultation) { [string]$PlanningConsultation.receipt_path } else { '' }),
        [string]$SpecialistLifecycleDisclosurePath,
        $(if ($Cleanup) { [string]$Cleanup.receipt_path } else { '' }),
        [string]$DeliveryAcceptanceReportPath,
        [string]$MemoryActivationReportPath,
        [string]$MemoryActivationMarkdownPath
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }

    if ($HostStageDisclosure) {
        $criticalArtifactPaths += [string]$HostStageDisclosurePath
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$HostUserBriefingPath)) {
        $criticalArtifactPaths += [string]$HostUserBriefingPath
    }
    if ($DelegationValidation) {
        $criticalArtifactPaths += [string]$DelegationValidation.receipt_path
    }

    $artifactReadiness = Wait-VibeArtifactSet -Paths $criticalArtifactPaths
    if (-not $artifactReadiness.ready) {
        throw ("Governed runtime returned before critical artifacts were durable. Missing: {0}" -f (@($artifactReadiness.missing) -join ', '))
    }

    $delegationValidationReceiptPath = if ($DelegationValidation) { [string]$DelegationValidation.receipt_path } else { '' }
    $summaryArtifacts = New-VibeRuntimeSummaryArtifactProjection `
        -SkeletonReceiptPath ([string]$Skeleton.receipt_path) `
        -RuntimeInputPacketPath ([string]$RuntimeInput.packet_path) `
        -GovernanceCapsulePath ([string]$GovernanceCapsule.path) `
        -StageLineagePath ([string]$StageLineage.path) `
        -IntentContractPath $interviewReceiptPath `
        -RequirementDocPath $requirementDocPath `
        -RequirementReceiptPath $requirementReceiptPath `
        -ExecutionPlanPath $(if ($Plan) { [string]$Plan.execution_plan_path } else { '' }) `
        -ExecutionPlanReceiptPath $(if ($Plan) { [string]$Plan.receipt_path } else { '' }) `
        -ExecuteReceiptPath $(if ($Execute) { [string]$Execute.receipt_path } else { '' }) `
        -ExecutionManifestPath $(if ($Execute) { [string]$Execute.execution_manifest_path } else { '' }) `
        -ExecutionTopologyPath $(if ($Execute) { [string]$Execute.execution_topology_path } else { '' }) `
        -ExecutionProofManifestPath $(if ($Execute) { [string]$Execute.execution_proof_manifest_path } else { '' }) `
        -DiscussionSpecialistConsultationPath $(if ($DiscussionConsultation) { [string]$DiscussionConsultation.receipt_path } else { '' }) `
        -PlanningSpecialistConsultationPath $(if ($PlanningConsultation) { [string]$PlanningConsultation.receipt_path } else { '' }) `
        -SpecialistLifecycleDisclosurePath ([string]$SpecialistLifecycleDisclosurePath) `
        -HostStageDisclosurePath $(if ($HostStageDisclosure) { [string]$HostStageDisclosurePath } else { '' }) `
        -HostUserBriefingPath ([string]$HostUserBriefingPath) `
        -CleanupReceiptPath $(if ($Cleanup) { [string]$Cleanup.receipt_path } else { '' }) `
        -DeliveryAcceptanceReportPath ([string]$DeliveryAcceptanceReportPath) `
        -DeliveryAcceptanceMarkdownPath ([string]$DeliveryAcceptanceMarkdownPath) `
        -MemoryActivationReportPath ([string]$MemoryActivationReportPath) `
        -MemoryActivationMarkdownPath ([string]$MemoryActivationMarkdownPath) `
        -DelegationEnvelopePath ([string]$HierarchyState.delegation_envelope_path) `
        -DelegationValidationReceiptPath $delegationValidationReceiptPath
    $relativeArtifacts = New-VibeRuntimeSummaryRelativeArtifactProjection -BasePath $ArtifactBaseRoot -Artifacts $summaryArtifacts

    $summary = New-VibeRuntimeSummaryProjection `
        -RunId $RunId `
        -Mode $Mode `
        -Task $Task `
        -ArtifactRoot $ArtifactBaseRoot `
        -SessionRoot $SessionRoot `
        -HierarchyState $HierarchyState `
        -Artifacts $summaryArtifacts `
        -RelativeArtifacts $relativeArtifacts `
        -StageLineage $StageLineage `
        -StorageProjection $StorageProjection `
        -MemoryActivationReport $MemoryActivationReport `
        -DeliveryAcceptanceReport $DeliveryAcceptanceReport `
        -SpecialistDecision $(if ($ExecutionManifestDocument -and $ExecutionManifestDocument.PSObject.Properties.Name -contains 'specialist_decision' -and $null -ne $ExecutionManifestDocument.specialist_decision) { $ExecutionManifestDocument.specialist_decision } elseif ($Execute -and $Execute.receipt -and $Execute.receipt.PSObject.Properties.Name -contains 'specialist_decision' -and $null -ne $Execute.receipt.specialist_decision) { $Execute.receipt.specialist_decision } else { $null }) `
        -SpecialistUserDisclosure $(if ($Execute -and $Execute.receipt -and $Execute.receipt.PSObject.Properties.Name -contains 'specialist_user_disclosure') { $Execute.receipt.specialist_user_disclosure } else { $null }) `
        -SpecialistConsultation (New-VibeSpecialistConsultationRuntimeProjection -Receipts @($(if ($DiscussionConsultation) { $DiscussionConsultation.receipt } else { $null }), $(if ($PlanningConsultation) { $PlanningConsultation.receipt } else { $null }))) `
        -SpecialistLifecycleDisclosure $SpecialistLifecycleDisclosure `
        -HostStageDisclosure $HostStageDisclosure `
        -HostUserBriefing $HostUserBriefing `
        -BoundedReturnControl $BoundedReturnControl

    $summaryPath = Join-Path $SessionRoot 'runtime-summary.json'
    Write-VibeJsonArtifact -Path $summaryPath -Value $summary

    return [pscustomobject]@{
        run_id = $RunId
        mode = $Mode
        session_root = $SessionRoot
        summary_path = $summaryPath
        host_stage_disclosure_path = if ($HostStageDisclosure) { [string]$HostStageDisclosurePath } else { $null }
        host_stage_disclosure = $HostStageDisclosure
        host_user_briefing_path = $HostUserBriefingPath
        host_user_briefing = $HostUserBriefing
        summary = $summary
    }
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}
$hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $HostDecisionJson
$hostContinuationContext = Get-VibeHostContinuationContext -HostDecision $hostDecision
$structuredBoundedReentry = Test-VibeStructuredBoundedReentryContext -ContinuationContext $hostContinuationContext
$artifactBaseRoot = Get-VibeArtifactRoot -RepoRoot $runtime.repo_root -Runtime $runtime -ArtifactRoot $ArtifactRoot
$storageProjection = New-VibeWorkspaceArtifactProjection `
    -RepoRoot $runtime.repo_root `
    -Runtime $runtime `
    -ArtifactRoot $ArtifactRoot `
    -RouterTargetRoot (Resolve-VgoTargetRoot -HostId (Resolve-VgoHostId -HostId $env:VCO_HOST_ID))
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
if (-not [string]::IsNullOrWhiteSpace([string]$hierarchyState.delegation_envelope_path)) {
    $hierarchyArgs.DelegationEnvelopePath = [string]$hierarchyState.delegation_envelope_path
}

$skeleton = & (Join-Path $PSScriptRoot 'Invoke-SkeletonCheck.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$governanceCapsule = Write-VibeGovernanceCapsule `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'skeleton_check' `
    -CurrentReceiptPath ([string]$skeleton.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
$delegationValidation = $null
if ([string]$hierarchyState.governance_scope -eq 'child') {
    $delegationValidation = Assert-VibeDelegationEnvelope `
        -SessionRoot ([string]$skeleton.session_root) `
        -EnvelopePath ([string]$hierarchyState.delegation_envelope_path) `
        -HierarchyState $hierarchyState `
        -ExpectedChildRunId $RunId `
        -ExpectedParentRunId ([string]$hierarchyState.parent_run_id) `
        -ExpectedParentUnitId ([string]$hierarchyState.parent_unit_id) `
        -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
}
$memorySkeletonDigest = New-VibeSkeletonMemoryDigest -Runtime $runtime -Skeleton $skeleton -Task $Task -SessionRoot ([string]$skeleton.session_root)
$memorySkeletonCognee = $null
$skeletonMemoryReads = @($memorySkeletonDigest)
if (-not $structuredBoundedReentry) {
    $memorySkeletonCognee = Get-VibeCogneeReadAction -Runtime $runtime -Stage 'skeleton_check' -Task $Task -SessionRoot ([string]$skeleton.session_root)
    $skeletonMemoryReads = @($memorySkeletonDigest, $memorySkeletonCognee)
}
$freezeArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    ArtifactRoot = $ArtifactRoot
    EntryIntentId = $EntryIntentId
    RequestedStageStop = $RequestedStageStop
    RequestedGradeFloor = $RequestedGradeFloor
    HostDecisionJson = $HostDecisionJson
    ApprovedSpecialistSkillIds = $ApprovedSpecialistSkillIds
}
foreach ($key in @($hierarchyArgs.Keys)) {
    $freezeArgs[$key] = $hierarchyArgs[$key]
}
$runtimeInput = & (Join-Path $PSScriptRoot 'Freeze-RuntimeInputPacket.ps1') @freezeArgs
$runtimeInputPacket = if ($runtimeInput -and $runtimeInput.PSObject.Properties.Name -contains 'packet' -and $null -ne $runtimeInput.packet) {
    $runtimeInput.packet
} else {
    $null
}
$routeResult = if ($runtimeInput -and $runtimeInput.PSObject.Properties.Name -contains 'route_result' -and $null -ne $runtimeInput.route_result) {
    $runtimeInput.route_result
} else {
    $null
}
$requestedStop = Resolve-VibeRequestedStageStop -RequestedStageStop $(if ($runtimeInputPacket) { [string]$runtimeInputPacket.requested_stage_stop } else { '' })
$discussionRoutingLayer = New-VibeSpecialistRoutingLifecycleLayerProjection -RuntimeInputPacket $runtimeInputPacket
if ($discussionRoutingLayer) {
    $discussionRoutingSegment = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $discussionRoutingLayer
    $discussionRoutingEvent = New-VibeHostStageDisclosureEventProjection -Segment $discussionRoutingSegment
    Add-VibeHostStageDisclosureEvent -SessionRoot ([string]$skeleton.session_root) -DisclosureEvent $discussionRoutingEvent | Out-Null
}
$confirmRequired = [bool](Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('route_snapshot', 'confirm_required') -DefaultValue $false)
if ($confirmRequired) {
    $confirmUi = if ($routeResult -and $routeResult.PSObject.Properties.Name -contains 'confirm_ui' -and $null -ne $routeResult.confirm_ui) {
        $routeResult.confirm_ui
    } else {
        $null
    }
    $confirmRenderedText = if (
        $confirmUi -and
        $confirmUi.PSObject.Properties.Name -contains 'rendered_text' -and
        -not [string]::IsNullOrWhiteSpace([string]$confirmUi.rendered_text)
    ) {
        [string]$confirmUi.rendered_text
    } else {
        @(
            'Routing requires confirmation before governed execution can continue.',
            ('- route_mode: `{0}`' -f $(Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('route_snapshot', 'route_mode') -DefaultValue 'confirm_required')),
            ('- selected_skill: `{0}`' -f $(Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('route_snapshot', 'selected_skill') -DefaultValue 'unknown')),
            'Reply with the missing clarifications or confirm the routed skill choice, then re-enter canonical `vibe` through the same host surface.'
        ) -join "`n"
    }
    $confirmSkills = if ($confirmUi -and $confirmUi.PSObject.Properties.Name -contains 'options' -and $null -ne $confirmUi.options) {
        @($confirmUi.options | ForEach-Object {
            [pscustomobject]@{
                skill_id = if ($_.PSObject.Properties.Name -contains 'skill') { [string]$_.skill } else { $null }
                description = if ($_.PSObject.Properties.Name -contains 'description') { [string]$_.description } else { $null }
                score = if ($_.PSObject.Properties.Name -contains 'score') { $_.score } else { $null }
                source = 'confirm_ui'
            }
        })
    } else {
        @($runtimeInputPacket.specialist_recommendations | ForEach-Object {
            [pscustomobject]@{
                skill_id = if ($_.PSObject.Properties.Name -contains 'skill_id') { [string]$_.skill_id } else { $null }
                description = if ($_.PSObject.Properties.Name -contains 'rationale') { [string]$_.rationale } else { $null }
                score = $null
                source = 'specialist_recommendation'
            }
        })
    }
    $confirmDisclosureEvent = [pscustomobject]@{
        event_id = 'routing_confirmation_required'
        segment_id = 'routing_confirmation'
        stage = 'skeleton_check'
        category = 'routing'
        truth_layer = 'route_selection'
        status = 'confirm_required'
        gate_status = 'confirm_required'
        skill_count = @($confirmSkills).Count
        skills = @($confirmSkills)
        rendered_text = $confirmRenderedText
    }
    Add-VibeHostStageDisclosureEvent -SessionRoot ([string]$skeleton.session_root) -DisclosureEvent $confirmDisclosureEvent | Out-Null
    $hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
    $hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
        Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $hostUserBriefing = [pscustomobject]@{
        stage = 'skeleton_check'
        route_mode = 'confirm_required'
        selected_skill = Get-VibeNestedPropertySafe -InputObject $runtimeInputPacket -PropertyPath @('route_snapshot', 'selected_skill') -DefaultValue $null
        clarification_questions = if ($confirmUi -and $confirmUi.PSObject.Properties.Name -contains 'clarification_questions') { @($confirmUi.clarification_questions) } else { @() }
        options = if ($confirmUi -and $confirmUi.PSObject.Properties.Name -contains 'options') { @($confirmUi.options) } else { @() }
        route_decision_contract = if ($confirmUi -and $confirmUi.PSObject.Properties.Name -contains 'route_decision_contract') { $confirmUi.route_decision_contract } else { $null }
        rendered_text = $confirmRenderedText
    }
    $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot ([string]$skeleton.session_root)
    Write-VgoUtf8NoBomText -Path $hostUserBriefingPath -Content ($confirmRenderedText + [Environment]::NewLine)

    return Complete-VibeGovernedRuntimeStop `
        -RunId $RunId `
        -Mode $Mode `
        -Task $Task `
        -ArtifactBaseRoot $artifactBaseRoot `
        -SessionRoot ([string]$skeleton.session_root) `
        -HierarchyState $hierarchyState `
        -StorageProjection $storageProjection `
        -Skeleton $skeleton `
        -RuntimeInput $runtimeInput `
        -GovernanceCapsule $governanceCapsule `
        -StageLineage $stageLineage `
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -HostUserBriefing $hostUserBriefing `
        -HostUserBriefingPath $hostUserBriefingPath `
        -DelegationValidation $delegationValidation
}
$interview = & (Join-Path $PSScriptRoot 'Invoke-DeepInterview.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'deep_interview' `
    -PreviousStageName 'skeleton_check' `
    -PreviousStageReceiptPath ([string]$skeleton.receipt_path) `
    -CurrentReceiptPath ([string]$interview.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
$memoryDeepInterviewRead = $null
$deepInterviewMemoryReads = @()
$requirementContextReads = @($memorySkeletonDigest)
if (-not $structuredBoundedReentry) {
    $memoryDeepInterviewRead = Get-VibeDeepInterviewMemoryReadAction -Runtime $runtime -Task $Task -SessionRoot ([string]$skeleton.session_root)
    $deepInterviewMemoryReads = @($memoryDeepInterviewRead)
    $requirementContextReads = @($memoryDeepInterviewRead, $memorySkeletonCognee, $memorySkeletonDigest)
}
$requirementMemoryContext = New-VibeRequirementContextPack -Runtime $runtime -ReadActions $requirementContextReads -SessionRoot ([string]$skeleton.session_root)
$discussionConsultation = Invoke-VibeSpecialistConsultationWindow `
    -Task $Task `
    -RunId $RunId `
    -SessionRoot ([string]$skeleton.session_root) `
    -RepoRoot ([string]$runtime.repo_root) `
    -WindowId 'discussion' `
    -Stage 'deep_interview' `
    -SourceArtifactPath ([string]$interview.receipt_path) `
    -Recommendations @($(if ($runtimeInputPacket) { $runtimeInputPacket.specialist_recommendations } else { @() })) `
    -Policy $runtime.specialist_consultation_policy
$discussionConsultationLayer = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $discussionConsultation.receipt
if ($discussionConsultationLayer) {
    $discussionConsultationSegment = New-VibeHostUserBriefingSegmentProjection `
        -LifecycleLayer $discussionConsultationLayer `
        -ConsultationReceipt $discussionConsultation.receipt
    $discussionConsultationEvent = New-VibeHostStageDisclosureEventProjection -Segment $discussionConsultationSegment
    Add-VibeHostStageDisclosureEvent -SessionRoot ([string]$skeleton.session_root) -DisclosureEvent $discussionConsultationEvent | Out-Null
}
$requirementArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    IntentContractPath = $interview.receipt_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    MemoryContextPath = $requirementMemoryContext.context_path
    DiscussionConsultationPath = $discussionConsultation.receipt_path
    ArtifactRoot = $ArtifactRoot
}
foreach ($key in @($hierarchyArgs.Keys)) {
    $requirementArgs[$key] = $hierarchyArgs[$key]
}
$requirement = & (Join-Path $PSScriptRoot 'Write-RequirementDoc.ps1') @requirementArgs
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'requirement_doc' `
    -PreviousStageName 'deep_interview' `
    -PreviousStageReceiptPath ([string]$interview.receipt_path) `
    -CurrentReceiptPath ([string]$requirement.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
if ($requestedStop -eq 'requirement_doc') {
    $hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
    $hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
        Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $boundedReturnControl = New-VibeBoundedReturnControlProjection `
        -RepoRoot ([string]$runtime.repo_root) `
        -RunId $RunId `
        -EntryIntentId $EntryIntentId `
        -StageLineage $stageLineage
    $hostUserBriefing = New-VibeHostUserBriefingProjection -BoundedReturnControl $boundedReturnControl
    $hostUserBriefingPath = ''
    if ($hostUserBriefing) {
        $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot ([string]$skeleton.session_root)
        Write-VgoUtf8NoBomText -Path $hostUserBriefingPath -Content (([string]$hostUserBriefing.rendered_text) + [Environment]::NewLine)
    }

    return Complete-VibeGovernedRuntimeStop `
        -RunId $RunId `
        -Mode $Mode `
        -Task $Task `
        -ArtifactBaseRoot $artifactBaseRoot `
        -SessionRoot ([string]$skeleton.session_root) `
        -HierarchyState $hierarchyState `
        -StorageProjection $storageProjection `
        -Skeleton $skeleton `
        -RuntimeInput $runtimeInput `
        -GovernanceCapsule $governanceCapsule `
        -StageLineage $stageLineage `
        -Interview $interview `
        -Requirement $requirement `
        -DiscussionConsultation $discussionConsultation `
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -HostUserBriefing $hostUserBriefing `
        -HostUserBriefingPath $hostUserBriefingPath `
        -BoundedReturnControl $boundedReturnControl `
        -DelegationValidation $delegationValidation
}
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
$memoryPlanSerena = $null
$memoryPlanCognee = $null
$xlPlanReadActions = @()
if (-not $structuredBoundedReentry) {
    $memoryPlanSerena = Get-VibeSerenaReadAction -Runtime $runtime -Stage 'xl_plan' -Task $Task -SessionRoot ([string]$skeleton.session_root)
    $memoryPlanCognee = Get-VibeCogneeReadAction -Runtime $runtime -Stage 'xl_plan' -Task $Task -SessionRoot ([string]$skeleton.session_root)
    $xlPlanReadActions = @($memoryPlanSerena, $memoryPlanCognee)
}
$planMemoryContext = New-VibePlanMemoryContextPack -Runtime $runtime -ReadActions $xlPlanReadActions -SessionRoot ([string]$skeleton.session_root) -Stage 'xl_plan' -ArtifactName 'plan-context-pack.json'
$planningConsultation = Invoke-VibeSpecialistConsultationWindow `
    -Task $Task `
    -RunId $RunId `
    -SessionRoot ([string]$skeleton.session_root) `
    -RepoRoot ([string]$runtime.repo_root) `
    -WindowId 'planning' `
    -Stage 'requirement_doc' `
    -SourceArtifactPath ([string]$requirement.requirement_doc_path) `
    -Recommendations @($(if ($runtimeInputPacket) { $runtimeInputPacket.specialist_recommendations } else { @() })) `
    -Policy $runtime.specialist_consultation_policy
$planningConsultationLayer = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $planningConsultation.receipt
if ($planningConsultationLayer) {
    $planningConsultationSegment = New-VibeHostUserBriefingSegmentProjection `
        -LifecycleLayer $planningConsultationLayer `
        -ConsultationReceipt $planningConsultation.receipt
    $planningConsultationEvent = New-VibeHostStageDisclosureEventProjection -Segment $planningConsultationSegment
    Add-VibeHostStageDisclosureEvent -SessionRoot ([string]$skeleton.session_root) -DisclosureEvent $planningConsultationEvent | Out-Null
}
$planArgs.PlanMemoryContextPath = $planMemoryContext.context_path
$planArgs.DiscussionConsultationPath = $discussionConsultation.receipt_path
$planArgs.PlanningConsultationPath = $planningConsultation.receipt_path
$plan = & (Join-Path $PSScriptRoot 'Write-XlPlan.ps1') @planArgs
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'xl_plan' `
    -PreviousStageName 'requirement_doc' `
    -PreviousStageReceiptPath ([string]$requirement.receipt_path) `
    -CurrentReceiptPath ([string]$plan.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
if ($requestedStop -eq 'xl_plan') {
    $hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
    $hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
        Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $boundedReturnControl = New-VibeBoundedReturnControlProjection `
        -RepoRoot ([string]$runtime.repo_root) `
        -RunId $RunId `
        -EntryIntentId $EntryIntentId `
        -StageLineage $stageLineage
    $hostUserBriefing = New-VibeHostUserBriefingProjection -BoundedReturnControl $boundedReturnControl
    $hostUserBriefingPath = ''
    if ($hostUserBriefing) {
        $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot ([string]$skeleton.session_root)
        Write-VgoUtf8NoBomText -Path $hostUserBriefingPath -Content (([string]$hostUserBriefing.rendered_text) + [Environment]::NewLine)
    }

    return Complete-VibeGovernedRuntimeStop `
        -RunId $RunId `
        -Mode $Mode `
        -Task $Task `
        -ArtifactBaseRoot $artifactBaseRoot `
        -SessionRoot ([string]$skeleton.session_root) `
        -HierarchyState $hierarchyState `
        -StorageProjection $storageProjection `
        -Skeleton $skeleton `
        -RuntimeInput $runtimeInput `
        -GovernanceCapsule $governanceCapsule `
        -StageLineage $stageLineage `
        -Interview $interview `
        -Requirement $requirement `
        -Plan $plan `
        -DiscussionConsultation $discussionConsultation `
        -PlanningConsultation $planningConsultation `
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -HostUserBriefing $hostUserBriefing `
        -HostUserBriefingPath $hostUserBriefingPath `
        -BoundedReturnControl $boundedReturnControl `
        -DelegationValidation $delegationValidation
}
$grade = if ($plan.receipt -and $plan.receipt.internal_grade) { [string]$plan.receipt.internal_grade } else { Get-VibeInternalGrade -Task $Task }
$memoryPlanExecuteRead = Get-VibeRufloReadAction -Runtime $runtime -Task $Task -SessionRoot ([string]$skeleton.session_root) -Grade $grade
$executionMemoryContext = New-VibePlanMemoryContextPack -Runtime $runtime -ReadActions @($memoryPlanExecuteRead) -SessionRoot ([string]$skeleton.session_root) -Stage 'plan_execute' -ArtifactName 'execution-context-pack.json'
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
$executeArgs.ExecutionMemoryContextPath = $executionMemoryContext.context_path
$execute = & (Join-Path $PSScriptRoot 'Invoke-PlanExecute.ps1') @executeArgs
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'plan_execute' `
    -PreviousStageName 'xl_plan' `
    -PreviousStageReceiptPath ([string]$plan.receipt_path) `
    -CurrentReceiptPath ([string]$execute.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
if ($requestedStop -eq 'plan_execute') {
    $hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
    $hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
        Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $executionManifestDocument = if (Test-Path -LiteralPath ([string]$execute.execution_manifest_path)) {
        Get-Content -LiteralPath ([string]$execute.execution_manifest_path) -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }

    # plan_execute stops before cleanup/user-facing execution handoff is finalized, so this early return
    # intentionally does not synthesize bounded-return credentials or a host-user briefing.
    return Complete-VibeGovernedRuntimeStop `
        -RunId $RunId `
        -Mode $Mode `
        -Task $Task `
        -ArtifactBaseRoot $artifactBaseRoot `
        -SessionRoot ([string]$skeleton.session_root) `
        -HierarchyState $hierarchyState `
        -StorageProjection $storageProjection `
        -Skeleton $skeleton `
        -RuntimeInput $runtimeInput `
        -GovernanceCapsule $governanceCapsule `
        -StageLineage $stageLineage `
        -Interview $interview `
        -Requirement $requirement `
        -Plan $plan `
        -Execute $execute `
        -DiscussionConsultation $discussionConsultation `
        -PlanningConsultation $planningConsultation `
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -ExecutionManifestDocument $executionManifestDocument `
        -DelegationValidation $delegationValidation
}
$cleanup = & (Join-Path $PSScriptRoot 'Invoke-PhaseCleanup.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot -ExecuteGovernanceCleanup:$ExecuteGovernanceCleanup -ApplyManagedNodeCleanup:$ApplyManagedNodeCleanup
$stageLineage = Add-VibeStageLineageEntry `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -RootRunId ([string]$hierarchyState.root_run_id) `
    -StageName 'phase_cleanup' `
    -PreviousStageName 'plan_execute' `
    -PreviousStageReceiptPath ([string]$execute.receipt_path) `
    -CurrentReceiptPath ([string]$cleanup.receipt_path) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
$memoryExecuteWrite = New-VibeExecutionMemoryWriteAction `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -SessionRoot ([string]$skeleton.session_root) `
    -Runtime $runtime `
    -RunId $RunId `
    -Task $Task `
    -Grade $grade
$memoryExecuteRufloWrite = New-VibeRufloExecutionWriteAction `
    -Runtime $runtime `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -SessionRoot ([string]$skeleton.session_root) `
    -RunId $RunId `
    -Task $Task `
    -Grade $grade
$memoryCleanupDecision = Get-VibeCleanupDecisionWriteAction `
    -RequirementDocPath ([string]$requirement.requirement_doc_path) `
    -ExecutionPlanPath ([string]$plan.execution_plan_path) `
    -Runtime $runtime `
    -SessionRoot ([string]$skeleton.session_root) `
    -Task $Task
$memoryCleanupCognee = Get-VibeCogneeCleanupWriteAction `
    -Runtime $runtime `
    -Task $Task `
    -RequirementDocPath ([string]$requirement.requirement_doc_path) `
    -ExecutionPlanPath ([string]$plan.execution_plan_path) `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -SessionRoot ([string]$skeleton.session_root)
$memoryCleanupFold = New-VibeCleanupMemoryFold `
    -RequirementDocPath ([string]$requirement.requirement_doc_path) `
    -ExecutionPlanPath ([string]$plan.execution_plan_path) `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -CleanupReceiptPath ([string]$cleanup.receipt_path) `
    -SessionRoot ([string]$skeleton.session_root)
$memoryActivation = New-VibeMemoryActivationReport `
    -Runtime $runtime `
    -RunId $RunId `
    -SessionRoot ([string]$skeleton.session_root) `
    -SkeletonReadActions $skeletonMemoryReads `
    -DeepInterviewReadActions $deepInterviewMemoryReads `
    -RequirementContextPack $requirementMemoryContext `
    -XlPlanReadActions $xlPlanReadActions `
    -PlanContextPack $planMemoryContext `
    -PlanExecuteReadActions @($memoryPlanExecuteRead) `
    -PlanExecuteContextPack $executionMemoryContext `
    -PlanExecuteWriteActions @($memoryExecuteWrite, $memoryExecuteRufloWrite) `
    -CleanupWriteActions @($memoryCleanupDecision, $memoryCleanupCognee) `
    -CleanupFoldAction $memoryCleanupFold
$deliveryAcceptanceReportPath = Join-Path $skeleton.session_root 'delivery-acceptance-report.json'
$deliveryAcceptanceMarkdownPath = Join-Path $skeleton.session_root 'delivery-acceptance-report.md'
$executionManifestDocument = if (Test-Path -LiteralPath ([string]$execute.execution_manifest_path)) {
    Get-Content -LiteralPath ([string]$execute.execution_manifest_path) -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$deliveryAcceptanceReport = if (Test-Path -LiteralPath $deliveryAcceptanceReportPath) {
    Get-Content -LiteralPath $deliveryAcceptanceReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$deliveryAcceptanceReportArtifactPath = if (Test-Path -LiteralPath $deliveryAcceptanceReportPath) {
    [string]$deliveryAcceptanceReportPath
} else {
    ''
}
$deliveryAcceptanceMarkdownArtifactPath = if (Test-Path -LiteralPath $deliveryAcceptanceMarkdownPath) {
    [string]$deliveryAcceptanceMarkdownPath
} else {
    ''
}
$specialistLifecycleDisclosure = New-VibeSpecialistLifecycleDisclosureProjection `
    -RuntimeInputPacket $runtimeInputPacket `
    -DiscussionConsultationReceipt $discussionConsultation.receipt `
    -PlanningConsultationReceipt $planningConsultation.receipt `
    -SpecialistUserDisclosure $(if ($execute -and $execute.receipt -and $execute.receipt.PSObject.Properties.Name -contains 'specialist_user_disclosure') { $execute.receipt.specialist_user_disclosure } else { $null }) `
    -ExecutionManifest $executionManifestDocument
$specialistLifecycleDisclosurePath = Get-VibeSpecialistLifecycleDisclosurePath -SessionRoot ([string]$skeleton.session_root)
Write-VibeJsonArtifact -Path $specialistLifecycleDisclosurePath -Value $specialistLifecycleDisclosure
$hostUserBriefing = New-VibeHostUserBriefingProjection `
    -LifecycleDisclosure $specialistLifecycleDisclosure `
    -DiscussionConsultationReceipt $discussionConsultation.receipt `
    -PlanningConsultationReceipt $planningConsultation.receipt `
    -DeliveryAcceptanceReport $deliveryAcceptanceReport
$hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
$hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
    Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$hostUserBriefingPath = $null
if ($hostUserBriefing) {
    $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot ([string]$skeleton.session_root)
    Write-VgoUtf8NoBomText -Path $hostUserBriefingPath -Content (([string]$hostUserBriefing.rendered_text) + [Environment]::NewLine)
}

$requirementReceiptDocument = if (Test-Path -LiteralPath ([string]$requirement.receipt_path)) {
    Get-Content -LiteralPath ([string]$requirement.receipt_path) -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
if ($requirementReceiptDocument) {
    if ($requirementReceiptDocument.PSObject.Properties.Name -contains 'specialist_lifecycle_disclosure_path') {
        $requirementReceiptDocument.specialist_lifecycle_disclosure_path = [string]$specialistLifecycleDisclosurePath
    } else {
        $requirementReceiptDocument | Add-Member -NotePropertyName specialist_lifecycle_disclosure_path -NotePropertyValue ([string]$specialistLifecycleDisclosurePath)
    }
    Write-VibeJsonArtifact -Path ([string]$requirement.receipt_path) -Value $requirementReceiptDocument
    $requirement.receipt = $requirementReceiptDocument
}

$planReceiptDocument = if (Test-Path -LiteralPath ([string]$plan.receipt_path)) {
    Get-Content -LiteralPath ([string]$plan.receipt_path) -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
if ($planReceiptDocument) {
    if ($planReceiptDocument.PSObject.Properties.Name -contains 'specialist_lifecycle_disclosure_path') {
        $planReceiptDocument.specialist_lifecycle_disclosure_path = [string]$specialistLifecycleDisclosurePath
    } else {
        $planReceiptDocument | Add-Member -NotePropertyName specialist_lifecycle_disclosure_path -NotePropertyValue ([string]$specialistLifecycleDisclosurePath)
    }
    Write-VibeJsonArtifact -Path ([string]$plan.receipt_path) -Value $planReceiptDocument
    $plan.receipt = $planReceiptDocument
}

$criticalArtifactPaths = @(
    [string]$skeleton.receipt_path,
    [string]$runtimeInput.packet_path,
    [string]$governanceCapsule.path,
    [string]$stageLineage.path,
    [string]$interview.receipt_path,
    [string]$requirement.requirement_doc_path,
    [string]$requirement.receipt_path,
    [string]$plan.execution_plan_path,
    [string]$plan.receipt_path,
    [string]$execute.receipt_path,
    [string]$execute.execution_manifest_path,
    [string]$execute.execution_topology_path,
    [string]$execute.execution_proof_manifest_path,
    [string]$discussionConsultation.receipt_path,
    [string]$planningConsultation.receipt_path,
    [string]$specialistLifecycleDisclosurePath,
    [string]$cleanup.receipt_path,
    [string]$memoryActivation.report_path,
    [string]$memoryActivation.markdown_path
)
if (-not [string]::IsNullOrWhiteSpace($deliveryAcceptanceReportArtifactPath)) {
    $criticalArtifactPaths += $deliveryAcceptanceReportArtifactPath
}
if ($hostStageDisclosure) {
    $criticalArtifactPaths += [string]$hostStageDisclosurePath
}
if (-not [string]::IsNullOrWhiteSpace([string]$hostUserBriefingPath)) {
    $criticalArtifactPaths += [string]$hostUserBriefingPath
}
if ($delegationValidation) {
    $criticalArtifactPaths += [string]$delegationValidation.receipt_path
}
$artifactReadiness = Wait-VibeArtifactSet -Paths $criticalArtifactPaths

if (-not $artifactReadiness.ready) {
    throw ("Governed runtime returned before critical artifacts were durable. Missing: {0}" -f (@($artifactReadiness.missing) -join ', '))
}

$delegationValidationReceiptPath = if ($delegationValidation) { [string]$delegationValidation.receipt_path } else { '' }
$summaryArtifacts = New-VibeRuntimeSummaryArtifactProjection `
    -SkeletonReceiptPath ([string]$skeleton.receipt_path) `
    -RuntimeInputPacketPath ([string]$runtimeInput.packet_path) `
    -GovernanceCapsulePath ([string]$governanceCapsule.path) `
    -StageLineagePath ([string]$stageLineage.path) `
    -IntentContractPath ([string]$interview.receipt_path) `
    -RequirementDocPath ([string]$requirement.requirement_doc_path) `
    -RequirementReceiptPath ([string]$requirement.receipt_path) `
    -ExecutionPlanPath ([string]$plan.execution_plan_path) `
    -ExecutionPlanReceiptPath ([string]$plan.receipt_path) `
    -ExecuteReceiptPath ([string]$execute.receipt_path) `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -ExecutionTopologyPath ([string]$execute.execution_topology_path) `
    -ExecutionProofManifestPath ([string]$execute.execution_proof_manifest_path) `
    -DiscussionSpecialistConsultationPath ([string]$discussionConsultation.receipt_path) `
    -PlanningSpecialistConsultationPath ([string]$planningConsultation.receipt_path) `
    -SpecialistLifecycleDisclosurePath ([string]$specialistLifecycleDisclosurePath) `
    -HostStageDisclosurePath $(if ($hostStageDisclosure) { [string]$hostStageDisclosurePath } else { '' }) `
    -HostUserBriefingPath ([string]$hostUserBriefingPath) `
    -CleanupReceiptPath ([string]$cleanup.receipt_path) `
    -DeliveryAcceptanceReportPath $deliveryAcceptanceReportArtifactPath `
    -DeliveryAcceptanceMarkdownPath $deliveryAcceptanceMarkdownArtifactPath `
    -MemoryActivationReportPath ([string]$memoryActivation.report_path) `
    -MemoryActivationMarkdownPath ([string]$memoryActivation.markdown_path) `
    -DelegationEnvelopePath ([string]$hierarchyState.delegation_envelope_path) `
    -DelegationValidationReceiptPath $delegationValidationReceiptPath
$relativeArtifacts = New-VibeRuntimeSummaryRelativeArtifactProjection -BasePath $artifactBaseRoot -Artifacts $summaryArtifacts

$summary = New-VibeRuntimeSummaryProjection `
    -RunId $RunId `
    -Mode $Mode `
    -Task $Task `
    -ArtifactRoot $artifactBaseRoot `
    -SessionRoot ([string]$skeleton.session_root) `
    -HierarchyState $hierarchyState `
    -Artifacts $summaryArtifacts `
    -RelativeArtifacts $relativeArtifacts `
    -StageLineage $stageLineage `
    -StorageProjection $storageProjection `
    -MemoryActivationReport $memoryActivation.report `
    -DeliveryAcceptanceReport $deliveryAcceptanceReport `
    -SpecialistDecision $(if ($executionManifestDocument -and $executionManifestDocument.PSObject.Properties.Name -contains 'specialist_decision' -and $null -ne $executionManifestDocument.specialist_decision) { $executionManifestDocument.specialist_decision } elseif ($execute -and $execute.receipt -and $execute.receipt.PSObject.Properties.Name -contains 'specialist_decision' -and $null -ne $execute.receipt.specialist_decision) { $execute.receipt.specialist_decision } else { $null }) `
    -SpecialistUserDisclosure $(if ($execute -and $execute.receipt -and $execute.receipt.PSObject.Properties.Name -contains 'specialist_user_disclosure') { $execute.receipt.specialist_user_disclosure } else { $null }) `
    -SpecialistConsultation (New-VibeSpecialistConsultationRuntimeProjection -Receipts @($discussionConsultation.receipt, $planningConsultation.receipt)) `
    -SpecialistLifecycleDisclosure $specialistLifecycleDisclosure `
    -HostStageDisclosure $hostStageDisclosure `
    -HostUserBriefing $hostUserBriefing `
    -BoundedReturnControl $null

$summaryPath = Join-Path $skeleton.session_root 'runtime-summary.json'
Write-VibeJsonArtifact -Path $summaryPath -Value $summary

[pscustomobject]@{
    run_id = $RunId
    mode = $Mode
    session_root = $skeleton.session_root
    summary_path = $summaryPath
    host_stage_disclosure_path = if ($hostStageDisclosure) { [string]$hostStageDisclosurePath } else { $null }
    host_stage_disclosure = $hostStageDisclosure
    host_user_briefing_path = $hostUserBriefingPath
    host_user_briefing = $hostUserBriefing
    summary = $summary
}
