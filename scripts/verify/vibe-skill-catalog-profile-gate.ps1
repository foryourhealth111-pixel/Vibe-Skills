param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

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

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Resolve-CatalogPackagingPath {
    param([string]$RepoRoot)

    $runtimePackagingPath = Join-Path $RepoRoot 'config\runtime-core-packaging.json'
    $runtimePackaging = Read-JsonFile -Path $runtimePackagingPath
    $manifestRel = [string]$runtimePackaging.catalog_packaging_manifest
    if ([string]::IsNullOrWhiteSpace($manifestRel)) {
        $manifestRel = 'config/skill-catalog-packaging.json'
    }
    return (Join-Path $RepoRoot $manifestRel)
}

function Test-SkillDirectory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }

    return (Test-Path -LiteralPath (Join-Path $Path 'SKILL.md')) -or
        (Test-Path -LiteralPath (Join-Path $Path 'SKILL.runtime-mirror.md'))
}

function Get-PropertyNames {
    param([object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Collections.IDictionary]) {
        return @($Value.Keys | ForEach-Object { [string]$_ })
    }
    return @($Value.PSObject.Properties.Name | ForEach-Object { [string]$_ })
}

function Get-MapValue {
    param(
        [object]$Map,
        [string]$Key
    )

    if ($null -eq $Map) { return $null }
    if ($Map -is [System.Collections.IDictionary]) {
        return $Map[$Key]
    }
    return $Map.$Key
}

function Get-OptionalCollectionProperty {
    param(
        [object]$Object,
        [string]$PropertyName
    )

    if ($null -eq $Object) { return @() }
    if ($Object.PSObject.Properties.Name -notcontains $PropertyName) {
        return @()
    }

    return @($Object.$PropertyName)
}

function Resolve-CatalogProfileSkillNames {
    param(
        [string]$ProfileId,
        [object]$Profiles,
        [object]$Groups,
        [string]$CatalogRoot,
        [System.Collections.Generic.HashSet[string]]$Seen
    )

    $names = [System.Collections.Generic.HashSet[string]]::new()
    if ($Seen.Contains($ProfileId)) {
        return $names
    }
    $Seen.Add($ProfileId) | Out-Null

    $profile = Get-MapValue -Map $Profiles -Key $ProfileId
    if ($null -eq $profile) {
        throw "Unknown catalog profile: $ProfileId"
    }

    foreach ($skillName in (Get-OptionalCollectionProperty -Object $profile -PropertyName 'skills')) {
        $text = [string]$skillName
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            $names.Add($text) | Out-Null
        }
    }

    foreach ($groupId in (Get-OptionalCollectionProperty -Object $profile -PropertyName 'groups')) {
        $group = Get-MapValue -Map $Groups -Key ([string]$groupId)
        if ($null -eq $group) {
            throw "Unknown catalog group '$groupId' referenced by profile '$ProfileId'"
        }
        foreach ($skillName in (Get-OptionalCollectionProperty -Object $group -PropertyName 'skills')) {
            $text = [string]$skillName
            if (-not [string]::IsNullOrWhiteSpace($text)) {
                $names.Add($text) | Out-Null
            }
        }
    }

    foreach ($nestedProfileId in (Get-OptionalCollectionProperty -Object $profile -PropertyName 'include_profiles')) {
        $nested = Resolve-CatalogProfileSkillNames -ProfileId ([string]$nestedProfileId) -Profiles $Profiles -Groups $Groups -CatalogRoot $CatalogRoot -Seen $Seen
        foreach ($skillName in $nested) {
            $names.Add([string]$skillName) | Out-Null
        }
    }

    if ([bool]$profile.include_all_bundled) {
        foreach ($candidate in Get-ChildItem -LiteralPath $CatalogRoot -Directory) {
            if (Test-SkillDirectory -Path $candidate.FullName) {
                $names.Add([string]$candidate.Name) | Out-Null
            }
        }
    }

    foreach ($excluded in (Get-OptionalCollectionProperty -Object $profile -PropertyName 'exclude_skills')) {
        $text = [string]$excluded
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            $names.Remove($text) | Out-Null
        }
    }

    $names.Remove('vibe') | Out-Null
    return $names
}

. (Join-Path $PSScriptRoot "..\common\vibe-governance-helpers.ps1")
$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot

$runtimePackagingPath = Join-Path $repoRoot 'config\runtime-core-packaging.json'
$minimalManifestPath = Join-Path $repoRoot 'config\runtime-core-packaging.minimal.json'
$fullManifestPath = Join-Path $repoRoot 'config\runtime-core-packaging.full.json'
$catalogPackagingPath = Resolve-CatalogPackagingPath -RepoRoot $repoRoot

$assertions = @()
$assertions += Assert-True -Condition (Test-Path -LiteralPath $runtimePackagingPath) -Message 'runtime-core packaging manifest exists'
$assertions += Assert-True -Condition (Test-Path -LiteralPath $minimalManifestPath) -Message 'runtime-core minimal manifest exists'
$assertions += Assert-True -Condition (Test-Path -LiteralPath $fullManifestPath) -Message 'runtime-core full manifest exists'
$assertions += Assert-True -Condition (Test-Path -LiteralPath $catalogPackagingPath) -Message 'skill catalog packaging manifest exists'

if ($assertions -contains $false) {
    exit 1
}

$runtimePackaging = Read-JsonFile -Path $runtimePackagingPath
$minimalManifest = Read-JsonFile -Path $minimalManifestPath
$fullManifest = Read-JsonFile -Path $fullManifestPath
$catalogPackaging = Read-JsonFile -Path $catalogPackagingPath

