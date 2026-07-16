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
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$results = @()

$requiredFiles = @(
    'SKILL.md',
    'protocols/runtime.md',
    'protocols/think.md',
    'protocols/do.md',
    'protocols/team.md',
    'protocols/retro.md',
    'config/runtime-contract.json',
    'config/runtime-modes.json',
    'config/fallback-governance.json',
    'config/implementation-guardrails.json',
    'config/runtime-input-packet-policy.json',
    'config/requirement-doc-policy.json',
    'config/plan-execution-policy.json',
    'config/phase-cleanup-policy.json',
    'docs/requirements/README.md',
    'templates/requirements/governed-requirement-template.md',
    'templates/plans/governed-execution-plan-template.md',
    'scripts/runtime/VibeRuntime.Common.ps1',
    'scripts/runtime/Invoke-SkeletonCheck.ps1',
    'scripts/runtime/Invoke-DeepInterview.ps1',
    'scripts/runtime/Write-RequirementDoc.ps1',
    'scripts/runtime/Write-XlPlan.ps1',
    'scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1',
    'scripts/runtime/Invoke-PlanExecute.ps1',
    'scripts/runtime/Invoke-PhaseCleanup.ps1',
    'scripts/verify/vibe-runtime-execution-proof-gate.ps1',
    'scripts/verify/vibe-module-dispatch-closure-gate.ps1',
    'scripts/verify/vibe-no-silent-fallback-contract-gate.ps1',
    'scripts/verify/vibe-no-self-introduced-fallback-gate.ps1',
    'scripts/verify/vibe-release-truth-consistency-gate.ps1'
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $relativePath
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $fullPath) -Message ("required governed runtime file exists: {0}" -f $relativePath) -Details $fullPath
}
Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $runtimeEntryPath) -Message 'effective governed runtime entrypoint exists' -Details $runtimeEntryPath

$runtimeContract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Assertion -Results ([ref]$results) -Condition ($runtimeContract.entry_skill -eq 'vibe') -Message 'runtime contract entry skill is vibe'
Add-Assertion -Results ([ref]$results) -Condition (@($runtimeContract.stages).Count -eq 6) -Message 'runtime contract defines six fixed stages'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.no_silent_fallback) -Message 'runtime contract forbids silent fallback'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.fallback_hazard_alert_required) -Message 'runtime contract requires fallback hazard alerts'
Add-Assertion -Results ([ref]$results) -Condition ([bool]$runtimeContract.invariants.no_self_introduced_fallback_without_requirement_approval) -Message 'runtime contract forbids self-introduced fallback without requirement approval'

$skillText = Get-Content -LiteralPath (Join-Path $repoRoot 'SKILL.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition (
    $skillText.Contains('skeleton_check') -and
    $skillText.Contains('deep_interview') -and
    $skillText.Contains('requirement_doc') -and
    $skillText.Contains('xl_plan') -and
    $skillText.Contains('plan_execute') -and
    $skillText.Contains('phase_cleanup')
) -Message 'SKILL.md documents the fixed stage machine'
Add-Assertion -Results ([ref]$results) -Condition ($skillText.Contains('governance-capsule.json')) -Message 'SKILL.md documents governance capsule artifact'
Add-Assertion -Results ([ref]$results) -Condition ($skillText.Contains('stage-lineage.json')) -Message 'SKILL.md documents stage-lineage artifact'
Add-Assertion -Results ([ref]$results) -Condition (
    $skillText.Contains('agent-execution-handoff.json.result_contract') -and
    $skillText.Contains('not execution evidence') -and
    $skillText.Contains('creates `module-execution.json`')
) -Message 'SKILL.md keeps the result contract separate from Agent execution evidence'

$teamText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\team.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($teamText.Contains('$vibe')) -Message 'team protocol requires subagent prompts to end with $vibe'
$runtimeText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\runtime.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($runtimeText.Contains('governance-capsule.json')) -Message 'runtime protocol documents governance capsule artifact'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeText.Contains('delegation-envelope.json')) -Message 'runtime protocol documents delegation envelope artifact'
Add-Assertion -Results ([ref]$results) -Condition (
    $runtimeText.Contains('agent-execution-handoff.json.result_contract') -and
    $runtimeText.Contains('not execution evidence') -and
    $runtimeText.Contains('writes the complete result to `module-execution.json`')
) -Message 'runtime protocol keeps the result contract separate from Agent execution evidence'

