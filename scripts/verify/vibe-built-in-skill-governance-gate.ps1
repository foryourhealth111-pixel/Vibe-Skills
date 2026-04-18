param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

function New-CaseInsensitiveSet {
    return New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
}

function Get-JsonDocument {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

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

function Get-RoutingCoverage {
    param(
        [string]$SkillId,
        [object]$PackManifest,
        [object]$KeywordIndex,
        [object]$RoutingRules
    )

    $inPackManifest = $false
    foreach ($pack in @($PackManifest.packs)) {
        if (@($pack.skill_candidates) -contains $SkillId) {
            $inPackManifest = $true
            break
        }

        $defaults = @()
        if ($null -ne $pack.defaults_by_task) {
            $defaults = @($pack.defaults_by_task.PSObject.Properties | ForEach-Object { [string]$_.Value })
        }
        if ($defaults -contains $SkillId) {
            $inPackManifest = $true
            break
        }
    }

    $inKeywordIndex = ($null -ne $KeywordIndex.skills -and @($KeywordIndex.skills.PSObject.Properties.Name) -contains $SkillId)
    $inRoutingRules = ($null -ne $RoutingRules.skills -and @($RoutingRules.skills.PSObject.Properties.Name) -contains $SkillId)

    $coverage = if ($inPackManifest -and $inKeywordIndex -and $inRoutingRules) {
        'full'
    } elseif ($inPackManifest -or $inKeywordIndex -or $inRoutingRules) {
        'partial'
    } else {
        'none'
    }

    return [pscustomobject]@{
        skill_id = $SkillId
        routing_coverage = $coverage
        in_pack_manifest = [bool]$inPackManifest
        in_keyword_index = [bool]$inKeywordIndex
        in_routing_rules = [bool]$inRoutingRules
    }
}

function Find-PatternHits {
    param(
        [string]$Text,
        [string[]]$Patterns
    )

    $hits = New-Object System.Collections.Generic.List[string]
    foreach ($pattern in $Patterns) {
        if ([string]::IsNullOrWhiteSpace($pattern)) {
            continue
        }
        if ([regex]::IsMatch($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $hits.Add([string]$pattern) | Out-Null
        }
    }
    return @($hits | Select-Object -Unique)
}

function Write-Artifacts {
    param(
        [string]$RepoRoot,
        [string]$OutputDirectory,
        [pscustomobject]$Artifact
    )

    $dir = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        Join-Path $RepoRoot 'outputs/verify'
    } else {
        $OutputDirectory
    }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    $jsonPath = Join-Path $dir 'vibe-built-in-skill-governance-gate.json'
    $mdPath = Join-Path $dir 'vibe-built-in-skill-governance-gate.md'
    $Artifact | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# VCO Built-In Skill Governance Gate') | Out-Null
    $lines.Add('') | Out-Null
    $lines.Add(('- Gate Result: **{0}**' -f $Artifact.gate_result)) | Out-Null
    $lines.Add(('- Bundled Skill Count: {0}' -f $Artifact.summary.bundled_skill_count)) | Out-Null
    $lines.Add(('- Full Routing Count: {0}' -f $Artifact.summary.full_routing_count)) | Out-Null
    $lines.Add(('- Partial Routing Count: {0}' -f $Artifact.summary.partial_routing_count)) | Out-Null
    $lines.Add(('- None Routing Count: {0}' -f $Artifact.summary.none_routing_count)) | Out-Null
    $lines.Add(('- Autonomous Phrase Violations: {0}' -f $Artifact.summary.auto_phrase_violation_count)) | Out-Null
    $lines.Add(('- Boilerplate Candidates: {0}' -f $Artifact.summary.boilerplate_candidate_count)) | Out-Null
    $lines.Add(('- Keyword Collisions: {0}' -f $Artifact.summary.keyword_collision_count)) | Out-Null
    $lines.Add('') | Out-Null

    $lines.Add('## Autonomous Phrase Violations') | Out-Null
    $lines.Add('') | Out-Null
    if (@($Artifact.auto_phrase_violations).Count -eq 0) {
        $lines.Add('- none') | Out-Null
    } else {
        foreach ($item in $Artifact.auto_phrase_violations) {
            $lines.Add(('- `{0}` coverage=`{1}` phrases={2}' -f $item.skill_id, $item.routing_coverage, (@($item.patterns) -join ', '))) | Out-Null
        }
    }
    $lines.Add('') | Out-Null

    $lines.Add('## Boilerplate Candidates') | Out-Null
    $lines.Add('') | Out-Null
    if (@($Artifact.boilerplate_candidates).Count -eq 0) {
        $lines.Add('- none') | Out-Null
    } else {
        foreach ($item in @($Artifact.boilerplate_candidates | Select-Object -First 25)) {
            $lines.Add(('- `{0}` coverage=`{1}` patterns={2}' -f $item.skill_id, $item.routing_coverage, (@($item.patterns) -join ', '))) | Out-Null
        }
    }
    $lines.Add('') | Out-Null

    $lines.Add('## Keyword Collisions') | Out-Null
    $lines.Add('') | Out-Null
    if (@($Artifact.keyword_collisions).Count -eq 0) {
        $lines.Add('- none') | Out-Null
    } else {
        foreach ($item in @($Artifact.keyword_collisions | Select-Object -First 25)) {
            $lines.Add(('- `{0}` shared_by={1}' -f $item.keyword, (@($item.skill_ids) -join ', '))) | Out-Null
        }
    }
    $lines.Add('') | Out-Null

    $lines.Add('## Assertions') | Out-Null
    $lines.Add('') | Out-Null
    foreach ($assertion in $Artifact.assertions) {
        $lines.Add(('- `{0}` {1}' -f $(if ($assertion.pass) { 'PASS' } else { 'FAIL' }), $assertion.message)) | Out-Null
    }

    $lines -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$policyPath = Join-Path $repoRoot 'config/bundled-skill-governance-policy.json'

$assertions = [System.Collections.Generic.List[object]]::new()
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $policyPath) -Message 'bundled skill governance policy exists' -Details $policyPath
if (-not (Test-Path -LiteralPath $policyPath)) {
    exit 1
}

$policy = Get-JsonDocument -Path $policyPath
$skillsRoot = Join-Path $repoRoot $policy.scope.skills_root
$packManifestPath = Join-Path $repoRoot $policy.scope.pack_manifest
$keywordIndexPath = Join-Path $repoRoot $policy.scope.skill_keyword_index
$routingRulesPath = Join-Path $repoRoot $policy.scope.skill_routing_rules

Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $skillsRoot) -Message 'bundled skills root exists' -Details $skillsRoot
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $packManifestPath) -Message 'pack manifest exists' -Details $packManifestPath
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $keywordIndexPath) -Message 'skill keyword index exists' -Details $keywordIndexPath
Add-Assertion -Assertions $assertions -Pass (Test-Path -LiteralPath $routingRulesPath) -Message 'skill routing rules exist' -Details $routingRulesPath

