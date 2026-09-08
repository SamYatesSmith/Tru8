# Evidence evaluation preparation — 8 September 2026

User authorised preparing the evaluation pack, with an explicit constraint:
no maintained rates/current answers, institution-specific runtime rules or AI
triggers. This checkpoint changes only evaluation tooling, test data and docs.
The application never imports this pack.

## Deliverable

- Local complete capture directory: `tmp/passage-evaluation-2026-09-08-public`.
- Tracked specification, capture hashes, extraction summary and instructions:
  `backend/tests/evaluation/passage_quality/`.
- Tool: `backend/scripts/prepare_passage_evaluation.py`; capture performs six
  public GET requests, prepare works offline on those bytes and refuses changed
  hashes or replacement output directories. No model calls or database writes.
- Eight source-based cases: SQLite concurrency/BUSY in both directions, read-only
  version/conditions, original/reversed historical Bank claim, SELECT scope in
  both directions, and unrelated evidence. Expected review guidance is separate
  from the model-input file; scores are null/not-run.
- Eight generated fictional cases vary values/dates and reverse the claim over
  identical sources. Controls cover an older record keeper versus a later change,
  a page-header clock, negation and a future plan. The seed is recorded; new seeds
  produce different values. These are test scenarios, not a runtime fact store.

Five pages returned HTTP 200. The SELECT abstract endpoint returned HTTP 203 and
was not accepted as a successful capture. FDA text is available; the trial's full
text was not fetched. No substituted search summary is passed off as captured
trial text. Source availability remains explicit in each affected case.

These are new public captures, **not** yesterday's exact production inputs. The
original analysis date must not be inferred from the new retrieval timestamp.
Historical expectations will remain historical; fixtures require no updates when
real-world values change. Raw HTML and full extracted content remain local; hashes
and source references are committed for provenance.

## Finding before model evaluation

Using Tru8's existing extraction method on the saved Bank homepage returns 668
characters. The result consists of news/event material, including a rate in a July
policy headline, but excludes the current-value widget and next-decision date
present in the raw HTML. The comparison article's 780-character extraction includes
a site-header date. This independently exposes extraction/date-contamination risks
matching the shape of the original assessment. It does not establish that the old
production run used identical bytes or that the new model path makes the same error.

Sources: [Bank homepage](https://www.bankofengland.co.uk/),
[comparison article](https://londondaily.com/bank-of-england-holds-rates-steady-at-4-25),
[SQLite WAL](https://www.sqlite.org/wal.html),
[SQLite release notes](https://www.sqlite.org/releaselog/3_22_0.html),
[FDA announcement](https://www.fda.gov/news-events/press-announcements/fda-approves-first-treatment-reduce-risk-serious-heart-problems-specifically-adults-obesity-or),
[trial abstract endpoint](https://pubmed.ncbi.nlm.nih.gov/37952131/).

## Next action

Prioritise a **general extraction-coverage improvement**, tested against the frozen
bytes and unrelated page layouts. Preserve structured content and distinguish body
facts from navigation/header dates; do not introduce Bank selectors or rate tables.
Measure gains and noise separately. Keep the old extraction output as a baseline.

Before paid model comparison, freeze shared source classifications and ensure both
arms use identical input pools. Evaluate extraction/selection omissions separately
from mapping errors, with opposing cases and no-relationship controls. Review exact
quotations separately from entailment. The current pack has no measured mapping
accuracy, and limited source availability must remain visible.

Validation: three preparation tests pass (changed-byte rejection, reviewer-answer
separation/missing-source disclosure, and generated-control variation). Raw source
capture and offline preparation have run successfully. Full replay validation is
recorded in the implementation register. No runtime setting or model changed;
`ENABLE_PASSAGE_MAPPING=False` remains unchanged.
