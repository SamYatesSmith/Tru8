# Integrated passage evaluation — 8 September 2026

**Decision: keep both rollout switches OFF.** Extraction and quotation recovery
show useful gains, but the new path is not ready to activate: temporal interpretation
and element-specific entailment still produce misleading relationships.

This evaluates the original improvement plan's extraction, mapping completeness,
traceable basis and temporal-scope targets. It introduces no maintained fact values,
institution-specific rules, AI triggers or model replacements.

## Method

16 scenarios × 4 configurations = **64 completed arms**:

| Configuration | Extraction | Distillation and passage review |
|---|---|---|
| s0p0 | Legacy | Legacy |
| s1p0 | Structured supplement | Legacy |
| s0p1 | Legacy | Passage-aware |
| s1p1 | Structured supplement | Passage-aware |

Source bytes were hash-checked. Shared classifications were generated once and
frozen across arms. Original/reversed claims were included; arm order alternated by
case. Eight fictional controls cover changed values, page clocks, negation and future
plans. Reviewer guidance was not supplied to models. Where extraction produced
identical text, those arms also expose model variation rather than extraction gain.

Configured models were unchanged: `gemini-3.5-flash-lite` for classification,
distillation and completion; `gemini-3.7-flash` for mapping, with the existing fallback
configuration retained. Responses and model-use metadata were saved. No live source
retrieval, decomposition, database writing, frontend operation or deployment occurred.
The fixed elements and leading snippets make this a controlled mapping experiment,
not a complete reproduction of live semantic-snippet retrieval or production runs.

SELECT has FDA material only: the unavailable trial abstract is explicitly missing.
These are fresh saved captures, not yesterday's exact pipeline inputs. Timings were
collected during other local verification and are not a production speed benchmark.

## Live defect found and corrected

The initial sweep stopped after 18 completed arms. Of its 8 passage-enabled arms,
2 failed with `invalid_response`, 3 were partial and 3 complete. The failing responses
used the original element JSON structure: the passage prompt contained that schema
as well as instructions to replace it with a pair schema. Existing validators safely
rejected the unexpected shape, but this prevented useful quotation linking.

The correction removes the competing element-output contract, retains the shared
relationship rules, and gives `passage_review` a dedicated provider response schema.
No semantic or exact-quotation guard was weakened. Its enabled pipeline fingerprint
is v2; default-off prompts/fingerprints remain unchanged. The corrected complete sweep
reused the same classifications. Initial and corrected results remain separate.

## Results and remaining failures

| Area | Observed result | Assessment |
|---|---|---|
| SQLite BUSY | Passage-aware arms retain the exception relationship with quotations; one older-path identical-text run misses it | Useful recovery; model variation is visible |
| Reversed SQLite claim | Both older arms miss the possibility relationship; both passage-aware arms retain it | Useful recovery in both claim directions |
| Read-only SQLite | Passage-aware arms connect the main documentation as well as release notes | Improved mapping coverage; not additional independent evidence |
| Bank decision date | Structured extraction supplies the missing decision block | Extraction gain confirmed |
| Bank cross-element mapping | s1p1 adds the rate-level article as a challenge to the separate decision-date element | **False directional addition; fails acceptance** |
| Temporal applicability | Real article header date and fictional page clock are treated as fact dates | **General temporal failure; fails acceptance** |
| SELECT | Overgeneralised population/endpoint/effect claims are challenged in all arms; scoped population coverage improves, effect-metric coverage varies | Mixed; primary trial text and full semantic grading still missing |
| Unrelated sources | No relationships added in any arm | Control passes |
| Negation/future plans | New values are challenged or withheld; older-value cases can remain contextual | More cautious behaviour; not a broad accuracy claim |

Among 32 corrected passage-enabled arms, 15 report complete, 15 needs_review and
2 partial. These are **processing statuses**, not correctness grades: the false Bank
addition appears in a `complete` review. Twenty-one pair disagreements are exposed
instead of silently overwriting earlier relationships; two pair rows are rejected.

All **40 retained citations** pass exact-text/source-version checks. That validates
their textual basis, not the relationship inferred from it. The Bank error illustrates
why those two checks must remain separate. No overall semantic-accuracy percentage
or 8/10 product re-score is justified by this targeted, non-blinded review.

## Next implementation target

1. Require evidence to address the exact element/facet before accepting a directional
   addition. A different rate value cannot contradict a scheduled decision date.
2. Represent the applicability of the cited fact separately from publication,
   retrieval and page/header clocks. Unknown applicability must be treated honestly
   in both directions; no domain override or maintained number can resolve it.
3. Turn the observed failures into general regressions, vary fictional values/dates
   and add unseen page layouts. Re-run on the same source pool before activation.

Source independence and decomposition refinements remain in the original register;
they were not evaluated by this fixed-element experiment.

## Evidence and validation

- Harness: `backend/scripts/run_passage_evaluation.py`; dry-run by default,
  explicit `--execute`, request/character limits, hash checks, frozen-classification
  reuse and a STOP file between requests. No application writes or persistent flags.
- Initial records: `tmp/passage-factorial-evaluation/` (operator-interrupted).
- Corrected records: `tmp/passage-factorial-corrected/` (64/64 arms completed,
  140 requests, 1,186,347 request characters).
- Tracked summary with per-output hashes and relationship counts:
  `backend/tests/evaluation/passage_quality/factorial_summary.json`.
- Across both sweeps, 188 saved provider responses report 331,099 prompt tokens,
  42,706 candidate-output tokens and 68,348 thinking tokens (442,153 total). An
  interrupted in-flight request may be absent; this is not billing reconciliation.
- 42 backend checks passed, including schema wiring, unchanged validation, evaluator
  isolation/budgets and real PostgreSQL passage persistence. Default-off replay:
  **185 ok / 1 warn / 13 known fail / 2 unexercised**, zero cassette drift. No golden
  updates or production activation.