if (
    -not (Test-Path -LiteralPath $skillsRoot) -or
    -not (Test-Path -LiteralPath $packManifestPath) -or
    -not (Test-Path -LiteralPath $keywordIndexPath) -or
    -not (Test-Path -LiteralPath $routingRulesPath)
) {
    exit 1
}

$packManifest = Get-JsonDocument -Path $packManifestPath
$keywordIndex = Get-JsonDocument -Path $keywordIndexPath
$routingRules = Get-JsonDocument -Path $routingRulesPath
$allowlistedSkills = New-CaseInsensitiveSet
foreach ($item in @($policy.autonomous_phrase_rules.allowlisted_skills)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
        [void]$allowlistedSkills.Add([string]$item)
    }
}

$bundledSkillDirs = @(Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name)
$routingCoverage = New-Object System.Collections.Generic.List[object]
$autoViolations = New-Object System.Collections.Generic.List[object]
$boilerplateCandidates = New-Object System.Collections.Generic.List[object]

foreach ($dir in $bundledSkillDirs) {
    $skillId = [string]$dir.Name
    $skillMdPath = Join-Path $dir.FullName 'SKILL.md'
    $coverage = Get-RoutingCoverage -SkillId $skillId -PackManifest $packManifest -KeywordIndex $keywordIndex -RoutingRules $routingRules
    $routingCoverage.Add([pscustomobject]@{
            skill_id = $coverage.skill_id
            routing_coverage = $coverage.routing_coverage
            in_pack_manifest = $coverage.in_pack_manifest
            in_keyword_index = $coverage.in_keyword_index
            in_routing_rules = $coverage.in_routing_rules
            skill_md_path = $skillMdPath
        }) | Out-Null

    if (-not (Test-Path -LiteralPath $skillMdPath)) {
        continue
    }

    $text = Get-Content -LiteralPath $skillMdPath -Raw -Encoding UTF8
    $autoHits = Find-PatternHits -Text $text -Patterns @($policy.autonomous_phrase_rules.banned_patterns)
    if ($autoHits.Count -gt 0 -and -not $allowlistedSkills.Contains($skillId)) {
        $autoViolations.Add([pscustomobject]@{
                skill_id = $skillId
                skill_md_path = $skillMdPath
                routing_coverage = $coverage.routing_coverage
                in_pack_manifest = $coverage.in_pack_manifest
                in_keyword_index = $coverage.in_keyword_index
                in_routing_rules = $coverage.in_routing_rules
                patterns = @($autoHits)
            }) | Out-Null
    }

    $boilerplateHits = Find-PatternHits -Text $text -Patterns @($policy.boilerplate_description_rules.patterns)
    if ($boilerplateHits.Count -gt 0) {
        $boilerplateCandidates.Add([pscustomobject]@{
                skill_id = $skillId
                skill_md_path = $skillMdPath
                routing_coverage = $coverage.routing_coverage
                patterns = @($boilerplateHits)
            }) | Out-Null
    }
}

