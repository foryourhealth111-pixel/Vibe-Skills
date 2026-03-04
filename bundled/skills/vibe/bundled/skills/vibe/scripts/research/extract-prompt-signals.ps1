param(
    [string]$SourceRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "third_party\system-prompts-mirror"),
    [string]$OutputPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\external-corpus\prompt-signals.json"),
    [int]$TopTermsPerFile = 15
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-StopWords {
    return [System.Collections.Generic.HashSet[string]]::new([string[]]@(
        "the", "and", "for", "with", "that", "this", "from", "are", "you", "your", "not", "use", "tool",
        "tools", "json", "txt", "yaml", "yml", "file", "files", "path", "paths", "code", "user", "users",
        "into", "when", "what", "where", "which", "have", "has", "had", "was", "were", "can", "could",
        "should", "would", "will", "must", "may", "their", "they", "them", "then", "than", "only", "also",
        "each", "more", "most", "just", "like", "using", "used", "been", "over", "under", "into", "about",
        "here", "there", "very", "much", "many", "some", "such", "same", "mode", "prompt", "prompts"
    ))
}

function Get-StrategySignals {
    param([string]$TextLower)

    return [pscustomobject]@{
        planning = [bool]($TextLower -match "\b(plan|planning|roadmap|milestone|spec|design)\b")
        execution = [bool]($TextLower -match "\b(implement|execute|run|apply|patch)\b")
        verification = [bool]($TextLower -match "\b(verify|validation|quality gate|assert|check)\b")
        testing = [bool]($TextLower -match "\b(test|unit test|integration test|red green refactor|tdd)\b")
        security = [bool]($TextLower -match "\b(security|vulnerability|safety|owasp|threat)\b")
        fallback = [bool]($TextLower -match "\b(fallback|degraded|retry|graceful)\b")
        routing = [bool]($TextLower -match "\b(route|routing|router|classify|classification|intent)\b")
        multi_agent = [bool]($TextLower -match "\b(subagent|multi-agent|swarm|team orchestration|spawn_agent)\b")
        mcp = [bool]($TextLower -match "\b(mcp|model context protocol|tool schema|input_schema)\b")
    }
}

function Get-TermFrequency {
    param(
        [string]$TextLower,
        [System.Collections.Generic.HashSet[string]]$StopWords
    )

    $result = @{}
    $matches = [Regex]::Matches($TextLower, "[a-z][a-z0-9_/\-]{2,}")
    foreach ($match in $matches) {
        $token = $match.Value
        if ($StopWords.Contains($token)) { continue }
        if (-not $result.ContainsKey($token)) {
            $result[$token] = 0
        }
        $result[$token]++
    }
    return $result
}

function Merge-Frequency {
    param(
        [hashtable]$Target,
        [hashtable]$Incoming
    )

    foreach ($entry in $Incoming.GetEnumerator()) {
        if (-not $Target.ContainsKey($entry.Key)) {
            $Target[$entry.Key] = 0
        }
        $Target[$entry.Key] += [int]$entry.Value
    }
}

function Get-TopTerms {
    param(
        [hashtable]$Frequency,
        [int]$Limit = 15
    )

    return @(
        $Frequency.GetEnumerator() |
        Sort-Object -Property @{ Expression = "Value"; Descending = $true }, @{ Expression = "Key"; Descending = $false } |
        Select-Object -First $Limit |
        ForEach-Object {
            [pscustomobject]@{
                term = [string]$_.Key
                count = [int]$_.Value
            }
        }
    )
}

function Get-RelativePathCompat {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseResolved = (Resolve-Path -LiteralPath $BasePath).Path
    $targetResolved = (Resolve-Path -LiteralPath $TargetPath).Path
    if (-not $baseResolved.EndsWith("\")) {
        $baseResolved += "\"
    }

    $baseUri = New-Object System.Uri($baseResolved)
    $targetUri = New-Object System.Uri($targetResolved)
    $relative = [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString())
    return $relative.Replace("\", "/")
}

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "SourceRoot not found: $SourceRoot"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$stopWords = Get-StopWords
$globalFrequency = @{}
$fileRecords = New-Object System.Collections.Generic.List[object]
$signalCounts = @{
    planning = 0
    execution = 0
    verification = 0
    testing = 0
    security = 0
    fallback = 0
    routing = 0
    multi_agent = 0
    mcp = 0
}

$sourceExtensions = @(".txt", ".json", ".yaml", ".yml", ".md")
$files = Get-ChildItem -Path $SourceRoot -Recurse -File | Where-Object { $sourceExtensions -contains $_.Extension.ToLowerInvariant() }

foreach ($file in $files) {
    $raw = ""
    try {
        $raw = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    } catch {
        Write-Warning "Skipping unreadable file: $($file.FullName)"
        continue
    }

    if ([string]::IsNullOrWhiteSpace($raw)) { continue }

    $relativePath = Get-RelativePathCompat -BasePath $SourceRoot -TargetPath $file.FullName
    $segments = $relativePath.Split("/")
    $vendor = if ($segments.Count -gt 0) { $segments[0] } else { "unknown" }
    $textLower = $raw.ToLowerInvariant()

    $localFrequency = Get-TermFrequency -TextLower $textLower -StopWords $stopWords
    Merge-Frequency -Target $globalFrequency -Incoming $localFrequency
    $topTerms = Get-TopTerms -Frequency $localFrequency -Limit $TopTermsPerFile
    $signals = Get-StrategySignals -TextLower $textLower

    foreach ($name in @("planning", "execution", "verification", "testing", "security", "fallback", "routing", "multi_agent", "mcp")) {
        if ($signals.$name) {
            $signalCounts[$name]++
        }
    }

    $fileRecords.Add([pscustomobject]@{
        vendor = $vendor
        relative_path = $relativePath
        extension = $file.Extension.ToLowerInvariant()
        size_bytes = [int64]$file.Length
        strategy_signals = $signals
        top_terms = $topTerms
    })
}

$vendorStats = @(
    $fileRecords |
    Group-Object -Property vendor |
    Sort-Object -Property Count -Descending |
    ForEach-Object {
        [pscustomobject]@{
            vendor = [string]$_.Name
            file_count = [int]$_.Count
        }
    }
)

$result = [pscustomobject]@{
    version = 1
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    source_root = $SourceRoot
    file_count = [int]$fileRecords.Count
    vendor_count = [int]$vendorStats.Count
    signal_counts = [pscustomobject]$signalCounts
    vendors = $vendorStats
    token_frequency = (Get-TopTerms -Frequency $globalFrequency -Limit 400)
    files = $fileRecords
}

$result | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

Write-Host "Extracted signals from $($result.file_count) files."
Write-Host "Output: $OutputPath"
