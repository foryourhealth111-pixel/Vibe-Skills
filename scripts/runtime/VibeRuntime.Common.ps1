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
        skill_promotion_policy = if (Test-Path -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json')) { Get-Content -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json } else { Get-VgoSkillPromotionPolicyDefaults }
        execution_topology_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-topology-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        native_specialist_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\native-specialist-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        execution_runtime_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-runtime-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        cleanup_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        proof_class_registry = Get-Content -LiteralPath (Join-Path $repoRoot 'config\proof-class-registry.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_governance = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-governance.json') -Raw -Encoding UTF8 | ConvertFrom-Json
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
    }
}

function Initialize-VibeWorkspaceProjectDescriptor {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowNull()] [object]$Runtime = $null
    )

    $storage = New-VibeWorkspaceArtifactProjection -RepoRoot $RepoRoot -Runtime $Runtime
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
            status = if ($Policy.child_specialist_suggestion_contract.PSObject.Properties.Name -contains 'status') { [string]$Policy.child_specialist_suggestion_contract.status } else { 'advisory_until_root_approval' }
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

function New-VibeRuntimeSummaryArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$SkeletonReceiptPath,
        [Parameter(Mandatory)] [string]$RuntimeInputPacketPath,
        [Parameter(Mandatory)] [string]$IntentContractPath,
        [Parameter(Mandatory)] [string]$RequirementDocPath,
        [Parameter(Mandatory)] [string]$RequirementReceiptPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanPath,
        [Parameter(Mandatory)] [string]$ExecutionPlanReceiptPath,
        [Parameter(Mandatory)] [string]$ExecuteReceiptPath,
        [Parameter(Mandatory)] [string]$ExecutionManifestPath,
        [Parameter(Mandatory)] [string]$ExecutionTopologyPath,
        [Parameter(Mandatory)] [string]$ExecutionProofManifestPath,
        [Parameter(Mandatory)] [string]$CleanupReceiptPath,
        [Parameter(Mandatory)] [string]$DeliveryAcceptanceReportPath,
        [Parameter(Mandatory)] [string]$DeliveryAcceptanceMarkdownPath,
        [Parameter(Mandatory)] [string]$MemoryActivationReportPath,
        [Parameter(Mandatory)] [string]$MemoryActivationMarkdownPath
    )

    return [pscustomobject]@{
        skeleton_receipt = $SkeletonReceiptPath
        runtime_input_packet = $RuntimeInputPacketPath
        intent_contract = $IntentContractPath
        requirement_doc = $RequirementDocPath
        requirement_receipt = $RequirementReceiptPath
        execution_plan = $ExecutionPlanPath
        execution_plan_receipt = $ExecutionPlanReceiptPath
        execute_receipt = $ExecuteReceiptPath
        execution_manifest = $ExecutionManifestPath
        execution_topology = $ExecutionTopologyPath
        execution_proof_manifest = $ExecutionProofManifestPath
        cleanup_receipt = $CleanupReceiptPath
        delivery_acceptance_report = $DeliveryAcceptanceReportPath
        delivery_acceptance_markdown = $DeliveryAcceptanceMarkdownPath
        memory_activation_report = $MemoryActivationReportPath
        memory_activation_markdown = $MemoryActivationMarkdownPath
    }
}

function New-VibeRuntimeSummaryRelativeArtifactProjection {
    param(
        [Parameter(Mandatory)] [string]$BasePath,
        [Parameter(Mandatory)] [object]$Artifacts
    )

    $relativeArtifacts = [ordered]@{}
    foreach ($property in @($Artifacts.PSObject.Properties)) {
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
