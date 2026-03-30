param(
    [Parameter(Mandatory)] [string]$RepoRoot,
    [Parameter(Mandatory)] [string]$TargetRoot,
    [Parameter(Mandatory)] [string]$HostId,
    [ValidateSet('minimal', 'full')] [string]$Profile = 'full',
    [switch]$RequireClosedReady,
    [switch]$AllowExternalSkillFallback
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')
. (Join-Path $RepoRoot 'scripts\common\Resolve-VgoAdapter.ps1')

function Get-VgoPreferredPythonCommand {
    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return [string]$command.Source
        }
    }
    return $null
}

$pythonInstaller = Join-Path $RepoRoot 'scripts\install\install_vgo_adapter.py'
$pythonCommand = Get-VgoPreferredPythonCommand
if ((Test-Path -LiteralPath $pythonInstaller) -and -not [string]::IsNullOrWhiteSpace($pythonCommand)) {
    $cmd = @($pythonCommand)
    if ([System.IO.Path]::GetFileName($pythonCommand).ToLowerInvariant() -eq 'py') {
        $cmd += '-3'
    }
    $cmd += @(
        $pythonInstaller,
        '--repo-root', $RepoRoot,
        '--target-root', $TargetRoot,
        '--host', $HostId,
        '--profile', $Profile
    )
    if ($RequireClosedReady) {
        $cmd += '--require-closed-ready'
    }
    if ($AllowExternalSkillFallback) {
        $cmd += '--allow-external-skill-fallback'
    }
    & $cmd[0] @($cmd[1..($cmd.Count - 1)])
    if ($LASTEXITCODE -ne 0) {
        throw ("Python adapter installer failed with exit code {0}." -f $LASTEXITCODE)
    }
    return
}

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

function Restore-SkillEntryPointIfNeeded {
    param([string]$SkillRoot)

    $skillMd = Join-Path $SkillRoot 'SKILL.md'
    $mirrorPath = Join-Path $SkillRoot 'SKILL.runtime-mirror.md'
    if ((Test-Path -LiteralPath $skillMd -PathType Leaf) -or -not (Test-Path -LiteralPath $mirrorPath -PathType Leaf)) {
        return
    }

    Move-Item -LiteralPath $mirrorPath -Destination $skillMd -Force
}

function Get-VgoPlatformTag {
    if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        return 'windows'
    }
    if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::OSX)) {
        return 'macos'
    }
    return 'linux'
}

