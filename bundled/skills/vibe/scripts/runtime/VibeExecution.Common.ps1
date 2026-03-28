Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')

function Expand-VibeExecutionTemplate {
    param(
        [AllowEmptyString()] [string]$Text,
        [hashtable]$Tokens
    )

    $value = if ($null -eq $Text) { '' } else { [string]$Text }
    foreach ($key in @($Tokens.Keys)) {
        $value = $value.Replace($key, [string]$Tokens[$key])
    }
    return $value
}

function Invoke-VibeCapturedProcess {
    param(
        [Parameter(Mandatory)] [string]$Command,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory)] [string]$WorkingDirectory,
        [Parameter(Mandatory)] [int]$TimeoutSeconds,
        [Parameter(Mandatory)] [string]$StdOutPath,
        [Parameter(Mandatory)] [string]$StdErrPath
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $Command
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    $quotedArguments = foreach ($argument in @($Arguments)) {
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

    try {
        if (-not $process.Start()) {
            throw "Failed to start process: $Command"
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()

        $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
        if ($timedOut) {
            try {
                $process.Kill($true)
            } catch {
            }
            $process.WaitForExit()
        }

        $stdoutText = $stdoutTask.GetAwaiter().GetResult()
        $stderrText = $stderrTask.GetAwaiter().GetResult()
        Write-VgoUtf8NoBomText -Path $StdOutPath -Content $stdoutText
        Write-VgoUtf8NoBomText -Path $StdErrPath -Content $stderrText

        return [pscustomobject]@{
            exit_code = if ($timedOut) { -1 } else { [int]$process.ExitCode }
            timed_out = [bool]$timedOut
            stdout_path = $StdOutPath
            stderr_path = $StdErrPath
            stdout_preview = (($stdoutText -split "`r?`n" | Where-Object { $_ -ne '' }) | Select-Object -First 5)
            stderr_preview = (($stderrText -split "`r?`n" | Where-Object { $_ -ne '' }) | Select-Object -First 5)
        }
    } finally {
        $process.Dispose()
    }
}

function Invoke-VibeExecutionUnit {
    param(
        [Parameter(Mandatory)] [object]$Unit,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [hashtable]$Tokens,
        [Parameter(Mandatory)] [int]$DefaultTimeoutSeconds
    )

    $logsRoot = Join-Path $SessionRoot 'execution-logs'
    $resultsRoot = Join-Path $SessionRoot 'execution-results'
    New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $unitId = [string]$Unit.unit_id
    $kind = [string]$Unit.kind
    $timeoutSeconds = if ($Unit.PSObject.Properties.Name -contains 'timeout_seconds' -and $null -ne $Unit.timeout_seconds) {
        [int]$Unit.timeout_seconds
    } else {
        [int]$DefaultTimeoutSeconds
    }
    $expectedExitCode = if ($Unit.PSObject.Properties.Name -contains 'expected_exit_code' -and $null -ne $Unit.expected_exit_code) {
        [int]$Unit.expected_exit_code
    } else {
        0
    }
    $cwd = Expand-VibeExecutionTemplate -Text ([string]$Unit.cwd) -Tokens $Tokens
    if ([string]::IsNullOrWhiteSpace($cwd)) {
        $cwd = $RepoRoot
    }
    if (-not [System.IO.Path]::IsPathRooted($cwd)) {
        $cwd = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $cwd))
    }

    $stdoutPath = Join-Path $logsRoot ("{0}.stdout.log" -f $unitId)
    $stderrPath = Join-Path $logsRoot ("{0}.stderr.log" -f $unitId)
    $startedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')

    $command = ''
    $arguments = @()
    $display = ''

    switch ($kind) {
        'powershell_file' {
            $scriptPathRaw = Expand-VibeExecutionTemplate -Text ([string]$Unit.script_path) -Tokens $Tokens
            $scriptPath = if ([System.IO.Path]::IsPathRooted($scriptPathRaw)) {
                [System.IO.Path]::GetFullPath($scriptPathRaw)
            } else {
                [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $scriptPathRaw))
            }

            $args = @()
            foreach ($arg in @($Unit.arguments)) {
                $args += (Expand-VibeExecutionTemplate -Text ([string]$arg) -Tokens $Tokens)
            }

            $invocation = Get-VgoPowerShellFileInvocation -ScriptPath $scriptPath -ArgumentList $args -NoProfile
            $command = [string]$invocation.host_path
            $arguments = @($invocation.arguments)
            $display = @($command) + @($arguments) -join ' '
        }
        'python_command' {
            $commandSpec = Expand-VibeExecutionTemplate -Text ([string]$Unit.command) -Tokens $Tokens
            $pythonInvocation = Resolve-VgoPythonCommandSpec -Command $commandSpec
            $command = [string]$pythonInvocation.host_path
            $arguments = @($pythonInvocation.prefix_arguments)
            foreach ($arg in @($Unit.arguments)) {
                $arguments += (Expand-VibeExecutionTemplate -Text ([string]$arg) -Tokens $Tokens)
            }
            $display = @($command) + @($arguments) -join ' '
        }
        'shell_command' {
            $command = Expand-VibeExecutionTemplate -Text ([string]$Unit.command) -Tokens $Tokens
            foreach ($arg in @($Unit.arguments)) {
                $arguments += (Expand-VibeExecutionTemplate -Text ([string]$arg) -Tokens $Tokens)
            }
            $display = @($command) + @($arguments) -join ' '
        }
        default {
            throw "Unsupported benchmark execution unit kind: $kind"
        }
    }

    $processResult = Invoke-VibeCapturedProcess -Command $command -Arguments $arguments -WorkingDirectory $cwd -TimeoutSeconds $timeoutSeconds -StdOutPath $stdoutPath -StdErrPath $stderrPath

    $resolvedArtifacts = @()
    foreach ($artifact in @($Unit.expected_artifacts)) {
        $expanded = Expand-VibeExecutionTemplate -Text ([string]$artifact) -Tokens $Tokens
        $artifactPath = if ([System.IO.Path]::IsPathRooted($expanded)) {
            [System.IO.Path]::GetFullPath($expanded)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $cwd $expanded))
        }
        $resolvedArtifacts += [pscustomobject]@{
            path = $artifactPath
            exists = [bool](Test-Path -LiteralPath $artifactPath)
        }
    }

    $finishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    $verificationPassed = (-not $processResult.timed_out) -and ([int]$processResult.exit_code -eq $expectedExitCode) -and (@($resolvedArtifacts | Where-Object { -not $_.exists }).Count -eq 0)

    $unitResult = [pscustomobject]@{
        unit_id = $unitId
        kind = $kind
        status = if ($verificationPassed) { 'completed' } elseif ($processResult.timed_out) { 'timed_out' } else { 'failed' }
        started_at = $startedAt
        finished_at = $finishedAt
        command = $command
        arguments = @($arguments)
        display_command = $display
        cwd = $cwd
        timeout_seconds = $timeoutSeconds
        expected_exit_code = $expectedExitCode
        exit_code = [int]$processResult.exit_code
        timed_out = [bool]$processResult.timed_out
        stdout_path = $processResult.stdout_path
        stderr_path = $processResult.stderr_path
        stdout_preview = @($processResult.stdout_preview)
        stderr_preview = @($processResult.stderr_preview)
        expected_artifacts = @($resolvedArtifacts)
        verification_passed = [bool]$verificationPassed
    }

    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $unitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $unitResult

    return [pscustomobject]@{
        result = $unitResult
        result_path = $resultPath
    }
}

