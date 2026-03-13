param(
    [switch]$WriteArtifacts,
    [string]$ConfigPath,
    [string]$DocPath,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'

function Add-Check {
    param(
        [string]$CheckId,
        [bool]$Condition,
        [string]$Message,
        [object]$Expected,
        [object]$Actual,
        [object]$Path
    )

    $result = [pscustomobject]@{
        check_id = $CheckId
        passed = $Condition
        message = $Message
        expected = $Expected
        actual = $Actual
        path = $Path
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

function New-MarkdownReport {
    param([object]$Report)
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# Watch Portfolio Gate')
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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
if (-not $ConfigPath) { $ConfigPath = Join-Path $repoRoot 'config\candidate-watch-decisions.json' }
if (-not $DocPath) { $DocPath = Join-Path $repoRoot 'docs\watch-portfolio-rationalization.md' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repoRoot 'outputs\verify' }

$script:checks = New-Object System.Collections.Generic.List[object]
$configExists = Test-Path -LiteralPath $ConfigPath
Add-Check -CheckId 'config-exists' -Condition $configExists -Message 'watch decision config exists' -Expected 'present' -Actual $(if ($configExists) { 'present' } else { 'missing' }) -Path $ConfigPath

$docExists = Test-Path -LiteralPath $DocPath
Add-Check -CheckId 'doc-exists' -Condition $docExists -Message 'watch rationalization doc exists' -Expected 'present' -Actual $(if ($docExists) { 'present' } else { 'missing' }) -Path $DocPath

if ($configExists) {
    $config = Read-JsonFile -Path $ConfigPath
    $candidates = @($config.candidates)
    Add-Check -CheckId 'candidate-count' -Condition ($candidates.Count -eq 8) -Message 'exactly eight watch candidates recorded' -Expected 8 -Actual $candidates.Count -Path $ConfigPath
    Add-Check -CheckId 'current-state-watch' -Condition (@($candidates | Where-Object { $_.current_state -ne 'watch' }).Count -eq 0) -Message 'all entries remain on watch lane' -Expected 'watch only' -Actual (@($candidates | Select-Object -ExpandProperty current_state) -join ', ') -Path $ConfigPath
    Add-Check -CheckId 'no-default-surface-change' -Condition (@($candidates | Where-Object { $_.default_surface_change }).Count -eq 0) -Message 'no candidate expands default surface' -Expected '0 true values' -Actual (@($candidates | Where-Object { $_.default_surface_change }).Count) -Path $ConfigPath
    $allowed = @('hold', 'pilot', 'review-ready')
    $unknown = @($candidates | Where-Object { $allowed -notcontains $_.decision_label })
    Add-Check -CheckId 'decision-labels-valid' -Condition ($unknown.Count -eq 0) -Message 'decision labels stay within allowed watch-lane outcomes' -Expected ($allowed -join ', ') -Actual (@($unknown | Select-Object -ExpandProperty decision_label) -join ', ') -Path $ConfigPath
}

if ($docExists) {
    $doc = Get-Content -LiteralPath $DocPath -Raw -Encoding UTF8
    Add-Check -CheckId 'doc-default-surface-guardrail' -Condition ($doc -match '不扩大默认面|default surface') -Message 'doc preserves the no-default-surface guardrail' -Expected 'guardrail statement' -Actual 'content scanned' -Path $DocPath
    Add-Check -CheckId 'doc-board-language' -Condition ($doc -match 'review-ready|pilot|hold') -Message 'doc explicitly uses board decision language' -Expected 'review-ready/pilot/hold' -Actual 'content scanned' -Path $DocPath
}

$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    summary = [pscustomobject]@{
        assertions = $script:checks.Count
        passed = @($script:checks | Where-Object { $_.passed }).Count
        failed = @($script:checks | Where-Object { -not $_.passed }).Count
    }
    checks = $script:checks
}

$report | ConvertTo-Json -Depth 6

if ($WriteArtifacts) {
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $jsonPath = Join-Path $OutputDirectory 'watch-portfolio-gate.json'
    $mdPath = Join-Path $OutputDirectory 'watch-portfolio-gate.md'
    ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    (New-MarkdownReport -Report $report) | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host ('Wrote {0}' -f $jsonPath) -ForegroundColor Green
    Write-Host ('Wrote {0}' -f $mdPath) -ForegroundColor Green
}

if (@($script:checks | Where-Object { -not $_.passed }).Count -gt 0) {
    exit 1
}

