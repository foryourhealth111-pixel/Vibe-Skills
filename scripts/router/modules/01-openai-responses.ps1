# OpenAI Responses API client helpers (advice-only integrations).

$script:OpenAiDefaultBaseUrl = "https://api.openai.com/v1"

function Get-OpenAiBaseUrl {
    param(
        [string]$Override,
        [string[]]$EnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )

    if ($Override) { return $Override.TrimEnd("/") }
    foreach ($candidate in @($EnvCandidates)) {
        if (-not $candidate) { continue }
        $value = [Environment]::GetEnvironmentVariable([string]$candidate)
        if ($value) { return ([string]$value).TrimEnd("/") }
    }
    return $script:OpenAiDefaultBaseUrl
}

function Get-OpenAiV1BaseUrl {
    param(
        [string]$Override,
        [string[]]$EnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )

    $base = Get-OpenAiBaseUrl -Override $Override -EnvCandidates $EnvCandidates
    if (-not $base) { return $base }

    $trim = ([string]$base).TrimEnd("/")
    if ($trim -match "(/v1)(/|$)") { return $trim }
    return ("{0}/v1" -f $trim)
}

function Get-AnthropicMessagesBaseUrl {
    param(
        [string]$Override,
        [string[]]$EnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )

    return (Get-OpenAiV1BaseUrl -Override $Override -EnvCandidates $EnvCandidates)
}

function Get-OpenAiApiKey {
    param([string]$EnvName = "VCO_INTENT_ADVICE_API_KEY")
    if ($EnvName) {
        $value = [Environment]::GetEnvironmentVariable([string]$EnvName)
        if ($value) { return [string]$value }
    }
    return $null
}

function Get-OpenAiResponsesEndpoint {
    param(
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )
    $base = Get-OpenAiV1BaseUrl -Override $BaseUrl -EnvCandidates $BaseUrlEnvCandidates
    return ("{0}/responses" -f $base)
}

function Get-OpenAiChatCompletionsEndpoint {
    param(
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )
    $base = Get-OpenAiV1BaseUrl -Override $BaseUrl -EnvCandidates $BaseUrlEnvCandidates
    return ("{0}/chat/completions" -f $base)
}

function Get-OpenAiEmbeddingsEndpoint {
    param(
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_VECTOR_DIFF_BASE_URL")
    )
    $base = Get-OpenAiV1BaseUrl -Override $BaseUrl -EnvCandidates $BaseUrlEnvCandidates
    return ("{0}/embeddings" -f $base)
}

