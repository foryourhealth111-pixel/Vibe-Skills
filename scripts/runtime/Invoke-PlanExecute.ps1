param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$RequirementDocPath = '',
    [string]$ExecutionPlanPath = '',
    [string]$RuntimeInputPacketPath = '',
    [string]$ExecutionMemoryContextPath = '',
    [string]$ArtifactRoot = '',
    [AllowEmptyString()] [string]$GovernanceScope = '',
    [AllowEmptyString()] [string]$RootRunId = '',
    [AllowEmptyString()] [string]$ParentRunId = '',
    [AllowEmptyString()] [string]$ParentUnitId = ''
)

Set-StrictMode -Off
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
    $envelopePath = Get-VibeGovernanceArtifactPath -SessionRoot $laneRoot -ArtifactName 'delegation_envelope'
    New-Item -ItemType Directory -Path $laneRoot -Force | Out-Null
    $approvedSpecialists = @()
    if ($LaneEntry.PSObject.Properties.Name -contains 'dispatch' -and $null -ne $LaneEntry.dispatch) {
        $approvedSkillId = [string]$LaneEntry.dispatch.skill_id
        if (-not [string]::IsNullOrWhiteSpace($approvedSkillId)) {
            $approvedSpecialists += $approvedSkillId
        }
    }
    Write-VibeDelegationEnvelope `
        -Path $envelopePath `
        -RootRunId ([string]($HierarchyState.root_run_id)) `
        -ParentRunId $RunId `
        -ParentUnitId ([string]($LaneEntry.source_unit_id)) `
        -ChildRunId $laneId `
        -RequirementDocPath $RequirementPath `
        -ExecutionPlanPath $PlanPath `
        -WriteScope ([string]($LaneEntry.write_scope)) `
        -ApprovedSpecialists @($approvedSpecialists) `
        -ReviewMode ([string]($LaneEntry.review_mode)) | Out-Null
    $laneSpec = [pscustomobject]@{
        lane_id = $laneId
        lane_kind = [string]($LaneEntry.lane_kind)
        lane_root = $laneRoot
        run_id = $laneId
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
        delegation_envelope_path = $envelopePath
        tokens = [pscustomobject]$Tokens
        unit = if ($LaneEntry.PSObject.Properties.Name -contains 'unit') { $LaneEntry.unit } else { $null }
        dispatch = if ($LaneEntry.PSObject.Properties.Name -contains 'dispatch') { $LaneEntry.dispatch } else { $null }
    }
    Write-VibeJsonArtifact -Path $specPath -Value $laneSpec
    return [pscustomobject]@{
        lane_id = $laneId
        lane_root = $laneRoot
        spec_path = $specPath
        repo_root = [string]$laneSpec.repo_root
        lane_entry = $LaneEntry
    }
}

function Resolve-VibeDelegatedLaneWorkingDirectory {
    param(
        [Parameter(Mandatory)] [object]$LaneRuntime
    )

    $requestedLaneRoot = if (
        $LaneRuntime.PSObject.Properties.Name -contains 'lane_root' -and
        -not [string]::IsNullOrWhiteSpace([string]($LaneRuntime.lane_root))
    ) {
        [string]($LaneRuntime.lane_root)
    } else {
        $null
    }
    $resolvedLaneRoot = $null
    $laneRootValid = $false
    if (-not [string]::IsNullOrWhiteSpace($requestedLaneRoot)) {
        try {
            $resolvedLaneRoot = [System.IO.Path]::GetFullPath($requestedLaneRoot)
            $laneRootValid = Test-Path -LiteralPath $resolvedLaneRoot -PathType Container
        } catch {
            $resolvedLaneRoot = $requestedLaneRoot
            $laneRootValid = $false
        }
    }

    $requestedWorkingDirectory = if (
        $LaneRuntime.PSObject.Properties.Name -contains 'repo_root' -and
        -not [string]::IsNullOrWhiteSpace([string]($LaneRuntime.repo_root))
    ) {
        [string]($LaneRuntime.repo_root)
    } else {
        $null
    }

    $resolvedRepoRoot = $null
    $repoRootValid = $false
    if (-not [string]::IsNullOrWhiteSpace($requestedWorkingDirectory)) {
        try {
            $resolvedRepoRoot = [System.IO.Path]::GetFullPath($requestedWorkingDirectory)
            $repoRootValid = Test-Path -LiteralPath $resolvedRepoRoot -PathType Container
        } catch {
            $resolvedRepoRoot = $requestedWorkingDirectory
            $repoRootValid = $false
        }
    }

    $laneRootFallbackReason = if ($laneRootValid) { $null } elseif ([string]::IsNullOrWhiteSpace($requestedLaneRoot)) { 'lane_root_missing' } else { 'lane_root_invalid' }
    $effectiveWorkingDirectory = if ($repoRootValid) {
        $resolvedRepoRoot
    } elseif (-not [string]::IsNullOrWhiteSpace($resolvedLaneRoot)) {
        $resolvedLaneRoot
    } elseif (-not [string]::IsNullOrWhiteSpace($requestedLaneRoot)) {
        $requestedLaneRoot
    } else {
        [System.IO.Path]::GetFullPath('.')
    }
    return [pscustomobject]@{
        lane_root = if (-not [string]::IsNullOrWhiteSpace($resolvedLaneRoot)) { $resolvedLaneRoot } elseif (-not [string]::IsNullOrWhiteSpace($requestedLaneRoot)) { $requestedLaneRoot } else { [System.IO.Path]::GetFullPath('.') }
        requested_lane_root = $requestedLaneRoot
        resolved_lane_root = $resolvedLaneRoot
        lane_root_valid = [bool]$laneRootValid
        lane_root_fallback_reason = if ($null -eq $laneRootFallbackReason) { $null } else { [string]$laneRootFallbackReason }
        requested_working_directory = $requestedWorkingDirectory
        resolved_repo_root = $resolvedRepoRoot
        repo_root_valid = [bool]$repoRootValid
        effective_working_directory = $effectiveWorkingDirectory
        fallback_reason = if ($repoRootValid) {
            if ($null -eq $laneRootFallbackReason) { $null } else { [string]$laneRootFallbackReason }
        } elseif ([string]::IsNullOrWhiteSpace($requestedWorkingDirectory)) {
            'repo_root_missing'
        } else {
            'repo_root_invalid'
        }
    }
}

function Get-VibeDelegatedLanePayloadContractVersion {
    return '1.0'
}

