<#
Aggregate agent-evaluation JSON files.

Example:
  .\scripts\summarize_agent_evaluations.ps1

Optional:
  .\scripts\summarize_agent_evaluations.ps1 -Pattern "agent-eval-*gemini*.json" -Label gemini-v093-summary
#>

param(
    [string]$InputDir = "data\agent_eval",
    [string]$Pattern = "agent-eval-*.json",
    [string]$Label = "agent-eval-summary"
)

$ErrorActionPreference = "Stop"

Write-Host "Aggregating agent evaluations"
Write-Host "InputDir: $InputDir"
Write-Host "Pattern:  $Pattern"
Write-Host "Label:    $Label"

sdc-mcp-gateway summarize-agent-evaluations --input-dir $InputDir --label $Label --pattern $Pattern

if ($LASTEXITCODE -ne 0) {
    throw "summarize-agent-evaluations failed"
}
