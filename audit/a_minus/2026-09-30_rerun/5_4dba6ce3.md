# #5 4dba6ce3 — EU gas storage 67% vs 83% norm, lowest on record, re-run 30 Sep

Graded 2026-09-30, blind, from the owner payload, the public payload and the rendered `/r/` page.

**Claim as analysed:** "As of 11 September 2026, EU-wide gas storage stocks are 67% full against a seasonal norm of 83%, representing pretty much the lowest level on record for this time of year." (Faithful to the input.)

**Element states:**
- e1 As of 11 September 2026, EU-wide gas storage stocks are 67% full: **Supported** (2 supports, 0 challenges, 6 context)
- e2 The seasonal norm for 11 September 2026 is 83% full: **Contextual** (0 supports, 0 challenges, 3 context)
- e3 Storage levels are pretty much the lowest on record for this time of year: **Supported** (3 supports, 0 challenges, 2 context)

## Hard checks
- **H1 PASS.** e1: Seeking Alpha (9 Sep), "Gas storage across the European Union is only ~67% full". IEEFA gives "68.04% full on 12 September 2026", so about 67 to 68% on the 11th, and Supported is fair. e2: only an X post gives the norm ("well below the historical average of 83%", early September), so Contextual is fair. e3: IEEFA, "gas storage at the lowest level for this time of year since records began in 2011"; Reuters commentary, "the lowest level for this time of year in 15 years". Supported is fair.
- **H2 PASS (marginal).** The supports bear the way they are filed. The weakest is oenergetice.cz (20 Sep), "European storage facilities are currently just under 67 percent full", which is later than the 11th with no date given for the figure. It matches the claimed level, so a reader would accept it as broadly supporting. The Le Monde support ("a historically low level for this time of year", start of September) is loose against "lowest on record" but points the same way.
- **H3 PASS (with note).** The register is GIE AGSI+, and it is not in the pool. An official EU relay of it is present and mapped: Consilium, "In September 2026, the reserves are at 68%. This data comes from Gas Infrastructure Europe". The Commission's gas storage page is also present. A secondary tracker reading AGSI+ (global-energy-flow.com) sits in the Gathered list.
- **H4 FAIL (classify).** The PRIMARY tier holds a publisher index page. The Gathered list shows "Primary · Reports and Presentations · europeangashub.com", a commercial news site's listing page ("European gas storage replenishment has remained weak during summer 2026…"). It is neither an originator nor data.
- **H5 PASS.** "Of 3 elements examined, 2 predominantly supported; 1 informed by contextual evidence." Supports 5 / Context 9 / Challenges 0, which is consistent.

## Soft checks
- **S1 PASS.** All three elements are substantive.
- **S2 PASS.** e2 carries "Why · No source here directly supports or challenges this part; 3 sources give context". Its Note, "No provided evidence reports a seasonal norm of 83% for 11 September 2026", is technically right, but the X post does say "historical average of 83%" for early September.
- **S3 FAIL (notables).** The Notables main supporting source is Le Monde, "European gas reserves at historic lows" (5 Sep, "only 65% full, a historically low level"). The best supporting source is IEEFA, which gives the 12 September figure (68.04%) and "lowest level for this time of year since records began in 2011". So is Reuters' "lowest level for this time of year in 15 years".
- **S4 FAIL (retrieve).** The same WSJ article appears twice in the Gathered list ("Winter Is Approaching and Europe Is Running Low on…" wsj.com ×2, one URL with `?eafs_enabled=false`).
- **S5 PASS (marginal).** The Gathered rows are all about European gas, though some are stale or tangential (ING, December 2025; Spherical Insights on Britain; tacto.ai price page).
- **S6 PASS.** Counters agree: 13 of 26 mapped; 2 primary · 8 reporting · 3 commentary · 13 not mapped.
- **S7 N-A.** The input is text.
- **S8 N-A.** The claim holds up against the web: the IEEFA and WSJ "15-year low" reporting confirms it. No known rebuttal.
- **S9 N-A.**

Also noted, with no check failed: the relationship review demoted FT (3 Sep, "the lowest level recorded for this time of year since records began") to context on a date mismatch. Le Monde (5 Sep) and Reuters (8 Sep) kept supports on the same element, so date scoping is inconsistent. The europeangashub.com "European Gas Storage" listing page (a headline index) is mapped as context to e3. Reuters news (17 Sep, "69% full, below the 85% average") bears on e2's norm but is unmapped.

## Grade: **B** (1 hard fail: H4 classify; 2 soft fails: S3 notables, S4 retrieve)

**Single change that would most lift this record:** Keep publisher index and listing pages (europeangashub.com "Reports and Presentations") out of the PRIMARY tier.
