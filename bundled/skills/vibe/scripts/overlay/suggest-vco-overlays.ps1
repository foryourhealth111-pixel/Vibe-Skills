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
$catalogPath = Join-Path $vcoRoot 'config\vco-overlays.json'
$catalog = Read-JsonFile $catalogPath

$maxSelect = 2
if ($null -ne $catalog.max_select -and [int]$catalog.max_select -gt 0) {
  $maxSelect = [int]$catalog.max_select
}

$resolvedTopK = $TopK
if ($resolvedTopK -le 0) {
  $resolvedTopK = [int]$catalog.top_k
}
if ($resolvedTopK -le 0) { $resolvedTopK = 4 }

$providers = @()
foreach ($p in $catalog.providers) {
  $providerId = [string]$p.id
  $providerName = [string]$p.name
  $priorityBoost = 0.0
  if ($null -ne $p.priority_boost) { $priorityBoost = [double]$p.priority_boost }

  $providerConfigFile = Join-Path $vcoRoot ([string]$p.config_path)
  $providerConfig = Read-JsonFile $providerConfigFile

  $providers += [pscustomobject]@{
    Id = $providerId
    Name = $providerName
    PriorityBoost = $priorityBoost
    Config = $providerConfig
  }
}

$overlayById = [System.Collections.Generic.Dictionary[string, object]]::new([StringComparer]::OrdinalIgnoreCase)
$overlayRows = @()
$normalizedText = Normalize-Text $Task

foreach ($provider in $providers) {
  foreach ($overlay in $provider.Config.overlays) {
    $overlayId = [string]$overlay.id
    if ($overlayById.ContainsKey($overlayId)) {
      throw "Duplicate overlay id across providers: $overlayId"
    }

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

    $score += [double]$provider.PriorityBoost

    $overlayById[$overlayId] = @{
      provider_id = $provider.Id
      provider_name = $provider.Name
      overlay = $overlay
    }

    $overlayRows += [pscustomobject]@{
      ProviderId = $provider.Id
      ProviderName = $provider.Name
      Id = $overlayId
      Name = [string]$overlay.name
      Description = [string]$overlay.description
      OverlayPath = [string]$overlay.overlay_path
      Score = $score
      HitCount = [int]$hits.Count
      Hits = $hits
    }
  }
}

$hasSignal = ($overlayRows | Where-Object { $_.HitCount -gt 0 } | Measure-Object).Count -gt 0

