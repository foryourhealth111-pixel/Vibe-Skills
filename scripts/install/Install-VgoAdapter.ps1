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
$script:SelectedInstallProfile = [string]$PSBoundParameters['Profile']
if ([string]::IsNullOrWhiteSpace($script:SelectedInstallProfile)) {
    $script:SelectedInstallProfile = 'full'
}
$script:RuntimeSupportRootRel = '.vibeskills\runtime-support'

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
        '--profile', $script:SelectedInstallProfile
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
    Add-VgoCreatedPath -Path $Destination
}

function Copy-SkillRootsWithoutSelfShadow {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$RepoRoot,
        [string[]]$ExcludeSkillNames = @()
    )

    if (-not (Test-Path -LiteralPath $Source)) { return }

    $repoRootFull = [System.IO.Path]::GetFullPath($RepoRoot)
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Add-VgoCreatedPath -Path $Destination

    foreach ($child in @(Get-ChildItem -LiteralPath $Source -Force -ErrorAction SilentlyContinue | Sort-Object Name)) {
        if ($ExcludeSkillNames -contains [string]$child.Name) {
            continue
        }
        $target = Join-Path $Destination $child.Name
        if ([System.IO.Path]::GetFullPath($target) -eq $repoRootFull) {
            continue
        }
        if ($child.PSIsContainer) {
            Copy-DirContent -Source $child.FullName -Destination $target
        } else {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $child.FullName -Destination $target -Force
            Add-VgoCreatedPath -Path $target
        }
    }
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

function Convert-SkillEntryPointToRuntimeMirror {
    param([string]$SkillRoot)

    $skillMd = Join-Path $SkillRoot 'SKILL.md'
    $mirrorPath = Join-Path $SkillRoot 'SKILL.runtime-mirror.md'
    if (Test-Path -LiteralPath $mirrorPath -PathType Leaf) {
        if (Test-Path -LiteralPath $skillMd -PathType Leaf) {
            Remove-Item -LiteralPath $skillMd -Force
        }
        return
    }

    if (Test-Path -LiteralPath $skillMd -PathType Leaf) {
        Move-Item -LiteralPath $skillMd -Destination $mirrorPath -Force
    }
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

function Get-VgoSafeRelativeContractPath {
    param(
        [object]$Value,
        [string]$Default,
        [string]$FieldName
    )

    $raw = [string]$(if ($null -ne $Value) { $Value } else { $Default })
    $raw = $raw.Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        $raw = $Default
    }

    $normalized = $raw.Replace('\', '/').Trim('/')
    if ([System.IO.Path]::IsPathRooted($normalized)) {
        throw "Invalid relative path for ${FieldName}: $raw"
    }

    $parts = @($normalized.Split('/') | Where-Object { $_ -ne '' })
    if ($parts.Count -eq 0 -or @($parts | Where-Object { $_ -in @('.', '..') }).Count -gt 0) {
        throw "Invalid relative path for ${FieldName}: $raw"
    }

    return (($parts -join '/'))
}

function Get-VgoSafeSkillName {
    param(
        [object]$Value,
        [string]$FieldName
    )

    $name = [string]$Value
    $name = $name.Trim()
    if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('/') -or $name.Contains('\') -or $name -in @('.', '..')) {
        throw "Invalid skill name in ${FieldName}: $Value"
    }
    return $name
}

function Get-VgoExistingInstallLedger {
    param([string]$TargetRoot)

    $ledgerPath = Join-Path $TargetRoot '.vibeskills\install-ledger.json'
    if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) {
        return $null
    }

    try {
        $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    } catch {
        return $null
    }

    if (-not ($ledger -is [System.Collections.IDictionary])) {
        return $null
    }
    return $ledger
}

function Get-VgoManagedSkillNamesFromLedger {
    param(
        [hashtable]$Ledger,
        [string]$TargetRoot
    )

    if (-not ($Ledger -is [System.Collections.IDictionary])) {
        return @()
    }

    $managed = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::Ordinal)
    foreach ($fieldName in @('managed_skill_names', 'managed_runtime_skill_names', 'managed_catalog_skill_names')) {
        foreach ($rawName in @($Ledger[$fieldName])) {
            $text = [string]$rawName
            if ([string]::IsNullOrWhiteSpace($text)) {
                continue
            }
            $managed.Add((Get-VgoSafeSkillName -Value $text -FieldName $fieldName)) | Out-Null
        }
    }

    $skillsRoot = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
    foreach ($rawPath in @($Ledger['created_paths'])) {
        $text = [string]$rawPath
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }
        try {
            $candidate = [System.IO.Path]::GetFullPath($text)
        } catch {
            continue
        }
        if (-not $candidate.StartsWith($skillsRoot, [System.StringComparison]::Ordinal)) {
            continue
        }
        $relative = $candidate.Substring($skillsRoot.Length).TrimStart('\', '/')
        if ([string]::IsNullOrWhiteSpace($relative)) {
            continue
        }
        $firstPart = @($relative -split '[\\/]') | Select-Object -First 1
        if (-not [string]::IsNullOrWhiteSpace([string]$firstPart)) {
            $managed.Add([string]$firstPart) | Out-Null
        }
    }

    $canonicalVibeRoot = [string]$Ledger['canonical_vibe_root']
    if (-not [string]::IsNullOrWhiteSpace($canonicalVibeRoot)) {
        $managed.Add((Split-Path -Leaf $canonicalVibeRoot)) | Out-Null
    }

    return @($managed | Sort-Object)
}

function Remove-VgoPreviouslyManagedSkillDirs {
    param(
        [string]$TargetRoot,
        [string[]]$PreviousManagedSkillNames = @(),
        [string[]]$CurrentManagedSkillNames = @()
    )

    $skillsRoot = Join-Path $TargetRoot 'skills'
    if (-not (Test-Path -LiteralPath $skillsRoot -PathType Container)) {
        return
    }

    $currentManaged = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::Ordinal)
    foreach ($name in @($CurrentManagedSkillNames)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$name)) {
            $currentManaged.Add([string]$name) | Out-Null
        }
    }

    foreach ($name in @($PreviousManagedSkillNames | Sort-Object -CaseSensitive -Unique)) {
        if ([string]::IsNullOrWhiteSpace([string]$name) -or $currentManaged.Contains([string]$name)) {
            continue
        }
        $skillRoot = Join-Path $skillsRoot ([string]$name)
        if (Test-Path -LiteralPath $skillRoot -PathType Container) {
            Remove-Item -LiteralPath $skillRoot -Recurse -Force
        }
    }
}

function Test-VgoSkillOnlyActivationHost {
    param([string]$HostId)

    return $HostId -in @('claude-code', 'cursor', 'windsurf', 'openclaw', 'opencode')
}

function Get-VgoDefaultCatalogProfileId {
    param([string]$Profile)

    $profileId = [string]$Profile
    $profileId = $profileId.Trim()
    switch ($profileId) {
        'minimal' { return 'foundation-workflow' }
        'full' { return 'default-full' }
        default { return $profileId }
    }
}

function Test-VgoSkillDirectory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }

    return (Test-Path -LiteralPath (Join-Path $Path 'SKILL.md')) -or
        (Test-Path -LiteralPath (Join-Path $Path 'SKILL.runtime-mirror.md'))
}

