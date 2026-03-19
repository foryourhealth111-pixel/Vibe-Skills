Set-StrictMode -Version Latest

function Get-VgoProtectedDocumentCleanupPolicy {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [AllowEmptyString()] [string]$PolicyPath = ''
    )

    $resolvedPolicyPath = if ([string]::IsNullOrWhiteSpace($PolicyPath)) {
        Join-Path $RepoRoot 'config\phase-cleanup-policy.json'
    } else {
        $PolicyPath
    }

    if (-not (Test-Path -LiteralPath $resolvedPolicyPath)) {
        throw "phase cleanup policy not found: $resolvedPolicyPath"
    }

    return (Get-Content -LiteralPath $resolvedPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-VgoProtectedDocumentExtensions {
    param([Parameter(Mandatory)] [psobject]$Policy)

    $extensions = @()
    if ($Policy.PSObject.Properties.Name -contains 'protected_document_policy') {
        $extensions = @($Policy.protected_document_policy.extensions)
    }

    return @($extensions | ForEach-Object {
            $value = ([string]$_).Trim()
            if ([string]::IsNullOrWhiteSpace($value)) { return }
            if ($value.StartsWith('.')) { $value.ToLowerInvariant() } else { ".$($value.ToLowerInvariant())" }
        } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
}

function Test-VgoProtectedDocumentFile {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string[]]$Extensions
    )

    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    return ($Extensions -contains $extension)
}

function Get-VgoProtectedDocumentSnapshot {
    param(
        [Parameter(Mandatory)] [string]$BaseRoot,
        [Parameter(Mandatory)] [string[]]$Roots,
        [Parameter(Mandatory)] [string[]]$Extensions
    )

    $items = New-Object 'System.Collections.Generic.List[object]'
    foreach ($root in @($Roots)) {
        if ([string]::IsNullOrWhiteSpace($root)) {
            continue
        }

        $fullRoot = [System.IO.Path]::GetFullPath($root)
        if (-not (Test-Path -LiteralPath $fullRoot)) {
            continue
        }

        foreach ($file in @(Get-ChildItem -LiteralPath $fullRoot -Recurse -File -ErrorAction SilentlyContinue)) {
            if (-not (Test-VgoProtectedDocumentFile -Path $file.FullName -Extensions $Extensions)) {
                continue
            }

            $items.Add([pscustomobject]@{
                    full_path = [System.IO.Path]::GetFullPath($file.FullName)
                    relative_path = [System.IO.Path]::GetRelativePath($BaseRoot, $file.FullName).Replace('\', '/')
                    root = $fullRoot
                    extension = $file.Extension.ToLowerInvariant()
                    size_bytes = [int64]$file.Length
                    last_write_utc = $file.LastWriteTimeUtc.ToString('o')
                }) | Out-Null
        }
    }

    return @($items | Sort-Object relative_path)
}

function Get-VgoProtectedDocumentManifest {
    param(
        [Parameter(Mandatory)] [string]$RepoRoot,
        [Parameter(Mandatory)] [psobject]$Policy,
        [Parameter(Mandatory)] [string]$TmpRoot
    )

    $extensions = Get-VgoProtectedDocumentExtensions -Policy $Policy
    $snapshotRoots = @()
    if ($Policy.protected_document_policy.PSObject.Properties.Name -contains 'snapshot_roots') {
        foreach ($relativeRoot in @($Policy.protected_document_policy.snapshot_roots)) {
            $snapshotRoots += [System.IO.Path]::GetFullPath((Join-Path $RepoRoot ([string]$relativeRoot)))
        }
    }

    if (-not ($snapshotRoots -contains $TmpRoot) -and (Test-Path -LiteralPath $TmpRoot)) {
        $snapshotRoots += [System.IO.Path]::GetFullPath($TmpRoot)
    }

    $snapshot = Get-VgoProtectedDocumentSnapshot -BaseRoot $RepoRoot -Roots $snapshotRoots -Extensions $extensions
    $tmpItems = @($snapshot | Where-Object { Test-VgoPathWithin -ParentPath $TmpRoot -ChildPath $_.full_path })
    $retainedItems = @($snapshot | Where-Object { -not (Test-VgoPathWithin -ParentPath $TmpRoot -ChildPath $_.full_path) })

    return [pscustomobject]@{
        snapshot = $snapshot
        tmp_items = $tmpItems
        retained_items = $retainedItems
        summary = [ordered]@{
            protected_total = @($snapshot).Count
            tmp_protected_total = @($tmpItems).Count
            retained_outside_tmp_total = @($retainedItems).Count
        }
    }
}

function Move-VgoProtectedDocumentsToQuarantine {
    param(
        [Parameter(Mandatory)] [string]$TmpRoot,
        [Parameter(Mandatory)] [string]$QuarantineRoot,
        [Parameter(Mandatory)] [string[]]$Extensions
    )

    $moved = New-Object 'System.Collections.Generic.List[object]'
    if (-not (Test-Path -LiteralPath $TmpRoot)) {
        return @()
    }

    foreach ($file in @(Get-ChildItem -LiteralPath $TmpRoot -Recurse -File -ErrorAction SilentlyContinue)) {
        if (-not (Test-VgoProtectedDocumentFile -Path $file.FullName -Extensions $Extensions)) {
            continue
        }

        $relativePath = [System.IO.Path]::GetRelativePath($TmpRoot, $file.FullName)
        $targetPath = Join-Path $QuarantineRoot $relativePath
        $parent = Split-Path -Parent $targetPath
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }

        Move-Item -LiteralPath $file.FullName -Destination $targetPath -Force
        $moved.Add([pscustomobject]@{
                original_path = [System.IO.Path]::GetFullPath($file.FullName)
                relative_path = $relativePath.Replace('\', '/')
                quarantine_path = [System.IO.Path]::GetFullPath($targetPath)
                extension = $file.Extension.ToLowerInvariant()
            }) | Out-Null
    }

    return @($moved | Sort-Object relative_path)
}

function Test-VgoProtectedDocumentPostConditions {
    param(
        [Parameter(Mandatory)] [psobject]$Manifest,
        $QuarantinedItems = $null
    )

    $assertions = New-Object 'System.Collections.Generic.List[object]'
    $normalizedQuarantinedItems = @(
        foreach ($item in @($QuarantinedItems)) {
            if ($null -eq $item) {
                continue
            }

            if ($item -eq [System.Management.Automation.Internal.AutomationNull]::Value) {
                continue
            }

            $item
        }
    )

    foreach ($item in @($Manifest.retained_items)) {
        $exists = Test-Path -LiteralPath $item.full_path
        $assertions.Add([pscustomobject]@{
                pass = [bool]$exists
                message = "protected asset retained outside tmp: $($item.relative_path)"
                path = $item.full_path
            }) | Out-Null
    }

    foreach ($item in $normalizedQuarantinedItems) {
        $exists = Test-Path -LiteralPath $item.quarantine_path
        $assertions.Add([pscustomobject]@{
                pass = [bool]$exists
                message = "protected tmp asset moved to quarantine: $($item.relative_path)"
                path = $item.quarantine_path
            }) | Out-Null
    }

    return $assertions.ToArray()
}