function Test-VibeTruthyEnvironmentValue {
    param(
        [AllowEmptyString()] [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    return @('1', 'true', 'yes', 'on') -contains $Value.Trim().ToLowerInvariant()
}

function Resolve-VibeNativeSpecialistAdapter {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    $runtime = Get-VibeRuntimeContext -ScriptPath $ScriptPath
    $policy = $runtime.native_specialist_execution_policy
    if ($null -eq $policy -or -not [bool]$policy.enabled) {
        return [pscustomobject]@{
            enabled = $false
            live_execution_allowed = $false
            reason = 'native_specialist_execution_policy_disabled'
            runtime = $runtime
            policy = $policy
            adapter = $null
            command_path = $null
        }
    }

    $disableEnvName = if ($policy.PSObject.Properties.Name -contains 'disable_env') { [string]$policy.disable_env } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($disableEnvName)) {
        $disableEnvValue = [Environment]::GetEnvironmentVariable($disableEnvName)
        if (Test-VibeTruthyEnvironmentValue -Value $disableEnvValue) {
            return [pscustomobject]@{
                enabled = $true
                live_execution_allowed = $false
                reason = ("native_specialist_execution_disabled_via_env:{0}" -f $disableEnvName)
                runtime = $runtime
                policy = $policy
                adapter = $null
                command_path = $null
            }
        }
    }

    $enableEnvName = if ($policy.PSObject.Properties.Name -contains 'enable_env') { [string]$policy.enable_env } else { '' }
    $defaultEnabled = if ($policy.PSObject.Properties.Name -contains 'default_enabled') { [bool]$policy.default_enabled } else { $false }
    $liveExecutionAllowed = $defaultEnabled
    if (-not [string]::IsNullOrWhiteSpace($enableEnvName)) {
        $enableEnvValue = [Environment]::GetEnvironmentVariable($enableEnvName)
        if (Test-VibeTruthyEnvironmentValue -Value $enableEnvValue) {
            $liveExecutionAllowed = $true
        }
    }

    if (-not $liveExecutionAllowed) {
        return [pscustomobject]@{
            enabled = $true
            live_execution_allowed = $false
            reason = 'native_specialist_execution_not_enabled'
            runtime = $runtime
            policy = $policy
            adapter = $null
            command_path = $null
        }
    }

    $adapterId = if ($policy.PSObject.Properties.Name -contains 'default_adapter_id' -and -not [string]::IsNullOrWhiteSpace([string]$policy.default_adapter_id)) {
        [string]$policy.default_adapter_id
    } else {
        'codex'
    }
    $adapter = $null
    foreach ($candidate in @($policy.adapters)) {
        if ([string]$candidate.id -eq $adapterId) {
            $adapter = $candidate
            break
        }
    }
    if ($null -eq $adapter) {
        return [pscustomobject]@{
            enabled = $true
            live_execution_allowed = $false
            reason = ("native_specialist_adapter_missing:{0}" -f $adapterId)
            runtime = $runtime
            policy = $policy
            adapter = $null
            command_path = $null
        }
    }

    $commandPath = $null
    $resolvedReason = $null
    if ($adapter.PSObject.Properties.Name -contains 'executable_env' -and -not [string]::IsNullOrWhiteSpace([string]$adapter.executable_env)) {
        $envCommand = [Environment]::GetEnvironmentVariable([string]$adapter.executable_env)
        if (-not [string]::IsNullOrWhiteSpace($envCommand)) {
            $candidate = Get-Command $envCommand -ErrorAction SilentlyContinue
            if ($candidate) {
                $commandPath = [string]$candidate.Source
            } elseif (Test-Path -LiteralPath $envCommand) {
                $commandPath = [System.IO.Path]::GetFullPath($envCommand)
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($commandPath)) {
        $candidate = Get-Command ([string]$adapter.command) -ErrorAction SilentlyContinue
        if ($candidate) {
            $commandPath = [string]$candidate.Source
        }
    }
    if ([string]::IsNullOrWhiteSpace($commandPath)) {
        $resolvedReason = ("native_specialist_adapter_command_unavailable:{0}" -f [string]$adapter.command)
    }

    return [pscustomobject]@{
        enabled = $true
        live_execution_allowed = [bool](-not [string]::IsNullOrWhiteSpace($commandPath))
        reason = if ($resolvedReason) { $resolvedReason } else { 'native_specialist_execution_ready' }
        runtime = $runtime
        policy = $policy
        adapter = $adapter
        command_path = $commandPath
    }
}

function New-VibeSpecialistResultSchema {
    param(
        [Parameter(Mandatory)] [object]$Policy
    )

    $statusEnum = if ($Policy.result_schema -and $Policy.result_schema.status_enum) {
        @($Policy.result_schema.status_enum)
    } else {
        @('completed', 'completed_with_notes', 'blocked')
    }
    $requiredFields = if ($Policy.result_schema -and $Policy.result_schema.required_fields) {
        @($Policy.result_schema.required_fields)
    } else {
        @('status', 'summary', 'verification_notes', 'changed_files', 'bounded_output_notes')
    }

    return [pscustomobject]@{
        type = 'object'
        properties = [pscustomobject]@{
            status = [pscustomobject]@{
                type = 'string'
                enum = @($statusEnum)
            }
            summary = [pscustomobject]@{
                type = 'string'
            }
            verification_notes = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
            changed_files = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
            bounded_output_notes = [pscustomobject]@{
                type = 'array'
                items = [pscustomobject]@{
                    type = 'string'
                }
            }
        }
        required = @($requiredFields)
        additionalProperties = $false
    }
}

function Get-VibeGitStatusSnapshot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $gitDir = Join-Path $RepoRoot '.git'
    if (-not (Test-Path -LiteralPath $gitDir)) {
        return [pscustomobject]@{
            available = $false
            paths = @()
            lines = @()
        }
    }

    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCommand) {
        return [pscustomobject]@{
            available = $false
            paths = @()
            lines = @()
        }
    }

    $snapshot = & ([string]$gitCommand.Source) -C $RepoRoot status --porcelain --untracked-files=all 2>$null
    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{
            available = $false
            paths = @()
            lines = @()
        }
    }

    $paths = @()
    foreach ($line in @($snapshot)) {
        $text = [string]$line
        if ([string]::IsNullOrWhiteSpace($text) -or $text.Length -lt 4) {
            continue
        }
        $pathText = $text.Substring(3).Trim()
        if ($pathText -match ' -> ') {
            $pathText = ($pathText -split ' -> ')[-1].Trim()
        }
        if (-not [string]::IsNullOrWhiteSpace($pathText)) {
            $paths += $pathText
        }
    }

    return [pscustomobject]@{
        available = $true
        paths = @($paths | Select-Object -Unique)
        lines = @($snapshot)
    }
}

