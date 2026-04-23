Set-StrictMode -Off
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

# Alias for compatibility with VibeExecution.Common.ps1 which calls Get-VibeHostAdapterIdentityProjection
function global:Get-VibeHostAdapterIdentityProjection {
    param(
        [AllowNull()] [object]$HostAdapter,
        [AllowEmptyString()] [string]$RequestedPropertyName = 'requested_id',
        [AllowEmptyString()] [string]$EffectivePropertyName = 'id',
        [AllowEmptyString()] [string]$FallbackHostId = ''
    )
    return New-VibeHostAdapterIdentityProjection -HostAdapter $HostAdapter -RequestedPropertyName $RequestedPropertyName -EffectivePropertyName $EffectivePropertyName -FallbackHostId $FallbackHostId
}

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

function Get-VibePropertySafe {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$PropertyName,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    if (-not (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName $PropertyName)) {
        return $DefaultValue
    }

    try {
        return $InputObject.$PropertyName
    } catch {
        return $DefaultValue
    }
}

function Get-VibeSafeArrayCount {
    param(
        [AllowNull()] [object]$InputObject
    )
    
    if ($null -eq $InputObject) {
        return 0
    }
    
    try {
        # Handle arrays and collections
        if ($InputObject -is [System.Collections.ICollection]) {
            return [int]$InputObject.Count
        }
        # Handle objects with Count property
        if (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName 'Count') {
            return [int]$InputObject.Count
        }
        # Handle objects with Length property
        if (Test-VibeObjectHasProperty -InputObject $InputObject -PropertyName 'Length') {
            return [int]$InputObject.Length
        }
        # Treat scalar as count 1
        return 1
    } catch {
        return 0
    }
}

function Get-VibeNestedPropertySafe {
    param(
        [AllowNull()] [object]$InputObject,
        [AllowNull()] [string[]]$PropertyPath,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }
    
    # Handle null or empty PropertyPath
    if ($null -eq $PropertyPath) {
        return $InputObject
    }
    
    # Safely get Count (handles Set-StrictMode)
    $pathCount = 0
    try {
        # Use @() to handle null/undefined PropertyPath safely
        $pathCount = @($PropertyPath).Count
    } catch {
        return $DefaultValue
    }
    
    if ($pathCount -eq 0) {
        return $InputObject
    }

    $current = $InputObject
    foreach ($prop in $PropertyPath) {
        if ($null -eq $current) {
            return $DefaultValue
        }
        if (-not (Test-VibeObjectHasProperty -InputObject $current -PropertyName $prop)) {
            return $DefaultValue
        }
        try {
            $current = $current.$prop
        } catch {
            return $DefaultValue
        }
    }

    return $current
}

function New-VibeHostAdapterIdentityProjection {
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

    $hostAdapter = Get-VibePropertySafe -InputObject $Runtime -PropertyName 'host_adapter'
    $identity = New-VibeHostAdapterIdentityProjection `
        -HostAdapter $hostAdapter `
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

    return New-VibeHostAdapterIdentityProjection `
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

    $routeSnapshot = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'route_snapshot'
    $authorityFlags = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'authority_flags'
    $divergenceShadow = Get-VibePropertySafe -InputObject $RuntimeInputPacket -PropertyName 'divergence_shadow'

    return [pscustomobject]@{
        router_selected_skill = Get-VibeNestedPropertySafe -InputObject $routeSnapshot -PropertyPath @('selected_skill') -DefaultValue $null
        runtime_selected_skill = Get-VibeNestedPropertySafe -InputObject $authorityFlags -PropertyPath @('explicit_runtime_skill') -DefaultValue $DefaultRuntimeSkill
        skill_mismatch = Get-VibeNestedPropertySafe -InputObject $divergenceShadow -PropertyPath @('skill_mismatch') -DefaultValue $false
        confirm_required = Get-VibeNestedPropertySafe -InputObject $routeSnapshot -PropertyPath @('confirm_required') -DefaultValue $false
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
        specialist_consultation_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\specialist-consultation-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        skill_promotion_policy = if (Test-Path -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json')) { Get-Content -LiteralPath (Join-Path $repoRoot 'config\skill-promotion-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json } else { Get-VgoSkillPromotionPolicyDefaults }
        execution_topology_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-topology-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        native_specialist_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\native-specialist-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        requirement_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\requirement-doc-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        plan_execution_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\plan-execution-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        execution_runtime_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\execution-runtime-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        governed_evolution_artifact_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\governed-evolution-artifact-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        cleanup_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\phase-cleanup-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        proof_class_registry = Get-Content -LiteralPath (Join-Path $repoRoot 'config\proof-class-registry.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_governance = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-governance.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_tier_router = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-tier-router.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_runtime_v3_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-runtime-v3-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_stage_activation_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-stage-activation-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_retrieval_budget_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-retrieval-budget-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_disclosure_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-disclosure-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        memory_ingest_policy = Get-Content -LiteralPath (Join-Path $repoRoot 'config\memory-ingest-policy.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        workspace_memory_plane = Get-Content -LiteralPath (Join-Path $repoRoot 'config\workspace-memory-plane.json') -Raw -Encoding UTF8 | ConvertFrom-Json
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
    return [pscustomobject]@{
        identity_scope = 'workspace'
        driver_contract = 'workspace_shared_memory_v1'
        logical_owners = @('state_store', 'serena', 'ruflo', 'cognee')
    }
}

function Test-VibeWritableDirectory {
    param(
        [AllowEmptyString()] [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    $candidate = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $candidate)) {
        return $false
    }

    try {
        $item = Get-Item -LiteralPath $candidate -ErrorAction Stop
        $directory = if ($item.PSIsContainer) { [string]$item.FullName } else { [string]$item.Directory.FullName }
        if ([string]::IsNullOrWhiteSpace($directory)) {
            return $false
        }

        $probePath = Join-Path $directory ('.vibe-write-probe-{0}.tmp' -f [System.Guid]::NewGuid().ToString('N'))
        [System.IO.File]::WriteAllText($probePath, '')
        Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

function Resolve-VibeGovernedArtifactRootFromPath {
    param(
        [AllowEmptyString()] [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $resolvedPath)) {
        return $null
    }

    $container = if (Test-Path -LiteralPath $resolvedPath -PathType Container) {
        $resolvedPath
    } else {
        Split-Path -Parent $resolvedPath
    }
    if ([string]::IsNullOrWhiteSpace($container)) {
        return $null
    }

    $leafName = [System.IO.Path]::GetFileName($container)
    $parent = Split-Path -Parent $container
    if (($leafName -in @('requirements', 'plans')) -and ([System.IO.Path]::GetFileName($parent) -eq 'docs')) {
        return [System.IO.Path]::GetFullPath((Split-Path -Parent $parent))
    }

    return [System.IO.Path]::GetFullPath($container)
}

function Resolve-VibeNativeSpecialistWorkingRoot {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$SessionRoot = '',
        [AllowEmptyString()] [string]$RequirementDocPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanPath = '',
        [AllowEmptyString()] [string]$SourceArtifactPath = ''
    )

    $preferArtifactWorkspace = (
        (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/runtime/Invoke-VibeCanonicalEntry.ps1') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $RepoRoot 'config/version-governance.json') -PathType Leaf)
    )
    $orderedCandidates = if ($preferArtifactWorkspace) {
        @(
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $RequirementDocPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $ExecutionPlanPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $SourceArtifactPath),
            $SessionRoot,
            $RepoRoot
        )
    } else {
        @(
            $RepoRoot,
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $RequirementDocPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $ExecutionPlanPath),
            $(Resolve-VibeGovernedArtifactRootFromPath -Path $SourceArtifactPath),
            $SessionRoot
        )
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @($orderedCandidates)) {
        if ([string]::IsNullOrWhiteSpace([string]$candidate)) {
            continue
        }

        $resolvedCandidate = [System.IO.Path]::GetFullPath([string]$candidate)
        if (-not (Test-Path -LiteralPath $resolvedCandidate)) {
            continue
        }
        if (-not $candidates.Contains($resolvedCandidate)) {
            $candidates.Add($resolvedCandidate) | Out-Null
        }
    }

    foreach ($candidate in @($candidates)) {
        if (Test-VibeWritableDirectory -Path $candidate) {
            return $candidate
        }
    }

    if ($candidates.Count -gt 0) {
        return [string]$candidates[0]
    }

    return [System.IO.Path]::GetFullPath($RepoRoot)
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
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract
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
    $memoryPlane = Get-VibeWorkspaceMemoryPlaneContract
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

function Get-VibeSpecialistDecisionSidecarPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return Join-Path $SessionRoot 'specialist-decision.json'
}

function Get-VibeOptionalSpecialistDecisionOverride {
    param(
        [AllowEmptyString()] [string]$SessionRoot
    )

    if ([string]::IsNullOrWhiteSpace($SessionRoot)) {
        return $null
    }

    $path = Get-VibeSpecialistDecisionSidecarPath -SessionRoot $SessionRoot
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }

    return [pscustomobject]@{
        path = [string]$path
        payload = (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
}

function Get-VibeSpecialistDecisionDefaultNotes {
    param(
        [AllowEmptyString()] [string]$DecisionState = '',
        [AllowEmptyString()] [string]$ResolutionMode = ''
    )

    switch ($ResolutionMode) {
        'approved_dispatch' { return 'Bounded specialist recommendations were surfaced and auto-promoted into approved dispatch.' }
        'degraded' { return 'Specialist recommendations existed, but execution remained explicitly degraded before live native dispatch closed cleanly.' }
        'blocked' { return 'Specialist recommendations existed, but execution stayed blocked before live native dispatch could proceed.' }
        'local_suggestion_only' { return 'Residual local specialist suggestions remained advisory and require explicit escalation before execution.' }
        'no_specialist_needed' { return 'No bounded specialist recommendations were frozen for this run, and governed execution explicitly recorded that no specialist help was needed.' }
        'repo_asset_fallback' { return 'No bounded specialist recommendations were frozen for this run, and governed execution explicitly recorded a repo-asset fallback that must remain traceable.' }
        'pending_resolution' { return 'No bounded specialist recommendations were frozen for this run; execution must explicitly resolve whether no specialist was needed or a repo-asset fallback was used.' }
    }

    switch ($DecisionState) {
        'approved_dispatch' { return 'Bounded specialist recommendations were surfaced and auto-promoted into approved dispatch.' }
        'degraded' { return 'Specialist recommendations existed, but execution remained explicitly degraded before live native dispatch closed cleanly.' }
        'blocked' { return 'Specialist recommendations existed, but execution stayed blocked before live native dispatch could proceed.' }
        'local_suggestion_only' { return 'Residual local specialist suggestions remained advisory and require explicit escalation before execution.' }
        default { return 'No bounded specialist recommendations were frozen for this run; execution must explicitly resolve whether no specialist was needed or a repo-asset fallback was used.' }
    }
}

function New-VibeSpecialistDecisionProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$LocalSuggestions = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$BlockedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [object[]]$DegradedDispatch = @(),
        [AllowEmptyCollection()] [AllowNull()] [string[]]$MatchedSkillIds = @(),
        [AllowEmptyCollection()] [AllowNull()] [string[]]$SurfacedSkillIds = @(),
        [int]$RecommendationCount = -1,
        [AllowNull()] [object]$OverridePayload = $null,
        [AllowEmptyString()] [string]$OverrideSourcePath = ''
    )

    $dispatchSource = if (
        $null -ne $RuntimeInputPacket -and
        (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'specialist_dispatch') -and
        $null -ne $RuntimeInputPacket.specialist_dispatch
    ) {
        $RuntimeInputPacket.specialist_dispatch
    } else {
        $null
    }

    $approvedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $ApprovedDispatch) -gt 0) {
        @($ApprovedDispatch)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'approved_dispatch')) {
        @($dispatchSource.approved_dispatch)
    } else {
        @()
    }
    $localSuggestionArray = if ((Get-VibeSafeArrayCount -InputObject $LocalSuggestions) -gt 0) {
        @($LocalSuggestions)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'local_specialist_suggestions')) {
        @($dispatchSource.local_specialist_suggestions)
    } else {
        @()
    }
    $blockedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $BlockedDispatch) -gt 0) {
        @($BlockedDispatch)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'blocked')) {
        @($dispatchSource.blocked)
    } else {
        @()
    }
    $degradedDispatchArray = if ((Get-VibeSafeArrayCount -InputObject $DegradedDispatch) -gt 0) {
        @($DegradedDispatch)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'degraded')) {
        @($dispatchSource.degraded)
    } else {
        @()
    }

    $approvedDispatchSkillIds = @($approvedDispatchArray | ForEach-Object {
        if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $localSuggestionSkillIds = if ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'local_suggestion_skill_ids') -and (Get-VibeSafeArrayCount -InputObject $dispatchSource.local_suggestion_skill_ids) -gt 0) {
        @($dispatchSource.local_suggestion_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @($localSuggestionArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $blockedSkillIds = if ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'blocked_skill_ids') -and (Get-VibeSafeArrayCount -InputObject $dispatchSource.blocked_skill_ids) -gt 0) {
        @($dispatchSource.blocked_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @($blockedDispatchArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $degradedSkillIds = if ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'degraded_skill_ids') -and (Get-VibeSafeArrayCount -InputObject $dispatchSource.degraded_skill_ids) -gt 0) {
        @($dispatchSource.degraded_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } else {
        @($degradedDispatchArray | ForEach-Object {
            if ($null -ne $_ -and (Test-VibeObjectHasProperty -InputObject $_ -PropertyName 'skill_id')) { [string]$_.skill_id } else { '' }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $explicitMatchedSkillIds = @()
    if ($null -ne $MatchedSkillIds) {
        $explicitMatchedSkillIds = @($MatchedSkillIds | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $matchedSkillIds = @()
    if (@($explicitMatchedSkillIds).Count -gt 0) {
        $matchedSkillIds = @($explicitMatchedSkillIds)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'matched_skill_ids')) {
        $matchedSkillIds = @($dispatchSource.matched_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $explicitSurfacedSkillIds = @()
    if ($null -ne $SurfacedSkillIds) {
        $explicitSurfacedSkillIds = @($SurfacedSkillIds | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $surfacedSkillIds = @()
    if (@($explicitSurfacedSkillIds).Count -gt 0) {
        $surfacedSkillIds = @($explicitSurfacedSkillIds)
    } elseif ($null -ne $dispatchSource -and (Test-VibeObjectHasProperty -InputObject $dispatchSource -PropertyName 'surfaced_skill_ids')) {
        $surfacedSkillIds = @($dispatchSource.surfaced_skill_ids | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    }
    $recommendationCountResolved = if ($RecommendationCount -ge 0) {
        [int]$RecommendationCount
    } elseif ($null -ne $RuntimeInputPacket -and (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'specialist_recommendations')) {
        @($RuntimeInputPacket.specialist_recommendations).Count
    } else {
        @($surfacedSkillIds).Count
    }

    $decisionState = if (@($approvedDispatchSkillIds).Count -gt 0) {
        'approved_dispatch'
    } elseif (@($degradedSkillIds).Count -gt 0) {
        'degraded'
    } elseif (@($blockedSkillIds).Count -gt 0) {
        'blocked'
    } elseif (@($localSuggestionSkillIds).Count -gt 0) {
        'local_suggestion_only'
    } else {
        'no_specialist_recommendations'
    }

    $resolutionMode = switch ($decisionState) {
        'approved_dispatch' { 'approved_dispatch' }
        'degraded' { 'degraded' }
        'blocked' { 'blocked' }
        'local_suggestion_only' { 'local_suggestion_only' }
        default { 'pending_resolution' }
    }
    $resolutionNotes = Get-VibeSpecialistDecisionDefaultNotes -DecisionState $decisionState -ResolutionMode $resolutionMode

    $repoAssetFallback = [pscustomobject]@{
        used = $false
        asset_paths = @()
        reason = ''
        legal_basis = ''
        traceability_basis = @()
    }

    if ($null -ne $OverridePayload) {
        $overrideProvidedNotes = $false
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'decision_state') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.decision_state)) {
            $decisionState = [string]$OverridePayload.decision_state
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'resolution_mode') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.resolution_mode)) {
            $resolutionMode = [string]$OverridePayload.resolution_mode
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'notes') -and -not [string]::IsNullOrWhiteSpace([string]$OverridePayload.notes)) {
            $resolutionNotes = [string]$OverridePayload.notes
            $overrideProvidedNotes = $true
        }
        if ((Test-VibeObjectHasProperty -InputObject $OverridePayload -PropertyName 'repo_asset_fallback') -and $null -ne $OverridePayload.repo_asset_fallback) {
            $repoAssetFallbackSource = $OverridePayload.repo_asset_fallback
            $repoAssetFallbackAssetPaths = if (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'asset_paths') {
                @($repoAssetFallbackSource.asset_paths | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
            $repoAssetFallbackTraceabilityBasis = if (
                (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'traceability_basis') -and
                $null -ne $repoAssetFallbackSource.traceability_basis
            ) {
                @($repoAssetFallbackSource.traceability_basis | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
            } else {
                @()
            }
            $repoAssetFallback = [pscustomobject]@{
                used = if (Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'used') { [bool]$repoAssetFallbackSource.used } else { @($repoAssetFallbackAssetPaths).Count -gt 0 }
                asset_paths = @($repoAssetFallbackAssetPaths)
                reason = if ((Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string]$repoAssetFallbackSource.reason)) { [string]$repoAssetFallbackSource.reason } else { '' }
                legal_basis = if ((Test-VibeObjectHasProperty -InputObject $repoAssetFallbackSource -PropertyName 'legal_basis') -and -not [string]::IsNullOrWhiteSpace([string]$repoAssetFallbackSource.legal_basis)) { [string]$repoAssetFallbackSource.legal_basis } else { '' }
                traceability_basis = @($repoAssetFallbackTraceabilityBasis)
            }
        }
        if (-not $overrideProvidedNotes) {
            $resolutionNotes = Get-VibeSpecialistDecisionDefaultNotes -DecisionState $decisionState -ResolutionMode $resolutionMode
        }
    }

    return [pscustomobject]@{
        decision_state = $decisionState
        resolution_mode = $resolutionMode
        recommendation_count = [int]$recommendationCountResolved
        matched_skill_ids = @($matchedSkillIds)
        surfaced_skill_ids = @($surfacedSkillIds)
        approved_dispatch_skill_ids = @($approvedDispatchSkillIds)
        local_suggestion_skill_ids = @($localSuggestionSkillIds)
        blocked_skill_ids = @($blockedSkillIds)
        degraded_skill_ids = @($degradedSkillIds)
        repo_asset_fallback = $repoAssetFallback
        notes = $resolutionNotes
        source = if ([string]::IsNullOrWhiteSpace($OverrideSourcePath)) { 'runtime_structural_projection' } else { 'runtime_structural_projection_plus_sidecar' }
        override_source_path = if ([string]::IsNullOrWhiteSpace($OverrideSourcePath)) { $null } else { [string]$OverrideSourcePath }
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
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = '',
        [AllowEmptyString()] [string]$RequestedGradeFloor = '',
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
    $selected = Get-VibePropertySafe -InputObject $RouteResult -PropertyName 'selected'
    $routerSelectedSkill = if ($null -ne $selected) { [string]$selected.skill } else { $null }

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

    $packetSpecialistDecision = New-VibeSpecialistDecisionProjection `
        -ApprovedDispatch @($SpecialistDispatch.approved_dispatch) `
        -LocalSuggestions @($SpecialistDispatch.local_specialist_suggestions) `
        -BlockedDispatch $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'blocked' -and $null -ne $SpecialistDispatch.blocked) { @($SpecialistDispatch.blocked) } else { @() }) `
        -DegradedDispatch $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'degraded' -and $null -ne $SpecialistDispatch.degraded) { @($SpecialistDispatch.degraded) } else { @() }) `
        -MatchedSkillIds $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'matched_skill_ids' -and $null -ne $SpecialistDispatch.matched_skill_ids) { @($SpecialistDispatch.matched_skill_ids) } else { @() }) `
        -SurfacedSkillIds $(if ($SpecialistDispatch.PSObject.Properties.Name -contains 'surfaced_skill_ids' -and $null -ne $SpecialistDispatch.surfaced_skill_ids) { @($SpecialistDispatch.surfaced_skill_ids) } else { @() }) `
        -RecommendationCount @($SpecialistRecommendations).Count

    return [pscustomobject]@{
        stage = 'runtime_input_freeze'
        run_id = $RunId
        governance_scope = Get-VibeNestedPropertySafe -InputObject $HierarchyState -PropertyPath @('governance_scope') -DefaultValue ''
        task = $Task
        entry_intent_id = if ([string]::IsNullOrWhiteSpace($EntryIntentId)) { $null } else { [string]$EntryIntentId }
        requested_stage_stop = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) { $null } else { [string]$RequestedStageStop }
        requested_grade_floor = if ([string]::IsNullOrWhiteSpace($RequestedGradeFloor)) { $null } else { [string]$RequestedGradeFloor }
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
            selected_pack = if ($null -ne $selected) { [string]$selected.pack_id } else { $null }
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
            escalation_required = Get-VibeNestedPropertySafe -InputObject $SpecialistDispatch -PropertyPath @('escalation_required') -DefaultValue $false
            escalation_status = Get-VibeNestedPropertySafe -InputObject $SpecialistDispatch -PropertyPath @('escalation_status') -DefaultValue ''
            approval_owner = Get-VibeNestedPropertySafe -InputObject $Policy -PropertyPath @('child_specialist_suggestion_contract', 'approval_owner') -DefaultValue 'root_vibe'
            status = Get-VibeNestedPropertySafe -InputObject $Policy -PropertyPath @('child_specialist_suggestion_contract', 'status') -DefaultValue 'auto_promote_when_safe_same_round'
        }
        specialist_decision = $packetSpecialistDecision
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

