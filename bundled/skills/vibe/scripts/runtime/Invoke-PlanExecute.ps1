param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$RequirementDocPath = '',
    [string]$ExecutionPlanPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeExecution.Common.ps1')

function New-VibeDelegatedLaneSpec {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [string]$RequirementPath,
        [Parameter(Mandatory)] [string]$PlanPath,
        [Parameter(Mandatory)] [hashtable]$Tokens,
        [Parameter(Mandatory)] [int]$DefaultTimeoutSeconds,
        [Parameter(Mandatory)] [object]$LaneEntry
    )

    $laneId = [string]($LaneEntry.lane_id)
    $laneRoot = Join-Path (Join-Path $SessionRoot 'child-lanes') $laneId
    $specPath = Join-Path $laneRoot 'lane-spec.json'
    New-Item -ItemType Directory -Path $laneRoot -Force | Out-Null
    $laneSpec = [pscustomobject]@{
        lane_id = $laneId
        lane_kind = [string]($LaneEntry.lane_kind)
        lane_root = $laneRoot
        run_id = $RunId
        mode = $Mode
        governance_scope = 'child'
        root_run_id = [string]($HierarchyState.root_run_id)
        parent_run_id = $RunId
        parent_unit_id = [string]($LaneEntry.source_unit_id)
        requirement_doc_path = $RequirementPath
        execution_plan_path = $PlanPath
        repo_root = $Tokens['${REPO_ROOT}']
        default_timeout_seconds = $DefaultTimeoutSeconds
        parallelizable = [bool]($LaneEntry.parallelizable)
        write_scope = [string]($LaneEntry.write_scope)
        review_mode = [string]($LaneEntry.review_mode)
        tokens = [pscustomobject]$Tokens
        unit = if ($LaneEntry.PSObject.Properties.Name -contains 'unit') { $LaneEntry.unit } else { $null }
        dispatch = if ($LaneEntry.PSObject.Properties.Name -contains 'dispatch') { $LaneEntry.dispatch } else { $null }
    }
    Write-VibeJsonArtifact -Path $specPath -Value $laneSpec
    return [pscustomobject]@{
        lane_id = $laneId
        lane_root = $laneRoot
        spec_path = $specPath
        lane_entry = $LaneEntry
    }
}

function Start-VibeDelegatedLaneProcess {
    param(
        [Parameter(Mandatory)] [object]$LaneRuntime,
        [Parameter(Mandatory)] [string]$HelperScriptPath
    )

    $stdoutPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-process.stdout.log'
    $stderrPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-process.stderr.log'
    $invocation = Get-VgoPowerShellFileInvocation -ScriptPath $HelperScriptPath -ArgumentList @('-LaneSpecPath', ([string]($LaneRuntime.spec_path))) -NoProfile

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = [string]($invocation.host_path)
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.WorkingDirectory = Split-Path -Parent ([string]($LaneRuntime.spec_path))

    $quotedArguments = foreach ($argument in @($invocation.arguments)) {
        $text = [string]$argument
        if ($text -match '[\s"]') {
            '"' + ($text -replace '"', '\"') + '"'
        } else {
            $text
        }
    }
    $startInfo.Arguments = [string]::Join(' ', @($quotedArguments))

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw ("Failed to start delegated lane process for {0}" -f ([string]($LaneRuntime.lane_id)))
    }

    return [pscustomobject]@{
        lane_id = [string]($LaneRuntime.lane_id)
        lane_root = [string]($LaneRuntime.lane_root)
        lane_entry = $LaneRuntime.lane_entry
        process = $process
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        stdout_task = $process.StandardOutput.ReadToEndAsync()
        stderr_task = $process.StandardError.ReadToEndAsync()
    }
}

