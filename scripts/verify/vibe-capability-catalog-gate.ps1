param(
    [switch]$WriteArtifacts,
    [string]$OutputDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\governance")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Add-Assertion {
    param(
        [ref]$Results,
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ""
    )

    $record = [pscustomobject]@{
        passed = [bool]$Condition
        message = $Message
        details = $Details
    }
    $Results.Value += $record

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        if ($Details) {
            Write-Host "       $Details" -ForegroundColor DarkRed
        }
    }
}

function Test-SetContains {
    param(
        [string[]]$Actual,
        [string[]]$ExpectedSubset
    )

    $actualSet = @($Actual | Where-Object { $_ } | Sort-Object -Unique)
    foreach ($item in @($ExpectedSubset | Where-Object { $_ } | Sort-Object -Unique)) {
        if (-not ($actualSet -contains $item)) {
            return $false
        }
    }
    return $true
}

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-SkillNames {
    param([string]$Path)
    $lock = Read-JsonFile -Path $Path
    return @($lock.skills | ForEach-Object { [string]$_.name } | Where-Object { $_ } | Sort-Object -Unique)
}

function Get-CanonicalSkillNames {
    param([string]$RepoRoot)

    $coreSkillsRoot = Join-Path $RepoRoot "core\skills"
    if (-not (Test-Path -LiteralPath $coreSkillsRoot)) {
        return @()
    }

    $skillIds = @()
    foreach ($dir in @(Get-ChildItem -LiteralPath $coreSkillsRoot -Force -Directory | Sort-Object Name)) {
        $skillJsonPath = Join-Path $dir.FullName "skill.json"
        if (-not (Test-Path -LiteralPath $skillJsonPath)) {
            continue
        }

        $skillJson = Read-JsonFile -Path $skillJsonPath
        $source = if ($skillJson.PSObject.Properties.Name -contains "source_of_truth") { $skillJson.source_of_truth } else { $null }
        $sourceKind = if ($null -ne $source -and $source.PSObject.Properties.Name -contains "kind") { [string]$source.kind } else { "" }
        $skillId = if ($skillJson.PSObject.Properties.Name -contains "skill_id") { [string]$skillJson.skill_id } else { [string]$dir.Name }

        if ($sourceKind -eq "canonical-skill" -and -not [string]::IsNullOrWhiteSpace($skillId)) {
            $skillIds += $skillId
        }
    }

    return @($skillIds | Sort-Object -Unique)
}

function Write-GateArtifacts {
    param(
        [string]$Directory,
        [object]$Summary
    )

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $jsonPath = Join-Path $Directory "vibe-capability-catalog-gate.json"
    $mdPath = Join-Path $Directory "vibe-capability-catalog-gate.md"

    $Summary | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $md = New-Object System.Text.StringBuilder
    [void]$md.AppendLine("# Vibe Capability Catalog Gate")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("- Generated: $($Summary.generated_at)")
    [void]$md.AppendLine("- Passed: $($Summary.gate_passed)")
    [void]$md.AppendLine("- Assertions: $($Summary.assertion_count)")
    [void]$md.AppendLine("- Failures: $($Summary.failure_count)")
    [void]$md.AppendLine("- Capability count: $($Summary.capability_count)")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Required Corpus Sources")
    [void]$md.AppendLine("")
    foreach ($item in $Summary.required_corpus_sources) {
        [void]$md.AppendLine("- $item")
    }
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Material-only Capabilities")
    [void]$md.AppendLine("")
    foreach ($item in $Summary.material_only_capabilities) {
        [void]$md.AppendLine("- $item")
    }
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Failures")
    [void]$md.AppendLine("")
    $failed = @($Summary.results | Where-Object { -not $_.passed })
    if ($failed.Count -eq 0) {
        [void]$md.AppendLine("- None")
    } else {
        foreach ($item in $failed) {
            [void]$md.AppendLine("- $($item.message): $($item.details)")
        }
    }

    $md.ToString() | Set-Content -LiteralPath $mdPath -Encoding UTF8
    Write-Host "Artifacts written: $jsonPath"
    Write-Host "Artifacts written: $mdPath"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$paths = [ordered]@{
    governance_doc = Join-Path $repoRoot "docs\discovery-eval-corpus-governance.md"
    reference_doc = Join-Path $repoRoot "references\capability-catalog.md"
    catalog = Join-Path $repoRoot "config\capability-catalog.json"
    pilot_doc = Join-Path $repoRoot "docs\upstream-eval-pilot-scenarios.md"
    skills_lock = Join-Path $repoRoot "config\skills-lock.json"
}

$results = @()
$requiredTopKeys = @(
    "version",
    "schema_version",
    "updated",
    "catalog_purpose",
    "governance",
    "corpus_sources",
    "default_interview_questions",
    "capabilities"
)
$requiredGovernanceKeys = @(
    "catalog_kind",
    "compatibility_contract",
    "material_layer_boundary",
    "forbidden_outcomes"
)
$requiredLegacyFields = @(
    "id",
    "display_name",
    "task_allow",
    "keywords",
    "skills"
)
$requiredCapabilityFields = @(
    "id",
    "display_name",
    "summary",
    "catalog_kind",
    "task_allow",
    "keywords",
    "skills",
    "problem_domains",
    "inputs",
    "outputs",
    "applicable_planes",
    "upstream_sources",
    "dedup_with",
    "retirement_conditions",
    "materialization",
    "evaluation_hooks",
    "evidence_artifacts"
)
$requiredCorpusSources = @(
    "awesome-vibe-coding",
    "awesome-ai-tools",
    "vibe-coding-cn",
    "awesome-ai-agents-e2b"
)
$requiredMaterialCapabilities = @(
    "vibe_workflow_discovery_corpus",
    "ai_tool_landscape_corpus",
    "vibe_cn_localization_corpus",
    "sandbox_agent_eval_corpus"
)

foreach ($entry in $paths.GetEnumerator()) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $entry.Value) -Message ("required file exists: {0}" -f $entry.Key) -Details $entry.Value
}

