Set-StrictMode -Version Latest

$script:VgoGovernanceHelpersRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function New-VgoUtf8NoBomEncoding {
    return [System.Text.UTF8Encoding]::new($false)
}

function Write-VgoUtf8NoBomText {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [AllowEmptyString()] [string]$Content
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    [System.IO.File]::WriteAllText($Path, $Content, (New-VgoUtf8NoBomEncoding))
}

function Append-VgoUtf8NoBomText {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [AllowEmptyString()] [string]$Content
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    [System.IO.File]::AppendAllText($Path, $Content, (New-VgoUtf8NoBomEncoding))
}

function Test-VgoUtf8BomBytes {
    param([byte[]]$Bytes)
    return ($null -ne $Bytes -and $Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF)
}

function Get-VgoFileBomInfo {
    param([Parameter(Mandatory)] [string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    return [pscustomobject]@{
        path = [System.IO.Path]::GetFullPath($Path)
        has_utf8_bom = [bool](Test-VgoUtf8BomBytes -Bytes $bytes)
        byte_count = [int]$bytes.Length
        first_three_hex = if ($bytes.Length -ge 3) { ('{0:X2}{1:X2}{2:X2}' -f $bytes[0], $bytes[1], $bytes[2]) } else { $null }
    }
}

function ConvertTo-VgoFullPath {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [string]$RelativePath
    )

    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $RelativePath))
}

function Test-VgoPathWithin {
    param(
        [Parameter(Mandatory)] [string]$ParentPath,
        [Parameter(Mandatory)] [string]$ChildPath
    )

    if ([string]::IsNullOrWhiteSpace($ParentPath) -or [string]::IsNullOrWhiteSpace($ChildPath)) {
        return $false
    }

    $parentFull = [System.IO.Path]::GetFullPath($ParentPath)
    $childFull = [System.IO.Path]::GetFullPath($ChildPath)
    if (-not $parentFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $parentFull += [System.IO.Path]::DirectorySeparatorChar
    }

    return $childFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Resolve-VgoRepoRoot {
    param(
        [Parameter(Mandatory)] [string]$StartPath
    )

    $resolved = Resolve-Path -LiteralPath $StartPath -ErrorAction Stop
    $current = [string]$resolved.Path
    if (Test-Path -LiteralPath $current -PathType Leaf) {
        $current = Split-Path -Parent $current
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        $governancePath = Join-Path $current 'config\version-governance.json'
        if (Test-Path -LiteralPath $governancePath) {
            [void]$candidates.Add([System.IO.Path]::GetFullPath($current))
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    if ($candidates.Count -eq 0) {
        throw "Unable to resolve VCO repo root from: $StartPath"
    }

    $gitCandidates = @($candidates | Where-Object { Test-Path -LiteralPath (Join-Path $_ '.git') })
    if ($gitCandidates.Count -gt 0) {
        # Prefer the nearest governed git root so runtime entrypoints executed from
        # worktrees resolve to the active governed tree rather than the outer source repo.
        return [System.IO.Path]::GetFullPath($gitCandidates[0])
    }

    # In installed-host layouts the outer target root may also carry a config directory.
    # Without a git root, prefer the nearest governed root to the executing script so
    # installed runtime entrypoints resolve to skills/vibe instead of the host target.
    return [System.IO.Path]::GetFullPath($candidates[0])
}

function Get-VgoParentPath {
    param(
        [AllowEmptyString()] [string]$Path,
        [switch]$AllowFilesystemRoot
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ''
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath($Path)
    } catch {
        return ''
    }

    $parent = Split-Path -Parent $fullPath
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $fullPath) {
        return ''
    }

    try {
        $parentFull = [System.IO.Path]::GetFullPath($parent)
    } catch {
        return ''
    }

    $root = [System.IO.Path]::GetPathRoot($parentFull)
    if (-not $AllowFilesystemRoot -and -not [string]::IsNullOrWhiteSpace($root) -and $parentFull -eq $root) {
        return ''
    }

    return $parentFull
}

function Test-VgoCanonicalRepoExecution {
    param(
        [AllowEmptyString()] [string]$StartPath
    )

    if ([string]::IsNullOrWhiteSpace($StartPath)) {
        return $false
    }

    try {
        $repoRoot = Resolve-VgoRepoRoot -StartPath $StartPath
    } catch {
        return $false
    }

    return (Test-Path -LiteralPath (Join-Path $repoRoot '.git'))
}

function Read-VgoJsonFile {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Get-VgoOperatorPreviewStringListProperty {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$OperatorId,
        [Parameter(Mandatory)] [string]$PropertyName
    )

    $contractPath = Join-Path $RepoRoot 'config\operator-preview-contract.json'
    if (-not (Test-Path -LiteralPath $contractPath)) {
        return @()
    }

    try {
        $contract = Read-VgoJsonFile -Path $contractPath
    } catch {
        return @()
    }

    if ($null -eq $contract -or
        $contract.PSObject.Properties.Name -notcontains 'operators' -or
        $null -eq $contract.operators) {
        return @()
    }

    $operators = $contract.operators
    $operator = $null
    if ($operators -is [System.Collections.IDictionary]) {
        if ($operators.Contains($OperatorId)) {
            $operator = $operators[$OperatorId]
        }
    } elseif ($null -ne $operators.PSObject -and $operators.PSObject.Properties.Name -contains $OperatorId) {
        $operator = $operators.$OperatorId
    }

    if ($null -eq $operator -or
        $operator.PSObject.Properties.Name -notcontains $PropertyName -or
        $null -eq $operator.$PropertyName) {
        return @()
    }

    return @($operator.$PropertyName | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
}

function Get-VgoAdapterRegistryPayload {
    param(
        [AllowEmptyString()] [string]$StartPath = ''
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($StartPath)) {
        [void]$candidates.Add($StartPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($script:VgoGovernanceHelpersRoot)) {
        [void]$candidates.Add($script:VgoGovernanceHelpersRoot)
    }

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        $current = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath $current -PathType Leaf) {
            $current = Split-Path -Parent $current
        }

        while (-not [string]::IsNullOrWhiteSpace($current)) {
            foreach ($relativePath in @('config\adapter-registry.json', 'adapters\index.json')) {
                $registryPath = Join-Path $current $relativePath
                if (Test-Path -LiteralPath $registryPath) {
                    return (Read-VgoJsonFile -Path $registryPath)
                }
            }

            $parent = Split-Path -Parent $current
            if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
                break
            }
            $current = $parent
        }
    }

    throw 'Unable to resolve adapter registry for VGO governance helpers.'
}

function Resolve-VgoHostCatalog {
    param(
        [AllowEmptyString()] [string]$StartPath = ''
    )

    $registry = Get-VgoAdapterRegistryPayload -StartPath $StartPath
    $entries = @{}
    $aliases = @{}

    foreach ($alias in $registry.aliases.PSObject.Properties) {
        $aliases[[string]$alias.Name] = [string]$alias.Value
    }

    foreach ($adapter in @($registry.adapters)) {
        $hostName = [string]$adapter.id
        $hostProfile = $null
        if ($adapter.PSObject.Properties.Name -contains 'host_profile' -and -not [string]::IsNullOrWhiteSpace([string]$adapter.host_profile)) {
            $profilePath = Join-Path (Resolve-VgoRepoRoot -StartPath $script:VgoGovernanceHelpersRoot) ([string]$adapter.host_profile)
            if (Test-Path -LiteralPath $profilePath) {
                try {
                    $hostProfile = Read-VgoJsonFile -Path $profilePath
                } catch {
                    $hostProfile = $null
                }
            }
        }
        if ($null -ne $hostProfile -and $hostProfile.PSObject.Properties.Name -contains 'host_name' -and -not [string]::IsNullOrWhiteSpace([string]$hostProfile.host_name)) {
            $hostName = [string]$hostProfile.host_name
        }

        $entries[[string]$adapter.id] = [pscustomobject]@{
            id = [string]$adapter.id
            host_name = $hostName
            env = if ($adapter.default_target_root.PSObject.Properties.Name -contains 'env') { [string]$adapter.default_target_root.env } else { '' }
            rel = if ($adapter.default_target_root.PSObject.Properties.Name -contains 'rel') { [string]$adapter.default_target_root.rel } else { '' }
            kind = if ($adapter.default_target_root.PSObject.Properties.Name -contains 'kind') { [string]$adapter.default_target_root.kind } else { '' }
        }
    }

    $entries['generic'] = [pscustomobject]@{
        id = 'generic'
        host_name = 'Generic Host'
        env = ''
        rel = '.vibe-skills/generic'
        kind = 'host-home'
    }

    if (-not $aliases.Contains('claude')) {
        $aliases['claude'] = 'claude-code'
    }

    return [pscustomobject]@{
        default_adapter_id = [string]$registry.default_adapter_id
        entries = $entries
        aliases = $aliases
    }
}

function Get-VgoBootstrapSummary {
    param(
        [Parameter(Mandatory)] [psobject]$Adapter
    )

    if ($Adapter.PSObject.Properties.Name -contains 'bootstrap_summary' -and -not [string]::IsNullOrWhiteSpace([string]$Adapter.bootstrap_summary)) {
        return [string]$Adapter.bootstrap_summary
    }

    switch ([string]$Adapter.id) {
        'codex' { return 'strongest governed lane' }
        'windsurf' { return 'supported path + runtime adapter' }
        'openclaw' { return 'preview runtime-core adapter' }
        'opencode' { return 'preview guidance adapter' }
        default { return 'supported install/use path' }
    }
}

function Get-VgoBootstrapHostChoices {
    param(
        [AllowEmptyString()] [string]$StartPath = ''
    )

    $registry = Get-VgoAdapterRegistryPayload -StartPath $StartPath
    $choices = New-Object System.Collections.Generic.List[object]
    $index = 1

    foreach ($adapter in @($registry.adapters)) {
        $hostId = [string]$adapter.id
        if ([string]::IsNullOrWhiteSpace($hostId)) {
            continue
        }

        $aliases = New-Object System.Collections.Generic.List[string]
        [void]$aliases.Add($hostId)
        if ($registry.PSObject.Properties.Name -contains 'aliases' -and $null -ne $registry.aliases) {
            foreach ($alias in $registry.aliases.PSObject.Properties) {
                if ([string]$alias.Value -eq $hostId -and -not $aliases.Contains([string]$alias.Name)) {
                    [void]$aliases.Add([string]$alias.Name)
                }
            }
        }

        [void]$choices.Add([pscustomobject]@{
            index = $index
            id = $hostId
            summary = Get-VgoBootstrapSummary -Adapter $adapter
            aliases = @($aliases)
        })
        $index += 1
    }

    return $choices.ToArray()
}

function Get-VgoSupportedHostList {
    param(
        [AllowEmptyString()] [string]$StartPath = ''
    )

    return @((Get-VgoBootstrapHostChoices -StartPath $StartPath) | ForEach-Object { [string]$_.id })
}

function Get-VgoSupportedHostHint {
    param(
        [AllowEmptyString()] [string]$StartPath = ''
    )

    return ((Get-VgoSupportedHostList -StartPath $StartPath) -join '|')
}

function Test-VgoTargetRootMatchesRelativeSignature {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$RelativeSignature
    )

    $normalizedTarget = [System.IO.Path]::GetFullPath($TargetRoot).Replace('\', '/').TrimEnd('/').ToLowerInvariant()
    $normalizedSignature = ([string]$RelativeSignature).Replace('\', '/').Trim('/').ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($normalizedSignature)) {
        return $false
    }

    $leaf = Split-Path -Leaf $normalizedTarget
    if ($normalizedSignature -notlike '*/*') {
        return ($leaf -eq $normalizedSignature) -or $normalizedTarget.EndsWith('/' + $normalizedSignature)
    }

    return $normalizedTarget.EndsWith('/' + $normalizedSignature)
}

function Resolve-VgoHomeDirectory {
    param(
        [AllowEmptyString()] [string]$HomePath = ''
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($HomePath)) {
        [void]$candidates.Add($HomePath)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HOME)) {
        [void]$candidates.Add($env:HOME)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        [void]$candidates.Add($env:USERPROFILE)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HOMEDRIVE) -and -not [string]::IsNullOrWhiteSpace($env:HOMEPATH)) {
        [void]$candidates.Add(($env:HOMEDRIVE + $env:HOMEPATH))
    }

    try {
        $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
        if (-not [string]::IsNullOrWhiteSpace($userProfile)) {
            [void]$candidates.Add($userProfile)
        }
    } catch {
    }

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        try {
            return [System.IO.Path]::GetFullPath($candidate)
        } catch {
            continue
        }
    }

    throw 'Unable to resolve a platform-neutral user home directory.'
}

