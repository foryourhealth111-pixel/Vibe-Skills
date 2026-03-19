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

    Write-Host ('[{0}] {1}' -f $(if ($Pass) { 'PASS' } else { 'FAIL' }), $Message) -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
}

function Write-GateArtifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [psobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { Join-Path $RepoRoot 'outputs\verify' } else { $OutputDirectory }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    $jsonPath = Join-Path $dir 'vibe-runtime-boundary-gate.json'
    $mdPath = Join-Path $dir 'vibe-runtime-boundary-gate.md'
    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Runtime Boundary Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Failure Count: {0}' -f $Artifact.summary.failure_count),
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

$paths = [ordered]@{
    runtime = Join-Path $repoRoot 'protocols\runtime.md'
    think = Join-Path $repoRoot 'protocols\think.md'
    skill = Join-Path $repoRoot 'bundled\skills\vibe\SKILL.md'
    bridge = '/home/lqf/table/table3/docs/architecture/evcode-host-runtime-bridge.md'
}

foreach ($entry in $paths.GetEnumerator()) {
    Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $entry.Value) -Message ("required runtime-boundary asset exists: {0}" -f $entry.Key) -Details $entry.Value
}

$runtimeRaw = Get-Content -LiteralPath $paths.runtime -Raw -Encoding UTF8
$thinkRaw = Get-Content -LiteralPath $paths.think -Raw -Encoding UTF8
$skillRaw = Get-Content -LiteralPath $paths.skill -Raw -Encoding UTF8
$bridgeRaw = Get-Content -LiteralPath $paths.bridge -Raw -Encoding UTF8

Add-Assertion -Assertions $assertions -Pass ($runtimeRaw.Contains('superpowers and similar process layers: workflow discipline only')) -Message 'runtime protocol preserves discipline-only status for process layers'
Add-Assertion -Assertions $assertions -Pass ($runtimeRaw.Contains('a second requirement truth surface')) -Message 'runtime protocol forbids a second requirement truth surface'
Add-Assertion -Assertions $assertions -Pass ($runtimeRaw.Contains('a second plan truth surface')) -Message 'runtime protocol forbids a second plan truth surface'

Add-Assertion -Assertions $assertions -Pass ($thinkRaw.Contains('must not create a second requirement or plan truth')) -Message 'think protocol rejects second requirement/plan truth'
Add-Assertion -Assertions $assertions -Pass ($thinkRaw.Contains('VCO remains the only governed runtime skeleton')) -Message 'think protocol preserves VCO as sole governed runtime skeleton'

Add-Assertion -Assertions $assertions -Pass ($skillRaw.Contains('Compatibility With Process Layers')) -Message 'vibe skill exposes process-layer compatibility section'
Add-Assertion -Assertions $assertions -Pass ($skillRaw.Contains('second visible startup/runtime prompt surface')) -Message 'vibe skill forbids second visible startup/runtime prompt surface'
Add-Assertion -Assertions $assertions -Pass ($skillRaw.Contains('second execution-plan surface')) -Message 'vibe skill forbids second execution-plan surface'

Add-Assertion -Assertions $assertions -Pass ($bridgeRaw.Contains('This hook must not emit a visible startup prompt.')) -Message 'bridge doc preserves no-visible-startup-prompt rule'
Add-Assertion -Assertions $assertions -Pass ($bridgeRaw.Contains('EvCode does not create a second router.')) -Message 'bridge doc preserves no-second-router rule'
Add-Assertion -Assertions $assertions -Pass ($bridgeRaw.Contains('second visible entry or plan surface')) -Message 'bridge doc forbids second visible entry / plan surface'

$failureCount = @($assertions | Where-Object { -not $_.pass }).Count
$gateResult = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
$artifact = [pscustomobject]@{
    gate = 'vibe-runtime-boundary-gate'
    repo_root = $repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = $gateResult
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
