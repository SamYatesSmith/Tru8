# Range-period gate: independent review

**Date:** 2026-09-24.
**Reviews:** `audit/2026-09-24_a_minus_range_period_design.md`.
**Scope:** read-only. No checks were run and nothing was spent. The prototype is a scratch script over the 19 stored public payloads plus `labels.csv`.

## Verdict: APPROVE WITH CHANGES

The measured claim reproduces exactly: 5 fires, all `should_demote`/P, and none on `must_survive` or `either`. The mechanism is the right shape for the problem: mechanical, a receipt on every exclusion, and never a deletion.

But the evidence shows only that the rule catches the cases it was built from. It does not show that the rule is safe:
- Only **2 of the 19 records** contain a range element at all (#2 e6e0c00d, #19 6ad65eb5).
- On those elements, every must-survive ref post-dates the range end.

So the false-positive rate is **untested**, not zero. As written, the rule also demotes genuine counterexamples. That is the same sycophancy hazard that failed the relationship-review eval this morning. Required changes R1 to R8 are below. R1 and R2 are blocking.

## 1. Reuse versus new parser, and overlap

- **No existing parser reads a year range.**
  - `_PERIOD_EXPR` matches only a month (optionally with a year) or ISO `YYYY-MM`.
  - So `_BETWEEN_INTERVAL` and `_FROM_TO_INTERVAL` never match "between 2010 and 2020", and `element_interval_end` returns None.
  - `element_period` accepts only month-level periods.
  - The prototype confirms that the measure and temporal gates are both disarmed on all 6 range elements in the corpus.
  - A new, small parser is justified. It should live in `temporal_scope.py` beside `interval_ends` and reuse `_YEAR` bounds and `_publication_with_month`.
- **The overlap is real in one form: `YYYY-YY` with a second part of 12 or less.**
  - "Inflation in 2010-12 was high": the range parse gives 2010–2012, and `element_period` gives **Period(2010, 12)** (the `_ISO` regex).
  - Both gates arm on the same element. The design's line "temporal and this rule never target the same element shape" is asserted, not enforced.
  - Separately, and not caused by this design: "the 2008-09 recession" already arms the temporal gate as **September 2008**. That is an existing temporal defect worth its own line in OPEN_WORK.

## 2. False positives, run through the prototype regex

| Element text | Arms? | Problem |
|---|---|---|
| "The 2010–2020 plan cut emissions by 30%" | yes | The range names the plan, not the period of the claim |
| "A 2020-22 budget allocated £4bn" | yes | Same: a naming modifier |
| "Section 1981-1983 claims" | yes | A statute or section number |
| "Emissions will fall 40% between 2020 and 2030" | yes | **Every** source predates 2030, so every directional ref is demoted and the element is forced to `unresolved` |
| "UK public spending was £1.1tn in 2019-20" | yes | A fiscal year that ends April 2020. A June 2020 ONS outturn would be demoted by the 1 December 2020 cutoff |
| "Wages grew every year between 2010 and 2020" | yes | A 2015 source showing a fall in 2013 is a **valid challenge** (a counterexample), not context |
| "Sweden chose not to impose a lockdown in 2020-22" (#19 e1, live) | yes | A 2021 report of a 2021 lockdown would be a valid counterexample, and it would be demoted |
| "Congress passed the ACA between 2010 and 2020" | yes | An event element: a 2012 source fully establishes it |
| "aged 18-24", "COVID-19", "2019-nCoV", "49-47", "Churchill (1874–1965)" | no | Already safe because of the four-digit 19xx/20xx start and the 1900 floor |

**The core logical flaw.** "A source published before the range ends cannot establish the range" is true only for elements that **aggregate over the whole range**: a cumulative count, a total, or a comparison of totals (both measured cases).
- For a **universal** element ("every year", "never", "not … in", "throughout", "each"), a mid-range source cannot support it but CAN refute it.
- For an **existential or event** element, it can do both.

The design's Risks section treats "grew every year" as honestly `context`. That is wrong. It demotes the challenge that refutes the claim, which breaches invariant #7 in the sycophantic direction. Symmetric relabelling does not make an asymmetric logic symmetric.

## 3. Cutoff and data availability

- **Available at the gate: yes.**
  - `_IndexedEvidence.ev` is the pipeline evidence dict and carries `published_date` and `date_basis`. The temporal and measure gates already read `item.ev.get(...)`.
  - The main-pool and recovery builders set both fields (`retrieve.py:1535/1708/1985`, `runner.py:2035`).
  - The 5 measured fires have basis `engine` (GAO) and `page_metadata` (the other 4), all on the allowlist.
- **The 1 December cutoff** is lenient: December sources survive. For calendar-year ranges that leniency points in the safe direction, so I accept it. It is wrong for fiscal, academic and season years (R3).
  - Parse the date with `_publication_with_month`, so a year-only date never fires.
  - Say in the design that string comparison is not the mechanism.
- **Living pages** (FAQs, CMS landing pages, dataset pages) keep an old publication date over updated content.
  - Cheap guard (R5): do not fire when the item's title and snippet (`item.text`) name the range end year or a later year.
  - All 5 measured fires survive this guard: none of their title+snippet texts names 2020 or 2022.
  - It must use `item.text`, not the retained passages: KFF's passages mention 2020, so a passage-based guard would lose that fire.

## 4. Measured claim, re-run

The prototype reproduces the 5 fires exactly (#2 e1/e2/e3, #19 e3 ×2), both with and without the basis guard.

Scanning the elements of all 19 payloads finds range elements only on #2 (3 elements) and #19 (3 elements). No other element arms.
- #19 e1 and e2 arm but have no pre-cutoff refs, so there are no fires.
- The result is state-positive: #2 e1 moves from disputed to supported (thin), because the PMC primary alone meets the floor of 3. #19 e3 keeps 3 challenges.

The sample says nothing about specificity. R7 below addresses that.

## 5. Placement

The docstring's additive argument is that later gates only claim refs the earlier ones left alone. Placing the new gate before jurisdiction breaks that: foreign official sources on range elements would change receipt reason, from "another country's" to "published before range end".

Place it **after `date_scope`**, so the time-family stays together. The four gates before it (temporal, readable_text, jurisdiction, measure) are then untouched by construction. It must still be before same_study and echo, and echo stays last.

## Required changes

- **R1 (blocking): aggregate-only arming.** Arm only when the element states a quantity (a numeral, "million", or %) or a comparative ("lower/higher/more … than", superlative) with the range as its period.
  - Disarm on universal or negated forms: every, each, annual(ly), never, always, not, no, throughout, consecutive, "chose not".
  - Disarm on event elements with no quantity (reuse `element_is_event`).
- **R2 (blocking): the range must be the period.**
  - Require a temporal preposition immediately before the range (`in`, `during`, `over`, `across`, `between`, `from`).
  - Refuse when a noun follows the range (plan, budget, strategy, programme, season, term, cohort, Parliament) or when a section/page marker precedes it (§, section, pp., No.).
  - Disarm when the range end is at or after the check's year, or when the sentence is `_FORWARD_LOOKING`.
- **R3: fiscal-year and ISO ambiguity.**
  - Refuse `YYYY-YY` where the end year is the start year plus 1, or where fiscal, financial, tax, academic, school or season words are adjacent.
  - Refuse a two-digit second part of 12 or less (the ISO month clash).
- **R4: enforce mutual exclusion.** Disarm when `element_period` or `element_interval_end` is non-None, or when the element has more than one range.
- **R5: the stale-date guard.** No fire when `item.text` names the end year or later.
- **R6: a full receipt and wiring.**
  - The receipt carries `date_basis` and `range_end_cutoff`.
  - Add the key to `_SCOPE_RECEIPT_KEYS`, to `_SCOPE_NOTE_LABELS` (`checks.py:2131`), and to the bench `comparator.py` / `capture.py` label maps.
  - `readable_text` is itself missing from `_SCOPE_NOTE_LABELS`. Fix it alongside.
  - The gate gets its own flag.
- **R7: adversarial unit tests.** Every row of the §2 table must be pinned as NOT firing: counterexample, forecast, fiscal year, naming modifier, section number, `2010-12`. The two measured records must be pinned as firing.
- **R8: order test.** Pin the new position, and show on the bench that no corpus element arms, so moving it is receipt-neutral there. Run the bench and control arm as the design says.