function New-VibeNativeSpecialistPrompt {
    param(
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [string]$WriteScope,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$RootRunId = '',
        [AllowEmptyString()] [string]$ParentRunId = '',
        [AllowEmptyString()] [string]$ParentUnitId = ''
    )

    $lines = @(
        ('$' + [string]$Dispatch.skill_id),
        '',
        'You are a bounded specialist execution lane running under hidden vibe governance.',
        'Do not replace the governed runtime. Do not create a second requirement surface or a second plan surface.',
        ('specialist_skill_id: {0}' -f [string]$Dispatch.skill_id),
        ('bounded_role: {0}' -f [string]$Dispatch.bounded_role),
        ('governance_scope: {0}' -f $GovernanceScope),
        ('run_id: {0}' -f $RunId)
    )
    if (-not [string]::IsNullOrWhiteSpace($RootRunId)) {
        $lines += ('root_run_id: {0}' -f $RootRunId)
    }
    if (-not [string]::IsNullOrWhiteSpace($ParentRunId)) {
        $lines += ('parent_run_id: {0}' -f $ParentRunId)
    }
    if (-not [string]::IsNullOrWhiteSpace($ParentUnitId)) {
        $lines += ('parent_unit_id: {0}' -f $ParentUnitId)
    }
    $lines += @(
        ('write_scope: {0}' -f $WriteScope),
        ('requirement_doc: {0}' -f $RequirementDocPath),
        ('execution_plan: {0}' -f $ExecutionPlanPath),
        '',
        'Rules:',
        '- Preserve the named specialist skill native workflow.',
        '- Remain bounded to the frozen requirement and execution plan.',
        '- Do not widen scope or self-approve new specialist dispatch.',
        '- Keep outputs specialist-specific and include verification notes.',
        '- If no repo change is needed, return an empty changed_files array.',
        '',
        'Required inputs:'
    )
    foreach ($item in @($Dispatch.required_inputs)) {
        $lines += ('- {0}' -f [string]$item)
    }
    $lines += @(
        '',
        'Expected outputs:'
    )
    foreach ($item in @($Dispatch.expected_outputs)) {
        $lines += ('- {0}' -f [string]$item)
    }
    $lines += @(
        '',
        ('Verification expectation: {0}' -f [string]$Dispatch.verification_expectation),
        '',
        'Return only JSON matching the provided schema.'
    )
    return ($lines -join [Environment]::NewLine)
}

