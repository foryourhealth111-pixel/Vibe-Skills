# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-OpenSpecTaskId {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType
    )

    $raw = "{0}|{1}|{2}" -f $Grade, $TaskType, $PromptLower
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
        $hashBytes = $sha1.ComputeHash($bytes)
        $hash = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
        if ($hash.Length -ge 12) {
            return $hash.Substring(0, 12)
        }
        return $hash
    } finally {
        $sha1.Dispose()
    }
}

function Get-OpenSpecGovernanceAdvice {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedCanonical,
        [object]$OpenSpecPolicy
    )

    if (-not $OpenSpecPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            profile = "none"
            task_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            bypass_due_to_requested_skill = $false
            preserve_routing_assignment = $true
            task_id = $null
            recommended_artifact = $null
            should_upgrade_to_full = $false
            upgrade_trigger_matches = @()
        }
    }

    $mode = if ($OpenSpecPolicy.mode) { [string]$OpenSpecPolicy.mode } else { "off" }
    if ($mode -eq "off") {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            profile = "none"
            task_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            bypass_due_to_requested_skill = $false
            preserve_routing_assignment = $true
            task_id = $null
            recommended_artifact = $null
            should_upgrade_to_full = $false
            upgrade_trigger_matches = @()
        }
    }

    $profile = "none"
    if ($OpenSpecPolicy.profile_by_grade) {
        $gradeKeys = @($OpenSpecPolicy.profile_by_grade.PSObject.Properties.Name)
        if ($gradeKeys -contains $Grade) {
            $profile = [string]$OpenSpecPolicy.profile_by_grade.$Grade
        }
    }

    $taskApplicable = $false
    if ($profile -ne "none" -and $OpenSpecPolicy.required_task_types_by_profile) {
        $profileKeys = @($OpenSpecPolicy.required_task_types_by_profile.PSObject.Properties.Name)
        if ($profileKeys -contains $profile) {
            $requiredTasks = @($OpenSpecPolicy.required_task_types_by_profile.$profile)
            $taskApplicable = ($requiredTasks -contains $TaskType)
        }
    }

    $requestedSkillWhitelist = @()
    if (
        $OpenSpecPolicy.exemptions -and
        $OpenSpecPolicy.exemptions.PSObject.Properties.Name -contains 'requested_skill_whitelist' -and
        $null -ne $OpenSpecPolicy.exemptions.requested_skill_whitelist
    ) {
        $requestedSkillWhitelist = @($OpenSpecPolicy.exemptions.requested_skill_whitelist)
    }

    # requested skill bypass only applies when explicitly whitelisted
    $requestedSkillBypassEnabled = $false
    if (
        $OpenSpecPolicy.exemptions -and
        $OpenSpecPolicy.exemptions.PSObject.Properties.Name -contains 'requested_skill_bypass' -and
        $null -ne $OpenSpecPolicy.exemptions.requested_skill_bypass
    ) {
        $requestedSkillBypassEnabled = [bool]$OpenSpecPolicy.exemptions.requested_skill_bypass
    }

    $requestedCanonicalLower = ""
    if ($RequestedCanonical) {
        $requestedCanonicalLower = ([string]$RequestedCanonical).ToLowerInvariant()
    }

    $requestedSkillWhitelisted = $false
    if ($requestedCanonicalLower -and $requestedSkillWhitelist.Count -gt 0) {
        foreach ($whitelistedSkill in $requestedSkillWhitelist) {
            if (([string]$whitelistedSkill).ToLowerInvariant() -eq $requestedCanonicalLower) {
                $requestedSkillWhitelisted = $true
                break
            }
        }
    }

    $bypassDueToRequestedSkill = $false
    $bypassDueToRequestedSkill = $requestedSkillBypassEnabled -and $requestedSkillWhitelisted

    # trivial prompts stay exempt outside planning
    $trivialNonPlanningExempt = $false
    if ($TaskType -ne "planning" -and $OpenSpecPolicy.exemptions -and $OpenSpecPolicy.exemptions.trivial_prompt_patterns) {
        foreach ($pattern in @($OpenSpecPolicy.exemptions.trivial_prompt_patterns)) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$pattern)) {
                $trivialNonPlanningExempt = $true
                break
            }
        }
    }

    $taskId = Get-OpenSpecTaskId -PromptLower $PromptLower -Grade $Grade -TaskType $TaskType
    $recommendedArtifact = $null
    if ($profile -eq "lite") {
        $liteDir = if ($OpenSpecPolicy.m_lite -and $OpenSpecPolicy.m_lite.directory) {
            [string]$OpenSpecPolicy.m_lite.directory
        } else {
            "openspec/micro"
        }
        $recommendedArtifact = "{0}/{1}.md" -f $liteDir.TrimEnd("/"), $taskId
    } elseif ($profile -eq "full") {
        $changesDir = if ($OpenSpecPolicy.full -and $OpenSpecPolicy.full.changes_dir) {
            [string]$OpenSpecPolicy.full.changes_dir
        } else {
            "openspec/changes"
        }
        $recommendedArtifact = "{0}/{1}" -f $changesDir.TrimEnd("/"), $taskId
    }

    $softScopeHit = $true
    if ($OpenSpecPolicy.soft_confirm_scope) {
        $scopeGrades = @()
        $scopeTasks = @()
        if ($OpenSpecPolicy.soft_confirm_scope.grades) {
            $scopeGrades = @($OpenSpecPolicy.soft_confirm_scope.grades)
        }
        if ($OpenSpecPolicy.soft_confirm_scope.task_types) {
            $scopeTasks = @($OpenSpecPolicy.soft_confirm_scope.task_types)
        }

        if ($scopeGrades.Count -gt 0 -and -not ($scopeGrades -contains $Grade)) {
            $softScopeHit = $false
        }
        if ($scopeTasks.Count -gt 0 -and -not ($scopeTasks -contains $TaskType)) {
            $softScopeHit = $false
        }
    }

    $enforcement = "none"
    $reason = "task_not_applicable"
    if ($trivialNonPlanningExempt) {
        $reason = "trivial_non_planning_exempt"
    } elseif ($taskApplicable -and -not $bypassDueToRequestedSkill) {
        if ($profile -eq "lite") {
            $enforcement = "advisory"
            $reason = "m_lite_card"
        } elseif ($profile -eq "full") {
            switch ($mode) {
                "strict" {
                    $enforcement = "required"
                    $reason = "full_required_strict"
                }
                "soft" {
                    if ($softScopeHit) {
                        $enforcement = "confirm_required"
                        $reason = "full_confirm_soft"
                    } else {
                        $enforcement = "advisory"
                        $reason = "full_advisory_soft_outside_scope"
                    }
                }
                default {
                    $enforcement = "advisory"
                    $reason = "full_advisory_shadow"
                }
            }
        } else {
            $enforcement = "advisory"
            $reason = "profile_none"
        }
    } elseif ($bypassDueToRequestedSkill) {
        $reason = "requested_skill_bypass_whitelist"
    }

    $upgradeMatches = @()
    if ($profile -eq "lite" -and $OpenSpecPolicy.upgrade_triggers) {
        foreach ($trigger in @($OpenSpecPolicy.upgrade_triggers)) {
            if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$trigger)) {
                $upgradeMatches += [string]$trigger
            }
        }
    }

    $preserveRoutingAssignment = $true
    if ($OpenSpecPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$OpenSpecPolicy.preserve_routing_assignment
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        profile = $profile
        task_applicable = $taskApplicable
        enforcement = $enforcement
        reason = $reason
        bypass_due_to_requested_skill = $bypassDueToRequestedSkill
        preserve_routing_assignment = $preserveRoutingAssignment
        task_id = $taskId
        recommended_artifact = $recommendedArtifact
        should_upgrade_to_full = ($upgradeMatches.Count -gt 0)
        upgrade_trigger_matches = @($upgradeMatches)
    }
}

