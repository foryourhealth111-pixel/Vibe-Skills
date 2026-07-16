param(
  [Parameter(Mandatory = $true)]
  [string]$Task,
  [switch]$AsJson
)

$ErrorActionPreference = 'Stop'

function Normalize-PathString {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $Path
  }

  $normalized = $Path -replace '^Microsoft\.PowerShell\.Core\\FileSystem::', ''
  $normalized = $normalized -replace '^\\\\\?\\', ''
  return $normalized
}

function Normalize-Text {
  param([string]$Text)
  if ($null -eq $Text) { return '' }
  return $Text.Trim().ToLowerInvariant()
}

function Test-AnyKeyword {
  param(
    [string]$Text,
    [string[]]$Keywords
  )

  foreach ($keyword in $Keywords) {
    if ($Text.Contains($keyword.ToLowerInvariant())) {
      return $true
    }
  }

  return $false
}

function Add-Score {
  param(
    [hashtable]$Scores,
    [string]$Provider,
    [double]$Delta
  )

  $Scores[$Provider] = [double]$Scores[$Provider] + [double]$Delta
}

function Add-Reason {
  param(
    [hashtable]$ReasonMap,
    [string]$Provider,
    [string]$Reason
  )

  if ([string]::IsNullOrWhiteSpace($Reason)) {
    return
  }

  if ($ReasonMap[$Provider] -notcontains $Reason) {
    $ReasonMap[$Provider] += $Reason
  }
}

function Join-UniqueReasons {
  param([object[]]$Reasons)

  if ($null -eq $Reasons) {
    return ''
  }

  $filtered = @($Reasons | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
  return ($filtered -join '；')
}

$scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Definition }
$scriptPath = Normalize-PathString -Path $scriptPath
$scriptDirectory = Split-Path -Parent $scriptPath
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDirectory '..\..'))
$policyPath = Join-Path $repoRoot 'config\browserops-provider-policy.json'
$forbiddenPolicyPath = Join-Path $repoRoot 'config\forbidden-mcp-policy.json'
$policy = Get-Content -Raw $policyPath -Encoding UTF8 | ConvertFrom-Json
$forbiddenPolicy = Get-Content -Raw $forbiddenPolicyPath -Encoding UTF8 | ConvertFrom-Json
$forbiddenProviderIds = @($forbiddenPolicy.forbidden_mcp_ids | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() })
$configuredProviderIds = @(
  [string]$policy.default_provider
  @($policy.provider_priority)
  @($policy.providers.PSObject.Properties.Name)
  @($policy.providers.PSObject.Properties | ForEach-Object { [string]$_.Value.fallback_provider })
) | ForEach-Object { $_.Trim().ToLowerInvariant() } | Select-Object -Unique
$blockedProviderIds = @($configuredProviderIds | Where-Object { $forbiddenProviderIds -contains $_ })
if ($blockedProviderIds.Count -gt 0) {
  throw ("BrowserOps policy contains forbidden MCP provider ids: {0}" -f ($blockedProviderIds -join ', '))
}
$text = Normalize-Text -Text $Task

$scores = @{
  'api' = 0.0
  'browser-host-native' = 0.0
  'turix-cua' = 0.0
  'browser-use' = 0.0
}

$reasons = @{
  'api' = @()
  'browser-host-native' = @()
  'turix-cua' = @()
  'browser-use' = @()
}

$signalMap = @{
  'api' = @('api', 'rest', 'graphql', 'endpoint', 'http', 'json', '接口', '结构化接口', '结构化数据', '服务调用', '拉取数据')
  'browser-host-native' = @('login', 'form', 'submit', 'click', 'button', 'navigate', 'dom', 'download', 'upload', 'network', 'console', 'performance', 'request', 'response', 'header', 'cookie', 'waterfall', '登录', '表单', '提交', '点击', '按钮', '页面元素', '抓取页面', '调试', '控制台', '性能', '请求', '响应', '报错')
  'turix-cua' = @('visual', 'gui', 'screen', 'desktop', 'computer use', '真实界面', '视觉', '屏幕', '桌面', '弱结构')
  'browser-use' = @('browse', 'browser agent', 'research navigation', 'open web', 'crawl', '多步浏览', '开放式浏览', '探索网页', '跨网站', '网页研究', 'research')
}

foreach ($provider in $policy.provider_priority) {
  if (Test-AnyKeyword -Text $text -Keywords $signalMap[$provider]) {
    Add-Score -Scores $scores -Provider $provider -Delta 1.0
    switch ($provider) {
      'api' { Add-Reason -ReasonMap $reasons -Provider $provider -Reason '命中结构化接口信号，符合 API-first 原则' }
      'browser-host-native' { Add-Reason -ReasonMap $reasons -Provider $provider -Reason '命中浏览器交互或诊断信号，使用宿主已允许的原生浏览器能力' }
      'turix-cua' { Add-Reason -ReasonMap $reasons -Provider $provider -Reason '命中视觉与真实界面信号，适合 GUI/弱结构页面' }
      'browser-use' { Add-Reason -ReasonMap $reasons -Provider $provider -Reason '命中开放式浏览与多步导航信号，适合作为候选 provider' }
    }
  }
}

if (Test-AnyKeyword -Text $text -Keywords @('request', 'response', 'network', 'console', 'header', '调试', '报错', '控制台')) {
  Add-Score -Scores $scores -Provider 'browser-host-native' -Delta 1.2
  Add-Reason -ReasonMap $reasons -Provider 'browser-host-native' -Reason '调试信号强，使用宿主原生诊断能力'
}