function New-VibeDegradedSpecialistDispatchResult {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$Policy,
        [Parameter(Mandatory)] [string]$Reason,
        [AllowEmptyString()] [string]$WriteScope = '',
        [AllowEmptyString()] [string]$ReviewMode = 'native_contract'
    )

    $logsRoot = Join-Path $SessionRoot 'execution-logs'
    $resultsRoot = Join-Path $SessionRoot 'execution-results'
    New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $stdoutPath = Join-Path $logsRoot ("{0}.stdout.log" -f $UnitId)
    $stderrPath = Join-Path $logsRoot ("{0}.stderr.log" -f $UnitId)
    $startedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')

    $stdoutLines = @(
        ([string]$Policy.degrade_contract.hazard_alert),
        ("skill_id={0}" -f [string]$Dispatch.skill_id),
        ("degradation_reason={0}" -f $Reason)
    )
    Write-VgoUtf8NoBomText -Path $stdoutPath -Content (($stdoutLines -join [Environment]::NewLine) + [Environment]::NewLine)
    Write-VgoUtf8NoBomText -Path $stderrPath -Content ''

    $finishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    $unitResult = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_dispatch'
        status = [string]$Policy.degrade_contract.status
        started_at = $startedAt
        finished_at = $finishedAt
        command = ("specialist:{0}" -f [string]$Dispatch.skill_id)
        arguments = @(
            ("--bounded-role={0}" -f [string]$Dispatch.bounded_role)
        )
        display_command = ("specialist:{0} --bounded-role={1}" -f [string]$Dispatch.skill_id, [string]$Dispatch.bounded_role)
        cwd = $SessionRoot
        timeout_seconds = 0
        expected_exit_code = 0
        exit_code = 0
        timed_out = $false
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        stdout_preview = @($stdoutLines)
        stderr_preview = @()
        expected_artifacts = @()
        verification_passed = [bool]$Policy.degrade_contract.verification_passed
        specialist_skill_id = [string]$Dispatch.skill_id
        bounded_role = [string]$Dispatch.bounded_role
        native_usage_required = [bool]$Dispatch.native_usage_required
        must_preserve_workflow = [bool]$Dispatch.must_preserve_workflow
        write_scope = $WriteScope
        review_mode = $ReviewMode
        execution_driver = [string]$Policy.degrade_contract.execution_driver
        live_native_execution = $false
        degraded = $true
        degradation_reason = $Reason
        hazard_alert = [string]$Policy.degrade_contract.hazard_alert
        changed_files = @()
        verification_notes = @()
        bounded_output_notes = @()
    }

    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $unitResult

    return [pscustomobject]@{
        result = $unitResult
        result_path = $resultPath
    }
}

