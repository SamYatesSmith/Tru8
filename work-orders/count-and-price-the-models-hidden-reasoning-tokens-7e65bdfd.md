# Count and price the models' hidden reasoning tokens in every per-check cost figure, the margin report, and the model-comparison harness.

Tru8 · pinned to f8733df · effort M · risk low

The late-August model switch put production on models that always spend hidden reasoning effort, and the vendor bills that effort at the expensive output rate. Every cost figure today counts only the visible answer text, so the per-check cost, the answer to 'does a check pay for itself?', and any future model comparison all read lower than what the invoice will say — and the gap grows with exactly the models just adopted. Because the raw counts are stored with each check, teaching the price rules about reasoning also reprices history for the checks that already recorded it.

## Files

- modify `backend/app/core/cost_constants.py`
- modify `backend/app/pipeline/runner.py`
- modify `backend/app/pipeline/evidence_classifier.py`
- modify `backend/app/pipeline/evidence_distiller.py`
- modify `backend/scripts/cost_report.py`
- modify `backend/scripts/eval_mapping_model.py`
- modify `backend/tests/unit/test_cost_constants.py`
- modify `backend/tests/unit/test_cost_report.py`

## Steps

1. In backend/app/core/cost_constants.py, change `_cost(input_tokens, output_tokens, model)` to `_cost(input_tokens, output_tokens, model, thinking_tokens=0)` and add `+ (thinking_tokens / 1_000_000) * r["output"]` to the returned expression, with a comment stating Google bills thought tokens at the output rate.
2. In backend/app/core/cost_constants.py, change `estimate_llm_cost_usd(input_tokens, output_tokens, by_stage=None)` to accept a fourth keyword arg `thinking_tokens: int = 0`. In the no-by_stage branch pass it through to `_cost`. In the stage loop read `st = int(stage.get("thinking_tokens", 0) or 0)`, pass `st` to `_cost`, and accumulate `seen_think += st`; after the loop compute `rem_think = max(0, int(thinking_tokens) - seen_think)` and include it in the residual `_cost` call at the default rate.
3. In backend/app/core/cost_constants.py `build_cost_telemetry`, read `think_tok = int(tok.get("thinking_tokens", 0) or 0)` beside the existing in_tok/out_tok reads, pass `thinking_tokens=think_tok` to `estimate_llm_cost_usd`, and add `"thinking_tokens": think_tok,` to the `"llm"` dict in the returned blob.
4. In backend/app/pipeline/runner.py `_accumulate_tokens`, after the `bucket["output_tokens"]` line add: `if usage.get("thinking_tokens"): bucket["thinking_tokens"] = bucket.get("thinking_tokens", 0) + usage.get("thinking_tokens", 0)` (same pattern as ClaimMapAnalyzer._accumulate at claim_map_analyzer.py:2144-2147).
5. In backend/app/pipeline/evidence_classifier.py `_accumulate` (line 885) and backend/app/pipeline/evidence_distiller.py `_accumulate` (line 241), add the identical thinking_tokens accumulation block used by ClaimMapAnalyzer._accumulate (claim_map_analyzer.py:2144-2147), so their `get_token_usage()` output — and therefore `by_stage` — carries thinking counts.
6. In backend/app/pipeline/runner.py, add `llm_thinking_tokens: Optional[int] = None` to `PipelineMetrics` beside `llm_output_tokens`, emit it in `to_dict()` when not None (same conditional pattern as `llm_output_tokens`), and in `extract_pipeline_metrics` set it from `token_usage.get("thinking_tokens") or None`.
7. In backend/scripts/cost_report.py `row_costs`, read `think_tok = _int(llm.get("thinking_tokens"))`, pass `thinking_tokens=think_tok` to `estimate_llm_cost_usd`, and add `"thinking_tokens": think_tok,` to the returned dict.
8. In backend/scripts/cost_report.py `_stage_cost_usd`, pass `thinking_tokens=_int(stage.get("thinking_tokens"))` to `estimate_llm_cost_usd` so per-stage figures cannot drift from the per-check total.
9. In backend/scripts/cost_report.py `build_report`, add `"thinking_tokens": 0` to the stage `setdefault` dict, accumulate `agg["thinking_tokens"] += _int(stage.get("thinking_tokens"))`, and include `"thinking_tokens": s["thinking_tokens"],` in the per-stage rows of the returned report; in `render`, add a `think tok` column to the WHERE THE LLM SPEND GOES table printing `s['thinking_tokens']`.
10. In backend/scripts/eval_mapping_model.py `call_google_model`, after building the usage dict add: `thoughts = usage_meta.get("thoughtsTokenCount", 0)` and `if thoughts: usage["thinking_tokens"] = thoughts` (mirror of app/services/google_ai.py:472-474).
11. In backend/scripts/eval_mapping_model.py `_print_comparison_summary`, delete the local `PRICING` dict and the `PRICING.get(model_name, ...)` lookup; import `_rate` from `app.core.cost_constants` (the module already imports from `app.core.config`) and set `pricing = _rate(model_name)`; add `total_think = sum(r.get("usage", {}).get("thinking_tokens", 0) for r in valid_results)` and include `total_think` at the output rate in `total_cost`; print the thinking total in the Tokens line and per-claim breakdown.
12. In backend/scripts/eval_mapping_model.py, update the `MODELS` list in `run_evaluation`: change the `flash_lite` entry's model to `gemini-3.5-flash-lite` and the `flash_thinking` entry's model to `gemini-3.7-flash` (the production mapping model per app/core/config.py:584-585), and update the module docstring's model list to match.
13. In backend/tests/unit/test_cost_constants.py, add `test_thinking_tokens_priced_at_output_rate` — a by_stage map whose analyzer stage carries `"thinking_tokens": 10_000` with `models_used` naming `gemini-3.7-flash` must cost exactly `10_000 * 3.75 / 1e6` more than the same stage without thinking tokens — and `test_build_cost_telemetry_stores_thinking_tokens` — `build_cost_telemetry({"llm_token_usage": {"input_tokens": 1, "output_tokens": 1, "thinking_tokens": 7}})` must return `out["llm"]["thinking_tokens"] == 7`.
14. In backend/tests/unit/test_cost_report.py, add `test_row_costs_prices_thinking_tokens` — a telemetry blob whose llm section carries `thinking_tokens` and whose by_stage stage carries the same count must yield a strictly higher `llm_usd` than the identical blob without them, and the returned dict must expose the count under `thinking_tokens`.
15. Run `cd backend && pytest tests/unit/test_cost_constants.py tests/unit/test_cost_report.py tests/unit/pipeline -q --no-cov` and fix any regression before finishing.

