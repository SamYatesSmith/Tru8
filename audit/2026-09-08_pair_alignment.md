# Pair-local element alignment — 2026-09-08

This is part of the original evidence-mapping work, not evidence that the product has reached the user's 8/10 minimum.

## Diagnosis and change

Inspection of the previous failed SQLite review confirmed that the exception and complete element description were supplied. The remaining failure therefore was not missing source text. Elements were listed separately from pairs, which carried only element IDs. A plausible alignment weakness was judging the source's general benefit rather than the full target proposition.

Each passage-review pair now also carries its exact `element_description`, resolved by element ID. Global instructions, model, budgets, sources, classifier labels and relationship merge policy are unchanged. This tests local context alignment; it does not prove the earlier separation was the sole cause. Candidate-only fingerprint advances to v6. Passage mapping and structured extraction remain disabled.

## Captured real-source regression

Repeated the same 19-source SQLite mapping comparison in default/candidate/candidate/default order. Both candidate runs correctly mapped the official page as supporting e1 and challenging e2/e3. Both default runs still mapped it only to e1. Ten model requests. This is fixed captured mapping, not a new retrieval run, full distillation evaluation or repeated live end-to-end acceptance. Two candidate successes are not a reliability estimate.

## Beyond SQLite

Added eight new synthetic cases covering cache failures, backup conditions, filtering exceptions, motor noise, bounded testing, negative propositions, distinct endpoints and explicit full support. Expectations were declared before candidate execution. Both versions ran twice per case against the identical final input hash.

Baseline: 15/16 complete case runs passed. Candidate: 15/16. All positive-support and explicit-exception expectations passed in the candidate. Its remaining mismatch was the untested-temperature condition: `unrelated` left it unmapped where `context` was expected. The baseline instead called this a challenge in one repeat. Expected answers have not been weakened to count either mismatch as a pass.

The first baseline corpus contained two ambiguous descriptions: “has been demonstrated” was inconsistent with a context expectation where the source explicitly said untested; “did not change” lacked a starting value for judging elimination. These were corrected before candidate testing, and the entire baseline was rerun. Initial results remain at `tmp/pair-alignment-baseline`; the comparable runs are `tmp/pair-alignment-baseline-corrected` and `tmp/pair-alignment-local-description`. The synthetic corpus is new relative to this tuning session, not a real-source held-out benchmark. It cannot establish cross-domain accuracy.

Tracked corpus and results: `backend/tests/evaluation/passage_quality/pair_alignment_cases.json` and `pair_alignment_results.json`. Raw SQLite outputs: `tmp/sqlite-captured-mapping-local-description`. Total requests this checkpoint: 48 synthetic reviews (including the superseded baseline) plus 10 captured mapping requests. No application data writes or deployment.

## Validation and next gate

76 focused checks passed, including exact element-to-pair prompt binding, provenance, applicability and fingerprint stability. Full replay matched 185 ok / 1 warn / 13 known fail / 2 unexercised with no cassette drift (`tmp/quality-replay-pair-alignment.log`). No golden or cassette updates.

Do not activate from these results. Next acceptance must use broader real-source held-out cases and check contextual omissions as well as unsupported directional relationships. Full distillation/decomposition, source independence, PDF pagination, browser/operational acceptance and the human re-score remain open in the original plan.
