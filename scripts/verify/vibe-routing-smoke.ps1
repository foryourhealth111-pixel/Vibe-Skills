param()

$ErrorActionPreference = 'Stop'

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    Write-Host "[FAIL] $Message"
    return $false
}

function Assert-FileContains {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Message
    )

    $content = Get-Content -Path $Path -Raw
    return Assert-True -Condition ([bool]($content -match $Pattern)) -Message $Message
}

function Assert-FileNotContains {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Message
    )

    $content = Get-Content -Path $Path -Raw
    return Assert-True -Condition (-not [bool]($content -match $Pattern)) -Message $Message
}

function Get-VibeGrade {
    param([string]$Prompt)

    $parallelRegex = '(并行|多智能体|multi-agent|parallel|frontend\s*\+\s*backend|前后端)'
    $designRegex = '(设计|架构|重构|迁移|重新设计|新系统|design|architect|refactor|migrate|redesign|new\s+system)'

    if ($Prompt -match $parallelRegex) {
        return 'XL'
    }

    if ($Prompt -match $designRegex) {
        return 'L'
    }

    return 'M'
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$skillRoot = Join-Path $repoRoot ''

$mainSkill = Join-Path $skillRoot 'SKILL.md'
$mainDo = Join-Path $skillRoot 'protocols\do.md'
$mainTeam = Join-Path $skillRoot 'protocols\team.md'
$mainThink = Join-Path $skillRoot 'protocols\think.md'
$mainFallback = Join-Path $skillRoot 'references\fallback-chains.md'
$mainConflict = Join-Path $skillRoot 'references\conflict-rules.md'

$bundleRoot = Join-Path $skillRoot 'bundled\skills\vibe'
$bundleSkill = Join-Path $bundleRoot 'SKILL.md'
$bundleDo = Join-Path $bundleRoot 'protocols\do.md'
$bundleTeam = Join-Path $bundleRoot 'protocols\team.md'
$bundleThink = Join-Path $bundleRoot 'protocols\think.md'
$bundleFallback = Join-Path $bundleRoot 'references\fallback-chains.md'
$bundleConflict = Join-Path $bundleRoot 'references\conflict-rules.md'

$targetFiles = @(
    $mainSkill,
    $mainDo,
    $mainTeam,
    $mainThink,
    $mainFallback,
    $mainConflict,
    $bundleSkill,
    $bundleDo,
    $bundleTeam,
    $bundleThink,
    $bundleFallback,
    $bundleConflict
)

$results = @()

Write-Host "=== Runtime-neutral terminology checks ==="
foreach ($file in $targetFiles) {
    $results += Assert-FileNotContains -Path $file -Pattern 'AskUserQuestion' -Message "No AskUserQuestion in $file"
    $results += Assert-FileNotContains -Path $file -Pattern 'TodoWrite' -Message "No TodoWrite in $file"
}

$results += Assert-FileContains -Path $mainSkill -Pattern 'user_confirm interface' -Message 'Main SKILL exposes user_confirm interface'
$results += Assert-FileContains -Path $mainSkill -Pattern 'state_store \(runtime-neutral\)' -Message 'Main SKILL exposes runtime-neutral state_store'
$results += Assert-FileContains -Path $bundleSkill -Pattern 'user_confirm interface' -Message 'Bundled SKILL exposes user_confirm interface'
$results += Assert-FileContains -Path $bundleSkill -Pattern 'state_store \(runtime-neutral\)' -Message 'Bundled SKILL exposes runtime-neutral state_store'

Write-Host "`n=== Routing scenario smoke tests ==="

$cases = @(
    [pscustomobject]@{
        Name = 'M';
        Prompt = '/vibe 给 signup 页加前端校验';
        Expected = 'M';
    },
    [pscustomobject]@{
        Name = 'L';
        Prompt = '/vibe 设计并实现认证系统';
        Expected = 'L';
    },
    [pscustomobject]@{
        Name = 'XL';
        Prompt = '/vibe 并行重构数据层和接口层';
        Expected = 'XL';
    }
)

foreach ($case in $cases) {
    $actual = Get-VibeGrade -Prompt $case.Prompt
    $results += Assert-True -Condition ($actual -eq $case.Expected) -Message "[$($case.Name)] grade expected=$($case.Expected), actual=$actual"
}

$results += Assert-FileContains -Path $mainSkill -Pattern 'M=single-agent' -Message '[M] documented as single-agent flow'
$results += Assert-FileContains -Path $mainSkill -Pattern 'L grade always follows: design → plan → user approval → subagent execution → two-stage review\.' -Message '[L] documented as design-first then execute'
$results += Assert-FileContains -Path $mainSkill -Pattern 'spawn_agent`/`send_input`/`wait`/`close_agent' -Message '[XL] main skill requires native agent lifecycle APIs'
$results += Assert-FileContains -Path $mainTeam -Pattern 'Option A: Codex Native Team \+ ruflo Collaboration' -Message '[XL] team protocol keeps Native+ruflo preferred path'
$results += Assert-FileContains -Path $mainTeam -Pattern 'Store intermediate state via ruflo `memory_store`' -Message '[XL] team protocol includes ruflo collaboration storage'
$results += Assert-FileContains -Path $mainTeam -Pattern 'Run native lifecycle only: `spawn_agent` → `send_input` → `wait` → `close_agent`' -Message '[XL] degraded path still uses native lifecycle APIs'
$results += Assert-FileContains -Path $mainTeam -Pattern 'Use runtime-neutral state_store \+ conversation context for milestone state' -Message '[XL] degraded path uses runtime-neutral state_store'

$passCount = ($results | Where-Object { $_ }).Count
$failCount = ($results | Where-Object { -not $_ }).Count
$total = $results.Count

Write-Host "`n=== Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}

Write-Host 'All vibe routing smoke tests passed.'
exit 0