## Acceptance

    $ a command that must pass
    > a file that must contain
    ~ something you judge for yourself
    ? nobody established that this can fail before the work

    $?  cd backend && pytest tests/unit/test_cost_constants.py tests/unit/test_cost_report.py -k thinking -q --no-cov
        (not run here: not a plain command — it is not run from here)
    >   backend/app/core/cost_constants.py           thinking_tokens
    >   backend/app/pipeline/runner.py               thinking_tokens
    >   backend/app/pipeline/evidence_classifier.py  thinking_tokens
    >   backend/app/pipeline/evidence_distiller.py   thinking_tokens
    >   backend/scripts/cost_report.py               thinking_tokens
    >   backend/scripts/eval_mapping_model.py        thoughtsTokenCount
    ~   For a check whose mapping stage records reasoning tokens, the stored cost estimate
        and the margin report both rise by exactly those tokens priced at the model's output
        rate, and historical checks that recorded reasoning counts reprice without any
        backfill

State at HEAD, never a diff, so a rebase or a squash cannot break them.

## What this does not fix

These checks can all pass with the following still true. Confirmed by reading the
repository, and named here so nobody reads a green run as a finished outcome.

- Three pipeline stages still report no token usage at all — a limitation the cost module itself declares — so even with reasoning tokens counted, every per-check cost remains a stated floor and every margin a ceiling.

## Discuss these before you act

A second reading of this order, made inside this repository, could not settle the
following. Put them to your agent here before implementing anything — it can open
the code and you can watch it answer. None of them stops the order being worth doing.

- **Is this actually true of this code?** The reader would be told that until the pipeline's totalling step is fixed, no reasoning count survives into the stored record, so fixing the price rules alone accomplishes nothing. That is not true. The mapping stage — the one stage that provably spends reasoning effort on the new models — already writes its reasoning count into the per-stage breakdown that is stored with every check, because its own accumulator keeps that count and the runner copies its whole usage dictionary into the stored record. The order's own corrected price rule reads that per-stage breakdown first, so checks recorded since the model switch reprice with reasoning included even if the totalling step were never touched. Only the grand total and the two smaller stages actually drop the counts.
  Cited: `backend/app/pipeline/runner.py:3017`
- **Is this actually true of this code?** The reader would be told the comparison summary currently shows the production models costed at zero, meaning past comparison runs understated them to nothing. In fact the production models have never appeared in any summary: the list of models the harness runs is fixed in the script with no way to override it from the command line, and all three models on that list are present in its price table, so the zero-price fallback is a branch that is never taken. The real defect is that the harness cannot run the current production models at all — they are absent from its results, not priced at zero in them.
  Cited: `backend/scripts/eval_mapping_model.py:604`
- **Would this step change anything here?** This step changes nothing. The per-stage helper hands the whole stage record to the pricing function, and under this same order's rewritten price rule the function already reads the reasoning count out of that record and prices it inside its loop. The extra argument only feeds a leftover calculation that subtracts what the loop has already seen from what was passed in — and since both come from the same field of the same record, that leftover is always zero, exactly as it is when the argument is omitted. A later reader could mistake this argument for load-bearing drift protection when it is arithmetic that always produces zero.
  Cited: `backend/scripts/cost_report.py:219`

## Cited

- `backend/app/core/cost_constants.py:137` —     return (input_tokens / 1_000_000) * r["input"] + (output_tokens / 1_000_000) * r[
- `backend/app/pipeline/runner.py:151` —     bucket["output_tokens"] += usage.get("output_tokens", 0)
- `backend/app/pipeline/claim_map_analyzer.py:2144` —             if usage.get("thinking_tokens"):
- `backend/app/services/google_ai.py:472` —                         thoughts = usage_meta.get("thoughtsTokenCount", 0)
- `backend/app/pipeline/evidence_classifier.py:889` —             self._token_usage["output_tokens"] += usage.get("output_tokens", 0)
- `backend/app/pipeline/evidence_distiller.py:245` —             self._token_usage["output_tokens"] += usage.get("output_tokens", 0)
- `backend/scripts/cost_report.py:180` —     out_tok = _int(llm.get("output_tokens"))
- `backend/scripts/eval_mapping_model.py:288` —         "output_tokens": usage_meta.get("candidatesTokenCount", 0),
- `backend/scripts/eval_mapping_model.py:815` —         pricing = PRICING.get(model_name, {"input": 0, "output": 0})
- `backend/app/core/config.py:585` —         "gemini-3.7-flash", env="MAPPING_GOOGLE_MODEL"
- `backend/app/core/config.py:118` —         "gemini-3.5-flash-lite", env="GOOGLE_LLM_MODEL"
- `backend/app/pipeline/runner.py:3017` —             **analyzer.get_token_usage(),
- `backend/app/core/cost_constants.py:59` —     "gemini-3.7-flash": {"input": 0.75, "output": 3.75},

