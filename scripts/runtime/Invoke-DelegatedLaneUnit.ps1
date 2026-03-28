param(
    [Parameter(Mandatory)] [string]$LaneSpecPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')
. (Join-Path $PSScriptRoot 'VibeExecution.Common.ps1')

$laneSpec = Get-Content -LiteralPath $LaneSpecPath -Raw -Encoding UTF8 | ConvertFrom-Json
$laneRoot = [string]$laneSpec.lane_root
New-Item -ItemType Directory -Path $laneRoot -Force | Out-Null

$laneKind = [string]$laneSpec.lane_kind
$receiptPath = Join-Path $laneRoot 'lane-receipt.json'
$notesPath = Join-Path $laneRoot 'lane-notes.md'
$receipt = $null
$resultPath = $null

switch ($laneKind) {
    'benchmark_unit' {
        $tokens = @{}
        foreach ($property in @($laneSpec.tokens.PSObject.Properties)) {
            $tokens[$property.Name] = [string]$property.Value
        }

        $laneStartedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
        $executed = Invoke-VibeExecutionUnit `
            -Unit $laneSpec.unit `
            -RepoRoot ([string]$laneSpec.repo_root) `
            -SessionRoot $laneRoot `
            -Tokens $tokens `
            -DefaultTimeoutSeconds ([int]$laneSpec.default_timeout_seconds)
        $laneFinishedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')

        $envelopedResult = [pscustomobject]@{}
        foreach ($property in @($executed.result.PSObject.Properties)) {
            $envelopedResult | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value
        }
        $envelopedResult.started_at = $laneStartedAt
        $envelopedResult.finished_at = $laneFinishedAt

        $resultPath = [string]$executed.result_path
        Write-VibeJsonArtifact -Path $resultPath -Value $envelopedResult
        $receipt = [pscustomobject]@{
            lane_id = [string]$laneSpec.lane_id
            lane_kind = $laneKind
            governance_scope = 'child'
            run_id = [string]$laneSpec.run_id
            root_run_id = [string]$laneSpec.root_run_id
            parent_run_id = [string]$laneSpec.parent_run_id
            parent_unit_id = [string]$laneSpec.parent_unit_id
            requirement_doc_path = [string]$laneSpec.requirement_doc_path
            execution_plan_path = [string]$laneSpec.execution_plan_path
            execution_driver = 'delegated_process_unit'
            parallelizable = [bool]$laneSpec.parallelizable
            write_scope = [string]$laneSpec.write_scope
            review_mode = [string]$laneSpec.review_mode
            status = [string]$envelopedResult.status
            verification_passed = [bool]$envelopedResult.verification_passed
            result_path = $resultPath
            started_at = [string]$envelopedResult.started_at
            finished_at = [string]$envelopedResult.finished_at
            generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        }
        Write-VibeMarkdownArtifact -Path $notesPath -Lines @(
            "# Delegated Lane Notes",
            '',
            "- lane_id: $([string]$laneSpec.lane_id)",
            "- lane_kind: benchmark_unit",
            "- write_scope: $([string]$laneSpec.write_scope)",
            "- verification_passed: $([bool]$envelopedResult.verification_passed)",
            "- result_path: $resultPath"
        )
    }
    'specialist_dispatch' {
        $dispatch = $laneSpec.dispatch
        $executed = Invoke-VibeSpecialistDispatchUnit `
            -UnitId ("{0}-specialist" -f [string]$laneSpec.lane_id) `
            -Dispatch $dispatch `
            -SessionRoot $laneRoot `
            -RepoRoot ([string]$laneSpec.repo_root) `
            -RequirementDocPath ([string]$laneSpec.requirement_doc_path) `
            -ExecutionPlanPath ([string]$laneSpec.execution_plan_path) `
            -RunId ([string]$laneSpec.run_id) `
            -GovernanceScope ([string]$laneSpec.governance_scope) `
            -RootRunId ([string]$laneSpec.root_run_id) `
            -ParentRunId ([string]$laneSpec.parent_run_id) `
            -ParentUnitId ([string]$laneSpec.parent_unit_id) `
            -WriteScope ([string]$laneSpec.write_scope) `
            -ReviewMode ([string]$laneSpec.review_mode)

        $resultPath = [string]$executed.result_path
        $receipt = [pscustomobject]@{
            lane_id = [string]$laneSpec.lane_id
            lane_kind = $laneKind
            governance_scope = 'child'
            run_id = [string]$laneSpec.run_id
            root_run_id = [string]$laneSpec.root_run_id
            parent_run_id = [string]$laneSpec.parent_run_id
            parent_unit_id = [string]$laneSpec.parent_unit_id
            requirement_doc_path = [string]$laneSpec.requirement_doc_path
            execution_plan_path = [string]$laneSpec.execution_plan_path
            execution_driver = [string]$executed.result.execution_driver
            parallelizable = [bool]$laneSpec.parallelizable
            write_scope = [string]$laneSpec.write_scope
            review_mode = [string]$laneSpec.review_mode
            status = [string]$executed.result.status
            verification_passed = [bool]$executed.result.verification_passed
            specialist_skill_id = [string]$dispatch.skill_id
            bounded_role = [string]$dispatch.bounded_role
            dispatch_phase = if ($dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$dispatch.dispatch_phase } else { 'in_execution' }
            binding_profile = if ($dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$dispatch.binding_profile } else { 'default' }
            lane_policy = if ($dispatch.PSObject.Properties.Name -contains 'lane_policy') { [string]$dispatch.lane_policy } else { 'inherit_grade' }
            native_usage_required = [bool]$dispatch.native_usage_required
            must_preserve_workflow = [bool]$dispatch.must_preserve_workflow
            result_path = $resultPath
            started_at = [string]$executed.result.started_at
            finished_at = [string]$executed.result.finished_at
            generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        }
        Write-VibeMarkdownArtifact -Path $notesPath -Lines @(
            "# Native Specialist Dispatch Receipt",
            '',
            "- specialist_skill_id: $([string]$dispatch.skill_id)",
            "- execution_driver: $([string]$executed.result.execution_driver)",
            "- bounded_role: $([string]$dispatch.bounded_role)",
            "- dispatch_phase: $(if ($dispatch.PSObject.Properties.Name -contains 'dispatch_phase') { [string]$dispatch.dispatch_phase } else { 'in_execution' })",
            "- binding_profile: $(if ($dispatch.PSObject.Properties.Name -contains 'binding_profile') { [string]$dispatch.binding_profile } else { 'default' })",
            "- lane_policy: $(if ($dispatch.PSObject.Properties.Name -contains 'lane_policy') { [string]$dispatch.lane_policy } else { 'inherit_grade' })",
            "- parallelizable: $([bool]$laneSpec.parallelizable)",
            "- native_usage_required: $([bool]$dispatch.native_usage_required)",
            "- verification_expectation: $([string]$dispatch.verification_expectation)",
            "- required_inputs: $([string]::Join(', ', @($dispatch.required_inputs)))",
            "- expected_outputs: $([string]::Join(', ', @($dispatch.expected_outputs)))",
            "- result_path: $resultPath"
        )
    }
    default {
        throw "Unsupported delegated lane kind: $laneKind"
    }
}

Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

[pscustomobject]@{
    lane_receipt_path = $receiptPath
    lane_notes_path = $notesPath
    lane_result_path = $resultPath
    receipt = $receipt
} | ConvertTo-Json -Depth 20 -Compress
