param(
    [Parameter(Mandatory)] [string]$Task,
    [ValidateSet('interactive_governed')] [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [AllowEmptyString()] [string]$WorkspaceRoot = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$EntryIntentId = '',
    [AllowEmptyString()] [string]$RequestedStageStop = '',
    [AllowEmptyString()] [string]$RequestedGradeFloor = '',
    [AllowEmptyString()] [string]$HostDecisionJson = '',
    [AllowEmptyString()] [string]$ModuleExecutionJsonFile = '',
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

function Invoke-VibePythonRuntimeSummaryFinalizer {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [object]$Payload,
        [Parameter(Mandatory)] [string]$SummaryPath
    )

    $pythonInvocation = Get-VgoPythonCommand
    $scriptPath = Join-Path $RepoRoot 'packages\runtime-core\src\vgo_runtime\canonical_entry.py'
    $runtimeCoreSrc = Join-Path $RepoRoot 'packages\runtime-core\src'
    $contractsSrc = Join-Path $RepoRoot 'packages\contracts\src'
    $inputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("vgo-runtime-summary-finalize-" + [System.Guid]::NewGuid().ToString("N") + ".json")
    $previousPythonPath = $env:PYTHONPATH

    try {
        Write-VibeJsonArtifact -Path $inputPath -Value $Payload
        $pythonPathEntries = @($runtimeCoreSrc, $contractsSrc)
        if (-not [string]::IsNullOrWhiteSpace($previousPythonPath)) {
            $pythonPathEntries += $previousPythonPath
        }
        $env:PYTHONPATH = ($pythonPathEntries -join [System.IO.Path]::PathSeparator)
        $pythonArgs = @($pythonInvocation.prefix_arguments)
        $pythonArgs += @(
            $scriptPath,
            '--finalize-runtime-summary-input-json', $inputPath,
            '--output-json-path', $SummaryPath
        )
        $commandOutput = & $pythonInvocation.host_path @pythonArgs 2>&1
        $commandExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($commandExitCode -ne 0) {
            throw ("Python runtime summary finalizer exited with code {0}: {1}" -f $commandExitCode, ((@($commandOutput) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine))
        }
        if (-not (Test-Path -LiteralPath $SummaryPath -PathType Leaf)) {
            throw ("Python runtime summary finalizer did not write runtime-summary.json: {0}" -f $SummaryPath)
        }
        return (Get-Content -LiteralPath $SummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json)
    } finally {
        if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONPATH = $previousPythonPath
        }
        if (Test-Path -LiteralPath $inputPath) {
            Remove-Item -LiteralPath $inputPath -Force -ErrorAction SilentlyContinue
        }
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
    $moduleExecutionPath = if (
        $Execute -and
        $Execute.PSObject.Properties.Name -contains 'module_execution_path' -and
        -not [string]::IsNullOrWhiteSpace([string]$Execute.module_execution_path) -and
        (Test-Path -LiteralPath ([string]$Execute.module_execution_path) -PathType Leaf)
    ) {
        [string]$Execute.module_execution_path
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
        $(if ($Plan) { [string]$Plan.module_work_plan_path } else { '' }),
        $(if ($Plan) { [string]$Plan.receipt_path } else { '' }),
        $(if ($Execute) { [string]$Execute.receipt_path } else { '' }),
        $(if ($Execute) { [string]$Execute.execution_manifest_path } else { '' }),
        $moduleExecutionPath,
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

    if (-not (Test-Path -LiteralPath ([string]$RuntimeInput.packet_path) -PathType Leaf)) {
        throw 'Missing Python-built runtime-input-packet.json.'
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
        -ModuleWorkPlanPath $(if ($Plan) { [string]$Plan.module_work_plan_path } else { '' }) `
        -ModuleExecutionPath $moduleExecutionPath `
        -AgentExecutionHandoffPath $(if ($Execute -and $Execute.PSObject.Properties.Name -contains 'agent_execution_handoff_path') { [string]$Execute.agent_execution_handoff_path } else { '' }) `
        -ExecuteReceiptPath $(if ($Execute) { [string]$Execute.receipt_path } else { '' }) `
        -ExecutionManifestPath $(if ($Execute) { [string]$Execute.execution_manifest_path } else { '' }) `
        -HostStageDisclosurePath $(if ($HostStageDisclosure) { [string]$HostStageDisclosurePath } else { '' }) `
        -HostUserBriefingPath ([string]$HostUserBriefingPath) `
        -CleanupReceiptPath $(if ($Cleanup) { [string]$Cleanup.receipt_path } else { '' }) `
        -DeliveryAcceptanceReportPath ([string]$DeliveryAcceptanceReportPath) `
        -DeliveryAcceptanceMarkdownPath ([string]$DeliveryAcceptanceMarkdownPath) `
        -MemoryActivationReportPath ([string]$MemoryActivationReportPath) `
        -MemoryActivationMarkdownPath ([string]$MemoryActivationMarkdownPath) `
        -DelegationEnvelopePath ([string]$HierarchyState.delegation_envelope_path) `
        -DelegationValidationReceiptPath $delegationValidationReceiptPath
    $summaryPath = Join-Path $SessionRoot 'runtime-summary.json'
    $summary = Invoke-VibePythonRuntimeSummaryFinalizer `
        -RepoRoot $runtime.repo_root `
        -Payload ([pscustomobject]@{
            run_id = $RunId
            mode = $Mode
            task = $Task
            artifact_root = $ArtifactBaseRoot
            session_root = $SessionRoot
            hierarchy_state = $HierarchyState
            artifacts = $summaryArtifacts
            module_assignments = $RuntimeInput.packet.module_assignments
            stage_lineage = $StageLineage
            storage_projection = $StorageProjection
            memory_activation_report = $MemoryActivationReport
            delivery_acceptance_report = $DeliveryAcceptanceReport
            host_stage_disclosure = $HostStageDisclosure
            host_user_briefing = $HostUserBriefing
            bounded_return_control = $BoundedReturnControl
            agent_execution_handoff = $(if ($Execute -and $Execute.PSObject.Properties.Name -contains 'agent_execution_handoff') { $Execute.agent_execution_handoff } else { $null })
        }) `
        -SummaryPath $summaryPath

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
$workspaceRootWasProvided = -not [string]::IsNullOrWhiteSpace($WorkspaceRoot)
$artifactRootWasProvided = -not [string]::IsNullOrWhiteSpace($ArtifactRoot)
$resolvedWorkspaceRoot = if (-not $workspaceRootWasProvided -and $artifactRootWasProvided) {
    Get-VibeWorkspaceRoot -RepoRoot $runtime.repo_root -WorkspaceRoot $ArtifactRoot
} else {
    Get-VibeWorkspaceRoot -RepoRoot $runtime.repo_root -WorkspaceRoot $WorkspaceRoot
}
$runtime | Add-Member -NotePropertyName workspace_root -NotePropertyValue $resolvedWorkspaceRoot -Force
$artifactBaseRoot = if (-not $workspaceRootWasProvided -and $artifactRootWasProvided) {
    $resolvedWorkspaceRoot
} else {
    Get-VibeArtifactRoot `
        -RepoRoot $runtime.repo_root `
        -Runtime $runtime `
        -WorkspaceRoot $resolvedWorkspaceRoot `
        -ArtifactRoot $ArtifactRoot
}
$ArtifactRoot = $artifactBaseRoot
if ($workspaceRootWasProvided -or $artifactRootWasProvided) {
    Initialize-VibeWorkspaceProjectDescriptor `
        -RepoRoot $runtime.repo_root `
        -WorkspaceRoot $resolvedWorkspaceRoot `
        -Runtime $runtime | Out-Null
}
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}
if (-not [string]::IsNullOrWhiteSpace($ModuleExecutionJsonFile)) {
    if ($RequestedStageStop -ne 'phase_cleanup') {
        throw 'Agent module execution re-entry must target phase_cleanup.'
    }

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $artifactBaseRoot
    $submittedModuleExecutionPath = [System.IO.Path]::GetFullPath($ModuleExecutionJsonFile)
    $moduleExecutionPath = Get-VibeModuleExecutionPath -SessionRoot $sessionRoot
    if ($submittedModuleExecutionPath -ne [System.IO.Path]::GetFullPath($moduleExecutionPath)) {
        Copy-Item -LiteralPath $submittedModuleExecutionPath -Destination $moduleExecutionPath -Force
    }

    $runtimeInputPath = Join-Path $sessionRoot 'runtime-input-packet.json'
    $governanceCapsulePath = Join-Path $sessionRoot 'governance-capsule.json'
    $stageLineagePath = Join-Path $sessionRoot 'stage-lineage.json'
    $executeReceiptPath = Join-Path $sessionRoot 'phase-execute.json'
    $executionManifestPath = Join-Path $sessionRoot 'execution-manifest.json'
    foreach ($requiredPath in @(
        $runtimeInputPath,
        $governanceCapsulePath,
        $stageLineagePath,
        $executeReceiptPath,
        $executionManifestPath,
        (Join-Path $sessionRoot 'module-work-plan.json'),
        (Join-Path $sessionRoot 'agent-execution-handoff.json')
    )) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw ("Agent module execution re-entry is missing source artifact: {0}" -f $requiredPath)
        }
    }

    $stageLineageDocument = Get-Content -LiteralPath $stageLineagePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$stageLineageDocument.last_stage_name -ne 'plan_execute') {
        throw 'Agent module execution re-entry requires a source run stopped at plan_execute.'
    }
    $runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $frozenTask = [string]$runtimeInputPacket.task
    if ([string]::IsNullOrWhiteSpace($frozenTask)) {
        throw 'Agent module execution re-entry requires the frozen task from runtime-input-packet.json.'
    }
    $executionManifestDocument = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $moduleExecution = Get-Content -LiteralPath $moduleExecutionPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $moduleWorkPlanPath = Join-Path $sessionRoot 'module-work-plan.json'
    $moduleWorkPlan = Get-Content -LiteralPath $moduleWorkPlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $agentExecutionHandoff = Get-Content -LiteralPath (Join-Path $sessionRoot 'agent-execution-handoff.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $resultContract = Get-VibePropertySafe -InputObject $agentExecutionHandoff -PropertyName 'result_contract' -DefaultValue $null
    if ($null -eq $resultContract) {
        throw 'Agent execution handoff is missing result_contract.'
    }
    foreach ($requiredField in @($resultContract.required_top_level_fields)) {
        if (-not (Test-VibeObjectHasProperty -InputObject $moduleExecution -PropertyName $requiredField)) {
            throw ("Agent module execution is missing required field: {0}" -f $requiredField)
        }
    }
    if ([string]$moduleExecution.schema_version -ne 'module_execution_v1') {
        throw 'Agent module execution must use module_execution_v1.'
    }
    if ([string]$agentExecutionHandoff.source_run_id -ne $RunId -or [string]$moduleExecution.source_run_id -ne $RunId) {
        throw 'Agent module execution source_run_id must match the handoff run.'
    }
    if (Test-VibeObjectHasProperty -InputObject $resultContract -PropertyName 'tdd_evidence') {
        if (-not (Test-VibeObjectHasProperty -InputObject $moduleExecution -PropertyName 'tdd_evidence')) {
            throw 'Agent module execution TDD evidence must be a JSON object.'
        }
        $tddContract = $resultContract.tdd_evidence
        $tddEvidence = $moduleExecution.tdd_evidence
        if ($null -eq $tddEvidence -or -not (Test-VibeStructuredObject -InputObject $tddEvidence)) {
            throw 'Agent module execution TDD evidence must be a JSON object.'
        }
        foreach ($requiredField in @($tddContract.required_result_fields)) {
            if (-not (Test-VibeObjectHasProperty -InputObject $tddEvidence -PropertyName $requiredField)) {
                throw ("Agent module execution TDD evidence is missing required field: {0}" -f $requiredField)
            }
        }
        $tddState = [string]$tddEvidence.state
        if ($tddState -notin @($tddContract.terminal_states)) {
            throw 'Agent module execution TDD evidence state must be passing, failing, or blocked.'
        }
        foreach ($listField in @(
            'evidence_paths',
            'red_phase_evidence_paths',
            'green_phase_evidence_paths',
            'refactor_phase_evidence_paths',
            'covered_code_task_tdd_evidence_requirements',
            'covered_code_task_tdd_exceptions'
        )) {
            $listValue = $tddEvidence.PSObject.Properties[$listField].Value
            if ($null -eq $listValue -or $listValue -is [string] -or $listValue -isnot [System.Collections.IEnumerable]) {
                throw ("Agent module execution TDD evidence {0} must be a JSON array of strings." -f $listField)
            }
            foreach ($item in @($listValue)) {
                if ($item -isnot [string] -or [string]::IsNullOrWhiteSpace([string]$item)) {
                    throw ("Agent module execution TDD evidence {0} must be a JSON array of strings." -f $listField)
                }
            }
        }
        if ($tddEvidence.notes -isnot [string]) {
            throw 'Agent module execution TDD evidence notes must be a string.'
        }
        if ($tddState -eq 'passing') {
            $requiredTddRequirements = @($tddContract.required_code_task_tdd_evidence_requirements)
            $requiredTddExceptions = @($tddContract.required_code_task_tdd_exceptions)
            if ((@($tddEvidence.covered_code_task_tdd_evidence_requirements) -join "`n") -cne ($requiredTddRequirements -join "`n")) {
                throw 'Passing Agent module execution TDD evidence must cover the frozen TDD requirements.'
            }
            if ((@($tddEvidence.covered_code_task_tdd_exceptions) -join "`n") -cne ($requiredTddExceptions -join "`n")) {
                throw 'Passing Agent module execution TDD evidence must cover the frozen TDD exceptions.'
            }
            if (@($tddEvidence.evidence_paths).Count -eq 0) {
                throw 'Passing Agent module execution TDD evidence requires evidence paths.'
            }
            if ($requiredTddRequirements.Count -gt 0 -and @($tddEvidence.red_phase_evidence_paths).Count -eq 0) {
                throw 'Passing Agent module execution TDD evidence requires red-phase evidence paths.'
            }
            if ($requiredTddRequirements.Count -gt 0 -and @($tddEvidence.green_phase_evidence_paths).Count -eq 0) {
                throw 'Passing Agent module execution TDD evidence requires green-phase evidence paths.'
            }
        }
    }
    $expectedPlanDigest = (Get-FileHash -LiteralPath $moduleWorkPlanPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ([string]$moduleExecution.module_work_plan_digest -ne $expectedPlanDigest) {
        throw 'Agent module execution does not match the approved module work plan digest.'
    }
    $plannedUnits = @($moduleWorkPlan.work_units)
    $submittedUnits = @($moduleExecution.units)
    $plannedUnitIds = @($plannedUnits | ForEach-Object { [string]$_.unit_id } | Sort-Object)
    $submittedUnitIds = @($submittedUnits | ForEach-Object { [string]$_.unit_id } | Sort-Object)
    if (($plannedUnitIds -join "`n") -cne ($submittedUnitIds -join "`n")) {
        throw 'Agent module execution work units must exactly match the approved plan.'
    }
    foreach ($plannedUnit in $plannedUnits) {
        $unitId = [string]$plannedUnit.unit_id
        $submittedUnit = @($submittedUnits | Where-Object { [string]$_.unit_id -eq $unitId } | Select-Object -First 1)
        if ($submittedUnit.Count -ne 1) {
            throw ("Agent module execution work unit is missing or duplicated: {0}" -f $unitId)
        }
        foreach ($requiredField in @('unit_id', 'module_id', 'skill_id', 'role', 'state', 'result_summary', 'evidence_paths', 'verification_results')) {
            if (-not (Test-VibeObjectHasProperty -InputObject $submittedUnit[0] -PropertyName $requiredField)) {
                throw ("Agent module execution unit {0} is missing required field: {1}" -f $unitId, $requiredField)
            }
        }
        if (
            [string]$submittedUnit[0].module_id -ne [string]$plannedUnit.module_id -or
            [string]$submittedUnit[0].skill_id -ne [string]$plannedUnit.skill_id -or
            [string]$submittedUnit[0].role -ne [string]$plannedUnit.role
        ) {
            throw ("Agent module execution work unit changed its approved binding: {0}" -f $unitId)
        }
        $unitState = [string]$submittedUnit[0].state
        if ($unitState -notin @('completed', 'failed', 'blocked')) {
            throw ("Agent module execution unit {0} is not terminal." -f $unitId)
        }
        if ($unitState -eq 'completed' -and [string]::IsNullOrWhiteSpace([string]$submittedUnit[0].result_summary)) {
            throw ("Completed Agent module execution unit {0} requires a result summary." -f $unitId)
        }
    }
    $plannedModules = @($moduleWorkPlan.modules)
    $submittedModules = @($moduleExecution.modules)
    $plannedModuleIds = @($plannedModules | ForEach-Object { [string]$_.module_id } | Sort-Object)
    $submittedModuleIds = @($submittedModules | ForEach-Object { [string]$_.module_id } | Sort-Object)
    if (($plannedModuleIds -join "`n") -cne ($submittedModuleIds -join "`n")) {
        throw 'Agent module execution modules must exactly match the approved plan.'
    }
    foreach ($plannedModule in $plannedModules) {
        $moduleId = [string]$plannedModule.module_id
        $submittedModule = @($submittedModules | Where-Object { [string]$_.module_id -eq $moduleId } | Select-Object -First 1)
        if ($submittedModule.Count -ne 1) {
            throw ("Agent module execution module is missing or duplicated: {0}" -f $moduleId)
        }
        foreach ($requiredField in @('module_id', 'required', 'execution_mode', 'gap_reason', 'state', 'criterion_results')) {
            if (-not (Test-VibeObjectHasProperty -InputObject $submittedModule[0] -PropertyName $requiredField)) {
                throw ("Agent module execution module {0} is missing required field: {1}" -f $moduleId, $requiredField)
            }
        }
        if (
            [bool]$submittedModule[0].required -ne [bool]$plannedModule.required
        ) {
            throw ("Agent module execution module changed its required binding: {0}" -f $moduleId)
        }
        if ([string]$submittedModule[0].execution_mode -cne [string]$plannedModule.execution_mode) {
            throw ("Agent module execution module changed its execution_mode binding: {0}" -f $moduleId)
        }
        $plannedGapReason = if ($null -eq $plannedModule.gap_reason) { $null } else { [string]$plannedModule.gap_reason }
        $submittedGapReason = if ($null -eq $submittedModule[0].gap_reason) { $null } else { [string]$submittedModule[0].gap_reason }
        if (
            (($null -eq $plannedGapReason) -ne ($null -eq $submittedGapReason)) -or
            ($null -ne $plannedGapReason -and $submittedGapReason -cne $plannedGapReason)
        ) {
            throw ("Agent module execution module changed its gap_reason binding: {0}" -f $moduleId)
        }
        if ([string]$submittedModule[0].state -notin @('completed', 'failed', 'blocked')) {
            throw ("Agent module execution module {0} is not terminal." -f $moduleId)
        }

        $plannedCriteria = @($plannedModule.acceptance_criteria)
        $submittedCriteria = @($submittedModule[0].criterion_results)
        $plannedCriterionIds = @($plannedCriteria | ForEach-Object { [string]$_.criterion_id } | Sort-Object)
        $submittedCriterionIds = @($submittedCriteria | ForEach-Object {
                if (-not (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'criterion_id')) {
                    ''
                } else {
                    [string]$_.criterion_id
                }
            } | Sort-Object)
        if (
            ($plannedCriterionIds -join "`n") -cne ($submittedCriterionIds -join "`n") -or
            $submittedCriteria.Count -ne $plannedCriteria.Count
        ) {
            throw ("Agent module execution module {0} criterion results must exactly match the approved plan." -f $moduleId)
        }
        foreach ($criterionResult in $submittedCriteria) {
            $criterionId = [string]$criterionResult.criterion_id
            if (-not (Test-VibeObjectHasProperty -InputObject $criterionResult -PropertyName 'state')) {
                throw ("Agent module execution criterion {0}:{1} is missing required field: state" -f $moduleId, $criterionId)
            }
            $criterionState = [string]$criterionResult.state
            if ($criterionState -notin @('passing', 'failing', 'blocked')) {
                throw ("Agent module execution criterion {0}:{1} has unsupported state: {2}" -f $moduleId, $criterionId, $criterionState)
            }
        }
    }
    $requiredModuleIds = @(
        $plannedModules |
            Where-Object { [bool]$_.required } |
            ForEach-Object { [string]$_.module_id }
    )
    $completedUnitCount = @($moduleExecution.units | Where-Object { [string]$_.module_id -in $requiredModuleIds -and [string]$_.state -eq 'completed' }).Count
    $failedUnitCount = @($moduleExecution.units | Where-Object { [string]$_.module_id -in $requiredModuleIds -and [string]$_.state -eq 'failed' }).Count
    $blockedUnitCount = @($moduleExecution.units | Where-Object { [string]$_.module_id -in $requiredModuleIds -and [string]$_.state -eq 'blocked' }).Count
    $failedModuleCount = @($moduleExecution.modules | Where-Object { [string]$_.module_id -in $requiredModuleIds -and [string]$_.state -eq 'failed' }).Count
    $blockedModuleCount = @($moduleExecution.modules | Where-Object { [string]$_.module_id -in $requiredModuleIds -and [string]$_.state -eq 'blocked' }).Count
    $executionManifestDocument.status = if (($failedUnitCount + $blockedUnitCount + $failedModuleCount + $blockedModuleCount) -eq 0) { 'completed' } else { 'completed_with_failures' }
    $executionManifestDocument.module_handoff.status = 'agent_results_received'
    $executionManifestDocument.module_handoff.control_owner = 'vibe'
    $executionManifestDocument | Add-Member -NotePropertyName 'module_execution_path' -NotePropertyValue $moduleExecutionPath -Force
    $executionManifestDocument | Add-Member -NotePropertyName 'completed_unit_count' -NotePropertyValue ([int]$completedUnitCount) -Force
    $executionManifestDocument | Add-Member -NotePropertyName 'failed_unit_count' -NotePropertyValue ([int]$failedUnitCount) -Force
    $executionManifestDocument | Add-Member -NotePropertyName 'blocked_unit_count' -NotePropertyValue ([int]$blockedUnitCount) -Force
    Write-VibeJsonArtifact -Path $executionManifestPath -Value $executionManifestDocument

    $requirementReceiptPath = Join-Path $sessionRoot 'requirement-doc-receipt.json'
    $executionPlanReceiptPath = Join-Path $sessionRoot 'execution-plan-receipt.json'
    $requirementReceipt = Get-Content -LiteralPath $requirementReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionPlanReceipt = Get-Content -LiteralPath $executionPlanReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $requirementContextArtifact = Get-Content -LiteralPath ([string]$requirementReceipt.memory_context_path) -Raw -Encoding UTF8 | ConvertFrom-Json
    $requirementMemoryContext = [pscustomobject]@{
        context_path = [string]$requirementReceipt.memory_context_path
        disclosure_level = [string]$requirementContextArtifact.disclosure_level
        capsule_count = [int]$requirementContextArtifact.capsule_count
        selected_capsules = @($requirementContextArtifact.selected_capsules)
        injected_item_count = @($requirementContextArtifact.items).Count
        estimated_tokens = [int]$requirementContextArtifact.estimated_tokens
        budget = $requirementContextArtifact.budget
    }
    $planContextArtifact = Get-Content -LiteralPath ([string]$executionPlanReceipt.plan_memory_context_path) -Raw -Encoding UTF8 | ConvertFrom-Json
    $planMemoryContext = [pscustomobject]@{
        context_path = [string]$executionPlanReceipt.plan_memory_context_path
        disclosure_level = [string]$planContextArtifact.disclosure_level
        capsule_count = [int]$planContextArtifact.capsule_count
        selected_capsules = @($planContextArtifact.selected_capsules)
        injected_item_count = @($planContextArtifact.items).Count
        estimated_tokens = [int]$planContextArtifact.estimated_tokens
        budget = $planContextArtifact.budget
    }
    $executionMemoryContextPath = Join-Path $sessionRoot 'memory-activation\execution-context-pack.json'
    $executionContextArtifact = Get-Content -LiteralPath $executionMemoryContextPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionMemoryContext = [pscustomobject]@{
        context_path = $executionMemoryContextPath
        disclosure_level = [string]$executionContextArtifact.disclosure_level
        capsule_count = [int]$executionContextArtifact.capsule_count
        selected_capsules = @($executionContextArtifact.selected_capsules)
        injected_item_count = @($executionContextArtifact.items).Count
        estimated_tokens = [int]$executionContextArtifact.estimated_tokens
        budget = $executionContextArtifact.budget
    }
    $memoryBackendRoot = Join-Path $sessionRoot 'memory-backend'
    $restoredMemoryReadActions = @(
        Get-ChildItem -LiteralPath $memoryBackendRoot -Filter '*-read-response.json' -File -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
            $backendResult = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            $owner = switch -Regex ($_.BaseName) {
                '^serena-' { 'Serena'; break }
                '^cognee-' { 'Cognee'; break }
                '^ruflo-' { 'ruflo'; break }
                default { 'state_store' }
            }
            [pscustomobject]@{
                owner = $owner
                status = [string]$backendResult.status
                item_count = [int]$backendResult.item_count
                items = @($backendResult.items)
                capsule_count = if ($backendResult.PSObject.Properties.Name -contains 'capsule_count') { [int]$backendResult.capsule_count } else { 0 }
                capsules = if ($backendResult.PSObject.Properties.Name -contains 'capsules') { @($backendResult.capsules) } else { @() }
                artifact_path = if ($backendResult.PSObject.Properties.Name -contains 'artifact_path') { $backendResult.artifact_path } else { $null }
                project_key = if ($backendResult.PSObject.Properties.Name -contains 'project_key') { $backendResult.project_key } else { $null }
                project_key_source = if ($backendResult.PSObject.Properties.Name -contains 'project_key_source') { $backendResult.project_key_source } else { $null }
                workspace_memory_plane = if ($backendResult.PSObject.Properties.Name -contains 'workspace_memory_plane') { $backendResult.workspace_memory_plane } else { $null }
            }
        }
    )
    $restoredSkeletonReadActions = @($restoredMemoryReadActions | Where-Object {
            [string]$_.owner -in @('state_store', 'Cognee')
        })
    if (@($restoredSkeletonReadActions | Where-Object { [string]$_.owner -eq 'state_store' }).Count -eq 0) {
        $restoredSkeletonReadActions = @(
            New-VibeSkeletonMemoryDigest -Runtime $runtime -Skeleton ([pscustomobject]@{
                    receipt = Get-Content -LiteralPath (Join-Path $sessionRoot 'skeleton-receipt.json') -Raw -Encoding UTF8 | ConvertFrom-Json
                    receipt_path = Join-Path $sessionRoot 'skeleton-receipt.json'
                }) -Task $frozenTask -SessionRoot $sessionRoot
        ) + @($restoredSkeletonReadActions)
    }
    $restoredDeepInterviewReadActions = @($restoredMemoryReadActions | Where-Object { [string]$_.owner -eq 'Serena' })
    if (@($restoredDeepInterviewReadActions).Count -eq 0 -and @($restoredMemoryReadActions).Count -gt 0) {
        $restoredDeepInterviewReadActions = @($restoredMemoryReadActions[0])
    }
    $restoredXlPlanReadActions = @($restoredMemoryReadActions | Where-Object {
            [string]$_.owner -in @('Serena', 'Cognee')
        })

    $cleanup = & (Join-Path $PSScriptRoot 'Invoke-PhaseCleanup.ps1') `
        -Task $frozenTask `
        -Mode $Mode `
        -RunId $RunId `
        -ArtifactRoot $artifactBaseRoot `
        -ExecuteGovernanceCleanup:$ExecuteGovernanceCleanup `
        -ApplyManagedNodeCleanup:$ApplyManagedNodeCleanup
    $stageLineage = Add-VibeStageLineageEntry `
        -SessionRoot $sessionRoot `
        -RunId $RunId `
        -RootRunId $RunId `
        -StageName 'phase_cleanup' `
        -PreviousStageName 'plan_execute' `
        -PreviousStageReceiptPath $executeReceiptPath `
        -CurrentReceiptPath ([string]$cleanup.receipt_path) `
        -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract

    $deliveryAcceptanceReportPath = Join-Path $sessionRoot 'delivery-acceptance-report.json'
    $deliveryAcceptanceMarkdownPath = Join-Path $sessionRoot 'delivery-acceptance-report.md'
    $deliveryAcceptanceReport = if (Test-Path -LiteralPath $deliveryAcceptanceReportPath) {
        Get-Content -LiteralPath $deliveryAcceptanceReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $hostUserBriefing = New-VibeHostUserBriefingProjection `
        -DeliveryAcceptanceReport $deliveryAcceptanceReport
    $hostUserBriefingPath = ''
    if ($hostUserBriefing) {
        $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot $sessionRoot
        Write-VgoUtf8NoBomText `
            -Path $hostUserBriefingPath `
            -Content (([string]$hostUserBriefing.rendered_text) + [Environment]::NewLine)
    }
    $memoryExecuteWrite = New-VibeExecutionMemoryWriteAction `
        -ExecutionManifestPath $executionManifestPath `
        -SessionRoot $sessionRoot `
        -Runtime $runtime `
        -RunId $RunId `
        -Task $frozenTask `
        -Grade ([string]$executionManifestDocument.internal_grade)
    $memoryExecuteRufloWrite = New-VibeRufloExecutionWriteAction `
        -Runtime $runtime `
        -ExecutionManifestPath $executionManifestPath `
        -SessionRoot $sessionRoot `
        -RunId $RunId `
        -Task $frozenTask `
        -Grade ([string]$executionManifestDocument.internal_grade)
    $memoryCleanupDecision = Get-VibeCleanupDecisionWriteAction `
        -RequirementDocPath ([string]$executionPlanReceipt.requirement_doc_path) `
        -ExecutionPlanPath ([string]$executionPlanReceipt.execution_plan_path) `
        -Runtime $runtime `
        -SessionRoot $sessionRoot `
        -Task $frozenTask
    $memoryCleanupCognee = Get-VibeCogneeCleanupWriteAction `
        -Runtime $runtime `
        -Task $frozenTask `
        -RequirementDocPath ([string]$executionPlanReceipt.requirement_doc_path) `
        -ExecutionPlanPath ([string]$executionPlanReceipt.execution_plan_path) `
        -ExecutionManifestPath $executionManifestPath `
        -SessionRoot $sessionRoot
    $memoryCleanupFold = New-VibeCleanupMemoryFold `
        -RequirementDocPath ([string]$executionPlanReceipt.requirement_doc_path) `
        -ExecutionPlanPath ([string]$executionPlanReceipt.execution_plan_path) `
        -ExecutionManifestPath $executionManifestPath `
        -CleanupReceiptPath ([string]$cleanup.receipt_path) `
        -SessionRoot $sessionRoot
    $memoryActivation = New-VibeMemoryActivationReport `
        -Runtime $runtime `
        -RunId $RunId `
        -SessionRoot $sessionRoot `
        -SkeletonReadActions @($restoredSkeletonReadActions) `
        -DeepInterviewReadActions @($restoredDeepInterviewReadActions) `
        -RequirementContextPack $requirementMemoryContext `
        -XlPlanReadActions @($restoredXlPlanReadActions) `
        -PlanContextPack $planMemoryContext `
        -PlanExecuteReadActions @($restoredMemoryReadActions) `
        -PlanExecuteContextPack $executionMemoryContext `
        -PlanExecuteWriteActions @($memoryExecuteWrite, $memoryExecuteRufloWrite) `
        -CleanupWriteActions @($memoryCleanupDecision, $memoryCleanupCognee) `
        -CleanupFoldAction $memoryCleanupFold
    $hierarchyState = Get-VibeHierarchyState `
        -GovernanceScope '' `
        -RunId $RunId `
        -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract
    $storageProjection = New-VibeWorkspaceArtifactProjection `
        -RepoRoot $runtime.repo_root `
        -WorkspaceRoot $resolvedWorkspaceRoot `
        -Runtime $runtime `
        -ArtifactRoot $artifactBaseRoot `
        -RouterTargetRoot (Resolve-VgoTargetRoot -HostId (Resolve-VgoHostId -HostId $env:VCO_HOST_ID))
    $priorSummaryPath = Join-Path $sessionRoot 'runtime-summary.json'
    $priorSummary = if (Test-Path -LiteralPath $priorSummaryPath) {
        Get-Content -LiteralPath $priorSummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $priorArtifacts = if ($priorSummary -and $priorSummary.PSObject.Properties.Name -contains 'artifacts') {
        $priorSummary.artifacts
    } else {
        $null
    }
    $summaryArtifacts = New-VibeRuntimeSummaryArtifactProjection `
        -SkeletonReceiptPath (Join-Path $sessionRoot 'skeleton-receipt.json') `
        -RuntimeInputPacketPath $runtimeInputPath `
        -GovernanceCapsulePath $governanceCapsulePath `
        -StageLineagePath $stageLineagePath `
        -IntentContractPath ([string]$priorArtifacts.intent_contract) `
        -RequirementDocPath ([string]$priorArtifacts.requirement_doc) `
        -RequirementReceiptPath ([string]$priorArtifacts.requirement_receipt) `
        -ExecutionPlanPath ([string]$priorArtifacts.execution_plan) `
        -ExecutionPlanReceiptPath ([string]$priorArtifacts.execution_plan_receipt) `
        -ModuleWorkPlanPath (Join-Path $sessionRoot 'module-work-plan.json') `
        -ModuleExecutionPath $moduleExecutionPath `
        -AgentExecutionHandoffPath (Join-Path $sessionRoot 'agent-execution-handoff.json') `
        -ExecuteReceiptPath $executeReceiptPath `
        -ExecutionManifestPath $executionManifestPath `
        -HostStageDisclosurePath ([string]$priorArtifacts.host_stage_disclosure) `
        -HostUserBriefingPath $hostUserBriefingPath `
        -CleanupReceiptPath ([string]$cleanup.receipt_path) `
        -DeliveryAcceptanceReportPath $(if (Test-Path -LiteralPath $deliveryAcceptanceReportPath) { $deliveryAcceptanceReportPath } else { '' }) `
        -DeliveryAcceptanceMarkdownPath $(if (Test-Path -LiteralPath $deliveryAcceptanceMarkdownPath) { $deliveryAcceptanceMarkdownPath } else { '' }) `
        -MemoryActivationReportPath ([string]$memoryActivation.report_path) `
        -MemoryActivationMarkdownPath ([string]$memoryActivation.markdown_path)
    $summary = Invoke-VibePythonRuntimeSummaryFinalizer `
        -RepoRoot $runtime.repo_root `
        -Payload ([pscustomobject]@{
            run_id = $RunId
            mode = $Mode
            task = $frozenTask
            artifact_root = $artifactBaseRoot
            session_root = $sessionRoot
            hierarchy_state = $hierarchyState
            artifacts = $summaryArtifacts
            module_assignments = $runtimeInputPacket.module_assignments
            stage_lineage = $stageLineage
            storage_projection = $storageProjection
            memory_activation_report = $memoryActivation.report
            delivery_acceptance_report = $deliveryAcceptanceReport
            host_stage_disclosure = $(if ($priorSummary) { $priorSummary.host_stage_disclosure } else { $null })
            host_user_briefing = $hostUserBriefing
            bounded_return_control = $null
            agent_execution_handoff = $null
            module_execution = $moduleExecution
        }) `
        -SummaryPath $priorSummaryPath

    return [pscustomobject]@{
        run_id = $RunId
        mode = $Mode
        session_root = $sessionRoot
        summary_path = $priorSummaryPath
        summary = $summary
    }
}
$hostDecision = ConvertFrom-VibeHostDecisionJson -HostDecisionJson $HostDecisionJson
$hostContinuationContext = Get-VibeHostContinuationContext -HostDecision $hostDecision
$structuredBoundedReentry = Test-VibeStructuredBoundedReentryContext -ContinuationContext $hostContinuationContext
$storageProjection = New-VibeWorkspaceArtifactProjection `
    -RepoRoot $runtime.repo_root `
    -WorkspaceRoot $resolvedWorkspaceRoot `
    -Runtime $runtime `
    -ArtifactRoot $artifactBaseRoot `
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

$skeleton = & (Join-Path $PSScriptRoot 'Invoke-SkeletonCheck.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $artifactBaseRoot
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
    WorkspaceRoot = $resolvedWorkspaceRoot
    ArtifactRoot = $artifactBaseRoot
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
$requestedStop = Resolve-VibeRequestedStageStop -RequestedStageStop $(if ($runtimeInputPacket) { [string]$runtimeInputPacket.requested_stage_stop } else { '' })
$interview = & (Join-Path $PSScriptRoot 'Invoke-DeepInterview.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $artifactBaseRoot -HostDecisionJson $HostDecisionJson
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
$requirementArgs = @{
    Task = $Task
    Mode = $Mode
    RunId = $RunId
    IntentContractPath = $interview.receipt_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    MemoryContextPath = $requirementMemoryContext.context_path
    ArtifactRoot = $artifactBaseRoot
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
    $boundedSkillSearchGuide = if (
        $runtimeInputPacket.PSObject.Properties.Name -contains 'skill_search_guide' -and
        $null -ne $runtimeInputPacket.skill_search_guide
    ) {
        $runtimeInputPacket.skill_search_guide
    } else {
        $null
    }
    $boundedReturnControl = New-VibeBoundedReturnControlProjection `
        -RepoRoot ([string]$runtime.repo_root) `
        -RunId $RunId `
        -EntryIntentId $EntryIntentId `
        -StageLineage $stageLineage `
        -WorkflowLevelConfirmation $interview.intent_contract.workflow_level_confirmation `
        -SkillSearchGuide $boundedSkillSearchGuide
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
    ArtifactRoot = $artifactBaseRoot
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
$planArgs.PlanMemoryContextPath = $planMemoryContext.context_path
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
        -StageLineage $stageLineage `
        -SkillSearchGuide $(if ($runtimeInputPacket.PSObject.Properties.Name -contains 'skill_search_guide') { $runtimeInputPacket.skill_search_guide } else { $null })
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
    ModuleWorkPlanPath = $plan.module_work_plan_path
    RuntimeInputPacketPath = $runtimeInput.packet_path
    ArtifactRoot = $artifactBaseRoot
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
if ($execute.PSObject.Properties.Name -contains 'agent_execution_handoff' -and $null -ne $execute.agent_execution_handoff) {
    $hostStageDisclosurePath = Get-VibeHostStageDisclosurePath -SessionRoot ([string]$skeleton.session_root)
    $hostStageDisclosure = if (Test-Path -LiteralPath $hostStageDisclosurePath) {
        Get-Content -LiteralPath $hostStageDisclosurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }
    $hostUserBriefing = New-VibeAgentExecutionHandoffBriefing -Handoff $execute.agent_execution_handoff
    $hostUserBriefingPath = Get-VibeHostUserBriefingPath -SessionRoot ([string]$skeleton.session_root)
    Write-VgoUtf8NoBomText -Path $hostUserBriefingPath -Content (([string]$hostUserBriefing.rendered_text) + [Environment]::NewLine)
    $executionManifestDocument = if (Test-Path -LiteralPath ([string]$execute.execution_manifest_path)) {
        Get-Content -LiteralPath ([string]$execute.execution_manifest_path) -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
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
        -Execute $execute `
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -HostUserBriefing $hostUserBriefing `
        -HostUserBriefingPath $hostUserBriefingPath `
        -ExecutionManifestDocument $executionManifestDocument `
        -DelegationValidation $delegationValidation
}
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
        -HostStageDisclosure $hostStageDisclosure `
        -HostStageDisclosurePath $hostStageDisclosurePath `
        -ExecutionManifestDocument $executionManifestDocument `
        -DelegationValidation $delegationValidation
}
$cleanup = & (Join-Path $PSScriptRoot 'Invoke-PhaseCleanup.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $artifactBaseRoot -ExecuteGovernanceCleanup:$ExecuteGovernanceCleanup -ApplyManagedNodeCleanup:$ApplyManagedNodeCleanup
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
$hostUserBriefing = New-VibeHostUserBriefingProjection `
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
    [string]$cleanup.receipt_path,
    [string]$memoryActivation.report_path,
    [string]$memoryActivation.markdown_path
) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
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

if (-not (Test-Path -LiteralPath ([string]$runtimeInput.packet_path) -PathType Leaf)) {
    throw 'Missing Python-built runtime-input-packet.json.'
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
    -ModuleWorkPlanPath ([string]$plan.module_work_plan_path) `
    -ModuleExecutionPath $(if ($execute.PSObject.Properties.Name -contains 'module_execution_path') { [string]$execute.module_execution_path } else { '' }) `
    -AgentExecutionHandoffPath $(if ($execute.PSObject.Properties.Name -contains 'agent_execution_handoff_path') { [string]$execute.agent_execution_handoff_path } else { '' }) `
    -ExecuteReceiptPath ([string]$execute.receipt_path) `
    -ExecutionManifestPath ([string]$execute.execution_manifest_path) `
    -HostStageDisclosurePath $(if ($hostStageDisclosure) { [string]$hostStageDisclosurePath } else { '' }) `
    -HostUserBriefingPath ([string]$hostUserBriefingPath) `
    -CleanupReceiptPath ([string]$cleanup.receipt_path) `
    -DeliveryAcceptanceReportPath $deliveryAcceptanceReportArtifactPath `
    -DeliveryAcceptanceMarkdownPath $deliveryAcceptanceMarkdownArtifactPath `
    -MemoryActivationReportPath ([string]$memoryActivation.report_path) `
    -MemoryActivationMarkdownPath ([string]$memoryActivation.markdown_path) `
    -DelegationEnvelopePath ([string]$hierarchyState.delegation_envelope_path) `
    -DelegationValidationReceiptPath $delegationValidationReceiptPath
$summaryPath = Join-Path $skeleton.session_root 'runtime-summary.json'
$summary = Invoke-VibePythonRuntimeSummaryFinalizer `
    -RepoRoot $runtime.repo_root `
    -Payload ([pscustomobject]@{
        run_id = $RunId
        mode = $Mode
        task = $Task
        artifact_root = $artifactBaseRoot
        session_root = [string]$skeleton.session_root
        hierarchy_state = $hierarchyState
        artifacts = $summaryArtifacts
        module_assignments = $runtimeInputPacket.module_assignments
        stage_lineage = $stageLineage
        storage_projection = $storageProjection
        memory_activation_report = $memoryActivation.report
        delivery_acceptance_report = $deliveryAcceptanceReport
        host_stage_disclosure = $hostStageDisclosure
        host_user_briefing = $hostUserBriefing
        bounded_return_control = $null
    }) `
    -SummaryPath $summaryPath

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
