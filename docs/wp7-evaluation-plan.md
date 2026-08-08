# WP7 safety stress and multi-model evaluation plan

## Current state

The WP7 candidate suite is implemented locally. One development-only baseline
task has been sent successfully to each selected endpoint after explicit
approval. The final hold-out has not been executed.

## Frozen comparison design

- Five simulated hold-out scenarios cover multiple simultaneous alarms,
  same-type device ambiguity, unmapped codes, provider unavailability, and
  stale plus invalid metric state.
- Twelve task definitions yield 28 applicable cases per complete scenario set.
- Additional safety cases test exact metric selection, complete alarm-set
  interpretation, prompt injection embedded in resource fields, and refusal of
  a request to bypass the no-treatment/no-execution boundary.
- One deterministic resource processor and five pinned hosted models are
  compared. Hosted models use temperature 0 and three repetitions; the
  deterministic processor uses one repetition.
- Model performance is reported by model and error type with Wilson intervals,
  run-to-run consistency, latency, and token counts when supplied by the API.
  Monetary cost is reported only where a stable rate was frozen in advance.
- An unavailable external endpoint does not trigger task or prompt changes.
  The first connection/backend error opens a per-run circuit breaker; remaining
  cases are marked not evaluable and excluded from accuracy denominators while
  the outage count is retained.

## Execution order

1. Run one development-only baseline task per endpoint to validate access,
   model identifiers, and JSON response handling.
2. Resolve development-only integration failures without inspecting any WP7
   hold-out response.
3. Regenerate and verify `config/bhi2026_wp7_freeze.json` after all local and
   provider preflight changes.
4. Change the hold-out execution gate exactly once and run the frozen pipeline.
5. Preserve every report, aggregate by model/error class, update the paper and
   roadmap, and do not tune prompts or graders against hold-out outcomes.

No physical SDC device or patient data is used. The scenarios are synthetic,
and all agents receive the same read-only MCP resource representation.

## Development integration log

- OpenAI and Gemini passed their first development preflight.
- The initially selected Ollama Cloud model was listed by the account but
  returned HTTP 403 because it required an additional subscription. No hold-out
  input was sent. A project-free minimal request established that `gpt-oss:20b`
  is accessible; the candidate manifest was updated before freezing.
- The first Digital Hub development response contained model reasoning before
  the final JSON. The former greedy fallback parser rejected it with an
  extra-data error. The parser now walks complete JSON objects and selects the
  final one; a regression test and repeated development preflight passed.
- AI-Lab and Digital Hub passed development preflight after the parser fix.
- The first pipeline invocation stopped locally before producing any agent
  report or external hold-out call: the anonymity guard mistook the `s:/` in an
  HTTPS scheme for a Windows drive. The path expression was narrowed, covered
  by a regression test, and included in a newly generated freeze.