function Resolve-VgoAdapterEntry {
    param(
        [AllowEmptyString()] [string]$StartPath = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    $registry = Get-VgoAdapterRegistryPayload -StartPath $StartPath
    $requestedHostId = $HostId
    $resolvedHostId = Resolve-VgoHostId -HostId $requestedHostId
    $adapter = @($registry.adapters | Where-Object { [string]$_.id -eq $resolvedHostId } | Select-Object -First 1)[0]
    if ($null -eq $adapter) {
        throw "Unsupported VCO host id: $resolvedHostId"
    }

    return [pscustomobject]@{
        requested_id = if ([string]::IsNullOrWhiteSpace($requestedHostId)) { $null } else { [string]$requestedHostId }
        id = [string]$adapter.id
        status = if ($adapter.PSObject.Properties.Name -contains 'status') { [string]$adapter.status } else { $null }
        install_mode = if ($adapter.PSObject.Properties.Name -contains 'install_mode') { [string]$adapter.install_mode } else { $null }
        check_mode = if ($adapter.PSObject.Properties.Name -contains 'check_mode') { [string]$adapter.check_mode } else { $null }
        bootstrap_mode = if ($adapter.PSObject.Properties.Name -contains 'bootstrap_mode') { [string]$adapter.bootstrap_mode } else { $null }
        default_target_root = if ($adapter.PSObject.Properties.Name -contains 'default_target_root') { $adapter.default_target_root } else { $null }
        host_profile = if ($adapter.PSObject.Properties.Name -contains 'host_profile') { [string]$adapter.host_profile } else { $null }
        settings_map = if ($adapter.PSObject.Properties.Name -contains 'settings_map') { [string]$adapter.settings_map } else { $null }
        closure = if ($adapter.PSObject.Properties.Name -contains 'closure') { [string]$adapter.closure } else { $null }
        manifest = if ($adapter.PSObject.Properties.Name -contains 'manifest') { [string]$adapter.manifest } else { $null }
    }
}

function Resolve-VgoHostId {
    param(
        [AllowEmptyString()] [string]$HostId = ''
    )

    $catalog = Resolve-VgoHostCatalog -StartPath $script:VgoGovernanceHelpersRoot
    $resolved = $HostId
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        $resolved = $env:VCO_HOST_ID
    }
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        $resolved = if (-not [string]::IsNullOrWhiteSpace([string]$catalog.default_adapter_id)) { [string]$catalog.default_adapter_id } else { 'codex' }
    }

    $normalized = $resolved.Trim().ToLowerInvariant()
    if ($catalog.aliases.Contains($normalized)) {
        $normalized = [string]$catalog.aliases[$normalized]
    }

    if ($catalog.entries.Contains($normalized)) {
        return $normalized
    }

    $supported = @($catalog.entries.Keys | Sort-Object)
    throw "Unsupported VCO host id: $resolved. Supported values: $($supported -join ', ')"
}

function Resolve-VgoDefaultTargetRoot {
    param(
        [AllowEmptyString()] [string]$HostId = ''
    )

    $resolvedHostId = Resolve-VgoHostId -HostId $HostId
    $catalog = Resolve-VgoHostCatalog -StartPath $script:VgoGovernanceHelpersRoot
    $entry = $catalog.entries[$resolvedHostId]
    if ($null -eq $entry) {
        throw "Unsupported VCO host id: $resolvedHostId"
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$entry.env)) {
        $envValue = [Environment]::GetEnvironmentVariable([string]$entry.env)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            return [System.IO.Path]::GetFullPath($envValue)
        }
    }

    $homeDir = Resolve-VgoHomeDirectory
    return [System.IO.Path]::GetFullPath((Join-Path $homeDir ([string]$entry.rel)))
}

function Resolve-VgoTargetRoot {
    param(
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) {
        return [System.IO.Path]::GetFullPath($TargetRoot)
    }

    return Resolve-VgoDefaultTargetRoot -HostId $HostId
}

function Assert-VgoOfficialRuntimeHost {
    param(
        [AllowEmptyString()] [string]$HostId = ''
    )

    $resolvedHostId = Resolve-VgoHostId -HostId $HostId
    if ($resolvedHostId -ne 'codex') {
        throw ([string]::Format(
            "The governed install/check closure lane currently supports only host='codex'. For host='{0}', use the matching supported host path instead of claiming governed closure.",
            $resolvedHostId
        ))
    }
}

