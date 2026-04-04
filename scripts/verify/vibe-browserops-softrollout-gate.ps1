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

        $jsonPath = Join-Path $dir 'vibe-browserops-softrollout-gate.json'
        $mdPath = Join-Path $dir 'vibe-browserops-softrollout-gate.md'
        Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

        $lines = @(
            '# VCO BrowserOps Soft Rollout Gate',
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
    $requiredPaths = @(
    'docs/governance/browserops-soft-rollout-governance.md',
    'config/browserops-provider-policy.json',
    'config/browserops-scorecard.json'
)
    foreach ($relPath in $requiredPaths) {
        $fullPath = Join-Path $repoRoot $relPath
        Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $fullPath) -Message ('required asset exists: ' + $relPath) -Details $fullPath
    }

    $keywordChecks = @(
    [pscustomobject]@{ path = 'docs/governance/browserops-soft-rollout-governance.md'; keywords = @(
    'BrowserOps Soft Rollout Governance',
    'candidate_soft_only',
    'fallback'
) },
    [pscustomobject]@{ path = 'config/browserops-provider-policy.json'; keywords = @(
    'browser-use',
    'candidate_only',
    'fallback_provider'
) },
    [pscustomobject]@{ path = 'config/browserops-scorecard.json'; keywords = @(
    'telemetry_readiness',
    'manual_confirm_required'
) }
)
    foreach ($check in $keywordChecks) {
        $targetPath = Join-Path $repoRoot $check.path
        if (-not (Test-Path -LiteralPath $targetPath)) {
            continue
        }
        $raw = Get-Content -LiteralPath $targetPath -Raw -Encoding UTF8
        foreach ($keyword in @($check.keywords)) {
            Add-Assertion -Assertions $assertions -Pass ($raw.Contains($keyword)) -Message ('keyword present in ' + $check.path + ': ' + $keyword) -Details $keyword
        }
    }

    $failureCount = @($assertions | Where-Object { -not $_.pass }).Count
    $gateResult = if ($failureCount -eq 0) { 'PASS' } else { 'FAIL' }
    $artifact = [pscustomobject]@{
        gate = 'vibe-browserops-softrollout-gate'
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
