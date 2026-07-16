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
        [System.Collections.Generic.List[object]]$Assertions,
        [bool]$Pass,
        [string]$Message,
        [object]$Details = $null
    )

    $Assertions.Add([pscustomobject]@{
        pass = [bool]$Pass
        message = $Message
        details = $Details
    }) | Out-Null

    Write-Host ("[{0}] {1}" -f $(if ($Pass) { 'PASS' } else { 'FAIL' }), $Message) -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
}

function Invoke-SupportedHostRuntimeTruthProbe {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RuntimeEntrypointPath,
        [Parameter(Mandatory)] [string]$HostId,
        [Parameter(Mandatory)] [System.Collections.Generic.List[object]]$Assertions
    )

    $runId = "no-silent-fallback-$HostId-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $artifactRoot = Join-Path $RepoRoot (".tmp\vibe-no-silent-fallback-{0}" -f $runId)
    $previousHostId = $env:VCO_HOST_ID

    try {
        $env:VCO_HOST_ID = $HostId

        $hostDecisionJson = @{
            agent_skill_organization = [ordered]@{
                schema_version = 'agent_skill_organization_v1'
                derived_by = 'agent'
                workflow_level = 'L'
                modules = @(
                    [ordered]@{
                        module_id = 'host_contract_probe'
                        goal = 'Verify the supported host handoff contract.'
                        candidate_skill_ids = @()
                        execution_mode = 'blocked_gap'
                        acceptance_criteria = @(
                            [ordered]@{
                                criterion_id = 'host-contract-result'
                                description = 'The supported host handoff contract is verified.'
                                verification_mode = 'automated'
                            }
                        )
                    }
                )
                selected_skills = @()
                uncovered_modules = @(
                    [ordered]@{
                        module_id = 'host_contract_probe'
                        reason = 'This structural gate does not need a task Skill.'
                    }
                )
                workflow_level_contract = [ordered]@{
                    L = 'Use one serial governed lane.'
                    XL = 'Use bounded waves for dependency-ready, non-conflicting work.'
                }
            }
        } | ConvertTo-Json -Depth 20 -Compress

        $summary = & $RuntimeEntrypointPath `
            -Task "Verify canonical vibe proof-chain truth for host $HostId. `$vibe" `
            -Mode interactive_governed `
            -RunId $runId `
            -ArtifactRoot $artifactRoot `
            -HostDecisionJson $hostDecisionJson

        $summaryBody = if ($summary -and $summary.PSObject.Properties.Name -contains 'summary') { $summary.summary } else { $null }
        $summaryArtifacts = if ($summaryBody -and $summaryBody.PSObject.Properties.Name -contains 'artifacts') { $summaryBody.artifacts } else { $null }
        $runtimeInputPacketPath = if ($summaryArtifacts -and $summaryArtifacts.PSObject.Properties.Name -contains 'runtime_input_packet') { [string]$summaryArtifacts.runtime_input_packet } else { '' }
        $moduleWorkPlanPath = if ($summaryArtifacts -and $summaryArtifacts.PSObject.Properties.Name -contains 'module_work_plan') { [string]$summaryArtifacts.module_work_plan } else { '' }
        $agentExecutionHandoffPath = if ($summaryArtifacts -and $summaryArtifacts.PSObject.Properties.Name -contains 'agent_execution_handoff') { [string]$summaryArtifacts.agent_execution_handoff } else { '' }
        $executionManifestPath = if ($summaryArtifacts -and $summaryArtifacts.PSObject.Properties.Name -contains 'execution_manifest') { [string]$summaryArtifacts.execution_manifest } else { '' }
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $runtimeInputPacketPath) -Message "$HostId runtime emits runtime-input-packet artifact" -Details $runtimeInputPacketPath
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $moduleWorkPlanPath) -Message "$HostId runtime emits module-work-plan artifact" -Details $moduleWorkPlanPath
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $agentExecutionHandoffPath) -Message "$HostId runtime emits agent-execution-handoff artifact" -Details $agentExecutionHandoffPath
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $executionManifestPath) -Message "$HostId runtime emits execution-manifest artifact" -Details $executionManifestPath

        if (
            -not (Test-Path -LiteralPath $runtimeInputPacketPath) -or
            -not (Test-Path -LiteralPath $moduleWorkPlanPath) -or
            -not (Test-Path -LiteralPath $agentExecutionHandoffPath) -or
            -not (Test-Path -LiteralPath $executionManifestPath)
        ) {
            return
        }

        $runtimeInput = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $moduleWorkPlan = Get-Content -LiteralPath $moduleWorkPlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $agentExecutionHandoff = Get-Content -LiteralPath $agentExecutionHandoffPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

        Add-Assertion -Assertions $Assertions -Pass ($runtimeInput.PSObject.Properties.Name -contains 'module_assignments') -Message "$HostId runtime-input-packet contains module_assignments"
        Add-Assertion -Assertions $Assertions -Pass (-not ($runtimeInput.PSObject.Properties.Name -contains 'skill_usage')) -Message "$HostId runtime-input-packet omits retired skill_usage ledger"
        $boundSkillIds = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $runtimeInput)
        $plannedUnitIds = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
        $handoffUnitIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
        $handoffSkillIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
        $sortedBoundSkillIds = @($boundSkillIds | Sort-Object -Unique)
        $moduleExecutionPath = [string]$agentExecutionHandoff.module_execution_path

        Add-Assertion -Assertions $Assertions -Pass ($moduleWorkPlan.schema_version -eq 'module_work_plan_v1') -Message "$HostId module-work-plan is the approved work authority"
        Add-Assertion -Assertions $Assertions -Pass ($agentExecutionHandoff.schema_version -eq 'agent_execution_handoff_v1') -Message "$HostId agent-execution-handoff uses the current contract"
        Add-Assertion -Assertions $Assertions -Pass ($agentExecutionHandoff.status -eq 'agent_action_required') -Message "$HostId handoff requires Agent module work"
        Add-Assertion -Assertions $Assertions -Pass (($plannedUnitIds -join '|') -ceq ($handoffUnitIds -join '|')) -Message "$HostId Agent handoff follows module-work-plan.json"
        Add-Assertion -Assertions $Assertions -Pass (($sortedBoundSkillIds -join '|') -ceq ($handoffSkillIds -join '|')) -Message "$HostId Agent handoff preserves the approved Skill organization"
        Add-Assertion -Assertions $Assertions -Pass ([System.IO.Path]::GetFileName($moduleExecutionPath) -eq 'module-execution.json') -Message "$HostId handoff names module-execution.json as the Agent result"
        Add-Assertion -Assertions $Assertions -Pass ($executionManifest.status -eq 'agent_action_required') -Message "$HostId execution manifest stops for Agent action"
        Add-Assertion -Assertions $Assertions -Pass ($executionManifest.module_handoff.status -eq 'agent_action_required') -Message "$HostId module_handoff records Agent control"
        Add-Assertion -Assertions $Assertions -Pass (($executionManifest.module_handoff.assigned_skill_ids -join '|') -ceq ($handoffSkillIds -join '|')) -Message "$HostId module_handoff matches the Agent execution handoff"
    }
    finally {
        if ([string]::IsNullOrWhiteSpace($previousHostId)) {
            Remove-Item Env:VCO_HOST_ID -ErrorAction SilentlyContinue
        } else {
            $env:VCO_HOST_ID = $previousHostId
        }
        if (-not $WriteArtifacts -and (Test-Path -LiteralPath $artifactRoot)) {
            Remove-Item -LiteralPath $artifactRoot -Recurse -Force
        }
    }
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-no-silent-fallback-contract-gate.json'
    $mdPath = Join-Path $dir 'vibe-no-silent-fallback-contract-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO No Silent Fallback Contract Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failure count: `{0}`' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )

    foreach ($assertion in @($Artifact.assertions)) {
        $lines += ('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$assertions = [System.Collections.Generic.List[object]]::new()

$runtimeContractPath = Join-Path $repoRoot 'config\runtime-contract.json'
$fallbackPolicyPath = Join-Path $repoRoot 'config\fallback-governance.json'
$routerGovernancePath = Join-Path $repoRoot 'config\router-model-governance.json'
$runtimeProtocolPath = Join-Path $repoRoot 'protocols\runtime.md'
$truthGatePath = Join-Path $repoRoot 'scripts\verify\vibe-canonical-entry-truth-gate.ps1'
$routeScriptPath = Join-Path $repoRoot 'scripts\router\resolve-pack-route.ps1'
$runtimeEntrypointPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig

$runtimeContract = Get-Content -LiteralPath $runtimeContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$fallbackPolicy = Get-Content -LiteralPath $fallbackPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$routerGovernance = Get-Content -LiteralPath $routerGovernancePath -Raw -Encoding UTF8 | ConvertFrom-Json
$runtimeProtocol = Get-Content -LiteralPath $runtimeProtocolPath -Raw -Encoding UTF8
$truthGate = Get-Content -LiteralPath $truthGatePath -Raw -Encoding UTF8

Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.no_silent_fallback) -Message 'runtime contract encodes no_silent_fallback'
Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.no_silent_degradation) -Message 'runtime contract encodes no_silent_degradation'
Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.fallback_hazard_alert_required) -Message 'runtime contract requires fallback hazard alert'
Add-Assertion -Assertions $assertions -Pass (-not [bool]$fallbackPolicy.silent_fallback) -Message 'fallback policy forbids silent fallback'
Add-Assertion -Assertions $assertions -Pass (-not [bool]$fallbackPolicy.silent_degradation) -Message 'fallback policy forbids silent degradation'
Add-Assertion -Assertions $assertions -Pass ([bool]$fallbackPolicy.require_hazard_alert) -Message 'fallback policy requires hazard alert'
Add-Assertion -Assertions $assertions -Pass ([string]$routerGovernance.provider_neutral_contract.degrade_honesty.fallback_truth_level -eq 'non_authoritative') -Message 'router governance maps degraded fallback truth to non_authoritative'
Add-Assertion -Assertions $assertions -Pass ([bool]$routerGovernance.hard_rules.must_emit_hazard_alert_for_fallback) -Message 'router governance requires fallback hazard alert'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('Silent fallback and silent degradation are forbidden.')) -Message 'runtime protocol documents no silent fallback'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('module_assignments')) -Message 'runtime protocol requires module_assignments evidence'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('module-work-plan.json')) -Message 'runtime protocol names the approved module work plan'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('agent-execution-handoff.json')) -Message 'runtime protocol requires the Agent execution handoff'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('module-execution.json')) -Message 'runtime protocol requires the Agent module result on re-entry'
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $truthGatePath) -Message 'canonical truth gate script exists' -Details $truthGatePath
Add-Assertion -Assertions $assertions -Pass ($truthGate.Contains('host-launch-receipt.json')) -Message 'canonical truth gate requires host-launch-receipt.json'
Add-Assertion -Assertions $assertions -Pass ($truthGate.Contains('reading SKILL.md alone is not canonical vibe entry')) -Message 'canonical truth gate rejects SKILL.md-only activation claims'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry.')) -Message 'runtime protocol documents that prose-only activation is not proof of canonical vibe entry'

$route = & $routeScriptPath -Prompt 'help me with this' -Grade 'M' -TaskType 'research' | ConvertFrom-Json
$lowSignalHasNoCandidate = (
    [string]$route.router_contract_mode -eq 'candidate_discovery_only' -and
    [string]$route.candidate_source -eq 'local_skill_index' -and
    [string]$route.route_mode -eq 'no_local_candidate' -and
    [string]$route.route_reason -eq 'no_local_candidate_above_threshold' -and
    -not [bool]$route.fallback_applied -and
    -not [bool]$route.fallback_active -and
    -not [bool]$route.hazard_alert_required -and
    [string]$route.truth_level -eq 'local_index_no_match' -and
    [string]$route.degradation_state -eq 'no_local_candidate' -and
    -not [bool]$route.non_authoritative -and
    $null -eq $route.hazard_alert
)
Add-Assertion -Assertions $assertions -Pass $lowSignalHasNoCandidate -Message 'low-signal route reports no local candidate without selecting or executing a fallback'

foreach ($hostId in @('codex', 'claude-code', 'opencode')) {
    Invoke-SupportedHostRuntimeTruthProbe -RepoRoot $repoRoot -RuntimeEntrypointPath $runtimeEntrypointPath -HostId $hostId -Assertions $assertions
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$artifact = [pscustomobject]@{
    gate = 'vibe-no-silent-fallback-contract-gate'
    repo_root = $repoRoot
    gate_result = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [pscustomobject]@{
        failure_count = $failureCount
        route_mode = if ($route) { [string]$route.route_mode } else { '' }
        route_reason = if ($route) { [string]$route.route_reason } else { '' }
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