function Invoke-VibeSpecialistDispatchUnit {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [AllowEmptyString()] [string]$RootRunId = '',
        [AllowEmptyString()] [string]$ParentRunId = '',
        [AllowEmptyString()] [string]$ParentUnitId = '',
        [AllowEmptyString()] [string]$WriteScope = '',
        [AllowEmptyString()] [string]$ReviewMode = 'native_contract'
    )

    $adapterResolution = Resolve-VibeNativeSpecialistAdapter -ScriptPath $PSCommandPath
    $policy = $adapterResolution.policy
    if (-not $adapterResolution.live_execution_allowed -or $null -eq $adapterResolution.adapter) {
        return New-VibeDegradedSpecialistDispatchResult `
            -UnitId $UnitId `
            -Dispatch $Dispatch `
            -SessionRoot $SessionRoot `
            -Policy $policy `
            -Reason ([string]$adapterResolution.reason) `
            -WriteScope $WriteScope `
            -ReviewMode $ReviewMode
    }

    $adapter = $adapterResolution.adapter
    $logsRoot = Join-Path $SessionRoot 'execution-logs'
    $resultsRoot = Join-Path $SessionRoot 'execution-results'
    New-Item -ItemType Directory -Path $logsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $resultsRoot -Force | Out-Null

    $stdoutPath = Join-Path $logsRoot ("{0}.stdout.log" -f $UnitId)
    $stderrPath = Join-Path $logsRoot ("{0}.stderr.log" -f $UnitId)
    $responsePath = Join-Path $resultsRoot ("{0}.response.json" -f $UnitId)
    $schemaPath = Join-Path $SessionRoot ("{0}.schema.json" -f $UnitId)
    $promptPath = Join-Path $SessionRoot ("{0}.prompt.md" -f $UnitId)
    $beforeGitPath = Join-Path $SessionRoot ("{0}.git-before.txt" -f $UnitId)
    $afterGitPath = Join-Path $SessionRoot ("{0}.git-after.txt" -f $UnitId)
    $startedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')

    $schema = New-VibeSpecialistResultSchema -Policy $policy
    Write-VibeJsonArtifact -Path $schemaPath -Value $schema
    $prompt = New-VibeNativeSpecialistPrompt `
        -Dispatch $Dispatch `
        -RequirementDocPath $RequirementDocPath `
        -ExecutionPlanPath $ExecutionPlanPath `
        -GovernanceScope $GovernanceScope `
        -WriteScope $WriteScope `
        -RunId $RunId `
        -RootRunId $RootRunId `
        -ParentRunId $ParentRunId `
        -ParentUnitId $ParentUnitId
    Write-VgoUtf8NoBomText -Path $promptPath -Content ($prompt + [Environment]::NewLine)

    $beforeSnapshot = Get-VibeGitStatusSnapshot -RepoRoot $RepoRoot
    Write-VgoUtf8NoBomText -Path $beforeGitPath -Content ((@($beforeSnapshot.lines) -join [Environment]::NewLine) + [Environment]::NewLine)

    $arguments = @()
    foreach ($item in @($adapter.arguments_prefix)) {
        $arguments += [string]$item
    }
    $arguments += @(
        '-C', $RepoRoot,
        '--output-schema', $schemaPath,
        '-o', $responsePath,
        $prompt
    )
    $processResult = Invoke-VibeCapturedProcess `
        -Command ([string]$adapterResolution.command_path) `
        -Arguments $arguments `
        -WorkingDirectory $RepoRoot `
        -TimeoutSeconds ([int]$policy.default_timeout_seconds) `
        -StdOutPath $stdoutPath `
        -StdErrPath $stderrPath

    $afterSnapshot = Get-VibeGitStatusSnapshot -RepoRoot $RepoRoot
    Write-VgoUtf8NoBomText -Path $afterGitPath -Content ((@($afterSnapshot.lines) -join [Environment]::NewLine) + [Environment]::NewLine)

    $parsedResponse = $null
    $responseParseError = $null
    if (Test-Path -LiteralPath $responsePath) {
        try {
            $parsedResponse = Get-Content -LiteralPath $responsePath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $responseParseError = $_.Exception.Message
        }
    } else {
        $responseParseError = 'native_specialist_response_missing'
    }

    $beforeLookup = @{}
    foreach ($path in @($beforeSnapshot.paths)) {
        $beforeLookup[[string]$path] = $true
    }
    $observedChangedFiles = @()
    foreach ($path in @($afterSnapshot.paths)) {
        if (-not $beforeLookup.ContainsKey([string]$path)) {
            $observedChangedFiles += [string]$path
        }
    }

    $responseStatus = if ($parsedResponse -and $parsedResponse.PSObject.Properties.Name -contains 'status') {
        [string]$parsedResponse.status
    } else {
        ''
    }
    $responseSummary = if ($parsedResponse -and $parsedResponse.PSObject.Properties.Name -contains 'summary') {
        [string]$parsedResponse.summary
    } else {
        $null
    }
    $verificationNotes = if ($parsedResponse -and $parsedResponse.PSObject.Properties.Name -contains 'verification_notes') {
        @($parsedResponse.verification_notes | ForEach-Object { [string]$_ })
    } else {
        @()
    }
    $changedFiles = if ($parsedResponse -and $parsedResponse.PSObject.Properties.Name -contains 'changed_files') {
        @($parsedResponse.changed_files | ForEach-Object { [string]$_ })
    } else {
        @()
    }
    $boundedOutputNotes = if ($parsedResponse -and $parsedResponse.PSObject.Properties.Name -contains 'bounded_output_notes') {
        @($parsedResponse.bounded_output_notes | ForEach-Object { [string]$_ })
    } else {
        @()
    }

    $verificationPassed = (-not $processResult.timed_out) -and ([int]$processResult.exit_code -eq 0) -and ($null -ne $parsedResponse) -and (@('completed', 'completed_with_notes') -contains $responseStatus)
    $effectiveStatus = if ($verificationPassed) {
        'completed'
    } elseif ($processResult.timed_out) {
        'timed_out'
    } elseif (-not [string]::IsNullOrWhiteSpace($responseStatus)) {
        $responseStatus
    } else {
        'failed'
    }

    $finishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    $unitResult = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_dispatch'
        status = $effectiveStatus
        started_at = $startedAt
        finished_at = $finishedAt
        command = [string]$adapterResolution.command_path
        arguments = @($arguments)
        display_command = @([string]$adapterResolution.command_path) + @($arguments) -join ' '
        cwd = $RepoRoot
        timeout_seconds = [int]$policy.default_timeout_seconds
        expected_exit_code = 0
        exit_code = [int]$processResult.exit_code
        timed_out = [bool]$processResult.timed_out
        stdout_path = $processResult.stdout_path
        stderr_path = $processResult.stderr_path
        stdout_preview = @($processResult.stdout_preview)
        stderr_preview = @($processResult.stderr_preview)
        expected_artifacts = @(
            [pscustomobject]@{
                path = $responsePath
                exists = [bool](Test-Path -LiteralPath $responsePath)
            }
        )
        verification_passed = [bool]$verificationPassed
        specialist_skill_id = [string]$Dispatch.skill_id
        bounded_role = [string]$Dispatch.bounded_role
        native_usage_required = [bool]$Dispatch.native_usage_required
        must_preserve_workflow = [bool]$Dispatch.must_preserve_workflow
        write_scope = $WriteScope
        review_mode = $ReviewMode
        execution_driver = [string]$adapter.execution_driver
        host_adapter_id = [string]$adapter.id
        live_native_execution = $true
        degraded = $false
        requirement_doc_path = $RequirementDocPath
        execution_plan_path = $ExecutionPlanPath
        response_json_path = $responsePath
        prompt_path = $promptPath
        schema_path = $schemaPath
        git_status_before_path = $beforeGitPath
        git_status_after_path = $afterGitPath
        changed_files = @($changedFiles)
        observed_changed_files = @($observedChangedFiles)
        verification_notes = @($verificationNotes)
        bounded_output_notes = @($boundedOutputNotes)
        summary = $responseSummary
        response_parse_error = $responseParseError
    }

    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $unitResult

    return [pscustomobject]@{
        result = $unitResult
        result_path = $resultPath
    }
}

