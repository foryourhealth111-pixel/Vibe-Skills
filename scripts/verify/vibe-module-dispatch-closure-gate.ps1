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

    $Results.Value += [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        if ($Details) {
            Write-Host "       $Details" -ForegroundColor DarkRed
        }
    }
}

function Invoke-ClosureScenario {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$ArtifactRoot,
        [AllowNull()] [psobject]$RuntimeConfig = $null,
        [AllowEmptyString()] [string]$GovernanceScope = 'root',
        [AllowEmptyString()] [string]$RootRunId = '',
        [AllowEmptyString()] [string]$ParentRunId = '',
        [AllowEmptyString()] [string]$ParentUnitId = '',
        [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
        [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [string[]]$ApprovedSkillIds = @(),
        [Parameter(Mandatory)] [string]$HostDecisionJson
    )

    $scriptPath = Get-VgoRuntimeEntrypointPath -RepoRoot $RepoRoot -RuntimeConfig $RuntimeConfig
    return & $scriptPath `
        -Task $Task `
        -Mode interactive_governed `
        -RunId $RunId `
        -ArtifactRoot $ArtifactRoot `
        -GovernanceScope $GovernanceScope `
        -RootRunId $RootRunId `
        -ParentRunId $ParentRunId `
        -ParentUnitId $ParentUnitId `
        -InheritedRequirementDocPath $InheritedRequirementDocPath `
        -InheritedExecutionPlanPath $InheritedExecutionPlanPath `
        -DelegationEnvelopePath $DelegationEnvelopePath `
        -ApprovedSpecialistSkillIds $ApprovedSkillIds `
        -HostDecisionJson $HostDecisionJson
}

function New-ModuleHandoffHostDecisionJson {
    param(
        [Parameter(Mandatory)] [string]$SkillId,
        [Parameter(Mandatory)] [string]$ModuleId,
        [Parameter(Mandatory)] [string]$Goal
    )

    return @{
        agent_skill_organization = [ordered]@{
            schema_version = 'agent_skill_organization_v1'
            derived_by = 'agent'
            workflow_level = 'XL'
            modules = @(
                [ordered]@{
                    module_id = $ModuleId
                    goal = $Goal
                    candidate_skill_ids = @($SkillId)
                    execution_mode = 'skill_assigned'
                    acceptance_criteria = @(
                        [ordered]@{
                            criterion_id = ("{0}-result" -f $ModuleId)
                            description = 'The module result is present and verified.'
                            verification_mode = 'automated'
                        }
                    )
                }
            )
            selected_skills = @(
                [ordered]@{
                    skill_id = $SkillId
                    module_ids = @($ModuleId)
                    responsibility = 'Own the approved module work.'
                    reason = 'The Agent selected this local Skill after reading its SKILL.md.'
                }
            )
            uncovered_modules = @()
            workflow_level_contract = [ordered]@{
                L = 'Use one serial governed lane.'
                XL = 'Use bounded waves for dependency-ready, non-conflicting work.'
            }
        }
    } | ConvertTo-Json -Depth 20 -Compress
}

function New-ClosureDelegationEnvelopeForGate {
    param(
        [Parameter(Mandatory)] [object]$RootSummary,
        [Parameter(Mandatory)] [string]$ChildRunId,
        [Parameter(Mandatory)] [string]$ParentUnitId,
        [AllowNull()] [string[]]$ApprovedSkillIds = @()
    )

    $sessionRoot = [string]$RootSummary.summary.session_root
    $childSessionRoot = Join-Path ([System.IO.Path]::GetDirectoryName($sessionRoot)) $ChildRunId
    New-Item -ItemType Directory -Path $childSessionRoot -Force | Out-Null
    $envelopePath = Get-VibeGovernanceArtifactPath -SessionRoot $childSessionRoot -ArtifactName 'delegation_envelope'
    Write-VibeDelegationEnvelope `
        -Path $envelopePath `
        -RootRunId ([string]$RootSummary.summary.run_id) `
        -ParentRunId ([string]$RootSummary.summary.run_id) `
        -ParentUnitId $ParentUnitId `
        -ChildRunId $ChildRunId `
        -RequirementDocPath ([string]$RootSummary.summary.artifacts.requirement_doc) `
        -ExecutionPlanPath ([string]$RootSummary.summary.artifacts.execution_plan) `
        -WriteScope 'gate:module-handoff-closure' `
        -ApprovedSpecialists @($ApprovedSkillIds) `
        -ReviewMode 'module_acceptance' | Out-Null
    return $envelopePath
}

function Get-HandoffClosureState {
    param([Parameter(Mandatory)] [object]$Summary)

    $runtimeInput = Get-Content -LiteralPath $Summary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $moduleWorkPlan = Get-Content -LiteralPath $Summary.summary.artifacts.module_work_plan -Raw -Encoding UTF8 | ConvertFrom-Json
    $agentExecutionHandoff = Get-Content -LiteralPath $Summary.summary.artifacts.agent_execution_handoff -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionManifest = Get-Content -LiteralPath $Summary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

    return [pscustomobject]@{
        runtime_input = $runtimeInput
        module_work_plan = $moduleWorkPlan
        agent_execution_handoff = $agentExecutionHandoff
        execution_manifest = $executionManifest
        bound_skill_ids = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $runtimeInput | Sort-Object -Unique)
        plan_skill_ids = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
        plan_unit_ids = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
        handoff_skill_ids = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
        handoff_unit_ids = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
    }
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$results = @()
$artifactRoot = Join-Path $repoRoot (".tmp\module-handoff-closure-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8))
$originalAgentsHome = $env:VIBE_AGENTS_HOME
$gateHostRoot = Join-Path $artifactRoot '.agents'
$gateSkillsRoot = Join-Path $gateHostRoot 'skills'

New-Item -ItemType Directory -Path $gateSkillsRoot -Force | Out-Null
Copy-Item `
    -LiteralPath (Join-Path $repoRoot 'bundled\skills\systematic-debugging') `
    -Destination (Join-Path $gateSkillsRoot 'systematic-debugging') `
    -Recurse `
    -Force
$env:VIBE_AGENTS_HOME = $gateHostRoot

try {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath (Join-Path $repoRoot 'scripts\runtime\Invoke-PlanExecute.ps1')) -Message 'plan execute script exists'

    $officialHostDecisionJson = New-ModuleHandoffHostDecisionJson `
        -SkillId 'systematic-debugging' `
        -ModuleId 'official_debugging' `
        -Goal 'Investigate the reported failure systematically.'
    $official = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' `
        -RunId ('closure-official-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
        -ArtifactRoot $artifactRoot `
        -RuntimeConfig $context.runtimeConfig `
        -HostDecisionJson $officialHostDecisionJson
    $officialState = Get-HandoffClosureState -Summary $official

    Add-Assertion -Results ([ref]$results) -Condition ($officialState.runtime_input.PSObject.Properties.Name -contains 'module_assignments') -Message 'official smoke runtime packet includes module_assignments'
    Add-Assertion -Results ([ref]$results) -Condition (@($officialState.bound_skill_ids).Count -ge 1) -Message 'official smoke module_assignments carries bounded skill truth'
    Add-Assertion -Results ([ref]$results) -Condition (($officialState.plan_skill_ids -join '|') -ceq ($officialState.bound_skill_ids -join '|')) -Message 'official smoke module plan matches the frozen organization projection'
    Add-Assertion -Results ([ref]$results) -Condition (($officialState.handoff_unit_ids -join '|') -ceq ($officialState.plan_unit_ids -join '|')) -Message 'official smoke Agent handoff follows module-work-plan.json'
    Add-Assertion -Results ([ref]$results) -Condition (($officialState.handoff_skill_ids -join '|') -ceq ($officialState.plan_skill_ids -join '|')) -Message 'official smoke Agent handoff preserves approved Skills'
    Add-Assertion -Results ([ref]$results) -Condition ($officialState.execution_manifest.module_handoff.status -eq 'agent_action_required') -Message 'official smoke module_handoff requires Agent action'
    Add-Assertion -Results ([ref]$results) -Condition (($officialState.execution_manifest.module_handoff.assigned_skill_ids -join '|') -ceq ($officialState.handoff_skill_ids -join '|')) -Message 'official smoke module_handoff matches agent-execution-handoff.json'

    $originalHostId = $env:VCO_HOST_ID
    $originalCodexHome = $env:CODEX_HOME
    $scenarioAgentsHome = $env:VIBE_AGENTS_HOME
    try {
        $customTargetRoot = Join-Path $artifactRoot '.codex-custom'
        $customSkillDir = Join-Path $customTargetRoot 'skills\custom\genomics-qc-flow'
        New-Item -ItemType Directory -Path $customSkillDir -Force | Out-Null
        @(
            '---',
            'name: genomics-qc-flow',
            'description: Custom genomics QC workflow for module handoff closure validation.',
            '---',
            '# genomics-qc-flow'
        ) | Set-Content -LiteralPath (Join-Path $customSkillDir 'SKILL.md') -Encoding UTF8

        $customConfigRoot = Join-Path $customTargetRoot 'config'
        New-Item -ItemType Directory -Path $customConfigRoot -Force | Out-Null
        @'
{
  "workflows": [
    {
      "id": "genomics-qc-flow",
      "enabled": true,
      "path": "skills/custom/genomics-qc-flow",
      "keywords": ["bioanalysis", "qc", "workflow"],
      "intent_tags": ["planning", "coding", "research"],
      "non_goals": ["billing"],
      "requires": ["vibe"],
      "trigger_mode": "advisory",
      "preferred_stages": ["plan_execute"],
      "parallelizable_in_root_xl": true,
      "priority": 82
    }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $customConfigRoot 'custom-workflows.json') -Encoding UTF8

        $env:VCO_HOST_ID = 'codex'
        $env:CODEX_HOME = $customTargetRoot
        $env:VIBE_AGENTS_HOME = $customTargetRoot

        $customHostDecisionJson = New-ModuleHandoffHostDecisionJson `
            -SkillId 'genomics-qc-flow' `
            -ModuleId 'genomics_qc' `
            -Goal 'Run the approved genomics quality-control workflow.'
        $custom = Invoke-ClosureScenario `
            -RepoRoot $repoRoot `
            -Task 'Need bioanalysis qc workflow and governed planning for genomics deliverables.' `
            -RunId ('closure-custom-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
            -ArtifactRoot $artifactRoot `
            -ApprovedSkillIds @('genomics-qc-flow') `
            -RuntimeConfig $context.runtimeConfig `
            -HostDecisionJson $customHostDecisionJson
        $customState = Get-HandoffClosureState -Summary $custom

        Add-Assertion -Results ([ref]$results) -Condition ($customState.runtime_input.PSObject.Properties.Name -contains 'module_assignments') -Message 'custom smoke runtime packet includes module_assignments'
        Add-Assertion -Results ([ref]$results) -Condition (($customState.plan_skill_ids -join '|') -ceq ($customState.bound_skill_ids -join '|')) -Message 'custom smoke module plan matches the frozen organization projection'
        Add-Assertion -Results ([ref]$results) -Condition (($customState.handoff_unit_ids -join '|') -ceq ($customState.plan_unit_ids -join '|')) -Message 'custom smoke Agent handoff follows module-work-plan.json'
        Add-Assertion -Results ([ref]$results) -Condition ($customState.handoff_skill_ids -contains 'genomics-qc-flow') -Message 'custom smoke hands the admitted custom Skill to the Agent'
        Add-Assertion -Results ([ref]$results) -Condition (($customState.execution_manifest.module_handoff.assigned_skill_ids -join '|') -ceq ($customState.handoff_skill_ids -join '|')) -Message 'custom smoke module_handoff matches agent-execution-handoff.json'
    }
    finally {
        $env:VCO_HOST_ID = $originalHostId
        $env:CODEX_HOME = $originalCodexHome
        $env:VIBE_AGENTS_HOME = $scenarioAgentsHome
    }

    $rootHostDecisionJson = New-ModuleHandoffHostDecisionJson `
        -SkillId 'systematic-debugging' `
        -ModuleId 'root_debugging' `
        -Goal 'Preserve the root-approved debugging work for child execution.'
    $root = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'Root bounded work seed for child module handoff closure checks.' `
        -RunId ('closure-root-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
        -ArtifactRoot $artifactRoot `
        -RuntimeConfig $context.runtimeConfig `
        -HostDecisionJson $rootHostDecisionJson
    $rootState = Get-HandoffClosureState -Summary $root

    $childRunId = 'closure-child-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $childParentUnitId = 'closure-child-unit'
    $childDelegationEnvelopePath = New-ClosureDelegationEnvelopeForGate `
        -RootSummary $root `
        -ChildRunId $childRunId `
        -ParentUnitId $childParentUnitId `
        -ApprovedSkillIds $rootState.bound_skill_ids

    $child = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'Preserve the root-approved module work in the child handoff.' `
        -RunId $childRunId `
        -ArtifactRoot $artifactRoot `
        -GovernanceScope 'child' `
        -RootRunId ([string]$root.summary.run_id) `
        -ParentRunId ([string]$root.summary.run_id) `
        -ParentUnitId $childParentUnitId `
        -InheritedRequirementDocPath ([string]$root.summary.artifacts.requirement_doc) `
        -InheritedExecutionPlanPath ([string]$root.summary.artifacts.execution_plan) `
        -DelegationEnvelopePath $childDelegationEnvelopePath `
        -ApprovedSkillIds $rootState.bound_skill_ids `
        -RuntimeConfig $context.runtimeConfig `
        -HostDecisionJson $rootHostDecisionJson
    $childState = Get-HandoffClosureState -Summary $child

    Add-Assertion -Results ([ref]$results) -Condition ($childState.runtime_input.PSObject.Properties.Name -contains 'module_assignments') -Message 'child closure smoke runtime packet includes module_assignments'
    Add-Assertion -Results ([ref]$results) -Condition (@($childState.bound_skill_ids).Count -ge 1) -Message 'child closure smoke keeps inherited bounded work in module_assignments'
    Add-Assertion -Results ([ref]$results) -Condition (($childState.handoff_unit_ids -join '|') -ceq ($childState.plan_unit_ids -join '|')) -Message 'child closure smoke Agent handoff follows module-work-plan.json'
    Add-Assertion -Results ([ref]$results) -Condition (($childState.handoff_skill_ids -join '|') -ceq ($rootState.bound_skill_ids -join '|')) -Message 'child closure smoke hands off only root-approved Skills'
    Add-Assertion -Results ([ref]$results) -Condition (($childState.execution_manifest.module_handoff.assigned_skill_ids -join '|') -ceq ($childState.handoff_skill_ids -join '|')) -Message 'child closure smoke module_handoff matches agent-execution-handoff.json'
}
finally {
    $env:VIBE_AGENTS_HOME = $originalAgentsHome
    if (-not $WriteArtifacts -and (Test-Path -LiteralPath $artifactRoot)) {
        Remove-Item -LiteralPath $artifactRoot -Recurse -Force
    }
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    artifact_root = $artifactRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-module-dispatch-closure'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-module-dispatch-closure-gate.json') -Value $report
}

if (-not $gatePassed) {
    throw "vibe-module-dispatch-closure-gate failed with $failureCount failing assertion(s)."
}

$report
