param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [ValidateSet("codex", "claude-code", "cursor", "windsurf", "openclaw", "opencode")]
  [string]$HostId = "codex",
  [string]$TargetRoot = '',
  [switch]$InstallExternal,
  [switch]$StrictOffline,
  [switch]$RequireClosedReady,
  [switch]$AllowExternalSkillFallback,
  [switch]$SkipRuntimeFreshnessGate
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')
. (Join-Path $RepoRoot 'scripts\common\Resolve-VgoAdapter.ps1')
$HostId = Resolve-VgoHostId -HostId $HostId
$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId
$Adapter = Resolve-VgoAdapterDescriptor -RepoRoot $RepoRoot -HostId $HostId

function Test-CanonicalRepoExecution {
  param([string]$RepoRoot)
  return (Test-VgoCanonicalRepoExecution -StartPath $RepoRoot)
}
function Get-PreferredPythonCommand {
  foreach ($candidate in @('python', 'python3', 'py')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
      return $candidate
    }
  }
  return $null
}
function Get-InstallGovernance {
  param([string]$RepoRoot)
  $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
  if (-not (Test-Path -LiteralPath $governancePath)) {
    throw "version-governance config not found: $governancePath"
  }
  try {
    return Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    throw ("Failed to parse version-governance.json: " + $_.Exception.Message)
  }
}
function Get-InstalledRuntimeConfig {
  param([psobject]$Governance)
  $defaults = [ordered]@{
    target_relpath = 'skills/vibe'
    receipt_relpath = 'skills/vibe/outputs/runtime-freshness-receipt.json'
    post_install_gate = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
    frontmatter_gate = 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
  }
  $runtimeConfig = $null
  if ($null -ne $Governance -and $Governance.PSObject.Properties.Name -contains 'runtime' -and $null -ne $Governance.runtime) {
    if ($Governance.runtime.PSObject.Properties.Name -contains 'installed_runtime') {
      $runtimeConfig = $Governance.runtime.installed_runtime
    }
  }
  if ($null -eq $runtimeConfig) {
    return [pscustomobject]$defaults
  }
  $merged = [ordered]@{}
  foreach ($key in $defaults.Keys) {
    if ($runtimeConfig.PSObject.Properties.Name -contains $key -and $null -ne $runtimeConfig.$key -and -not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.$key)) {
      $merged[$key] = $runtimeConfig.$key
    } else {
      $merged[$key] = $defaults[$key]
    }
  }
  return [pscustomobject]$merged
}
function Invoke-InstalledRuntimeFreshnessGate {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot,
    [switch]$SkipGate
  )
  if ($SkipGate) {
    Write-Warning 'Skipping runtime freshness gate by request.'
    return
  }
  if (-not (Test-CanonicalRepoExecution -RepoRoot $RepoRoot)) {
    Write-Warning 'Runtime freshness gate requires running install.ps1 from the canonical repo root; skipping because no outer .git root was found.'
    return
  }
  $governance = Get-InstallGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $gateRel = [string]$runtimeConfig.post_install_gate
  if ([string]::IsNullOrWhiteSpace($gateRel)) {
    $gateRel = 'scripts\verify\vibe-installed-runtime-freshness-gate.ps1'
  }
  $gatePath = Join-Path $RepoRoot $gateRel
  if (-not (Test-Path -LiteralPath $gatePath)) {
    throw "runtime freshness gate script missing: $gatePath"
  }
  $receiptRel = [string]$runtimeConfig.receipt_relpath
  $global:LASTEXITCODE = 0
  & $gatePath -TargetRoot $TargetRoot -WriteReceipt
  $gateExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
  if ($gateExitCode -ne 0) {
    throw 'Runtime freshness gate failed after install.'
  }
  if (-not [string]::IsNullOrWhiteSpace($receiptRel)) {
    $receiptPath = Join-Path $TargetRoot $receiptRel
    if (-not (Test-Path -LiteralPath $receiptPath)) {
      throw "Runtime freshness receipt missing after install: $receiptPath"
    }
  }

  $frontmatterGateRel = [string]$runtimeConfig.frontmatter_gate
  if (-not [string]::IsNullOrWhiteSpace($frontmatterGateRel)) {
    $frontmatterGatePath = Join-Path $RepoRoot $frontmatterGateRel
    if (-not (Test-Path -LiteralPath $frontmatterGatePath)) {
      throw "frontmatter gate script missing: $frontmatterGatePath"
    }
    $global:LASTEXITCODE = 0
    & $frontmatterGatePath -TargetRoot $TargetRoot
    $frontmatterExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($frontmatterExitCode -ne 0) {
      throw 'Frontmatter BOM gate failed after install.'
    }
  }
}