function Wait-VibeDelegatedLaneProcess {
    param(
        [Parameter(Mandatory)] [object]$Handle,
        [Parameter(Mandatory)] [int]$TimeoutSeconds
    )

    $timedOut = -not $Handle.process.WaitForExit($TimeoutSeconds * 1000)
    if ($timedOut) {
        try {
            $Handle.process.Kill($true)
        } catch {
        }
        $Handle.process.WaitForExit()
    }

    $stdoutText = $Handle.stdout_task.GetAwaiter().GetResult()
    $stderrText = $Handle.stderr_task.GetAwaiter().GetResult()
    Write-VgoUtf8NoBomText -Path ([string]($Handle.stdout_path)) -Content $stdoutText
    Write-VgoUtf8NoBomText -Path ([string]($Handle.stderr_path)) -Content $stderrText

    $payloadText = ($stdoutText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
    if ([string]::IsNullOrWhiteSpace($payloadText)) {
        throw ("Delegated lane process returned empty payload for {0}" -f ([string]($Handle.lane_id)))
    }

    $payload = $payloadText | ConvertFrom-Json
    $laneReceipt = Get-Content -LiteralPath ([string]($payload.lane_receipt_path)) -Raw -Encoding UTF8 | ConvertFrom-Json
    $laneResult = if ($payload.lane_result_path -and (Test-Path -LiteralPath ([string]($payload.lane_result_path)))) {
        Get-Content -LiteralPath ([string]($payload.lane_result_path)) -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $null
    }

    $processExitCode = if ($timedOut) { -1 } else { [int]($Handle.process.ExitCode) }
    $Handle.process.Dispose()

    return [pscustomobject]@{
        lane_id = [string]($Handle.lane_id)
        lane_entry = $Handle.lane_entry
        exit_code = $processExitCode
        timed_out = [bool]$timedOut
        stdout_path = [string]($Handle.stdout_path)
        stderr_path = [string]($Handle.stderr_path)
        lane_receipt_path = [string]($payload.lane_receipt_path)
        lane_notes_path = [string]($payload.lane_notes_path)
        lane_result_path = if ($payload.lane_result_path) { [string]($payload.lane_result_path) } else { $null }
        lane_receipt = $laneReceipt
        lane_result = $laneResult
    }
}

function New-VibeReviewReceipt {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$LaneId,
        [Parameter(Mandatory)] [string]$ReviewKind,
        [Parameter(Mandatory)] [object]$LaneReceipt,
        [AllowEmptyString()] [string]$SourcePath = ''
    )

    $reviewsRoot = Join-Path $SessionRoot 'reviews'
    New-Item -ItemType Directory -Path $reviewsRoot -Force | Out-Null
    $reviewPath = Join-Path $reviewsRoot ("{0}-{1}.json" -f $LaneId, $ReviewKind)

    $passed = switch ($ReviewKind) {
        'spec' { [string]($LaneReceipt.status) -eq 'completed' }
        'quality' { [bool]($LaneReceipt.verification_passed) }
        default { $false }
    }

    $reviewReceipt = [pscustomobject]@{
        lane_id = $LaneId
        review_kind = $ReviewKind
        passed = [bool]$passed
        governance_scope = 'root'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        source_lane_receipt_path = if (-not [string]::IsNullOrWhiteSpace($SourcePath)) {
            $SourcePath
        } elseif ($LaneReceipt.PSObject.Properties.Name -contains 'result_path') {
            [string]($LaneReceipt.result_path)
        } elseif ($LaneReceipt.PSObject.Properties.Name -contains 'lane_result_path') {
            [string]($LaneReceipt.lane_result_path)
        } else {
            $null
        }
        notes = if ($ReviewKind -eq 'spec') {
            'Spec compliance review confirms the delegated lane completed inside the frozen scope.'
        } else {
            'Code quality review confirms the delegated lane passed its verification contract.'
        }
    }
    Write-VibeJsonArtifact -Path $reviewPath -Value $reviewReceipt
    return [pscustomobject]@{
        receipt_path = $reviewPath
        receipt = $reviewReceipt
    }
}

function Invoke-VibeDirectLaneEntry {
    param(
        [Parameter(Mandatory)] [object]$LaneEntry,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [hashtable]$Tokens,
        [Parameter(Mandatory)] [int]$DefaultTimeoutSeconds,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$RequirementPath,
        [Parameter(Mandatory)] [string]$PlanPath,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [string]$RunId
    )

    switch ([string]$LaneEntry.lane_kind) {
        'benchmark_unit' {
            $executed = Invoke-VibeExecutionUnit `
                -Unit $LaneEntry.unit `
                -RepoRoot $RepoRoot `
                -SessionRoot $SessionRoot `
                -Tokens $Tokens `
                -DefaultTimeoutSeconds $DefaultTimeoutSeconds
            return [pscustomobject]@{
                lane_id = [string]$LaneEntry.lane_id
                lane_entry = $LaneEntry
                exit_code = [int]$executed.result.exit_code
                timed_out = [bool]$executed.result.timed_out
                lane_receipt_path = $null
                lane_notes_path = $null
                lane_result_path = [string]$executed.result_path
                lane_receipt = $null
                lane_result = $executed.result
            }
        }
        'specialist_dispatch' {
            $executed = Invoke-VibeSpecialistDispatchUnit `
                -UnitId ("{0}-specialist" -f [string]$LaneEntry.lane_id) `
                -Dispatch $LaneEntry.dispatch `
                -SessionRoot $SessionRoot `
                -RepoRoot $RepoRoot `
                -RequirementDocPath $RequirementPath `
                -ExecutionPlanPath $PlanPath `
                -RunId $RunId `
                -GovernanceScope ([string]$HierarchyState.governance_scope) `
                -RootRunId ([string]$HierarchyState.root_run_id) `
                -ParentRunId $(if ($null -eq $HierarchyState.parent_run_id) { '' } else { [string]$HierarchyState.parent_run_id }) `
                -ParentUnitId $(if ($null -eq $HierarchyState.parent_unit_id) { '' } else { [string]$HierarchyState.parent_unit_id }) `
                -WriteScope ([string]$LaneEntry.write_scope) `
                -ReviewMode ([string]$LaneEntry.review_mode)
            return [pscustomobject]@{
                lane_id = [string]$LaneEntry.lane_id
                lane_entry = $LaneEntry
                exit_code = [int]$executed.result.exit_code
                timed_out = [bool]$executed.result.timed_out
                lane_receipt_path = $null
                lane_notes_path = $null
                lane_result_path = [string]$executed.result_path
                lane_receipt = $null
                lane_result = $executed.result
            }
        }
        default {
            throw ("Unsupported direct lane kind: {0}" -f [string]$LaneEntry.lane_kind)
        }
    }
}

