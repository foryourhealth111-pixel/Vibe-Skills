param(
    [switch]$WriteArtifacts
)

$ErrorActionPreference = 'Stop'

function Add-Assertion {
    param(
        [System.Collections.Generic.List[object]]$Collection,
        [bool]$Condition,
        [string]$Message
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }

    [void]$Collection.Add([pscustomobject]@{
        ok = [bool]$Condition
        message = [string]$Message
    })
}

function Add-WarningNote {
    param(
        [System.Collections.Generic.List[string]]$Collection,
        [string]$Message
    )

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
    [void]$Collection.Add([string]$Message)
}

function Read-JsonFile {
    param([Parameter(Mandatory)] [string]$Path)

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Test-ContentPattern {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Pattern
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    return [bool](Select-String -LiteralPath $Path -Pattern $Pattern -SimpleMatch -Quiet)
}

function Find-MarkdownTableRow {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$RowStartsWith
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    foreach ($line in $lines) {
        $trimmed = [string]$line
        if ($trimmed.TrimStart().StartsWith($RowStartsWith)) {
            return $trimmed
        }
    }

    return $null
}

function Split-MarkdownTableCells {
    param([Parameter(Mandatory)] [string]$Line)

    $cells = @()
    foreach ($part in ($Line -split '\\|')) {
        $t = $part.Trim()
        if (-not [string]::IsNullOrWhiteSpace($t)) {
            $cells += $t
        }
    }
    return $cells
}

function Write-Artifacts {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $jsonPath = Join-Path $outputDir 'vibe-dist-manifest-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-dist-manifest-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Dist Manifest Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Release: `{0}` (updated `{1}`)' -f $Artifact.release.version, $Artifact.release.updated),
        ('- Assertion Failures: {0}' -f $Artifact.summary.failures),
        ('- Warnings: {0}' -f $Artifact.summary.warnings),
        ''
    )

    if ($Artifact.assertions.Count -gt 0) {
        $lines += '## Assertions'
        $lines += ''
        foreach ($item in $Artifact.assertions) {
            $lines += ('- [{0}] {1}' -f $(if ($item.ok) { 'PASS' } else { 'FAIL' }), $item.message)
        }
        $lines += ''
    }

    if ($Artifact.warnings.Count -gt 0) {
        $lines += '## Warnings'
        $lines += ''
        foreach ($item in $Artifact.warnings) {
            $lines += ('- {0}' -f $item)
        }
        $lines += ''
    }

    Write-VgoUtf8NoBomText -Path $mdPath -Content ($lines -join "`n")
}

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = [string]$context.repoRoot
$governance = $context.governance

$assertions = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]

$releaseVersion = if ($governance.release -and ($governance.release.PSObject.Properties.Name -contains 'version')) { [string]$governance.release.version } else { $null }
$releaseUpdated = if ($governance.release -and ($governance.release.PSObject.Properties.Name -contains 'updated')) { [string]$governance.release.updated } else { $null }

$results = [ordered]@{
    gate = 'vibe-dist-manifest-gate'
    repo_root = $repoRoot
    generated_at = (Get-Date).ToString('s')
    gate_result = 'FAIL'
    release = [ordered]@{
        version = $releaseVersion
        updated = $releaseUpdated
    }
    assertions = @()
    warnings = @()
    summary = [ordered]@{
        failures = 0
        warnings = 0
    }
    dist = [ordered]@{
        required_manifests = @()
    }
}

Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace($releaseVersion)) -Message '[governance] release.version is present'
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace($releaseUpdated)) -Message '[governance] release.updated is present'

