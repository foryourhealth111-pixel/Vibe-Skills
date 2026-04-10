Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Get-VibeHostAdapterEntry {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$HostId = ''
    )

    return Resolve-VgoAdapterEntry -StartPath $RepoRoot -HostId $HostId
}

function Resolve-VibeHostTargetRoot {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    if ($null -eq $HostAdapter -or $null -eq $HostAdapter.default_target_root) {
        return $null
    }

    $targetSpec = $HostAdapter.default_target_root
    $envName = if ($targetSpec.PSObject.Properties.Name -contains 'env') { [string]$targetSpec.env } else { '' }
    $rel = if ($targetSpec.PSObject.Properties.Name -contains 'rel') { [string]$targetSpec.rel } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $envValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($envValue)) {
            return [System.IO.Path]::GetFullPath($envValue)
        }
    }
    if ([string]::IsNullOrWhiteSpace($rel)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($rel)) {
        return [System.IO.Path]::GetFullPath($rel)
    }
    $homeDir = Resolve-VgoHomeDirectory
    return [System.IO.Path]::GetFullPath((Join-Path $homeDir $rel))
}

function Get-VibeRelativePathCompat {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)

    if ($baseFull -eq $targetFull) {
        return '.'
    }

    if ($baseFull.Substring(0, 1).ToUpperInvariant() -ne $targetFull.Substring(0, 1).ToUpperInvariant()) {
        return $targetFull
    }

    $baseWithSeparator = $baseFull.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $baseUri = New-Object System.Uri($baseWithSeparator)
    $targetUri = New-Object System.Uri($targetFull)
    $relative = [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString())
    return $relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Test-VibePathWithinRoot {
    param(
        [Parameter(Mandatory)] [string]$RootPath,
        [Parameter(Mandatory)] [string]$CandidatePath
    )

    $rootFull = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\', '/')
    $candidateFull = [System.IO.Path]::GetFullPath($CandidatePath).TrimEnd('\', '/')

    if ($rootFull.Length -eq 0 -or $candidateFull.Length -eq 0) {
        return $false
    }

    if ($rootFull.Equals($candidateFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    $rootWithDirectorySeparator = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    $rootWithAltDirectorySeparator = $rootFull + [System.IO.Path]::AltDirectorySeparatorChar

    return (
        $candidateFull.StartsWith($rootWithDirectorySeparator, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($rootWithAltDirectorySeparator, [System.StringComparison]::OrdinalIgnoreCase)
    )
}

function Test-VibeObjectHasProperty {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName
    )

    if ($null -eq $InputObject -or [string]::IsNullOrWhiteSpace($PropertyName)) {
        return $false
    }

    $propertyNames = @($InputObject.PSObject.Properties | ForEach-Object { [string]$_.Name })
    return ($propertyNames -contains $PropertyName)
}

function Get-VibeHostAdapterIdentityProjection {
    param(
        [AllowNull()] [object]$HostAdapter,
        [AllowEmptyString()] [string]$RequestedPropertyName = 'requested_id',
        [AllowEmptyString()] [string]$EffectivePropertyName = 'id',
        [AllowEmptyString()] [string]$FallbackHostId = ''
    )

    $requestedHostId = if ([string]::IsNullOrWhiteSpace($FallbackHostId)) { $null } else { [string]$FallbackHostId }
    $effectiveHostId = if ([string]::IsNullOrWhiteSpace($FallbackHostId)) { $null } else { [string]$FallbackHostId }

    if ($null -ne $HostAdapter) {
        $requestedFields = @($RequestedPropertyName, 'requested_id', 'requested_host_id', 'id', 'effective_host_id') | Select-Object -Unique
        $effectiveFields = @($EffectivePropertyName, 'id', 'effective_host_id', 'requested_id', 'requested_host_id') | Select-Object -Unique

        foreach ($field in @($requestedFields)) {
            if (Test-VibeObjectHasProperty -InputObject $HostAdapter -PropertyName $field) {
                $candidateRequestedHostId = [string]$HostAdapter.$field
                if (-not [string]::IsNullOrWhiteSpace($candidateRequestedHostId)) {
                    $requestedHostId = $candidateRequestedHostId
                    break
                }
            }
        }
        foreach ($field in @($effectiveFields)) {
            if (Test-VibeObjectHasProperty -InputObject $HostAdapter -PropertyName $field) {
                $candidateEffectiveHostId = [string]$HostAdapter.$field
                if (-not [string]::IsNullOrWhiteSpace($candidateEffectiveHostId)) {
                    $effectiveHostId = $candidateEffectiveHostId
                    break
                }
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($requestedHostId) -and -not [string]::IsNullOrWhiteSpace($effectiveHostId)) {
        $requestedHostId = [string]$effectiveHostId
    }
    if ([string]::IsNullOrWhiteSpace($effectiveHostId) -and -not [string]::IsNullOrWhiteSpace($requestedHostId)) {
        $effectiveHostId = [string]$requestedHostId
    }

    return [pscustomobject]@{
        requested_id = if ([string]::IsNullOrWhiteSpace($requestedHostId)) { $null } else { [string]$requestedHostId }
        id = if ([string]::IsNullOrWhiteSpace($effectiveHostId)) { $null } else { [string]$effectiveHostId }
        requested_host_id = if ([string]::IsNullOrWhiteSpace($requestedHostId)) { $null } else { [string]$requestedHostId }
        effective_host_id = if ([string]::IsNullOrWhiteSpace($effectiveHostId)) { $null } else { [string]$effectiveHostId }
    }
}

function New-VibeRuntimeHostAdapterProjection {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$FallbackHostId = '',
        [AllowEmptyString()] [string]$TargetRoot = ''
    )

    $identity = Get-VibeHostAdapterIdentityProjection `
        -HostAdapter $Runtime.host_adapter `
        -RequestedPropertyName 'requested_id' `
        -EffectivePropertyName 'id' `
        -FallbackHostId $FallbackHostId

    $hostSettingsPath = $null
    if ($Runtime -and (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_settings')) {
        $hostSettings = $Runtime.host_settings
        if ($null -ne $hostSettings -and (Test-VibeObjectHasProperty -InputObject $hostSettings -PropertyName 'path') -and -not [string]::IsNullOrWhiteSpace($hostSettings.path)) {
            $hostSettingsPath = [string]$hostSettings.path
        }
    }

    $hostClosurePath = $null
    if ($Runtime -and (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_closure')) {
        $hostClosure = $Runtime.host_closure
        if ($null -ne $hostClosure -and (Test-VibeObjectHasProperty -InputObject $hostClosure -PropertyName 'path') -and -not [string]::IsNullOrWhiteSpace($hostClosure.path)) {
            $hostClosurePath = [string]$hostClosure.path
        }
    }

    return [pscustomobject]@{
        requested_id = $identity.requested_id
        id = $identity.id
        requested_host_id = $identity.requested_host_id
        effective_host_id = $identity.effective_host_id
        status = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'status')) { [string]$Runtime.host_adapter.status } else { $null }
        install_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'install_mode')) { [string]$Runtime.host_adapter.install_mode } else { $null }
        check_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'check_mode')) { [string]$Runtime.host_adapter.check_mode } else { $null }
        bootstrap_mode = if ($Runtime.host_adapter -and (Test-VibeObjectHasProperty -InputObject $Runtime.host_adapter -PropertyName 'bootstrap_mode')) { [string]$Runtime.host_adapter.bootstrap_mode } else { $null }
        target_root = if ([string]::IsNullOrWhiteSpace($TargetRoot)) { $null } else { [string]$TargetRoot }
        host_settings_path = $hostSettingsPath
        closure_path = $hostClosurePath
    }
}

