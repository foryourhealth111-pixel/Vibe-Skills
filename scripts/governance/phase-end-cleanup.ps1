param(
    [switch]$WriteArtifacts,
    [switch]$IncludeMirrorGates,
    [switch]$SkipInventory,
    [switch]$SkipTmpPurge,
    [switch]$SkipLocalExcludeInstall,
    [switch]$SkipNodeAudit,
    [switch]$SkipNodeCleanup,
    [switch]$ApplyManagedNodeCleanup,
    [switch]$PreviewOnly,
    [string]$TmpRootOverride = '',
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\common\ProtectedDocumentCleanup.ps1')

function Invoke-VgoPhaseEndStep {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Kind,
        [Parameter(Mandatory)] [scriptblock]$Action,
        [Parameter(Mandatory)] [System.Collections.Generic.List[object]]$Steps
    )

    try {
        $result = & $Action
        $Steps.Add([pscustomobject]@{
                name = $Name
                kind = $Kind
                status = 'passed'
                details = $result
            }) | Out-Null
        return $result
    } catch {
        $Steps.Add([pscustomobject]@{
                name = $Name
                kind = $Kind
                status = 'failed'
                error = $_.Exception.Message
            }) | Out-Null
        throw
    }
}

function Resolve-CleanupArtifactsDirectory {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$OutputDirectory
    )

    if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
        return [System.IO.Path]::GetFullPath($OutputDirectory)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot 'outputs\verify'))
}

$context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
$repoRoot = $context.repoRoot
$steps = [System.Collections.Generic.List[object]]::new()
$gateArgs = @()
if ($WriteArtifacts) {
    $gateArgs += '-WriteArtifacts'
}
if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $gateArgs += @('-OutputDirectory', $OutputDirectory)
}

$policy = Get-VgoProtectedDocumentCleanupPolicy -RepoRoot $repoRoot
$cleanupOperatorContract = if ($policy.PSObject.Properties.Name -contains 'operator_contract' -and $null -ne $policy.operator_contract) { $policy.operator_contract } else { [pscustomobject]@{ preview_only_supported = $false; preview_only_switch = ''; protected_tmp_default_action = [string]$policy.protected_document_policy.default_action_mode; protected_tmp_quarantine_required = $false; quarantine_handler = '' } }
if ($PreviewOnly -and -not [bool]$cleanupOperatorContract.preview_only_supported) { throw 'phase cleanup policy does not declare preview-only support.' }
$tmpRoot = if ([string]::IsNullOrWhiteSpace($TmpRootOverride)) {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot '.tmp'))
} else {
    [System.IO.Path]::GetFullPath($TmpRootOverride)
}
$artifactsDir = Resolve-CleanupArtifactsDirectory -RepoRoot $repoRoot -OutputDirectory $OutputDirectory
$quarantineRelative = [string]$policy.protected_document_policy.quarantine_root
$quarantineRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $quarantineRelative))
$documentExtensions = Get-VgoProtectedDocumentExtensions -Policy $policy
$protectedManifest = Get-VgoProtectedDocumentManifest -RepoRoot $repoRoot -Policy $policy -TmpRoot $tmpRoot
$quarantined = @()

if ($WriteArtifacts) {
    New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
    Write-VgoUtf8NoBomText -Path (Join-Path $artifactsDir 'phase-end-cleanup-protected-document-manifest.json') -Content ($protectedManifest | ConvertTo-Json -Depth 100)
}

$steps.Add([pscustomobject]@{
        name = 'snapshot-protected-document-assets'
        kind = 'cleanup'
        status = 'passed'
        details = [pscustomobject]@{
            protected_total = $protectedManifest.summary.protected_total
            tmp_protected_total = $protectedManifest.summary.tmp_protected_total
            retained_outside_tmp_total = $protectedManifest.summary.retained_outside_tmp_total
        }
    }) | Out-Null