$runId = "contract-gate-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\governed-runtime-contract-{0}" -f $runId)
$hostRoot = Join-Path $artifactRoot '.agents'
$hostSkillsRoot = Join-Path $hostRoot 'skills'
$originalAgentsHome = $env:VIBE_AGENTS_HOME

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
            XL = 'Use bounded waves when the approved organization needs them.'
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

try {
    $env:VIBE_AGENTS_HOME = $hostRoot
    $summary = & $runtimeEntryPath -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' -Mode interactive_governed -RunId $runId -ArtifactRoot $artifactRoot -HostDecisionJson $hostDecisionJson
}
finally {
    $env:VIBE_AGENTS_HOME = $originalAgentsHome
}

Add-Assertion -Results ([ref]$results) -Condition ($summary.mode -eq 'interactive_governed') -Message 'runtime smoke summary keeps interactive_governed as the effective mode'

$artifactPaths = @(
    $summary.summary.artifacts.skeleton_receipt,
    $summary.summary.artifacts.intent_contract,
    $summary.summary.artifacts.governance_capsule,
    $summary.summary.artifacts.stage_lineage,
    $summary.summary.artifacts.requirement_doc,
    $summary.summary.artifacts.execution_plan,
    $summary.summary.artifacts.module_work_plan,
    $summary.summary.artifacts.agent_execution_handoff,
    $summary.summary.artifacts.execute_receipt,
    $summary.summary.artifacts.execution_manifest,
    $summary.summary.artifacts.host_user_briefing
)

foreach ($artifactPath in $artifactPaths) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $artifactPath) -Message ("runtime smoke artifact exists: {0}" -f ([System.IO.Path]::GetFileName($artifactPath))) -Details $artifactPath
}

$executeReceipt = Get-Content -LiteralPath $summary.summary.artifacts.execute_receipt -Raw -Encoding UTF8 | ConvertFrom-Json
$executionManifest = Get-Content -LiteralPath $summary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$moduleWorkPlan = Get-Content -LiteralPath $summary.summary.artifacts.module_work_plan -Raw -Encoding UTF8 | ConvertFrom-Json
$agentExecutionHandoff = Get-Content -LiteralPath $summary.summary.artifacts.agent_execution_handoff -Raw -Encoding UTF8 | ConvertFrom-Json
$runtimeInputPacket = Get-Content -LiteralPath $summary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
$governanceCapsule = Get-Content -LiteralPath $summary.summary.artifacts.governance_capsule -Raw -Encoding UTF8 | ConvertFrom-Json
$stageLineage = Get-Content -LiteralPath $summary.summary.artifacts.stage_lineage -Raw -Encoding UTF8 | ConvertFrom-Json
$generatedRequirement = Get-Content -LiteralPath $summary.summary.artifacts.requirement_doc -Raw -Encoding UTF8
$generatedPlan = Get-Content -LiteralPath $summary.summary.artifacts.execution_plan -Raw -Encoding UTF8
$hostUserBriefing = Get-Content -LiteralPath $summary.summary.artifacts.host_user_briefing -Raw -Encoding UTF8
$resultContract = $agentExecutionHandoff.result_contract
$actualModuleWorkPlanDigest = (Get-FileHash -LiteralPath $summary.summary.artifacts.module_work_plan -Algorithm SHA256).Hash.ToLowerInvariant()
$plannedUnitIds = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
$handoffUnitIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
$resultContractUnitIds = @($resultContract.units | ForEach-Object { [string]$_.unit_id })
$plannedUnitBindings = @($moduleWorkPlan.work_units | Select-Object unit_id, module_id, skill_id, role)
$handoffUnitBindings = @($agentExecutionHandoff.units | Select-Object unit_id, module_id, skill_id, role)
$resultContractUnitBindings = @($resultContract.units | Select-Object unit_id, module_id, skill_id, role)
$plannedUnitBindingsJson = ConvertTo-Json -InputObject $plannedUnitBindings -Depth 10 -Compress
$handoffUnitBindingsJson = ConvertTo-Json -InputObject $handoffUnitBindings -Depth 10 -Compress
$resultContractUnitBindingsJson = ConvertTo-Json -InputObject $resultContractUnitBindings -Depth 10 -Compress
$plannedModules = @($moduleWorkPlan.modules | Select-Object module_id, required, execution_mode, gap_reason, acceptance_criteria)
$resultContractModules = @($resultContract.modules | Select-Object module_id, required, execution_mode, gap_reason, acceptance_criteria)
$plannedModulesJson = ConvertTo-Json -InputObject $plannedModules -Depth 20 -Compress
$resultContractModulesJson = ConvertTo-Json -InputObject $resultContractModules -Depth 20 -Compress
$expectedStageIds = @($runtimeContract.stages | ForEach-Object { [string]$_.id })
$expectedHandoffStageIds = @($expectedStageIds | Where-Object { $_ -ne 'phase_cleanup' })