function Resolve-VibeDelegatedLanePayload {
    param(
        [AllowEmptyString()] [string]$StdoutText = '',
        [Parameter(Mandatory)] [string]$PayloadPath
    )

    $payloadCandidates = @()
    $parseFailures = @()
    $payloadText = ($StdoutText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
    if (-not [string]::IsNullOrWhiteSpace($payloadText)) {
        $payloadCandidates += [pscustomobject]@{
            source = 'stdout_terminal_json'
            content = $payloadText
        }
    }

    if (Test-Path -LiteralPath $PayloadPath) {
        try {
            $payloadCandidates += [pscustomobject]@{
                source = 'lane_payload_artifact'
                content = Get-Content -LiteralPath $PayloadPath -Raw -Encoding UTF8
            }
        } catch {
            $parseFailures += 'lane_payload_artifact:read_failed'
        }
    }

    foreach ($candidate in @($payloadCandidates)) {
        if ([string]::IsNullOrWhiteSpace([string]$candidate.content)) {
            $parseFailures += ('{0}:empty' -f [string]$candidate.source)
            continue
        }

        try {
            $payload = [string]$candidate.content | ConvertFrom-Json
        } catch {
            $parseFailures += ('{0}:invalid_json' -f [string]$candidate.source)
            continue
        }

        if (-not ($payload.PSObject.Properties.Name -contains 'lane_receipt_path')) {
            $parseFailures += ('{0}:missing_lane_receipt_path' -f [string]$candidate.source)
            continue
        }
        $laneReceiptPath = [string]$payload.lane_receipt_path
        if ([string]::IsNullOrWhiteSpace($laneReceiptPath)) {
            $parseFailures += ('{0}:empty_lane_receipt_path' -f [string]$candidate.source)
            continue
        }

        return [pscustomobject]@{
            payload = $payload
            source = [string]$candidate.source
            parse_failures = @($parseFailures)
        }
    }

    return [pscustomobject]@{
        payload = $null
        source = $null
        parse_failures = @($parseFailures)
    }
}

function Start-VibeDelegatedLaneProcess {
    param(
        [Parameter(Mandatory)] [object]$LaneRuntime,
        [Parameter(Mandatory)] [string]$HelperScriptPath
    )

    $stdoutPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-process.stdout.log'
    $stderrPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-process.stderr.log'
    $payloadPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-payload.json'
    $launchMetadataPath = Join-Path ([string]($LaneRuntime.lane_root)) 'lane-launch.json'
    $invocation = Get-VgoPowerShellFileInvocation -ScriptPath $HelperScriptPath -ArgumentList @('-LaneSpecPath', ([string]($LaneRuntime.spec_path))) -NoProfile
    $workingDirectoryInfo = Resolve-VibeDelegatedLaneWorkingDirectory -LaneRuntime $LaneRuntime

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = [string]($invocation.host_path)
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.WorkingDirectory = [string]$workingDirectoryInfo.effective_working_directory

    $quotedArguments = foreach ($argument in @($invocation.arguments)) {
        $text = [string]$argument
        if ($text -match '[\s"]') {
            '"' + ($text -replace '"', '\"') + '"'
        } else {
            $text
        }
    }
    $startInfo.Arguments = [string]::Join(' ', @($quotedArguments))

    $launchMetadata = [pscustomobject]@{
        lane_id = [string]($LaneRuntime.lane_id)
        lane_root = [string]($LaneRuntime.lane_root)
        spec_path = [string]($LaneRuntime.spec_path)
        helper_script_path = [string]$HelperScriptPath
        host_kind = if ($invocation.PSObject.Properties.Name -contains 'host_kind') { [string]$invocation.host_kind } else { 'pwsh' }
        powershell_host_path = [string]($invocation.host_path)
        fallback_used = [bool]$(if ($invocation.PSObject.Properties.Name -contains 'fallback_used') { $invocation.fallback_used } else { $false })
        resolved_command = [string]($invocation.host_path)
        resolved_arguments = @($invocation.arguments)
        arguments_render_mode = 'RenderedString'
        payload_contract_version = Get-VibeDelegatedLanePayloadContractVersion
        requested_lane_root = if ($null -eq $workingDirectoryInfo.requested_lane_root) { $null } else { [string]$workingDirectoryInfo.requested_lane_root }
        resolved_lane_root = if ($null -eq $workingDirectoryInfo.resolved_lane_root) { $null } else { [string]$workingDirectoryInfo.resolved_lane_root }
        lane_root_valid = [bool]$workingDirectoryInfo.lane_root_valid
        lane_root_fallback_reason = if ($null -eq $workingDirectoryInfo.lane_root_fallback_reason) { $null } else { [string]$workingDirectoryInfo.lane_root_fallback_reason }
        requested_working_directory = if ($null -eq $workingDirectoryInfo.requested_working_directory) { $null } else { [string]$workingDirectoryInfo.requested_working_directory }
        resolved_repo_root = if ($null -eq $workingDirectoryInfo.resolved_repo_root) { $null } else { [string]$workingDirectoryInfo.resolved_repo_root }
        effective_working_directory = [string]$workingDirectoryInfo.effective_working_directory
        resolved_working_directory = [string]$workingDirectoryInfo.effective_working_directory
        repo_root_valid = [bool]$workingDirectoryInfo.repo_root_valid
        fallback_reason = if ($null -eq $workingDirectoryInfo.fallback_reason) { $null } else { [string]$workingDirectoryInfo.fallback_reason }
        preflight = [pscustomobject]@{
            executable_exists = [bool](Test-Path -LiteralPath ([string]($invocation.host_path)))
            executable_is_file = [bool](Test-Path -LiteralPath ([string]($invocation.host_path)) -PathType Leaf)
            working_directory_exists = [bool](Test-Path -LiteralPath ([string]$workingDirectoryInfo.effective_working_directory))
            working_directory_is_directory = [bool](Test-Path -LiteralPath ([string]$workingDirectoryInfo.effective_working_directory) -PathType Container)
            script_exists = [bool](Test-Path -LiteralPath ([string]$HelperScriptPath))
            script_is_file = [bool](Test-Path -LiteralPath ([string]$HelperScriptPath) -PathType Leaf)
            script_used_as_executable = [bool]([string]($invocation.host_path) -eq [string]$HelperScriptPath)
        }
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        payload_path = $payloadPath
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $launchMetadataPath -Value $launchMetadata

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
        payload_path = $payloadPath
        launch_metadata_path = $launchMetadataPath
        requested_working_directory = if ($null -eq $workingDirectoryInfo.requested_working_directory) { $null } else { [string]$workingDirectoryInfo.requested_working_directory }
        effective_working_directory = [string]$workingDirectoryInfo.effective_working_directory
        repo_root_valid = [bool]$workingDirectoryInfo.repo_root_valid
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

    $processExitCode = if ($timedOut) { -1 } else { [int]($Handle.process.ExitCode) }
    $payloadRecovery = Resolve-VibeDelegatedLanePayload -StdoutText $stdoutText -PayloadPath ([string]($Handle.payload_path))
    if ($timedOut -or $processExitCode -ne 0 -or $null -eq $payloadRecovery.payload) {
        $failureReasons = @()
        if ($timedOut) {
            $failureReasons += 'timeout'
        }
        if ($processExitCode -ne 0) {
            $failureReasons += ('exit_code={0}' -f $processExitCode)
        }
        if ($null -eq $payloadRecovery.payload) {
            $failureReasons += 'payload_unavailable'
        }
        if (@($payloadRecovery.parse_failures).Count -gt 0) {
            $failureReasons += ('payload_parse_failures={0}' -f ([string]::Join(', ', @($payloadRecovery.parse_failures))))
        }

        $message = @(
            ('Delegated lane payload handoff failed for lane_id={0}' -f ([string]($Handle.lane_id))),
            ('reasons={0}' -f ([string]::Join(', ', @($failureReasons)))),
            ('effective_working_directory={0}' -f [string]($Handle.effective_working_directory)),
            ('requested_working_directory={0}' -f $(if ($Handle.requested_working_directory) { [string]$Handle.requested_working_directory } else { '<none>' })),
            ('stdout_path={0}' -f [string]($Handle.stdout_path)),
            ('stderr_path={0}' -f [string]($Handle.stderr_path)),
            ('payload_path={0}' -f [string]($Handle.payload_path))
        ) -join '; '
        $Handle.process.Dispose()
        throw $message
    }

    $payload = $payloadRecovery.payload
    try {
        $laneReceipt = Get-Content -LiteralPath ([string]($payload.lane_receipt_path)) -Raw -Encoding UTF8 | ConvertFrom-Json
        $laneResult = if ($payload.lane_result_path -and (Test-Path -LiteralPath ([string]($payload.lane_result_path)))) {
            Get-Content -LiteralPath ([string]($payload.lane_result_path)) -Raw -Encoding UTF8 | ConvertFrom-Json
        } else {
            $null
        }
    } finally {
        $Handle.process.Dispose()
    }

    return [pscustomobject]@{
        lane_id = [string]($Handle.lane_id)
        lane_entry = $Handle.lane_entry
        exit_code = $processExitCode
        timed_out = [bool]$timedOut
        stdout_path = [string]($Handle.stdout_path)
        stderr_path = [string]($Handle.stderr_path)
        payload_path = [string]($Handle.payload_path)
        payload_source = [string]$payloadRecovery.source
        effective_working_directory = [string]($Handle.effective_working_directory)
        requested_working_directory = if ($Handle.requested_working_directory) { [string]$Handle.requested_working_directory } else { $null }
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
        'execution_unit' {
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
        dispatch_phase = if ([string]$Outcome.lane_entry.lane_kind -eq 'specialist_dispatch' -and $Outcome.lane_entry.dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$Outcome.lane_entry.dispatch.dispatch_phase } else { $null }
        binding_profile = if ([string]$Outcome.lane_entry.lane_kind -eq 'specialist_dispatch' -and $Outcome.lane_entry.dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$Outcome.lane_entry.dispatch.binding_profile } else { $null }
        lane_policy = if ([string]$Outcome.lane_entry.lane_kind -eq 'specialist_dispatch' -and $Outcome.lane_entry.dispatch.PSObject.Properties.Name -contains 'lane_policy') { [string]$Outcome.lane_entry.dispatch.lane_policy } else { $null }
        write_scope = [string]$Outcome.lane_entry.write_scope
        execution_driver = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'execution_driver') { [string]$Outcome.lane_result.execution_driver } else { $null }
        live_native_execution = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'live_native_execution') { [bool]$Outcome.lane_result.live_native_execution } else { $false }
        degraded = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'degraded') { [bool]$Outcome.lane_result.degraded } else { $false }
        prompt_path = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'prompt_path' -and -not [string]::IsNullOrWhiteSpace([string]$Outcome.lane_result.prompt_path)) { [string]$Outcome.lane_result.prompt_path } else { $null }
        prompt_injection_complete = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'prompt_injection_complete') { [bool]$Outcome.lane_result.prompt_injection_complete } else { $false }
        missing_prompt_injection_fields = if ($Outcome.lane_result -and $Outcome.lane_result.PSObject.Properties.Name -contains 'missing_prompt_injection_fields') { @($Outcome.lane_result.missing_prompt_injection_fields) } else { @() }
    }
}

function Test-VibeReceiptCountsAsSuccessful {
    param(
        [Parameter(Mandatory)] [object]$Receipt
    )

    if ([bool]$Receipt.verification_passed) {
        return $true
    }

    if (
        [string]$Receipt.lane_kind -eq 'specialist_dispatch' -and
        [bool]$Receipt.degraded -and
        [string]$Receipt.status -eq 'degraded_non_authoritative' -and
        [int]$Receipt.exit_code -eq 0
    ) {
        return $true
    }

    return $false
}

