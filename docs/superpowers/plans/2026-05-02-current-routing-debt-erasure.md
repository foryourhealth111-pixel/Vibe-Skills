# Current Routing Debt Erasure Implementation Plan

> Historical / Retired Note: This implementation plan intentionally discusses
> retired routing terminology as cleanup targets. The current routing model is
> `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`;
> old terms here are debt targets, not current runtime states.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an executable current-routing debt audit and cleanup pass that removes retired routing fields from current paths and keeps any old-field support isolated as retired compatibility.

**Architecture:** Add a policy-driven debt gate that scans current runtime, router, docs, and tests using explicit current-field and retired-term contracts. Use that gate to move legacy consultation readers out of current runtime files, clean current fixtures that still write retired fields, and keep old terms only in retired or historical boundaries.

**Tech Stack:** PowerShell verification gates, Python `pytest`, JSON policy files, Markdown audit reports, existing Vibe-Skills runtime/router scripts.

---

## Task 1: Add The Current Routing Debt Policy

**Files:**
- Create: `config/current-routing-debt-erasure.json`
- Create: `tests/runtime_neutral/test_current_routing_debt_erasure_policy.py`

- [ ] **Step 1: Write the failing policy test**

Create `tests/runtime_neutral/test_current_routing_debt_erasure_policy.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "current-routing-debt-erasure.json"


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_policy_defines_current_field_chain_and_retired_terms() -> None:
    policy = load_policy()

    assert policy["schema_version"] == 1
    assert policy["current_model"] == [
        "skill_candidates",
        "skill_routing.selected",
        "selected_skill_execution",
        "skill_usage.used",
        "skill_usage.unused",
        "skill_usage.evidence",
    ]

    active_fields = set(policy["active_fields"])
    for field in [
        "skill_candidates",
        "skill_routing",
        "skill_routing.candidates",
        "skill_routing.selected",
        "skill_routing.rejected",
        "selected_skill_execution",
        "skill_execution_units",
        "approved_skill_execution",
        "execution_skill_outcomes",
        "skill_usage",
        "skill_usage.loaded_skills",
        "skill_usage.used",
        "skill_usage.unused",
        "skill_usage.used_skills",
        "skill_usage.unused_skills",
        "skill_usage.evidence",
    ]:
        assert field in active_fields

    retired_terms = set(policy["retired_terms"])
    for term in [
        "legacy_skill_routing",
        "specialist_recommendations",
        "stage_assistant_hints",
        "specialist_dispatch",
        "approved_consultation",
        "consulted_units",
        "route authority",
        "stage assistant",
        "consultation expert",
        "primary skill",
        "secondary skill",
    ]:
        assert term in retired_terms


def test_policy_separates_current_and_legacy_scopes() -> None:
    policy = load_policy()
    current_paths = set(policy["scan_scopes"]["current_paths"])
    allowed_paths = set(policy["scan_scopes"]["legacy_allowed_paths"])

    assert "scripts/runtime/VibeRuntime.Common.ps1" in current_paths
    assert "scripts/router/resolve-pack-route.ps1" in current_paths
    assert "packages/runtime-core/src/vgo_runtime" in current_paths
    assert "tests/runtime_neutral" in current_paths
    assert "tests/unit" in current_paths
    assert "tests/integration" in current_paths

    assert "tests/runtime_neutral/test_retired_old_routing_compat.py" in allowed_paths
    assert "docs/governance/historical-routing-terminology.md" in allowed_paths
    assert "docs/superpowers/specs" in allowed_paths

    excluded_roots = set(policy["scan_scopes"]["excluded_roots"])
    assert "bundled/skills" in excluded_roots
    assert "dist" in excluded_roots
    assert "vendor" in excluded_roots
    assert "third_party" in excluded_roots
    assert ".worktrees" in excluded_roots
```