if (-not $SkipTmpPurge) {
    if ($PreviewOnly) {
        $steps.Add([pscustomobject]@{
                name = 'tmp-purge'
                kind = 'cleanup'
                status = 'skipped'
                details = [pscustomobject]@{
                    preview_only = $true
                    tmp_exists = [bool](Test-Path -LiteralPath $tmpRoot)
                    candidate_protected_document_count = $protectedManifest.summary.tmp_protected_total
                    quarantine_root = $quarantineRoot
                }
            }) | Out-Null
    } else {
        $tmpRemoved = Invoke-VgoPhaseEndStep -Name 'tmp-purge' -Kind 'cleanup' -Steps $steps -Action {
            if (Test-Path -LiteralPath $tmpRoot) {
                $quarantinedItems = Move-VgoProtectedDocumentsToQuarantine -TmpRoot $tmpRoot -QuarantineRoot $quarantineRoot -Extensions $documentExtensions
                $script:quarantined = @($quarantinedItems)
                Remove-Item -LiteralPath $tmpRoot -Recurse -Force
                return [pscustomobject]@{
                    removed = $true
                    quarantined_count = @($quarantinedItems).Count
                    quarantine_root = $quarantineRoot
                }
            }

            return [pscustomobject]@{
                removed = $false
                quarantined_count = 0
                quarantine_root = $quarantineRoot
            }
        }
        if ($WriteArtifacts) {
            Write-VgoUtf8NoBomText -Path (Join-Path $artifactsDir 'phase-end-cleanup-protected-document-quarantine.json') -Content (($quarantined | ConvertTo-Json -Depth 100))
        }
    }
} else {
    $steps.Add([pscustomobject]@{
            name = 'tmp-purge'
            kind = 'cleanup'
            status = 'skipped'
        }) | Out-Null
}

$protectedAssertions = @(Test-VgoProtectedDocumentPostConditions -Manifest $protectedManifest -QuarantinedItems $quarantined)
$protectedFailures = @($protectedAssertions | Where-Object { -not $_.pass }).Count
$steps.Add([pscustomobject]@{
        name = 'protected-document-post-checks'
        kind = 'cleanup'
        status = $(if ($protectedFailures -eq 0) { 'passed' } else { 'failed' })
        details = [pscustomobject]@{
            total = @($protectedAssertions).Count
            failure_count = $protectedFailures
            assertions = @($protectedAssertions)
        }
    }) | Out-Null
if ($protectedFailures -gt 0) {
    throw 'Protected document cleanup post-checks failed.'
}

if (-not $SkipLocalExcludeInstall) {
    Invoke-VgoPhaseEndStep -Name 'install-local-worktree-excludes' -Kind 'governance' -Steps $steps -Action {
        & (Join-Path $repoRoot 'scripts\governance\install-local-worktree-excludes.ps1')
    } | Out-Null
} else {
    $steps.Add([pscustomobject]@{
            name = 'install-local-worktree-excludes'
            kind = 'governance'
            status = 'skipped'
        }) | Out-Null
}

if (-not $SkipInventory) {
    Invoke-VgoPhaseEndStep -Name 'export-repo-cleanliness-inventory' -Kind 'governance' -Steps $steps -Action {
        & (Join-Path $repoRoot 'scripts\governance\export-repo-cleanliness-inventory.ps1') @gateArgs
    } | Out-Null
} else {
    $steps.Add([pscustomobject]@{
            name = 'export-repo-cleanliness-inventory'
            kind = 'governance'
            status = 'skipped'
        }) | Out-Null
}

Invoke-VgoPhaseEndStep -Name 'vibe-repo-cleanliness-gate' -Kind 'verify' -Steps $steps -Action {
    & (Join-Path $repoRoot 'scripts\verify\vibe-repo-cleanliness-gate.ps1') @gateArgs
} | Out-Null