function Assert-VgoTargetRootMatchesHostIntent {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [AllowEmptyString()] [string]$HostId = ''
    )

    $resolvedHostId = Resolve-VgoHostId -HostId $HostId
    $catalog = Resolve-VgoHostCatalog -StartPath $script:VgoGovernanceHelpersRoot
    $currentEntry = $catalog.entries[$resolvedHostId]
    if ($null -eq $currentEntry) {
        throw "Unsupported VCO host id: $resolvedHostId"
    }

    foreach ($entry in @($catalog.entries.Values)) {
        if ([string]$entry.id -eq $resolvedHostId) {
            continue
        }
        if ([string]$entry.id -eq 'generic') {
            continue
        }

        $signatures = @([string]$entry.rel)
        if ([string]$entry.id -eq 'opencode') {
            $signatures += '.opencode'
        }

        foreach ($signature in $signatures) {
            if (-not (Test-VgoTargetRootMatchesRelativeSignature -TargetRoot $TargetRoot -RelativeSignature $signature)) {
                continue
            }

            if ($resolvedHostId -eq 'generic') {
                throw ([string]::Format(
                    "TargetRoot '{0}' looks like a host-native root ({1}), but HostId resolved to 'generic'. Use a neutral generic target root instead.",
                    $TargetRoot,
                    [string]$entry.host_name
                ))
            }

            throw ([string]::Format(
                "TargetRoot '{0}' looks like a {1} root, but HostId resolved to '{2}'. Pass the matching host id or use a {3} target root.",
                $TargetRoot,
                [string]$entry.host_name,
                $resolvedHostId,
                [string]$currentEntry.host_name
            ))
        }
    }
}

function Resolve-VgoInstalledSkillsRoot {
    param(
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId) 'skills'))
}

function Resolve-VgoExternalRoot {
    param(
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId) '_external'))
}

function Resolve-VgoPathSpec {
    param(
        [AllowEmptyString()] [string]$PathSpec = '',
        [AllowEmptyString()] [string]$RepoRoot = '',
        [AllowEmptyString()] [string]$TargetRoot = '',
        [AllowEmptyString()] [string]$HostId = ''
    )

    if ([string]::IsNullOrWhiteSpace($PathSpec)) {
        return ''
    }

    $expanded = [string]$PathSpec
    $codexRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
    $skillsRoot = Resolve-VgoInstalledSkillsRoot -TargetRoot $TargetRoot -HostId $HostId
    $externalRoot = Resolve-VgoExternalRoot -TargetRoot $TargetRoot -HostId $HostId

    $expanded = $expanded.Replace('${CODEX_HOME}', $codexRoot)
    $expanded = $expanded.Replace('${CODEX_SKILLS_ROOT}', $skillsRoot)
    $expanded = $expanded.Replace('${VCO_EXTERNAL_ROOT}', $externalRoot)

    if ($expanded -eq '~') {
        return (Resolve-VgoHomeDirectory)
    }
    if ($expanded.StartsWith('~/') -or $expanded.StartsWith('~\')) {
        $suffix = $expanded.Substring(2)
        return [System.IO.Path]::GetFullPath((Join-Path (Resolve-VgoHomeDirectory) $suffix))
    }

    if ([System.IO.Path]::IsPathRooted($expanded)) {
        return [System.IO.Path]::GetFullPath($expanded)
    }

    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $expanded))
    }

    return [System.IO.Path]::GetFullPath($expanded)
}

function Get-VgoPowerShellCommand {
    $currentProcessPath = $null
    try {
        $currentProcessPath = (Get-Process -Id $PID -ErrorAction Stop).Path
    } catch {
        $currentProcessPath = $null
    }

    $candidates = @(
        $currentProcessPath,
        (Join-Path $PSHOME 'pwsh.exe'),
        (Join-Path $PSHOME 'pwsh'),
        (Join-Path $PSHOME 'powershell.exe'),
        (Join-Path $PSHOME 'powershell'),
        (Get-Command pwsh -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command powershell -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command pwsh.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command powershell.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        if (Test-Path -LiteralPath $candidate) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }

    throw 'Unable to resolve a PowerShell host for governed sub-process execution.'
}

function Test-VgoWindowsAppsPythonStubPath {
    param(
        [AllowEmptyString()] [string]$Path,
        [AllowEmptyString()] [string]$CommandName = ''
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    $normalizedCommand = if ($null -eq $CommandName) { '' } else { ([string]$CommandName).Trim().ToLowerInvariant() }
    if ($normalizedCommand -notin @('python', 'python3')) {
        return $false
    }

    $normalizedPath = [string]$Path
    return $normalizedPath -match '(^|[\\/])Microsoft[\\/]WindowsApps[\\/].*python3?(\.(exe|cmd|bat))?$'
}

function Resolve-VgoPythonCandidate {
    param(
        [Parameter(Mandatory)] [string]$CommandName,
        [string[]]$PrefixArguments = @()
    )

    $candidates = @(Get-Command $CommandName -All -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate) -or -not (Test-Path -LiteralPath $candidate)) {
            continue
        }

        if (Test-VgoWindowsAppsPythonStubPath -Path $candidate -CommandName $CommandName) {
            continue
        }

        return [pscustomobject]@{
            host_path = [System.IO.Path]::GetFullPath($candidate)
            host_leaf = [System.IO.Path]::GetFileName($candidate).ToLowerInvariant()
            prefix_arguments = @($PrefixArguments)
        }
    }

    return $null
}

function Get-VgoPythonCommand {
    $python3 = Resolve-VgoPythonCandidate -CommandName 'python3'
    if ($null -ne $python3) {
        return $python3
    }

    $python = Resolve-VgoPythonCandidate -CommandName 'python'
    if ($null -ne $python) {
        return $python
    }

    $pyLauncher = Resolve-VgoPythonCandidate -CommandName 'py' -PrefixArguments @('-3')
    if ($null -ne $pyLauncher) {
        return $pyLauncher
    }

    throw "Unable to resolve a Python host for governed execution. Tried 'python', 'python3', and 'py -3'."
}

function Resolve-VgoPythonCommandSpec {
    param(
        [AllowEmptyString()] [string]$Command = ''
    )

    $normalized = if ($null -eq $Command) { '' } else { ([string]$Command).Trim() }
    if ([string]::IsNullOrWhiteSpace($normalized) -or $normalized -in @('python', 'python3', 'py', '${VGO_PYTHON}')) {
        return Get-VgoPythonCommand
    }

    if ([System.IO.Path]::IsPathRooted($normalized) -and (Test-Path -LiteralPath $normalized)) {
        return [pscustomobject]@{
            host_path = [System.IO.Path]::GetFullPath($normalized)
            host_leaf = [System.IO.Path]::GetFileName($normalized).ToLowerInvariant()
            prefix_arguments = @()
        }
    }

    $resolved = Get-Command $normalized -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
    if (-not [string]::IsNullOrWhiteSpace($resolved) -and (Test-Path -LiteralPath $resolved)) {
        return [pscustomobject]@{
            host_path = [System.IO.Path]::GetFullPath($resolved)
            host_leaf = [System.IO.Path]::GetFileName($resolved).ToLowerInvariant()
            prefix_arguments = @()
        }
    }

    throw "Unable to resolve requested Python command spec: $normalized"
}

function Get-VgoPowerShellFileInvocation {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath,
        [string[]]$ArgumentList = @(),
        [switch]$NoProfile
    )

    $hostPath = Get-VgoPowerShellCommand
    $hostLeaf = [System.IO.Path]::GetFileName($hostPath).ToLowerInvariant()
    $args = @()

    if ($NoProfile) {
        $args += '-NoProfile'
    }

    if ($hostLeaf -like 'powershell*') {
        $args += @('-ExecutionPolicy', 'Bypass')
    }

    $args += @('-File', [System.IO.Path]::GetFullPath($ScriptPath))
    if ($ArgumentList.Count -gt 0) {
        $args += $ArgumentList
    }

    return [pscustomobject]@{
        host_path = $hostPath
        host_leaf = $hostLeaf
        arguments = @($args)
    }
}

function Invoke-VgoPowerShellFile {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath,
        [string[]]$ArgumentList = @(),
        [switch]$NoProfile
    )

    $invocation = Get-VgoPowerShellFileInvocation -ScriptPath $ScriptPath -ArgumentList $ArgumentList -NoProfile:$NoProfile
    $global:LASTEXITCODE = 0
    $scriptOutput = @(& $invocation.host_path @($invocation.arguments))
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }

    return [pscustomobject]@{
        host_path = [string]$invocation.host_path
        arguments = @($invocation.arguments)
        exit_code = $exitCode
        output = @($scriptOutput)
    }
}