function Resolve-VibeRequestedStageStop {
    param(
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    $stageOrder = @(Get-VibeGovernedRuntimeStageOrder)
    if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        return [string]$stageOrder[$stageOrder.Count - 1]
    }

    $normalized = [string]$RequestedStageStop
    if ($stageOrder -notcontains $normalized) {
        throw ("unsupported requested governed stage stop: {0}" -f $RequestedStageStop)
    }
    return $normalized
}

function Read-VibeEntrySurfaceConfig {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot
    )

    $configPath = Join-Path $RepoRoot 'config\vibe-entry-surfaces.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw ("vibe entry surface config not found: {0}" -f $configPath)
    }

    return Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-VibeEntryRequestedStageStop {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$EntryIntentId = '',
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        return Resolve-VibeRequestedStageStop -RequestedStageStop $RequestedStageStop
    }

    if (-not [string]::IsNullOrWhiteSpace($EntryIntentId)) {
        $surfaceConfig = Read-VibeEntrySurfaceConfig -RepoRoot $RepoRoot
        foreach ($entry in @($surfaceConfig.entries)) {
            if ($null -eq $entry) {
                continue
            }
            $entryId = if (
                $entry.PSObject.Properties.Name -contains 'id' -and
                -not [string]::IsNullOrWhiteSpace([string]$entry.id)
            ) {
                [string]$entry.id
            } else {
                ''
            }
            if ($entryId -ne [string]$EntryIntentId) {
                continue
            }

            $entryRequestedStop = if (
                $entry.PSObject.Properties.Name -contains 'requested_stage_stop' -and
                -not [string]::IsNullOrWhiteSpace([string]$entry.requested_stage_stop)
            ) {
                [string]$entry.requested_stage_stop
            } else {
                ''
            }
            if (-not [string]::IsNullOrWhiteSpace($entryRequestedStop)) {
                return Resolve-VibeRequestedStageStop -RequestedStageStop $entryRequestedStop
            }
            break
        }
    }

    return Resolve-VibeRequestedStageStop -RequestedStageStop ''
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
        [Parameter(Mandatory)] [string]$SkeletonReceiptPath,
        [Parameter(Mandatory)] [string]$RuntimeInputPacketPath,
        [Parameter(Mandatory)] [string]$GovernanceCapsulePath,
        [Parameter(Mandatory)] [string]$StageLineagePath,
        [AllowEmptyString()] [string]$IntentContractPath = '',
        [AllowEmptyString()] [string]$RequirementDocPath = '',
        [AllowEmptyString()] [string]$RequirementReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanPath = '',
        [AllowEmptyString()] [string]$ExecutionPlanReceiptPath = '',
        [AllowEmptyString()] [string]$ExecuteReceiptPath = '',
        [AllowEmptyString()] [string]$ExecutionManifestPath = '',
        [AllowEmptyString()] [string]$ExecutionTopologyPath = '',
        [AllowEmptyString()] [string]$ExecutionProofManifestPath = '',
        [AllowEmptyString()] [string]$DiscussionSpecialistConsultationPath = '',
        [AllowEmptyString()] [string]$PlanningSpecialistConsultationPath = '',
        [AllowEmptyString()] [string]$SpecialistLifecycleDisclosurePath = '',
        [AllowEmptyString()] [string]$HostStageDisclosurePath = '',
        [AllowEmptyString()] [string]$HostUserBriefingPath = '',
        [AllowEmptyString()] [string]$CleanupReceiptPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceReportPath = '',
        [AllowEmptyString()] [string]$DeliveryAcceptanceMarkdownPath = '',
        [AllowEmptyString()] [string]$MemoryActivationReportPath = '',
        [AllowEmptyString()] [string]$MemoryActivationMarkdownPath = '',
        [AllowEmptyString()] [string]$DelegationEnvelopePath = '',
        [AllowEmptyString()] [string]$DelegationValidationReceiptPath = '',
        [AllowEmptyString()] [string]$ObservedFailurePatternsPath = '',
        [AllowEmptyString()] [string]$ObservedPitfallEventsPath = '',
        [AllowEmptyString()] [string]$AtomicSkillCallChainPath = '',
        [AllowEmptyString()] [string]$ProposalLayerPath = '',
        [AllowEmptyString()] [string]$ProposalLayerMarkdownPath = '',
        [AllowEmptyString()] [string]$ApplicationReadinessReportPath = '',
        [AllowEmptyString()] [string]$ApplicationReadinessMarkdownPath = '',
        [AllowEmptyString()] [string]$WarningCardsPath = '',
        [AllowEmptyString()] [string]$PreflightChecklistPath = '',
        [AllowEmptyString()] [string]$RemediationNotesPath = '',
        [AllowEmptyString()] [string]$CandidateCompositeSkillDraftPath = '',
        [AllowEmptyString()] [string]$ThresholdPolicySuggestionPath = ''
    )

    return [pscustomobject]@{
        skeleton_receipt = $SkeletonReceiptPath
        runtime_input_packet = $RuntimeInputPacketPath
        governance_capsule = $GovernanceCapsulePath
        stage_lineage = $StageLineagePath
        intent_contract = if ([string]::IsNullOrWhiteSpace($IntentContractPath)) { $null } else { $IntentContractPath }
        requirement_doc = if ([string]::IsNullOrWhiteSpace($RequirementDocPath)) { $null } else { $RequirementDocPath }
        requirement_receipt = if ([string]::IsNullOrWhiteSpace($RequirementReceiptPath)) { $null } else { $RequirementReceiptPath }
        execution_plan = if ([string]::IsNullOrWhiteSpace($ExecutionPlanPath)) { $null } else { $ExecutionPlanPath }
        execution_plan_receipt = if ([string]::IsNullOrWhiteSpace($ExecutionPlanReceiptPath)) { $null } else { $ExecutionPlanReceiptPath }
        execute_receipt = if ([string]::IsNullOrWhiteSpace($ExecuteReceiptPath)) { $null } else { $ExecuteReceiptPath }
        execution_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionManifestPath)) { $null } else { $ExecutionManifestPath }
        execution_topology = if ([string]::IsNullOrWhiteSpace($ExecutionTopologyPath)) { $null } else { $ExecutionTopologyPath }
        execution_proof_manifest = if ([string]::IsNullOrWhiteSpace($ExecutionProofManifestPath)) { $null } else { $ExecutionProofManifestPath }
        discussion_specialist_consultation = if ([string]::IsNullOrWhiteSpace($DiscussionSpecialistConsultationPath)) { $null } else { $DiscussionSpecialistConsultationPath }
        planning_specialist_consultation = if ([string]::IsNullOrWhiteSpace($PlanningSpecialistConsultationPath)) { $null } else { $PlanningSpecialistConsultationPath }
        specialist_lifecycle_disclosure = if ([string]::IsNullOrWhiteSpace($SpecialistLifecycleDisclosurePath)) { $null } else { $SpecialistLifecycleDisclosurePath }
        host_stage_disclosure = if ([string]::IsNullOrWhiteSpace($HostStageDisclosurePath)) { $null } else { $HostStageDisclosurePath }
        host_user_briefing = if ([string]::IsNullOrWhiteSpace($HostUserBriefingPath)) { $null } else { $HostUserBriefingPath }
        cleanup_receipt = if ([string]::IsNullOrWhiteSpace($CleanupReceiptPath)) { $null } else { $CleanupReceiptPath }
        delivery_acceptance_report = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceReportPath)) { $null } else { $DeliveryAcceptanceReportPath }
        delivery_acceptance_markdown = if ([string]::IsNullOrWhiteSpace($DeliveryAcceptanceMarkdownPath)) { $null } else { $DeliveryAcceptanceMarkdownPath }
        memory_activation_report = if ([string]::IsNullOrWhiteSpace($MemoryActivationReportPath)) { $null } else { $MemoryActivationReportPath }
        memory_activation_markdown = if ([string]::IsNullOrWhiteSpace($MemoryActivationMarkdownPath)) { $null } else { $MemoryActivationMarkdownPath }
        delegation_envelope = if ([string]::IsNullOrWhiteSpace($DelegationEnvelopePath)) { $null } else { $DelegationEnvelopePath }
        delegation_validation_receipt = if ([string]::IsNullOrWhiteSpace($DelegationValidationReceiptPath)) { $null } else { $DelegationValidationReceiptPath }
        observed_failure_patterns = if ([string]::IsNullOrWhiteSpace($ObservedFailurePatternsPath)) { $null } else { $ObservedFailurePatternsPath }
        observed_pitfall_events = if ([string]::IsNullOrWhiteSpace($ObservedPitfallEventsPath)) { $null } else { $ObservedPitfallEventsPath }
        atomic_skill_call_chain = if ([string]::IsNullOrWhiteSpace($AtomicSkillCallChainPath)) { $null } else { $AtomicSkillCallChainPath }
        proposal_layer = if ([string]::IsNullOrWhiteSpace($ProposalLayerPath)) { $null } else { $ProposalLayerPath }
        proposal_layer_markdown = if ([string]::IsNullOrWhiteSpace($ProposalLayerMarkdownPath)) { $null } else { $ProposalLayerMarkdownPath }
        application_readiness_report = if ([string]::IsNullOrWhiteSpace($ApplicationReadinessReportPath)) { $null } else { $ApplicationReadinessReportPath }
        application_readiness_markdown = if ([string]::IsNullOrWhiteSpace($ApplicationReadinessMarkdownPath)) { $null } else { $ApplicationReadinessMarkdownPath }
        warning_cards = if ([string]::IsNullOrWhiteSpace($WarningCardsPath)) { $null } else { $WarningCardsPath }
        preflight_checklist = if ([string]::IsNullOrWhiteSpace($PreflightChecklistPath)) { $null } else { $PreflightChecklistPath }
        remediation_notes = if ([string]::IsNullOrWhiteSpace($RemediationNotesPath)) { $null } else { $RemediationNotesPath }
        candidate_composite_skill_draft = if ([string]::IsNullOrWhiteSpace($CandidateCompositeSkillDraftPath)) { $null } else { $CandidateCompositeSkillDraftPath }
        threshold_policy_suggestion = if ([string]::IsNullOrWhiteSpace($ThresholdPolicySuggestionPath)) { $null } else { $ThresholdPolicySuggestionPath }
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

    $policy = Get-VibePropertySafe -InputObject $MemoryActivationReport -PropertyName 'policy'
    $summary = Get-VibePropertySafe -InputObject $MemoryActivationReport -PropertyName 'summary'

    return [pscustomobject]@{
        policy_mode = Get-VibeNestedPropertySafe -InputObject $policy -PropertyPath @('mode') -DefaultValue ''
        routing_contract = Get-VibeNestedPropertySafe -InputObject $policy -PropertyPath @('routing_contract') -DefaultValue ''
        fallback_event_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('fallback_event_count') -DefaultValue 0
        artifact_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('artifact_count') -DefaultValue 0
        budget_guard_respected = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('budget_guard_respected') -DefaultValue $false
    }
}

