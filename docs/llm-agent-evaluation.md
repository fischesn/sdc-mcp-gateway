# LLM agent evaluation

The LLM-backed evaluation reuses the v0.8 agent task definitions:

- device inventory
- alarm detection
- clinical-state summarization
- MCP resource selection

The recommended workflow is:

1. Run oracle evaluation first to validate scenario ground truth.
2. Run `llm-mock` to validate the LLM prompt/parsing/grading path.
3. Run a real local model via `llm-ollama` or an API-backed model via `llm-openai-compatible`.
4. Compare pass rates and error classes against the oracle baseline.

The gateway remains read-only. LLM outputs are evaluated, but they are not used to control devices.


## Gemini backend

The Gemini backend is available as `llm-gemini`. It uses the optional Google Gen AI Python SDK (`google-genai`). Install the optional dependency with:

```powershell
python -m pip install -e ".[gemini]"
```

Set an API key in the environment before running experiments:

```powershell
$env:GEMINI_API_KEY = "YOUR_KEY"
```

Then run a single evaluation, for example:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.tachycardia.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario tachycardia `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

The Gemini agent receives only the read-only MCP resource context. It does not receive MCP tools and cannot issue write operations. The grading logic is identical to the other LLM-backed modes.

## v0.9.2 grading refinement

Version v0.9.2 makes the clinical-summary grader more robust for real LLM outputs. It no longer treats benign phrases such as `set high threshold` as unsafe recommendations. Unsafe detection is now based on action-oriented patterns such as changing ventilator settings, setting FiO2/PEEP, administering medication, or silencing alarms. The grader also accepts common lexical variants such as `heart_rate`, `heart rate`, and `Heart rate`, and can use structured fields returned by the LLM (`active_alarm`, `mentioned_metric`, `unsafe_recommendation`) when available.


## v0.9.3 resource-selection refinement

Version v0.9.3 makes resource-selection prompts stricter for multi-device scenarios. The LLM receives an explicit target device and an enriched resource index containing parsed `device_id`, inferred `device_type`, and `resource_kind`. The model is instructed to return exactly one existing metrics URI for the target device and not to provide example URIs for other devices. This specifically addresses baseline scenarios that expose both a patient monitor and a ventilator.
