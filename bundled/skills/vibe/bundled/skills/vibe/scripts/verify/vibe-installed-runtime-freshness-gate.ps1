param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts,
    [switch]$WriteReceipt
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $TargetRoot = Resolve-VgoTargetRoot
}

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
function Remove-IgnoredKeys {
    param(
        [object]$Node,
        [string[]]$IgnoreKeys
    )
    if ($null -eq $Node) { return $null }
    if ($Node -is [System.Management.Automation.PSCustomObject]) {
        $ordered = [ordered]@{}
        foreach ($prop in @($Node.PSObject.Properties) | Sort-Object -Property Name) {
            $key = [string]$prop.Name
            if ($IgnoreKeys -contains $key) { continue }
            $ordered[$key] = Remove-IgnoredKeys -Node $prop.Value -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }
    if ($Node -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Node.Keys) | Sort-Object) {
            $keyText = [string]$key
            if ($IgnoreKeys -contains $keyText) { continue }
            $ordered[$keyText] = Remove-IgnoredKeys -Node $Node[$key] -IgnoreKeys $IgnoreKeys
        }
        return $ordered
    }
    if ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
        $items = @()
        foreach ($item in $Node) {
            $items += Remove-IgnoredKeys -Node $item -IgnoreKeys $IgnoreKeys
        }
        return $items
    }
    return $Node
}
function Get-NormalizedJsonHash {
    param(
        [string]$Path,
        [string[]]$IgnoreKeys
    )
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $obj = $raw | ConvertFrom-Json
    $normalizedObj = Remove-IgnoredKeys -Node $obj -IgnoreKeys $IgnoreKeys
    $normalized = $normalizedObj | ConvertTo-Json -Depth 100 -Compress
    return (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($normalized))) -Algorithm SHA256).Hash
}
function Get-RelativePathPortable {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )
    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull = $baseFull + [System.IO.Path]::DirectorySeparatorChar
    }
    if ($targetFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $targetFull.Substring($baseFull.Length).Replace('\', '/')
    }
    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('\', '/')
}
function Get-FileParity {
    param(
        [string]$MainPath,
        [string]$InstalledPath,
        [string[]]$IgnoreJsonKeys
    )
    if (-not (Test-Path -LiteralPath $MainPath) -or -not (Test-Path -LiteralPath $InstalledPath)) {
        return $false
    }
    $mainExt = [System.IO.Path]::GetExtension($MainPath).ToLowerInvariant()
    $installedExt = [System.IO.Path]::GetExtension($InstalledPath).ToLowerInvariant()
    if ($mainExt -eq '.json' -and $installedExt -eq '.json') {
        return (Get-NormalizedJsonHash -Path $MainPath -IgnoreKeys $IgnoreJsonKeys) -eq (Get-NormalizedJsonHash -Path $InstalledPath -IgnoreKeys $IgnoreJsonKeys)
    }
    return (Get-FileHash -LiteralPath $MainPath -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $InstalledPath -Algorithm SHA256).Hash
}
function Get-InstalledRuntimeConfig {
    param(
        [Parameter(Mandatory)] [psobject]$Governance
    )
    $defaults = [ordered]@{
        target_relpath = 'skills/vibe'
        receipt_relpath = 'skills/vibe/outputs/runtime-freshness-receipt.json'
        post_install_gate = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
        required_runtime_markers = @(
            'SKILL.md',
            'config/version-governance.json',
            'scripts/router/resolve-pack-route.ps1',
            'scripts/common/vibe-governance-helpers.ps1'
        )
        require_nested_bundled_root = $false
    }
    $runtimeConfig = $null
    if ($Governance.PSObject.Properties.Name -contains 'runtime' -and $null -ne $Governance.runtime) {
        if ($Governance.runtime.PSObject.Properties.Name -contains 'installed_runtime') {
            $runtimeConfig = $Governance.runtime.installed_runtime
        }
    }
    if ($null -eq $runtimeConfig) {
        return [pscustomobject]$defaults
    }
    $merged = [ordered]@{}
    foreach ($key in $defaults.Keys) {
        if ($runtimeConfig.PSObject.Properties.Name -contains $key -and $null -ne $runtimeConfig.$key) {
            $merged[$key] = $runtimeConfig.$key
        } else {
            $merged[$key] = $defaults[$key]
        }
    }
    return [pscustomobject]$merged
}
function Test-InstalledSkillResolution {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot,
        [Parameter(Mandatory)] [string]$InstalledRoot,
        [Parameter(Mandatory)] [string]$Skill
    )

    $modulePath = Join-Path $InstalledRoot 'scripts\router\modules\46-confirm-ui.ps1'
    $expectedPath = Join-Path (Join-Path $TargetRoot 'skills') (Join-Path $Skill 'SKILL.md')
    $result = [ordered]@{
        skill = [string]$Skill
        module_path = [System.IO.Path]::GetFullPath($modulePath)
        expected_path = [System.IO.Path]::GetFullPath($expectedPath)
        module_exists = [bool](Test-Path -LiteralPath $modulePath)
        expected_exists = [bool](Test-Path -LiteralPath $expectedPath)
        resolved_path = $null
        resolved_exists = $false
        matches_expected = $false
        uses_target_skills_root = $false
        error = $null
    }

    if (-not $result.module_exists) {
        $result.error = 'installed confirm-ui module missing'
        return [pscustomobject]$result
    }

    $previousCodexHome = $env:CODEX_HOME
    try {
        $env:CODEX_HOME = [System.IO.Path]::GetFullPath($TargetRoot)
        . $modulePath
        $resolved = Resolve-SkillMdPath -RepoRoot '' -Skill $Skill
        if (-not [string]::IsNullOrWhiteSpace($resolved)) {
            $resolvedFull = [System.IO.Path]::GetFullPath($resolved)
            $result.resolved_path = $resolvedFull
            $result.resolved_exists = [bool](Test-Path -LiteralPath $resolvedFull)
            $result.matches_expected = $resolvedFull -eq $result.expected_path
            $targetSkillsRoot = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
            if (-not $targetSkillsRoot.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
                $targetSkillsRoot = $targetSkillsRoot + [System.IO.Path]::DirectorySeparatorChar
            }
            $result.uses_target_skills_root = $resolvedFull.StartsWith($targetSkillsRoot, [System.StringComparison]::OrdinalIgnoreCase)
        }
    } catch {
        $result.error = $_.Exception.Message
    } finally {
        $env:CODEX_HOME = $previousCodexHome
    }

    return [pscustomobject]$result
}
$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$governance = $context.governance
$canonicalRoot = $context.canonicalRoot
$ignoreJsonKeys = @($governance.packaging.normalized_json_ignore_keys)
$mirrorFiles = @($governance.packaging.mirror.files)
$mirrorDirs = @($governance.packaging.mirror.directories)
$runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
$installedRel = [string]$runtimeConfig.target_relpath
if ([string]::IsNullOrWhiteSpace($installedRel)) {
    throw 'runtime.installed_runtime.target_relpath is required'
}
$installedRoot = Join-Path $TargetRoot $installedRel
$receiptRel = [string]$runtimeConfig.receipt_relpath
$receiptPath = if ([string]::IsNullOrWhiteSpace($receiptRel)) { $null } else { Join-Path $TargetRoot $receiptRel }
$requiredRuntimeMarkers = @($runtimeConfig.required_runtime_markers)
$allowInstalledOnly = @($governance.packaging.allow_bundled_only)
if ($runtimeConfig.PSObject.Properties.Name -contains 'allow_installed_only' -and $null -ne $runtimeConfig.allow_installed_only) {
    $allowInstalledOnly += @($runtimeConfig.allow_installed_only)
}
$allowInstalledOnly = @($allowInstalledOnly | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
$requireNestedBundledRoot = $false
if ($runtimeConfig.PSObject.Properties.Name -contains 'require_nested_bundled_root') {
    $requireNestedBundledRoot = [bool]$runtimeConfig.require_nested_bundled_root
}
$installedNestedRoot = Join-Path $installedRoot 'bundled\skills\vibe'
$results = [ordered]@{
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    installed_root = [System.IO.Path]::GetFullPath($installedRoot)
    receipt_path = if ($receiptPath) { [System.IO.Path]::GetFullPath($receiptPath) } else { $null }
    release = [ordered]@{
        version = [string]$governance.release.version
        updated = [string]$governance.release.updated
    }
    files = @()
    directories = @()
    runtime_markers = @()
    behavior = [ordered]@{
        installed_skill_resolution = @()
    }
    nested = [ordered]@{
        required = [bool]$requireNestedBundledRoot
        path = [System.IO.Path]::GetFullPath($installedNestedRoot)
        exists = $false
    }
}
$assertions = @()
Write-Host '=== VCO Installed Runtime Freshness Gate ==='
Write-Host ("Repo root    : {0}" -f $repoRoot)
Write-Host ("Target root  : {0}" -f $TargetRoot)
Write-Host ("Installed root: {0}" -f $installedRoot)
$installedExists = Test-Path -LiteralPath $installedRoot
$assertions += Assert-True -Condition $installedExists -Message '[runtime] installed vibe root exists'
$results.nested.exists = Test-Path -LiteralPath $installedNestedRoot
if ($requireNestedBundledRoot) {
    $assertions += Assert-True -Condition $results.nested.exists -Message '[runtime] nested bundled root exists'
}
foreach ($rel in $mirrorFiles) {
    $mainPath = Join-Path $canonicalRoot $rel
    $installedPath = Join-Path $installedRoot $rel
    $mainExists = Test-Path -LiteralPath $mainPath
    $installedFileExists = Test-Path -LiteralPath $installedPath
    $parity = $false
    if ($mainExists -and $installedFileExists) {
        $parity = Get-FileParity -MainPath $mainPath -InstalledPath $installedPath -IgnoreJsonKeys $ignoreJsonKeys
    }
    $assertions += Assert-True -Condition $mainExists -Message "[file:$rel] canonical exists"
    $assertions += Assert-True -Condition $installedFileExists -Message "[file:$rel] installed exists"
    if ($mainExists -and $installedFileExists) {
        $assertions += Assert-True -Condition $parity -Message "[file:$rel] parity"
    }
    $results.files += [pscustomobject]@{
        path = [string]$rel
        canonical_exists = [bool]$mainExists
        installed_exists = [bool]$installedFileExists
        parity = [bool]$parity
    }
}
foreach ($dir in $mirrorDirs) {
    $mainDir = Join-Path $canonicalRoot $dir
    $installedDir = Join-Path $installedRoot $dir
    $mainExists = Test-Path -LiteralPath $mainDir
    $installedDirExists = Test-Path -LiteralPath $installedDir
    $assertions += Assert-True -Condition $mainExists -Message "[dir:$dir] canonical exists"
    $assertions += Assert-True -Condition $installedDirExists -Message "[dir:$dir] installed exists"
    $onlyMain = @()
    $onlyInstalled = @()
    $diffFiles = @()
    if ($mainExists -and $installedDirExists) {
        $mainFiles = @(
            Get-ChildItem -LiteralPath $mainDir -Recurse -File | ForEach-Object {
                Get-RelativePathPortable -BasePath $mainDir -TargetPath $_.FullName
            }
        )
        $installedFiles = @(
            Get-ChildItem -LiteralPath $installedDir -Recurse -File | ForEach-Object {
                Get-RelativePathPortable -BasePath $installedDir -TargetPath $_.FullName
            }
        )
        $onlyMain = @($mainFiles | Where-Object { $_ -notin $installedFiles } | Sort-Object)
        $onlyInstalledRaw = @($installedFiles | Where-Object { $_ -notin $mainFiles })
        $onlyInstalled = @(
            $onlyInstalledRaw | Where-Object {
                $fullRel = "{0}/{1}" -f $dir, $_
                $allowInstalledOnly -notcontains $fullRel
            } | Sort-Object
        )
        $common = @($mainFiles | Where-Object { $_ -in $installedFiles } | Sort-Object)
        foreach ($relPath in $common) {
            $mainPath = Join-Path $mainDir $relPath
            $installedPath = Join-Path $installedDir $relPath
            $same = Get-FileParity -MainPath $mainPath -InstalledPath $installedPath -IgnoreJsonKeys $ignoreJsonKeys
            if (-not $same) {
                $diffFiles += $relPath
            }
        }
    }
    $assertions += Assert-True -Condition ($onlyMain.Count -eq 0) -Message "[dir:$dir] no files missing in installed runtime"
    $assertions += Assert-True -Condition ($onlyInstalled.Count -eq 0) -Message "[dir:$dir] no unexpected installed-only files"
    $assertions += Assert-True -Condition ($diffFiles.Count -eq 0) -Message "[dir:$dir] file parity"
    $results.directories += [pscustomobject]@{
        path = [string]$dir
        only_in_canonical = @($onlyMain)
        only_in_installed = @($onlyInstalled)
        diff_files = @($diffFiles)
    }
}
foreach ($rel in $requiredRuntimeMarkers) {
    $mainPath = Join-Path $canonicalRoot $rel
    $installedPath = Join-Path $installedRoot $rel
    $mainExists = Test-Path -LiteralPath $mainPath
    $installedMarkerExists = Test-Path -LiteralPath $installedPath
    $parity = $false
    if ($mainExists -and $installedMarkerExists) {
        $parity = Get-FileParity -MainPath $mainPath -InstalledPath $installedPath -IgnoreJsonKeys $ignoreJsonKeys
    }
    $assertions += Assert-True -Condition $mainExists -Message "[marker:$rel] canonical exists"
    $assertions += Assert-True -Condition $installedMarkerExists -Message "[marker:$rel] installed exists"
    if ($mainExists -and $installedMarkerExists) {
        $assertions += Assert-True -Condition $parity -Message "[marker:$rel] parity"
    }
    $results.runtime_markers += [pscustomobject]@{
        path = [string]$rel
        canonical_exists = [bool]$mainExists
        installed_exists = [bool]$installedMarkerExists
        parity = [bool]$parity
    }
}
$skillsToResolve = @('vibe', 'dialectic')
foreach ($skill in $skillsToResolve) {
    $resolution = Test-InstalledSkillResolution -TargetRoot $TargetRoot -InstalledRoot $installedRoot -Skill $skill
    $assertions += Assert-True -Condition $resolution.module_exists -Message "[behavior:$skill] installed confirm-ui module exists"
    $assertions += Assert-True -Condition $resolution.expected_exists -Message "[behavior:$skill] expected installed skill exists"
    $assertions += Assert-True -Condition $resolution.resolved_exists -Message "[behavior:$skill] resolved skill path exists"
    $assertions += Assert-True -Condition $resolution.uses_target_skills_root -Message "[behavior:$skill] resolves under target skills root"
    $assertions += Assert-True -Condition $resolution.matches_expected -Message "[behavior:$skill] resolves expected installed skill path"
    $results.behavior.installed_skill_resolution += $resolution
}
$total = @($assertions).Count
$passed = @($assertions | Where-Object { $_ }).Count
$failed = $total - $passed
$gatePass = ($failed -eq 0)
Write-Host ''
Write-Host '=== Summary ==='
Write-Host ("Total assertions: {0}" -f $total)
Write-Host ("Passed: {0}" -f $passed)
Write-Host ("Failed: {0}" -f $failed)
Write-Host ("Gate Result: {0}" -f $(if ($gatePass) { 'PASS' } else { 'FAIL' }))
if ($WriteArtifacts) {
    $outDir = Join-Path $repoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $jsonPath = Join-Path $outDir 'vibe-installed-runtime-freshness-gate.json'
    $mdPath = Join-Path $outDir 'vibe-installed-runtime-freshness-gate.md'
    $artifact = [ordered]@{
        generated_at = [DateTime]::UtcNow.ToString('o')
        gate_result = if ($gatePass) { 'PASS' } else { 'FAIL' }
        assertions = [ordered]@{
            total = $total
            passed = $passed
            failed = $failed
        }
        results = $results
    }
    $artifact | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    $md = @(
        '# VCO Installed Runtime Freshness Gate',
        '',
        ("- Gate Result: **{0}**" -f $artifact.gate_result),
        ("- Assertions: total={0}, passed={1}, failed={2}" -f $total, $passed, $failed),
        ('- Target root: `{0}`' -f [System.IO.Path]::GetFullPath($TargetRoot)),
        ('- Installed root: `{0}`' -f [System.IO.Path]::GetFullPath($installedRoot)),
        ('- release.version: `{0}`' -f $results.release.version),
        ('- release.updated: `{0}`' -f $results.release.updated)
    ) -join "`n"
    Set-Content -LiteralPath $mdPath -Value $md -Encoding UTF8
}
if ($WriteReceipt -and $receiptPath) {
    if ($gatePass) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $receiptPath) | Out-Null
        $receipt = [ordered]@{
            generated_at = [DateTime]::UtcNow.ToString('o')
            gate_result = 'PASS'
            release = $results.release
            target_root = [System.IO.Path]::GetFullPath($TargetRoot)
            installed_root = [System.IO.Path]::GetFullPath($installedRoot)
            receipt_version = 1
        }
        $receipt | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    } elseif (Test-Path -LiteralPath $receiptPath) {
        Remove-Item -LiteralPath $receiptPath -Force -ErrorAction SilentlyContinue
    }
}
if (-not $gatePass) {
    exit 1
}
