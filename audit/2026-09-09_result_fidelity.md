# Result fidelity correction — 9 September 2026

Continues `7d7c986` on `codex/evidence-quality`. The measured restatement and PDF-fragment cases now pass, but broader integrated acceptance still fails. Candidate settings remain OFF; no production deployment or 8/10 claim.

## Implemented

- The candidate's lexical recital fallback permits an explicit reported study finding with additional finding/design framing in the overlapping sentence. Bare repetition, attributed claims, plans and existing subject/verification protections remain covered. This is a narrow heuristic exemption from substring exclusion, not proof of a finding or independent replication. The default path is unchanged.
- Final scope review now asks for the complete result, including effect measure, and stores an exact excerpt, explanation and input hash for accepted compatible decisions. Missing or malformed responses retain the prior mapping with incomplete review status.
- Context corrections can select exact short source lines by ID. This resolves the observed model reconstruction of broken PDF columns without accepting reconstructed quotations. Lines are never truncated into selectable excerpts. Compatible decisions still require a valid copied result quotation rather than substituting a selected fragment.
- Candidate completion explicitly retains substantively related different-population/endpoint/study sources as context; unrelated sources remain eligible to be unmapped.
- Clarified the distinction between a measured null result and a general account of unproven benefit with an unspecified tested endpoint. The real creatine source exposed this boundary; an initial clarification failed both repeats and is retained in the evaluation history.
- Enabled passage fingerprint advances from v9 to v10. No default fingerprint, model selection, persistent flag, benchmark golden or cassette changed.

## Validation and failed attempts

**194 backend tests passed**, including the PostgreSQL passage/revision integration check, existing recital and temporal protections, default fingerprint isolation, source preservation and malformed quotation handling. Docker Desktop was started to restore the existing local Postgres/Redis services; no database reset occurred.

The first sandbox evaluation returned no model response and was stopped; it is not a model-quality score. The connected initial evaluation passed 34/36 checks: the model correctly identified the PDF's missing result but its reconstructed quote failed exact matching. Exact line selection then passed both PDF repeats. The subsequent receipt inspection found truncation of selected long lines; the final implementation removes that truncation and restricts selection to contextual corrections.

Final fixed-source evaluation: **38/38 relationship checks across two repeats** (24 original broader checks plus 14 result controls). All source inputs preserved. Controls cover the real PDF fragment and unspecified-endpoint source, equivalent quantitative measures, true null findings, plans, different measures and attributed reporting of a trial's result. This is a diagnostic set used during development, not a human-held-out benchmark. The original 20/24 criteria were not weakened.

Default replay: **185 ok / 1 warn / 13 known fail / 2 unexercised**, matching the established baseline, with no cassette-miss/drift failures. Expected exit 1; log `tmp/quality-replay-result-fidelity.log`. This is default-path regression evidence, not candidate quality acceptance.

## Integrated evidence and remaining failures

Three fresh local reports completed, using public-web retrieval and local persistence/direct owner/public reads:

| Case | Local check ID | Sources | Seconds |
|---|---|---:|---:|
| Venus | `4cf2c134-1073-422c-8589-612b36d8a993` | 14 | 43 |
| Creatine | `c8388b2d-e0cf-4e95-8694-491e55f6a090` | 14 | 44 |
| SELECT | `45380df8-5ba0-45ea-9f26-32e86b9e54f9` | 18 | 154 |

All owner/public source URL sets and snapshot identities matched. These runs exposed the final quotation and creatine boundary corrections; they are **not integrated acceptance of the final code**. The last scope review was replayed against their frozen pools, leaving persisted reports unchanged:

- **Creatine:** the unsupported prevention challenge becomes context, preserving its original interpretation. Its original persisted report remains disputed; the final frozen re-review is contextual.
- **Venus:** the final re-review reached its 25-second bound and disclosed `failed`, retaining its prior supported map. Do not count this as successful final review.
- **SELECT:** 12 of 15 directional pairs assessed; three remain outside the existing cap. Two assessed sources (`ev-e034ece5a149`, `ev-49522d797c58`) still receive compatible/support labels for the full 20% assertion although their supplied blocks establish only a qualitative MACE benefit. The second also reports a different 37.8% inflammatory-marker result. Matching trial/population and an exact quote still do not establish the complete asserted effect size. The original methods-fragment case is fixed, but this broader fidelity failure is not.

The fresh SELECT scope call took about 5.7 seconds; its 154-second total is not attributable to that call alone. Live pools differ from yesterday; these are not controlled speed or source-count comparisons. Passage coverage remains incomplete, and the capped/failed final reviews remain visible. No browser/HTTP/worker or production acceptance was performed.

## Next bounded work

Use `qualitative_effect_failures.json` as the next predeclared failure pair. Review how complete-assertion grounding is represented: the amount, measure and endpoint need evidence together, rather than a model declaring the source generally compatible. Preserve equivalent-measure and actual-null controls, sources and original receipts; do not infer correctness from exact numerical occurrence alone. Resolve review completeness/timeouts separately and then rerun integrated acceptance on the final implementation. Human review, operational reconciliation and source-role/independence acceptance remain open.

## Reproduction

- Runner: `backend/scripts/evaluate_result_fidelity.py --output <fresh directory>` from `backend` with the existing test runtime and `PYTHONPATH=.`. Two repeats; local process flag only; stops on a missing response. This makes paid calls through the configured providers.
- Tracked protocol/history/results: `backend/tests/evaluation/passage_quality/result_fidelity_results.json`.
- Frozen actual sources: `result_fragment_failure.json`, `unestablished_endpoint_failure.json`, `qualitative_effect_failures.json` in the same directory.
- Raw final controlled outputs: `tmp/result-fidelity-signoff/`; intermediate attempts remain in the directories named in the tracked history.
- Fresh reports: `tmp/integrated-result-fidelity-2026-09-09/`; final frozen re-review: `tmp/integrated-result-fidelity-final-review/`.

Commercial assessment and unrelated working-tree changes remain separate.
