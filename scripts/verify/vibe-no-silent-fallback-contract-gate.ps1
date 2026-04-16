param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Add-Assertion {
    param(
        [System.Collections.Generic.List[object]]$Assertions,
        [bool]$Pass,
        [string]$Message,
        [object]$Details = $null
    )

    $Assertions.Add([pscustomobject]@{
        pass = [bool]$Pass
        message = $Message
        details = $Details
    }) | Out-Null

    Write-Host ("[{0}] {1}" -f $(if ($Pass) { 'PASS' } else { 'FAIL' }), $Message) -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
}

function Invoke-SupportedHostRuntimeTruthProbe {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RuntimeEntrypointPath,
        [Parameter(Mandatory)] [string]$HostId,
        [Parameter(Mandatory)] [System.Collections.Generic.List[object]]$Assertions
    )

    $runId = "no-silent-fallback-$HostId-" + [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $artifactRoot = Join-Path $RepoRoot (".tmp\vibe-no-silent-fallback-{0}" -f $runId)
    $previousHostId = $env:VCO_HOST_ID
    $previousDisableNative = $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION
    $previousEnableNative = $env:VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION

    try {
        $env:VCO_HOST_ID = $HostId
        $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION = '1'
        $env:VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION = '0'

        $summary = & $RuntimeEntrypointPath `
            -Task "Verify canonical vibe proof-chain truth for host $HostId. `$vibe" `
            -Mode interactive_governed `
            -RunId $runId `
            -ArtifactRoot $artifactRoot

        $runtimeInputPacketPath = [string]$summary.summary.artifacts.runtime_input_packet
        $executionManifestPath = [string]$summary.summary.artifacts.execution_manifest
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $runtimeInputPacketPath) -Message "$HostId runtime emits runtime-input-packet artifact" -Details $runtimeInputPacketPath
        Add-Assertion -Assertions $Assertions -Pass (Test-Path -LiteralPath $executionManifestPath) -Message "$HostId runtime emits execution-manifest artifact" -Details $executionManifestPath

        if (-not (Test-Path -LiteralPath $runtimeInputPacketPath) -or -not (Test-Path -LiteralPath $executionManifestPath)) {
            return
        }

        $runtimeInput = Get-Content -LiteralPath $runtimeInputPacketPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $executionManifest = Get-Content -LiteralPath $executionManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

        Add-Assertion -Assertions $Assertions -Pass ($runtimeInput.PSObject.Properties.Name -contains 'route_snapshot') -Message "$HostId runtime-input-packet contains route_snapshot"
        Add-Assertion -Assertions $Assertions -Pass ($runtimeInput.route_snapshot -and [string]$runtimeInput.route_snapshot.selected_skill -eq 'vibe') -Message "$HostId route_snapshot keeps vibe as selected_skill"
        Add-Assertion -Assertions $Assertions -Pass ($runtimeInput.PSObject.Properties.Name -contains 'specialist_dispatch') -Message "$HostId runtime-input-packet contains specialist_dispatch artifact"
        Add-Assertion -Assertions $Assertions -Pass ($runtimeInput.PSObject.Properties.Name -contains 'specialist_recommendations') -Message "$HostId runtime-input-packet contains specialist_recommendations artifact"
        Add-Assertion -Assertions $Assertions -Pass (@($runtimeInput.specialist_recommendations).Count -ge 1) -Message "$HostId runtime-input-packet preserves specialist recommendation evidence"

        Add-Assertion -Assertions $Assertions -Pass ($executionManifest.PSObject.Properties.Name -contains 'specialist_accounting') -Message "$HostId execution-manifest contains specialist_accounting artifact"
        Add-Assertion -Assertions $Assertions -Pass ($executionManifest.specialist_accounting.PSObject.Properties.Name -contains 'effective_execution_status') -Message "$HostId specialist_accounting records effective_execution_status"
    }
    finally {
        if ([string]::IsNullOrWhiteSpace($previousHostId)) {
            Remove-Item Env:VCO_HOST_ID -ErrorAction SilentlyContinue
        } else {
            $env:VCO_HOST_ID = $previousHostId
        }
        if ([string]::IsNullOrWhiteSpace($previousDisableNative)) {
            Remove-Item Env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION -ErrorAction SilentlyContinue
        } else {
            $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION = $previousDisableNative
        }
        if ([string]::IsNullOrWhiteSpace($previousEnableNative)) {
            Remove-Item Env:VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION -ErrorAction SilentlyContinue
        } else {
            $env:VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION = $previousEnableNative
        }
        if (-not $WriteArtifacts -and (Test-Path -LiteralPath $artifactRoot)) {
            Remove-Item -LiteralPath $artifactRoot -Recurse -Force
        }
    }
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir 'vibe-no-silent-fallback-contract-gate.json'
    $mdPath = Join-Path $dir 'vibe-no-silent-fallback-contract-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO No Silent Fallback Contract Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failure count: `{0}`' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )

    foreach ($assertion in @($Artifact.assertions)) {
        $lines += ('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$assertions = [System.Collections.Generic.List[object]]::new()

$runtimeContractPath = Join-Path $repoRoot 'config\runtime-contract.json'
$fallbackPolicyPath = Join-Path $repoRoot 'config\fallback-governance.json'
$routerGovernancePath = Join-Path $repoRoot 'config\router-model-governance.json'
$skillPath = Join-Path $repoRoot 'SKILL.md'
$runtimeProtocolPath = Join-Path $repoRoot 'protocols\runtime.md'
$truthGatePath = Join-Path $repoRoot 'scripts\verify\vibe-canonical-entry-truth-gate.ps1'
$routeScriptPath = Join-Path $repoRoot 'scripts\router\resolve-pack-route.ps1'
$runtimeEntrypointPath = Get-VgoRuntimeEntrypointPath -RepoRoot $repoRoot -RuntimeConfig $context.runtimeConfig

$runtimeContract = Get-Content -LiteralPath $runtimeContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$fallbackPolicy = Get-Content -LiteralPath $fallbackPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$routerGovernance = Get-Content -LiteralPath $routerGovernancePath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillText = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
$runtimeProtocol = Get-Content -LiteralPath $runtimeProtocolPath -Raw -Encoding UTF8
$truthGate = Get-Content -LiteralPath $truthGatePath -Raw -Encoding UTF8

Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.no_silent_fallback) -Message 'runtime contract encodes no_silent_fallback'
Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.no_silent_degradation) -Message 'runtime contract encodes no_silent_degradation'
Add-Assertion -Assertions $assertions -Pass ([bool]$runtimeContract.invariants.fallback_hazard_alert_required) -Message 'runtime contract requires fallback hazard alert'
Add-Assertion -Assertions $assertions -Pass (-not [bool]$fallbackPolicy.silent_fallback) -Message 'fallback policy forbids silent fallback'
Add-Assertion -Assertions $assertions -Pass (-not [bool]$fallbackPolicy.silent_degradation) -Message 'fallback policy forbids silent degradation'
Add-Assertion -Assertions $assertions -Pass ([bool]$fallbackPolicy.require_hazard_alert) -Message 'fallback policy requires hazard alert'
Add-Assertion -Assertions $assertions -Pass ([string]$routerGovernance.provider_neutral_contract.degrade_honesty.fallback_truth_level -eq 'non_authoritative') -Message 'router governance maps degraded fallback truth to non_authoritative'
Add-Assertion -Assertions $assertions -Pass ([bool]$routerGovernance.hard_rules.must_emit_hazard_alert_for_fallback) -Message 'router governance requires fallback hazard alert'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('Silent fallback and silent degradation are forbidden.')) -Message 'runtime protocol documents no silent fallback'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('route_snapshot')) -Message 'runtime protocol requires route_snapshot evidence'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('specialist dispatch accounting')) -Message 'runtime protocol requires specialist dispatch accounting evidence'
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $truthGatePath) -Message 'canonical truth gate script exists' -Details $truthGatePath
Add-Assertion -Assertions $assertions -Pass ($truthGate.Contains('host-launch-receipt.json')) -Message 'canonical truth gate requires host-launch-receipt.json'
Add-Assertion -Assertions $assertions -Pass ($truthGate.Contains('reading SKILL.md alone is not canonical vibe entry')) -Message 'canonical truth gate rejects SKILL.md-only activation claims'
Add-Assertion -Assertions $assertions -Pass ($skillText.Contains('Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry.')) -Message 'SKILL.md documents that prose-only activation is not proof of canonical vibe entry'
Add-Assertion -Assertions $assertions -Pass ($runtimeProtocol.Contains('Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry.')) -Message 'runtime protocol documents that prose-only activation is not proof of canonical vibe entry'

