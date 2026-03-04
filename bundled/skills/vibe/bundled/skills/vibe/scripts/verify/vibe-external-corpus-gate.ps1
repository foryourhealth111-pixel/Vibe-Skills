param(
    [string]$CandidateSkillIndexPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\external-corpus\skill-keyword-index.candidate.json"),
    [string]$OutputDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "outputs\external-corpus"),
    [switch]$RunExistingSmoke,
    [switch]$FailOnSmokeError
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType
    )

    $routeScript = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path "scripts\router\resolve-pack-route.ps1"
    $json = & $routeScript -Prompt $Prompt -Grade $Grade -TaskType $TaskType
    return ($json | ConvertFrom-Json)
}

function Get-RouteMetrics {
    param(
        [string]$Label
    )

    $cases = @(
        [pscustomobject]@{ expected = "orchestration-core"; grade = "L"; task = "planning"; prompt = "Design a workflow orchestration strategy for multi-agent delivery" },
        [pscustomobject]@{ expected = "orchestration-core"; grade = "M"; task = "planning"; prompt = "Route this task and classify the execution path" },
        [pscustomobject]@{ expected = "code-quality"; grade = "M"; task = "review"; prompt = "Run code review and identify behavioral regressions" },
        [pscustomobject]@{ expected = "code-quality"; grade = "L"; task = "debug"; prompt = "Perform root cause investigation for this failing build" },
        [pscustomobject]@{ expected = "data-ml"; grade = "L"; task = "research"; prompt = "Train a machine learning model and evaluate feature engineering quality" },
        [pscustomobject]@{ expected = "data-ml"; grade = "M"; task = "coding"; prompt = "Build a sklearn pipeline with cross validation and SHAP analysis" },
        [pscustomobject]@{ expected = "bio-science"; grade = "L"; task = "research"; prompt = "Analyze single-cell sequencing data and marker genes with scanpy" },
        [pscustomobject]@{ expected = "docs-media"; grade = "M"; task = "coding"; prompt = "Process xlsx spreadsheets and export a docx and pdf report" },
        [pscustomobject]@{ expected = "integration-devops"; grade = "L"; task = "debug"; prompt = "Fix GitHub Actions CI failure and inspect deployment errors in Sentry" },
        [pscustomobject]@{ expected = "ai-llm"; grade = "M"; task = "research"; prompt = "Optimize prompt strategy for Responses API with embedding retrieval" },
        [pscustomobject]@{ expected = "research-design"; grade = "L"; task = "planning"; prompt = "Create hypothesis-driven experimental design and methodology plan" },
        [pscustomobject]@{ expected = "research-design"; grade = "L"; task = "research"; prompt = "Search literature and synthesize a scientific writing outline" }
    )

    $total = 0
    $correct = 0
    $fallback = 0
    $gapSum = 0.0
    $details = New-Object System.Collections.Generic.List[object]

    foreach ($case in $cases) {
        $route = Invoke-Route -Prompt $case.prompt -Grade $case.grade -TaskType $case.task
        $total++

        $selectedPack = [string]$route.selected.pack_id
        $isCorrect = $selectedPack -eq $case.expected
        if ($isCorrect) { $correct++ }
        if ($route.route_mode -eq "legacy_fallback") { $fallback++ }

        $score1 = if ($route.ranked.Count -gt 0) { [double]$route.ranked[0].score } else { 0.0 }
        $score2 = if ($route.ranked.Count -gt 1) { [double]$route.ranked[1].score } else { 0.0 }
        $gap = [Math]::Round($score1 - $score2, 4)
        $gapSum += $gap

        $details.Add([pscustomobject]@{
            prompt = $case.prompt
            expected_pack = $case.expected
            selected_pack = $selectedPack
            route_mode = [string]$route.route_mode
            correct = $isCorrect
            confidence = [double]$route.confidence
            route_gap = $gap
        })
    }

    $accuracy = if ($total -gt 0) { [Math]::Round($correct / $total, 4) } else { 0.0 }
    $fallbackRate = if ($total -gt 0) { [Math]::Round($fallback / $total, 4) } else { 0.0 }
    $avgGap = if ($total -gt 0) { [Math]::Round($gapSum / $total, 4) } else { 0.0 }

    return [pscustomobject]@{
        label = $Label
        total = $total
        correct = $correct
        accuracy = $accuracy
        fallback_count = $fallback
        fallback_rate = $fallbackRate
        avg_route_gap = $avgGap
        details = $details
    }
}

