param(
    [Parameter(Mandatory)] [string]$RequirementDocPath,
    [switch]$EmitPlanMarkdown,
    [switch]$EmitJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\AntiProxyGoalDrift.ps1')

$packet = Get-VgoAntiProxyGoalDriftPacketFromRequirementDoc -RequirementDocPath $RequirementDocPath

if ($EmitPlanMarkdown) {
    (Get-VgoAntiProxyGoalDriftPlanLines -Packet $packet) -join [Environment]::NewLine
    return
}

if ($EmitJson) {
    $packet | ConvertTo-Json -Depth 10
    return
}

$packet