function Test-VgoPathWithinOrEqual {
  param(
    [string]$ParentPath,
    [string]$ChildPath
  )

  if ([string]::IsNullOrWhiteSpace($ParentPath) -or [string]::IsNullOrWhiteSpace($ChildPath)) {
    return $false
  }

  try {
    $parentFull = [System.IO.Path]::GetFullPath($ParentPath)
    $childFull = [System.IO.Path]::GetFullPath($ChildPath)
  } catch {
    return $false
  }

  if ($parentFull -eq $childFull) {
    return $true
  }

  return (Test-VgoPathWithin -ParentPath $parentFull -ChildPath $childFull)
}

function Get-VgoJsonStringArray {
  param($Value)

  $items = New-Object 'System.Collections.Generic.List[string]'
  foreach ($item in @($Value)) {
    if ($null -eq $item) {
      continue
    }
    $text = ([string]$item).Trim()
    if (-not [string]::IsNullOrWhiteSpace($text)) {
      $items.Add($text)
    }
  }

  return @($items.ToArray())
}

function Get-VgoJsonPropertyValue {
  param(
    [AllowNull()] $Node,
    [string]$Name
  )

  if ($null -eq $Node -or [string]::IsNullOrWhiteSpace($Name)) {
    return $null
  }

  if ($Node -is [System.Collections.IDictionary]) {
    if ($Node.Contains($Name)) {
      return $Node[$Name]
    }
    return $null
  }

  if ($Node.PSObject.Properties.Name -contains $Name) {
    return $Node.$Name
  }

  return $null
}

function Get-InstallLedgerManagedSkillNames {
  param(
    [psobject]$Ledger,
    [string]$TargetRoot
  )

  $managed = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($name in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'managed_skill_names'))) {
    [void]$managed.Add($name)
  }

  $skillsRoot = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'created_paths'))) {
    try {
      $candidatePath = [System.IO.Path]::GetFullPath($rawPath)
    } catch {
      continue
    }
    if (-not (Test-VgoPathWithin -ParentPath $skillsRoot -ChildPath $candidatePath)) {
      continue
    }
    $relativePath = $candidatePath.Substring($skillsRoot.Length).TrimStart('\', '/')
    if ([string]::IsNullOrWhiteSpace($relativePath)) {
      continue
    }
    $skillName = ($relativePath -split '[\\/]', 2)[0]
    if (-not [string]::IsNullOrWhiteSpace($skillName)) {
      [void]$managed.Add($skillName)
    }
  }

  $canonicalVibeRoot = [string](Get-VgoJsonPropertyValue -Node $Ledger -Name 'canonical_vibe_root')
  $canonicalVibeRoot = $canonicalVibeRoot.Trim()
  if (-not [string]::IsNullOrWhiteSpace($canonicalVibeRoot)) {
    [void]$managed.Add([System.IO.Path]::GetFileName($canonicalVibeRoot))
  }

  return @($managed | Sort-Object)
}