$docsDistributionLanes = Join-Path $repoRoot 'docs\universalization\distribution-lanes.md'
$docsInstallMatrix = Join-Path $repoRoot 'docs\universalization\install-matrix.md'
$docsPlatformInstallMatrix = Join-Path $repoRoot 'docs\universalization\platform-install-matrix.md'
$docsPlatformSupportMatrix = Join-Path $repoRoot 'docs\universalization\platform-support-matrix.md'
$docsHostCapabilityMatrix = Join-Path $repoRoot 'docs\universalization\host-capability-matrix.md'

Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docsDistributionLanes) -Message '[docs] distribution-lanes.md exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docsInstallMatrix) -Message '[docs] install-matrix.md exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docsPlatformInstallMatrix) -Message '[docs] platform-install-matrix.md exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docsPlatformSupportMatrix) -Message '[docs] platform-support-matrix.md exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docsHostCapabilityMatrix) -Message '[docs] host-capability-matrix.md exists'

$requiredManifests = @(
    [pscustomobject]@{ lane_id = 'core'; path = 'dist/core/manifest.json' },
    [pscustomobject]@{ lane_id = 'official-runtime'; path = 'dist/official-runtime/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-codex'; path = 'dist/host-codex/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-claude-code'; path = 'dist/host-claude-code/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-cursor'; path = 'dist/host-cursor/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-windsurf'; path = 'dist/host-windsurf/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-openclaw'; path = 'dist/host-openclaw/manifest.json' },
    [pscustomobject]@{ lane_id = 'host-opencode'; path = 'dist/host-opencode/manifest.json' }
)
$results.dist.required_manifests = @($requiredManifests | ForEach-Object { $_.path })

$requiredPublicManifests = @(
    [pscustomobject]@{ package_id = 'vibeskills-core'; path = 'dist/manifests/vibeskills-core.json'; expected_status = 'supported-with-constraints' },
    [pscustomobject]@{ package_id = 'vibeskills-codex'; path = 'dist/manifests/vibeskills-codex.json'; expected_status = 'supported-with-constraints' },
    [pscustomobject]@{ package_id = 'vibeskills-claude-code'; path = 'dist/manifests/vibeskills-claude-code.json'; expected_status = 'preview' },
    [pscustomobject]@{ package_id = 'vibeskills-cursor'; path = 'dist/manifests/vibeskills-cursor.json'; expected_status = 'preview' },
    [pscustomobject]@{ package_id = 'vibeskills-windsurf'; path = 'dist/manifests/vibeskills-windsurf.json'; expected_status = 'preview' },
    [pscustomobject]@{ package_id = 'vibeskills-openclaw'; path = 'dist/manifests/vibeskills-openclaw.json'; expected_status = 'preview' },
    [pscustomobject]@{ package_id = 'vibeskills-opencode'; path = 'dist/manifests/vibeskills-opencode.json'; expected_status = 'not-yet-proven' },
    [pscustomobject]@{ package_id = 'vibeskills-generic'; path = 'dist/manifests/vibeskills-generic.json'; expected_status = 'advisory-only' }
)
$results.dist.public_manifests = @($requiredPublicManifests | ForEach-Object { $_.path })

$allowedLaneKinds = @('tier-1-official-runtime', 'universal-core', 'host-adapter')
$allowedStability = @('tier-1', 'preview', 'supported-with-constraints', 'not-yet-proven')
$allowedPlatformRatings = @('full-authoritative', 'supported-with-constraints', 'degraded-but-supported', 'not-yet-proven')