function Get-VgoRelativePathPortable {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull += [System.IO.Path]::DirectorySeparatorChar
    }

    if ($targetFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $targetFull.Substring($baseFull.Length).Replace('\', '/')
    }

    $baseUri = [System.Uri]::new($baseFull)
    $targetUri = [System.Uri]::new($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('\', '/')
}

function Remove-VgoIgnoredKeys {
    param(
        [object]$Node,
        [string[]]$IgnoreKeys
    )

    if ($null -eq $Node) {
        return $null
    }

    if ($Node -is [System.Management.Automation.PSCustomObject]) {
        $ordered = [ordered]@{}
        foreach ($prop in @($Node.PSObject.Properties) | Sort-Object -Property Name) {
            $key = [string]$prop.Name
            if ($IgnoreKeys -contains $key) {
                continue
            }
            $ordered[$key] = Remove-VgoIgnoredKeys -Node $prop.Value -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }

    if ($Node -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Node.Keys) | Sort-Object) {
            $keyText = [string]$key
            if ($IgnoreKeys -contains $keyText) {
                continue
            }
            $ordered[$keyText] = Remove-VgoIgnoredKeys -Node $Node[$key] -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }

    if ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
        $items = @()
        foreach ($item in $Node) {
            $items += Remove-VgoIgnoredKeys -Node $item -IgnoreKeys $IgnoreKeys
        }
        return $items
    }

    return $Node
}

function Get-VgoNormalizedJsonHash {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [string[]]$IgnoreKeys = @()
    )

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $obj = $raw | ConvertFrom-Json
    $normalizedObj = Remove-VgoIgnoredKeys -Node $obj -IgnoreKeys $IgnoreKeys
    $normalized = $normalizedObj | ConvertTo-Json -Depth 100 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $stream = [System.IO.MemoryStream]::new($bytes)
    try {
        return (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash
    } finally {
        $stream.Dispose()
    }
}

function Test-VgoFileParity {
    param(
        [Parameter(Mandatory)] [string]$ReferencePath,
        [Parameter(Mandatory)] [string]$CandidatePath,
        [string[]]$IgnoreJsonKeys = @()
    )

    if (-not (Test-Path -LiteralPath $ReferencePath) -or -not (Test-Path -LiteralPath $CandidatePath)) {
        return $false
    }

    $referenceExt = [System.IO.Path]::GetExtension($ReferencePath).ToLowerInvariant()
    $candidateExt = [System.IO.Path]::GetExtension($CandidatePath).ToLowerInvariant()
    if ($referenceExt -eq '.json' -and $candidateExt -eq '.json') {
        return (Get-VgoNormalizedJsonHash -Path $ReferencePath -IgnoreKeys $IgnoreJsonKeys) -eq (Get-VgoNormalizedJsonHash -Path $CandidatePath -IgnoreKeys $IgnoreJsonKeys)
    }

    return (Get-FileHash -LiteralPath $ReferencePath -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $CandidatePath -Algorithm SHA256).Hash
}

function Get-VgoRelativeFileList {
    param(
        [Parameter(Mandatory)] [string]$RootPath
    )

    if (-not (Test-Path -LiteralPath $RootPath)) {
        return @()
    }

    return @(
        Get-ChildItem -LiteralPath $RootPath -Recurse -File | ForEach-Object {
            Get-VgoRelativePathPortable -BasePath $RootPath -TargetPath $_.FullName
        } | Sort-Object -Unique
    )
}

function Get-VgoLatestJsonlRecord {
    param(
        [Parameter(Mandatory)] [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    for ($index = $lines.Count - 1; $index -ge 0; $index--) {
        try {
            return ($lines[$index] | ConvertFrom-Json)
        } catch {
            continue
        }
    }

    return $null
}

function Get-VgoPackagingManifestSpecs {
    param(
        [Parameter(Mandatory)] [psobject]$Packaging
    )

    $manifestInput = if ($Packaging.PSObject.Properties.Name -contains 'manifests') { $Packaging.manifests } else { $null }
    $specs = @()
    if ($null -eq $manifestInput) {
        return @()
    }

    if ($manifestInput -is [System.Collections.IEnumerable] -and -not ($manifestInput -is [string])) {
        foreach ($item in @($manifestInput)) {
            if ($null -eq $item) {
                continue
            }

            $manifestId = if ($item.PSObject.Properties.Name -contains 'id') { [string]$item.id } else { '' }
            $manifestPath = if ($item.PSObject.Properties.Name -contains 'path') { [string]$item.path } else { '' }
            if ([string]::IsNullOrWhiteSpace($manifestPath)) {
                continue
            }

            $specs += [pscustomobject]@{
                id = $manifestId
                path = $manifestPath.Replace('\', '/')
            }
        }
        return @($specs)
    }

    $names = @()
    if ($manifestInput -is [System.Collections.IDictionary]) {
        $names = @($manifestInput.Keys)
    } else {
        $names = @($manifestInput.PSObject.Properties.Name)
    }

    foreach ($name in $names) {
        $value = if ($manifestInput -is [System.Collections.IDictionary]) { $manifestInput[$name] } else { $manifestInput.$name }
        if ($null -eq $value) {
            continue
        }

        $manifestPath = if ($value.PSObject.Properties.Name -contains 'path') { [string]$value.path } else { [string]$value }
        if ([string]::IsNullOrWhiteSpace($manifestPath)) {
            continue
        }

        $specs += [pscustomobject]@{
            id = [string]$name
            path = $manifestPath.Replace('\', '/')
        }
    }

    return @($specs)
}

function Get-VgoPackagingContract {
    param(
        [Parameter(Mandatory)] [psobject]$Governance,
        [AllowEmptyString()] [string]$RepoRoot = ''
    )

    $defaults = [ordered]@{
        runtime_payload = [ordered]@{
            files = @('SKILL.md', 'check.ps1', 'check.sh', 'install.ps1', 'install.sh')
            directories = @('config', 'protocols', 'references', 'docs', 'scripts')
        }
        target_overrides = [ordered]@{}
        allow_installed_only = @()
        normalized_json_ignore_keys = @('updated', 'generated_at')
    }

    $packaging = if ($Governance.PSObject.Properties.Name -contains 'packaging') { $Governance.packaging } else { $null }
    if ($null -eq $packaging) {
        return [pscustomobject]$defaults
    }

    $runtimePayload = $null
    if ($packaging.PSObject.Properties.Name -contains 'runtime_payload' -and $null -ne $packaging.runtime_payload) {
        $runtimePayload = $packaging.runtime_payload
    } elseif ($packaging.PSObject.Properties.Name -contains 'mirror' -and $null -ne $packaging.mirror) {
        $runtimePayload = $packaging.mirror
    }
    $mirrorFiles = if ($null -ne $runtimePayload -and $runtimePayload.PSObject.Properties.Name -contains 'files') { @($runtimePayload.files) } else { @($defaults.runtime_payload.files) }
    $mirrorDirs = if ($null -ne $runtimePayload -and $runtimePayload.PSObject.Properties.Name -contains 'directories') { @($runtimePayload.directories) } else { @($defaults.runtime_payload.directories) }
    $targetOverridesInput = if ($packaging.PSObject.Properties.Name -contains 'target_overrides' -and $null -ne $packaging.target_overrides) { $packaging.target_overrides } else { $null }
    $manifestSpecs = Get-VgoPackagingManifestSpecs -Packaging $packaging
    $allowBundledOnly = if ($packaging.PSObject.Properties.Name -contains 'allow_installed_only') {
        @($packaging.allow_installed_only)
    } elseif ($packaging.PSObject.Properties.Name -contains 'allow_bundled_only') {
        @($packaging.allow_bundled_only)
    } else {
        @($defaults.allow_installed_only)
    }
    $ignoreKeys = if ($packaging.PSObject.Properties.Name -contains 'normalized_json_ignore_keys') { @($packaging.normalized_json_ignore_keys) } else { @($defaults.normalized_json_ignore_keys) }

    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        foreach ($manifestSpec in $manifestSpecs) {
            $manifestPath = Join-Path $RepoRoot $manifestSpec.path
            if (-not (Test-Path -LiteralPath $manifestPath)) {
                throw "packaging manifest not found: $manifestPath"
            }

            $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($manifest.PSObject.Properties.Name -contains 'files' -and $null -ne $manifest.files) {
                $mirrorFiles += @($manifest.files)
            }
            if ($manifest.PSObject.Properties.Name -contains 'directories' -and $null -ne $manifest.directories) {
                $mirrorDirs += @($manifest.directories)
            }
        }
    }

    $targetOverrides = [ordered]@{}
    if ($null -ne $targetOverridesInput) {
        $targetNames = @()
        if ($targetOverridesInput -is [System.Collections.IDictionary]) {
            $targetNames = @($targetOverridesInput.Keys)
        } else {
            if ($null -ne $targetOverridesInput.PSObject -and $null -ne $targetOverridesInput.PSObject.Properties) {
                $targetNames = @($targetOverridesInput.PSObject.Properties | ForEach-Object { $_.Name })
            }
        }

        foreach ($targetName in $targetNames) {
            $targetValue = if ($targetOverridesInput -is [System.Collections.IDictionary]) { $targetOverridesInput[$targetName] } else { $targetOverridesInput.$targetName }
            if ($null -eq $targetValue) {
                continue
            }

            $targetFiles = if ($targetValue.PSObject.Properties.Name -contains 'files') { @($targetValue.files) } else { @() }
            $targetDirs = if ($targetValue.PSObject.Properties.Name -contains 'directories') { @($targetValue.directories) } else { @() }
            $targetOverrides[[string]$targetName] = [pscustomobject]@{
                files = @($targetFiles)
                directories = @($targetDirs)
            }
        }
    }

    return [pscustomobject]@{
        runtime_payload = [pscustomobject]@{
            files = @($mirrorFiles | ForEach-Object { ([string]$_).Replace('\', '/') } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            directories = @($mirrorDirs | ForEach-Object { ([string]$_).Replace('\', '/') } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        }
        mirror = [pscustomobject]@{
            files = @($mirrorFiles | ForEach-Object { ([string]$_).Replace('\', '/') } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            directories = @($mirrorDirs | ForEach-Object { ([string]$_).Replace('\', '/') } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        }
        manifests = @($manifestSpecs)
        target_overrides = [pscustomobject]$targetOverrides
        allow_installed_only = @($allowBundledOnly)
        allow_bundled_only = @($allowBundledOnly)
        normalized_json_ignore_keys = @($ignoreKeys)
    }
}

function Get-VgoEffectiveTargetPackaging {
    param(
        [Parameter(Mandatory)] [psobject]$Packaging,
        [AllowEmptyString()] [string]$TargetId = ''
    )

    $baseFiles = @($Packaging.mirror.files)
    $baseDirs = @($Packaging.mirror.directories)
    $targetOnlyFiles = @()
    $targetOnlyDirs = @()

    if (-not [string]::IsNullOrWhiteSpace($TargetId) -and $Packaging.PSObject.Properties.Name -contains 'target_overrides' -and $null -ne $Packaging.target_overrides) {
        $targetOverrides = $Packaging.target_overrides
        $override = $null
        if ($targetOverrides -is [System.Collections.IDictionary]) {
            if ($targetOverrides.Contains($TargetId)) {
                $override = $targetOverrides[$TargetId]
            }
        } else {
            $overrideNames = @()
            if ($null -ne $targetOverrides.PSObject -and $null -ne $targetOverrides.PSObject.Properties) {
                $overrideNames = @($targetOverrides.PSObject.Properties | ForEach-Object { $_.Name })
            }
            if ($overrideNames -contains $TargetId) {
                $override = $targetOverrides.$TargetId
            }
        }

        if ($null -ne $override) {
            $targetOnlyFiles = if ($override.PSObject.Properties.Name -contains 'files') { @($override.files) } else { @() }
            $targetOnlyDirs = if ($override.PSObject.Properties.Name -contains 'directories') { @($override.directories) } else { @() }
        }
    }

    return [pscustomobject]@{
        files = @($baseFiles + $targetOnlyFiles | Select-Object -Unique)
        directories = @($baseDirs + $targetOnlyDirs | Select-Object -Unique)
        target_only_files = @($targetOnlyFiles)
        target_only_directories = @($targetOnlyDirs)
    }
}

function Test-VgoGovernedMirrorRelativePath {
    param(
        [Parameter(Mandatory)] [string]$RelativePath,
        [Parameter(Mandatory)] [psobject]$Packaging,
        [AllowEmptyString()] [string]$TargetId = ''
    )

    $rel = $RelativePath.Replace('\', '/')
    $effective = Get-VgoEffectiveTargetPackaging -Packaging $Packaging -TargetId $TargetId
    if (@($effective.files) -contains $rel) {
        return $true
    }

    foreach ($dir in @($effective.directories)) {
        $prefix = ('{0}/' -f $dir).Replace('\', '/')
        if ($rel.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Get-VgoInstalledRuntimeEmergencyFallbackDefaults {
    return [pscustomobject][ordered]@{
        target_relpath = 'skills/vibe'
        receipt_relpath = 'skills/vibe/outputs/runtime-freshness-receipt.json'
        post_install_gate = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
        coherence_gate = 'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
        frontmatter_gate = 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
        neutral_freshness_gate = 'scripts/verify/runtime_neutral/freshness_gate.py'
        runtime_entrypoint = 'scripts/runtime/invoke-vibe-runtime.ps1'
        receipt_contract_version = 1
        shell_degraded_behavior = 'warn_and_skip_authoritative_runtime_gate'
        required_runtime_markers = @(
            'SKILL.md',
            'config/version-governance.json',
            'scripts/common/vibe-governance-helpers.ps1',
            'scripts/runtime/invoke-vibe-runtime.ps1',
            'scripts/router/resolve-pack-route.ps1'
        )
        require_nested_bundled_root = $false
    }
}

function Get-VgoInstalledRuntimeFallbackDefaults {
    return Get-VgoInstalledRuntimeEmergencyFallbackDefaults
}

function Get-VgoInstalledRuntimeDefaultsFromContracts {
    $helperPath = Join-Path $PSScriptRoot 'runtime_contracts.py'
    if (-not (Test-Path -LiteralPath $helperPath)) {
        throw "Installed-runtime contract bridge missing: $helperPath"
    }

    $python = Get-VgoPythonCommand
    $args = @()
    if ($null -ne $python.prefix_arguments) {
        $args += @($python.prefix_arguments)
    }
    $args += @($helperPath, 'installed-runtime-config', '--mode', 'installed')

    $raw = & $python.host_path @args
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($raw | Out-String))) {
        throw 'Unable to load installed-runtime defaults from scripts/common/runtime_contracts.py.'
    }

    return ($raw | ConvertFrom-Json)
}

function Get-VgoInstalledRuntimeConfig {
    param(
        [Parameter(Mandatory)] [psobject]$Governance
    )

    try {
        $defaults = Get-VgoInstalledRuntimeDefaultsFromContracts
    } catch {
        $defaults = Get-VgoInstalledRuntimeEmergencyFallbackDefaults
    }

    $runtimeConfig = $null
    if ($Governance.PSObject.Properties.Name -contains 'runtime' -and $null -ne $Governance.runtime) {
        if ($Governance.runtime.PSObject.Properties.Name -contains 'installed_runtime') {
            $runtimeConfig = $Governance.runtime.installed_runtime
        }
    }

    if ($null -eq $runtimeConfig) {
        return $defaults
    }

    $merged = [ordered]@{}
    $defaultKeys = @($defaults.PSObject.Properties | ForEach-Object { [string]$_.Name })
    foreach ($key in $defaultKeys) {
        $defaultValue = $defaults.$key
        if ($key -eq 'required_runtime_markers') {
            if ($runtimeConfig.PSObject.Properties.Name -contains $key -and $null -ne $runtimeConfig.$key) {
                $merged[$key] = @($runtimeConfig.$key)
            } else {
                $merged[$key] = @($defaultValue)
            }
            continue
        }

        if ($runtimeConfig.PSObject.Properties.Name -contains $key -and $null -ne $runtimeConfig.$key -and -not (($runtimeConfig.$key -is [string]) -and [string]::IsNullOrWhiteSpace([string]$runtimeConfig.$key))) {
            $merged[$key] = $runtimeConfig.$key
        } else {
            $merged[$key] = $defaultValue
        }
    }

    return [pscustomobject]$merged
}

function Get-VgoRuntimeEntrypointPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [psobject]$RuntimeConfig
    )

    if ($null -ne $RuntimeConfig -and $RuntimeConfig.PSObject.Properties.Name -contains 'runtime_entrypoint' -and -not [string]::IsNullOrWhiteSpace([string]$RuntimeConfig.runtime_entrypoint)) {
        $runtimeEntrypointRel = [string]$RuntimeConfig.runtime_entrypoint
    } else {
        try {
            $runtimeEntrypointRel = [string](Get-VgoInstalledRuntimeDefaultsFromContracts).runtime_entrypoint
        } catch {
            $runtimeEntrypointRel = [string](Get-VgoInstalledRuntimeEmergencyFallbackDefaults).runtime_entrypoint
        }
    }

    return Join-Path $RepoRoot $runtimeEntrypointRel
}

function Get-VgoMirrorTopologyTargets {
    param(
        [Parameter(Mandatory)] [psobject]$Governance,
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $targets = @()
    $topology = if ($Governance.PSObject.Properties.Name -contains 'mirror_topology') { $Governance.mirror_topology } else { $null }
    if ($null -ne $topology -and $topology.PSObject.Properties.Name -contains 'targets' -and $null -ne $topology.targets) {
        $targets = @($topology.targets)
    }

    if ($targets.Count -eq 0) {
        $legacy = if ($Governance.PSObject.Properties.Name -contains 'source_of_truth') { $Governance.source_of_truth } else { $null }
        $canonicalRel = if ($null -ne $legacy -and $legacy.PSObject.Properties.Name -contains 'canonical_root') { [string]$legacy.canonical_root } else { '.' }
        if ([string]::IsNullOrWhiteSpace($canonicalRel)) {
            $canonicalRel = '.'
        }
        $targets = @(
            [pscustomobject]@{ id = 'canonical'; path = $canonicalRel; role = 'canonical'; required = $true; presence_policy = 'required'; sync_enabled = $false; parity_policy = 'authoritative' }
        )
        $bundledRel = if ($null -ne $legacy -and $legacy.PSObject.Properties.Name -contains 'bundled_root') { [string]$legacy.bundled_root } else { $null }
        if (-not [string]::IsNullOrWhiteSpace($bundledRel)) {
            $targets += [pscustomobject]@{ id = 'bundled'; path = $bundledRel; role = 'mirror'; required = $true; presence_policy = 'required'; sync_enabled = $true; parity_policy = 'full' }
        }
        $nestedRel = if ($null -ne $legacy -and $legacy.PSObject.Properties.Name -contains 'nested_bundled_root') { [string]$legacy.nested_bundled_root } else { $null }
        if (-not [string]::IsNullOrWhiteSpace($nestedRel)) {
            $targets += [pscustomobject]@{ id = 'nested_bundled'; path = $nestedRel; role = 'mirror'; required = $false; presence_policy = 'if_present_must_match'; sync_enabled = $false; parity_policy = 'full'; materialization_mode = 'release_install_only' }
        }
    }

    $topologyTargets = @()
    foreach ($target in $targets) {
        $targetId = if ($target.PSObject.Properties.Name -contains 'id') { [string]$target.id } else { $null }
        if ([string]::IsNullOrWhiteSpace($targetId)) {
            continue
        }

        $targetPath = if ($target.PSObject.Properties.Name -contains 'path') { [string]$target.path } else { $null }
        if ([string]::IsNullOrWhiteSpace($targetPath)) {
            continue
        }

        $fullPath = ConvertTo-VgoFullPath -BasePath $RepoRoot -RelativePath $targetPath
        $role = if ($target.PSObject.Properties.Name -contains 'role' -and -not [string]::IsNullOrWhiteSpace([string]$target.role)) { [string]$target.role } else { 'mirror' }
        $required = if ($target.PSObject.Properties.Name -contains 'required') { [bool]$target.required } else { $false }
        $presencePolicy = if ($target.PSObject.Properties.Name -contains 'presence_policy' -and -not [string]::IsNullOrWhiteSpace([string]$target.presence_policy)) { [string]$target.presence_policy } else { if ($required) { 'required' } else { 'optional' } }
        $syncEnabled = if ($target.PSObject.Properties.Name -contains 'sync_enabled') { [bool]$target.sync_enabled } else { -not ($role -eq 'canonical') }
        $parityPolicy = if ($target.PSObject.Properties.Name -contains 'parity_policy' -and -not [string]::IsNullOrWhiteSpace([string]$target.parity_policy)) { [string]$target.parity_policy } else { if ($role -eq 'canonical') { 'authoritative' } else { 'full' } }
        $materializationMode = if ($target.PSObject.Properties.Name -contains 'materialization_mode' -and -not [string]::IsNullOrWhiteSpace([string]$target.materialization_mode)) { [string]$target.materialization_mode } else { if ($targetId -eq 'nested_bundled' -and -not $syncEnabled) { 'release_install_only' } else { 'tracked_mirror' } }

        $materializationMarker = Join-Path $fullPath 'SKILL.md'
        $targetExists = (Test-Path -LiteralPath $fullPath)
        if ($targetExists) {
            $targetExists = (Test-Path -LiteralPath $materializationMarker)
        }

        $topologyTargets += [pscustomobject]@{
            id = $targetId
            path = $targetPath.Replace('\', '/')
            fullPath = $fullPath
            role = $role
            required = $required
            presence_policy = $presencePolicy
            sync_enabled = $syncEnabled
            parity_policy = $parityPolicy
            materialization_mode = $materializationMode
            exists = $targetExists
            isCanonical = ($role -eq 'canonical')
        }
    }

    return @($topologyTargets)
}

function Get-VgoMirrorTarget {
    param(
        [Parameter(Mandatory)] [object[]]$Targets,
        [Parameter(Mandatory)] [string]$Id
    )

    $match = @($Targets | Where-Object { $_.id -eq $Id } | Select-Object -First 1)
    if ($match.Count -eq 0) {
        return $null
    }

    return $match[0]
}

function Get-VgoLegacySourceOfTruthCompatibility {
    param(
        [Parameter(Mandatory)] [psobject]$Governance,
        [Parameter(Mandatory)] [object[]]$Targets
    )

    $legacy = if ($Governance.PSObject.Properties.Name -contains 'source_of_truth') { $Governance.source_of_truth } else { $null }
    $mismatches = New-Object System.Collections.Generic.List[object]
    if ($null -eq $legacy) {
        return [pscustomobject]@{
            isCompatible = $false
            mismatches = @(
                [pscustomobject]@{ field = 'source_of_truth'; expected = '<present>'; actual = '<missing>' }
            )
        }
    }

    $checks = @(
        [pscustomobject]@{ field = 'canonical_root'; targetId = 'canonical' },
        [pscustomobject]@{ field = 'bundled_root'; targetId = 'bundled' },
        [pscustomobject]@{ field = 'nested_bundled_root'; targetId = 'nested_bundled' }
    )

    foreach ($check in $checks) {
        $target = Get-VgoMirrorTarget -Targets $Targets -Id $check.targetId
        if ($null -eq $target) {
            continue
        }

        $actual = if ($legacy.PSObject.Properties.Name -contains $check.field) { [string]$legacy.($check.field) } else { $null }
        $expected = [string]$target.path
        if ([string]::IsNullOrWhiteSpace($actual) -and -not [string]::IsNullOrWhiteSpace($expected)) {
            [void]$mismatches.Add([pscustomobject]@{ field = $check.field; expected = $expected; actual = '<missing>' })
            continue
        }

        $normalizedActual = ([string]$actual).Replace('\', '/').Trim('/')
        $normalizedExpected = ([string]$expected).Replace('\', '/').Trim('/')
        if ($normalizedActual -ne $normalizedExpected) {
            [void]$mismatches.Add([pscustomobject]@{ field = $check.field; expected = $expected; actual = $actual })
        }
    }

    return [pscustomobject]@{
        isCompatible = ($mismatches.Count -eq 0)
        mismatches = @($mismatches.ToArray())
    }
}

function Test-VgoInstalledRuntimeMaterialization {
    param(
        [AllowEmptyString()] [string]$RepoRoot,
        [AllowNull()] [psobject]$RuntimeConfig
    )

    if ([string]::IsNullOrWhiteSpace($RepoRoot) -or $null -eq $RuntimeConfig) {
        return $false
    }

    $requiredMarkers = @()
    if ($RuntimeConfig.PSObject.Properties.Name -contains 'required_runtime_markers' -and $null -ne $RuntimeConfig.required_runtime_markers) {
        $requiredMarkers = @($RuntimeConfig.required_runtime_markers)
    }
    if (@($requiredMarkers).Count -eq 0) {
        return $false
    }

    foreach ($marker in @($requiredMarkers)) {
        if ([string]::IsNullOrWhiteSpace([string]$marker)) {
            continue
        }

        $markerPath = Join-Path $RepoRoot ([string]$marker)
        if (-not (Test-Path -LiteralPath $markerPath)) {
            return $false
        }
    }

    return $true
}

function Assert-VgoCanonicalExecutionContext {
    param(
        [Parameter(Mandatory)] [psobject]$Context
    )

    $policy = $Context.execution_context_policy
    $requireOuterGitRoot = $true
    $failIfScriptUnderMirror = $true

    if ($null -ne $policy) {
        if ($policy.PSObject.Properties.Name -contains 'require_outer_git_root') {
            $requireOuterGitRoot = [bool]$policy.require_outer_git_root
        }
        if ($policy.PSObject.Properties.Name -contains 'fail_if_script_path_is_under_mirror_root') {
            $failIfScriptUnderMirror = [bool]$policy.fail_if_script_path_is_under_mirror_root
        }
    }

    $hasOuterGitRoot = (Test-Path -LiteralPath (Join-Path $Context.repoRoot '.git'))
    $hasInstalledRuntimeMaterialization = Test-VgoInstalledRuntimeMaterialization -RepoRoot ([string]$Context.repoRoot) -RuntimeConfig $Context.runtimeConfig
    if ($requireOuterGitRoot -and -not $hasOuterGitRoot -and -not $hasInstalledRuntimeMaterialization) {
        throw "Execution-context lock failed: resolved repo root is not the outer git root -> $($Context.repoRoot)"
    }

    if ($failIfScriptUnderMirror) {
        $scriptPath = [System.IO.Path]::GetFullPath([string]$Context.script_path)
        $matchedTargets = @(
            $Context.mirrorTargets | Where-Object {
                -not $_.isCanonical -and (Test-VgoPathWithin -ParentPath $_.fullPath -ChildPath $scriptPath)
            }
        )

        if ($matchedTargets.Count -gt 0) {
            $targetIds = ($matchedTargets | ForEach-Object { $_.id }) -join ', '
            throw "Execution-context lock failed: governance/verify scripts must run from the canonical repo tree, not from mirror targets. targets=$targetIds script=$scriptPath repoRoot=$($Context.repoRoot)"
        }
    }

    return $true
}

function Get-VgoGovernanceContext {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath,
        [switch]$EnforceExecutionContext
    )

    $resolvedScript = Resolve-Path -LiteralPath $ScriptPath -ErrorAction Stop
    $repoRoot = Resolve-VgoRepoRoot -StartPath $resolvedScript.Path
    $governancePath = Join-Path $repoRoot 'config\version-governance.json'
    if (-not (Test-Path -LiteralPath $governancePath)) {
        throw "version-governance config not found: $governancePath"
    }

    $governance = Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $packaging = Get-VgoPackagingContract -Governance $governance -RepoRoot $repoRoot
    $runtimeConfig = Get-VgoInstalledRuntimeConfig -Governance $governance
    $mirrorTargets = Get-VgoMirrorTopologyTargets -Governance $governance -RepoRoot $repoRoot

    $mirrorTargetMap = [ordered]@{}
    foreach ($target in $mirrorTargets) {
        $mirrorTargetMap[$target.id] = $target
    }

    $topology = if ($governance.PSObject.Properties.Name -contains 'mirror_topology') { $governance.mirror_topology } else { $null }
    $canonicalTargetId = if ($null -ne $topology -and $topology.PSObject.Properties.Name -contains 'canonical_target_id' -and -not [string]::IsNullOrWhiteSpace([string]$topology.canonical_target_id)) { [string]$topology.canonical_target_id } else { 'canonical' }
    $syncSourceTargetId = if ($null -ne $topology -and $topology.PSObject.Properties.Name -contains 'sync_source_target_id' -and -not [string]::IsNullOrWhiteSpace([string]$topology.sync_source_target_id)) { [string]$topology.sync_source_target_id } else { $canonicalTargetId }

    $canonicalTarget = Get-VgoMirrorTarget -Targets $mirrorTargets -Id $canonicalTargetId
    if ($null -eq $canonicalTarget) {
        $canonicalTarget = @($mirrorTargets | Where-Object { $_.role -eq 'canonical' } | Select-Object -First 1)[0]
    }
    if ($null -eq $canonicalTarget) {
        throw 'mirror topology does not define a canonical target.'
    }

    $bundledTarget = Get-VgoMirrorTarget -Targets $mirrorTargets -Id 'bundled'
    $nestedTarget = Get-VgoMirrorTarget -Targets $mirrorTargets -Id 'nested_bundled'
    $syncSourceTarget = Get-VgoMirrorTarget -Targets $mirrorTargets -Id $syncSourceTargetId
    if ($null -eq $syncSourceTarget) {
        $syncSourceTarget = $canonicalTarget
    }

    $executionContextPolicy = $null
    if ($governance.PSObject.Properties.Name -contains 'execution_context_policy') {
        $executionContextPolicy = $governance.execution_context_policy
    } elseif ($governance.PSObject.Properties.Name -contains 'packaging' -and $governance.packaging -and $governance.packaging.PSObject.Properties.Name -contains 'execution_context_policy') {
        $executionContextPolicy = $governance.packaging.execution_context_policy
    }

    $legacyCompatibility = Get-VgoLegacySourceOfTruthCompatibility -Governance $governance -Targets $mirrorTargets

    $context = [pscustomobject]@{
        repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
        governancePath = [System.IO.Path]::GetFullPath($governancePath)
        governance = $governance
        packaging = $packaging
        runtimeConfig = $runtimeConfig
        mirrorTargets = @($mirrorTargets)
        mirrorTargetMap = $mirrorTargetMap
        canonicalTarget = $canonicalTarget
        bundledTarget = $bundledTarget
        nestedTarget = $nestedTarget
        syncSourceTarget = $syncSourceTarget
        canonicalRoot = [string]$canonicalTarget.fullPath
        bundledRoot = if ($null -ne $bundledTarget) { [string]$bundledTarget.fullPath } else { $null }
        nestedBundledRoot = if ($null -ne $nestedTarget) { [string]$nestedTarget.fullPath } else { $null }
        legacySourceOfTruthCompatibility = $legacyCompatibility
        execution_context_policy = $executionContextPolicy
        script_path = [System.IO.Path]::GetFullPath([string]$resolvedScript.Path)
    }

    if ($EnforceExecutionContext) {
        Assert-VgoCanonicalExecutionContext -Context $context | Out-Null
    }

    return $context
}

function Get-VgoSkillPromotionPolicyDefaults {
    return [pscustomobject]@{
        promotion_enabled = $true
        default_mode = 'recall_first'
        allow_auto_dispatch_when_non_destructive = $true
        require_contract_complete = $true
        destructive_prompt_patterns = [pscustomobject]@{
            destructive_delete = @(
                '\b(delete|remove|drop|erase)\b(?=[^\r\n]{0,60}\b(all|entire|branch|branches|database|db|table|tables|schema|schemas|bucket|buckets|workspace|workspaces|environment|environments|settings?|config(?:uration)?|artifacts?|files?|directories?|directory|repo(?:sitory)?|repositories|index(?:es)?|collection(?:s)?|secrets?|credentials?)\b)',
                '\b(delete|remove|drop|erase)\b(?=[^\r\n]{0,60}(?:~[\\/]|\.{1,2}[\\/]|[A-Za-z]:[\\/]|[\\/]{2}|\/)[^\s]+)',
                '删除.{0,20}(全部|整个|分支|数据库|数据表|表|模式|桶|工作区|环境|设置|配置|产物|文件|目录|仓库|索引|集合|密钥|凭据)',
                '移除.{0,20}(全部|整个|分支|数据库|数据表|表|模式|桶|工作区|环境|设置|配置|产物|文件|目录|仓库|索引|集合|密钥|凭据)',
                '清空.{0,20}(数据库|数据表|表|桶|工作区|环境|设置|配置|目录|仓库|索引|集合)'
            )
            destructive_overwrite = @(
                '\b(overwrite|replace)\b(?=[^\r\n]{0,60}\b(all|entire|settings?|config(?:uration)?|environment|environments|provider|providers|deployment|deployments|database|db|table|tables|schema|schemas|artifacts?|files?|secrets?|credentials?)\b)',
                '\b(overwrite|replace)\b(?=[^\r\n]{0,60}(?:~[\\/]|\.{1,2}[\\/]|[A-Za-z]:[\\/]|[\\/]{2}|\/)[^\s]+)',
                '覆盖.{0,20}(全部|整个|设置|配置|环境|提供商|部署|数据库|数据表|表|模式|产物|文件|密钥|凭据)',
                '替换.{0,20}(全部|整个|设置|配置|环境|提供商|部署|数据库|数据表|表|模式|产物|文件|密钥|凭据)'
            )
            destructive_reset = @(
                '\b(reset|uninstall|wipe|destroy|purge)\b(?=[^\r\n]{0,60}\b(all|entire|environment|environments|workspace|workspaces|settings?|config(?:uration)?|repository|repositories|repo|repos|database|db|table|tables|schema|schemas|artifacts?|files?|branch|branches|deployment|deployments|production)\b)',
                '\b(reset|uninstall|wipe|destroy|purge)\b(?=[^\r\n]{0,60}(?:~[\\/]|\.{1,2}[\\/]|[A-Za-z]:[\\/]|[\\/]{2}|\/)[^\s]+)',
                '重置.{0,20}(全部|整个|环境|工作区|设置|配置|仓库|数据库|数据表|表|模式|产物|文件|分支|部署|生产)',
                '卸载.{0,20}(全部|整个|环境|工作区|设置|配置|仓库|数据库|产物|文件|部署)',
                '销毁.{0,20}(全部|整个|环境|工作区|设置|配置|仓库|数据库|数据表|表|模式|产物|文件|分支|部署|生产)'
            )
        }
        degraded_fallback_rules = [pscustomobject]@{
            missing_contract = 'explicit_degraded'
        }
    }
}

function Get-VgoSkillPromotionPolicy {
    param(
        [AllowNull()] [object]$Policy
    )

    $defaults = Get-VgoSkillPromotionPolicyDefaults
    if ($null -eq $Policy) {
        return $defaults
    }

    return [pscustomobject]@{
        promotion_enabled = if ($Policy.PSObject.Properties.Name -contains 'promotion_enabled' -and $null -ne $Policy.promotion_enabled) { [bool]$Policy.promotion_enabled } else { [bool]$defaults.promotion_enabled }
        default_mode = if ($Policy.PSObject.Properties.Name -contains 'default_mode' -and -not [string]::IsNullOrWhiteSpace([string]$Policy.default_mode)) { [string]$Policy.default_mode } else { [string]$defaults.default_mode }
        allow_auto_dispatch_when_non_destructive = if ($Policy.PSObject.Properties.Name -contains 'allow_auto_dispatch_when_non_destructive' -and $null -ne $Policy.allow_auto_dispatch_when_non_destructive) { [bool]$Policy.allow_auto_dispatch_when_non_destructive } else { [bool]$defaults.allow_auto_dispatch_when_non_destructive }
        require_contract_complete = if ($Policy.PSObject.Properties.Name -contains 'require_contract_complete' -and $null -ne $Policy.require_contract_complete) { [bool]$Policy.require_contract_complete } else { [bool]$defaults.require_contract_complete }
        destructive_prompt_patterns = if ($Policy.PSObject.Properties.Name -contains 'destructive_prompt_patterns' -and $null -ne $Policy.destructive_prompt_patterns) { $Policy.destructive_prompt_patterns } else { $defaults.destructive_prompt_patterns }
        degraded_fallback_rules = if ($Policy.PSObject.Properties.Name -contains 'degraded_fallback_rules' -and $null -ne $Policy.degraded_fallback_rules) { $Policy.degraded_fallback_rules } else { $defaults.degraded_fallback_rules }
    }
}

function Get-VgoSkillContractCompleteness {
    param(
        [AllowEmptyString()] [string]$SkillMdPath = '',
        [AllowEmptyString()] [string]$SkillRoot = '',
        [AllowEmptyString()] [string]$Description = '',
        [AllowNull()] [object]$RequiredInputs = $null,
        [AllowNull()] [object]$ExpectedOutputs = $null,
        [AllowEmptyString()] [string]$VerificationExpectation = '',
        [bool]$NativeUsageRequired = $true,
        [bool]$MustPreserveWorkflow = $true
    )

    $missingFields = @()
    if ([string]::IsNullOrWhiteSpace($SkillMdPath)) {
        $missingFields += 'native_skill_entrypoint'
    }
    if ([string]::IsNullOrWhiteSpace($SkillRoot)) {
        $missingFields += 'skill_root'
    }
    if ([string]::IsNullOrWhiteSpace($Description)) {
        $missingFields += 'native_skill_description'
    }
    $requiredInputsPresent = @($RequiredInputs | Where-Object {
        -not [string]::IsNullOrWhiteSpace([string]$_)
    })
    if ($requiredInputsPresent.Count -eq 0) {
        $missingFields += 'required_inputs'
    }
    $expectedOutputsPresent = @($ExpectedOutputs | Where-Object {
        -not [string]::IsNullOrWhiteSpace([string]$_)
    })
    if ($expectedOutputsPresent.Count -eq 0) {
        $missingFields += 'expected_outputs'
    }
    if ([string]::IsNullOrWhiteSpace($VerificationExpectation)) {
        $missingFields += 'verification_expectation'
    }
    if (-not $NativeUsageRequired) {
        $missingFields += 'native_usage_required'
    }
    if (-not $MustPreserveWorkflow) {
        $missingFields += 'must_preserve_workflow'
    }

    return [pscustomobject]@{
        complete = [bool](@($missingFields).Count -eq 0)
        missing_fields = @($missingFields)
    }
}

function Get-VgoDestructiveIntentAssessment {
    param(
        [AllowEmptyString()] [string]$Prompt = '',
        [AllowNull()] [object]$PromotionPolicy = $null
    )

    $policy = Get-VgoSkillPromotionPolicy -Policy $PromotionPolicy
    $patterns = $policy.destructive_prompt_patterns
    $reasonCodes = @()
    $promptText = if ([string]::IsNullOrWhiteSpace($Prompt)) { '' } else { [string]$Prompt }

    foreach ($property in @($patterns.PSObject.Properties)) {
        $reasonCode = [string]$property.Name
        foreach ($pattern in @($property.Value)) {
            if ([string]::IsNullOrWhiteSpace([string]$pattern)) {
                continue
            }
            try {
                if ([System.Text.RegularExpressions.Regex]::IsMatch($promptText, [string]$pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                    $reasonCodes += $reasonCode
                    break
                }
            } catch {
                continue
            }
        }
    }

    $reasonCodes = @($reasonCodes | Select-Object -Unique)
    return [pscustomobject]@{
        destructive = [bool](@($reasonCodes).Count -gt 0)
        destructive_reason_codes = @($reasonCodes)
        rollback_possible = [bool](@($reasonCodes).Count -gt 0)
        snapshot_required = [bool](@($reasonCodes).Count -gt 0)
    }
}

function Get-VgoSkillPromotionMetadata {
    param(
        [AllowEmptyString()] [string]$Prompt = '',
        [AllowEmptyString()] [string]$SkillMdPath = '',
        [AllowEmptyString()] [string]$SkillRoot = '',
        [AllowEmptyString()] [string]$Description = '',
        [AllowNull()] [object]$RequiredInputs = $null,
        [AllowNull()] [object]$ExpectedOutputs = $null,
        [AllowEmptyString()] [string]$VerificationExpectation = '',
        [bool]$NativeUsageRequired = $true,
        [bool]$MustPreserveWorkflow = $true,
        [AllowNull()] [object]$PromotionPolicy = $null
    )

    $policy = Get-VgoSkillPromotionPolicy -Policy $PromotionPolicy
    $destructive = Get-VgoDestructiveIntentAssessment -Prompt $Prompt -PromotionPolicy $policy
    $contract = Get-VgoSkillContractCompleteness `
        -SkillMdPath $SkillMdPath `
        -SkillRoot $SkillRoot `
        -Description $Description `
        -RequiredInputs $RequiredInputs `
        -ExpectedOutputs $ExpectedOutputs `
        -VerificationExpectation $VerificationExpectation `
        -NativeUsageRequired $NativeUsageRequired `
        -MustPreserveWorkflow $MustPreserveWorkflow

    $recommendedAction = 'surface_only'
    if (-not [bool]$policy.promotion_enabled) {
        $recommendedAction = 'disabled'
    } elseif ([bool]$destructive.destructive) {
        $recommendedAction = 'require_confirmation'
    } elseif ([bool]$policy.require_contract_complete -and -not [bool]$contract.complete) {
        $recommendedAction = 'degrade_missing_contract'
    } elseif ([bool]$policy.allow_auto_dispatch_when_non_destructive) {
        $recommendedAction = 'auto_dispatch'
    }

    $promotionEligible = [bool](
        [bool]$policy.promotion_enabled -and
        -not [bool]$destructive.destructive -and
        (
            -not [bool]$policy.require_contract_complete -or
            [bool]$contract.complete
        )
    )

    return [pscustomobject]@{
        promotion_enabled = [bool]$policy.promotion_enabled
        promotion_eligible = $promotionEligible
        destructive = [bool]$destructive.destructive
        destructive_reason_codes = @($destructive.destructive_reason_codes)
        rollback_possible = [bool]$destructive.rollback_possible
        snapshot_required = [bool]$destructive.snapshot_required
        contract_complete = [bool]$contract.complete
        contract_missing_fields = @($contract.missing_fields)
        recommended_promotion_action = [string]$recommendedAction
    }
}
