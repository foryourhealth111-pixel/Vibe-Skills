param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-router-offline-degrade-contract-gate.json'
    $mdPath = Join-Path $dir 'vibe-router-offline-degrade-contract-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Router Offline Degrade Contract Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Tested providers: `{0}`' -f $Artifact.summary.tested_provider_count),
        ('- Failure count: `{0}`' -f $Artifact.summary.failure_count),
        '',
        '## Defaults Contract',
        '',
        ('- default_runtime_state: `{0}`' -f $Artifact.results.defaults.default_runtime_state),
        ('- fallback_provider_mode: `{0}`' -f $Artifact.results.defaults.fallback_provider_mode),
        ('- offline_frozen_enabled: `{0}`' -f $Artifact.results.defaults.offline_frozen_enabled),
        '',
        '## Provider Offline Tests',
        ''
    )

    foreach ($p in @($Artifact.results.providers)) {
        $lines += ('- `{0}` module=`{1}` expected_reason=`{2}` ok=`{3}` observed_reason=`{4}`' -f $p.id, $p.module_relpath, $p.expected_reason, $p.ok, $p.observed_reason)
    }

    if (@($Artifact.results.failures).Count -gt 0) {
        $lines += ''
        $lines += '## Failures'
        $lines += ''
        foreach ($f in @($Artifact.results.failures)) {
            $lines += ('- {0}' -f $f)
        }
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

function Require-File {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Failures
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        [void]$Failures.Add("missing_required_file:$Path")
        return $false
    }
    return $true
}

function Remove-ProcessEnvVar {
    param([Parameter(Mandatory)][string]$Name)
    if (Test-Path -LiteralPath ("env:{0}" -f $Name)) {
        Remove-Item -LiteralPath ("env:{0}" -f $Name) -ErrorAction SilentlyContinue
    }
}

