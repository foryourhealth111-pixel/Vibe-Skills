param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'

function Add-Check {
    param(
        [string]$CheckId,
        [bool]$Condition,
        [string]$Message,
        [object]$Path,
        [object]$Expected,
        [object]$Actual
    )

    $result = [pscustomobject]@{
        check_id = $CheckId
        passed = $Condition
        message = $Message
        path = $Path
        expected = $Expected
        actual = $Actual
    }
    $script:checks.Add($result) | Out-Null
    $prefix = if ($Condition) { 'PASS' } else { 'FAIL' }
    $color = if ($Condition) { 'Green' } else { 'Red' }
    Write-Host ('[{0}][{1}] {2}' -f $prefix, $CheckId, $Message) -ForegroundColor $color
}

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Require-File {
    param([string]$RelativePath)
    $path = Join-Path $script:repoRoot $RelativePath
    $exists = Test-Path -LiteralPath $path
    Add-Check -CheckId ('exists:' + $RelativePath.Replace('\','/')) -Condition $exists -Message ('required file exists: {0}' -f $RelativePath) -Path $path -Expected 'present' -Actual $(if ($exists) { 'present' } else { 'missing' })
    return $path
}

function Test-MarkdownSections {
    param(
        [string]$Path,
        [string[]]$RequiredPatterns,
        [string]$CheckPrefix
    )

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    foreach ($pattern in $RequiredPatterns) {
        Add-Check -CheckId ('{0}:{1}' -f $CheckPrefix, $pattern) -Condition ($content -match $pattern) -Message ('markdown section/pattern present: {0}' -f $pattern) -Path $Path -Expected $pattern -Actual 'content scanned'
    }
}

function New-MarkdownReport {
    param([object]$Report)
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# Wave15-18 Consistency Gate')
    $lines.Add('')
    $lines.Add(('- Generated: {0}' -f $Report.generated_at))
    $lines.Add(('- Assertions: `{0}`' -f $Report.summary.assertions))
    $lines.Add(('- Passed: `{0}`' -f $Report.summary.passed))
    $lines.Add(('- Failed: `{0}`' -f $Report.summary.failed))
    $lines.Add('')
    $lines.Add('## Checks')
    $lines.Add('')
    foreach ($check in $Report.checks.ToArray()) {
        $state = if ($check.passed) { 'PASS' } else { 'FAIL' }
        $lines.Add(('- `{0}` `{1}` — {2}' -f $state, $check.check_id, $check.message))
    }
    return ($lines -join [Environment]::NewLine)
}

$script:repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $script:repoRoot 'outputs\verify'
}
$script:checks = New-Object System.Collections.Generic.List[object]

$requiredFiles = @(
    'config\candidate-watch-decisions.json',
    'config\eval-slicing-policy.json',
    'config\skill-intake-priority.json',
    'config\xl-operator-checkpoints.json',
    'config\watch-lane-priority-bands.json',
    'docs\watch-portfolio-rationalization.md',
    'docs\eval-slicing-operationalization.md',
    'docs\xl-operator-playbook.md',
    'docs\wave15-18-execution-backlog.md',
    'docs\watch-lane-remaining-value-cases.md',
    'references\promotion-memos\wave15-18-promotion-prep.md',
    'docs\releases\wave15-18-release-packet.md'
)

$fileMap = @{}
foreach ($file in $requiredFiles) {
    $fileMap[$file] = Require-File -RelativePath $file
}

$watchPath = $fileMap['config\candidate-watch-decisions.json']
$bandPath = $fileMap['config\watch-lane-priority-bands.json']
$evalPath = $fileMap['config\eval-slicing-policy.json']
$priorityPath = $fileMap['config\skill-intake-priority.json']
$checkpointPath = $fileMap['config\xl-operator-checkpoints.json']

if (Test-Path -LiteralPath $watchPath) {
    $watch = Read-JsonFile -Path $watchPath
    $watchCandidates = @($watch.candidates)
    Add-Check -CheckId 'watch:candidate-count' -Condition ($watchCandidates.Count -eq 8) -Message 'watch decisions keep 8-candidate baseline' -Path $watchPath -Expected 8 -Actual $watchCandidates.Count
    Add-Check -CheckId 'watch:no-default-expansion' -Condition (@($watchCandidates | Where-Object { $_.default_surface_change }).Count -eq 0) -Message 'watch decisions preserve no-default-expansion rule' -Path $watchPath -Expected '0 true values' -Actual (@($watchCandidates | Where-Object { $_.default_surface_change }).Count)
}

if ((Test-Path -LiteralPath $watchPath) -and (Test-Path -LiteralPath $bandPath)) {
    $watch = Read-JsonFile -Path $watchPath
    $bands = Read-JsonFile -Path $bandPath
    $watchIds = @($watch.candidates | Select-Object -ExpandProperty id)
    $mappedIds = @($bands.candidate_band_map.PSObject.Properties.Name)
    $missingMap = @($watchIds | Where-Object { $mappedIds -notcontains $_ })
    Add-Check -CheckId 'watch:band-map-complete' -Condition ($missingMap.Count -eq 0) -Message 'every watch candidate has a watch-lane priority band' -Path $bandPath -Expected 'all watch candidate ids mapped' -Actual ($missingMap -join ', ')
}

if (Test-Path -LiteralPath $evalPath) {
    $eval = Read-JsonFile -Path $evalPath
    $planes = @($eval.slices | Select-Object -ExpandProperty plane -Unique)
    Add-Check -CheckId 'eval:plane-coverage' -Condition (@('prompt','tool','team','portfolio' | Where-Object { $planes -contains $_ }).Count -eq 4) -Message 'eval slicing covers prompt/tool/team/portfolio planes' -Path $evalPath -Expected 'prompt, tool, team, portfolio' -Actual ($planes -join ', ')
    Add-Check -CheckId 'eval:no-default-expansion' -Condition (@($eval.slices | Where-Object { $_.default_surface_change }).Count -eq 0) -Message 'eval slices remain reporting-only' -Path $evalPath -Expected '0 true values' -Actual (@($eval.slices | Where-Object { $_.default_surface_change }).Count)
}

if (Test-Path -LiteralPath $priorityPath) {
    $priority = Read-JsonFile -Path $priorityPath
    Add-Check -CheckId 'intake:band-count' -Condition (@($priority.bands).Count -ge 4) -Message 'skill intake policy keeps at least four priority bands' -Path $priorityPath -Expected '>= 4' -Actual (@($priority.bands).Count)
}

if (Test-Path -LiteralPath $checkpointPath) {
    $checkpoint = Read-JsonFile -Path $checkpointPath
    Add-Check -CheckId 'checkpoint:min-count' -Condition (@($checkpoint.checkpoints).Count -ge 5) -Message 'XL operator policy keeps at least five checkpoints' -Path $checkpointPath -Expected '>= 5' -Actual (@($checkpoint.checkpoints).Count)
}

Test-MarkdownSections -Path $fileMap['docs\watch-portfolio-rationalization.md'] -RequiredPatterns @('review-ready', 'pilot', 'hold', '不扩大默认面|default surface') -CheckPrefix 'doc:watch'
Test-MarkdownSections -Path $fileMap['docs\eval-slicing-operationalization.md'] -RequiredPatterns @('shadow', 'default surface', 'slice') -CheckPrefix 'doc:eval'
Test-MarkdownSections -Path $fileMap['docs\xl-operator-playbook.md'] -RequiredPatterns @('checkpoint', 'board-handoff', 'verification') -CheckPrefix 'doc:xl'
Test-MarkdownSections -Path $fileMap['docs\wave15-18-execution-backlog.md'] -RequiredPatterns @('Wave15', 'Wave16', 'Wave17', 'Wave18', 'rollback') -CheckPrefix 'doc:backlog'
Test-MarkdownSections -Path $fileMap['docs\watch-lane-remaining-value-cases.md'] -RequiredPatterns @('high-yield-advisory', 'gated-pilot-only', 'hold-until-gap') -CheckPrefix 'doc:cases'
Test-MarkdownSections -Path $fileMap['references\promotion-memos\wave15-18-promotion-prep.md'] -RequiredPatterns @('decision_context', 'candidate_snapshot', 'dedup_review', 'rubric_summary', 'routing_impact', 'verification', 'rollback') -CheckPrefix 'doc:memo'
Test-MarkdownSections -Path $fileMap['docs\releases\wave15-18-release-packet.md'] -RequiredPatterns @('change-summary', 'evidence', 'gate-results', 'owner-and-landing-zone', 'degraded-mode', 'rollback-plan', 'retro-trigger') -CheckPrefix 'doc:packet'

$termCorpus = @()
foreach ($path in @($fileMap.Values)) {
    if (Test-Path -LiteralPath $path) {
        $termCorpus += (Get-Content -LiteralPath $path -Raw -Encoding UTF8)
    }
}
$joined = $termCorpus -join "`n"
foreach ($term in @('active', 'watch', 'hold', 'pilot', 'review-ready', 'rollback-ready')) {
    Add-Check -CheckId ('term:' + $term) -Condition ($joined -match [regex]::Escape($term)) -Message ('decision term appears somewhere in the artifact set: {0}' -f $term) -Path 'artifact corpus' -Expected $term -Actual 'content scanned'
}
Add-Check -CheckId 'corpus:no-default-expansion' -Condition ($joined -match '不扩大默认面|default surface expansion') -Message 'artifact corpus explicitly preserves no-default-expansion constraint' -Path 'artifact corpus' -Expected 'guardrail language' -Actual 'content scanned'

$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    summary = [pscustomobject]@{
        assertions = $script:checks.Count
        passed = @($script:checks | Where-Object { $_.passed }).Count
        failed = @($script:checks | Where-Object { -not $_.passed }).Count
    }
    checks = $script:checks
}

$report | ConvertTo-Json -Depth 8

if ($WriteArtifacts) {
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $jsonPath = Join-Path $OutputDirectory 'wave15-18-consistency-gate.json'
    $mdPath = Join-Path $OutputDirectory 'wave15-18-consistency-gate.md'
    ($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    (New-MarkdownReport -Report $report) | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host ('Wrote {0}' -f $jsonPath) -ForegroundColor Green
    Write-Host ('Wrote {0}' -f $mdPath) -ForegroundColor Green
}

if (@($script:checks | Where-Object { -not $_.passed }).Count -gt 0) {
    exit 1
}

