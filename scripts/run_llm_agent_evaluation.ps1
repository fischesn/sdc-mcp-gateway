<#
Run LLM-backed agent evaluation for all v0.9 scenarios.

Default backend is llm-mock so the script works without external services.
For a local Ollama model:
  .\scripts\run_llm_agent_evaluation.ps1 -Agent llm-ollama -LlmModel llama3.1

For Gemini Developer API:
  $env:GEMINI_API_KEY = "..."
  .\scripts\run_llm_agent_evaluation.ps1 -Agent llm-gemini -LlmModel gemini-2.5-flash

For an OpenAI-compatible endpoint:
  $env:OPENAI_API_KEY = "..."
  .\scripts\run_llm_agent_evaluation.ps1 -Agent llm-openai-compatible -LlmModel gpt-4.1-mini
#>

param(
    [string]$Agent = "llm-mock",
    [string]$LlmModel = "mock-medical-agent",
    [string]$LlmEndpoint = "",
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
    $Args = @(
        "evaluate-agent-tasks",
        "--config", $Evaluation.Config,
        "--mie", $MieFile,
        "--tasks", $TasksFile,
        "--scenario", $Evaluation.Scenario,
        "--agent", $Agent,
        "--llm-model", $LlmModel,
        "--output-dir", $OutputDir,
        "--label", "agent-eval-v09-$Agent",
        "--elapsed-s", "$ElapsedS"
    )
    if ($LlmEndpoint -ne "") {
        $Args += @("--llm-endpoint", $LlmEndpoint)
    }
    Invoke-Checked "LLM agent evaluation $($Evaluation.Scenario)" $Args
}

Write-Host ""
Write-Host "All LLM agent evaluations completed. Outputs are in $OutputDir"
