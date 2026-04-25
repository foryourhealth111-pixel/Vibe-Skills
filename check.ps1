param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [string]$HostId = "codex",
  [string]$TargetRoot = '',
  [switch]$SkipRuntimeFreshnessGate,
  [switch]$Deep,
  [Alias('?')]
  [switch]$Help
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-WrapperUsage {
  Write-Output 'Usage: check.ps1 [-Profile minimal|full] [-HostId <id>] [-TargetRoot <path>] [-SkipRuntimeFreshnessGate] [-Deep] [-Help|-?]'
  Write-Output 'Runs the governed VCO adapter health check without falling back to legacy check scripts.'
}

if ($Help) {
  Show-WrapperUsage
  exit 0
}

. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')

$HostId = Resolve-VgoHostId -HostId $HostId
$Adapter = Resolve-VgoAdapterEntry -StartPath $RepoRoot -HostId $HostId

$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId

function Test-CanonicalRepoExecution {
  param([string]$RepoRoot)
  return (Test-VgoCanonicalRepoExecution -StartPath $RepoRoot)
}

function Get-CheckGovernance {
  param([string]$RepoRoot)

  $governancePath = Join-Path $RepoRoot 'config\version-governance.json'
  if (-not (Test-Path -LiteralPath $governancePath)) {
    return $null
  }

  try {
    return Get-Content -LiteralPath $governancePath -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    Write-Host ("[WARN] failed to parse version-governance.json -> " + $_.Exception.Message) -ForegroundColor Yellow
    $script:warn++
    return $null
  }
}

function Get-InstalledRuntimeConfig {
  param([psobject]$Governance)

  $defaults = [ordered]@{
    target_relpath = 'skills/vibe'
    receipt_relpath = 'skills/vibe/outputs/runtime-freshness-receipt.json'
    post_install_gate = 'scripts/verify/vibe-installed-runtime-freshness-gate.ps1'
    frontmatter_gate = 'scripts/verify/vibe-bom-frontmatter-gate.ps1'
    coherence_gate = 'scripts/verify/vibe-release-install-runtime-coherence-gate.ps1'
    receipt_contract_version = 1
    shell_degraded_behavior = 'warn_and_skip_authoritative_runtime_gate'
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

function Get-InstalledRuntimeTargetRelpath {
  param([psobject]$RuntimeConfig)

  $targetRel = if ($null -ne $RuntimeConfig -and $RuntimeConfig.PSObject.Properties.Name -contains 'target_relpath') {
    [string]$RuntimeConfig.target_relpath
  } else {
    ''
  }
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    return 'skills/vibe'
  }
  return $targetRel
}

function Resolve-DirectRuntimeExecutableForCheck {
  param([string]$HostId)

  $envName = $null
  $defaultCommand = $null
  switch ([string]$HostId) {
    'codex' {
      $envName = 'VGO_CODEX_EXECUTABLE'
      $defaultCommand = 'codex'
    }
    default {
      return [pscustomobject]@{
        command = $null
        resolved_path = $null
        source = $null
        ready = $false
      }
    }
  }

  $command = $defaultCommand
  $resolvedPath = $null
  $source = $null
  $envValue = if (-not [string]::IsNullOrWhiteSpace($envName)) { [Environment]::GetEnvironmentVariable($envName) } else { $null }
  if (-not [string]::IsNullOrWhiteSpace($envValue)) {
    $command = [string]$envValue
    $candidate = Get-Command $envValue -ErrorAction SilentlyContinue
    if ($candidate) {
      $resolvedPath = [string]$candidate.Source
      $source = "env:$envName"
    } elseif (Test-Path -LiteralPath $envValue -PathType Leaf) {
      $resolvedPath = [System.IO.Path]::GetFullPath($envValue)
      $source = "env:$envName"
    }
  }
  if ([string]::IsNullOrWhiteSpace($resolvedPath) -and -not [string]::IsNullOrWhiteSpace($defaultCommand)) {
    $candidate = Get-Command $defaultCommand -ErrorAction SilentlyContinue
    if ($candidate) {
      $resolvedPath = [string]$candidate.Source
      $source = "path:$defaultCommand"
    }
  }

  return [pscustomobject]@{
    command = $command
    resolved_path = $resolvedPath
    source = $source
    ready = [bool](-not [string]::IsNullOrWhiteSpace($resolvedPath))
  }
}

function Invoke-RuntimeNeutralBootstrapDoctor {
  param(
    [Parameter(Mandatory)] [string]$RepoRoot,
    [Parameter(Mandatory)] [string]$TargetRoot
  )

  $doctorPath = Join-Path $RepoRoot 'scripts\verify\runtime_neutral\bootstrap_doctor.py'
  if (-not (Test-Path -LiteralPath $doctorPath)) {
    return 127
  }

  $pythonCommand = $null
  foreach ($candidate in @('python', 'python3', 'py')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $command) {
      $pythonCommand = $command
      break
    }
  }
  if ($null -eq $pythonCommand) {
    return 127
  }

  $pythonLeaf = [System.IO.Path]::GetFileName([string]$pythonCommand.Source).ToLowerInvariant()
  $pythonArgs = @()
  if ($pythonLeaf -eq 'py.exe' -or $pythonLeaf -eq 'py') {
    $pythonArgs += '-3'
  }
  $pythonArgs += @($doctorPath, '--target-root', $TargetRoot, '--write-artifacts')
  & $pythonCommand.Source @pythonArgs 2>&1 | ForEach-Object { Write-Host $_ }
  if ($null -eq $LASTEXITCODE) {
    return 0
  }
  return [int]$LASTEXITCODE
}