foreach ($item in $requiredManifests) {
    $manifestRel = [string]$item.path
    $manifestPath = Join-Path $repoRoot $manifestRel
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $manifestPath) -Message ("[dist] manifest exists: {0}" -f $manifestRel)

    $manifest = $null
    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $manifest = Read-JsonFile -Path $manifestPath
            Add-Assertion -Collection $assertions -Condition $true -Message ("[dist] manifest parses as JSON: {0}" -f $manifestRel)
        } catch {
            Add-Assertion -Collection $assertions -Condition $false -Message ("[dist] manifest parses as JSON: {0} -> {1}" -f $manifestRel, $_.Exception.Message)
        }
    }

    if ($null -eq $manifest) {
        continue
    }

    Add-Assertion -Collection $assertions -Condition ([int]$manifest.schema_version -eq 1) -Message ("[dist] schema_version == 1: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition ([string]$manifest.lane_id -eq [string]$item.lane_id) -Message ("[dist] lane_id matches expected ({0}): {1}" -f $item.lane_id, $manifestRel)
    Add-Assertion -Collection $assertions -Condition ($allowedLaneKinds -contains [string]$manifest.lane_kind) -Message ("[dist] lane_kind is allowed: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition ($allowedStability -contains [string]$manifest.stability) -Message ("[dist] stability is allowed: {0}" -f $manifestRel)

    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'summary' -and -not [string]::IsNullOrWhiteSpace([string]$manifest.summary)) -Message ("[dist] summary is present: {0}" -f $manifestRel)

    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'source_release' -and $null -ne $manifest.source_release) -Message ("[dist] source_release is present: {0}" -f $manifestRel)
    if ($manifest.PSObject.Properties.Name -contains 'source_release' -and $null -ne $manifest.source_release) {
        Add-Assertion -Collection $assertions -Condition ([string]$manifest.source_release.version -eq $releaseVersion) -Message ("[dist] source_release.version matches governance: {0}" -f $manifestRel)
        Add-Assertion -Collection $assertions -Condition ([string]$manifest.source_release.updated -eq $releaseUpdated) -Message ("[dist] source_release.updated matches governance: {0}" -f $manifestRel)
    }

    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'docs' -and $null -ne $manifest.docs) -Message ("[dist] docs references are present: {0}" -f $manifestRel)
    if ($manifest.PSObject.Properties.Name -contains 'docs' -and $null -ne $manifest.docs) {
        $docValues = @(
            [string]$manifest.docs.distribution_lanes,
            [string]$manifest.docs.install_matrix,
            [string]$manifest.docs.platform_install_matrix,
            [string]$manifest.docs.platform_support_matrix,
            [string]$manifest.docs.host_capability_matrix
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        foreach ($docRel in $docValues) {
            $docPath = Join-Path $repoRoot $docRel
            Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docPath) -Message ("[dist] referenced doc exists: {0} ({1})" -f $docRel, $manifestRel)
        }
    }

    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'capability_promises') -Message ("[dist] capability_promises is present: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition (@($manifest.capability_promises).Count -ge 1) -Message ("[dist] capability_promises is non-empty: {0}" -f $manifestRel)

    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'non_goals') -Message ("[dist] non_goals is present: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition (@($manifest.non_goals).Count -ge 1) -Message ("[dist] non_goals is non-empty: {0}" -f $manifestRel)

    foreach ($promise in @($manifest.capability_promises)) {
        $promiseId = if ($promise.PSObject.Properties.Name -contains 'id') { [string]$promise.id } else { $null }
        Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace($promiseId)) -Message ("[dist] promise has id: {0}" -f $manifestRel)
        if ($promise.PSObject.Properties.Name -contains 'evidence_paths') {
            foreach ($evidenceRel in @($promise.evidence_paths)) {
                if ([string]::IsNullOrWhiteSpace([string]$evidenceRel)) { continue }
                Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot ([string]$evidenceRel))) -Message ("[dist] evidence path exists: {0} ({1})" -f $evidenceRel, $manifestRel)
            }
        }
    }

    if ($manifest.lane_id -eq 'official-runtime' -or $manifest.lane_id -eq 'host-codex') {
        Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'entrypoints' -and $null -ne $manifest.entrypoints) -Message ("[dist] entrypoints are declared: {0}" -f $manifestRel)
        if ($manifest.PSObject.Properties.Name -contains 'entrypoints' -and $null -ne $manifest.entrypoints) {
            Add-Assertion -Collection $assertions -Condition ([string]$manifest.entrypoints.install_primary -eq 'install.ps1') -Message ("[dist] install_primary is install.ps1: {0}" -f $manifestRel)
            Add-Assertion -Collection $assertions -Condition ([string]$manifest.entrypoints.check_primary -eq 'check.ps1') -Message ("[dist] check_primary is check.ps1: {0}" -f $manifestRel)
            Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot ([string]$manifest.entrypoints.install_primary))) -Message ("[dist] install_primary exists: {0}" -f $manifestRel)
            Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot ([string]$manifest.entrypoints.check_primary))) -Message ("[dist] check_primary exists: {0}" -f $manifestRel)
        }
    } else {
        if ($manifest.PSObject.Properties.Name -contains 'entrypoints' -and $null -ne $manifest.entrypoints) {
            $installPrimary = if ($manifest.entrypoints.PSObject.Properties.Name -contains 'install_primary') { $manifest.entrypoints.install_primary } else { $null }
            $checkPrimary = if ($manifest.entrypoints.PSObject.Properties.Name -contains 'check_primary') { $manifest.entrypoints.check_primary } else { $null }
            if ($null -ne $installPrimary -or $null -ne $checkPrimary) {
                Add-WarningNote -Collection $warnings -Message ("lane {0} declares entrypoints; ensure it does not overclaim closure (manifest={1})." -f $manifest.lane_id, $manifestRel)
            }
        }
    }

    if ($manifest.PSObject.Properties.Name -contains 'support' -and $null -ne $manifest.support) {
        $platformSupport = $manifest.support.platform_support
        if ($null -ne $platformSupport -and ($platformSupport.PSObject.Properties.Name -contains 'interpretation')) {
            $interp = [string]$platformSupport.interpretation
            Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace($interp)) -Message ("[dist] platform_support.interpretation is present: {0}" -f $manifestRel)

            if ($interp -eq 'inherit_official_runtime') {
                Add-Assertion -Collection $assertions -Condition ($platformSupport.PSObject.Properties.Name -contains 'ratings' -and $null -ne $platformSupport.ratings) -Message ("[dist] platform_support.ratings declared for inherit_official_runtime: {0}" -f $manifestRel)
                if ($platformSupport.PSObject.Properties.Name -contains 'ratings' -and $null -ne $platformSupport.ratings) {
                    foreach ($key in @('windows','linux_pwsh','linux_no_pwsh','macos_pwsh','macos_no_pwsh')) {
                        $value = if ($platformSupport.ratings.PSObject.Properties.Name -contains $key) { [string]$platformSupport.ratings.$key } else { $null }
                        Add-Assertion -Collection $assertions -Condition ($allowedPlatformRatings -contains $value) -Message ("[dist] platform rating {0} is allowed ({1}): {2}" -f $key, $value, $manifestRel)
                    }
                }
            }
        }
    }
}