function Add-InstallLedgerOwnedFile {
  param(
    [System.Collections.Generic.HashSet[string]]$OwnedFiles,
    [string]$TargetRoot,
    [string]$PathValue
  )

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return
  }

  try {
    $candidatePath = [System.IO.Path]::GetFullPath($PathValue)
  } catch {
    return
  }

  if (-not (Test-VgoPathWithinOrEqual -ParentPath $TargetRoot -ChildPath $candidatePath)) {
    return
  }

  if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
    [void]$OwnedFiles.Add($candidatePath)
  }
}

function Add-InstallLedgerOwnedTreeFiles {
  param(
    [System.Collections.Generic.HashSet[string]]$OwnedFiles,
    [string]$TargetRoot,
    [string]$PathValue
  )

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return
  }

  try {
    $candidatePath = [System.IO.Path]::GetFullPath($PathValue)
  } catch {
    return
  }

  if (-not (Test-VgoPathWithinOrEqual -ParentPath $TargetRoot -ChildPath $candidatePath)) {
    return
  }

  if (-not (Test-Path -LiteralPath $candidatePath -PathType Container)) {
    return
  }

  foreach ($file in @(Get-ChildItem -LiteralPath $candidatePath -Recurse -File -Force -ErrorAction SilentlyContinue)) {
    [void]$OwnedFiles.Add([System.IO.Path]::GetFullPath($file.FullName))
  }
}

function Get-InstallLedgerPayloadSummary {
  param(
    [psobject]$Ledger,
    [string]$TargetRoot
  )

  $targetRootFull = [System.IO.Path]::GetFullPath($TargetRoot)
  $skillsRootFull = [System.IO.Path]::GetFullPath((Join-Path $TargetRoot 'skills'))
  $managedSkillNames = @(Get-InstallLedgerManagedSkillNames -Ledger $Ledger -TargetRoot $TargetRoot)
  $managedSkillSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($name in $managedSkillNames) {
    [void]$managedSkillSet.Add($name)
  }

  $installedSkillNames = New-Object 'System.Collections.Generic.List[string]'
  foreach ($name in $managedSkillNames) {
    if ($name.StartsWith('.')) {
      continue
    }
    $skillRoot = Join-Path $skillsRootFull $name
    if (Test-Path -LiteralPath $skillRoot -PathType Container) {
      $installedSkillNames.Add($name)
    }
  }

  $ownedFiles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

  foreach ($name in $managedSkillNames) {
    $skillRoot = Join-Path $skillsRootFull $name
    if (Test-Path -LiteralPath $skillRoot -PathType Container) {
      Add-InstallLedgerOwnedTreeFiles -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $skillRoot
    }
  }

  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'owned_tree_roots'))) {
    try {
      $candidatePath = [System.IO.Path]::GetFullPath($rawPath)
    } catch {
      continue
    }
    if ($candidatePath -eq $targetRootFull -or $candidatePath -eq $skillsRootFull) {
      continue
    }
    $candidateParent = [System.IO.Path]::GetDirectoryName($candidatePath)
    if ($candidateParent -eq $skillsRootFull -and -not $managedSkillSet.Contains([System.IO.Path]::GetFileName($candidatePath))) {
      continue
    }
    Add-InstallLedgerOwnedTreeFiles -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $candidatePath
  }

  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'created_paths'))) {
    Add-InstallLedgerOwnedFile -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $rawPath
  }
  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'managed_json_paths'))) {
    Add-InstallLedgerOwnedFile -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $rawPath
  }
  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'generated_from_template_if_absent'))) {
    Add-InstallLedgerOwnedFile -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $rawPath
  }
  foreach ($rawPath in @(Get-VgoJsonStringArray -Value (Get-VgoJsonPropertyValue -Node $Ledger -Name 'specialist_wrapper_paths'))) {
    Add-InstallLedgerOwnedFile -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $rawPath
  }
  foreach ($entry in @((Get-VgoJsonPropertyValue -Node $Ledger -Name 'merged_files'))) {
    if ($null -eq $entry) {
      continue
    }
    $pathValue = [string](Get-VgoJsonPropertyValue -Node $entry -Name 'path')
    Add-InstallLedgerOwnedFile -OwnedFiles $ownedFiles -TargetRoot $targetRootFull -PathValue $pathValue
  }

  return [ordered]@{
    installed_skill_count = $installedSkillNames.Count
    installed_skill_names = @($installedSkillNames.ToArray() | Sort-Object)
    installed_file_count = $ownedFiles.Count
  }
}

