# Mapping failures on the 2026-09-28 re-measure (H1/H2)

**Source:** the blind grades in `audit/a_minus/2026-09-28_rerun/` (18 records, production `9aff4ea`), and the stored payloads' element receipts.
**Prior work, not repeated here:** `audit/2026-09-24_a_minus_mapping_design.md`. M1, the model relationship review, failed its eval twice and is a hard stop. M2 (unreadable text) and M3 (per-subject interested-party release, event-quarter containment) shipped.

**Size:** 12 mapping-related hard fails on 9 records (#1, #2, #5, #6, #7, #10, #12, #15, #19). Wrong directional refs (H2) fell from 13 records to 5, so the mix has changed: most failures now **remove or miss a correct support**, rather than add a wrong one.

## Three families

### A. A gate removes the authoritative source's own support (#7, #10)
The claim reports an organisation's own finding. The organisation's own publication is then demoted as if it were an interested party restating the claim.
- **#7, recital:** Cook's results page "According to the September 2026 toplines, Democrats hold a two-point advantage… 49% to 47%" goes supports → context. e2 falls to Unresolved on one reporting source.
- **#10, interested-party** (prong `name_in_domain`, centralbank.ie): the CBI Q3 bulletin's "1.2 percentage points per annum … according to Central Bank of Ireland research" goes supports → context. The page then says "No provided evidence contains the specific figure". That is false.
- **Why M3 did not catch these:** the per-subject org release covers interested-party **prong 1 only**, and the recital gate has no org-publication release at all. R6 released challenges only.
- **Fix:** mechanical. Extend the M3 org release (a named ORG subject + the closed publication/measurement verb list) to the `name_in_domain` prong and to the recital gate. Keep the TRU-018F guards: person or claimant subjects, and executive-comms domains, are never released. Difficulty 3 on 018F-guarding gates, so it needs a design and review first.

### B. A source is mapped to one element but not its sibling (#1, #12, #15)
The mapper files a source against e1 (or e3) but not against a sibling element that the same text states outright.
- **#1:** BBC, Guardian ×2 and Irish News state Harborne's £36m. All are mapped to e1 only, so e3 ("Harborne contributed £36m") reads Unresolved on one source.
- **#12:** Statista gives 427.49 ppm (2025) and 322.89–325.13 (1968–70). It is mapped to e1 and e2 but not e3 ("now greater than then"), so e3 reads Contextual.
- **#15:** at least 7 sources state "29% fall in people queuing". All are mapped to e3, none to e2, so e2 reads Unresolved.
- **Fix:** open. Stage 5.1 coverage recovery claims cross-element mapping, so why it did not fire here is the first question. It is a free investigation, read from the stored receipts. Any fix must stay **add-by-model, never add-by-rule**: mechanically copying supports across elements would be a sycophancy mechanism. A plausible shape: when an element ends unresolved or contextual, one targeted mapper call per element, offering the sources already mapped to its siblings, with all the gates re-applied.

### C. Wrong-scope directional refs (#2, #6, #10, #12, #19)
Model judgement:
- #2: a subset count filed as a challenge.
- #6: "21,000 in 2025 alone" filed as support for "28,700 since 2025".
- #10: ECB and Franklin Templeton work filed as support for "CBI research says".
- #12: Keeling's 1950s ~310 ppm filed as support for late-1960s ~320.
- #19: Cato's "lowest excess mortality" filed as a **challenge**, and Wikipedia's confirmed deaths filed as a challenge on excess mortality.

This is the class M1 targeted, and it failed. One mechanical subset exists: in #6, the figure gate missed because "21,000" is not written next to "trade". Everything else needs a model; the founder's possible future path is recorded in the 2026-09-24 doc (3.7-flash, demote-on-unknown, supports only).

**#5 is not counted as a fault here.** The figure gate demoted "66% (8 Sep)" and "68.04% (13 Sep)" as support for "67% on 11 Sep". The grader called it borderline. Loosening figure matching to "close enough" is a sycophancy risk, so it stays as is.

## What fixing these moves (ceiling; fixes assumed perfect)
| Family | Hard fails cleared | Grade change |
|---|---|---|
| A | #7 H1, #10 H1 | none reaches A−; #7 still fails H3, #10 still fails H2 and H4 |
| B | #1 H1, #12 H1, #15 H1 | **#1 → A−** (only S6 left); #15 B− → B; #12 still fails H2 and H4 |
| C | #2, #6, #10, #12, #19 H2 | none alone |

**Reading:** mapping fixes alone reach about **1 A−** on this set. The A− rate also needs retrieval: the authoritative source is missing (H3) on 7 of 18.

## Family B: root cause found (2026-09-28, free investigation)
Three coupled causes, all confirmed on the stored payloads:
1. **The mapping prompt forbids it.** Since NF-19 (`a903729`, 2026-06-16), `MAPPING_PROMPT` and `BATCH_MAPPING_PROMPT` have said "Map each item to the SINGLE element it most directly addresses … Do NOT duplicate the same item across elements". The rule was kept on purpose as the NF-12 guard against element collapse (every element carrying the same refs).
   - #1: all 9 outlets stating "Harborne £36m" are filed under e1 only; e3 has one (Al Jazeera).
   - #15: every "29% fall" source is under e3 or e1; e2 has one support.
   - #12: Statista is under e1 + e2, not e3.
2. **The completion backstop only looks at unmapped items.** `_complete_unmapped_evidence` never re-offers an item already mapped to a sibling.
3. **Coverage recovery cannot reach it:**
   - **Trigger:** it fires only when more than 40% of elements need recovery, or one is context-only. A single unresolved element in 3 is 33%, so #1 and #15 never qualified (0 recovery items).
   - **Pool:** when it does fire (#12, 4 items), it maps **only newly retrieved** evidence, never the existing pool.

**Why not simply delete the rule:** it would reopen NF-12, where every element carries every source.

**Proposed shape (difficulty 3, so design + independent review before any build):**
- A **sibling re-offer pass** after mapping and the gates. For each element that ends unresolved or contextual, make one targeted mapper call offering the pool items already filed supports/challenges on its siblings, plus unmapped items, asking about THAT element only.
- Symmetric: supports and challenges both.
- All gates re-applied, then the state re-derived.
- Add-by-model only; never a mechanical copy.
- Cost is about one flash call per weak element.
- Paid offline eval on the 18 pools before any flag goes on.
