param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
    [switch]$ExecuteGovernanceCleanup,
    [switch]$ApplyManagedNodeCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeSkillRouting.Common.ps1')

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
$Mode = Resolve-VibeRuntimeMode -Mode $Mode -DefaultMode ([string]$runtime.runtime_modes.default_mode)
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -Runtime $runtime -ArtifactRoot $ArtifactRoot
$shouldExecuteGovernanceCleanup = [bool]$ExecuteGovernanceCleanup
$shouldExecuteBoundedDefaultCleanup = $false
foreach ($defaultMode in @($runtime.cleanup_policy.bounded_default_modes)) {
    if ([string]$defaultMode -eq [string]$Mode) {
        $shouldExecuteBoundedDefaultCleanup = $true
        break
    }
}

$deliveryAcceptanceReportPath = Join-Path $sessionRoot 'delivery-acceptance-report.json'
$deliveryAcceptanceMarkdownPath = Join-Path $sessionRoot 'delivery-acceptance-report.md'

function Invoke-VibeDeliveryAcceptanceEvaluation {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$ReportPath,
        [Parameter(Mandatory)] [string]$MarkdownPath
    )

    $scriptPath = Join-Path $RepoRoot 'scripts\verify\runtime_neutral\runtime_delivery_acceptance.py'
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        return [pscustomobject]@{
            acceptance = $null
            error_message = "Missing runtime delivery acceptance evaluator: $scriptPath"
        }
    }

    try {
        $pythonInvocation = Get-VgoPythonCommand
        $pythonArgs = @($pythonInvocation.prefix_arguments)
        $pythonArgs += @(
            $scriptPath,
            '--repo-root', $RepoRoot,
            '--session-root', $SessionRoot,
            '--write-artifacts',
            '--output-directory', $SessionRoot
        )
        $commandOutput = & $pythonInvocation.host_path @pythonArgs 2>&1
        $commandExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }

        $report = if (Test-Path -LiteralPath $ReportPath) {
            Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } else {
            $commandText = (@($commandOutput) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
            if ([string]::IsNullOrWhiteSpace($commandText)) {
                throw 'runtime_delivery_acceptance.py produced neither artifact nor JSON output.'
            }
            $commandText | ConvertFrom-Json
        }

        return [pscustomobject]@{
            acceptance = [pscustomobject]@{
                report_path = $ReportPath
                markdown_path = if (Test-Path -LiteralPath $MarkdownPath) { $MarkdownPath } else { $null }
                gate_result = [string]$report.summary.gate_result
                completion_language_allowed = [bool]$report.summary.completion_language_allowed
                runtime_status = [string]$report.summary.runtime_status
                readiness_state = [string]$report.summary.readiness_state
                manual_review_layer_count = [int]$report.summary.manual_review_layer_count
                failing_layer_count = [int]$report.summary.failing_layer_count
                forbidden_completion_hit_count = [int]$report.summary.forbidden_completion_hit_count
                incomplete_layers = @($report.summary.incomplete_layers)
                command_exit_code = $commandExitCode
            }
            error_message = $null
        }
    } catch {
        return [pscustomobject]@{
            acceptance = $null
            error_message = $_.Exception.Message
        }
    }
}

function Update-VibeRuntimeSummaryAcceptance {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$ReportPath,
        [Parameter(Mandatory)] [string]$ReceiptPath
    )

    $summaryPath = Join-Path $SessionRoot 'runtime-summary.json'
    if (-not (Test-Path -LiteralPath $summaryPath -PathType Leaf)) {
        return
    }

    $pythonInvocation = Get-VgoPythonCommand
    $scriptPath = Join-Path $RepoRoot 'packages\runtime-core\src\vgo_runtime\canonical_entry.py'
    $pythonArgs = @($pythonInvocation.prefix_arguments)
    $pythonArgs += @(
        $scriptPath,
        '--refresh-runtime-summary-acceptance',
        '--runtime-summary-json', $summaryPath,
        '--delivery-acceptance-report-json', $ReportPath,
        '--cleanup-receipt-path', $ReceiptPath
    )
    $commandOutput = & $pythonInvocation.host_path @pythonArgs 2>&1
    $commandExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($commandExitCode -ne 0) {
        throw ("Python runtime summary acceptance refresh exited with code {0}: {1}" -f $commandExitCode, ((@($commandOutput) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine))
    }
}

$cleanupResult = $null
$cleanupError = $null
$cleanupMode = 'receipt_only'
$deliveryAcceptance = $null
$deliveryAcceptanceError = $null
$cleanupAdmitted = $false
$receipt = [pscustomobject]@{
    stage = 'phase_cleanup'
    run_id = $RunId
    mode = $Mode
    task = $Task
    cleanup_mode = $cleanupMode
    cleanup_admitted = $false
    default_bounded_cleanup_applied = $false
    execute_governance_cleanup_requested = [bool]$ExecuteGovernanceCleanup
    managed_node_cleanup_applied = $false
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    cleanup_result = $cleanupResult
    cleanup_error = $cleanupError
    delivery_acceptance = $deliveryAcceptance
    delivery_acceptance_error = $deliveryAcceptanceError
    proof_class = [string]$runtime.proof_class_registry.artifact_class_defaults.cleanup_receipt
}

$receiptPath = Join-Path $sessionRoot 'cleanup-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

$preCleanupEvaluation = Invoke-VibeDeliveryAcceptanceEvaluation `
    -RepoRoot $runtime.repo_root `
    -SessionRoot $sessionRoot `
    -ReportPath $deliveryAcceptanceReportPath `
    -MarkdownPath $deliveryAcceptanceMarkdownPath
