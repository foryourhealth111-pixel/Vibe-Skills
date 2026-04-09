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

function New-VibeExecutedSpecialistUnitSummary {
    param(
        [Parameter(Mandatory)] [object]$UnitReceipt,
        [AllowNull()] [object]$LaneEntry = $null
    )

    return [pscustomobject]@{
        unit_id = [string]$UnitReceipt.unit_id
        skill_id = [string]$UnitReceipt.skill_id
        dispatch_phase = if ($UnitReceipt.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$UnitReceipt.dispatch_phase } else { $null }
        binding_profile = if ($UnitReceipt.PSObject.Properties.Name -contains 'binding_profile') { [string]$UnitReceipt.binding_profile } else { $null }
        lane_policy = if ($UnitReceipt.PSObject.Properties.Name -contains 'lane_policy') { [string]$UnitReceipt.lane_policy } else { $null }
        parallelizable = [bool]$(if ($null -ne $LaneEntry -and $LaneEntry.PSObject.Properties.Name -contains 'parallelizable') { $LaneEntry.parallelizable } else { $false })
        result_path = [string]$UnitReceipt.result_path
        verification_passed = [bool]$UnitReceipt.verification_passed
        execution_driver = [string]$UnitReceipt.execution_driver
        live_native_execution = [bool]$UnitReceipt.live_native_execution
        degraded = [bool]$UnitReceipt.degraded
        prompt_path = if ($UnitReceipt.PSObject.Properties.Name -contains 'prompt_path' -and -not [string]::IsNullOrWhiteSpace([string]$UnitReceipt.prompt_path)) { [string]$UnitReceipt.prompt_path } else { $null }
        prompt_injection_complete = [bool]$(if ($UnitReceipt.PSObject.Properties.Name -contains 'prompt_injection_complete') { $UnitReceipt.prompt_injection_complete } else { $false })
        missing_prompt_injection_fields = @($(if ($UnitReceipt.PSObject.Properties.Name -contains 'missing_prompt_injection_fields') { $UnitReceipt.missing_prompt_injection_fields } else { @() }))
        lane_receipt_path = if ($UnitReceipt.lane_receipt_path) { [string]$UnitReceipt.lane_receipt_path } else { $null }
    }
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
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    try {
        $startInfo.StandardOutputEncoding = $utf8NoBom
    } catch {
    }
    try {
        $startInfo.StandardErrorEncoding = $utf8NoBom
    } catch {
    }

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
            throw "Unsupported execution unit kind: $kind"
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

function Resolve-VibeProcessInvocationSpec {
    param(
        [Parameter(Mandatory)] [string]$CommandPath,
        [string[]]$ArgumentList = @()
    )

    $normalizedCommandPath = if ([System.IO.Path]::IsPathRooted($CommandPath) -and (Test-Path -LiteralPath $CommandPath)) {
        [System.IO.Path]::GetFullPath($CommandPath)
    } else {
        [string]$CommandPath
    }
    $extension = [System.IO.Path]::GetExtension($normalizedCommandPath).ToLowerInvariant()
    if ($extension -eq '.ps1') {
        $invocation = Get-VgoPowerShellFileInvocation -ScriptPath $normalizedCommandPath -ArgumentList $ArgumentList -NoProfile
        return [pscustomobject]@{
            command_path = [string]$invocation.host_path
            arguments = @($invocation.arguments)
        }
    }

    return [pscustomobject]@{
        command_path = $normalizedCommandPath
        arguments = @($ArgumentList)
    }
}

function Resolve-VibeBridgeExecutable {
    param(
        [Parameter(Mandatory)] [object]$Adapter,
        [object]$Runtime = $null
    )

    $resolvedCommandPath = $null
    $envName = if ($Adapter.PSObject.Properties.Name -contains 'bridge_executable_env') { [string]$Adapter.bridge_executable_env } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $envValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            $candidate = Get-Command $envValue -ErrorAction SilentlyContinue
            if ($candidate) {
                $resolvedCommandPath = [string]$candidate.Source
            } elseif (Test-Path -LiteralPath $envValue) {
                $resolvedCommandPath = [System.IO.Path]::GetFullPath($envValue)
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedCommandPath) -and $null -ne $Runtime -and $Runtime.PSObject.Properties.Name -contains 'host_settings' -and $null -ne $Runtime.host_settings) {
        $hostSettings = $Runtime.host_settings
        if ($hostSettings.PSObject.Properties.Name -contains 'data' -and $null -ne $hostSettings.data) {
            $specialistWrapper = if ($hostSettings.data.PSObject.Properties.Name -contains 'specialist_wrapper') { $hostSettings.data.specialist_wrapper } else { $null }
            if ($null -ne $specialistWrapper) {
                $ready = if ($specialistWrapper.PSObject.Properties.Name -contains 'ready') { [bool]$specialistWrapper.ready } else { $false }
                $launcherPath = if ($specialistWrapper.PSObject.Properties.Name -contains 'launcher_path') { [string]$specialistWrapper.launcher_path } else { '' }
                if ($ready -and -not [string]::IsNullOrWhiteSpace($launcherPath) -and (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
                    $resolvedCommandPath = [System.IO.Path]::GetFullPath($launcherPath)
                }
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedCommandPath) -and $null -ne $Runtime -and $Runtime.PSObject.Properties.Name -contains 'host_closure' -and $null -ne $Runtime.host_closure) {
        $hostClosure = $Runtime.host_closure
        if ($hostClosure.PSObject.Properties.Name -contains 'data' -and $null -ne $hostClosure.data) {
            $specialistWrapper = if ($hostClosure.data.PSObject.Properties.Name -contains 'specialist_wrapper') { $hostClosure.data.specialist_wrapper } else { $null }
            if ($null -ne $specialistWrapper) {
                $ready = if ($specialistWrapper.PSObject.Properties.Name -contains 'ready') { [bool]$specialistWrapper.ready } else { $false }
                $launcherPath = if ($specialistWrapper.PSObject.Properties.Name -contains 'launcher_path') { [string]$specialistWrapper.launcher_path } else { '' }
                if ($ready -and -not [string]::IsNullOrWhiteSpace($launcherPath) -and (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
                    $resolvedCommandPath = [System.IO.Path]::GetFullPath($launcherPath)
                }
            }
        }
    }

    $defaultCommand = if ($Adapter.PSObject.Properties.Name -contains 'bridge_command') { [string]$Adapter.bridge_command } else { '' }
    if ([string]::IsNullOrWhiteSpace($resolvedCommandPath) -and -not [string]::IsNullOrWhiteSpace($defaultCommand)) {
        $candidate = Get-Command $defaultCommand -ErrorAction SilentlyContinue
        if ($candidate) {
            $resolvedCommandPath = [string]$candidate.Source
        }
    }

    if ([string]::IsNullOrWhiteSpace($resolvedCommandPath)) {
        $reason = if (-not [string]::IsNullOrWhiteSpace($envName)) {
            ("native_specialist_bridge_command_unavailable:{0}" -f [string]$Adapter.id)
        } else {
            ("native_specialist_adapter_command_unavailable:{0}" -f [string]$Adapter.id)
        }
        return [pscustomobject]@{
            command_path = $null
            reason = $reason
        }
    }

    return [pscustomobject]@{
        command_path = [string]$resolvedCommandPath
        reason = 'native_specialist_bridge_ready'
    }
}

function Resolve-VibeNativeSpecialistAdapter {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    $runtime = Get-VibeRuntimeContext -ScriptPath $ScriptPath
    $policy = $runtime.native_specialist_execution_policy
    $runtimeHostAdapterIdentity = Get-VibeHostAdapterIdentityProjection `
        -HostAdapter $runtime.host_adapter `
        -RequestedPropertyName 'requested_id' `
        -EffectivePropertyName 'id'
    if ($null -eq $policy -or -not [bool]$policy.enabled) {
        return [pscustomobject]@{
            enabled = $false
            live_execution_allowed = $false
            reason = 'native_specialist_execution_policy_disabled'
            runtime = $runtime
            policy = $policy
            adapter = $null
            requested_host_adapter_id = [string]$runtimeHostAdapterIdentity.requested_host_id
            effective_host_adapter_id = [string]$runtimeHostAdapterIdentity.effective_host_id
            command_path = $null
            invocation_arguments_prefix = @()
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
                requested_host_adapter_id = [string]$runtimeHostAdapterIdentity.requested_host_id
                effective_host_adapter_id = [string]$runtimeHostAdapterIdentity.effective_host_id
                command_path = $null
                invocation_arguments_prefix = @()
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
            requested_host_adapter_id = [string]$runtimeHostAdapterIdentity.requested_host_id
            effective_host_adapter_id = [string]$runtimeHostAdapterIdentity.effective_host_id
            command_path = $null
            invocation_arguments_prefix = @()
        }
    }

    $adapterId = if (-not [string]::IsNullOrWhiteSpace([string]$runtimeHostAdapterIdentity.effective_host_id)) {
        [string]$runtimeHostAdapterIdentity.effective_host_id
    } elseif ($policy.PSObject.Properties.Name -contains 'default_adapter_id' -and -not [string]::IsNullOrWhiteSpace([string]$policy.default_adapter_id)) {
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
            requested_host_adapter_id = [string]$runtimeHostAdapterIdentity.requested_host_id
            effective_host_adapter_id = [string]$runtimeHostAdapterIdentity.effective_host_id
            command_path = $null
            invocation_arguments_prefix = @()
        }
    }

    $commandPath = $null
    $invocationArgumentsPrefix = @()
    $resolvedReason = $null
    $invocationKind = if ($adapter.PSObject.Properties.Name -contains 'invocation_kind') { [string]$adapter.invocation_kind } else { 'direct' }

    if ($invocationKind -eq 'python_runner') {
        $bridgeResolution = Resolve-VibeBridgeExecutable -Adapter $adapter -Runtime $runtime
        if ([string]::IsNullOrWhiteSpace([string]$bridgeResolution.command_path)) {
            $resolvedReason = [string]$bridgeResolution.reason
        } else {
            $pythonInvocation = Resolve-VgoPythonCommandSpec -Command '${VGO_PYTHON}'
            $runnerScriptPath = if ($adapter.PSObject.Properties.Name -contains 'runner_script_path' -and -not [string]::IsNullOrWhiteSpace([string]$adapter.runner_script_path)) {
                [System.IO.Path]::GetFullPath((Join-Path $runtime.repo_root ([string]$adapter.runner_script_path)))
            } else {
                $null
            }
            if ([string]::IsNullOrWhiteSpace($runnerScriptPath) -or -not (Test-Path -LiteralPath $runnerScriptPath)) {
                $resolvedReason = ("native_specialist_runner_missing:{0}" -f [string]$adapter.id)
            } else {
                $commandPath = [string]$pythonInvocation.host_path
                $invocationArgumentsPrefix = @($pythonInvocation.prefix_arguments)
                $invocationArgumentsPrefix += @(
                    $runnerScriptPath,
                    '--host-adapter', ([string]$adapter.id),
                    '--bridge-executable', ([string]$bridgeResolution.command_path)
                )
                if ($adapter.PSObject.Properties.Name -contains 'bridge_contract' -and -not [string]::IsNullOrWhiteSpace([string]$adapter.bridge_contract)) {
                    $invocationArgumentsPrefix += @('--bridge-contract', ([string]$adapter.bridge_contract))
                }
                foreach ($item in @($adapter.runner_arguments_prefix)) {
                    $invocationArgumentsPrefix += [string]$item
                }
            }
        }
    } else {
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
        } else {
            $invocationSpec = Resolve-VibeProcessInvocationSpec -CommandPath $commandPath -ArgumentList @()
            $commandPath = [string]$invocationSpec.command_path
            $invocationArgumentsPrefix = @($invocationSpec.arguments)
        }
    }

    return [pscustomobject]@{
        enabled = $true
        live_execution_allowed = [bool](-not [string]::IsNullOrWhiteSpace($commandPath))
        reason = if ($resolvedReason) { $resolvedReason } else { 'native_specialist_execution_ready' }
        runtime = $runtime
        policy = $policy
        adapter = $adapter
        requested_host_adapter_id = if (-not [string]::IsNullOrWhiteSpace([string]$runtimeHostAdapterIdentity.requested_host_id)) { [string]$runtimeHostAdapterIdentity.requested_host_id } else { [string]$adapterId }
        effective_host_adapter_id = [string]$adapter.id
        command_path = $commandPath
        invocation_arguments_prefix = @($invocationArgumentsPrefix)
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

function Test-VibeSpecialistResponseAgainstSchema {
    param(
        [AllowNull()] [object]$Response,
        [Parameter(Mandatory)] [object]$Schema
    )

    $errors = @()
    if ($null -eq $Response) {
        return [pscustomobject]@{
            passed = $false
            errors = @('response_missing')
        }
    }

    $responseProperties = @($Response.PSObject.Properties.Name | ForEach-Object { [string]$_ })
    $schemaProperties = if ($Schema.PSObject.Properties.Name -contains 'properties' -and $Schema.properties) {
        @($Schema.properties.PSObject.Properties.Name | ForEach-Object { [string]$_ })
    } else {
        @()
    }

    foreach ($requiredField in @($Schema.required)) {
        $fieldName = [string]$requiredField
        if (-not ($responseProperties -contains $fieldName)) {
            $errors += ("missing_required_field:{0}" -f $fieldName)
        }
    }

    if ($Schema.PSObject.Properties.Name -contains 'additionalProperties' -and -not [bool]$Schema.additionalProperties) {
        foreach ($responseField in @($responseProperties)) {
            if (-not ($schemaProperties -contains [string]$responseField)) {
                $errors += ("unexpected_field:{0}" -f [string]$responseField)
            }
        }
    }

    foreach ($schemaField in @($schemaProperties)) {
        if (-not ($responseProperties -contains [string]$schemaField)) {
            continue
        }

        $fieldSchema = $Schema.properties.$schemaField
        $fieldValue = $Response.$schemaField
        $expectedType = if ($fieldSchema.PSObject.Properties.Name -contains 'type') { [string]$fieldSchema.type } else { '' }

        switch ($expectedType) {
            'string' {
                if ($fieldValue -isnot [string]) {
                    $errors += ("invalid_type:{0}:expected_string" -f [string]$schemaField)
                    continue
                }
                if ($fieldSchema.PSObject.Properties.Name -contains 'enum' -and @($fieldSchema.enum).Count -gt 0) {
                    $allowedValues = @($fieldSchema.enum | ForEach-Object { [string]$_ })
                    if (-not ($allowedValues -contains [string]$fieldValue)) {
                        $errors += ("invalid_enum:{0}:{1}" -f [string]$schemaField, [string]$fieldValue)
                    }
                }
            }
            'array' {
                if ($fieldValue -is [string]) {
                    $errors += ("invalid_type:{0}:expected_array" -f [string]$schemaField)
                    continue
                }
                $items = @($fieldValue)
                foreach ($item in @($items)) {
                    if ($item -isnot [string]) {
                        $errors += ("invalid_array_item_type:{0}:expected_string" -f [string]$schemaField)
                        break
                    }
                }
            }
        }
    }

    return [pscustomobject]@{
        passed = [bool]($errors.Count -eq 0)
        errors = @($errors)
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
        'You must use the specialist source of truth declared below for this bounded task.',
        ('specialist_skill_id: {0}' -f [string]$Dispatch.skill_id),
        ('bounded_role: {0}' -f [string]$Dispatch.bounded_role),
        ('native_skill_entrypoint: {0}' -f [string]$(if ($Dispatch.PSObject.Properties.Name -contains 'native_skill_entrypoint') { $Dispatch.native_skill_entrypoint } else { '' })),
        ('skill_root: {0}' -f [string]$(if ($Dispatch.PSObject.Properties.Name -contains 'skill_root') { $Dispatch.skill_root } else { '' })),
        ('visibility_class: {0}' -f [string]$(if ($Dispatch.PSObject.Properties.Name -contains 'visibility_class') { $Dispatch.visibility_class } else { '' })),
        ('usage_required: {0}' -f [string]([bool]$(if ($Dispatch.PSObject.Properties.Name -contains 'usage_required') { $Dispatch.usage_required } else { $Dispatch.native_usage_required })).ToString().ToLowerInvariant()),
        ('must_preserve_workflow: {0}' -f [string]([bool]$Dispatch.must_preserve_workflow).ToString().ToLowerInvariant()),
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
        '- Open the declared native_skill_entrypoint before doing bounded specialist work.',
        '- Treat the declared skill root as the only bounded specialist loading root.',
        '- Preserve the named specialist skill native workflow.',
        '- Remain bounded to the frozen requirement and execution plan.',
        '- Do not widen scope or self-approve new specialist dispatch.',
        '- Keep outputs specialist-specific and include verification notes.',
        '- If no repo change is needed, return an empty changed_files array.',
        '',
        'Progressive loading policy:'
    )
    foreach ($item in @($(if ($Dispatch.PSObject.Properties.Name -contains 'progressive_load_policy') { $Dispatch.progressive_load_policy } else { @() }))) {
        $lines += ('- {0}' -f [string]$item)
    }
    $lines += @(
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

function Get-VibeSpecialistPromptInjectionAssessment {
    param(
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$Prompt
    )

    $requiredPairs = @()
    $requiredPairs += [pscustomobject]@{ name = 'native_skill_entrypoint'; value = [string]$(if ($Dispatch.PSObject.Properties.Name -contains 'native_skill_entrypoint') { $Dispatch.native_skill_entrypoint } else { '' }) }
    $requiredPairs += [pscustomobject]@{ name = 'skill_root'; value = [string]$(if ($Dispatch.PSObject.Properties.Name -contains 'skill_root') { $Dispatch.skill_root } else { '' }) }
    $requiredPairs += [pscustomobject]@{ name = 'usage_required'; value = [string]([bool]$(if ($Dispatch.PSObject.Properties.Name -contains 'usage_required') { $Dispatch.usage_required } else { $Dispatch.native_usage_required })).ToString().ToLowerInvariant() }
    $requiredPairs += [pscustomobject]@{ name = 'must_preserve_workflow'; value = [string]([bool]$Dispatch.must_preserve_workflow).ToString().ToLowerInvariant() }

    $missingFields = @()
    foreach ($pair in @($requiredPairs)) {
        if ([string]::IsNullOrWhiteSpace([string]$pair.value)) {
            $missingFields += [string]$pair.name
            continue
        }
        $needle = "{0}: {1}" -f [string]$pair.name, [string]$pair.value
        if (-not ([string]$Prompt).Contains($needle)) {
            $missingFields += [string]$pair.name
        }
    }

    return [pscustomobject]@{
        complete = [bool](@($missingFields).Count -eq 0)
        missing_fields = @($missingFields | Select-Object -Unique)
    }
}

function New-VibeDegradedSpecialistDispatchResult {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$Policy,
        [Parameter(Mandatory)] [string]$Reason,
        [AllowNull()] [object]$AdapterResolution = $null,
        [AllowEmptyString()] [string]$WriteScope = '',
        [AllowEmptyString()] [string]$ReviewMode = 'native_contract',
        [AllowEmptyString()] [string]$PromptPath = '',
        [AllowEmptyCollection()] [string[]]$MissingPromptInjectionFields = @()
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
        usage_required = [bool]$(if ($Dispatch.PSObject.Properties.Name -contains 'usage_required') { $Dispatch.usage_required } else { $Dispatch.native_usage_required })
        must_preserve_workflow = [bool]$Dispatch.must_preserve_workflow
        native_skill_entrypoint = if ($Dispatch.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$Dispatch.native_skill_entrypoint } else { $null }
        skill_root = if ($Dispatch.PSObject.Properties.Name -contains 'skill_root') { [string]$Dispatch.skill_root } else { $null }
        visibility_class = if ($Dispatch.PSObject.Properties.Name -contains 'visibility_class') { [string]$Dispatch.visibility_class } else { $null }
        write_scope = $WriteScope
        review_mode = $ReviewMode
        prompt_path = if ([string]::IsNullOrWhiteSpace($PromptPath)) { $null } else { [string]$PromptPath }
        prompt_injection_complete = [bool]((-not [string]::IsNullOrWhiteSpace($PromptPath)) -and (@($MissingPromptInjectionFields).Count -eq 0))
        missing_prompt_injection_fields = @($MissingPromptInjectionFields | Select-Object -Unique)
        execution_driver = [string]$Policy.degrade_contract.execution_driver
        requested_host_adapter_id = if ($AdapterResolution -and $AdapterResolution.PSObject.Properties.Name -contains 'requested_host_adapter_id') { [string]$AdapterResolution.requested_host_adapter_id } else { $null }
        host_adapter_id = if ($AdapterResolution -and $AdapterResolution.PSObject.Properties.Name -contains 'effective_host_adapter_id') { [string]$AdapterResolution.effective_host_adapter_id } else { $null }
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

function New-VibeBlockedSpecialistDispatchResult {
    param(
        [Parameter(Mandatory)] [string]$UnitId,
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$SessionRoot,
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
    $reasonCodes = if ($Dispatch.PSObject.Properties.Name -contains 'destructive_reason_codes') { @($Dispatch.destructive_reason_codes) } else { @() }
    $stdoutLines = @(
        'Specialist dispatch blocked before execution.',
        ("skill_id={0}" -f [string]$Dispatch.skill_id),
        ("block_reason={0}" -f $Reason),
        ("destructive_reason_codes={0}" -f (@($reasonCodes) -join ','))
    )
    Write-VgoUtf8NoBomText -Path $stdoutPath -Content (($stdoutLines -join [Environment]::NewLine) + [Environment]::NewLine)
    Write-VgoUtf8NoBomText -Path $stderrPath -Content ''

    $finishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    $unitResult = [pscustomobject]@{
        unit_id = $UnitId
        kind = 'specialist_dispatch'
        status = 'blocked'
        started_at = $startedAt
        finished_at = $finishedAt
        command = ("specialist:{0}" -f [string]$Dispatch.skill_id)
        arguments = @()
        display_command = ("specialist:{0}" -f [string]$Dispatch.skill_id)
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
        verification_passed = $false
        specialist_skill_id = [string]$Dispatch.skill_id
        bounded_role = [string]$Dispatch.bounded_role
        native_usage_required = [bool]$Dispatch.native_usage_required
        must_preserve_workflow = [bool]$Dispatch.must_preserve_workflow
        write_scope = $WriteScope
        review_mode = $ReviewMode
        execution_driver = 'blocked_specialist_contract_receipt'
        live_native_execution = $false
        degraded = $false
        blocked = $true
        block_reason = $Reason
        destructive_reason_codes = @($reasonCodes)
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
            -AdapterResolution $adapterResolution `
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
    $promptInjection = Get-VibeSpecialistPromptInjectionAssessment -Dispatch $Dispatch -Prompt $prompt
    if (-not [bool]$promptInjection.complete) {
        return New-VibeDegradedSpecialistDispatchResult `
            -UnitId $UnitId `
            -Dispatch $Dispatch `
            -SessionRoot $SessionRoot `
            -Policy $policy `
            -Reason 'authoritative_prompt_injection_incomplete' `
            -AdapterResolution $adapterResolution `
            -WriteScope $WriteScope `
            -ReviewMode $ReviewMode `
            -PromptPath $promptPath `
            -MissingPromptInjectionFields @($promptInjection.missing_fields)
    }

    $beforeSnapshot = Get-VibeGitStatusSnapshot -RepoRoot $RepoRoot
    Write-VgoUtf8NoBomText -Path $beforeGitPath -Content ((@($beforeSnapshot.lines) -join [Environment]::NewLine) + [Environment]::NewLine)

    $arguments = @()
    foreach ($item in @($adapterResolution.invocation_arguments_prefix)) {
        $arguments += [string]$item
    }
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

    $schemaValidation = Test-VibeSpecialistResponseAgainstSchema -Response $parsedResponse -Schema $schema
    $verificationPassed = (-not $processResult.timed_out) -and ([int]$processResult.exit_code -eq 0) -and ($null -ne $parsedResponse) -and [bool]$schemaValidation.passed -and (@('completed', 'completed_with_notes') -contains $responseStatus)
    $effectiveStatus = if ($verificationPassed) {
        'completed'
    } elseif ($processResult.timed_out) {
        'timed_out'
    } elseif ($responseStatus -eq 'blocked' -and [int]$processResult.exit_code -eq 0 -and [string]::IsNullOrWhiteSpace($responseParseError) -and [bool]$schemaValidation.passed) {
        'blocked'
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
        usage_required = [bool]$(if ($Dispatch.PSObject.Properties.Name -contains 'usage_required') { $Dispatch.usage_required } else { $Dispatch.native_usage_required })
        must_preserve_workflow = [bool]$Dispatch.must_preserve_workflow
        native_skill_entrypoint = if ($Dispatch.PSObject.Properties.Name -contains 'native_skill_entrypoint') { [string]$Dispatch.native_skill_entrypoint } else { $null }
        skill_root = if ($Dispatch.PSObject.Properties.Name -contains 'skill_root') { [string]$Dispatch.skill_root } else { $null }
        visibility_class = if ($Dispatch.PSObject.Properties.Name -contains 'visibility_class') { [string]$Dispatch.visibility_class } else { $null }
        write_scope = $WriteScope
        review_mode = $ReviewMode
        execution_driver = [string]$adapter.execution_driver
        requested_host_adapter_id = [string]$adapterResolution.requested_host_adapter_id
        host_adapter_id = [string]$adapter.id
        live_native_execution = $true
        degraded = $false
        requirement_doc_path = $RequirementDocPath
        execution_plan_path = $ExecutionPlanPath
        response_json_path = $responsePath
        prompt_path = $promptPath
        prompt_injection_complete = [bool]$promptInjection.complete
        missing_prompt_injection_fields = @($promptInjection.missing_fields)
        schema_path = $schemaPath
        git_status_before_path = $beforeGitPath
        git_status_after_path = $afterGitPath
        changed_files = @($changedFiles)
        observed_changed_files = @($observedChangedFiles)
        verification_notes = @($verificationNotes)
        bounded_output_notes = @($boundedOutputNotes)
        summary = $responseSummary
        response_parse_error = $responseParseError
        response_schema_errors = @($schemaValidation.errors)
    }

    $resultPath = Join-Path $resultsRoot ("{0}.json" -f $UnitId)
    Write-VibeJsonArtifact -Path $resultPath -Value $unitResult

    return [pscustomobject]@{
        result = $unitResult
        result_path = $resultPath
    }
}

function Get-VibeExecutionProfileById {
    param(
        [Parameter(Mandatory)] [object]$ExecutionPolicy,
        [Parameter(Mandatory)] [string]$ProfileId
    )

    foreach ($candidate in @($ExecutionPolicy.profiles)) {
        if ([string]$candidate.id -eq $ProfileId) {
            return $candidate
        }
    }

    throw "Unable to resolve execution profile '$ProfileId'."
}

function Get-VibeExecutionTopologyProfile {
    param(
        [Parameter(Mandatory)] [object]$ExecutionPolicy,
        [Parameter(Mandatory)] [object]$TopologyPolicy,
        [Parameter(Mandatory)] [string]$Grade
    )

    $gradePolicy = $TopologyPolicy.grades.$Grade
    if ($null -eq $gradePolicy) {
        throw "Unable to resolve execution topology policy for grade '$Grade'."
    }

    $profileId = [string]$ExecutionPolicy.default_profile_id
    $profile = Get-VibeExecutionProfileById -ExecutionPolicy $ExecutionPolicy -ProfileId $profileId

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

function Get-VibeSpecialistDispatchPhaseSortOrder {
    param(
        [AllowEmptyString()] [string]$DispatchPhase
    )

    switch ([string]$DispatchPhase) {
        'pre_execution' { return 10 }
        'in_execution' { return 20 }
        'post_execution' { return 30 }
        'verification' { return 40 }
        default { return 20 }
    }
}

function New-VibeSpecialistLaneEntry {
    param(
        [Parameter(Mandatory)] [object]$Dispatch,
        [Parameter(Mandatory)] [string]$Grade,
        [Parameter(Mandatory)] [string]$GovernanceScope
    )

    $lanePolicy = if ($Dispatch.PSObject.Properties.Name -contains 'lane_policy' -and -not [string]::IsNullOrWhiteSpace([string]$Dispatch.lane_policy)) {
        [string]$Dispatch.lane_policy
    } else {
        'inherit_grade'
    }
    $parallelizable = $false
    if ($Grade -eq 'XL' -and $GovernanceScope -eq 'root') {
        $parallelizable = [bool]$Dispatch.parallelizable_in_root_xl -and ($lanePolicy -ne 'serial')
    }

    $writeScope = if ($Dispatch.PSObject.Properties.Name -contains 'write_scope' -and -not [string]::IsNullOrWhiteSpace([string]$Dispatch.write_scope)) {
        [string]$Dispatch.write_scope
    } else {
        "specialist:{0}" -f [string]$Dispatch.skill_id
    }

    return [pscustomobject]@{
        lane_id = "specialist-{0}-{1}" -f [string]$Dispatch.dispatch_phase, [string]$Dispatch.skill_id
        lane_kind = 'specialist_dispatch'
        source_unit_id = [string]$Dispatch.skill_id
        specialist_skill_id = [string]$Dispatch.skill_id
        dispatch_phase = if ($Dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$Dispatch.dispatch_phase } else { 'in_execution' }
        binding_profile = if ($Dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$Dispatch.binding_profile } else { 'default' }
        lane_policy = $lanePolicy
        execution_priority = if ($Dispatch.PSObject.Properties.Name -contains 'execution_priority') { [int]$Dispatch.execution_priority } else { 50 }
        parallelizable = [bool]$parallelizable
        write_scope = $writeScope
        review_mode = if ($Dispatch.PSObject.Properties.Name -contains 'review_mode' -and -not [string]::IsNullOrWhiteSpace([string]$Dispatch.review_mode)) { [string]$Dispatch.review_mode } else { 'native_contract' }
        dispatch = $Dispatch
    }
}

function New-VibeSpecialistPhaseSteps {
    param(
        [Parameter(Mandatory)] [string]$WaveId,
        [Parameter(Mandatory)] [string]$Phase,
        [Parameter(Mandatory)] [string]$Grade,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [object]$ProfileDef,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$Dispatches
    )

    $steps = @()
    $orderedDispatches = @(
        $Dispatches |
            Sort-Object `
                @{ Expression = { Get-VibeSpecialistDispatchPhaseSortOrder -DispatchPhase ([string]$_.dispatch_phase) } }, `
                @{ Expression = { if ($_.PSObject.Properties.Name -contains 'execution_priority') { [int]$_.execution_priority } else { 50 } } }, `
                @{ Expression = { [string]$_.skill_id } }
    )
    if (@($orderedDispatches).Count -eq 0) {
        return @()
    }

    $units = @()
    foreach ($dispatch in @($orderedDispatches)) {
        $units += New-VibeSpecialistLaneEntry -Dispatch $dispatch -Grade $Grade -GovernanceScope $GovernanceScope
    }

    $parallelUnits = @($units | Where-Object { $_.parallelizable })
    $serialUnits = @($units | Where-Object { -not $_.parallelizable })
    if (@($parallelUnits).Count -gt 0) {
        $steps += [pscustomobject]@{
            step_id = "{0}-specialist-{1}-parallel" -f $WaveId, $Phase
            execution_mode = 'bounded_parallel'
            review_mode = [string]$parallelUnits[0].review_mode
            max_parallel_units = [int]$ProfileDef.max_parallel_units
            units = @($parallelUnits)
        }
    }

    $serialIndex = 0
    foreach ($entry in @($serialUnits)) {
        $serialIndex += 1
        $steps += [pscustomobject]@{
            step_id = "{0}-specialist-{1}-serial-{2}" -f $WaveId, $Phase, $serialIndex
            execution_mode = 'sequential'
            review_mode = [string]$entry.review_mode
            max_parallel_units = 1
            units = @($entry)
        }
    }

    return @($steps)
}

function New-VibeExecutionTopology {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Grade,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [Parameter(Mandatory)] [object]$ExecutionPolicy,
        [Parameter(Mandatory)] [object]$TopologyPolicy,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [object[]]$ApprovedDispatch
    )

    $profileDef = Get-VibeExecutionTopologyProfile -ExecutionPolicy $ExecutionPolicy -TopologyPolicy $TopologyPolicy -Grade $Grade
    $effectiveSpecialistExecutionMode = [string]$profileDef.specialist_execution_mode
    if (@($ApprovedDispatch).Count -gt 0) {
        $effectiveSpecialistExecutionMode = 'native_bounded_units'
    }
    $steps = @()
    $specialistPhaseBuckets = [ordered]@{
        pre_execution = @()
        in_execution = @()
        post_execution = @()
        verification = @()
    }
    foreach ($dispatch in @($ApprovedDispatch)) {
        $phase = if ($dispatch.PSObject.Properties.Name -contains 'dispatch_phase' -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.dispatch_phase)) {
            [string]$dispatch.dispatch_phase
        } else {
            'in_execution'
        }
        if (-not $specialistPhaseBuckets.Contains($phase)) {
            $phase = 'in_execution'
        }
        $specialistPhaseBuckets[$phase] += $dispatch
    }

    $waveCount = @($profileDef.profile.waves).Count

    $waveIndex = 0
    foreach ($wave in @($profileDef.profile.waves)) {
        $waveIndex += 1
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
                lane_kind = 'execution_unit'
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
            $prependedSteps = @()
            $appendedSteps = @()

            if ($waveIndex -eq 1) {
                $prependedSteps += New-VibeSpecialistPhaseSteps `
                    -WaveId ([string]$wave.wave_id) `
                    -Phase 'pre_execution' `
                    -Grade $Grade `
                    -GovernanceScope $GovernanceScope `
                    -ProfileDef $profileDef `
                    -Dispatches @($specialistPhaseBuckets.pre_execution)

                $appendedSteps += New-VibeSpecialistPhaseSteps `
                    -WaveId ([string]$wave.wave_id) `
                    -Phase 'in_execution' `
                    -Grade $Grade `
                    -GovernanceScope $GovernanceScope `
                    -ProfileDef $profileDef `
                    -Dispatches @($specialistPhaseBuckets.in_execution)
            }

            if ($waveIndex -eq $waveCount) {
                $appendedSteps += New-VibeSpecialistPhaseSteps `
                    -WaveId ([string]$wave.wave_id) `
                    -Phase 'post_execution' `
                    -Grade $Grade `
                    -GovernanceScope $GovernanceScope `
                    -ProfileDef $profileDef `
                    -Dispatches @($specialistPhaseBuckets.post_execution)

                $appendedSteps += New-VibeSpecialistPhaseSteps `
                    -WaveId ([string]$wave.wave_id) `
                    -Phase 'verification' `
                    -Grade $Grade `
                    -GovernanceScope $GovernanceScope `
                    -ProfileDef $profileDef `
                    -Dispatches @($specialistPhaseBuckets.verification)
            }

            $waveSteps = @($prependedSteps) + @($waveSteps) + @($appendedSteps)
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
        specialist_phase_bindings = [pscustomobject]@{
            pre_execution = @($specialistPhaseBuckets.pre_execution)
            in_execution = @($specialistPhaseBuckets.in_execution)
            post_execution = @($specialistPhaseBuckets.post_execution)
            verification = @($specialistPhaseBuckets.verification)
        }
        parallelizable_specialist_unit_count = @($ApprovedDispatch | Where-Object { [bool]$_.parallelizable_in_root_xl }).Count
        waves = @($steps)
    }
}
