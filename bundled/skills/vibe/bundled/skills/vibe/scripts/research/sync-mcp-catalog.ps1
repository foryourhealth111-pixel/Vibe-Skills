param(
    [string]$SourceRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'third_party\vco-ecosystem-mirror\awesome-mcp-servers'),
    [string]$OutputPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'references\awesome-mcp-servers.snapshot.json')
)

$ErrorActionPreference = "Stop"

function Get-LanguageTag {
    param([string]$Name)

    if ($Name -ieq 'README.md') { return 'en' }
    if ($Name -match '^README-(.+)\.md$') { return $Matches[1] }
    return 'unknown'
}

function Get-GitHubRepoFromUrl {
    param([string]$Url)

    try {
        $uri = [System.Uri]$Url
        if ($uri.Host -notmatch 'github\.com$') { return $null }
        $segments = @($uri.AbsolutePath.Trim('/').Split('/'))
        if ($segments.Count -lt 2) { return $null }
        return ('{0}/{1}' -f $segments[0], $segments[1])
    } catch {
        return $null
    }
}

$sourceRootResolved = Resolve-Path $SourceRoot
$readmes = @(Get-ChildItem -LiteralPath $sourceRootResolved -File -Filter 'README*.md' | Sort-Object Name)
if ($readmes.Count -eq 0) {
    throw "No README*.md files found under $sourceRootResolved"
}

$entries = New-Object System.Collections.Generic.List[object]
$sourceFiles = @()

foreach ($readme in $readmes) {
    $sourceFiles += [string]$readme.FullName
    $headings = @()
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $readme.FullName -Encoding UTF8) {
        $lineNumber += 1

        if ($line -match '^(#{1,6})\s+(.+?)\s*$') {
            $level = $Matches[1].Length
            $title = $Matches[2].Trim()
            if ($headings.Count -ge $level) {
                $headings = @($headings[0..($level - 2)])
            }
            $headings += $title
            continue
        }

        if ($line -match '^\s*[-*+]\s+.*?\[(?<label>[^\]]+)\]\((?<url>https?://[^)\s]+)\)') {
            $url = $Matches['url']
            $label = $Matches['label'].Trim()
            try {
                $urlHost = ([System.Uri]$url).Host
            } catch {
                $urlHost = $null
            }

            $entries.Add([ordered]@{
                readme = [string]$readme.Name
                language = Get-LanguageTag -Name $readme.Name
                line = $lineNumber
                section = $(if ($headings.Count -gt 0) { $headings[-1] } else { $null })
                section_path = $(if ($headings.Count -gt 0) { $headings -join ' > ' } else { $null })
                label = $label
                url = $url
                host = $urlHost
                github_repo = Get-GitHubRepoFromUrl -Url $url
            }) | Out-Null
        }
    }
}

$outputObject = [pscustomobject]@{
    generated_at = [DateTime]::UtcNow.ToString('o')
    source_root = [string]$sourceRootResolved
    source_files = [string[]]@($sourceFiles)
    readme_count = $readmes.Count
    entry_count = $entries.Count
    generation_policy = 'snapshot-only; does not mutate config/tool-registry.json'
    sample_entries = [object[]]($entries | Select-Object -First 5)
    entries = [object[]]$entries.ToArray()
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
$outputObject | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

Write-Host '=== MCP Catalog Sync ===' -ForegroundColor Cyan
Write-Host ("Source root : {0}" -f $sourceRootResolved)
Write-Host ("README count: {0}" -f $readmes.Count)
Write-Host ("Entry count : {0}" -f $entries.Count)
Write-Host ("Output      : {0}" -f $OutputPath)