function Update-InstallLedgerPayloadSummary {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot
  )

  $ledgerPath = Join-Path $TargetRoot '.vibeskills\install-ledger.json'
  if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) {
    throw "Install ledger missing for refresh: $ledgerPath"
  }

  try {
    $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    throw ("Failed to parse install ledger for refresh: " + $_.Exception.Message)
  }

  $payloadSummary = [pscustomobject](Get-InstallLedgerPayloadSummary -Ledger $ledger -TargetRoot $TargetRoot)
  $ledger | Add-Member -NotePropertyName 'payload_summary' -NotePropertyValue $payloadSummary -Force

  Write-VgoUtf8NoBomText -Path $ledgerPath -Content ($ledger | ConvertTo-Json -Depth 20)
}
function Copy-DirContent {
  param(
    [string]$Source,
    [string]$Destination
  )
  if (-not (Test-Path -LiteralPath $Source)) { return }
  $sourceFull = [System.IO.Path]::GetFullPath($Source)
  $destinationFull = [System.IO.Path]::GetFullPath($Destination)
  if ($sourceFull -eq $destinationFull) {
    Write-Host "Skip self-copy: $sourceFull"
    return
  }
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

function Resolve-CodexDuplicateSkillRoot {
  param(
    [string]$TargetRoot,
    [string]$HostId
  )

  if ([string]$HostId -ne 'codex') {
    return $null
  }

  $leaf = (Split-Path -Path $TargetRoot -Leaf).ToLowerInvariant()
  if ($leaf -ne '.codex') {
    return $null
  }

  $parent = Get-VgoParentPath -Path $TargetRoot
  if ([string]::IsNullOrWhiteSpace($parent)) {
    return $null
  }

  return (Join-Path $parent '.agents\skills\vibe')
}

function Test-VibeSkillDirectory {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $false
  }

  $skillMd = Join-Path $Path 'SKILL.md'
  if (-not (Test-Path -LiteralPath $skillMd)) {
    return $false
  }

  $lines = Get-Content -LiteralPath $skillMd -TotalCount 20 -Encoding UTF8
  return [bool](@($lines | Where-Object { $_ -match '^\s*name:\s*vibe\s*$' }).Count -gt 0)
}

