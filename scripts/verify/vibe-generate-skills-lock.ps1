param(
    [string]$SkillsRoot = "",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-BytesHash {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $stream = [System.IO.MemoryStream]::new($Bytes)
    try {
        return (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash.ToLower()
    } finally {
        $stream.Dispose()
    }
}

function Test-TextLikeFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )

    $textExt = @(
        ".md", ".txt", ".json", ".ps1", ".psm1", ".sh",
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xml",
        ".csv", ".tsv", ".js", ".ts", ".jsx", ".tsx",
        ".py", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".css", ".html", ".htm", ".sql"
    )

    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($textExt -contains $ext) {
        return $true
    }

    return -not ($Bytes -contains 0)
}

function Get-NormalizedFileHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $rawBytes = [System.IO.File]::ReadAllBytes($Path)
    if (-not (Test-TextLikeFile -Path $Path -Bytes $rawBytes)) {
        return Get-BytesHash -Bytes $rawBytes
    }

    $text = [System.Text.Encoding]::UTF8.GetString($rawBytes)
    $normalized = $text.Replace("`r`n", "`n").Replace("`r", "`n")
    $normalizedBytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    return Get-BytesHash -Bytes $normalizedBytes
}

function Get-SkillDirHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirPath
    )

    $filesByRelative = @{}
    $relativePaths = [System.Collections.Generic.List[string]]::new()
    $entries = New-Object System.Collections.Generic.List[string]
    $totalBytes = 0

    foreach ($file in Get-ChildItem -LiteralPath $DirPath -Force -Recurse -File) {
        $relative = $file.FullName.Substring($DirPath.Length + 1).Replace('\', '/')
        if (
            $relative.Equals("config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase) -or
            $relative.EndsWith("/config/skills-lock.json", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            continue
        }
        $filesByRelative[$relative] = $file
        $relativePaths.Add($relative)
    }

    $relativePaths.Sort([System.StringComparer]::Ordinal)
    foreach ($relative in $relativePaths) {
        $file = $filesByRelative[$relative]
        $hash = Get-NormalizedFileHash -Path $file.FullName
        $entries.Add("$relative`:$hash")
        $totalBytes += $file.Length
    }

    $joined = [string]::Join("`n", $entries)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
    $dirHash = Get-BytesHash -Bytes $bytes

    return [pscustomobject]@{
        dir_hash   = $dirHash
        file_count = $relativePaths.Count
        bytes      = $totalBytes
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if ([string]::IsNullOrWhiteSpace($SkillsRoot)) {
    $SkillsRoot = Join-Path $repoRoot "bundled\skills"
}
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "config\skills-lock.json"
}

if (-not (Test-Path -LiteralPath $SkillsRoot)) {
    throw "Skills root not found: $SkillsRoot"
}

$skills = @()
$dirs = Get-ChildItem -LiteralPath $SkillsRoot -Force -Directory | Sort-Object Name
foreach ($dir in $dirs) {
    $info = Get-SkillDirHash -DirPath $dir.FullName
    $skillMdPath = Join-Path $dir.FullName "SKILL.md"
    $skillMdHash = $null
    if (Test-Path -LiteralPath $skillMdPath) {
        $skillMdHash = Get-NormalizedFileHash -Path $skillMdPath
    }

    $skills += [pscustomobject]@{
        name          = $dir.Name
        relative_path = ("bundled/skills/" + $dir.Name)
        file_count    = $info.file_count
        bytes         = $info.bytes
        skill_md_hash = $skillMdHash
        dir_hash      = $info.dir_hash
    }
}

$totalBytes = ($skills | Measure-Object -Property bytes -Sum).Sum
$payload = [ordered]@{
    version      = 1
    generated_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssK")
    source       = "bundled/skills"
    skill_count  = $skills.Count
    total_bytes  = $totalBytes
    skills       = $skills
}

$json = $payload | ConvertTo-Json -Depth 6
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("skills-lock generated: {0}" -f $OutputPath)
Write-Host ("skills={0}, bytes={1}" -f $skills.Count, $totalBytes)