foreach ($item in $requiredPublicManifests) {
    $manifestRel = [string]$item.path
    $manifestPath = Join-Path $repoRoot $manifestRel
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $manifestPath) -Message ("[dist-public] manifest exists: {0}" -f $manifestRel)

    $manifest = $null
    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $manifest = Read-JsonFile -Path $manifestPath
            Add-Assertion -Collection $assertions -Condition $true -Message ("[dist-public] manifest parses as JSON: {0}" -f $manifestRel)
        } catch {
            Add-Assertion -Collection $assertions -Condition $false -Message ("[dist-public] manifest parses as JSON: {0} -> {1}" -f $manifestRel, $_.Exception.Message)
        }
    }

    if ($null -eq $manifest) {
        continue
    }

    Add-Assertion -Collection $assertions -Condition ([string]$manifest.manifest_kind -eq 'vibeskills-distribution-manifest') -Message ("[dist-public] manifest_kind is vibeskills-distribution-manifest: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition ([int]$manifest.manifest_version -eq 1) -Message ("[dist-public] manifest_version == 1: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition ([string]$manifest.package_id -eq [string]$item.package_id) -Message ("[dist-public] package_id matches expected ({0}): {1}" -f $item.package_id, $manifestRel)
    Add-Assertion -Collection $assertions -Condition ([string]$manifest.status -eq [string]$item.expected_status) -Message ("[dist-public] status matches expected ({0}): {1}" -f $item.expected_status, $manifestRel)
    Add-Assertion -Collection $assertions -Condition ($manifest.PSObject.Properties.Name -contains 'truth_sources') -Message ("[dist-public] truth_sources is present: {0}" -f $manifestRel)
    Add-Assertion -Collection $assertions -Condition (@($manifest.truth_sources).Count -ge 1) -Message ("[dist-public] truth_sources is non-empty: {0}" -f $manifestRel)

    foreach ($truthRel in @($manifest.truth_sources)) {
        if ([string]::IsNullOrWhiteSpace([string]$truthRel)) { continue }
        Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot ([string]$truthRel))) -Message ("[dist-public] truth source exists: {0} ({1})" -f $truthRel, $manifestRel)
    }
}