function Resolve-CheckTargetContext {
  param(
    [Parameter(Mandatory)] [string]$InputRoot,
    [psobject]$RuntimeConfig
  )

  $targetRel = Get-InstalledRuntimeTargetRelpath -RuntimeConfig $RuntimeConfig
  $normalizedInputRoot = [System.IO.Path]::GetFullPath($InputRoot)
  $segments = @($targetRel -split '[\\/]+' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  $installedGovernancePath = Join-Path $normalizedInputRoot 'config\version-governance.json'
  $skillDescriptorPath = Join-Path $normalizedInputRoot 'SKILL.md'

  if ($segments.Count -gt 0 -and (Test-Path -LiteralPath $installedGovernancePath) -and (Test-Path -LiteralPath $skillDescriptorPath)) {
    $hostCandidate = $normalizedInputRoot
    $matched = $true
    for ($index = $segments.Count - 1; $index -ge 0; $index--) {
      $leaf = Split-Path -Leaf $hostCandidate
      if ([string]::IsNullOrWhiteSpace($leaf) -or $leaf.ToLowerInvariant() -ne ([string]$segments[$index]).ToLowerInvariant()) {
        $matched = $false
        break
      }
      $parent = Split-Path -Parent $hostCandidate
      if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $hostCandidate) {
        $matched = $false
        break
      }
      $hostCandidate = [System.IO.Path]::GetFullPath($parent)
    }

    if ($matched) {
      return [pscustomobject]@{
        target_root = $hostCandidate
        installed_root = $normalizedInputRoot
        target_relpath = $targetRel
        input_kind = 'installed_root'
      }
    }
  }

  return [pscustomobject]@{
    target_root = $normalizedInputRoot
    installed_root = [System.IO.Path]::GetFullPath((Join-Path $normalizedInputRoot $targetRel))
    target_relpath = $targetRel
    input_kind = 'host_root'
  }
}

function Check-Condition {
  param(
    [string]$Label,
    [bool]$Condition,
    [string]$FailureDetail = $null
  )

  if ($Condition) {
    Write-Host "[OK] $Label"
    $script:pass++
  } else {
    if ([string]::IsNullOrWhiteSpace($FailureDetail)) {
      Write-Host "[FAIL] $Label" -ForegroundColor Red
    } else {
      Write-Host "[FAIL] $Label -> $FailureDetail" -ForegroundColor Red
    }
    $script:fail++
  }
}

function Write-WarnNote {
  param([string]$Message)

  Write-Host "[WARN] $Message" -ForegroundColor Yellow
  $script:warn++
}

function Get-JsonObject {
  param(
    [string]$Path,
    [string]$Label
  )

  try {
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    Write-Host ("[FAIL] {0} parse -> {1}" -f $Label, $_.Exception.Message) -ForegroundColor Red
    $script:fail++
    return $null
  }
}

function Normalize-ComparablePath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $null
  }

  return [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\','/')).ToLowerInvariant()
}