function Get-AnthropicMessagesEndpoint {
    param(
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )

    $base = Get-AnthropicMessagesBaseUrl -Override $BaseUrl -EnvCandidates $BaseUrlEnvCandidates
    return ("{0}/messages" -f $base)
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

function ConvertFrom-OpenAiEventStreamDataObjects {
    param([string]$EventStreamText)

    if (-not $EventStreamText) { return @() }

    $items = @()
    foreach ($line in ($EventStreamText -split "`n")) {
        $trim = ([string]$line).Trim()
        if (-not $trim.StartsWith("data:")) { continue }

        $payload = $trim.Substring(5).Trim()
        if (-not $payload -or $payload -eq "[DONE]") { continue }

        try {
            $obj = ($payload | ConvertFrom-Json)
            if ($obj) { $items += $obj }
        } catch { }
    }

    return @($items)
}

function Get-OpenAiResponseFromEventStreamText {
    param([string]$EventStreamText)

    if (-not $EventStreamText) { return $null }

    $events = @(ConvertFrom-OpenAiEventStreamDataObjects -EventStreamText $EventStreamText)
    if ($events.Count -eq 0) { return $null }

    $withResponse = @($events | Where-Object { $_ -and $_.response })
    if ($withResponse.Count -eq 0) { return $null }

    $completed = @($withResponse | Where-Object { $_.type -eq "response.completed" -or ($_.response -and $_.response.status -eq "completed") })
    if ($completed.Count -gt 0) { return $completed[-1].response }

    return $withResponse[-1].response
}

function Get-OpenAiChatCompletionOutputText {
    param([object]$Response)

    if (-not $Response) { return $null }

    try {
        $choices = @($Response.choices)
        if ($choices.Count -eq 0) { return $null }
        $msg = $choices[0].message
        if ($msg -and $msg.content) { return ([string]$msg.content).Trim() }
    } catch { }

    return $null
}

function Get-AnthropicMessageOutputText {
    param([object]$Response)

    if (-not $Response) { return $null }

    try {
        $content = @($Response.content)
        if ($content.Count -eq 0) { return $null }

        $parts = @()
        foreach ($block in $content) {
            if (-not $block) { continue }
            if ($block.type -ne "text") { continue }
            if ($block.text) { $parts += [string]$block.text }
        }

        if ($parts.Count -eq 0) { return $null }
        return ($parts -join "`n").Trim()
    } catch {
        return $null
    }
}

function Get-OpenAiEmbeddingsOutputVectors {
    param([object]$Response)

    if (-not $Response) { return @() }

    try {
        $data = @($Response.data)
        if ($data.Count -eq 0) { return @() }

        $hasIndex = $true
        try {
            $null = $data[0].index
        } catch {
            $hasIndex = $false
        }

        $rows = if ($hasIndex) { @($data | Sort-Object -Property index) } else { @($data) }

        $vectors = @()
        foreach ($row in $rows) {
            if (-not $row) { continue }
            if ($row.embedding) {
                $vectors += ,@($row.embedding)
            }
        }

        if ($vectors.Count -eq 0) { return @() }
        return ,$vectors
    } catch {
        return @()
    }
}

function Invoke-OpenAiResponsesCreate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Model,
        [Parameter(Mandatory = $true)]
        [object]$InputItems,
        [Parameter(Mandatory = $true)]
        [object]$TextFormat,
        [string]$Instructions = "",
        [int]$MaxOutputTokens = 800,
        [double]$Temperature = 0.2,
        [double]$TopP = 1.0,
        [int]$TimeoutMs = 2500,
        [string]$ApiKey,
        [string]$ApiKeyEnv = "VCO_INTENT_ADVICE_API_KEY",
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL"),
        [switch]$Store
    )

    $resolvedApiKey = if ($ApiKey) { $ApiKey } else { Get-OpenAiApiKey -EnvName $ApiKeyEnv }
    if (-not $resolvedApiKey) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_intent_advice_api_key"
            status_code = $null
            latency_ms = 0
            output_text = $null
            response = $null
            error = $null
        }
    }

    $endpoint = Get-OpenAiResponsesEndpoint -BaseUrl $BaseUrl -BaseUrlEnvCandidates $BaseUrlEnvCandidates
    $timeoutSec = [Math]::Max(1, [int][Math]::Ceiling([double]$TimeoutMs / 1000.0))

    $body = [ordered]@{
        model = $Model
        input = $InputItems
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

        $respObj = $resp
        try {
            if ($respObj -is [string]) {
                $s = [string]$respObj
                $parsed = $null
                try { $parsed = ($s | ConvertFrom-Json) } catch { }
                if (-not $parsed -and ($s -match "(^|`n)event:\s" -or $s -match "(^|`n)data:\s")) {
                    $candidate = Get-OpenAiResponseFromEventStreamText -EventStreamText $s
                    if ($candidate) { $parsed = $candidate }
                }
                if ($parsed) { $respObj = $parsed }
            }
        } catch { }

        $outputText = Get-OpenAiResponseOutputText -Response $respObj
        return [pscustomobject]@{
            ok = $true
            abstained = $false
            reason = "ok"
            status_code = 200
            latency_ms = [int]$sw.ElapsedMilliseconds
            output_text = $outputText
            response = $respObj
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

function Invoke-OpenAiChatCompletionsCreate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Model,
        [Parameter(Mandatory = $true)]
        [object[]]$Messages,
        [object]$ResponseFormat,
        [int]$MaxTokens = 800,
        [double]$Temperature = 0.2,
        [double]$TopP = 1.0,
        [int]$TimeoutMs = 2500,
        [string]$ApiKey,
        [string]$ApiKeyEnv = "VCO_INTENT_ADVICE_API_KEY",
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL")
    )

    $resolvedApiKey = if ($ApiKey) { $ApiKey } else { Get-OpenAiApiKey -EnvName $ApiKeyEnv }
    if (-not $resolvedApiKey) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_intent_advice_api_key"
            status_code = $null
            latency_ms = 0
            output_text = $null
            response = $null
            error = $null
        }
    }

    $endpoint = Get-OpenAiChatCompletionsEndpoint -BaseUrl $BaseUrl -BaseUrlEnvCandidates $BaseUrlEnvCandidates
    $timeoutSec = [Math]::Max(1, [int][Math]::Ceiling([double]$TimeoutMs / 1000.0))

    $body = [ordered]@{
        model = $Model
        messages = @($Messages)
        max_tokens = [int]$MaxTokens
        temperature = [double]$Temperature
        top_p = [double]$TopP
        stream = $false
    }

    if ($ResponseFormat) {
        $body.response_format = $ResponseFormat
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
        $outputText = Get-OpenAiChatCompletionOutputText -Response $resp
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

function Invoke-OpenAiEmbeddingsCreate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Model,
        [Parameter(Mandatory = $true)]
        [object]$InputItems,
        [int]$TimeoutMs = 2500,
        [string]$ApiKey,
        [string]$ApiKeyEnv = "VCO_VECTOR_DIFF_API_KEY",
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_VECTOR_DIFF_BASE_URL")
    )

    $resolvedApiKey = if ($ApiKey) { $ApiKey } else { Get-OpenAiApiKey -EnvName $ApiKeyEnv }
    if (-not $resolvedApiKey) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_vector_diff_api_key"
            status_code = $null
            latency_ms = 0
            vectors = @()
            response = $null
            error = $null
        }
    }

    $endpoint = Get-OpenAiEmbeddingsEndpoint -BaseUrl $BaseUrl -BaseUrlEnvCandidates $BaseUrlEnvCandidates
    $timeoutSec = [Math]::Max(1, [int][Math]::Ceiling([double]$TimeoutMs / 1000.0))

    $body = [ordered]@{
        model = $Model
        input = $InputItems
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
        $vectors = Get-OpenAiEmbeddingsOutputVectors -Response $resp
        return [pscustomobject]@{
            ok = $true
            abstained = $false
            reason = "ok"
            status_code = 200
            latency_ms = [int]$sw.ElapsedMilliseconds
            vectors = @($vectors)
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
            vectors = @()
            response = $null
            error = $message
        }
    }
}