# Truth checks against existing host/platform truth docs (conservative, table-row based)

$hostCodexRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| Codex |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostCodexRow) -Message '[truth] host capability row for Codex exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| Codex | `supported-with-constraints` |') -Message '[truth] Codex host status remains supported-with-constraints in host capability matrix'

$hostClaudeRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| Claude Code |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostClaudeRow) -Message '[truth] host capability row for Claude Code exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| Claude Code | `preview` |') -Message '[truth] Claude Code host status remains preview in host capability matrix'

$hostCursorRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| Cursor |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostCursorRow) -Message '[truth] host capability row for Cursor exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| Cursor | `preview` |') -Message '[truth] Cursor host status remains preview in host capability matrix'

$hostWindsurfRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| Windsurf |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostWindsurfRow) -Message '[truth] host capability row for Windsurf exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| Windsurf | `preview` |') -Message '[truth] Windsurf host status remains preview in host capability matrix'

$hostOpenClawRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| OpenClaw |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostOpenClawRow) -Message '[truth] host capability row for OpenClaw exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| OpenClaw | `preview` |') -Message '[truth] OpenClaw host status remains preview in host capability matrix'

$hostOpenCodeRow = Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| OpenCode |'
Add-Assertion -Collection $assertions -Condition ($null -ne $hostOpenCodeRow) -Message '[truth] host capability row for OpenCode exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsHostCapabilityMatrix -Pattern '| OpenCode | `not-yet-proven` |') -Message '[truth] OpenCode host status remains not-yet-proven in host capability matrix'

$platformWindowsRow = Find-MarkdownTableRow -Path $docsPlatformSupportMatrix -RowStartsWith '| Windows |'
Add-Assertion -Collection $assertions -Condition ($null -ne $platformWindowsRow) -Message '[truth] platform row for Windows exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsPlatformSupportMatrix -Pattern '| Windows | `install.ps1`, `one-shot-setup.ps1` | `check.ps1` | strongest current path for PowerShell-first gates | `full-authoritative` |') -Message '[truth] Windows platform rating remains full-authoritative in platform support matrix'

Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsPlatformSupportMatrix -Pattern 'Linux without `pwsh` is an honest degraded path') -Message '[truth] platform support matrix documents degraded-without-pwsh truth'

foreach ($lane in @('official-runtime','core','host-codex','host-claude-code','host-cursor','host-windsurf','host-openclaw','host-opencode')) {
    Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsDistributionLanes -Pattern ('`{0}`' -f $lane)) -Message ("[docs] distribution-lanes.md mentions lane {0}" -f $lane)
    Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $docsInstallMatrix -Pattern ('`{0}`' -f $lane)) -Message ("[docs] install-matrix.md mentions lane {0}" -f $lane)
}

$results.assertions = @($assertions.ToArray())
$results.warnings = @($warnings.ToArray())
$results.summary.failures = @($assertions | Where-Object { -not $_.ok }).Count
$results.summary.warnings = $warnings.Count
$results.gate_result = if ($results.summary.failures -eq 0) { 'PASS' } else { 'FAIL' }

if ($WriteArtifacts) {
    Write-Artifacts -RepoRoot $repoRoot -Artifact ([pscustomobject]$results)
}

if ($results.summary.failures -gt 0) {
    exit 1
}
