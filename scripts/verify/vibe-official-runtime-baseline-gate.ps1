param(
    [string]$TargetRoot = '',
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

function Write-Artifacts {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [psobject]$Artifact
    )

    $outputDir = Join-Path $RepoRoot 'outputs\verify'
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $jsonPath = Join-Path $outputDir 'vibe-official-runtime-baseline-gate.json'
    $mdPath = Join-Path $outputDir 'vibe-official-runtime-baseline-gate.md'

    Write-VgoUtf8NoBomText -Path $jsonPath -Content ($Artifact | ConvertTo-Json -Depth 100)

    $lines = @(
        '# VCO Official Runtime Baseline Gate',
        '',
        ('- Gate Result: **{0}**' -f $Artifact.gate_result),
        ('- Repo Root: `{0}`' -f $Artifact.repo_root),
        ('- Target Root: `{0}`' -f $Artifact.target_root),
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

$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$governance = $context.governance
$packaging = $context.packaging
$runtimeConfig = $context.runtimeConfig

$repoRoot = [string]$context.repoRoot
$targetRootFull = [System.IO.Path]::GetFullPath($TargetRoot)

$assertions = New-Object System.Collections.Generic.List[object]
$warnings = New-Object System.Collections.Generic.List[string]

$docPath = Join-Path $repoRoot 'docs\universalization\official-runtime-baseline.md'
$bundleReadmePath = Join-Path $repoRoot 'references\proof-bundles\official-runtime-baseline\README.md'
$manifestPath = Join-Path $repoRoot 'references\proof-bundles\official-runtime-baseline\baseline-manifest.json'

$installPs1 = Join-Path $repoRoot 'install.ps1'
$installAdapterPs1 = Join-Path $repoRoot 'scripts\install\Install-VgoAdapter.ps1'
$checkPs1 = Join-Path $repoRoot 'check.ps1'
$installSh = Join-Path $repoRoot 'install.sh'
$checkSh = Join-Path $repoRoot 'check.sh'

$results = [ordered]@{
    gate = 'vibe-official-runtime-baseline-gate'
    repo_root = $repoRoot
    target_root = $targetRootFull
    generated_at = (Get-Date).ToString('s')
    gate_result = 'FAIL'
    release = [ordered]@{
        version = if ($governance.release -and ($governance.release.PSObject.Properties.Name -contains 'version')) { [string]$governance.release.version } else { $null }
        updated = if ($governance.release -and ($governance.release.PSObject.Properties.Name -contains 'updated')) { [string]$governance.release.updated } else { $null }
        channel = if ($governance.release -and ($governance.release.PSObject.Properties.Name -contains 'channel')) { [string]$governance.release.channel } else { $null }
    }
    contract = [ordered]@{
        doc = 'docs/universalization/official-runtime-baseline.md'
        proof_bundle = 'references/proof-bundles/official-runtime-baseline'
        manifest = 'references/proof-bundles/official-runtime-baseline/baseline-manifest.json'
        runtime = [ordered]@{
            target_relpath = [string]$runtimeConfig.target_relpath
            receipt_relpath = [string]$runtimeConfig.receipt_relpath
            receipt_contract_version = [int]$runtimeConfig.receipt_contract_version
            post_install_gate = [string]$runtimeConfig.post_install_gate
            frontmatter_gate = if ($runtimeConfig.PSObject.Properties.Name -contains 'frontmatter_gate') { [string]$runtimeConfig.frontmatter_gate } else { $null }
            coherence_gate = [string]$runtimeConfig.coherence_gate
            shell_degraded_behavior = [string]$runtimeConfig.shell_degraded_behavior
            required_runtime_markers_count = @($runtimeConfig.required_runtime_markers).Count
        }
        packaging = [ordered]@{
            mirror_files = @($packaging.mirror.files)
            mirror_directories = @($packaging.mirror.directories)
            manifests = @($packaging.manifests)
        }
    }
    assertions = @()
    warnings = @()
    summary = [ordered]@{
        failures = 0
        warnings = 0
    }
}

Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $docPath) -Message '[docs] official runtime baseline doc exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $bundleReadmePath) -Message '[proof-bundle] README exists'
Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $manifestPath) -Message '[proof-bundle] baseline manifest exists'

Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$results.release.version)) -Message '[governance] release.version is present'
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$results.release.updated)) -Message '[governance] release.updated is present'