function New-VibeRuntimeSummaryDeliveryAcceptanceProjection {
    param(
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    if ($null -eq $DeliveryAcceptanceReport) {
        return $null
    }

    $summary = Get-VibePropertySafe -InputObject $DeliveryAcceptanceReport -PropertyName 'summary'

    return [pscustomobject]@{
        gate_result = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('gate_result') -DefaultValue ''
        completion_language_allowed = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('completion_language_allowed') -DefaultValue $false
        readiness_state = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('readiness_state') -DefaultValue ''
        manual_review_layer_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('manual_review_layer_count') -DefaultValue 0
        failing_layer_count = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('failing_layer_count') -DefaultValue 0
    }
}

function Read-VibeJsonArtifactIfExists {
    param([AllowEmptyString()] [string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "Failed to parse JSON artifact '$Path': $($_.Exception.Message)"
    }
}

function Test-VibeGovernedStageReached {
    param(
        [AllowEmptyString()] [string]$TerminalStage,
        [AllowEmptyString()] [string]$TargetStage
    )

    if ([string]::IsNullOrWhiteSpace($TerminalStage) -or [string]::IsNullOrWhiteSpace($TargetStage)) {
        return $false
    }

    $stageOrder = @(Get-VibeGovernedRuntimeStageOrder)
    $terminalIndex = [Array]::IndexOf($stageOrder, [string]$TerminalStage)
    $targetIndex = [Array]::IndexOf($stageOrder, [string]$TargetStage)
    if ($terminalIndex -lt 0 -or $targetIndex -lt 0) {
        return $false
    }

    return ($terminalIndex -ge $targetIndex)
}

function Resolve-VibeGovernedEvolutionArtifactAllowList {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    $policy = Get-VibePropertySafe -InputObject $Runtime -PropertyName 'governed_evolution_artifact_policy'
    if ($null -eq $policy) {
        return @()
    }

    $stopStage = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        if ((Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'default_stop_stage') -and -not [string]::IsNullOrWhiteSpace([string]$policy.default_stop_stage)) {
            [string]$policy.default_stop_stage
        } else {
            'phase_cleanup'
        }
    } else {
        [string]$RequestedStageStop
    }

    $profiles = Get-VibePropertySafe -InputObject $policy -PropertyName 'stop_stage_profiles'
    if ($null -eq $profiles -or $profiles.PSObject.Properties.Name -notcontains $stopStage) {
        return @()
    }

    $profile = $profiles.$stopStage
    $resolved = New-Object System.Collections.Generic.List[string]
    $steps = Get-VibePropertySafe -InputObject $profile -PropertyName 'steps'
    if ($null -eq $steps) {
        return @()
    }

    foreach ($stepName in @($steps.PSObject.Properties.Name)) {
        $stepProfile = $steps.$stepName
        $enabledArtifacts = Get-VibePropertySafe -InputObject $stepProfile -PropertyName 'enabled_artifacts' -DefaultValue @()
        foreach ($artifactName in @($enabledArtifacts)) {
            $name = [string]$artifactName
            if (-not [string]::IsNullOrWhiteSpace($name) -and -not $resolved.Contains($name)) {
                [void]$resolved.Add($name)
            }
        }
    }

    return @($resolved)
}

function Test-VibeGovernedEvolutionArtifactAllowed {
    param(
        [string[]]$AllowedArtifacts = @(),
        [Parameter(Mandatory)] [string]$ArtifactName
    )

    return (@($AllowedArtifacts) -contains [string]$ArtifactName)
}

function Get-VibeGovernedEvolutionArtifactPolicyDefinition {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$ArtifactName
    )

    $policy = Get-VibePropertySafe -InputObject $Runtime -PropertyName 'governed_evolution_artifact_policy'
    $steps = Get-VibePropertySafe -InputObject $policy -PropertyName 'steps'
    if ($null -eq $steps) {
        return $null
    }

    foreach ($stepName in @($steps.PSObject.Properties.Name)) {
        $stepDefinition = $steps.$stepName
        if ($null -ne $stepDefinition -and $stepDefinition.PSObject.Properties.Name -contains $ArtifactName) {
            return $stepDefinition.$ArtifactName
        }
    }

    return $null
}

function Test-VibeGovernedEvolutionArtifactUnitAllowed {
    param(
        [Parameter(Mandatory)] [object]$Runtime,
        [Parameter(Mandatory)] [string]$ArtifactFileName,
        [Parameter(Mandatory)] [string]$UnitName,
        [AllowEmptyString()] [string]$RequestedStageStop = ''
    )

    $artifactDefinition = Get-VibeGovernedEvolutionArtifactPolicyDefinition -Runtime $Runtime -ArtifactName $ArtifactFileName
    if ($null -eq $artifactDefinition) {
        return $false
    }
    $units = Get-VibePropertySafe -InputObject $artifactDefinition -PropertyName 'units'
    if ($null -eq $units -or $units.PSObject.Properties.Name -notcontains $UnitName) {
        return $false
    }

    $unitDefinition = $units.$UnitName
    $firstAvailableStage = Get-VibePropertySafe -InputObject $unitDefinition -PropertyName 'first_available_stage' -DefaultValue ''
    if ([string]::IsNullOrWhiteSpace([string]$firstAvailableStage)) {
        return $false
    }

    $effectiveStopStage = if ([string]::IsNullOrWhiteSpace($RequestedStageStop)) {
        $policy = Get-VibePropertySafe -InputObject $Runtime -PropertyName 'governed_evolution_artifact_policy'
        if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'default_stop_stage')) {
            [string]$policy.default_stop_stage
        } else {
            'phase_cleanup'
        }
    } else {
        [string]$RequestedStageStop
    }

    return (Test-VibeGovernedStageReached -TerminalStage $effectiveStopStage -TargetStage ([string]$firstAvailableStage))
}

function Get-VibePropertyCount {
    param(
        [AllowNull()] [object]$Map,
        [Parameter(Mandatory)] [string]$Name
    )

    if ($null -eq $Map) {
        return 0
    }
    $property = $Map.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return 0
    }

    try {
        return [int]$property.Value
    } catch {
        return 0
    }
}

function Get-VibeObservedMemberValue {
    param(
        [AllowNull()] [object]$InputObject,
        [Parameter(Mandatory)] [string]$Name
    )

    if ($null -eq $InputObject) {
        return $null
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Contains($Name)) {
            return $InputObject[$Name]
        }
        return $null
    }
    foreach ($property in @($InputObject.PSObject.Properties)) {
        if ([string]$property.Name -eq $Name) {
            return $property.Value
        }
    }
    return $null
}

function ConvertTo-VibeObservedArray {
    param([AllowNull()] [object]$InputObject)

    if ($null -eq $InputObject) {
        return @()
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Count -eq 0) {
            return @()
        }
        return @($InputObject)
    }
    $properties = @($InputObject.PSObject.Properties)
    if ($properties.Count -eq 0 -and -not ($InputObject -is [string])) {
        return @()
    }
    return @($InputObject)
}

function Get-VibeProcessHealthObservationContext {
    param([AllowNull()] [object]$CleanupReceipt)

    $auditPath = $null
    $cleanupPreviewPath = $null
    if ($null -ne $CleanupReceipt -and (Test-VibeObjectHasProperty -InputObject $CleanupReceipt -PropertyName 'cleanup_result') -and $null -ne $CleanupReceipt.cleanup_result) {
        if (
            (Test-VibeObjectHasProperty -InputObject $CleanupReceipt.cleanup_result -PropertyName 'node_audit') -and
            $null -ne $CleanupReceipt.cleanup_result.node_audit -and
            (Test-VibeObjectHasProperty -InputObject $CleanupReceipt.cleanup_result.node_audit -PropertyName 'artifact_path') -and
            -not [string]::IsNullOrWhiteSpace([string]$CleanupReceipt.cleanup_result.node_audit.artifact_path)
        ) {
            $auditPath = [string]$CleanupReceipt.cleanup_result.node_audit.artifact_path
        }
        if (
            (Test-VibeObjectHasProperty -InputObject $CleanupReceipt.cleanup_result -PropertyName 'node_cleanup_preview') -and
            $null -ne $CleanupReceipt.cleanup_result.node_cleanup_preview -and
            (Test-VibeObjectHasProperty -InputObject $CleanupReceipt.cleanup_result.node_cleanup_preview -PropertyName 'artifact_path') -and
            -not [string]::IsNullOrWhiteSpace([string]$CleanupReceipt.cleanup_result.node_cleanup_preview.artifact_path)
        ) {
            $cleanupPreviewPath = [string]$CleanupReceipt.cleanup_result.node_cleanup_preview.artifact_path
        }
    }

    return [pscustomobject]@{
        audit_path = $auditPath
        audit_payload = Read-VibeJsonArtifactIfExists -Path $auditPath
        cleanup_preview_path = $cleanupPreviewPath
        cleanup_preview_payload = Read-VibeJsonArtifactIfExists -Path $cleanupPreviewPath
    }
}

function New-VibeObservedFailurePatternsArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ExecutionManifest,
        [AllowNull()] [object]$CleanupReceipt,
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    $processHealth = Get-VibeProcessHealthObservationContext -CleanupReceipt $CleanupReceipt
    $executionStatus = [string](Get-VibeObservedMemberValue -InputObject $ExecutionManifest -Name 'status')
    $cleanupMode = [string](Get-VibeObservedMemberValue -InputObject $CleanupReceipt -Name 'cleanup_mode')
    $deliverySummary = Get-VibeObservedMemberValue -InputObject $DeliveryAcceptanceReport -Name 'summary'
    $gateResult = [string](Get-VibeObservedMemberValue -InputObject $deliverySummary -Name 'gate_result')
    $runtimeStatus = [string](Get-VibeObservedMemberValue -InputObject $deliverySummary -Name 'runtime_status')
    $readinessState = [string](Get-VibeObservedMemberValue -InputObject $deliverySummary -Name 'readiness_state')
    $processSummary = Get-VibeObservedMemberValue -InputObject $processHealth.audit_payload -Name 'summary'
    $classifications = Get-VibeObservedMemberValue -InputObject $processSummary -Name 'classifications'
    $cleanupCandidateCount = [int](Get-VibeObservedMemberValue -InputObject $processSummary -Name 'cleanup_candidate_count')
    $managedStaleCount = Get-VibePropertyCount -Map $classifications -Name 'managed_stale'
    $managedMissingHeartbeatCount = Get-VibePropertyCount -Map $classifications -Name 'managed_missing_heartbeat'
    $managedCompletedAliveCount = Get-VibePropertyCount -Map $classifications -Name 'managed_completed_process_alive'
    $partialCompletion = (
        (-not [string]::IsNullOrWhiteSpace($executionStatus) -and $executionStatus -ne 'completed' -and $executionStatus -ne 'failed') -or
        (-not [string]::IsNullOrWhiteSpace($runtimeStatus) -and $runtimeStatus -ne 'completed' -and $runtimeStatus -ne 'failed')
    )

    $patterns = @(
        [pscustomobject]@{
            pattern_id = 'execution_failed'
            classification = 'execution_failed'
            failure_type = 'execution_failed'
            active = ($executionStatus -eq 'failed')
            severity = 'high'
            evidence_refs = @('execution-manifest.json')
            details = [pscustomobject]@{ execution_status = if ([string]::IsNullOrWhiteSpace($executionStatus)) { $null } else { $executionStatus } }
        },
        [pscustomobject]@{
            pattern_id = 'partial_completion'
            classification = 'partial_completion'
            failure_type = 'partial_completion'
            active = [bool]$partialCompletion
            severity = 'medium'
            evidence_refs = @('execution-manifest.json', 'delivery-acceptance-report.json')
            details = [pscustomobject]@{
                execution_status = if ([string]::IsNullOrWhiteSpace($executionStatus)) { $null } else { $executionStatus }
                runtime_status = if ([string]::IsNullOrWhiteSpace($runtimeStatus)) { $null } else { $runtimeStatus }
            }
        },
        [pscustomobject]@{
            pattern_id = 'cleanup_degraded'
            classification = 'cleanup_degraded'
            failure_type = 'cleanup_degraded'
            active = ($cleanupMode -eq 'cleanup_degraded')
            severity = 'high'
            evidence_refs = @('cleanup-receipt.json')
            details = [pscustomobject]@{
                cleanup_mode = if ([string]::IsNullOrWhiteSpace($cleanupMode)) { $null } else { $cleanupMode }
                cleanup_error = [string](Get-VibeObservedMemberValue -InputObject $CleanupReceipt -Name 'cleanup_error')
            }
        },
        [pscustomobject]@{
            pattern_id = 'delivery_gate_failed'
            classification = 'delivery_gate_failed'
            failure_type = 'delivery_gate_failed'
            active = (-not [string]::IsNullOrWhiteSpace($gateResult) -and $gateResult -ne 'pass')
            severity = 'high'
            evidence_refs = @('delivery-acceptance-report.json')
            details = [pscustomobject]@{
                gate_result = if ([string]::IsNullOrWhiteSpace($gateResult)) { $null } else { $gateResult }
                readiness_state = if ([string]::IsNullOrWhiteSpace($readinessState)) { $null } else { $readinessState }
            }
        },
        [pscustomobject]@{
            pattern_id = 'process_health_risk'
            classification = 'process_health_risk'
            failure_type = 'process_health_risk'
            active = (($cleanupCandidateCount + $managedStaleCount + $managedMissingHeartbeatCount + $managedCompletedAliveCount) -gt 0)
            severity = 'medium'
            evidence_refs = @($(if ($processHealth.audit_path) { $processHealth.audit_path } else { 'cleanup-receipt.json' }))
            details = [pscustomobject]@{
                cleanup_candidate_count = $cleanupCandidateCount
                managed_stale_count = $managedStaleCount
                managed_missing_heartbeat_count = $managedMissingHeartbeatCount
                managed_completed_process_alive_count = $managedCompletedAliveCount
            }
        }
    )

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        summary = [pscustomobject]@{
            active_failure_pattern_count = @($patterns | Where-Object { $_.active }).Count
            has_any_failure_pattern = [bool](@($patterns | Where-Object { $_.active }).Count -gt 0)
        }
        patterns = @($patterns)
    }
}

function New-VibeObservedPitfallEventsArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$RuntimeInputPacket,
        [AllowNull()] [object]$CleanupReceipt,
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    $processHealth = Get-VibeProcessHealthObservationContext -CleanupReceipt $CleanupReceipt
    $routeSnapshot = Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'route_snapshot'
    $deliverySummary = Get-VibeObservedMemberValue -InputObject $DeliveryAcceptanceReport -Name 'summary'
    $processSummary = Get-VibeObservedMemberValue -InputObject $processHealth.audit_payload -Name 'summary'
    $classifications = Get-VibeObservedMemberValue -InputObject $processSummary -Name 'classifications'
    $cleanupCandidateCount = [int](Get-VibeObservedMemberValue -InputObject $processSummary -Name 'cleanup_candidate_count')
    $managedStaleCount = Get-VibePropertyCount -Map $classifications -Name 'managed_stale'
    $gateResult = [string](Get-VibeObservedMemberValue -InputObject $deliverySummary -Name 'gate_result')
    $cleanupMode = [string](Get-VibeObservedMemberValue -InputObject $CleanupReceipt -Name 'cleanup_mode')

    $events = @()
    if ([bool](Get-VibeObservedMemberValue -InputObject $routeSnapshot -Name 'confirm_required')) {
        $events += [pscustomobject]@{
            pitfall_type = 'confirm_required_route'
            source_layer = 'routing'
            source_artifact = 'runtime-input-packet.json'
            source_stage = 'runtime_input_packet'
            trigger_field = 'route_snapshot.confirm_required'
            trigger_value = $true
            count = 1
            confidence_level = 'high'
        }
    }
    if ([bool](Get-VibeObservedMemberValue -InputObject $routeSnapshot -Name 'fallback_active')) {
        $events += [pscustomobject]@{
            pitfall_type = 'fallback_active_route'
            source_layer = 'routing'
            source_artifact = 'runtime-input-packet.json'
            source_stage = 'runtime_input_packet'
            trigger_field = 'route_snapshot.fallback_active'
            trigger_value = $true
            count = 1
            confidence_level = 'high'
        }
    }
    if ([bool](Get-VibeObservedMemberValue -InputObject $routeSnapshot -Name 'non_authoritative')) {
        $events += [pscustomobject]@{
            pitfall_type = 'non_authoritative_route'
            source_layer = 'routing'
            source_artifact = 'runtime-input-packet.json'
            source_stage = 'runtime_input_packet'
            trigger_field = 'route_snapshot.non_authoritative'
            trigger_value = $true
            count = 1
            confidence_level = 'high'
        }
    }
    if ($cleanupCandidateCount -gt 0) {
        $events += [pscustomobject]@{
            pitfall_type = 'cleanup_candidate_present'
            source_layer = 'process_health'
            source_artifact = if ($processHealth.audit_path) { $processHealth.audit_path } else { 'cleanup-receipt.json' }
            source_stage = 'phase_cleanup'
            trigger_field = 'summary.cleanup_candidate_count'
            trigger_value = $cleanupCandidateCount
            count = $cleanupCandidateCount
            confidence_level = 'high'
        }
    }
    if ($managedStaleCount -gt 0) {
        $events += [pscustomobject]@{
            pitfall_type = 'managed_stale_detected'
            source_layer = 'process_health'
            source_artifact = if ($processHealth.audit_path) { $processHealth.audit_path } else { 'cleanup-receipt.json' }
            source_stage = 'phase_cleanup'
            trigger_field = 'summary.classifications.managed_stale'
            trigger_value = $managedStaleCount
            count = $managedStaleCount
            confidence_level = 'high'
        }
    }
    if ($cleanupMode -eq 'cleanup_degraded') {
        $events += [pscustomobject]@{
            pitfall_type = 'cleanup_degraded'
            source_layer = 'cleanup'
            source_artifact = 'cleanup-receipt.json'
            source_stage = 'phase_cleanup'
            trigger_field = 'cleanup_mode'
            trigger_value = $cleanupMode
            count = 1
            confidence_level = 'high'
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($gateResult) -and $gateResult -ne 'pass') {
        $events += [pscustomobject]@{
            pitfall_type = 'delivery_gate_failed'
            source_layer = 'delivery'
            source_artifact = 'delivery-acceptance-report.json'
            source_stage = 'phase_cleanup'
            trigger_field = 'summary.gate_result'
            trigger_value = $gateResult
            count = 1
            confidence_level = 'high'
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        summary = [pscustomobject]@{
            pitfall_event_count = @($events).Count
            has_any_pitfall_event = [bool](@($events).Count -gt 0)
        }
        events = @($events)
    }
}

function Get-VibeProposalEvidenceLevel {
    param(
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$AtomicSkillCallChain
    )

    $failureCount = if ($null -ne $ObservedFailurePatterns -and (Test-VibeObjectHasProperty -InputObject $ObservedFailurePatterns -PropertyName 'summary')) { [int]$ObservedFailurePatterns.summary.active_failure_pattern_count } else { 0 }
    $pitfallCount = if ($null -ne $ObservedPitfallEvents -and (Test-VibeObjectHasProperty -InputObject $ObservedPitfallEvents -PropertyName 'summary')) { [int]$ObservedPitfallEvents.summary.pitfall_event_count } else { 0 }
    $skillEventCount = if ($null -ne $AtomicSkillCallChain -and (Test-VibeObjectHasProperty -InputObject $AtomicSkillCallChain -PropertyName 'summary')) { [int]$AtomicSkillCallChain.summary.event_count } else { 0 }
    if ($failureCount -gt 0 -or $pitfallCount -gt 0) { return 'strong' }
    if ($skillEventCount -gt 0) { return 'moderate' }
    return 'limited'
}

function New-VibeAtomicSkillCallChainArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$RuntimeInputPacket,
        [AllowNull()] [object]$ExecutionTopology,
        [AllowNull()] [object]$ExecutionManifest,
        [AllowNull()] [object]$StageLineage
    )

    $events = @()
    $sequence = 0
    $runtimeInputGeneratedAt = [string](Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'generated_at')
    $authorityFlags = Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'authority_flags'
    $routeSnapshot = Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'route_snapshot'
    $specialistDispatch = Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'specialist_dispatch'
    $governorSkillId = [string](Get-VibeObservedMemberValue -InputObject $authorityFlags -Name 'explicit_runtime_skill')
    if ([string]::IsNullOrWhiteSpace($governorSkillId)) { $governorSkillId = [string](Get-VibeObservedMemberValue -InputObject $authorityFlags -Name 'runtime_entry') }
    if ([string]::IsNullOrWhiteSpace($governorSkillId)) { $governorSkillId = [string](Get-VibeObservedMemberValue -InputObject $routeSnapshot -Name 'selected_skill') }
    if ([string]::IsNullOrWhiteSpace($governorSkillId)) { $governorSkillId = 'vibe' }

    $sequence += 1
    $events += [pscustomobject]@{
        event_id = ('{0}-{1:d4}' -f $RunId, $sequence)
        sequence = $sequence
        run_id = $RunId
        observed_at = $runtimeInputGeneratedAt
        event_type = 'runtime_governor_activated'
        skill_id = $governorSkillId
        stage = 'skeleton_check'
        source_layer = 'runtime'
        source_artifact = 'runtime-input-packet.json'
        lane_id = $null
        unit_id = $null
        status = 'active'
        reason = 'governed_runtime_entry'
        dispatch_phase = $null
        binding_profile = $null
        write_scope = $null
        review_mode = $null
        confidence = $null
        degraded = $false
        verification_passed = $null
        evidence_refs = @('runtime-input-packet.json', 'stage-lineage.json')
    }

    foreach ($candidate in @(ConvertTo-VibeObservedArray -InputObject $(Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'specialist_recommendations'))) {
        $skillId = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'skill_id')
        if ([string]::IsNullOrWhiteSpace($skillId)) { continue }
        $sequence += 1
        $events += [pscustomobject]@{
            event_id = ('{0}-{1:d4}' -f $RunId, $sequence)
            sequence = $sequence
            run_id = $RunId
            observed_at = $runtimeInputGeneratedAt
            event_type = 'skill_candidate_surfaced'
            skill_id = $skillId
            stage = 'runtime_input_freeze'
            source_layer = 'routing'
            source_artifact = 'runtime-input-packet.json'
            lane_id = $null
            unit_id = $null
            status = 'candidate'
            reason = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'reason')
            dispatch_phase = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'dispatch_phase')
            binding_profile = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'binding_profile')
            write_scope = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'write_scope')
            review_mode = [string](Get-VibeObservedMemberValue -InputObject $candidate -Name 'review_mode')
            confidence = Get-VibeObservedMemberValue -InputObject $candidate -Name 'confidence'
            degraded = $false
            verification_passed = $null
            evidence_refs = @('runtime-input-packet.json')
        }
    }

    foreach ($dispatchType in @('approved_dispatch', 'blocked', 'degraded')) {
        foreach ($dispatchEntry in @(ConvertTo-VibeObservedArray -InputObject $(Get-VibeObservedMemberValue -InputObject $specialistDispatch -Name $dispatchType))) {
            $skillId = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'skill_id')
            if ([string]::IsNullOrWhiteSpace($skillId)) { continue }
            $sequence += 1
            $events += [pscustomobject]@{
                event_id = ('{0}-{1:d4}' -f $RunId, $sequence)
                sequence = $sequence
                run_id = $RunId
                observed_at = $runtimeInputGeneratedAt
                event_type = 'skill_dispatch_' + ($(if ($dispatchType -eq 'approved_dispatch') { 'approved' } else { $dispatchType }))
                skill_id = $skillId
                stage = 'runtime_input_freeze'
                source_layer = 'routing'
                source_artifact = 'runtime-input-packet.json'
                lane_id = $null
                unit_id = $null
                status = if ($dispatchType -eq 'approved_dispatch') { 'approved' } else { [string]$dispatchType }
                reason = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'recommended_promotion_action')
                dispatch_phase = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'dispatch_phase')
                binding_profile = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'binding_profile')
                write_scope = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'write_scope')
                review_mode = [string](Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'review_mode')
                confidence = Get-VibeObservedMemberValue -InputObject $dispatchEntry -Name 'confidence'
                degraded = [bool]($dispatchType -eq 'degraded')
                verification_passed = $null
                evidence_refs = @('runtime-input-packet.json')
            }
        }
    }

    foreach ($wave in @(ConvertTo-VibeObservedArray -InputObject $(Get-VibeObservedMemberValue -InputObject $ExecutionManifest -Name 'waves'))) {
        foreach ($step in @(ConvertTo-VibeObservedArray -InputObject $(Get-VibeObservedMemberValue -InputObject $wave -Name 'steps'))) {
            foreach ($unit in @(ConvertTo-VibeObservedArray -InputObject $(Get-VibeObservedMemberValue -InputObject $step -Name 'units'))) {
                $skillId = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'skill_id')
                if ([string]::IsNullOrWhiteSpace($skillId)) { continue }
                $resultPath = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'result_path')
                $evidenceRefs = @('execution-manifest.json')
                if (-not [string]::IsNullOrWhiteSpace($resultPath)) { $evidenceRefs += $resultPath }
                $sequence += 1
                $events += [pscustomobject]@{
                    event_id = ('{0}-{1:d4}' -f $RunId, $sequence)
                    sequence = $sequence
                    run_id = $RunId
                    observed_at = [string](Get-VibeObservedMemberValue -InputObject $ExecutionManifest -Name 'generated_at')
                    event_type = 'skill_execution_finished'
                    skill_id = $skillId
                    stage = 'plan_execute'
                    source_layer = 'execution'
                    source_artifact = 'execution-manifest.json'
                    lane_id = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'lane_id')
                    unit_id = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'unit_id')
                    status = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'status')
                    reason = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'execution_driver')
                    dispatch_phase = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'dispatch_phase')
                    binding_profile = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'binding_profile')
                    write_scope = [string](Get-VibeObservedMemberValue -InputObject $unit -Name 'write_scope')
                    review_mode = [string](Get-VibeObservedMemberValue -InputObject $step -Name 'review_mode')
                    confidence = $null
                    degraded = [bool](Get-VibeObservedMemberValue -InputObject $unit -Name 'degraded')
                    verification_passed = Get-VibeObservedMemberValue -InputObject $unit -Name 'verification_passed'
                    evidence_refs = @($evidenceRefs)
                }
            }
        }
    }

    $skillIds = @($events | ForEach-Object { [string]$_.skill_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    $executedSkillIds = @($events | Where-Object { $_.event_type -eq 'skill_execution_finished' } | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)
    $degradedSkillIds = @($events | Where-Object { [bool]$_.degraded } | ForEach-Object { [string]$_.skill_id } | Select-Object -Unique)

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        summary = [pscustomobject]@{
            event_count = @($events).Count
            skill_count = @($skillIds).Count
            executed_skill_count = @($executedSkillIds).Count
            degraded_skill_count = @($degradedSkillIds).Count
        }
        events = @($events)
    }
}

function New-VibeWarningCardsArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$DeliveryAcceptanceReport
    )

    $cards = @()
    foreach ($pattern in @($(if ($null -ne $ObservedFailurePatterns -and (Test-VibeObjectHasProperty -InputObject $ObservedFailurePatterns -PropertyName 'patterns')) { $ObservedFailurePatterns.patterns } else { @() }) | Where-Object { $_.active })) {
        $cards += [pscustomobject]@{
            card_id = 'warning-' + [string]$pattern.pattern_id
            severity = if ([string]::IsNullOrWhiteSpace([string]$pattern.severity)) { 'medium' } else { [string]$pattern.severity }
            title = ([string]$pattern.classification -replace '_', ' ')
            summary = "Observed active failure pattern: $([string]$pattern.classification)."
            source_signals = @([string]$pattern.classification)
            evidence_refs = @($pattern.evidence_refs)
            review_recommended = $true
        }
    }
    foreach ($pitfall in @($(if ($null -ne $ObservedPitfallEvents -and (Test-VibeObjectHasProperty -InputObject $ObservedPitfallEvents -PropertyName 'events')) { $ObservedPitfallEvents.events } else { @() }))) {
        $cards += [pscustomobject]@{
            card_id = 'warning-pitfall-' + [string]$pitfall.pitfall_type
            severity = if ([string]$pitfall.pitfall_type -match 'delivery|cleanup') { 'high' } else { 'medium' }
            title = ([string]$pitfall.pitfall_type -replace '_', ' ')
            summary = "Observed pitfall event: $([string]$pitfall.pitfall_type)."
            source_signals = @([string]$pitfall.pitfall_type)
            evidence_refs = @([string]$pitfall.source_artifact)
            review_recommended = $true
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{
            card_count = @($cards).Count
            high_severity_count = @(@($cards | Where-Object { [string]$_.severity -eq 'high' })).Count
        }
        cards = @($cards)
    }
}

function New-VibePreflightChecklistArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$RuntimeSummary
    )

    $checks = @()
    $seenIds = @{}
    foreach ($pattern in @($(if ($null -ne $ObservedFailurePatterns -and (Test-VibeObjectHasProperty -InputObject $ObservedFailurePatterns -PropertyName 'patterns')) { $ObservedFailurePatterns.patterns } else { @() }) | Where-Object { $_.active })) {
        $checkId = 'check-' + [string]$pattern.pattern_id
        if ($seenIds.ContainsKey($checkId)) { continue }
        $seenIds[$checkId] = $true
        $checks += [pscustomobject]@{
            check_id = $checkId
            label = "review $([string]$pattern.classification)"
            why = "Previous run observed active failure pattern '$([string]$pattern.classification)'."
            source_signal = [string]$pattern.classification
            required_before_next_run = $true
        }
    }
    foreach ($pitfall in @($(if ($null -ne $ObservedPitfallEvents -and (Test-VibeObjectHasProperty -InputObject $ObservedPitfallEvents -PropertyName 'events')) { $ObservedPitfallEvents.events } else { @() }))) {
        $checkId = 'check-pitfall-' + [string]$pitfall.pitfall_type
        if ($seenIds.ContainsKey($checkId)) { continue }
        $seenIds[$checkId] = $true
        $checks += [pscustomobject]@{
            check_id = $checkId
            label = "review $([string]$pitfall.pitfall_type)"
            why = "Previous run observed pitfall event '$([string]$pitfall.pitfall_type)'."
            source_signal = [string]$pitfall.pitfall_type
            required_before_next_run = $true
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{ check_count = @($checks).Count }
        checks = @($checks)
    }
}

function New-VibeRemediationNotesArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$AtomicSkillCallChain
    )

    $notes = @()
    foreach ($pattern in @($(if ($null -ne $ObservedFailurePatterns -and (Test-VibeObjectHasProperty -InputObject $ObservedFailurePatterns -PropertyName 'patterns')) { $ObservedFailurePatterns.patterns } else { @() }) | Where-Object { $_.active })) {
        $notes += [pscustomobject]@{
            note_id = 'remediation-' + [string]$pattern.pattern_id
            remediation_type = 'failure_pattern'
            suggested_remediation = "Review and contain failure pattern '$([string]$pattern.classification)' before reuse."
            evidence_level = 'pattern'
        }
    }
    foreach ($pitfall in @($(if ($null -ne $ObservedPitfallEvents -and (Test-VibeObjectHasProperty -InputObject $ObservedPitfallEvents -PropertyName 'events')) { $ObservedPitfallEvents.events } else { @() }))) {
        $notes += [pscustomobject]@{
            note_id = 'remediation-pitfall-' + [string]$pitfall.pitfall_type
            remediation_type = 'pitfall'
            suggested_remediation = "Add review handling for pitfall '$([string]$pitfall.pitfall_type)'."
            evidence_level = 'pitfall'
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{ note_count = @($notes).Count }
        notes = @($notes)
    }
}

function New-VibeCandidateCompositeSkillDraftArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$AtomicSkillCallChain,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents
    )

    $events = @($(if ($null -ne $AtomicSkillCallChain -and (Test-VibeObjectHasProperty -InputObject $AtomicSkillCallChain -PropertyName 'events')) { $AtomicSkillCallChain.events } else { @() }))
    $approvedSpecialists = @(
        $events |
        Where-Object { [string]$_.event_type -eq 'skill_dispatch_approved' -and [string]$_.skill_id -ne 'vibe' } |
        ForEach-Object { [string]$_.skill_id } |
        Select-Object -Unique
    )
    $drafts = @()
    if (@($approvedSpecialists).Count -gt 0) {
        $degradedSkillIds = @(
            $events |
            Where-Object { [bool]$_.degraded } |
            ForEach-Object { [string]$_.skill_id } |
            Select-Object -Unique
        )
        $pitfallTypes = @()
        if ($null -ne $ObservedPitfallEvents -and $ObservedPitfallEvents.PSObject.Properties.Name -contains 'events') {
            $pitfallTypes = @($ObservedPitfallEvents.events | ForEach-Object { [string]$_.pitfall_type } | Select-Object -Unique)
        }
        $activeFailures = @()
        if ($null -ne $ObservedFailurePatterns -and $ObservedFailurePatterns.PSObject.Properties.Name -contains 'patterns') {
            $activeFailures = @($ObservedFailurePatterns.patterns | Where-Object { $_.active } | ForEach-Object { [string]$_.classification } | Select-Object -Unique)
        }
        $drafts += [pscustomobject]@{
            draft_id = 'draft-review-bundle'
            title = 'observed specialist composition surface'
            trigger_shape = 'observed specialist co-dispatch under governed review / verification'
            governor_skill = 'vibe'
            component_skills = @($approvedSpecialists)
            entry_conditions = @(
                'A governed run surfaced one or more approved specialist dispatches.',
                'This draft records an observed specialist combination for review-only follow-up.'
            )
            known_risks = @($degradedSkillIds + $pitfallTypes + $activeFailures | Select-Object -Unique)
            promotion_readiness = if (@($degradedSkillIds).Count -gt 0) { 'needs-shadow-review' } else { 'review-signal' }
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{ draft_count = @($drafts).Count }
        drafts = @($drafts)
    }
}

function New-VibeThresholdPolicySuggestionArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$RuntimeInputPacket,
        [AllowNull()] [object]$RuntimeSummary
    )

    $pitfallEvents = @($(if ($null -ne $ObservedPitfallEvents -and (Test-VibeObjectHasProperty -InputObject $ObservedPitfallEvents -PropertyName 'events')) { $ObservedPitfallEvents.events } else { @() }))
    $suggestions = @()
    if (@($pitfallEvents | Where-Object { [string]$_.pitfall_type -eq 'confirm_required_route' }).Count -gt 0) {
        $suggestions += [pscustomobject]@{
            suggestion_id = 'policy-confirm-review'
            policy_area = 'routing_confirm'
            current_signal = 'confirm_required_route'
            suggested_change = 'Keep confirm-related routing under manual review until repeated sessions stop hitting confirm_required.'
            expected_benefit = 'Reduce silent escalation of ambiguous routes.'
            risk_if_applied = 'May increase manual review frequency.'
            review_path = 'shadow-review'
        }
    }
    $activeDeliveryFailure = @($(if ($null -ne $ObservedFailurePatterns -and (Test-VibeObjectHasProperty -InputObject $ObservedFailurePatterns -PropertyName 'patterns')) { $ObservedFailurePatterns.patterns } else { @() }) | Where-Object { [string]$_.classification -eq 'delivery_gate_failed' -and [bool]$_.active }).Count -gt 0
    if ($activeDeliveryFailure) {
        $suggestions += [pscustomobject]@{
            suggestion_id = 'policy-delivery-gate'
            policy_area = 'delivery_acceptance'
            current_signal = 'delivery_gate_failed'
            suggested_change = 'Treat delivery gate failures as a hard review stop for similar runs.'
            expected_benefit = 'Prevent premature completion claims.'
            risk_if_applied = 'Can slow down runs that are near-complete but still noisy.'
            review_path = 'board-review'
        }
    }
    $routeSnapshot = Get-VibeObservedMemberValue -InputObject $RuntimeInputPacket -Name 'route_snapshot'
    if ([bool](Get-VibeObservedMemberValue -InputObject $routeSnapshot -Name 'fallback_active')) {
        $suggestions += [pscustomobject]@{
            suggestion_id = 'policy-fallback-shadow'
            policy_area = 'routing_fallback'
            current_signal = 'fallback_active_route'
            suggested_change = 'Shadow-review fallback-active routes before loosening fallback thresholds.'
            expected_benefit = 'Catch low-confidence task routing drift earlier.'
            risk_if_applied = 'Adds temporary review overhead.'
            review_path = 'shadow-review'
        }
    }

    return [pscustomobject]@{
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{ suggestion_count = @($suggestions).Count }
        suggestions = @($suggestions)
    }
}

