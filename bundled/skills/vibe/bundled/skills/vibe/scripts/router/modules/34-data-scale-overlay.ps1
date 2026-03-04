# Auto-extracted router module. Keep function bodies behavior-identical.

function Get-PathCandidatesFromPrompt {
    param(
        [string]$Prompt,
        [string[]]$SupportedExtensions
    )

    $paths = @()
    if (-not $Prompt -or -not $SupportedExtensions -or $SupportedExtensions.Count -eq 0) {
        return @()
    }

    $escapedExt = @($SupportedExtensions | ForEach-Object { [Regex]::Escape(([string]$_).ToLowerInvariant()) } | Sort-Object -Unique)
    if ($escapedExt.Count -eq 0) {
        return @()
    }

    $extPattern = ($escapedExt | Sort-Object { $_.Length } -Descending) -join "|"
    $regexes = @(
        [Regex]::new('"([^"]+\.(?:' + $extPattern + '))"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase),
        [Regex]::new("'([^']+\.(?:$extPattern))'", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase),
        [Regex]::new('([^\s"'';,()]+?\.(?:' + $extPattern + '))', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    )

    foreach ($regex in $regexes) {
        $matches = $regex.Matches($Prompt)
        foreach ($m in $matches) {
            if ($m.Groups.Count -lt 2) { continue }
            $candidate = [string]$m.Groups[1].Value
            if (-not $candidate) { continue }
            $normalized = $candidate.Trim().Trim('"', "'").TrimEnd('.', ',', ';', ')', ']')
            if ($normalized) {
                $paths += $normalized
            }
        }
    }

    return @($paths | Select-Object -Unique)
}

function Resolve-ExistingPathCandidates {
    param(
        [string[]]$PathCandidates,
        [bool]$WorkspaceProbeEnabled,
        [int]$WorkspaceProbeLimit,
        [string[]]$WorkspaceProbeExtensions
    )

    $resolvedPaths = @()
    $cwd = (Get-Location).Path

    foreach ($candidate in @($PathCandidates)) {
        $raw = [Environment]::ExpandEnvironmentVariables([string]$candidate)
        if (-not $raw) { continue }

        $tries = @()
        if ([System.IO.Path]::IsPathRooted($raw)) {
            $tries += $raw
        } else {
            $tries += (Join-Path -Path $cwd -ChildPath $raw)
            $tries += $raw
        }

        foreach ($tryPath in $tries) {
            if (-not $tryPath) { continue }
            if (Test-Path -LiteralPath $tryPath -PathType Leaf) {
                $resolved = (Resolve-Path -LiteralPath $tryPath -ErrorAction SilentlyContinue).Path
                if ($resolved) {
                    $resolvedPaths += $resolved
                    break
                }
            }
        }
    }

    if ($resolvedPaths.Count -eq 0 -and $WorkspaceProbeEnabled) {
        $limit = if ($WorkspaceProbeLimit -gt 0) { $WorkspaceProbeLimit } else { 3 }
        $probeExt = @($WorkspaceProbeExtensions | ForEach-Object { [string]$_ } | Where-Object { $_ })
        if ($probeExt.Count -gt 0) {
            foreach ($ext in $probeExt) {
                $pattern = "*.$ext"
                $hits = Get-ChildItem -Path $cwd -File -Filter $pattern -ErrorAction SilentlyContinue | Select-Object -First $limit
                foreach ($h in $hits) {
                    if ($h -and $h.FullName) {
                        $resolvedPaths += [string]$h.FullName
                    }
                }
                if ($resolvedPaths.Count -ge $limit) { break }
            }
        }
    }

    return @($resolvedPaths | Select-Object -Unique)
}

function Get-DetectedExtension {
    param(
        [string]$Path,
        [string[]]$SupportedExtensions
    )

    $name = [System.IO.Path]::GetFileName([string]$Path).ToLowerInvariant()
    foreach ($ext in @($SupportedExtensions | Sort-Object { $_.Length } -Descending)) {
        $needle = "." + ([string]$ext).ToLowerInvariant()
        if ($name.EndsWith($needle)) {
            return ([string]$ext).ToLowerInvariant()
        }
    }

    return [System.IO.Path]::GetExtension($name).TrimStart('.').ToLowerInvariant()
}

function Test-WorkbookExtension {
    param([string]$Extension)
    return ($Extension -in @("xlsx", "xlsm", "xls"))
}

function Test-CsvLikeExtension {
    param([string]$Extension)
    return ($Extension -in @(
            "csv", "tsv", "tab", "psv", "ssv", "scsv",
            "csv.gz", "tsv.gz", "tab.gz", "psv.gz", "ssv.gz", "scsv.gz",
            "csv.zst", "tsv.zst", "tab.zst"
        ))
}

function Get-DelimiterHint {
    param(
        [string]$Extension,
        [string]$HeaderLine
    )

    if ($Extension -match "^(tsv|tab)(\.|$)") { return "`t" }
    if ($Extension -match "^psv(\.|$)") { return "|" }
    if ($Extension -match "^(ssv|scsv)(\.|$)") { return ";" }

    $candidates = @(",", ";", "`t", "|")
    $best = ","
    $bestCount = -1
    foreach ($d in $candidates) {
        $count = ([string]$HeaderLine).Split($d).Count
        if ($count -gt $bestCount) {
            $best = $d
            $bestCount = $count
        }
    }

    return $best
}

function Get-DelimitedFileSampleStats {
    param(
        [string]$Path,
        [string]$Extension,
        [int64]$FileSizeBytes,
        [int]$MaxLines,
        [int]$MaxChars
    )

    $result = [ordered]@{
        columns = $null
        delimiter = $null
        sample_rows = 0
        sample_bytes = 0
        estimated_rows = $null
    }

    if ($Extension -match "\.(gz|zst)$") {
        return [pscustomobject]$result
    }

    $lineCap = if ($MaxLines -gt 0) { $MaxLines } else { 200 }
    $charCap = if ($MaxChars -gt 0) { $MaxChars } else { 200000 }

    $rawLines = @()
    try {
        $rawLines = @(Get-Content -LiteralPath $Path -TotalCount $lineCap -Encoding UTF8 -ErrorAction Stop)
    } catch {
        return [pscustomobject]$result
    }

    if ($rawLines.Count -eq 0) {
        return [pscustomobject]$result
    }

    $lines = @()
    $chars = 0
    foreach ($line in $rawLines) {
        $text = [string]$line
        if (($chars + $text.Length + 1) -gt $charCap -and $lines.Count -gt 0) {
            break
        }
        $lines += $text
        $chars += ($text.Length + 1)
    }

    if ($lines.Count -eq 0) {
        return [pscustomobject]$result
    }

    $header = [string]$lines[0]
    $delimiter = Get-DelimiterHint -Extension $Extension -HeaderLine $header
    $splitPattern = [Regex]::Escape($delimiter)
    $columns = if ($header.Length -gt 0) { ([Regex]::Split($header, $splitPattern, [System.Text.RegularExpressions.RegexOptions]::None)).Count } else { 0 }
    $sampleRows = [Math]::Max(0, $lines.Count - 1)

    $sampleText = $lines -join "`n"
    $sampleBytes = [System.Text.Encoding]::UTF8.GetByteCount($sampleText)
    $estimatedRows = $null
    if ($sampleRows -gt 0 -and $sampleBytes -gt 0 -and $FileSizeBytes -gt 0) {
        $estimatedRows = [int64][Math]::Round(([double]$FileSizeBytes / [double]$sampleBytes) * [double]$sampleRows, 0)
    }

    $result.columns = $columns
    $result.delimiter = $delimiter
    $result.sample_rows = $sampleRows
    $result.sample_bytes = $sampleBytes
    $result.estimated_rows = $estimatedRows
    return [pscustomobject]$result
}

function Get-DataScaleOverlayAdvice {
    param(
        [string]$Prompt,
        [string]$PromptLower,
        [string]$Grade,
        [string]$TaskType,
        [string]$RouteMode,
        [string]$SelectedPackId,
        [string]$SelectedSkill,
        [string[]]$PackCandidates,
        [object]$DataScaleOverlayPolicy
    )

    if (-not $DataScaleOverlayPolicy) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_missing"
            preserve_routing_assignment = $true
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $enabled = $true
    if ($DataScaleOverlayPolicy.enabled -ne $null) {
        $enabled = [bool]$DataScaleOverlayPolicy.enabled
    }
    $mode = if ($DataScaleOverlayPolicy.mode) { [string]$DataScaleOverlayPolicy.mode } else { "off" }
    if ((-not $enabled) -or ($mode -eq "off")) {
        return [pscustomobject]@{
            enabled = $false
            mode = "off"
            task_applicable = $false
            grade_applicable = $false
            pack_applicable = $false
            skill_applicable = $false
            scope_applicable = $false
            enforcement = "none"
            reason = "policy_off"
            preserve_routing_assignment = $true
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $taskAllow = @("coding", "research")
    if ($DataScaleOverlayPolicy.task_allow) {
        $taskAllow = @($DataScaleOverlayPolicy.task_allow)
    }
    $gradeAllow = @("M", "L", "XL")
    if ($DataScaleOverlayPolicy.grade_allow) {
        $gradeAllow = @($DataScaleOverlayPolicy.grade_allow)
    }

    $packAllow = @()
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.pack_allow) {
        $packAllow = @($DataScaleOverlayPolicy.monitor.pack_allow)
    }
    $skillAllow = @()
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.skill_allow) {
        $skillAllow = @($DataScaleOverlayPolicy.monitor.skill_allow)
    }
    $supportedExt = @("csv", "tsv", "tab", "psv", "ssv", "scsv", "csv.gz", "tsv.gz", "tab.gz", "psv.gz", "ssv.gz", "scsv.gz", "csv.zst", "tsv.zst", "tab.zst", "xlsx", "xlsm", "xls")
    if ($DataScaleOverlayPolicy.monitor -and $DataScaleOverlayPolicy.monitor.supported_extensions) {
        $supportedExt = @($DataScaleOverlayPolicy.monitor.supported_extensions)
    }

    $taskApplicable = ($taskAllow -contains $TaskType)
    $gradeApplicable = ($gradeAllow -contains $Grade)
    $packApplicable = if ($packAllow.Count -gt 0) { $packAllow -contains $SelectedPackId } else { $true }
    $skillApplicable = if ($skillAllow.Count -gt 0) { $skillAllow -contains $SelectedSkill } else { $true }
    $scopeApplicable = ($taskApplicable -and $gradeApplicable -and $packApplicable -and $skillApplicable)

    $preserveRoutingAssignment = $true
    if ($DataScaleOverlayPolicy.preserve_routing_assignment -ne $null) {
        $preserveRoutingAssignment = [bool]$DataScaleOverlayPolicy.preserve_routing_assignment
    }

    if (-not $scopeApplicable) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $false
            enforcement = "none"
            reason = "outside_scope"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $probeEnabled = $true
    $extractFromPrompt = $true
    $workspaceProbeWhenNoPath = $false
    $workspaceProbeLimit = 3
    $workspaceProbeExtensions = @("csv", "tsv", "tab", "psv", "ssv", "scsv", "xlsx", "xlsm", "xls")
    $sampleMaxLines = 200
    $sampleMaxChars = 200000

    if ($DataScaleOverlayPolicy.path_probe) {
        if ($DataScaleOverlayPolicy.path_probe.enabled -ne $null) {
            $probeEnabled = [bool]$DataScaleOverlayPolicy.path_probe.enabled
        }
        if ($DataScaleOverlayPolicy.path_probe.extract_from_prompt -ne $null) {
            $extractFromPrompt = [bool]$DataScaleOverlayPolicy.path_probe.extract_from_prompt
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_when_no_path -ne $null) {
            $workspaceProbeWhenNoPath = [bool]$DataScaleOverlayPolicy.path_probe.workspace_probe_when_no_path
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_limit -ne $null) {
            $workspaceProbeLimit = [int]$DataScaleOverlayPolicy.path_probe.workspace_probe_limit
        }
        if ($DataScaleOverlayPolicy.path_probe.workspace_probe_extensions) {
            $workspaceProbeExtensions = @($DataScaleOverlayPolicy.path_probe.workspace_probe_extensions)
        }
        if ($DataScaleOverlayPolicy.path_probe.read_sample_max_lines -ne $null) {
            $sampleMaxLines = [int]$DataScaleOverlayPolicy.path_probe.read_sample_max_lines
        }
        if ($DataScaleOverlayPolicy.path_probe.read_sample_max_chars -ne $null) {
            $sampleMaxChars = [int]$DataScaleOverlayPolicy.path_probe.read_sample_max_chars
        }
    }

    if (-not $probeEnabled) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "probe_disabled"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @()
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $pathsDetected = @()
    if ($extractFromPrompt) {
        $pathsDetected = Get-PathCandidatesFromPrompt -Prompt $Prompt -SupportedExtensions $supportedExt
    }
    $pathsExisting = Resolve-ExistingPathCandidates -PathCandidates $pathsDetected -WorkspaceProbeEnabled $workspaceProbeWhenNoPath -WorkspaceProbeLimit $workspaceProbeLimit -WorkspaceProbeExtensions $workspaceProbeExtensions

    if ($pathsExisting.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "no_existing_data_path"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @($pathsDetected)
            paths_existing = @()
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $fileAnalysis = @()
    foreach ($path in $pathsExisting) {
        $item = $null
        try {
            $item = Get-Item -LiteralPath $path -ErrorAction Stop
        } catch {
            continue
        }
        if (-not $item) { continue }

        $ext = Get-DetectedExtension -Path $item.FullName -SupportedExtensions $supportedExt
        $isWorkbook = Test-WorkbookExtension -Extension $ext
        $isCsvLike = Test-CsvLikeExtension -Extension $ext
        $isCompressed = ($ext -match "\.(gz|zst)$")

        $columns = $null
        $estimatedRows = $null
        $sampleRows = 0
        if ($isCsvLike -and -not $isCompressed) {
            $sample = Get-DelimitedFileSampleStats -Path $item.FullName -Extension $ext -FileSizeBytes ([int64]$item.Length) -MaxLines $sampleMaxLines -MaxChars $sampleMaxChars
            $columns = $sample.columns
            $estimatedRows = $sample.estimated_rows
            $sampleRows = $sample.sample_rows
        }

        $fileAnalysis += [pscustomobject]@{
            path = [string]$item.FullName
            size_bytes = [int64]$item.Length
            extension = $ext
            is_workbook = $isWorkbook
            is_csv_like = $isCsvLike
            is_compressed = $isCompressed
            columns = $columns
            estimated_rows = $estimatedRows
            sample_rows = $sampleRows
        }
    }

    if ($fileAnalysis.Count -eq 0) {
        return [pscustomobject]@{
            enabled = $true
            mode = $mode
            task_applicable = $taskApplicable
            grade_applicable = $gradeApplicable
            pack_applicable = $packApplicable
            skill_applicable = $skillApplicable
            scope_applicable = $true
            enforcement = "advisory"
            reason = "probe_failed"
            preserve_routing_assignment = $preserveRoutingAssignment
            paths_detected = @($pathsDetected)
            paths_existing = @($pathsExisting)
            probe_file_count = 0
            probe_primary_file = $null
            probe_file_analysis = @()
            data_scale = "unknown"
            size_bytes = 0
            estimated_rows = $null
            column_count = $null
            is_workbook = $false
            is_csv_like = $false
            is_compressed = $false
            operation_prefers_xan = $false
            recommended_skill = $null
            confidence = 0.0
            confirm_required = $false
            auto_override = $false
            override_candidate_allowed = $false
        }
    }

    $primary = $fileAnalysis | Sort-Object -Property @{ Expression = "size_bytes"; Descending = $true } | Select-Object -First 1
    $sizeBytes = [int64]$primary.size_bytes
    $estimatedRows = if ($primary.estimated_rows -ne $null) { [int64]$primary.estimated_rows } else { $null }
    $columnCount = if ($primary.columns -ne $null) { [int]$primary.columns } else { $null }
    $isWorkbook = [bool]$primary.is_workbook
    $isCsvLike = [bool]$primary.is_csv_like
    $isCompressed = [bool]$primary.is_compressed

    $mediumSize = 52428800
    $largeSize = 314572800
    $mediumRows = 500000
    $largeRows = 3000000
    $confirmMin = 0.6
    $overrideMin = 0.85

    if ($DataScaleOverlayPolicy.thresholds) {
        if ($DataScaleOverlayPolicy.thresholds.medium_size_bytes -ne $null) { $mediumSize = [int64]$DataScaleOverlayPolicy.thresholds.medium_size_bytes }
        if ($DataScaleOverlayPolicy.thresholds.large_size_bytes -ne $null) { $largeSize = [int64]$DataScaleOverlayPolicy.thresholds.large_size_bytes }
        if ($DataScaleOverlayPolicy.thresholds.medium_estimated_rows -ne $null) { $mediumRows = [int64]$DataScaleOverlayPolicy.thresholds.medium_estimated_rows }
        if ($DataScaleOverlayPolicy.thresholds.large_estimated_rows -ne $null) { $largeRows = [int64]$DataScaleOverlayPolicy.thresholds.large_estimated_rows }
        if ($DataScaleOverlayPolicy.thresholds.confirm_confidence_min -ne $null) { $confirmMin = [double]$DataScaleOverlayPolicy.thresholds.confirm_confidence_min }
        if ($DataScaleOverlayPolicy.thresholds.high_confidence_for_override -ne $null) { $overrideMin = [double]$DataScaleOverlayPolicy.thresholds.high_confidence_for_override }
    }

    $isLargeBySize = ($sizeBytes -ge $largeSize)
    $isLargeByRows = ($estimatedRows -ne $null -and $estimatedRows -ge $largeRows)
    $isMediumBySize = ($sizeBytes -ge $mediumSize)
    $isMediumByRows = ($estimatedRows -ne $null -and $estimatedRows -ge $mediumRows)

    $dataScale = "small"
    if ($isLargeBySize -or $isLargeByRows) {
        $dataScale = "large"
    } elseif ($isMediumBySize -or $isMediumByRows) {
        $dataScale = "medium"
    }

    $csvDefaultSkill = "spreadsheet"
    $csvLargeSkill = "xan"
    $workbookSkill = "xlsx"
    $workbookAnalysisSkill = "excel-analysis"
    $operationKeywords = @("join", "groupby", "dedup", "frequency", "sort", "filter", "pipeline", "aggregate", "window", "parallel", "merge", "split", "分组", "去重", "聚合", "连接", "排序", "过滤", "管道", "流式")
    if ($DataScaleOverlayPolicy.recommendations) {
        if ($DataScaleOverlayPolicy.recommendations.csv_default_skill) { $csvDefaultSkill = [string]$DataScaleOverlayPolicy.recommendations.csv_default_skill }
        if ($DataScaleOverlayPolicy.recommendations.csv_large_skill) { $csvLargeSkill = [string]$DataScaleOverlayPolicy.recommendations.csv_large_skill }
        if ($DataScaleOverlayPolicy.recommendations.workbook_skill) { $workbookSkill = [string]$DataScaleOverlayPolicy.recommendations.workbook_skill }
        if ($DataScaleOverlayPolicy.recommendations.workbook_analysis_skill) { $workbookAnalysisSkill = [string]$DataScaleOverlayPolicy.recommendations.workbook_analysis_skill }
        if ($DataScaleOverlayPolicy.recommendations.operations_preferring_xan) {
            $operationKeywords = @($DataScaleOverlayPolicy.recommendations.operations_preferring_xan)
        }
    }

    $operationPrefersXan = $false
    foreach ($kw in $operationKeywords) {
        if (Test-KeywordHit -PromptLower $PromptLower -Keyword ([string]$kw)) {
            $operationPrefersXan = $true
            break
        }
    }

    $recommendedSkill = $null
    $confidence = 0.0
    $reason = "no_recommendation"
    if ($isWorkbook) {
        $pivotLike = (Test-KeywordHit -PromptLower $PromptLower -Keyword "pivot") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "pivot table") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "数据透视") -or (Test-KeywordHit -PromptLower $PromptLower -Keyword "透视表")
        $recommendedSkill = if ($pivotLike) { $workbookAnalysisSkill } else { $workbookSkill }
        $confidence = 0.9
        $reason = "workbook_detected"
    } elseif ($isCsvLike) {
        if ($dataScale -eq "large") {
            $recommendedSkill = $csvLargeSkill
            $confidence = 0.9
            $reason = "csv_large_detected"
        } elseif ($dataScale -eq "medium" -and $operationPrefersXan) {
            $recommendedSkill = $csvLargeSkill
            $confidence = 0.72
            $reason = "csv_medium_operation_prefers_xan"
        } else {
            $recommendedSkill = $csvDefaultSkill
            $confidence = 0.68
            $reason = "csv_default_path"
        }
    } else {
        $reason = "unsupported_extension"
    }

    $overrideCandidateAllowed = ($recommendedSkill -and ($PackCandidates -contains $recommendedSkill))
    $enforcement = "advisory"
    $confirmRequired = $false
    $autoOverride = $false

    if ($recommendedSkill -and $overrideCandidateAllowed -and $SelectedSkill -and ($recommendedSkill -ne $SelectedSkill)) {
        switch ($mode) {
            "soft" {
                if ($confidence -ge $confirmMin) {
                    $enforcement = "confirm_required"
                    $confirmRequired = $true
                }
            }
            "strict" {
                if ($confidence -ge $overrideMin) {
                    $enforcement = "required"
                    $autoOverride = $true
                } elseif ($confidence -ge $confirmMin) {
                    $enforcement = "confirm_required"
                    $confirmRequired = $true
                }
            }
        }
    }

    return [pscustomobject]@{
        enabled = $true
        mode = $mode
        task_applicable = $taskApplicable
        grade_applicable = $gradeApplicable
        pack_applicable = $packApplicable
        skill_applicable = $skillApplicable
        scope_applicable = $scopeApplicable
        enforcement = $enforcement
        reason = $reason
        preserve_routing_assignment = $preserveRoutingAssignment
        paths_detected = @($pathsDetected)
        paths_existing = @($pathsExisting)
        probe_file_count = $fileAnalysis.Count
        probe_primary_file = [string]$primary.path
        probe_file_analysis = @($fileAnalysis)
        data_scale = $dataScale
        size_bytes = [int64]$sizeBytes
        estimated_rows = $estimatedRows
        column_count = $columnCount
        is_workbook = $isWorkbook
        is_csv_like = $isCsvLike
        is_compressed = $isCompressed
        operation_prefers_xan = $operationPrefersXan
        recommended_skill = $recommendedSkill
        confidence = [Math]::Round([double]$confidence, 4)
        confirm_required = $confirmRequired
        auto_override = $autoOverride
        override_candidate_allowed = $overrideCandidateAllowed
    }
}


