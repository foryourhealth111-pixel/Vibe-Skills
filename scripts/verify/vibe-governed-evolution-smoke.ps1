param(
    [string]$Task = 'Summarize the repository structure, produce governed evolution artifacts, and close the run cleanly.',
    [string]$RepoRoot = '',
    [string]$ArtifactRoot = '',
    [string]$RunId = '',
    [string]$SessionRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-DefaultRepoRoot {
    $start = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $start '..\..')).Path
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Read-GovernedEvolutionPolicy {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $path = Join-Path $RepoRoot 'config\governed-evolution-artifact-policy.json'
    return Read-JsonFile -Path $path
}

function Get-EnabledArtifactFiles {
    param(
        [Parameter(Mandatory = $true)]$Policy,
        [Parameter(Mandatory = $true)][string]$StopStage
    )

    $result = [System.Collections.Generic.List[string]]::new()
    if ($null -eq $Policy -or -not $Policy.PSObject.Properties.Name.Contains('stop_stage_profiles')) {
        return @()
    }
    $profiles = $Policy.stop_stage_profiles
    if (-not $profiles.PSObject.Properties.Name.Contains($StopStage)) {
        return @()
    }
    $profile = $profiles.$StopStage
    if ($null -eq $profile -or -not $profile.PSObject.Properties.Name.Contains('steps')) {
        return @()
    }
    foreach ($stepName in @($profile.steps.PSObject.Properties.Name)) {
        $step = $profile.steps.$stepName
        if ($null -eq $step -or -not $step.PSObject.Properties.Name.Contains('enabled_artifacts')) {
            continue
        }
        foreach ($fileName in @($step.enabled_artifacts)) {
            $name = [string]$fileName
            if (-not [string]::IsNullOrWhiteSpace($name) -and -not $result.Contains($name)) {
                $result.Add($name)
            }
        }
    }
    return @($result)
}

function Has-Property {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )
    return $null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name
}

function Require {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message,
        [System.Collections.Generic.List[string]]$Failures
    )
    if (-not $Condition) {
        $Failures.Add($Message)
    }
}

function Require-Properties {
    param(
        $Items,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Properties,
        [System.Collections.Generic.List[string]]$Failures
    )

    $index = 0
    foreach ($item in @($Items)) {
        foreach ($property in $Properties) {
            Require (Has-Property $item $property) "$Label #$index missing $property" $Failures
        }
        $index += 1
    }
}

function Get-RequiredMemberValue {
    param(
        [Parameter(Mandatory = $true)]$InputObject,
        [Parameter(Mandatory = $true)][string]$Name,
        [System.Collections.Generic.List[string]]$Failures,
        [string]$Label = 'object'
    )

    if (-not (Has-Property $InputObject $Name)) {
        Require $false "$Label missing $Name" $Failures
        return $null
    }

    return $InputObject.$Name
}

function Require-NonEmptyStringMember {
    param(
        [Parameter(Mandatory = $true)]$InputObject,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Label,
        [System.Collections.Generic.List[string]]$Failures
    )

    if (-not (Has-Property $InputObject $Name)) {
        Require $false "$Label missing $Name" $Failures
        return
    }

    $value = [string]$InputObject.$Name
    Require (-not [string]::IsNullOrWhiteSpace($value)) "$Label missing populated $Name" $Failures
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Resolve-DefaultRepoRoot
}

if ([string]::IsNullOrWhiteSpace($ArtifactRoot)) {
    $ArtifactRoot = Join-Path $RepoRoot 'outputs\governed-evolution-test'
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = 'governed-evolution-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
}

if ([string]::IsNullOrWhiteSpace($SessionRoot)) {
    $runtimeScript = Join-Path $RepoRoot 'scripts\runtime\invoke-vibe-runtime.ps1'
    if (-not (Test-Path -LiteralPath $runtimeScript)) {
        throw "Missing runtime entrypoint: $runtimeScript"
    }

    New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null

    $previousDisableNative = $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION
    $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION = '1'
    try {
        $result = & $runtimeScript `
            -Task $Task `
            -Mode interactive_governed `
            -RunId $RunId `
            -ArtifactRoot $ArtifactRoot
    }
    finally {
        if ($null -eq $previousDisableNative) {
            Remove-Item Env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION -ErrorAction SilentlyContinue
        }
        else {
            $env:VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION = $previousDisableNative
        }
    }

    if ($null -eq $result) {
        throw 'invoke-vibe-runtime.ps1 returned null.'
    }

    $SessionRoot = [string]$result.session_root
}

if ([string]::IsNullOrWhiteSpace($SessionRoot)) {
    throw 'No session root was provided or generated.'
}

