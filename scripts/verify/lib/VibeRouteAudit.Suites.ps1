Set-StrictMode -Version Latest

function Invoke-VibeRouteNoLocalCandidateAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $workspace = New-VibeRouteAuditWorkspace -RepoRoot $RepoRoot
    try {
        $results = @()
        $cases = Get-VibeRouteReplayCases -RepoRoot $RepoRoot -ExpectedRouteMode "no_local_candidate"

        Write-Host "=== Vibe Routing No-Local-Candidate Audit ==="
        foreach ($case in $cases) {
            $route = Invoke-VibeRouteAudit `
                -RepoRoot $RepoRoot `
                -TargetRoot $workspace.target_root `
                -Prompt ([string]$case.prompt) `
                -Grade ([string]$case.grade) `
                -TaskType ([string]$case.task_type)

            $label = [string]$case.id
            $results += Assert-VibeRouteTrue -Condition ([string]$route.route_mode -eq "no_local_candidate") -Message "[$label] route mode stays no_local_candidate"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.route_reason -eq "no_local_candidate_above_threshold") -Message "[$label] route reason explains the no-match fallback"
            $results += Assert-VibeRouteTrue -Condition ($null -eq $route.candidate_focus) -Message "[$label] selected candidate is empty"
            $results += Assert-VibeRouteTrue -Condition ([double]$route.top1_top2_gap -ge 0) -Message "[$label] top1_top2_gap is non-negative"
            $results += Assert-VibeRouteTrue -Condition (-not ($route.PSObject.Properties.Name -contains "confirm_ui")) -Message "[$label] no confirm_ui is emitted for no-match fallback"
        }

        return New-VibeRouteSuiteSummary -Title "Vibe Routing No-Local-Candidate Audit" -Assertions $results
    } finally {
        Remove-VibeRouteAuditWorkspace -Workspace $workspace
    }
}

function Invoke-VibeRouteLocalOwnerAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $workspace = New-VibeRouteAuditWorkspace -RepoRoot $RepoRoot
    try {
        $results = @()
        $cases = Get-VibeRouteReplayCases -RepoRoot $RepoRoot -ExpectedRouteMode "local_skill_overlay"

        Write-Host "=== Vibe Routing Local-Owner Audit ==="
        foreach ($case in $cases) {
            $route = Invoke-VibeRouteAudit `
                -RepoRoot $RepoRoot `
                -TargetRoot $workspace.target_root `
                -Prompt ([string]$case.prompt) `
                -Grade ([string]$case.grade) `
                -TaskType ([string]$case.task_type)

            $label = [string]$case.id
            $expectedPack = [string]$case.expected.candidate_focus_pack
            $expectedSkill = [string]$case.expected.candidate_focus_skill
            $results += Assert-VibeRouteTrue -Condition ([string]$route.route_mode -eq "local_skill_overlay") -Message "[$label] route mode lands on local_skill_overlay"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.candidate_focus.pack_id -eq $expectedPack) -Message "[$label] selected pack is $expectedPack"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.candidate_focus.skill -eq $expectedSkill) -Message "[$label] selected skill is $expectedSkill"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.candidate_source -eq "local_skill_index") -Message "[$label] candidate source stays local_skill_index"
            $results += Assert-VibeRouteTrue -Condition ([double]$route.top1_top2_gap -ge 0) -Message "[$label] top1_top2_gap is non-negative"
        }

        return New-VibeRouteSuiteSummary -Title "Vibe Routing Local-Owner Audit" -Assertions $results
    } finally {
        Remove-VibeRouteAuditWorkspace -Workspace $workspace
    }
}

function Invoke-VibeRouteRequestedSkillAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $workspace = New-VibeRouteAuditWorkspace -RepoRoot $RepoRoot
    try {
        $results = @()
        Write-Host "=== Vibe Routing Requested-Skill Audit ==="

        $explicitCases = @(
            [pscustomobject]@{
                Name           = "mixed-case requested local skill"
                Prompt         = "请用机器学习专家视角审视这个分类方案"
                Grade          = "L"
                TaskType       = "research"
                RequestedSkill = "Scikit-Learn"
                ExpectedSkill  = "scikit-learn"
            },
            [pscustomobject]@{
                Name           = "vibe request keeps runtime authority while routing specialist"
                Prompt         = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."
                Grade          = "XL"
                TaskType       = "debug"
                RequestedSkill = "vibe"
                ExpectedSkill  = "systematic-debugging"
            }
        )

        foreach ($case in $explicitCases) {
            $route = Invoke-VibeRouteAudit `
                -RepoRoot $RepoRoot `
                -TargetRoot $workspace.target_root `
                -Prompt $case.Prompt `
                -Grade $case.Grade `
                -TaskType $case.TaskType `
                -RequestedSkill $case.RequestedSkill

            $label = [string]$case.Name
            $results += Assert-VibeRouteTrue -Condition ([string]$route.route_mode -eq "local_skill_overlay") -Message "[$label] route mode stays local_skill_overlay"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.candidate_focus.pack_id -eq "local-skill-index") -Message "[$label] selected pack stays local-skill-index"
            $results += Assert-VibeRouteTrue -Condition ([string]$route.candidate_focus.skill -eq [string]$case.ExpectedSkill) -Message "[$label] selected skill is $($case.ExpectedSkill)"
        }

        $missingRequested = Invoke-VibeRouteAudit `
            -RepoRoot $RepoRoot `
            -TargetRoot $workspace.target_root `
            -Prompt "Use manuscript-as-code." `
            -Grade "M" `
            -TaskType "planning" `
            -RequestedSkill "manuscript-as-code"
        $results += Assert-VibeRouteTrue -Condition ($null -eq $missingRequested.selected) -Message "[missing requested skill] selected candidate is empty"
        $results += Assert-VibeRouteTrue -Condition ([string]$missingRequested.route_reason -eq "requested_local_skill_not_found") -Message "[missing requested skill] route reason is requested_local_skill_not_found"
        $results += Assert-VibeRouteTrue -Condition (($missingRequested.rejected_specialist_reasons | ConvertTo-Json -Depth 6) -match "manuscript-as-code") -Message "[missing requested skill] rejected_specialist_reasons mention manuscript-as-code"

        $detA = Invoke-VibeRouteAudit `
            -RepoRoot $RepoRoot `
            -TargetRoot $workspace.target_root `
            -Prompt "Please use scikit-learn to prototype a tabular classification baseline, run feature selection, and compare cross-validation metrics." `
            -Grade "L" `
            -TaskType "coding"
        $detB = Invoke-VibeRouteAudit `
            -RepoRoot $RepoRoot `
            -TargetRoot $workspace.target_root `
            -Prompt "Please use scikit-learn to prototype a tabular classification baseline, run feature selection, and compare cross-validation metrics." `
            -Grade "L" `
            -TaskType "coding"
        $results += Assert-VibeRouteTrue -Condition ([string]$detA.route_mode -eq [string]$detB.route_mode) -Message "[determinism] route mode is stable"
        $results += Assert-VibeRouteTrue -Condition ([string]$detA.selected.skill -eq [string]$detB.selected.skill) -Message "[determinism] selected skill is stable"
        $results += Assert-VibeRouteTrue -Condition ([double]$detA.top1_top2_gap -eq [double]$detB.top1_top2_gap) -Message "[determinism] top1_top2_gap is stable"

        return New-VibeRouteSuiteSummary -Title "Vibe Routing Requested-Skill Audit" -Assertions $results
    } finally {
        Remove-VibeRouteAuditWorkspace -Workspace $workspace
    }
}
