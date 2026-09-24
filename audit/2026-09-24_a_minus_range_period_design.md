# Range-period gate: a source published before a range ends cannot establish the range (design for review)

**Date:** 2026-09-24.
**Status:** DRAFT for independent review.
**Rule:** difficulty 3.
**Origin:** option 3 after the relationship-review eval failed (`audit/2026-09-24_a_minus_mapping_design.md`, eval section). That eval found the model catches wrong-PERIOD refs well once given dates; this is the part a mechanical rule can own.

## The rule
Where an element states an explicit CLOSED year range, and an evidence item's publication date is **before 1 December of the range's end year**, the directional ref becomes `context` with a receipt:
- Range forms: "between 2010 and 2020", "2010–2020", "2020-22", "from 2010 to 2020".
- Receipt: `rule: published_before_range_end`, `element_range`, `published_date`.

Rationale: a source written before a period ends cannot state what happened over the whole period. A 2018 snapshot ("37 models as of March 2018") is not the 2010–2020 total, and a 2021 ONS release covering 2020 is not "2020–22". Symmetric: supports and challenges alike.

## Deliberately NOT covered
Each of these needs judgement that a date comparison cannot make, so each is left to the mapper and prompt, and was labelled "either" or excluded in the eval set:
- "As of <date>" state elements (daily-moving figures; the FT 3 Sept / Algebris 2 Sept vs 11 Sept cases).
- "since X" and "recent years" (open-ended or relative).
- "current/now" with undated sources (ACS "current 416 ppm" has no `published_date`).
- Elements whose date decomposition dropped (#7).

## Guards
- **Only trusted publication dates.** `date_basis` in `temporal_scope.TRUSTED_PUBLICATION_BASES`, the same allowlist the F1 publication resolution uses (`url_inferred_suspect` refused). No date means no fire; silence is never out of period.
- **Only a strictly increasing range:** end > start, both 1900–2099.
- **Placement:** a new scope gate placed after temporal and the readable-text gate, before jurisdiction; it joins `_SCOPE_RECEIPT_KEYS`. Temporal (single-month elements) and this rule (range elements) never target the same element shape.

## Measured (free, the 156 labelled pairs of `audit/a_minus/review_eval/labels.csv`)
**5 fires, all `should_demote`/P, 0 on `must_survive` or `either`:**
- #2: GAO 2018 and KFF 2018 ×2 against 2010–2020.
- #19: Guardian Aug 2022 and ONS Mar 2021 against 2020–22.

That is 5 of the 10 `should_demote` P refs. #2's GAO challenge is the one that makes e1 read disputed (a hard H1 fail).

## Risks
- **A source published mid-range can legitimately give a PARTIAL figure** the element's wording asks for, e.g. an element "grew every year between 2010 and 2020" and a 2015 source on 2010–2015. That source still cannot establish the whole-range claim, so `context` is the honest label, not an error.
- **`page_metadata` dates can be badly wrong** (the known CSO case). The allowlist is the mitigation; the bench cannot see this.
- **Cassettes:** a post-mapping gate re-keys nothing unless it changes a state that triggers coverage recovery. Bench + control arm.

---

## Build log: 2026-09-24 (review: APPROVE WITH CHANGES, `audit/2026-09-24_a_minus_range_period_review.md`)

**All required changes applied** (`app/utils/range_period.py`, gate `range_period`, flag `ENABLE_RANGE_PERIOD_GATE`):
- **Aggregate elements only.** The element must carry a figure (digits outside the range itself, or a number word such as "one million") or a total/comparison word. Universal or negated elements never arm ("every year", "not", "never"…), since a mid-range counterexample is valid for them (invariant #7).
- **The range must be the claim's period.** It must be introduced by a temporal preposition, and it is not followed by plan / budget / strategy / act…; span ≥ 2 years (fiscal years excluded); the end must not be in the future.
- **One gate per element shape:** an element with a month-level period belongs to temporal.
- **Placement:** straight after `date_scope`.
- **Labels:** `range_period` added to `_SCOPE_RECEIPT_KEYS`, `_SCOPE_NOTE_LABELS` (plus the missing `readable_text`) and the review-sheet labels.

**Measured:**
- On the 156 labelled pairs: **5 fires, all `should_demote`/P, 0 on `must_survive` or `either`.**
- Across all 19 stored records only the expected 4 elements arm (#2 ×3, #19 ×1).
- The first number-word miss ("almost one million clinicians") was caught by this measurement and fixed.

**Tests:** 19, including every adversarial case from the review (a named plan, a forecast, a fiscal year, a section range, "every year", a negated aggregate); all 6 mutants caught.

**Verification:**
- Unit 4,028 pass.
- Bench: no difference beyond the known 5647/93DD flakes (5647 replays identically alone).

**Logged, not fixed:** the temporal gate reads "2008-09" as September 2008 (review finding).