function New-VibeProposalLayerArtifact {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ObservedFailurePatterns,
        [AllowNull()] [object]$ObservedPitfallEvents,
        [AllowNull()] [object]$AtomicSkillCallChain,
        [AllowNull()] [object]$WarningCardsArtifact,
        [AllowNull()] [object]$PreflightChecklistArtifact,
        [AllowEmptyString()] [string]$WarningCardsPath = '',
        [AllowEmptyString()] [string]$PreflightChecklistPath = '',
        [AllowEmptyString()] [string]$RemediationNotesPath = '',
        [AllowEmptyString()] [string]$CandidateCompositeSkillDraftPath = '',
        [AllowEmptyString()] [string]$ThresholdPolicySuggestionPath = ''
    )

    $cards = @($(if ($null -ne $WarningCardsArtifact -and (Test-VibeObjectHasProperty -InputObject $WarningCardsArtifact -PropertyName 'cards')) { $WarningCardsArtifact.cards } else { @() }))
    $checks = @($(if ($null -ne $PreflightChecklistArtifact -and (Test-VibeObjectHasProperty -InputObject $PreflightChecklistArtifact -PropertyName 'checks')) { $PreflightChecklistArtifact.checks } else { @() }))
    return [pscustomobject]@{
        schema_version = 1
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        summary = [pscustomobject]@{
            evidence_level = Get-VibeProposalEvidenceLevel -ObservedFailurePatterns $ObservedFailurePatterns -ObservedPitfallEvents $ObservedPitfallEvents -AtomicSkillCallChain $AtomicSkillCallChain
            warning_card_count = @($cards).Count
            preflight_check_count = @($checks).Count
        }
        artifacts = [pscustomobject]@{
            warning_cards = if ([string]::IsNullOrWhiteSpace($WarningCardsPath)) { $null } else { $WarningCardsPath }
            preflight_checklist = if ([string]::IsNullOrWhiteSpace($PreflightChecklistPath)) { $null } else { $PreflightChecklistPath }
            remediation_notes = if ([string]::IsNullOrWhiteSpace($RemediationNotesPath)) { $null } else { $RemediationNotesPath }
            candidate_composite_skill_draft = if ([string]::IsNullOrWhiteSpace($CandidateCompositeSkillDraftPath)) { $null } else { $CandidateCompositeSkillDraftPath }
            threshold_policy_suggestion = if ([string]::IsNullOrWhiteSpace($ThresholdPolicySuggestionPath)) { $null } else { $ThresholdPolicySuggestionPath }
        }
    }
}

function New-VibeProposalLayerMarkdownLines {
    param(
        [Parameter(Mandatory)] [object]$ProposalLayerArtifact,
        [AllowNull()] [object]$WarningCardsArtifact = $null,
        [AllowNull()] [object]$PreflightChecklistArtifact = $null
    )

    $lines = @(
        '# Proposal Layer',
        '',
        ('- mode: `{0}`' -f [string]$ProposalLayerArtifact.mode),
        ('- review_status: `{0}`' -f [string]$ProposalLayerArtifact.review_status),
        ('- evidence_level: `{0}`' -f [string]$ProposalLayerArtifact.summary.evidence_level),
        ''
    )
    if ($WarningCardsArtifact) {
        $lines += '## Warning Cards'
        foreach ($card in @($WarningCardsArtifact.cards)) {
            $lines += ('- {0}: {1}' -f [string]$card.card_id, [string]$card.summary)
        }
        $lines += ''
    }
    if ($PreflightChecklistArtifact) {
        $lines += '## Preflight Checklist'
        foreach ($check in @($PreflightChecklistArtifact.checks)) {
            $lines += ('- {0}: {1}' -f [string]$check.check_id, [string]$check.why)
        }
        $lines += ''
    }
    return @($lines)
}

function New-VibeApplicationReadinessReport {
    param(
        [Parameter(Mandatory)] [string]$RunId,
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$ProposalLayerArtifact,
        [AllowNull()] [object]$WarningCardsArtifact,
        [AllowNull()] [object]$PreflightChecklistArtifact,
        [AllowNull()] [object]$RemediationNotesArtifact,
        [AllowNull()] [object]$CandidateCompositeSkillDraftArtifact,
        [AllowNull()] [object]$ThresholdPolicySuggestionArtifact,
        [AllowEmptyString()] [string]$ProposalLayerPath = '',
        [AllowEmptyString()] [string]$WarningCardsPath = '',
        [AllowEmptyString()] [string]$PreflightChecklistPath = '',
        [AllowEmptyString()] [string]$RemediationNotesPath = '',
        [AllowEmptyString()] [string]$CandidateCompositeSkillDraftPath = '',
        [AllowEmptyString()] [string]$ThresholdPolicySuggestionPath = ''
    )

    $laneACandidates = @()
    foreach ($card in @($(if ($null -ne $WarningCardsArtifact -and (Test-VibeObjectHasProperty -InputObject $WarningCardsArtifact -PropertyName 'cards')) { $WarningCardsArtifact.cards } else { @() }))) {
        $evidenceRefs = @($(if ($card.PSObject.Properties.Name -contains 'evidence_refs') { $card.evidence_refs } else { @() }))
        $laneACandidates += [pscustomobject]@{
            candidate_id = 'lane-a-warning-' + [string]$card.card_id
            proposal_type = 'warning_card'
            source_ref = if ([string]::IsNullOrWhiteSpace($WarningCardsPath)) { [string]$card.card_id } else { $WarningCardsPath + '#' + [string]$card.card_id }
            recommended_surface = 'warning_surface'
            activation_mode = 'advisory'
            target_stage = 'session_start'
            readiness = if (@($evidenceRefs).Count -eq 0) { 'needs_more_review' } else { 'ready_for_review' }
            blocked_by = if (@($evidenceRefs).Count -eq 0) { @('missing_evidence_refs') } else { @() }
            required_manual_actions = @('Confirm the warning text and trigger before enabling a shared warning surface.')
            evidence_refs = @($evidenceRefs)
            boundary_impact = 'none'
            coupling_risk = 'low'
            regression_risk = 'low'
        }
    }
    foreach ($check in @($(if ($null -ne $PreflightChecklistArtifact -and (Test-VibeObjectHasProperty -InputObject $PreflightChecklistArtifact -PropertyName 'checks')) { $PreflightChecklistArtifact.checks } else { @() }))) {
        $sourceSignal = [string](Get-VibeObservedMemberValue -InputObject $check -Name 'source_signal')
        $laneACandidates += [pscustomobject]@{
            candidate_id = 'lane-a-preflight-' + [string]$check.check_id
            proposal_type = 'preflight_check'
            source_ref = if ([string]::IsNullOrWhiteSpace($PreflightChecklistPath)) { [string]$check.check_id } else { $PreflightChecklistPath + '#' + [string]$check.check_id }
            recommended_surface = 'preflight_rule_set'
            activation_mode = if ([bool](Get-VibeObservedMemberValue -InputObject $check -Name 'required_before_next_run')) { 'guarded' } else { 'advisory' }
            target_stage = 'before_execute'
            readiness = if ([string]::IsNullOrWhiteSpace($sourceSignal)) { 'needs_more_review' } else { 'ready_for_review' }
            blocked_by = if ([string]::IsNullOrWhiteSpace($sourceSignal)) { @('missing_source_signal') } else { @() }
            required_manual_actions = @('Classify the check as soft-check or hard-check before reuse.')
            evidence_refs = @($sourceSignal)
            boundary_impact = 'none'
            coupling_risk = 'low'
            regression_risk = if ([bool](Get-VibeObservedMemberValue -InputObject $check -Name 'required_before_next_run')) { 'medium' } else { 'low' }
        }
    }
    foreach ($note in @($(if ($null -ne $RemediationNotesArtifact -and (Test-VibeObjectHasProperty -InputObject $RemediationNotesArtifact -PropertyName 'notes')) { $RemediationNotesArtifact.notes } else { @() }))) {
        $laneACandidates += [pscustomobject]@{
            candidate_id = 'lane-a-remediation-' + [string]$note.note_id
            proposal_type = 'remediation_note'
            source_ref = if ([string]::IsNullOrWhiteSpace($RemediationNotesPath)) { [string]$note.note_id } else { $RemediationNotesPath + '#' + [string]$note.note_id }
            recommended_surface = 'remediation_playbook'
            activation_mode = 'review_assist'
            target_stage = 'post_cleanup_review'
            readiness = 'ready_for_review'
            blocked_by = @()
            required_manual_actions = @('Confirm the remediation text before promoting it into a reusable playbook entry.')
            evidence_levels = @([string]$note.evidence_level)
            boundary_impact = 'none'
            coupling_risk = 'low'
            regression_risk = 'low'
        }
    }

    $laneBCandidates = @()
    foreach ($draft in @($(if ($null -ne $CandidateCompositeSkillDraftArtifact -and (Test-VibeObjectHasProperty -InputObject $CandidateCompositeSkillDraftArtifact -PropertyName 'drafts')) { $CandidateCompositeSkillDraftArtifact.drafts } else { @() }))) {
        $blockedBy = @()
        $componentSkills = @($(if ($draft.PSObject.Properties.Name -contains 'component_skills') { $draft.component_skills } else { @() }))
        if (@($componentSkills).Count -eq 0) {
            $blockedBy += 'missing_component_skills'
        }
        $promotionReadiness = if ($draft.PSObject.Properties.Name -contains 'promotion_readiness') { [string]$draft.promotion_readiness } else { '' }
        $laneBCandidates += [pscustomobject]@{
            candidate_id = 'lane-b-draft-' + [string]$draft.draft_id
            proposal_type = 'composite_skill_draft'
            source_ref = if ([string]::IsNullOrWhiteSpace($CandidateCompositeSkillDraftPath)) { [string]$draft.draft_id } else { $CandidateCompositeSkillDraftPath + '#' + [string]$draft.draft_id }
            recommended_surface = 'review_signal_surface'
            governance_path = 'lifecycle.review_only'
            target_scope = 'observed_specialist_combination'
            manual_review_required = $true
            shadow_required = [bool]($promotionReadiness -eq 'needs-shadow-review')
            shadow_plan_status = if (@($blockedBy).Count -gt 0) { 'missing_prerequisites' } elseif ($promotionReadiness -eq 'needs-shadow-review') { 'review_before_shadow' } else { 'review_only' }
            board_review_required = $false
            replay_evidence_refs = @($ProposalLayerPath, $CandidateCompositeSkillDraftPath)
            rollback_plan_required = $true
            readiness = if (@($blockedBy).Count -gt 0) { 'blocked' } elseif ($promotionReadiness -eq 'needs-shadow-review') { 'ready_for_shadow_review' } else { 'ready_for_review' }
            blocked_by = @($blockedBy)
            required_manual_actions = @(
                'Confirm whether this is only an observed specialist combination or a stable reusable pattern.',
                'Do not treat this surface as a promotion-ready composite skill proposal without extra evidence.'
            )
            boundary_impact = 'module_boundary_review'
            coupling_risk = if (@($componentSkills).Count -gt 2) { 'medium' } else { 'low' }
            regression_risk = if ($promotionReadiness -eq 'needs-shadow-review') { 'medium' } else { 'low' }
        }
    }
    foreach ($suggestion in @($(if ($null -ne $ThresholdPolicySuggestionArtifact -and (Test-VibeObjectHasProperty -InputObject $ThresholdPolicySuggestionArtifact -PropertyName 'suggestions')) { $ThresholdPolicySuggestionArtifact.suggestions } else { @() }))) {
        $reviewPath = [string](Get-VibeObservedMemberValue -InputObject $suggestion -Name 'review_path')
        $policyArea = [string](Get-VibeObservedMemberValue -InputObject $suggestion -Name 'policy_area')
        $boundaryImpact = switch ($policyArea) {
            'routing_confirm' { 'routing_policy' }
            'routing_fallback' { 'routing_policy' }
            'delivery_acceptance' { 'delivery_policy' }
            default { 'policy_review' }
        }
        $laneBCandidates += [pscustomobject]@{
            candidate_id = 'lane-b-policy-' + [string]$suggestion.suggestion_id
            proposal_type = 'threshold_policy_suggestion'
            source_ref = if ([string]::IsNullOrWhiteSpace($ThresholdPolicySuggestionPath)) { [string]$suggestion.suggestion_id } else { $ThresholdPolicySuggestionPath + '#' + [string]$suggestion.suggestion_id }
            recommended_surface = 'policy_shadow_candidate'
            governance_path = if ($boundaryImpact -eq 'delivery_policy') { 'policy.board_review' } else { 'policy.shadow' }
            target_scope = if ([string]::IsNullOrWhiteSpace($policyArea)) { 'policy_scope_unknown' } else { $policyArea }
            manual_review_required = $true
            shadow_required = $true
            shadow_plan_status = if ([string]::IsNullOrWhiteSpace($reviewPath)) { 'missing_prerequisites' } elseif ($boundaryImpact -eq 'delivery_policy') { 'needs_board_bundle' } else { 'ready_to_prepare' }
            board_review_required = [bool]($boundaryImpact -eq 'delivery_policy')
            replay_evidence_refs = @($ProposalLayerPath, $ThresholdPolicySuggestionPath)
            rollback_plan_required = $true
            readiness = if ([string]::IsNullOrWhiteSpace($reviewPath)) { 'blocked' } else { 'ready_for_shadow_review' }
            blocked_by = if ([string]::IsNullOrWhiteSpace($reviewPath)) { @('missing_review_path') } else { @() }
            required_manual_actions = @('Confirm the target policy scope before any shadow rollout.', 'Prepare rollback wording before applying any threshold change.')
            boundary_impact = $boundaryImpact
            coupling_risk = if ($policyArea -like 'routing_*') { 'medium' } else { 'low' }
            regression_risk = 'medium'
        }
    }

    $readyForReviewCount = @(@($laneACandidates) + @($laneBCandidates) | Where-Object { [string]$_.readiness -eq 'ready_for_review' }).Count
    $readyForShadowReviewCount = @(@($laneACandidates) + @($laneBCandidates) | Where-Object { [string]$_.readiness -eq 'ready_for_shadow_review' }).Count
    $blockedCount = @($laneACandidates + $laneBCandidates | Where-Object { [string]$_.readiness -eq 'blocked' }).Count
    $highRiskFindings = @($laneBCandidates | Where-Object { [string]$_.regression_risk -eq 'medium' -or [string]$_.coupling_risk -eq 'medium' } | ForEach-Object { [string]$_.candidate_id } | Select-Object -Unique)

    return [pscustomobject]@{
        gate_version = 1
        run_id = $RunId
        generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        session_root = $SessionRoot
        mode = 'report-only'
        review_status = 'pending-review'
        input_artifacts = [pscustomobject]@{
            proposal_layer = if ([string]::IsNullOrWhiteSpace($ProposalLayerPath)) { $null } else { $ProposalLayerPath }
            warning_cards = if ([string]::IsNullOrWhiteSpace($WarningCardsPath)) { $null } else { $WarningCardsPath }
            preflight_checklist = if ([string]::IsNullOrWhiteSpace($PreflightChecklistPath)) { $null } else { $PreflightChecklistPath }
            remediation_notes = if ([string]::IsNullOrWhiteSpace($RemediationNotesPath)) { $null } else { $RemediationNotesPath }
            candidate_composite_skill_draft = if ([string]::IsNullOrWhiteSpace($CandidateCompositeSkillDraftPath)) { $null } else { $CandidateCompositeSkillDraftPath }
            threshold_policy_suggestion = if ([string]::IsNullOrWhiteSpace($ThresholdPolicySuggestionPath)) { $null } else { $ThresholdPolicySuggestionPath }
        }
        lane_a_candidates = @($laneACandidates)
        lane_b_candidates = @($laneBCandidates)
        summary = [pscustomobject]@{
            lane_a_candidate_count = @($laneACandidates).Count
            lane_b_candidate_count = @($laneBCandidates).Count
            ready_for_review_count = $readyForReviewCount
            ready_for_shadow_review_count = $readyForShadowReviewCount
            blocked_count = $blockedCount
            highest_risk_findings = @($highRiskFindings)
        }
    }
}