function Get-VgoRuntimeCorePackaging {
    param(
        [string]$RepoRoot,
        [string]$Profile
    )

    $packagingPath = Join-Path $RepoRoot 'config\runtime-core-packaging.json'
    $packaging = Get-Content -LiteralPath $packagingPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    $manifestRel = $null
    if ($packaging.ContainsKey('profile_manifests') -and $packaging['profile_manifests'] -is [System.Collections.IDictionary]) {
        $manifestRel = [string]$packaging['profile_manifests'][$Profile]
    }
    if (-not [string]::IsNullOrWhiteSpace($manifestRel)) {
        $manifestPath = Join-Path $RepoRoot $manifestRel
        if (-not (Test-Path -LiteralPath $manifestPath)) {
            throw "Runtime-core packaging manifest missing for profile '$Profile': $manifestPath"
        }
        $packaging = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    }

    if (-not $packaging.ContainsKey('profile')) {
        $packaging['profile'] = $Profile
    }
    if (-not $packaging.ContainsKey('bundled_skills_source')) {
        $packaging['bundled_skills_source'] = 'bundled/skills'
    }
    if (-not $packaging.ContainsKey('skills_allowlist')) {
        $packaging['skills_allowlist'] = @()
    }
    if (-not $packaging.ContainsKey('catalog_profile')) {
        $packaging['catalog_profile'] = Get-VgoDefaultCatalogProfileId -Profile $Profile
    }
    if (-not $packaging.ContainsKey('runtime_profile')) {
        $packaging['runtime_profile'] = 'core-default'
    }
    if (-not $packaging.ContainsKey('copy_bundled_skills')) {
        $packaging['copy_bundled_skills'] = [bool](@($packaging['copy_directories']) | Where-Object { [string]$_['target'] -eq 'skills' }).Count
    }
    if (-not $packaging.ContainsKey('exclude_bundled_skill_names')) {
        $canonicalRel = 'skills/vibe'
        if ($packaging.ContainsKey('canonical_vibe_payload') -and $packaging['canonical_vibe_payload']) {
            $canonicalRel = [string]$packaging['canonical_vibe_payload']['target_relpath']
        } elseif ($packaging.ContainsKey('canonical_vibe_mirror') -and $packaging['canonical_vibe_mirror']) {
            $canonicalRel = [string]$packaging['canonical_vibe_mirror']['target_relpath']
        }
        $packaging['exclude_bundled_skill_names'] = @((Split-Path -Leaf $canonicalRel))
    }

    return $packaging
}

function Get-VgoSkillCatalogPackagingRelPath {
    param([string]$RepoRoot)

    $runtimePackagingPath = Join-Path $RepoRoot 'config\runtime-core-packaging.json'
    $runtimePackaging = Get-Content -LiteralPath $runtimePackagingPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    return (Get-VgoSafeRelativeContractPath -Value $runtimePackaging['catalog_packaging_manifest'] -Default 'config/skill-catalog-packaging.json' -FieldName 'catalog_packaging_manifest')
}

function Get-VgoInstalledRuntimeOwnerRoot {
    param([string]$RepoRoot)

    $parent = Split-Path -Parent $RepoRoot
    if ([string]::IsNullOrWhiteSpace($parent) -or (Split-Path -Leaf $parent) -ne 'skills') {
        return $null
    }

    $ownerRoot = Split-Path -Parent $parent
    $ledgerPath = Join-Path $ownerRoot '.vibeskills\install-ledger.json'
    if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) {
        return $null
    }

    try {
        $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    } catch {
        return $null
    }
    if (-not ($ledger -is [System.Collections.IDictionary]) -or -not $ledger.ContainsKey('canonical_vibe_root')) {
        return $null
    }
    $canonicalVibeRoot = [string]$ledger['canonical_vibe_root']
    if ([string]::IsNullOrWhiteSpace($canonicalVibeRoot)) {
        return $null
    }
    if ([System.IO.Path]::GetFullPath($canonicalVibeRoot) -ne [System.IO.Path]::GetFullPath($RepoRoot)) {
        return $null
    }

    return $ownerRoot
}

function Get-VgoInstalledRuntimeSupportRoot {
    param([string]$RepoRoot)

    $ownerRoot = Get-VgoInstalledRuntimeOwnerRoot -RepoRoot $RepoRoot
    if ([string]::IsNullOrWhiteSpace($ownerRoot)) {
        return $null
    }

    $supportRoot = Join-Path $ownerRoot $script:RuntimeSupportRootRel
    if (Test-Path -LiteralPath $supportRoot -PathType Container) {
        return $supportRoot
    }

    return $null
}

function Get-VgoSkillCatalogPackagingPath {
    param(
        [string]$RepoRoot,
        [string]$TargetRoot = $null
    )

    $manifestRel = Get-VgoSkillCatalogPackagingRelPath -RepoRoot $RepoRoot
    $repoCandidate = Join-Path $RepoRoot $manifestRel
    if (Test-Path -LiteralPath $repoCandidate -PathType Leaf) {
        return [pscustomobject]@{
            base_root = $RepoRoot
            path = $repoCandidate
            relative_path = $manifestRel
        }
    }

    $sourceSupportRoot = Get-VgoInstalledRuntimeSupportRoot -RepoRoot $RepoRoot
    if (-not [string]::IsNullOrWhiteSpace($sourceSupportRoot)) {
        $sourceSupportCandidate = Join-Path $sourceSupportRoot $manifestRel
        if (Test-Path -LiteralPath $sourceSupportCandidate -PathType Leaf) {
            return [pscustomobject]@{
                base_root = $sourceSupportRoot
                path = $sourceSupportCandidate
                relative_path = $manifestRel
            }
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) {
        $supportRoot = Join-Path $TargetRoot $script:RuntimeSupportRootRel
        $supportCandidate = Join-Path $supportRoot $manifestRel
        if (Test-Path -LiteralPath $supportCandidate -PathType Leaf) {
            return [pscustomobject]@{
                base_root = $supportRoot
                path = $supportCandidate
                relative_path = $manifestRel
            }
        }
    }

    return [pscustomobject]@{
        base_root = $RepoRoot
        path = $repoCandidate
        relative_path = $manifestRel
    }
}

function Get-VgoSkillCatalogPackaging {
    param(
        [string]$RepoRoot,
        [string]$TargetRoot = $null
    )

    $packagingLocation = Get-VgoSkillCatalogPackagingPath -RepoRoot $RepoRoot -TargetRoot $TargetRoot
    return [pscustomobject]@{
        base_root = [string]$packagingLocation.base_root
        path = [string]$packagingLocation.path
        manifest_rel = [string]$packagingLocation.relative_path
        packaging = (Get-Content -LiteralPath $packagingLocation.path -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable)
    }
}

function Get-VgoSkillCatalogRoot {
    param(
        [string]$RepoRoot,
        [hashtable]$CatalogPackaging
    )

    $catalogRootRel = if ($CatalogPackaging.ContainsKey('catalog_root')) { [string]$CatalogPackaging['catalog_root'] } else { 'bundled/skills' }
    return (Join-Path $RepoRoot $catalogRootRel)
}

function Get-VgoInstalledRuntimeCatalogSourceInfo {
    param([string]$RepoRoot)

    $ownerRoot = Get-VgoInstalledRuntimeOwnerRoot -RepoRoot $RepoRoot
    if ([string]::IsNullOrWhiteSpace($ownerRoot)) {
        return $null
    }

    $ledgerPath = Join-Path $ownerRoot '.vibeskills\install-ledger.json'
    if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) {
        return $null
    }

    $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
    if (-not ($ledger -is [System.Collections.IDictionary])) {
        return $null
    }

    $catalogSkillNames = @(
        @($ledger['managed_catalog_skill_names']) |
            ForEach-Object { Get-VgoSafeSkillName -Value $_ -FieldName 'managed_catalog_skill_names' } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Sort-Object -CaseSensitive -Unique
    )
    if (@($catalogSkillNames).Count -eq 0) {
        return $null
    }

    $skillsRoot = Join-Path $ownerRoot 'skills'
    if (-not (Test-Path -LiteralPath $skillsRoot -PathType Container)) {
        return $null
    }

    return [pscustomobject]@{
        catalog_root = $skillsRoot
        bundled_skill_names = $catalogSkillNames
    }
}

