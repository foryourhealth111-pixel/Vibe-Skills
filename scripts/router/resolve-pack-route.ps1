param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [AllowEmptyString()]
    [string]$Grade = "",
    [AllowEmptyString()]
    [string]$TaskType = "",
    [string]$RequestedSkill,
    [string]$HostId,
    [string]$TargetRoot,
    [string]$WorkspaceRoot,
    [AllowEmptyString()]
    [string]$HostDecisionJson = "",
    [switch]$Probe,
    [string]$ProbeLabel,
    [string]$ProbeOutputDir,
    [switch]$ProbeIncludePrompt,
    [int]$ProbePromptMaxChars = 1600,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSEdition -eq 'Desktop' -or $PSVersionTable.Platform -eq 'Win32NT') {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} else {
    $OutputEncoding = [System.Text.Encoding]::UTF8
}

function Resolve-LocalRouterPython {
    $commands = @(
        @{ exe = 'py'; args = @('-3') },
        @{ exe = 'python'; args = @() },
        @{ exe = 'python3'; args = @() }
    )
    foreach ($command in $commands) {
        $resolved = Get-Command -Name $command.exe -ErrorAction SilentlyContinue
        if ($null -ne $resolved) {
            return [pscustomobject]@{
                exe = [string]$resolved.Source
                args = [string[]]$command.args
            }
        }
    }
    throw 'Unable to locate Python for local skill router.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Resolve-LocalRouterPython
$pythonPathParts = @(
    (Join-Path $repoRoot 'apps\vgo-cli\src'),
    (Join-Path $repoRoot 'packages\runtime-core\src'),
    (Join-Path $repoRoot 'packages\contracts\src')
)
$oldPythonPath = [string]$env:PYTHONPATH
$env:PYTHONPATH = (($pythonPathParts + @($oldPythonPath)) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }) -join [System.IO.Path]::PathSeparator
$oldPythonUtf8 = [string]$env:PYTHONUTF8
$oldPythonIoEncoding = [string]$env:PYTHONIOENCODING
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$routeOutputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("vgo-route-output-" + [System.Guid]::NewGuid().ToString("N") + ".json")

$routeArgs = @(
    '-m', 'vgo_cli.main',
    'route',
    '--repo-root', $repoRoot,
    '--prompt', $Prompt,
    '--grade', $(if ([string]::IsNullOrWhiteSpace($Grade)) { 'M' } else { $Grade }),
    '--task-type', $(if ([string]::IsNullOrWhiteSpace($TaskType)) { 'planning' } else { $TaskType }),
    '--output-json-path', $routeOutputPath,
    '--force-runtime-neutral'
)
if (-not [string]::IsNullOrWhiteSpace([string]$RequestedSkill)) {
    $routeArgs += @('--requested-skill', [string]$RequestedSkill)
}
if (-not [string]::IsNullOrWhiteSpace([string]$HostId)) {
    $routeArgs += @('--host-id', [string]$HostId)
}
if (-not [string]::IsNullOrWhiteSpace([string]$TargetRoot)) {
    $routeArgs += @('--target-root', [string]$TargetRoot)
}
if (-not [string]::IsNullOrWhiteSpace([string]$WorkspaceRoot)) {
    $routeArgs += @('--workspace-root', [string]$WorkspaceRoot)
}

try {
    $output = & $python.exe @($python.args + $routeArgs) 2>&1
    $exitCode = if ($null -ne $global:LASTEXITCODE) { [int]$global:LASTEXITCODE } else { 0 }
    if ($exitCode -ne 0) {
        Write-Error ((@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine)
        exit $exitCode
    }
    if (-not (Test-Path -LiteralPath $routeOutputPath -PathType Leaf)) {
        throw "Local skill router did not write route JSON output: $routeOutputPath"
    }
    $text = [System.IO.File]::ReadAllText($routeOutputPath, [System.Text.Encoding]::UTF8).Trim()
    if (-not [string]::IsNullOrWhiteSpace($text)) {
        Write-Output $text
    }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    if ([string]::IsNullOrWhiteSpace($oldPythonUtf8)) {
        Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONUTF8 = $oldPythonUtf8
    }
    if ([string]::IsNullOrWhiteSpace($oldPythonIoEncoding)) {
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONIOENCODING = $oldPythonIoEncoding
    }
    if (Test-Path -LiteralPath $routeOutputPath) {
        Remove-Item -LiteralPath $routeOutputPath -Force -ErrorAction SilentlyContinue
    }
}
