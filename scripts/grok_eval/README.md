# grok_eval — Exos model evaluation harness

Benchmarks **Grok 4.6/4.7** against our model mix (local Ollama, Opus 4.8, Kimi K3) on a fixed,
**NON-CONTROLLED, BLK3-adjacent** eval set. Precursor to the exo3 Grok integration
(see `drafts/exo3_Grok_Secure_GNC_Execution_Plan.md`).

## Guardrail (non-negotiable)
Public / non-controlled content ONLY. **No ITAR / CUI / BLK3-vehicle data** ever enters
`eval_set.json`. The runner aborts if any item is not `controlled:false`. Controlled GNC work
belongs in the secure enclave / on local self-hostable models — never in a hosted-API eval.

## Run it
```bash
cd scripts/grok_eval
python3 run_eval.py                    # local only (free): qwen3.6:35b-a3b + gemma4:e4b
python3 run_eval.py --grok             # + Grok 4.6 (needs xai_api_key)
python3 run_eval.py --opus --kimi      # + Opus 4.8 + Kimi K3 (spend)
python3 run_eval.py --only grok        # Grok only
python3 run_eval.py --grok --grok-model grok-4.7   # after 4.7 GA
python3 score.py                       # model × category rollup of the newest run
```

## Enabling cloud models
Add keys to `~/.openclaw/secrets.json`:
- **Grok:** `xai_api_key` (from https://console.x.ai/). Endpoint is OpenAI-compatible
  (`https://api.x.ai/v1/chat/completions`), model id `grok-4.6` (falls back to `grok-4-6`).
- **Opus:** already present (`anthropic_default_key_main`).
- **Kimi:** already present (`moonshot_api_key`); model via `KIMI_MODEL` env or `kimi_eval_model` secret.

Cloud models are **OFF by default** — nothing bills unless you pass its flag.

## Output
`results/<UTC-timestamp>/<model>/<item_id>.txt` (raw answers) + `summary.json`
(latency, char count, token usage where the API returns it). Judge answers against the
`rubric` fields in `eval_set.json`.

## Transition to 4.7
When Grok 4.7 ships: `python3 run_eval.py --grok --grok-model grok-4.7`, then diff its answers
against the 4.6 run. Keep 4.6 as the fallback rung.
