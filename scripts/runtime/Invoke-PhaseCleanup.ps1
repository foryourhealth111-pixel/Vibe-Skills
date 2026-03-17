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

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$shouldExecuteGovernanceCleanup = [bool]$ExecuteGovernanceCleanup
$shouldExecuteBoundedDefaultCleanup = $false
foreach ($defaultMode in @($runtime.cleanup_policy.bounded_default_modes)) {
    if ([string]$defaultMode -eq [string]$Mode) {
        $shouldExecuteBoundedDefaultCleanup = $true
        break
    }
}

$cleanupResult = $null
$cleanupError = $null
$cleanupMode = 'receipt_only'
if ($shouldExecuteGovernanceCleanup) {
    $cleanupArgs = @()
    $cleanupArgs += '-WriteArtifacts'
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

        if ($ApplyManagedNodeCleanup) {
            $cleanupMode = 'destructive_cleanup_applied'
        } else {
            $cleanupMode = 'bounded_cleanup_executed'
        }
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
}

$receipt = [pscustomobject]@{
    stage = 'phase_cleanup'
    run_id = $RunId
    mode = $Mode
    task = $Task
    cleanup_mode = $cleanupMode
    default_bounded_cleanup_applied = [bool]($shouldExecuteBoundedDefaultCleanup -and -not $ExecuteGovernanceCleanup)
    execute_governance_cleanup_requested = [bool]$ExecuteGovernanceCleanup
    managed_node_cleanup_applied = [bool]$ApplyManagedNodeCleanup
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    cleanup_result = $cleanupResult
    cleanup_error = $cleanupError
    proof_class = [string]$runtime.proof_class_registry.artifact_class_defaults.cleanup_receipt
}

$receiptPath = Join-Path $sessionRoot 'cleanup-receipt.json'
Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    receipt_path = $receiptPath
    receipt = $receipt
}