function ConvertTo-VibeExecutedUnitReceipt {
    param(
        [Parameter(Mandatory)] [string]$WaveId,
        [Parameter(Mandatory)] [string]$StepId,
        [Parameter(Mandatory)] [object]$Outcome
    )

    $unitId = if ($Outcome.lane_result) {
        [string]$Outcome.lane_result.unit_id
    } else {
        [string]$Outcome.lane_entry.source_unit_id
    }

    return [pscustomobject]@{
        unit_id = $unitId
        wave_id = $WaveId
        step_id = $StepId
        lane_id = [string]$Outcome.lane_id
        lane_kind = [string]$Outcome.lane_entry.lane_kind
        status = if ($Outcome.lane_result) { [string]$Outcome.lane_result.status } else { [string]$Outcome.lane_receipt.status }
        exit_code = if ($Outcome.lane_result) { [int]$Outcome.lane_result.exit_code } else { [int]$Outcome.exit_code }
        timed_out = if ($Outcome.lane_result) { [bool]$Outcome.lane_result.timed_out } else { [bool]$Outcome.timed_out }
        verification_passed = if ($Outcome.lane_result) { [bool]$Outcome.lane_result.verification_passed } else { [bool]$Outcome.lane_receipt.verification_passed }
        result_path = [string]$Outcome.lane_result_path
        lane_receipt_path = if ($Outcome.lane_receipt_path) { [string]$Outcome.lane_receipt_path } else { $null }
        skill_id = if ([string]$Outcome.lane_entry.lane_kind -eq 'specialist_dispatch') { [string]$Outcome.lane_entry.dispatch.skill_id } else { $null }
        write_scope = [string]$Outcome.lane_entry.write_scope
        execution_driver = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'execution_driver') { [string]$Outcome.lane_result.execution_driver } else { $null }
        live_native_execution = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'live_native_execution') { [bool]$Outcome.lane_result.live_native_execution } else { $false }
        degraded = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'degraded') { [bool]$Outcome.lane_result.degraded } else { $false }
    }
}

function Get-VibePlanSections {
    param(
        [Parameter(Mandatory)] [string]$PlanPath
    )

    $sections = [ordered]@{}
    $currentSection = '__preamble__'
    $sections[$currentSection] = [System.Collections.Generic.List[string]]::new()
    foreach ($line in @(Get-Content -LiteralPath $PlanPath -Encoding UTF8)) {
        if ($line -match '^##\s+(.*)$') {
            $currentSection = $Matches[1].Trim()
            if (-not $sections.Contains($currentSection)) {
                $sections[$currentSection] = [System.Collections.Generic.List[string]]::new()
            }
            continue
        }
        $sections[$currentSection].Add([string]$line) | Out-Null
    }

    return $sections
}

