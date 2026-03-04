param()

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$governanceScript = Join-Path $repoRoot "scripts\governance\invoke-openspec-governance.ps1"
$policyPath = Join-Path $repoRoot "config\openspec-policy.json"

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

function Ensure-Property {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Value
    )

    if ($null -eq $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
    }
}

function Write-Utf8NoBomText {
    param(
        [string]$Path,
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill
    )

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

$cases = @(
    [pscustomobject]@{
        Name = "L planning orchestration"
        Prompt = "create implementation plan and task breakdown with milestones"
        Grade = "L"
        TaskType = "planning"
        RequestedSkill = $null
        ExpectedPack = "orchestration-core"
        ExpectedProfile = "full"
        ExpectedEnforcement = "required"
    },
    [pscustomobject]@{
        Name = "L planning aios-core"
        Prompt = "create PRD and user story backlog with quality gate"
        Grade = "L"
        TaskType = "planning"
        RequestedSkill = $null
        ExpectedPack = "aios-core"
        ExpectedProfile = "full"
        ExpectedEnforcement = "required"
    },
    [pscustomobject]@{
        Name = "XL planning confirm scope"
        Prompt = "plan a multi-agent refactor for data layer and integration boundaries"
        Grade = "XL"
        TaskType = "planning"
        RequestedSkill = $null
        ExpectedPack = $null
        ExpectedProfile = "full"
        ExpectedEnforcement = "required"
    },
    [pscustomobject]@{
        Name = "L non-planning outside scope"
        Prompt = "investigate recent OpenAI model release notes and summarize findings"
        Grade = "L"
        TaskType = "research"
        RequestedSkill = $null
        ExpectedPack = $null
        ExpectedProfile = "full"
        ExpectedEnforcement = "none"
    },
    [pscustomobject]@{
        Name = "M planning governance-first"
        Prompt = "small module implementation plan without architecture change"
        Grade = "M"
        TaskType = "planning"
        RequestedSkill = $null
        ExpectedPack = "orchestration-core"
        ExpectedProfile = "full"
        ExpectedEnforcement = "required"
    },
    [pscustomobject]@{
        Name = "Requested skill outside whitelist"
        Prompt = "run code review and security scan"
        Grade = "M"
        TaskType = "review"
        RequestedSkill = "code-review"
        ExpectedPack = "code-quality"
        ExpectedProfile = "full"
        ExpectedEnforcement = "none"
        ExpectedBypass = $false
        ExpectedReason = "task_not_applicable"
    },
    [pscustomobject]@{
        Name = "Requested skill whitelist bypass"
        Prompt = "plan implementation milestones for module refactor"
        Grade = "M"
        TaskType = "planning"
        RequestedSkill = "writing-plans"
        ExpectedPack = "orchestration-core"
        ExpectedProfile = "full"
        ExpectedEnforcement = "none"
        ExpectedBypass = $true
        ExpectedReasonPattern = "requested_skill_bypass*"
    }
)

$results = @()

Write-Host "=== VCO OpenSpec Governance Gate ==="

$policyBytesBackup = [System.IO.File]::ReadAllBytes($policyPath)
$policyRawBackup = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
try {
    $policyObj = $policyRawBackup | ConvertFrom-Json

    Ensure-Property -Object $policyObj -Name "profile_by_grade" -Value ([pscustomobject]@{})
    Ensure-Property -Object $policyObj -Name "required_task_types_by_profile" -Value ([pscustomobject]@{})
    Ensure-Property -Object $policyObj -Name "exemptions" -Value ([pscustomobject]@{})
    Ensure-Property -Object $policyObj -Name "soft_confirm_scope" -Value ([pscustomobject]@{})
    Ensure-Property -Object $policyObj.exemptions -Name "requested_skill_bypass" -Value $false
    Ensure-Property -Object $policyObj.exemptions -Name "requested_skill_whitelist" -Value @()

    $policyObj.mode = "strict"
    $policyObj.preserve_routing_assignment = $true
    $policyObj.profile_by_grade.M = "full"
    $policyObj.profile_by_grade.L = "full"
    $policyObj.profile_by_grade.XL = "full"
    $policyObj.required_task_types_by_profile.full = @("planning")
    $policyObj.exemptions.requested_skill_bypass = $true
    $policyObj.exemptions.requested_skill_whitelist = @("sc:design", "brainstorming", "writing-plans")

    Write-Utf8NoBomText -Path $policyPath -Content ($policyObj | ConvertTo-Json -Depth 30)

    foreach ($case in $cases) {
        $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType -RequestedSkill $case.RequestedSkill

        $results += Assert-True -Condition ($null -ne $route.selected) -Message "[$($case.Name)] selected route exists"
        if ($case.ExpectedPack) {
            $results += Assert-True -Condition ($route.selected.pack_id -eq $case.ExpectedPack) -Message "[$($case.Name)] selected pack unchanged ($($case.ExpectedPack))"
        }
        $results += Assert-True -Condition ($null -ne $route.openspec_advice) -Message "[$($case.Name)] openspec_advice exists"
        $results += Assert-True -Condition ($route.openspec_advice.enabled -eq $true) -Message "[$($case.Name)] openspec advice enabled"
        $results += Assert-True -Condition ($route.openspec_advice.profile -eq $case.ExpectedProfile) -Message "[$($case.Name)] profile is $($case.ExpectedProfile)"
        $results += Assert-True -Condition ($route.openspec_advice.enforcement -eq $case.ExpectedEnforcement) -Message "[$($case.Name)] enforcement is $($case.ExpectedEnforcement)"
        if ($null -ne $case.PSObject.Properties["ExpectedBypass"]) {
            $results += Assert-True -Condition ($route.openspec_advice.bypass_due_to_requested_skill -eq $case.ExpectedBypass) -Message "[$($case.Name)] bypass_due_to_requested_skill is $($case.ExpectedBypass)"
        }
        if ($null -ne $case.PSObject.Properties["ExpectedReason"]) {
            $results += Assert-True -Condition ($route.openspec_advice.reason -eq $case.ExpectedReason) -Message "[$($case.Name)] reason is $($case.ExpectedReason)"
        }
        if ($null -ne $case.PSObject.Properties["ExpectedReasonPattern"]) {
            $results += Assert-True -Condition ($route.openspec_advice.reason -like $case.ExpectedReasonPattern) -Message "[$($case.Name)] reason matches $($case.ExpectedReasonPattern)"
        }
        $results += Assert-True -Condition ($route.openspec_advice.preserve_routing_assignment -eq $true) -Message "[$($case.Name)] preserve routing assignment"
    }

    $governance = & $governanceScript `
        -Prompt "small module implementation plan without architecture change" `
        -Grade "M" `
        -TaskType "planning" `
        -NoAutoCreateLite
    $governanceObj = $governance | ConvertFrom-Json
    $results += Assert-True -Condition ($governanceObj.status -in @("full_ready", "full_missing")) -Message "[governance script] full profile handling status"
    $results += Assert-True -Condition ($governanceObj.selected_pack -eq "orchestration-core") -Message "[governance script] selected pack preserved"

    $strictTaskId = "governance-gate-{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 12))
    $strictGovernance = & $governanceScript `
        -Prompt "plan governance-first changes with architecture constraints" `
        -Grade "M" `
        -TaskType "planning" `
        -TaskId $strictTaskId `
        -NoAutoCreateLite
    $strictObj = $strictGovernance | ConvertFrom-Json

    $results += Assert-True -Condition ($strictObj.status -eq "full_missing") -Message "[strict missing] full skeleton missing status"
    $results += Assert-True -Condition ($strictObj.enforcement -eq "required") -Message "[strict missing] enforcement is required"
    $results += Assert-True -Condition ($strictObj.enforced -eq $true) -Message "[strict missing] governance blocks execution"
    $results += Assert-True -Condition ($strictObj.required_action -eq "rerun_with_WriteArtifacts_to_create_full_spec_change") -Message "[strict missing] required action is rerun_with_WriteArtifacts_to_create_full_spec_change"
} finally {
    [System.IO.File]::WriteAllBytes($policyPath, $policyBytesBackup)
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

Write-Host "OpenSpec governance gate passed."
exit 0
