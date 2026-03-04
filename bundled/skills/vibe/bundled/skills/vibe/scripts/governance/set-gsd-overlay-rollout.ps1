param(
    [ValidateSet("off", "shadow", "soft-lxl-planning", "strict-lxl-planning")]
    [string]$Stage = "soft-lxl-planning",
    [switch]$MainOnly,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Load-Overlay {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "GSD overlay config not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Ensure-CommonShape {
    param([object]$Overlay)

    if (-not $Overlay.soft_confirm_scope) {
        $Overlay | Add-Member -NotePropertyName soft_confirm_scope -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    if (-not $Overlay.task_allow) {
        $Overlay | Add-Member -NotePropertyName task_allow -NotePropertyValue @("planning") -Force
    }
    if (-not $Overlay.grade_allow) {
        $Overlay | Add-Member -NotePropertyName grade_allow -NotePropertyValue @("L", "XL") -Force
    }
    if (-not $Overlay.assumption_gate) {
        $Overlay | Add-Member -NotePropertyName assumption_gate -NotePropertyValue ([pscustomobject]@{
            enabled = $true
            confirm_required_for = @("XL")
            artifact = "assumptions.md"
        }) -Force
    }
}

function Apply-Stage {
    param(
        [object]$Overlay,
        [string]$StageName
    )

    Ensure-CommonShape -Overlay $Overlay

    $Overlay.preserve_routing_assignment = $true
    $Overlay.routing_integration = "protocol_hooks_only"
    $Overlay.task_allow = @("planning")
    $Overlay.grade_allow = @("L", "XL")
    $Overlay.soft_confirm_scope.grades = @("L", "XL")
    $Overlay.soft_confirm_scope.task_types = @("planning")

    switch ($StageName) {
        "off" {
            $Overlay.enabled = $false
            $Overlay.mode = "off"
            if ($Overlay.assumption_gate) {
                $Overlay.assumption_gate.confirm_required_for = @()
            }
        }
        "shadow" {
            $Overlay.enabled = $true
            $Overlay.mode = "shadow"
            if ($Overlay.assumption_gate) {
                $Overlay.assumption_gate.confirm_required_for = @("XL")
            }
        }
        "soft-lxl-planning" {
            $Overlay.enabled = $true
            $Overlay.mode = "soft"
            if ($Overlay.assumption_gate) {
                $Overlay.assumption_gate.confirm_required_for = @("XL")
            }
        }
        "strict-lxl-planning" {
            $Overlay.enabled = $true
            $Overlay.mode = "strict"
            if ($Overlay.assumption_gate) {
                $Overlay.assumption_gate.confirm_required_for = @("L", "XL")
            }
        }
        default {
            throw "Unsupported stage: $StageName"
        }
    }

    $Overlay.updated = (Get-Date -Format "yyyy-MM-dd")
}

function Save-Overlay {
    param(
        [string]$Path,
        [object]$Overlay
    )

    $json = $Overlay | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$targets = @(
    (Join-Path $repoRoot "config/gsd-overlay.json")
)
if (-not $MainOnly) {
    $bundledPath = Join-Path $repoRoot "bundled/skills/vibe/config/gsd-overlay.json"
    if (Test-Path -LiteralPath $bundledPath) {
        $targets += $bundledPath
    } else {
        Write-Warning "Bundled mirror not found, applying stage to main config only: $bundledPath"
    }
}

$results = @()
foreach ($path in $targets) {
    $overlay = Load-Overlay -Path $path
    Apply-Stage -Overlay $overlay -StageName $Stage

    if (-not $WhatIf) {
        Save-Overlay -Path $path -Overlay $overlay
    }

    $results += [pscustomobject]@{
        path = $path
        stage = $Stage
        enabled = [bool]$overlay.enabled
        mode = $overlay.mode
        task_allow = $overlay.task_allow
        grade_allow = $overlay.grade_allow
        soft_confirm_scope = $overlay.soft_confirm_scope
        assumption_gate = $overlay.assumption_gate
        updated = $overlay.updated
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