function Get-VibeBenchmarkProfileById {
    param(
        [Parameter(Mandatory)] [object]$BenchmarkPolicy,
        [Parameter(Mandatory)] [string]$ProfileId
    )

    foreach ($candidate in @($BenchmarkPolicy.profiles)) {
        if ([string]$candidate.id -eq $ProfileId) {
            return $candidate
        }
    }

    throw "Unable to resolve benchmark execution profile '$ProfileId'."
}

function Get-VibeExecutionTopologyProfile {
    param(
        [Parameter(Mandatory)] [object]$BenchmarkPolicy,
        [Parameter(Mandatory)] [object]$TopologyPolicy,
        [Parameter(Mandatory)] [string]$Grade
    )

    $gradePolicy = $TopologyPolicy.grades.$Grade
    if ($null -eq $gradePolicy) {
        throw "Unable to resolve execution topology policy for grade '$Grade'."
    }

    $profileId = [string]$BenchmarkPolicy.default_profile_id
    $profile = Get-VibeBenchmarkProfileById -BenchmarkPolicy $BenchmarkPolicy -ProfileId $profileId

    return [pscustomobject]@{
        profile_id = $profileId
        profile = $profile
        delegation_mode = [string]$gradePolicy.delegation_mode
        unit_execution = [string]$gradePolicy.unit_execution
        max_parallel_units = [int]$gradePolicy.max_parallel_units
        review_mode = [string]$gradePolicy.review_mode
        specialist_execution_mode = [string]$gradePolicy.specialist_execution_mode
    }
}

