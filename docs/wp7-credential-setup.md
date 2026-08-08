# WP7 credential setup

Do not place API keys in YAML, `.env` files inside the repository, command-line
arguments, logs, or chat messages. The most reliable hand-off is a local
PowerShell secrets file outside both repositories, for example
`$env:USERPROFILE\.codex\wp7-secrets.ps1`:

```powershell
$env:OPENAI_API_KEY = "..."
$env:GEMINI_API_KEY = "..."
$env:AI_LAB_API_KEY = "..."
$env:AI_LAB_BASE_URL = "https://institutional-endpoint.example/v1"
$env:DIGITAL_HUB_API_KEY = "..."
$env:DIGITAL_HUB_BASE_URL = "https://hosted-endpoint.example/v1"
$env:OLLAMA_API_KEY = "..." # Ollama Cloud
```

WP7 can dot-source this file and launch the evaluation in the same process. The
file must not print its variables and should be readable only by the local user.

If the AI-Lab endpoint uses a different environment-variable name or no bearer
token, adapt only `AI_LAB_API_KEY`; do not disclose the value. Before a run, the
harness should check only whether each required variable is present and must
never print its contents.

Ollama Cloud uses the authenticated cloud API and is evaluated as an external
provider. A local Ollama service is optional and is not part of the frozen WP7
comparison. If it is configured for a later development run, PowerShell syntax
must include the environment prefix, for example
`$env:OLLAMA_BASE_URL = "http://localhost:11434"`.