- [ ] **Step 2: Run the policy test and verify it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_erasure_policy.py -q
```

Expected: FAIL with `FileNotFoundError` for `config/current-routing-debt-erasure.json`.

- [ ] **Step 3: Add the policy file**

Create `config/current-routing-debt-erasure.json`:

```json
{
  "schema_version": 1,
  "current_model": [
    "skill_candidates",
    "skill_routing.selected",
    "selected_skill_execution",
    "skill_usage.used",
    "skill_usage.unused",
    "skill_usage.evidence"
  ],
  "active_fields": [
    "skill_candidates",
    "skill_routing",
    "skill_routing.candidates",
    "skill_routing.selected",
    "skill_routing.rejected",
    "selected_skill_execution",
    "skill_execution_units",
    "approved_skill_execution",
    "execution_skill_outcomes",
    "skill_usage",
    "skill_usage.loaded_skills",
    "skill_usage.used",
    "skill_usage.unused",
    "skill_usage.used_skills",
    "skill_usage.unused_skills",
    "skill_usage.evidence"
  ],
  "retired_terms": [
    "legacy_skill_routing",
    "specialist_recommendations",
    "stage_assistant_hints",
    "specialist_dispatch",
    "discussion_specialist_consultation",
    "planning_specialist_consultation",
    "approved_consultation",
    "consulted_units",
    "discussion_consultation",
    "planning_consultation",
    "route owner",
    "route authority",
    "primary skill",
    "secondary skill",
    "consultation expert",
    "auxiliary expert",
    "stage assistant"
  ],
  "high_risk_retired_fields": [
    "legacy_skill_routing",
    "specialist_recommendations",
    "stage_assistant_hints",
    "specialist_dispatch",
    "approved_consultation",
    "consulted_units"
  ],
  "medium_risk_retired_terms": [
    "route authority",
    "stage assistant",
    "consultation expert",
    "primary skill",
    "secondary skill"
  ],
  "scan_scopes": {
    "current_paths": [
      "SKILL.md",
      "config",
      "scripts/router",
      "scripts/runtime",
      "packages/runtime-core/src/vgo_runtime",
      "tests/runtime_neutral",
      "tests/unit",
      "tests/integration",
      "scripts/verify",
      "docs/governance/current-routing-contract.md",
      "docs/governance/current-runtime-field-contract.md",
      "docs/install",
      "docs/status",
      "protocols"
    ],
    "legacy_allowed_paths": [
      "scripts/router/legacy",
      "scripts/runtime/legacy",
      "tests/runtime_neutral/test_retired_old_routing_compat.py",
      "tests/runtime_neutral/test_simplified_skill_routing_contract.py",
      "tests/runtime_neutral/test_current_routing_contract_cleanup.py",
      "tests/runtime_neutral/test_vibe_specialist_consultation.py",
      "tests/runtime_neutral/test_active_consultation_simplification.py",
      "tests/runtime_neutral/test_historical_routing_doc_compression.py",
      "docs/governance/historical-routing-terminology.md",
      "docs/superpowers/specs",
      "docs/superpowers/plans",
      "references/fixtures"
    ],
    "excluded_roots": [
      "bundled/skills",
      "dist",
      "vendor",
      "third_party",
      "outputs",
      ".pytest_cache",
      "__pycache__",
      ".worktrees"
    ]
  },
  "classification_rules": {
    "P0": "retired field is written to current runtime, router, generated docs, or completion output",
    "P1": "current code or current tests depend on retired fields outside a retired boundary",
    "P2": "current docs explain active behavior using retired terms",
    "P3": "retired term appears only in legacy, retired, historical, fixture, or audit evidence"
  },
  "success_thresholds": {
    "P0": 0,
    "P1": 0,
    "P2": 0
  }
}
```

- [ ] **Step 4: Run the policy test and verify it passes**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_erasure_policy.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add config/current-routing-debt-erasure.json tests/runtime_neutral/test_current_routing_debt_erasure_policy.py
git commit -m "test: define current routing debt policy"
```

## Task 2: Add The Debt Gate Tests

**Files:**
- Create: `tests/runtime_neutral/test_current_routing_debt_gate.py`
- Create later in Task 3: `scripts/verify/vibe-current-routing-debt-gate.ps1`

- [ ] **Step 1: Write the failing gate tests**

Create `tests/runtime_neutral/test_current_routing_debt_gate.py`:

```python
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "verify" / "vibe-current-routing-debt-gate.ps1"
POLICY = REPO_ROOT / "config" / "current-routing-debt-erasure.json"


def powershell() -> str:
    shell = (
        shutil.which("pwsh")
        or shutil.which("pwsh.exe")
        or shutil.which("powershell")
        or shutil.which("powershell.exe")
    )
    if not shell:
        pytest.skip("PowerShell executable not available")
    return shell


def run_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [powershell(), "-NoLogo", "-NoProfile", "-File", str(GATE), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_gate_reports_json_and_clean_current_surfaces() -> None:
    result = run_gate("-Json")
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["policy_path"].replace("\\", "/").endswith("config/current-routing-debt-erasure.json")
    assert payload["summary"]["P0"] == 0
    assert payload["summary"]["P1"] == 0
    assert payload["summary"]["P2"] == 0
    assert payload["summary"]["legacy_allowed_hits"] > 0
    assert "legacy_skill_routing" in payload["retired_terms"]
    assert "skill_routing.selected" in payload["current_fields"]
    assert payload["current_model"] == [
        "skill_candidates",
        "skill_routing.selected",
        "selected_skill_execution",
        "skill_usage.used",
        "skill_usage.unused",
        "skill_usage.evidence",
    ]


def test_gate_writes_audit_artifacts() -> None:
    result = run_gate("-WriteArtifacts")
    assert result.returncode == 0, result.stdout + result.stderr

    json_path = REPO_ROOT / "outputs" / "verify" / "current-routing-debt-gate.json"
    audit_json_path = REPO_ROOT / "outputs" / "verify" / "current-routing-debt-audit.json"

    assert json_path.exists()
    assert audit_json_path.exists()

    gate_payload = json.loads(json_path.read_text(encoding="utf-8"))
    audit_payload = json.loads(audit_json_path.read_text(encoding="utf-8"))
    expected_audit_name = f"{gate_payload['generated_at'][:10]}-current-routing-debt-audit.md"
    audit_md_path = REPO_ROOT / "docs" / "audits" / expected_audit_name
    assert audit_md_path.exists()
    audit_markdown = audit_md_path.read_text(encoding="utf-8")

    assert gate_payload["status"] == "pass"
    assert audit_payload["status"] == "pass"
    assert "# Current Routing Debt Audit" in audit_markdown
    assert "P0 Current Output Pollution: 0" in audit_markdown
    assert "P1 Current Code Dependency: 0" in audit_markdown
    assert "P2 Current Documentation Pollution: 0" in audit_markdown


def test_gate_policy_file_exists_and_is_valid_json() -> None:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["success_thresholds"] == {"P0": 0, "P1": 0, "P2": 0}
```

- [ ] **Step 2: Run the gate tests and verify they fail**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate.py -q
```

Expected: FAIL because `scripts/verify/vibe-current-routing-debt-gate.ps1` does not exist.

- [ ] **Step 3: Commit the failing tests**

```powershell
git add tests/runtime_neutral/test_current_routing_debt_gate.py
git commit -m "test: require current routing debt gate"
```

## Task 3: Implement The Current Routing Debt Gate

**Files:**
- Create: `scripts/verify/vibe-current-routing-debt-gate.ps1`
- Uses: `config/current-routing-debt-erasure.json`
- Produces: `outputs/verify/current-routing-debt-gate.json`
- Produces: `outputs/verify/current-routing-debt-audit.json`
- Produces: `docs/audits/<run-date>-current-routing-debt-audit.md`

- [ ] **Step 1: Add the gate implementation**

Create `scripts/verify/vibe-current-routing-debt-gate.ps1`:

```powershell
param(
    [switch]$Json,
    [switch]$WriteArtifacts,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
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
        return $pathFull.Substring($rootFull.Length).TrimStart('\', '/').Replace('\', '/')
    }
    return $pathFull.Replace('\', '/')
}

function Test-PathPrefix {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string[]]$Prefixes
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

    foreach ($relative in $currentPaths) {
        $full = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $full)) {
            throw "Configured current_paths entry not found: $relative ($full)"
        }
        if (Test-Path -LiteralPath $full -PathType Leaf) {
            $item = Get-Item -LiteralPath $full
            if ($extensions -contains $item.Extension.ToLowerInvariant()) {
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
            if ($extensions -contains $file.Extension.ToLowerInvariant()) {
                $files.Add($file) | Out-Null
            }
        }
    }

    return @($files.ToArray() | Sort-Object FullName -Unique)
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
                $fragments.Add([pscustomobject]@{ kind = 'string'; text = $buffer.ToString() }) | Out-Null
                $buffer.Clear() | Out-Null
                $inString = $false
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
        }
    }
    return @($fragments.ToArray())
}