function Get-VibeRuntimePacketHostAdapterAlignment {
    param(
        [AllowNull()] [object]$RuntimeInputPacket
    )

    return Get-VibeHostAdapterIdentityProjection `
        -HostAdapter $(if ($null -ne $RuntimeInputPacket -and $RuntimeInputPacket.PSObject.Properties.Name -contains 'host_adapter') { $RuntimeInputPacket.host_adapter } else { $null }) `
        -RequestedPropertyName 'requested_host_id' `
        -EffectivePropertyName 'effective_host_id'
}

function New-VibeRouteRuntimeAlignmentProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket,
        [AllowEmptyString()] [string]$DefaultRuntimeSkill = 'vibe'
    )

    $hostAdapterIdentity = Get-VibeRuntimePacketHostAdapterAlignment -RuntimeInputPacket $RuntimeInputPacket

    return [pscustomobject]@{
        router_selected_skill = if ($null -ne $RuntimeInputPacket) { [string]$RuntimeInputPacket.route_snapshot.selected_skill } else { $null }
        runtime_selected_skill = if ($null -ne $RuntimeInputPacket) { [string]$RuntimeInputPacket.authority_flags.explicit_runtime_skill } else { $DefaultRuntimeSkill }
        skill_mismatch = if ($null -ne $RuntimeInputPacket) { [bool]$RuntimeInputPacket.divergence_shadow.skill_mismatch } else { $false }
        confirm_required = if ($null -ne $RuntimeInputPacket) { [bool]$RuntimeInputPacket.route_snapshot.confirm_required } else { $false }
        requested_host_adapter_id = $hostAdapterIdentity.requested_host_id
        effective_host_adapter_id = $hostAdapterIdentity.effective_host_id
    }
}

function Get-VibeHostSettingsRecord {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    $targetRoot = Resolve-VibeHostTargetRoot -HostAdapter $HostAdapter
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return $null
    }

    $settingsPath = Join-Path $targetRoot '.vibeskills\host-settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) {
        return $null
    }

    try {
        $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }

    return [pscustomobject]@{
        target_root = $targetRoot
        path = $settingsPath
        data = $settings
    }
}

function Get-VibeHostClosureRecord {
    param(
        [Parameter(Mandatory)] [object]$HostAdapter
    )

    $targetRoot = Resolve-VibeHostTargetRoot -HostAdapter $HostAdapter
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return $null
    }

    $closurePath = Join-Path $targetRoot '.vibeskills\host-closure.json'
    if (-not (Test-Path -LiteralPath $closurePath -PathType Leaf)) {
        return $null
    }

    try {
        $closure = Get-Content -LiteralPath $closurePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }

    return [pscustomobject]@{
        target_root = $targetRoot
        path = $closurePath
        data = $closure
    }
}

function Get-VibeUpgradeReminder {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$HostAdapter
    )

    if ($null -eq $HostAdapter) {
        return $null
    }

    $targetRoot = Resolve-VibeHostTargetRoot -HostAdapter $HostAdapter
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return $null
    }

    $identity = Get-VibeHostAdapterIdentityProjection -HostAdapter $HostAdapter
    $hostId = if (-not [string]::IsNullOrWhiteSpace([string]$identity.id)) { [string]$identity.id } else { [string]$identity.requested_id }
    if ([string]::IsNullOrWhiteSpace($hostId)) {
        return $null
    }

    $scriptPath = Join-Path $RepoRoot 'apps\vgo-cli\src\vgo_cli\version_reminder.py'
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        return $null
    }

    try {
        $python = Get-VgoPythonCommand
        $args = @()
        if ($null -ne $python.prefix_arguments) {
            $args += @($python.prefix_arguments)
        }
        $args += @($scriptPath, '--repo-root', $RepoRoot, '--target-root', $targetRoot, '--host', $hostId)
        $output = & $python.host_path @args 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $null
        }
        $lines = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
        if ($lines.Count -eq 0) {
            return $null
        }
        return [string]$lines[-1]
    } catch {
        return $null
    }
}

function Get-VibeRuntimeContext {
    param(
        [Parameter(Mandatory)] [string]$ScriptPath
    )

    $governanceContext = Get-VgoGovernanceContext -ScriptPath $ScriptPath -EnforceExecutionContext
    $repoRoot = $governanceContext.repoRoot
    $hostAdapter = Get-VibeHostAdapterEntry -RepoRoot $repoRoot

    return [pscustomobject]@{
        repo_root = $repoRoot
        governance_context = $governanceContext
        host_adapter = $hostAdapter
        host_settings = Get-VibeHostSettingsRecord -HostAdapter $hostAdapter
        host_closure = Get-VibeHostClosureRecord -HostAdapter $hostAdapter
        runtime_contract = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-contract.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_modes = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-modes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        runtime_input_packet_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\runtime-input-packet-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        vibe_entry_surfaces = Get-Content -LiteralPath (Join-Path $repoRoot 'config\vibe-entry-surfaces.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        skill_promotion_policy = if (Test-Path -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json')) { Get-Content -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json } else { Get-VgoSkillPromotionPolicyDefaults }
        execution_topology_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-topology-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        native_specialist_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\native-specialist-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        execution_runtime_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-runtime-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        cleanup_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        proof_class_registry = Get-Content -LiteralPath (Join-Path $repoRoot 'config\proof-class-registry.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_governance = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-governance.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        workspace_memory_plane = Get-Content -LiteralPath (Join-Path $repoRoot 'config\workspace-memory-plane.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_disclosure_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-disclosure-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_ingest_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-ingest-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_tier_router = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-tier-router.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_runtime_v3_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-runtime-v3-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_stage_activation_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-stage-activation-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_retrieval_budget_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-retrieval-budget-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_backend_adapters = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-backend-adapters.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    }
}

function Get-VibeWorkspaceRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath($RepoRoot)
}

function Get-VibeWorkspaceSidecarRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceRoot -RepoRoot $RepoRoot) '.vibeskills'))
}

function Get-VibeWorkspaceProjectDescriptorPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path (Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot) 'project.json'))
}

function Get-VibeWorkspaceMemoryPlaneContract {
    param(
        [AllowNull()] [object]$Runtime = $null
    )

    $identityScope = 'workspace'
    $logicalOwners = @('state_store', 'serena', 'ruflo', 'cognee')
    if (
        $null -ne $Runtime -and
        (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'workspace_memory_plane') -and
        $null -ne $Runtime.workspace_memory_plane
    ) {
        $workspacePlane = $Runtime.workspace_memory_plane
        if (
            (Test-VibeObjectHasProperty -InputObject $workspacePlane -PropertyName 'workspace_identity') -and
            $null -ne $workspacePlane.workspace_identity -and
            (Test-VibeObjectHasProperty -InputObject $workspacePlane.workspace_identity -PropertyName 'scope') -and
            -not [string]::IsNullOrWhiteSpace([string]$workspacePlane.workspace_identity.scope)
        ) {
            $identityScope = [string]$workspacePlane.workspace_identity.scope
        }
        if (
            (Test-VibeObjectHasProperty -InputObject $workspacePlane -PropertyName 'canonical_owners') -and
            $null -ne $workspacePlane.canonical_owners
        ) {
            $owners = $workspacePlane.canonical_owners
            $logicalOwners = @(
                if ((Test-VibeObjectHasProperty -InputObject $owners -PropertyName 'session') -and -not [string]::IsNullOrWhiteSpace([string]$owners.session)) { [string]$owners.session } else { 'state_store' }
                if ((Test-VibeObjectHasProperty -InputObject $owners -PropertyName 'project_decision') -and -not [string]::IsNullOrWhiteSpace([string]$owners.project_decision)) { [string]$owners.project_decision } else { 'serena' }
                if ((Test-VibeObjectHasProperty -InputObject $owners -PropertyName 'short_term_semantic') -and -not [string]::IsNullOrWhiteSpace([string]$owners.short_term_semantic)) { [string]$owners.short_term_semantic } else { 'ruflo' }
                if ((Test-VibeObjectHasProperty -InputObject $owners -PropertyName 'long_term_graph') -and -not [string]::IsNullOrWhiteSpace([string]$owners.long_term_graph)) { [string]$owners.long_term_graph } else { 'cognee' }
            )
        }
    }

    return [pscustomobject]@{
        identity_scope = $identityScope
        driver_contract = 'workspace_shared_memory_v1'
        logical_owners = @($logicalOwners)
    }
}

function Get-VibeHostSidecarRoot {
    param(
        [AllowNull()] [object]$Runtime,
        [AllowEmptyString()] [string]$RouterTargetRoot = ''
    )

    $hostTargetRoot = if ([string]::IsNullOrWhiteSpace($RouterTargetRoot)) { $null } else { [System.IO.Path]::GetFullPath($RouterTargetRoot) }

    if ([string]::IsNullOrWhiteSpace($hostTargetRoot) -and $null -ne $Runtime) {
        if (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_settings') -and
            $null -ne $Runtime.host_settings -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_settings -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_settings.target_root)
        ) {
            $hostTargetRoot = [System.IO.Path]::GetFullPath([string]$Runtime.host_settings.target_root)
        } elseif (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_closure') -and
            $null -ne $Runtime.host_closure -and
            (Test-VibeObjectHasProperty -InputObject $Runtime.host_closure -PropertyName 'target_root') -and
            -not [string]::IsNullOrWhiteSpace([string]$Runtime.host_closure.target_root)
        ) {
            $hostTargetRoot = [System.IO.Path]::GetFullPath([string]$Runtime.host_closure.target_root)
        } elseif (
            (Test-VibeObjectHasProperty -InputObject $Runtime -PropertyName 'host_adapter') -and
            $null -ne $Runtime.host_adapter
        ) {
            $resolvedTargetRoot = Resolve-VibeHostTargetRoot -HostAdapter $Runtime.host_adapter
            if (-not [string]::IsNullOrWhiteSpace($resolvedTargetRoot)) {
                $hostTargetRoot = [System.IO.Path]::GetFullPath($resolvedTargetRoot)
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($hostTargetRoot)) {
        return $null
    }

    return [System.IO.Path]::GetFullPath((Join-Path $hostTargetRoot '.vibeskills'))
}

function New-VibeWorkspaceArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = '',
        [AllowEmptyString()] [string]$RouterTargetRoot = ''
    )

    $workspaceRoot = Get-VibeWorkspaceRoot -RepoRoot $RepoRoot
    $workspaceSidecarRoot = Get-VibeWorkspaceSidecarRoot -RepoRoot $RepoRoot
    $projectDescriptorPath = Get-VibeWorkspaceProjectDescriptorPath -RepoRoot $RepoRoot
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract -Runtime $Runtime
    $useDefaultWorkspaceSidecar = [string]::IsNullOrWhiteSpace($ArtifactRoot)

    if ($useDefaultWorkspaceSidecar) {
        $resolvedArtifactRoot = $workspaceSidecarRoot
        $artifactRootSource = 'workspace_sidecar_default'
    } elseif ([System.IO.Path]::IsPathRooted($ArtifactRoot)) {
        $resolvedArtifactRoot = [System.IO.Path]::GetFullPath($ArtifactRoot)
        $artifactRootSource = 'explicit_override'
    } else {
        $resolvedArtifactRoot = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $ArtifactRoot))
        $artifactRootSource = 'explicit_override'
    }

    return [pscustomobject]@{
        workspace_root = $workspaceRoot
        workspace_sidecar_root = $workspaceSidecarRoot
        project_descriptor_path = $projectDescriptorPath
        artifact_root = $resolvedArtifactRoot
        artifact_root_source = $artifactRootSource
        default_workspace_sidecar_artifact_root = [bool]$useDefaultWorkspaceSidecar
        host_sidecar_root = Get-VibeHostSidecarRoot -Runtime $Runtime -RouterTargetRoot $RouterTargetRoot
        workspace_memory_identity_root = $projectDescriptorPath
        workspace_memory_identity_scope = [string]$memoryPlane.identity_scope
        workspace_memory_driver_contract = [string]$memoryPlane.driver_contract
        workspace_memory_logical_owners = [string[]]@($memoryPlane.logical_owners)
    }
}

function Initialize-VibeWorkspaceProjectDescriptor {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$Runtime = $null
    )

    $storage = New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -Runtime $Runtime
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract -Runtime $Runtime
    $descriptorPath = [string]$storage.project_descriptor_path
    $descriptor = [pscustomobject]@{
        schema_version = 1
        brand = 'vibeskills'
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        workspace_root = [string]$storage.workspace_root
        workspace_sidecar_root = [string]$storage.workspace_sidecar_root
        project_descriptor_path = [string]$storage.project_descriptor_path
        default_artifact_root = [string]$storage.workspace_sidecar_root
        relative_runtime_contract = [pscustomobject]@{
            requirement_root = 'docs/requirements'
            execution_plan_root = 'docs/plans'
            session_root = 'outputs/runtime/vibe-sessions'
        }
        memory_plane = [pscustomobject]@{
            identity_root = [string]$storage.project_descriptor_path
            identity_scope = [string]$memoryPlane.identity_scope
            driver_contract = [string]$memoryPlane.driver_contract
            logical_owners = [string[]]@($memoryPlane.logical_owners)
        }
        host_sidecar_root = if ([string]::IsNullOrWhiteSpace([string]$storage.host_sidecar_root)) { $null } else { [string]$storage.host_sidecar_root }
    }

    Write-VibeJsonArtifact -Path $descriptorPath -Value $descriptor
    return $descriptorPath
}

function New-VibeRunId {
    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $suffix = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "$timestamp-$suffix"
}

function Resolve-VibeRuntimeMode {
    param(
        [AllowEmptyString()] [string]$Mode,
        [AllowEmptyString()] [string]$DefaultMode = 'interactive_governed'
    )

    if ([string]::IsNullOrWhiteSpace($Mode)) {
        return $DefaultMode
    }

    $normalized = $Mode.Trim().ToLowerInvariant()
    if ($normalized -ne 'interactive_governed') {
        throw "Unsupported vibe runtime mode: $Mode"
    }

    return 'interactive_governed'
}

function Resolve-VibeGovernanceScope {
    param(
        [AllowEmptyString()] [string]$GovernanceScope,
        [AllowEmptyString()] [string]$DefaultScope = 'root'
    )

    if ([string]::IsNullOrWhiteSpace($GovernanceScope)) {
        return $DefaultScope
    }

    $normalized = $GovernanceScope.Trim().ToLowerInvariant()
    if ($normalized -notin @('root', 'child')) {
        throw "Unsupported governance scope: $GovernanceScope"
    }

    return $normalized
}

function Get-VibeHierarchyState {
    param(
        [Parameter(Mandatory)] [AllowEmptyString()] [string]$GovernanceScope,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$RootRunId = '',
        [AllowEmptyString()] [string]$ParentRunId = '',
        [AllowEmptyString()] [string]$ParentUnitId = '',
        [AllowEmptyString()] [string]$InheritedRequirementDocPath = '',
        [AllowEmptyString()] [string]$InheritedExecutionPlanPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [Parameter(Mandatory)] [object]$HierarchyContract
    )

    $scope = Resolve-VibeGovernanceScope -GovernanceScope $GovernanceScope -DefaultScope ([string]$HierarchyContract.default_governance_scope)
    $authoritySource = if ($scope -eq 'child') {
        $HierarchyContract.child_authority_flags
    } else {
        $HierarchyContract.root_authority_flags
    }

    $resolvedRootRunId = if ($scope -eq 'root') {
        $RunId
    } elseif (-not [string]::IsNullOrWhiteSpace($RootRunId)) {
        $RootRunId
    } elseif (-not [string]::IsNullOrWhiteSpace($ParentRunId)) {
        $ParentRunId
    } else {
        $RunId
    }

    $resolvedParentRunId = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($ParentRunId)) {
        $ParentRunId
    } else {
        $null
    }

    return [pscustomobject]@{
        governance_scope = $scope
        root_run_id = $resolvedRootRunId
        parent_run_id = $resolvedParentRunId
        parent_unit_id = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($ParentUnitId)) { $ParentUnitId } else { $null }
        inherited_requirement_doc_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($InheritedRequirementDocPath)) { [System.IO.Path]::GetFullPath($InheritedRequirementDocPath) } else { $null }
        inherited_execution_plan_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($InheritedExecutionPlanPath)) { [System.IO.Path]::GetFullPath($InheritedExecutionPlanPath) } else { $null }
        delegation_envelope_path = if ($scope -eq 'child' -and -not [string]::IsNullOrWhiteSpace($DelegationEnvelopePath)) { [System.IO.Path]::GetFullPath($DelegationEnvelopePath) } else { $null }
        allow_requirement_freeze = [bool]$authoritySource.allow_requirement_freeze
        allow_plan_freeze = [bool]$authoritySource.allow_plan_freeze
        allow_global_dispatch = [bool]$authoritySource.allow_global_dispatch
        allow_completion_claim = [bool]$authoritySource.allow_completion_claim
    }
}

function New-VibeHierarchyProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState,
        [switch]$IncludeGovernanceScope
    )

    $projection = [ordered]@{}
    if ($IncludeGovernanceScope) {
        $projection.governance_scope = [string]$HierarchyState.governance_scope
    }
    $projection.root_run_id = [string]$HierarchyState.root_run_id
    $projection.parent_run_id = if ($null -eq $HierarchyState.parent_run_id) { $null } else { [string]$HierarchyState.parent_run_id }
    $projection.parent_unit_id = if ($null -eq $HierarchyState.parent_unit_id) { $null } else { [string]$HierarchyState.parent_unit_id }
    $projection.inherited_requirement_doc_path = if ($null -eq $HierarchyState.inherited_requirement_doc_path) { $null } else { [string]$HierarchyState.inherited_requirement_doc_path }
    $projection.inherited_execution_plan_path = if ($null -eq $HierarchyState.inherited_execution_plan_path) { $null } else { [string]$HierarchyState.inherited_execution_plan_path }
    $projection.delegation_envelope_path = if ((Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'delegation_envelope_path') -and $null -ne $HierarchyState.delegation_envelope_path) { [string]$HierarchyState.delegation_envelope_path } else { $null }
    return [pscustomobject]$projection
}

function New-VibeAuthorityCapabilityProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState
    )

    return [pscustomobject]@{
        allow_requirement_freeze = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_requirement_freeze') { [bool]$HierarchyState.allow_requirement_freeze } else { $false }
        allow_plan_freeze = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_plan_freeze') { [bool]$HierarchyState.allow_plan_freeze } else { $false }
        allow_global_dispatch = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_global_dispatch') { [bool]$HierarchyState.allow_global_dispatch } else { $false }
        allow_completion_claim = if (Test-VibeObjectHasProperty -InputObject $HierarchyState -PropertyName 'allow_completion_claim') { [bool]$HierarchyState.allow_completion_claim } else { $false }
    }
}

function New-VibeRuntimePacketAuthorityFlagsProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState,
        [AllowEmptyString()] [string]$RuntimeEntry = 'vibe',
        [AllowEmptyString()] [string]$ExplicitRuntimeSkill = 'vibe',
        [AllowEmptyString()] [string]$RouterTruthLevel = '',
        [bool]$ShadowOnly = $false,
        [bool]$NonAuthoritative = $false
    )

    $capabilities = New-VibeAuthorityCapabilityProjection -HierarchyState $HierarchyState

    return [pscustomobject]@{
        runtime_entry = if ([string]::IsNullOrWhiteSpace($RuntimeEntry)) { $null } else { [string]$RuntimeEntry }
        explicit_runtime_skill = if ([string]::IsNullOrWhiteSpace($ExplicitRuntimeSkill)) { $null } else { [string]$ExplicitRuntimeSkill }
        router_truth_level = if ([string]::IsNullOrWhiteSpace($RouterTruthLevel)) { $null } else { [string]$RouterTruthLevel }
        shadow_only = [bool]$ShadowOnly
        non_authoritative = [bool]$NonAuthoritative
        allow_requirement_freeze = [bool]$capabilities.allow_requirement_freeze
        allow_plan_freeze = [bool]$capabilities.allow_plan_freeze
        allow_global_dispatch = [bool]$capabilities.allow_global_dispatch
        allow_completion_claim = [bool]$capabilities.allow_completion_claim
    }
}

function New-VibeRuntimeInputPacketProjection {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$InternalGrade,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = '',
        [AllowEmptyString()] [string]$RequestedGradeFloor = '',
        [Parameter(Mandatory)] [object]$HierarchyState,
        [Parameter(Mandatory)] [object]$HierarchyProjection,
        [Parameter(Mandatory)] [object]$AuthorityFlagsProjection,
        [AllowNull()] [object]$StorageProjection = $null,
        [Parameter(Mandatory)] [object]$RouteResult,
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$TaskType = '',
        [AllowNull()] [string]$RequestedSkill = $null,
        [AllowEmptyString()] [string]$RouterHostId = '',
        [AllowEmptyString()] [string]$RouterTargetRoot = '',
        [bool]$Unattended = $false,
        [AllowEmptyString()] [string]$RouterScriptPath = '',
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = 'vibe',
        [AllowNull()] [object[]]$SpecialistRecommendations = @(),
        [Parameter(Mandatory)] [object]$SpecialistDispatch,
        [AllowNull()] [object[]]$OverlayDecisions = @(),
        [Parameter(Mandatory)] [object]$Policy
    )

    $confirmRequired = ([string]$RouteResult.route_mode -eq 'confirm_required')
    $routerSelectedSkill = if ($RouteResult.selected) { [string]$RouteResult.selected.skill } else { $null }

    $customAdmission = if (
        $RouteResult.PSObject.Properties.Name -contains 'custom_admission' -and
        $null -ne $RouteResult.custom_admission
    ) {
        [pscustomobject]@{
            status = [string]$RouteResult.custom_admission.status
            target_root = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'target_root') { [string]$RouteResult.custom_admission.target_root } else { $null }
            admitted_candidate_count = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'admitted_candidates') { @($RouteResult.custom_admission.admitted_candidates).Count } else { 0 }
            admitted_skill_ids = if ($RouteResult.custom_admission.PSObject.Properties.Name -contains 'admitted_candidates') {
                @($RouteResult.custom_admission.admitted_candidates | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
        }
    } else {
        $null
    }

    return [pscustomobject]@{
        stage = 'runtime_input_freeze'
        run_id = $RunId
        governance_scope = [string]$HierarchyState.governance_scope
        task = $Task
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        runtime_mode = $Mode
        internal_grade = $InternalGrade
        entry_intent_id = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { $null } else { [string]$EntryIntentId }
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { [string]$RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { [string]$RequestedGradeFloor }
        hierarchy = $HierarchyProjection
        canonical_router = [pscustomobject]@{
            prompt = $Task
            task_type = if ([string]::IsNullOrWhiteSpace($TaskType)) { $null } else { [string]$TaskType }
            requested_skill = if ([string]::IsNullOrWhiteSpace([string]$RequestedSkill)) { $null } else { [string]$RequestedSkill }
            host_id = if ([string]::IsNullOrWhiteSpace($RouterHostId)) { $null } else { [string]$RouterHostId }
            target_root = if ([string]::IsNullOrWhiteSpace($RouterTargetRoot)) { $null } else { [string]$RouterTargetRoot }
            unattended = [bool]$Unattended
            route_script_path = if ([string]::IsNullOrWhiteSpace($RouterScriptPath)) { $null } else { [string]$RouterScriptPath }
        }
        host_adapter = (New-VibeRuntimeHostAdapterProjection -Runtime $Runtime -FallbackHostId $RouterHostId -TargetRoot $RouterTargetRoot)
        route_snapshot = [pscustomobject]@{
            selected_pack = if ($RouteResult.selected) { [string]$RouteResult.selected.pack_id } else { $null }
            selected_skill = $routerSelectedSkill
            route_mode = [string]$RouteResult.route_mode
            route_reason = [string]$RouteResult.route_reason
            confirm_required = [bool]$confirmRequired
            confidence = if ($RouteResult.confidence -ne $null) { [double]$RouteResult.confidence } else { $null }
            truth_level = [string]$RouteResult.truth_level
            degradation_state = [string]$RouteResult.degradation_state
            non_authoritative = [bool]$RouteResult.non_authoritative
            fallback_active = [bool]$RouteResult.fallback_active
            hazard_alert_required = [bool]$RouteResult.hazard_alert_required
            unattended_override_applied = [bool]$RouteResult.unattended_override_applied
            custom_admission_status = if ($RouteResult.PSObject.Properties.Name -contains 'custom_admission' -and $RouteResult.custom_admission) { [string]$RouteResult.custom_admission.status } else { $null }
        }
        custom_admission = $customAdmission
        specialist_recommendations = @($SpecialistRecommendations)
        specialist_dispatch = [pscustomobject]@{
            approved_dispatch = [object[]]@($SpecialistDispatch.approved_dispatch)
            local_specialist_suggestions = [object[]]@($SpecialistDispatch.local_specialist_suggestions)
            blocked = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked' -and $null -ne $SpecialistDispatch.blocked) { [object[]]@($SpecialistDispatch.blocked) } else { @() }
            degraded = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded' -and $null -ne $SpecialistDispatch.degraded) { [object[]]@($SpecialistDispatch.degraded) } else { @() }
            approved_skill_ids = @($SpecialistDispatch.approved_dispatch | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
            local_suggestion_skill_ids = @($SpecialistDispatch.local_specialist_suggestions | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
            matched_skill_ids = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $SpecialistDispatch.matched_skill_ids) { [object[]]@($SpecialistDispatch.matched_skill_ids) } else { @() }
            surfaced_skill_ids = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $SpecialistDispatch.surfaced_skill_ids) { [object[]]@($SpecialistDispatch.surfaced_skill_ids) } else { @() }
            blocked_skill_ids = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked_skill_ids' -and $null -ne $SpecialistDispatch.blocked_skill_ids) { [object[]]@($SpecialistDispatch.blocked_skill_ids) } else { @() }
            degraded_skill_ids = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded_skill_ids' -and $null -ne $SpecialistDispatch.degraded_skill_ids) { [object[]]@($SpecialistDispatch.degraded_skill_ids) } else { @() }
            ghost_match_skill_ids = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'ghost_match_skill_ids' -and $null -ne $SpecialistDispatch.ghost_match_skill_ids) { [object[]]@($SpecialistDispatch.ghost_match_skill_ids) } else { @() }
            promotion_outcomes = if ($SpecialistDispatch.PSObject.Properties.Name -contains 'promotion_outcomes' -and $null -ne $SpecialistDispatch.promotion_outcomes) { [object[]]@($SpecialistDispatch.promotion_outcomes) } else { @() }
            escalation_required = [bool]$SpecialistDispatch.escalation_required
            escalation_status = [string]$SpecialistDispatch.escalation_status
            approval_owner = if ($Policy.child_specialist_suggestion_contract.PSObject.Properties.Name -contains 'approval_owner') { [string]$Policy.child_specialist_suggestion_contract.approval_owner } else { 'root_vibe' }
            status = if ($Policy.child_specialist_suggestion_contract.PSObject.Properties.Name -contains 'status') { [string]$Policy.child_specialist_suggestion_contract.status } else { 'auto_promote_when_safe_same_round' }
        }
        overlay_decisions = @($OverlayDecisions)
        authority_flags = $AuthorityFlagsProjection
        storage = $StorageProjection
        divergence_shadow = [pscustomobject]@{
            router_selected_skill = $routerSelectedSkill
            runtime_selected_skill = if ([string]::IsNullOrWhiteSpace($RuntimeSelectedSkill)) { $null } else { [string]$RuntimeSelectedSkill }
            skill_mismatch = [bool](-not [string]::Equals($routerSelectedSkill, $RuntimeSelectedSkill, [System.StringComparison]::OrdinalIgnoreCase))
            confirm_required = [bool]$confirmRequired
            explicit_runtime_override_applied = [bool](-not [string]::IsNullOrWhiteSpace($RuntimeSelectedSkill))
            explicit_runtime_override_reason = 'governed_runtime_entry'
            governance_scope_mismatch = $false
        }
        provenance = [pscustomobject]@{
            source_of_truth = 'canonical_router_shadow_freeze'
            freeze_before_requirement_doc = [bool]$Policy.freeze_before_requirement_doc
            proof_class = 'structure'
        }
    }
}

function New-VibeExecutionAuthorityProjection {
    param(
        [Parameter(Mandatory)] [object]$HierarchyState
    )

    $capabilities = New-VibeAuthorityCapabilityProjection -HierarchyState $HierarchyState

    return [pscustomobject]@{
        canonical_requirement_write_allowed = [bool]$capabilities.allow_requirement_freeze
        canonical_plan_write_allowed = [bool]$capabilities.allow_plan_freeze
        global_dispatch_allowed = [bool]$capabilities.allow_global_dispatch
        completion_claim_allowed = [bool]$capabilities.allow_completion_claim
    }
}

function Get-VibeGovernedRuntimeStageOrder {
    return @(
        'skeleton_check',
        'deep_interview',
        'requirement_doc',
        'xl_plan',
        'plan_execute',
        'phase_cleanup'
    )
}

function Get-VibeGovernedStageIndex {
    param(
        [AllowEmptyString()] [string]$StageName
    )

    if ([string]::IsNullOrWhiteSpace($StageName)) {
        return -1
    }

    $stageOrder = @(Get-VibeGovernedRuntimeStageOrder)
    for ($index = 0; $index -lt $stageOrder.Count; $index++) {
        if ([string]::Equals([string]$stageOrder[$index], [string]$StageName, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $index
        }
    }

    return -1
}

function Test-VibeGovernedStageReached {
    param(
        [AllowEmptyString()] [string]$TerminalStage,
        [AllowEmptyString()] [string]$TargetStage
    )

    $terminalIndex = Get-VibeGovernedStageIndex -StageName $TerminalStage
    $targetIndex = Get-VibeGovernedStageIndex -StageName $TargetStage
    if ($terminalIndex -lt 0 -or $targetIndex -lt 0) {
        return $false
    }

    return ($terminalIndex -ge $targetIndex)
}

function Get-VibeGradeRank {
    param(
        [AllowEmptyString()] [string]$Grade
    )

    $normalizedGrade = if ([string]::IsNullOrWhiteSpace($Grade)) { '' } else { [string]$Grade.ToUpperInvariant() }
    switch ($normalizedGrade) {
        'M' { return 0 }
        'L' { return 1 }
        'XL' { return 2 }
        default { return -1 }
    }
}

function Resolve-VibeGovernedGrade {
    param(
        [Parameter(Mandatory)] [string]$BaseGrade,
        [AllowEmptyString()] [string]$RequestedGradeFloor = '',
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedBaseGrade = if ([string]::IsNullOrWhiteSpace($BaseGrade)) { 'M' } else { [string]$BaseGrade.ToUpperInvariant() }
    $resolvedRequestedFloor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { [string]$RequestedGradeFloor.ToUpperInvariant() }

    if (-not [string]::IsNullOrWhiteSpace($resolvedRequestedFloor)) {
        $allowlist = if (
            $null -ne $Policy -and
            $Policy.PSObject.Properties.Name -contains 'public_grade_floor_allowlist' -and
            $null -ne $Policy.public_grade_floor_allowlist
        ) {
            @($Policy.public_grade_floor_allowlist | ForEach-Object { [string]$_ })
        } else {
            @('L', 'XL')
        }

        if ($allowlist -notcontains $resolvedRequestedFloor) {
            throw ("Unsupported requested grade floor '{0}'." -f $resolvedRequestedFloor)
        }
    }

    $resolvedGrade = $resolvedBaseGrade
    if (-not [string]::IsNullOrWhiteSpace($resolvedRequestedFloor)) {
        if ((Get-VibeGradeRank -Grade $resolvedRequestedFloor) -gt (Get-VibeGradeRank -Grade $resolvedBaseGrade)) {
            $resolvedGrade = $resolvedRequestedFloor
        }
    }

    return [pscustomobject]@{
        internal_grade = $resolvedGrade
        requested_grade_floor = $resolvedRequestedFloor
    }
}

function Resolve-VibeEntryIntentSelection {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = '',
        [AllowEmptyString()] [string]$RequestedGradeFloor = ''
    )

    $entryConfig = $Runtime.vibe_entry_surfaces
    $canonicalSkill = if (
        $null -ne $entryConfig -and
        $entryConfig.PSObject.Properties.Name -contains 'canonical_runtime_skill' -and
        -not [string]::IsNullOrWhiteSpace([string]$entryConfig.canonical_runtime_skill)
    ) {
        [string]$entryConfig.canonical_runtime_skill
    } else {
        'vibe'
    }

    $resolvedEntryIntentId = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { $canonicalSkill } else { [string]$EntryIntentId }
    $entry = @($entryConfig.entries | Where-Object { [string]::Equals([string]$_.id, $resolvedEntryIntentId, [System.StringComparison]::OrdinalIgnoreCase) } | Select-Object -First 1)
    if (@($entry).Count -eq 0) {
        throw ("Unsupported vibe entry intent id '{0}'." -f $resolvedEntryIntentId)
    }

    $selectedEntry = $entry[0]
    $resolvedStageStop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        [string]$selectedEntry.requested_stage_stop
    } else {
        [string]$RequestedStageStop
    }

    if ((Get-VibeGovernedStageIndex -StageName $resolvedStageStop) -lt 0) {
        throw ("Unsupported requested stop stage '{0}'." -f $resolvedStageStop)
    }

    $requestedFloor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { [string]$RequestedGradeFloor.ToUpperInvariant() }
    $allowGradeFlags = $true
    if ($selectedEntry.PSObject.Properties.Name -contains 'allow_grade_flags') {
        $allowGradeFlags = [bool]$selectedEntry.allow_grade_flags
    }
    if (-not $allowGradeFlags -and -not [string]::IsNullOrWhiteSpace($requestedFloor)) {
        throw ("Entry intent '{0}' does not allow grade flags." -f [string]$selectedEntry.id)
    }

    return [pscustomobject]@{
        entry_intent_id = [string]$selectedEntry.id
        entry_display_name = if ($selectedEntry.PSObject.Properties.Name -contains 'display_name') { [string]$selectedEntry.display_name } else { [string]$selectedEntry.id }
        requested_stage_stop = $resolvedStageStop
        requested_grade_floor = $requestedFloor
        canonical_runtime_skill = $canonicalSkill
        allow_grade_flags = [bool]$allowGradeFlags
    }
}

function Get-VibeGovernanceArtifactContract {
    param(
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $artifacts = if (
        $null -ne $HierarchyContract -and
        $HierarchyContract.PSObject.Properties.Name -contains 'governance_artifacts' -and
        $null -ne $HierarchyContract.governance_artifacts
    ) {
        $HierarchyContract.governance_artifacts
    } else {
        $null
    }

    return [pscustomobject]@{
        capsule = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'capsule' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.capsule)) { [string]$artifacts.capsule } else { 'governance-capsule.json' }
        lineage = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'lineage' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.lineage)) { [string]$artifacts.lineage } else { 'stage-lineage.json' }
        delegation_envelope = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'delegation_envelope' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.delegation_envelope)) { [string]$artifacts.delegation_envelope } else { 'delegation-envelope.json' }
        delegation_validation = if ($artifacts -and $artifacts.PSObject.Properties.Name -contains 'delegation_validation' -and -not [string]::IsNullOrWhiteSpace([string]$artifacts.delegation_validation)) { [string]$artifacts.delegation_validation } else { 'delegation-validation-receipt.json' }
    }
}

function Get-VibeGovernanceArtifactPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [ValidateSet('capsule', 'lineage', 'delegation_envelope', 'delegation_validation')] [string]$ArtifactName,
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $contract = Get-VibeGovernanceArtifactContract -HierarchyContract $HierarchyContract
    $fileName = [string]$contract.$ArtifactName
    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot $fileName))
}

function Write-VibeGovernanceCapsule {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$GovernanceScope,
        [AllowEmptyString()] [string]$RuntimeSelectedSkill = 'vibe',
        [AllowNull()] [string[]]$AllowedStageSequence = $(Get-VibeGovernedRuntimeStageOrder),
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $capsulePath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'capsule' -HierarchyContract $HierarchyContract
    $capsule = [pscustomobject]@{
        run_id = $RunId
        root_run_id = $RootRunId
        governance_scope = $GovernanceScope
        runtime_selected_skill = if ([string]::IsNullOrWhiteSpace($RuntimeSelectedSkill)) { 'vibe' } else { [string]$RuntimeSelectedSkill }
        state_machine_version = 'governed-runtime-v1'
        allowed_stage_sequence = @($AllowedStageSequence)
        requirement_truth_owner = if ($GovernanceScope -eq 'root') { 'root_governed' } else { 'root_governed_inherited' }
        plan_truth_owner = if ($GovernanceScope -eq 'root') { 'root_governed' } else { 'root_governed_inherited' }
        created_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $capsulePath -Value $capsule

    return [pscustomobject]@{
        path = $capsulePath
        capsule = $capsule
    }
}

function Add-VibeStageLineageEntry {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$StageName,
        [AllowEmptyString()] [string]$PreviousStageName = '',
        [AllowEmptyString()] [string]$PreviousStageReceiptPath = '',
        [AllowEmptyString()] [string]$CurrentReceiptPath = '',
        [AllowNull()] [object]$HierarchyContract = $null
    )

    $lineagePath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'lineage' -HierarchyContract $HierarchyContract
    $document = if (Test-Path -LiteralPath $lineagePath) {
        Get-Content -LiteralPath $lineagePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        [pscustomobject]@{
            run_id = $RunId
            root_run_id = $RootRunId
            stages = @()
        }
    }

    $stages = [System.Collections.ArrayList]::new()
    foreach ($stage in @($document.stages)) {
        [void]$stages.Add($stage)
    }
    if (-not [string]::IsNullOrWhiteSpace($PreviousStageName)) {
        if ($stages.Count -eq 0) {
            throw ("Cannot record stage '{0}' before lineage contains previous stage '{1}'." -f $StageName, $PreviousStageName)
        }
        $lastStage = $stages[$stages.Count - 1]
        if ([string]$lastStage.stage_name -ne $PreviousStageName) {
            throw ("Stage lineage mismatch for '{0}'. Expected previous stage '{1}', found '{2}'." -f $StageName, $PreviousStageName, [string]$lastStage.stage_name)
        }
        if (-not [string]::IsNullOrWhiteSpace($PreviousStageReceiptPath) -and -not (Test-Path -LiteralPath $PreviousStageReceiptPath)) {
            throw ("Stage lineage prerequisite receipt missing for '{0}': {1}" -f $StageName, $PreviousStageReceiptPath)
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($CurrentReceiptPath) -and -not (Test-Path -LiteralPath $CurrentReceiptPath)) {
        throw ("Current stage receipt missing for '{0}': {1}" -f $StageName, $CurrentReceiptPath)
    }

    $entry = [pscustomobject]@{
        stage_name = $StageName
        run_id = $RunId
        root_run_id = $RootRunId
        previous_stage_name = if ([string]::IsNullOrWhiteSpace($PreviousStageName)) { $null } else { $PreviousStageName }
        previous_stage_receipt_path = if ([string]::IsNullOrWhiteSpace($PreviousStageReceiptPath)) { $null } else { [System.IO.Path]::GetFullPath($PreviousStageReceiptPath) }
        current_receipt_path = if ([string]::IsNullOrWhiteSpace($CurrentReceiptPath)) { $null } else { [System.IO.Path]::GetFullPath($CurrentReceiptPath) }
        transition_validated = $true
        validated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    [void]$stages.Add($entry)
    $document = [pscustomobject]@{
        run_id = $RunId
        root_run_id = $RootRunId
        stages = @($stages)
        last_stage_name = $StageName
        updated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $lineagePath -Value $document

    return [pscustomobject]@{
        path = $lineagePath
        lineage = $document
        entry = $entry
    }
}

function Write-VibeDelegationEnvelope {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$RootRunId,
        [Parameter(Mandatory)] [string]$ParentRunId,
        [Parameter(Mandatory)] [string]$ParentUnitId,
        [Parameter(Mandatory)] [string]$ChildRunId,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$WriteScope,
        [AllowNull()] [string[]]$ApprovedSpecialists = @(),
        [AllowEmptyString()] [string]$ReviewMode = 'native_contract'
    )

    $envelope = [pscustomobject]@{
        root_run_id = $RootRunId
        parent_run_id = $ParentRunId
        parent_unit_id = $ParentUnitId
        child_run_id = $ChildRunId
        governance_scope = 'child_governed'
        requirement_doc_path = [System.IO.Path]::GetFullPath($RequirementDocPath)
        execution_plan_path = [System.IO.Path]::GetFullPath($ExecutionPlanPath)
        write_scope = $WriteScope
        approved_specialists = @($ApprovedSpecialists | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
        review_mode = if ([string]::IsNullOrWhiteSpace($ReviewMode)) { 'native_contract' } else { $ReviewMode }
        prompt_tail_required = '$vibe'
        allow_requirement_freeze = $false
        allow_plan_freeze = $false
        allow_root_completion_claim = $false
    }
    Write-VibeJsonArtifact -Path $Path -Value $envelope

    return [pscustomobject]@{
        path = [System.IO.Path]::GetFullPath($Path)
        envelope = $envelope
    }
}

function Assert-VibeDelegationEnvelope {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [AllowEmptyString()] [string]$EnvelopePath,
        [AllowNull()] [object]$HierarchyState = $null,
        [AllowNull()] [object]$LaneSpec = $null,
        [AllowEmptyString()] [string]$ExpectedWriteScope = '',
        [AllowEmptyString()] [string]$ExpectedChildRunId = '',
        [AllowEmptyString()] [string]$ExpectedParentRunId = '',
        [AllowEmptyString()] [string]$ExpectedParentUnitId = '',
        [AllowEmptyString()] [string]$ExpectedSkillId = '',
        [AllowNull()] [object]$HierarchyContract = $null
    )

    if ([string]::IsNullOrWhiteSpace($EnvelopePath) -or -not (Test-Path -LiteralPath $EnvelopePath)) {
        throw ("Child-governed runtime requires DelegationEnvelopePath and the referenced file must exist: {0}" -f $EnvelopePath)
    }

    $envelope = Get-Content -LiteralPath $EnvelopePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $writeScopeValue = if ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'write_scope') { [string]$LaneSpec.write_scope } elseif (-not [string]::IsNullOrWhiteSpace($ExpectedWriteScope)) { $ExpectedWriteScope } elseif ($envelope.PSObject.Properties.Name -contains 'write_scope') { [string]$envelope.write_scope } else { '' }
    $approvedSpecialists = if ($envelope.PSObject.Properties.Name -contains 'approved_specialists' -and $null -ne $envelope.approved_specialists) {
        @($envelope.approved_specialists | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @()
    }

    $requirementMatches = $true
    $planMatches = $true
    if ($null -ne $HierarchyState) {
        if ($HierarchyState.inherited_requirement_doc_path) {
            $requirementMatches = ([System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path) -eq [System.IO.Path]::GetFullPath([string]$HierarchyState.inherited_requirement_doc_path))
        }
        if ($HierarchyState.inherited_execution_plan_path) {
            $planMatches = ([System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path) -eq [System.IO.Path]::GetFullPath([string]$HierarchyState.inherited_execution_plan_path))
        }
    } elseif ($null -ne $LaneSpec) {
        $requirementMatches = ([System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path) -eq [System.IO.Path]::GetFullPath([string]$LaneSpec.requirement_doc_path))
        $planMatches = ([System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path) -eq [System.IO.Path]::GetFullPath([string]$LaneSpec.execution_plan_path))
    }

    $writeScopeValid = -not [string]::IsNullOrWhiteSpace([string]$envelope.write_scope)
    if (-not [string]::IsNullOrWhiteSpace($writeScopeValue)) {
        $writeScopeValid = $writeScopeValid -and ([string]$envelope.write_scope -eq $writeScopeValue)
    }

    $childRunValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedChildRunId)) {
        $ExpectedChildRunId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'run_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.run_id)) {
        [string]$LaneSpec.run_id
    } else {
        ''
    }
    $parentRunValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedParentRunId)) {
        $ExpectedParentRunId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'parent_run_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.parent_run_id)) {
        [string]$LaneSpec.parent_run_id
    } elseif ($null -ne $HierarchyState -and -not [string]::IsNullOrWhiteSpace([string]$HierarchyState.parent_run_id)) {
        [string]$HierarchyState.parent_run_id
    } else {
        ''
    }
    $parentUnitValue = if (-not [string]::IsNullOrWhiteSpace($ExpectedParentUnitId)) {
        $ExpectedParentUnitId
    } elseif ($null -ne $LaneSpec -and $LaneSpec.PSObject.Properties.Name -contains 'parent_unit_id' -and -not [string]::IsNullOrWhiteSpace([string]$LaneSpec.parent_unit_id)) {
        [string]$LaneSpec.parent_unit_id
    } elseif ($null -ne $HierarchyState -and -not [string]::IsNullOrWhiteSpace([string]$HierarchyState.parent_unit_id)) {
        [string]$HierarchyState.parent_unit_id
    } else {
        ''
    }
    $childRunValid = $true
    if (-not [string]::IsNullOrWhiteSpace($childRunValue)) {
        $childRunValid = ([string]$envelope.child_run_id -eq $childRunValue)
    }
    $parentRunValid = $true
    if (-not [string]::IsNullOrWhiteSpace($parentRunValue)) {
        $parentRunValid = ([string]$envelope.parent_run_id -eq $parentRunValue)
    }
    $parentUnitValid = $true
    if (-not [string]::IsNullOrWhiteSpace($parentUnitValue)) {
        $parentUnitValid = ([string]$envelope.parent_unit_id -eq $parentUnitValue)
    }

    $specialistApprovalValid = $true
    if (-not [string]::IsNullOrWhiteSpace($ExpectedSkillId)) {
        $specialistApprovalValid = ($approvedSpecialists -contains $ExpectedSkillId)
    }
    $promptTailValid = ([string]$envelope.prompt_tail_required -eq '$vibe')
    $scopeValid = ([string]$envelope.governance_scope -eq 'child_governed')
    $rootRunValid = $true
    if ($null -ne $HierarchyState -and $HierarchyState.root_run_id) {
        $rootRunValid = ([string]$envelope.root_run_id -eq [string]$HierarchyState.root_run_id)
    } elseif ($null -ne $LaneSpec -and $LaneSpec.root_run_id) {
        $rootRunValid = ([string]$envelope.root_run_id -eq [string]$LaneSpec.root_run_id)
    }

    if (-not $scopeValid) {
        throw ("Delegation envelope governance scope must be child_governed: {0}" -f [string]$envelope.governance_scope)
    }
    if (-not $promptTailValid) {
        throw 'Delegation envelope must require $vibe prompt tail discipline.'
    }
    if (-not $requirementMatches -or -not $planMatches) {
        throw 'Delegation envelope does not match inherited canonical requirement/plan truth.'
    }
    if (-not $writeScopeValid) {
        throw 'Delegation envelope must declare a non-empty matching write scope.'
    }
    if (-not $rootRunValid) {
        throw 'Delegation envelope root run id does not match the governed child context.'
    }
    if (-not $childRunValid) {
        throw 'Delegation envelope child run id does not match the governed child context.'
    }
    if (-not $parentRunValid) {
        throw 'Delegation envelope parent run id does not match the governed child context.'
    }
    if (-not $parentUnitValid) {
        throw 'Delegation envelope parent unit id does not match the governed child context.'
    }
    if (-not $specialistApprovalValid) {
        throw ("Delegation envelope does not approve specialist dispatch: {0}" -f $ExpectedSkillId)
    }

    $receiptPath = Get-VibeGovernanceArtifactPath -SessionRoot $SessionRoot -ArtifactName 'delegation_validation' -HierarchyContract $HierarchyContract
    $receipt = [pscustomobject]@{
        child_run_id = if (-not [string]::IsNullOrWhiteSpace($childRunValue)) { $childRunValue } elseif ($envelope.PSObject.Properties.Name -contains 'child_run_id') { [string]$envelope.child_run_id } else { $null }
        root_run_id = [string]$envelope.root_run_id
        envelope_path = [System.IO.Path]::GetFullPath($EnvelopePath)
        requirement_doc_path = [System.IO.Path]::GetFullPath([string]$envelope.requirement_doc_path)
        execution_plan_path = [System.IO.Path]::GetFullPath([string]$envelope.execution_plan_path)
        write_scope_valid = [bool]$writeScopeValid
        prompt_tail_valid = [bool]$promptTailValid
        child_run_valid = [bool]$childRunValid
        parent_run_valid = [bool]$parentRunValid
        parent_unit_valid = [bool]$parentUnitValid
        specialist_approval_valid = [bool]$specialistApprovalValid
        validated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    Write-VibeJsonArtifact -Path $receiptPath -Value $receipt

    return [pscustomobject]@{
        receipt_path = $receiptPath
        receipt = $receipt
        envelope = $envelope
    }
}

function New-VibeRuntimeSummaryArtifactProjection {
    param(
        [AllowEmptyString()] [string]$SkeletonReceiptPath = '',
        [AllowEmptyString()] [string]$RuntimeInputPacketPath = '',
        [AllowEmptyString()] [string]$GovernanceCapsulePath = '',
        [AllowEmptyString()] [string]$StageLineagePath = '',
        [AllowEmptyString()] [string]$IntentContractPath = '',
        [AllowEmptyString()] [string]$RequirementDocPath = '',
        [AllowEmptyString()] [string]$RequirementReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanReceiptPath = '',
        [AllowEmptyString()] [string]$ExecuteReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionManifestPath = '',
        [AllowEmptyString()] [string]$ExecutionTopologyPath = '',
        [AllowEmptyString()] [string]$ExecutionProofManifestPath = '',
        [AllowEmptyString()] [string]$CleanupReceiptPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceReportPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceMarkdownPath = '',
        [AllowEmptyString()] [string]$MemoryActivationReportPath = '',
        [AllowEmptyString()] [string]$MemoryActivationMarkdownPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [AllowEmptyString()] [string]$DelegationValidationReceiptPath = ''
    )

    return [pscustomobject]@{
        skeleton_receipt = if ([string]::IsNullOrWhiteSpace($SkeletonReceiptPath)) { $null } else { $SkeletonReceiptPath }
        runtime_input_packet = if ([string]::IsNullOrWhiteSpace($RuntimeInputPacketPath)) { $null } else { $RuntimeInputPacketPath }
        governance_capsule = if ([string]::IsNullOrWhiteSpace($GovernanceCapsulePath)) { $null } else { $GovernanceCapsulePath }
        stage_lineage = if ([string]::IsNullOrWhiteSpace($StageLineagePath)) { $null } else { $StageLineagePath }
        intent_contract = if ([string]::IsNullOrWhiteSpace($IntentContractPath)) { $null } else { $IntentContractPath }
        requirement_doc = if ([string]::IsNullOrWhiteSpace($RequirementDocPath)) { $null } else { $RequirementDocPath }
        requirement_receipt = if ([string]::IsNullOrWhiteSpace($RequirementReceiptPath)) { $null } else { $RequirementReceiptPath }
        execution_plan = if ([string]::IsNullOrWhiteSpace($ExecutionPlanPath)) { $null } else { $ExecutionPlanPath }
        execution_plan_receipt = if ([string]::IsNullOrWhiteSpace($ExecutionPlanReceiptPath)) { $null } else { $ExecutionPlanReceiptPath }
        execute_receipt = if ([string]::IsNullOrWhiteSpace($ExecuteReceiptPath)) { $null } else { $ExecuteReceiptPath }
        execution_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionManifestPath)) { $null } else { $ExecutionManifestPath }
        execution_topology = if ([string]::IsNullOrWhiteSpace($ExecutionTopologyPath)) { $null } else { $ExecutionTopologyPath }
        execution_proof_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionProofManifestPath)) { $null } else { $ExecutionProofManifestPath }
        cleanup_receipt = if ([string]::IsNullOrWhiteSpace($CleanupReceiptPath)) { $null } else { $CleanupReceiptPath }
        delivery_acceptance_report = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceReportPath)) { $null } else { $DeliveryAcceptanceReportPath }
        delivery_acceptance_markdown = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceMarkdownPath)) { $null } else { $DeliveryAcceptanceMarkdownPath }
        memory_activation_report = if ([string]::IsNullOrWhiteSpace($MemoryActivationReportPath)) { $null } else { $MemoryActivationReportPath }
        memory_activation_markdown = if ([string]::IsNullOrWhiteSpace($MemoryActivationMarkdownPath)) { $null } else { $MemoryActivationMarkdownPath }
        delegation_envelope = if ([string]::IsNullOrWhiteSpace($DelegationEnvelopePath)) { $null } else { $DelegationEnvelopePath }
        delegation_validation_receipt = if ([string]::IsNullOrWhiteSpace($DelegationValidationReceiptPath)) { $null } else { $DelegationValidationReceiptPath }
    }
}

function New-VibeRuntimeSummaryRelativeArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [object]$Artifacts
    )

    $relativeArtifacts = [ordered]@{}
    foreach ($property in @($Artifacts.PSObject.Properties)) {
        if ($null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            $relativeArtifacts[[string]$property.Name] = $null
            continue
        }
        $relativeArtifacts[[string]$property.Name] = Get-VibeRelativePathCompat -BasePath $BasePath -TargetPath ([string]$property.Value)
    }

    return [pscustomobject]$relativeArtifacts
}

function New-VibeRuntimeSummaryMemoryActivationProjection {
    param(
        [AllowNull()] [object]$MemoryActivationReport
    )

    if ($null -eq $MemoryActivationReport) {
        return $null
    }

    return [pscustomobject]@{
        policy_mode = [string]$MemoryActivationReport.policy.mode
        routing_contract = [string]$MemoryActivationReport.policy.routing_contract
        fallback_event_count = [int]$MemoryActivationReport.summary.fallback_event_count
        artifact_count = [int]$MemoryActivationReport.summary.artifact_count
        budget_guard_respected = [bool]$MemoryActivationReport.summary.budget_guard_respected
    }
}

function New-VibeRuntimeSummaryDeliveryAcceptanceProjection {
    param(
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    if ($null -eq $DeliveryAcceptanceReport) {
        return $null
    }

    return [pscustomobject]@{
        gate_result = [string]$DeliveryAcceptanceReport.summary.gate_result
        completion_language_allowed = [bool]$DeliveryAcceptanceReport.summary.completion_language_allowed
        readiness_state = [string]$DeliveryAcceptanceReport.summary.readiness_state
        manual_review_layer_count = [int]$DeliveryAcceptanceReport.summary.manual_review_layer_count
        failing_layer_count = [int]$DeliveryAcceptanceReport.summary.failing_layer_count
    }
}

function New-VibeRuntimeSummaryProjection {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$ArtifactRoot,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [Parameter(Mandatory)] [object]$HierarchyState,
        [AllowEmptyString()] [string]$TerminalStage = '',
        [AllowNull()] [object[]]$ExecutedStageOrder = @(),
        [Parameter(Mandatory)] [object]$Artifacts,
        [Parameter(Mandatory)] [object]$RelativeArtifacts,
        [AllowNull()] [object]$StorageProjection = $null,
        [AllowNull()] [object]$MemoryActivationReport,
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    return [pscustomobject]@{
        run_id = $RunId
        governance_scope = [string]$HierarchyState.governance_scope
        mode = $Mode
        task = $Task
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        artifact_root = $ArtifactRoot
        session_root = $SessionRoot
        session_root_relative = Get-VibeRelativePathCompat -BasePath $ArtifactRoot -TargetPath $SessionRoot
        hierarchy = New-VibeHierarchyProjection -HierarchyState $HierarchyState
        stage_order = @(Get-VibeGovernedRuntimeStageOrder)
        executed_stage_order = [object[]]@($ExecutedStageOrder)
        terminal_stage = if ([string]::IsNullOrWhiteSpace($TerminalStage)) { $null } else { [string]$TerminalStage }
        artifacts = $Artifacts
        storage = $StorageProjection
        memory_activation = New-VibeRuntimeSummaryMemoryActivationProjection -MemoryActivationReport $MemoryActivationReport
        delivery_acceptance = New-VibeRuntimeSummaryDeliveryAcceptanceProjection -DeliveryAcceptanceReport $DeliveryAcceptanceReport
        artifacts_relative = $RelativeArtifacts
    }
}

function ConvertTo-VibeSlug {
    param(
        [AllowEmptyString()] [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return 'task'
    }

    $normalized = $Text.ToLowerInvariant()
    $normalized = [regex]::Replace($normalized, '[^a-z0-9]+', '-')
    $normalized = $normalized.Trim('-')
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return 'task'
    }

    if ($normalized.Length -gt 64) {
        return $normalized.Substring(0, 64).Trim('-')
    }

    return $normalized
}

function Get-VibeTitleFromTask {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $flat = ($Task -replace '\s+', ' ').Trim()
    if ($flat.Length -le 80) {
        return $flat
    }

    return ($flat.Substring(0, 80).Trim() + '...')
}

function Get-VibeArtifactRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    return [string](New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -Runtime $Runtime -ArtifactRoot $ArtifactRoot).artifact_root
}

function Get-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -Runtime $Runtime -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("outputs\runtime\vibe-sessions\{0}" -f $RunId)))
}

function Ensure-VibeSessionRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowNull()] [object]$Runtime = $null,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -Runtime $Runtime -ArtifactRoot $ArtifactRoot
    New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null
    if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
        Initialize-VibeWorkspaceProjectDescriptor -RepoRoot $RepoRoot -Runtime $Runtime | Out-Null
    }
    return $sessionRoot
}

function Write-VibeJsonArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [object]$Value
    )

    $json = $Value | ConvertTo-Json -Depth 20
    Write-VgoUtf8NoBomText -Path $Path -Content $json
}

function Write-VibeMarkdownArtifact {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [AllowEmptyString()] [string[]]$Lines
    )

    Write-VgoUtf8NoBomText -Path $Path -Content (($Lines -join [Environment]::NewLine) + [Environment]::NewLine)
}

function Get-VibeInternalGrade {
    param(
        [Parameter(Mandatory)] [string]$Task
    )

    $taskLower = $Task.ToLowerInvariant()
    $xlPatterns = @('xl', 'multi-agent', 'parallel', 'wave', 'batch', '无人值守', 'autonomous', 'benchmark', 'front.*back', 'end-to-end')
    $lPatterns = @('design', 'plan', 'architecture', 'refactor', 'migrate', 'research', 'governance', '访谈', '规划', '设计', '治理')

    foreach ($pattern in $xlPatterns) {
        if ($taskLower -match $pattern) {
            return 'XL'
        }
    }

    foreach ($pattern in $lPatterns) {
        if ($taskLower -match $pattern) {
            return 'L'
        }
    }

    if ($Task.Length -gt 180) {
        return 'L'
    }

    return 'M'
}

function New-VibeIntentContractObject {
    param(
        [Parameter(Mandatory)] [string]$Task,
        [Parameter(Mandatory)] [string]$Mode
    )

    $Mode = Resolve-VibeRuntimeMode -Mode $Mode
    $title = Get-VibeTitleFromTask -Task $Task
    $grade = Get-VibeInternalGrade -Task $Task
    $assumptions = @()
    $assumptions += 'Interactive clarification is allowed if unresolved ambiguity materially changes implementation.'
    return [pscustomobject]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        title = $title
        goal = $title
        deliverable = 'Governed implementation artifacts, verification evidence, and cleanup receipts'
        constraints = @(
            'Do not bypass the fixed six-stage governed runtime.',
            'Do not widen scope silently beyond the frozen requirement document.'
        )
        acceptance_criteria = @(
            'Requirement document is frozen before execution.',
            'Execution plan exists before implementation.',
            'Verification evidence exists before completion claims.',
            'Phase cleanup receipt is produced.'
        )
        non_goals = @(
            'Do not treat M/L/XL as user-facing entry branches.',
            'Do not introduce a second router or control plane.'
        )
        risk_tolerance = 'moderate'
        autonomy_mode = $Mode
        open_questions = @()
        inference_notes = @(
            'This contract was derived from the raw task text.',
            'Interactive mode may still surface explicit clarification questions outside the script path.'
        )
        assumptions = @($assumptions)
        internal_grade = $grade
        source_task = $Task
    }
}

function Get-VibeRequirementDocPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\requirements\{0}-{1}.md" -f $date, $slug)))
}

function Get-VibeExecutionPlanPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $slug = ConvertTo-VibeSlug -Text $Task
    $date = (Get-Date).ToString('yyyy-MM-dd')
    $baseRoot = Get-VibeArtifactRoot -RepoRoot $RepoRoot -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $baseRoot ("docs\plans\{0}-{1}-execution-plan.md" -f $date, $slug)))
}

function Get-VibeRuntimeInputPacketPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $sessionRoot 'runtime-input-packet.json'))
}

function Get-VibeExecutionTopologyPath {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [string]$RunId,
        [AllowEmptyString()] [string]$ArtifactRoot = ''
    )

    $sessionRoot = Get-VibeSessionRoot -RepoRoot $RepoRoot -RunId $RunId -ArtifactRoot $ArtifactRoot
    return [System.IO.Path]::GetFullPath((Join-Path $sessionRoot 'execution-topology.json'))
}
