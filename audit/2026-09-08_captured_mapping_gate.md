# Captured SQLite mapping gate — 2026-09-08

## Controlled scope

Used the exact 19 saved evidence objects, classifications, distilled snippets, retained passages and three extracted elements from local live check `49cec0a3-8b93-48de-a526-54be33390e8f`. The saved pipeline result does not retain all full document texts, so this is a mapping comparison, not a reconstruction of full distillation. No new retrieval, reclassification, application writes, model changes or runtime flag activation.

Each sweep uses default/candidate/candidate/default order, resetting map references and states. The candidate changes the opt-in mapping instruction and bounded retained-passage review together. This is not a blinded or held-out evaluation. All results, including failed iterations, remain recorded in `backend/tests/evaluation/passage_quality/sqlite_captured_mapping_results.json`; raw traces are in the corresponding `tmp/sqlite-captured-mapping-*` directories. Input hashes match across sweeps.

## Findings and candidate changes

Raw lexical overlap ranked general WAL background above the retained BUSY exception for one element. Added within-document term-frequency ranking and priority for exact compound identifiers such as error/API/configuration names. No specific domain, product, error code, or factual value is built into the selector. Selection remains bounded to two excerpts per pair and twelve pairs; most possible pairs can remain uninspected.

The identifier-preserving selection supplied the exception, but the model sometimes quoted the preceding benefit while supporting a universal conclusion. Added an opt-in full-proposition instruction: preserve quantifiers, read the full excerpt, and do not ignore explicit exceptions while selecting a quote. Passage contract fingerprint advances to v5 when enabled. Both feature flags remain off.

Final sweep: both default runs map the official page only to support e1 (concurrency premise), missing e2/e3 challenges. Both candidate runs correctly challenge e3 (errors never occur) while preserving e1 support. Only one candidate run correctly challenges e2 (eliminates all scenarios); the other incorrectly supports it despite the supplied exception. **Activation gate fails.** Exact quotations alone do not establish correct relationships.

Four sweeps total: 16 mapping runs, 40 model HTTP requests, 708,236 request characters. Intermediate frequency-only and identifier-only failures are retained. The final candidate matches five of six expected official source/element relationships across two repeats, but that small tuned-case count is not an accuracy estimate or progress score toward 8/10.

## Validation and remaining work

76 focused checks passed, covering passage planning/review, applicability, provenance and fingerprint stability. Final replay matched 185 ok / 1 warn / 13 known fail / 2 unexercised, with no cassette drift (`tmp/quality-replay-passage-ranking-final.log`). The default path is unchanged; no deployment or candidate activation. No goldens or cassettes changed.

Next: resolve the remaining full-proposition relationship error and assess broader held-out cases before activation. Full distillation, decomposition, source independence, PDF pagination, browser/operational acceptance and a human product re-score remain open. The user's 8/10 minimum has not been demonstrated.
