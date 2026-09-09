# Quantitative result guard (candidate) — 9 September 2026

Track Q phase 2, first correction. Continues the [result fidelity correction](2026-09-09_result_fidelity.md), whose remaining failure pair is frozen in `backend/tests/evaluation/passage_quality/qualitative_effect_failures.json`. Candidate-only: everything here sits behind `ENABLE_PASSAGE_MAPPING` (OFF), inside `relationship_scope_review.py`. The default path is untouched.

## The failure

Claim: *In the SELECT trial, semaglutide reduced major adverse cardiovascular events by 20% relative to placebo …* Two sources were retained as **support** after the final scope review:

- `ev-e034ece5a149` (news-medical.net): the quoted result is "Semaglutide reduced MACE incidence in the SELECT trial." No figure.
- `ev-49522d797c58` (peptide science daily): the quoted result is a qualitative MACE sentence; the only figure on the page, 37.8%, is hsCRP, a different endpoint.

Matching trial, population and endpoint plus an exact quote still do not establish the complete quantitative assertion. Two prompt tightenings had already failed to make the model hold the line (recorded in the result-fidelity history), which is the NF-11 lesson again: a fragile rule needs a mechanical form.

## The rule

Beside the existing named-study identity guard, and in the same shape: when the model returns `compatible` for a **supports** pair and the element states a quantitative effect, the quoted result must carry one of that figure's accepted forms. Otherwise the decision becomes `unknown` on the `result` dimension, the reference is retained as `context`, and the receipt records `decision_basis: quantitative_result_not_quoted` with the model's own decision beside it.

Accepted forms are generated mechanically, never inferred: the percentage as written and its spelled variants (`20%`, `20 percent`, `20 per cent`, `20 percentage point`), and the ratio forms of a relative change (`0.80`, `0.8`, `1.20`). A ratio stated in the element yields the ratio and the percentage it expresses. This is a presence check, not arithmetic proof; whether a figure is absolute or relative, or on the right endpoint, remains the model's judgement, which the prompt already demands. Challenges are not held to a figure: a null result on the claimed endpoint needs none. Elements that state no figure are untouched.

## Why not a prompt

The prompt already says "a stray matching number does not establish the asserted effect" and "quote the actual result, including the portions needed for the complete assertion". The model quoted a result without the figure and called it compatible twice. A guard that reads the quote is the only form that cannot be talked out of it, and it records that it overrode the model rather than hiding it.

## Evidence

- Unit tests drive the real parser with the frozen pair (both references → `context`, both receipts carry `quantitative_result_not_quoted` and `model_decision: compatible`, sources byte-identical), six form controls (risk ratio 0.70 ↔ 30%, "30 percent", hazard ratio 0.80 ↔ 20% all pass; 37.8% on another endpoint and a bare "reduced admissions" do not; an element with no figure is untouched), and a null-result challenge left alone. `test_relationship_scope_review.py`: 53 collected, all pass (with the second rule below).
- The candidate fingerprint moves `v10 → v11` (flag-only; verification reads the stored fingerprint).
- `scripts/evaluate_result_fidelity.py` now includes the pair as two result cases (`qualitative_effect_e034ec`, `qualitative_effect_49522d`) with the fixture's hash in the protocol.
- **Paid run 1 (founder-approved, 2026-09-09, `tmp/result-fidelity-quant-guard-2026-09-09/`): 39 of 42.** The frozen SELECT pair passed both repeats (4/4) and all nine result controls passed both repeats (18/18), so the guard does what it was built for. The three failures are elsewhere and are NOT the guard: on three of eight null-result **challenges** in the broader controls (`named_trial` ×2, `endpoint` ×1) the model returned `mismatch` on the `result` dimension ("the claim says reduced, the source says identical rates") and the review demoted the challenge to context. That is the one demotion the review must never make: a contrary result on the result dimension IS the challenge. 38 model responses; token usage was not recorded by the evaluator on this run (it is from run 2 on).

## Second rule: a contrary result is the challenge

Same shape again: when the model returns `mismatch` on dimension `result` for a **challenges** pair, the decision is treated as `compatible` (the challenge stands) and the receipt records `decision_basis: contrary_result_is_the_challenge` with the model's decision beside it. Only the result dimension is exempt: a challenge from the wrong population, endpoint, study or measure is still scoped. A support whose quoted result contradicts the element still becomes context; the review never flips a relationship. Tests drive the exact failing decisions through the real parser (both challenges retained), the other dimensions still scope, and a support/result mismatch still demotes.

- **Paid run 2 pending founder go-ahead** (same protocol; token usage now recorded). The evaluator (two repeats × 4 broader mapping cases + 9 result cases) is the acceptance step for this correction; it makes model calls and is held for the founder's go-ahead under the ask-before-every-paid-run rule. Estimated well under 10p at the recorded token volumes.

## Remaining, after this

Review completeness (Venus's final review hit its 25 s bound; SELECT reviewed 12 of 15 pairs), source-role and study-independence grouping (alternate hosts of one study are one study), then the integrated candidate re-run on the final code.
