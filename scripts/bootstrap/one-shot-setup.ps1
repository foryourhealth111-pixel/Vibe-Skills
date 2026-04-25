param(
    [ValidateSet('minimal', 'full')]
    [string]$Profile = 'full',
    [string]$HostId = '',
    [string]$TargetRoot = '',
    [switch]$SkipExternalInstall,
    [switch]$StrictOffline,
    [switch]$SyncUserEnv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-NonEmptyString {
    param([AllowNull()][string]$Value)
    return (-not [string]::IsNullOrWhiteSpace($Value))
}

function Test-IsInteractiveBootstrap {
    try {
        return [Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected
    } catch {
        return $true
    }
}

function Prompt-VgoHostId {
    $choices = @(Get-VgoBootstrapHostChoices -StartPath $PSScriptRoot)
    if ($choices.Count -eq 0) {
        throw 'No bootstrap host choices were available from the adapter registry.'
    }

    while ($true) {
        Write-Host 'Select the install target before bootstrap:'
        foreach ($entry in $choices) {
            Write-Host ("  {0}) {1,-12} - {2}" -f $entry.index, $entry.id, $entry.summary)
        }

        $choice = [string](Read-Host ("Install into which agent? [1-{0}]" -f $choices.Count))
        $normalized = $choice.Trim().ToLowerInvariant()
        foreach ($entry in $choices) {
            if ($normalized -eq [string]$entry.index -or $normalized -eq [string]$entry.id) {
                return [string]$entry.id
            }
            foreach ($alias in @($entry.aliases)) {
                if ($normalized -eq [string]$alias) {
                    return [string]$entry.id
                }
            }
        }

        Write-Warning ("Unsupported choice: {0}. Enter 1-{1}, or a supported host name." -f $choice, $choices.Count)
    }
}

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

if (-not (Test-NonEmptyString -Value $HostId)) {
    if (Test-NonEmptyString -Value $env:VCO_HOST_ID) {
        $HostId = $env:VCO_HOST_ID
    } elseif (Test-IsInteractiveBootstrap) {
        $HostId = Prompt-VgoHostId
    } else {
        throw ("No host was provided for one-shot bootstrap. Pass -HostId {0} when running non-interactively." -f (Get-VgoSupportedHostHint -StartPath $PSScriptRoot))
    }
}
$HostId = Resolve-VgoHostId -HostId $HostId
$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId
$repoRoot = Resolve-VgoRepoRoot -StartPath $PSCommandPath
$Adapter = Resolve-VgoAdapterEntry -StartPath $repoRoot -HostId $HostId

function Write-McpAutoProvisionSummary {
    param(
        [Parameter(Mandatory)] [string]$TargetRoot
    )

    $receiptPath = Join-Path $TargetRoot '.vibeskills\mcp-auto-provision.json'
    $activePath = Join-Path $TargetRoot 'mcp\servers.active.json'
    Write-Host 'MCP auto-provision summary'
    if (-not (Test-Path -LiteralPath $receiptPath)) {
        Write-Host '- receipt: missing' -ForegroundColor Yellow
        return
    }

    $payload = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $activeServers = @{}
    if (Test-Path -LiteralPath $activePath) {
        try {
            $activePayload = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($null -ne $activePayload -and $activePayload.PSObject.Properties.Name -contains 'servers' -and $null -ne $activePayload.servers) {
                foreach ($serverProp in $activePayload.servers.PSObject.Properties) {
                    $activeServers[[string]$serverProp.Name] = $serverProp.Value
                }
            }
        } catch {
        }
    }
    Write-Host ("- installed_locally: {0}" -f ([string]($payload.install_state -eq 'installed_locally')).ToLowerInvariant())
    Write-Host ("- mcp_auto_provision_attempted: {0}" -f ([string][bool]$payload.mcp_auto_provision_attempted).ToLowerInvariant())
    $manualFollowUp = @()
    foreach ($item in @($payload.mcp_results)) {
        if ($null -eq $item) { continue }
        $name = [string]$item.name
        $status = [string]$item.status
        $nextStep = [string]$item.next_step
        if ($status -eq 'local_tool_present' -and $activeServers.ContainsKey($name)) {
            $activeServer = $activeServers[$name]
            $mode = if ($null -ne $activeServer -and $activeServer.PSObject.Properties.Name -contains 'mode') { [string]$activeServer.mode } else { '' }
            $commandName = if ($null -ne $activeServer -and $activeServer.PSObject.Properties.Name -contains 'command') { [string]$activeServer.command } else { '' }
            if ($mode -eq 'stdio' -and (Test-NonEmptyString -Value $commandName) -and (Get-Command $commandName -ErrorAction SilentlyContinue)) {
                $status = 'ready'
                $nextStep = 'none'
            }
        }
        Write-Host ("- {0}: status={1} next_step={2}" -f $name, $status, $nextStep)
        if ($status -ne 'ready') {
            $manualFollowUp += $name
        }
    }
    Write-Host ("- manual_follow_up: {0}" -f $(if ($manualFollowUp.Count -gt 0) { $manualFollowUp -join ', ' } else { 'none' }))
}

$installPath = Join-Path $repoRoot 'install.ps1'
$checkPath = Join-Path $repoRoot 'check.ps1'
$materializePath = Join-Path $repoRoot 'scripts\setup\materialize-codex-mcp-profile.ps1'
$claudeScaffoldPath = Join-Path $repoRoot 'scripts\bootstrap\scaffold-claude-preview.ps1'

Write-Host '=== VCO One-Shot Setup ===' -ForegroundColor Cyan
Write-Host ("Repo root           : {0}" -f $repoRoot)
Write-Host ("Host                : {0}" -f $HostId)
Write-Host ("Mode                : {0}" -f $Adapter.bootstrap_mode)
Write-Host ("Target root         : {0}" -f $TargetRoot)
Write-Host ("Profile             : {0}" -f $Profile)
Write-Host ("StrictOffline       : {0}" -f ([bool]$StrictOffline))
Write-Host ("SkipExternalInstall : {0}" -f ([bool]$SkipExternalInstall))
Write-Host ("SyncUserEnv         : {0}" -f ([bool]$SyncUserEnv))

if (-not $SkipExternalInstall) {
    Write-Host 'External CLI install is enabled. npm-based steps such as claude-flow may take several minutes, and deprecated warnings are advisory unless the command exits non-zero.' -ForegroundColor DarkYellow
}

$installArgs = @{
    Profile = $Profile
    HostId = $HostId
    TargetRoot = $TargetRoot
}
if (-not $SkipExternalInstall) {
    $installArgs.InstallExternal = $true
}
if ($StrictOffline) {
    $installArgs.StrictOffline = $true
}

Write-Host ''
Write-Host '[1/5] Installing adapter payload...' -ForegroundColor Yellow
$previousInstallReportSuppression = $env:VGO_SUPPRESS_INSTALL_COMPLETION_REPORT
$env:VGO_SUPPRESS_INSTALL_COMPLETION_REPORT = '1'
try {
    & $installPath @installArgs
} finally {
    if ([string]::IsNullOrWhiteSpace($previousInstallReportSuppression)) {
        Remove-Item Env:VGO_SUPPRESS_INSTALL_COMPLETION_REPORT -ErrorAction SilentlyContinue
    } else {
        $env:VGO_SUPPRESS_INSTALL_COMPLETION_REPORT = $previousInstallReportSuppression
    }
}

switch ([string]$Adapter.bootstrap_mode) {
    'governed' {
        Write-Host '[2/5] Built-in online enhancement configuration is skipped in public install.' -ForegroundColor DarkGray

        if ($SyncUserEnv) {
            Write-Host '[3/5] User environment sync skipped; public install does not export provider settings.' -ForegroundColor DarkGray
        } else {
            Write-Host '[3/5] User environment sync skipped.' -ForegroundColor DarkGray
        }

        Write-Host '[4/5] Materializing MCP profile...' -ForegroundColor Yellow
        & $materializePath -TargetRoot $TargetRoot -Force | Out-Null
        Write-Host '[5/5] Running deep health check...' -ForegroundColor Yellow
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    'preview-guidance' {
        if ($HostId -eq 'claude-code') {
            Write-Host '[2/5] Hook installation is frozen for Claude Code because of compatibility issues.' -ForegroundColor Yellow
            & $claudeScaffoldPath -RepoRoot $repoRoot -TargetRoot $TargetRoot -Force | Out-Null
        } else {
            Write-Host ("[2/5] Host-specific scaffold is currently unavailable for '{0}'." -f $HostId) -ForegroundColor Yellow
        }
        Write-Host '[3/5] No hook files or extra preview settings were installed into the target root.' -ForegroundColor DarkGray
        Write-Host ("[4/5] Provider settings remain host-managed for '{0}'. Built-in online enhancement configuration is not part of public install." -f $HostId) -ForegroundColor DarkGray
        Write-Host '[5/5] Running supported-path health check...' -ForegroundColor Yellow
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    'runtime-core' {
        Write-Host '[2/5] Runtime-adapter path does not materialize host settings.' -ForegroundColor DarkGray
        Write-Host '[3/5] Runtime-adapter path does not seed provider settings; public install skips built-in online enhancement configuration.' -ForegroundColor DarkGray
        Write-Host '[4/5] User environment sync skipped for the runtime-adapter path.' -ForegroundColor DarkGray
        Write-Host '[5/5] Running runtime-adapter health check...' -ForegroundColor Yellow
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    default {
        throw \"Unsupported adapter bootstrap mode: $($Adapter.bootstrap_mode)\"
    }
}

Write-Host ''
Write-McpAutoProvisionSummary -TargetRoot $TargetRoot
Write-Host 'One-shot setup completed.' -ForegroundColor Green
$checkShellPath = Get-VgoPowerShellCommand
$checkShellLeaf = [System.IO.Path]::GetFileName($checkShellPath).ToLowerInvariant()
$checkCommandParts = @($checkShellLeaf, '-NoProfile')
if ($checkShellLeaf -like 'powershell*') {
    $checkCommandParts += @('-ExecutionPolicy', 'Bypass')
}
$checkCommandParts += @('-File', $checkPath, '-Profile', $Profile, '-HostId', $HostId, '-TargetRoot', $TargetRoot, '-Deep')
$checkCommand = ($checkCommandParts | ForEach-Object {
    $text = [string]$_
    if ($text -match '\s') {
        '"' + ($text -replace '"', '\"') + '"'
    } else {
        $text
    }
}) -join ' '
Write-Host ('- Re-run deep doctor anytime with: {0}' -f $checkCommand)
if ($Adapter.bootstrap_mode -eq 'governed') {
    Write-Host ('- MCP active file: {0}' -f (Join-Path $TargetRoot 'mcp\servers.active.json'))
}
Write-Host ('- Doctor artifacts: {0}' -f (Join-Path $repoRoot 'outputs\verify'))