function Merge-JsonObject {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [hashtable]$Patch
    )

    $existing = @{}
    if (Test-Path -LiteralPath $Path) {
        try {
            $parsed = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
            if ($null -ne $parsed) {
                $existing = $parsed
            }
        } catch {
            $existing = @{}
        }
    }

    $merged = @{}
    foreach ($key in $existing.Keys) {
        $merged[$key] = $existing[$key]
    }
    foreach ($key in $Patch.Keys) {
        $value = $Patch[$key]
        if ($merged.ContainsKey($key) -and $merged[$key] -is [hashtable] -and $value -is [hashtable]) {
            $next = @{}
            foreach ($nestedKey in $merged[$key].Keys) {
                $next[$nestedKey] = $merged[$key][$nestedKey]
            }
            foreach ($nestedKey in $value.Keys) {
                $next[$nestedKey] = $value[$nestedKey]
            }
            $merged[$key] = $next
        } else {
            $merged[$key] = $value
        }
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    $merged | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Test-VgoPathInsideTargetRoot {
    param(
        [object]$Value,
        [string]$TargetRoot
    )

    if ($Value -isnot [string] -or [string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    try {
        $candidatePath = if ([System.IO.Path]::IsPathRooted($Value)) {
            [System.IO.Path]::GetFullPath($Value)
        } else {
            [System.IO.Path]::GetFullPath((Join-Path $TargetRoot $Value))
        }
        $rootPath = [System.IO.Path]::GetFullPath($TargetRoot)
        $relative = [System.IO.Path]::GetRelativePath($rootPath, $candidatePath)
        if ([string]::IsNullOrWhiteSpace($relative) -or $relative -eq '.') {
            return $true
        }
        return -not ($relative -eq '..' -or $relative.StartsWith("..$([System.IO.Path]::DirectorySeparatorChar)"))
    } catch {
        return $false
    }
}

function Test-VgoOwnedLegacyOpenCodeNode {
    param(
        [object]$Node,
        [string]$TargetRoot
    )

    if ($Node -isnot [System.Collections.IDictionary]) {
        return $false
    }

    $hostId = [string]$Node['host_id']
    if (-not [string]::IsNullOrWhiteSpace($hostId) -and $hostId.ToLowerInvariant() -ne 'opencode') {
        return $false
    }
    if ([bool]$Node['managed']) {
        return $true
    }

    foreach ($key in @('commands_root', 'command_root_compat', 'agents_root', 'agent_root_compat', 'specialist_wrapper')) {
        if (Test-VgoPathInsideTargetRoot -Value $Node[$key] -TargetRoot $TargetRoot) {
            return $true
        }
    }

    return $false
}

function Repair-VgoLegacyOpenCodeConfig {
    param([string]$TargetRoot)

    $settingsPath = Join-Path $TargetRoot 'opencode.json'
    $receipt = [ordered]@{
        path = [System.IO.Path]::GetFullPath($settingsPath)
        status = 'not-present'
    }
    if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) {
        return [pscustomobject]$receipt
    }

    try {
        $payload = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    } catch {
        $receipt.status = 'parse-failed'
        return [pscustomobject]$receipt
    }

    if ($payload -isnot [System.Collections.IDictionary]) {
        $receipt.status = 'non-object'
        return [pscustomobject]$receipt
    }

    if (-not $payload.ContainsKey('vibeskills')) {
        $receipt.status = 'already-clean'
        return [pscustomobject]$receipt
    }

    $node = $payload['vibeskills']
    if (-not (Test-VgoOwnedLegacyOpenCodeNode -Node $node -TargetRoot $TargetRoot)) {
        $receipt.status = 'foreign-node-preserved'
        return [pscustomobject]$receipt
    }

    $nextPayload = [ordered]@{}
    foreach ($key in $payload.Keys) {
        if ($key -ne 'vibeskills') {
            $nextPayload[$key] = $payload[$key]
        }
    }

    if ($nextPayload.Count -eq 0) {
        Remove-Item -LiteralPath $settingsPath -Force
        $receipt.status = 'removed-owned-node-and-deleted-empty-file'
        return [pscustomobject]$receipt
    }

    $nextPayload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
    $receipt.status = 'removed-owned-node'
    $receipt.preserved_keys = @($nextPayload.Keys | Sort-Object)
    return [pscustomobject]$receipt
}

function Get-VgoHostBridgeCommandEnvName {
    param([string]$HostId)

    switch ([string]$HostId) {
        'claude-code' { return 'VGO_CLAUDE_CODE_SPECIALIST_BRIDGE_COMMAND' }
        'cursor' { return 'VGO_CURSOR_SPECIALIST_BRIDGE_COMMAND' }
        'windsurf' { return 'VGO_WINDSURF_SPECIALIST_BRIDGE_COMMAND' }
        'openclaw' { return 'VGO_OPENCLAW_SPECIALIST_BRIDGE_COMMAND' }
        'opencode' { return 'VGO_OPENCODE_SPECIALIST_BRIDGE_COMMAND' }
        default { return $null }
    }
}

function Resolve-VgoHostBridgeCommand {
    param([string]$HostId)

    $envName = Get-VgoHostBridgeCommandEnvName -HostId $HostId
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $envValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            $command = Get-Command $envValue -ErrorAction SilentlyContinue
            if ($null -ne $command) {
                return [pscustomobject]@{
                    command = [string]$command.Source
                    source = "env:$envName"
                    env_name = $envName
                }
            }
            if (Test-Path -LiteralPath $envValue) {
                return [pscustomobject]@{
                    command = [System.IO.Path]::GetFullPath($envValue)
                    source = "env:$envName"
                    env_name = $envName
                }
            }
        }
    }

    $candidates = switch ([string]$HostId) {
        'claude-code' { @('claude', 'claude-code') }
        'cursor' { @('cursor-agent', 'cursor') }
        'windsurf' { @('windsurf', 'codeium') }
        'openclaw' { @('openclaw') }
        'opencode' { @('opencode') }
        default { @() }
    }
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return [pscustomobject]@{
                command = [string]$command.Source
                source = "path:$candidate"
                env_name = $envName
            }
        }
    }

    return [pscustomobject]@{
        command = $null
        source = $null
        env_name = $envName
    }
}

