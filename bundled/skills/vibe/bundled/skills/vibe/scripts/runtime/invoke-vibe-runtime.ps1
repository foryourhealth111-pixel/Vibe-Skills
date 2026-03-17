param(
    [Parameter(Mandatory)] [string]$Task,
    [ValidateSet('interactive_governed', 'benchmark_autonomous')] [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = '',
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
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}
$artifactBaseRoot = Get-VibeArtifactRoot -RepoRoot $runtime.repo_root -ArtifactRoot $ArtifactRoot

$skeleton = & (Join-Path $PSScriptRoot 'Invoke-SkeletonCheck.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$runtimeInput = & (Join-Path $PSScriptRoot 'Freeze-RuntimeInputPacket.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$interview = & (Join-Path $PSScriptRoot 'Invoke-DeepInterview.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot
$requirement = & (Join-Path $PSScriptRoot 'Write-RequirementDoc.ps1') -Task $Task -Mode $Mode -RunId $RunId -IntentContractPath $interview.receipt_path -RuntimeInputPacketPath $runtimeInput.packet_path -ArtifactRoot $ArtifactRoot
$plan = & (Join-Path $PSScriptRoot 'Write-XlPlan.ps1') -Task $Task -Mode $Mode -RunId $RunId -RequirementDocPath $requirement.requirement_doc_path -RuntimeInputPacketPath $runtimeInput.packet_path -ArtifactRoot $ArtifactRoot
$execute = & (Join-Path $PSScriptRoot 'Invoke-PlanExecute.ps1') -Task $Task -Mode $Mode -RunId $RunId -RequirementDocPath $requirement.requirement_doc_path -ExecutionPlanPath $plan.execution_plan_path -RuntimeInputPacketPath $runtimeInput.packet_path -ArtifactRoot $ArtifactRoot
$cleanup = & (Join-Path $PSScriptRoot 'Invoke-PhaseCleanup.ps1') -Task $Task -Mode $Mode -RunId $RunId -ArtifactRoot $ArtifactRoot -ExecuteGovernanceCleanup:$ExecuteGovernanceCleanup -ApplyManagedNodeCleanup:$ApplyManagedNodeCleanup

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
    [string]$execute.benchmark_proof_manifest_path,
    [string]$cleanup.receipt_path
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
    benchmark_proof_manifest = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$execute.benchmark_proof_manifest_path)
    cleanup_receipt = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$cleanup.receipt_path)
}

$summary = [pscustomobject]@{
    run_id = $RunId
    mode = $Mode
    task = $Task
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    artifact_root = $artifactBaseRoot
    session_root = $skeleton.session_root
    session_root_relative = Get-VibeRelativePathCompat -BasePath $artifactBaseRoot -TargetPath ([string]$skeleton.session_root)
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
        benchmark_proof_manifest = $execute.benchmark_proof_manifest_path
        cleanup_receipt = $cleanup.receipt_path
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