if (-not $hasSignal) {
  $fallbackIds = @()
  if ($null -ne $catalog.stage_fallbacks) {
    $fallbackIds = @($catalog.stage_fallbacks.$Stage)
    if ($fallbackIds.Count -eq 0) { $fallbackIds = @($catalog.stage_fallbacks.any) }
  }

  $fallbackSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($id in $fallbackIds) { [void]$fallbackSet.Add([string]$id) }

  $overlayRows = $overlayRows | Sort-Object -Property `
    @{ Expression = { $fallbackSet.Contains($_.Id) }; Descending = $true }, `
    @{ Expression = { $_.Score }; Descending = $true }, `
    @{ Expression = { $_.Name }; Descending = $false }
} else {
  $overlayRows = $overlayRows | Sort-Object -Property `
    @{ Expression = { $_.Score }; Descending = $true }, `
    @{ Expression = { $_.Name }; Descending = $false }
}

$recommended = @($overlayRows | Select-Object -First $resolvedTopK)

$menuLines = New-Object System.Collections.Generic.List[string]
$menuLines.Add("Results: recommend $($recommended.Count) overlay(s) (advice-only), stage=$Stage.")
$menuLines.Add("Options (select up to $maxSelect):")

for ($i = 0; $i -lt $recommended.Count; $i++) {
  $row = $recommended[$i]
  $scoreText = "score=$([math]::Round($row.Score, 2))"
  $hitText = Format-MatchSummary $row.Hits
  $menuLines.Add(("{0}. [{1}] {2} - {3} ({4}; {5})" -f ($i + 1), $row.ProviderId, $row.Name, $row.Description, $scoreText, $hitText))
}

$menuLines.Add("")
$menuLines.Add("Usage:")
$menuLines.Add(("- Suggestions only: powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Task `"<text>`" -Stage {1}" -f $MyInvocation.MyCommand.Path, $Stage))
$menuLines.Add(("- Render injection:  powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Task `"<text>`" -Stage {1} -Select `"1,2`"" -f $MyInvocation.MyCommand.Path, $Stage))
$menuLines.Add(("- Or select by id:   -Select `"gitnexus-foundation,agency-testing`""))

$confirmUi = @{
  rendered_text = ($menuLines -join "`n")
  max_select = $maxSelect
  top_k = $resolvedTopK
}

function Find-OverlayByNumber([object[]]$recommendedRows, [int]$n) {
  if ($n -lt 1 -or $n -gt $recommendedRows.Count) { return $null }
  return $recommendedRows[$n - 1]
}

function Find-OverlayMetaById([System.Collections.Generic.Dictionary[string, object]]$index, [string]$overlayId) {
  if ($index.ContainsKey($overlayId)) { return $index[$overlayId] }
  return $null
}

function Render-OverlayInjection([string]$vcoRootPath, [object[]]$selectedOverlays) {
  $parts = New-Object System.Collections.Generic.List[string]
  $parts.Add("--- BEGIN VCO PROMPT OVERLAY (advice-only) ---")

  foreach ($sel in $selectedOverlays) {
    $overlayFile = Resolve-OverlayPath -vcoRoot $vcoRootPath -overlayPath ([string]$sel.overlay_path)
    $body = Get-Content -LiteralPath $overlayFile -Raw -Encoding UTF8
    $parts.Add("")
    $parts.Add(("# Overlay: [{0}] {1}" -f [string]$sel.provider_id, [string]$sel.name))
    $parts.Add($body.Trim())
  }

  $parts.Add("")
  $parts.Add("--- END VCO PROMPT OVERLAY ---")
  return ($parts -join "`n")
}

$selectedOverlayRows = @()
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

    $meta = Find-OverlayMetaById -index $overlayById -overlayId $token
    if ($null -eq $meta) { throw "Unknown overlay id: $token" }
    $selectedIds.Add([string]$token)
  }

  $dedup = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($id in $selectedIds) { [void]$dedup.Add($id) }

  $finalIds = @($dedup)
  if ($finalIds.Count -gt $maxSelect) {
    throw "Too many overlays selected ($($finalIds.Count)); max_select=$maxSelect"
  }

  foreach ($id in $finalIds) {
    $meta = Find-OverlayMetaById -index $overlayById -overlayId $id
    if ($null -eq $meta) { throw "Overlay config not found: $id" }

    $o = $meta.overlay
    $selectedOverlayRows += [pscustomobject]@{
      id = [string]$o.id
      name = [string]$o.name
      overlay_path = [string]$o.overlay_path
      provider_id = [string]$meta.provider_id
      provider_name = [string]$meta.provider_name
    }
  }
}

$result = @{
  version = 1
  task = $Task
  stage = $Stage
  top_k = $resolvedTopK
  providers = @($providers | ForEach-Object { @{ id = $_.Id; name = $_.Name } })
  recommendations = @(
    $recommended | ForEach-Object {
      @{
        id = $_.Id
        name = $_.Name
        provider_id = $_.ProviderId
        description = $_.Description
        score = [math]::Round($_.Score, 2)
        hits = $_.Hits
        overlay_path = $_.OverlayPath
      }
    }
  )
  confirm_ui = $confirmUi
}

if ($selectedOverlayRows.Count -gt 0) {
  $result.selected = @($selectedOverlayRows | ForEach-Object { @{ id = $_.id; name = $_.name; provider_id = $_.provider_id; overlay_path = $_.overlay_path } })
  $result.overlay_injection = Render-OverlayInjection -vcoRootPath $vcoRoot -selectedOverlays $selectedOverlayRows
}

if ($AsJson) {
  $result | ConvertTo-Json -Depth 7
  exit 0
}

Write-Output $confirmUi.rendered_text

if ($selectedOverlayRows.Count -gt 0) {
  Write-Output ""
  Write-Output $result.overlay_injection
}