function Get-VgoSkillCatalogProfiles {
    param(
        [string]$BaseRoot,
        [hashtable]$CatalogPackaging
    )

    $profilesRel = Get-VgoSafeRelativeContractPath -Value $(if ($CatalogPackaging.ContainsKey('profiles_manifest')) { [string]$CatalogPackaging['profiles_manifest'] } else { $null }) -Default 'config/skill-catalog-profiles.json' -FieldName 'profiles_manifest'
    return (Get-Content -LiteralPath (Join-Path $BaseRoot $profilesRel) -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable)
}

function Get-VgoSkillCatalogGroups {
    param(
        [string]$BaseRoot,
        [hashtable]$CatalogPackaging
    )

    $groupsRel = Get-VgoSafeRelativeContractPath -Value $(if ($CatalogPackaging.ContainsKey('groups_manifest')) { [string]$CatalogPackaging['groups_manifest'] } else { $null }) -Default 'config/skill-catalog-groups.json' -FieldName 'groups_manifest'
    return (Get-Content -LiteralPath (Join-Path $BaseRoot $groupsRel) -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable)
}

function Resolve-VgoCatalogProfileSkillNames {
    param(
        [string]$CatalogBaseRoot,
        [hashtable]$CatalogPackaging,
        [string]$ProfileId,
        [string]$CatalogRoot = $null,
        [string[]]$BundledSkillNames = @(),
        [System.Collections.Generic.HashSet[string]]$Seen
    )

    if ([string]::IsNullOrWhiteSpace($ProfileId)) {
        $ProfileId = Get-VgoDefaultCatalogProfileId -Profile $script:SelectedInstallProfile
    }

    $profiles = (Get-VgoSkillCatalogProfiles -BaseRoot $CatalogBaseRoot -CatalogPackaging $CatalogPackaging)['profiles']
    $groups = (Get-VgoSkillCatalogGroups -BaseRoot $CatalogBaseRoot -CatalogPackaging $CatalogPackaging)['groups']
    if (-not ($profiles -is [System.Collections.IDictionary]) -or -not $profiles.Contains($ProfileId)) {
        throw "Unknown skill catalog profile: $ProfileId"
    }

    $names = [System.Collections.Generic.HashSet[string]]::new()
    if ($Seen.Contains($ProfileId)) {
        return $names
    }
    $Seen.Add($ProfileId) | Out-Null

    $profile = $profiles[$ProfileId]
    foreach ($skillName in @($profile['skills'])) {
        $text = Get-VgoSafeSkillName -Value $skillName -FieldName ("profile '{0}'" -f $ProfileId)
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            $names.Add($text) | Out-Null
        }
    }

    foreach ($groupId in @($profile['groups'])) {
        $groupKey = [string]$groupId
        if (-not $groups.Contains($groupKey)) {
            throw "Unknown skill catalog group '$groupKey' in profile '$ProfileId'"
        }
        foreach ($skillName in @($groups[$groupKey]['skills'])) {
            $text = Get-VgoSafeSkillName -Value $skillName -FieldName ("group '{0}' in profile '{1}'" -f $groupKey, $ProfileId)
            if (-not [string]::IsNullOrWhiteSpace($text)) {
                $names.Add($text) | Out-Null
            }
        }
    }

    foreach ($nestedProfile in @($profile['include_profiles'])) {
        $resolved = Resolve-VgoCatalogProfileSkillNames -CatalogBaseRoot $CatalogBaseRoot -CatalogPackaging $CatalogPackaging -ProfileId ([string]$nestedProfile) -CatalogRoot $CatalogRoot -BundledSkillNames $BundledSkillNames -Seen $Seen
        foreach ($skillName in $resolved) {
            $names.Add([string]$skillName) | Out-Null
        }
    }

    if ([bool]$profile['include_all_bundled']) {
        if (@($BundledSkillNames).Count -gt 0) {
            foreach ($skillName in @($BundledSkillNames)) {
                $text = Get-VgoSafeSkillName -Value $skillName -FieldName ("include_all_bundled for profile '{0}'" -f $ProfileId)
                if (-not [string]::IsNullOrWhiteSpace($text)) {
                    $names.Add($text) | Out-Null
                }
            }
        } elseif (-not [string]::IsNullOrWhiteSpace($CatalogRoot) -and (Test-Path -LiteralPath $CatalogRoot -PathType Container)) {
            foreach ($candidate in @(Get-ChildItem -LiteralPath $CatalogRoot -Directory -ErrorAction SilentlyContinue)) {
                if (Test-VgoSkillDirectory -Path $candidate.FullName) {
                    $names.Add([string]$candidate.Name) | Out-Null
                }
            }
        }
    }

    foreach ($excluded in @($profile['exclude_skills'])) {
        $text = Get-VgoSafeSkillName -Value $excluded -FieldName ("exclude_skills for profile '{0}'" -f $ProfileId)
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            $names.Remove($text) | Out-Null
        }
    }
    $names.Remove('vibe') | Out-Null
    return $names
}

function Sync-VgoCatalogRuntimeSupportFiles {
    param([string]$RepoRoot)

    $catalogPackagingInfo = Get-VgoSkillCatalogPackaging -RepoRoot $RepoRoot -TargetRoot $TargetRoot
    $catalogPackaging = $catalogPackagingInfo.packaging
    $catalogBaseRoot = [string]$catalogPackagingInfo.base_root
    $supportRoot = Join-Path $TargetRoot $script:RuntimeSupportRootRel
    $manifestRel = [string]$catalogPackagingInfo.manifest_rel
    $relpaths = @(
        $manifestRel,
        (Get-VgoSafeRelativeContractPath -Value $(if ($catalogPackaging.ContainsKey('profiles_manifest')) { $catalogPackaging['profiles_manifest'] } else { $null }) -Default 'config/skill-catalog-profiles.json' -FieldName 'profiles_manifest'),
        (Get-VgoSafeRelativeContractPath -Value $(if ($catalogPackaging.ContainsKey('groups_manifest')) { $catalogPackaging['groups_manifest'] } else { $null }) -Default 'config/skill-catalog-groups.json' -FieldName 'groups_manifest')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Sort-Object -CaseSensitive -Unique

    foreach ($relpath in $relpaths) {
        $src = Join-Path $catalogBaseRoot $relpath
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
            throw "Catalog support manifest missing: $src"
        }
        $dst = Join-Path $supportRoot $relpath
        if ([System.IO.Path]::GetFullPath($src) -eq [System.IO.Path]::GetFullPath($dst)) {
            continue
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Add-VgoCreatedPath -Path $dst
    }
}

function Get-VgoRepoOwnedSkillSourceRoots {
    param([string]$RepoRoot)

    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @(
        (Join-Path $RepoRoot 'bundled\skills'),
        (Join-Path $RepoRoot 'bundled\superpowers-skills')
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Container) -and -not $roots.Contains($candidate)) {
            $roots.Add($candidate) | Out-Null
        }
    }
    return @($roots)
}