function Resolve-LocalPathForCheck {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $Path
  }

  if ([System.IO.Path]::DirectorySeparatorChar -ne '\') {
    return $Path
  }

  if ($Path -match '^/mnt/([a-zA-Z])/(.*)$') {
    $drive = $Matches[1].ToUpperInvariant()
    $rest = ($Matches[2] -replace '/', '\')
    return "${drive}:\\$rest"
  }

  if ($Path -match '^/([a-zA-Z])/(.*)$') {
    $drive = $Matches[1].ToUpperInvariant()
    $rest = ($Matches[2] -replace '/', '\')
    return "${drive}:\\$rest"
  }

  return $Path
}

function ConvertTo-IntCheckValue {
  param(
    [object]$Value,
    [int]$Default = 0
  )

  $raw = if ($null -eq $Value) { $null } else { [string]$Value }
  $parsed = $Default
  $valid = $false
  if (-not [string]::IsNullOrWhiteSpace($raw)) {
    $valid = [int]::TryParse($raw, [ref]$parsed)
  }

  return [pscustomobject]@{
    raw = $raw
    value = $parsed
    valid = $valid
  }
}

function Format-OptionalValue {
  param([string]$Value)

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return '<missing>'
  }

  return $Value
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

function Check-CodexDuplicateSkillSurface {
  param(
    [string]$TargetRoot,
    [string]$HostId
  )

  $duplicateRoot = Resolve-CodexDuplicateSkillRoot -TargetRoot $TargetRoot -HostId $HostId
  if ([string]::IsNullOrWhiteSpace($duplicateRoot) -or -not (Test-Path -LiteralPath $duplicateRoot -PathType Container)) {
    return
  }

  if (Test-VibeSkillDirectory -Path $duplicateRoot) {
    Write-Host ("[FAIL] duplicate Codex-discovered vibe skill surface -> {0}" -f $duplicateRoot) -ForegroundColor Red
    Write-Host '[FAIL] Re-run install.ps1 for the default Codex root to quarantine the legacy .agents copy, or move it out of .agents/skills manually.' -ForegroundColor Red
    $script:fail++
    return
  }

  Write-WarnNote -Message ("unexpected directory exists at Codex duplicate-surface path: {0}" -f $duplicateRoot)
}

function Test-ReceiptTargetFreshness {
  param(
    [string]$TargetRoot,
    [psobject]$RuntimeConfig
  )

  $receiptRel = [string]$RuntimeConfig.receipt_relpath
  if ([string]::IsNullOrWhiteSpace($receiptRel)) {
    return
  }

  $receiptPath = Join-Path $TargetRoot $receiptRel
  if (-not (Test-Path -LiteralPath $receiptPath)) {
    return
  }

  $targetRel = [string]$RuntimeConfig.target_relpath
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    $targetRel = 'skills/vibe'
  }

  $installedGovernancePath = Join-Path $TargetRoot (Join-Path $targetRel 'config\version-governance.json')
  if (-not (Test-Path -LiteralPath $installedGovernancePath)) {
    return
  }

  $installedGovernance = Get-JsonObject -Path $installedGovernancePath -Label 'installed vibe governance'
  if ($null -eq $installedGovernance) {
    return
  }

  $receipt = Get-JsonObject -Path $receiptPath -Label 'runtime freshness receipt'
  if ($null -eq $receipt) {
    return
  }

  $targetRel = [string]$RuntimeConfig.target_relpath
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    $targetRel = 'skills/vibe'
  }

  $expectedTargetRoot = Normalize-ComparablePath -Path $TargetRoot
  $expectedInstalledRoot = Normalize-ComparablePath -Path (Join-Path $TargetRoot $targetRel)
  $receiptTargetRoot = Normalize-ComparablePath -Path ([string]$receipt.target_root)
  $receiptInstalledRoot = Normalize-ComparablePath -Path ([string]$receipt.installed_root)

  $receiptGateResult = if ($receipt.PSObject.Properties.Name -contains 'gate_result') { [string]$receipt.gate_result } else { $null }
  Check-Condition -Label 'vibe runtime freshness receipt gate_result' -Condition ($receiptGateResult -eq 'PASS') -FailureDetail (Format-OptionalValue -Value $receiptGateResult)

  $receiptVersionCheck = if ($receipt.PSObject.Properties.Name -contains 'receipt_version') {
    ConvertTo-IntCheckValue -Value $receipt.receipt_version
  } else {
    ConvertTo-IntCheckValue
  }
  $expectedReceiptContractVersionCheck = if ($RuntimeConfig.PSObject.Properties.Name -contains 'receipt_contract_version') {
    ConvertTo-IntCheckValue -Value $RuntimeConfig.receipt_contract_version -Default 1
  } else {
    ConvertTo-IntCheckValue -Value 1 -Default 1
  }
  $expectedReceiptContractVersion = $expectedReceiptContractVersionCheck.value
  $receiptVersionFailureDetail = if ($receiptVersionCheck.valid) {
    [string]$receiptVersionCheck.value
  } else {
    Format-OptionalValue -Value $receiptVersionCheck.raw
  }
  $expectedVersionFailureDetail = if ($expectedReceiptContractVersionCheck.valid) {
    [string]$expectedReceiptContractVersion
  } else {
    Format-OptionalValue -Value $expectedReceiptContractVersionCheck.raw
  }
  Check-Condition `
    -Label 'vibe runtime freshness receipt version' `
    -Condition ($expectedReceiptContractVersionCheck.valid -and $receiptVersionCheck.valid -and $receiptVersionCheck.value -ge $expectedReceiptContractVersion) `
    -FailureDetail ("receipt={0}; expected={1}" -f $receiptVersionFailureDetail, $expectedVersionFailureDetail)

  Check-Condition -Label 'vibe runtime freshness receipt target_root' -Condition ($receiptTargetRoot -eq $expectedTargetRoot) -FailureDetail (Format-OptionalValue -Value ([string]$receipt.target_root))
  Check-Condition -Label 'vibe runtime freshness receipt installed_root' -Condition ($receiptInstalledRoot -eq $expectedInstalledRoot) -FailureDetail (Format-OptionalValue -Value ([string]$receipt.installed_root))

  $installedRelease = if ($installedGovernance.PSObject.Properties.Name -contains 'release') { $installedGovernance.release } else { $null }
  $installedVersion = if ($null -ne $installedRelease -and $installedRelease.PSObject.Properties.Name -contains 'version') { [string]$installedRelease.version } else { $null }
  $installedUpdated = if ($null -ne $installedRelease -and $installedRelease.PSObject.Properties.Name -contains 'updated') { [string]$installedRelease.updated } else { $null }
  $receiptRelease = if ($receipt.PSObject.Properties.Name -contains 'release') { $receipt.release } else { $null }
  $receiptVersion = if ($null -ne $receiptRelease -and $receiptRelease.PSObject.Properties.Name -contains 'version') { [string]$receiptRelease.version } else { $null }
  $receiptUpdated = if ($null -ne $receiptRelease -and $receiptRelease.PSObject.Properties.Name -contains 'updated') { [string]$receiptRelease.updated } else { $null }

  if (-not [string]::IsNullOrWhiteSpace($installedVersion)) {
    Check-Condition -Label 'vibe runtime freshness receipt release.version' -Condition ($receiptVersion -eq $installedVersion) -FailureDetail (Format-OptionalValue -Value $receiptVersion)
  }

  if (-not [string]::IsNullOrWhiteSpace($installedUpdated)) {
    Check-Condition -Label 'vibe runtime freshness receipt release.updated' -Condition ($receiptUpdated -eq $installedUpdated) -FailureDetail (Format-OptionalValue -Value $receiptUpdated)
  }
}

function Show-InstalledRuntimeUpgradeHint {
  param(
    [psobject]$Governance,
    [string]$TargetRoot,
    [psobject]$RuntimeConfig
  )

  if ($null -eq $Governance -or $null -eq $RuntimeConfig) {
    return
  }

  $targetRel = [string]$RuntimeConfig.target_relpath
  if ([string]::IsNullOrWhiteSpace($targetRel)) {
    $targetRel = 'skills/vibe'
  }

  $installedGovernancePath = Join-Path $TargetRoot (Join-Path $targetRel 'config\version-governance.json')
  if (-not (Test-Path -LiteralPath $installedGovernancePath)) {
    return
  }

  $installedGovernance = Get-JsonObject -Path $installedGovernancePath -Label 'installed vibe governance'
  if ($null -eq $installedGovernance) {
    return
  }

  $repoRelease = if ($Governance.PSObject.Properties.Name -contains 'release') { $Governance.release } else { $null }
  $installedRelease = if ($installedGovernance.PSObject.Properties.Name -contains 'release') { $installedGovernance.release } else { $null }
  if ($null -eq $repoRelease -or $null -eq $installedRelease) {
    return
  }

  $repoVersion = if ($repoRelease.PSObject.Properties.Name -contains 'version') { [string]$repoRelease.version } else { $null }
  $repoUpdated = if ($repoRelease.PSObject.Properties.Name -contains 'updated') { [string]$repoRelease.updated } else { $null }
  $installedVersion = if ($installedRelease.PSObject.Properties.Name -contains 'version') { [string]$installedRelease.version } else { $null }
  $installedUpdated = if ($installedRelease.PSObject.Properties.Name -contains 'updated') { [string]$installedRelease.updated } else { $null }

  $versionMismatch = (-not [string]::IsNullOrWhiteSpace($repoVersion)) -and ($repoVersion -ne $installedVersion)
  $updatedMismatch = (-not [string]::IsNullOrWhiteSpace($repoUpdated)) -and ($repoUpdated -ne $installedUpdated)
  if ($versionMismatch -or $updatedMismatch) {
    Write-Host ("[INFO] installed runtime release differs from canonical repo release (installed={0}/{1}, repo={2}/{3}). Re-run install.ps1 or one-shot-setup.ps1 for TargetRoot={4} before treating freshness failures as receipt-only issues." -f (Format-OptionalValue -Value $installedVersion), (Format-OptionalValue -Value $installedUpdated), (Format-OptionalValue -Value $repoVersion), (Format-OptionalValue -Value $repoUpdated), $TargetRoot) -ForegroundColor Yellow
  }
}

function Invoke-RuntimeFreshnessCheck {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot,
    [switch]$SkipGate
  )

  $governance = Get-CheckGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  Show-InstalledRuntimeUpgradeHint -Governance $governance -TargetRoot $TargetRoot -RuntimeConfig $runtimeConfig
  $receiptRel = [string]$runtimeConfig.receipt_relpath

  if ($SkipGate) {
    if (-not [string]::IsNullOrWhiteSpace($receiptRel)) {
      $receiptPath = Join-Path $TargetRoot $receiptRel
      if (Test-Path -LiteralPath $receiptPath) {
        Check-Path -Label 'vibe runtime freshness receipt' -Path $receiptPath
        Test-ReceiptTargetFreshness -TargetRoot $TargetRoot -RuntimeConfig $runtimeConfig
      } else {
        Write-Host '[WARN] vibe runtime freshness receipt unavailable because the gate was skipped by request.' -ForegroundColor Yellow
        $script:warn++
      }
    }
    Write-Host '[WARN] runtime freshness gate skipped by request.' -ForegroundColor Yellow
    $script:warn++
    return
  }

  if (-not [string]::IsNullOrWhiteSpace($receiptRel)) {
    Check-Path -Label 'vibe runtime freshness receipt' -Path (Join-Path $TargetRoot $receiptRel)
    Test-ReceiptTargetFreshness -TargetRoot $TargetRoot -RuntimeConfig $runtimeConfig
  }

  if (-not (Test-CanonicalRepoExecution -RepoRoot $RepoRoot)) {
    Write-Host '[WARN] runtime freshness gate skipped: run canonical repo check.ps1 to execute freshness verification.' -ForegroundColor Yellow
    $script:warn++
    return
  }

  $gateRel = [string]$runtimeConfig.post_install_gate
  if ([string]::IsNullOrWhiteSpace($gateRel)) {
    $gateRel = 'scripts\verify\vibe-installed-runtime-freshness-gate.ps1'
  }

  $gatePath = Join-Path $RepoRoot $gateRel
  if (-not (Test-Path -LiteralPath $gatePath)) {
    Write-Host "[FAIL] vibe runtime freshness gate script -> $gatePath" -ForegroundColor Red
    $script:fail++
    return
  }

  $global:LASTEXITCODE = 0
  & $gatePath -TargetRoot $TargetRoot
  $gateExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
  if ($gateExitCode -eq 0) {
    Write-Host '[OK] vibe installed runtime freshness gate'
    $script:pass++
  } else {
    Write-Host '[FAIL] vibe installed runtime freshness gate' -ForegroundColor Red
    $script:fail++
  }
}

function Invoke-RuntimeFrontmatterCheck {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot
  )

  if (-not (Test-CanonicalRepoExecution -RepoRoot $RepoRoot)) {
    Write-Host '[WARN] runtime frontmatter gate skipped: run canonical repo check.ps1 to execute BOM/frontmatter verification.' -ForegroundColor Yellow
    $script:warn++
    return
  }

  $governance = Get-CheckGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $gateRel = [string]$runtimeConfig.frontmatter_gate
  if ([string]::IsNullOrWhiteSpace($gateRel)) {
    $gateRel = 'scripts\verify\vibe-bom-frontmatter-gate.ps1'
  }

  $gatePath = Join-Path $RepoRoot $gateRel
  if (-not (Test-Path -LiteralPath $gatePath)) {
    Write-Host "[FAIL] vibe runtime frontmatter gate script -> $gatePath" -ForegroundColor Red
    $script:fail++
    return
  }

  $global:LASTEXITCODE = 0
  & $gatePath -TargetRoot $TargetRoot
  $gateExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
  if ($gateExitCode -eq 0) {
    Write-Host '[OK] vibe runtime BOM/frontmatter gate'
    $script:pass++
  } else {
    Write-Host '[FAIL] vibe runtime BOM/frontmatter gate' -ForegroundColor Red
    $script:fail++
  }
}

function Invoke-RuntimeCoherenceCheck {
  param(
    [string]$RepoRoot,
    [string]$TargetRoot
  )

  if (-not (Test-CanonicalRepoExecution -RepoRoot $RepoRoot)) {
    Write-Host '[WARN] runtime coherence gate skipped: run canonical repo check.ps1 to execute coherence verification.' -ForegroundColor Yellow
    $script:warn++
    return
  }

  $governance = Get-CheckGovernance -RepoRoot $RepoRoot
  $runtimeConfig = Get-InstalledRuntimeConfig -Governance $governance
  $gateRel = [string]$runtimeConfig.coherence_gate
  if ([string]::IsNullOrWhiteSpace($gateRel)) {
    $gateRel = 'scripts\verify\vibe-release-install-runtime-coherence-gate.ps1'
  }

  $gatePath = Join-Path $RepoRoot $gateRel
  if (-not (Test-Path -LiteralPath $gatePath)) {
    Write-Host "[FAIL] vibe runtime coherence gate script -> $gatePath" -ForegroundColor Red
    $script:fail++
    return
  }

  $global:LASTEXITCODE = 0
  & $gatePath -TargetRoot $TargetRoot
  $gateExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
  if ($gateExitCode -eq 0) {
    Write-Host '[OK] vibe release/install/runtime coherence gate'
    $script:pass++
  } else {
    Write-Host '[FAIL] vibe release/install/runtime coherence gate' -ForegroundColor Red
    $script:fail++
  }
}

$requiredSkills = @('vibe', 'dialectic', 'local-vco-roles', 'spec-kit-vibe-compat', 'superclaude-framework-compat', 'ralph-loop', 'cancel-ralph', 'tdd-guide', 'think-harder')
$requiredWorkflow = @('brainstorming', 'writing-plans', 'subagent-driven-development', 'systematic-debugging')
$optionalWorkflow = @('requesting-code-review', 'receiving-code-review', 'verification-before-completion')

$pass = 0
$fail = 0
$warn = 0

function Check-Path {
  param([string]$Label, [string]$Path, [bool]$Required = $true)
  if (Test-Path -LiteralPath $Path) {
    Write-Host "[OK] $Label"
    $script:pass++
  } elseif ($Required) {
    Write-Host "[FAIL] $Label -> $Path" -ForegroundColor Red
    $script:fail++
  } else {
    Write-Host "[WARN] $Label -> $Path" -ForegroundColor Yellow
    $script:warn++
  }
}

function Check-PathAbsent {
  param([string]$Label, [string]$Path)

  if (Test-Path -LiteralPath $Path) {
    Write-Host "[FAIL] $Label -> $Path" -ForegroundColor Red
    $script:fail++
  } else {
    Write-Host "[OK] $Label"
    $script:pass++
  }
}

function Get-ProfilePackagingManifestPath {
  param(
    [string]$TargetRoot,
    [string]$Profile
  )

  return (Join-Path $TargetRoot ("config\runtime-core-packaging.{0}.json" -f $Profile))
}

function Get-ProjectedSkillNamesForCheck {
  param(
    [string]$TargetRoot,
    [string]$Profile,
    [string]$ProjectionName,
    [string]$HostId
  )

  $manifestPath = Get-ProfilePackagingManifestPath -TargetRoot $TargetRoot -Profile $Profile
  if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    return @()
  }

  $payload = Get-JsonObject -Path $manifestPath -Label ("runtime packaging manifest ({0})" -f $Profile)
  if ($null -eq $payload -or -not $payload.PSObject.Properties.Name.Contains($ProjectionName)) {
    return @()
  }

  $projection = $payload.$ProjectionName
  if ($null -eq $projection) {
    return @()
  }

  if ($ProjectionName -eq 'compatibility_skill_projections' -and $projection.PSObject.Properties.Name.Contains('host_allowlist')) {
    $allowlist = @($projection.host_allowlist | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($allowlist.Count -gt 0 -and $allowlist -notcontains $HostId) {
      return @()
    }
  }

  return @(
    @($projection.projected_skill_names) |
      ForEach-Object { [string]$_ } |
      Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
      Select-Object -Unique
  )
}

function Invoke-AdapterSpecificChecks {
  param(
    [psobject]$Adapter,
    [string]$TargetRoot,
    [string]$HostId,
    [string]$RuntimeSkillRoot,
    [string]$RuntimeNestedSkillRoot,
    [bool]$NestedBundledRequired,
    [string]$NestedBundledPresencePolicy
  )

  if ([string]$Adapter.check_mode -eq 'governed') {
    Check-Path -Label "settings.json" -Path (Join-Path $TargetRoot 'settings.json')
  }
  if ([string]$Adapter.check_mode -eq 'preview-guidance') {
    if ([string]$Adapter.id -eq 'opencode') {
      Write-Host '[INFO] opencode preview now runs as skills-only activation; the real opencode.json stays untouched and sidecar state is verified' -ForegroundColor Cyan
    } else {
      Write-Host ("[INFO] {0} preview now runs as skills-only activation; host-native config files stay untouched and sidecar state is verified" -f $Adapter.id) -ForegroundColor Cyan
    }
  }
  if ([string]$Adapter.check_mode -eq 'runtime-core') {
    Write-Host ("[INFO] {0} runtime-core now verifies skill-native activation and sidecar state only; host-native workflow/config files are intentionally absent" -f $Adapter.id) -ForegroundColor Cyan
  }
  if ([string]$Adapter.id -in @('claude-code', 'cursor', 'windsurf', 'openclaw', 'opencode')) {
    Check-Path -Label "host settings sidecar" -Path (Join-Path $TargetRoot '.vibeskills\host-settings.json')
  }
  if ([string]$Adapter.check_mode -eq 'governed') {
    Check-Path -Label "plugins manifest" -Path (Join-Path $TargetRoot 'config\plugins-manifest.codex.json')
    Check-Path -Label "rules/common" -Path (Join-Path $TargetRoot 'rules\common\agents.md')
    Check-Path -Label "mcp template" -Path (Join-Path $TargetRoot 'mcp\servers.template.json')
  }

  $hostClosurePath = Join-Path $TargetRoot '.vibeskills\host-closure.json'
  Check-Path -Label "host closure manifest" -Path $hostClosurePath
  if (Test-Path -LiteralPath $hostClosurePath) {
    $hostClosure = Get-JsonObject -Path $hostClosurePath -Label 'host closure manifest'
    $directRuntime = Resolve-DirectRuntimeExecutableForCheck -HostId $HostId
    if ($directRuntime.ready) {
      Check-Condition -Label ("direct runtime executable -> {0}" -f [string]$directRuntime.resolved_path) -Condition $true
    } elseif ([string]$HostId -eq 'codex') {
      Write-WarnNote -Message ("direct runtime executable unavailable for {0} ({1})" -f [string]$HostId, (Format-OptionalValue -Value ([string]$directRuntime.command)))
    }
    if ($null -ne $hostClosure) {
      $closureState = if ($hostClosure.PSObject.Properties.Name -contains 'host_closure_state') { [string]$hostClosure.host_closure_state } else { '' }
      if (-not [string]::IsNullOrWhiteSpace($closureState)) {
        if ($closureState -eq 'closed_ready') {
          if ([string]$HostId -eq 'codex' -and -not $directRuntime.ready) {
            Write-WarnNote -Message ("host closure receipt stale -> {0} (live direct runtime unavailable for {1})" -f $closureState, [string]$HostId)
          } else {
            Check-Condition -Label 'host closure state' -Condition $true
          }
        } elseif ([string]$HostId -eq 'codex' -and $directRuntime.ready) {
          Write-WarnNote -Message ("host closure receipt stale -> {0} (live direct runtime ready via {1})" -f $closureState, (Format-OptionalValue -Value ([string]$directRuntime.source)))
        } else {
          Write-WarnNote -Message ("host closure state -> {0}" -f $closureState)
        }
      }
    }
    if ($null -ne $hostClosure -and $hostClosure.PSObject.Properties.Name -contains 'specialist_wrapper' -and $null -ne $hostClosure.specialist_wrapper) {
      $launcherPath = if ($hostClosure.specialist_wrapper.PSObject.Properties.Name -contains 'launcher_path') { [string]$hostClosure.specialist_wrapper.launcher_path } else { '' }
      if (-not [string]::IsNullOrWhiteSpace($launcherPath)) {
        Check-Path -Label "specialist wrapper launcher" -Path (Resolve-LocalPathForCheck -Path $launcherPath)
      }
    }
  }

  Check-Path -Label "upstream lock" -Path (Join-Path $TargetRoot 'config\upstream-lock.json')
  $installedRuntimeGovernancePath = Join-Path $TargetRoot (Join-Path $startupRuntimeTargetRel 'config\version-governance.json')
  Check-Path -Label "vibe version governance config" -Path $installedRuntimeGovernancePath
  $runtimeReleaseLedgerRequired = $true
  if (Test-Path -LiteralPath $installedRuntimeGovernancePath) {
    $installedRuntimeGovernance = Get-JsonObject -Path $installedRuntimeGovernancePath -Label 'installed vibe governance'
    if ($null -ne $installedRuntimeGovernance -and $installedRuntimeGovernance.PSObject.Properties.Name -contains 'packaging' -and $null -ne $installedRuntimeGovernance.packaging) {
      $packaging = $installedRuntimeGovernance.packaging
      $mirror = if ($packaging.PSObject.Properties.Name -contains 'mirror' -and $null -ne $packaging.mirror) { $packaging.mirror } else { $null }
      $mirrorDirs = if ($null -ne $mirror -and $mirror.PSObject.Properties.Name -contains 'directories') { @($mirror.directories | ForEach-Object { [string]$_ }) } else { @() }
      $allowBundledOnly = if ($packaging.PSObject.Properties.Name -contains 'allow_bundled_only') { @($packaging.allow_bundled_only | ForEach-Object { [string]$_ }) } else { @() }
      if ('references' -notin $mirrorDirs -and 'references/release-ledger.jsonl' -notin $allowBundledOnly) {
        $runtimeReleaseLedgerRequired = $false
      }
    }
  }
  if ($runtimeReleaseLedgerRequired) {
    Check-Path -Label "vibe release ledger" -Path (Join-Path $RuntimeSkillRoot 'references\release-ledger.jsonl')
  } else {
    Check-Condition -Label "vibe release ledger skipped (not packaged into installed runtime contract)" -Condition $true
  }

  function Resolve-SkillDescriptorPath {
    param([string]$SkillName)
    $publicPath = Join-Path $TargetRoot "skills\$SkillName\SKILL.md"
    if (Test-Path -LiteralPath $publicPath -PathType Leaf) {
      return $publicPath
    }
    $hiddenRuntimeMirror = Join-Path $RuntimeSkillRoot "bundled\skills\$SkillName\SKILL.runtime-mirror.md"
    if (Test-Path -LiteralPath $hiddenRuntimeMirror -PathType Leaf) {
      return $hiddenRuntimeMirror
    }
    return (Join-Path $RuntimeSkillRoot "bundled\skills\$SkillName\SKILL.md")
  }

  foreach ($name in $requiredSkills) {
    Check-Path -Label "skill/$name" -Path (Resolve-SkillDescriptorPath -SkillName $name)
  }

  Check-Path -Label "vibe router script" -Path (Join-Path $RuntimeSkillRoot 'scripts\router\resolve-pack-route.ps1')
  Check-Path -Label "vibe memory governance config" -Path (Join-Path $RuntimeSkillRoot 'config\memory-governance.json')
  Check-Path -Label "vibe data scale overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\data-scale-overlay.json')
  Check-Path -Label "vibe quality debt overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\quality-debt-overlay.json')
  Check-Path -Label "vibe framework interop overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\framework-interop-overlay.json')
  Check-Path -Label "vibe ml lifecycle overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\ml-lifecycle-overlay.json')
  Check-Path -Label "vibe python clean code overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\python-clean-code-overlay.json')
  Check-Path -Label "vibe system design overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\system-design-overlay.json')
  Check-Path -Label "vibe cuda kernel overlay config" -Path (Join-Path $RuntimeSkillRoot 'config\cuda-kernel-overlay.json')
  Check-Path -Label "vibe observability policy config" -Path (Join-Path $RuntimeSkillRoot 'config\observability-policy.json')
  Check-Path -Label "vibe heartbeat policy config" -Path (Join-Path $RuntimeSkillRoot 'config\heartbeat-policy.json')
  Check-Path -Label "vibe deep discovery policy config" -Path (Join-Path $RuntimeSkillRoot 'config\deep-discovery-policy.json')
  Check-Path -Label "vibe llm acceleration policy config" -Path (Join-Path $RuntimeSkillRoot 'config\llm-acceleration-policy.json')
  Check-Path -Label "vibe capability catalog config" -Path (Join-Path $RuntimeSkillRoot 'config\capability-catalog.json')
  Check-Path -Label "vibe retrieval policy config" -Path (Join-Path $RuntimeSkillRoot 'config\retrieval-policy.json')
  Check-Path -Label "vibe retrieval intent profiles config" -Path (Join-Path $RuntimeSkillRoot 'config\retrieval-intent-profiles.json')
  Check-Path -Label "vibe retrieval source registry config" -Path (Join-Path $RuntimeSkillRoot 'config\retrieval-source-registry.json')
  Check-Path -Label "vibe retrieval rerank weights config" -Path (Join-Path $RuntimeSkillRoot 'config\retrieval-rerank-weights.json')
  Check-Path -Label "vibe exploration policy config" -Path (Join-Path $RuntimeSkillRoot 'config\exploration-policy.json')
  Check-Path -Label "vibe exploration intent profiles config" -Path (Join-Path $RuntimeSkillRoot 'config\exploration-intent-profiles.json')
  Check-Path -Label "vibe exploration domain map config" -Path (Join-Path $RuntimeSkillRoot 'config\exploration-domain-map.json')
  if ($NestedBundledRequired) {
    Check-Path -Label "vibe bundled retrieval intent profiles config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\retrieval-intent-profiles.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled retrieval source registry config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\retrieval-source-registry.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled retrieval rerank weights config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\retrieval-rerank-weights.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled exploration policy config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\exploration-policy.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled exploration intent profiles config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\exploration-intent-profiles.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled exploration domain map config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\exploration-domain-map.json') -Required:$NestedBundledRequired
    Check-Path -Label "vibe bundled llm acceleration policy config" -Path (Join-Path $RuntimeNestedSkillRoot 'config\llm-acceleration-policy.json') -Required:$NestedBundledRequired
    Check-PathAbsent -Label "vibe nested bundled skill entrypoint hidden" -Path (Join-Path $RuntimeNestedSkillRoot 'SKILL.md')
    Check-Path -Label "vibe nested bundled skill runtime mirror" -Path (Join-Path $RuntimeNestedSkillRoot 'SKILL.runtime-mirror.md') -Required:$NestedBundledRequired
  } else {
    Write-Host ("[OK] vibe nested bundled config checks skipped (target absent; policy={0})" -f $NestedBundledPresencePolicy)
    $script:pass++
  }

  foreach ($name in $requiredWorkflow) {
    Check-Path -Label "workflow skill/$name" -Path (Resolve-SkillDescriptorPath -SkillName $name)
  }

  if ($Profile -eq 'full') {
    foreach ($name in $optionalWorkflow) {
      Check-Path -Label "optional workflow skill/$name" -Path (Resolve-SkillDescriptorPath -SkillName $name) -Required:$false
    }
  }

  if ([string]$Adapter.id -eq 'codex' -and [string]$Adapter.check_mode -eq 'governed' -and $Profile -eq 'full') {
    foreach ($name in (Get-ProjectedSkillNamesForCheck -TargetRoot $TargetRoot -Profile $Profile -ProjectionName 'compatibility_skill_projections' -HostId $HostId)) {
      Check-Path -Label "skill/$name" -Path (Resolve-SkillDescriptorPath -SkillName $name)
    }
  }

  if ([string]$Adapter.id -eq 'opencode') {
    foreach ($name in @('vibe', 'vibe-implement', 'vibe-review')) {
      Check-Path -Label "opencode command/$name" -Path (Join-Path (Join-Path $TargetRoot 'commands') "$name.md")
      Check-Path -Label "opencode compat command/$name" -Path (Join-Path (Join-Path $TargetRoot 'command') "$name.md")
    }
    foreach ($name in @('vibe-plan', 'vibe-implement', 'vibe-review')) {
      Check-Path -Label "opencode agent/$name" -Path (Join-Path (Join-Path $TargetRoot 'agents') "$name.md")
      Check-Path -Label "opencode compat agent/$name" -Path (Join-Path (Join-Path $TargetRoot 'agent') "$name.md")
    }
    Check-Path -Label 'opencode preview config example' -Path (Join-Path $TargetRoot 'opencode.json.example')
  }

  if ([string]$Adapter.id -eq 'codex' -and [string]$Adapter.check_mode -eq 'governed') {
    $codexCommandNames = Get-ProjectedSkillNamesForCheck -TargetRoot $TargetRoot -Profile $Profile -ProjectionName 'public_skill_surface' -HostId $HostId
    foreach ($name in $codexCommandNames) {
      Check-Path -Label "codex command/$name" -Path (Join-Path (Join-Path $TargetRoot 'commands') "$name.md") -Required:$false
    }
  }
}

Write-Host "=== VCO Adapter Health Check ===" -ForegroundColor Cyan
$startupGovernance = Get-CheckGovernance -RepoRoot $RepoRoot
$startupRuntimeConfig = Get-InstalledRuntimeConfig -Governance $startupGovernance
$targetContext = Resolve-CheckTargetContext -InputRoot $TargetRoot -RuntimeConfig $startupRuntimeConfig
$TargetRoot = [string]$targetContext.target_root
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId
$startupRuntimeTargetRel = [string]$targetContext.target_relpath

Write-Host "Host: $HostId"
Write-Host "Mode: $($Adapter.check_mode)"
Write-Host "Target: $TargetRoot"
Write-Host "SkipRuntimeFreshnessGate: $SkipRuntimeFreshnessGate"
Write-Host "Deep: $Deep"

$runtimeSkillRoot = [string]$targetContext.installed_root
$runtimeNestedSkillRoot = Join-Path $runtimeSkillRoot 'bundled\skills\vibe'
$runtimeNestedSkillRootExists = Test-Path -LiteralPath $runtimeNestedSkillRoot
$nestedBundledPresencePolicy = 'optional'
$nestedBundledRequired = $false
if ($startupRuntimeConfig.PSObject.Properties.Name -contains 'require_nested_bundled_root') {
  $nestedBundledRequired = [bool]$startupRuntimeConfig.require_nested_bundled_root
}
if ($null -ne $startupGovernance -and $startupGovernance.PSObject.Properties.Name -contains 'mirror_topology' -and $null -ne $startupGovernance.mirror_topology) {
  $topology = $startupGovernance.mirror_topology
  if ($topology.PSObject.Properties.Name -contains 'targets' -and $null -ne $topology.targets) {
    $nestedBundledTarget = $topology.targets | Where-Object { [string]$_.id -eq 'nested_bundled' } | Select-Object -First 1
    if ($null -ne $nestedBundledTarget) {
      if ($nestedBundledTarget.PSObject.Properties.Name -contains 'presence_policy' -and -not [string]::IsNullOrWhiteSpace([string]$nestedBundledTarget.presence_policy)) {
        $nestedBundledPresencePolicy = [string]$nestedBundledTarget.presence_policy
      }
      if (($nestedBundledTarget.PSObject.Properties.Name -contains 'required' -and [bool]$nestedBundledTarget.required) -or $nestedBundledPresencePolicy -eq 'required') {
        $nestedBundledRequired = $true
      }
    }
  }
}

Invoke-AdapterSpecificChecks -Adapter $Adapter -TargetRoot $TargetRoot -HostId $HostId -RuntimeSkillRoot $runtimeSkillRoot -RuntimeNestedSkillRoot $runtimeNestedSkillRoot -NestedBundledRequired:$nestedBundledRequired -NestedBundledPresencePolicy $nestedBundledPresencePolicy
Check-CodexDuplicateSkillSurface -TargetRoot $TargetRoot -HostId $HostId

Invoke-RuntimeFreshnessCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot -SkipGate:$SkipRuntimeFreshnessGate
Invoke-RuntimeFrontmatterCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot
Invoke-RuntimeCoherenceCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot

if ($Adapter.check_mode -eq 'governed' -and (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Host "[OK] npm"
  $pass++
} elseif ($Adapter.check_mode -eq 'governed') {
  Write-Host "[WARN] npm not found (needed for claude-flow)" -ForegroundColor Yellow
  $warn++
} else {
  Write-Host "[OK] npm check skipped for non-governed adapter mode"
  $pass++
}

if ($Deep) {
  if ($Adapter.check_mode -eq 'governed' -or $HostId -eq 'claude-code') {
    $doctorPath = Join-Path $RepoRoot 'scripts\verify\vibe-bootstrap-doctor-gate.ps1'
    if (-not (Test-Path -LiteralPath $doctorPath)) {
      Write-Host "[FAIL] vibe bootstrap doctor gate script -> $doctorPath" -ForegroundColor Red
      $fail++
    } else {
      $doctorExitCode = Invoke-RuntimeNeutralBootstrapDoctor -RepoRoot $RepoRoot -TargetRoot $TargetRoot
      if ($doctorExitCode -eq 127) {
        $global:LASTEXITCODE = 0
        & $doctorPath -TargetRoot $TargetRoot -WriteArtifacts
        $doctorExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
      }
      if ($doctorExitCode -eq 0) {
        Write-Host '[OK] vibe bootstrap doctor gate'
        $pass++
      } else {
        Write-Host '[FAIL] vibe bootstrap doctor gate' -ForegroundColor Red
        $fail++
      }
    }
  } else {
    Write-Host "[WARN] deep doctor skipped for adapter mode '$($Adapter.check_mode)' on host '$HostId'" -ForegroundColor Yellow
    $warn++
  }
}

Write-Host ""
Write-Host "Result: $pass passed, $fail failed, $warn warnings"
if ($fail -gt 0) { exit 1 }
