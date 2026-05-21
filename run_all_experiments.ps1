<#
Run all SDC-MCP gateway simulation experiments and aggregate the results.

Assumptions:
- Run this script from the repository root, i.e. the directory containing:
  pyproject.toml, config/, src/, data/
- The Python virtual environment is already activated.
- sdc-mcp-gateway v0.7.1 or later is installed in editable mode.
- The scenarios and configs shipped with v0.7.1 are present.

Example:
  .\scripts\run_all_experiments.ps1

Optional:
  .\scripts\run_all_experiments.ps1 -Iterations 200 -Warmup 20
#>

param(
    [int]$Iterations = 100,
    [int]$Warmup = 10,
    [string]$OutputDir = "data\experiment_runs",
    [string]$MieFile = "config\sdc_mie.yaml",
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Message
    Write-Host "============================================================"
}

function Invoke-Checked {
    param(
        [string]$Description,
        [string[]]$CommandArgs
    )

    Write-Host ""
    Write-Host ">>> $Description"
    Write-Host "sdc-mcp-gateway $($CommandArgs -join ' ')"
    & sdc-mcp-gateway @CommandArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: sdc-mcp-gateway $($CommandArgs -join ' ')"
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Section "SDC-MCP Gateway experiment batch"
Write-Host "Iterations: $Iterations"
Write-Host "Warmup:     $Warmup"
Write-Host "OutputDir:  $OutputDir"
Write-Host "MIE file:   $MieFile"

if (-not $SkipPytest) {
    Write-Section "Running pytest"
    & pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed. Aborting experiments."
    }
}

Write-Section "Running MCP smoke tests"
Invoke-Checked "Internal MCP smoke test" @(
    "mcp-smoke-test",
    "--config", "config\gateway.simulated.example.yaml",
    "--mie", $MieFile
)

Invoke-Checked "End-to-end MCP client smoke test" @(
    "mcp-client-smoke-test",
    "--config", "config\gateway.simulated.example.yaml",
    "--mie", $MieFile
)

$Experiments = @(
    @{
        Name = "baseline"
        Config = "config\gateway.simulated.example.yaml"
        Pattern = "baseline-v07-run*.summary.json"
        SummaryLabel = "baseline-v07-summary"
    },
    @{
        Name = "tachycardia"
        Config = "config\gateway.simulated.tachycardia.example.yaml"
        Pattern = "tachycardia-v07-run*.summary.json"
        SummaryLabel = "tachycardia-v07-summary"
    },
    @{
        Name = "spo2-drop"
        Config = "config\gateway.simulated.spo2-drop.example.yaml"
        Pattern = "spo2-drop-v07-run*.summary.json"
        SummaryLabel = "spo2-drop-v07-summary"
    },
    @{
        Name = "airway-pressure"
        Config = "config\gateway.simulated.high-airway-pressure.example.yaml"
        Pattern = "airway-pressure-v07-run*.summary.json"
        SummaryLabel = "airway-pressure-v07-summary"
    }
)

foreach ($Experiment in $Experiments) {
    Write-Section "Benchmarking experiment: $($Experiment.Name)"

    for ($Run = 1; $Run -le 3; $Run++) {
        $Label = "$($Experiment.Name)-v07-run$Run"

        Invoke-Checked "Benchmark $Label" @(
            "benchmark",
            "--config", $Experiment.Config,
            "--mie", $MieFile,
            "--iterations", "$Iterations",
            "--warmup", "$Warmup",
            "--output-dir", $OutputDir,
            "--label", $Label
        )
    }

    Write-Section "Aggregating experiment: $($Experiment.Name)"

    Invoke-Checked "Aggregate $($Experiment.Name)" @(
        "summarize-benchmarks",
        "--input-dir", $OutputDir,
        "--label", $Experiment.SummaryLabel,
        "--pattern", $Experiment.Pattern
    )
}

Write-Section "All experiments completed successfully"

Write-Host "Generated files are in:"
Write-Host "  $OutputDir"
Write-Host ""
Write-Host "Expected aggregate files:"
foreach ($Experiment in $Experiments) {
    Write-Host "  $($Experiment.SummaryLabel)-<timestamp>.aggregate.json"
    Write-Host "  $($Experiment.SummaryLabel)-<timestamp>.aggregate.csv"
}

Write-Host ""
Write-Host "Suggested next step:"
Write-Host "  Inspect the newest *.aggregate.json files and commit/tag the code version used for the experiment."
