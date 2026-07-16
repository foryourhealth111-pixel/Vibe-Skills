param(
    [string]$OutputDir = "",
    [switch]$CompareInstalled,
    [string]$InstalledPluginsPath = "",
    [switch]$NoNpm,
    [switch]$NoGitHub,
    [int]$MaxRepos = 0,
    [string]$CorpusManifestPath = "",
    [string]$MirrorRoot = "",
    [switch]$WriteJson
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "JSON file not found: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-TextFile {
    param(
        [string]$Path,
        [string]$Content
    )
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

function Normalize-GitHubRepoUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return "" }
    $u = $Url.Trim()
    $u = $u -replace "\.git$", ""
    $u = $u.TrimEnd("/")
    return $u
}

function Parse-GitHubOwnerRepo {
    param([string]$RepoUrl)
    $u = Normalize-GitHubRepoUrl -Url $RepoUrl
    if ($u -notmatch "^https://github\.com/([^/]+)/([^/]+)$") { return $null }
    return [pscustomobject]@{
        owner = $Matches[1]
        repo = $Matches[2]
    }
}

function Get-GitHubHeaders {
    $token = ""
    if ($env:GITHUB_TOKEN) { $token = $env:GITHUB_TOKEN }
    elseif ($env:GH_TOKEN) { $token = $env:GH_TOKEN }

    $headers = @{
        "Accept"               = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent"           = "vco-skills-codex-upstream-audit"
    }
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $headers["Authorization"] = "Bearer $token"
    }
    return $headers
}

function Try-InvokeRestJson {
    param(
        [string]$Url,
        [hashtable]$Headers = @{}
    )
    try {
        return Invoke-RestMethod -Uri $Url -Headers $Headers -Method Get -ErrorAction Stop
    } catch {
        return $null
    }
}

function To-GitRemoteUrl {
    param([string]$RepoUrl)
    $u = Normalize-GitHubRepoUrl -Url $RepoUrl
    if ([string]::IsNullOrWhiteSpace($u)) { return "" }
    if ($u.EndsWith(".git")) { return $u }
    return ("{0}.git" -f $u)
}

function Try-ParseSemVer {
    param([string]$TagName)
    if ([string]::IsNullOrWhiteSpace($TagName)) { return $null }
    $t = $TagName.Trim()
    if ($t -match '^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$') {
        return [pscustomobject]@{
            name  = $TagName
            major = [int]$Matches[1]
            minor = [int]$Matches[2]
            patch = [int]$Matches[3]
        }
    }
    return $null
}

function Try-GitLsRemoteHead {
    param([string]$RepoUrl)
    $remote = To-GitRemoteUrl -RepoUrl $RepoUrl
    if ([string]::IsNullOrWhiteSpace($remote)) { return $null }
    try {
        $lines = @(git ls-remote --symref $remote HEAD 2>$null)
    } catch {
        return $null
    }
    $branch = ""
    $sha = ""
    foreach ($line in $lines) {
        if ($line -match '^ref:\s+refs/heads/([^ ]+)\s+HEAD$') {
            $branch = [string]$Matches[1]
            continue
        }
        if ($line -match '^([a-f0-9]{40})\s+HEAD$') {
            $sha = [string]$Matches[1]
        }
    }
    if ([string]::IsNullOrWhiteSpace($sha)) { return $null }
    return [pscustomobject]@{ branch = $branch; sha = $sha }
}

function Try-GitLsRemoteLatestTag {
    param([string]$RepoUrl)
    $remote = To-GitRemoteUrl -RepoUrl $RepoUrl
    if ([string]::IsNullOrWhiteSpace($remote)) { return "" }
    $tagNames = New-Object System.Collections.Generic.List[string]
    try {
        $lines = @(git ls-remote --tags --refs $remote 2>$null)
    } catch {
        return ""
    }
    foreach ($line in $lines) {
        if ($line -match '^[a-f0-9]{40}\s+refs/tags/(.+)$') {
            $tagNames.Add([string]$Matches[1]) | Out-Null
        }
    }
    if ($tagNames.Count -eq 0) { return "" }
    $best = $null
    foreach ($tagName in $tagNames) {
        $parsed = Try-ParseSemVer -TagName $tagName
        if (-not $parsed) { continue }
        if (-not $best -or
            $parsed.major -gt $best.major -or
            ($parsed.major -eq $best.major -and $parsed.minor -gt $best.minor) -or
            ($parsed.major -eq $best.major -and $parsed.minor -eq $best.minor -and $parsed.patch -gt $best.patch)) {
            $best = $parsed
        }
    }
    if ($best) { return [string]$best.name }
    return [string](@($tagNames | Sort-Object | Select-Object -Last 1))
}