$catalog = $null
$skillNames = @()
$governanceDoc = ""
$referenceDoc = ""
$pilotDoc = ""

if (Test-Path -LiteralPath $paths.catalog) {
    $catalog = Read-JsonFile -Path $paths.catalog
}
if (Test-Path -LiteralPath $paths.skills_lock) {
    $skillNames = Get-SkillNames -Path $paths.skills_lock
    $skillNames = @($skillNames + (Get-CanonicalSkillNames -RepoRoot $repoRoot) | Sort-Object -Unique)
}
if (Test-Path -LiteralPath $paths.governance_doc) {
    $governanceDoc = Get-Content -LiteralPath $paths.governance_doc -Raw -Encoding UTF8
}
if (Test-Path -LiteralPath $paths.reference_doc) {
    $referenceDoc = Get-Content -LiteralPath $paths.reference_doc -Raw -Encoding UTF8
}
if (Test-Path -LiteralPath $paths.pilot_doc) {
    $pilotDoc = Get-Content -LiteralPath $paths.pilot_doc -Raw -Encoding UTF8
}

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $catalog) -Message "capability catalog JSON parses"

$materialOnlyCapabilities = @()

if ($catalog) {
    $catalogKeys = @($catalog.PSObject.Properties.Name)
    foreach ($key in $requiredTopKeys) {
        Add-Assertion -Results ([ref]$results) -Condition ($catalogKeys -contains $key) -Message ("catalog contains top-level key: {0}" -f $key)
    }

    $governanceKeys = @($catalog.governance.PSObject.Properties.Name)
    foreach ($key in $requiredGovernanceKeys) {
        Add-Assertion -Results ([ref]$results) -Condition ($governanceKeys -contains $key) -Message ("governance contains key: {0}" -f $key)
    }

    Add-Assertion -Results ([ref]$results) -Condition (@($catalog.default_interview_questions).Count -ge 3) -Message "default interview questions are populated"

    $corpusSourceIds = @($catalog.corpus_sources | ForEach-Object { [string]$_.id } | Where-Object { $_ })
    Add-Assertion -Results ([ref]$results) -Condition (Test-SetContains -Actual $corpusSourceIds -ExpectedSubset $requiredCorpusSources) -Message "required corpus sources are registered" -Details ((@($corpusSourceIds | Sort-Object) -join ", "))

    Add-Assertion -Results ([ref]$results) -Condition (@($catalog.capabilities).Count -ge 18) -Message "capability catalog includes Wave37-38 expanded capability set"

    foreach ($capability in @($catalog.capabilities)) {
        $capabilityId = [string]$capability.id
        $capabilityKeys = @($capability.PSObject.Properties.Name)
        foreach ($field in $requiredCapabilityFields) {
            Add-Assertion -Results ([ref]$results) -Condition ($capabilityKeys -contains $field) -Message ("capability {0} contains field: {1}" -f $capabilityId, $field)
        }

        foreach ($field in $requiredLegacyFields) {
            Add-Assertion -Results ([ref]$results) -Condition ($capabilityKeys -contains $field) -Message ("legacy field preserved for {0}: {1}" -f $capabilityId, $field)
        }

        Add-Assertion -Results ([ref]$results) -Condition (@($capability.keywords).Count -ge 1) -Message ("capability {0} has keywords" -f $capabilityId)
        Add-Assertion -Results ([ref]$results) -Condition (@($capability.skills).Count -ge 1) -Message ("capability {0} has skills" -f $capabilityId)

        foreach ($skill in @($capability.skills)) {
            Add-Assertion -Results ([ref]$results) -Condition ($skillNames -contains [string]$skill) -Message ("skill exists for capability {0}: {1}" -f $capabilityId, $skill)
        }

        $materialization = $capability.materialization
        if ($capability.catalog_kind -in @("discovery_corpus", "eval_corpus", "reference_only")) {
            $materialOnlyCapabilities += $capabilityId
            Add-Assertion -Results ([ref]$results) -Condition ([string]$materialization.mode -eq "material_only") -Message ("material-only mode enforced for {0}" -f $capabilityId)
            Add-Assertion -Results ([ref]$results) -Condition ([string]$materialization.runtime_surface -eq "none") -Message ("runtime_surface none enforced for {0}" -f $capabilityId)
        }
        if ($capability.catalog_kind -eq "productized_capability") {
            Add-Assertion -Results ([ref]$results) -Condition ([string]$materialization.mode -eq "runtime_recommendation") -Message ("runtime recommendation mode enforced for {0}" -f $capabilityId)
            Add-Assertion -Results ([ref]$results) -Condition ([string]$materialization.runtime_surface -eq "vco-native") -Message ("vco-native runtime surface enforced for {0}" -f $capabilityId)
        }
    }

    $capabilityIds = @($catalog.capabilities | ForEach-Object { [string]$_.id } | Where-Object { $_ })
    Add-Assertion -Results ([ref]$results) -Condition (Test-SetContains -Actual $capabilityIds -ExpectedSubset $requiredMaterialCapabilities) -Message "required material-layer capabilities exist"

    foreach ($capabilityId in $requiredMaterialCapabilities) {
        $entry = @($catalog.capabilities | Where-Object { $_.id -eq $capabilityId })[0]
        if ($null -ne $entry) {
            $expectedKind = if ($capabilityId -eq "sandbox_agent_eval_corpus") { "eval_corpus" } else { "discovery_corpus" }
            Add-Assertion -Results ([ref]$results) -Condition ([string]$entry.catalog_kind -eq $expectedKind) -Message ("catalog kind matches for {0}" -f $capabilityId)
        }
    }

    $architectureEntry = @($catalog.capabilities | Where-Object { $_.id -eq "architecture_design" })[0]
    if ($null -ne $architectureEntry) {
        Add-Assertion -Results ([ref]$results) -Condition (@($architectureEntry.skills) -contains "architecture-patterns") -Message "architecture_design uses canonical architecture-patterns skill"
        Add-Assertion -Results ([ref]$results) -Condition (-not (@($architectureEntry.skills) -contains "system-design-overlay")) -Message "architecture_design no longer references nonexistent system-design-overlay"
    }
}