if (Test-AnyKeyword -Text $text -Keywords @('登录', '表单', '提交', '点击', 'button', 'dom', '下载', '上传')) {
  Add-Score -Scores $scores -Provider 'browser-host-native' -Delta 1.1
  Add-Reason -ReasonMap $reasons -Provider 'browser-host-native' -Reason '任务具备明确浏览器动作，优先使用宿主原生能力'
}

if (Test-AnyKeyword -Text $text -Keywords @('跨网站', '多步浏览', '开放式浏览', '探索网页', 'research navigation', 'crawl', 'research')) {
  Add-Score -Scores $scores -Provider 'browser-use' -Delta 1.35
  Add-Reason -ReasonMap $reasons -Provider 'browser-use' -Reason '任务属于跨站或开放式导航，browser-use 只作为 provider candidate 进入建议层'
}

if (Test-AnyKeyword -Text $text -Keywords @('视觉', '真实界面', '屏幕', 'gui', '弱结构', '桌面')) {
  Add-Score -Scores $scores -Provider 'turix-cua' -Delta 1.2
  Add-Reason -ReasonMap $reasons -Provider 'turix-cua' -Reason '任务依赖视觉布局，需维持 confirm_required 偏置'
}

if ($scores['api'] -gt 0) {
  Add-Reason -ReasonMap $reasons -Provider 'browser-host-native' -Reason '如 API 路径不可用，可回退到宿主原生浏览器能力'
}

if (($scores['browser-use'] -gt 0) -and (Test-AnyKeyword -Text $text -Keywords @('表单', '提交', '点击', 'dom', '结构化', 'api'))) {
  Add-Score -Scores $scores -Provider 'browser-use' -Delta -0.35
  Add-Reason -ReasonMap $reasons -Provider 'browser-use' -Reason '任务同时具备更确定的脚本化或接口路径，不允许 browser-use 抢占执行面'
}

$priorityIndex = @{}
for ($index = 0; $index -lt $policy.provider_priority.Count; $index++) {
  $priorityIndex[$policy.provider_priority[$index]] = $index
}

$ordered = @(
  $scores.GetEnumerator() |
    Sort-Object -Property @{ Expression = { $_.Value }; Descending = $true }, @{ Expression = { $priorityIndex[$_.Key] }; Descending = $false }
)

$selectedProvider = $ordered[0].Key
$topScore = [double]$ordered[0].Value
$runnerUpScore = 0.0
if ($ordered.Count -gt 1) {
  $runnerUpScore = [double]$ordered[1].Value
}

if ($topScore -le 0) {
  $selectedProvider = $policy.default_provider
  $topScore = 0.55
  Add-Reason -ReasonMap $reasons -Provider $selectedProvider -Reason '未命中强信号，按 policy 回退到默认 provider'
}

$selectedConfig = $policy.providers.PSObject.Properties[$selectedProvider].Value
$fallbackProvider = [string]$selectedConfig.fallback_provider
$gap = [Math]::Max(0.0, $topScore - $runnerUpScore)
$confidence = [Math]::Round([Math]::Min(0.96, 0.54 + [Math]::Min(0.24, $topScore * 0.09) + [Math]::Min(0.14, $gap * 0.10)), 2)

$riskyKeywordHit = Test-AnyKeyword -Text $text -Keywords @($policy.high_risk_keywords)
$confirmRequired = [bool]$selectedConfig.confirm_required
if ($riskyKeywordHit -or $gap -lt 0.25) {
  $confirmRequired = $true
}

if ($selectedProvider -eq 'browser-use') {
  Add-Reason -ReasonMap $reasons -Provider $selectedProvider -Reason 'browser-use 在 VCO 中不是新 orchestrator，只能以 advice/shadow-first 方式提出建议'
}

if ($selectedProvider -eq 'turix-cua') {
  Add-Reason -ReasonMap $reasons -Provider $selectedProvider -Reason 'turix-cua 属于视觉候选路径，必须保留宿主原生回退'
}

if ($confirmRequired) {
  Add-Reason -ReasonMap $reasons -Provider $selectedProvider -Reason '当前任务满足 confirm_required 条件，建议先确认再执行'
}

$considered = @(
  foreach ($provider in $policy.provider_priority) {
    [pscustomobject]@{
      provider = $provider
      score = [Math]::Round([double]$scores[$provider], 2)
    }
  }
) | Sort-Object -Property @{ Expression = { $_.score }; Descending = $true }, @{ Expression = { $priorityIndex[$_.provider] }; Descending = $false }

$result = [pscustomobject]@{
  task = $Task
  provider = $selectedProvider
  reason = (Join-UniqueReasons -Reasons $reasons[$selectedProvider])
  confidence = $confidence
  confirm_required = [bool]$confirmRequired
  fallback_provider = $fallbackProvider
  mode = [string]$policy.mode
  control_plane_owner = [string]$policy.control_plane_owner
  considered = $considered
}

if ($AsJson) {
  $result | ConvertTo-Json -Depth 6
  exit 0
}

Write-Host 'BrowserOps provider 建议结果'
Write-Host "- provider: $($result.provider)"
Write-Host "- confidence: $($result.confidence)"
Write-Host "- confirm_required: $($result.confirm_required)"
Write-Host "- fallback_provider: $($result.fallback_provider)"
Write-Host "- reason: $($result.reason)"
Write-Host "- mode: $($result.mode)"