$SessionRoot = (Resolve-Path $SessionRoot).Path
$failures = [System.Collections.Generic.List[string]]::new()
$policy = Read-GovernedEvolutionPolicy -RepoRoot $RepoRoot
$expectedFiles = @('runtime-summary.json') + @(Get-EnabledArtifactFiles -Policy $policy -StopStage 'phase_cleanup')

$paths = [ordered]@{}
foreach ($fileName in @($expectedFiles)) {
    $paths[$fileName] = Join-Path $SessionRoot $fileName
}

foreach ($entry in $paths.GetEnumerator()) {
    Require (Test-Path -LiteralPath $entry.Value) "missing $($entry.Key): $($entry.Value)" $failures
}

if ($failures.Count -eq 0) {
    $summary = Read-JsonFile $paths['runtime-summary.json']
    $failurePayload = Read-JsonFile $paths['failure-patterns.json']
    $pitfallPayload = Read-JsonFile $paths['pitfall-events.json']
    $atomicPayload = Read-JsonFile $paths['atomic-skill-call-chain.json']
    $proposalLayer = Read-JsonFile $paths['proposal-layer.json']
    $warningCards = Read-JsonFile $paths['warning-cards.json']
    $preflightChecklist = Read-JsonFile $paths['preflight-checklist.json']
    $remediationNotes = Read-JsonFile $paths['remediation-notes.json']
    $candidateDraft = Read-JsonFile $paths['candidate-composite-skill-draft.json']
    $policySuggestion = Read-JsonFile $paths['threshold-policy-suggestion.json']
    $readinessReport = Read-JsonFile $paths['application-readiness-report.json']

    $artifacts = Get-RequiredMemberValue -InputObject $summary -Name 'artifacts' -Failures $failures -Label 'runtime-summary.json'
    $expectedArtifactRefs = [ordered]@{
        observed_failure_patterns       = 'failure-patterns.json'
        observed_pitfall_events         = 'pitfall-events.json'
        atomic_skill_call_chain         = 'atomic-skill-call-chain.json'
        proposal_layer                  = 'proposal-layer.json'
        proposal_layer_markdown         = 'proposal-layer.md'
        warning_cards                   = 'warning-cards.json'
        preflight_checklist             = 'preflight-checklist.json'
        remediation_notes               = 'remediation-notes.json'
        candidate_composite_skill_draft = 'candidate-composite-skill-draft.json'
        threshold_policy_suggestion     = 'threshold-policy-suggestion.json'
        application_readiness_report    = 'application-readiness-report.json'
        application_readiness_markdown  = 'application-readiness-report.md'
    }

    foreach ($artifactName in $expectedArtifactRefs.Keys) {
        Require-NonEmptyStringMember -InputObject $artifacts -Name $artifactName -Label 'runtime-summary.json artifacts' -Failures $failures
        if (Has-Property $artifacts $artifactName) {
            $leaf = Split-Path -Leaf ([string]$artifacts.$artifactName)
            Require ($leaf -eq $expectedArtifactRefs[$artifactName]) "runtime-summary.json artifacts.$artifactName must reference $($expectedArtifactRefs[$artifactName])" $failures
        }
    }

    $failurePatterns = @()
    $pitfallEvents = @()
    $atomicEvents = @()
    $cards = @()
    $checks = @()
    $notes = @()
    $drafts = @()
    $suggestions = @()
    $laneACandidates = @()
    $laneBCandidates = @()

    if (Has-Property $failurePayload 'patterns') { $failurePatterns = @($failurePayload.patterns) } else { Require $false 'failure-patterns.json missing patterns' $failures }
    if (Has-Property $pitfallPayload 'events') { $pitfallEvents = @($pitfallPayload.events) } else { Require $false 'pitfall-events.json missing events' $failures }
    if (Has-Property $atomicPayload 'events') { $atomicEvents = @($atomicPayload.events) } else { Require $false 'atomic-skill-call-chain.json missing events' $failures }
    if (Has-Property $warningCards 'cards') { $cards = @($warningCards.cards) } else { Require $false 'warning-cards.json missing cards' $failures }
    if (Has-Property $preflightChecklist 'checks') { $checks = @($preflightChecklist.checks) } else { Require $false 'preflight-checklist.json missing checks' $failures }
    if (Has-Property $remediationNotes 'notes') { $notes = @($remediationNotes.notes) } else { Require $false 'remediation-notes.json missing notes' $failures }
    if (Has-Property $candidateDraft 'drafts') { $drafts = @($candidateDraft.drafts) } else { Require $false 'candidate-composite-skill-draft.json missing drafts' $failures }
    if (Has-Property $policySuggestion 'suggestions') { $suggestions = @($policySuggestion.suggestions) } else { Require $false 'threshold-policy-suggestion.json missing suggestions' $failures }
    if (Has-Property $readinessReport 'lane_a_candidates') { $laneACandidates = @($readinessReport.lane_a_candidates) } else { Require $false 'application-readiness-report.json missing lane_a_candidates' $failures }
    if (Has-Property $readinessReport 'lane_b_candidates') { $laneBCandidates = @($readinessReport.lane_b_candidates) } else { Require $false 'application-readiness-report.json missing lane_b_candidates' $failures }

    if (Has-Property $proposalLayer 'mode') { Require ($proposalLayer.mode -eq 'report-only') 'proposal-layer.json mode must be report-only' $failures } else { Require $false 'proposal-layer.json missing mode' $failures }
    if (Has-Property $proposalLayer 'review_status') { Require ($proposalLayer.review_status -eq 'pending-review') 'proposal-layer.json review_status must be pending-review' $failures } else { Require $false 'proposal-layer.json missing review_status' $failures }
    Require (Has-Property $proposalLayer 'artifacts') 'proposal-layer.json missing artifacts' $failures
    Require (Has-Property $proposalLayer 'summary') 'proposal-layer.json missing summary' $failures

    if (Has-Property $readinessReport 'mode') { Require ($readinessReport.mode -eq 'report-only') 'application-readiness-report.json mode must be report-only' $failures } else { Require $false 'application-readiness-report.json missing mode' $failures }
    if (Has-Property $readinessReport 'review_status') { Require ($readinessReport.review_status -eq 'pending-review') 'application-readiness-report.json review_status must be pending-review' $failures } else { Require $false 'application-readiness-report.json missing review_status' $failures }
    Require (Has-Property $readinessReport 'input_artifacts') 'application-readiness-report.json missing input_artifacts' $failures
    Require (Has-Property $readinessReport 'summary') 'application-readiness-report.json missing summary' $failures

    Require-Properties $failurePatterns 'failure pattern' @('pattern_id', 'classification', 'evidence_refs') $failures
    Require-Properties $pitfallEvents 'pitfall event' @('pitfall_type', 'source_layer', 'source_artifact', 'confidence_level') $failures
    Require-Properties $atomicEvents 'atomic skill event' @('event_id', 'event_type', 'skill_id', 'stage', 'source_artifact') $failures
    Require-Properties $cards 'warning card' @('card_id', 'severity', 'title', 'summary', 'evidence_refs') $failures
    Require-Properties $checks 'preflight check' @('check_id', 'label', 'why', 'source_signal') $failures
    Require-Properties $notes 'remediation note' @('note_id', 'remediation_type', 'suggested_remediation', 'evidence_level') $failures
    Require-Properties $drafts 'candidate draft' @('draft_id', 'governor_skill', 'component_skills', 'promotion_readiness') $failures
    Require-Properties $suggestions 'policy suggestion' @('suggestion_id', 'policy_area', 'suggested_change', 'review_path') $failures
    Require-Properties $laneACandidates 'lane A candidate' @('candidate_id', 'proposal_type', 'recommended_surface', 'activation_mode', 'target_stage', 'readiness', 'boundary_impact', 'coupling_risk', 'regression_risk') $failures
    Require-Properties $laneBCandidates 'lane B candidate' @('candidate_id', 'proposal_type', 'recommended_surface', 'governance_path', 'target_scope', 'manual_review_required', 'shadow_required', 'shadow_plan_status', 'board_review_required', 'rollback_plan_required', 'readiness', 'boundary_impact', 'coupling_risk', 'regression_risk') $failures
}

if ($failures.Count -gt 0) {
    foreach ($failure in $failures) {
        Write-Output "[FAIL] $failure"
    }
    throw "Governed evolution smoke failed with $($failures.Count) failure(s)."
}

[pscustomobject]@{
    status = 'passed'
    run_id = $RunId
    session_root = $SessionRoot
    checked_artifact_count = $paths.Count
    failure_pattern_count = $failurePatterns.Count
    pitfall_event_count = $pitfallEvents.Count
    atomic_skill_event_count = $atomicEvents.Count
    warning_card_count = $cards.Count
    preflight_check_count = $checks.Count
    remediation_note_count = $notes.Count
    candidate_draft_count = $drafts.Count
    threshold_policy_suggestion_count = $suggestions.Count
    lane_a_candidate_count = $laneACandidates.Count
    lane_b_candidate_count = $laneBCandidates.Count
} | ConvertTo-Json -Depth 8