function New-VgoHostSpecialistWrapper {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$HostId,
        [string]$BridgeCommand,
        [string]$BridgeEnvName
    )

    $toolsRoot = Join-Path $TargetRoot '.vibeskills\bin'
    New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null

    $wrapperPy = Join-Path $toolsRoot ("{0}-specialist-wrapper.py" -f $HostId)
    $embeddedCommand = if ([string]::IsNullOrWhiteSpace($BridgeCommand)) { '' } else { $BridgeCommand }
    $pythonScript = @"
#!/usr/bin/env python3
import os
import subprocess
import sys

HOST_ID = $(ConvertTo-Json $HostId -Compress)
TARGET_COMMAND = $(ConvertTo-Json $embeddedCommand -Compress)
BRIDGE_ENV_NAME = $(ConvertTo-Json $BridgeEnvName -Compress)

def main() -> int:
    command = TARGET_COMMAND or os.environ.get(BRIDGE_ENV_NAME or "", "").strip()
    if not command:
        sys.stderr.write(f"host specialist bridge command unavailable for {HOST_ID}\n")
        return 3
    return subprocess.run([command, *sys.argv[1:]], check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())
"@
    Set-Content -LiteralPath $wrapperPy -Value $pythonScript -Encoding UTF8

    $platformTag = Get-VgoPlatformTag
    if ($platformTag -eq 'windows') {
        $launcherPath = Join-Path $toolsRoot ("{0}-specialist-wrapper.cmd" -f $HostId)
        $cmdScript = @"
@echo off
setlocal
set SCRIPT_DIR=%~dp0
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  set PY_CMD=%LocalAppData%\Programs\Python\Python311\python.exe
) else if exist "%ProgramFiles%\Python311\python.exe" (
  set PY_CMD=%ProgramFiles%\Python311\python.exe
) else (
  set PY_CMD=py -3
)
%PY_CMD% "%SCRIPT_DIR%$(Split-Path -Leaf $wrapperPy)" %*
"@
        Set-Content -LiteralPath $launcherPath -Value $cmdScript -Encoding ASCII
    } else {
        $launcherPath = Join-Path $toolsRoot ("{0}-specialist-wrapper.sh" -f $HostId)
        $shScript = @'
#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo 'python runtime unavailable for host specialist wrapper' >&2
  exit 127
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/__WRAPPER_FILE__" "$@"
'@
        $shScript = $shScript.Replace('__WRAPPER_FILE__', (Split-Path -Leaf $wrapperPy))
        Set-Content -LiteralPath $launcherPath -Value $shScript -Encoding UTF8
        try {
            chmod +x $launcherPath
            chmod +x $wrapperPy
        } catch {
        }
    }

    return [pscustomobject]@{
        platform = $platformTag
        launcher_path = [System.IO.Path]::GetFullPath($launcherPath)
        script_path = [System.IO.Path]::GetFullPath($wrapperPy)
        ready = -not [string]::IsNullOrWhiteSpace($BridgeCommand)
        bridge_command = $BridgeCommand
    }
}

