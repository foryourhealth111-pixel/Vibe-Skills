# OpenAI Responses API client helpers (advice-only integrations).

$script:OpenAiDefaultBaseUrl = "https://api.openai.com/v1"

function Get-OpenAiBaseUrl {
    param([string]$Override)

    if ($Override) { return $Override.TrimEnd("/") }
    if ($env:OPENAI_BASE_URL) { return ([string]$env:OPENAI_BASE_URL).TrimEnd("/") }
    if ($env:OPENAI_API_BASE) { return ([string]$env:OPENAI_API_BASE).TrimEnd("/") }
    return $script:OpenAiDefaultBaseUrl
}

function Get-OpenAiApiKey {
    if ($env:OPENAI_API_KEY) { return [string]$env:OPENAI_API_KEY }
    return $null
}

function Get-OpenAiResponsesEndpoint {
    param([string]$BaseUrl)
    $base = Get-OpenAiBaseUrl -Override $BaseUrl
    return ("{0}/responses" -f $base)
}

function Get-OpenAiResponseOutputText {
    param([object]$Response)

    if (-not $Response) { return $null }
    $keys = @($Response.PSObject.Properties.Name)
    if ($keys -contains "output_text" -and $Response.output_text) {
        return [string]$Response.output_text
    }

    if (-not ($keys -contains "output")) { return $null }
    $outputItems = @($Response.output)
    if ($outputItems.Count -eq 0) { return $null }

    $parts = @()
    foreach ($item in $outputItems) {
        if (-not $item) { continue }
        if ($item.type -ne "message") { continue }
        $content = @($item.content)
        foreach ($c in $content) {
            if (-not $c) { continue }
            if ($c.type -ne "output_text") { continue }
            if ($c.text) { $parts += [string]$c.text }
        }
    }

    if ($parts.Count -eq 0) { return $null }
    return ($parts -join "`n").Trim()
}

function Invoke-OpenAiResponsesCreate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Model,
        [Parameter(Mandatory = $true)]
        [object]$Input,
        [Parameter(Mandatory = $true)]
        [object]$TextFormat,
        [string]$Instructions = "",
        [int]$MaxOutputTokens = 800,
        [double]$Temperature = 0.2,
        [double]$TopP = 1.0,
        [int]$TimeoutMs = 2500,
        [string]$ApiKey,
        [string]$BaseUrl,
        [switch]$Store
    )

    $resolvedApiKey = if ($ApiKey) { $ApiKey } else { Get-OpenAiApiKey }
    if (-not $resolvedApiKey) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_openai_api_key"
            status_code = $null
            latency_ms = 0
            output_text = $null
            response = $null
            error = $null
        }
    }

    $endpoint = Get-OpenAiResponsesEndpoint -BaseUrl $BaseUrl
    $timeoutSec = [Math]::Max(1, [int][Math]::Ceiling([double]$TimeoutMs / 1000.0))

    $body = [ordered]@{
        model = $Model
        input = $Input
        text = [ordered]@{
            format = $TextFormat
        }
        max_output_tokens = [int]$MaxOutputTokens
        temperature = [double]$Temperature
        top_p = [double]$TopP
        tool_choice = "none"
        tools = @()
        store = [bool]$Store
    }
    if ($Instructions) {
        $body.instructions = [string]$Instructions
    }

    $json = ($body | ConvertTo-Json -Depth 20 -Compress)

    $headers = @{
        "Authorization" = ("Bearer {0}" -f $resolvedApiKey)
        "Content-Type"  = "application/json"
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri $endpoint -Method Post -Headers $headers -Body $json -TimeoutSec $timeoutSec
        $sw.Stop()
        $outputText = Get-OpenAiResponseOutputText -Response $resp
        return [pscustomobject]@{
            ok = $true
            abstained = $false
            reason = "ok"
            status_code = 200
            latency_ms = [int]$sw.ElapsedMilliseconds
            output_text = $outputText
            response = $resp
            error = $null
        }
    } catch {
        $sw.Stop()
        $message = $_.Exception.Message
        $status = $null
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $status = [int]$_.Exception.Response.StatusCode
            }
        } catch { }

        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "openai_http_error"
            status_code = $status
            latency_ms = [int]$sw.ElapsedMilliseconds
            output_text = $null
            response = $null
            error = $message
        }
    }
}