function Invoke-AnthropicMessagesCreate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Model,
        [Parameter(Mandatory = $true)]
        [object[]]$Messages,
        [string]$System = "",
        [int]$MaxTokens = 800,
        [double]$Temperature = 0.2,
        [double]$TopP = 1.0,
        [int]$TimeoutMs = 2500,
        [string]$ApiKey,
        [string]$ApiKeyEnv = "VCO_INTENT_ADVICE_API_KEY",
        [string]$BaseUrl,
        [string[]]$BaseUrlEnvCandidates = @("VCO_INTENT_ADVICE_BASE_URL"),
        [string]$AnthropicVersion = "2023-06-01"
    )

    $resolvedApiKey = if ($ApiKey) { $ApiKey } else { Get-OpenAiApiKey -EnvName $ApiKeyEnv }
    if (-not $resolvedApiKey) {
        return [pscustomobject]@{
            ok = $false
            abstained = $true
            reason = "missing_intent_advice_api_key"
            status_code = $null
            latency_ms = 0
            output_text = $null
            response = $null
            error = $null
        }
    }

    $endpoint = Get-AnthropicMessagesEndpoint -BaseUrl $BaseUrl -BaseUrlEnvCandidates $BaseUrlEnvCandidates
    $timeoutSec = [Math]::Max(1, [int][Math]::Ceiling([double]$TimeoutMs / 1000.0))

    $body = [ordered]@{
        model = $Model
        max_tokens = [int]$MaxTokens
        temperature = [double]$Temperature
        messages = @($Messages)
    }
    if ($TopP -gt 0.0) {
        $body.top_p = [double]$TopP
    }
    if ($System) {
        $body.system = [string]$System
    }

    $json = ($body | ConvertTo-Json -Depth 20 -Compress)
    $headers = @{
        "x-api-key" = [string]$resolvedApiKey
        "anthropic-version" = if ($AnthropicVersion) { [string]$AnthropicVersion } else { "2023-06-01" }
        "Content-Type" = "application/json"
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri $endpoint -Method Post -Headers $headers -Body $json -TimeoutSec $timeoutSec
        $sw.Stop()
        $outputText = Get-AnthropicMessageOutputText -Response $resp
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
            reason = "anthropic_http_error"
            status_code = $status
            latency_ms = [int]$sw.ElapsedMilliseconds
            output_text = $null
            response = $null
            error = $message
        }
    }
}
