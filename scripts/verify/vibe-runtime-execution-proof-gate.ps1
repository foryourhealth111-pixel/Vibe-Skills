param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\runtime\VibeRuntime.Common.ps1')

function Add-Assertion {
    param(
        [ref]$Results,
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ''
    )

    $record = [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }
    $Results.Value += $record

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        if ($Details) {
            Write-Host "       $Details" -ForegroundColor DarkRed
        }
    }
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$results = @()

$requiredFiles = @(
    'config/runtime-input-packet-policy.json',
    'scripts/runtime/Invoke-PlanExecute.ps1'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required execution proof file exists: {0}" -f $relativePath) -Details $fullPath
}

$runId = "execution-proof-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\execution-proof-{0}" -f $runId)
$hostRoot = Join-Path $artifactRoot '.agents'
$hostSkillsRoot = Join-Path $hostRoot 'skills'
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$originalAgentsHome = $env:VIBE_AGENTS_HOME
$summary = $null

New-Item -ItemType Directory -Path $hostSkillsRoot -Force | Out-Null
Copy-Item `
    -LiteralPath (Join-Path $repoRoot 'bundled\skills\systematic-debugging') `
    -Destination (Join-Path $hostSkillsRoot 'systematic-debugging') `
    -Recurse `
    -Force

$hostDecisionJson = @{
    agent_skill_organization = [ordered]@{
        schema_version = 'agent_skill_organization_v1'
        derived_by = 'agent'
        workflow_level = 'L'
        modules = @(
            [ordered]@{
                module_id = 'debug_investigation'
                goal = 'Investigate the failing test and stack trace.'
                candidate_skill_ids = @('systematic-debugging')
                execution_mode = 'skill_assigned'
                acceptance_criteria = @(
                    [ordered]@{
                        criterion_id = 'debug-investigation-result'
                        description = 'The debugging investigation satisfies the approved module goal.'
                        verification_mode = 'automated'
                    }
                )
            }
        )
        selected_skills = @(
            [ordered]@{
                skill_id = 'systematic-debugging'
                module_ids = @('debug_investigation')
                responsibility = 'Own the approved debugging module.'
                reason = 'The Agent selected this Skill after reading its SKILL.md.'
            }
        )
        uncovered_modules = @()
        workflow_level_contract = [ordered]@{
            L = 'Use one serial governed lane.'
            XL = 'Use bounded waves for dependency-ready, non-conflicting work.'
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

try {
    $env:VIBE_AGENTS_HOME = $hostRoot
    $summary = & $runtimeEntryPath `
        -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' `
        -Mode interactive_governed `
        -RunId $runId `
        -ArtifactRoot $artifactRoot `
        -HostDecisionJson $hostDecisionJson
}
finally {
    $env:VIBE_AGENTS_HOME = $originalAgentsHome
}

$runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet
$moduleWorkPlanPath = [string]$summary.summary.artifacts.module_work_plan
$agentExecutionHandoffPath = [string]$summary.summary.artifacts.agent_execution_handoff
$executeReceiptPath = [string]$summary.summary.artifacts.execute_receipt
$executionManifestPath = [string]$summary.summary.artifacts.execution_manifest
$hostUserBriefingPath = [string]$summary.summary.artifacts.host_user_briefing

foreach ($path in @($runtimeInputPacketPath, $moduleWorkPlanPath, $agentExecutionHandoffPath, $executeReceiptPath, $executionManifestPath, $hostUserBriefingPath)) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $path) -Message ("handoff proof artifact exists: {0}" -f ([System.IO.Path]::GetFileName($path))) -Details $path
}

$runtimeInputPacket = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
$moduleWorkPlan = Get-Content -LiteralPath $moduleWorkPlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$agentExecutionHandoff = Get-Content -LiteralPath $agentExecutionHandoffPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executeReceipt = Get-Content -LiteralPath $executeReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$hostUserBriefing = Get-Content -LiteralPath $hostUserBriefingPath -Raw -Encoding UTF8

$boundSkillIds = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $runtimeInputPacket | Sort-Object -Unique)
$plannedUnitIds = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
$handoffUnitIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
$handoffSkillIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
$missingEntrypoints = @($agentExecutionHandoff.units | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.skill_entrypoint) -or -not (Test-Path -LiteralPath ([string]$_.skill_entrypoint) -PathType Leaf) })
$moduleExecutionPath = [string]$agentExecutionHandoff.module_execution_path
$resultContract = $agentExecutionHandoff.result_contract
$submissionTemplate = $resultContract.submission_template
$actualModuleWorkPlanDigest = (Get-FileHash -LiteralPath $moduleWorkPlanPath -Algorithm SHA256).Hash.ToLowerInvariant()
$resultContractUnitIds = @($resultContract.units | ForEach-Object { [string]$_.unit_id })
$plannedUnitBindings = @($moduleWorkPlan.work_units | Select-Object unit_id, module_id, skill_id, role)
$handoffUnitBindings = @($agentExecutionHandoff.units | Select-Object unit_id, module_id, skill_id, role)
$resultContractUnitBindings = @($resultContract.units | Select-Object unit_id, module_id, skill_id, role)
$submissionTemplateUnitBindings = @($submissionTemplate.units | Select-Object unit_id, module_id, skill_id, role)
$plannedUnitBindingsJson = ConvertTo-Json -InputObject $plannedUnitBindings -Depth 10 -Compress
$handoffUnitBindingsJson = ConvertTo-Json -InputObject $handoffUnitBindings -Depth 10 -Compress
$resultContractUnitBindingsJson = ConvertTo-Json -InputObject $resultContractUnitBindings -Depth 10 -Compress
$submissionTemplateUnitBindingsJson = ConvertTo-Json -InputObject $submissionTemplateUnitBindings -Depth 10 -Compress
$plannedModules = @($moduleWorkPlan.modules | Select-Object module_id, required, execution_mode, gap_reason, acceptance_criteria)
$resultContractModules = @($resultContract.modules | Select-Object module_id, required, execution_mode, gap_reason, acceptance_criteria)
$submissionTemplateModules = @($submissionTemplate.modules | Select-Object module_id, required, execution_mode, gap_reason)
$plannedModulesJson = ConvertTo-Json -InputObject $plannedModules -Depth 20 -Compress
$resultContractModulesJson = ConvertTo-Json -InputObject $resultContractModules -Depth 20 -Compress
$submissionTemplateModulesJson = ConvertTo-Json -InputObject $submissionTemplateModules -Depth 20 -Compress
$plannedModuleBindingsJson = ConvertTo-Json -InputObject @($moduleWorkPlan.modules | Select-Object module_id, required, execution_mode, gap_reason) -Depth 10 -Compress

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'handoff proof summary runs in interactive_governed mode'
Add-Assertion -Results ([ref]$results) -Condition ($summary.summary.terminal_stage -eq 'plan_execute') -Message 'handoff proof stops at plan_execute for Agent action'
Add-Assertion -Results ([ref]$results) -Condition ($null -eq $summary.summary.artifacts.cleanup_receipt) -Message 'handoff proof does not enter phase cleanup early'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-logs'))) -Message 'handoff proof creates no kernel execution logs'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-results'))) -Message 'handoff proof creates no kernel execution results'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-proof'))) -Message 'handoff proof creates no kernel execution proof directory'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.stage -eq 'runtime_input_freeze') -Message 'runtime input packet is frozen before Agent work'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'runtime input packet keeps vibe as runtime authority'
Add-Assertion -Results ([ref]$results) -Condition (($boundSkillIds -join '|') -ceq ($handoffSkillIds -join '|')) -Message 'Agent handoff preserves the approved module Skill organization'
Add-Assertion -Results ([ref]$results) -Condition ($moduleWorkPlan.schema_version -eq 'module_work_plan_v1') -Message 'module-work-plan.json is the approved work authority'
Add-Assertion -Results ([ref]$results) -Condition (($plannedUnitIds -join '|') -ceq ($handoffUnitIds -join '|')) -Message 'agent-execution-handoff.json follows every approved work unit'
Add-Assertion -Results ([ref]$results) -Condition ($agentExecutionHandoff.status -eq 'agent_action_required' -and $agentExecutionHandoff.control_owner -eq 'agent') -Message 'Agent execution handoff transfers control to the current Agent'
Add-Assertion -Results ([ref]$results) -Condition ($missingEntrypoints.Count -eq 0) -Message 'every assigned Skill handoff names an existing SKILL.md'
Add-Assertion -Results ([ref]$results) -Condition ([System.IO.Path]::GetFileName($moduleExecutionPath) -eq 'module-execution.json') -Message 'handoff names module-execution.json as the Agent result'
Add-Assertion -Results ([ref]$results) -Condition ($resultContract.schema_version -ceq 'module_execution_v1') -Message 'result_contract freezes the module_execution_v1 submission schema'
Add-Assertion -Results ([ref]$results) -Condition (
    $resultContract.source_run_id -ceq $runId -and
    $resultContract.source_run_id -ceq [string]$moduleWorkPlan.source_run_id -and
    $resultContract.source_run_id -ceq [string]$agentExecutionHandoff.source_run_id
) -Message 'result_contract binds the source run'
Add-Assertion -Results ([ref]$results) -Condition ($resultContract.module_work_plan_digest -ceq $actualModuleWorkPlanDigest) -Message 'result_contract binds the actual module-work-plan.json SHA256 digest'
Add-Assertion -Results ([ref]$results) -Condition ((@($resultContract.terminal_states) -join '|') -ceq 'completed|failed|blocked') -Message 'result_contract allows terminal results only'
Add-Assertion -Results ([ref]$results) -Condition ((@($resultContract.criterion_terminal_states) -join '|') -ceq 'passing|failing|blocked') -Message 'result_contract defines exact criterion terminal states'
Add-Assertion -Results ([ref]$results) -Condition ((@($resultContract.criterion_result_required_fields) -join '|') -ceq 'criterion_id|state') -Message 'result_contract defines criterion result fields'
Add-Assertion -Results ([ref]$results) -Condition (
    $resultContract.PSObject.Properties.Name -contains 'tdd_evidence' -and
    @($resultContract.tdd_evidence.required_code_task_tdd_evidence_requirements).Count -gt 0 -and
    (@($resultContract.tdd_evidence.terminal_states) -join '|') -ceq 'passing|failing|blocked'
) -Message 'code-task result_contract freezes inline TDD evidence requirements'
Add-Assertion -Results ([ref]$results) -Condition (
    $submissionTemplate.schema_version -ceq 'module_execution_v1' -and
    $submissionTemplate.source_run_id -ceq $runId -and
    $submissionTemplate.module_work_plan_digest -ceq $actualModuleWorkPlanDigest
) -Message 'result_contract submission_template is bound to the same run and plan'
Add-Assertion -Results ([ref]$results) -Condition (
    ($resultContractUnitIds -join '|') -ceq ($plannedUnitIds -join '|') -and
    ($resultContractUnitIds -join '|') -ceq ($handoffUnitIds -join '|')
) -Message 'result_contract unit ids match the plan and handoff'
Add-Assertion -Results ([ref]$results) -Condition (
    $resultContractUnitBindingsJson -ceq $plannedUnitBindingsJson -and
    $resultContractUnitBindingsJson -ceq $handoffUnitBindingsJson -and
    $submissionTemplateUnitBindingsJson -ceq $plannedUnitBindingsJson
) -Message 'result_contract preserves every unit role, module, and Skill binding'
Add-Assertion -Results ([ref]$results) -Condition ($resultContractModulesJson -ceq $plannedModulesJson) -Message 'result_contract modules match the approved plan'
Add-Assertion -Results ([ref]$results) -Condition ($submissionTemplateModulesJson -ceq $plannedModuleBindingsJson) -Message 'submission_template preserves every module binding'
Add-Assertion -Results ([ref]$results) -Condition (
    @($resultContract.units | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0 -and
    @($resultContract.modules | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0
) -Message 'result_contract contains no prewritten execution results'
Add-Assertion -Results ([ref]$results) -Condition (
    @($submissionTemplate.units | Where-Object { $null -ne $_.state }).Count -eq 0 -and
    @($submissionTemplate.modules | Where-Object { $null -ne $_.state }).Count -eq 0 -and
    @($submissionTemplate.modules | ForEach-Object { @($_.criterion_results) } | Where-Object { $null -ne $_.state }).Count -eq 0 -and
    $null -eq $submissionTemplate.tdd_evidence.state
) -Message 'submission_template contains fillable placeholders, not prewritten results'
Add-Assertion -Results ([ref]$results) -Condition ($hostUserBriefing.Contains('Use `result_contract` from `agent-execution-handoff.json`')) -Message 'user briefing points the Agent to result_contract'
Add-Assertion -Results ([ref]$results) -Condition (
    $hostUserBriefing.Contains('same `module-execution.json`') -and
    $hostUserBriefing.Contains('do not create a separate `tdd-evidence.json`')
) -Message 'user briefing keeps code-task TDD evidence in module-execution.json'
Add-Assertion -Results ([ref]$results) -Condition ($null -eq $summary.summary.artifacts.module_execution) -Message 'plan_execute does not publish Agent module results before re-entry'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath $moduleExecutionPath)) -Message 'plan_execute leaves module-execution.json for the Agent to write'
Add-Assertion -Results ([ref]$results) -Condition (
    @($agentExecutionHandoff.units | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0
) -Message 'Agent handoff contains work instructions, not prewritten result states'
Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -eq 'agent_action_required') -Message 'execute receipt records Agent action required'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'agent_action_required') -Message 'execution manifest records Agent action required'
Add-Assertion -Results ([ref]$results) -Condition (-not ($executionManifest.PSObject.Properties.Name -contains 'plan_shadow')) -Message 'execution manifest omits retired plan shadow'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.module_handoff.status -eq 'agent_action_required' -and $executionManifest.module_handoff.control_owner -eq 'agent') -Message 'module_handoff records Agent control'
Add-Assertion -Results ([ref]$results) -Condition (($executionManifest.module_handoff.assigned_skill_ids -join '|') -ceq ($handoffSkillIds -join '|')) -Message 'module_handoff matches agent-execution-handoff.json'

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    runtime_summary_path = $summary.summary_path
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-runtime-execution-proof'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-runtime-execution-proof-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-runtime-execution-proof-gate failed with $failureCount failing assertion(s)."
}

$report
