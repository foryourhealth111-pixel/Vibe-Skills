param()

$ErrorActionPreference = "Stop"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ""
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    if ($Details) {
        Write-Host "[FAIL] $Message - $Details" -ForegroundColor Red
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }
    return $false
}

function Read-Json {
    param([Parameter(Mandatory)] [string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Invoke-Route {
    param(
        [Parameter(Mandatory)] [string]$Prompt,
        [Parameter(Mandatory)] [string]$Grade,
        [Parameter(Mandatory)] [string]$TaskType,
        [AllowEmptyString()] [string]$RequestedSkill = ""
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
    $args = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if (-not [string]::IsNullOrWhiteSpace($RequestedSkill)) {
        $args.RequestedSkill = $RequestedSkill
    }
    return (& $resolver @args | ConvertFrom-Json)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$manifest = Read-Json -Path (Join-Path $repoRoot "config\pack-manifest.json")
$retrievalProfiles = Read-Json -Path (Join-Path $repoRoot "config\retrieval-intent-profiles.json")
$runtimeContract = Read-Json -Path (Join-Path $repoRoot "config\runtime-contract.json")
$skillMd = Get-Content -LiteralPath (Join-Path $repoRoot "SKILL.md") -Raw -Encoding UTF8
$runtimeProtocol = Get-Content -LiteralPath (Join-Path $repoRoot "protocols\runtime.md") -Raw -Encoding UTF8

$results = @()

$activePackIds = @($manifest.packs | ForEach-Object { [string]$_.id })
$results += Assert-True -Condition (-not ($activePackIds -contains "orchestration-core")) -Message "active pack-manifest no longer contains orchestration-core" -Details ("packs={0}" -f ($activePackIds -join ", "))
$results += Assert-True -Condition ($activePackIds -contains "workflow-compatibility") -Message "explicit compatibility pack exists"

$recommendedPacks = @(
    $retrievalProfiles.profiles |
        ForEach-Object { @($_.recommended_packs | ForEach-Object { [string]$_ }) }
)
$results += Assert-True -Condition (-not ($recommendedPacks -contains "orchestration-core")) -Message "retrieval profiles do not recommend orchestration-core"

$results += Assert-True -Condition ($runtimeContract.authority.PSObject.Properties.Name -contains "local_installed_skill_recommender") -Message "runtime contract names local installed specialist recommender owner"
$results += Assert-True -Condition ([string]$runtimeContract.authority.local_installed_skill_recommender -eq "packages/runtime-core/src/vgo_runtime/router_contract_runtime.py") -Message "local installed specialist recommender points at python semantic owner"
$results += Assert-True -Condition ($runtimeContract.authority.PSObject.Properties.Name -contains "local_installed_skill_recommender_bridge") -Message "runtime contract names local installed specialist recommender bridge"
$results += Assert-True -Condition ([string]$runtimeContract.authority.local_installed_skill_recommender_bridge -eq "scripts/router/resolve-pack-route.ps1") -Message "local installed specialist recommender bridge points at resolve-pack-route.ps1"
$results += Assert-True -Condition ($runtimeContract.authority.PSObject.Properties.Name -contains "canonical_router") -Message "runtime contract keeps canonical_router compatibility field"

$results += Assert-True -Condition (
    $skillMd -match 'packages/runtime-core/src/vgo_runtime/router_contract_runtime.py' -and
    $skillMd -match 'compatibility bridge' -and
    $skillMd -match 'scripts/router/resolve-pack-route.ps1'
) -Message "SKILL.md names the candidate-audit owner before its compatibility bridge"
$results += Assert-True -Condition ($skillMd -notmatch "(?m)^\s*Canonical router:") -Message "SKILL.md no longer labels router as the canonical entry"
$results += Assert-True -Condition ($runtimeProtocol -match 'semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`') -Message "runtime protocol defines the candidate-audit owner before its bridge"
$results += Assert-True -Condition ($runtimeProtocol -match 'compatibility bridge `scripts/router/resolve-pack-route.ps1`') -Message "runtime protocol keeps resolve-pack-route.ps1 as compatibility bridge"
$results += Assert-True -Condition ($runtimeProtocol -notmatch "Canonical router authority stays intact") -Message "runtime protocol no longer gives router authority priority over vibe"

$blockedRoutes = @(
    [pscustomobject]@{ Name = "generic planning"; Prompt = "Write an implementation plan and task breakdown"; Grade = "L"; TaskType = "planning" },
    [pscustomobject]@{ Name = "generic brainstorming"; Prompt = "Brainstorm several possible approaches before execution"; Grade = "L"; TaskType = "planning" },
    [pscustomobject]@{ Name = "generic subagent"; Prompt = "Split the work into several parallel subagents"; Grade = "XL"; TaskType = "planning" }
)

foreach ($case in $blockedRoutes) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType
    $selectedPack = if ($route.candidate_focus) { [string]$route.candidate_focus.pack_id } else { "" }
    $rankedPackIds = @($route.ranked | ForEach-Object { [string]$_.pack_id })
    $selectedSkill = if ($route.candidate_focus) { [string]$route.candidate_focus.skill } else { "" }
    $results += Assert-True -Condition ($selectedPack -ne "orchestration-core") -Message "[$($case.Name)] selected pack is not orchestration-core" -Details ("selected={0}/{1}" -f $selectedPack, $selectedSkill)
    $results += Assert-True -Condition (-not ($rankedPackIds -contains "orchestration-core")) -Message "[$($case.Name)] ranked packs exclude orchestration-core" -Details ("ranked={0}" -f ($rankedPackIds -join ", "))
}

$passCount = @($results | Where-Object { $_ }).Count
$failCount = @($results | Where-Object { -not $_ }).Count
$total = @($results).Count

Write-Host ""
Write-Host "=== Orchestration-Core Hard Removal Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}
