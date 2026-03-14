param(
  [ValidateSet("minimal", "full")]
  [string]$Profile = "full",
  [string]$TargetRoot = '',
  [switch]$SkipRuntimeFreshnessGate,
  [switch]$Deep
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $RepoRoot 'scripts\common\vibe-governance-helpers.ps1')
if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
  $TargetRoot = Resolve-VgoTargetRoot
}

function Test-CanonicalRepoExecution {
  param([string]$RepoRoot)
  return (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))
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

function Format-OptionalValue {
  param([string]$Value)

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return '<missing>'
  }

  return $Value
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

  $receiptVersionValue = if ($receipt.PSObject.Properties.Name -contains 'receipt_version') { [int]$receipt.receipt_version } else { 0 }
  $expectedReceiptContractVersion = if ($RuntimeConfig.PSObject.Properties.Name -contains 'receipt_contract_version') { [int]$RuntimeConfig.receipt_contract_version } else { 1 }
  Check-Condition -Label 'vibe runtime freshness receipt version' -Condition ($receiptVersionValue -ge $expectedReceiptContractVersion) -FailureDetail ([string]$receiptVersionValue)

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
  if (-not [string]::IsNullOrWhiteSpace($receiptRel)) {
    Check-Path -Label 'vibe runtime freshness receipt' -Path (Join-Path $TargetRoot $receiptRel)
    Test-ReceiptTargetFreshness -TargetRoot $TargetRoot -RuntimeConfig $runtimeConfig
  }

  if ($SkipGate) {
    Write-Host '[WARN] runtime freshness gate skipped by request.' -ForegroundColor Yellow
    $script:warn++
    return
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

Write-Host "=== VCO Codex Health Check ===" -ForegroundColor Cyan
Write-Host "Target: $TargetRoot"
Write-Host "SkipRuntimeFreshnessGate: $SkipRuntimeFreshnessGate"
Write-Host "Deep: $Deep"

Check-Path -Label "settings.json" -Path (Join-Path $TargetRoot 'settings.json')
Check-Path -Label "plugins manifest" -Path (Join-Path $TargetRoot 'config\plugins-manifest.codex.json')
Check-Path -Label "upstream lock" -Path (Join-Path $TargetRoot 'config\upstream-lock.json')
$startupGovernance = Get-CheckGovernance -RepoRoot $RepoRoot
$startupRuntimeConfig = Get-InstalledRuntimeConfig -Governance $startupGovernance
$startupRuntimeTargetRel = [string]$startupRuntimeConfig.target_relpath
if ([string]::IsNullOrWhiteSpace($startupRuntimeTargetRel)) {
  $startupRuntimeTargetRel = 'skills/vibe'
}

$runtimeSkillRoot = Join-Path $TargetRoot $startupRuntimeTargetRel
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
    $nestedBundledTarget = @($topology.targets | Where-Object { [string]$_.id -eq 'nested_bundled' } | Select-Object -First 1)[0]
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

Check-Path -Label "vibe version governance config" -Path (Join-Path $TargetRoot (Join-Path $startupRuntimeTargetRel 'config\version-governance.json'))
Check-Path -Label "vibe release ledger" -Path (Join-Path $runtimeSkillRoot 'references\release-ledger.jsonl')

foreach ($name in $requiredSkills) {
  Check-Path -Label "skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md")
}