function Get-VibePlanDerivedExecutionShadow {
    param(
        [Parameter(Mandatory)] [string]$PlanPath,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    $sections = Get-VibePlanSections -PlanPath $PlanPath
    $units = @()
    $sectionOrder = @('Wave Plan', 'Specialist Skill Dispatch Plan', 'Verification Commands', 'Phase Cleanup Contract')
    $unitIndex = 0

    foreach ($sectionName in $sectionOrder) {
        if (-not $sections.Contains($sectionName)) {
            continue
        }

        foreach ($line in @($sections[$sectionName])) {
            $trimmed = [string]$line.Trim()
            if (-not $trimmed.StartsWith('-')) {
                continue
            }

            $unitIndex += 1
            $classification = 'advisory_only_unit'
            $reason = 'narrative_bullet_without_executable_command'
            $inlineCommands = [regex]::Matches($trimmed, '`([^`]+)`') | ForEach-Object { $_.Groups[1].Value }

            if ($sectionName -eq 'Specialist Skill Dispatch Plan') {
                $classification = 'specialist_dispatch_unit'
                $reason = 'bounded_native_specialist_dispatch_declared'
            } elseif (@($inlineCommands).Count -gt 0) {
                $classification = 'executable_unit'
                $reason = 'inline_command_detected'
            } elseif ($sectionName -eq 'Verification Commands') {
                $classification = 'ambiguous_unit'
                $reason = 'verification intent present but command not frozen'
            } elseif ($sectionName -eq 'Phase Cleanup Contract') {
                $classification = 'advisory_only_unit'
                $reason = 'cleanup requirement declared but execution delegated to cleanup stage'
            }

            $units += [pscustomobject]@{
                unit_id = ('shadow-{0:00}' -f $unitIndex)
                source_section = $sectionName
                line = $trimmed
                classification = $classification
                reason = $reason
                extracted_commands = @($inlineCommands)
            }
        }
    }

    $shadow = [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        run_id = $RunId
        execution_plan_path = $PlanPath
        candidate_unit_count = @($units).Count
        executable_unit_count = @($units | Where-Object { $_.classification -eq 'executable_unit' }).Count
        specialist_dispatch_unit_count = @($units | Where-Object { $_.classification -eq 'specialist_dispatch_unit' }).Count
        advisory_only_unit_count = @($units | Where-Object { $_.classification -eq 'advisory_only_unit' }).Count
        ambiguous_unit_count = @($units | Where-Object { $_.classification -eq 'ambiguous_unit' }).Count
        unsafe_unit_count = @($units | Where-Object { $_.classification -eq 'unsafe_unit' }).Count
        non_executable_narrative_count = @($units | Where-Object { $_.classification -eq 'non_executable_narrative' }).Count
        units = @($units)
        proof_class = 'structure'
        promotion_suitable = $false
    }

    $shadowPath = Join-Path $SessionRoot 'plan-derived-execution-shadow.json'
    Write-VibeJsonArtifact -Path $shadowPath -Value $shadow

    return [pscustomobject]@{
        path = $shadowPath
        payload = $shadow
    }
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$grade = Get-VibeInternalGrade -Task $Task
$requirementPath = if (-not [string]::IsNullOrWhiteSpace($RequirementDocPath)) { $RequirementDocPath } else { Get-VibeRequirementDocPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot }
$planPath = if (-not [string]::IsNullOrWhiteSpace($ExecutionPlanPath)) { $ExecutionPlanPath } else { Get-VibeExecutionPlanPath -RepoRoot $runtime.repo_root -Task $Task -ArtifactRoot $ArtifactRoot }
$runtimeInputPath = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath)) { $RuntimeInputPacketPath } else { Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot }
$runtimeInputPacket = if (Test-Path -LiteralPath $runtimeInputPath) {
    Get-Content -LiteralPath $runtimeInputPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$hierarchyState = Get-VibeHierarchyState `
    -GovernanceScope $(if ($runtimeInputPacket) { [string]$runtimeInputPacket.governance_scope } else { $GovernanceScope }) `
    -RunId $RunId `
    -RootRunId $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.root_run_id } else { $RootRunId }) `
    -ParentRunId $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.parent_run_id } else { $ParentRunId }) `
    -ParentUnitId $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.parent_unit_id } else { $ParentUnitId }) `
    -InheritedRequirementDocPath $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.inherited_requirement_doc_path } else { $RequirementDocPath }) `
    -InheritedExecutionPlanPath $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.inherited_execution_plan_path } else { $ExecutionPlanPath }) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract

$policy = $runtime.benchmark_execution_policy
$proofRegistry = $runtime.proof_class_registry
$profile = Get-VibeBenchmarkProfileById -BenchmarkPolicy $policy -ProfileId ([string]$policy.default_profile_id)

$logsRoot = Join-Path $sessionRoot 'execution-logs'
$resultsRoot = Join-Path $sessionRoot 'execution-results'
$proofRoot = Join-Path $sessionRoot ([string]$profile.proof_bundle_dirname)
New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null
New-Item -ItemType Directory -Path $proofRoot -Force | Out-Null

$tokens = @{
    '${REPO_ROOT}' = [System.IO.Path]::GetFullPath($runtime.repo_root)
    '${SESSION_ROOT}' = [System.IO.Path]::GetFullPath($sessionRoot)
    '${REQUIREMENT_DOC}' = [System.IO.Path]::GetFullPath($requirementPath)
    '${EXECUTION_PLAN}' = [System.IO.Path]::GetFullPath($planPath)
    '${RUN_ID}' = [string]$RunId
    '${ROOT_RUN_ID}' = [string]$hierarchyState.root_run_id
}
$planShadow = Get-VibePlanDerivedExecutionShadow -PlanPath $planPath -RunId $RunId -SessionRoot $sessionRoot
$specialistRecommendations = if ($runtimeInputPacket) { @($runtimeInputPacket.specialist_recommendations) } else { @() }
$approvedDispatch = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.approved_dispatch) } else { @() }
$localSuggestions = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.local_specialist_suggestions) } else { @() }
$executionTopologyPath = Get-VibeExecutionTopologyPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$executionTopology = if (Test-Path -LiteralPath $executionTopologyPath) {
    Get-Content -LiteralPath $executionTopologyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $derivedTopology = New-VibeExecutionTopology `
        -RunId $RunId `
        -Grade $grade `
        -GovernanceScope ([string]$hierarchyState.governance_scope) `
        -BenchmarkPolicy $policy `
        -TopologyPolicy $runtime.execution_topology_policy `
        -ApprovedDispatch @($approvedDispatch)
    Write-VibeJsonArtifact -Path $executionTopologyPath -Value $derivedTopology
    $derivedTopology
}
$specialistSkills = @($approvedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$escalationRequired = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { [bool]$runtimeInputPacket.specialist_dispatch.escalation_required } else { $false }
$escalationPath = $null
if ([string]$hierarchyState.governance_scope -eq 'child' -and $escalationRequired) {
    $escalation = [pscustomobject]@{
        run_id = $RunId
        governance_scope = [string]$hierarchyState.governance_scope
        root_run_id = [string]$hierarchyState.root_run_id
        parent_run_id = if ($null -eq $hierarchyState.parent_run_id) { $null } else { [string]$hierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $hierarchyState.parent_unit_id) { $null } else { [string]$hierarchyState.parent_unit_id }
        approval_owner = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { [string]$runtimeInputPacket.specialist_dispatch.approval_owner } else { 'root_vibe' }
        status = 'root_approval_required'
        requested_specialist_skill_ids = @($localSuggestions | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        local_specialist_suggestions = @($localSuggestions)
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    $escalationPath = Join-Path $sessionRoot 'specialist-escalation-request.json'
    Write-VibeJsonArtifact -Path $escalationPath -Value $escalation
}

$waveReceipts = @()
$resultPaths = @()
$executedUnitCount = 0
$successfulUnitCount = 0
$failedUnitCount = 0
$timedOutUnitCount = 0
$plannedUnitCount = 0
$delegatedLaneCount = 0
$reviewReceiptCount = 0
$reviewReceiptPaths = @()
$executedSpecialistUnits = @()
$parallelCandidateUnitCount = 0
$parallelUnitsExecutedCount = 0
$parallelExecutedUnitIds = @()
$parallelExecutionWindows = @()
$serialExecutionOrder = @()
$executedThroughChildLanes = 0
$helperScriptPath = Join-Path $PSScriptRoot 'Invoke-DelegatedLaneUnit.ps1'

foreach ($topologyWave in @($executionTopology.waves)) {
    $waveStartedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $waveUnitReceipts = @()
    $stepReceipts = @()
    $plannedWaveUnits = [int](($topologyWave.steps | ForEach-Object { @($_.units).Count } | Measure-Object -Sum).Sum)
    $plannedUnitCount += $plannedWaveUnits

    foreach ($step in @($topologyWave.steps)) {
        $stepStartedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        $stepMode = [string]$step.execution_mode
        $stepOutcomes = @()

        if ($stepMode -eq 'bounded_parallel') {
            $parallelCandidateUnitCount += @($step.units).Count
            $currentBatch = @()
            $currentScopes = @{}
            $batches = @()

            foreach ($laneEntry in @($step.units)) {
                $scopeKey = [string]$laneEntry.write_scope
                $shouldFlush = ($currentBatch.Count -ge [int]$step.max_parallel_units) -or $currentScopes.ContainsKey($scopeKey)
                if ($shouldFlush -and $currentBatch.Count -gt 0) {
                    $batches += ,@($currentBatch)
                    $currentBatch = @()
                    $currentScopes = @{}
                }
                $currentBatch += $laneEntry
                $currentScopes[$scopeKey] = $true
            }
            if ($currentBatch.Count -gt 0) {
                $batches += ,@($currentBatch)
            }

            foreach ($batch in @($batches)) {
                if (@($batch).Count -ge 2 -and [string]$hierarchyState.governance_scope -eq 'root') {
                    $handles = @()
                    foreach ($laneEntry in @($batch)) {
                        $laneRuntime = New-VibeDelegatedLaneSpec `
                            -SessionRoot $sessionRoot `
                            -RunId $RunId `
                            -Mode $Mode `
                            -HierarchyState $hierarchyState `
                            -RequirementPath $requirementPath `
                            -PlanPath $planPath `
                            -Tokens $tokens `
                            -DefaultTimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds) `
                            -LaneEntry $laneEntry
                        $delegatedLaneCount += 1
                        $executedThroughChildLanes += 1
                        $handles += Start-VibeDelegatedLaneProcess -LaneRuntime $laneRuntime -HelperScriptPath $helperScriptPath
                    }

                    $windowOutcomes = @()
                    foreach ($handle in @($handles)) {
                        $windowOutcomes += Wait-VibeDelegatedLaneProcess -Handle $handle -TimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds)
                    }
                    $stepOutcomes += $windowOutcomes
                    $parallelUnitsExecutedCount += @($windowOutcomes).Count
                    $parallelExecutedUnitIds += @($windowOutcomes | ForEach-Object {
                        if ($_.lane_result) { [string]$_.lane_result.unit_id } else { [string]$_.lane_entry.source_unit_id }
                    })
                    $parallelExecutionWindows += [pscustomobject]@{
                        wave_id = [string]$topologyWave.wave_id
                        step_id = [string]$step.step_id
                        unit_ids = @($windowOutcomes | ForEach-Object {
                            if ($_.lane_result) { [string]$_.lane_result.unit_id } else { [string]$_.lane_entry.source_unit_id }
                        })
                    }
                } else {
                    foreach ($laneEntry in @($batch)) {
                        $outcome = if ([string]$hierarchyState.governance_scope -eq 'root' -and [string]$executionTopology.delegation_mode -ne 'none') {
                            $laneRuntime = New-VibeDelegatedLaneSpec `
                                -SessionRoot $sessionRoot `
                                -RunId $RunId `
                                -Mode $Mode `
                                -HierarchyState $hierarchyState `
                                -RequirementPath $requirementPath `
                                -PlanPath $planPath `
                                -Tokens $tokens `
                                -DefaultTimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds) `
                                -LaneEntry $laneEntry
                            $delegatedLaneCount += 1
                            $executedThroughChildLanes += 1
                            $handle = Start-VibeDelegatedLaneProcess -LaneRuntime $laneRuntime -HelperScriptPath $helperScriptPath
                            Wait-VibeDelegatedLaneProcess -Handle $handle -TimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds)
                        } else {
                            Invoke-VibeDirectLaneEntry `
                                -LaneEntry $laneEntry `
                                -RepoRoot $runtime.repo_root `
                                -SessionRoot $sessionRoot `
                                -Tokens $tokens `
                                -DefaultTimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds) `
                                -Mode $Mode `
                                -RequirementPath $requirementPath `
                                -PlanPath $planPath `
                                -HierarchyState $hierarchyState `
                                -RunId $RunId
                        }
                        $stepOutcomes += $outcome
                        $serialExecutionOrder += if ($outcome.lane_result) { [string]$outcome.lane_result.unit_id } else { [string]$laneEntry.source_unit_id }
                    }
                }
            }
        } else {
            foreach ($laneEntry in @($step.units)) {
                $outcome = if ([string]$hierarchyState.governance_scope -eq 'root' -and [string]$executionTopology.delegation_mode -ne 'none' -and [string]$laneEntry.lane_kind -eq 'benchmark_unit') {
                    $laneRuntime = New-VibeDelegatedLaneSpec `
                        -SessionRoot $sessionRoot `
                        -RunId $RunId `
                        -Mode $Mode `
                        -HierarchyState $hierarchyState `
                        -RequirementPath $requirementPath `
                        -PlanPath $planPath `
                        -Tokens $tokens `
                        -DefaultTimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds) `
                        -LaneEntry $laneEntry
                    $delegatedLaneCount += 1
                    $executedThroughChildLanes += 1
                    $handle = Start-VibeDelegatedLaneProcess -LaneRuntime $laneRuntime -HelperScriptPath $helperScriptPath
                    Wait-VibeDelegatedLaneProcess -Handle $handle -TimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds)
                } else {
                    Invoke-VibeDirectLaneEntry `
                        -LaneEntry $laneEntry `
                        -RepoRoot $runtime.repo_root `
                        -SessionRoot $sessionRoot `
                        -Tokens $tokens `
                        -DefaultTimeoutSeconds ([int]$policy.scheduler.default_timeout_seconds) `
                        -Mode $Mode `
                        -RequirementPath $requirementPath `
                        -PlanPath $planPath `
                        -HierarchyState $hierarchyState `
                        -RunId $RunId
                }
                $stepOutcomes += $outcome
                $serialExecutionOrder += if ($outcome.lane_result) { [string]$outcome.lane_result.unit_id } else { [string]$laneEntry.source_unit_id }

                if ([string]$step.review_mode -eq 'two_stage_after_unit' -and $outcome.lane_receipt) {
                    foreach ($reviewKind in @('spec', 'quality')) {
                        $review = New-VibeReviewReceipt `
                            -SessionRoot $sessionRoot `
                            -LaneId ([string]$outcome.lane_id) `
                            -ReviewKind $reviewKind `
                            -LaneReceipt $outcome.lane_receipt `
                            -SourcePath ([string]$outcome.lane_receipt_path)
                        $reviewReceiptCount += 1
                        $reviewReceiptPaths += [string]$review.receipt_path
                    }
                }
            }
        }

        foreach ($outcome in @($stepOutcomes)) {
            $unitReceipt = ConvertTo-VibeExecutedUnitReceipt `
                -WaveId ([string]$topologyWave.wave_id) `
                -StepId ([string]$step.step_id) `
                -Outcome $outcome
            $waveUnitReceipts += $unitReceipt
            $resultPaths += [string]$unitReceipt.result_path
            $executedUnitCount += 1
            if ([bool]$unitReceipt.verification_passed) {
                $successfulUnitCount += 1
            } elseif ([bool]$unitReceipt.timed_out) {
                $timedOutUnitCount += 1
                $failedUnitCount += 1
            } else {
                $failedUnitCount += 1
            }

            if ([string]$unitReceipt.lane_kind -eq 'specialist_dispatch') {
                $executedSpecialistUnits += [pscustomobject]@{
                    unit_id = [string]$unitReceipt.unit_id
                    skill_id = [string]$unitReceipt.skill_id
                    result_path = [string]$unitReceipt.result_path
                    verification_passed = [bool]$unitReceipt.verification_passed
                    execution_driver = [string]$unitReceipt.execution_driver
                    live_native_execution = [bool]$unitReceipt.live_native_execution
                    degraded = [bool]$unitReceipt.degraded
                    lane_receipt_path = if ($unitReceipt.lane_receipt_path) { [string]$unitReceipt.lane_receipt_path } else { $null }
                }
            }
        }

        $stepReceipts += [pscustomobject]@{
            step_id = [string]$step.step_id
            execution_mode = $stepMode
            started_at = $stepStartedAt
            finished_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            planned_unit_count = @($step.units).Count
            executed_unit_count = @($stepOutcomes).Count
            status = if (@($stepOutcomes | Where-Object { -not $_.lane_result.verification_passed }).Count -eq 0) { 'completed' } else { 'failed' }
            units = @($waveUnitReceipts | Where-Object { [string]$_.step_id -eq [string]$step.step_id })
        }
    }

    $waveReceipts += [pscustomobject]@{
        wave_id = [string]$topologyWave.wave_id
        description = [string]$topologyWave.description
        status = if (@($waveUnitReceipts | Where-Object { -not $_.verification_passed }).Count -eq 0) { 'completed' } else { 'failed' }
        started_at = $waveStartedAt
        finished_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        planned_unit_count = [int]$plannedWaveUnits
        executed_unit_count = @($waveUnitReceipts).Count
        steps = @($stepReceipts)
        units = @($waveUnitReceipts)
    }
}