function Get-VgoExternalSkillSourceRoots {
    param([string]$RepoRoot)

    $ownedRoots = @(Get-VgoRepoOwnedSkillSourceRoots -RepoRoot $RepoRoot)
    $canonicalSkillsRoot = Get-VgoParentPath -Path $RepoRoot
    $workspaceRoot = Get-VgoParentPath -Path $canonicalSkillsRoot
    $workspaceSkillsRoot = $null
    $workspaceSuperpowersRoot = $null
    if (-not [string]::IsNullOrWhiteSpace($workspaceRoot)) {
        $workspaceSkillsRoot = Join-Path $workspaceRoot 'skills'
        $workspaceSuperpowersRoot = Join-Path $workspaceRoot 'superpowers\skills'
    }
    $candidates = @($canonicalSkillsRoot, $workspaceSkillsRoot, $workspaceSuperpowersRoot)

    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate) -or -not (Test-Path -LiteralPath $candidate -PathType Container)) {
            continue
        }
        $candidateFull = [System.IO.Path]::GetFullPath($candidate)
        if (@($ownedRoots | ForEach-Object { [System.IO.Path]::GetFullPath($_) }) -contains $candidateFull) {
            continue
        }
        if (-not $roots.Contains($candidateFull)) {
            $roots.Add($candidateFull) | Out-Null
        }
    }
    return @($roots)
}

function Get-VgoDesiredRuntimeManagedSkillNames {
    param([hashtable]$Packaging)

    $canonicalRel = 'skills/vibe'
    if ($Packaging.ContainsKey('canonical_vibe_payload') -and $Packaging['canonical_vibe_payload']) {
        $canonicalRel = [string]$Packaging['canonical_vibe_payload']['target_relpath']
    } elseif ($Packaging.ContainsKey('canonical_vibe_mirror') -and $Packaging['canonical_vibe_mirror']) {
        $canonicalRel = [string]$Packaging['canonical_vibe_mirror']['target_relpath']
    }

    $names = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::Ordinal)
    $names.Add((Split-Path -Leaf $canonicalRel)) | Out-Null
    foreach ($name in @('dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')) {
        $names.Add($name) | Out-Null
    }
    return @($names | Sort-Object)
}

$script:VgoCreatedPaths = [System.Collections.Generic.HashSet[string]]::new()
$script:VgoManagedJsonPaths = [System.Collections.Generic.HashSet[string]]::new()
$script:VgoTemplateGeneratedPaths = [System.Collections.Generic.HashSet[string]]::new()
$script:VgoSpecialistWrapperPaths = [System.Collections.Generic.List[string]]::new()

function Add-VgoTrackedPath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Set
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    if ($null -eq $Set) {
        return
    }

    $resolved = [System.IO.Path]::GetFullPath($Path)
    if ($Set -is [System.Collections.Generic.HashSet[string]]) {
        [void]$Set.Add($resolved)
        return
    }

    if ($Set.PSObject.Methods.Name -contains 'Add') {
        [void]$Set.Add($resolved)
        return
    }

    throw 'Tracked path set does not support Add().'
}

function Add-VgoCreatedPath {
    param([Parameter(Mandatory)] [string]$Path)

    Add-VgoTrackedPath -Path $Path -Set $script:VgoCreatedPaths
}

function Add-VgoManagedJsonPath {
    param([Parameter(Mandatory)] [string]$Path)

    Add-VgoTrackedPath -Path $Path -Set $script:VgoManagedJsonPaths
}

function Add-VgoTemplateGeneratedPath {
    param([Parameter(Mandatory)] [string]$Path)

    Add-VgoTrackedPath -Path $Path -Set $script:VgoTemplateGeneratedPaths
}

function Add-VgoSpecialistWrapperPath {
    param([Parameter(Mandatory)] [string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    $resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not $script:VgoSpecialistWrapperPaths.Contains($resolved)) {
        [void]$script:VgoSpecialistWrapperPaths.Add($resolved)
    }
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
    Add-VgoCreatedPath -Path $toolsRoot

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
    Add-VgoCreatedPath -Path $wrapperPy
    Add-VgoSpecialistWrapperPath -Path $wrapperPy

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
    Add-VgoCreatedPath -Path $launcherPath
    Add-VgoSpecialistWrapperPath -Path $launcherPath

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
    if (Test-VgoSkillOnlyActivationHost -HostId $HostId) {
        $settingsPath = Join-Path $TargetRoot '.vibeskills\host-settings.json'
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $settingsPath) | Out-Null
        $payload = [ordered]@{
            schema_version = 1
            host_id = $HostId
            managed = $true
            skills_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
            runtime_skill_entry = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills\vibe\SKILL.md'))
            explicit_vibe_skill_invocation = @('$vibe', '/vibe')
            specialist_wrapper = [ordered]@{
                launcher_path = [string]$WrapperInfo.launcher_path
                script_path = [string]$WrapperInfo.script_path
                ready = [bool]$WrapperInfo.ready
            }
        }
        $commandsRoot = Join-Path $TargetRoot 'commands'
        $agentsRoot = Join-Path $TargetRoot 'agents'
        $workflowRoot = Join-Path $TargetRoot 'global_workflows'
        $mcpConfigPath = Join-Path $TargetRoot 'mcp_config.json'
        if (Test-Path -LiteralPath $commandsRoot -PathType Container) {
            $payload.commands_root = [System.IO.Path]::GetFullPath($commandsRoot)
        }
        if (Test-Path -LiteralPath $agentsRoot -PathType Container) {
            $payload.agents_root = [System.IO.Path]::GetFullPath($agentsRoot)
        }
        if (Test-Path -LiteralPath $workflowRoot -PathType Container) {
            $payload.workflow_root = [System.IO.Path]::GetFullPath($workflowRoot)
        }
        if (Test-Path -LiteralPath $mcpConfigPath -PathType Leaf) {
            $payload.mcp_config = [System.IO.Path]::GetFullPath($mcpConfigPath)
        }
        $payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
        Add-VgoCreatedPath -Path $settingsPath
        Add-VgoManagedJsonPath -Path $settingsPath
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
        skills_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
        runtime_skill_entry = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills\vibe\SKILL.md'))
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
    Add-VgoCreatedPath -Path $closurePath
    return [pscustomobject]@{
        path = [System.IO.Path]::GetFullPath($closurePath)
        data = [pscustomobject]$closure
    }
}

function Write-VgoInstallLedger {
    param(
        [Parameter(Mandatory)] [psobject]$Adapter,
        [Parameter(Mandatory)] [string]$Profile,
        [Parameter(Mandatory)] [hashtable]$Packaging,
        [Parameter(Mandatory)] [string[]]$RuntimeManagedSkillNames,
        [string]$CatalogProfile = '',
        [string[]]$CatalogManagedSkillNames = @(),
        [string[]]$ExternalFallbackUsed = @()
    )

    $ledgerPath = Join-Path $TargetRoot '.vibeskills\install-ledger.json'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ledgerPath) | Out-Null

    $managedSkillNames = @($RuntimeManagedSkillNames + $CatalogManagedSkillNames | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Sort-Object -CaseSensitive -Unique)

    $ledger = [ordered]@{
        schema_version = 1
        host_id = [string]$Adapter.id
        install_mode = [string]$Adapter.install_mode
        profile = [string]$Profile
        target_root = [System.IO.Path]::GetFullPath($TargetRoot)
        runtime_root = [System.IO.Path]::GetFullPath($TargetRoot)
        canonical_vibe_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills\vibe'))
        created_paths = @($script:VgoCreatedPaths | Sort-Object)
        managed_json_paths = @($script:VgoManagedJsonPaths | Sort-Object)
        generated_from_template_if_absent = @($script:VgoTemplateGeneratedPaths | Sort-Object)
        specialist_wrapper_paths = @($script:VgoSpecialistWrapperPaths)
        external_fallback_used = @($ExternalFallbackUsed | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Sort-Object -Unique)
        managed_runtime_units = @('runtime-core')
        managed_runtime_skill_names = @($RuntimeManagedSkillNames | Sort-Object -CaseSensitive -Unique)
        managed_catalog_profiles = @($(if (-not [string]::IsNullOrWhiteSpace($CatalogProfile)) { $CatalogProfile }))
        managed_catalog_skill_names = @($CatalogManagedSkillNames | Sort-Object -CaseSensitive -Unique)
        managed_skill_names = @($managedSkillNames)
        packaging_manifest = [ordered]@{
            profile = [string]$Packaging['profile']
            package_id = [string]$Packaging['package_id']
            runtime_profile = [string]$Packaging['runtime_profile']
            catalog_profile = [string]$Packaging['catalog_profile']
            copy_bundled_skills = [bool]$Packaging['copy_bundled_skills']
        }
        timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        ownership_source = 'install-ledger'
    }

    $ledger | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ledgerPath -Encoding UTF8
    return [System.IO.Path]::GetFullPath($ledgerPath)
}

