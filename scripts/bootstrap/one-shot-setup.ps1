param(
    [ValidateSet('minimal', 'full')]
    [string]$Profile = 'full',
    [string]$HostId = '',
    [string]$TargetRoot = '',
    [switch]$SkipExternalInstall,
    [switch]$StrictOffline,
    [switch]$SyncUserEnv,
    [string]$OpenAIBaseUrl = '',
    [string]$OpenAIApiKey = '',
    [string]$ArkBaseUrl = '',
    [string]$ArkApiKey = ''
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
    while ($true) {
        Write-Host 'Select the install target before bootstrap:'
        Write-Host '  1) codex        - strongest governed lane'
        Write-Host '  2) claude-code  - preview scaffold lane'
        Write-Host '  3) generic      - runtime-core for other agents'
        Write-Host '  4) opencode     - runtime-core for OpenCode'
        $choice = [string](Read-Host 'Install into which agent? [1-4]')
        $normalized = $choice.Trim().ToLowerInvariant()
        switch ($normalized) {
            '1' { return 'codex' }
            'codex' { return 'codex' }
            '2' { return 'claude-code' }
            'claude' { return 'claude-code' }
            'claude-code' { return 'claude-code' }
            '3' { return 'generic' }
            'generic' { return 'generic' }
            'other' { return 'generic' }
            'other-agent' { return 'generic' }
            'other-agents' { return 'generic' }
            '4' { return 'opencode' }
            'opencode' { return 'opencode' }
            default { Write-Warning "Unsupported choice: $choice. Enter 1, 2, 3, 4, or a host name." }
        }
    }
}

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')
. (Join-Path $PSScriptRoot '..\common\Resolve-VgoAdapter.ps1')
if (-not (Test-NonEmptyString -Value $HostId)) {
    if (Test-NonEmptyString -Value $env:VCO_HOST_ID) {
        $HostId = $env:VCO_HOST_ID
    } elseif (Test-IsInteractiveBootstrap) {
        $HostId = Prompt-VgoHostId
    } else {
        throw 'No host was provided for one-shot bootstrap. Pass -HostId codex|claude-code|generic|opencode when running non-interactively.'
    }
}
$HostId = Resolve-VgoHostId -HostId $HostId
$TargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot -HostId $HostId
Assert-VgoTargetRootMatchesHostIntent -TargetRoot $TargetRoot -HostId $HostId
$repoRoot = Resolve-VgoRepoRoot -StartPath $PSCommandPath
$Adapter = Resolve-VgoAdapterDescriptor -RepoRoot $repoRoot -HostId $HostId

function Get-ExistingSettingEnvValue {
    param(
        [Parameter(Mandatory)] [string]$CodexRoot,
        [Parameter(Mandatory)] [string]$Name
    )

    $settingsPath = Join-Path $CodexRoot 'settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        return $null
    }

    try {
        $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }

    if ($null -eq $settings -or -not ($settings.PSObject.Properties.Name -contains 'env') -or $null -eq $settings.env) {
        return $null
    }

    if ($settings.env.PSObject.Properties.Name -contains $Name) {
        $value = [string]$settings.env.$Name
        if (Test-NonEmptyString -Value $value) {
            return $value
        }
    }

    return $null
}

$installPath = Join-Path $repoRoot 'install.ps1'
$checkPath = Join-Path $repoRoot 'check.ps1'
$materializePath = Join-Path $repoRoot 'scripts\setup\materialize-codex-mcp-profile.ps1'
$persistOpenAiPath = Join-Path $repoRoot 'scripts\setup\persist-codex-openai-env.ps1'
$persistArkPath = Join-Path $repoRoot 'scripts\setup\persist-codex-ark-env.ps1'
$syncEnvPath = Join-Path $repoRoot 'scripts\setup\sync-codex-settings-to-user-env.ps1'
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
& $installPath @installArgs