Check-Path -Label "vibe router script" -Path (Join-Path $runtimeSkillRoot 'scripts\router\resolve-pack-route.ps1')
Check-Path -Label "vibe memory governance config" -Path (Join-Path $runtimeSkillRoot 'config\memory-governance.json')
Check-Path -Label "vibe data scale overlay config" -Path (Join-Path $runtimeSkillRoot 'config\data-scale-overlay.json')
Check-Path -Label "vibe quality debt overlay config" -Path (Join-Path $runtimeSkillRoot 'config\quality-debt-overlay.json')
Check-Path -Label "vibe framework interop overlay config" -Path (Join-Path $runtimeSkillRoot 'config\framework-interop-overlay.json')
Check-Path -Label "vibe ml lifecycle overlay config" -Path (Join-Path $runtimeSkillRoot 'config\ml-lifecycle-overlay.json')
Check-Path -Label "vibe python clean code overlay config" -Path (Join-Path $runtimeSkillRoot 'config\python-clean-code-overlay.json')
Check-Path -Label "vibe system design overlay config" -Path (Join-Path $runtimeSkillRoot 'config\system-design-overlay.json')
Check-Path -Label "vibe cuda kernel overlay config" -Path (Join-Path $runtimeSkillRoot 'config\cuda-kernel-overlay.json')
Check-Path -Label "vibe observability policy config" -Path (Join-Path $runtimeSkillRoot 'config\observability-policy.json')
Check-Path -Label "vibe heartbeat policy config" -Path (Join-Path $runtimeSkillRoot 'config\heartbeat-policy.json')
Check-Path -Label "vibe deep discovery policy config" -Path (Join-Path $runtimeSkillRoot 'config\deep-discovery-policy.json')
Check-Path -Label "vibe llm acceleration policy config" -Path (Join-Path $runtimeSkillRoot 'config\llm-acceleration-policy.json')
Check-Path -Label "vibe capability catalog config" -Path (Join-Path $runtimeSkillRoot 'config\capability-catalog.json')
Check-Path -Label "vibe retrieval policy config" -Path (Join-Path $runtimeSkillRoot 'config\retrieval-policy.json')
Check-Path -Label "vibe retrieval intent profiles config" -Path (Join-Path $runtimeSkillRoot 'config\retrieval-intent-profiles.json')
Check-Path -Label "vibe retrieval source registry config" -Path (Join-Path $runtimeSkillRoot 'config\retrieval-source-registry.json')
Check-Path -Label "vibe retrieval rerank weights config" -Path (Join-Path $runtimeSkillRoot 'config\retrieval-rerank-weights.json')
Check-Path -Label "vibe exploration policy config" -Path (Join-Path $runtimeSkillRoot 'config\exploration-policy.json')
Check-Path -Label "vibe exploration intent profiles config" -Path (Join-Path $runtimeSkillRoot 'config\exploration-intent-profiles.json')
Check-Path -Label "vibe exploration domain map config" -Path (Join-Path $runtimeSkillRoot 'config\exploration-domain-map.json')
if ($nestedBundledRequired) {
  Check-Path -Label "vibe bundled retrieval intent profiles config" -Path (Join-Path $runtimeNestedSkillRoot 'config\retrieval-intent-profiles.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled retrieval source registry config" -Path (Join-Path $runtimeNestedSkillRoot 'config\retrieval-source-registry.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled retrieval rerank weights config" -Path (Join-Path $runtimeNestedSkillRoot 'config\retrieval-rerank-weights.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled exploration policy config" -Path (Join-Path $runtimeNestedSkillRoot 'config\exploration-policy.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled exploration intent profiles config" -Path (Join-Path $runtimeNestedSkillRoot 'config\exploration-intent-profiles.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled exploration domain map config" -Path (Join-Path $runtimeNestedSkillRoot 'config\exploration-domain-map.json') -Required:$nestedBundledRequired
  Check-Path -Label "vibe bundled llm acceleration policy config" -Path (Join-Path $runtimeNestedSkillRoot 'config\llm-acceleration-policy.json') -Required:$nestedBundledRequired
} else {
  Write-Host ("[OK] vibe nested bundled config checks skipped (target absent; policy={0})" -f $nestedBundledPresencePolicy)
  $script:pass++
}

foreach ($name in $requiredWorkflow) {
  Check-Path -Label "workflow skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md")
}

if ($Profile -eq 'full') {
  foreach ($name in $optionalWorkflow) {
    Check-Path -Label "optional workflow skill/$name" -Path (Join-Path $TargetRoot "skills\$name\SKILL.md") -Required:$false
  }
}

Check-Path -Label "rules/common" -Path (Join-Path $TargetRoot 'rules\common\agents.md')
Check-Path -Label "hooks/write-guard.js" -Path (Join-Path $TargetRoot 'hooks\write-guard.js')
Check-Path -Label "mcp template" -Path (Join-Path $TargetRoot 'mcp\servers.template.json')

Invoke-RuntimeFreshnessCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot -SkipGate:$SkipRuntimeFreshnessGate
Invoke-RuntimeFrontmatterCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot
Invoke-RuntimeCoherenceCheck -RepoRoot $RepoRoot -TargetRoot $TargetRoot

if (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host "[OK] npm"
  $pass++
} else {
  Write-Host "[WARN] npm not found (needed for claude-flow)" -ForegroundColor Yellow
  $warn++
}

if ($Deep) {
  $doctorPath = Join-Path $RepoRoot 'scripts\verify\vibe-bootstrap-doctor-gate.ps1'
  if (-not (Test-Path -LiteralPath $doctorPath)) {
    Write-Host "[FAIL] vibe bootstrap doctor gate script -> $doctorPath" -ForegroundColor Red
    $fail++
  } else {
    $global:LASTEXITCODE = 0
    & $doctorPath -TargetRoot $TargetRoot -WriteArtifacts
    $doctorExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($doctorExitCode -eq 0) {
      Write-Host '[OK] vibe bootstrap doctor gate'
      $pass++
    } else {
      Write-Host '[FAIL] vibe bootstrap doctor gate' -ForegroundColor Red
      $fail++
    }
  }
}

Write-Host ""
Write-Host "Result: $pass passed, $fail failed, $warn warnings"
if ($fail -gt 0) { exit 1 }
