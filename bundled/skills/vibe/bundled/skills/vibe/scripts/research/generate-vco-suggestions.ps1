param(
    [string]$SignalPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\external-corpus\prompt-signals.json"),
    [string]$SourceRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "third_party\system-prompts-mirror"),
    [string]$SkillIndexPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "config\skill-keyword-index.json"),
    [string]$PackManifestPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "config\pack-manifest.json"),
    [string]$OutputDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\external-corpus"),
    [int]$MinPhraseHits = 3,
    [int]$MaxKeywordsPerSkill = 8
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function New-PhraseRule {
    param(
        [string]$Skill,
        [string]$Phrase,
        [string]$Regex
    )

    return [pscustomobject]@{
        skill = $Skill
        phrase = $Phrase
        regex = $Regex
    }
}

function Count-Matches {
    param(
        [string[]]$Texts,
        [string]$Regex
    )

    $count = 0
    foreach ($text in $Texts) {
        $count += [Regex]::Matches($text, $Regex).Count
    }
    return $count
}

if (-not (Test-Path -LiteralPath $SignalPath)) {
    throw "Signal file not found: $SignalPath. Run extract-prompt-signals.ps1 first."
}
if (-not (Test-Path -LiteralPath $SkillIndexPath)) {
    throw "Skill index not found: $SkillIndexPath"
}
if (-not (Test-Path -LiteralPath $PackManifestPath)) {
    throw "Pack manifest not found: $PackManifestPath"
}
if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Source root not found: $SourceRoot"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$signals = Get-Content -LiteralPath $SignalPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillIndex = Get-Content -LiteralPath $SkillIndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
$packManifest = Get-Content -LiteralPath $PackManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$scanExtensions = @(".txt", ".json", ".yaml", ".yml", ".md")
$corpusTexts = @(
    Get-ChildItem -Path $SourceRoot -Recurse -File |
    Where-Object { $scanExtensions -contains $_.Extension.ToLowerInvariant() } |
    ForEach-Object {
        try {
            (Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8).ToLowerInvariant()
        } catch {
            ""
        }
    } |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)

$phraseRules = @(
    (New-PhraseRule -Skill "vibe" -Phrase "tool selection" -Regex "\btool selection\b")
    (New-PhraseRule -Skill "vibe" -Phrase "task classification" -Regex "\btask classification\b")
    (New-PhraseRule -Skill "vibe" -Phrase "agent orchestration" -Regex "\bagent orchestration\b")
    (New-PhraseRule -Skill "subagent-driven-development" -Phrase "multi-agent workflow" -Regex "\bmulti-agent workflow\b")
    (New-PhraseRule -Skill "subagent-driven-development" -Phrase "parallel agents" -Regex "\bparallel agents?\b")
    (New-PhraseRule -Skill "systematic-debugging" -Phrase "root cause investigation" -Regex "\broot cause investigation\b")
    (New-PhraseRule -Skill "systematic-debugging" -Phrase "failure analysis" -Regex "\bfailure analysis\b")
    (New-PhraseRule -Skill "tdd-guide" -Phrase "red green refactor" -Regex "\bred green refactor\b")
    (New-PhraseRule -Skill "tdd-guide" -Phrase "test-first development" -Regex "\btest[- ]first development\b")
    (New-PhraseRule -Skill "code-reviewer" -Phrase "risk assessment" -Regex "\brisk assessment\b")
    (New-PhraseRule -Skill "code-reviewer" -Phrase "behavioral regression" -Regex "\bbehavioral regression\b")
    (New-PhraseRule -Skill "security-reviewer" -Phrase "defensive security" -Regex "\bdefensive security\b")
    (New-PhraseRule -Skill "security-reviewer" -Phrase "threat model" -Regex "\bthreat model\b")
    (New-PhraseRule -Skill "mcp-integration" -Phrase "tool schema" -Regex "\btool schema\b")
    (New-PhraseRule -Skill "mcp-integration" -Phrase "input schema" -Regex "\binput_schema\b|\binput schema\b")
    (New-PhraseRule -Skill "openai-docs" -Phrase "codex cli" -Regex "\bcodex cli\b")
    (New-PhraseRule -Skill "openai-docs" -Phrase "chat completions" -Regex "\bchat completions\b")
    (New-PhraseRule -Skill "openai-knowledge" -Phrase "responses api" -Regex "\bresponses api\b")
    (New-PhraseRule -Skill "documentation-lookup" -Phrase "api reference" -Regex "\bapi reference\b")
    (New-PhraseRule -Skill "prompt-lookup" -Phrase "system prompt" -Regex "\bsystem prompt\b")
    (New-PhraseRule -Skill "prompt-lookup" -Phrase "prompt template" -Regex "\bprompt template\b")
)

$existingSkillNames = @($skillIndex.skills.PSObject.Properties.Name)
$skillAdditions = @{}
$ruleResults = New-Object System.Collections.Generic.List[object]