$manifest = $null
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        Add-Assertion -Collection $assertions -Condition $true -Message '[proof-bundle] baseline manifest parses as JSON'
    } catch {
        Add-Assertion -Collection $assertions -Condition $false -Message ('[proof-bundle] baseline manifest parses as JSON -> {0}' -f $_.Exception.Message)
    }
}

if ($null -ne $manifest) {
    $manifestReleaseVersion = if ($manifest.PSObject.Properties.Name -contains 'source_release' -and $manifest.source_release -and ($manifest.source_release.PSObject.Properties.Name -contains 'version')) { [string]$manifest.source_release.version } else { $null }
    $manifestReleaseUpdated = if ($manifest.PSObject.Properties.Name -contains 'source_release' -and $manifest.source_release -and ($manifest.source_release.PSObject.Properties.Name -contains 'updated')) { [string]$manifest.source_release.updated } else { $null }
    Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$manifestReleaseVersion)) -Message '[manifest] source_release.version is present'
    Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$manifestReleaseUpdated)) -Message '[manifest] source_release.updated is present'

    if (-not [string]::IsNullOrWhiteSpace([string]$results.release.version) -and -not [string]::IsNullOrWhiteSpace([string]$manifestReleaseVersion)) {
        Add-Assertion -Collection $assertions -Condition ([string]$manifestReleaseVersion -eq [string]$results.release.version) -Message '[manifest] source_release.version matches config/version-governance.json release.version'
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$results.release.updated) -and -not [string]::IsNullOrWhiteSpace([string]$manifestReleaseUpdated)) {
        Add-Assertion -Collection $assertions -Condition ([string]$manifestReleaseUpdated -eq [string]$results.release.updated) -Message '[manifest] source_release.updated matches config/version-governance.json release.updated'
    }

    $requiredProtectedPaths = @(
        'install.ps1',
        'install.sh',
        'check.ps1',
        'check.sh',
        'scripts/bootstrap',
        'scripts/router',
        'config/version-governance.json'
    )
    foreach ($requiredPath in $requiredProtectedPaths) {
        Add-Assertion -Collection $assertions -Condition (@($manifest.protected_paths) -contains [string]$requiredPath) -Message ("[manifest] protected_paths includes {0}" -f $requiredPath)
        Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $requiredPath)) -Message ("[repo] protected path exists: {0}" -f $requiredPath)
    }

    $requiredAuthorityContracts = @(
        'docs/universalization/official-runtime-baseline.md',
        'config/version-governance.json',
        'scripts/router/resolve-pack-route.ps1'
    )
    foreach ($requiredPath in $requiredAuthorityContracts) {
        Add-Assertion -Collection $assertions -Condition (@($manifest.authority_contracts) -contains [string]$requiredPath) -Message ("[manifest] authority_contracts includes {0}" -f $requiredPath)
        Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $requiredPath)) -Message ("[repo] authority contract exists: {0}" -f $requiredPath)
    }

    $requiredGates = @(
        'scripts/verify/vibe-pack-routing-smoke.ps1',
        'scripts/verify/vibe-router-contract-gate.ps1',
        'scripts/verify/vibe-version-consistency-gate.ps1',
        'scripts/verify/vibe-version-packaging-gate.ps1'
    )
    foreach ($runtimeGate in @([string]$runtimeConfig.post_install_gate, [string]$runtimeConfig.frontmatter_gate, [string]$runtimeConfig.coherence_gate)) {
        if (-not [string]::IsNullOrWhiteSpace($runtimeGate) -and -not (@($requiredGates) -contains $runtimeGate)) {
            $requiredGates += $runtimeGate
        }
    }
    foreach ($requiredGate in $requiredGates) {
        Add-Assertion -Collection $assertions -Condition (@($manifest.minimum_non_regression_gates) -contains [string]$requiredGate) -Message ("[manifest] minimum_non_regression_gates includes {0}" -f $requiredGate)
        Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $requiredGate)) -Message ("[repo] required gate exists: {0}" -f $requiredGate)
    }
}

