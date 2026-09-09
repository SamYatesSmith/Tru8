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

- Unit tests drive the real parser with the frozen pair (both references → `context`, both receipts carry `quantitative_result_not_quoted` and `model_decision: compatible`, sources byte-identical), six form controls (risk ratio 0.70 ↔ 30%, "30 percent", hazard ratio 0.80 ↔ 20% all pass; 37.8% on another endpoint and a bare "reduced admissions" do not; an element with no figure is untouched), and a null-result challenge left alone. `test_relationship_scope_review.py`: 47 passed.
- The candidate fingerprint moves `v10 → v11` (flag-only; verification reads the stored fingerprint).
- `scripts/evaluate_result_fidelity.py` now includes the pair as two result cases (`qualitative_effect_e034ec`, `qualitative_effect_49522d`) with the fixture's hash in the protocol.
- **Paid confirmation not yet run.** The evaluator (two repeats × 4 broader mapping cases + 9 result cases) is the acceptance step for this correction; it makes model calls and is held for the founder's go-ahead under the ask-before-every-paid-run rule. Estimated well under 10p at the recorded token volumes.

## Remaining, after this

Review completeness (Venus's final review hit its 25 s bound; SELECT reviewed 12 of 15 pairs), source-role and study-independence grouping (alternate hosts of one study are one study), then the integrated candidate re-run on the final code.
