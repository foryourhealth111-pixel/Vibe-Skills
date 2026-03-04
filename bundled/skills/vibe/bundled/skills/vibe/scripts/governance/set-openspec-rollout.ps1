param(
    [ValidateSet("off", "shadow", "soft-lxl-planning", "strict-lxl-planning")]
    [string]$Stage = "soft-lxl-planning",
    [switch]$MainOnly,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Load-Policy {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "OpenSpec policy not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Ensure-CommonShape {
    param([object]$Policy)

    if (-not $Policy.profile_by_grade) {
        $Policy | Add-Member -NotePropertyName profile_by_grade -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    if (-not $Policy.required_task_types_by_profile) {
        $Policy | Add-Member -NotePropertyName required_task_types_by_profile -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    if (-not $Policy.soft_confirm_scope) {
        $Policy | Add-Member -NotePropertyName soft_confirm_scope -NotePropertyValue ([pscustomobject]@{}) -Force
    }
}

function Apply-Stage {
    param(
        [object]$Policy,
        [string]$StageName
    )

    Ensure-CommonShape -Policy $Policy

    $Policy.preserve_routing_assignment = $true
    $Policy.routing_integration = "post_route_governance_only"
    $Policy.profile_by_grade.M = "lite"
    $Policy.profile_by_grade.L = "full"
    $Policy.profile_by_grade.XL = "full"
    $Policy.required_task_types_by_profile.full = @("planning")
    $Policy.soft_confirm_scope.grades = @("L", "XL")
    $Policy.soft_confirm_scope.task_types = @("planning")

    switch ($StageName) {
        "off" {
            $Policy.mode = "off"
        }
        "shadow" {
            $Policy.mode = "shadow"
        }
        "soft-lxl-planning" {
            $Policy.mode = "soft"
        }
        "strict-lxl-planning" {
            $Policy.mode = "strict"
        }
        default {
            throw "Unsupported stage: $StageName"
        }
    }

    $Policy.updated = (Get-Date -Format "yyyy-MM-dd")
}

function Save-Policy {
    param(
        [string]$Path,
        [object]$Policy
    )

    $json = $Policy | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$targets = @(
    (Join-Path $repoRoot "config/openspec-policy.json")
)
if (-not $MainOnly) {
    $targets += (Join-Path $repoRoot "bundled/skills/vibe/config/openspec-policy.json")
}

$results = @()
foreach ($path in $targets) {
    $policy = Load-Policy -Path $path
    Apply-Stage -Policy $policy -StageName $Stage

    if (-not $WhatIf) {
        Save-Policy -Path $path -Policy $policy
    }

    $results += [pscustomobject]@{
        path = $path
        stage = $Stage
        mode = $policy.mode
        profile_by_grade = $policy.profile_by_grade
        required_task_types_by_profile = $policy.required_task_types_by_profile
        soft_confirm_scope = $policy.soft_confirm_scope
        preserve_routing_assignment = $policy.preserve_routing_assignment
        updated = $policy.updated
        wrote = (-not $WhatIf)
    }
}

[pscustomobject]@{
    ok = $true
    stage = $Stage
    main_only = [bool]$MainOnly
    what_if = [bool]$WhatIf
    results = $results
} | ConvertTo-Json -Depth 20