$keywordBuckets = @{}
$ignoredKeywords = New-CaseInsensitiveSet
foreach ($item in @($policy.keyword_collision_rules.ignore_keywords)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
        [void]$ignoredKeywords.Add(([string]$item).Trim())
    }
}

if ($null -ne $keywordIndex.skills) {
    foreach ($skillEntry in @($keywordIndex.skills.PSObject.Properties)) {
        $skillId = [string]$skillEntry.Name
        $skillPayload = $skillEntry.Value
        foreach ($keyword in @($skillPayload.keywords)) {
            $normalizedKeyword = ([string]$keyword).Trim().ToLowerInvariant()
            if ([string]::IsNullOrWhiteSpace($normalizedKeyword) -or $ignoredKeywords.Contains($normalizedKeyword)) {
                continue
            }

            if (-not $keywordBuckets.ContainsKey($normalizedKeyword)) {
                $keywordBuckets[$normalizedKeyword] = New-CaseInsensitiveSet
            }
            [void]$keywordBuckets[$normalizedKeyword].Add($skillId)
        }
    }
}

$keywordCollisions = New-Object System.Collections.Generic.List[object]
$minimumCollisionSize = [int]$policy.keyword_collision_rules.minimum_skill_count
foreach ($keyword in @($keywordBuckets.Keys | Sort-Object)) {
    $skillIds = @($keywordBuckets[$keyword] | Sort-Object)
    if ($skillIds.Count -ge $minimumCollisionSize) {
        $keywordCollisions.Add([pscustomobject]@{
                keyword = $keyword
                skill_ids = $skillIds
                skill_count = $skillIds.Count
            }) | Out-Null
    }
}

$fullRoutingCount = @($routingCoverage | Where-Object { $_.routing_coverage -eq 'full' }).Count
$partialRoutingCount = @($routingCoverage | Where-Object { $_.routing_coverage -eq 'partial' }).Count
$noneRoutingCount = @($routingCoverage | Where-Object { $_.routing_coverage -eq 'none' }).Count

$noAutoViolations = ($autoViolations.Count -eq 0)
$autoViolationDetails = @($autoViolations | ForEach-Object { $_.skill_id })
Add-Assertion -Assertions $assertions -Pass $noAutoViolations `
    -Message 'bundled built-in skills do not claim autonomous activation' `
    -Details $autoViolationDetails

$artifact = [pscustomobject]@{
    gate = 'vibe-built-in-skill-governance-gate'
    repo_root = [string]$repoRoot
    generated_at = (Get-Date).ToString('s')
    policy_id = [string]$policy.policy_id
    gate_result = if (@($assertions | Where-Object { -not $_.pass }).Count -eq 0) { 'PASS' } else { 'FAIL' }
    summary = [ordered]@{
        bundled_skill_count = $bundledSkillDirs.Count
        full_routing_count = $fullRoutingCount
        partial_routing_count = $partialRoutingCount
        none_routing_count = $noneRoutingCount
        auto_phrase_violation_count = $autoViolations.Count
        boilerplate_candidate_count = $boilerplateCandidates.Count
        keyword_collision_count = $keywordCollisions.Count
    }
    auto_phrase_violations = @($autoViolations | Sort-Object skill_id)
    boilerplate_candidates = @($boilerplateCandidates | Sort-Object skill_id)
    keyword_collisions = @($keywordCollisions | Sort-Object @{ Expression = 'skill_count'; Descending = $true }, keyword)
    routing_coverage = @($routingCoverage | Sort-Object skill_id)
    assertions = @($assertions)
}

if ($WriteArtifacts) {
    Write-Artifacts -RepoRoot $repoRoot -OutputDirectory $OutputDirectory -Artifact $artifact
}

if ($artifact.gate_result -ne 'PASS') {
    exit 1
}

exit 0