Invoke-VgoPhaseEndStep -Name 'vibe-output-artifact-boundary-gate' -Kind 'verify' -Steps $steps -Action {
    & (Join-Path $repoRoot 'scripts\verify\vibe-output-artifact-boundary-gate.ps1') @gateArgs
} | Out-Null

if ($IncludeMirrorGates) {
    Invoke-VgoPhaseEndStep -Name 'vibe-mirror-edit-hygiene-gate' -Kind 'verify' -Steps $steps -Action {
        & (Join-Path $repoRoot 'scripts\verify\vibe-mirror-edit-hygiene-gate.ps1') @gateArgs
    } | Out-Null

    Invoke-VgoPhaseEndStep -Name 'vibe-nested-bundled-parity-gate' -Kind 'verify' -Steps $steps -Action {
        & (Join-Path $repoRoot 'scripts\verify\vibe-nested-bundled-parity-gate.ps1') @gateArgs
    } | Out-Null

    Invoke-VgoPhaseEndStep -Name 'vibe-version-packaging-gate' -Kind 'verify' -Steps $steps -Action {
        & (Join-Path $repoRoot 'scripts\verify\vibe-version-packaging-gate.ps1') @gateArgs
    } | Out-Null
}

if (-not $SkipNodeAudit) {
    Invoke-VgoPhaseEndStep -Name 'Invoke-NodeProcessAudit' -Kind 'governance' -Steps $steps -Action {
        if ($WriteArtifacts) {
            & (Join-Path $repoRoot 'scripts\governance\Invoke-NodeProcessAudit.ps1') -WriteMarkdown
        } else {
            & (Join-Path $repoRoot 'scripts\governance\Invoke-NodeProcessAudit.ps1')
        }
    } | Out-Null
} else {
    $steps.Add([pscustomobject]@{
            name = 'Invoke-NodeProcessAudit'
            kind = 'governance'
            status = 'skipped'
        }) | Out-Null
}

if (-not $SkipNodeCleanup) {
    Invoke-VgoPhaseEndStep -Name 'Invoke-NodeZombieCleanup' -Kind 'governance' -Steps $steps -Action {
        if ($ApplyManagedNodeCleanup) {
            & (Join-Path $repoRoot 'scripts\governance\Invoke-NodeZombieCleanup.ps1') -Apply
        } else {
            & (Join-Path $repoRoot 'scripts\governance\Invoke-NodeZombieCleanup.ps1')
        }
    } | Out-Null
} else {
    $steps.Add([pscustomobject]@{
            name = 'Invoke-NodeZombieCleanup'
            kind = 'governance'
            status = 'skipped'
        }) | Out-Null
}

[pscustomobject]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    repo_root = $repoRoot
    tmp_root = $tmpRoot
    preview_only = [bool]$PreviewOnly
    write_artifacts = [bool]$WriteArtifacts
    include_mirror_gates = [bool]$IncludeMirrorGates
    apply_managed_node_cleanup = [bool]$ApplyManagedNodeCleanup
    operator_contract = [pscustomobject]@{
        preview_only_supported = [bool]$cleanupOperatorContract.preview_only_supported
        preview_only_switch = [string]$cleanupOperatorContract.preview_only_switch
        protected_tmp_default_action = [string]$cleanupOperatorContract.protected_tmp_default_action
        protected_tmp_quarantine_required = [bool]$cleanupOperatorContract.protected_tmp_quarantine_required
        quarantine_handler = [string]$cleanupOperatorContract.quarantine_handler
    }
    protected_document_summary = [pscustomobject]@{
        protected_total = $protectedManifest.summary.protected_total
        tmp_protected_total = $protectedManifest.summary.tmp_protected_total
        retained_outside_tmp_total = $protectedManifest.summary.retained_outside_tmp_total
        quarantined_total = @($quarantined).Count
        quarantine_root = $quarantineRoot
    }
    steps = @($steps)
} | ConvertTo-Json -Depth 10
