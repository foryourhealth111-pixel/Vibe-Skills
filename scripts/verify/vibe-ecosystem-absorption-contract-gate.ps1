param()

$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition,[string]$Message)
    if ($Condition) { Write-Host "[PASS] $Message"; return $true }
    Write-Host "[FAIL] $Message" -ForegroundColor Red; return $false
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$matrixPath = Join-Path $repoRoot "docs\governance\absorption-admission-matrix.md"
$docsPath = Join-Path $repoRoot "docs\external-tooling\mcp-vs-skill-vs-manual.md"
$content = Get-Content -Raw $matrixPath -Encoding UTF8
$rules = Get-Content -Raw $docsPath -Encoding UTF8
$resources = @("mem0ai/mem0","letta-ai/letta","dair-ai/Prompt-Engineering-Guide","browser-use/browser-use","simular-ai/Agent-S")
$checks = @()
$checks += Assert-True (Test-Path $matrixPath) "admission matrix exists"
$checks += Assert-True (Test-Path $docsPath) "admission criteria doc exists"
$checks += Assert-True ($rules -match 'Lane 1: MCP' -and $rules -match 'Lane 5: Manual Reference') "all admission lanes documented"
foreach ($resource in $resources) {
    $checks += Assert-True ($content.Contains($resource)) ("matrix contains {0}" -f $resource)
}
$checks += Assert-True ($content -match 'Starting Mode') "matrix includes rollout starting mode"
$checks += Assert-True ($content -match 'Explicit Reject Surface') "matrix includes reject surface"
if ($checks -contains $false) { throw "ecosystem absorption contract gate failed" }
Write-Host "[PASS] ecosystem absorption contract gate succeeded" -ForegroundColor Green
