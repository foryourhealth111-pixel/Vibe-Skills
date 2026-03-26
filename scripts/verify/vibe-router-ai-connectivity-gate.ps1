param(
    [string]$TargetRoot = '',
    [switch]$WriteArtifacts,
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\common\vibe-governance-helpers.ps1')

try {
    $context = Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext
    $repoRoot = $context.repoRoot
    $resolvedTargetRoot = Resolve-VgoTargetRoot -TargetRoot $TargetRoot
    $probeScript = Join-Path $repoRoot 'scripts\verify\runtime_neutral\router_ai_connectivity_probe.py'

    if (-not (Test-Path -LiteralPath $probeScript)) {
        throw "runtime-neutral router AI connectivity probe missing: $probeScript"
    }

    $probeArgs = @(
        $probeScript
        '--target-root'
        $resolvedTargetRoot
    )
    if ($WriteArtifacts) {
        $probeArgs += '--write-artifacts'
        if (-not [string]::IsNullOrWhiteSpace($OutputDirectory)) {
            $probeArgs += '--output-directory'
            $probeArgs += $OutputDirectory
        }
    }

    $pythonInvocation = Get-VgoPythonCommand

    Write-Host '=== VCO Router AI Connectivity Gate ==='
    Write-Host ("[INFO] target_root={0}" -f $resolvedTargetRoot)
    if ($WriteArtifacts) {
        if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
            Write-Host ("[INFO] output_directory={0}" -f (Join-Path $repoRoot 'outputs\verify'))
        } else {
            Write-Host ("[INFO] output_directory={0}" -f $OutputDirectory)
        }
    }
    Write-Host '[INFO] advisory_only=true route_mutation=false'

    $global:LASTEXITCODE = 0
    & $pythonInvocation.host_path @($pythonInvocation.prefix_arguments) @probeArgs
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }

    $gateResult = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }
    Write-Host ("[INFO] gate_result={0} exit_code={1}" -f $gateResult, $exitCode)
    exit $exitCode
} catch {
    Write-Host ("[FAIL] {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