function Invoke-CodexDuplicateSkillQuarantine {
  param(
    [string]$TargetRoot,
    [string]$HostId
  )

  $duplicateRoot = Resolve-CodexDuplicateSkillRoot -TargetRoot $TargetRoot -HostId $HostId
  if ([string]::IsNullOrWhiteSpace($duplicateRoot) -or -not (Test-Path -LiteralPath $duplicateRoot -PathType Container)) {
    return
  }

  $targetSkillRoot = Join-Path $TargetRoot 'skills\vibe'
  if (-not (Test-Path -LiteralPath $targetSkillRoot -PathType Container)) {
    return
  }

  $duplicateFull = [System.IO.Path]::GetFullPath($duplicateRoot)
  $targetFull = [System.IO.Path]::GetFullPath($targetSkillRoot)
  if ($duplicateFull -eq $targetFull) {
    return
  }

  if (-not (Test-VibeSkillDirectory -Path $duplicateRoot)) {
    throw "Duplicate Codex-discovered skill surface exists at '$duplicateRoot', but it is not a recognizable vibe skill copy. Move it out of .agents/skills manually."
  }

  $agentsHome = Get-VgoParentPath -Path (Get-VgoParentPath -Path $duplicateRoot)
  if ([string]::IsNullOrWhiteSpace($agentsHome)) {
    throw "Unable to resolve .agents home for duplicate skill surface: $duplicateRoot"
  }

  $quarantineRoot = Join-Path $agentsHome 'skills-disabled'
  $quarantinePath = Join-Path $quarantineRoot ("vibe.codex-duplicate-" + (Get-Date -Format 'yyyyMMddTHHmmss'))
  New-Item -ItemType Directory -Force -Path $quarantineRoot | Out-Null
  Move-Item -LiteralPath $duplicateRoot -Destination $quarantinePath
  Write-Warning ("Quarantined duplicate Codex-discovered vibe skill: {0} -> {1}" -f $duplicateRoot, $quarantinePath)
}
function Ensure-SkillPresent {
  param(
    [string]$Name,
    [bool]$Required,
    [string[]]$FallbackSources = @(),
    [string]$TargetRoot,
    [bool]$AllowExternalSkillFallback,
    [System.Collections.Generic.List[string]]$ExternalFallbackUsed,
    [System.Collections.Generic.List[string]]$MissingRequiredSkills
  )
  if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $TargetRoot = $script:TargetRoot
  }
  if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    throw 'Ensure-SkillPresent requires TargetRoot.'
  }
  if ([string]::IsNullOrWhiteSpace($Name)) {
    throw 'Ensure-SkillPresent requires Name.'
  }
  $targetSkillMd = Join-Path $TargetRoot ("skills\" + $Name + "\SKILL.md")
  if (Test-Path -LiteralPath $targetSkillMd) { return }
  if ($AllowExternalSkillFallback) {
    foreach ($src in $FallbackSources) {
      if ([string]::IsNullOrWhiteSpace($src)) { continue }
      if (Test-Path -LiteralPath $src) {
        Write-Warning "Using external fallback source for skill '$Name': $src"
        $destination = Join-Path $TargetRoot ("skills\" + $Name)
        Copy-DirContent -Source $src -Destination $destination
        Restore-SkillEntryPointIfNeeded -SkillRoot $destination
        $ExternalFallbackUsed.Add($Name) | Out-Null
        break
      }
    }
  }
  if (-not (Test-Path -LiteralPath $targetSkillMd)) {
    if ($Required) {
      $MissingRequiredSkills.Add($Name) | Out-Null
      Write-Warning "Missing required vendored skill: $Name"
    } else {
      Write-Warning "Missing optional vendored skill: $Name"
    }
  }
}
function Sync-VibeCanonicalToTarget {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot
  )
  $governance = Get-InstallGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $canonicalRoot = Join-Path $RepoRoot ([string]$governance.source_of_truth.canonical_root)
  $mirrorFiles = @($governance.packaging.mirror.files)
  $mirrorDirs = @($governance.packaging.mirror.directories)
  $targetRel = [string]$runtimeConfig.target_relpath
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    $targetRel = 'skills\vibe'
  }
  $targetVibeRoot = Join-Path $TargetRoot $targetRel
  foreach ($rel in $mirrorFiles) {
    $src = Join-Path $canonicalRoot $rel
    $dst = Join-Path $targetVibeRoot $rel
    if (-not (Test-Path -LiteralPath $src)) { continue }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
  }
  foreach ($dir in $mirrorDirs) {
    $srcDir = Join-Path $canonicalRoot $dir
    $dstDir = Join-Path $targetVibeRoot $dir
    if (-not (Test-Path -LiteralPath $srcDir)) { continue }
    if (Test-Path -LiteralPath $dstDir) {
      Remove-Item -LiteralPath $dstDir -Recurse -Force
    }
    Copy-DirContent -Source $srcDir -Destination $dstDir
  }
}

