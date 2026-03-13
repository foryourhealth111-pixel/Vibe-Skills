param(
  [Parameter(Mandatory = $true)]
  [string]$Task,

  [ValidateSet('think', 'do', 'review', 'team', 'retro', 'any')]
  [string]$Stage = 'any',

  [int]$TopK = 0,

  [string]$Select = '',

  [switch]$AsJson
)

$ErrorActionPreference = 'Stop'

function Get-VcoRoot {
  $root = Resolve-Path (Join-Path $PSScriptRoot '..\..') | Select-Object -ExpandProperty Path
  return $root
}

function Normalize-Text([string]$text) {
  if ($null -eq $text) { return '' }
  return $text.ToLowerInvariant()
}

function Test-KeywordHit([string]$normalizedText, [string]$keyword) {
  if ([string]::IsNullOrWhiteSpace($keyword)) { return $false }

  $kw = Normalize-Text $keyword

  $isShortToken = $kw -match '^[a-z0-9]{1,3}$'
  if (-not $isShortToken) {
    return $normalizedText.Contains($kw)
  }

  $pattern = "(?<![a-z0-9])$([regex]::Escape($kw))(?![a-z0-9])"
  return [regex]::IsMatch($normalizedText, $pattern)
}

function Read-JsonFile([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) {
    throw "JSON file not found: $path"
  }
  $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
  return $raw | ConvertFrom-Json
}

function Resolve-OverlayPath([string]$vcoRoot, [string]$overlayPath) {
  if ([string]::IsNullOrWhiteSpace($overlayPath)) { return '' }
  $full = Join-Path $vcoRoot $overlayPath
  return (Resolve-Path -LiteralPath $full | Select-Object -ExpandProperty Path)
}

function Format-MatchSummary([string[]]$hits) {
  if ($null -eq $hits -or $hits.Count -eq 0) { return 'hits: (none)' }
  $top = $hits | Select-Object -First 6
  if ($hits.Count -le 6) { return ('hits: ' + ($top -join ', ')) }
  return ('hits: ' + ($top -join ', ') + " ... +$($hits.Count - $top.Count)")
}

$vcoRoot = Get-VcoRoot
$configPath = Join-Path $vcoRoot 'config\gitnexus-overlays.json'
$config = Read-JsonFile $configPath

$maxSelect = 1
if ($null -ne $config.max_select -and [int]$config.max_select -gt 0) {
  $maxSelect = [int]$config.max_select
}

$resolvedTopK = $TopK
if ($resolvedTopK -le 0) {
  $resolvedTopK = [int]$config.top_k
}
if ($resolvedTopK -le 0) { $resolvedTopK = 3 }

$normalizedText = Normalize-Text $Task
$overlayRows = @()

foreach ($overlay in $config.overlays) {
  $hits = @()
  foreach ($kw in $overlay.keywords) {
    if (Test-KeywordHit -normalizedText $normalizedText -keyword ([string]$kw)) {
      $hits += [string]$kw
    }
  }

  $score = [double]$hits.Count

  if ($Stage -ne 'any' -and $null -ne $overlay.preferred_stages) {
    $preferred = @($overlay.preferred_stages | ForEach-Object { Normalize-Text ([string]$_) })
    if ($preferred -contains (Normalize-Text $Stage)) {
      $score += 0.25
    }
  }

  $overlayRows += [pscustomobject]@{
    Id = [string]$overlay.id
    Name = [string]$overlay.name
    Description = [string]$overlay.description
    OverlayPath = [string]$overlay.overlay_path
    PreferredStages = @($overlay.preferred_stages)
    Score = $score
    Hits = $hits
  }
}

$hasSignal = ($overlayRows | Measure-Object -Property Score -Maximum).Maximum -gt 0

if (-not $hasSignal) {
  $fallbackIds = @()
  if ($null -ne $config.stage_fallbacks) {
    $fallbackIds = @($config.stage_fallbacks.$Stage)
    if ($fallbackIds.Count -eq 0) { $fallbackIds = @($config.stage_fallbacks.any) }
  }

  $fallbackSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($id in $fallbackIds) { [void]$fallbackSet.Add([string]$id) }

  $overlayRows = $overlayRows | Sort-Object -Property @{ Expression = { $fallbackSet.Contains($_.Id) }; Descending = $true }, @{ Expression = { $_.Score }; Descending = $true }
} else {
  $overlayRows = $overlayRows | Sort-Object -Property @{ Expression = { $_.Score }; Descending = $true }, @{ Expression = { $_.Name }; Descending = $false }
}

$recommended = @($overlayRows | Select-Object -First $resolvedTopK)

$menuLines = New-Object System.Collections.Generic.List[string]
$menuLines.Add("Results: recommend $($recommended.Count) overlay(s) (advice-only), stage=$Stage.")
$menuLines.Add("Options (select up to $maxSelect):")