$governancePhrases = @(
    "第二 runtime surface",
    "awesome-vibe-coding",
    "awesome-ai-tools",
    "vibe-coding-cn",
    "awesome-ai-agents-e2b",
    "runtime_surface = none"
)
$governancePhrases[0] = "second runtime surface"
foreach ($phrase in $governancePhrases) {
    Add-Assertion -Results ([ref]$results) -Condition ($governanceDoc -match [regex]::Escape($phrase)) -Message ("discovery/eval governance doc mentions: {0}" -f $phrase)
}

foreach ($phrase in @(
    "productized_capability",
    "discovery_corpus",
    "eval_corpus",
    "reference_only",
    "material_only",
    "runtime_recommendation"
)) {
    Add-Assertion -Results ([ref]$results) -Condition ($referenceDoc -match [regex]::Escape($phrase)) -Message ("capability catalog reference mentions: {0}" -f $phrase)
}

foreach ($scenarioId in @(
    "pilot-discovery-vibe-workflows",
    "pilot-tool-landscape-watch",
    "pilot-cn-query-localization",
    "pilot-e2b-sandbox-eval",
    "pilot-corpus-to-catalog-dedup",
    "pilot-material-layer-boundary",
    "pilot-role-pack-supervisor-seed",
    "pilot-skill-distillation-quality"
)) {
    Add-Assertion -Results ([ref]$results) -Condition ($pilotDoc -match [regex]::Escape($scenarioId)) -Message ("pilot doc includes scenario: {0}" -f $scenarioId)
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$summary = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    gate_passed = ($failureCount -eq 0)
    assertion_count = $results.Count
    failure_count = $failureCount
    capability_count = if ($catalog) { @($catalog.capabilities).Count } else { 0 }
    required_corpus_sources = $requiredCorpusSources
    material_only_capabilities = @($materialOnlyCapabilities | Sort-Object -Unique)
    results = $results
}

if ($WriteArtifacts) {
    Write-GateArtifacts -Directory $OutputDirectory -Summary $summary
}

Write-Host ""
Write-Host "=== Summary ==="
Write-Host ("Assertions: {0}" -f $summary.assertion_count)
Write-Host ("Failures: {0}" -f $summary.failure_count)

if (-not $summary.gate_passed) {
    exit 1
}

Write-Host "Capability catalog gate passed." -ForegroundColor Green
exit 0
