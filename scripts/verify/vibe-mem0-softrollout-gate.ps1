param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ''
)

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

    $color = if ($Pass) { 'Green' } else { 'Red' }
    $status = if ($Pass) { 'PASS' } else { 'FAIL' }
    Write-Host ('[{0}] {1}' -f $status, $Message) -ForegroundColor $color
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    $jsonPath = Join-Path $dir 'vibe-mem0-softrollout-gate.json'
    $mdPath = Join-Path $dir 'vibe-mem0-softrollout-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO mem0 Soft Rollout Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failures: {0}' -f $Artifact.summary.failure_count),
        '',
        '## Assertions',
        ''
    )
    foreach ($assertion in $Artifact.assertions) {
        $lines += ('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)
    }
    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$assertions = [System.Collections.Generic.List[object]]::new()

$docPath = Join-Path $repoRoot 'docs/governance/mem0-soft-rollout-governance.md'
$contractPath = Join-Path $repoRoot 'references/mem0-write-admission-contract.md'
$mem0PolicyPath = Join-Path $repoRoot 'config/mem0-backend-policy.json'
$runtimePolicyPath = Join-Path $repoRoot 'config/memory-runtime-v3-policy.json'

foreach ($path in @($docPath, $contractPath, $mem0PolicyPath, $runtimePolicyPath)) {
    Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $path) -Message ('required asset exists: ' + [System.IO.Path]::GetFileName($path)) -Details $path
}

if ((@($assertions | Where-Object { -not $_.pass }).Count) -eq 0) {
    $docText = Get-Content -LiteralPath $docPath -Raw -Encoding UTF8
    $contractText = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8
    $docLower = $docText.ToLowerInvariant()
    $contractLower = $contractText.ToLowerInvariant()

    $mem0 = Get-Content -LiteralPath $mem0PolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $runtime = Get-Content -LiteralPath $runtimePolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json

    Add-Assertion -Assertions $assertions -Pass ($mem0.role -eq 'optional_external_preference_backend') -Message 'mem0 role stays optional_external_preference_backend'
    Add-Assertion -Assertions $assertions -Pass (@('shadow', 'soft') -contains [string]$mem0.mode) -Message 'mem0 mode limited to shadow or soft'
    Add-Assertion -Assertions $assertions -Pass (($mem0.mode -ne 'soft') -or ($mem0.enabled -eq $true)) -Message 'soft mode requires enabled=true'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.allowed_payload_types) -contains 'preference') -Message 'mem0 policy allows preference payloads'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.allowed_payload_types) -contains 'style_hint') -Message 'mem0 policy allows style_hint payloads'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.allowed_payload_types) -contains 'recurring_constraint') -Message 'mem0 policy allows recurring_constraint payloads'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.allowed_payload_types) -contains 'output_preference') -Message 'mem0 policy allows output_preference payloads'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.forbidden_payload_types) -contains 'route_assignment') -Message 'mem0 policy forbids route_assignment writes'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.forbidden_payload_types) -contains 'canonical_project_decision') -Message 'mem0 policy forbids canonical_project_decision writes'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.forbidden_payload_types) -contains 'primary_session_state') -Message 'mem0 policy forbids primary_session_state writes'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.forbidden_payload_types) -contains 'security_secret') -Message 'mem0 policy forbids security_secret writes'
    Add-Assertion -Assertions $assertions -Pass (@($mem0.forbidden_payload_types) -contains 'build_truth') -Message 'mem0 policy forbids build_truth writes'
    Add-Assertion -Assertions $assertions -Pass ($mem0.fallback_behavior.on_missing_backend -eq 'keep_core_memory_owners') -Message 'missing backend preserves core memory owners'
    Add-Assertion -Assertions $assertions -Pass ($mem0.fallback_behavior.on_forbidden_write -eq 'deny_and_report') -Message 'forbidden write falls back to deny_and_report'

    Add-Assertion -Assertions $assertions -Pass ($runtime.extension_planes.mem0.role -eq 'external_preference_backend') -Message 'runtime v3 registers mem0 as external_preference_backend'
    Add-Assertion -Assertions $assertions -Pass (@($runtime.extension_planes.mem0.allowed_modes) -contains 'shadow') -Message 'runtime v3 allows mem0 shadow mode'
    Add-Assertion -Assertions $assertions -Pass (@($runtime.extension_planes.mem0.allowed_modes) -contains 'soft') -Message 'runtime v3 allows mem0 soft mode'
    Add-Assertion -Assertions $assertions -Pass ($runtime.extension_planes.mem0.soft_requires_operator_opt_in -eq $true) -Message 'runtime v3 requires operator opt-in for soft rollout'
    Add-Assertion -Assertions $assertions -Pass ($runtime.extension_planes.mem0.preserve_core_truth_sources -eq $true) -Message 'runtime v3 preserves core truth sources'
    Add-Assertion -Assertions $assertions -Pass ($runtime.extension_planes.mem0.cannot_be_primary -eq $true) -Message 'runtime v3 prevents mem0 from becoming primary'

    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('soft rollout')) -Message 'governance doc names soft rollout'
    Add-Assertion -Assertions $assertions -Pass ($docText.Contains('shadow -> soft')) -Message 'governance doc documents shadow -> soft'
    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('opt-in')) -Message 'governance doc documents opt-in'
    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('kill switch')) -Message 'governance doc documents kill switch'
    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('rollback')) -Message 'governance doc documents rollback'
    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('audit')) -Message 'governance doc documents audit trail'
    Add-Assertion -Assertions $assertions -Pass ($docLower.Contains('advisory-only')) -Message 'governance doc preserves advisory-only fallback'

    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('payload_type')) -Message 'admission contract contains payload_type'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('stability_window')) -Message 'admission contract contains stability_window'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('user_confirmation')) -Message 'admission contract contains user_confirmation'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('evaluation_id')) -Message 'admission contract contains evaluation_id'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('policy_version')) -Message 'admission contract contains policy_version'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('fallback_owner')) -Message 'admission contract contains fallback_owner'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('route_assignment')) -Message 'admission contract rejects route_assignment'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('security_secret')) -Message 'admission contract rejects security_secret'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('build_truth')) -Message 'admission contract rejects build_truth'
    Add-Assertion -Assertions $assertions -Pass ($contractLower.Contains('rollback')) -Message 'admission contract documents rollback behavior'
}

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$gateResult = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
$artifact = [pscustomobject]@{
    gate = 'vibe-mem0-softrollout-gate'
    repo_root = $repoRoot
    gate_result = $gateResult
    generated_at = (Get-Date).ToString('s')
    assertions = @($assertions)
    summary = [ordered]@{
        total = $assertions.Count
        failure_count = $failureCount
    }
}

if ($WriteArtifacts) {
    Write-GateArtifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($failureCount -gt 0) {
    exit 1
}