function Invoke-SmokeScript {
    param(
        [string]$ScriptPath,
        [string]$ShellPath
    )

    $outPath = Join-Path $env:TEMP ("vibe-smoke-" + [guid]::NewGuid().ToString("N") + ".out.txt")
    $errPath = Join-Path $env:TEMP ("vibe-smoke-" + [guid]::NewGuid().ToString("N") + ".err.txt")
    try {
        $proc = Start-Process -FilePath $ShellPath `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) `
            -PassThru -Wait -NoNewWindow `
            -RedirectStandardOutput $outPath `
            -RedirectStandardError $errPath

        $stderr = if (Test-Path -LiteralPath $errPath) { Get-Content -LiteralPath $errPath -Raw -Encoding UTF8 } else { "" }
        $stdout = if (Test-Path -LiteralPath $outPath) { Get-Content -LiteralPath $outPath -Raw -Encoding UTF8 } else { "" }

        if ($proc.ExitCode -eq 0) {
            return [pscustomobject]@{
                script = (Split-Path -Leaf $ScriptPath)
                success = $true
                error = $null
            }
        }

        $errorText = if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            ($stderr.Trim() -split "(\r?\n)") | Select-Object -Last 1
        } elseif (-not [string]::IsNullOrWhiteSpace($stdout)) {
            "exit=$($proc.ExitCode); tail=" + (($stdout.Trim() -split "(\r?\n)") | Select-Object -Last 1)
        } else {
            "exit=$($proc.ExitCode)"
        }

        return [pscustomobject]@{
            script = (Split-Path -Leaf $ScriptPath)
            success = $false
            error = $errorText
        }
    } catch {
        return [pscustomobject]@{
            script = (Split-Path -Leaf $ScriptPath)
            success = $false
            error = $_.Exception.Message
        }
    } finally {
        Remove-Item -LiteralPath $outPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $errPath -Force -ErrorAction SilentlyContinue
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$configSkillIndexPath = Join-Path $repoRoot "config\skill-keyword-index.json"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

if (-not (Test-Path -LiteralPath $configSkillIndexPath)) {
    throw "Config skill index not found: $configSkillIndexPath"
}

$backupPath = Join-Path $OutputDirectory "skill-keyword-index.backup.json"
$hadCandidate = Test-Path -LiteralPath $CandidateSkillIndexPath

$shellPath = if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    (Get-Command pwsh -ErrorAction SilentlyContinue).Source
} elseif (Get-Command powershell -ErrorAction SilentlyContinue) {
    (Get-Command powershell -ErrorAction SilentlyContinue).Source
} else {
    throw "No PowerShell host found for smoke execution."
}

$mutexName = "Global\VibeExternalCorpusGateSkillIndexLock"
$mutex = New-Object System.Threading.Mutex($false, $mutexName)
$lockTaken = $false

