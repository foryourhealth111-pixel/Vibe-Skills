# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-GsdOverlayAdvice {
    param(
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [object]$GsdOverlayPolicy
    )

    if (-not $GsdOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            preflight_should_apply = $false
            wave_contract_should_apply = $false
            should_apply_hook = $false
            artifacts = [pscustomobject]@{
                brownfield_directory = $null
                assumption_artifact = $null
                wave_artifact = $null
            }
        }
    }

    $enabled = $true
    if ($GsdOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$GsdOverlayPolicy.enabled
    }

    $mode = if ($GsdOverlayPolicy.mode) { [string]$GsdOverlayPolicy.mode } else { "off" }
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
            preflight_should_apply = $false
            wave_contract_should_apply = $false
            should_apply_hook = $false
            artifacts = [pscustomobject]@{
                brownfield_directory = $null
                assumption_artifact = $null
                wave_artifact = $null
            }
        }
    }

    $taskAllow = @("planning")
    if ($GsdOverlayPolicy.task_allow) {
        $taskAllow = @($GsdOverlayPolicy.task_allow)
    }

    $gradeAllow = @("L", "XL")
    if ($GsdOverlayPolicy.grade_allow) {
        $gradeAllow = @($GsdOverlayPolicy.grade_allow)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $scopeApplicable = ($taskApplicable -and $gradeApplicable)

    $preflightApply = $scopeApplicable

    $waveEnabled = $false
    $waveXlOnly = $true
    if ($GsdOverlayPolicy.wave_contract) {
        if ($GsdOverlayPolicy.wave_contract.enabled -ne $null) {
            $waveEnabled = [bool]$GsdOverlayPolicy.wave_contract.enabled
        }
        if ($GsdOverlayPolicy.wave_contract.xl_only -ne $null) {
            $waveXlOnly = [bool]$GsdOverlayPolicy.wave_contract.xl_only
        }
    }

    $waveTaskAllowed = ($TaskType -in @("planning", "coding"))
    $waveGradeAllowed = (($Grade -eq "XL") -or (-not $waveXlOnly))
    $waveApply = ($scopeApplicable -and $waveEnabled -and $waveTaskAllowed -and $waveGradeAllowed)

    $enforcement = "none"
    $reason = "outside_scope"
    if ($scopeApplicable) {
        $confirmGrades = @("XL")
        if ($GsdOverlayPolicy.assumption_gate -and $GsdOverlayPolicy.assumption_gate.confirm_required_for) {
            $confirmGrades = @($GsdOverlayPolicy.assumption_gate.confirm_required_for)
        }

        switch ($mode) {
            "shadow" {
                $enforcement = "advisory"
                $reason = "shadow_advisory"
            }
            "soft" {
                if ($confirmGrades -contains $Grade) {
                    $enforcement = "confirm_required"
                    $reason = "soft_confirm_scope_hit"
                } else {
                    $enforcement = "advisory"
                    $reason = "soft_advisory_outside_confirm_grade"
                }
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
    if ($GsdOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$GsdOverlayPolicy.preserve_routing_assignment
    }

    $brownfieldDirectory = $null
    if ($GsdOverlayPolicy.brownfield_context -and $GsdOverlayPolicy.brownfield_context.directory) {
        $brownfieldDirectory = [string]$GsdOverlayPolicy.brownfield_context.directory
    }

    $assumptionArtifact = if ($GsdOverlayPolicy.assumption_gate -and $GsdOverlayPolicy.assumption_gate.artifact) {
        [string]$GsdOverlayPolicy.assumption_gate.artifact
    } else {
        "assumptions.md"
    }

    $waveArtifact = if ($GsdOverlayPolicy.wave_contract -and $GsdOverlayPolicy.wave_contract.artifact) {
        [string]$GsdOverlayPolicy.wave_contract.artifact
    } else {
        "waves.json"
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
        preflight_should_apply = $preflightApply
        wave_contract_should_apply = $waveApply
        should_apply_hook = ($preflightApply -or $waveApply)
        artifacts = [pscustomobject]@{
            brownfield_directory = $brownfieldDirectory
            assumption_artifact = $assumptionArtifact
            wave_artifact = $waveArtifact
        }
    }
}


