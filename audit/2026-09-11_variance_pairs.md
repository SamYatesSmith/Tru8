# Run-to-run variance — two matched pairs measured on 2026-09-11 (free, from public payloads)

**Why this exists.** Wave 0 re-runs produced two pairs of checks on the same claim text within
minutes. Because the per-claim evidence cache (24 h) replayed the first run's pool for the second,
each pair isolates what varies AFTER retrieval on an IDENTICAL pool. Payloads:
`/api/v1/checks/public/<id>?detailed=true`. Companion (code reading): `2026-09-11_variance_sources.md`.

## Pair 1 — wildfire, "2026 is the quietest year for wildfires in Europe by some distance"
`580fd5b4` (09:47 UTC, fresh retrieval, 25 s) vs `12f607d1` (10:00 UTC, cache replay, 10 s, no queryPlan)

| Layer | Same? | Detail |
|---|---|---|
| Pool (URLs) | **identical** 16/16 | cache replay |
| Relevance scores | identical | scored values are cached with the pool |
| Content basis | identical (10 distilled · 3 snippet · 3 full) | distillation output cached too |
| Decomposition | **identical** (2 elements, same wording) | deterministic this time |
| Classification (tier) | **2 of 16 flipped** | Senedd research page primary → commentary; ISRM newsletter commentary → reporting |
| Mapping refs | **13 vs 11**; 0 relationship flips on shared keys; 5 only in A, 3 only in B | courthousenews and Senedd moved e1 → e2; Copernicus, crisis24, newpolis dropped; ISRM added |
| Element states | identical (disputed / disputed) | but thin-sourcing flag present on one, absent on the other |
| NOTE lines | differ | one carried verdict language ("directly contradicting the claim") |

Reading: with pool, scores, distillates and elements all fixed, the classifier still moved 2/16
tiers and the mapper emitted a different reference set (which element a source attaches to, and
whether it attaches at all). Both are model sampling on identical prompts.

## Pair 2 — heatwave, "Europe's recent heatwaves are being caused by declining air pollution rather than climate change"
`a093c7d2` (09:58 UTC, fresh, 3× disputed) vs `bebfa026` (10:04 UTC, cache replay + recovery, disputed/disputed/unresolved)

| Layer | Same? | Detail |
|---|---|---|
| Base pool | **identical** 16/16 URLs, tiers, types, relevance, basis | cache replay |
| Coverage recovery | A none · **B +6 items** | recovery fired only in B, after B's mapping left e3 thin |
| Decomposition | **differs** | A e2 "The causal link between declining air pollution…"; B e3 "Declining air pollution acts as the causal driver…"; element order changed |
| Mapping refs | 18 vs 21; 12 only-A, 15 only-B; 1 relationship flip on a shared key | driven by the different element set |
| e3 supports in B | two recovery items, basis snippet (Washington Stand, Pielke Substack); `relevanceScore` 0.0 is the retrieval composite, which recovery items never receive — they are LLM-scored separately (`llmRelevanceScore`, see runner.py ~2600) | recovery items become the ONLY supports → "unresolved, thin" |
| Nature + AGU papers | B: context on e3 (rel 0.32 / 0.50) · A: unmapped | |

Reading: decomposition sampling changed the element set; that changed which items mapped; the
resulting thin element triggered coverage recovery, which injected six items (the two that became
supports are OPINION tier, LLM-relevance 5/5) that then defined the element's state. Cascade: decomposition → mapping → recovery → state.

## What the pairs establish
1. **Retrieval is not the only churn.** On a byte-identical pool: classifier 2/16 tier flips (pair 1),
   mapper reference-set churn 15–40% (pair 1: 8 of 16 refs differ), decomposition wording churn (pair 2).
2. **Tier flips are state-bearing** (tier feeds `_STATE_TIER_WEIGHTS` and the thin-sourcing flag).
3. **Coverage recovery amplifies**: it runs only when mapping leaves an element thin (>40% unresolved
   or a starved element), so a single sampling difference upstream decides whether six more sources
   enter and whether the element reads `unresolved` on opinion supports.
4. **The evidence cache already gives a free, exact instrument**: any claim run twice inside 24 h
   replays the pool, so classify/map/decompose churn can be measured for model cost only (no search).

## Measurement design (owed, ask before spending)
Run ONE cached pool N=5 times (model calls only, ~3–5p each): record per run the tier per URL, the
element wording, the ref set per element, states, flags. Report: tier flip rate, ref Jaccard between
runs, element-wording edit distance, state agreement. Do it on 3 claims (pair 1, pair 2, NHS). Then
decide: temperature/seed on classify + map (if the API exposes a seed), majority-vote classification
(3 samples → mode) for tier only, decomposition caching by claim hash, and relevance-scoring
recovery items before they can bear state.
