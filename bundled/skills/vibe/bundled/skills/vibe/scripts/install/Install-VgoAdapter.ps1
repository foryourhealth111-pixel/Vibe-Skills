param(
    [Parameter(Mandatory)] [string]$RepoRoot,
    [Parameter(Mandatory)] [string]$TargetRoot,
    [Parameter(Mandatory)] [string]$HostId,
    [ValidateSet('minimal', 'full')] [string]$Profile = 'full',
    [switch]$AllowExternalSkillFallback
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')
. (Join-Path $RepoRoot 'scripts\common\Resolve-VgoAdapter.ps1')

function Copy-DirContent {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) { return }
    $sourceFull = [System.IO.Path]::GetFullPath($Source)
    $destinationFull = [System.IO.Path]::GetFullPath($Destination)
    if ($sourceFull -eq $destinationFull) {
        return
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

function Ensure-SkillPresent {
    param(
        [string]$Name,
        [bool]$Required,
        [string[]]$FallbackSources = @(),
        [System.Collections.Generic.List[string]]$ExternalFallbackUsed,
        [System.Collections.Generic.List[string]]$MissingRequiredSkills
    )

    $targetSkillMd = Join-Path $TargetRoot ("skills\" + $Name + "\SKILL.md")
    if (Test-Path -LiteralPath $targetSkillMd) { return }
    if ($AllowExternalSkillFallback) {
        foreach ($src in $FallbackSources) {
            if ([string]::IsNullOrWhiteSpace($src)) { continue }
            if (Test-Path -LiteralPath $src) {
                Copy-DirContent -Source $src -Destination (Join-Path $TargetRoot ("skills\" + $Name))
                $ExternalFallbackUsed.Add($Name) | Out-Null
                break
            }
        }
    }
    if (-not (Test-Path -LiteralPath $targetSkillMd)) {
        if ($Required) {
            $MissingRequiredSkills.Add($Name) | Out-Null
        }
    }
}

function Sync-VibeCanonicalToTarget {
    param(
        [string]$RepoRoot,
        [string]$TargetRoot,
        [string]$TargetRel = 'skills\vibe'
    )

    $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
    if (-not (Test-Path -LiteralPath $governancePath)) {
        throw "version-governance config not found: $governancePath"
    }
    $governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $canonicalRoot = Join-Path $RepoRoot ([string]$governance.source_of_truth.canonical_root)
    $mirrorFiles = @($governance.packaging.mirror.files)
    $mirrorDirs = @($governance.packaging.mirror.directories)
    $targetVibeRoot = Join-Path $TargetRoot $TargetRel

    foreach ($rel in $mirrorFiles) {
        $src = Join-Path $canonicalRoot $rel
        $dst = Join-Path $targetVibeRoot $rel
        if (-not (Test-Path -LiteralPath $src)) { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
    foreach ($dir in $mirrorDirs) {
        $srcDir = Join-Path $canonicalRoot $dir
        $dstDir = Join-Path $targetVibeRoot $dir
        if (-not (Test-Path -LiteralPath $srcDir)) { continue }
        if (Test-Path -LiteralPath $dstDir) {
            Remove-Item -LiteralPath $dstDir -Recurse -Force
        }
        Copy-DirContent -Source $srcDir -Destination $dstDir
    }
}

function Install-RuntimeCorePayload {
    param([psobject]$Adapter)

    $packagingPath = Join-Path $RepoRoot 'config\runtime-core-packaging.json'
    $packaging = Get-Content -LiteralPath $packagingPath -Raw -Encoding UTF8 | ConvertFrom-Json

    foreach ($dir in @($packaging.directories)) {
        New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot ([string]$dir)) | Out-Null
    }

    foreach ($entry in @($packaging.copy_directories)) {
        $src = Join-Path $RepoRoot ([string]$entry.source)
        $dst = Join-Path $TargetRoot ([string]$entry.target)
        Copy-DirContent -Source $src -Destination $dst
    }

    foreach ($entry in @($packaging.copy_files)) {
        $src = Join-Path $RepoRoot ([string]$entry.source)
        $dst = Join-Path $TargetRoot ([string]$entry.target)
        $optional = $false
        if ($entry.PSObject.Properties.Name -contains 'optional') {
            $optional = [bool]$entry.optional
        }
        if (-not (Test-Path -LiteralPath $src)) {
            if ($optional) { continue }
            throw "Runtime-core packaging source missing: $src"
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }

    $targetVibeRel = 'skills\vibe'
    if ($packaging.PSObject.Properties.Name -contains 'canonical_vibe_mirror' -and $null -ne $packaging.canonical_vibe_mirror) {
        if ($packaging.canonical_vibe_mirror.PSObject.Properties.Name -contains 'target_relpath' -and -not [string]::IsNullOrWhiteSpace([string]$packaging.canonical_vibe_mirror.target_relpath)) {
            $targetVibeRel = [string]$packaging.canonical_vibe_mirror.target_relpath
        }
    }

    Sync-VibeCanonicalToTarget -RepoRoot $RepoRoot -TargetRoot $TargetRoot -TargetRel $targetVibeRel

    $canonicalSkillsRoot = Get-VgoParentPath -Path $RepoRoot
    $workspaceRoot = Get-VgoParentPath -Path $canonicalSkillsRoot
    $workspaceSkillsRoot = if (-not [string]::IsNullOrWhiteSpace($workspaceRoot)) { Join-Path $workspaceRoot 'skills' } else { '' }
    $workspaceSuperpowersRoot = if (-not [string]::IsNullOrWhiteSpace($workspaceRoot)) { Join-Path $workspaceRoot 'superpowers\skills' } else { '' }
    $bundledSuperpowersRoot = Join-Path $RepoRoot 'bundled\superpowers-skills'

    function New-SkillFallbackSources {
        param(
            [Parameter(Mandatory)] [string]$Name,
            [string[]]$Roots
        )

        $sources = New-Object System.Collections.Generic.List[string]
        foreach ($root in $Roots) {
            if ([string]::IsNullOrWhiteSpace($root)) { continue }
            if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
            $candidate = Join-Path $root $Name
            if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                $sources.Add($candidate) | Out-Null
            }
        }
        return @($sources | Select-Object -Unique)
    }

    $requiredCore = @('dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')
    $requiredWorkflow = @('brainstorming', 'writing-plans', 'subagent-driven-development', 'systematic-debugging')
    $optionalWorkflow = @('requesting-code-review', 'receiving-code-review', 'verification-before-completion')

    $externalFallbackUsed = New-Object System.Collections.Generic.List[string]
    $missingRequiredSkills = New-Object System.Collections.Generic.List[string]

    foreach ($name in $requiredCore) {
        Ensure-SkillPresent -Name $name -Required $true -FallbackSources @(
            (New-SkillFallbackSources -Name $name -Roots @($canonicalSkillsRoot, $workspaceSkillsRoot, $workspaceSuperpowersRoot, $bundledSuperpowersRoot))
        ) -ExternalFallbackUsed $externalFallbackUsed -MissingRequiredSkills $missingRequiredSkills
    }

    foreach ($name in $requiredWorkflow) {
        Ensure-SkillPresent -Name $name -Required $true -FallbackSources @(
            (New-SkillFallbackSources -Name $name -Roots @($workspaceSkillsRoot, $workspaceSuperpowersRoot, $bundledSuperpowersRoot, $canonicalSkillsRoot))
        ) -ExternalFallbackUsed $externalFallbackUsed -MissingRequiredSkills $missingRequiredSkills
    }

    if ($Profile -eq 'full') {
        foreach ($name in $optionalWorkflow) {
            Ensure-SkillPresent -Name $name -Required $false -FallbackSources @(
                (New-SkillFallbackSources -Name $name -Roots @($workspaceSkillsRoot, $workspaceSuperpowersRoot, $bundledSuperpowersRoot, $canonicalSkillsRoot))
            ) -ExternalFallbackUsed $externalFallbackUsed -MissingRequiredSkills $missingRequiredSkills
        }
    }

    if ($missingRequiredSkills.Count -gt 0) {
        $missing = ($missingRequiredSkills | Select-Object -Unique) -join ', '
        throw "Missing required vendored skills: $missing"
    }

    return [pscustomobject]@{
        mode = [string]$Adapter.install_mode
        external_fallback_used = @($externalFallbackUsed | Select-Object -Unique)
    }
}

function Install-GovernedCodexPayload {
    Copy-DirContent -Source (Join-Path $RepoRoot 'rules') -Destination (Join-Path $TargetRoot 'rules')
    Copy-DirContent -Source (Join-Path $RepoRoot 'agents\templates') -Destination (Join-Path $TargetRoot 'agents\templates')
    Copy-DirContent -Source (Join-Path $RepoRoot 'mcp') -Destination (Join-Path $TargetRoot 'mcp')
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot 'config') | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\plugins-manifest.codex.json') -Destination (Join-Path $TargetRoot 'config\plugins-manifest.codex.json') -Force

    $settingsPath = Join-Path $TargetRoot 'settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\settings.template.codex.json') -Destination $settingsPath -Force
    }
}

function Install-ClaudeGuidancePayload {
    return
}

function Install-RuntimeCoreModePayload {
    $commandsRoot = Join-Path $RepoRoot 'commands'
    if (Test-Path -LiteralPath $commandsRoot) {
        Copy-DirContent -Source $commandsRoot -Destination (Join-Path $TargetRoot 'global_workflows')
    }

    $mcpTemplate = Join-Path $RepoRoot 'mcp\servers.template.json'
    $mcpConfigPath = Join-Path $TargetRoot 'mcp_config.json'
    if ((Test-Path -LiteralPath $mcpTemplate) -and -not (Test-Path -LiteralPath $mcpConfigPath)) {
        Copy-Item -LiteralPath $mcpTemplate -Destination $mcpConfigPath -Force
    }
}

$adapter = Resolve-VgoAdapterDescriptor -RepoRoot $RepoRoot -HostId $HostId
$result = Install-RuntimeCorePayload -Adapter $adapter
switch ([string]$adapter.install_mode) {
    'governed' { Install-GovernedCodexPayload }
    'preview-guidance' { Install-ClaudeGuidancePayload }
    'runtime-core' {
        Install-RuntimeCoreModePayload
    }
    default { throw "Unsupported adapter install mode: $($adapter.install_mode)" }
}

[pscustomobject]@{
    host_id = [string]$adapter.id
    install_mode = [string]$adapter.install_mode
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    external_fallback_used = @($result.external_fallback_used)
} | ConvertTo-Json -Depth 10
