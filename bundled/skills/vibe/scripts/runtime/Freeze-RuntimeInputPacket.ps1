param(
    [Parameter(Mandatory)] [string]$Task,
    [string]$Mode = 'interactive_governed',
    [string]$RunId = '',
    [string]$ArtifactRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'VibeRuntime.Common.ps1')

function Get-VibeRouterTaskType {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $taskLower = $Task.ToLowerInvariant()
    if ($taskLower -match 'review|审查|评审') {
        return 'review'
    }
    if ($taskLower -match 'debug|bug|错误|修复') {
        return 'debug'
    }
    if ($taskLower -match 'research|调研|研究') {
        return 'research'
    }
    if ($taskLower -match 'implement|build|upgrade|更新|增强|执行') {
        return 'coding'
    }
    return 'planning'
}

function New-VibeAdviceSnapshot {
    param(
        [string]$Name,
        [object]$Advice
    )

    if ($null -eq $Advice) {
        return $null
    }

    $snapshot = [ordered]@{
        name = $Name
    }

    foreach ($field in @('enabled', 'mode', 'enforcement', 'reason', 'preserve_routing_assignment', 'confirm_required', 'scope_applicable', 'task_applicable', 'grade_applicable')) {
        if ($Advice.PSObject.Properties.Name -contains $field) {
            $snapshot[$field] = $Advice.$field
        }
    }

    return [pscustomobject]$snapshot
}

$runtime = Get-VibeRuntimeContext -ScriptPath $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = New-VibeRunId
}

$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
$policy = $runtime.runtime_input_packet_policy
$grade = Get-VibeInternalGrade -Task $Task
$taskType = Get-VibeRouterTaskType -Task $Task
$routerScriptPath = Join-Path $runtime.repo_root ([string]$policy.router_script_path)
$requestedSkill = if ($policy.default_requested_skill) { [string]$policy.default_requested_skill } else { 'vibe' }
$unattended = ($Mode -eq 'benchmark_autonomous')

$routeArgs = @(
    '-Prompt', $Task,
    '-Grade', $grade,
    '-TaskType', $taskType,
    '-RequestedSkill', $requestedSkill
)
if ($unattended) {
    $routeArgs += '-Unattended'
}

$routeInvocation = Invoke-VgoPowerShellFile -ScriptPath $routerScriptPath -ArgumentList $routeArgs -NoProfile

if ([int]$routeInvocation.exit_code -ne 0) {
    throw ("Failed to freeze runtime input packet because canonical router exited with code {0}." -f [int]$routeInvocation.exit_code)
}

$routeJson = (@($routeInvocation.output) -join [Environment]::NewLine).Trim()
$routeResult = $routeJson | ConvertFrom-Json

$overlayDecisions = @()
foreach ($overlayField in @($policy.overlay_fields)) {
    if (-not ($routeResult.PSObject.Properties.Name -contains $overlayField)) {
        continue
    }
    $snapshot = New-VibeAdviceSnapshot -Name $overlayField -Advice $routeResult.$overlayField
    if ($null -ne $snapshot) {
        $overlayDecisions += $snapshot
    }
}

$confirmRequired = ([string]$routeResult.route_mode -eq 'confirm_required')
$runtimeSelectedSkill = [string]$policy.explicit_runtime_skill
$routerSelectedSkill = if ($routeResult.selected) { [string]$routeResult.selected.skill } else { $null }
$packet = [pscustomobject]@{
    stage = 'runtime_input_freeze'
    run_id = $RunId
    task = $Task
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    runtime_mode = $Mode
    internal_grade = $grade
    canonical_router = [pscustomobject]@{
        prompt = $Task
        task_type = $taskType
        requested_skill = $requestedSkill
        unattended = [bool]$unattended
        route_script_path = $routerScriptPath
    }
    route_snapshot = [pscustomobject]@{
        selected_pack = if ($routeResult.selected) { [string]$routeResult.selected.pack_id } else { $null }
        selected_skill = $routerSelectedSkill
        route_mode = [string]$routeResult.route_mode
        route_reason = [string]$routeResult.route_reason
        confirm_required = [bool]$confirmRequired
        confidence = if ($routeResult.confidence -ne $null) { [double]$routeResult.confidence } else { $null }
        truth_level = [string]$routeResult.truth_level
        degradation_state = [string]$routeResult.degradation_state
        non_authoritative = [bool]$routeResult.non_authoritative
        fallback_active = [bool]$routeResult.fallback_active
        hazard_alert_required = [bool]$routeResult.hazard_alert_required
        unattended_override_applied = [bool]$routeResult.unattended_override_applied
    }
    overlay_decisions = @($overlayDecisions)
    authority_flags = [pscustomobject]@{
        runtime_entry = 'vibe'
        explicit_runtime_skill = $runtimeSelectedSkill
        router_truth_level = [string]$routeResult.truth_level
        shadow_only = [bool]$policy.shadow_only
        non_authoritative = [bool]$routeResult.non_authoritative
    }
    divergence_shadow = [pscustomobject]@{
        router_selected_skill = $routerSelectedSkill
        runtime_selected_skill = $runtimeSelectedSkill
        skill_mismatch = [bool](-not [string]::Equals($routerSelectedSkill, $runtimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase))
        confirm_required = [bool]$confirmRequired
        explicit_runtime_override_applied = [bool](-not [string]::IsNullOrWhiteSpace($runtimeSelectedSkill))
        explicit_runtime_override_reason = 'governed_runtime_entry'
    }
    provenance = [pscustomobject]@{
        source_of_truth = 'canonical_router_shadow_freeze'
        freeze_before_requirement_doc = [bool]$policy.freeze_before_requirement_doc
        proof_class = 'structure'
    }
}

$packetPath = Get-VibeRuntimeInputPacketPath -RepoRoot $runtime.repo_root -RunId $RunId -ArtifactRoot $ArtifactRoot
Write-VibeJsonArtifact -Path $packetPath -Value $packet

[pscustomobject]@{
    run_id = $RunId
    session_root = $sessionRoot
    packet_path = $packetPath
    packet = $packet
}