function New-VibeApplicationReadinessMarkdownLines {
    param(
        [Parameter(Mandatory)] [object]$ApplicationReadinessReport
    )

    function Format-VibeMarkdownCell {
        param([AllowNull()] [object]$Value)

        if ($null -eq $Value) {
            return ''
        }
        if ($Value -is [array]) {
            $text = (@($Value) | ForEach-Object { [string]$_ }) -join ', '
        } else {
            $text = [string]$Value
        }
        return ($text -replace '\|', '\|' -replace "`r?`n", ' ')
    }

    function Join-VibeMarkdownListValue {
        param([AllowNull()] [object]$Value)

        if ($null -eq $Value) {
            return ''
        }
        $items = @($Value | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if (@($items).Count -eq 0) {
            return ''
        }
        return ($items -join ', ')
    }

    function Get-VibeReadableProposalType {
        param([AllowEmptyString()] [string]$ProposalType)

        switch ($ProposalType) {
            'warning_card' { return 'Warning card' }
            'preflight_check' { return 'Preflight check' }
            'remediation_note' { return 'Remediation note' }
            'composite_skill_draft' { return 'Observed composition draft' }
            'threshold_policy_suggestion' { return 'Threshold or policy suggestion' }
            default {
                if ([string]::IsNullOrWhiteSpace($ProposalType)) { return 'Unknown type' }
                return $ProposalType
            }
        }
    }

    function Get-VibeReadableSurface {
        param([AllowEmptyString()] [string]$Surface)

        switch ($Surface) {
            'warning_surface' { return 'Show as a warning before the next run' }
            'preflight_rule_set' { return 'Add as a preflight check before execution' }
            'remediation_playbook' { return 'Capture as a review or cleanup playbook note' }
            'shadow_candidate' { return 'Enter shadow review, not direct promotion' }
            'review_signal_surface' { return 'Expose first as a review-only observed combination' }
            'policy_shadow_candidate' { return 'Enter policy shadow or board review, not direct policy change' }
            default {
                if ([string]::IsNullOrWhiteSpace($Surface)) { return 'No surface assigned' }
                return $Surface
            }
        }
    }

    function Get-VibeReadableReadiness {
        param([AllowEmptyString()] [string]$Readiness)

        switch ($Readiness) {
            'ready_for_review' { return 'Ready for manual review' }
            'ready_for_shadow_review' { return 'Ready to prepare shadow review' }
            'needs_more_review' { return 'Needs more review' }
            'blocked' { return 'Blocked' }
            default {
                if ([string]::IsNullOrWhiteSpace($Readiness)) { return 'Unspecified' }
                return $Readiness
            }
        }
    }

    function Get-VibeReadableRisk {
        param(
            [AllowEmptyString()] [string]$BoundaryImpact,
            [AllowEmptyString()] [string]$CouplingRisk,
            [AllowEmptyString()] [string]$RegressionRisk
        )

        $parts = @()
        switch ($BoundaryImpact) {
            'none' { $parts += 'No module boundary impact' }
            'module_boundary_review' { $parts += 'Needs module-boundary review' }
            'routing_policy' { $parts += 'Touches routing policy' }
            'delivery_policy' { $parts += 'Touches delivery policy' }
            'policy_review' { $parts += 'Needs policy review' }
            default {
                if (-not [string]::IsNullOrWhiteSpace($BoundaryImpact)) { $parts += ('Boundary impact=' + $BoundaryImpact) }
            }
        }

        switch ($CouplingRisk) {
            'low' { $parts += 'Low coupling risk' }
            'medium' { $parts += 'Medium coupling risk' }
            'high' { $parts += 'High coupling risk' }
            default {
                if (-not [string]::IsNullOrWhiteSpace($CouplingRisk)) { $parts += ('Coupling risk=' + $CouplingRisk) }
            }
        }

        switch ($RegressionRisk) {
            'low' { $parts += 'Low regression risk' }
            'medium' { $parts += 'Medium regression risk' }
            'high' { $parts += 'High regression risk' }
            default {
                if (-not [string]::IsNullOrWhiteSpace($RegressionRisk)) { $parts += ('Regression risk=' + $RegressionRisk) }
            }
        }

        return ($parts -join '; ')
    }

    function Get-VibeReadableCandidateTitle {
        param([object]$Candidate)

        $candidateId = [string]$Candidate.candidate_id
        $proposalType = [string]$Candidate.proposal_type

        $name = $candidateId
        foreach ($prefix in @(
            'lane-a-warning-warning-pitfall-',
            'lane-a-warning-warning-',
            'lane-a-preflight-check-pitfall-',
            'lane-a-preflight-check-',
            'lane-a-remediation-remediation-skill-',
            'lane-a-remediation-remediation-',
            'lane-b-draft-',
            'lane-b-policy-policy-'
        )) {
            if ($name.StartsWith($prefix)) {
                $name = $name.Substring($prefix.Length)
                break
            }
        }

        if ($name -eq 'delivery-gate' -and $proposalType -eq 'threshold_policy_suggestion') {
            $readableName = 'Delivery acceptance policy suggestion'
            return ((Get-VibeReadableProposalType -ProposalType $proposalType) + ': ' + $readableName)
        }

        $readableName = switch ($name) {
            'partial_completion' { 'Run did not complete cleanly' }
            'delivery_gate_failed' { 'Delivery acceptance failed' }
            'delivery-acceptance' { 'Delivery acceptance failure' }
            'delivery-gate' { 'Delivery gate should remain under review' }
            'code-reviewer' { 'code-reviewer skill degraded' }
            'peer-review' { 'peer-review skill degraded' }
            'draft-review-bundle' { 'Observed composition draft' }
            default { $name -replace '_', ' ' }
        }

        return ((Get-VibeReadableProposalType -ProposalType $proposalType) + ': ' + $readableName)
    }

    function Get-VibeReadableNextStep {
        param([object]$Candidate)

        $proposalType = [string]$Candidate.proposal_type
        $surface = [string]$Candidate.recommended_surface

        switch ($proposalType) {
            'warning_card' { return 'Keep as a warning only; do not auto-block execution.' }
            'preflight_check' { return 'Decide manually whether this should be a soft check or a hard check.' }
            'remediation_note' { return 'Confirm the wording before promoting it into a reusable remediation note.' }
            'composite_skill_draft' { return 'First confirm whether this is only an observed combination before deciding on any shadow review.' }
            'threshold_policy_suggestion' {
                if ([string]$Candidate.governance_path -eq 'policy.board_review') {
                    return 'Send to board review and add rollback wording before considering any policy change.'
                }
                return 'Enter policy shadow first; do not change live policy directly.'
            }
            default { return (Get-VibeReadableSurface -Surface $surface) }
        }
    }

    function Get-VibeReadableManualActions {
        param([object]$Candidate)

        switch ([string]$Candidate.proposal_type) {
            'warning_card' { return 'Confirm the warning text and trigger conditions before adding it to a shared warning surface.' }
            'preflight_check' { return 'Decide whether the check should remain soft or become hard.' }
            'remediation_note' { return 'Confirm the remediation wording before turning it into a reusable playbook item.' }
            'composite_skill_draft' { return 'Confirm there is a stable reusable pattern; do not treat it as promotion-ready without extra evidence.' }
            'threshold_policy_suggestion' { return 'Confirm target policy scope, add rollback wording, and only then consider shadow or board review.' }
            default {
                $manualActions = Join-VibeMarkdownListValue -Value $Candidate.required_manual_actions
                if ([string]::IsNullOrWhiteSpace($manualActions)) {
                    return 'No additional manual actions.'
                }
                return $manualActions
            }
        }
    }

    function Add-VibeReadableCandidateRows {
        param(
            [AllowNull()] [object[]]$Candidates,
            [string[]]$Lines
        )

        foreach ($candidate in @($Candidates)) {
            $title = Get-VibeReadableCandidateTitle -Candidate $candidate
            $surface = Get-VibeReadableSurface -Surface ([string]$candidate.recommended_surface)
            $readiness = Get-VibeReadableReadiness -Readiness ([string]$candidate.readiness)
            $risk = Get-VibeReadableRisk -BoundaryImpact ([string]$candidate.boundary_impact) -CouplingRisk ([string]$candidate.coupling_risk) -RegressionRisk ([string]$candidate.regression_risk)
            $nextStep = Get-VibeReadableNextStep -Candidate $candidate
            $blockedBy = Join-VibeMarkdownListValue -Value $candidate.blocked_by
            if ([string]::IsNullOrWhiteSpace($blockedBy)) {
                $blockedBy = 'None'
            }

            $Lines += ('| {0} | {1} | {2} | {3} | {4} | {5} |' -f `
                (Format-VibeMarkdownCell $title),
                (Format-VibeMarkdownCell $surface),
                (Format-VibeMarkdownCell $readiness),
                (Format-VibeMarkdownCell $risk),
                (Format-VibeMarkdownCell $nextStep),
                (Format-VibeMarkdownCell $blockedBy))
        }

        return $Lines
    }

    $laneA = @($ApplicationReadinessReport.lane_a_candidates)
    $laneB = @($ApplicationReadinessReport.lane_b_candidates)

    $highestRiskFindingNames = @()
    $highestRiskFindingIds = @($ApplicationReadinessReport.summary.highest_risk_findings | ForEach-Object { [string]$_ })
    foreach ($findingId in @($highestRiskFindingIds)) {
        $matchedCandidate = @($laneA + $laneB | Where-Object { [string]$_.candidate_id -eq $findingId } | Select-Object -First 1)
        if (@($matchedCandidate).Count -gt 0) {
            $highestRiskFindingNames += Get-VibeReadableCandidateTitle -Candidate $matchedCandidate[0]
        } else {
            $highestRiskFindingNames += $findingId
        }
    }

    $lines = @(
        '# Application Readiness Report',
        '',
        '## Summary',
        '',
        ('- Run: `' + [string]$ApplicationReadinessReport.run_id + '`'),
        ('- Mode: `' + [string]$ApplicationReadinessReport.mode + '`; review status: `' + [string]$ApplicationReadinessReport.review_status + '`'),
        ('- Lane A low-risk reuse candidates: `' + [int]$ApplicationReadinessReport.summary.lane_a_candidate_count + '`'),
        ('- Lane B governance review candidates: `' + [int]$ApplicationReadinessReport.summary.lane_b_candidate_count + '`'),
        ('- Ready for manual review: `' + [int]$ApplicationReadinessReport.summary.ready_for_review_count + '`'),
        ('- Ready for shadow review: `' + [int]$ApplicationReadinessReport.summary.ready_for_shadow_review_count + '`'),
        ('- Blocked: `' + [int]$ApplicationReadinessReport.summary.blocked_count + '`')
    )

    $highestRiskFindings = Join-VibeMarkdownListValue -Value $highestRiskFindingNames
    if (-not [string]::IsNullOrWhiteSpace($highestRiskFindings)) {
        $lines += ('- Highest risk findings: ' + $highestRiskFindings)
    }

    if (@($laneA).Count -gt 0) {
        $lines += @(
            '',
            '## Lane A: Low-Risk Reuse Candidates',
            '',
            'These candidates should remain warnings, preflight checks, or remediation notes. They should not directly change default routing or global skill weights.',
            '',
            '| Candidate | Suggested surface | Readiness | Risk | Suggested next step | Blockers |',
            '| --- | --- | --- | --- | --- | --- |'
        )
        $lines = Add-VibeReadableCandidateRows -Candidates $laneA -Lines $lines

        $lines += @('', '### Manual Actions', '')
        foreach ($candidate in @($laneA)) {
            $manualActions = Get-VibeReadableManualActions -Candidate $candidate
            if (-not [string]::IsNullOrWhiteSpace($manualActions)) {
                $lines += ('- ' + (Format-VibeMarkdownCell (Get-VibeReadableCandidateTitle -Candidate $candidate)) + ': ' + (Format-VibeMarkdownCell $manualActions))
            }
        }
    }

    if (@($laneB).Count -gt 0) {
        $lines += @(
            '',
            '## Lane B: Governance Review Candidates',
            '',
            'These candidates all require manual review. Some are only observed combination surfaces, while others are closer to governance-change discussions, so none of them should be applied directly to live policy or formal skill lifecycle state.',
            '',
            '| Candidate | Suggested surface | Readiness | Risk | Suggested next step | Blockers |',
            '| --- | --- | --- | --- | --- | --- |'
        )
        $lines = Add-VibeReadableCandidateRows -Candidates $laneB -Lines $lines

        $lines += @('', '### Manual Actions', '')
        foreach ($candidate in @($laneB)) {
            $manualActions = Get-VibeReadableManualActions -Candidate $candidate
            if (-not [string]::IsNullOrWhiteSpace($manualActions)) {
                $lines += ('- ' + (Format-VibeMarkdownCell (Get-VibeReadableCandidateTitle -Candidate $candidate)) + ': ' + (Format-VibeMarkdownCell $manualActions))
            }
        }
    }

    $lines += @(
        '',
        '## Traceability',
        '',
        'Machine-readable fields remain in `application-readiness-report.json`. This Markdown is only a human review view and not the canonical truth surface.'
    )

    return @($lines)
}

function Get-VibeStageLineageExecutedStageOrder {
    param(
        [AllowNull()] [object]$StageLineage = $null
    )

    if ($null -eq $StageLineage) {
        return @()
    }

    $lineageSource = if ((Test-VibeObjectHasProperty -InputObject $StageLineage -PropertyName 'lineage') -and $null -ne $StageLineage.lineage) {
        $StageLineage.lineage
    } else {
        $StageLineage
    }

    $stageEntries = @()
    if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stages') -and $null -ne $lineageSource.stages) {
        $stageEntries = @($lineageSource.stages)
    } elseif ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'entries') -and $null -ne $lineageSource.entries) {
        $stageEntries = @($lineageSource.entries)
    }

    $stageNames = New-Object System.Collections.ArrayList
    foreach ($entry in @($stageEntries)) {
        if ($null -eq $entry) {
            continue
        }
        $stageName = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'stage_name') -and -not [string]::IsNullOrWhiteSpace([string]$entry.stage_name)) {
            [string]$entry.stage_name
        } elseif ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$entry.stage)) {
            [string]$entry.stage
        } else {
            ''
        }
        if (-not [string]::IsNullOrWhiteSpace($stageName)) {
            [void]$stageNames.Add($stageName)
        }
    }

    if ($stageNames.Count -eq 0) {
        $topLevelStageName = if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stage_name') -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.stage_name)) {
            [string]$lineageSource.stage_name
        } elseif ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.stage)) {
            [string]$lineageSource.stage
        } else {
            ''
        }
        if (-not [string]::IsNullOrWhiteSpace($topLevelStageName)) {
            [void]$stageNames.Add($topLevelStageName)
        }
    }

    return [string[]]$stageNames.ToArray()
}

function Get-VibeStageLineageTerminalStage {
    param(
        [AllowNull()] [object]$StageLineage = $null
    )

    if ($null -eq $StageLineage) {
        return $null
    }

    $lineageSource = if ((Test-VibeObjectHasProperty -InputObject $StageLineage -PropertyName 'lineage') -and $null -ne $StageLineage.lineage) {
        $StageLineage.lineage
    } else {
        $StageLineage
    }

    foreach ($propertyName in @('last_stage_name', 'last_stage')) {
        if ((Test-VibeObjectHasProperty -InputObject $lineageSource -PropertyName $propertyName) -and -not [string]::IsNullOrWhiteSpace([string]$lineageSource.$propertyName)) {
            return [string]$lineageSource.$propertyName
        }
    }

    $executedStageOrder = @(Get-VibeStageLineageExecutedStageOrder -StageLineage $lineageSource)
    if ($executedStageOrder.Count -gt 0) {
        return [string]$executedStageOrder[$executedStageOrder.Count - 1]
    }

    return $null
}

function Get-VibeInteractiveSpecialistDisclosurePolicy {
    param(
        [AllowNull()] [object]$RuntimeInputPacketPolicy
    )

    $policy = $null
    if ($null -ne $RuntimeInputPacketPolicy -and (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacketPolicy -PropertyName 'interactive_specialist_disclosure')) {
        $policy = $RuntimeInputPacketPolicy.interactive_specialist_disclosure
    }

    return [pscustomobject]@{
        enabled = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'enabled')) { [bool]$policy.enabled } else { $false }
        stage = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$policy.stage)) { [string]$policy.stage } else { 'plan_execute' }
        mode = 'approved_dispatch_pre_execution_unified_once'
        timing = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'timing') -and -not [string]::IsNullOrWhiteSpace([string]$policy.timing)) { [string]$policy.timing } else { 'before_execution' }
        scope = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'scope') -and -not [string]::IsNullOrWhiteSpace([string]$policy.scope)) { [string]$policy.scope } else { 'approved_dispatch_only' }
        aggregation = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'aggregation') -and -not [string]::IsNullOrWhiteSpace([string]$policy.aggregation)) { [string]$policy.aggregation } else { 'unified_once' }
        path_source = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'path_source') -and -not [string]::IsNullOrWhiteSpace([string]$policy.path_source)) { [string]$policy.path_source } else { 'native_skill_entrypoint' }
        require_entrypoint_path = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'require_entrypoint_path')) { [bool]$policy.require_entrypoint_path } else { $true }
        include_description = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'include_description')) { [bool]$policy.include_description } else { $true }
        header = if ($null -ne $policy -and (Test-VibeObjectHasProperty -InputObject $policy -PropertyName 'header') -and -not [string]::IsNullOrWhiteSpace([string]$policy.header)) { [string]$policy.header } else { 'Pre-dispatch specialist disclosure:' }
    }
}

function New-VibeSpecialistUserDisclosureProjection {
    param(
        [AllowEmptyCollection()] [AllowNull()] [object[]]$ApprovedDispatch = @(),
        [AllowNull()] [object]$Policy = $null
    )

    $resolvedPolicy = if ($null -ne $Policy) { $Policy } else { Get-VibeInteractiveSpecialistDisclosurePolicy }
    if (-not [bool]$resolvedPolicy.enabled) {
        return $null
    }

    $routedSkills = New-Object System.Collections.Generic.List[object]
    $seenSkillIds = @{}
    foreach ($dispatch in @($ApprovedDispatch)) {
        if ($null -eq $dispatch) {
            continue
        }

        $skillId = [string]$dispatch.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId) -or $seenSkillIds.ContainsKey($skillId)) {
            continue
        }

        $entrypointRaw = if (Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'native_skill_entrypoint') { [string]$dispatch.native_skill_entrypoint } else { '' }
        $entrypoint = $null
        $entrypointMissing = $false
        $entrypointPathInvalid = $false
        $entrypointPathState = 'resolved'
        if ([string]::IsNullOrWhiteSpace($entrypointRaw)) {
            $entrypointMissing = $true
            $entrypointPathState = 'missing'
        } elseif (-not [System.IO.Path]::IsPathRooted($entrypointRaw)) {
            $entrypointPathInvalid = $true
            $entrypointPathState = 'invalid'
        } else {
            $entrypoint = [System.IO.Path]::GetFullPath($entrypointRaw)
        }

        $seenSkillIds[$skillId] = $true
        $routedSkills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                native_skill_entrypoint = if ([string]::IsNullOrWhiteSpace($entrypoint)) { $null } else { $entrypoint }
                native_skill_entrypoint_raw = if ([string]::IsNullOrWhiteSpace($entrypointRaw)) { $null } else { $entrypointRaw }
                entrypoint_path_state = $entrypointPathState
                entrypoint_missing = $entrypointMissing
                entrypoint_path_invalid = $entrypointPathInvalid
                entrypoint_requirement_satisfied = if ([bool]$resolvedPolicy.require_entrypoint_path) { -not $entrypointMissing -and -not $entrypointPathInvalid } else { $true }
                native_skill_description = if ([bool]$resolvedPolicy.include_description -and (Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.native_skill_description)) { [string]$dispatch.native_skill_description } else { $null }
                dispatch_phase = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'dispatch_phase') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.dispatch_phase)) { [string]$dispatch.dispatch_phase } else { $null }
                write_scope = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'write_scope') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.write_scope)) { [string]$dispatch.write_scope } else { $null }
                review_mode = if ((Test-VibeObjectHasProperty -InputObject $dispatch -PropertyName 'review_mode') -and -not [string]::IsNullOrWhiteSpace([string]$dispatch.review_mode)) { [string]$dispatch.review_mode } else { $null }
            }
        )
    }

    if ($routedSkills.Count -eq 0) {
        return $null
    }

    $renderedLines = @([string]$resolvedPolicy.header)
    foreach ($entry in $routedSkills) {
        $renderedLines += ('- {0} -> {1}' -f [string]$entry.skill_id, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $entry))
    }

    return [pscustomobject]@{
        enabled = [bool]$resolvedPolicy.enabled
        stage = [string]$resolvedPolicy.stage
        mode = [string]$resolvedPolicy.mode
        timing = [string]$resolvedPolicy.timing
        scope = [string]$resolvedPolicy.scope
        aggregation = [string]$resolvedPolicy.aggregation
        path_source = [string]$resolvedPolicy.path_source
        routed_skill_count = [int]$routedSkills.Count
        routed_skills = [object[]]$routedSkills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function Get-VibeSpecialistEntrypointDisplayText {
    param(
        [AllowNull()] [object]$SkillRecord = $null
    )

    if ($null -eq $SkillRecord) {
        return 'path unavailable'
    }

    $resolvedEntrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint)
    ) {
        [string]$SkillRecord.native_skill_entrypoint
    } else {
        $null
    }
    if (-not [string]::IsNullOrWhiteSpace($resolvedEntrypoint)) {
        return $resolvedEntrypoint
    }

    $rawEntrypoint = if (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint_raw') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint_raw)
    ) {
        [string]$SkillRecord.native_skill_entrypoint_raw
    } elseif (
        (Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'native_skill_entrypoint') -and
        -not [string]::IsNullOrWhiteSpace([string]$SkillRecord.native_skill_entrypoint)
    ) {
        [string]$SkillRecord.native_skill_entrypoint
    } else {
        $null
    }

    $entrypointMissing = if ((Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'entrypoint_missing')) { [bool]$SkillRecord.entrypoint_missing } else { $false }
    $entrypointPathInvalid = if ((Test-VibeObjectHasProperty -InputObject $SkillRecord -PropertyName 'entrypoint_path_invalid')) { [bool]$SkillRecord.entrypoint_path_invalid } else { $false }
    if ($entrypointPathInvalid -and -not [string]::IsNullOrWhiteSpace($rawEntrypoint)) {
        return ('{0} (invalid entrypoint path)' -f $rawEntrypoint)
    }
    if ($entrypointMissing) {
        return 'path unavailable (missing entrypoint path)'
    }
    if (-not [string]::IsNullOrWhiteSpace($rawEntrypoint)) {
        return $rawEntrypoint
    }

    return 'path unavailable'
}

function Get-VibeSpecialistLifecycleDisclosurePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'specialist-lifecycle-disclosure.json'))
}

function New-VibeSpecialistRoutingLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket
    )

    if ($null -eq $RuntimeInputPacket -or -not (Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'specialist_recommendations')) {
        return $null
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @('Discussion-chain routed Skills:')
    foreach ($recommendation in @($RuntimeInputPacket.specialist_recommendations)) {
        if ($null -eq $recommendation) {
            continue
        }

        $skillId = [string]$recommendation.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        $entrypoint = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.native_skill_entrypoint)) { [string]$recommendation.native_skill_entrypoint } else { $null }
        if (-not [string]::IsNullOrWhiteSpace($entrypoint) -and [System.IO.Path]::IsPathRooted($entrypoint)) {
            $entrypoint = [System.IO.Path]::GetFullPath($entrypoint)
        }
        $whyNow = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'reason') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.reason)) { [string]$recommendation.reason } else { 'routed as a relevant specialist candidate for the governed discussion and planning chain' }

        $skills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                why_now = $whyNow
                source = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'source') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.source)) { [string]$recommendation.source } else { $null }
                native_skill_entrypoint = $entrypoint
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $recommendation -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$recommendation.native_skill_description)) { [string]$recommendation.native_skill_description } else { $null }
                state = 'routed'
            }
        ) | Out-Null
        $renderedLines += ('- {0}: {1} ({2})' -f $skillId, $whyNow, $(if ([string]::IsNullOrWhiteSpace($entrypoint)) { 'path unavailable' } else { $entrypoint }))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = 'discussion_routing'
        truth_layer = 'routing'
        stage = if ((Test-VibeObjectHasProperty -InputObject $RuntimeInputPacket -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$RuntimeInputPacket.stage)) { [string]$RuntimeInputPacket.stage } else { 'runtime_input_freeze' }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistConsultationLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$ConsultationReceipt
    )

    if ($null -eq $ConsultationReceipt -or -not [bool]$ConsultationReceipt.enabled) {
        return $null
    }

    $windowId = if ((Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'window_id') -and -not [string]::IsNullOrWhiteSpace([string]$ConsultationReceipt.window_id)) {
        [string]$ConsultationReceipt.window_id
    } else {
        $null
    }
    if ($windowId -notin @('discussion', 'planning')) {
        throw 'Enabled specialist consultation receipts must declare window_id as discussion or planning.'
    }
    $consultedUnits = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'consulted_units') -and
        $null -ne $ConsultationReceipt.consulted_units
    ) {
        @($ConsultationReceipt.consulted_units)
    } else {
        @()
    }
    $routedUnits = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'routed_units') -and
        $null -ne $ConsultationReceipt.routed_units
    ) {
        @($ConsultationReceipt.routed_units)
    } else {
        @()
    }
    $consultedCount = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'summary') -and
        $null -ne $ConsultationReceipt.summary -and
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt.summary -PropertyName 'consulted_unit_count')
    ) {
        [int]$ConsultationReceipt.summary.consulted_unit_count
    } else {
        @($consultedUnits).Count
    }
    $routedCount = if (
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'summary') -and
        $null -ne $ConsultationReceipt.summary -and
        (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt.summary -PropertyName 'routed_unit_count')
    ) {
        [int]$ConsultationReceipt.summary.routed_unit_count
    } else {
        @($routedUnits).Count
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @(if ($routedCount -gt 0 -and $consultedCount -eq 0) {
        ('Specialist consultation routing during {0}:' -f $windowId)
    } elseif ($consultedCount -gt 0 -and $routedCount -eq 0) {
        ('Specialist consultation during {0}:' -f $windowId)
    } else {
        ('Recorded specialist consultation chain during {0}:' -f $windowId)
    })
    foreach ($disclosure in @($ConsultationReceipt.user_disclosures)) {
        if ($null -eq $disclosure) {
            continue
        }

        $consultedUnit = $null
        foreach ($candidate in @($consultedUnits)) {
            if ($null -ne $candidate -and [string]$candidate.skill_id -eq [string]$disclosure.skill_id) {
                $consultedUnit = $candidate
                break
            }
        }
        $routedUnit = $null
        foreach ($candidate in @($routedUnits)) {
            if ($null -ne $candidate -and [string]$candidate.skill_id -eq [string]$disclosure.skill_id) {
                $routedUnit = $candidate
                break
            }
        }

        $skills.Add(
            [pscustomobject]@{
                skill_id = [string]$disclosure.skill_id
                why_now = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'why_now') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.why_now)) { [string]$disclosure.why_now } else { $null }
                native_skill_entrypoint = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.native_skill_entrypoint)) { [string]$disclosure.native_skill_entrypoint } else { $null }
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $disclosure -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$disclosure.native_skill_description)) { [string]$disclosure.native_skill_description } else { $null }
                state = if ($consultedUnit -and (Test-VibeObjectHasProperty -InputObject $consultedUnit -PropertyName 'status')) {
                    [string]$consultedUnit.status
                } elseif ($routedUnit -and (Test-VibeObjectHasProperty -InputObject $routedUnit -PropertyName 'status')) {
                    [string]$routedUnit.status
                } else {
                    'consultation_disclosed'
                }
                summary = if ($consultedUnit -and (Test-VibeObjectHasProperty -InputObject $consultedUnit -PropertyName 'summary')) {
                    [string]$consultedUnit.summary
                } elseif ($routedUnit -and (Test-VibeObjectHasProperty -InputObject $routedUnit -PropertyName 'summary')) {
                    [string]$routedUnit.summary
                } else {
                    $null
                }
            }
        ) | Out-Null
        $renderedLines += ('- {0}: {1} ({2})' -f [string]$disclosure.skill_id, [string]$disclosure.why_now, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $disclosure))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = ('{0}_consultation' -f $windowId)
        truth_layer = 'consultation'
        stage = if ((Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$ConsultationReceipt.stage)) { [string]$ConsultationReceipt.stage } else { $windowId }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistExecutionLifecycleLayerProjection {
    param(
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$ExecutionManifest = $null
    )

    if ($null -eq $SpecialistUserDisclosure) {
        return $null
    }

    $executedSkillIds = @()
    if ($null -ne $ExecutionManifest -and (Test-VibeObjectHasProperty -InputObject $ExecutionManifest -PropertyName 'specialist_accounting') -and $null -ne $ExecutionManifest.specialist_accounting) {
        foreach ($unit in @($ExecutionManifest.specialist_accounting.executed_specialist_units)) {
            if ($null -eq $unit) {
                continue
            }
            if ((Test-VibeObjectHasProperty -InputObject $unit -PropertyName 'skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$unit.skill_id)) {
                $executedSkillIds += [string]$unit.skill_id
            } elseif ((Test-VibeObjectHasProperty -InputObject $unit -PropertyName 'specialist_skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$unit.specialist_skill_id)) {
                $executedSkillIds += [string]$unit.specialist_skill_id
            }
        }
        $executedSkillIds = @($executedSkillIds | Select-Object -Unique)
    }

    $skills = New-Object System.Collections.Generic.List[object]
    $renderedLines = @('Execution-chain specialist disclosure:')
    foreach ($entry in @($SpecialistUserDisclosure.routed_skills)) {
        if ($null -eq $entry) {
            continue
        }
        $skillId = [string]$entry.skill_id
        if ([string]::IsNullOrWhiteSpace($skillId)) {
            continue
        }
        $state = if ($executedSkillIds -contains $skillId) { 'executed' } else { 'disclosed_for_execution' }
        $skills.Add(
            [pscustomobject]@{
                skill_id = $skillId
                why_now = 'approved for execution-time specialist dispatch under governed vibe'
                native_skill_entrypoint = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_entrypoint') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_entrypoint)) { [string]$entry.native_skill_entrypoint } else { $null }
                native_skill_entrypoint_raw = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_entrypoint_raw') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_entrypoint_raw)) { [string]$entry.native_skill_entrypoint_raw } else { $null }
                entrypoint_path_state = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_path_state') -and -not [string]::IsNullOrWhiteSpace([string]$entry.entrypoint_path_state)) { [string]$entry.entrypoint_path_state } else { 'resolved' }
                entrypoint_missing = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_missing')) { [bool]$entry.entrypoint_missing } else { $false }
                entrypoint_path_invalid = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'entrypoint_path_invalid')) { [bool]$entry.entrypoint_path_invalid } else { $false }
                native_skill_description = if ((Test-VibeObjectHasProperty -InputObject $entry -PropertyName 'native_skill_description') -and -not [string]::IsNullOrWhiteSpace([string]$entry.native_skill_description)) { [string]$entry.native_skill_description } else { $null }
                state = $state
            }
        ) | Out-Null
        $renderedLines += ('- {0}: approved for execution ({1})' -f $skillId, (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $entry))
    }

    if ($skills.Count -eq 0) {
        return $null
    }

    return [pscustomobject]@{
        layer_id = 'execution_dispatch'
        truth_layer = 'execution'
        stage = if ((Test-VibeObjectHasProperty -InputObject $SpecialistUserDisclosure -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$SpecialistUserDisclosure.stage)) { [string]$SpecialistUserDisclosure.stage } else { 'plan_execute' }
        skill_count = [int]$skills.Count
        skills = [object[]]$skills.ToArray()
        rendered_text = ($renderedLines -join "`n")
    }
}

function New-VibeSpecialistLifecycleDisclosureProjection {
    param(
        [AllowNull()] [object]$RuntimeInputPacket = $null,
        [AllowNull()] [object]$DiscussionConsultationReceipt = $null,
        [AllowNull()] [object]$PlanningConsultationReceipt = $null,
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$ExecutionManifest = $null
    )

    $layers = New-Object System.Collections.Generic.List[object]
    foreach ($candidate in @(
        (New-VibeSpecialistRoutingLifecycleLayerProjection -RuntimeInputPacket $RuntimeInputPacket),
        (New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $DiscussionConsultationReceipt),
        (New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $PlanningConsultationReceipt),
        (New-VibeSpecialistExecutionLifecycleLayerProjection -SpecialistUserDisclosure $SpecialistUserDisclosure -ExecutionManifest $ExecutionManifest)
    )) {
        if ($null -ne $candidate) {
            $layers.Add($candidate) | Out-Null
        }
    }

    $layerArray = [object[]]$layers.ToArray()
    $skillIds = @()
    $renderedSections = @()
    foreach ($layer in @($layerArray)) {
        foreach ($skill in @($layer.skills)) {
            if ($null -ne $skill -and -not [string]::IsNullOrWhiteSpace([string]$skill.skill_id)) {
                $skillIds += [string]$skill.skill_id
            }
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$layer.rendered_text)) {
            $renderedSections += [string]$layer.rendered_text
        }
    }
    $skillIds = @($skillIds | Select-Object -Unique)

    return [pscustomobject]@{
        enabled = [bool](@($layerArray).Count -gt 0)
        truth_model = 'routing_consultation_execution_separated'
        layer_count = @($layerArray).Count
        skill_count = @($skillIds).Count
        skill_ids = @($skillIds)
        layers = $layerArray
        rendered_text = (@($renderedSections) -join "`n`n")
    }
}

function Get-VibeSpecialistLifecycleDisclosureMarkdownLines {
    param(
        [AllowNull()] [object]$LifecycleDisclosure = $null,
        [AllowEmptyCollection()] [string[]]$IncludeLayerIds = @()
    )

    if ($null -eq $LifecycleDisclosure -or -not [bool]$LifecycleDisclosure.enabled) {
        return @()
    }

    $allowedLayerIds = @($IncludeLayerIds | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    $lines = @(
        '## Unified Specialist Lifecycle Disclosure',
        'This unified disclosure keeps routing truth, consultation truth, and execution truth separate while showing one user-readable specialist timeline.'
    )
    foreach ($layer in @($LifecycleDisclosure.layers)) {
        if ($allowedLayerIds.Count -gt 0 -and -not ($allowedLayerIds -contains [string]$layer.layer_id)) {
            continue
        }
        $lines += @(
            '',
            ('### {0}' -f [string]$layer.layer_id)
        )
        foreach ($skill in @($layer.skills)) {
            $lines += @(
                ('- Skill: {0}' -f [string]$skill.skill_id),
                ('  State: {0}' -f [string]$skill.state),
                ('  Why now: {0}' -f [string]$skill.why_now),
                ('  Loaded from: {0}' -f (Get-VibeSpecialistEntrypointDisplayText -SkillRecord $skill))
            )
        }
    }

    return @($lines)
}

function Get-VibeHostUserBriefingPath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'host-user-briefing.md'))
}