function Resolve-VibeEffectiveSpecialistDispatch {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowEmptyCollection()] [object[]]$ApprovedDispatch = @(),
        [AllowEmptyCollection()] [object[]]$LocalSuggestions = @(),
        [AllowNull()] [object]$SuggestionContract = $null
    )

    $frozenApprovedDispatch = @($ApprovedDispatch)
    $originalLocalSuggestions = @($LocalSuggestions)
    $frozenApprovedSkillIds = @($frozenApprovedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $originalLocalSkillIds = @($originalLocalSuggestions | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $originalEscalationRequired = if ($RuntimeInputPacket -and $RuntimeInputPacket.specialist_dispatch) {
        [bool]$RuntimeInputPacket.specialist_dispatch.escalation_required
    } else {
        @($originalLocalSuggestions).Count -gt 0
    }
    $originalEscalationStatus = if ($RuntimeInputPacket -and $RuntimeInputPacket.specialist_dispatch -and $RuntimeInputPacket.specialist_dispatch.escalation_status) {
        [string]$RuntimeInputPacket.specialist_dispatch.escalation_status
    } elseif ($originalEscalationRequired) {
        'root_approval_required'
    } else {
        'not_required'
    }

    $result = [ordered]@{
        frozen_approved_dispatch = @($frozenApprovedDispatch)
        frozen_approved_skill_ids = @($frozenApprovedSkillIds)
        effective_approved_dispatch = @($frozenApprovedDispatch)
        effective_approved_skill_ids = @($frozenApprovedSkillIds)
        auto_approved_dispatch = @()
        auto_approved_skill_ids = @()
        original_local_specialist_suggestions = @($originalLocalSuggestions)
        original_local_suggestion_skill_ids = @($originalLocalSkillIds)
        residual_local_specialist_suggestions = @($originalLocalSuggestions)
        residual_local_suggestion_skill_ids = @($originalLocalSkillIds)
        escalation_required = [bool]$originalEscalationRequired
        escalation_status = [string]$originalEscalationStatus
        approval_owner = if ($SuggestionContract -and $SuggestionContract.PSObject.Properties.Name -contains 'approval_owner') {
            [string]$SuggestionContract.approval_owner
        } else {
            'root_vibe'
        }
        auto_absorb_gate = [pscustomobject]@{
            enabled = $false
            same_round = $false
            status = if ([string]$HierarchyState.governance_scope -eq 'child' -and @($originalLocalSuggestions).Count -gt 0) { 'disabled' } else { 'not_applicable' }
            approval_source = $null
            auto_approved_skill_ids = @()
            rejected_skill_ids = @()
            rejected_suggestions = @()
            receipt_path = $null
        }
    }

    if ([string]$HierarchyState.governance_scope -ne 'child' -or @($originalLocalSuggestions).Count -eq 0) {
        return [pscustomobject]$result
    }

    $autoAbsorbGate = if ($SuggestionContract -and $SuggestionContract.PSObject.Properties.Name -contains 'auto_absorb_gate') {
        $SuggestionContract.auto_absorb_gate
    } else {
        $null
    }
    if ($null -eq $autoAbsorbGate -or -not [bool]$autoAbsorbGate.enabled) {
        return [pscustomobject]$result
    }

    $sameRound = $true
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'same_round' -and $null -ne $autoAbsorbGate.same_round) {
        $sameRound = [bool]$autoAbsorbGate.same_round
    }
    $approvalSource = if ($autoAbsorbGate.PSObject.Properties.Name -contains 'approval_source' -and -not [string]::IsNullOrWhiteSpace([string]$autoAbsorbGate.approval_source)) {
        [string]$autoAbsorbGate.approval_source
    } else {
        'root_vibe_auto_absorb_gate'
    }
    $result.auto_absorb_gate.enabled = $true
    $result.auto_absorb_gate.same_round = [bool]$sameRound
    $result.auto_absorb_gate.approval_source = $approvalSource

    if (-not $sameRound) {
        $result.auto_absorb_gate.status = 'not_same_round'
        return [pscustomobject]$result
    }

    $requireExistingRootDispatch = $false
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'require_existing_root_dispatch' -and $null -ne $autoAbsorbGate.require_existing_root_dispatch) {
        $requireExistingRootDispatch = [bool]$autoAbsorbGate.require_existing_root_dispatch
    }
    if ($requireExistingRootDispatch -and @($frozenApprovedDispatch).Count -eq 0) {
        $result.auto_absorb_gate.status = 'requires_existing_root_dispatch'
        return [pscustomobject]$result
    }

    $disableEnvName = if ($autoAbsorbGate.PSObject.Properties.Name -contains 'disable_env') { [string]$autoAbsorbGate.disable_env } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($disableEnvName) -and (Test-VibeTruthyEnvironmentValue -Value ([Environment]::GetEnvironmentVariable($disableEnvName)))) {
        $result.auto_absorb_gate.status = ("disabled_via_env:{0}" -f $disableEnvName)
        return [pscustomobject]$result
    }

    $forceEscalationEnvName = if ($autoAbsorbGate.PSObject.Properties.Name -contains 'force_escalation_env') { [string]$autoAbsorbGate.force_escalation_env } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($forceEscalationEnvName) -and (Test-VibeTruthyEnvironmentValue -Value ([Environment]::GetEnvironmentVariable($forceEscalationEnvName)))) {
        $result.auto_absorb_gate.status = ("forced_escalation_via_env:{0}" -f $forceEscalationEnvName)
        return [pscustomobject]$result
    }

    $requiredRuntimeSkill = if ($autoAbsorbGate.PSObject.Properties.Name -contains 'required_runtime_skill') {
        [string]$autoAbsorbGate.required_runtime_skill
    } else {
        ''
    }
    if (-not [string]::IsNullOrWhiteSpace($requiredRuntimeSkill)) {
        $effectiveRuntimeSkill = if ($RuntimeInputPacket -and $RuntimeInputPacket.authority_flags) {
            [string]$RuntimeInputPacket.authority_flags.explicit_runtime_skill
        } else {
            'vibe'
        }
        if (-not [string]::Equals($effectiveRuntimeSkill, $requiredRuntimeSkill, [System.StringComparison]::OrdinalIgnoreCase)) {
            $result.auto_absorb_gate.status = 'runtime_authority_mismatch'
            return [pscustomobject]$result
        }
    }

    $requireKnownRecommendation = $true
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'require_known_recommendation' -and $null -ne $autoAbsorbGate.require_known_recommendation) {
        $requireKnownRecommendation = [bool]$autoAbsorbGate.require_known_recommendation
    }
    $requireNativeWorkflow = $true
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'require_native_workflow' -and $null -ne $autoAbsorbGate.require_native_workflow) {
        $requireNativeWorkflow = [bool]$autoAbsorbGate.require_native_workflow
    }
    $requireNativeUsageRequired = $true
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'require_native_usage_required' -and $null -ne $autoAbsorbGate.require_native_usage_required) {
        $requireNativeUsageRequired = [bool]$autoAbsorbGate.require_native_usage_required
    }
    $maxAutoAbsorbCount = [int]::MaxValue
    if ($autoAbsorbGate.PSObject.Properties.Name -contains 'max_auto_absorb_count' -and $null -ne $autoAbsorbGate.max_auto_absorb_count) {
        $maxAutoAbsorbCount = [int]$autoAbsorbGate.max_auto_absorb_count
    }

    $recommendationLookup = @{}
    if ($RuntimeInputPacket -and $RuntimeInputPacket.PSObject.Properties.Name -contains 'specialist_recommendations') {
        foreach ($recommendation in @($RuntimeInputPacket.specialist_recommendations)) {
            $skillId = [string]$recommendation.skill_id
            if (-not [string]::IsNullOrWhiteSpace($skillId) -and -not $recommendationLookup.ContainsKey($skillId)) {
                $recommendationLookup[$skillId] = $recommendation
            }
        }
    }

    $effectiveLookup = @{}
    foreach ($skillId in @($frozenApprovedSkillIds)) {
        $effectiveLookup[$skillId] = $true
    }

    $autoApprovedDispatch = @()
    $rejectedSuggestions = @()
    foreach ($suggestion in @($originalLocalSuggestions)) {
        $skillId = [string]$suggestion.skill_id
        $rejectionReason = $null
        $effectiveSuggestion = $suggestion

        if ([string]::IsNullOrWhiteSpace($skillId)) {
            $rejectionReason = 'missing_skill_id'
        } elseif ($effectiveLookup.ContainsKey($skillId)) {
            $rejectionReason = 'already_effective'
        } elseif ($requireKnownRecommendation -and -not $recommendationLookup.ContainsKey($skillId)) {
            $rejectionReason = 'not_in_frozen_recommendations'
        } else {
            if ($recommendationLookup.ContainsKey($skillId)) {
                $effectiveSuggestion = $recommendationLookup[$skillId]
            }

            if ($requireNativeWorkflow -and -not [bool]$effectiveSuggestion.must_preserve_workflow) {
                $rejectionReason = 'must_preserve_workflow_missing'
            } elseif ($requireNativeUsageRequired -and -not [bool]$effectiveSuggestion.native_usage_required) {
                $rejectionReason = 'native_usage_required_missing'
            } elseif (@($autoApprovedDispatch).Count -ge $maxAutoAbsorbCount) {
                $rejectionReason = 'max_auto_absorb_count_exceeded'
            }
        }

        if ($rejectionReason) {
            $rejectedSuggestions += [pscustomobject]@{
                skill_id = if ([string]::IsNullOrWhiteSpace($skillId)) { $null } else { $skillId }
                reason = $rejectionReason
                suggestion = $suggestion
            }
            continue
        }

        $autoApprovedDispatch += $effectiveSuggestion
        $effectiveLookup[$skillId] = $true
    }

    $residualSuggestions = @($rejectedSuggestions | ForEach-Object { $_.suggestion })
    $residualSkillIds = @($residualSuggestions | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $effectiveApprovedDispatch = @($frozenApprovedDispatch + $autoApprovedDispatch)
    $effectiveApprovedSkillIds = @($effectiveApprovedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    $result.effective_approved_dispatch = @($effectiveApprovedDispatch)
    $result.effective_approved_skill_ids = @($effectiveApprovedSkillIds)
    $result.auto_approved_dispatch = @($autoApprovedDispatch)
    $result.auto_approved_skill_ids = @($autoApprovedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $result.residual_local_specialist_suggestions = @($residualSuggestions)
    $result.residual_local_suggestion_skill_ids = @($residualSkillIds)
    $result.escalation_required = @($residualSuggestions).Count -gt 0 -and (
        $null -eq $SuggestionContract -or
        -not ($SuggestionContract.PSObject.Properties.Name -contains 'escalation_required') -or
        [bool]$SuggestionContract.escalation_required
    )
    $result.escalation_status = if ([bool]$result.escalation_required) {
        'root_approval_required'
    } elseif (@($autoApprovedDispatch).Count -gt 0) {
        'root_auto_approved_same_round'
    } else {
        'not_required'
    }

    $result.auto_absorb_gate.status = if (@($autoApprovedDispatch).Count -gt 0 -and @($residualSuggestions).Count -eq 0) {
        'auto_approved_same_round'
    } elseif (@($autoApprovedDispatch).Count -gt 0) {
        'partially_auto_approved_same_round'
    } elseif (@($originalLocalSuggestions).Count -gt 0) {
        'rejected_all_candidates'
    } else {
        'not_applicable'
    }
    $result.auto_absorb_gate.auto_approved_skill_ids = @($result.auto_approved_skill_ids)
    $result.auto_absorb_gate.rejected_skill_ids = @($rejectedSuggestions | ForEach-Object {
        if ($_.skill_id) { [string]$_.skill_id }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $result.auto_absorb_gate.rejected_suggestions = @($rejectedSuggestions)

    $resolutionReceipt = [pscustomobject]@{
        run_id = if ($RuntimeInputPacket) { [string]$RuntimeInputPacket.run_id } else { $null }
        governance_scope = [string]$HierarchyState.governance_scope
        root_run_id = [string]$HierarchyState.root_run_id
        parent_run_id = if ($null -eq $HierarchyState.parent_run_id) { $null } else { [string]$HierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $HierarchyState.parent_unit_id) { $null } else { [string]$HierarchyState.parent_unit_id }
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        approval_owner = [string]$result.approval_owner
        approval_source = [string]$approvalSource
        same_round = [bool]$sameRound
        frozen_approved_skill_ids = @($frozenApprovedSkillIds)
        original_local_suggestion_skill_ids = @($originalLocalSkillIds)
        effective_approved_skill_ids = @($effectiveApprovedSkillIds)
        auto_approved_skill_ids = @($result.auto_approved_skill_ids)
        residual_local_suggestion_skill_ids = @($residualSkillIds)
        escalation_required = [bool]$result.escalation_required
        escalation_status = [string]$result.escalation_status
        gate_status = [string]$result.auto_absorb_gate.status
        rejected_suggestions = @($rejectedSuggestions)
    }
    $resolutionReceiptPath = Join-Path $SessionRoot 'specialist-dispatch-resolution.json'
    Write-VibeJsonArtifact -Path $resolutionReceiptPath -Value $resolutionReceipt
    $result.auto_absorb_gate.receipt_path = $resolutionReceiptPath

    return [pscustomobject]$result
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
    $specialistSections = @('Specialist Skill Dispatch Plan', 'Specialist Consultation', 'Unified Specialist Lifecycle Disclosure')
    $sectionOrder = @('Wave Plan', 'Specialist Skill Dispatch Plan', 'Specialist Consultation', 'Unified Specialist Lifecycle Disclosure', 'Verification Commands', 'Phase Cleanup Contract')
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

            if ($specialistSections -contains $sectionName) {
                $classification = 'specialist_dispatch_unit'
                $reason = if ($sectionName -eq 'Specialist Skill Dispatch Plan') { 'bounded_native_specialist_dispatch_declared' } else { 'specialist_consultation_or_lifecycle_declared' }
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

function Resolve-VibeExecutionTargetRoot {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$Runtime = $null
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($null -ne $RuntimeInputPacket) {
        if (
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'canonical_router') -and
            $null -ne $RuntimeInputPacket.canonical_router -and
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.canonical_router -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$RuntimeInputPacket.canonical_router.target_root)
        ) {
            [void]$candidates.Add([string]$RuntimeInputPacket.canonical_router.target_root)
        }

        if (
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'host_adapter') -and
            $null -ne $RuntimeInputPacket.host_adapter -and
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.host_adapter -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$RuntimeInputPacket.host_adapter.target_root)
        ) {
            [void]$candidates.Add([string]$RuntimeInputPacket.host_adapter.target_root)
        }

        if (
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'custom_admission') -and
            $null -ne $RuntimeInputPacket.custom_admission -and
            (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket.custom_admission -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$RuntimeInputPacket.custom_admission.target_root)
        ) {
            [void]$candidates.Add([string]$RuntimeInputPacket.custom_admission.target_root)
        }
    }

    if ($null -ne $Runtime) {
        if (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_settings') -and
            $null -ne $Runtime.host_settings -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_settings -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_settings.target_root)
        ) {
            [void]$candidates.Add([string]$Runtime.host_settings.target_root)
        }

        if (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_closure') -and
            $null -ne $Runtime.host_closure -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_closure -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_closure.target_root)
        ) {
            [void]$candidates.Add([string]$Runtime.host_closure.target_root)
        }
    }

    foreach ($candidate in @($candidates)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate)) {
            return [System.IO.Path]::GetFullPath([string]$candidate)
        }
    }

    return Resolve-VgoTargetRoot -HostId (Resolve-VgoHostId -HostId $env:VCO_HOST_ID)
}