$profilesPath = Join-Path $repoRoot ([string]$catalogPackaging.profiles_manifest)
$groupsPath = Join-Path $repoRoot ([string]$catalogPackaging.groups_manifest)
$catalogRoot = Join-Path $repoRoot ([string]$catalogPackaging.catalog_root)

$assertions += Assert-True -Condition (Test-Path -LiteralPath $profilesPath) -Message 'skill catalog profiles manifest exists'
$assertions += Assert-True -Condition (Test-Path -LiteralPath $groupsPath) -Message 'skill catalog groups manifest exists'
$assertions += Assert-True -Condition (Test-Path -LiteralPath $catalogRoot -PathType Container) -Message 'skill catalog root exists'

if ($assertions -contains $false) {
    exit 1
}

$profilesDoc = Read-JsonFile -Path $profilesPath
$groupsDoc = Read-JsonFile -Path $groupsPath
$profiles = $profilesDoc.profiles
$groups = $groupsDoc.groups

$assertions += Assert-True -Condition ((Get-PropertyNames -Value $profiles) -contains 'foundation-workflow') -Message 'catalog profiles declare foundation-workflow'
$assertions += Assert-True -Condition ((Get-PropertyNames -Value $profiles) -contains 'default-full') -Message 'catalog profiles declare default-full'
$assertions += Assert-True -Condition ((Get-PropertyNames -Value $groups) -contains 'workflow-foundation') -Message 'catalog groups declare workflow-foundation'
$assertions += Assert-True -Condition ((Get-PropertyNames -Value $groups) -contains 'optional-review') -Message 'catalog groups declare optional-review'
$assertions += Assert-True -Condition ([string]$minimalManifest.catalog_profile -eq 'foundation-workflow') -Message 'minimal runtime-core manifest binds foundation-workflow catalog profile'
$assertions += Assert-True -Condition ([string]$fullManifest.catalog_profile -eq 'default-full') -Message 'full runtime-core manifest binds default-full catalog profile'
$assertions += Assert-True -Condition (-not [bool]$minimalManifest.copy_bundled_skills) -Message 'minimal runtime-core manifest does not copy bundled skills wholesale'
$assertions += Assert-True -Condition (-not [bool]$fullManifest.copy_bundled_skills) -Message 'full runtime-core manifest does not copy bundled skills wholesale'

$profileResults = @()
foreach ($profileId in @('foundation-workflow', 'default-full')) {
    $seen = [System.Collections.Generic.HashSet[string]]::new()
    $resolved = Resolve-CatalogProfileSkillNames -ProfileId $profileId -Profiles $profiles -Groups $groups -CatalogRoot $catalogRoot -Seen $seen
    $resolvedList = @($resolved | Sort-Object)
    $missing = @()
    foreach ($skillName in $resolvedList) {
        if (-not (Test-SkillDirectory -Path (Join-Path $catalogRoot $skillName))) {
            $missing += $skillName
        }
    }

    $assertions += Assert-True -Condition ($resolvedList.Count -gt 0) -Message ("catalog profile '{0}' resolves at least one skill" -f $profileId)
    $assertions += Assert-True -Condition (@($missing).Count -eq 0) -Message ("catalog profile '{0}' resolves only valid skill directories" -f $profileId)
    $assertions += Assert-True -Condition ('shared-templates' -notin $resolvedList) -Message ("catalog profile '{0}' excludes non-skill template directories" -f $profileId)
    $assertions += Assert-True -Condition ('.system' -notin $resolvedList) -Message ("catalog profile '{0}' excludes nested system skill containers" -f $profileId)

    $profileResults += [pscustomobject]@{
        profile_id = $profileId
        resolved_skill_count = $resolvedList.Count
        resolved_skill_names = $resolvedList
        missing_skill_dirs = @($missing | Sort-Object)
    }
}

$result = [ordered]@{
    runtime_packaging = [ordered]@{
        profile_manifests = $runtimePackaging.profile_manifests
        minimal_catalog_profile = [string]$minimalManifest.catalog_profile
        full_catalog_profile = [string]$fullManifest.catalog_profile
    }
    skill_catalog = [ordered]@{
        package_id = [string]$catalogPackaging.package_id
        catalog_root = [string]$catalogPackaging.catalog_root
        profiles_manifest = [string]$catalogPackaging.profiles_manifest
        groups_manifest = [string]$catalogPackaging.groups_manifest
        profiles = $profileResults
    }
}

if ($WriteArtifacts) {
    $outputRoot = $OutputDirectory
    if ([string]::IsNullOrWhiteSpace($outputRoot)) {
        $outputRoot = Join-Path $repoRoot 'outputs\runtime\verification'
    }
    New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
    $jsonPath = Join-Path $outputRoot 'vibe-skill-catalog-profile-gate.json'
    $mdPath = Join-Path $outputRoot 'vibe-skill-catalog-profile-gate.md'
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    $markdownLines = [System.Collections.Generic.List[string]]::new()
    $markdownLines.Add('# Vibe Skill Catalog Profile Gate')
    $markdownLines.Add('')
    $markdownLines.Add([string]::Format('- package_id: `{0}`', $result.skill_catalog.package_id))
    $markdownLines.Add([string]::Format('- catalog_root: `{0}`', $result.skill_catalog.catalog_root))
    $markdownLines.Add([string]::Format('- minimal profile: `{0}`', $result.runtime_packaging.minimal_catalog_profile))
    $markdownLines.Add([string]::Format('- full profile: `{0}`', $result.runtime_packaging.full_catalog_profile))
    $markdownLines | Set-Content -LiteralPath $mdPath -Encoding UTF8
}

if ($assertions -contains $false) {
    exit 1
}

Write-Host 'Skill catalog profile gate passed.' -ForegroundColor Green
