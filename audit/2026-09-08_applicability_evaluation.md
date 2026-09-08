# Element and time applicability: candidate evaluation

The candidate improves two observed errors in a small controlled comparison, but
**does not meet acceptance**. Both `ENABLE_PASSAGE_MAPPING` and
`ENABLE_STRUCTURED_EXTRACTION` remain OFF. No deployment or model change.

## Implemented candidate

One shared addendum applies to initial, batch, recovery, completion and passage
mapping when passage mapping is enabled. It distinguishes the exact element from
sibling propositions and fact-effective time from publication, capture and page
clocks. Unknown applicability requires context; explicit changes and timeless
evidence retain directional relationships. No institution, source domain, maintained
date or value is used in the runtime rules. The enabled fingerprint contract is v3;
default-off requests and fingerprints retain their previous behaviour.

This remains a **prompt-based candidate**, not a mechanical entailment guarantee.
Existing source receipts expose dates without establishing applicability. The model
can still ignore these instructions. We have not implemented a reliable semantic
admission mechanism, and the results below prevent treating this phase as resolved.

## Controlled comparison

Five saved cases, each with four extraction/passage configurations: 20 arms,
47 provider requests, 440,796 request characters. Original source versions and
classifications were reused. The configured models are unchanged. This exercises
fixed-element mapping, not retrieval, decomposition or a full product check.

Combined structured/passage arm, compared with the previous saved sweep:

| Target | Previous | Candidate |
| --- | --- | --- |
| Fictional page clock establishes fact date | Incorrect support | Context: fixed in this sample |
| Rate difference challenges decision-date element | Incorrect challenge | No directional link: fixed in this sample |
| Undated real-page rate establishes historical rate | Incorrect support | Still incorrect |
| Article header establishes historical rate | Incorrect challenge | Still incorrect |
| Undated current schedule establishes prior-day schedule | Incorrect support | Still incorrect |
| Explicit effective change | Direct support | Retained |
| SQLite concurrency and BUSY positive controls | Direct support | Retained |
| Unrelated source | No directional link | Retained |

Eleven manually reviewed assertions cover these five cases. The previous combined
arm fails five; the candidate fails three. These counts are **not overall accuracy**:
the sample is targeted, not blinded, and one repeat cannot separate prompt effect
from model variability. The new fictional value/date layouts have not yet been
tested. The remaining real-page errors affect initial mapping as well as passage
review, so rejecting only newly added passage references would be insufficient.

## Evaluation protection

`backend/scripts/score_passage_regressions.py` compares final stored relationships
against offline expectations. It ignores processing-status badges and exact-text
success as semantic acceptance signals. Positive controls prevent blanket context
from passing. Missing cases/elements and mismatched captured-source or element
versions fail. The CLI exits 1 if the combined arm fails; it does not automatically
change runtime switches. Passing this limited gate would still not authorise rollout.

Expectations and results are tracked under
`backend/tests/evaluation/passage_quality/applicability_{expectations,baseline_scores,candidate_scores}.json`.
Expectations contain fixture source IDs and manual review decisions, never runtime
fact values, and are not passed to models. Results identify exact output hashes.

Reproduce the offline check from `backend`:

```powershell
python scripts/score_passage_regressions.py --run ../tmp/passage-applicability-evaluation --expectations tests/evaluation/passage_quality/applicability_expectations.json --output ../tmp/applicability-score.json
```

Raw evaluation records: `tmp/passage-applicability-evaluation/`; completed plan,
20 arm outputs and 47 sanitized request/response records. Reported usage totals:
88,733 prompt, 8,646 candidate-output, 14,352 thinking tokens; 111,731 total.
These are provider usage counters, not a monetary billing reconciliation.

## Validation and remaining implementation

44 backend checks passed, including provider instruction gating, passage persistence,
fingerprint compatibility, evaluator isolation, and semantic-check failure behaviour.
Default replay: **185 ok / 1 warn / 13 known fail / 2 unexercised**, zero cassette
drift (`tmp/quality-replay-applicability.log`). No golden/cassette changes.

Next implement an explicit fact-applicability assessment with validated source
anchors and conservative admission, applied consistently to initial relationships
and passage additions. Preserve visible uncertainty when applicability is absent;
do not let a self-labelled model assessment count as proof. Keep exact-text
validation separate from entailment. Then repeat these failures plus reversed,
negated, planned-change and unseen fictional controls before accepting the change.
Any user-facing applicability receipt must be reflected in source detail and shared
reports when implemented; this candidate adds no new UI state to display.