function Set-VgoManagedHostSettings {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$HostId,
        [Parameter(Mandatory)] [pscustomobject]$WrapperInfo
    )

    $materialized = New-Object System.Collections.Generic.List[string]
    if ($HostId -in @('cursor', 'claude-code')) {
        $settingsPath = Join-Path $TargetRoot 'settings.json'
        Merge-JsonObject -Path $settingsPath -Patch @{
            vibeskills = @{
                host_id = $HostId
                managed = $true
                commands_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'commands'))
                specialist_wrapper = [string]$WrapperInfo.launcher_path
            }
        }
        $materialized.Add([System.IO.Path]::GetFullPath($settingsPath)) | Out-Null
    } elseif ($HostId -in @('openclaw', 'windsurf')) {
        $settingsPath = Join-Path $TargetRoot '.vibeskills\host-settings.json'
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $settingsPath) | Out-Null
        @{
            host_id = $HostId
            managed = $true
            commands_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'commands'))
            workflow_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'global_workflows'))
            mcp_config = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'mcp_config.json'))
            specialist_wrapper = [string]$WrapperInfo.launcher_path
        } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
        $materialized.Add([System.IO.Path]::GetFullPath($settingsPath)) | Out-Null
    }

    return @($materialized)
}

function Test-VgoClosedReadyRequiredForAdapter {
    param([psobject]$Adapter)

    return ([string]$Adapter.install_mode).ToLowerInvariant() -ne 'governed'
}