function Try-GetInstalledPluginEntry {
    param(
        [object]$Installed,
        [string]$PluginId
    )
    if (-not $Installed -or -not $Installed.plugins) { return $null }
    $prop = $Installed.plugins.PSObject.Properties | Where-Object { $_.Name -eq $PluginId } | Select-Object -First 1
    if (-not $prop) { return $null }
    $entries = @($prop.Value)
    if ($entries.Count -eq 0) { return $null }
    return ($entries | Select-Object -First 1)
}

function Get-ShortSha {
    param([string]$Sha)
    if ([string]::IsNullOrWhiteSpace($Sha)) { return "" }
    return $Sha.Substring(0, [Math]::Min(7, $Sha.Length))
}

function Resolve-AuditPath {
    param(
        [string]$RepoRoot,
        [string]$Candidate
    )
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return "" }
    return (Resolve-VgoPathSpec -PathSpec $Candidate -RepoRoot $RepoRoot)
}

function Get-MirrorStateText {
    param(
        [string]$Slug,
        [string]$ExpectedHead,
        [object[]]$Roots
    )
    if ([string]::IsNullOrWhiteSpace($Slug) -or $null -eq $Roots -or $Roots.Count -eq 0) {
        return ""
    }
    $states = New-Object System.Collections.Generic.List[string]
    foreach ($root in $Roots) {
        $rootId = [string]$root.id
        $rootPath = [string]$root.path
        if ([string]::IsNullOrWhiteSpace($rootPath) -or -not (Test-Path -LiteralPath $rootPath)) {
            $states.Add(("{0}:missing-root" -f $rootId)) | Out-Null
            continue
        }
        $repoDir = Join-Path $rootPath $Slug
        if (-not (Test-Path -LiteralPath $repoDir)) {
            $states.Add(("{0}:missing" -f $rootId)) | Out-Null
            continue
        }
        if (-not (Test-Path -LiteralPath (Join-Path $repoDir '.git'))) {
            $states.Add(("{0}:present-no-git" -f $rootId)) | Out-Null
            continue
        }
        $actualHead = ""
        try {
            $actualHead = [string](git -C $repoDir rev-parse HEAD 2>$null | Select-Object -First 1)
        } catch {
            $actualHead = ""
        }
        if ([string]::IsNullOrWhiteSpace($actualHead)) {
            $states.Add(("{0}:unresolved" -f $rootId)) | Out-Null
            continue
        }
        if (-not [string]::IsNullOrWhiteSpace($ExpectedHead) -and $actualHead -ne $ExpectedHead) {
            $states.Add(("{0}:drift expected={1} actual={2}" -f $rootId, (Get-ShortSha -Sha $ExpectedHead), (Get-ShortSha -Sha $actualHead))) | Out-Null
        } else {
            $states.Add(("{0}:present@{1}" -f $rootId, (Get-ShortSha -Sha $actualHead))) | Out-Null
        }
    }
    return ($states -join '; ')
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot 'outputs\governance'
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$versionGovernancePath = Join-Path $repoRoot 'config\version-governance.json'
$vcoVersion = ""
if (Test-Path -LiteralPath $versionGovernancePath) {
    $versionGovernance = Read-JsonFile -Path $versionGovernancePath
    if ($versionGovernance.release -and $versionGovernance.release.version) {
        $vcoVersion = [string]$versionGovernance.release.version
    }
}

$manifestPath = Join-Path $repoRoot 'config\plugins-manifest.upstream.json'
$lockPath = Join-Path $repoRoot 'config\upstream-lock.json'
$manifest = $null
$lock = $null
if (Test-Path -LiteralPath $manifestPath) { $manifest = Read-JsonFile -Path $manifestPath }
if (Test-Path -LiteralPath $lockPath) { $lock = Read-JsonFile -Path $lockPath }

if ([string]::IsNullOrWhiteSpace($CorpusManifestPath)) {
    $CorpusManifestPath = Join-Path $repoRoot 'config\upstream-corpus-manifest.json'
}
$corpusManifest = $null
if (Test-Path -LiteralPath $CorpusManifestPath) {
    $corpusManifest = Read-JsonFile -Path $CorpusManifestPath
}

$pluginEntries = @()
if ($manifest -and $manifest.plugins) {
    foreach ($tierProperty in @($manifest.plugins.PSObject.Properties)) {
        $tier = [string]$tierProperty.Name
        foreach ($plugin in @($tierProperty.Value)) {
            $repoUrl = ''
            if ($null -ne $plugin -and $plugin.PSObject.Properties.Name -contains 'repo' -and $plugin.repo) {
                $repoUrl = Normalize-GitHubRepoUrl -Url ([string]$plugin.repo)
            }
            if ([string]::IsNullOrWhiteSpace($repoUrl)) { continue }
            $id = if ($plugin.PSObject.Properties.Name -contains 'id' -and $plugin.id) { [string]$plugin.id } elseif ($plugin.PSObject.Properties.Name -contains 'name' -and $plugin.name) { [string]$plugin.name } else { $repoUrl }
            $pluginEntries += [pscustomobject]@{
                source = "plugins-manifest.$tier"
                id = $id
                name = $id
                repo_url = $repoUrl
                slug = ""
                lane = ""
                status = ""
                owner = ""
                next_action = ""
                observed_head_sha = ""
                license = ""
            }
        }
    }
}

$lockEntries = @()
if ($lock -and $lock.dependencies) {
    foreach ($dependency in @($lock.dependencies)) {
        $repoUrl = Normalize-GitHubRepoUrl -Url ([string]$dependency.upstream_repo)
        if ([string]::IsNullOrWhiteSpace($repoUrl)) { continue }
        $lockEntries += [pscustomobject]@{
            source = 'upstream-lock'
            id = [string]$dependency.id
            name = [string]$dependency.id
            repo_url = $repoUrl
            slug = ""
            lane = ""
            status = ""
            owner = ""
            next_action = ""
            observed_head_sha = [string]$dependency.upstream_ref
            license = ""
        }
    }
}

$corpusEntries = @()
$corpusSummary = [ordered]@{}
$mirrorRoots = @()
if ($corpusManifest) {
    foreach ($entry in @($corpusManifest.entries)) {
        $corpusEntries += [pscustomobject]@{
            source = 'upstream-corpus-manifest'
            id = [string]$entry.slug
            name = [string]$entry.slug
            repo_url = Normalize-GitHubRepoUrl -Url ([string]$entry.repo_url)
            slug = [string]$entry.slug
            lane = [string]$entry.lane
            status = [string]$entry.status
            owner = [string]$entry.owner
            next_action = [string]$entry.next_action
            observed_head_sha = [string]$entry.observed_head_sha
            license = [string]$entry.license
        }
    }
    if ($corpusManifest.summary) {
        $corpusSummary = [ordered]@{
            total_entries = [int]$corpusManifest.summary.total_entries
            lane_counts = $corpusManifest.summary.lane_counts
            status_counts = $corpusManifest.summary.status_counts
        }
    }
    foreach ($root in @($corpusManifest.mirror_roots)) {
        $mirrorRoots += [pscustomobject]@{
            id = [string]$root.id
            path = Resolve-AuditPath -RepoRoot $repoRoot -Candidate ([string]$root.path)
            required_for_freshness_gate = [bool]$root.required_for_freshness_gate
        }
    }
}
if (-not [string]::IsNullOrWhiteSpace($MirrorRoot)) {
    $mirrorRoots = @([pscustomobject]@{ id = 'override'; path = Resolve-AuditPath -RepoRoot $repoRoot -Candidate $MirrorRoot; required_for_freshness_gate = $true })
}

$allEntries = @($pluginEntries + $lockEntries + $corpusEntries) | Where-Object { -not [string]::IsNullOrWhiteSpace($_.repo_url) }
$repoToSources = @{}
foreach ($entry in $allEntries) {
    if (-not $entry.repo_url.StartsWith('https://github.com/')) { continue }
    if (-not $repoToSources.ContainsKey($entry.repo_url)) {
        $repoToSources[$entry.repo_url] = New-Object System.Collections.Generic.List[object]
    }
    $repoToSources[$entry.repo_url].Add($entry) | Out-Null
}

$installed = $null
if ($CompareInstalled) {
    if ([string]::IsNullOrWhiteSpace($InstalledPluginsPath)) {
        $InstalledPluginsPath = Join-Path (Resolve-VgoTargetRoot) 'plugins\plugins.json'
    }
    if (Test-Path -LiteralPath $InstalledPluginsPath) {
        $installed = Read-JsonFile -Path $InstalledPluginsPath
    }
}

$githubHeaders = Get-GitHubHeaders
$rows = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[string]
$repoUrls = @($repoToSources.Keys | Sort-Object)
if ($MaxRepos -gt 0) {
    $repoUrls = $repoUrls | Select-Object -First $MaxRepos
}

foreach ($repoUrl in $repoUrls) {
    $sources = [object[]]$repoToSources[$repoUrl].ToArray()
    $corpusSource = $sources | Where-Object { $_.source -eq 'upstream-corpus-manifest' } | Select-Object -First 1
    $parsed = Parse-GitHubOwnerRepo -RepoUrl $repoUrl
    if (-not $parsed) { continue }

    $slug = if ($corpusSource -and $corpusSource.slug) { [string]$corpusSource.slug } else { [string]$parsed.repo }
    $lane = if ($corpusSource -and $corpusSource.lane) { [string]$corpusSource.lane } else { '' }
    $status = if ($corpusSource -and $corpusSource.status) { [string]$corpusSource.status } else { '' }
    $owner = if ($corpusSource -and $corpusSource.owner) { [string]$corpusSource.owner } else { '' }
    $nextAction = if ($corpusSource -and $corpusSource.next_action) { [string]$corpusSource.next_action } else { '' }
    $observedHead = if ($corpusSource -and $corpusSource.observed_head_sha) { [string]$corpusSource.observed_head_sha } else { '' }
    $license = if ($corpusSource -and $corpusSource.license) { [string]$corpusSource.license } else { '' }

    $defaultBranch = ''
    $headSha = ''
    $headDate = ''
    $latestRelease = ''
    $latestReleaseDate = ''
    $latestTag = ''
    $pushedAt = ''

    $lsRemoteHead = Try-GitLsRemoteHead -RepoUrl $repoUrl
    if ($lsRemoteHead) {
        $defaultBranch = [string]$lsRemoteHead.branch
        $headSha = [string]$lsRemoteHead.sha
    }
    $latestTag = Try-GitLsRemoteLatestTag -RepoUrl $repoUrl

    if (-not $NoGitHub) {
        $repoInfo = Try-InvokeRestJson -Url ("https://api.github.com/repos/{0}/{1}" -f $parsed.owner, $parsed.repo) -Headers $githubHeaders
        if ($repoInfo) {
            if ([string]::IsNullOrWhiteSpace($defaultBranch) -and $repoInfo.default_branch) {
                $defaultBranch = [string]$repoInfo.default_branch
            }
            if ([string]::IsNullOrWhiteSpace($license) -and $repoInfo.license -and $repoInfo.license.spdx_id) {
                $license = [string]$repoInfo.license.spdx_id
            }
            if ($repoInfo.pushed_at) {
                $pushedAt = [string]$repoInfo.pushed_at
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($defaultBranch)) {
            $headInfo = Try-InvokeRestJson -Url ("https://api.github.com/repos/{0}/{1}/commits/{2}" -f $parsed.owner, $parsed.repo, $defaultBranch) -Headers $githubHeaders
            if ($headInfo) {
                if ([string]::IsNullOrWhiteSpace($headSha) -and $headInfo.sha) {
                    $headSha = [string]$headInfo.sha
                }
                if ($headInfo.commit -and $headInfo.commit.author -and $headInfo.commit.author.date) {
                    $headDate = [string]$headInfo.commit.author.date
                }
            }
        }
        $releaseInfo = Try-InvokeRestJson -Url ("https://api.github.com/repos/{0}/{1}/releases/latest" -f $parsed.owner, $parsed.repo) -Headers $githubHeaders
        if ($releaseInfo) {
            if ($releaseInfo.tag_name) { $latestRelease = [string]$releaseInfo.tag_name }
            if ($releaseInfo.published_at) { $latestReleaseDate = [string]$releaseInfo.published_at }
        }
        if ([string]::IsNullOrWhiteSpace($latestTag)) {
            $tagInfo = Try-InvokeRestJson -Url ("https://api.github.com/repos/{0}/{1}/tags?per_page=1&page=1" -f $parsed.owner, $parsed.repo) -Headers $githubHeaders
            if ($tagInfo -and @($tagInfo).Count -gt 0 -and $tagInfo[0].name) {
                $latestTag = [string]$tagInfo[0].name
            }
        }
    }

    $sourceLabels = @($sources | ForEach-Object { $_.id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
    $sourceLabelText = ($sourceLabels -join ', ')

    $installedText = ''
    if ($CompareInstalled) {
        $installedEntries = @()
        foreach ($src in $sources) {
            if (-not $src.source.StartsWith('plugins-manifest.')) { continue }
            if ([string]::IsNullOrWhiteSpace($src.id)) { continue }
            $entry = Try-GetInstalledPluginEntry -Installed $installed -PluginId $src.id
            if (-not $entry) { continue }
            $version = [string]$entry.version
            $sha = Get-ShortSha -Sha ([string]$entry.gitCommitSha)
            $installedEntries += ("{0}={1}({2})" -f $src.id, $version, $sha)
        }
        if ($installedEntries.Count -gt 0) {
            $installedText = ($installedEntries -join '; ')
        }
    }

    $mirrorState = Get-MirrorStateText -Slug $slug -ExpectedHead $observedHead -Roots $mirrorRoots

    $rows.Add([pscustomobject]@{
        slug = $slug
        repo_url = $repoUrl
        sources = $sourceLabelText
        lane = $lane
        status = $status
        owner = $owner
        next_action = $nextAction
        license = $license
        default_branch = $defaultBranch
        head_sha = $headSha
        head_date = $headDate
        observed_head_sha = $observedHead
        latest_release = $latestRelease
        latest_release_date = $latestReleaseDate
        latest_tag = $latestTag
        pushed_at = $pushedAt
        mirror_state = $mirrorState
        installed = $installedText
    }) | Out-Null
}

$npmRows = New-Object System.Collections.Generic.List[object]

$now = Get-Date
$timestamp = $now.ToString('yyyyMMdd-HHmmss')
$reportPath = Join-Path $OutputDir ("upstream-audit_{0}.md" -f $timestamp)
$jsonPath = Join-Path $OutputDir ("upstream-audit_{0}.json" -f $timestamp)

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('# VCO Upstream Audit') | Out-Null
$lines.Add('') | Out-Null
if (-not [string]::IsNullOrWhiteSpace($vcoVersion)) {
    $lines.Add(("- VCO version: {0}" -f $vcoVersion)) | Out-Null
}
$lines.Add(("- Generated: {0}" -f $now.ToString('s'))) | Out-Null
$lines.Add(('- Repo root: `' + $repoRoot + '`')) | Out-Null
if (-not [string]::IsNullOrWhiteSpace($CorpusManifestPath) -and (Test-Path -LiteralPath $CorpusManifestPath)) {
    $lines.Add(('- Corpus manifest: `' + $CorpusManifestPath + '`')) | Out-Null
}
if ($mirrorRoots.Count -gt 0) {
    $rootText = @($mirrorRoots | ForEach-Object { $_.id + '=`' + $_.path + '`' }) -join '; '
    $lines.Add(("- Mirror roots: {0}" -f $rootText)) | Out-Null
}
if ($CompareInstalled -and -not [string]::IsNullOrWhiteSpace($InstalledPluginsPath)) {
    $lines.Add(('- Installed plugins: `' + $InstalledPluginsPath + '`')) | Out-Null
}

if ($corpusManifest) {
    $lines.Add('') | Out-Null
    $lines.Add('## Upstream Corpus Summary') | Out-Null
    $lines.Add('') | Out-Null
    $lines.Add(("- Tracked entries: {0}" -f [int]$corpusManifest.summary.total_entries)) | Out-Null
    if ($corpusManifest.summary.lane_counts) {
        foreach ($property in @($corpusManifest.summary.lane_counts.PSObject.Properties) | Sort-Object Name) {
            $lines.Add(('- Lane ' + $property.Name + ': ' + $property.Value)) | Out-Null
        }
    }
    if ($corpusManifest.summary.status_counts) {
        foreach ($property in @($corpusManifest.summary.status_counts.PSObject.Properties) | Sort-Object Name) {
            $lines.Add(('- Status ' + $property.Name + ': ' + $property.Value)) | Out-Null
        }
    }
}

$lines.Add('') | Out-Null
$lines.Add('## GitHub Repos') | Out-Null
$lines.Add('') | Out-Null
$lines.Add('| Slug | Repo | Lane | Status | Owner | Branch | Head | Expected | Mirror State | Latest Release | Sources | Next Action |') | Out-Null
$lines.Add('|---|---|---|---|---|---|---|---|---|---|---|---|') | Out-Null
foreach ($row in $rows) {
    $lines.Add(("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} | {10} | {11} |" -f
        ($row.slug -replace '\|', '\\|'),
        ($row.repo_url -replace '\|', '\\|'),
        ($row.lane -replace '\|', '\\|'),
        ($row.status -replace '\|', '\\|'),
        ($row.owner -replace '\|', '\\|'),
        ($row.default_branch -replace '\|', '\\|'),
        ((Get-ShortSha -Sha $row.head_sha) -replace '\|', '\\|'),
        ((Get-ShortSha -Sha $row.observed_head_sha) -replace '\|', '\\|'),
        (($row.mirror_state -replace '\|', '\\|') -replace "`n", ' '),
        ($row.latest_release -replace '\|', '\\|'),
        ($row.sources -replace '\|', '\\|'),
        (($row.next_action -replace '\|', '\\|') -replace "`n", ' ')
    )) | Out-Null
}

if ($npmRows.Count -gt 0) {
    $lines.Add('') | Out-Null
    $lines.Add('## npm Packages') | Out-Null
    $lines.Add('') | Out-Null
    $lines.Add('| Package | Latest | Modified |') | Out-Null
    $lines.Add('|---|---|---|') | Out-Null
    foreach ($package in $npmRows) {
        $lines.Add(("| {0} | {1} | {2} |" -f
            ($package.package -replace '\|', '\\|'),
            ($package.latest -replace '\|', '\\|'),
            ($package.modified -replace '\|', '\\|')
        )) | Out-Null
    }
}

if ($errors.Count -gt 0) {
    $lines.Add('') | Out-Null
    $lines.Add('## Errors') | Out-Null
    $lines.Add('') | Out-Null
    foreach ($errorText in $errors) {
        $lines.Add(("- {0}" -f $errorText)) | Out-Null
    }
}

Write-TextFile -Path $reportPath -Content ($lines -join "`n")
$corpusManifestPathResolved = ''
if (Test-Path -LiteralPath $CorpusManifestPath) {
    $corpusManifestPathResolved = [System.IO.Path]::GetFullPath($CorpusManifestPath)
}
if ($WriteJson) {
    $mirrorRootsArtifact = foreach ($root in $mirrorRoots) {
        [ordered]@{
            id = $root.id
            path = $root.path
            required_for_freshness_gate = $root.required_for_freshness_gate
        }
    }
    $artifact = [ordered]@{
        generated_at = [DateTime]::UtcNow.ToString('o')
        repo_root = $repoRoot
        corpus_manifest_path = $corpusManifestPathResolved
        mirror_roots = @($mirrorRootsArtifact)
        corpus_summary = $corpusSummary
        rows = [object[]]$rows.ToArray()
        npm_packages = [object[]]$npmRows.ToArray()
        errors = [string[]]$errors.ToArray()
    }
    $artifact | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
}

Write-Host 'Upstream audit report written:' -ForegroundColor Green
Write-Host $reportPath
if ($WriteJson) {
    Write-Host 'Upstream audit json written:' -ForegroundColor Green
    Write-Host $jsonPath
}