$deliveryAcceptance = $preCleanupEvaluation.acceptance
$deliveryAcceptanceError = $preCleanupEvaluation.error_message
$cleanupAdmitted = (
    $null -ne $deliveryAcceptance -and
    [string]$deliveryAcceptance.gate_result -eq 'PASS' -and
    [bool]$deliveryAcceptance.completion_language_allowed
)

if (-not $cleanupAdmitted) {
    $cleanupResult = [pscustomobject]@{
        performed = $false
        reason = 'delivery_acceptance_not_passed'
    }
} elseif ($shouldExecuteGovernanceCleanup) {
    $cleanupArgs = @('-WriteArtifacts')
    if ($ApplyManagedNodeCleanup) {
        $cleanupArgs += '-ApplyManagedNodeCleanup'
    }
    try {
        $cleanupInvocation = Invoke-VgoPowerShellFile -ScriptPath (Join-Path $runtime.repo_root 'scripts\governance\phase-end-cleanup.ps1') -ArgumentList $cleanupArgs -NoProfile
        $cleanupResultText = (@($cleanupInvocation.output) -join [Environment]::NewLine).Trim()
        $cleanupResult = if ([string]::IsNullOrWhiteSpace($cleanupResultText)) {
            $cleanupInvocation
        } else {
            $cleanupResultText | ConvertFrom-Json
        }
        $cleanupMode = if ($ApplyManagedNodeCleanup) { 'destructive_cleanup_applied' } else { 'bounded_cleanup_executed' }
    } catch {
        $cleanupError = $_.Exception.Message
        $cleanupMode = 'cleanup_degraded'
    }
} elseif ($shouldExecuteBoundedDefaultCleanup) {
    try {
        $nodeAuditDir = Join-Path $sessionRoot 'process-health-audits'
        $nodeCleanupDir = Join-Path $sessionRoot 'process-health-cleanups'
        New-Item -ItemType Directory -Path $nodeAuditDir -Force | Out-Null
        New-Item -ItemType Directory -Path $nodeCleanupDir -Force | Out-Null

        $auditResult = & (Join-Path $runtime.repo_root 'scripts\governance\Invoke-NodeProcessAudit.ps1') -PassThru -WriteMarkdown -OutputDirectory $nodeAuditDir -RepoRoot $runtime.repo_root
        $cleanupPreview = & (Join-Path $runtime.repo_root 'scripts\governance\Invoke-NodeZombieCleanup.ps1') -PassThru -OutputDirectory $nodeCleanupDir -RepoRoot $runtime.repo_root
        $cleanupResult = [pscustomobject]@{
            execution_scope = 'session_bounded_default'
            repo_root = $runtime.repo_root
            session_root = $sessionRoot
            temp_cleanup = [pscustomobject]@{
                performed = $false
                reason = 'session_artifacts_retained_as_proof'
            }
            node_audit = [pscustomobject]@{
                artifact_path = [string]$auditResult.artifact_path
                markdown_path = [string]$auditResult.markdown_path
                summary = $auditResult.payload.summary
            }
            node_cleanup_preview = [pscustomobject]@{
                artifact_path = [string]$cleanupPreview.artifact_path
                apply_requested = [bool]$cleanupPreview.payload.apply_requested
                cleanup_candidate_count = [int]$cleanupPreview.payload.cleanup_candidate_count
                results = @($cleanupPreview.payload.results)
            }
        }
        $cleanupMode = 'bounded_cleanup_executed'
    } catch {
        $cleanupError = $_.Exception.Message
        $cleanupMode = 'cleanup_degraded'
    }
} else {
    $cleanupResult = [pscustomobject]@{
        performed = $false
        reason = 'no_cleanup_action_requested'
    }
}

$receipt.cleanup_admitted = [bool]$cleanupAdmitted
$receipt.default_bounded_cleanup_applied = [bool]($cleanupAdmitted -and $shouldExecuteBoundedDefaultCleanup -and -not $ExecuteGovernanceCleanup)
$receipt.managed_node_cleanup_applied = [bool]($cleanupMode -eq 'destructive_cleanup_applied')
$receipt.cleanup_mode = $cleanupMode
$receipt.cleanup_result = $cleanupResult
$receipt.cleanup_error = $cleanupError
$receipt.delivery_acceptance = $deliveryAcceptance
$receipt.delivery_acceptance_error = $deliveryAcceptanceError
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

$finalEvaluation = Invoke-VibeDeliveryAcceptanceEvaluation `
    -RepoRoot $runtime.repo_root `
    -SessionRoot $sessionRoot `
    -ReportPath $deliveryAcceptanceReportPath `
    -MarkdownPath $deliveryAcceptanceMarkdownPath
$deliveryAcceptance = $finalEvaluation.acceptance
$deliveryAcceptanceError = $finalEvaluation.error_message
$receipt.delivery_acceptance = $deliveryAcceptance
$receipt.delivery_acceptance_error = $deliveryAcceptanceError
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt
if ($null -ne $deliveryAcceptance -and [string]::IsNullOrWhiteSpace([string]$deliveryAcceptanceError)) {
    Update-VibeRuntimeSummaryAcceptance `
        -RepoRoot $runtime.repo_root `
        -SessionRoot $sessionRoot `
        -ReportPath $deliveryAcceptanceReportPath `
        -ReceiptPath $receiptPath
}

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    receipt_path = $receiptPath
    receipt = $receipt
}
