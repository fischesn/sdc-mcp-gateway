<#
Run deterministic oracle-agent evaluation for all v0.8 scenarios.

Assumptions:
- Run from the repository root.
- The virtual environment is activated.
- sdc-mcp-gateway v0.8.0 or later is installed.
#>

param(
    [string]$OutputDir = "data\agent_eval",
    [string]$MieFile = "config\sdc_mie.yaml",
    [string]$TasksFile = "config\agent_eval.tasks.yaml",
    [double]$ElapsedS = 100.0
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([string]$Description, [string[]]$CommandArgs)
    Write-Host ""
    Write-Host ">>> $Description"
    Write-Host "sdc-mcp-gateway $($CommandArgs -join ' ')"
    & sdc-mcp-gateway @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: sdc-mcp-gateway $($CommandArgs -join ' ')"
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Evaluations = @(
    @{ Scenario = "baseline"; Config = "config\gateway.simulated.example.yaml" },
    @{ Scenario = "tachycardia"; Config = "config\gateway.simulated.tachycardia.example.yaml" },
    @{ Scenario = "spo2-drop"; Config = "config\gateway.simulated.spo2-drop.example.yaml" },
    @{ Scenario = "airway-pressure"; Config = "config\gateway.simulated.high-airway-pressure.example.yaml" }
)

foreach ($Evaluation in $Evaluations) {
    Invoke-Checked "Agent evaluation $($Evaluation.Scenario)" @(
        "evaluate-agent-tasks",
        "--config", $Evaluation.Config,
        "--mie", $MieFile,
        "--tasks", $TasksFile,
        "--scenario", $Evaluation.Scenario,
        "--agent", "oracle",
        "--output-dir", $OutputDir,
        "--label", "agent-eval-v08",
        "--elapsed-s", "$ElapsedS"
    )
}

Write-Host ""
Write-Host "All agent evaluations completed. Outputs are in $OutputDir"