function Write-VgoHostClosure {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [psobject]$Adapter
    )

    $bridgeResolution = Resolve-VgoHostBridgeCommand -HostId ([string]$Adapter.id)
    $wrapperInfo = New-VgoHostSpecialistWrapper -TargetRoot $TargetRoot -HostId ([string]$Adapter.id) -BridgeCommand ([string]$bridgeResolution.command) -BridgeEnvName ([string]$bridgeResolution.env_name)
    $settingsMaterialized = Set-VgoManagedHostSettings -TargetRoot $TargetRoot -HostId ([string]$Adapter.id) -WrapperInfo $wrapperInfo
    $commandsRoot = Join-Path $TargetRoot 'commands'
    $closureState = if ($wrapperInfo.ready) { 'closed_ready' } else { 'configured_offline_unready' }
    $closure = [ordered]@{
        schema_version = 1
        host_id = [string]$Adapter.id
        platform = Get-VgoPlatformTag
        target_root = [System.IO.Path]::GetFullPath($TargetRoot)
        install_mode = [string]$Adapter.install_mode
        commands_root = [System.IO.Path]::GetFullPath($commandsRoot)
        global_workflows_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'global_workflows'))
        mcp_config_path = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'mcp_config.json'))
        host_closure_state = $closureState
        commands_materialized = (Test-Path -LiteralPath $commandsRoot -PathType Container)
        settings_materialized = @($settingsMaterialized)
        specialist_wrapper = [ordered]@{
            launcher_path = [string]$wrapperInfo.launcher_path
            script_path = [string]$wrapperInfo.script_path
            ready = [bool]$wrapperInfo.ready
            bridge_command = [string]$bridgeResolution.command
            bridge_source = [string]$bridgeResolution.source
        }
    }
    $closurePath = Join-Path $TargetRoot '.vibeskills\host-closure.json'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $closurePath) | Out-Null
    $closure | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $closurePath -Encoding UTF8
    return [pscustomobject]@{
        path = [System.IO.Path]::GetFullPath($closurePath)
        data = [pscustomobject]$closure
    }
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
                $destination = Join-Path $TargetRoot ("skills\" + $Name)
                Copy-DirContent -Source $src -Destination $destination
                Restore-SkillEntryPointIfNeeded -SkillRoot $destination
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

function Get-GeneratedNestedCompatibilitySuffix {
    param([psobject]$Governance)

    $topology = if ($Governance.PSObject.Properties.Name -contains 'mirror_topology') { $Governance.mirror_topology } else { $null }
    $targets = if ($null -ne $topology -and $topology.PSObject.Properties.Name -contains 'targets' -and $null -ne $topology.targets) { @($topology.targets) } else { @() }
    $bundledPath = $null
    $nestedPath = $null
    $materializationMode = $null
    foreach ($target in $targets) {
        $targetId = if ($target.PSObject.Properties.Name -contains 'id') { [string]$target.id } else { '' }
        switch ($targetId) {
            'bundled' {
                $bundledPath = if ($target.PSObject.Properties.Name -contains 'path') { [string]$target.path } else { $null }
            }
            'nested_bundled' {
                $nestedPath = if ($target.PSObject.Properties.Name -contains 'path') { [string]$target.path } else { $null }
                $materializationMode = if ($target.PSObject.Properties.Name -contains 'materialization_mode') { [string]$target.materialization_mode } else { $null }
            }
        }
    }

    $legacy = if ($Governance.PSObject.Properties.Name -contains 'source_of_truth') { $Governance.source_of_truth } else { $null }
    if ([string]::IsNullOrWhiteSpace($bundledPath)) {
        $bundledPath = if ($null -ne $legacy -and $legacy.PSObject.Properties.Name -contains 'bundled_root') { [string]$legacy.bundled_root } else { 'bundled/skills/vibe' }
    }
    if ([string]::IsNullOrWhiteSpace($nestedPath)) {
        $nestedPath = if ($null -ne $legacy -and $legacy.PSObject.Properties.Name -contains 'nested_bundled_root') { [string]$legacy.nested_bundled_root } else { $null }
    }
    if ([string]::IsNullOrWhiteSpace($nestedPath)) {
        $nestedPath = '{0}/{1}' -f $bundledPath, $bundledPath
    }
    if ([string]::IsNullOrWhiteSpace($materializationMode)) {
        $materializationMode = 'release_install_only'
    }
    if ($materializationMode -ne 'release_install_only') {
        return $null
    }

    $bundledNorm = $bundledPath.Replace('\', '/').Trim('/')
    $nestedNorm = $nestedPath.Replace('\', '/').Trim('/')
    if (-not $nestedNorm.StartsWith($bundledNorm + '/', [System.StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }

    $suffix = $nestedNorm.Substring($bundledNorm.Length + 1).Trim('/')
    if ([string]::IsNullOrWhiteSpace($suffix)) {
        return $null
    }

    return $suffix.Replace('/', '\')
}

function Sync-InstalledGeneratedNestedCompatibilityRoot {
    param(
        [Parameter(Mandatory)] [psobject]$Governance,
        [Parameter(Mandatory)] [string]$TargetRoot,
        [string]$TargetRel = 'skills\vibe'
    )

    $nestedSuffix = Get-GeneratedNestedCompatibilitySuffix -Governance $Governance
    if ([string]::IsNullOrWhiteSpace($nestedSuffix)) {
        return
    }

    $targetVibeRoot = Join-Path $TargetRoot $TargetRel
    $nestedRoot = Join-Path $targetVibeRoot $nestedSuffix
    if ([System.IO.Path]::GetFullPath($targetVibeRoot) -eq [System.IO.Path]::GetFullPath($nestedRoot)) {
        return
    }

    if (Test-Path -LiteralPath $nestedRoot) {
        Remove-Item -LiteralPath $nestedRoot -Recurse -Force
    }

    $mirrorFiles = @($Governance.packaging.mirror.files)
    $mirrorDirs = @($Governance.packaging.mirror.directories)
    foreach ($rel in $mirrorFiles) {
        $src = Join-Path $targetVibeRoot $rel
        $dst = Join-Path $nestedRoot $rel
        if (-not (Test-Path -LiteralPath $src)) { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
    foreach ($dir in $mirrorDirs) {
        $srcDir = Join-Path $targetVibeRoot $dir
        $dstDir = Join-Path $nestedRoot $dir
        if (-not (Test-Path -LiteralPath $srcDir)) { continue }
        Copy-DirContent -Source $srcDir -Destination $dstDir
    }
}

function Install-RuntimeCorePayload {
    param([psobject]$Adapter)

    $packagingPath = Join-Path $RepoRoot 'config\runtime-core-packaging.json'
    $packaging = Get-Content -LiteralPath $packagingPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
    $governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json

    foreach ($dir in @($packaging.directories)) {
        New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot ([string]$dir)) | Out-Null
    }

    foreach ($entry in @($packaging.copy_directories)) {
        $src = Join-Path $RepoRoot ([string]$entry.source)
        $dst = Join-Path $TargetRoot ([string]$entry.target)
        Copy-DirContent -Source $src -Destination $dst
        if ([string]$entry.target -eq 'skills' -and (Test-Path -LiteralPath $dst -PathType Container)) {
            foreach ($skillDir in @(Get-ChildItem -LiteralPath $dst -Directory -ErrorAction SilentlyContinue)) {
                Restore-SkillEntryPointIfNeeded -SkillRoot $skillDir.FullName
            }
        }
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
    Sync-InstalledGeneratedNestedCompatibilityRoot -Governance $governance -TargetRoot $TargetRoot -TargetRel $targetVibeRel

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

function Install-OpenCodeGuidancePayload {
    Copy-DirContent -Source (Join-Path $RepoRoot 'config\opencode\commands') -Destination (Join-Path $TargetRoot 'commands')
    Copy-DirContent -Source (Join-Path $RepoRoot 'config\opencode\commands') -Destination (Join-Path $TargetRoot 'command')
    Copy-DirContent -Source (Join-Path $RepoRoot 'config\opencode\agents') -Destination (Join-Path $TargetRoot 'agents')
    Copy-DirContent -Source (Join-Path $RepoRoot 'config\opencode\agents') -Destination (Join-Path $TargetRoot 'agent')

    $exampleConfig = Join-Path $RepoRoot 'config\opencode\opencode.json.example'
    if (Test-Path -LiteralPath $exampleConfig) {
        Copy-Item -LiteralPath $exampleConfig -Destination (Join-Path $TargetRoot 'opencode.json.example') -Force
    }
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
$legacyOpenCodeConfigCleanup = $null
switch ([string]$adapter.install_mode) {
    'governed' { Install-GovernedCodexPayload }
    'preview-guidance' {
        if ([string]$adapter.id -eq 'opencode') {
            Install-OpenCodeGuidancePayload
            $legacyOpenCodeConfigCleanup = Repair-VgoLegacyOpenCodeConfig -TargetRoot $TargetRoot
        } elseif ([string]$adapter.id -eq 'claude-code' -or [string]$adapter.id -eq 'cursor') {
            Install-ClaudeGuidancePayload
        } else {
            throw "Unsupported preview-guidance adapter id: $($adapter.id)"
        }
    }
    'runtime-core' {
        Install-RuntimeCoreModePayload
    }
    default { throw "Unsupported adapter install mode: $($adapter.install_mode)" }
}

$closureReceipt = Write-VgoHostClosure -TargetRoot $TargetRoot -Adapter $adapter
$requireClosedReadyEffective = [bool]($RequireClosedReady -and (Test-VgoClosedReadyRequiredForAdapter -Adapter $adapter))
if ($requireClosedReadyEffective -and [string]$closureReceipt.data.host_closure_state -ne 'closed_ready') {
    throw ("Host closure for '{0}' is not closed_ready (got '{1}'). Configure the host specialist bridge command first, then retry install." -f [string]$adapter.id, [string]$closureReceipt.data.host_closure_state)
}

[pscustomobject]@{
    host_id = [string]$adapter.id
    install_mode = [string]$adapter.install_mode
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    external_fallback_used = @($result.external_fallback_used)
    host_closure_path = [string]$closureReceipt.path
    host_closure_state = [string]$closureReceipt.data.host_closure_state
    settings_materialized = @($closureReceipt.data.settings_materialized)
    legacy_opencode_config_cleanup = $legacyOpenCodeConfigCleanup
    specialist_wrapper_ready = [bool]$closureReceipt.data.specialist_wrapper.ready
    require_closed_ready_requested = [bool]$RequireClosedReady
    require_closed_ready_effective = $requireClosedReadyEffective
} | ConvertTo-Json -Depth 10