foreach ($rule in $phraseRules) {
    $hits = Count-Matches -Texts $corpusTexts -Regex $rule.regex
    $existsInSkillIndex = $existingSkillNames -contains $rule.skill

    $alreadyPresent = $false
    if ($existsInSkillIndex) {
        $keywords = @($skillIndex.skills.($rule.skill).keywords)
        $alreadyPresent = $keywords -contains $rule.phrase
    }

    $accepted = $existsInSkillIndex -and (-not $alreadyPresent) -and ($hits -ge $MinPhraseHits)
    if ($accepted) {
        if (-not $skillAdditions.ContainsKey($rule.skill)) {
            $skillAdditions[$rule.skill] = New-Object System.Collections.Generic.List[string]
        }
        $skillAdditions[$rule.skill].Add($rule.phrase)
    }

    $ruleResults.Add([pscustomobject]@{
        skill = $rule.skill
        phrase = $rule.phrase
        regex = $rule.regex
        hits = [int]$hits
        exists_in_skill_index = $existsInSkillIndex
        already_present = $alreadyPresent
        accepted = $accepted
    })
}

# Build candidate skill index with conservative additions.
$candidateSkillIndex = $skillIndex | ConvertTo-Json -Depth 100 | ConvertFrom-Json
$appliedCount = 0
foreach ($skillName in $skillAdditions.Keys) {
    $currentKeywords = @($candidateSkillIndex.skills.($skillName).keywords)
    $toAdd = @($skillAdditions[$skillName] | Sort-Object -Unique | Select-Object -First $MaxKeywordsPerSkill)
    foreach ($kw in $toAdd) {
        if ($currentKeywords -contains $kw) { continue }
        $currentKeywords += $kw
        $appliedCount++
    }
    $candidateSkillIndex.skills.($skillName).keywords = $currentKeywords
}

# Pack-level suggestions (advisory only; not auto-applied).
$packSuggestions = New-Object System.Collections.Generic.List[object]
foreach ($pack in $packManifest.packs) {
    $packKeywords = @($pack.trigger_keywords | ForEach-Object { $_.ToLowerInvariant() })
    $tokenHints = @(
        $signals.token_frequency |
        ForEach-Object { $_.term } |
        Where-Object { $_ -match "agent|debug|review|route|workflow|security|test|model|prompt|mcp" } |
        Select-Object -Unique |
        Select-Object -First 20
    )

    $missing = @($tokenHints | Where-Object { $packKeywords -notcontains $_ })
    $packSuggestions.Add([pscustomobject]@{
        pack_id = $pack.id
        advisory_trigger_candidates = @($missing | Select-Object -First 10)
    })
}

$summary = [pscustomobject]@{
    source_root = $SourceRoot
    signal_file = $SignalPath
    corpus_file_count = [int]$signals.file_count
    rules_evaluated = [int]$ruleResults.Count
    phrases_accepted = [int]($ruleResults | Where-Object { $_.accepted }).Count
    skill_keywords_added = $appliedCount
}

$suggestionObject = [pscustomobject]@{
    version = 1
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    summary = $summary
    skill_rule_results = $ruleResults
    skill_additions = @(
        $skillAdditions.GetEnumerator() | ForEach-Object {
            [pscustomobject]@{
                skill = [string]$_.Key
                additions = @($_.Value | Sort-Object -Unique)
            }
        }
    )
    pack_suggestions = $packSuggestions
}

$suggestionJsonPath = Join-Path $OutputDirectory "vco-suggestions.json"
$suggestionMdPath = Join-Path $OutputDirectory "vco-suggestions.md"
$candidateIndexPath = Join-Path $OutputDirectory "skill-keyword-index.candidate.json"

$suggestionObject | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $suggestionJsonPath -Encoding UTF8
$candidateSkillIndex | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $candidateIndexPath -Encoding UTF8

$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# VCO External Corpus Suggestions")
[void]$md.AppendLine("")
[void]$md.AppendLine("- Generated: $($suggestionObject.generated_at)")
[void]$md.AppendLine("- Source root: $SourceRoot")
[void]$md.AppendLine("- Corpus files scanned: $($summary.corpus_file_count)")
[void]$md.AppendLine("- Rules evaluated: $($summary.rules_evaluated)")
[void]$md.AppendLine("- Accepted phrases: $($summary.phrases_accepted)")
[void]$md.AppendLine("- Candidate skill keywords added: $($summary.skill_keywords_added)")
[void]$md.AppendLine("")
[void]$md.AppendLine("## Skill Additions")
[void]$md.AppendLine("")

$skillAdditionRows = @($suggestionObject.skill_additions)
if ($skillAdditionRows.Count -eq 0) {
    [void]$md.AppendLine("No safe additions met the threshold.")
} else {
    foreach ($entry in $skillAdditionRows) {
        [void]$md.AppendLine("- `$($entry.skill)`: $([string]::Join(", ", $entry.additions))")
    }
}

[void]$md.AppendLine("")
[void]$md.AppendLine("## Advisory Pack Trigger Candidates")
[void]$md.AppendLine("")
foreach ($entry in $suggestionObject.pack_suggestions) {
    [void]$md.AppendLine("- `$($entry.pack_id)`: $([string]::Join(", ", $entry.advisory_trigger_candidates))")
}

$md.ToString() | Set-Content -LiteralPath $suggestionMdPath -Encoding UTF8

Write-Host "Suggestions JSON: $suggestionJsonPath"
Write-Host "Suggestions Markdown: $suggestionMdPath"
Write-Host "Candidate skill index: $candidateIndexPath"