function Hide-InstalledRuntimeMirrorSkillEntryPoints {
  param([string]$TargetRoot)

  $nestedSkillsRoot = Join-Path $TargetRoot 'skills\vibe\bundled\skills'
  if (-not (Test-Path -LiteralPath $nestedSkillsRoot -PathType Container)) {
    return
  }

  $renamed = 0
  foreach ($skillDir in @(Get-ChildItem -LiteralPath $nestedSkillsRoot -Directory -ErrorAction SilentlyContinue)) {
    $skillMd = Join-Path $skillDir.FullName 'SKILL.md'
    if (-not (Test-Path -LiteralPath $skillMd -PathType Leaf)) {
      continue
    }

    $mirrorPath = Join-Path $skillDir.FullName 'SKILL.runtime-mirror.md'
    Move-Item -LiteralPath $skillMd -Destination $mirrorPath -Force
    Write-Host ("[INFO] Hid nested runtime mirror skill entrypoint: {0} -> {1}" -f $skillMd, $mirrorPath)
    $renamed++
  }

  if ($renamed -eq 0) {
    Write-Host "[INFO] Nested runtime mirror skill entrypoints already sanitized."
  }
}

function Restore-SkillEntryPointIfNeeded {
  param([string]$SkillRoot)

  $skillMd = Join-Path $SkillRoot 'SKILL.md'
  $mirrorPath = Join-Path $SkillRoot 'SKILL.runtime-mirror.md'
  if ((Test-Path -LiteralPath $skillMd -PathType Leaf) -or -not (Test-Path -LiteralPath $mirrorPath -PathType Leaf)) {
    return
  }

  Move-Item -LiteralPath $mirrorPath -Destination $skillMd -Force
}
Write-Host "=== VCO Adapter Installer ===" -ForegroundColor Cyan
Write-Host "Host   : $HostId"
Write-Host "Mode   : $($Adapter.install_mode)"
Write-Host "Profile: $Profile"
Write-Host "Target : $TargetRoot"
Write-Host "StrictOffline: $StrictOffline"
Write-Host "RequireClosedReady: $RequireClosedReady"
Write-Host "AllowExternalSkillFallback: $AllowExternalSkillFallback"
Write-Host "SkipRuntimeFreshnessGate: $SkipRuntimeFreshnessGate"
$installGovernance = Get-InstallGovernance -RepoRoot $RepoRoot
$installRuntimeConfig = Get-InstalledRuntimeConfig -Governance $installGovernance
$targetVibeRel = [string]$installRuntimeConfig.target_relpath
if ([string]::IsNullOrWhiteSpace($targetVibeRel)) {
  $targetVibeRel = 'skills\vibe'
}

$adapterInstallerPath = Join-Path $RepoRoot 'scripts\install\Install-VgoAdapter.ps1'
if (-not (Test-Path -LiteralPath $adapterInstallerPath)) {
  throw "Adapter installer script missing: $adapterInstallerPath"
}
$adapterInstallResult = & $adapterInstallerPath -RepoRoot $RepoRoot -TargetRoot $TargetRoot -HostId $HostId -Profile $Profile -RequireClosedReady:$RequireClosedReady -AllowExternalSkillFallback:$AllowExternalSkillFallback
$adapterInstallReceipt = $null
if ($adapterInstallResult) {
  try {
    $adapterInstallReceipt = ($adapterInstallResult | Out-String) | ConvertFrom-Json
  } catch {
    $adapterInstallReceipt = $null
  }
}
if ($RequireClosedReady -and $null -ne $adapterInstallReceipt) {
  $effective = if ($adapterInstallReceipt.PSObject.Properties.Name -contains 'require_closed_ready_effective') { [bool]$adapterInstallReceipt.require_closed_ready_effective } else { $false }
  $state = if ($adapterInstallReceipt.PSObject.Properties.Name -contains 'host_closure_state') { [string]$adapterInstallReceipt.host_closure_state } else { '' }
  if ($effective -and $state -ne 'closed_ready') {
    throw ("Install receipt is not closed_ready under RequireClosedReady (got '{0}')." -f $state)
  }
}
$externalFallbackUsed = New-Object System.Collections.Generic.List[string]
if ($null -ne $adapterInstallReceipt -and $adapterInstallReceipt.PSObject.Properties.Name -contains 'external_fallback_used') {
  foreach ($name in @($adapterInstallReceipt.external_fallback_used)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$name)) {
      $externalFallbackUsed.Add([string]$name) | Out-Null
    }
  }
}