function Get-VibeHostStageDisclosurePath {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $SessionRoot 'host-stage-disclosure.json'))
}

function New-VibeHostUserBriefingSegmentProjection {
    param(
        [AllowNull()] [object]$LifecycleLayer = $null,
        [AllowNull()] [object]$ConsultationReceipt = $null
    )

    if ($null -eq $LifecycleLayer) {
        return $null
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'layer_id') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.layer_id)) {
        [string]$LifecycleLayer.layer_id
    } else {
        return $null
    }

    $segmentLines = @()
    $category = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.truth_layer)) {
        [string]$LifecycleLayer.truth_layer
    } else {
        'informational'
    }
    $status = 'informational'
    $gateStatus = $null

    switch ($segmentId) {
        'discussion_routing' {
            $segmentLines += 'Vibe routed these Skills into the discussion/planning chain:'
        }
        'execution_dispatch' {
            $category = 'execution'
            $status = 'execution_disclosure'
            $segmentLines += 'Vibe approved these Skills for execution:'
        }
        default {
            if ($segmentId -match '^(discussion|planning)_consultation$') {
                $windowId = [string]$Matches[1]
                $freezeGate = Get-VibePropertySafe -InputObject $ConsultationReceipt -PropertyName 'freeze_gate'
                if ($freezeGate) {
                    $gateStatus = if ([bool]$freezeGate.passed) { 'passed' } else { 'failed' }
                    $status = if ([bool]$freezeGate.passed) { 'gate_passed' } else { 'gate_failed' }
                } else {
                    $gateStatus = 'not_applicable'
                    $status = 'gate_unknown'
                }
                $category = 'consultation'
                $consultedUnits = if (
                    $ConsultationReceipt -and
                    (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'consulted_units') -and
                    $null -ne $ConsultationReceipt.consulted_units
                ) {
                    @($ConsultationReceipt.consulted_units)
                } else {
                    @()
                }
                $routedUnits = if (
                    $ConsultationReceipt -and
                    (Test-VibeObjectHasProperty -InputObject $ConsultationReceipt -PropertyName 'routed_units') -and
                    $null -ne $ConsultationReceipt.routed_units
                ) {
                    @($ConsultationReceipt.routed_units)
                } else {
                    @()
                }
                $summary = Get-VibePropertySafe -InputObject $ConsultationReceipt -PropertyName 'summary'
                $consultedCount = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('consulted_unit_count') -DefaultValue @($consultedUnits).Count
                $routedCount = Get-VibeNestedPropertySafe -InputObject $summary -PropertyPath @('routed_unit_count') -DefaultValue @($routedUnits).Count
                if ($routedCount -gt 0 -and $consultedCount -eq 0) {
                    $segmentLines += ('Vibe routed these Skills for direct current-session consultation during {0}; freeze gate: {1}.' -f $windowId, $gateStatus)
                } elseif ($consultedCount -gt 0 -and $routedCount -eq 0) {
                    $segmentLines += ('Vibe consulted these Skills during {0}; freeze gate: {1}.' -f $windowId, $gateStatus)
                } else {
                    $segmentLines += ('Vibe recorded these Skills in the {0} consultation chain; freeze gate: {1}.' -f $windowId, $gateStatus)
                }
            } else {
                $segmentLines += ('Vibe reported specialist activity for {0}:' -f $segmentId)
            }
        }
    }

    foreach ($skill in @($LifecycleLayer.skills)) {
        if ($null -eq $skill) {
            continue
        }
        $skillId = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'skill_id') -and -not [string]::IsNullOrWhiteSpace([string]$skill.skill_id)) {
            [string]$skill.skill_id
        } else {
            continue
        }
        $state = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'state') -and -not [string]::IsNullOrWhiteSpace([string]$skill.state)) { [string]$skill.state } else { 'reported' }
        $entrypoint = Get-VibeSpecialistEntrypointDisplayText -SkillRecord $skill
        $whyNow = if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'why_now') -and -not [string]::IsNullOrWhiteSpace([string]$skill.why_now)) { [string]$skill.why_now } else { 'no additional rationale recorded' }
        $segmentLines += ('- {0} [{1}] from {2}' -f $skillId, $state, $entrypoint)
        $segmentLines += ('  Why: {0}' -f $whyNow)
        if ((Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'summary') -and -not [string]::IsNullOrWhiteSpace([string]$skill.summary)) {
            $segmentLines += ('  Summary: {0}' -f [string]$skill.summary)
        }
    }

    $segmentText = @($segmentLines) -join "`n"
    return [pscustomobject]@{
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.stage)) { [string]$LifecycleLayer.stage } else { $null }
        category = $category
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$LifecycleLayer.truth_layer)) { [string]$LifecycleLayer.truth_layer } else { $category }
        status = $status
        gate_status = $gateStatus
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $LifecycleLayer -PropertyName 'skill_count')) { [int]$LifecycleLayer.skill_count } else { @($LifecycleLayer.skills).Count }
        skills = @($LifecycleLayer.skills)
        rendered_text = $segmentText
    }
}