Add-Assertion -Results ([ref]$results) -Condition ($governanceCapsule.runtime_selected_skill -eq 'vibe') -Message 'runtime smoke governance capsule keeps vibe authority'
Add-Assertion -Results ([ref]$results) -Condition ((
    @($stageLineage.stages | ForEach-Object { [string]$_.stage_name }) -join '|'
) -eq ($expectedHandoffStageIds -join '|')) -Message 'runtime smoke stage-lineage stops at Agent execution handoff'
Add-Assertion -Results ([ref]$results) -Condition ($summary.summary.terminal_stage -eq 'plan_execute') -Message 'runtime smoke stops before phase cleanup'
Add-Assertion -Results ([ref]$results) -Condition ($null -eq $summary.summary.artifacts.cleanup_receipt) -Message 'runtime smoke omits cleanup receipt before Agent module execution'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-logs'))) -Message 'runtime smoke does not create kernel execution logs before Agent work'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-results'))) -Message 'runtime smoke does not create kernel execution results before Agent work'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath (Join-Path $summary.summary.session_root 'execution-proof'))) -Message 'runtime smoke does not create kernel execution proof directories before Agent work'
Add-Assertion -Results ([ref]$results) -Condition ($executeReceipt.status -eq 'agent_action_required') -Message 'runtime smoke execute receipt requires Agent action'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'agent_action_required') -Message 'runtime smoke execution manifest requires Agent action' -Details $executionManifest.status
Add-Assertion -Results ([ref]$results) -Condition (-not ($executionManifest.PSObject.Properties.Name -contains 'plan_shadow')) -Message 'runtime smoke execution manifest omits retired plan shadow'
Add-Assertion -Results ([ref]$results) -Condition ($agentExecutionHandoff.schema_version -eq 'agent_execution_handoff_v1') -Message 'runtime smoke emits the Agent execution handoff contract'
Add-Assertion -Results ([ref]$results) -Condition ($agentExecutionHandoff.status -eq 'agent_action_required' -and $agentExecutionHandoff.control_owner -eq 'agent') -Message 'runtime smoke gives skill execution control to the Agent'
Add-Assertion -Results ([ref]$results) -Condition ($agentExecutionHandoff.module_execution_path -eq (Join-Path $artifactRoot "outputs\runtime\vibe-sessions\$runId\module-execution.json")) -Message 'runtime smoke binds the Agent result path in the handoff contract'
Add-Assertion -Results ([ref]$results) -Condition ($resultContract.schema_version -ceq 'module_execution_v1') -Message 'runtime smoke result_contract freezes the module_execution_v1 submission schema'
Add-Assertion -Results ([ref]$results) -Condition (
    $resultContract.source_run_id -ceq $runId -and
    $resultContract.source_run_id -ceq [string]$moduleWorkPlan.source_run_id -and
    $resultContract.source_run_id -ceq [string]$agentExecutionHandoff.source_run_id
) -Message 'runtime smoke result_contract binds the source run'
Add-Assertion -Results ([ref]$results) -Condition ($resultContract.module_work_plan_digest -ceq $actualModuleWorkPlanDigest) -Message 'runtime smoke result_contract binds the actual module-work-plan.json SHA256 digest'
Add-Assertion -Results ([ref]$results) -Condition ((@($resultContract.terminal_states) -join '|') -ceq 'completed|failed|blocked') -Message 'runtime smoke result_contract allows terminal results only'
Add-Assertion -Results ([ref]$results) -Condition (
    ($resultContractUnitIds -join '|') -ceq ($plannedUnitIds -join '|') -and
    ($resultContractUnitIds -join '|') -ceq ($handoffUnitIds -join '|')
) -Message 'runtime smoke result_contract unit ids match the plan and handoff'
Add-Assertion -Results ([ref]$results) -Condition (
    $resultContractUnitBindingsJson -ceq $plannedUnitBindingsJson -and
    $resultContractUnitBindingsJson -ceq $handoffUnitBindingsJson
) -Message 'runtime smoke result_contract preserves every unit role, module, and Skill binding'
Add-Assertion -Results ([ref]$results) -Condition ($resultContractModulesJson -ceq $plannedModulesJson) -Message 'runtime smoke result_contract modules match the approved plan'
Add-Assertion -Results ([ref]$results) -Condition (
    @($resultContract.units | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0 -and
    @($resultContract.modules | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0
) -Message 'runtime smoke result_contract contains no prewritten execution results'
Add-Assertion -Results ([ref]$results) -Condition ($hostUserBriefing.Contains('Use `result_contract` from `agent-execution-handoff.json`')) -Message 'runtime smoke user briefing points the Agent to result_contract'
Add-Assertion -Results ([ref]$results) -Condition ($null -eq $summary.summary.artifacts.module_execution) -Message 'runtime smoke does not publish Agent module results before re-entry'
Add-Assertion -Results ([ref]$results) -Condition (-not (Test-Path -LiteralPath $agentExecutionHandoff.module_execution_path)) -Message 'runtime smoke leaves module-execution.json for the Agent to write'
Add-Assertion -Results ([ref]$results) -Condition (
    @($agentExecutionHandoff.units | Where-Object { $_.PSObject.Properties.Name -contains 'state' }).Count -eq 0
) -Message 'runtime smoke handoff contains work instructions, not prewritten result states'
Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.module_handoff.status -eq 'agent_action_required' -and $executionManifest.module_handoff.control_owner -eq 'agent') -Message 'runtime smoke module_handoff records Agent control'
Add-Assertion -Results ([ref]$results) -Condition ([int]$executionManifest.module_handoff.module_work_unit_count -eq @($moduleWorkPlan.work_units).Count) -Message 'runtime smoke module_handoff covers every approved work unit'
Add-Assertion -Results ([ref]$results) -Condition ($generatedRequirement.Contains('## Skill Search Guide')) -Message 'runtime smoke requirement doc includes Agent skill-search guidance'
Add-Assertion -Results ([ref]$results) -Condition (-not $generatedRequirement.Contains('## Skill Execution Decision')) -Message 'runtime smoke requirement doc does not expose preselected skill truth'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Task Modules')) -Message 'runtime smoke execution plan includes Agent task modules'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Candidate Skills By Module')) -Message 'runtime smoke execution plan includes module candidate audit'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Module Work Plan')) -Message 'runtime smoke execution plan includes the approved module work plan'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## Uncovered Modules')) -Message 'runtime smoke execution plan discloses uncovered modules'
Add-Assertion -Results ([ref]$results) -Condition ($generatedPlan.Contains('## L / XL Organization Difference')) -Message 'runtime smoke execution plan explains L and XL organization'

