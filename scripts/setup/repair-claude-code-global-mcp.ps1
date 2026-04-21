param(
    [string]$UserConfigPath = '',
    [switch]$PreserveClaudeFlowAliases
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

function Get-CommandLeaf {
    param([AllowNull()][string]$Command)

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return ''
    }
    $trimmed = $Command.Trim().Trim('"').Trim("'")
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return ''
    }
    return [System.IO.Path]::GetFileName($trimmed).ToLowerInvariant()
}

function Get-StringArray {
    param([AllowNull()]$Value)

    $items = @()
    if ($null -eq $Value) {
        return $items
    }
    foreach ($item in @($Value)) {
        $items += [string]$item
    }
    return $items
}

function ConvertTo-AsciiSafeJson {
    param(
        [Parameter(Mandatory)] $InputObject,
        [int]$Depth = 10
    )

    $json = $InputObject | ConvertTo-Json -Depth $Depth
    $builder = New-Object System.Text.StringBuilder
    foreach ($char in $json.ToCharArray()) {
        $codepoint = [int][char]$char
        if ($codepoint -gt 0x7F) {
            [void]$builder.AppendFormat('\u{0:x4}', $codepoint)
            continue
        }
        [void]$builder.Append($char)
    }

    return $builder.ToString()
}

function Test-WindowsBareNpxMcpServer {
    param([Parameter(Mandatory)] $Server)

    $commandLeaf = Get-CommandLeaf -Command ([string]$Server.command)
    if ($commandLeaf -notin @('npx', 'npx.cmd', 'npx.exe', 'npx.ps1')) {
        return $false
    }
    $args = Get-StringArray -Value $Server.args
    if ($args.Count -ge 2 -and $args[0].ToLowerInvariant() -eq '/c' -and (Get-CommandLeaf -Command $args[1]) -in @('npx', 'npx.cmd', 'npx.exe', 'npx.ps1')) {
        return $false
    }
    return $true
}

function Test-ClaudeFlowMcpServer {
    param([Parameter(Mandatory)] $Server)

    $commandLeaf = Get-CommandLeaf -Command ([string]$Server.command)
    if ($commandLeaf -notin @('claude-flow', 'claude-flow.cmd', 'claude-flow.exe', 'claude-flow.ps1')) {
        return $false
    }
    $args = Get-StringArray -Value $Server.args
    return ($args.Count -ge 2 -and $args[0] -eq 'mcp' -and $args[1] -eq 'start')
}

function Repair-McpServerTable {
    param(
        [AllowNull()]$ServerTable,
        [Parameter(Mandatory)] [string]$Scope,
        [Parameter(Mandatory)] $Wrapped,
        [Parameter(Mandatory)] $Removed
    )

    if ($null -eq $ServerTable) {
        return
    }

    $serverNames = @($ServerTable.PSObject.Properties.Name)
    foreach ($serverName in $serverNames) {
        $server = $ServerTable.$serverName
        if ($null -eq $server) {
            continue
        }

        if ((-not $PreserveClaudeFlowAliases) -and (Test-ClaudeFlowMcpServer -Server $server)) {
            $ServerTable.PSObject.Properties.Remove($serverName)
            $Removed.Add(('{0}:{1}' -f $Scope, $serverName)) | Out-Null
            continue
        }

        if (Test-WindowsBareNpxMcpServer -Server $server) {
            $existingArgs = Get-StringArray -Value $server.args
            $server.command = 'cmd'
            $server.args = @('/c', 'npx') + $existingArgs
            $Wrapped.Add(('{0}:{1}' -f $Scope, $serverName)) | Out-Null
        }
    }
}

function Repair-McpNameLists {
    param(
        [AllowNull()]$Node,
        [Parameter(Mandatory)] [string]$Scope,
        [Parameter(Mandatory)] $Cleaned
    )

    if ($null -eq $Node) {
        return
    }

    if ($PreserveClaudeFlowAliases) {
        return
    }

    foreach ($propertyName in @('enabledMcpServers', 'disabledMcpServers', 'enabledMcpjsonServers', 'disabledMcpjsonServers')) {
        if ($Node.PSObject.Properties.Name -notcontains $propertyName) {
            continue
        }
        $existing = @()
        foreach ($item in @(Get-StringArray -Value $Node.$propertyName)) {
            if ($item -notin @('claude-flow', 'ruflo')) {
                $existing += $item
            }
        }
        $beforeCount = @(Get-StringArray -Value $Node.$propertyName).Count
        $afterCount = $existing.Count
        if ($afterCount -ne $beforeCount) {
            $Node.$propertyName = $existing
            $Cleaned.Add(('{0}:{1}' -f $Scope, $propertyName)) | Out-Null
        }
    }
}

if ([string]::IsNullOrWhiteSpace($UserConfigPath)) {
    $userProfile = [Environment]::GetFolderPath('UserProfile')
    if ([string]::IsNullOrWhiteSpace($userProfile)) {
        throw 'Unable to resolve the current user profile directory.'
    }
    $UserConfigPath = Join-Path $userProfile '.claude.json'
}

$configPath = [System.IO.Path]::GetFullPath($UserConfigPath)
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Claude Code user config not found: $configPath"
}

try {
    $payload = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw ("Failed to parse Claude Code user config: " + $_.Exception.Message)
}

$wrapped = New-Object 'System.Collections.Generic.List[string]'
$removed = New-Object 'System.Collections.Generic.List[string]'
$cleanedLists = New-Object 'System.Collections.Generic.List[string]'

$globalMcpServers = if ($payload.PSObject.Properties.Name -contains 'mcpServers') { $payload.mcpServers } else { $null }
Repair-McpServerTable -ServerTable $globalMcpServers -Scope 'global' -Wrapped $wrapped -Removed $removed
Repair-McpNameLists -Node $payload -Scope 'global' -Cleaned $cleanedLists

if ($payload.PSObject.Properties.Name -contains 'projects' -and $null -ne $payload.projects) {
    foreach ($projectName in @($payload.projects.PSObject.Properties.Name)) {
        $project = $payload.projects.$projectName
        if ($null -eq $project) {
            continue
        }
        $projectMcpServers = if ($project.PSObject.Properties.Name -contains 'mcpServers') { $project.mcpServers } else { $null }
        Repair-McpServerTable -ServerTable $projectMcpServers -Scope ('project:{0}' -f $projectName) -Wrapped $wrapped -Removed $removed
        Repair-McpNameLists -Node $project -Scope ('project:{0}' -f $projectName) -Cleaned $cleanedLists
    }
}

$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupPath = '{0}.bak-vgo-{1}' -f $configPath, $timestamp
Copy-Item -LiteralPath $configPath -Destination $backupPath -Force
Write-VgoUtf8NoBomText -Path $configPath -Content (($payload | ConvertTo-Json -Depth 100) + "`n")

$result = [pscustomobject]@{
    user_config_path = $configPath
    backup_path = $backupPath
    wrapped_servers = @($wrapped)
    removed_servers = @($removed)
    cleaned_lists = @($cleanedLists)
    preserve_claude_flow_aliases = [bool]$PreserveClaudeFlowAliases
}

ConvertTo-AsciiSafeJson -InputObject $result -Depth 10