function New-VibeExecutionTopology {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Grade,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [object]$BenchmarkPolicy,
        [Parameter(Mandatory)] [object]$TopologyPolicy,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ApprovedDispatch
    )

    $profileDef = Get-VibeExecutionTopologyProfile -BenchmarkPolicy $BenchmarkPolicy -TopologyPolicy $TopologyPolicy -Grade $Grade
    $effectiveSpecialistExecutionMode = [string]$profileDef.specialist_execution_mode
    if (@($ApprovedDispatch).Count -gt 0) {
        $effectiveSpecialistExecutionMode = 'native_bounded_units'
    }
    $steps = @()

    foreach ($wave in @($profileDef.profile.waves)) {
        $waveSteps = @()
        $unitEntries = @()
        foreach ($unit in @($wave.units)) {
            $parallelizable = $false
            if ($Grade -eq 'XL' -and $GovernanceScope -eq 'root') {
                if ($unit.PSObject.Properties.Name -contains 'parallelizable' -and $null -ne $unit.parallelizable) {
                    $parallelizable = [bool]$unit.parallelizable
                } else {
                    $parallelizable = $profileDef.unit_execution -eq 'bounded_parallel'
                }
            }

            $writeScope = if ($unit.PSObject.Properties.Name -contains 'write_scope' -and -not [string]::IsNullOrWhiteSpace([string]$unit.write_scope)) {
                [string]$unit.write_scope
            } else {
                "{0}:{1}" -f [string]$TopologyPolicy.default_write_scope_prefix, [string]$unit.unit_id
            }

            $unitEntries += [pscustomobject]@{
                lane_id = "lane-{0}" -f [string]$unit.unit_id
                lane_kind = 'benchmark_unit'
                source_unit_id = [string]$unit.unit_id
                parallelizable = [bool]$parallelizable
                write_scope = $writeScope
                review_mode = [string]$profileDef.review_mode
                unit = $unit
            }
        }

        switch ($profileDef.delegation_mode) {
            'serial_child_lanes' {
                $index = 0
                foreach ($entry in @($unitEntries)) {
                    $index += 1
                    $waveSteps += [pscustomobject]@{
                        step_id = "{0}-step-{1}" -f [string]$wave.wave_id, $index
                        execution_mode = 'sequential'
                        review_mode = [string]$profileDef.review_mode
                        max_parallel_units = 1
                        units = @($entry)
                    }
                }
            }
            'selective_parallel_child_lanes' {
                $parallelUnits = @($unitEntries | Where-Object { $_.parallelizable })
                $serialUnits = @($unitEntries | Where-Object { -not $_.parallelizable })
                if (@($parallelUnits).Count -gt 0) {
                    $waveSteps += [pscustomobject]@{
                        step_id = "{0}-parallel" -f [string]$wave.wave_id
                        execution_mode = 'bounded_parallel'
                        review_mode = [string]$profileDef.review_mode
                        max_parallel_units = [int]$profileDef.max_parallel_units
                        units = @($parallelUnits)
                    }
                }
                $serialIndex = 0
                foreach ($entry in @($serialUnits)) {
                    $serialIndex += 1
                    $waveSteps += [pscustomobject]@{
                        step_id = "{0}-serial-{1}" -f [string]$wave.wave_id, $serialIndex
                        execution_mode = 'sequential'
                        review_mode = [string]$profileDef.review_mode
                        max_parallel_units = 1
                        units = @($entry)
                    }
                }
            }
            default {
                $waveSteps += [pscustomobject]@{
                    step_id = "{0}-direct" -f [string]$wave.wave_id
                    execution_mode = 'sequential'
                    review_mode = 'none'
                    max_parallel_units = 1
                    units = @($unitEntries)
                }
            }
        }

        if ($effectiveSpecialistExecutionMode -eq 'native_bounded_units' -and @($ApprovedDispatch).Count -gt 0) {
            $specialistUnits = @()
            foreach ($dispatch in @($ApprovedDispatch)) {
                $specialistUnits += [pscustomobject]@{
                    lane_id = "specialist-{0}" -f [string]$dispatch.skill_id
                    lane_kind = 'specialist_dispatch'
                    source_unit_id = [string]$dispatch.skill_id
                    specialist_skill_id = [string]$dispatch.skill_id
                    parallelizable = $false
                    write_scope = "specialist:{0}" -f [string]$dispatch.skill_id
                    review_mode = 'native_contract'
                    dispatch = $dispatch
                }
            }
            $waveSteps += [pscustomobject]@{
                step_id = "{0}-approved-specialists" -f [string]$wave.wave_id
                execution_mode = 'sequential'
                review_mode = 'checkpoint_after_step'
                max_parallel_units = 1
                units = @($specialistUnits)
            }
        }

        $steps += [pscustomobject]@{
            wave_id = [string]$wave.wave_id
            description = [string]$wave.description
            steps = @($waveSteps)
        }
    }

    return [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        run_id = $RunId
        governance_scope = $GovernanceScope
        grade = $Grade
        profile_id = [string]$profileDef.profile_id
        delegation_mode = [string]$profileDef.delegation_mode
        review_mode = [string]$profileDef.review_mode
        specialist_execution_mode = $effectiveSpecialistExecutionMode
        max_parallel_units = [int]$profileDef.max_parallel_units
        waves = @($steps)
    }
}
