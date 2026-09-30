# #14 7e4ddfaa — Reform UK £72m pledged, "more than any party has had", re-run 30 Sep

Graded 2026-09-30, blind, from the owner payload, the public payload and the rendered `/r/` page.

**Claim as analysed:** "Reform UK has been pledged £72m this week — £36m from Ben Delo and £36m from Christopher Harborne — more money than any party has had in the history of British democracy." (Faithful: verbatim input; the page restatement only swaps dashes for a clause.)

**Element states:**
- e1 Reform UK has been pledged £72m this week: **Supported** (2 supports, 0 challenges, 5 context)
- e2 The funds are £36m from Delo and £36m from Harborne: **Supported** (4 supports, 1 challenge, 2 context)
- e3 More money than any party has had in British history: **Challenged** (0 supports, 1 challenge, 5 context)

## Hard checks
- **H1 FAIL (map).** e3 reads "Challenged" on a single challenge, while the retained sources a reader sees point the other way: LRB "the largest single donation ever made to a British political party… The combined £72 million exceeded the amount raised by every British political party put together in 2025"; Best for Britain "more than seven times the largest amount ever given to a political party in our history"; BBC "the biggest single donation ever given to a political party in the UK". A careful reader would badge e3 supported, or at worst unresolved on the literal "has had" wording. It would not badge it challenged.
- **H2 FAIL (map).** Two wrong directional references. (1) Reuters (4 Dec 2025) is filed as challenging e3: "The biggest donation in British history was the 10 million pounds given to the Conservatives by businessman John Sainsbury". That is the old record, which £72m exceeds, so the text bears FOR the claim. (2) The Guardian, 12 Sept, is filed as challenging e2: "dwarfing the £15m contribution to Reform UK from… Christopher Harborne". That is Harborne's earlier running total, written before his matching £36m, so it is the wrong period. It is also the page's "Main challenging source".
- **H3 PASS.** No official register entry exists yet for pledges made this month; the Electoral Commission publishes quarterly. The originating announcements are carried by BBC, Guardian and Reuters coverage.
- **H4 PASS.** Nothing is filed in the primary tier.
- **H5 PASS.** "Of 3 elements examined, 2 predominantly supported; 1 challenged with none supporting." This matches the badges, and the counters (Supports 5 / Context 10 / Challenges 2) agree.

## Soft checks
- **S1 PASS.** All three elements are substantive parts of the claim.
- **S2 PASS.** e3 says "Why · 1 source challenges this part; none supports it."
- **S3 PASS.** Morning Star, "Two billionaires pledged £72 million… each decided to give £36m", covers e1 and e2.
- **S4 FAIL (retrieve).** Le Monde's "Crypto billionaire gives Farage's Reform UK record £36…" appears twice (two `srsltid` URL variants) in the "Gathered — not mapped" list.
- **S5 FAIL (retrieve).** A YouTube video ("£72 million donation is 'buying political power'") sits in the evidence ledger as REPORTING · News.
- **S6 FAIL (render).** The VIDEO lens renders raw entities: "Farage&#39;s £72m Donors Exposed — Rayner Says &quot;Buy Our Democracy&quot;". The LRB row is also dated 8 Oct 2026, after the report date (its issue cover date).
- **S7 N/A.** The claimant's piece (Fraser Nelson's Substack) is not in the pool.
- **S8 N/A.** I found no known rebuttal; the claim is broadly accurate as a record.
- **S9 N/A.**

Also noted, with no check failed: Harborne's matching gift is widely reported as announced a day after Delo's, so "this week" holds. Of the three context-demoted items on e1 (PBS, The National, Guardian briefing), all do mention the £72m. The scope review is conservative, not wrong.

## Grade: **B−** (H1, H2 fail; S4, S5, S6 fail)

**Single change that would most lift this record:** Stop the mapper filing an older record figure or a pre-event running total as a challenge (Reuters £10m, Guardian £15m), which would also clear e3's wrong badge.