function Set-ProcessEnvVar {
    param(
        [Parameter(Mandatory)][string]$Name,
        [AllowNull()][string]$Value
    )
    if ($null -eq $Value) {
        Remove-ProcessEnvVar -Name $Name
        return
    }
    Set-Item -LiteralPath ("env:{0}" -f $Name) -Value $Value
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot

$registryPath = Join-Path $repoRoot 'config\router-provider-registry.json'
$defaultsPath = Join-Path $repoRoot 'config\router-provider-defaults.json'

$failures = New-Object System.Collections.Generic.List[string]
$requiredOk = $true
$requiredOk = (Require-File -Path $registryPath -Failures $failures) -and $requiredOk
$requiredOk = (Require-File -Path $defaultsPath -Failures $failures) -and $requiredOk

$registry = $null
$defaults = $null
if ($requiredOk) {
    try { $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { [void]$failures.Add("invalid_json:$registryPath") }
    try { $defaults = Get-Content -LiteralPath $defaultsPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { [void]$failures.Add("invalid_json:$defaultsPath") }
}

if ($defaults) {
    if ([string]$defaults.policy -ne 'router-provider-layer-defaults') { [void]$failures.Add('defaults_policy_mismatch') }
    if ([string]$defaults.default_runtime_state -ne 'heuristic-only') { [void]$failures.Add('default_runtime_state_must_be_heuristic_only') }
    if ([string]$defaults.fallback_provider_mode -ne 'heuristic-only') { [void]$failures.Add('fallback_provider_mode_must_be_heuristic_only') }
    if (-not ($defaults.offline_frozen_mode -and [bool]$defaults.offline_frozen_mode.enabled)) { [void]$failures.Add('offline_frozen_mode_enabled_required') }
}

if ($registry) {
    if ([string]$registry.policy -ne 'router-provider-registry') { [void]$failures.Add('registry_policy_mismatch') }
    $authorityScript = if ($registry.canonical_router_authority -and $registry.canonical_router_authority.script_relpath) { [string]$registry.canonical_router_authority.script_relpath } else { '' }
    if ($authorityScript -ne 'scripts/router/resolve-pack-route.ps1') { [void]$failures.Add('canonical_authority_script_mismatch') }
    if (-not [bool]($registry.canonical_router_authority -and $registry.canonical_router_authority.provider_layer_advice_only)) {
        [void]$failures.Add('provider_layer_must_be_advice_only')
    }
}

$providerResults = @()
if ($registry -and @($registry.providers).Count -gt 0) {
    foreach ($p in @($registry.providers)) {
        if (-not $p) { continue }
        $id = [string]$p.id
        $moduleRel = [string]$p.module_relpath

        $offline = $p.offline_contract
        $expectedReason = if ($offline -and $offline.abstain_reason) { [string]$offline.abstain_reason } else { '' }
        $requiredEnvAny = @()
        try { $requiredEnvAny = @($offline.required_env_any) } catch { $requiredEnvAny = @() }
        $noNetwork = $false
        try { $noNetwork = [bool]$offline.no_network_without_credentials } catch { $noNetwork = $false }

        $result = [ordered]@{
            id = $id
            module_relpath = $moduleRel
            expected_reason = $expectedReason
            ok = $true
            observed_reason = $null
            observed_abstained = $null
        }

        $shouldTestOffline = ($requiredEnvAny.Count -gt 0) -and $noNetwork -and ($expectedReason -notin @('not_applicable', ''))
        if (-not $shouldTestOffline) {
            $providerResults += [pscustomobject]$result
            continue
        }

        if ([string]::IsNullOrWhiteSpace($moduleRel)) {
            [void]$failures.Add(("provider_missing_module_relpath:{0}" -f $id))
            $result.ok = $false
            $providerResults += [pscustomobject]$result
            continue
        }

        $moduleFull = ConvertTo-VgoFullPath -BasePath $repoRoot -RelativePath $moduleRel
        if (-not (Test-Path -LiteralPath $moduleFull)) {
            [void]$failures.Add(("provider_module_missing:{0}:{1}" -f $id, $moduleRel))
            $result.ok = $false
            $providerResults += [pscustomobject]$result
            continue
        }

        $envSnapshot = @{}
        foreach ($name in @($requiredEnvAny)) {
            $n = [string]$name
            if ([string]::IsNullOrWhiteSpace($n)) { continue }
            $envSnapshot[$n] = if (Test-Path -LiteralPath ("env:{0}" -f $n)) { [string](Get-Item -LiteralPath ("env:{0}" -f $n)).Value } else { $null }
        }

        # Also clear common base url overrides so offline tests never depend on host/user configs.
        foreach ($name in @('OPENAI_BASE_URL', 'OPENAI_API_BASE')) {
            if (-not $envSnapshot.ContainsKey($name)) {
                $envSnapshot[$name] = if (Test-Path -LiteralPath ("env:{0}" -f $name)) { [string](Get-Item -LiteralPath ("env:{0}" -f $name)).Value } else { $null }
            }
        }

        try {
            foreach ($name in @($envSnapshot.Keys)) {
                Remove-ProcessEnvVar -Name $name
            }

            . $moduleFull

            $invokeOk = $false
            $call = $null
            if ($moduleRel -like '*scripts/router/modules/01-openai-responses.ps1') {
                if (-not (Get-Command -Name Invoke-OpenAiResponsesCreate -ErrorAction SilentlyContinue)) {
                    throw "expected Invoke-OpenAiResponsesCreate to be available after dot-sourcing: $moduleRel"
                }
                $call = Invoke-OpenAiResponsesCreate -Model 'gpt-4.1-mini' -InputItems @() -TextFormat @{ type = 'text' } -TimeoutMs 1
                $invokeOk = $true
            }

            if (-not $invokeOk) {
                [void]$failures.Add(("offline_test_mapping_missing_for_module:{0}:{1}" -f $id, $moduleRel))
                $result.ok = $false
            } else {
                $result.observed_reason = if ($call -and $call.reason) { [string]$call.reason } else { $null }
                $result.observed_abstained = if ($call -and $call.abstained -ne $null) { [bool]$call.abstained } else { $null }

                if (-not ($call -and [bool]$call.abstained)) {
                    [void]$failures.Add(("offline_test_expected_abstained_true:{0}:{1}" -f $id, $moduleRel))
                    $result.ok = $false
                }
                if ([string]$result.observed_reason -ne $expectedReason) {
                    [void]$failures.Add(("offline_test_reason_mismatch:{0}:{1}:expected={2}:observed={3}" -f $id, $moduleRel, $expectedReason, $result.observed_reason))
                    $result.ok = $false
                }
            }
        } catch {
            [void]$failures.Add(("offline_test_exception:{0}:{1}:{2}" -f $id, $moduleRel, $_.Exception.Message))
            $result.ok = $false
        } finally {
            foreach ($name in @($envSnapshot.Keys)) {
                Set-ProcessEnvVar -Name $name -Value $envSnapshot[$name]
            }
        }

        $providerResults += [pscustomobject]$result
    }
}

$gateResult = if ($failures.Count -eq 0) { 'PASS' } else { 'FAIL' }
$testedProviders = @($providerResults | Where-Object { $_.expected_reason -and $_.expected_reason -notin @('not_applicable') })
$artifact = [pscustomobject]@{
    gate = 'vibe-router-offline-degrade-contract-gate'
    repo_root = $repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = $gateResult
    summary = [pscustomobject]@{
        tested_provider_count = [int]$testedProviders.Count
        failure_count = [int]$failures.Count
    }
    results = [pscustomobject]@{
        defaults = [pscustomobject]@{
            default_runtime_state = if ($defaults) { [string]$defaults.default_runtime_state } else { '' }
            fallback_provider_mode = if ($defaults) { [string]$defaults.fallback_provider_mode } else { '' }
            offline_frozen_enabled = if ($defaults -and $defaults.offline_frozen_mode) { [bool]$defaults.offline_frozen_mode.enabled } else { $false }
        }
        providers = @($providerResults)
        failures = @($failures)
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failures.Count -gt 0) { exit 1 }