switch ([string]$Adapter.bootstrap_mode) {
    'governed' {
        $existingOpenAiKey = Get-ExistingSettingEnvValue -CodexRoot $TargetRoot -Name 'OPENAI_API_KEY'
        $hasOpenAiSeed = (Test-NonEmptyString -Value $OpenAIApiKey) -or (Test-NonEmptyString -Value $env:OPENAI_API_KEY)
        if ($hasOpenAiSeed) {
            Write-Host '[2/5] Seeding OPENAI settings into target settings.json...' -ForegroundColor Yellow
            $openAiArgs = @{ CodexRoot = $TargetRoot }
            if (Test-NonEmptyString -Value $OpenAIBaseUrl) { $openAiArgs.BaseUrl = $OpenAIBaseUrl }
            if (Test-NonEmptyString -Value $OpenAIApiKey) { $openAiArgs.ApiKey = $OpenAIApiKey }
            & $persistOpenAiPath @openAiArgs
        } elseif (Test-NonEmptyString -Value $existingOpenAiKey) {
            Write-Host '[2/5] OPENAI settings already exist in target settings.json; keeping current value.' -ForegroundColor DarkGray
        } else {
            Write-Warning 'OPENAI_API_KEY not provided and not present in the current environment. Full online readiness will remain pending.'
        }

        $existingArkKey = Get-ExistingSettingEnvValue -CodexRoot $TargetRoot -Name 'ARK_API_KEY'
        $hasArkSeed = (Test-NonEmptyString -Value $ArkApiKey) -or (Test-NonEmptyString -Value $env:ARK_API_KEY)
        if ($hasArkSeed) {
            Write-Host '[3/5] Seeding ARK settings into target settings.json...' -ForegroundColor Yellow
            $arkArgs = @{ CodexRoot = $TargetRoot }
            if (Test-NonEmptyString -Value $ArkBaseUrl) { $arkArgs.BaseUrl = $ArkBaseUrl }
            if (Test-NonEmptyString -Value $ArkApiKey) { $arkArgs.ApiKey = $ArkApiKey }
            & $persistArkPath @arkArgs
        } elseif (Test-NonEmptyString -Value $existingArkKey) {
            Write-Host '[3/5] ARK settings already exist in target settings.json; keeping current value.' -ForegroundColor DarkGray
        } else {
            Write-Host '[3/5] ARK settings not provided; skipping optional ARK seeding.' -ForegroundColor DarkGray
        }

        if ($SyncUserEnv) {
            Write-Host '[4/5] Syncing configured settings.json env values into the user environment...' -ForegroundColor Yellow
            & $syncEnvPath -CodexRoot $TargetRoot -Target All -Scope User
        } else {
            Write-Host '[4/5] User environment sync skipped (pass -SyncUserEnv if you want registry env sync).' -ForegroundColor DarkGray
        }

        Write-Host '[5/5] Materializing MCP profile and running deep health check...' -ForegroundColor Yellow
        & $materializePath -TargetRoot $TargetRoot -Force | Out-Null
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    'preview-scaffold' {
        Write-Host '[2/5] Writing Claude preview scaffold...' -ForegroundColor Yellow
        & $claudeScaffoldPath -RepoRoot $repoRoot -TargetRoot $TargetRoot -Force | Out-Null
        Write-Host '[3/5] Claude preview keeps provider settings host-managed. You must supply url, apikey, and model yourself before claiming online readiness.' -ForegroundColor DarkGray
        Write-Host '[4/5] User environment sync is skipped for Claude preview.' -ForegroundColor DarkGray
        Write-Host '[5/5] Running preview health check...' -ForegroundColor Yellow
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    'runtime-core' {
        Write-Host '[2/5] Runtime-core lane does not materialize host settings.' -ForegroundColor DarkGray
        Write-Host '[3/5] Runtime-core lane does not seed provider settings. Configure url, apikey, and model in the target agent yourself.' -ForegroundColor DarkGray
        Write-Host '[4/5] User environment sync skipped for runtime-core lane.' -ForegroundColor DarkGray
        Write-Host '[5/5] Running runtime-core health check...' -ForegroundColor Yellow
        & $checkPath -Profile $Profile -HostId $HostId -TargetRoot $TargetRoot -Deep
    }
    default {
        throw \"Unsupported adapter bootstrap mode: $($Adapter.bootstrap_mode)\"
    }
}

Write-Host ''
Write-Host 'One-shot setup completed.' -ForegroundColor Green
Write-Host ('- Re-run deep doctor anytime with: pwsh -File "{0}" -Profile {1} -HostId {2} -TargetRoot "{3}" -Deep' -f $checkPath, $Profile, $HostId, $TargetRoot)
if ($Adapter.bootstrap_mode -eq 'governed') {
    Write-Host ('- MCP active file: {0}' -f (Join-Path $TargetRoot 'mcp\servers.active.json'))
}
Write-Host ('- Doctor artifacts: {0}' -f (Join-Path $repoRoot 'outputs\verify'))
