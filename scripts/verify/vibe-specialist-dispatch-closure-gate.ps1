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
        [string[]]$ApprovedSpecialistSkillIds = @()
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
        -ApprovedSpecialistSkillIds $ApprovedSpecialistSkillIds
}

function New-ClosureDelegationEnvelopeForGate {
    param(
        [Parameter(Mandatory)] [object]$RootSummary,
        [Parameter(Mandatory)] [string]$ChildRunId,
        [Parameter(Mandatory)] [string]$ParentUnitId,
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
        -ParentUnitId $ParentUnitId `
        -ChildRunId $ChildRunId `
        -RequirementDocPath ([string]$RootSummary.summary.artifacts.requirement_doc) `
        -ExecutionPlanPath ([string]$RootSummary.summary.artifacts.execution_plan) `
        -WriteScope 'gate:specialist-dispatch-closure' `
        -ApprovedSpecialists @($ApprovedSpecialists) `
        -ReviewMode 'native_contract' | Out-Null
    return $envelopePath
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$results = @()
$artifactRoot = Join-Path $repoRoot (".tmp\specialist-dispatch-closure-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

try {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath (Join-Path $repoRoot 'scripts\runtime\Invoke-PlanExecute.ps1')) -Message 'plan execute script exists'
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath (Join-Path $repoRoot 'scripts\verify\vibe-child-specialist-escalation-gate.ps1')) -Message 'child specialist escalation gate exists'

    $official = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'I have a failing test and a stack trace. Help me debug systematically before proposing fixes.' `
        -RunId ('closure-official-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
        -ArtifactRoot $artifactRoot `
        -RuntimeConfig $context.runtimeConfig
    $officialExecutionManifest = Get-Content -LiteralPath $official.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Assertion -Results ([ref]$results) -Condition ([bool]$officialExecutionManifest.dispatch_integrity.proof_passed) -Message 'official smoke dispatch integrity proof passes'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$officialExecutionManifest.dispatch_integrity.executed_specialists_subset_of_approved_dispatch) -Message 'official smoke executes no unapproved specialist'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$officialExecutionManifest.dispatch_integrity.native_contract_complete_for_approved_dispatch) -Message 'official smoke approved specialist dispatch keeps native contract metadata'

    $originalHostId = $env:VCO_HOST_ID
    $originalCodexHome = $env:CODEX_HOME
    try {
        $customTargetRoot = Join-Path $artifactRoot '.codex-custom'
        $customSkillDir = Join-Path $customTargetRoot 'skills\custom\genomics-qc-flow'
        New-Item -ItemType Directory -Path $customSkillDir -Force | Out-Null
        @(
            '---',
            'name: genomics-qc-flow',
            'description: Custom genomics QC workflow for specialist dispatch closure validation.',
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

        $custom = Invoke-ClosureScenario `
            -RepoRoot $repoRoot `
            -Task 'Need bioanalysis qc workflow and governed planning for genomics deliverables.' `
            -RunId ('closure-custom-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
            -ArtifactRoot $artifactRoot `
            -ApprovedSpecialistSkillIds @('genomics-qc-flow') `
            -RuntimeConfig $context.runtimeConfig
        $customExecutionManifest = Get-Content -LiteralPath $custom.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

        Add-Assertion -Results ([ref]$results) -Condition ([bool]$customExecutionManifest.dispatch_integrity.proof_passed) -Message 'custom smoke dispatch integrity proof passes'
        $customResolvedSkillIds = @(
            @($customExecutionManifest.dispatch_integrity.executed_specialist_skill_ids) +
            @($customExecutionManifest.dispatch_integrity.direct_routed_specialist_skill_ids) +
            @($customExecutionManifest.dispatch_integrity.resolved_specialist_skill_ids)
        ) | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
        Add-Assertion -Results ([ref]$results) -Condition ($customResolvedSkillIds -contains 'genomics-qc-flow') -Message 'custom smoke resolves admitted custom specialist'
        Add-Assertion -Results ([ref]$results) -Condition ([bool]$customExecutionManifest.dispatch_integrity.native_contract_complete_for_approved_dispatch) -Message 'custom smoke approved dispatch carries native entrypoint metadata'
    } finally {
        $env:VCO_HOST_ID = $originalHostId
        $env:CODEX_HOME = $originalCodexHome
    }

    $root = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'Root specialist dispatch seed for child escalation closure checks.' `
        -RunId ('closure-root-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)) `
        -ArtifactRoot $artifactRoot `
        -RuntimeConfig $context.runtimeConfig
    $rootRuntimeInput = Get-Content -LiteralPath $root.summary.artifacts.runtime_input_packet -Raw -Encoding UTF8 | ConvertFrom-Json
    $rootSelectedSkillExecution = Get-VibeRuntimeSelectedSkillExecutionProjection -RuntimeInputPacket $rootRuntimeInput
    $rootApprovedDispatch = if ($null -ne $rootSelectedSkillExecution -and $rootSelectedSkillExecution.PSObject.Properties.Name -contains 'selected_skill_execution') {
        @($rootSelectedSkillExecution.selected_skill_execution)
    } else {
        @()
    }
    $approvedSkillIds = @($rootApprovedDispatch | Select-Object -First 1 | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

    $childRunId = 'closure-child-' + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $childParentUnitId = 'closure-child-unit'
    $childDelegationEnvelopePath = New-ClosureDelegationEnvelopeForGate `
        -RootSummary $root `
        -ChildRunId $childRunId `
        -ParentUnitId $childParentUnitId `
        -ApprovedSpecialists $approvedSkillIds

    $child = Invoke-ClosureScenario `
        -RepoRoot $repoRoot `
        -Task 'Child specialist escalation advisory smoke.' `
        -RunId $childRunId `
        -ArtifactRoot $artifactRoot `
        -GovernanceScope 'child' `
        -RootRunId ([string]$root.summary.run_id) `
        -ParentRunId ([string]$root.summary.run_id) `
        -ParentUnitId $childParentUnitId `
        -InheritedRequirementDocPath ([string]$root.summary.artifacts.requirement_doc) `
        -InheritedExecutionPlanPath ([string]$root.summary.artifacts.execution_plan) `
        -DelegationEnvelopePath $childDelegationEnvelopePath `
        -ApprovedSpecialistSkillIds $approvedSkillIds `
        -RuntimeConfig $context.runtimeConfig
    $childExecutionManifest = Get-Content -LiteralPath $child.summary.artifacts.execution_manifest -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Assertion -Results ([ref]$results) -Condition ([bool]$childExecutionManifest.dispatch_integrity.proof_passed) -Message 'child smoke dispatch integrity proof passes'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$childExecutionManifest.dispatch_integrity.local_suggestions_contained) -Message 'child smoke does not execute advisory-only local suggestions'
    Add-Assertion -Results ([ref]$results) -Condition ([bool]$childExecutionManifest.dispatch_integrity.executed_specialists_subset_of_approved_dispatch) -Message 'child smoke executes only root-approved specialists'
}
finally {
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
        Join-Path $repoRoot 'outputs\verify\vibe-specialist-dispatch-closure'
    } elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
        [System.IO.Path]::GetFullPath($OutputDirectory)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
    }

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-VibeJsonArtifact -Path (Join-Path $targetDir 'vibe-specialist-dispatch-closure-gate.json') -Value $report
}

if (-not $gatePassed) {
    throw "vibe-specialist-dispatch-closure-gate failed with $failureCount failing assertion(s)."
}

$report
