# Competing-source acceptance pilot — 2026-09-08

Continues the [real-source pilot](2026-09-08_real_source_pilot.md) and the original route from a 6/10 report to a minimum 8/10. This phase tests long documents, competing software versions and a planned event against a completed-event account. It does not establish a finished-report score or authorise activation.

## Fixed comparison

Expectations and source URLs are in `backend/tests/evaluation/passage_quality/competing_source_pilot.json`; compact measured results and capture hashes are in `competing_source_pilot_results.json` beside it. Sources were frozen before the comparison. PostgreSQL 18 and 9.0 isolation documentation contain 24,235 and 14,033 extracted characters; NASA's planned DART announcement and retrospective contain 4,589 and 11,738. Three documents exceed the default 8,000-character distillation input. No padding was added.

Each case ran default/candidate/candidate/default against the same captured full text with actual configured distillation and mapping models. Evidence IDs use the production URL-hash shape. Elements and primary-source labels were fixed manually. Capture used BeautifulSoup with script/style/navigation/header/footer removal and main/article/body text, not the application HTML extractor. Retrieval, decomposition, classification, database persistence, workers and browser rendering were not exercised. Runtime flags remain OFF; no factual constants or publisher-specific rules were added.

The nine expectations cover three version-specific propositions and two DART propositions. A non-directional expectation accepts context or no reference. PostgreSQL 18's relationship to the historical 9.0 implementation element is deliberately unscored because a historical note could justify different interpretations. These are nine checks repeated twice per arm, not eighteen independent claims.

## Findings and corrections

The initial comparison scored default 14/18 and candidate 15/18, but the aggregate concealed a regression: the candidate rejected the retrospective's explicit completed-event date in both repeats. The original retained sentence says the impact occurred “on the evening of September 26, 2022.” The exact-date grammar accepted `on DATE`, but not part-of-day phrasing. The sentence was complete inside its retained passage; this was not a clipping failure.

The generic grammar now accepts `on the morning/afternoon/evening of DATE`. Tests ensure before/after/eve wording does not become a same-day anchor. No mission, publisher, date or changing factual value is encoded. The disabled candidate fingerprint advances from v6 to v7.

Repeating both arms after that correction produced:

| Case | Default repeat 1 / 2 | Candidate repeat 1 / 2 |
|---|---|---|
| Competing PostgreSQL versions | 4/5, 4/5 | 5/5, 5/5 |
| Planned versus completed event | 3/4, 3/4 | 4/4, 4/4 |
| Total relationship checks | 14/18 | 18/18 |

The default omitted the PostgreSQL serialization-anomaly challenge and the retrospective's technology-test support in both repeats. The candidate recovered those links without counting the old software version as directional evidence for the current-version propositions. Source counts were not reduced by either correction.

Reading explanations exposed an additional failure hidden by those scores: both candidate repeats labelled the planned announcement `context` after the temporal gate, while retaining model wording that claimed it confirmed a successful impact. Candidate temporal demotions now replace that wording with the gate's actual period-mismatch explanation and retain `original_reasoning` in the audit receipt. This change is under the existing candidate flag; default behavior is unchanged. The explanation describes the gate's period reading, not a general ability to understand event tense.

The final explanation correction was verified deterministically against both saved model outputs: restore the pre-gate relationship recorded in each receipt, run the actual gates with the saved evidence/citations, and verify context, corrected wording, original-reason preservation and unchanged citations. This was not another model comparison. Parser tests cover supports and challenges, candidate OFF behavior and repeat application. Further model calls could still produce different upstream output.

## Validation and boundaries

- 105 focused unit/integration tests passed, including date applicability, passage mapping, provenance, fingerprint stability and temporal parser wiring.
- Final full replay: 185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift (expected exit 1). Goldens and cassettes unchanged. Log: `tmp/quality-replay-competing-reason-final.log`.
- Each eight-run live sweep used 20 HTTP requests; request-character totals are recorded in the compact results. No production data, deployment, model setting or billing behavior was changed.
- Local raw captures/maps: `tmp/competing-source-pilot/` and `tmp/competing-source-pilot-date-correction/`; explanation verification is `reason-verification.json` in the latter. Their SHA-256 hashes are retained in the tracked summary; raw captures are local artifacts.

The next acceptance step should be a bounded finished-report comparison across several claim types, including source-role accuracy, decomposition and explanation quality. These controlled mapping tests have now covered the missing long/competing/date dimension; repeating this small set is not a substitute for that broader review. Candidate activation, the 8/10 assessment, PDF pagination and browser/worker acceptance remain open in the original plan.
