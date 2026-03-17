Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Get-VibeRuntimeContext {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    $governanceContext = Get-VgoGovernanceContext -ScriptPath $ScriptPath -EnforceExecutionContext
    $repoRoot = $governanceContext.repoRoot

    return [pscustomobject]@{
        repo_root = $repoRoot
        governance_context = $governanceContext
        runtime_contract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_modes = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-modes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_input_packet_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        benchmark_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\benchmark-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        cleanup_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        proof_class_registry = Get-Content -LiteralPath (Join-Path $repoRoot 'config\proof-class-registry.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    }
}

function New-VibeRunId {
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $suffix = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "$timestamp-$suffix"
}

function ConvertTo-VibeSlug {
    param(
        [AllowEmptyString()] [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return 'task'
    }

    $normalized = $Text.ToLowerInvariant()
    $normalized = [regex]::Replace($normalized, '[^a-z0-9]+', '-')
    $normalized = $normalized.Trim('-')
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return 'task'
    }

    if ($normalized.Length -gt 64) {
        return $normalized.Substring(0, 64).Trim('-')
    }

    return $normalized
}

function Get-VibeTitleFromTask {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $flat = ($Task -replace '\s+', ' ').Trim()
    if ($flat.Length -le 80) {
        return $flat
    }

    return ($flat.Substring(0, 80).Trim() + '...')
}

function Get-VibeArtifactRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        return [System.IO.Path]::GetFullPath($RepoRoot)
    }

    if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) {
        return [System.IO.Path]::GetFullPath($ArtifactRoot)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $ArtifactRoot))
}

function Get-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("outputs\runtime\vibe-sessions\{0}" -f $RunId)))
}

function Ensure-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null
    return $sessionRoot
}

function Write-VibeJsonArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 20
    Write-VgoUtf8NoBomText -Path $Path -Content $json
}

function Write-VibeMarkdownArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [AllowEmptyString()] [string[]]$Lines
    )

    Write-VgoUtf8NoBomText -Path $Path -Content (($Lines -join [Environment]::NewLine) + [Environment]::NewLine)
}

function Get-VibeInternalGrade {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $taskLower = $Task.ToLowerInvariant()
    $xlPatterns = @('xl', 'multi-agent', 'parallel', 'wave', 'batch', '无人值守', 'autonomous', 'benchmark', 'front.*back', 'end-to-end')
    $lPatterns = @('design', 'plan', 'architecture', 'refactor', 'migrate', 'research', 'governance', '访谈', '规划', '设计', '治理')

    foreach ($pattern in $xlPatterns) {
        if ($taskLower -match $pattern) {
            return 'XL'
        }
    }

    foreach ($pattern in $lPatterns) {
        if ($taskLower -match $pattern) {
            return 'L'
        }
    }

    if ($Task.Length -gt 180) {
        return 'L'
    }

    return 'M'
}

function New-VibeIntentContractObject {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Mode
    )

    $title = Get-VibeTitleFromTask -Task $Task
    $grade = Get-VibeInternalGrade -Task $Task
    $assumptions = @()
    if ($Mode -eq 'benchmark_autonomous') {
        $assumptions += 'Proceed without additional user questioning unless a hard blocker or safety boundary is reached.'
        $assumptions += 'Freeze inferred acceptance criteria into the requirement document before execution.'
    } else {
        $assumptions += 'Interactive clarification is allowed if unresolved ambiguity materially changes implementation.'
    }

    return [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        title = $title
        goal = $title
        deliverable = 'Governed implementation artifacts, verification evidence, and cleanup receipts'
        constraints = @(
            'Do not bypass the fixed six-stage governed runtime.',
            'Do not widen scope silently beyond the frozen requirement document.'
        )
        acceptance_criteria = @(
            'Requirement document is frozen before execution.',
            'Execution plan exists before implementation.',
            'Verification evidence exists before completion claims.',
            'Phase cleanup receipt is produced.'
        )
        non_goals = @(
            'Do not treat M/L/XL as user-facing entry branches.',
            'Do not introduce a second router or control plane.'
        )
        risk_tolerance = 'moderate'
        autonomy_mode = $Mode
        open_questions = @()
        inference_notes = @(
            'This contract was derived from the raw task text.',
            'Interactive mode may still surface explicit clarification questions outside the script path.'
        )
        assumptions = @($assumptions)
        internal_grade = $grade
        source_task = $Task
    }
}

function Get-VibeRequirementDocPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\requirements\{0}-{1}.md" -f $date, $slug)))
}

function Get-VibeExecutionPlanPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\plans\{0}-{1}-execution-plan.md" -f $date, $slug)))
}

function Get-VibeRuntimeInputPacketPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $sessionRoot 'runtime-input-packet.json'))
}