$effectiveUnitExecution = if ($parallelUnitsExecutedCount -gt 0 -and ($executedUnitCount -gt $parallelUnitsExecutedCount)) {
    'mixed'
} elseif ($parallelUnitsExecutedCount -gt 0) {
    'bounded_parallel'
} else {
    'sequential'
}

$baseStatus = if ($failedUnitCount -eq 0 -and $executedUnitCount -ge [int]$profile.expected_minimum_units) { 'completed' } elseif ($executedUnitCount -eq 0) { 'failed' } else { 'completed_with_failures' }
$liveSpecialistUnits = @($executedSpecialistUnits | Where-Object { [bool]$_.live_native_execution })
$degradedSpecialistUnits = @($executedSpecialistUnits | Where-Object { [bool]$_.degraded })
$totalSpecialistDispatchOutcomeCount = @($executedSpecialistUnits).Count
$effectiveSpecialistExecutionStatus = if (@($liveSpecialistUnits).Count -gt 0) { 'live_native_executed' } elseif (@($degradedSpecialistUnits).Count -gt 0) { 'explicitly_degraded' } else { 'none' }
$executionManifest = [pscustomobject]@{
    stage = 'plan_execute'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    internal_grade = $grade
    scheduler_kind = [string]$policy.scheduler.kind
    profile_id = [string]$profile.id
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    execution_topology_path = $executionTopologyPath
    runtime_input_packet_path = $runtimeInputPath
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    planned_wave_count = @($profile.waves).Count
    planned_unit_count = $plannedUnitCount
    executed_unit_count = $executedUnitCount
    successful_unit_count = $successfulUnitCount
    failed_unit_count = $failedUnitCount
    timed_out_unit_count = $timedOutUnitCount
    proof_class = [string]$proofRegistry.artifact_class_defaults.execution_manifest
    promotion_suitable = [string]$proofRegistry.promotion_suitability.runtime
    hierarchy = [pscustomobject]@{
        governance_scope = [string]$hierarchyState.governance_scope
        root_run_id = [string]$hierarchyState.root_run_id
        parent_run_id = if ($null -eq $hierarchyState.parent_run_id) { $null } else { [string]$hierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $hierarchyState.parent_unit_id) { $null } else { [string]$hierarchyState.parent_unit_id }
        inherited_requirement_doc_path = if ($null -eq $hierarchyState.inherited_requirement_doc_path) { $null } else { [string]$hierarchyState.inherited_requirement_doc_path }
        inherited_execution_plan_path = if ($null -eq $hierarchyState.inherited_execution_plan_path) { $null } else { [string]$hierarchyState.inherited_execution_plan_path }
    }
    authority = [pscustomobject]@{
        canonical_requirement_write_allowed = [bool]$hierarchyState.allow_requirement_freeze
        canonical_plan_write_allowed = [bool]$hierarchyState.allow_plan_freeze
        global_dispatch_allowed = [bool]$hierarchyState.allow_global_dispatch
        completion_claim_allowed = [bool]$hierarchyState.allow_completion_claim
    }
    route_runtime_alignment = [pscustomobject]@{
        router_selected_skill = if ($runtimeInputPacket) { [string]$runtimeInputPacket.route_snapshot.selected_skill } else { $null }
        runtime_selected_skill = if ($runtimeInputPacket) { [string]$runtimeInputPacket.authority_flags.explicit_runtime_skill } else { 'vibe' }
        skill_mismatch = if ($runtimeInputPacket) { [bool]$runtimeInputPacket.divergence_shadow.skill_mismatch } else { $false }
        confirm_required = if ($runtimeInputPacket) { [bool]$runtimeInputPacket.route_snapshot.confirm_required } else { $false }
    }
    execution_topology = [pscustomobject]@{
        path = $executionTopologyPath
        delegation_mode = [string]$executionTopology.delegation_mode
        wave_execution = 'sequential'
        step_execution = 'sequential'
        unit_execution = $effectiveUnitExecution
        max_parallel_units = [int]$executionTopology.max_parallel_units
        child_lane_unit_count = [int]$executedThroughChildLanes
        parallel_candidate_unit_count = [int]$parallelCandidateUnitCount
        parallel_units_executed_count = [int]$parallelUnitsExecutedCount
        parallel_executed_unit_ids = @($parallelExecutedUnitIds | Select-Object -Unique)
        parallel_execution_windows = @($parallelExecutionWindows)
        serial_execution_order = @($serialExecutionOrder)
        review_mode = [string]$executionTopology.review_mode
        two_stage_review = [pscustomobject]@{
            enabled = [bool]([string]$executionTopology.review_mode -eq 'two_stage_after_unit')
            review_receipt_count = [int]$reviewReceiptCount
            review_receipt_paths = @($reviewReceiptPaths)
        }
    }
    plan_shadow = [pscustomobject]@{
        path = $planShadow.path
        candidate_unit_count = [int]$planShadow.payload.candidate_unit_count
        executable_unit_count = [int]$planShadow.payload.executable_unit_count
        specialist_dispatch_unit_count = [int]$planShadow.payload.specialist_dispatch_unit_count
        advisory_only_unit_count = [int]$planShadow.payload.advisory_only_unit_count
        ambiguous_unit_count = [int]$planShadow.payload.ambiguous_unit_count
    }
    specialist_accounting = [pscustomobject]@{
        recommendation_count = @($specialistRecommendations).Count
        specialist_skill_count = @($specialistSkills).Count
        specialist_skills = @($specialistSkills)
        native_usage_required = [bool](@($specialistRecommendations | Where-Object { $_.native_usage_required }).Count -gt 0)
        execution_mode = if (@($approvedDispatch).Count -gt 0) { 'native_bounded_units' } else { [string]$executionTopology.specialist_execution_mode }
        effective_execution_status = $effectiveSpecialistExecutionStatus
        dispatch_unit_count = [int]$planShadow.payload.specialist_dispatch_unit_count
        recommendations = @($specialistRecommendations)
        approved_dispatch_count = @($approvedDispatch).Count
        approved_dispatch = @($approvedDispatch)
        executed_specialist_unit_count = @($liveSpecialistUnits).Count
        executed_specialist_units = @($liveSpecialistUnits)
        degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
        degraded_specialist_units = @($degradedSpecialistUnits)
        specialist_dispatch_outcomes = @($executedSpecialistUnits)
        local_suggestion_count = @($localSuggestions).Count
        local_specialist_suggestions = @($localSuggestions)
        escalation_required = [bool]$escalationRequired
        escalation_request_path = $escalationPath
    }
    status = if ([string]$hierarchyState.governance_scope -eq 'child' -and $baseStatus -eq 'completed') { 'completed_local_scope' } else { $baseStatus }
    waves = @($waveReceipts)
}

