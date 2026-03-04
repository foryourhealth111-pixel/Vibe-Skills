# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-RoutingRuleForCandidate {
    param(
        [string]$Candidate,
        [object]$RoutingRules
    )

    if (-not $RoutingRules -or -not $RoutingRules.skills -or -not $Candidate) {
        return $null
    }

    $keys = @($RoutingRules.skills.PSObject.Properties.Name)
    if ($keys -contains $Candidate) {
        return $RoutingRules.skills.$Candidate
    }

    return $null
}

function Test-RuleTaskAllowed {
    param(
        [object]$Rule,
        [string]$TaskType
    )

    if (-not $Rule -or -not $Rule.task_allow) { return $true }
    $allowed = @($Rule.task_allow)
    if ($allowed.Count -eq 0) { return $true }
    return ($allowed -contains $TaskType)
}

function Get-CanonicalForTaskHit {
    param(
        [object]$Rule,
        [string]$TaskType
    )

    if (-not $Rule -or -not $Rule.canonical_for_task) { return 0.0 }
    $canonical = @($Rule.canonical_for_task)
    if ($canonical -contains $TaskType) { return 1.0 }
    return 0.0
}

function Get-PackDefaultCandidate {
    param(
        [object]$Pack,
        [string]$TaskType,
        [string[]]$PreferredCandidates,
        [string[]]$AllCandidates
    )

    if (-not $Pack -or -not $Pack.defaults_by_task) { return $null }

    $taskKeys = @($Pack.defaults_by_task.PSObject.Properties.Name)
    if (-not ($taskKeys -contains $TaskType)) { return $null }

    $defaultSkill = [string]$Pack.defaults_by_task.$TaskType
    if (-not $defaultSkill) { return $null }

    if ($PreferredCandidates -and ($PreferredCandidates -contains $defaultSkill)) {
        return $defaultSkill
    }

    if ($AllCandidates -and ($AllCandidates -contains $defaultSkill)) {
        return $defaultSkill
    }

    return $null
}