try {
    try {
        $lockTaken = $mutex.WaitOne([TimeSpan]::FromSeconds(90))
    } catch [System.Threading.AbandonedMutexException] {
        $lockTaken = $true
    }

    if (-not $lockTaken) {
        throw "Could not acquire external corpus gate lock within timeout."
    }

    Copy-Item -LiteralPath $configSkillIndexPath -Destination $backupPath -Force

    $baselineMetrics = Get-RouteMetrics -Label "baseline"
    $candidateMetrics = $null
    $smokeResults = @()
    $gatePassed = $true
    $gateReasons = New-Object System.Collections.Generic.List[string]

    if ($hadCandidate) {
        Copy-Item -LiteralPath $CandidateSkillIndexPath -Destination $configSkillIndexPath -Force
        $candidateMetrics = Get-RouteMetrics -Label "candidate"

        if ($candidateMetrics.accuracy -lt $baselineMetrics.accuracy) {
            $gatePassed = $false
            $gateReasons.Add("candidate accuracy dropped ($($candidateMetrics.accuracy) < $($baselineMetrics.accuracy))")
        }
        if ($candidateMetrics.fallback_rate -gt $baselineMetrics.fallback_rate) {
            $gatePassed = $false
            $gateReasons.Add("candidate fallback_rate increased ($($candidateMetrics.fallback_rate) > $($baselineMetrics.fallback_rate))")
        }
        if ($candidateMetrics.avg_route_gap -lt ($baselineMetrics.avg_route_gap - 0.01)) {
            $gatePassed = $false
            $gateReasons.Add("candidate avg_route_gap regressed beyond tolerance")
        }
    } else {
        $gateReasons.Add("candidate skill index not found, baseline-only mode")
    }

    if ($RunExistingSmoke) {
        $smokeScripts = @(
            (Join-Path $PSScriptRoot "vibe-routing-smoke.ps1")
            (Join-Path $PSScriptRoot "vibe-pack-routing-smoke.ps1")
            (Join-Path $PSScriptRoot "vibe-keyword-precision-audit.ps1")
        )
        foreach ($script in $smokeScripts) {
            if (-not (Test-Path -LiteralPath $script)) { continue }
            $result = Invoke-SmokeScript -ScriptPath $script -ShellPath $shellPath
            $smokeResults += $result
            if (-not $result.success) {
                $gateReasons.Add("smoke script failed: $($result.script)")
                if ($FailOnSmokeError) {
                    $gatePassed = $false
                }
            }
        }
    }
    Copy-Item -LiteralPath $backupPath -Destination $configSkillIndexPath -Force

    $output = [pscustomobject]@{
        version = 1
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        candidate_skill_index = if ($hadCandidate) { $CandidateSkillIndexPath } else { $null }
        baseline = $baselineMetrics
        candidate = $candidateMetrics
        run_existing_smoke = [bool]$RunExistingSmoke
        smoke_results = $smokeResults
        gate_passed = $gatePassed
        reasons = @($gateReasons)
    }

    $jsonPath = Join-Path $OutputDirectory "external-corpus-gate.json"
    $mdPath = Join-Path $OutputDirectory "external-corpus-gate.md"

    $output | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $md = New-Object System.Text.StringBuilder
    [void]$md.AppendLine("# External Corpus Gate Result")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("- Generated: $($output.generated_at)")
    [void]$md.AppendLine("- Gate passed: $($output.gate_passed)")
    [void]$md.AppendLine("- Fail on smoke error: $([bool]$FailOnSmokeError)")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Baseline")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("- Accuracy: $($baselineMetrics.accuracy)")
    [void]$md.AppendLine("- Fallback rate: $($baselineMetrics.fallback_rate)")
    [void]$md.AppendLine("- Avg route gap: $($baselineMetrics.avg_route_gap)")

    if ($candidateMetrics -ne $null) {
        [void]$md.AppendLine("")
        [void]$md.AppendLine("## Candidate")
        [void]$md.AppendLine("")
        [void]$md.AppendLine("- Accuracy: $($candidateMetrics.accuracy)")
        [void]$md.AppendLine("- Fallback rate: $($candidateMetrics.fallback_rate)")
        [void]$md.AppendLine("- Avg route gap: $($candidateMetrics.avg_route_gap)")
    }

    [void]$md.AppendLine("")
    [void]$md.AppendLine("## Reasons")
    [void]$md.AppendLine("")
    foreach ($reason in $output.reasons) {
        [void]$md.AppendLine("- $reason")
    }

    $md.ToString() | Set-Content -LiteralPath $mdPath -Encoding UTF8

    Write-Host "Gate JSON: $jsonPath"
    Write-Host "Gate Markdown: $mdPath"
    Write-Host "Gate passed: $($output.gate_passed)"

    if (-not $output.gate_passed) {
        exit 1
    }
} finally {
    if ($lockTaken -and $mutex) {
        $mutex.ReleaseMutex() | Out-Null
    }
    if ($mutex) {
        $mutex.Dispose()
    }
}

exit 0