for ($i = 0; $i -lt $recommended.Count; $i++) {
  $row = $recommended[$i]
  $scoreText = "score=$([math]::Round($row.Score, 2))"
  $hitText = Format-MatchSummary $row.Hits
  $menuLines.Add(("{0}. {1} - {2} ({3}; {4})" -f ($i + 1), $row.Name, $row.Description, $scoreText, $hitText))
}

$menuLines.Add("")
$menuLines.Add("Usage:")
$menuLines.Add(("- Suggestions only: powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Task `"<text>`" -Stage {1}" -f $MyInvocation.MyCommand.Path, $Stage))
$menuLines.Add(("- Render injection:  powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Task `"<text>`" -Stage {1} -Select `"1`"" -f $MyInvocation.MyCommand.Path, $Stage))
$menuLines.Add(("- Or select by id:   -Select `"gitnexus-foundation`""))

$confirmUi = @{
  rendered_text = ($menuLines -join "`n")
  max_select = $maxSelect
  top_k = $resolvedTopK
}

function Find-OverlayById([object]$configObj, [string]$overlayId) {
  foreach ($o in $configObj.overlays) {
    if ([string]$o.id -ieq $overlayId) { return $o }
  }
  return $null
}

function Find-OverlayByNumber([object[]]$recommendedRows, [int]$n) {
  if ($n -lt 1 -or $n -gt $recommendedRows.Count) { return $null }
  return $recommendedRows[$n - 1]
}

function Render-OverlayInjection([string]$vcoRootPath, [object[]]$selectedOverlays) {
  $parts = New-Object System.Collections.Generic.List[string]
  $parts.Add("--- BEGIN VCO PROMPT OVERLAY (advice-only) ---")

  foreach ($sel in $selectedOverlays) {
    $overlayFile = Resolve-OverlayPath -vcoRoot $vcoRootPath -overlayPath ([string]$sel.overlay_path)
    $body = Get-Content -LiteralPath $overlayFile -Raw -Encoding UTF8
    $parts.Add("")
    $parts.Add(("# Overlay: {0}" -f [string]$sel.name))
    $parts.Add($body.Trim())
  }

  $parts.Add("")
  $parts.Add("--- END VCO PROMPT OVERLAY ---")
  return ($parts -join "`n")
}

$selectedOverlayObjs = @()
if (-not [string]::IsNullOrWhiteSpace($Select)) {
  $tokens = $Select -split '[,\s]+' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

  $selectedIds = [System.Collections.Generic.List[string]]::new()

  foreach ($t in $tokens) {
    $token = $t.Trim()

    if ($token -match '^\d+$') {
      $asNumber = [int]$token
      $row = Find-OverlayByNumber -recommendedRows $recommended -n $asNumber
      if ($null -eq $row) { throw "Invalid selection number: $token" }
      $selectedIds.Add([string]$row.Id)
      continue
    }

    $overlayObj = Find-OverlayById -configObj $config -overlayId $token
    if ($null -eq $overlayObj) { throw "Unknown overlay id: $token" }
    $selectedIds.Add([string]$overlayObj.id)
  }

  $dedup = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($id in $selectedIds) { [void]$dedup.Add($id) }

  $finalIds = @($dedup)
  if ($finalIds.Count -gt $maxSelect) {
    throw "Too many overlays selected ($($finalIds.Count)); max_select=$maxSelect"
  }

  foreach ($id in $finalIds) {
    $obj = Find-OverlayById -configObj $config -overlayId $id
    if ($null -eq $obj) { throw "Overlay config not found: $id" }
    $selectedOverlayObjs += $obj
  }
}

$result = @{
  version = 1
  task = $Task
  stage = $Stage
  top_k = $resolvedTopK
  recommendations = @(
    $recommended | ForEach-Object {
      @{
        id = $_.Id
        name = $_.Name
        description = $_.Description
        score = [math]::Round($_.Score, 2)
        hits = $_.Hits
        overlay_path = $_.OverlayPath
      }
    }
  )
  confirm_ui = $confirmUi
}

if ($selectedOverlayObjs.Count -gt 0) {
  $result.selected = @($selectedOverlayObjs | ForEach-Object { @{ id = $_.id; name = $_.name; overlay_path = $_.overlay_path } })
  $result.overlay_injection = Render-OverlayInjection -vcoRootPath $vcoRoot -selectedOverlays $selectedOverlayObjs
}

if ($AsJson) {
  $result | ConvertTo-Json -Depth 6
  exit 0
}

Write-Output $confirmUi.rendered_text

if ($selectedOverlayObjs.Count -gt 0) {
  Write-Output ""
  Write-Output $result.overlay_injection
}