function Ensure-SkillPresent {
    param(
        [string]$Name,
        [bool]$Required,
        [object]$SourceCandidates = @(),
        [System.Collections.Generic.List[string]]$ExternalFallbackUsed,
        [System.Collections.Generic.List[string]]$MissingRequiredSkills
    )

    $Name = Get-VgoSafeSkillName -Value $Name -FieldName 'Ensure-SkillPresent'
    $targetSkillMd = Join-Path $TargetRoot ("skills\" + $Name + "\SKILL.md")
    if (Test-Path -LiteralPath $targetSkillMd) { return }

    foreach ($candidate in @($SourceCandidates)) {
        if ($null -eq $candidate) { continue }
        $src = [string]$candidate.source
        if ([string]::IsNullOrWhiteSpace($src) -or -not (Test-Path -LiteralPath $src)) {
            continue
        }
        $destination = Join-Path $TargetRoot ("skills\" + $Name)
        Copy-DirContent -Source $src -Destination $destination
        Restore-SkillEntryPointIfNeeded -SkillRoot $destination
        if ([bool]$candidate.is_external) {
            $ExternalFallbackUsed.Add($Name) | Out-Null
        }
        break
    }
    if (-not (Test-Path -LiteralPath $targetSkillMd)) {
        if ($Required) {
            $MissingRequiredSkills.Add($Name) | Out-Null
        }
    }
}

function Test-VgoShouldReplaceClaudePreToolUseHookEntry {
    param(
        [object]$Entry,
        [string]$ManagedDescription,
        [string]$HookCommand
    )

    if ($Entry -isnot [System.Collections.IDictionary]) {
        return $false
    }

    $existingCommand = ''
    if ($Entry.Contains('hooks') -and $Entry['hooks'] -is [System.Collections.IList] -and @($Entry['hooks']).Count -gt 0) {
        $firstHook = @($Entry['hooks'])[0]
        if ($firstHook -is [System.Collections.IDictionary] -and $firstHook.Contains('command')) {
            $existingCommand = [string]$firstHook['command']
            $existingCommand = $existingCommand.Trim()
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($existingCommand)) {
        return $existingCommand -eq $HookCommand
    }

    $description = ''
    if ($Entry.Contains('description')) {
        $description = [string]$Entry['description']
        $description = $description.Trim()
    }
    return (-not [string]::IsNullOrWhiteSpace($description)) -and $description -eq $ManagedDescription
}

function Update-VgoClaudePreToolUseHook {
    param(
        [hashtable]$Settings,
        [string]$HookCommand
    )

    $managedDescription = 'VibeSkills managed write guard'
    $hooks = @{}
    if ($Settings.ContainsKey('hooks') -and $Settings['hooks'] -is [System.Collections.IDictionary]) {
        foreach ($key in $Settings['hooks'].Keys) {
            $hooks[$key] = $Settings['hooks'][$key]
        }
    }

    $preToolUse = @()
    if ($hooks.ContainsKey('PreToolUse') -and $hooks['PreToolUse'] -is [System.Collections.IList]) {
        $preToolUse = @($hooks['PreToolUse'])
    }

    $managedEntry = [ordered]@{
        matcher = 'Write'
        hooks = @(
            [ordered]@{
                type = 'command'
                command = $HookCommand
            }
        )
        description = $managedDescription
    }

    $nextPreToolUse = New-Object System.Collections.Generic.List[object]
    $replaced = $false
    foreach ($entry in $preToolUse) {
        if (Test-VgoShouldReplaceClaudePreToolUseHookEntry -Entry $entry -ManagedDescription $managedDescription -HookCommand $HookCommand) {
            if (-not $replaced) {
                $nextPreToolUse.Add($managedEntry) | Out-Null
                $replaced = $true
            }
            continue
        }
        $nextPreToolUse.Add($entry) | Out-Null
    }
    if (-not $replaced) {
        $nextPreToolUse.Add($managedEntry) | Out-Null
    }

    $hooks['PreToolUse'] = $nextPreToolUse.ToArray()
    $Settings['hooks'] = $hooks
}

function Install-ClaudeManagedSettings {
    param(
        [string]$RepoRoot,
        [string]$TargetRoot
    )

    $settingsPath = Join-Path $TargetRoot 'settings.json'
    $createdIfAbsent = -not (Test-Path -LiteralPath $settingsPath -PathType Leaf)
    $settings = @{}
    if (-not $createdIfAbsent) {
        try {
            $parsed = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
        } catch {
            throw "Failed to parse JSON settings file: $settingsPath"
        }
        if ($parsed -isnot [System.Collections.IDictionary]) {
            throw "Expected JSON object in settings file: $settingsPath"
        }
        foreach ($key in $parsed.Keys) {
            $settings[$key] = $parsed[$key]
        }
    }

    $hooksRoot = Join-Path $TargetRoot 'hooks'
    New-Item -ItemType Directory -Force -Path $hooksRoot | Out-Null
    Add-VgoCreatedPath -Path $hooksRoot
    $hookPath = Join-Path $hooksRoot 'write-guard.js'
    $sourceHook = @(
        (Join-Path $RepoRoot 'hooks\write-guard.js'),
        $hookPath
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace([string]$sourceHook)) {
        throw 'Claude managed settings require hooks/write-guard.js in the runtime payload or the existing target hooks directory.'
    }
    if ([System.IO.Path]::GetFullPath($sourceHook) -ne [System.IO.Path]::GetFullPath($hookPath)) {
        Copy-Item -LiteralPath $sourceHook -Destination $hookPath -Force
    }
    Add-VgoCreatedPath -Path $hookPath

    $hookCommand = 'node ' + [System.IO.Path]::GetFullPath($hookPath)
    $settings['vibeskills'] = [ordered]@{
        managed = $true
        host_id = 'claude-code'
        skills_root = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
        runtime_skill_entry = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills\vibe\SKILL.md'))
        hooks_root = [System.IO.Path]::GetFullPath($hooksRoot)
        managed_hook_command = $hookCommand
        managed_hook_description = 'VibeSkills managed write guard'
        explicit_vibe_skill_invocation = @('/vibe', '$vibe')
    }
    Update-VgoClaudePreToolUseHook -Settings $settings -HookCommand $hookCommand
    $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsPath -Encoding UTF8

    if ($createdIfAbsent) {
        Add-VgoCreatedPath -Path $settingsPath
    }
    Add-VgoManagedJsonPath -Path $settingsPath
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
    $packaging = Get-VgoPackagingContract -Governance $governance -RepoRoot $RepoRoot
    $canonicalRoot = Join-Path $RepoRoot ([string]$governance.source_of_truth.canonical_root)
    $mirrorFiles = @($packaging.mirror.files)
    $mirrorDirs = @($packaging.mirror.directories)
    $targetVibeRoot = Join-Path $TargetRoot $TargetRel

    if ([System.IO.Path]::GetFullPath($canonicalRoot) -eq [System.IO.Path]::GetFullPath($targetVibeRoot)) {
        return
    }

    if (Test-Path -LiteralPath $targetVibeRoot) {
        Remove-Item -LiteralPath $targetVibeRoot -Recurse -Force
    }

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

    $packaging = if ($Governance.PSObject.Properties.Name -contains 'packaging') { $Governance.packaging } else { $null }
    $generated = if ($null -ne $packaging -and $packaging.PSObject.Properties.Name -contains 'generated_compatibility') { $packaging.generated_compatibility } else { $null }
    $nestedRuntime = if ($null -ne $generated -and $generated.PSObject.Properties.Name -contains 'nested_runtime_root') { $generated.nested_runtime_root } else { $null }
    $generatedRelativePath = if ($null -ne $nestedRuntime -and $nestedRuntime.PSObject.Properties.Name -contains 'relative_path') { [string]$nestedRuntime.relative_path } else { $null }
    $generatedMode = if ($null -ne $nestedRuntime -and $nestedRuntime.PSObject.Properties.Name -contains 'materialization_mode') { [string]$nestedRuntime.materialization_mode } else { $null }
    if (-not [string]::IsNullOrWhiteSpace($generatedRelativePath)) {
        if ([string]::IsNullOrWhiteSpace($generatedMode)) {
            $generatedMode = 'install_only'
        }
        if ($generatedMode -notin @('install_only', 'release_install_only')) {
            return $null
        }
        return $generatedRelativePath.Replace('\', '/').Trim('/').Replace('/', '\')
    }

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
        [string]$TargetRel = 'skills\vibe',
        [string[]]$ManagedSkillNames = @()
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

    $nestedSkillsRoot = Split-Path -Parent $nestedRoot
    $sourceSkillsRoot = Split-Path -Parent $targetVibeRoot
    if (Test-Path -LiteralPath $nestedSkillsRoot) {
        Remove-Item -LiteralPath $nestedSkillsRoot -Recurse -Force
    }

    $managedSkillSet = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($name in @($ManagedSkillNames)) {
        if (-not [string]::IsNullOrWhiteSpace([string]$name)) {
            $managedSkillSet.Add([string]$name) | Out-Null
        }
    }

    foreach ($skillDir in @(Get-ChildItem -LiteralPath $sourceSkillsRoot -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
        if ($skillDir.Name -eq (Split-Path -Leaf $targetVibeRoot)) {
            continue
        }
        if ($managedSkillSet.Count -gt 0 -and -not $managedSkillSet.Contains([string]$skillDir.Name)) {
            continue
        }
        $destination = Join-Path $nestedSkillsRoot $skillDir.Name
        Copy-DirContent -Source $skillDir.FullName -Destination $destination
        Convert-SkillEntryPointToRuntimeMirror -SkillRoot $destination
    }

    $packaging = Get-VgoPackagingContract -Governance $Governance -RepoRoot $targetVibeRoot
    $mirrorFiles = @($packaging.mirror.files)
    $mirrorDirs = @($packaging.mirror.directories)
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
    Convert-SkillEntryPointToRuntimeMirror -SkillRoot $nestedRoot
}

function Install-RuntimeCorePayload {
    param([psobject]$Adapter)

    $packaging = Get-VgoRuntimeCorePackaging -RepoRoot $RepoRoot -Profile $script:SelectedInstallProfile
    $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
    $governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json

    $includeCommandSurfaces = -not (Test-VgoSkillOnlyActivationHost -HostId ([string]$Adapter.id))
    $runtimeDirectories = @($packaging['directories'] | Where-Object { $includeCommandSurfaces -or [string]$_ -ne 'commands' })
    foreach ($dir in $runtimeDirectories) {
        New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot ([string]$dir)) | Out-Null
    }

    $copyDirectories = @($packaging['copy_directories'] | Where-Object { $includeCommandSurfaces -or [string]$_['target'] -ne 'commands' })
    $targetVibeRel = 'skills\vibe'
    if ($packaging.ContainsKey('canonical_vibe_payload') -and $packaging['canonical_vibe_payload']) {
        $configuredTargetRel = [string]$packaging['canonical_vibe_payload']['target_relpath']
        if (-not [string]::IsNullOrWhiteSpace($configuredTargetRel)) {
            $targetVibeRel = $configuredTargetRel
        }
    } elseif ($packaging.ContainsKey('canonical_vibe_mirror') -and $packaging['canonical_vibe_mirror']) {
        $configuredTargetRel = [string]$packaging['canonical_vibe_mirror']['target_relpath']
        if (-not [string]::IsNullOrWhiteSpace($configuredTargetRel)) {
            $targetVibeRel = $configuredTargetRel
        }
    }

    $excludeBundledSkillNames = New-Object System.Collections.Generic.List[string]
    foreach ($name in @($packaging['exclude_bundled_skill_names'])) {
        if (-not [string]::IsNullOrWhiteSpace([string]$name)) {
            $excludeBundledSkillNames.Add([string]$name) | Out-Null
        }
    }
    $canonicalVibeName = Split-Path -Leaf $targetVibeRel
    if ($excludeBundledSkillNames -notcontains $canonicalVibeName) {
        $excludeBundledSkillNames.Add($canonicalVibeName) | Out-Null
    }

    $bundledSkillsSourceRel = [string]$packaging['bundled_skills_source']
    if ([string]::IsNullOrWhiteSpace($bundledSkillsSourceRel)) {
        $bundledSkillsSourceRel = 'bundled/skills'
    }

    foreach ($entry in $copyDirectories) {
        $src = Join-Path $RepoRoot ([string]$entry['source'])
        if ([string]$entry['target'] -eq 'skills' -and [string]$entry['source'] -eq $bundledSkillsSourceRel) {
            $src = Join-Path $RepoRoot $bundledSkillsSourceRel
        }
        $dst = Join-Path $TargetRoot ([string]$entry['target'])
        if ([string]$entry['target'] -eq 'skills') {
            Copy-SkillRootsWithoutSelfShadow -Source $src -Destination $dst -RepoRoot $RepoRoot -ExcludeSkillNames @($excludeBundledSkillNames)
        } else {
            Copy-DirContent -Source $src -Destination $dst
        }
        if ([string]$entry['target'] -eq 'skills' -and (Test-Path -LiteralPath $dst -PathType Container)) {
            foreach ($skillDir in @(Get-ChildItem -LiteralPath $dst -Directory -ErrorAction SilentlyContinue)) {
                Restore-SkillEntryPointIfNeeded -SkillRoot $skillDir.FullName
            }
        }
    }

    foreach ($entry in @($packaging['copy_files'])) {
        $src = Join-Path $RepoRoot ([string]$entry['source'])
        $dst = Join-Path $TargetRoot ([string]$entry['target'])
        $optional = [bool]$entry['optional']
        if (-not (Test-Path -LiteralPath $src)) {
            if ($optional) { continue }
            throw "Runtime-core packaging source missing: $src"
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }

    Sync-VibeCanonicalToTarget -RepoRoot $RepoRoot -TargetRoot $TargetRoot -TargetRel $targetVibeRel

    $repoOwnedRoots = @(Get-VgoRepoOwnedSkillSourceRoots -RepoRoot $RepoRoot)
    $externalRoots = @(Get-VgoExternalSkillSourceRoots -RepoRoot $RepoRoot)
    $requiredCore = @('dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')
    $externalFallbackUsed = New-Object System.Collections.Generic.List[string]
    $missingRequiredSkills = New-Object System.Collections.Generic.List[string]

    foreach ($name in $requiredCore) {
        $sourceCandidates = @()
        foreach ($root in $repoOwnedRoots) {
            $sourceCandidates += [pscustomobject]@{ source = (Join-Path $root $name); is_external = $false }
        }
        if ($AllowExternalSkillFallback) {
            foreach ($root in $externalRoots) {
                $sourceCandidates += [pscustomobject]@{ source = (Join-Path $root $name); is_external = $true }
            }
        }
        Ensure-SkillPresent -Name $name -Required $true -SourceCandidates $sourceCandidates -ExternalFallbackUsed $externalFallbackUsed -MissingRequiredSkills $missingRequiredSkills
    }

    if ($missingRequiredSkills.Count -gt 0) {
        $missing = ($missingRequiredSkills | Select-Object -Unique) -join ', '
        throw "Missing required vendored skills: $missing"
    }

    $runtimeManagedSkillNames = @(
        Get-VgoDesiredRuntimeManagedSkillNames -Packaging $packaging |
            Where-Object { Test-Path -LiteralPath (Join-Path $TargetRoot ("skills\" + $_)) -PathType Container }
    )

    return [pscustomobject]@{
        mode = [string]$Adapter.install_mode
        packaging = $packaging
        catalog_profile = [string]$packaging['catalog_profile']
        governance = $governance
        external_fallback_used = @($externalFallbackUsed | Select-Object -Unique)
        runtime_managed_skill_names = @($runtimeManagedSkillNames | Sort-Object -CaseSensitive -Unique)
        target_vibe_rel = $targetVibeRel
    }
}

function Install-SkillCatalogPayload {
    param([string]$CatalogProfile)

    if ([string]::IsNullOrWhiteSpace($CatalogProfile)) {
        $CatalogProfile = Get-VgoDefaultCatalogProfileId -Profile $script:SelectedInstallProfile
    }

    $catalogPackagingInfo = Get-VgoSkillCatalogPackaging -RepoRoot $RepoRoot -TargetRoot $TargetRoot
    $catalogPackaging = $catalogPackagingInfo.packaging
    $catalogBaseRoot = [string]$catalogPackagingInfo.base_root
    $bundledRoot = Get-VgoSkillCatalogRoot -RepoRoot $RepoRoot -CatalogPackaging $catalogPackaging
    $installedCatalogSource = Get-VgoInstalledRuntimeCatalogSourceInfo -RepoRoot $RepoRoot
    $catalogSourceRoot = $bundledRoot
    $bundledSkillNames = @()
    if ($installedCatalogSource) {
        $catalogSourceRoot = [string]$installedCatalogSource.catalog_root
        $bundledSkillNames = @($installedCatalogSource.bundled_skill_names)
    }
    $desiredSkillNames = Resolve-VgoCatalogProfileSkillNames -CatalogBaseRoot $catalogBaseRoot -CatalogPackaging $catalogPackaging -ProfileId $CatalogProfile -CatalogRoot $catalogSourceRoot -BundledSkillNames $bundledSkillNames -Seen ([System.Collections.Generic.HashSet[string]]::new())
    if (@($desiredSkillNames).Count -eq 0) {
        return [pscustomobject]@{
            catalog_packaging = $catalogPackaging
            external_fallback_used = @()
            managed_skill_names = @()
        }
    }

    $externalRoots = @(Get-VgoExternalSkillSourceRoots -RepoRoot $RepoRoot)
    $externalFallbackUsed = New-Object System.Collections.Generic.List[string]
    $missingRequiredSkills = New-Object System.Collections.Generic.List[string]

    foreach ($name in @($desiredSkillNames | Sort-Object)) {
        $sourceCandidates = @([pscustomobject]@{ source = (Join-Path $catalogSourceRoot $name); is_external = $false })
        if ($AllowExternalSkillFallback) {
            foreach ($root in $externalRoots) {
                if ([System.IO.Path]::GetFullPath($root) -eq [System.IO.Path]::GetFullPath($catalogSourceRoot)) {
                    continue
                }
                $sourceCandidates += [pscustomobject]@{ source = (Join-Path $root $name); is_external = $true }
            }
        }
        Ensure-SkillPresent -Name $name -Required $true -SourceCandidates $sourceCandidates -ExternalFallbackUsed $externalFallbackUsed -MissingRequiredSkills $missingRequiredSkills
    }

    if ($missingRequiredSkills.Count -gt 0) {
        $missing = ($missingRequiredSkills | Select-Object -Unique) -join ', '
        throw "Missing required catalog skills: $missing"
    }

    $managedSkillNames = @(
        $desiredSkillNames |
            Sort-Object |
            Where-Object { Test-Path -LiteralPath (Join-Path $TargetRoot ("skills\" + $_)) -PathType Container }
    )

    return [pscustomobject]@{
        catalog_packaging = $catalogPackaging
        external_fallback_used = @($externalFallbackUsed | Select-Object -Unique)
        managed_skill_names = @($managedSkillNames | Sort-Object -CaseSensitive -Unique)
    }
}

function Install-GovernedCodexPayload {
    Copy-DirContent -Source (Join-Path $RepoRoot 'rules') -Destination (Join-Path $TargetRoot 'rules')
    Copy-DirContent -Source (Join-Path $RepoRoot 'agents\templates') -Destination (Join-Path $TargetRoot 'agents\templates')
    Copy-DirContent -Source (Join-Path $RepoRoot 'mcp') -Destination (Join-Path $TargetRoot 'mcp')
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetRoot 'config') | Out-Null
    Add-VgoCreatedPath -Path (Join-Path $TargetRoot 'config')
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\plugins-manifest.codex.json') -Destination (Join-Path $TargetRoot 'config\plugins-manifest.codex.json') -Force
    Add-VgoCreatedPath -Path (Join-Path $TargetRoot 'config\plugins-manifest.codex.json')

    $settingsPath = Join-Path $TargetRoot 'settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\settings.template.codex.json') -Destination $settingsPath -Force
        Add-VgoTemplateGeneratedPath -Path $settingsPath
    }
    Add-VgoCreatedPath -Path $settingsPath
    Add-VgoManagedJsonPath -Path $settingsPath
}

function Install-ClaudeGuidancePayload {
    Install-ClaudeManagedSettings -RepoRoot $RepoRoot -TargetRoot $TargetRoot
}

function Install-CursorGuidancePayload {
}

function Install-OpenCodeGuidancePayload {
    $exampleConfig = Join-Path $RepoRoot 'config\opencode\opencode.json.example'
    if (Test-Path -LiteralPath $exampleConfig) {
        $destination = Join-Path $TargetRoot 'opencode.json.example'
        Copy-Item -LiteralPath $exampleConfig -Destination $destination -Force
        Add-VgoCreatedPath -Path $destination
    }
}

function Install-RuntimeCoreModePayload {
    param([psobject]$Adapter)

    if (Test-VgoSkillOnlyActivationHost -HostId ([string]$Adapter.id)) {
        return
    }

    $commandsRoot = Join-Path $RepoRoot 'commands'
    if (Test-Path -LiteralPath $commandsRoot) {
        $workflowRoot = Join-Path $TargetRoot 'global_workflows'
        Copy-DirContent -Source $commandsRoot -Destination $workflowRoot
        Add-VgoCreatedPath -Path $workflowRoot
    }

    $mcpTemplate = Join-Path $RepoRoot 'mcp\servers.template.json'
    $mcpConfigPath = Join-Path $TargetRoot 'mcp_config.json'
    if ((Test-Path -LiteralPath $mcpTemplate) -and -not (Test-Path -LiteralPath $mcpConfigPath)) {
        Copy-Item -LiteralPath $mcpTemplate -Destination $mcpConfigPath -Force
        Add-VgoCreatedPath -Path $mcpConfigPath
        Add-VgoManagedJsonPath -Path $mcpConfigPath
        Add-VgoTemplateGeneratedPath -Path $mcpConfigPath
    }
}

Add-VgoCreatedPath -Path $TargetRoot
$adapter = Resolve-VgoAdapterDescriptor -RepoRoot $RepoRoot -HostId $HostId
$previousLedger = Get-VgoExistingInstallLedger -TargetRoot $TargetRoot
$runtimeResult = Install-RuntimeCorePayload -Adapter $adapter
$catalogProfile = [string]$runtimeResult.catalog_profile
$catalogProfile = $catalogProfile.Trim()
if ([string]::IsNullOrWhiteSpace($catalogProfile)) {
    $catalogProfile = Get-VgoDefaultCatalogProfileId -Profile $script:SelectedInstallProfile
}
Sync-VgoCatalogRuntimeSupportFiles -RepoRoot $RepoRoot
$catalogResult = Install-SkillCatalogPayload -CatalogProfile $catalogProfile
$legacyOpenCodeConfigCleanup = $null
switch ([string]$adapter.install_mode) {
    'governed' { Install-GovernedCodexPayload }
    'preview-guidance' {
        if ([string]$adapter.id -eq 'opencode') {
            Install-OpenCodeGuidancePayload
        } elseif ([string]$adapter.id -eq 'claude-code') {
            Install-ClaudeGuidancePayload
        } elseif ([string]$adapter.id -eq 'cursor') {
            Install-CursorGuidancePayload
        } else {
            throw "Unsupported preview-guidance adapter id: $($adapter.id)"
        }
    }
    'runtime-core' {
        Install-RuntimeCoreModePayload -Adapter $adapter
    }
    default { throw "Unsupported adapter install mode: $($adapter.install_mode)" }
}

$currentManagedSkillNames = @(
    @($runtimeResult.runtime_managed_skill_names + $catalogResult.managed_skill_names) |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
        Sort-Object -CaseSensitive -Unique
)
Remove-VgoPreviouslyManagedSkillDirs `
    -TargetRoot $TargetRoot `
    -PreviousManagedSkillNames (Get-VgoManagedSkillNamesFromLedger -Ledger $previousLedger -TargetRoot $TargetRoot) `
    -CurrentManagedSkillNames $currentManagedSkillNames

Sync-InstalledGeneratedNestedCompatibilityRoot -Governance $runtimeResult.governance -TargetRoot $TargetRoot -TargetRel $runtimeResult.target_vibe_rel -ManagedSkillNames @($runtimeResult.runtime_managed_skill_names)

$closureReceipt = Write-VgoHostClosure -TargetRoot $TargetRoot -Adapter $adapter
$requireClosedReadyEffective = [bool]($RequireClosedReady -and (Test-VgoClosedReadyRequiredForAdapter -Adapter $adapter))
if ($requireClosedReadyEffective -and [string]$closureReceipt.data.host_closure_state -ne 'closed_ready') {
    throw ("Host closure for '{0}' is not closed_ready (got '{1}'). Configure the host specialist bridge command first, then retry install." -f [string]$adapter.id, [string]$closureReceipt.data.host_closure_state)
}
$combinedExternalFallbackUsed = @($runtimeResult.external_fallback_used + $catalogResult.external_fallback_used | Sort-Object -Unique)
$installLedgerPath = Write-VgoInstallLedger `
    -Adapter $adapter `
    -Profile $script:SelectedInstallProfile `
    -Packaging $runtimeResult.packaging `
    -RuntimeManagedSkillNames @($runtimeResult.runtime_managed_skill_names) `
    -CatalogProfile $catalogProfile `
    -CatalogManagedSkillNames @($catalogResult.managed_skill_names) `
    -ExternalFallbackUsed $combinedExternalFallbackUsed

[pscustomobject]@{
    host_id = [string]$adapter.id
    install_mode = [string]$adapter.install_mode
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    external_fallback_used = @($combinedExternalFallbackUsed)
    host_closure_path = [string]$closureReceipt.path
    host_closure_state = [string]$closureReceipt.data.host_closure_state
    install_ledger_path = [string]$installLedgerPath
    settings_materialized = @($closureReceipt.data.settings_materialized)
    legacy_opencode_config_cleanup = $legacyOpenCodeConfigCleanup
    specialist_wrapper_ready = [bool]$closureReceipt.data.specialist_wrapper.ready
    require_closed_ready_requested = [bool]$RequireClosedReady
    require_closed_ready_effective = $requireClosedReadyEffective
} | ConvertTo-Json -Depth 10