function Test-VibeInstalledRuntimeExecutionContext {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$TargetRoot = ''
    )

    if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
        return $false
    }

    $installedSkillRoot = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $TargetRoot 'skills') 'vibe'))
    return (Test-VgoPathWithin -ParentPath $installedSkillRoot -ChildPath $RepoRoot)
}

function New-VibeInstalledRuntimeVerificationUnit {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    return [pscustomobject]@{
        unit_id = $UnitId
        kind = 'powershell_file'
        parallelizable = $true
        write_scope = 'scripts/verify'
        script_path = $ScriptPath
        arguments = @('-TargetRoot', '${TARGET_ROOT}')
        cwd = '${REPO_ROOT}'
        timeout_seconds = 240
        expected_exit_code = 0
        expected_artifacts = @()
    }
}

function Get-VibeEffectiveExecutionPolicy {
    param(
        [Parameter(Mandatory)] [object]$ExecutionPolicy,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$TargetRoot = ''
    )

    if (-not (Test-VibeInstalledRuntimeExecutionContext -RepoRoot $RepoRoot -TargetRoot $TargetRoot)) {
        return $ExecutionPolicy
    }

    $policyCopy = $ExecutionPolicy | ConvertTo-Json -Depth 100 | ConvertFrom-Json
    foreach ($profileCandidate in @($policyCopy.profiles)) {
        foreach ($wave in @($profileCandidate.waves)) {
            $mappedUnits = foreach ($unit in @($wave.units)) {
                switch ([string]$unit.unit_id) {
                    'runtime-neutral-freshness-gate-tests' {
                        New-VibeInstalledRuntimeVerificationUnit `
                            -UnitId 'installed-runtime-freshness-gate' `
                            -ScriptPath 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
                        continue
                    }
                    { $_ -in @('version-consistency-gate', 'release-install-runtime-coherence-gate') } {
                        New-VibeInstalledRuntimeVerificationUnit `
                            -UnitId 'release-install-runtime-coherence-gate' `
                            -ScriptPath 'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
                        continue
                    }
                    default {
                        $unit
                    }
                }
            }
            $wave.units = @($mappedUnits)
        }
    }

    return $policyCopy
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $ArtifactRoot
$runtimeInputPacket = if (-not [string]::IsNullOrWhiteSpace($RuntimeInputPacketPath) -and (Test-Path -LiteralPath $RuntimeInputPacketPath)) {
    Get-Content -LiteralPath $RuntimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $null
}
$requestedGradeFloor = if (
    $runtimeInputPacket -and
    $runtimeInputPacket.PSObject.Properties.Name -contains 'requested_grade_floor' -and
    -not [string]::IsNullOrWhiteSpace([string]$runtimeInputPacket.requested_grade_floor)
) {
    [string]$runtimeInputPacket.requested_grade_floor
} else {
    ''
}
$grade = Get-VibeInternalGrade -Task $Task -RequestedGradeFloor $requestedGradeFloor
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
    -DelegationEnvelopePath $(if ($runtimeInputPacket -and $runtimeInputPacket.hierarchy) { [string]$runtimeInputPacket.hierarchy.delegation_envelope_path } else { '' }) `
    -HierarchyContract $runtime.runtime_input_packet_policy.hierarchy_contract

$executionTargetRoot = Resolve-VibeExecutionTargetRoot -RuntimeInputPacket $runtimeInputPacket -Runtime $runtime
$policy = Get-VibeEffectiveExecutionPolicy `
    -ExecutionPolicy $runtime.execution_runtime_policy `
    -RepoRoot ([System.IO.Path]::GetFullPath($runtime.repo_root)) `
    -TargetRoot $executionTargetRoot
$proofRegistry = $runtime.proof_class_registry
$profile = Get-VibeExecutionProfileById -ExecutionPolicy $policy -ProfileId ([string]$policy.default_profile_id)

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
    '${TARGET_ROOT}' = [string]$executionTargetRoot
    '${RUN_ID}' = [string]$RunId
    '${ROOT_RUN_ID}' = [string]$hierarchyState.root_run_id
}
$planShadow = Get-VibePlanDerivedExecutionShadow -PlanPath $planPath -RunId $RunId -SessionRoot $sessionRoot
$specialistRecommendations = if ($runtimeInputPacket) { @($runtimeInputPacket.specialist_recommendations) } else { @() }
$frozenApprovedDispatch = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.approved_dispatch) } else { @() }
$frozenLocalSuggestions = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch) { @($runtimeInputPacket.specialist_dispatch.local_specialist_suggestions) } else { @() }
$frozenBlockedDispatch = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'blocked' -and $null -ne $runtimeInputPacket.specialist_dispatch.blocked) { @($runtimeInputPacket.specialist_dispatch.blocked) } else { @() }
$frozenDegradedDispatch = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'degraded' -and $null -ne $runtimeInputPacket.specialist_dispatch.degraded) { @($runtimeInputPacket.specialist_dispatch.degraded) } else { @() }
$matchedSkillIds = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.matched_skill_ids) { @($runtimeInputPacket.specialist_dispatch.matched_skill_ids) } else { @() }
$surfacedSkillIds = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.surfaced_skill_ids) { @($runtimeInputPacket.specialist_dispatch.surfaced_skill_ids) } else { @() }
$blockedSkillIds = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'blocked_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.blocked_skill_ids) { @($runtimeInputPacket.specialist_dispatch.blocked_skill_ids) } else { @() }
$degradedSkillIds = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'degraded_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.degraded_skill_ids) { @($runtimeInputPacket.specialist_dispatch.degraded_skill_ids) } else { @() }
$ghostMatchSkillIds = if ($runtimeInputPacket -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'ghost_match_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.ghost_match_skill_ids) { @($runtimeInputPacket.specialist_dispatch.ghost_match_skill_ids) } else { @() }
$specialistDispatchResolution = Resolve-VibeEffectiveSpecialistDispatch `
    -SessionRoot $sessionRoot `
    -HierarchyState $hierarchyState `
    -RuntimeInputPacket $runtimeInputPacket `
    -ApprovedDispatch @($frozenApprovedDispatch) `
    -LocalSuggestions @($frozenLocalSuggestions) `
    -SuggestionContract $runtime.runtime_input_packet_policy.child_specialist_suggestion_contract
$approvedDispatch = @($specialistDispatchResolution.effective_approved_dispatch)
$localSuggestions = @($specialistDispatchResolution.residual_local_specialist_suggestions)
$autoApprovedDispatch = @($specialistDispatchResolution.auto_approved_dispatch)
$interactiveSpecialistDisclosurePolicy = Get-VibeInteractiveSpecialistDisclosurePolicy -RuntimeInputPacketPolicy $runtime.runtime_input_packet_policy
$specialistUserDisclosure = New-VibeSpecialistUserDisclosureProjection `
    -ApprovedDispatch @($approvedDispatch) `
    -Policy $interactiveSpecialistDisclosurePolicy
if ($specialistUserDisclosure) {
    $executionDisclosureLayer = New-VibeSpecialistExecutionLifecycleLayerProjection `
        -SpecialistUserDisclosure $specialistUserDisclosure `
        -ExecutionManifest $null
    $executionDisclosureSegment = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $executionDisclosureLayer
    $executionDisclosureEvent = New-VibeHostStageDisclosureEventProjection -Segment $executionDisclosureSegment
    Add-VibeHostStageDisclosureEvent -SessionRoot $sessionRoot -DisclosureEvent $executionDisclosureEvent | Out-Null
}
$executionTopologyPath = Get-VibeExecutionTopologyPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$executionTopology = New-VibeExecutionTopology `
    -RunId $RunId `
    -Grade $grade `
    -GovernanceScope ([string]$hierarchyState.governance_scope) `
    -ExecutionPolicy $policy `
    -TopologyPolicy $runtime.execution_topology_policy `
    -ApprovedDispatch @($approvedDispatch)
Write-VibeJsonArtifact -Path $executionTopologyPath -Value $executionTopology
$executionTopologyPath = Get-VibeExecutionTopologyPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$specialistSkills = @($approvedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$escalationRequired = [bool]$specialistDispatchResolution.escalation_required
$escalationPath = $null
if ([string]$hierarchyState.governance_scope -eq 'child' -and $escalationRequired) {
    $escalation = [pscustomobject]@{
        run_id = $RunId
        governance_scope = [string]$hierarchyState.governance_scope
        root_run_id = [string]$hierarchyState.root_run_id
        parent_run_id = if ($null -eq $hierarchyState.parent_run_id) { $null } else { [string]$hierarchyState.parent_run_id }
        parent_unit_id = if ($null -eq $hierarchyState.parent_unit_id) { $null } else { [string]$hierarchyState.parent_unit_id }
        approval_owner = [string]$specialistDispatchResolution.approval_owner
        status = [string]$specialistDispatchResolution.escalation_status
        requested_specialist_skill_ids = @($localSuggestions | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
        local_specialist_suggestions = @($localSuggestions)
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    $escalationPath = Join-Path $sessionRoot 'specialist-escalation-request.json'
    Write-VibeJsonArtifact -Path $escalationPath -Value $escalation
}

$blockedSpecialistUnits = @()
foreach ($dispatch in @($frozenBlockedDispatch)) {
    $blockedOutcome = New-VibeBlockedSpecialistDispatchResult `
        -UnitId ("blocked-{0}" -f [string]$dispatch.skill_id) `
        -Dispatch $dispatch `
        -SessionRoot $sessionRoot `
        -Reason $(if ($dispatch.PSObject.Properties.Name -contains 'recommended_promotion_action' -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.recommended_promotion_action)) { [string]$dispatch.recommended_promotion_action } else { 'require_confirmation' }) `
        -WriteScope $(if ($dispatch.PSObject.Properties.Name -contains 'write_scope') { [string]$dispatch.write_scope } else { '' }) `
        -ReviewMode $(if ($dispatch.PSObject.Properties.Name -contains 'review_mode') { [string]$dispatch.review_mode } else { 'native_contract' })
    $blockedSpecialistUnits += [pscustomobject]@{
        unit_id = [string]$blockedOutcome.result.unit_id
        skill_id = [string]$dispatch.skill_id
        dispatch_phase = if ($dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$dispatch.dispatch_phase } else { $null }
        binding_profile = if ($dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$dispatch.binding_profile } else { $null }
        lane_policy = if ($dispatch.PSObject.Properties.Name -contains 'lane_policy') { [string]$dispatch.lane_policy } else { $null }
        parallelizable = if ($dispatch.PSObject.Properties.Name -contains 'parallelizable_in_root_xl') { [bool]$dispatch.parallelizable_in_root_xl } else { $false }
        result_path = [string]$blockedOutcome.result_path
        verification_passed = [bool]$blockedOutcome.result.verification_passed
        execution_driver = [string]$blockedOutcome.result.execution_driver
        live_native_execution = $false
        degraded = $false
        blocked = $true
    }
}

$preDispatchDegradedUnits = @()
foreach ($dispatch in @($frozenDegradedDispatch)) {
    $degradedOutcome = New-VibeDegradedSpecialistDispatchResult `
        -UnitId ("degraded-{0}" -f [string]$dispatch.skill_id) `
        -Dispatch $dispatch `
        -SessionRoot $sessionRoot `
        -Policy $runtime.native_specialist_execution_policy `
        -Reason $(if ($dispatch.PSObject.Properties.Name -contains 'recommended_promotion_action' -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.recommended_promotion_action)) { [string]$dispatch.recommended_promotion_action } else { 'degrade_missing_contract' }) `
        -WriteScope $(if ($dispatch.PSObject.Properties.Name -contains 'write_scope') { [string]$dispatch.write_scope } else { '' }) `
        -ReviewMode $(if ($dispatch.PSObject.Properties.Name -contains 'review_mode') { [string]$dispatch.review_mode } else { 'native_contract' })
    $preDispatchDegradedUnits += [pscustomobject]@{
        unit_id = [string]$degradedOutcome.result.unit_id
        skill_id = [string]$dispatch.skill_id
        dispatch_phase = if ($dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$dispatch.dispatch_phase } else { $null }
        binding_profile = if ($dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$dispatch.binding_profile } else { $null }
        lane_policy = if ($dispatch.PSObject.Properties.Name -contains 'lane_policy') { [string]$dispatch.lane_policy } else { $null }
        parallelizable = if ($dispatch.PSObject.Properties.Name -contains 'parallelizable_in_root_xl') { [bool]$dispatch.parallelizable_in_root_xl } else { $false }
        result_path = [string]$degradedOutcome.result_path
        verification_passed = [bool]$degradedOutcome.result.verification_passed
        execution_driver = [string]$degradedOutcome.result.execution_driver
        live_native_execution = $false
        degraded = $true
        blocked = $false
    }
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
$resultPaths += @($blockedSpecialistUnits | ForEach-Object { [string]$_.result_path })
$resultPaths += @($preDispatchDegradedUnits | ForEach-Object { [string]$_.result_path })
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
                $outcome = if ([string]$hierarchyState.governance_scope -eq 'root' -and [string]$executionTopology.delegation_mode -ne 'none' -and [string]$laneEntry.lane_kind -eq 'execution_unit') {
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
            $unitCountsAsSuccessful = Test-VibeReceiptCountsAsSuccessful -Receipt $unitReceipt
            $waveUnitReceipts += $unitReceipt
            $resultPaths += [string]$unitReceipt.result_path
            $executedUnitCount += 1
            if ($unitCountsAsSuccessful) {
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
                    dispatch_phase = if ($unitReceipt.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$unitReceipt.dispatch_phase } else { $null }
                    binding_profile = if ($unitReceipt.PSObject.Properties.Name -contains 'binding_profile') { [string]$unitReceipt.binding_profile } else { $null }
                    lane_policy = if ($unitReceipt.PSObject.Properties.Name -contains 'lane_policy') { [string]$unitReceipt.lane_policy } else { $null }
                    parallelizable = [bool]$outcome.lane_entry.parallelizable
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
            status = if (@($waveUnitReceipts | Where-Object { [string]$_.step_id -eq [string]$step.step_id } | Where-Object { -not (Test-VibeReceiptCountsAsSuccessful -Receipt $_) }).Count -eq 0) { 'completed' } else { 'failed' }
            units = @($waveUnitReceipts | Where-Object { [string]$_.step_id -eq [string]$step.step_id })
        }
    }

    $waveReceipts += [pscustomobject]@{
        wave_id = [string]$topologyWave.wave_id
        description = [string]$topologyWave.description
        status = if (@($waveUnitReceipts | Where-Object { -not (Test-VibeReceiptCountsAsSuccessful -Receipt $_) }).Count -eq 0) { 'completed' } else { 'failed' }
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

$liveAttemptedSpecialistUnits = @($executedSpecialistUnits | Where-Object { [bool]$_.live_native_execution })
$liveSpecialistUnits = @($liveAttemptedSpecialistUnits | Where-Object { [bool]$_.verification_passed })
$failedLiveSpecialistUnits = @($liveAttemptedSpecialistUnits | Where-Object { -not [bool]$_.verification_passed })
$directRoutedSpecialistUnits = @($executedSpecialistUnits | Where-Object {
    -not [bool]$(if ($_.PSObject.Properties.Name -contains 'live_native_execution') { $_.live_native_execution } else { $false }) -and
    -not [bool]$(if ($_.PSObject.Properties.Name -contains 'degraded') { $_.degraded } else { $false }) -and
    -not [bool]$(if ($_.PSObject.Properties.Name -contains 'blocked') { $_.blocked } else { $false }) -and
    [string]$_.execution_driver -eq 'direct_current_session_route'
})
$verifiedSpecialistUnits = @($liveSpecialistUnits)

function Get-VibeSpecialistEntrySkillId {
    param(
        [AllowNull()] [object]$Entry = $null
    )

    if ($null -eq $Entry) {
        return $null
    }

    if (
        $Entry.PSObject.Properties.Name -contains 'skill_id' -and
        -not [string]::IsNullOrWhiteSpace([string]$Entry.skill_id)
    ) {
        return [string]$Entry.skill_id
    }
    if (
        $Entry.PSObject.Properties.Name -contains 'specialist_skill_id' -and
        -not [string]::IsNullOrWhiteSpace([string]$Entry.specialist_skill_id)
    ) {
        return [string]$Entry.specialist_skill_id
    }

    return $null
}

function Get-VibeSpecialistDispatchResolutionKey {
    param(
        [AllowNull()] [object]$Entry = $null
    )

    if ($null -eq $Entry) {
        return $null
    }

    $skillId = Get-VibeSpecialistEntrySkillId -Entry $Entry
    if ([string]::IsNullOrWhiteSpace($skillId)) {
        return $null
    }

    $dispatchPhase = if (
        $Entry.PSObject.Properties.Name -contains 'dispatch_phase' -and
        -not [string]::IsNullOrWhiteSpace([string]$Entry.dispatch_phase)
    ) {
        [string]$Entry.dispatch_phase
    } else {
        'in_execution'
    }

    return ('{0}|{1}' -f $dispatchPhase, $skillId)
}

function Get-VibeSpecialistDispatchExplicitPhase {
    param(
        [AllowNull()] [object]$Entry = $null
    )

    if (
        $null -ne $Entry -and
        $Entry.PSObject.Properties.Name -contains 'dispatch_phase' -and
        -not [string]::IsNullOrWhiteSpace([string]$Entry.dispatch_phase)
    ) {
        return [string]$Entry.dispatch_phase
    }

    return $null
}

function Test-VibeSpecialistEntrySupportedByCandidate {
    param(
        [AllowNull()] [object]$Entry = $null,
        [object[]]$Candidates = @()
    )

    if ($null -eq $Entry) {
        return $false
    }

    $entrySkillId = Get-VibeSpecialistEntrySkillId -Entry $Entry
    if ([string]::IsNullOrWhiteSpace($entrySkillId)) {
        return $false
    }

    $entryPhase = Get-VibeSpecialistDispatchExplicitPhase -Entry $Entry
    foreach ($candidate in @($Candidates)) {
        if ($null -eq $candidate) {
            continue
        }

        $candidateSkillId = Get-VibeSpecialistEntrySkillId -Entry $candidate
        if ([string]::IsNullOrWhiteSpace($candidateSkillId) -or $candidateSkillId -ne $entrySkillId) {
            continue
        }

        $candidatePhase = Get-VibeSpecialistDispatchExplicitPhase -Entry $candidate
        if ($null -ne $entryPhase -and $null -ne $candidatePhase) {
            if ($candidatePhase -eq $entryPhase) {
                return $true
            }
            continue
        }

        return $true
    }

    return $false
}

$recommendationSkillIds = @($specialistRecommendations | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$approvedDispatchSkillIds = @($approvedDispatch | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$localSuggestionSkillIds = @($localSuggestions | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$executedSpecialistSkillIds = @($verifiedSpecialistUnits | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$directRoutedSpecialistSkillIds = @($directRoutedSpecialistUnits | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$resolvedSpecialistSkillIds = @((@($executedSpecialistSkillIds) + @($directRoutedSpecialistSkillIds)) | Select-Object -Unique)
$recommendationResolutionKeys = @($specialistRecommendations | ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$approvedDispatchResolutionKeys = @($approvedDispatch | ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$localSuggestionResolutionKeys = @($localSuggestions | ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$executedSpecialistResolutionKeys = @($verifiedSpecialistUnits | ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$directRoutedSpecialistResolutionKeys = @($directRoutedSpecialistUnits | ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$resolvedSpecialistResolutionKeys = @((@($executedSpecialistResolutionKeys) + @($directRoutedSpecialistResolutionKeys)) | Select-Object -Unique)

$approvedDispatchMissingFromRecommendations = @($approvedDispatchSkillIds | Where-Object { $_ -notin $recommendationSkillIds })
$approvedDispatchMissingFromRecommendationsResolutionKeys = @(
    $approvedDispatch |
        Where-Object { -not (Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @($specialistRecommendations)) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$approvedDispatchNotExecuted = @(
    $approvedDispatch |
        Where-Object { -not (Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @($verifiedSpecialistUnits)) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$approvedDispatchNotResolved = @(
    $approvedDispatch |
        Where-Object { -not (Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @(@($verifiedSpecialistUnits) + @($directRoutedSpecialistUnits))) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$executedWithoutApproval = @(
    $verifiedSpecialistUnits |
        Where-Object { -not (Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @($approvedDispatch)) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$routedWithoutApproval = @(
    $directRoutedSpecialistUnits |
        Where-Object { -not (Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @($approvedDispatch)) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$localSuggestionsExecutedWithoutApproval = @(
    $localSuggestions |
        Where-Object { Test-VibeSpecialistEntrySupportedByCandidate -Entry $_ -Candidates @($verifiedSpecialistUnits) } |
        ForEach-Object { Get-VibeSpecialistDispatchResolutionKey -Entry $_ } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
$dispatchContractIncompleteSkillIds = @(
    $approvedDispatch | Where-Object {
        $hasNativeUsageRequired = $_.PSObject.Properties.Name -contains 'native_usage_required'
        $hasUsageRequired = $_.PSObject.Properties.Name -contains 'usage_required'
        $effectiveUsageRequired = if ($hasUsageRequired) {
            [bool]$_.usage_required
        } elseif ($hasNativeUsageRequired) {
            [bool]$_.native_usage_required
        } else {
            $false
        }
        $mustPreserveWorkflow = if ($_.PSObject.Properties.Name -contains 'must_preserve_workflow') {
            [bool]$_.must_preserve_workflow
        } else {
            $false
        }
        $nativeEntrypoint = if ($_.PSObject.Properties.Name -contains 'native_skill_entrypoint') {
            [string]$_.native_skill_entrypoint
        } else {
            ''
        }
        $skillRoot = if ($_.PSObject.Properties.Name -contains 'skill_root') {
            [string]$_.skill_root
        } else {
            ''
        }

        (-not $hasNativeUsageRequired -and -not $hasUsageRequired) -or
        -not $effectiveUsageRequired -or
        -not $mustPreserveWorkflow -or
        [string]::IsNullOrWhiteSpace($nativeEntrypoint) -or
        [string]::IsNullOrWhiteSpace($skillRoot)
    } | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
)

$dispatchIntegrity = [pscustomobject]@{
    recommendation_skill_ids = @($recommendationSkillIds)
    recommendation_resolution_keys = @($recommendationResolutionKeys)
    matched_skill_ids = @($matchedSkillIds)
    surfaced_skill_ids = @($surfacedSkillIds)
    approved_dispatch_skill_ids = @($approvedDispatchSkillIds)
    approved_dispatch_resolution_keys = @($approvedDispatchResolutionKeys)
    local_suggestion_skill_ids = @($localSuggestionSkillIds)
    local_suggestion_resolution_keys = @($localSuggestionResolutionKeys)
    blocked_skill_ids = @($blockedSkillIds)
    degraded_skill_ids = @($degradedSkillIds)
    ghost_match_skill_ids = @($ghostMatchSkillIds)
    executed_specialist_skill_ids = @($executedSpecialistSkillIds)
    executed_specialist_resolution_keys = @($executedSpecialistResolutionKeys)
    direct_routed_specialist_skill_ids = @($directRoutedSpecialistSkillIds)
    direct_routed_specialist_resolution_keys = @($directRoutedSpecialistResolutionKeys)
    resolved_specialist_skill_ids = @($resolvedSpecialistSkillIds)
    resolved_specialist_resolution_keys = @($resolvedSpecialistResolutionKeys)
    approved_dispatch_subset_of_recommendations = [bool](@($approvedDispatchMissingFromRecommendationsResolutionKeys).Count -eq 0)
    inherited_root_approval_allowed = [bool]([string]$hierarchyState.governance_scope -eq 'child')
    approved_dispatch_supported_by_recommendation_or_inherited_approval = [bool](
        (@($approvedDispatchMissingFromRecommendationsResolutionKeys).Count -eq 0) -or
        ([string]$hierarchyState.governance_scope -eq 'child')
    )
    approved_dispatch_fully_executed = [bool](@($approvedDispatchNotExecuted).Count -eq 0)
    approved_dispatch_fully_resolved = [bool](@($approvedDispatchNotResolved).Count -eq 0)
    executed_specialists_subset_of_approved_dispatch = [bool](@($executedWithoutApproval).Count -eq 0)
    routed_specialists_subset_of_approved_dispatch = [bool](@($routedWithoutApproval).Count -eq 0)
    local_suggestions_contained = [bool](@($localSuggestionsExecutedWithoutApproval).Count -eq 0)
    native_contract_complete_for_approved_dispatch = [bool](@($dispatchContractIncompleteSkillIds).Count -eq 0)
    matched_skills_resolved = [bool](@($ghostMatchSkillIds).Count -eq 0)
    approved_dispatch_missing_from_recommendations = @($approvedDispatchMissingFromRecommendations)
    approved_dispatch_missing_from_recommendations_resolution_keys = @($approvedDispatchMissingFromRecommendationsResolutionKeys)
    approved_dispatch_not_executed = @($approvedDispatchNotExecuted)
    approved_dispatch_not_resolved = @($approvedDispatchNotResolved)
    executed_without_approval = @($executedWithoutApproval)
    routed_without_approval = @($routedWithoutApproval)
    local_suggestions_executed_without_approval = @($localSuggestionsExecutedWithoutApproval)
    dispatch_contract_incomplete_skill_ids = @($dispatchContractIncompleteSkillIds)
}
$dispatchIntegrity | Add-Member -NotePropertyName 'proof_passed' -NotePropertyValue ([bool](
    $dispatchIntegrity.approved_dispatch_supported_by_recommendation_or_inherited_approval -and
    $dispatchIntegrity.approved_dispatch_fully_resolved -and
    $dispatchIntegrity.executed_specialists_subset_of_approved_dispatch -and
    $dispatchIntegrity.routed_specialists_subset_of_approved_dispatch -and
    $dispatchIntegrity.local_suggestions_contained -and
    $dispatchIntegrity.native_contract_complete_for_approved_dispatch -and
    $dispatchIntegrity.matched_skills_resolved
))
$topLevelProofPassed = [bool](
    ($failedUnitCount -eq 0) -and
    ($executedUnitCount -ge [int]$profile.expected_minimum_units) -and
    $dispatchIntegrity.proof_passed
)

$baseStatus = if ($failedUnitCount -eq 0 -and $executedUnitCount -ge [int]$profile.expected_minimum_units) { 'completed' } elseif ($executedUnitCount -eq 0) { 'failed' } else { 'completed_with_failures' }
$degradedSpecialistUnits = @(@($executedSpecialistUnits | Where-Object { [bool]$_.degraded }) + @($preDispatchDegradedUnits))
$nonDegradedExecutedSpecialistUnits = @($executedSpecialistUnits | Where-Object { -not [bool]$_.degraded })
$totalSpecialistDispatchOutcomeCount = @($nonDegradedExecutedSpecialistUnits).Count + @($blockedSpecialistUnits).Count + @($degradedSpecialistUnits).Count
$effectiveSpecialistExecutionStatus = if (@($liveSpecialistUnits).Count -gt 0 -and @($failedLiveSpecialistUnits).Count -eq 0) {
    'live_native_executed'
} elseif (@($liveSpecialistUnits).Count -gt 0 -and @($failedLiveSpecialistUnits).Count -gt 0) {
    'live_native_partial_failures'
} elseif (@($failedLiveSpecialistUnits).Count -gt 0) {
    'live_native_failed'
} elseif (@($directRoutedSpecialistUnits).Count -gt 0) {
    'direct_current_session_routed'
} elseif (@($degradedSpecialistUnits).Count -gt 0) {
    'explicitly_degraded'
} elseif (@($blockedSpecialistUnits).Count -gt 0) {
    'blocked_before_execution'
} else {
    'none'
}
$specialistDispatchUnitCount = @($approvedDispatch).Count
$specialistDecisionOverride = Get-VibeOptionalSpecialistDecisionOverride -SessionRoot $sessionRoot
$specialistDecision = New-VibeSpecialistDecisionProjection `
    -RuntimeInputPacket $runtimeInputPacket `
    -ApprovedDispatch @($approvedDispatch) `
    -LocalSuggestions @($localSuggestions) `
    -BlockedDispatch @($blockedSpecialistUnits) `
    -DegradedDispatch @($degradedSpecialistUnits) `
    -MatchedSkillIds $(if ($runtimeInputPacket -and $runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch' -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.matched_skill_ids) { @($runtimeInputPacket.specialist_dispatch.matched_skill_ids) } else { @() }) `
    -SurfacedSkillIds $(if ($runtimeInputPacket -and $runtimeInputPacket.PSObject.Properties.Name -contains 'specialist_dispatch' -and $runtimeInputPacket.specialist_dispatch -and $runtimeInputPacket.specialist_dispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $runtimeInputPacket.specialist_dispatch.surfaced_skill_ids) { @($runtimeInputPacket.specialist_dispatch.surfaced_skill_ids) } else { @() }) `
    -RecommendationCount @($specialistRecommendations).Count `
    -OverridePayload $(if ($specialistDecisionOverride) { $specialistDecisionOverride.payload } else { $null }) `
    -OverrideSourcePath $(if ($specialistDecisionOverride) { [string]$specialistDecisionOverride.path } else { '' })
$runtimePacketHostAdapterIdentity = Get-VibeRuntimePacketHostAdapterAlignment -RuntimeInputPacket $runtimeInputPacket
$routeRuntimeAlignment = New-VibeRouteRuntimeAlignmentProjection -RuntimeInputPacket $runtimeInputPacket -DefaultRuntimeSkill 'vibe'
$hierarchyProjection = New-VibeHierarchyProjection -HierarchyState $hierarchyState -IncludeGovernanceScope
$authorityProjection = New-VibeExecutionAuthorityProjection -HierarchyState $hierarchyState
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
    execution_memory_context_path = if ([string]::IsNullOrWhiteSpace($ExecutionMemoryContextPath)) { $null } else { $ExecutionMemoryContextPath }
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    planned_wave_count = @($profile.waves).Count
    planned_unit_count = $plannedUnitCount
    executed_unit_count = $executedUnitCount
    successful_unit_count = $successfulUnitCount
    failed_unit_count = $failedUnitCount
    timed_out_unit_count = $timedOutUnitCount
    proof_class = [string]$proofRegistry.artifact_class_defaults.execution_manifest
    promotion_suitable = [string]$proofRegistry.promotion_suitability.runtime
    hierarchy = $hierarchyProjection
    authority = $authorityProjection
    route_runtime_alignment = $routeRuntimeAlignment
    execution_topology = [pscustomobject]@{
        path = $executionTopologyPath
        delegation_mode = [string]$executionTopology.delegation_mode
        wave_execution = 'sequential'
        step_execution = 'sequential'
        unit_execution = $effectiveUnitExecution
        max_parallel_units = [int]$executionTopology.max_parallel_units
        child_lane_unit_count = [int]$executedThroughChildLanes
        parallelizable_specialist_unit_count = if ($executionTopology.PSObject.Properties.Name -contains 'parallelizable_specialist_unit_count') { [int]$executionTopology.parallelizable_specialist_unit_count } else { 0 }
        parallel_candidate_unit_count = [int]$parallelCandidateUnitCount
        parallel_units_executed_count = [int]$parallelUnitsExecutedCount
        parallel_executed_unit_ids = @($parallelExecutedUnitIds | Select-Object -Unique)
        parallel_execution_windows = @($parallelExecutionWindows)
        serial_execution_order = @($serialExecutionOrder)
        review_mode = [string]$executionTopology.review_mode
        specialist_phase_bindings = if ($executionTopology.PSObject.Properties.Name -contains 'specialist_phase_bindings') { $executionTopology.specialist_phase_bindings } else { $null }
        dispatch_resolution = [pscustomobject]@{
            source = 'plan_execute_effective_dispatch'
            frozen_approved_dispatch_count = @($frozenApprovedDispatch).Count
            effective_approved_dispatch_count = @($approvedDispatch).Count
            auto_approved_dispatch_count = @($autoApprovedDispatch).Count
            same_round_auto_absorb_applied = [bool](@($autoApprovedDispatch).Count -gt 0)
        }
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
        matched_skill_ids = @($matchedSkillIds)
        surfaced_skill_ids = @($surfacedSkillIds)
        specialist_skill_count = @($specialistSkills).Count
        specialist_skills = @($specialistSkills)
        native_usage_required = [bool](@($specialistRecommendations | Where-Object { $_.native_usage_required }).Count -gt 0)
        execution_mode = if (@($approvedDispatch).Count -gt 0) { 'native_bounded_units' } else { [string]$executionTopology.specialist_execution_mode }
        effective_execution_status = $effectiveSpecialistExecutionStatus
        dispatch_unit_count = [int]$specialistDispatchUnitCount
        recommendations = @($specialistRecommendations)
        frozen_approved_dispatch_count = @($frozenApprovedDispatch).Count
        frozen_approved_dispatch = @($frozenApprovedDispatch)
        approved_dispatch_count = @($approvedDispatch).Count
        approved_dispatch = @($approvedDispatch)
        auto_approved_dispatch_count = @($autoApprovedDispatch).Count
        auto_approved_dispatch = @($autoApprovedDispatch)
        requested_host_adapter_id = $runtimePacketHostAdapterIdentity.requested_host_id
        effective_host_adapter_id = $runtimePacketHostAdapterIdentity.effective_host_id
        phase_binding_counts = [pscustomobject]@{
            pre_execution = @($approvedDispatch | Where-Object { [string]$_.dispatch_phase -eq 'pre_execution' }).Count
            in_execution = @($approvedDispatch | Where-Object { [string]$_.dispatch_phase -eq 'in_execution' }).Count
            post_execution = @($approvedDispatch | Where-Object { [string]$_.dispatch_phase -eq 'post_execution' }).Count
            verification = @($approvedDispatch | Where-Object { [string]$_.dispatch_phase -eq 'verification' }).Count
        }
        parallelizable_dispatch_count = @($approvedDispatch | Where-Object { [bool]$_.parallelizable_in_root_xl }).Count
        attempted_specialist_unit_count = @($liveAttemptedSpecialistUnits).Count
        executed_specialist_unit_count = @($verifiedSpecialistUnits).Count
        failed_specialist_unit_count = @($failedLiveSpecialistUnits).Count
        direct_routed_specialist_unit_count = @($directRoutedSpecialistUnits).Count
        direct_routed_specialist_units = @($directRoutedSpecialistUnits)
        executed_specialist_units = @($verifiedSpecialistUnits)
        failed_specialist_units = @($failedLiveSpecialistUnits)
        blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
        blocked_specialist_units = @($blockedSpecialistUnits)
        degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
        degraded_specialist_units = @($degradedSpecialistUnits)
        blocked_skill_ids = @($blockedSkillIds)
        degraded_skill_ids = @($degradedSkillIds)
        ghost_match_skill_ids = @($ghostMatchSkillIds)
        specialist_dispatch_outcomes = @(@($nonDegradedExecutedSpecialistUnits) + @($blockedSpecialistUnits) + @($degradedSpecialistUnits))
        promotion_funnel = [pscustomobject]@{
            matched = @($matchedSkillIds).Count
            surfaced = @($surfacedSkillIds).Count
            dispatched = @($approvedDispatch).Count
            executed = @($verifiedSpecialistUnits).Count
            routed = @($directRoutedSpecialistUnits).Count
            blocked_due_to_destructive = @($blockedSkillIds).Count
            degraded_due_to_missing_contract = @($degradedSkillIds).Count
            ghost_match = @($ghostMatchSkillIds).Count
            executed_per_matched = if (@($matchedSkillIds).Count -gt 0) { [Math]::Round((@($verifiedSpecialistUnits).Count / [double]@($matchedSkillIds).Count), 4) } else { 0.0 }
            executed_rate = if (@($approvedDispatch).Count -gt 0) { [Math]::Round((@($verifiedSpecialistUnits).Count / [double]@($approvedDispatch).Count), 4) } else { 0.0 }
        }
        original_local_suggestion_count = @($frozenLocalSuggestions).Count
        original_local_specialist_suggestions = @($frozenLocalSuggestions)
        local_suggestion_count = @($localSuggestions).Count
        local_specialist_suggestions = @($localSuggestions)
        auto_absorb_gate = $specialistDispatchResolution.auto_absorb_gate
        escalation_required = [bool]$escalationRequired
        escalation_request_path = $escalationPath
    }
    specialist_decision = $specialistDecision
    specialist_user_disclosure = $specialistUserDisclosure
    dispatch_integrity = $dispatchIntegrity
    status = if ([string]$hierarchyState.governance_scope -eq 'child' -and $baseStatus -eq 'completed') { 'completed_local_scope' } else { $baseStatus }
    waves = @($waveReceipts)
}

$executionManifestPath = Join-Path $sessionRoot 'execution-manifest.json'
Write-VibeJsonArtifact -Path $executionManifestPath -Value $executionManifest

$proofManifest = [pscustomobject]@{
    bundle_kind = 'governed_execution_proof'
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
    proof_class = [string]$proofRegistry.artifact_class_defaults.execution_proof_manifest
    promotion_suitable = [string]$proofRegistry.promotion_suitability.runtime
    specialist_recommendation_count = @($specialistRecommendations).Count
    specialist_dispatch_unit_count = [int]$specialistDispatchUnitCount
    attempted_specialist_unit_count = @($liveAttemptedSpecialistUnits).Count
    executed_specialist_unit_count = @($verifiedSpecialistUnits).Count
    failed_specialist_unit_count = @($failedLiveSpecialistUnits).Count
    direct_routed_specialist_unit_count = @($directRoutedSpecialistUnits).Count
    blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
    degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
    specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
    specialist_execution_status = $effectiveSpecialistExecutionStatus
    auto_approved_specialist_unit_count = @($autoApprovedDispatch).Count
    residual_local_specialist_suggestion_count = @($localSuggestions).Count
    specialist_dispatch_resolution_path = if ($specialistDispatchResolution.auto_absorb_gate.receipt_path) { [string]$specialistDispatchResolution.auto_absorb_gate.receipt_path } else { $null }
    dispatch_integrity_proof_passed = [bool]$dispatchIntegrity.proof_passed
    delegated_lane_count = [int]$delegatedLaneCount
    review_receipt_count = [int]$reviewReceiptCount
    governance_scope = [string]$hierarchyState.governance_scope
    escalation_required = [bool]$escalationRequired
    proof_passed = [bool]$topLevelProofPassed
}
$proofManifestPath = Join-Path $proofRoot 'manifest.json'
Write-VibeJsonArtifact -Path $proofManifestPath -Value $proofManifest

$proofLines = @(
    '# Governed Execution Proof',
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
    ('- specialist_dispatch_unit_count: `{0}`' -f [int]$specialistDispatchUnitCount),
    ('- attempted_specialist_unit_count: `{0}`' -f @($liveAttemptedSpecialistUnits).Count),
    ('- executed_specialist_unit_count: `{0}`' -f @($verifiedSpecialistUnits).Count),
    ('- failed_specialist_unit_count: `{0}`' -f @($failedLiveSpecialistUnits).Count),
    ('- direct_routed_specialist_unit_count: `{0}`' -f @($directRoutedSpecialistUnits).Count),
    ('- blocked_specialist_unit_count: `{0}`' -f @($blockedSpecialistUnits).Count),
    ('- degraded_specialist_unit_count: `{0}`' -f @($degradedSpecialistUnits).Count),
    ('- auto_approved_specialist_unit_count: `{0}`' -f @($autoApprovedDispatch).Count),
    ('- residual_local_specialist_suggestion_count: `{0}`' -f @($localSuggestions).Count),
    ('- specialist_execution_status: `{0}`' -f $effectiveSpecialistExecutionStatus),
    ('- dispatch_integrity_proof_passed: `{0}`' -f [bool]$dispatchIntegrity.proof_passed),
    ('- execution_manifest: `{0}`' -f $executionManifestPath),
    ('- execution_topology: `{0}`' -f $executionTopologyPath),
    ('- plan_shadow: `{0}`' -f $planShadow.path),
    ''
)
if ($specialistUserDisclosure) {
    $proofLines += @(
        '## Specialist User Disclosure',
        [string]$specialistUserDisclosure.rendered_text,
        ''
    )
}
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
    execution_memory_context_path = if ([string]::IsNullOrWhiteSpace($ExecutionMemoryContextPath)) { $null } else { $ExecutionMemoryContextPath }
    plan_shadow_path = $planShadow.path
    execution_manifest_path = $executionManifestPath
    execution_proof_manifest_path = $proofManifestPath
    execution_topology_path = $executionTopologyPath
    executed_unit_count = $executedUnitCount
    successful_unit_count = $successfulUnitCount
    failed_unit_count = $failedUnitCount
    delegated_lane_count = [int]$delegatedLaneCount
    review_receipt_count = [int]$reviewReceiptCount
    specialist_recommendation_count = @($specialistRecommendations).Count
    specialist_dispatch_unit_count = [int]$specialistDispatchUnitCount
    attempted_specialist_unit_count = @($liveAttemptedSpecialistUnits).Count
    executed_specialist_unit_count = @($verifiedSpecialistUnits).Count
    failed_specialist_unit_count = @($failedLiveSpecialistUnits).Count
    direct_routed_specialist_unit_count = @($directRoutedSpecialistUnits).Count
    blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
    degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
    specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
    specialist_execution_status = $effectiveSpecialistExecutionStatus
    specialist_skills = @($specialistSkills)
    auto_approved_specialist_unit_count = @($autoApprovedDispatch).Count
    local_specialist_suggestion_count = @($localSuggestions).Count
    specialist_decision = $specialistDecision
    specialist_user_disclosure = $specialistUserDisclosure
    dispatch_integrity_proof_passed = [bool]$dispatchIntegrity.proof_passed
    dispatch_integrity = $dispatchIntegrity
    escalation_required = [bool]$escalationRequired
    escalation_request_path = $escalationPath
    specialist_dispatch_resolution_path = if ($specialistDispatchResolution.auto_absorb_gate.receipt_path) { [string]$specialistDispatchResolution.auto_absorb_gate.receipt_path } else { $null }
    completion_claim_allowed = [bool]$authorityProjection.completion_claim_allowed
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
    execution_proof_manifest_path = $proofManifestPath
    receipt = $receipt
}