$agentOrganization = $runtimeInputPacket.agent_skill_organization
$agentSelectedSkillIds = @($agentOrganization.selected_skills | ForEach-Object { [string]$_.skill_id } | Sort-Object -Unique)
$boundSkillIds = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $runtimeInputPacket | Sort-Object -Unique)
$handedOffSkillIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.skill_id } | Sort-Object -Unique)

Add-Assertion -Results ([ref]$results) -Condition ($agentOrganization.schema_version -eq 'agent_skill_organization_v1') -Message 'runtime smoke packet carries Agent-confirmed skill organization'
Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.module_assignments.source -eq 'agent_skill_organization') -Message 'runtime smoke module_assignments projects Agent skill organization'
Add-Assertion -Results ([ref]$results) -Condition (($boundSkillIds -join '|') -eq ($agentSelectedSkillIds -join '|')) -Message 'runtime smoke module_assignments matches Agent-selected skills'
Add-Assertion -Results ([ref]$results) -Condition ($moduleWorkPlan.schema_version -eq 'module_work_plan_v1') -Message 'runtime smoke uses the approved module work plan as execution authority'
Add-Assertion -Results ([ref]$results) -Condition (($handedOffSkillIds -join '|') -eq ($agentSelectedSkillIds -join '|')) -Message 'runtime smoke hands off only Agent-selected skills'
Add-Assertion -Results ([ref]$results) -Condition (($executionManifest.module_handoff.assigned_skill_ids -join '|') -eq ($handedOffSkillIds -join '|')) -Message 'runtime smoke module_handoff matches agent-execution-handoff.json'
Add-Assertion -Results ([ref]$results) -Condition (@($agentOrganization.uncovered_modules).Count -eq 0 -and @($agentOrganization.selected_skills).Count -eq 1) -Message 'runtime smoke preserves the Agent-selected module owner'
Add-Assertion -Results ([ref]$results) -Condition ([string]$runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'runtime smoke keeps vibe as explicit runtime skill'

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
        Join-Path $repoRoot 'outputs\verify\vibe-governed-runtime-contract'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-governed-runtime-contract-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-governed-runtime-contract-gate failed with $failureCount failing assertion(s)."
}

$report
