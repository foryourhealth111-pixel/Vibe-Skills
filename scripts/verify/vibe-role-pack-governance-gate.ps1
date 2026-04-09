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

function Test-SetEquality {
    param(
        [string[]]$Actual,
        [string[]]$Expected
    )

    $actualSorted = @($Actual | Where-Object { $_ } | Sort-Object -Unique)
    $expectedSorted = @($Expected | Where-Object { $_ } | Sort-Object -Unique)
    if ($actualSorted.Count -ne $expectedSorted.Count) {
        return $false
    }

    for ($index = 0; $index -lt $actualSorted.Count; $index++) {
        if ($actualSorted[$index] -ne $expectedSorted[$index]) {
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

function Get-TeamTemplateIds {
    param([string]$Path)

    $matches = Select-String -Path $Path -Pattern '^## Template \d+:\s+([^\r\n(]+)'
    $ids = foreach ($match in $matches) {
        $templateId = $match.Matches[0].Groups[1].Value.Trim()
        if ($templateId) { $templateId }
    }
    return @($ids | Sort-Object -Unique)
}

function Write-GateArtifacts {
    param(
        [string]$Directory,
        [object]$Summary
    )

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $jsonPath = Join-Path $Directory "vibe-role-pack-governance-gate.json"
    $mdPath = Join-Path $Directory "vibe-role-pack-governance-gate.md"

    $Summary | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $md = New-Object System.Text.StringBuilder
    [void]$md.AppendLine("# Vibe Role-Pack Governance Gate")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("- Generated: $($Summary.generated_at)")
    [void]$md.AppendLine("- Passed: $($Summary.gate_passed)")
    [void]$md.AppendLine("- Assertions: $($Summary.assertion_count)")
    [void]$md.AppendLine("- Failures: $($Summary.failure_count)")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Covered Upstreams")
    [void]$md.AppendLine("")
    foreach ($item in $Summary.upstream_ids) {
        [void]$md.AppendLine("- $item")
    }
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Role Packs")
    [void]$md.AppendLine("")
    foreach ($item in $Summary.role_pack_ids) {
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
    role_doc = Join-Path $repoRoot "docs\role-pack-distillation-governance.md"
    rules_ref = Join-Path $repoRoot "references\skill-distillation-rules.md"
    policy = Join-Path $repoRoot "config\role-pack-policy.json"
    team_templates = Join-Path $repoRoot "references\team-templates.md"
    skills_lock = Join-Path $repoRoot "config\skills-lock.json"
}

$results = @()
$expectedUpstreams = @(
    "agent-squad",
    "claude-skills",
    "awesome-agent-skills",
    "awesome-claude-code-subagents",
    "antigravity-awesome-skills",
    "awesome-claude-skills-composio"
)
$requiredTopKeys = @(
    "schema_version",
    "updated",
    "policy",
    "upstream_sources",
    "role_packs",
    "team_template_interop",
    "skill_distillation_contract"
)
$requiredForbidden = @(
    "second_orchestrator",
    "second_team_execution_owner",
    "direct_upstream_runtime_import"
)
$requiredContractFields = @(
    "artifact_id",
    "upstream_source",
    "artifact_type",
    "retained_value",
    "landing_decision",
    "canonical_owner",
    "dedup_with",
    "evidence_required",
    "rejection_reason_if_any"
)

foreach ($entry in $paths.GetEnumerator()) {
    Add-Assertion -Results ([ref]$results) -Condition (Test-Path -LiteralPath $entry.Value) -Message ("required file exists: {0}" -f $entry.Key) -Details $entry.Value
}

$policy = $null
$teamTemplateIds = @()
$skillNames = @()
$roleDoc = ""
$rulesDoc = ""

if (Test-Path -LiteralPath $paths.policy) {
    $policy = Read-JsonFile -Path $paths.policy
}
if (Test-Path -LiteralPath $paths.team_templates) {
    $teamTemplateIds = Get-TeamTemplateIds -Path $paths.team_templates
}
if (Test-Path -LiteralPath $paths.skills_lock) {
    $skillNames = Get-SkillNames -Path $paths.skills_lock
    $skillNames = @($skillNames + (Get-CanonicalSkillNames -RepoRoot $repoRoot) | Sort-Object -Unique)
}
if (Test-Path -LiteralPath $paths.role_doc) {
    $roleDoc = Get-Content -LiteralPath $paths.role_doc -Raw -Encoding UTF8
}
if (Test-Path -LiteralPath $paths.rules_ref) {
    $rulesDoc = Get-Content -LiteralPath $paths.rules_ref -Raw -Encoding UTF8
}

Add-Assertion -Results ([ref]$results) -Condition ($null -ne $policy) -Message "role-pack policy JSON parses"

if ($policy) {
    $policyKeys = @($policy.PSObject.Properties.Name)
    foreach ($key in $requiredTopKeys) {
        Add-Assertion -Results ([ref]$results) -Condition ($policyKeys -contains $key) -Message ("policy contains top-level key: {0}" -f $key)
    }

    $actualUpstreams = @($policy.upstream_sources | ForEach-Object { [string]$_.id } | Where-Object { $_ })
    Add-Assertion -Results ([ref]$results) -Condition (Test-SetEquality -Actual $actualUpstreams -Expected $expectedUpstreams) -Message "upstream source coverage matches Wave37 scope" -Details ((@($actualUpstreams | Sort-Object) -join ", "))

    $forbidden = @($policy.policy.forbidden_outcomes)
    foreach ($item in $requiredForbidden) {
        Add-Assertion -Results ([ref]$results) -Condition ($forbidden -contains $item) -Message ("forbidden outcome declared: {0}" -f $item)
    }

    Add-Assertion -Results ([ref]$results) -Condition (@($policy.role_packs).Count -ge 4) -Message "role-pack policy contains governed role packs"

    foreach ($pack in @($policy.role_packs)) {
        $packId = [string]$pack.id
        Add-Assertion -Results ([ref]$results) -Condition (-not [string]::IsNullOrWhiteSpace($packId)) -Message "role-pack has id"
        Add-Assertion -Results ([ref]$results) -Condition (@($pack.maps_to_templates).Count -ge 1) -Message ("role-pack maps to templates: {0}" -f $packId)

        foreach ($templateId in @($pack.maps_to_templates)) {
            Add-Assertion -Results ([ref]$results) -Condition ($teamTemplateIds -contains [string]$templateId) -Message ("template exists for role-pack {0}: {1}" -f $packId, $templateId)
        }

        foreach ($skill in @($pack.distillation_assets.skills)) {
            Add-Assertion -Results ([ref]$results) -Condition ($skillNames -contains [string]$skill) -Message ("skill exists for role-pack {0}: {1}" -f $packId, $skill)
        }
    }

    foreach ($link in @($policy.team_template_interop.template_links)) {
        $templateId = [string]$link.template_id
        Add-Assertion -Results ([ref]$results) -Condition ($teamTemplateIds -contains $templateId) -Message ("interop template link resolves: {0}" -f $templateId)
    }

    $contractFields = @($policy.skill_distillation_contract.required_card_fields | ForEach-Object { [string]$_ })
    Add-Assertion -Results ([ref]$results) -Condition (Test-SetEquality -Actual $contractFields -Expected $requiredContractFields) -Message "skill distillation contract fields are complete"
}

foreach ($phrase in @(
    "第二 orchestrator",
    "第二 team execution owner",
    "role-pack / team-template / skill-distillation governance",
    "agent-squad",
    "claude-skills",
    "awesome-agent-skills",
    "awesome-claude-code-subagents",
    "antigravity-awesome-skills",
    "awesome-claude-skills-composio"
)) {
    Add-Assertion -Results ([ref]$results) -Condition ($roleDoc -match [regex]::Escape($phrase)) -Message ("role governance doc mentions: {0}" -f $phrase)
}

foreach ($phrase in @(
    "team_pattern",
    "role_card",
    "skill_template",
    "reference_case",
    "merge_into_role_pack",
    "team_template_seed",
    "reference_only",
    "reject"
)) {
    Add-Assertion -Results ([ref]$results) -Condition ($rulesDoc -match [regex]::Escape($phrase)) -Message ("distillation rules mention: {0}" -f $phrase)
}

$failureCount = @($results | Where-Object { -not $_.passed }).Count
$summary = [pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    gate_passed = ($failureCount -eq 0)
    assertion_count = $results.Count
    failure_count = $failureCount
    upstream_ids = if ($policy) { @($policy.upstream_sources | ForEach-Object { [string]$_.id }) } else { @() }
    role_pack_ids = if ($policy) { @($policy.role_packs | ForEach-Object { [string]$_.id }) } else { @() }
    template_ids_checked = @($teamTemplateIds)
    skill_name_count = $skillNames.Count
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

Write-Host "Role-pack governance gate passed." -ForegroundColor Green
exit 0
