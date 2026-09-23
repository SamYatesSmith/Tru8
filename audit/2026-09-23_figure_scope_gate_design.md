# F2 — Figure scope gate (design, 2026-09-23)

**Status:** BUILT 2026-09-23 (approved in session), uncommitted pending bench + known-truth re-run.
**Motivation:** the 2026-09-23 re-run of the four-record known-truth set
(`OPEN_WORK.md` 2026-09-22 item 1). Supply fix passed Katz and Tidman; Legum and Kennedy
still fail, and both fail the same way: an element badged `supported` on a figure **no
source states**. Legum: part-period values ($600m–$1.86bn for 2025, $220m–$750m for Q1 2026)
summed by the mapper into $898m–$2.87bn. Kennedy: "68%, ~16 points below the five-year
average" turned into an 83% norm by the mapper doing the sum.

## 1. Rule

For an element that states a figure, a `supports` reference must come from a source that
**states** a matching figure of the same kind. If the source states figures of that kind
and none match, re-label the reference `context` with a receipt naming the element's
figure(s) and the source's. **Stated, not derived** — a sum or difference the mapper
computed is not something the source said.

- **Silence never fires.** A source stating no figure of that kind is left to the mapper
  (same convention as temporal/date gates: inferring from silence over-fires).
- **Any-match, not all-match.** An element with two figures ("£22m rather than the £53m
  forecast") is satisfied by a source stating either. All-match fired on 8 honest refs in
  the Scottish-tax records; any-match still catches every known failure.

## 2. What counts as a figure (mechanical, no LLM — `app/utils/figure_scope.py`)

| Kind | Form | Key |
|---|---|---|
| percentage | `67%`, `67 per cent`, `67 percent` — NOT `percentage points` | `pct` |
| currency | `$898 million`, `£72m`, `€2.87bn` (symbol + multiplier normalised) | `cur$` / `cur£` / `cur€` |
| count | number + noun within two words (`28,700 securities trades` → trade, security) | `n:<lemma>` |

Excluded: years (1800–2100 with no comma or multiplier), day-of-month dates, digits inside
words (`CO2`), percentage points.

**Thresholds never arm the gate** (added at build, 2026-09-23). "Unemployment fell
**below** 5%" is supported by a source stating 4.2%. A figure after below / under / above /
over / more than / fewer than / at least / at most / up to / exceeded / surpassed / topped
is a bound, not a point value, and is left out of the element's figures. Found by the
existing coverage-recovery fixture on the first full unit run — the 61-record prototype had
no bound-shaped element among its fires, so the firing count is unchanged (24).

**Only a support that RESTS on a number** (added at build, 2026-09-23). The mapper's
reasoning for the reference must itself cite a figure of the element's kind. "The
mini-budget caused 30-year gilt yields to spike to 5.1%" was supported by a source the
mapper cited for the CAUSE ("the sharp rise … was triggered by the mini-budget"); the first
build scoped it on the number and sent the element into coverage recovery (replay bench,
TRU-B4A3-C42D). All 24 prototype fires cite a figure in their reasoning, so none is lost.

**Tolerance:** the source figure's own precision (`29,000` covers 28,500–29,500; bare
`80%` covers 79.5–80.5 only — trailing-zero rounding applies only to comma-grouped counts
or multiplied values), widened to ±5% when the element carries an approximation word
(about, around, approximately, roughly, almost, nearly, some, close to, estimated).
`exactly` removes the source-rounding allowance.

**Text read:** title + snippet/text the mapper saw **+ retained passages**
(`text_provenance`). The union prevents a false fire when the figure sits in a window the
mapper did not get.

## 3. Supports only — measured, and why it is not a sycophancy mechanism

