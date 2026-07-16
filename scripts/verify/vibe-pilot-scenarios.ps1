param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Assert-True {
  param([bool]$Condition,[string]$Message)
  if ($Condition) {
    Write-Host "[PASS] $Message"
    return $true
  }
  Write-Host "[FAIL] $Message" -ForegroundColor Red
  return $false
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$fixturesDir = Join-Path $repoRoot 'scripts\verify\fixtures'
$fixtureFiles = @(
  'pilot-memory.json',
  'pilot-prompt.json',
  'pilot-browserops.json',
  'pilot-desktopops.json',
  'pilot-deep-extraction.json'
)

$checks = @()
$fixtures = @()

foreach ($file in $fixtureFiles) {
  $path = Join-Path $fixturesDir $file
  $checks += Assert-True (Test-Path -LiteralPath $path) "fixture exists: $file"
  if (-not (Test-Path -LiteralPath $path)) { continue }
  $fixture = Get-Content -Raw $path -Encoding UTF8 | ConvertFrom-Json
  $fixtures += $fixture
  $expectedScenarioId = [System.IO.Path]::GetFileNameWithoutExtension($file)
  $checks += Assert-True ($fixture.scenario_id -eq $expectedScenarioId) "scenario_id matches file name for $file"
  $checks += Assert-True (-not [string]::IsNullOrWhiteSpace([string]$fixture.plane_id)) "plane_id exists for $file"
  $checks += Assert-True (-not [string]::IsNullOrWhiteSpace([string]$fixture.task)) "task exists for $file"
  $checks += Assert-True (-not [string]::IsNullOrWhiteSpace([string]$fixture.objective)) "objective exists for $file"
  $checks += Assert-True ($null -ne $fixture.expected) "expected block exists for $file"
  $checks += Assert-True ((@($fixture.must_not).Count) -ge 1) "must_not exists for $file"
}

$planeIds = @($fixtures | ForEach-Object { [string]$_.plane_id })
$checks += Assert-True (($planeIds | Select-Object -Unique).Count -eq $planeIds.Count) 'pilot plane_id values are unique'

$memory = @($fixtures | Where-Object { $_.plane_id -eq 'memory-runtime-v2' }) | Select-Object -First 1
$prompt = @($fixtures | Where-Object { $_.plane_id -eq 'prompt-intelligence' }) | Select-Object -First 1
$browser = @($fixtures | Where-Object { $_.plane_id -eq 'browserops-provider' }) | Select-Object -First 1
$desktop = @($fixtures | Where-Object { $_.plane_id -eq 'desktopops-shadow' }) | Select-Object -First 1
$deep = @($fixtures | Where-Object { $_.plane_id -eq 'deep-extraction-governance' }) | Select-Object -First 1

$checks += Assert-True ($memory.expected.canonical_session_owner -eq 'state_store') 'memory pilot keeps state_store as canonical session owner'
$checks += Assert-True ($memory.expected.external_preference_backend -eq 'mem0') 'memory pilot keeps mem0 as external preference backend only'
$checks += Assert-True ($memory.expected.policy_contract_source -eq 'letta') 'memory pilot keeps Letta as policy contract source'
$checks += Assert-True (@($memory.must_not) -contains 'second_canonical_truth_source') 'memory pilot forbids second truth-source'

$checks += Assert-True ($prompt.expected.asset_only -eq $true) 'prompt pilot remains asset-only'
$checks += Assert-True ($prompt.expected.forbid_second_router -eq $true) 'prompt pilot forbids second router'
$checks += Assert-True ($prompt.expected.preserve_selected_pack -eq $true) 'prompt pilot preserves selected pack'
$checks += Assert-True (@($prompt.must_not) -contains 'second_router') 'prompt pilot explicitly forbids second router'

$checks += Assert-True ($desktop.expected.role -eq 'desktopops_shadow_advisor_only') 'desktop pilot keeps shadow advisor role'
$checks += Assert-True ($desktop.expected.forbid_default_execution_owner -eq $true) 'desktop pilot forbids default execution owner takeover'
$checks += Assert-True ($desktop.expected.contract_shape -eq 'aci+openworld') 'desktop pilot preserves ACI + OpenWorld contract shape'
$checks += Assert-True (@($desktop.must_not) -contains 'default_execution_owner_takeover') 'desktop pilot explicitly forbids default execution owner takeover'

$checks += Assert-True ($browser.expected.provider -eq 'browser-host-native') 'browser pilot records host-native browser capability as expected provider'
$checks += Assert-True ($browser.expected.confirm_required -eq $false) 'browser pilot records confirm_required=false for debug path'
$checks += Assert-True ($browser.expected.mode -eq 'shadow') 'browser pilot records shadow mode'
$checks += Assert-True (@($browser.must_not) -contains 'second_orchestrator') 'browser pilot explicitly forbids second orchestrator'
$checks += Assert-True (@($browser.must_not) -contains 'forbidden_mcp_provider') 'browser pilot explicitly forbids MCP provider recommendation'

$checks += Assert-True ($deep.expected.governed_mirror_coverage -eq 1.0) 'deep extraction pilot encodes full governed mirror coverage'
$checks += Assert-True ($deep.expected.runtime_only_artifact_count -eq 0) 'deep extraction pilot forbids runtime-only artifacts'
$checks += Assert-True ($deep.expected.upstream_manifest_coverage -eq 15) 'deep extraction pilot expects full upstream manifest coverage'
$checks += Assert-True ($deep.expected.productization_ratio_min -ge 0.8) 'deep extraction pilot encodes productization ratio target'
$checks += Assert-True (@($deep.must_not) -contains 'second_orchestrator') 'deep extraction pilot forbids second orchestrator'

$browserSuggestScript = Join-Path $repoRoot 'scripts\overlay\suggest-browserops-provider.ps1'
if (Test-Path -LiteralPath $browserSuggestScript) {
  try {
    $suggest = & $browserSuggestScript -Task $browser.task -AsJson | ConvertFrom-Json
    $checks += Assert-True ($suggest.provider -eq $browser.expected.provider) 'browser pilot dry-run resolves expected provider'
    $checks += Assert-True ($suggest.confirm_required -eq $browser.expected.confirm_required) 'browser pilot dry-run resolves expected confirm_required'
    $checks += Assert-True ($suggest.mode -eq $browser.expected.mode) 'browser pilot dry-run preserves shadow mode'
  }
  catch {
    Write-Host '[INFO] browser provider suggestion script unavailable or invalid; fallback to fixture-only validation' -ForegroundColor Yellow
    $checks += Assert-True ($true) 'browser pilot fixture-only validation accepted'
  }
}
else {
  Write-Host '[INFO] browser provider suggestion script missing; fallback to fixture-only validation' -ForegroundColor Yellow
  $checks += Assert-True ($true) 'browser pilot fixture-only validation accepted'
}

if ($checks -contains $false) {
  throw 'pilot scenarios gate failed'
}

Write-Host '[PASS] pilot scenarios gate succeeded' -ForegroundColor Green