$executionManifestPath = Join-Path $sessionRoot 'execution-manifest.json'
Write-VibeJsonArtifact -Path $executionManifestPath -Value $executionManifest

$proofManifest = [pscustomobject]@{
    bundle_kind = 'benchmark_autonomous_execution_proof'
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    run_id = $RunId
    mode = $Mode
    task = $Task
    session_root = $sessionRoot
    execution_manifest_path = $executionManifestPath
    plan_shadow_path = $planShadow.path
    execution_topology_path = $executionTopologyPath
    result_paths = @($resultPaths)
    executed_unit_count = $executedUnitCount
    successful_unit_count = $successfulUnitCount
    failed_unit_count = $failedUnitCount
    minimum_units_required = [int]$profile.expected_minimum_units
    proof_class = [string]$proofRegistry.artifact_class_defaults.benchmark_proof_manifest
    promotion_suitable = [string]$proofRegistry.promotion_suitability.runtime
    specialist_recommendation_count = @($specialistRecommendations).Count
    specialist_dispatch_unit_count = [int]$planShadow.payload.specialist_dispatch_unit_count
    executed_specialist_unit_count = @($liveSpecialistUnits).Count
    degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
    specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
    specialist_execution_status = $effectiveSpecialistExecutionStatus
    delegated_lane_count = [int]$delegatedLaneCount
    review_receipt_count = [int]$reviewReceiptCount
    governance_scope = [string]$hierarchyState.governance_scope
    escalation_required = [bool]$escalationRequired
    proof_passed = [bool](($failedUnitCount -eq 0) -and ($executedUnitCount -ge [int]$profile.expected_minimum_units))
}
$proofManifestPath = Join-Path $proofRoot 'manifest.json'
Write-VibeJsonArtifact -Path $proofManifestPath -Value $proofManifest