function Test-LineIsGuardAssertion {
    param([Parameter(Mandatory)] [string]$Line)
    $trimmed = $Line.TrimStart()
    if ($trimmed.StartsWith('assert ', [System.StringComparison]::OrdinalIgnoreCase) -and $Line.IndexOf(' not in ', [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
        return $true
    }
    foreach ($needle in @('assertNotIn', 'self.assertNotIn', 'assertNotRegex')) {
        if ($Line.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }
    foreach ($fragment in @(Get-LineCommentAndStringFragments -Line $Line)) {
        $fragmentText = [string]$fragment.text
        foreach ($needle in @('assert "not in"', ' not in ', 'NotIn')) {
            if ($fragmentText.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                return $true
            }
        }
    }
    return $false
}

function Test-LineIsRetiredExplanation {
    param([Parameter(Mandatory)] [string]$Line)
    $commentNeedles = @('retired', 'historical', 'legacy', 'old terms', 'old fields', 'not current', 'cleanup target', 'debt target')
    $stringNeedles = @('retired', 'historical', 'legacy compatibility', 'legacy field', 'legacy terms', 'old terms', 'old fields', 'not current', 'cleanup target', 'debt target')
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
$RepoRoot = $context.repoRoot
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

foreach ($file in Get-TextFiles -Root $RepoRoot -Policy $policy) {
    $relative = ConvertTo-RepoRelativePath -Path $file.FullName -Root $RepoRoot
    $allowedLegacyPath = Test-PathPrefix -Path $relative -Prefixes $legacyAllowed
    $layer = Get-CurrentLayer -RelativePath $relative
    $lines = @(Get-Content -LiteralPath $file.FullName -Encoding UTF8)

    for ($index = 0; $index -lt $lines.Count; $index++) {
        $lineText = [string]$lines[$index]
        foreach ($term in $retiredTerms) {
            if ($lineText.IndexOf($term, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
                continue
            }

            if ($allowedLegacyPath -or (Test-LineIsGuardAssertion -Line $lineText) -or (Test-LineIsRetiredExplanation -Line $lineText)) {
                $legacyAllowedHits += 1
                continue
            }

            $category = if ($layer -in @('current_runtime', 'current_router', 'runtime_core') -and ($highRisk -contains $term)) {
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
                'P1' { 'Move the old-field reader or fixture into a legacy/retired file, or rewrite it to current skill_routing and skill_usage fields.' }
                'P2' { 'Rewrite the text to the current candidate/selected/execution/used/unused/evidence model, or mark it as retired history.' }
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
    scanned_file_count = @(Get-TextFiles -Root $RepoRoot -Policy $policy).Count
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
    $verifyDir = Join-Path $RepoRoot 'outputs\verify'
    $auditDir = Join-Path $RepoRoot 'docs\audits'
    New-Item -ItemType Directory -Force -Path $verifyDir | Out-Null
    New-Item -ItemType Directory -Force -Path $auditDir | Out-Null

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
```

- [ ] **Step 2: Run the gate tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate.py -q
```

Expected before Tasks 4 and 5: FAIL if the new gate reports P1 current-code or current-test retired-field hits. Keep the failure output; it identifies the exact files for cleanup.

- [ ] **Step 3: Commit only if the gate test already passes**

If Step 2 passes:

```powershell
git add scripts/verify/vibe-current-routing-debt-gate.ps1
git commit -m "feat: add current routing debt gate"
```

If Step 2 fails with P1 findings, leave the script uncommitted and continue to Task 4 so the first passing commit contains the gate plus the cleanup that makes it true.

## Task 4: Move Retired Consultation Readers Out Of Current Runtime

**Files:**
- Create: `scripts/runtime/legacy/VibeRetiredConsultation.Common.ps1`
- Modify: `scripts/runtime/VibeRuntime.Common.ps1`
- Modify: `tests/runtime_neutral/test_current_routing_contract_cleanup.py`
- Modify: `tests/runtime_neutral/test_retired_old_routing_compat.py`

- [ ] **Step 1: Write a failing text-boundary test**

Append this test to `tests/runtime_neutral/test_current_routing_contract_cleanup.py`:

```python
def test_retired_consultation_field_reads_live_outside_current_runtime_common() -> None:
    current_text = (REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1").read_text(encoding="utf-8")
    legacy_text = (REPO_ROOT / "scripts" / "runtime" / "legacy" / "VibeRetiredConsultation.Common.ps1").read_text(
        encoding="utf-8"
    )

    for retired_field in [
        "consulted_units",
        "routed_units",
        "discussion_consultation",
        "planning_consultation",
    ]:
        assert retired_field not in current_text
        assert retired_field in legacy_text

    assert "New-VibeRetiredSpecialistConsultationLifecycleLayerProjection" in legacy_text
    assert "New-VibeSpecialistConsultationLifecycleLayerProjection" not in current_text
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_contract_cleanup.py::test_retired_consultation_field_reads_live_outside_current_runtime_common -q
```

Expected: FAIL because `scripts/runtime/legacy/VibeRetiredConsultation.Common.ps1` does not exist and `VibeRuntime.Common.ps1` still contains retired consultation field reads.

- [ ] **Step 3: Extract retired consultation functions**

Create `scripts/runtime/legacy/VibeRetiredConsultation.Common.ps1` by moving the current implementation of these legacy-only functions out of `scripts/runtime/VibeRuntime.Common.ps1`:

```text
New-VibeSpecialistConsultationLifecycleLayerProjection
```

Rename the moved function to:

```text
New-VibeRetiredSpecialistConsultationLifecycleLayerProjection
```

Inside `scripts/runtime/VibeRuntime.Common.ps1`, replace the two calls in `New-VibeSpecialistLifecycleDisclosureProjection`:

```powershell
(New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $DiscussionConsultationReceipt),
(New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $PlanningConsultationReceipt),
```

with:

```powershell
(New-VibeRetiredSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $DiscussionConsultationReceipt),
(New-VibeRetiredSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $PlanningConsultationReceipt),
```

At the top of `scripts/runtime/VibeRuntime.Common.ps1`, dot-source the retired helper after shared helper imports:

```powershell
$retiredConsultationHelper = Join-Path $PSScriptRoot 'legacy\VibeRetiredConsultation.Common.ps1'
if (Test-Path -LiteralPath $retiredConsultationHelper -PathType Leaf) {
    . $retiredConsultationHelper
}
```

Create the `legacy` directory with PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path .\scripts\runtime\legacy | Out-Null
```

- [ ] **Step 4: Keep retired behavior tests explicit**

In `tests/runtime_neutral/test_retired_old_routing_compat.py`, add a constant:

```python
RETIRED_CONSULTATION_COMMON = REPO_ROOT / "scripts" / "runtime" / "legacy" / "VibeRetiredConsultation.Common.ps1"
```

In the PowerShell script inside `test_current_selection_ignores_legacy_skill_routing_container`, dot-source the retired helper next to the existing common files when the test needs retired consultation behavior:

```python
f". {ps_quote(str(RETIRED_CONSULTATION_COMMON))}; "
```

In `test_legacy_consultation_projection_is_explicitly_legacy` inside `tests/runtime_neutral/test_current_routing_contract_cleanup.py`, dot-source `RETIRED_CONSULTATION_COMMON` and change the called function name to:

```powershell
New-VibeRetiredSpecialistConsultationLifecycleLayerProjection
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_contract_cleanup.py::test_retired_consultation_field_reads_live_outside_current_runtime_common -q
python -m pytest tests/runtime_neutral/test_current_routing_contract_cleanup.py::CurrentRoutingContractCleanupTests::test_legacy_consultation_projection_is_explicitly_legacy -q
python -m pytest tests/runtime_neutral/test_retired_old_routing_compat.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add scripts/runtime/VibeRuntime.Common.ps1 scripts/runtime/legacy/VibeRetiredConsultation.Common.ps1 tests/runtime_neutral/test_current_routing_contract_cleanup.py tests/runtime_neutral/test_retired_old_routing_compat.py
git commit -m "refactor: isolate retired consultation runtime readers"
```

## Task 5: Clean Current Test Fixtures That Still Emit Retired Fields

**Files:**
- Modify: `tests/unit/test_canonical_vibe_entry_launcher.py`
- Modify: `tests/integration/test_canonical_vibe_truth_gate.py`
- Modify: `tests/integration/test_verification_runtime_entrypoint_contract_cutover.py`
- Modify: `tests/runtime_neutral/test_current_routing_debt_gate.py`

- [ ] **Step 1: Add fixture-cleanliness assertions to the debt gate test**

Append to `tests/runtime_neutral/test_current_routing_debt_gate.py`:

```python
def test_current_unit_and_integration_fixtures_do_not_write_retired_root_fields() -> None:
    current_fixture_files = [
        REPO_ROOT / "tests" / "unit" / "test_canonical_vibe_entry_launcher.py",
        REPO_ROOT / "tests" / "integration" / "test_verification_runtime_entrypoint_contract_cutover.py",
    ]
    for path in current_fixture_files:
        text = path.read_text(encoding="utf-8")
        assert '"specialist_recommendations"' not in text, path
        assert '"specialist_dispatch"' not in text, path
        assert '"legacy_skill_routing"' not in text, path


def test_truth_gate_legacy_fixture_is_named_as_retired_fixture() -> None:
    text = (REPO_ROOT / "tests" / "integration" / "test_canonical_vibe_truth_gate.py").read_text(encoding="utf-8")
    assert "def _write_retired_legacy_truth_artifacts(" in text
    assert "def _write_valid_canonical_entry_artifacts(" in text
    valid_helper = text.split("def _write_valid_canonical_entry_artifacts(", 1)[1].split(
        "def test_truth_gate_rejects_missing_launch_receipt",
        1,
    )[0]
    assert '"legacy_skill_routing"' not in valid_helper
    assert '"specialist_recommendations"' not in valid_helper
    assert '"specialist_dispatch"' not in valid_helper
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate.py::test_current_unit_and_integration_fixtures_do_not_write_retired_root_fields tests/runtime_neutral/test_current_routing_debt_gate.py::test_truth_gate_legacy_fixture_is_named_as_retired_fixture -q
```

Expected: FAIL because current fixtures still mention retired root fields.

- [ ] **Step 3: Rewrite the unit fixture to current fields**

In `tests/unit/test_canonical_vibe_entry_launcher.py`, edit `_write_valid_truth_artifacts` so the `runtime-input-packet.json` payload removes:

```python
"specialist_recommendations": [
    {
        "skill_id": router_selected_skill,
    }
],
"specialist_dispatch": {
    "approved_dispatch": [],
    "local_specialist_suggestions": [],
},
```

Add this current usage block after `skill_routing`:

```python
"skill_usage": {
    "state_model": "binary_used_unused",
    "used": [],
    "unused": [{"skill_id": router_selected_skill}],
    "evidence": [],
},
"specialist_decision": {
    "decision_state": "no_specialist_recommendations",
    "resolution_mode": "no_specialist_needed",
    "recommendation_count": 0,
    "candidate_skill_ids_reviewed": [router_selected_skill],
    "selected_skill_ids": [],
    "rejected_candidates": [],
},
```

- [ ] **Step 4: Split the integration truth-gate legacy fixture**

In `tests/integration/test_canonical_vibe_truth_gate.py`, create a helper immediately after `_write_valid_canonical_entry_artifacts`:

```python
def _write_retired_legacy_truth_artifacts(session_root: Path) -> None:
    _write_valid_canonical_entry_artifacts(session_root)
    runtime_packet_path = session_root / "runtime-input-packet.json"
    runtime_packet = json.loads(runtime_packet_path.read_text(encoding="utf-8"))
    runtime_packet["legacy_skill_routing"] = {
        "specialist_recommendations": [
            {
                "skill_id": "systematic-debugging",
                "native_skill_entrypoint": "skills/systematic-debugging/SKILL.md",
            }
        ],
        "stage_assistant_hints": [],
        "specialist_dispatch": {
            "approved_dispatch": [],
            "local_specialist_suggestions": [],
            "status": "no_dispatch",
            "approved_skill_ids": [],
            "local_suggestion_skill_ids": [],
            "blocked_skill_ids": [],
            "degraded_skill_ids": [],
            "matched_skill_ids": [],
            "surfaced_skill_ids": [],
            "ghost_match_skill_ids": [],
            "escalation_required": False,
            "escalation_status": "not_required",
        },
    }
    _write_json(runtime_packet_path, runtime_packet)
```

Remove the `legacy_skill_routing` object from `_write_valid_canonical_entry_artifacts`.

Change only the tests that explicitly prove old artifact readability to call:

```python
_write_retired_legacy_truth_artifacts(session_root)
```

Keep current-entry acceptance tests using:

```python
_write_valid_canonical_entry_artifacts(session_root)
```

- [ ] **Step 5: Update verification-entrypoint contract cutover assertions**

In `tests/integration/test_verification_runtime_entrypoint_contract_cutover.py`, replace assertions that require gate source text to contain retired fields:

```python
assert "specialist_recommendations" in content
assert "specialist_dispatch" in content
```

with current contract assertions:

```python
assert "skill_routing" in content
assert "selected_skill_execution" in content
assert "skill_usage" in content
```

Replace:

```python
assert "specialist_dispatch" in gate
assert "specialist_recommendations" in gate
```

with:

```python
assert "skill_routing" in gate
assert "selected_skill_execution" in gate
assert "skill_usage" in gate
```

- [ ] **Step 6: Run focused fixture tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate.py::test_current_unit_and_integration_fixtures_do_not_write_retired_root_fields tests/runtime_neutral/test_current_routing_debt_gate.py::test_truth_gate_legacy_fixture_is_named_as_retired_fixture -q
python -m pytest tests/unit/test_canonical_vibe_entry_launcher.py -q
python -m pytest tests/integration/test_canonical_vibe_truth_gate.py -q
python -m pytest tests/integration/test_verification_runtime_entrypoint_contract_cutover.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tests/unit/test_canonical_vibe_entry_launcher.py tests/integration/test_canonical_vibe_truth_gate.py tests/integration/test_verification_runtime_entrypoint_contract_cutover.py tests/runtime_neutral/test_current_routing_debt_gate.py
git commit -m "test: retire old routing fields from current fixtures"
```

## Task 6: Wire The Gate Into Verify Documentation

**Files:**
- Modify: `scripts/verify/README.md`
- Modify: `scripts/verify/gate-family-index.md`
- Create: `tests/runtime_neutral/test_current_routing_debt_gate_docs.py`

- [ ] **Step 1: Write the failing docs test**

Create `tests/runtime_neutral/test_current_routing_debt_gate_docs.py`:

```python
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_verify_docs_include_current_routing_debt_gate() -> None:
    readme = (REPO_ROOT / "scripts" / "verify" / "README.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "scripts" / "verify" / "gate-family-index.md").read_text(encoding="utf-8")

    for text in [readme, index]:
        assert "vibe-current-routing-debt-gate.ps1" in text
        assert "current routing debt" in text.lower()


def test_common_verify_sequence_keeps_router_contract_before_debt_gate() -> None:
    readme = (REPO_ROOT / "scripts" / "verify" / "README.md").read_text(encoding="utf-8")
    router_index = readme.index("vibe-router-contract-gate.ps1")
    debt_index = readme.index("vibe-current-routing-debt-gate.ps1")
    assert router_index < debt_index
```

- [ ] **Step 2: Run the docs test and verify it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate_docs.py -q
```

Expected: FAIL because verify docs do not mention the new gate.

- [ ] **Step 3: Update verify README**

In `scripts/verify/README.md`, add this command to the Common Verify Sequence after `vibe-router-contract-gate.ps1`:

```powershell
& ".\vibe-current-routing-debt-gate.ps1" -WriteArtifacts
```

Add this note under High-Frequency Quick Starts:

````markdown
Current routing debt:

```powershell
& ".\vibe-current-routing-debt-gate.ps1" -WriteArtifacts
```
````

- [ ] **Step 4: Update gate family index**

In `scripts/verify/gate-family-index.md`, add `vibe-current-routing-debt-gate.ps1` to the Typical Closure Order after `vibe-router-contract-gate.ps1`.

Add it to the Cleanliness / outputs / compatibility hygiene family with this description:

```text
vibe-current-routing-debt-gate.ps1: verifies retired routing terms stay out of current runtime, router, docs, and current tests while allowing explicit retired/historical evidence.
```

- [ ] **Step 5: Run docs test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate_docs.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add scripts/verify/README.md scripts/verify/gate-family-index.md tests/runtime_neutral/test_current_routing_debt_gate_docs.py
git commit -m "docs: add current routing debt gate to verify flow"
```

## Task 7: Run The Gate, Review The Audit, And Commit Generated Evidence Policy

**Files:**
- Produces untracked or modified generated outputs under `outputs/verify/`
- Produces: `docs/audits/<run-date>-current-routing-debt-audit.md`
- Do not commit generated `outputs/verify/*` unless repo policy already tracks this exact class of verify output.

- [ ] **Step 1: Run the gate with artifacts**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-current-routing-debt-gate.ps1 -WriteArtifacts
```

Expected:

```text
Status: pass
P0 Current Output Pollution: 0
P1 Current Code Dependency: 0
P2 Current Documentation Pollution: 0
```

- [ ] **Step 2: Inspect generated audit JSON**

Run:

```powershell
Get-Content -Raw .\outputs\verify\current-routing-debt-audit.json | ConvertFrom-Json | Select-Object status,summary
```

Expected:

```text
status : pass
summary: @{P0=0; P1=0; P2=0; ...}
```

- [ ] **Step 3: Inspect generated audit Markdown**

Run:

```powershell
$latestAudit = Get-ChildItem .\docs\audits\*-current-routing-debt-audit.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content -Path $latestAudit.FullName -TotalCount 40
```

Expected to include:

```text
# Current Routing Debt Audit
P0 Current Output Pollution: 0
P1 Current Code Dependency: 0
P2 Current Documentation Pollution: 0
```

- [ ] **Step 4: Decide whether to track the Markdown audit**

Run:

```powershell
git status --short -- docs/audits outputs/verify
```

Expected: `docs/audits/<run-date>-current-routing-debt-audit.md` may be untracked; `outputs/verify/*` may be generated evidence.

Commit only the Markdown audit if the repo already tracks comparable `docs/audits/*.md` files:

```powershell
git ls-files docs/audits
```

If `docs/audits` has tracked audit reports, commit the new Markdown audit:

```powershell
$latestAudit = Get-ChildItem .\docs\audits\*-current-routing-debt-audit.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1
git add $latestAudit.FullName
git commit -m "docs: add current routing debt audit"
```

If `docs/audits` has no tracked audit reports, leave the generated Markdown uncommitted and mention its path in the implementation closeout.

## Task 8: Full Verification

**Files:**
- No file edits expected.

- [ ] **Step 1: Run focused Python tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_current_routing_debt_erasure_policy.py -q
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate.py -q
python -m pytest tests/runtime_neutral/test_current_routing_debt_gate_docs.py -q
python -m pytest tests/runtime_neutral/test_current_routing_contract_cleanup.py -q
python -m pytest tests/runtime_neutral/test_retired_old_routing_compat.py -q
python -m pytest tests/unit/test_canonical_vibe_entry_launcher.py -q
python -m pytest tests/integration/test_canonical_vibe_truth_gate.py -q
python -m pytest tests/integration/test_verification_runtime_entrypoint_contract_cutover.py -q
```

Expected: all selected tests PASS.

- [ ] **Step 2: Run focused PowerShell gates**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-contract-gate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-current-routing-contract-scan.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-routing-terminology-hard-cleanup-scan.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-current-routing-debt-gate.ps1 -WriteArtifacts
```

Expected: all gates exit 0 and print PASS or `status: pass`.

- [ ] **Step 3: Run broader runtime-neutral suite**

Run:

```powershell
python -m pytest tests/runtime_neutral -q
```

Expected: PASS. If this suite reveals an unrelated existing failure, capture the failing test name and rerun the focused test to confirm whether it is caused by this branch.

- [ ] **Step 4: Check working tree**

Run:

```powershell
git status --short
```

Expected: only intentionally generated `outputs/verify/*` files may remain uncommitted. Source, tests, docs, and policy changes are committed.

## Task 9: Closeout Commit And Evidence Summary

**Files:**
- No new files unless Task 7 tracks the Markdown audit.

- [ ] **Step 1: Commit any source/test/docs changes left unstaged**

Run:

```powershell
git status --short
```

If source, tests, policy, or docs files remain modified, commit them:

```powershell
git add config/current-routing-debt-erasure.json scripts/verify/vibe-current-routing-debt-gate.ps1 scripts/verify/README.md scripts/verify/gate-family-index.md scripts/runtime/VibeRuntime.Common.ps1 scripts/runtime/legacy/VibeRetiredConsultation.Common.ps1 tests/runtime_neutral/test_current_routing_debt_erasure_policy.py tests/runtime_neutral/test_current_routing_debt_gate.py tests/runtime_neutral/test_current_routing_debt_gate_docs.py tests/runtime_neutral/test_current_routing_contract_cleanup.py tests/runtime_neutral/test_retired_old_routing_compat.py tests/unit/test_canonical_vibe_entry_launcher.py tests/integration/test_canonical_vibe_truth_gate.py tests/integration/test_verification_runtime_entrypoint_contract_cutover.py
git commit -m "feat: erase current routing retired terminology debt"
```

- [ ] **Step 2: Record verification evidence for the final response**

Collect these exact facts from the terminal output:

```text
pytest focused test result
tests/runtime_neutral suite result
vibe-current-routing-debt-gate status
vibe-current-routing-contract-scan status
vibe-routing-terminology-hard-cleanup-scan status
git status --short result
```

- [ ] **Step 3: Do not claim global zero old-term matches**

The closeout wording must say:

```text
Current runtime/router/docs/tests are clean for P0/P1/P2. Legacy, retired, historical, and fixture hits remain explicit and allowed.
```

Do not say:

```text
All old terms were removed from the repository.
```

That would be false because historical evidence remains by design.

## Self-Review Checklist

- Spec coverage: Tasks 1-3 implement the policy, audit, and gate. Tasks 4-5 remove or isolate current P1 debt. Task 6 wires the gate into the verify flow. Tasks 7-9 generate evidence and close out.
- Current fields: The plan keeps the current field chain as `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage.used / skill_usage.unused / skill_usage.evidence`.
- Retired fields: The plan blocks `legacy_skill_routing`, `specialist_recommendations`, `stage_assistant_hints`, root `specialist_dispatch`, `approved_consultation`, and `consulted_units` from current paths.
- Safety: The plan does not change the six governed stages, router scoring, bundled skills, install payload, or runtime freshness contract.
- Verification: The plan includes focused tests, existing scans, the new gate, and the runtime-neutral suite.