The mirror (a `challenges` ref whose only figures MATCH the element → context) was
prototyped. **It fired 4 times across 61 stored records and was wrong every time:** Trust
the Evidence restating the NHS triage 29% to dispute its cause; NASA restating "90 minutes"
to say that is not Webb's orbit; a source stating 3,300 bees against "exactly 3,301". A
challenge that repeats the number is disputing its meaning, not its value. Building it would
strip the rebuttals the product most needs to show (the TTE critique is the one outreach
most depends on).

Invariant 7 holds because the rule IS symmetric in principle — **a directional relationship
must rest on what the source states.** A support rests on the stated figure; a challenge
from a different stated figure already rests on a statement, and a challenge that restates
the figure rests on something the gate cannot see. The gate only moves refs away from
`supports`: it can make an unsupported figure look unsupported; it cannot make a false
claim look supported, and it cannot remove a challenge.

## 4. Firing rate (prototype over 61 stored records, free — `output/rerun/proto.py`)

162 elements · 57 carry a figure · 182 directional refs on them · **24 support refs fire.**

| Record family | Fires | Correct? |
|---|---|---|
| Legum (4 runs) — value range + trade count | 14 | Yes — known truth: no source states the range; 21,000 / 14,000 / 3,600 are part-period counts |
| Kennedy (3 runs) — 83% norm, 67% level | 9 | Yes — 85% / 88% / 68.04% (13 Sep) are not the figure |
| Reform £72m | 1 | Rule-consistent: source states two £36m gifts; the total is the mapper's sum. **Founder call (§6)** |

**Zero fires on Katz, Tidman, or any record without a figure-sum failure.**

**Update (built 2026-09-23, same day): dated coincidences closed.** A matching figure
counts only if at least one sentence stating it names no period, or the element's own —
`unstated_reason` → `other_period`. Fires once on 66 stored records: exactly the GEF case.
Tolerance also made strict (82% no longer states 83%). Undated coincidences remain.

**Known limitation — coincident numbers mask.** Kennedy's re-run still leaves one support
standing: Global Energy Flow states "83%" — about storage on **1 November 2025**, a
different quantity. Same kind + same value = match. The gate errs toward leaving the
mapper's call in place, which is no worse than today. Binding a figure to its measure
(the noun it modifies) is the fix if this proves common; not in v1.

## 5. Placement (behaviour — order and ownership are test-pinned)

- Scope gate `figure_scope`, flag `ENABLE_FIGURE_SCOPE_GATE` (default True once approved).
- **Order:** temporal → jurisdiction → measure → date_scope → **figure_scope** →
  interested-party → recital → same_study → echo → (fact_applicability). After the
  period/place/day gates, which are more specific explanations and should own a ref first;
  before the source-identity gates. Echo stays last.
- Joins `_SCOPE_RECEIPT_KEYS` or both merge paths drop its receipts.
- Receipt: `{"element_figures": [...], "source_figures": [...], "rule": "not_stated"}`.
- `fires` checks `ref["relationship"] == "supports"` — the first gate to gate on
  direction; the `_ScopeGate` callable already receives the ref.

## 6. Founder decisions

1. **Supports-only** (§3) — recommended, measured.
2. **Summed figures are "not stated"** — Reform £72m from two £36m gifts goes to context.
   Recommended: yes. It is the Legum failure in miniature; allowing "obvious" sums reopens
   the door the gate exists to shut.

## 7. Verification plan

- Unit tests: parser table (each kind, exclusions, precision, `exactly`), gate fires/never
  fires, silence, any-match, ordering pin, receipt-key pin, supports-only pin (a
  challenge with a matching figure is untouched — the TTE case, verbatim).
- Replay bench: expect zero drift (no prompt change, no request-signature change).
  Bench cannot confirm improvement.
- **Known-truth set:** re-run Legum + Kennedy on the subscription (2 credits). Expect
  Legum el 02 and Kennedy el 02 → no `supports` on a stated-different figure; element reads
  `unresolved` / context-only. Katz + Tidman unchanged (prototype: zero fires) — re-run all
  four (4 credits) to confirm.
