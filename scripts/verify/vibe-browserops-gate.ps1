param()

$ErrorActionPreference = 'Stop'

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if ($Condition) {
    Write-Host "[PASS] $Message"
    return $true
  }

  Write-Host "[FAIL] $Message" -ForegroundColor Red
  return $false
}

function Normalize-PathString {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $Path
  }

  $normalized = $Path -replace '^Microsoft\.PowerShell\.Core\\FileSystem::', ''
  $normalized = $normalized -replace '^\\\\\?\\', ''
  return $normalized
}

function Invoke-SuggestJson {
  param(
    [string]$ScriptPath,
    [string]$Task
  )

  $raw = & $ScriptPath -Task $Task -AsJson | Out-String
  $json = (($raw -split "`r?`n") | Where-Object {
      $line = $_.Trim()
      $line -and $line -notmatch '^\[Proxy\]'
    }) -join "`n"

  if ([string]::IsNullOrWhiteSpace($json)) {
    throw "suggest-browserops-provider returned empty JSON payload for task: $Task"
  }

  return ($json | ConvertFrom-Json)
}

$scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Definition }
$scriptPath = Normalize-PathString -Path $scriptPath
$scriptDirectory = Split-Path -Parent $scriptPath
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDirectory '..\..'))
$policyPath = Join-Path $repoRoot 'config\browserops-provider-policy.json'
$forbiddenPolicyPath = Join-Path $repoRoot 'config\forbidden-mcp-policy.json'
$contractPath = Join-Path $repoRoot 'references\browser-task-contract.md'
$suggestPath = Join-Path $repoRoot 'scripts\overlay\suggest-browserops-provider.ps1'

$checks = @()
$checks += Assert-True (Test-Path -LiteralPath $policyPath) '存在 BrowserOps policy 文件'
$checks += Assert-True (Test-Path -LiteralPath $forbiddenPolicyPath) '存在 forbidden MCP policy 文件'
$checks += Assert-True (Test-Path -LiteralPath $contractPath) '存在 BrowserOps contract 文件'
$checks += Assert-True (Test-Path -LiteralPath $suggestPath) '存在 BrowserOps 建议脚本'

if ($checks -contains $false) {
  throw 'vibe-browserops-gate failed before content checks'
}

$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$forbiddenPolicy = Get-Content -LiteralPath $forbiddenPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$contractText = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8
$forbiddenProviderIds = @($forbiddenPolicy.forbidden_mcp_ids | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() })
$configuredProviderIds = @(
  [string]$policy.default_provider
  @($policy.provider_priority)
  @($policy.providers.PSObject.Properties.Name)
  @($policy.providers.PSObject.Properties | ForEach-Object { [string]$_.Value.fallback_provider })
) | ForEach-Object { $_.Trim().ToLowerInvariant() } | Select-Object -Unique

$checks += Assert-True ($policy.control_plane_owner -eq 'vco') 'VCO 仍是 BrowserOps 唯一控制面'
$checks += Assert-True ($policy.selection_policy.allow_second_orchestrator -eq $false) 'policy 明确禁止第二 orchestrator'
$checks += Assert-True ($policy.selection_policy.allow_provider_takeover -eq $false) 'policy 明确禁止 provider takeover'
$checks += Assert-True ($policy.selection_policy.allow_route_override -eq $false) 'policy 明确禁止 route override'
$checks += Assert-True (($policy.provider_priority -join ',') -eq 'api,browser-host-native,turix-cua,browser-use') 'provider 优先级顺序正确'
$checks += Assert-True (@($configuredProviderIds | Where-Object { $forbiddenProviderIds -contains $_ }).Count -eq 0) '活跃 provider 与 fallback 不包含 forbidden MCP id'
$checks += Assert-True ($policy.providers.'browser-use'.position -eq 'candidate_only') 'browser-use 被固定为 provider candidate'
$checks += Assert-True ($policy.providers.'browser-use'.takeover_forbidden -eq $true) 'browser-use 禁止 takeover'
$checks += Assert-True ($policy.providers.'browser-use'.confirm_required -eq $true) 'browser-use 默认受 confirm_required 偏置'
$checks += Assert-True ($policy.providers.'turix-cua'.confirm_required -eq $true) 'turix-cua 默认受 confirm_required 偏置'
$checks += Assert-True ($contractText.Contains('provider candidate，不是新 orchestrator')) 'contract 明确 browser-use 不是新 orchestrator'
$checks += Assert-True ($contractText.Contains('不得 takeover')) 'contract 明确保留 takeover 禁令'
$checks += Assert-True ($contractText.Contains('fallback_provider')) 'contract 明确保留 fallback_provider 字段'
$checks += Assert-True ($contractText.Contains('VCO 是唯一控制面。')) 'contract 明确保留单一控制面不变量'

$apiSample = Invoke-SuggestJson -ScriptPath $suggestPath -Task '通过 GraphQL 接口拉取结构化数据并导出 JSON'
$checks += Assert-True ($apiSample.provider -eq 'api') 'API 场景建议 api provider'
$checks += Assert-True ($apiSample.confirm_required -eq $false) '低风险 API 场景默认无需 confirm'

$hostNativeSample = Invoke-SuggestJson -ScriptPath $suggestPath -Task '登录后台后填写表单并点击提交按钮'
$checks += Assert-True ($hostNativeSample.provider -eq 'browser-host-native') '表单场景建议宿主原生浏览器能力'

$debugSample = Invoke-SuggestJson -ScriptPath $suggestPath -Task '需要调试 request header 和 console 报错'
$checks += Assert-True ($debugSample.provider -eq 'browser-host-native') '调试场景建议宿主原生浏览器能力'

$visualSample = Invoke-SuggestJson -ScriptPath $suggestPath -Task '根据屏幕视觉布局完成真实界面交互'
$checks += Assert-True ($visualSample.provider -eq 'turix-cua') '视觉 GUI 场景建议 turix-cua provider'
$checks += Assert-True ($visualSample.confirm_required -eq $true) '视觉 GUI 场景保持 confirm_required'

$browserUseSample = Invoke-SuggestJson -ScriptPath $suggestPath -Task '跨多个网站开放式浏览并收集研究线索'
$checks += Assert-True ($browserUseSample.provider -eq 'browser-use') '开放式浏览场景建议 browser-use provider candidate'
$checks += Assert-True ($browserUseSample.confirm_required -eq $true) 'browser-use 场景保持 confirm_required'
$checks += Assert-True (-not [string]::IsNullOrWhiteSpace($browserUseSample.reason)) '建议结果包含 reason'
$checks += Assert-True ($browserUseSample.PSObject.Properties.Name -contains 'confidence') '建议结果包含 confidence 字段'
$checks += Assert-True ($browserUseSample.PSObject.Properties.Name -contains 'fallback_provider') '建议结果包含 fallback_provider 字段'

foreach ($sample in @($apiSample, $hostNativeSample, $debugSample, $visualSample, $browserUseSample)) {
  $surfacedProviderIds = @(
    [string]$sample.provider
    [string]$sample.fallback_provider
    @($sample.considered | ForEach-Object { [string]$_.provider })
  ) | ForEach-Object { $_.Trim().ToLowerInvariant() } | Select-Object -Unique
  $checks += Assert-True (@($surfacedProviderIds | Where-Object { $forbiddenProviderIds -contains $_ }).Count -eq 0) '建议输出不包含 forbidden MCP id'
}

if ($checks -contains $false) {
  throw 'vibe-browserops-gate failed'
}

Write-Host '[PASS] BrowserOps provider 治理门禁通过' -ForegroundColor Green
