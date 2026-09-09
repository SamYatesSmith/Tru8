# Integrated candidate run 3 — 9 September 2026

Track Q phase 2 acceptance on the final phase-2 code (`25e7ac2`): three local reports with live retrieval and the candidate flag on inside the process only (`tmp/integrated-run3.py`, a copy of Codex's `tmp/integrated-result-fidelity.py` with a fresh output directory). Founder-approved paid run. Outputs: `tmp/integrated-run3-2026-09-09/{venus,creatine,select}/`. Nothing deployed; both flags remain OFF in every persistent configuration.

## Results

| Case | Check | Sources | Seconds | Element state | Directional refs kept | Scope review |
|---|---|---:|---:|---|---|---|
| Venus rotation vs orbit | `8d51b18d-4242-4c8f-aacb-cccc41994148` | 13 | 72 | supported | 4 supports (3 echo copies + 2 recitals scoped) | 3 of 4 assessed, one call, 2.9 s |
| Creatine prevents Parkinson's | `97a8d476-9480-443e-98d0-8e682b2b3672` | 19 | 74 | contextual | 0: all 6 progression-trial challenges scoped to context by the review, 2 echo copies | 6 of 6, one call, 2.9 s |
| SELECT 20% MACE reduction | `965bd01f-4c7e-4890-ab50-2c5ca9a5ee6e` | 16 | 40 | supported | 7 supports, 2 echo copies scoped | 7 of 7, **two calls** (6 + 1), 3.2 s and 1.4 s |

Owner and public source URL sets and snapshot identities agree in all three. Every source record is retained; nothing deleted.

## What the corrections did on live pools

- **All seven SELECT supports quote the 20% figure** in the scope review's accepted quotation (checked mechanically against the accepted forms: `20%`, `20 percent`, `0.80`…). The news-medical source that motivated the quantitative guard (`ev-e034ece5a149`) is in this pool again and was mapped `context` at the initial pass, the mapper itself noting it "does not state the specific 20% reduction figure"; the guard did not need to fire and stands as the backstop.
- **Creatine reads `contextual`, not `disputed`**: the six challenges were progression trials in diagnosed patients and the review scoped each with an onset-versus-progression explanation. This is Astra's finding 3 landing ("absence of prevention evidence should not be treated as direct evidence of no effect"); the earlier default run had read it as disputed.
- **The split review ran on SELECT** (7 pairs → calls of 6 and 1) with both calls completing; Venus's earlier 25 s timeout did not recur (one call, 2.9 s).
- **The same-study gate did not fire** on any of the three pools; nothing here verifies it beyond its unit tests.
- Passage review coverage: Venus 5 of 8 pairs assessed (`needs_review`), creatine and SELECT 11 of 11 (`needs_review` for conflicts, not gaps). Coverage caps remain disclosed rather than closed.

## Limits

Three cases, one run each, live pools that differ from the 2026-09-08 and morning runs (Venus 72 s and creatine 74 s against 43 s and 44 s that morning are retrieval variance, not a regression signal). Not a controlled comparison, not a human-reviewed benchmark, not browser or worker acceptance. The 8/10 gate's human review of directional relationships is still owed.

## Cost

From the three checks' `cost_telemetry` (a **partial floor**: captured LLM stages plus measured search units, excluding extract, relevance scoring and the query stage): venus $0.045, creatine $0.061, SELECT $0.064 — **$0.17 in total, about 13p**, over the 5–8p estimated before the run. Tokens across the three: 108,786 input, 17,057 output, 4,001 thinking. The estimate had priced the model calls and forgotten the search units; the next estimate for a live run starts from this figure.
