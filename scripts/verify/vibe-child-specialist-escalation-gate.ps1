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

function New-ChildDelegationEnvelopeForGate {
    param(
        [Parameter(Mandatory)] [object]$RootSummary,
        [Parameter(Mandatory)] [string]$ChildRunId,
        [AllowNull()] [string[]]$ApprovedSpecialists = @()
    )

    $sessionRoot = [string]$RootSummary.summary.session_root
    $childSessionRoot = Join-Path ([System.IO.Path]::GetDirectoryName($sessionRoot)) $ChildRunId
    New-Item -ItemType Directory -Path $childSessionRoot -Force | Out-Null
    $envelopePath = Get-VibeGovernanceArtifactPath -SessionRoot $childSessionRoot -ArtifactName 'delegation_envelope'
    Write-VibeDelegationEnvelope `
        -Path $envelopePath `
        -RootRunId ([string]$RootSummary.summary.run_id) `
        -ParentRunId ([string]$RootSummary.summary.run_id) `
        -ParentUnitId 'child-specialist-escalation-unit' `
        -ChildRunId $ChildRunId `
        -RequirementDocPath ([string]$RootSummary.summary.artifacts.requirement_doc) `
        -ExecutionPlanPath ([string]$RootSummary.summary.artifacts.execution_plan) `
        -WriteScope 'gate:child-specialist-escalation' `
        -ApprovedSpecialists @($ApprovedSpecialists) `
        -ReviewMode 'module_acceptance' | Out-Null
    return $envelopePath
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$runtimeEntryPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
$results = @()

$policyText = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8
foreach ($token in @('agent_skill_organization', 'module_assignments', 'module_skill_contract', 'host_module_execution_contract', 'module_acceptance')) {
    Add-Assertion -Results ([ref]$results) -Condition ($policyText.Contains($token)) -Message ("runtime input policy contains module handoff token: {0}" -f $token)
}

$teamText = Get-Content -LiteralPath (Join-Path $repoRoot 'protocols\team.md') -Raw -Encoding UTF8
$stableDocText = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\root-child-vibe-hierarchy-governance.md') -Raw -Encoding UTF8
Add-Assertion -Results ([ref]$results) -Condition ($teamText.Contains('they never auto-promote into approved module work units')) -Message 'team protocol forbids route candidates from becoming executable automatically'
Add-Assertion -Results ([ref]$results) -Condition ($stableDocText.Contains('until the root Agent explicitly updates the approved skill organization')) -Message 'stable hierarchy doc requires explicit root Agent approval'

$runId = "child-specialist-escalation-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
$artifactRoot = Join-Path $repoRoot (".tmp\child-specialist-escalation-{0}" -f $runId)
$hostRoot = Join-Path $artifactRoot '.agents'
$hostSkillsRoot = Join-Path $hostRoot 'skills'
New-Item -ItemType Directory -Path $hostSkillsRoot -Force | Out-Null
foreach ($skillId in @('systematic-debugging', 'scikit-learn')) {
    $source = Join-Path $repoRoot ("bundled\skills\{0}" -f $skillId)
    $destination = Join-Path $hostSkillsRoot $skillId
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}
$env:VIBE_AGENTS_HOME = $hostRoot
$hostDecisionJson = @{
    agent_skill_organization = [ordered]@{
        schema_version = 'agent_skill_organization_v1'
        derived_by = 'agent'
        workflow_level = 'XL'
        modules = @(
            [ordered]@{
                module_id = 'root_approved_debugging'
                goal = 'Preserve the root-approved debugging workflow in the child lane.'
                candidate_skill_ids = @('systematic-debugging', 'scikit-learn')
                execution_mode = 'skill_assigned'
                acceptance_criteria = @(
                    [ordered]@{
                        criterion_id = 'root-approved-debugging-result'
                        description = 'The child lane preserves and completes the root-approved debugging workflow.'
                        verification_mode = 'automated'
                    }
                )
            }
        )
        selected_skills = @(
            [ordered]@{
                skill_id = 'systematic-debugging'
                module_ids = @('root_approved_debugging')
                responsibility = 'Own the bounded debugging work approved by the root Agent.'
                reason = 'The root Agent selected this skill after reading its SKILL.md.'
            }
        )
        uncovered_modules = @()
        workflow_level_contract = [ordered]@{
            L = 'Use one serial governed lane.'
            XL = 'Use bounded waves while preserving root approval.'
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

$rootSummary = & $runtimeEntryPath `
    -Task 'I have a failing test and stack trace. Investigate it systematically.' `
    -Mode interactive_governed `
    -GovernanceScope root `
    -RunId ("{0}-root" -f $runId) `
    -ArtifactRoot $artifactRoot `
    -HostDecisionJson $hostDecisionJson

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $rootSummary) -Message 'root module handoff probe returned summary payload'
$hasRootSummary = ($null -ne $rootSummary) -and ($rootSummary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasRootSummary -Message 'root module handoff probe has summary object'

$approvedForChild = @()
if ($hasRootSummary) {
    $rootRuntimeInputPacket = Get-Content -LiteralPath $rootSummary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $rootModuleWorkPlan = Get-Content -LiteralPath $rootSummary.summary.artifacts.module_work_plan -Raw -Encoding UTF8 | ConvertFrom-Json
    $rootAgentExecutionHandoff = Get-Content -LiteralPath $rootSummary.summary.artifacts.agent_execution_handoff -Raw -Encoding UTF8 | ConvertFrom-Json
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.governance_scope -eq 'root') -Message 'root module handoff probe is in root scope'
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'root module handoff probe keeps vibe authority'
    $rootBoundSkillIds = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $rootRuntimeInputPacket)
    $rootPlanUnitIds = @($rootModuleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
    $rootHandoffUnitIds = @($rootAgentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.PSObject.Properties.Name -contains 'module_assignments') -Message 'root runtime packet includes module_assignments'
    Add-Assertion -Results ([ref]$results) -Condition ((@($rootBoundSkillIds).Count -eq 1) -and ([string]$rootBoundSkillIds[0] -eq 'systematic-debugging')) -Message 'root module_assignments contains only the Agent-approved debugging skill'
    Add-Assertion -Results ([ref]$results) -Condition ($rootRuntimeInputPacket.module_assignments.source -eq 'agent_skill_organization') -Message 'root module_assignments projects Agent skill organization'
    Add-Assertion -Results ([ref]$results) -Condition (($rootPlanUnitIds -join '|') -ceq ($rootHandoffUnitIds -join '|')) -Message 'root Agent handoff follows the approved module work plan'
    $approvedForChild = @($rootBoundSkillIds)
}

$childSummary = $null
if ($hasRootSummary) {
    $childRunId = ("{0}-child" -f $runId)
    $childDelegationEnvelopePath = New-ChildDelegationEnvelopeForGate -RootSummary $rootSummary -ChildRunId $childRunId -ApprovedSpecialists @($approvedForChild)
    $childSummary = & $runtimeEntryPath `
        -Task 'Train a scikit-learn model for this child task, but preserve the root-approved debugging boundary.' `
        -Mode interactive_governed `
        -GovernanceScope child `
        -RunId $childRunId `
        -RootRunId ([string]$rootSummary.summary.run_id) `
        -ParentRunId ([string]$rootSummary.summary.run_id) `
        -ParentUnitId 'child-specialist-escalation-unit' `
        -InheritedRequirementDocPath ([string]$rootSummary.summary.artifacts.requirement_doc) `
        -InheritedExecutionPlanPath ([string]$rootSummary.summary.artifacts.execution_plan) `
        -DelegationEnvelopePath $childDelegationEnvelopePath `
        -ApprovedSpecialistSkillIds $approvedForChild `
        -ArtifactRoot $artifactRoot `
        -HostDecisionJson $hostDecisionJson
}

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $childSummary) -Message 'child module handoff probe returned summary payload'
$hasChildSummary = ($null -ne $childSummary) -and ($childSummary.PSObject.Properties.Name -contains 'summary')
Add-Assertion -Results ([ref]$results) -Condition $hasChildSummary -Message 'child module handoff probe has summary object'

$handedOffSkillIds = @()
$childClaims = @()
if ($hasChildSummary) {
    $runtimeInputPacket = Get-Content -LiteralPath $childSummary.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $moduleWorkPlan = Get-Content -LiteralPath $childSummary.summary.artifacts.module_work_plan -Raw -Encoding UTF8 | ConvertFrom-Json
    $agentExecutionHandoff = Get-Content -LiteralPath $childSummary.summary.artifacts.agent_execution_handoff -Raw -Encoding UTF8 | ConvertFrom-Json
    $executionManifest = Get-Content -LiteralPath $childSummary.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    $delegationValidation = Get-Content -LiteralPath $childSummary.summary.artifacts.delegation_validation_receipt -Raw -Encoding UTF8 | ConvertFrom-Json

    $boundSkillIds = @(Get-VibeModuleAssignmentsBoundSkillIds -RuntimeInputPacket $runtimeInputPacket)
    $selectedSkillIds = @($runtimeInputPacket.agent_skill_organization.selected_skills | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $plannedUnitIds = @($moduleWorkPlan.work_units | ForEach-Object { [string]$_.unit_id })
    $handoffUnitIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.unit_id })
    $handedOffSkillIds = @($agentExecutionHandoff.units | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.governance_scope -eq 'child') -Message 'module handoff smoke runs in child scope'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.authority_flags.explicit_runtime_skill -eq 'vibe') -Message 'module handoff smoke keeps vibe runtime authority'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.PSObject.Properties.Name -contains 'module_assignments') -Message 'child runtime packet includes module_assignments'
    Add-Assertion -Results ([ref]$results) -Condition ((@($boundSkillIds).Count -eq 1) -and ([string]$boundSkillIds[0] -eq 'systematic-debugging')) -Message 'child module_assignments keeps only the root-approved skill'
    Add-Assertion -Results ([ref]$results) -Condition (($selectedSkillIds -join '|') -eq ($boundSkillIds -join '|')) -Message 'child module_assignments matches the Agent skill organization'
    Add-Assertion -Results ([ref]$results) -Condition ($runtimeInputPacket.module_assignments.source -eq 'agent_skill_organization') -Message 'child module_assignments source is Agent skill organization'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$delegationValidation.write_scope_valid) -Message 'child module handoff validates delegation write scope'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$delegationValidation.prompt_tail_valid) -Message 'child module handoff preserves $vibe prompt-tail discipline'
    Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$runtimeInputPacket.authority_flags.allow_completion_claim) -Message 'child runtime input packet disallows final completion claim'
    Add-Assertion -Results ([ref]$results) -Condition ($moduleWorkPlan.schema_version -eq 'module_work_plan_v1') -Message 'child run keeps module-work-plan.json as work authority'
    Add-Assertion -Results ([ref]$results) -Condition (($plannedUnitIds -join '|') -ceq ($handoffUnitIds -join '|')) -Message 'child Agent handoff follows the approved module work plan'
    Add-Assertion -Results ([ref]$results) -Condition (($handedOffSkillIds -join '|') -ceq ($boundSkillIds -join '|')) -Message 'child Agent handoff contains only root-approved Skills'

    $candidateAuditSkillIds = @($runtimeInputPacket.skill_routing.candidates | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    Add-Assertion -Results ([ref]$results) -Condition ($candidateAuditSkillIds -contains 'scikit-learn') -Message 'child candidate audit records the unapproved scikit-learn candidate'
    Add-Assertion -Results ([ref]$results) -Condition (-not ($boundSkillIds -contains 'scikit-learn')) -Message 'child candidate audit does not mutate module_assignments'

    Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.governance_scope -eq 'child') -Message 'execution manifest is marked child scope'
    Add-Assertion -Results ([ref]$results) -Condition (-not [bool]$executionManifest.authority.completion_claim_allowed) -Message 'child execution manifest cannot issue final completion claim'
    Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.status -eq 'agent_action_required') -Message 'child execution manifest stops for Agent module work'
    Add-Assertion -Results ([ref]$results) -Condition ($executionManifest.module_handoff.status -eq 'agent_action_required') -Message 'child module_handoff records Agent action required'
    Add-Assertion -Results ([ref]$results) -Condition (($executionManifest.module_handoff.assigned_skill_ids -join '|') -ceq ($handedOffSkillIds -join '|')) -Message 'child module_handoff matches agent-execution-handoff.json'

    $childClaims = if ($executionManifest.PSObject.Properties.Name -contains 'child_completion_claims') { @($executionManifest.child_completion_claims) } else { @() }
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$gatePassed = ($failureCount -eq 0)
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    gate_passed = $gatePassed
    assertion_count = @($results).Count
    failure_count = $failureCount
    runtime_summary_path = if ($null -ne $childSummary -and ($childSummary.PSObject.Properties.Name -contains 'summary_path')) { $childSummary.summary_path } else { $null }
    handed_off_skill_count = @($handedOffSkillIds).Count
    child_claim_count = @($childClaims).Count
    results = @($results)
}

if ($WriteArtifacts) {
    $targetDir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $repoRoot 'outputs\verify\vibe-child-specialist-escalation'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-child-specialist-escalation-gate.json') -Value $report
} elseif (Test-Path -LiteralPath $artifactRoot) {
    Remove-Item -LiteralPath $artifactRoot -Recurse -Force
}

if (-not $gatePassed) {
    throw "vibe-child-specialist-escalation-gate failed with $failureCount failing assertion(s)."
}

$report
