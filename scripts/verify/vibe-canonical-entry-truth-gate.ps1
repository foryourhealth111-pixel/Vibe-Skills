param(
    [Parameter(Mandatory)] [string]$SessionRoot,
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

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

function Read-JsonObject {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "JSON file is empty: $Path"
    }
    return ($raw | ConvertFrom-Json)
}

function Test-ObjectHasProperty {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName
    )

    return ($null -ne $InputObject -and $InputObject.PSObject.Properties.Name -contains $PropertyName)
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-canonical-entry-truth-gate.json'
    $mdPath = Join-Path $dir 'vibe-canonical-entry-truth-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Canonical Entry Truth Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Session Root: `{0}`' -f $Artifact.session_root),
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
$sessionRootResolved = [System.IO.Path]::GetFullPath($SessionRoot)
$assertions = [System.Collections.Generic.List[object]]::new()

$runtimeEntrypointPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $runtimeEntrypointPath) -Message 'canonical truth gate resolves runtime entrypoint path' -Details $runtimeEntrypointPath

$receiptPath = Join-Path $sessionRootResolved 'host-launch-receipt.json'
$runtimePacketPath = Join-Path $sessionRootResolved 'runtime-input-packet.json'
$governanceCapsulePath = Join-Path $sessionRootResolved 'governance-capsule.json'
$stageLineagePath = Join-Path $sessionRootResolved 'stage-lineage.json'

$hasReceipt = Test-Path -LiteralPath $receiptPath
$hasRuntimePacket = Test-Path -LiteralPath $runtimePacketPath
$hasGovernanceCapsule = Test-Path -LiteralPath $governanceCapsulePath
$hasStageLineage = Test-Path -LiteralPath $stageLineagePath

Add-Assertion -Assertions $assertions -Pass $hasReceipt -Message 'host-launch-receipt.json exists' -Details $receiptPath
if (-not $hasReceipt) {
    Add-Assertion -Assertions $assertions -Pass $false -Message 'reading SKILL.md alone is not canonical vibe entry' -Details 'canonical entry requires launch artifacts, not wrapper or bootstrap prose'
}
Add-Assertion -Assertions $assertions -Pass $hasRuntimePacket -Message 'runtime-input-packet.json exists' -Details $runtimePacketPath
Add-Assertion -Assertions $assertions -Pass $hasGovernanceCapsule -Message 'governance-capsule.json exists' -Details $governanceCapsulePath
Add-Assertion -Assertions $assertions -Pass $hasStageLineage -Message 'stage-lineage.json exists' -Details $stageLineagePath

if ($hasReceipt -and $hasRuntimePacket -and $hasGovernanceCapsule -and $hasStageLineage) {
    $receipt = Read-JsonObject -Path $receiptPath
    $runtimePacket = Read-JsonObject -Path $runtimePacketPath
    $governanceCapsule = Read-JsonObject -Path $governanceCapsulePath
    $stageLineage = Read-JsonObject -Path $stageLineagePath
    $entryIntentId = if (Test-ObjectHasProperty -InputObject $runtimePacket -PropertyName 'entry_intent_id') { [string]$runtimePacket.entry_intent_id } else { '' }
    $confirmRequired = $false

    Add-Assertion -Assertions $assertions -Pass ([string]$receipt.entry_id -eq 'vibe') -Message 'host launch receipt entry_id is vibe'
    Add-Assertion -Assertions $assertions -Pass ([string]$receipt.launch_mode -eq 'canonical-entry') -Message 'host launch receipt launch_mode is canonical-entry'
    Add-Assertion -Assertions $assertions -Pass ([string]$receipt.launch_status -eq 'verified') -Message 'host launch receipt launch_status is verified'
    Add-Assertion -Assertions $assertions -Pass (-not [string]::IsNullOrWhiteSpace([string]$receipt.host_id)) -Message 'host launch receipt records host id'

    Add-Assertion -Assertions $assertions -Pass (Test-ObjectHasProperty -InputObject $runtimePacket -PropertyName 'module_assignments') -Message 'runtime packet includes module_assignments'

    Add-Assertion -Assertions $assertions -Pass (-not [string]::IsNullOrWhiteSpace($entryIntentId)) -Message 'runtime packet preserves entry_intent_id independently from router authority'

    if (Test-ObjectHasProperty -InputObject $runtimePacket -PropertyName 'module_assignments') {
        $moduleAssignments = $runtimePacket.module_assignments
        $boundSkillIds = if (Test-ObjectHasProperty -InputObject $moduleAssignments -PropertyName 'units') {
            @($moduleAssignments.units | ForEach-Object { [string]$_.bound_skill } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        } else {
            @()
        }
        Add-Assertion -Assertions $assertions -Pass (Test-ObjectHasProperty -InputObject $moduleAssignments -PropertyName 'units') -Message 'runtime packet exposes module_assignments units'

        if ((Test-ObjectHasProperty -InputObject $runtimePacket -PropertyName 'agent_skill_organization') -and $null -ne $runtimePacket.agent_skill_organization) {
            $organizedSkillIds = @(
                $runtimePacket.agent_skill_organization.selected_skills |
                    ForEach-Object { [string]$_.skill_id } |
                    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                    Sort-Object -Unique
            )
            $sortedBoundSkillIds = @($boundSkillIds | Sort-Object -Unique)
            Add-Assertion -Assertions $assertions -Pass (($sortedBoundSkillIds -join '|') -eq ($organizedSkillIds -join '|')) -Message 'runtime packet module_assignments matches the Agent skill organization'
        }
    }

    Add-Assertion -Assertions $assertions -Pass (-not (Test-ObjectHasProperty -InputObject $runtimePacket -PropertyName 'skill_usage')) -Message 'runtime packet omits retired skill_usage ledger'

    Add-Assertion -Assertions $assertions -Pass ([string]$governanceCapsule.runtime_selected_skill -eq 'vibe') -Message 'governance capsule keeps vibe as runtime authority'

    $stageCount = if (Test-ObjectHasProperty -InputObject $stageLineage -PropertyName 'stages') { @($stageLineage.stages).Count } else { 0 }
    Add-Assertion -Assertions $assertions -Pass ($stageCount -ge 1) -Message 'stage lineage records at least one stage'
    $lastStageName = if (Test-ObjectHasProperty -InputObject $stageLineage -PropertyName 'last_stage_name') { [string]$stageLineage.last_stage_name } else { '' }
    Add-Assertion -Assertions $assertions -Pass (-not [string]::IsNullOrWhiteSpace($lastStageName)) -Message 'stage lineage records terminal stage name'
    if (-not [string]::IsNullOrWhiteSpace([string]$receipt.requested_stage_stop)) {
        Add-Assertion -Assertions $assertions -Pass ([string]$lastStageName -eq [string]$receipt.requested_stage_stop) -Message 'stage lineage terminal stage matches host launch receipt requested stop'
    }
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$artifact = [pscustomobject]@{
    gate = 'vibe-canonical-entry-truth-gate'
    repo_root = $repoRoot
    session_root = $sessionRootResolved
    gate_result = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [pscustomobject]@{
        failure_count = $failureCount
        session_root = $sessionRootResolved
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
