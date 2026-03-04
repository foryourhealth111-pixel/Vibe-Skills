# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-MemoryGovernanceAdvice {
    param(
        [string]$Grade,
        [string]$TaskType,
        [object]$MemoryGovernancePolicy
    )

    if (-not $MemoryGovernancePolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            primary_memory = $null
            project_decision_memory = $null
            short_term_memory = $null
            long_term_memory = $null
            disabled_systems = @()
            governance_contract = [pscustomobject]@{}
            role_boundaries = [pscustomobject]@{}
        }
    }

    $enabled = $true
    if ($MemoryGovernancePolicy.enabled -ne $null) {
        $enabled = [bool]$MemoryGovernancePolicy.enabled
    }

    $mode = if ($MemoryGovernancePolicy.mode) { [string]$MemoryGovernancePolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            primary_memory = $null
            project_decision_memory = $null
            short_term_memory = $null
            long_term_memory = $null
            disabled_systems = @()
            governance_contract = [pscustomobject]@{}
            role_boundaries = [pscustomobject]@{}
        }
    }

    $taskAllow = @("planning", "coding", "review", "debug", "research")
    if ($MemoryGovernancePolicy.task_allow) {
        $taskAllow = @($MemoryGovernancePolicy.task_allow)
    }

    $gradeAllow = @("M", "L", "XL")
    if ($MemoryGovernancePolicy.grade_allow) {
        $gradeAllow = @($MemoryGovernancePolicy.grade_allow)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $scopeApplicable = ($taskApplicable -and $gradeApplicable)

    $taskDefaults = $null
    if ($MemoryGovernancePolicy.defaults_by_task) {
        $taskKeys = @($MemoryGovernancePolicy.defaults_by_task.PSObject.Properties.Name)
        if ($taskKeys -contains $TaskType) {
            $taskDefaults = $MemoryGovernancePolicy.defaults_by_task.$TaskType
        }
    }

    $primaryMemory = if ($taskDefaults -and $taskDefaults.primary) { [string]$taskDefaults.primary } else { "state_store" }
    $projectDecisionMemory = if ($taskDefaults -and $taskDefaults.project_decisions) { [string]$taskDefaults.project_decisions } else { "serena" }
    $shortTermMemory = if ($taskDefaults -and $taskDefaults.short_cache) { [string]$taskDefaults.short_cache } else { "ruflo" }
    $longTermMemory = if ($taskDefaults -and $taskDefaults.long_term) { [string]$taskDefaults.long_term } else { "cognee" }

    $disabledSystems = @()
    if ($MemoryGovernancePolicy.role_boundaries -and $MemoryGovernancePolicy.role_boundaries.episodic_memory) {
        $episodicBoundary = $MemoryGovernancePolicy.role_boundaries.episodic_memory
        if ($episodicBoundary.status -eq "disabled") {
            if ($episodicBoundary.canonical_name) {
                $disabledSystems += [string]$episodicBoundary.canonical_name
            } else {
                $disabledSystems += "episodic-memory"
            }
        }
    }

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                $enforcement = "advisory"
                $reason = "soft_advisory"
            }
            "strict" {
                $enforcement = "required"
                $reason = "strict_required"
            }
            default {
                $enforcement = "advisory"
                $reason = "unknown_mode_advisory"
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($MemoryGovernancePolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$MemoryGovernancePolicy.preserve_routing_assignment
    }

    $governanceContract = [ordered]@{
        state_store = "session_state_only"
        serena = "explicit_project_decisions_only"
        ruflo = "short_term_vector_cache_only"
        cognee = "long_term_graph_memory_only"
        "episodic-memory" = "disabled"
    }

    $roleBoundaries = [pscustomobject]@{}
    if ($MemoryGovernancePolicy.role_boundaries) {
        $roleBoundaries = $MemoryGovernancePolicy.role_boundaries
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        primary_memory = $primaryMemory
        project_decision_memory = $projectDecisionMemory
        short_term_memory = $shortTermMemory
        long_term_memory = $longTermMemory
        disabled_systems = @($disabledSystems | Select-Object -Unique)
        governance_contract = [pscustomobject]$governanceContract
        role_boundaries = $roleBoundaries
    }
}


