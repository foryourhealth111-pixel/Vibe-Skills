param(
  [string]$RepoRoot = "",
  [switch]$StagedOnly,
  [int]$MaxFindings = 50
)

$ErrorActionPreference = "Stop"

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host $Title -ForegroundColor Cyan
}

function Resolve-RepoRoot {
  param([string]$Explicit)
  if ($Explicit) { return (Resolve-Path -LiteralPath $Explicit).Path }
  # scripts/verify -> repo root
  return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\\..")).Path
}

function Get-RedactedLine {
  param([string]$Line)
  if (-not $Line) { return $Line }
  $redacted = $Line
  # Redact OpenAI-style keys: sk- + 20+ alnum with at least one digit
  $redacted = [regex]::Replace($redacted, "(?i)sk-(?=[a-z0-9]*[0-9])[a-z0-9]{20,}", "sk-<REDACTED>")
  # Redact bearer tokens
  $redacted = [regex]::Replace($redacted, "(?i)bearer\\s+[a-z0-9_\\-\\.]{20,}", "Bearer <REDACTED>")
  return $redacted
}

$root = Resolve-RepoRoot -Explicit $RepoRoot

Write-Section "VCO secret scan (pre-push gate)"
Write-Host ("- repo_root: {0}" -f $root)
Write-Host ("- staged_only: {0}" -f ([bool]$StagedOnly))

if (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
  Write-Host "- WARNING: .git not found under repo_root; scanning working tree anyway." -ForegroundColor Yellow
}

$findings = New-Object System.Collections.Generic.List[object]

function Add-Finding {
  param(
    [string]$Kind,
    [string]$Path,
    [int]$Line,
    [string]$Preview
  )
  if ($findings.Count -ge $MaxFindings) { return }
  $findings.Add([pscustomobject]@{
    kind = $Kind
    path = $Path
    line = $Line
    preview = $Preview
  })
}

function Scan-Text {
  param(
    [string]$Text,
    [string]$VirtualPath
  )

  if (-not $Text) { return }

  $lines = $Text -split "`n"
  for ($i = 0; $i -lt $lines.Length; $i++) {
    $line = $lines[$i]
    if (-not $line) { continue }

    # 1) OpenAI key literal (quoted) - avoid false positives like "Risk-stratified"
    if ($line -match '(?i)["'']sk-(?=[a-z0-9]*[0-9])[a-z0-9]{20,}["'']') {
      Add-Finding -Kind "openai_key_literal" -Path $VirtualPath -Line ($i + 1) -Preview (Get-RedactedLine -Line $line)
      continue
    }

    # 2) Settings-style JSON env assignments (OPENAI_API_KEY / ARK_API_KEY)
    if ($line -match "(?i)\\bOPENAI_API_KEY\\b" -and ($line -notmatch "<REQUIRED>" ) -and ($line -notmatch "\\$\\{OPENAI_API_KEY\\}" ) -and ($line -notmatch "\\$OPENAI_API_KEY" )) {
      # If it's not a placeholder, flag it.
      Add-Finding -Kind "openai_api_key_assignment" -Path $VirtualPath -Line ($i + 1) -Preview (Get-RedactedLine -Line $line)
      continue
    }
    if ($line -match "(?i)\\bARK_API_KEY\\b" -and ($line -notmatch "<OPTIONAL" ) -and ($line -notmatch "\\$\\{ARK_API_KEY\\}" ) -and ($line -notmatch "\\$ARK_API_KEY" )) {
      Add-Finding -Kind "ark_api_key_assignment" -Path $VirtualPath -Line ($i + 1) -Preview (Get-RedactedLine -Line $line)
      continue
    }
  }
}

if ($StagedOnly) {
  Write-Section "Scan staged diff (added lines only)"
  $diff = ""
  try {
    $diff = (git -C $root diff --cached -U0)
  } catch {
    Write-Host "- Failed to read staged diff; falling back to full scan." -ForegroundColor Yellow
  }

  if ($diff) {
    $added = @()
    foreach ($l in ($diff -split "`n")) {
      if (-not $l) { continue }
      if ($l.StartsWith("+++") -or $l.StartsWith("---")) { continue }
      if ($l.StartsWith("+")) { $added += $l.Substring(1) }
    }
    Scan-Text -Text ($added -join "`n") -VirtualPath "<git:staged>"
  }
}

Write-Section "Scan working tree (targeted file types)"
$paths = Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FullName -notmatch "\\\\node_modules\\\\" -and
    $_.FullName -notmatch "\\\\outputs\\\\" -and
    $_.FullName -notmatch "\\\\telemetry\\\\" -and
    $_.Extension -in @(".json", ".yml", ".yaml", ".ps1", ".md", ".txt", ".toml", ".ini", ".env")
  } |
  Select-Object -ExpandProperty FullName

foreach ($p in $paths) {
  if ($findings.Count -ge $MaxFindings) { break }
  try {
    $content = Get-Content -LiteralPath $p -Raw -Encoding UTF8
  } catch {
    continue
  }
  Scan-Text -Text $content -VirtualPath $p
}

Write-Section "Result"
if ($findings.Count -eq 0) {
  Write-Host "- OK: no obvious secrets found." -ForegroundColor Green
  exit 0
}

Write-Host ("- FAIL: found {0} potential secret(s)." -f $findings.Count) -ForegroundColor Red
foreach ($f in $findings) {
  Write-Host ("  - [{0}] {1}:{2}" -f $f.kind, $f.path, $f.line) -ForegroundColor Yellow
  if ($f.preview) {
    Write-Host ("    {0}" -f $f.preview) -ForegroundColor DarkGray
  }
}

Write-Host ""
Write-Host "Fix: remove secrets from tracked files, then re-run this gate before pushing." -ForegroundColor Cyan
exit 2
