# Passage quality evaluation pack

This is test material, outside the application. Nothing here supplies facts,
rates, dates, publisher overrides or answers to Tru8 at runtime. Historical
fixtures remain historical when real-world values change; no schedule or AI
trigger maintains them.

## Prepared capture

Local pack: `tmp/passage-evaluation-2026-09-08-public/` at the repository root.
Five pages fetched with HTTP 200; the primary trial abstract returned HTTP 203
and remains unavailable. See `manifest.json` for URLs, timestamps and byte
hashes. These are **new public captures**, not the lost inputs of the original
7 September production runs. Response Date/Last-Modified are transport metadata,
not automatically publication or effective dates.

`prepared/inputs.json` contains eight cases with common captured source texts,
elements and selected-passage receipts. Eight additional generated fictional value/date controls are in `prepared/synthetic_inputs.json`, with separate `synthetic_review.json`. Their seed is recorded and can be varied; altered values are never attributed to real publishers. `prepared/review.json` is the unscored
review sheet. `prepared/run_contract.json` specifies the two processing arms
and pins the input hash. `prepared/extraction_report.json` records access and
extraction separately. Raw pages and long source texts stay in the local pack;
they are not application assets or redistributed in the repository.

## Reproduce

From `backend`, using the project Python environment:

```powershell
python scripts/prepare_passage_evaluation.py capture --spec tests/evaluation/passage_quality/spec.json --pack ../tmp/a-new-capture-directory
python scripts/prepare_passage_evaluation.py prepare --pack ../tmp/a-new-capture-directory
```

Capture is the only network step. Prepare checks original-byte hashes and uses
the same extraction method and passage selection as the product, offline.
Existing output directories are refused to protect frozen inputs. No model,
database, account, billing, deployment or application setting is changed.
Imports use the existing backend configuration; run from `backend`.

## Execution and scoring protocol — not yet run

1. Inspect raw versus extracted text first. Label a missing passage as fetch,
   extraction, selection or mapping failure; never merge these denominators.
2. Classify each source once and freeze the shared classification before the
   two model arms. The prepared sources deliberately have no invented tiers.
3. Use the same configured models, elements and source pool in both arms.
   Only the process-local passage flag differs. Run independently with fresh
   copies; no web retrieval, shared mutated objects or prompt tuning between
   arms. Record settings/fingerprint, prompt hashes, raw responses and usage.
4. Alternate arm order and repeat identical-input controls to measure model
   variation. Keep original/reversed cases together in the evaluation set,
   but never show reviewer expectations to either arm.
5. Score source-element relationships, missed decisive passages, false
   directional additions, exact quotations, entailment and temporal scope
   separately. Exact text occurrence is not entailment. Do not assign a quality
   score to an unrun arm or treat inaccessible full text as an extraction pass.
6. Review population, endpoint, comparator, effect metric and follow-up for
   trial examples. Multiple descriptions of SELECT remain one underlying trial.
7. Review source details in the frontend: one interaction to inspect the basis,
   context and uncertainty; test unavailable/stale citations and mobile layout.
8. Before activation, add held-out analogues beyond the supplied eight synthetic
   controls and repeat their generation with unseen seeds. Use fictional institutions clearly labelled as synthetic. Swap which source
   is newer, remove the effective date, add a header clock, negate a date and
   describe a planned change. Never misattribute altered text to a real source.

Model execution remains separately scoped. This preparation does not certify
quality or enable the passage-aware path.

## Initial extraction finding

The newly captured Bank homepage contains the current-rate widget and next
decision date in its raw HTML. The normal extractor returns only 668 characters,
including news/event listings and a rate in a July policy headline. It omits the
next-decision date. The contrasting article extraction includes a site-header
date. These reproduce the *shape* of the original coverage/date risks; they do
not prove the exact old production path or that the new mapper makes the same
error. Check `audit/2026-09-08_passage_evaluation_preparation.md` for next action.