$expectedMirrorFiles = @('SKILL.md', 'check.ps1', 'check.sh', 'install.ps1', 'install.sh')
foreach ($file in $expectedMirrorFiles) {
    Add-Assertion -Collection $assertions -Condition (@($packaging.mirror.files) -contains [string]$file) -Message ("[packaging] mirror.files includes {0}" -f $file)
}

$expectedMirrorDirs = @('templates', 'mcp')
foreach ($dir in $expectedMirrorDirs) {
    Add-Assertion -Collection $assertions -Condition (@($packaging.mirror.directories) -contains [string]$dir) -Message ("[packaging] mirror.directories includes {0}" -f $dir)
}

$forbiddenMirrorDirs = @('config', 'scripts', 'docs', 'references', 'protocols')
foreach ($dir in $forbiddenMirrorDirs) {
    Add-Assertion -Collection $assertions -Condition (-not (@($packaging.mirror.directories) -contains [string]$dir)) -Message ("[packaging] mirror.directories excludes broad root {0}" -f $dir)
}

$expectedManifestFiles = @('config/runtime-script-manifest.json', 'config/runtime-config-manifest.json')
foreach ($file in $expectedManifestFiles) {
    Add-Assertion -Collection $assertions -Condition (@($packaging.mirror.files) -contains [string]$file) -Message ("[packaging] mirror.files includes manifest {0}" -f $file)
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $file)) -Message ("[repo] manifest exists: {0}" -f $file)
}

$manifestPaths = @($packaging.manifests | ForEach-Object { [string]$_.path })
foreach ($manifestPath in $expectedManifestFiles) {
    Add-Assertion -Collection $assertions -Condition ($manifestPaths -contains $manifestPath) -Message ("[packaging] manifests declares {0}" -f $manifestPath)
}

Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.target_relpath)) -Message '[runtime] target_relpath is present'
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.receipt_relpath)) -Message '[runtime] receipt_relpath is present'
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.post_install_gate)) -Message '[runtime] post_install_gate is present'
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.coherence_gate)) -Message '[runtime] coherence_gate is present'

$declaredFrontmatterGate = $null
if ($governance.PSObject.Properties.Name -contains 'runtime' -and $null -ne $governance.runtime) {
    if ($governance.runtime.PSObject.Properties.Name -contains 'installed_runtime' -and $null -ne $governance.runtime.installed_runtime) {
        $installedRuntimeNode = $governance.runtime.installed_runtime
        if ($installedRuntimeNode.PSObject.Properties.Name -contains 'frontmatter_gate') {
            $declaredFrontmatterGate = [string]$installedRuntimeNode.frontmatter_gate
        }
        if ($installedRuntimeNode.PSObject.Properties.Name -contains 'shell_degraded_behavior') {
            Add-Assertion -Collection $assertions -Condition ([string]$installedRuntimeNode.shell_degraded_behavior -eq 'warn_and_skip_authoritative_runtime_gate') -Message '[runtime] shell_degraded_behavior declares warn-and-skip semantics'
        }
    }
}
Add-Assertion -Collection $assertions -Condition (-not [string]::IsNullOrWhiteSpace([string]$declaredFrontmatterGate)) -Message '[runtime] frontmatter_gate is declared in config/version-governance.json'
if (-not [string]::IsNullOrWhiteSpace([string]$declaredFrontmatterGate)) {
    Add-Assertion -Collection $assertions -Condition ([string]$declaredFrontmatterGate -eq [string]$runtimeConfig.frontmatter_gate) -Message '[runtime] frontmatter_gate declaration matches effective runtime contract'
}

$postInstallGatePath = if (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.post_install_gate)) { Join-Path $repoRoot ([string]$runtimeConfig.post_install_gate) } else { $null }
$frontmatterGatePath = if ($runtimeConfig.PSObject.Properties.Name -contains 'frontmatter_gate' -and -not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.frontmatter_gate)) { Join-Path $repoRoot ([string]$runtimeConfig.frontmatter_gate) } else { $null }
$coherenceGatePath = if (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.coherence_gate)) { Join-Path $repoRoot ([string]$runtimeConfig.coherence_gate) } else { $null }