function New-VibeHostStageDisclosureEventProjection {
    param(
        [AllowNull()] [object]$Segment = $null
    )

    if ($null -eq $Segment) {
        return $null
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'segment_id') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.segment_id)) {
        [string]$Segment.segment_id
    } else {
        return $null
    }

    $hasRoutedConsultation = $false
    $hasCompletedConsultation = $false
    foreach ($skill in @($Segment.skills)) {
        if ($null -eq $skill -or -not (Test-VibeObjectHasProperty -InputObject $skill -PropertyName 'state')) {
            continue
        }
        $state = [string]$skill.state
        if ($state -match '(^|_)routed($|_)') {
            $hasRoutedConsultation = $true
        }
        if ($state -in @('completed', 'completed_with_notes', 'consulted')) {
            $hasCompletedConsultation = $true
        }
    }

    $eventId = switch ($segmentId) {
        'discussion_routing' { 'discussion_routing_frozen' }
        'discussion_consultation' {
            if ($hasCompletedConsultation -and -not $hasRoutedConsultation) {
                'discussion_consultation_completed'
            } elseif ($hasRoutedConsultation -and -not $hasCompletedConsultation) {
                'discussion_consultation_routed'
            } else {
                'discussion_consultation_reported'
            }
        }
        'planning_consultation' {
            if ($hasCompletedConsultation -and -not $hasRoutedConsultation) {
                'planning_consultation_completed'
            } elseif ($hasRoutedConsultation -and -not $hasCompletedConsultation) {
                'planning_consultation_routed'
            } else {
                'planning_consultation_reported'
            }
        }
        'execution_dispatch' { 'execution_dispatch_confirmed' }
        default { ('{0}_reported' -f $segmentId) }
    }

    return [pscustomobject]@{
        event_id = $eventId
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.stage)) { [string]$Segment.stage } else { $null }
        category = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'category') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.category)) { [string]$Segment.category } else { $null }
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.truth_layer)) { [string]$Segment.truth_layer } else { $null }
        status = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'status') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.status)) { [string]$Segment.status } else { 'reported' }
        gate_status = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'gate_status') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.gate_status)) { [string]$Segment.gate_status } else { $null }
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'skill_count')) { [int]$Segment.skill_count } else { @($Segment.skills).Count }
        skills = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'skills')) { @($Segment.skills) } else { @() }
        rendered_text = if ((Test-VibeObjectHasProperty -InputObject $Segment -PropertyName 'rendered_text') -and -not [string]::IsNullOrWhiteSpace([string]$Segment.rendered_text)) { [string]$Segment.rendered_text } else { $null }
    }
}

function Add-VibeHostStageDisclosureEvent {
    param(
        [Parameter(Mandatory)] [string]$SessionRoot,
        [AllowNull()] [object]$DisclosureEvent = $null
    )

    if ($null -eq $DisclosureEvent) {
        return $null
    }

    $path = Get-VibeHostStageDisclosurePath -SessionRoot $SessionRoot
    $document = if (Test-Path -LiteralPath $path) {
        Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        [pscustomobject]@{
            enabled = $false
            protocol_version = 'v1'
            mode = 'progressive_host_stage_disclosure'
            append_only = $true
            event_count = 0
            last_sequence = 0
            freeze_gate_passed = $true
            events = @()
            rendered_text = ''
        }
    }

    $events = New-Object System.Collections.ArrayList
    foreach ($existingEvent in @($document.events)) {
        [void]$events.Add($existingEvent)
    }

    $segmentId = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'segment_id') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.segment_id)) {
        [string]$DisclosureEvent.segment_id
    } else {
        return $null
    }
    foreach ($existingEvent in @($events)) {
        if ($existingEvent -and [string]$existingEvent.segment_id -eq $segmentId) {
            return [pscustomobject]@{
                path = $path
                disclosure = $document
                event = $existingEvent
            }
        }
    }

    $recordedEvent = [pscustomobject]@{
        sequence = [int]($events.Count + 1)
        emitted_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        event_id = [string]$DisclosureEvent.event_id
        segment_id = $segmentId
        stage = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'stage') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.stage)) { [string]$DisclosureEvent.stage } else { $null }
        category = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'category') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.category)) { [string]$DisclosureEvent.category } else { $null }
        truth_layer = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'truth_layer') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.truth_layer)) { [string]$DisclosureEvent.truth_layer } else { $null }
        status = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'status') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.status)) { [string]$DisclosureEvent.status } else { 'reported' }
        gate_status = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'gate_status') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.gate_status)) { [string]$DisclosureEvent.gate_status } else { $null }
        skill_count = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'skill_count')) { [int]$DisclosureEvent.skill_count } else { @($DisclosureEvent.skills).Count }
        skills = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'skills')) { @($DisclosureEvent.skills) } else { @() }
        rendered_text = if ((Test-VibeObjectHasProperty -InputObject $DisclosureEvent -PropertyName 'rendered_text') -and -not [string]::IsNullOrWhiteSpace([string]$DisclosureEvent.rendered_text)) { [string]$DisclosureEvent.rendered_text } else { $null }
    }
    [void]$events.Add($recordedEvent)

    $eventArray = [object[]]$events.ToArray()
    $renderedSections = @()
    foreach ($eventEntry in @($eventArray)) {
        if ($null -eq $eventEntry -or [string]::IsNullOrWhiteSpace([string]$eventEntry.rendered_text)) {
            continue
        }
        $renderedSections += [string]$eventEntry.rendered_text
    }
    $failedConsultationEvents = @($eventArray | Where-Object { [string]$_.truth_layer -eq 'consultation' -and [string]$_.status -eq 'gate_failed' })
    $document = [pscustomobject]@{
        enabled = [bool](@($eventArray).Count -gt 0)
        protocol_version = 'v1'
        mode = 'progressive_host_stage_disclosure'
        append_only = $true
        event_count = [int]@($eventArray).Count
        last_sequence = [int]$recordedEvent.sequence
        freeze_gate_passed = [bool](@($failedConsultationEvents).Count -eq 0)
        events = $eventArray
        rendered_text = (@($renderedSections) -join "`n`n")
    }
    Write-VibeJsonArtifact -Path $path -Value $document

    return [pscustomobject]@{
        path = $path
        disclosure = $document
        event = $recordedEvent
    }
}

function New-VibeHostUserBriefingProjection {
    param(
        [AllowNull()] [object]$LifecycleDisclosure = $null,
        [AllowNull()] [object]$DiscussionConsultationReceipt = $null,
        [AllowNull()] [object]$PlanningConsultationReceipt = $null
    )

    if ($null -eq $LifecycleDisclosure -or -not [bool]$LifecycleDisclosure.enabled) {
        return $null
    }

    $consultationReceiptIndex = @{}
    foreach ($receipt in @($DiscussionConsultationReceipt, $PlanningConsultationReceipt)) {
        if ($null -eq $receipt) {
            continue
        }
        $windowId = if ((Test-VibeObjectHasProperty -InputObject $receipt -PropertyName 'window_id') -and -not [string]::IsNullOrWhiteSpace([string]$receipt.window_id)) {
            [string]$receipt.window_id
        } else {
            $null
        }
        if (-not [string]::IsNullOrWhiteSpace($windowId)) {
            $consultationReceiptIndex[$windowId] = $receipt
        }
    }

    $segments = New-Object System.Collections.Generic.List[object]
    $renderedSections = @('Specialist activity under governed vibe:')
    foreach ($layer in @($LifecycleDisclosure.layers)) {
        if ($null -eq $layer) {
            continue
        }
        $windowId = $null
        if ((Test-VibeObjectHasProperty -InputObject $layer -PropertyName 'layer_id') -and [string]$layer.layer_id -match '^(discussion|planning)_consultation$') {
            $windowId = [string]$Matches[1]
        }
        $receipt = if (-not [string]::IsNullOrWhiteSpace($windowId) -and $consultationReceiptIndex.ContainsKey($windowId)) { $consultationReceiptIndex[$windowId] } else { $null }
        $segment = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $layer -ConsultationReceipt $receipt
        if ($null -eq $segment) {
            continue
        }
        $segments.Add($segment) | Out-Null
        $renderedSections += @('', [string]$segment.rendered_text)
    }

    $segmentArray = [object[]]$segments.ToArray()
    $failedConsultationSegments = @($segmentArray | Where-Object { [string]$_.category -eq 'consultation' -and [string]$_.status -eq 'gate_failed' })
    $freezeGatePassed = [bool](@($failedConsultationSegments).Count -eq 0)

    return [pscustomobject]@{
        enabled = [bool](@($segmentArray).Count -gt 0)
        mode = 'progressive_specialist_host_briefing'
        freeze_gate_passed = $freezeGatePassed
        segment_count = @($segmentArray).Count
        segments = $segmentArray
        rendered_text = (@($renderedSections) -join "`n")
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
        [AllowNull()] [object]$StageLineage = $null,
        [AllowNull()] [object]$StorageProjection = $null,
        [AllowNull()] [object]$MemoryActivationReport,
        [AllowNull()] [object]$DeliveryAcceptanceReport,
        [AllowNull()] [object]$SpecialistDecision = $null,
        [AllowNull()] [object]$SpecialistUserDisclosure = $null,
        [AllowNull()] [object]$SpecialistConsultation = $null,
        [AllowNull()] [object]$SpecialistLifecycleDisclosure = $null,
        [AllowNull()] [object]$HostStageDisclosure = $null,
        [AllowNull()] [object]$HostUserBriefing = $null
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
        executed_stage_order = @(Get-VibeStageLineageExecutedStageOrder -StageLineage $StageLineage)
        terminal_stage = Get-VibeStageLineageTerminalStage -StageLineage $StageLineage
        artifacts = $Artifacts
        storage = $StorageProjection
        memory_activation = New-VibeRuntimeSummaryMemoryActivationProjection -MemoryActivationReport $MemoryActivationReport
        delivery_acceptance = New-VibeRuntimeSummaryDeliveryAcceptanceProjection -DeliveryAcceptanceReport $DeliveryAcceptanceReport
        specialist_decision = $SpecialistDecision
        specialist_user_disclosure = $SpecialistUserDisclosure
        specialist_consultation = $SpecialistConsultation
        specialist_lifecycle_disclosure = $SpecialistLifecycleDisclosure
        host_stage_disclosure = $HostStageDisclosure
        host_user_briefing = $HostUserBriefing
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
        [Parameter(Mandatory)] [string]$Task,
        [AllowEmptyString()] [string]$RequestedGradeFloor = ''
    )

    $grade = ''
    $taskLower = $Task.ToLowerInvariant()
    $xlPatterns = @('xl', 'multi-agent', 'parallel', 'wave', 'batch', '无人值守', 'autonomous', 'benchmark', 'front.*back', 'end-to-end')
    $lPatterns = @('design', 'plan', 'architecture', 'refactor', 'migrate', 'research', 'governance', '访谈', '规划', '设计', '治理')

    foreach ($pattern in $xlPatterns) {
        if ($taskLower -match $pattern) {
            $grade = 'XL'
            break
        }
    }

    if (-not $grade) {
        foreach ($pattern in $lPatterns) {
            if ($taskLower -match $pattern) {
                $grade = 'L'
                break
            }
        }
    }

    if (-not $grade -and $Task.Length -gt 180) {
        $grade = 'L'
    }

    if (-not $grade) {
        $grade = 'M'
    }

    $requestedFloor = [string]$RequestedGradeFloor
    if (-not [string]::IsNullOrWhiteSpace($requestedFloor)) {
        $normalizedFloor = $requestedFloor.Trim().ToUpperInvariant()
        $rank = @{
            'M' = 0
            'L' = 1
            'XL' = 2
        }
        if (-not $rank.ContainsKey($normalizedFloor)) {
            throw ("unsupported requested grade floor: {0}" -f $RequestedGradeFloor)
        }
        if ($rank[$normalizedFloor] -gt $rank[$grade]) {
            $grade = $normalizedFloor
        }
    }

    return $grade
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