$proofLines = @(
    '# Benchmark Autonomous Proof',
    '',
    ('- run_id: `{0}`' -f $RunId),
    ('- mode: `{0}`' -f $Mode),
    ('- profile: `{0}`' -f ([string]$profile.id)),
    ('- proof_class: `{0}`' -f ([string]$proofManifest.proof_class)),
    ('- executed_unit_count: `{0}`' -f $executedUnitCount),
    ('- successful_unit_count: `{0}`' -f $successfulUnitCount),
    ('- failed_unit_count: `{0}`' -f $failedUnitCount),
    ('- delegated_lane_count: `{0}`' -f $delegatedLaneCount),
    ('- review_receipt_count: `{0}`' -f $reviewReceiptCount),
    ('- specialist_recommendation_count: `{0}`' -f @($specialistRecommendations).Count),
    ('- specialist_dispatch_unit_count: `{0}`' -f [int]$planShadow.payload.specialist_dispatch_unit_count),
    ('- executed_specialist_unit_count: `{0}`' -f @($liveSpecialistUnits).Count),
    ('- degraded_specialist_unit_count: `{0}`' -f @($degradedSpecialistUnits).Count),
    ('- specialist_execution_status: `{0}`' -f $effectiveSpecialistExecutionStatus),
    ('- execution_manifest: `{0}`' -f $executionManifestPath),
    ('- execution_topology: `{0}`' -f $executionTopologyPath),
    ('- plan_shadow: `{0}`' -f $planShadow.path),
    ''
)
foreach ($waveReceipt in @($waveReceipts)) {
    $proofLines += @(
        "## $([string]$waveReceipt.wave_id)",
        "- status: $([string]$waveReceipt.status)",
        "- executed_unit_count: $([int]$waveReceipt.executed_unit_count)"
    )
    foreach ($unitReceipt in @($waveReceipt.units)) {
        $proofLines += ('- unit `{0}` -> status `{1}`, exit_code `{2}`' -f ([string]$unitReceipt.unit_id), ([string]$unitReceipt.status), ([int]$unitReceipt.exit_code))
    }
    $proofLines += ''
}
$proofSummaryPath = Join-Path $proofRoot 'operation-record.md'
Write-VibeMarkdownArtifact -Path $proofSummaryPath -Lines $proofLines

