param()

$ErrorActionPreference = "Stop"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    Write-Host "[FAIL] $Message" -ForegroundColor Red
    return $false
}

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"

    $routeArgs = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if ($RequestedSkill) {
        $routeArgs["RequestedSkill"] = $RequestedSkill
    }

    $json = & $resolver @routeArgs
    return ($json | ConvertFrom-Json)
}

function Set-MemoryGovernanceStage {
    param(
        [string]$ConfigPath,
        [ValidateSet("off", "shadow", "soft", "strict")]
        [string]$Stage
    )

    $policy = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

    switch ($Stage) {
        "off" {
            $policy.enabled = $false
            $policy.mode = "off"
        }
        "shadow" {
            $policy.enabled = $true
            $policy.mode = "shadow"
        }
        "soft" {
            $policy.enabled = $true
            $policy.mode = "soft"
        }
        "strict" {
            $policy.enabled = $true
            $policy.mode = "strict"
        }
    }

    $policy.updated = (Get-Date).ToString("yyyy-MM-dd")
    $policy | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$policyPath = Join-Path $repoRoot "config\memory-governance.json"
$originalRaw = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$results = @()

try {
    Write-Host "=== VCO Memory Governance Gate ==="

    Set-MemoryGovernanceStage -ConfigPath $policyPath -Stage "shadow"

    $routeShadowPlanning = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($null -ne $routeShadowPlanning.selected) -Message "[shadow] selected route exists"
    $results += Assert-True -Condition ($null -ne $routeShadowPlanning.memory_governance_advice) -Message "[shadow] memory_governance_advice exists"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.enabled -eq $true) -Message "[shadow] governance advice enabled"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.scope_applicable -eq $true) -Message "[shadow] scope applicable"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.enforcement -eq "advisory") -Message "[shadow] enforcement is advisory"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.primary_memory -eq "state_store") -Message "[shadow] primary memory is state_store"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.project_decision_memory -eq "serena") -Message "[shadow] project decisions map to Serena"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.short_term_memory -eq "ruflo") -Message "[shadow] short-term cache maps to ruflo"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.long_term_memory -eq "cognee") -Message "[shadow] long-term memory maps to Cognee"
    $results += Assert-True -Condition (@($routeShadowPlanning.memory_governance_advice.disabled_systems) -contains "episodic-memory") -Message "[shadow] episodic-memory is disabled"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.governance_contract.state_store -eq "session_state_only") -Message "[shadow] contract: state_store boundary"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.governance_contract.serena -eq "explicit_project_decisions_only") -Message "[shadow] contract: Serena boundary"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.governance_contract.ruflo -eq "short_term_vector_cache_only") -Message "[shadow] contract: ruflo boundary"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.governance_contract.cognee -eq "long_term_graph_memory_only") -Message "[shadow] contract: Cognee boundary"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.governance_contract.'episodic-memory' -eq "disabled") -Message "[shadow] contract: episodic-memory disabled"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.role_boundaries.episodic_memory.status -eq "disabled") -Message "[shadow] role boundary marks episodic-memory disabled"
    $results += Assert-True -Condition ($routeShadowPlanning.memory_governance_advice.preserve_routing_assignment -eq $true) -Message "[shadow] preserve routing assignment"

    $shadowPack = [string]$routeShadowPlanning.selected.pack_id
    $shadowSkill = [string]$routeShadowPlanning.selected.skill

    $routeShadowDebug = Invoke-Route -Prompt "debug flaky test failures and keep investigation notes" -Grade "M" -TaskType "debug" -RequestedSkill $null
    $results += Assert-True -Condition ($routeShadowDebug.memory_governance_advice.scope_applicable -eq $true) -Message "[shadow] debug task in scope"
    $results += Assert-True -Condition ($routeShadowDebug.memory_governance_advice.primary_memory -eq "state_store") -Message "[shadow] debug primary memory is state_store"

    Set-MemoryGovernanceStage -ConfigPath $policyPath -Stage "strict"
    $routeStrictPlanning = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeStrictPlanning.memory_governance_advice.enforcement -eq "required") -Message "[strict] enforcement is required"
    $results += Assert-True -Condition ($routeStrictPlanning.selected.pack_id -eq $shadowPack) -Message "[strict] selected pack unchanged"
    $results += Assert-True -Condition ($routeStrictPlanning.selected.skill -eq $shadowSkill) -Message "[strict] selected skill unchanged"

    Set-MemoryGovernanceStage -ConfigPath $policyPath -Stage "off"
    $routeOff = Invoke-Route -Prompt "create implementation plan and task breakdown with milestones" -Grade "L" -TaskType "planning" -RequestedSkill $null
    $results += Assert-True -Condition ($routeOff.memory_governance_advice.enabled -eq $false) -Message "[off] governance advice disabled"
    $results += Assert-True -Condition ($routeOff.selected.pack_id -eq $shadowPack) -Message "[off] selected pack unchanged"
    $results += Assert-True -Condition ($routeOff.selected.skill -eq $shadowSkill) -Message "[off] selected skill unchanged"

} finally {
    Set-Content -LiteralPath $policyPath -Value $originalRaw -Encoding UTF8
    Write-Host "Restored memory-governance policy to original content."
}

$passCount = ($results | Where-Object { $_ }).Count
$failCount = ($results | Where-Object { -not $_ }).Count
$total = $results.Count

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}

Write-Host "Memory governance gate passed."
exit 0
