# Figure quote review — design shape and honest grade (2026-09-23)

**Status:** DESIGN — awaiting founder go. Nothing built.
**Problem left after F2** (`2026-09-23_figure_scope_gate_design.md`, live `af7ce0b`): a
source that prints the element's number *about something else* still counts as stating it.
Kennedy `16133434` el 02 "seasonal norm … 83%" reads supported on global-energy-flow.com,
whose norm sentence says "about 82%" (20 August) and whose "83%" is storage on
1 November 2025. F2 reads the whole page as a bag of numbers; it cannot tell which
sentence the support rests on.

**Rejected:** binding every figure on a page to its measure and date (founder, rightly:
heavy, brittle, open-ended). **Rejected:** adding a quote field to the MAPPING prompt — it
re-keys every cassette and costs output tokens on every reference of every check.

## 1. Finding: the mechanism already exists, switched off

`app/services/relationship_scope_review.py` (Track Q, 8–9 Sep, built and evaluated) does
the "show me the sentence" check as a **separate, bounded model call after mapping**:

- For each directional ref, the model returns a decision and an **exact quote** (12–600
  chars) that code verifies is **verbatim in a supplied block** (mapping text + the two
  best retained passages). An invented or repaired quote is discarded.
- **`quantitative_result_not_quoted`**: a `compatible` support on an element stating a
  figure must carry that figure **inside the quote**, or it becomes `context` with a
  receipt. Built for the SELECT "20%" case; passed its frozen pair.
- Demote-only: never promotes, never flips; re-derives the element state; malformed or
  failed output keeps the mapper's label and discloses incomplete coverage.
- Bounds: ≤12 pairs, two concurrent calls of ≤6, 25 s deadline, 4,800 output tokens.

It is gated behind `ENABLE_PASSAGE_MAPPING`, which also switches on 13 other behaviours the
2026-09-09 regrade found not ready. So production never runs it.

## 2. Shape

1. **Own flag** `ENABLE_FIGURE_QUOTE_REVIEW` (default on after measurement) calling
   `review_relationship_scope` independently of `ENABLE_PASSAGE_MAPPING`.
2. **Scoped to what F2 leaves:** only `supports` refs on elements where
   `figure_scope.element_figures()` finds a point figure. Everything else keeps today's
   behaviour. Most checks have no such pair → **no extra call at all**.
3. **One figure parser:** `_quotes_stated_figure` uses `figure_scope` (%, currency, counts,
   precision, hedges, thresholds) instead of its own %-and-ratio-only `_figure_forms`,
   keeping its ratio forms. One definition of "states the figure", not two.
4. **Order:** F2 (mechanical, free) first; the review sees only supports F2 let through.
5. Receipts, state re-derivation and fail-open behaviour unchanged.

## 3. Honest grade

**Efficiency — B.**
- Build: small. The stage, its receipts, its UI disclosure and 124 tests exist; the work
  is a flag split, a pair filter, a parser swap, and tests. About half a day.
- Runtime: zero cost on checks with no figure-bearing support. Where it fires, one or two
  Flash-Lite calls of ≤6 pairs — fractions of a penny — **but 7–25 s of added wall time**,
  sequential after mapping, plus possibly again after coverage recovery. That latency is
  the real price and is unmeasured on the default path.
- Bench: new requests on any corpus claim with a figure-bearing support → a
  `--record-missing` patch pass (live calls, ASK first) and a re-record commit.

**Quality — B+ on arithmetic, B− on coincidence.**
- *Arithmetic/summing (Legum, Kennedy's 62%+15):* strong. No sentence states the derived
  figure, so no verbatim quote can contain it — the check is mechanical once the quote is
  verified. F2 already catches most of these; this is a second net.
- *Coincident number (GEF):* depends on the model choosing the norm sentence (82%) rather
  than the November sentence (83%). The prompt already says "a stray matching number does
  not establish the asserted effect" and makes `time` a scope dimension. Likely, not
  guaranteed — if it quotes the 83% sentence and calls it compatible, the figure check
  passes and the error stands.
- *Risks:* the figure check is literal on form — "two-thirds" for 67%, or "£2,870m" for
  "£2.87bn", would read as not quoted (false demotion; the parser normalises multipliers,
  not words). The 12-pair cap can leave pairs unreviewed on figure-dense claims (disclosed,
  not hidden). Supplied blocks are the mapping text + two ranked passages; if the deciding
  sentence is outside them the model returns `unknown` → demoted, the safe direction here.
- Evidence it works: frozen SELECT pair fixed; 8/8 synthetic controls; the 20/24 broader
  synthetic failures were attributed to other stages. **Never run on the default path or
  live**; never measured on our known-truth set.

**Likelihood to work — about 70% on Kennedy, moderate-high in general.**
- Kennedy el 02 flips to not-supported only if the model quotes the 82% sentence. On a
  1-credit re-run the answer is observable, but one run is one draw (the pool also varies:
  the 54b8699b pool supported 83% via an X post that genuinely states it — which this
  review would rightly keep).
- The larger uncertainty is not correctness but **latency** on figure-heavy checks.

## 4. Verification plan (before default-on)

1. Unit: pair filter (figure elements, supports only), shared parser, fail-open, flag split.
2. Offline: replay the review over the stored payloads of today's 7 re-runs (no retrieval;
   one small model call each — ASK). Expect Kennedy GEF demoted, Katz/Tidman untouched.
3. Bench patch pass + re-record; control arm on one claim.
4. Latency: record the added seconds on every run above; default-on only if p90 added
   ≤ 15 s.