Hide-InstalledRuntimeMirrorSkillEntryPoints -TargetRoot $TargetRoot

if ($InstallExternal) {
  if ($Adapter.install_mode -ne 'governed') {
    Write-Warning "InstallExternal is currently only applied to the governed Codex lane. Skipping external install for host '$HostId'."
  } else {
    Write-Host "Installing optional external dependencies..."
  $pythonCommand = Get-PreferredPythonCommand
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $temp = Join-Path $env:TEMP ("superclaude-" + [guid]::NewGuid().ToString("N"))
    try {
      git clone --depth 1 https://github.com/SuperClaude-Org/SuperClaude_Framework.git $temp | Out-Null
      $dest = Join-Path $TargetRoot 'commands\sc'
      if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
      if (Test-Path -LiteralPath (Join-Path $temp 'commands\sc')) {
        Copy-Item -LiteralPath (Join-Path $temp 'commands\sc') -Destination $dest -Recurse -Force
      } elseif (Test-Path -LiteralPath (Join-Path $temp 'sc')) {
        Copy-Item -LiteralPath (Join-Path $temp 'sc') -Destination $dest -Recurse -Force
      }
      Write-Host "Installed SuperClaude commands"
    } catch {
      Write-Warning "Failed to install SuperClaude commands: $($_.Exception.Message)"
    } finally {
      if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
    }
  }
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    try {
      npm install -g claude-flow | Out-Null
      Write-Host "Installed claude-flow"
    } catch {
      Write-Warning "Failed to install claude-flow"
    }
    try {
      npm install -g @th0rgal/ralph-wiggum | Out-Null
      Write-Host "Installed open-ralph-wiggum (@th0rgal/ralph-wiggum)"
    } catch {
      Write-Warning "Failed to install open-ralph-wiggum"
    }
  }
  if ($pythonCommand) {
    if (-not (Get-Command scrapling -ErrorAction SilentlyContinue)) {
      try {
        & $pythonCommand -m pip install 'scrapling[ai]' | Out-Null
        if (Get-Command scrapling -ErrorAction SilentlyContinue) {
          Write-Host "Installed scrapling[ai]"
        } else {
          Write-Warning "scrapling[ai] package install completed, but the scrapling CLI is still not callable from PATH. Ensure your Python scripts directory is exported before relying on the default scrapling MCP surface."
        }
      } catch {
        Write-Warning "Failed to install scrapling[ai]. Install manually (python -m pip install `"scrapling[ai]`") to enable the default scrapling MCP surface."
      }
    } else {
      Write-Host "scrapling already installed"
    }
  } else {
    Write-Warning "python/python3 not detected. Install Python + scrapling[ai] (python -m pip install `"scrapling[ai]`") to enable the default scrapling MCP surface."
  }
  if (-not (Get-Command xan -ErrorAction SilentlyContinue)) {
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
      try {
        scoop install xan | Out-Null
        Write-Host "Installed xan (via scoop)"
      } catch {
        Write-Warning "Failed to install xan via scoop"
      }
    } else {
      Write-Warning "xan CLI not detected. Install manually (Windows: scoop install xan) to enable large CSV acceleration."
    }
  } else {
    Write-Host "xan already installed"
  }
  if ($pythonCommand) {
    try {
      & $pythonCommand -c "import ivy; print(ivy.__version__)" *> $null
      Write-Host "ivy Python package already installed"
    } catch {
      Write-Warning "ivy Python package not detected. Install manually (pip install ivy) to enable framework-interop analyzer hints."
    }
  } else {
    Write-Warning "python/python3 not detected. Install Python + ivy (pip install ivy) if you want framework-interop analyzer hints."
  }
  if (-not (Get-Command fuck-u-code -ErrorAction SilentlyContinue)) {
    Write-Warning "fuck-u-code CLI not detected. Install manually if you want external quality-debt analyzer hints (quality-debt-overlay remains functional without it)."
  } else {
    Write-Host "fuck-u-code already installed"
  }
  try {
    $manifest = Get-Content -LiteralPath (Join-Path $RepoRoot 'config\plugins-manifest.codex.json') -Raw | ConvertFrom-Json
    Write-Host "Codex-only mode: plugin auto-install commands are disabled."
    foreach ($plugin in $manifest.core) {
      $mode = if ($plugin.PSObject.Properties.Name -contains 'install_mode') { $plugin.install_mode } else { 'manual-codex' }
      $hint = if ($plugin.PSObject.Properties.Name -contains 'install_hint') { $plugin.install_hint } else { 'Provision manually in your Codex environment.' }
      Write-Host ("[MANUAL] {0} ({1}) - {2}" -f $plugin.name, $mode, $hint)
    }
  } catch {
    Write-Warning "Failed to process plugin manifest"
  }
  }
}
if ($StrictOffline) {
  $offlineGate = Join-Path $RepoRoot 'scripts\verify\vibe-offline-skills-gate.ps1'
  if (-not (Test-Path -LiteralPath $offlineGate)) {
    throw "StrictOffline requested, but offline gate script is missing: $offlineGate"
  }
  & $offlineGate `
    -SkillsRoot (Join-Path $TargetRoot 'skills') `
    -PackManifestPath (Join-Path $RepoRoot 'config\pack-manifest.json') `
    -SkillsLockPath (Join-Path $RepoRoot 'config\skills-lock.json')
  if ($LASTEXITCODE -ne 0) {
    throw "StrictOffline validation failed (vibe-offline-skills-gate)."
  }
  if ($externalFallbackUsed.Count -gt 0) {
    throw ("StrictOffline rejected external fallback usage: " + (($externalFallbackUsed | Select-Object -Unique) -join ", "))
  }
} elseif ($externalFallbackUsed.Count -gt 0) {
  Write-Warning ("External fallback skills were used (non-reproducible install): " + (($externalFallbackUsed | Select-Object -Unique) -join ", "))
}
Invoke-CodexDuplicateSkillQuarantine -TargetRoot $TargetRoot -HostId $HostId
Invoke-InstalledRuntimeFreshnessGate -RepoRoot $RepoRoot -TargetRoot $TargetRoot -SkipGate:$SkipRuntimeFreshnessGate
Update-InstallLedgerPayloadSummary -RepoRoot $RepoRoot -TargetRoot $TargetRoot
Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
$checkShellPath = Get-VgoPowerShellCommand
$checkShellLeaf = [System.IO.Path]::GetFileName($checkShellPath).ToLowerInvariant()
$checkCommandParts = @($checkShellLeaf, '-NoProfile')
if ($checkShellLeaf -like 'powershell*') {
  $checkCommandParts += @('-ExecutionPolicy', 'Bypass')
}
$checkCommandParts += @('-File', '.\check.ps1', '-Profile', $Profile, '-TargetRoot', $TargetRoot)
$checkCommand = ($checkCommandParts | ForEach-Object {
  $text = [string]$_
  if ($text -match '\s') {
    '"' + ($text -replace '"', '\"') + '"'
  } else {
    $text
  }
}) -join ' '
Write-Host ("Run: {0}" -f $checkCommand)
