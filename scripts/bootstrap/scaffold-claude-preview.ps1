param(
    [Parameter(Mandatory)] [string]$RepoRoot,
    [Parameter(Mandatory)] [string]$TargetRoot,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')

function Copy-DirContent {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Source)) { return }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

[pscustomobject]@{
    result = 'PASS'
    host_id = 'claude-code'
    target_root = [System.IO.Path]::GetFullPath($TargetRoot)
    preview_settings_path = $null
    message = 'Claude preview scaffold no longer installs managed hooks or preview settings; use the supported settings-only installer path instead.'
} | ConvertTo-Json -Depth 10
