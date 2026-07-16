param(
    [switch]$Json,
    [switch]$WriteArtifacts,
    [AllowEmptyString()] [string]$RepoRoot = '',
    [AllowEmptyString()] [string]$ArtifactRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function ConvertTo-RepoRelativePath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Root
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    if ($pathFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        if ($pathFull.Length -eq $rootFull.Length) {
            return ''
        }
        $boundary = $pathFull[$rootFull.Length]
        if ($boundary -eq [System.IO.Path]::DirectorySeparatorChar -or $boundary -eq [System.IO.Path]::AltDirectorySeparatorChar) {
            return $pathFull.Substring($rootFull.Length).TrimStart('\', '/').Replace('\', '/')
        }
    }
    return $pathFull.Replace('\', '/')
}

function Test-PathPrefix {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [string[]]$Prefixes
    )

    $normalized = $Path.Replace('\', '/').TrimStart('/')
    foreach ($prefix in $Prefixes) {
        $candidate = [string]$prefix
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        $candidate = $candidate.Replace('\', '/').TrimEnd('/')
        if ($normalized.Equals($candidate, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
        if ($normalized.StartsWith($candidate + '/', [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-TextFiles {
    param(
        [Parameter(Mandatory)] [string]$Root,
        [Parameter(Mandatory)] [object]$Policy
    )

    $extensions = @('.ps1', '.py', '.json', '.md', '.sh', '.yaml', '.yml', '.toml')
    $excluded = @($Policy.scan_scopes.excluded_roots | ForEach-Object { [string]$_ })
    $currentPaths = @($Policy.scan_scopes.current_paths | ForEach-Object { [string]$_ })
    $files = New-Object System.Collections.Generic.List[object]
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($relative in $currentPaths) {
        $full = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $full)) {
            throw "Configured current_paths entry not found: $relative ($full)"
        }

        if (Test-Path -LiteralPath $full -PathType Leaf) {
            $item = Get-Item -LiteralPath $full
            $repoRelative = ConvertTo-RepoRelativePath -Path $item.FullName -Root $Root
            if (($extensions -contains $item.Extension.ToLowerInvariant()) -and -not (Test-PathPrefix -Path $repoRelative -Prefixes $excluded) -and $seen.Add($item.FullName)) {
                $files.Add($item) | Out-Null
            }
            continue
        }
        if (-not (Test-Path -LiteralPath $full -PathType Container)) {
            throw "Configured current_paths entry is neither a file nor a directory: $relative ($full)"
        }
        foreach ($file in Get-ChildItem -LiteralPath $full -Recurse -File) {
            $repoRelative = ConvertTo-RepoRelativePath -Path $file.FullName -Root $Root
            if (Test-PathPrefix -Path $repoRelative -Prefixes $excluded) {
                continue
            }
            if (($extensions -contains $file.Extension.ToLowerInvariant()) -and $seen.Add($file.FullName)) {
                $files.Add($file) | Out-Null
            }
        }
    }

    return @($files.ToArray() | Sort-Object FullName)
}

function Get-LineCommentAndStringFragments {
    param([Parameter(Mandatory)] [string]$Line)

    $fragments = New-Object System.Collections.Generic.List[object]
    $buffer = [System.Text.StringBuilder]::new()
    $singleQuote = [char]39
    $doubleQuote = [char]34
    $hash = [char]35
    $inString = $false
    $quoteChar = [char]0

    for ($i = 0; $i -lt $Line.Length; $i++) {
        $character = $Line[$i]
        if ($inString) {
            if ($character -eq $quoteChar) {
                if ($quoteChar -eq $singleQuote -and ($i + 1) -lt $Line.Length -and $Line[$i + 1] -eq $singleQuote) {
                    [void]$buffer.Append($Line[$i + 1])
                    $i += 1
                    continue
                }
                $fragments.Add([pscustomobject]@{ kind = 'string'; text = $buffer.ToString() }) | Out-Null
                $buffer.Clear() | Out-Null
                $inString = $false
                $quoteChar = [char]0
                continue
            }
            [void]$buffer.Append($character)
            continue
        }

        if ($character -eq $hash) {
            $fragments.Add([pscustomobject]@{ kind = 'comment'; text = $Line.Substring($i) }) | Out-Null
            break
        }
        if ($character -eq $singleQuote -or $character -eq $doubleQuote) {
            $inString = $true
            $quoteChar = $character
            $buffer.Clear() | Out-Null
        }
    }

    if ($inString -and $buffer.Length -gt 0) {
        $fragments.Add([pscustomobject]@{ kind = 'string'; text = $buffer.ToString() }) | Out-Null
    }

    return @($fragments.ToArray())
}

function Test-LineIsGuardAssertion {
    param([Parameter(Mandatory)] [string]$Line)

    $trimmed = $Line.TrimStart()
    if ($trimmed -match '(?i)^assert\s+.+\s+not\s+in\s+') {
        return $true
    }
    foreach ($needle in @('assertNotIn', 'self.assertNotIn', 'assertNotRegex')) {
        if ($Line.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }
    foreach ($fragment in @(Get-LineCommentAndStringFragments -Line $Line)) {
        $fragmentText = [string]$fragment.text
        foreach ($needle in @('assert "not in"', 'assertNotIn', 'self.assertNotIn', 'assertNotRegex', 'assert.NotIn')) {
            if ($fragmentText.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                return $true
            }
        }
    }
    return $false
}

function Test-LineIsRetiredExplanation {
    param([Parameter(Mandatory)] [string]$Line)

    $commentNeedles = @('retired', 'historical', 'legacy', 'old terms', 'old fields', 'not current', 'cleanup target', 'debt target', 'forbidden', 'do not')
    $stringNeedles = @('retired', 'historical', 'legacy compatibility', 'legacy field', 'legacy terms', 'old terms', 'old fields', 'not current', 'cleanup target', 'debt target', 'forbidden', 'do not')
    foreach ($fragment in @(Get-LineCommentAndStringFragments -Line $Line)) {
        $fragmentText = [string]$fragment.text
        $needles = if ([string]$fragment.kind -eq 'comment') { $commentNeedles } else { $stringNeedles }
        foreach ($needle in $needles) {
            if ($fragmentText.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                return $true
            }
        }
    }
    return $false
}

function Test-LineIsCurrentResolutionEnum {
    param([Parameter(Mandatory)] [string]$Line)

    return ($Line.IndexOf('no_specialist_recommendations', [System.StringComparison]::OrdinalIgnoreCase) -ge 0)
}

function Test-PolicyOrGateFile {
    param([Parameter(Mandatory)] [string]$RelativePath)

    $normalized = $RelativePath.Replace('\', '/')
    return (
        $normalized -eq 'config/current-routing-debt-erasure.json' -or
        $normalized -eq 'config/routing-terminology-hard-cleanup.json' -or
        $normalized -eq 'scripts/verify/vibe-current-routing-debt-gate.ps1' -or
        $normalized -eq 'scripts/verify/vibe-current-routing-contract-scan.ps1' -or
        $normalized -eq 'scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1' -or
        $normalized -eq 'tests/runtime_neutral/test_current_routing_debt_gate.py' -or
        $normalized -eq 'tests/runtime_neutral/test_current_routing_debt_erasure_policy.py'
    )
}

function Get-CurrentLayer {
    param([Parameter(Mandatory)] [string]$RelativePath)

    if ($RelativePath.StartsWith('scripts/runtime/', [System.StringComparison]::OrdinalIgnoreCase)) { return 'current_runtime' }
    if ($RelativePath.StartsWith('scripts/router/', [System.StringComparison]::OrdinalIgnoreCase)) { return 'current_router' }
    if ($RelativePath.StartsWith('packages/runtime-core/', [System.StringComparison]::OrdinalIgnoreCase)) { return 'runtime_core' }
    if ($RelativePath.StartsWith('tests/', [System.StringComparison]::OrdinalIgnoreCase)) { return 'current_tests' }
    if ($RelativePath.StartsWith('docs/', [System.StringComparison]::OrdinalIgnoreCase) -or $RelativePath -eq 'SKILL.md' -or $RelativePath.StartsWith('protocols/', [System.StringComparison]::OrdinalIgnoreCase)) { return 'current_docs' }
    return 'current_config_or_verify'
}

function New-DebtFinding {
    param(
        [Parameter(Mandatory)] [string]$Term,
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [int]$Line,
        [Parameter(Mandatory)] [string]$Category,
        [Parameter(Mandatory)] [string]$Layer,
        [Parameter(Mandatory)] [string]$Decision,
        [Parameter(Mandatory)] [string]$Reason,
        [Parameter(Mandatory)] [string]$SuggestedFix,
        [Parameter(Mandatory)] [string]$Text
    )

    [pscustomobject]@{
        term = $Term
        path = $Path
        line = $Line
        category = $Category
        current_layer = $Layer
        decision = $Decision
        reason = $Reason
        suggested_fix = $SuggestedFix
        text = $Text.Trim()
    }
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = [string]$context.repoRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
    $ArtifactRoot = $RepoRoot
}
else {
    $ArtifactRoot = [System.IO.Path]::GetFullPath($ArtifactRoot)
}
$policyPath = Join-Path $RepoRoot 'config\current-routing-debt-erasure.json'
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf)) {
    throw "current routing debt policy not found: $policyPath"
}

$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$retiredTerms = @($policy.retired_terms | ForEach-Object { [string]$_ })
$legacyAllowed = @($policy.scan_scopes.legacy_allowed_paths | ForEach-Object { [string]$_ })
$highRisk = @($policy.high_risk_retired_fields | ForEach-Object { [string]$_ })

$findings = New-Object System.Collections.Generic.List[object]
$legacyAllowedHits = 0
$scannedFiles = @(Get-TextFiles -Root $RepoRoot -Policy $policy)

foreach ($file in $scannedFiles) {
    $relative = ConvertTo-RepoRelativePath -Path $file.FullName -Root $RepoRoot
    $allowedLegacyPath = (Test-PathPrefix -Path $relative -Prefixes $legacyAllowed) -or (Test-PolicyOrGateFile -RelativePath $relative)
    $layer = Get-CurrentLayer -RelativePath $relative
    $lines = @(Get-Content -LiteralPath $file.FullName -Encoding UTF8)
    $insideCodeBlock = $false
    $insideRetiredSection = $false

    for ($index = 0; $index -lt $lines.Count; $index++) {
        $lineText = [string]$lines[$index]
        $trimmedLine = $lineText.Trim()
        if ($relative.EndsWith('.md', [System.StringComparison]::OrdinalIgnoreCase) -and $trimmedLine.StartsWith('```')) {
            $insideCodeBlock = -not $insideCodeBlock
        }
        if ($relative.EndsWith('.md', [System.StringComparison]::OrdinalIgnoreCase) -and -not $insideCodeBlock -and $trimmedLine -match '^##\s+') {
            $insideRetiredSection = ($trimmedLine -match '^##\s+(Retired|Historical|Legacy)')
        }
        foreach ($term in $retiredTerms) {
            if ($lineText.IndexOf($term, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
                continue
            }

            if ($allowedLegacyPath -or $insideRetiredSection -or (Test-LineIsGuardAssertion -Line $lineText) -or (Test-LineIsRetiredExplanation -Line $lineText) -or (Test-LineIsCurrentResolutionEnum -Line $lineText)) {
                $legacyAllowedHits += 1
                continue
            }

            $escapedTerm = [regex]::Escape($term)
            $looksLikeFieldWrite = $lineText -match "(?i)(['`"]?$escapedTerm['`"]?\s*[:=])"
            $category = if ($looksLikeFieldWrite -and $layer -in @('current_runtime', 'current_router', 'runtime_core', 'current_config_or_verify') -and ($highRisk -contains $term)) {
                'P0'
            } elseif ($layer -in @('current_runtime', 'current_router', 'runtime_core') -and ($highRisk -contains $term)) {
                'P1'
            } elseif ($layer -eq 'current_tests') {
                'P1'
            } elseif ($layer -eq 'current_docs') {
                'P2'
            } else {
                'P1'
            }

            $decision = switch ($category) {
                'P1' { 'delete_or_move_to_retired_boundary' }
                'P2' { 'rewrite_or_mark_retired_context' }
                default { 'delete_current_output' }
            }
            $reason = switch ($category) {
                'P1' { 'Retired routing field appears in current code or current tests outside an explicit retired boundary.' }
                'P2' { 'Retired routing term appears in current documentation without a retired-context marker.' }
                default { 'Retired field appears in a current output construction path.' }
            }
            $suggestedFix = switch ($category) {
                'P1' { 'Move the old-field reader or fixture into a legacy/retired file, or rewrite it to current Agent organization and completed module-work fields.' }
                'P2' { 'Rewrite the text to the current Agent organization, module handoff, and module-result model, or mark it as retired history.' }
                default { 'Remove the retired field from current output and assert the field is absent.' }
            }

            $findings.Add((New-DebtFinding -Term $term -Path $relative -Line ($index + 1) -Category $category -Layer $layer -Decision $decision -Reason $reason -SuggestedFix $suggestedFix -Text $lineText)) | Out-Null
        }
    }
}

$summary = [ordered]@{
    P0 = @($findings | Where-Object { $_.category -eq 'P0' }).Count
    P1 = @($findings | Where-Object { $_.category -eq 'P1' }).Count
    P2 = @($findings | Where-Object { $_.category -eq 'P2' }).Count
    P3 = @($findings | Where-Object { $_.category -eq 'P3' }).Count
    legacy_allowed_hits = [int]$legacyAllowedHits
    scanned_file_count = @($scannedFiles).Count
}

$status = if (
    [int]$summary.P0 -le [int]$policy.success_thresholds.P0 -and
    [int]$summary.P1 -le [int]$policy.success_thresholds.P1 -and
    [int]$summary.P2 -le [int]$policy.success_thresholds.P2
) { 'pass' } else { 'fail' }

$report = [pscustomobject]@{
    status = $status
    generated_at = (Get-Date).ToString('s')
    repo_root = $RepoRoot
    policy_path = $policyPath
    current_model = @($policy.current_model)
    current_fields = @($policy.active_fields)
    retired_terms = @($policy.retired_terms)
    summary = [pscustomobject]$summary
    findings = [object[]]$findings.ToArray()
}

if ($WriteArtifacts) {
    $artifactRootPath = [System.IO.Path]::GetFullPath($ArtifactRoot)
    $verifyDir = Join-Path $artifactRootPath 'outputs\verify'
    $auditDir = Join-Path $artifactRootPath 'docs\audits'
    New-Item -ItemType Directory -Force -Path $verifyDir | Out-Null
    New-Item -ItemType Directory -Force -Path $auditDir | Out-Null

    # Keep both filenames: gate consumers read the gate report, while audit
    # consumers use the historical audit JSON path for generated evidence.
    Write-VgoUtf8NoBomText -Path (Join-Path $verifyDir 'current-routing-debt-gate.json') -Content ($report | ConvertTo-Json -Depth 50)
    Write-VgoUtf8NoBomText -Path (Join-Path $verifyDir 'current-routing-debt-audit.json') -Content ($report | ConvertTo-Json -Depth 50)

    $mdLines = @(
        '# Current Routing Debt Audit',
        '',
        ('- Status: **{0}**' -f $status),
        ('- P0 Current Output Pollution: {0}' -f [int]$summary.P0),
        ('- P1 Current Code Dependency: {0}' -f [int]$summary.P1),
        ('- P2 Current Documentation Pollution: {0}' -f [int]$summary.P2),
        ('- Legacy / Retired Allowed Hits: {0}' -f [int]$summary.legacy_allowed_hits),
        '',
        '## Current Model',
        '',
        ('`{0}`' -f (@($policy.current_model) -join ' -> ')),
        '',
        '## Findings',
        ''
    )
    if (@($report.findings).Count -eq 0) {
        $mdLines += '- No blocking P0/P1/P2 findings.'
    } else {
        foreach ($finding in @($report.findings)) {
            $mdLines += ('- `{0}:{1}` [{2}] `{3}` -> {4}' -f $finding.path, $finding.line, $finding.category, $finding.term, $finding.decision)
        }
    }
    $auditStamp = ([string]$report.generated_at).Substring(0, 10)
    $auditFileName = '{0}-current-routing-debt-audit.md' -f $auditStamp
    Write-VgoUtf8NoBomText -Path (Join-Path $auditDir $auditFileName) -Content ($mdLines -join "`r`n")
}

if ($Json) {
    $report | ConvertTo-Json -Depth 50
} else {
    '=== VCO Current Routing Debt Gate ==='
    ('Status: {0}' -f $status)
    ('P0 Current Output Pollution: {0}' -f [int]$summary.P0)
    ('P1 Current Code Dependency: {0}' -f [int]$summary.P1)
    ('P2 Current Documentation Pollution: {0}' -f [int]$summary.P2)
    ('Legacy / Retired Allowed Hits: {0}' -f [int]$summary.legacy_allowed_hits)
    foreach ($finding in @($report.findings)) {
        '[FAIL] {0}:{1} [{2}] {3}' -f $finding.path, $finding.line, $finding.category, $finding.term
    }
}

if ($status -ne 'pass') {
    exit 1
}
exit 0