$receipt = [pscustomobject]@{
    stage = 'plan_execute'
    run_id = $RunId
    governance_scope = [string]$hierarchyState.governance_scope
    mode = $Mode
    internal_grade = $grade
    status = [string]$executionManifest.status
    requirement_doc_path = $requirementPath
    execution_plan_path = $planPath
    runtime_input_packet_path = $runtimeInputPath
    plan_shadow_path = $planShadow.path
    execution_manifest_path = $executionManifestPath
    benchmark_proof_manifest_path = $proofManifestPath
    execution_topology_path = $executionTopologyPath
    executed_unit_count = $executedUnitCount
    successful_unit_count = $successfulUnitCount
    failed_unit_count = $failedUnitCount
    delegated_lane_count = [int]$delegatedLaneCount
    review_receipt_count = [int]$reviewReceiptCount
    specialist_recommendation_count = @($specialistRecommendations).Count
    specialist_dispatch_unit_count = [int]$planShadow.payload.specialist_dispatch_unit_count
    executed_specialist_unit_count = @($liveSpecialistUnits).Count
    degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
    specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
    specialist_execution_status = $effectiveSpecialistExecutionStatus
    specialist_skills = @($specialistSkills)
    local_specialist_suggestion_count = @($localSuggestions).Count
    escalation_required = [bool]$escalationRequired
    escalation_request_path = $escalationPath
    completion_claim_allowed = [bool]$hierarchyState.allow_completion_claim
    proof_class = [string]$proofRegistry.artifact_class_defaults.execution_manifest
    verification_contract = @(
        'No completion claim without verification evidence.',
        'All subagent prompts must end with $vibe.',
        'Specialist help must preserve native workflow and remain bounded under vibe governance.',
        'Child-governed lanes may not issue final completion claims or mutate canonical requirement/plan truth.',
        'Phase cleanup must run after execution.'
    )
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}

$receiptPath = Join-Path $sessionRoot 'phase-execute.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    receipt_path = $receiptPath
    plan_shadow_path = $planShadow.path
    execution_manifest_path = $executionManifestPath
    execution_topology_path = $executionTopologyPath
    benchmark_proof_manifest_path = $proofManifestPath
    receipt = $receipt
}
