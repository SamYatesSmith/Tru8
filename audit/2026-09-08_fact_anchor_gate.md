# Explicit source-time anchor gate

The measured historical-rate and page-clock failures are now scoped to context in
the evaluated candidate. **Both rollout switches remain OFF.** This is a narrow
necessary-condition check, not a general applicability or entailment solution.

## Implementation

`fact_applicability.py` reads explicit day scope from an element's `on`/`as of`
wording, or a leading claim-level `As of` clause. For these elements, a directional
reference needs a date anchor in retained extraction text: a matching explicit day,
or an explicit effective/in-force-from interval covering that day. Publication,
capture time, generated facts and the machine clock cannot supply it.

The retained sentence must overlap the element in topic words or a quantity with
its unit. Dates are removed before matching quantities; a number alone cannot link
topics. This is a lexical prerequisite, **not a verified same-fact interpretation**.
Planned, conditional and negated interval starts cannot establish an effective
interval. A negated statement explicitly anchored at the target day can still be
dated evidence: relationship judgement remains separate. Clipped sentence edges
cannot silently lose qualifications and become accepted anchors.

The shared scope-gate path runs before state derivation in initial mapping,
completion and recovery, and after passage additions. Both support and challenge
are scoped symmetrically. Missing anchors preserve references as context, rewrite
their reason, and retain an exclusion receipt including the previous reason and
required day. Existing gate order is preserved. The opt-in fingerprint is v4;
disabled requests and behaviour remain unchanged.

The EVIDENCE and GAPS views display the exclusion reason with source and element
names, including when passage review did not run. These components also serve
shared reports. Earlier receipts are not presented as current exclusions after a
reference becomes directional. The source's contextual relationship reason is also
updated. No receipt is invented for an old report.

## Evaluation and correction

1. Full fixed-source sweep: 16 cases × 4 configurations, 64 arms, 137 model requests,
   1,294,755 request characters. Same models, source captures and classifications.
2. This removed the original historical-rate/date errors but initially downgraded
   a valid planned-change challenge: its source repeated the quantity/unit rather
   than the element's noun. That failure was retained in the evaluation record.
3. Quantity-with-unit matching corrected that loss without using any fixture value
   in runtime code. Two planned-change cases were rerun across four configurations:
   8 arms, 14 requests, 125,668 request characters.
4. Original and final gate predicates were compared on all 88 day-scoped
   source/element inputs in the full sweep. Only the planned-new-value source
   differed (four arms). The correction run covers it and its reversed control.
   Boundary/conditional hardening had no effect on the other recorded inputs.

Final evaluation records assemble **56 original arms and 8 correction arms**; this
is not described as one new 64-arm run. Per-file origin paths and hashes are in
`fact_anchor_summary.json`. The original failed planned-change result remains in
`fact_anchor_initial_scores.json`; it has not been overwritten.

The expanded offline expectations cover **27 conditions across 13 cases**. The
combined structured/passage configuration passes all 27 after correction:

- Historical rate/schedule and article-header assertions remain context; a rate
  discrepancy does not challenge a separate decision-date element.
- Page clocks do not establish the new or reversed fictional historical value.
- Explicit effective changes retain support/challenge in both directions.
- Dated negation and planned-change records retain their challenge to the claimed
  new value. Older point-in-time values are not silently carried forward.
- SQLite concurrency/BUSY directional evidence and the unrelated control survive.

These are manually reviewed fixed-source assertions, **not an accuracy percentage**.
The remaining three cases were inspected but are outside this gate's scored checks:
SQLite read-only evidence remains linked; SELECT overgeneralisations remain
challenged; scoped SELECT population/endpoint support is retained while its effect
metric remains context. No improvement claim is made for that unresolved metric.

All **29 retained citations** in the assembled records pass exact quote, offset and
source-version checks. Those checks still do not certify inferred relationships.

Provider usage: full sweep 349,275 tokens; correction 36,745 tokens, total 386,020
(286,095 prompt, 34,039 candidate-output, 65,886 thinking). These are usage counters,
not a billing reconciliation. No retrieval, decomposition, DB writes, model change,
persistent setting change or deployment was part of the model experiment.

## Validation and limits

Backend: 97 focused checks passed, including symmetric gating, disabled behaviour,
initial state recomputation, passage bypass protection, varied values/dates/units,
clipped qualifications, existing temporal gates, persistence and evaluator contracts.
Web: full 173-test suite passed; after filtering stale receipts, seven affected
tests and TypeScript passed. Final default replay matched **185 ok / 1 warn /
13 known fail / 2 unexercised**, zero cassette drift
(`tmp/quality-replay-fact-anchor-final.log`). No golden/cassette changes.

This gate recognises a limited set of English full-day expressions and explicit
intervals. Implicit/relative dates, multiple periods, paraphrases, complex conditions,
cross-sentence context, semantic subject identity and unseen layouts remain open.
Lexical or quantity overlap can still link different facts; accepted anchors are
never labelled proof. Bounded passage selection can omit valid temporal evidence.
Consequently both false admissions and conservative exclusions remain possible.

Next acceptance work is broader unseen-source and temporal-language testing,
including unsupported date forms and omitted context. Do not enable either rollout
switch solely because this targeted gate passes. The original decomposition,
source-independence and end-to-end/human output-quality acceptance work remains.

## Records

- Raw runs: `tmp/fact-anchor-evaluation/`, `tmp/fact-anchor-plan-correction/`.
- Assembled read-only comparison: `tmp/fact-anchor-combined/assembly.json`.
- Offline predicate comparison: `tmp/fact-anchor-equivalence.json`.
- Tracked expectations/results: `backend/tests/evaluation/passage_quality/fact_anchor_*.json`.
- Run the existing `score_passage_regressions.py` with the assembled directory and
  `fact_anchor_expectations.json`; it exits 0 for the combined arm. Disabled control
  arms still expose known errors and are not required to pass this rollout check.