$route = & $routeScriptPath -Prompt 'help me with this' -Grade 'M' -TaskType 'research' | ConvertFrom-Json
Add-Assertion -Assertions $assertions -Pass ([bool]$route.fallback_active) -Message 'low-signal route marks fallback_active'
Add-Assertion -Assertions $assertions -Pass ([bool]$route.hazard_alert_required) -Message 'low-signal route requires hazard alert'
Add-Assertion -Assertions $assertions -Pass ([string]$route.truth_level -eq 'non_authoritative') -Message 'low-signal route truth_level is non_authoritative'
Add-Assertion -Assertions $assertions -Pass ([string]$route.degradation_state -in @('fallback_active', 'fallback_guarded')) -Message 'low-signal route records fallback degradation state'
Add-Assertion -Assertions $assertions -Pass ($route.hazard_alert -and [string]$route.hazard_alert.title -eq 'FALLBACK HAZARD ALERT') -Message 'low-signal route emits fallback hazard alert object'
Add-Assertion -Assertions $assertions -Pass (
    $route.confirm_ui -and
    [string]$route.confirm_ui.rendered_text -match 'FALLBACK HAZARD ALERT'
) -Message 'confirm UI renders standalone fallback hazard alert'

foreach ($hostId in @('codex', 'claude-code', 'opencode')) {
    Invoke-SupportedHostRuntimeTruthProbe -RepoRoot $repoRoot -RuntimeEntrypointPath $runtimeEntrypointPath -HostId $hostId -Assertions $assertions
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$artifact = [pscustomobject]@{
    gate = 'vibe-no-silent-fallback-contract-gate'
    repo_root = $repoRoot
    gate_result = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [pscustomobject]@{
        failure_count = $failureCount
        route_mode = if ($route) { [string]$route.route_mode } else { '' }
        route_reason = if ($route) { [string]$route.route_reason } else { '' }
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