if ($null -ne $postInstallGatePath) {
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $postInstallGatePath) -Message '[runtime] post-install gate script exists'
}
if ($null -ne $frontmatterGatePath) {
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $frontmatterGatePath) -Message '[runtime] BOM/frontmatter gate script exists'
}
if ($null -ne $coherenceGatePath) {
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $coherenceGatePath) -Message '[runtime] coherence gate script exists'
}

$requiredRuntimeMarkers = @($runtimeConfig.required_runtime_markers)
Add-Assertion -Collection $assertions -Condition ($requiredRuntimeMarkers.Count -gt 0) -Message '[runtime] required_runtime_markers is non-empty'
foreach ($marker in $requiredRuntimeMarkers) {
    $markerText = [string]$marker
    if ([string]::IsNullOrWhiteSpace($markerText)) {
        continue
    }
    Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $markerText)) -Message ("[runtime] required marker exists: {0}" -f $markerText)
}

if (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.post_install_gate)) {
    Add-Assertion -Collection $assertions -Condition (@($requiredRuntimeMarkers) -contains [string]$runtimeConfig.post_install_gate) -Message '[runtime] required_runtime_markers includes post-install freshness gate'
}
if (-not [string]::IsNullOrWhiteSpace([string]$runtimeConfig.coherence_gate)) {
    Add-Assertion -Collection $assertions -Condition (@($requiredRuntimeMarkers) -contains [string]$runtimeConfig.coherence_gate) -Message '[runtime] required_runtime_markers includes coherence gate'
}

Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $installPs1) -Message '[install.ps1] exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $installPs1 -Pattern 'Invoke-InstalledRuntimeFreshnessGate') -Message '[install.ps1] references Invoke-InstalledRuntimeFreshnessGate'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $installPs1 -Pattern 'plugins-manifest.codex.json') -Message '[install.ps1] references plugins-manifest.codex.json'
Add-Assertion -Collection $assertions -Condition ((Test-ContentPattern -Path $installPs1 -Pattern 'settings.template.codex.json') -or (Test-ContentPattern -Path $installAdapterPs1 -Pattern 'settings.template.codex.json')) -Message '[install flow] references settings template'

Add-Assertion -Collection $assertions -Condition (Test-Path -LiteralPath $checkPs1) -Message '[check.ps1] exists'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $checkPs1 -Pattern 'Invoke-RuntimeFreshnessCheck') -Message '[check.ps1] references runtime freshness check'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $checkPs1 -Pattern 'Invoke-RuntimeFrontmatterCheck') -Message '[check.ps1] references runtime BOM/frontmatter check'
Add-Assertion -Collection $assertions -Condition (Test-ContentPattern -Path $checkPs1 -Pattern 'Invoke-RuntimeCoherenceCheck') -Message '[check.ps1] references runtime coherence check'

if (-not (Test-Path -LiteralPath $installSh)) {
    Add-Assertion -Collection $assertions -Condition $false -Message '[install.sh] exists'
}
if (-not (Test-Path -LiteralPath $checkSh)) {
    Add-Assertion -Collection $assertions -Condition $false -Message '[check.sh] exists'
}

$receiptPath = Join-Path $targetRootFull ([string]$runtimeConfig.receipt_relpath)
if (Test-Path -LiteralPath $receiptPath) {
    try {
        $receipt = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $receiptGateResult = if ($receipt.PSObject.Properties.Name -contains 'gate_result') { [string]$receipt.gate_result } else { $null }
        $receiptVersion = if ($receipt.PSObject.Properties.Name -contains 'receipt_version') { [int]$receipt.receipt_version } else { 0 }
        Add-Assertion -Collection $assertions -Condition ($receiptGateResult -eq 'PASS') -Message '[receipt] installed runtime receipt gate_result is PASS'
        Add-Assertion -Collection $assertions -Condition ($receiptVersion -ge [int]$runtimeConfig.receipt_contract_version) -Message '[receipt] installed runtime receipt version satisfies contract'
    } catch {
        Add-Assertion -Collection $assertions -Condition $false -Message ('[receipt] installed runtime receipt parses cleanly -> {0}' -f $_.Exception.Message)
    }
} else {
    Add-WarningNote -Collection $warnings -Message ('runtime receipt not found at {0}; baseline gate validated repo contract without installed-runtime evidence.' -f $receiptPath)
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
