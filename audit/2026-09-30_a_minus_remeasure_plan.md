# A− re-measure 3 — plan and run sheet (prepared 2026-09-30)

**Why:** the last re-measure (28 Sep, `9aff4ea`) scored **0/19 at A−**, with weak sources in PRIMARY (H4) the largest hard failure (10/18). Since then the H4 fixes (round 2 caps + the originator review) and several mapping/retrieval/surface fixes have shipped. This re-measure is the only way to know whether the grade moved, and which fault is now largest.

**Build under test:** production `ed83167` (or later). Changes since the 28 Sep re-measure build (`9aff4ea`):
- `b7a3d8f` H4 round 2: trackers, reference adapters, shortlinks, unrendered pages leave PRIMARY
- `ed83167` H4 class D: the originator review (explainers, calculators, copied docs leave PRIMARY)
- `765b434` H3: the search window reaches a dated event earlier this year
- `dd557f4` S4: Build C enforcing (one fetch slot per article)
- `0032ef7` S5: weather adapters answer only weather claims
- `29314a2` S3: Notables chosen by reach and tier · `a71e109` S6: shell titles ("Reddit", "X - The Everything App") read from the URL
- `7592e42` A1′ recital skip (an unowned document speaking is not a recital) · `a0d869a` completion keeps `llm_state`
- `43c757a` relationship review ON (supports only) · `ac071e6` figure-parser fixes · `b50672e` PDF memory fix

**Cost:** 19 Console checks on the founder's account (no extra charge). Grading: free (blind agents + the read-only tru8 tools).

## How to run (founder)
1. On the dashboard, submit each input below **exactly as written** (copy the text inside the quotes), one at a time.
2. If the check pauses for claim selection, **select every claim offered** (the 28 Sep re-measure did the same).
3. Paste each finished check's dashboard link into the table (or send the 19 links in one message). #16 and #17 are the same input on purpose: they test consistency.

## Run sheet
| # | Input (submit verbatim) | 28 Sep grade | New check link |
|---|---|---|---|
| 1 | "Reform UK's £72 million came in the space of one weekend – £36 million each from crypto billionaires Ben Delo and Christopher Harborne." | B (`392525b1`) | |
| 2 | "Between 2010 and 2020, the CMS Innovation Center launched 54 demonstration models encompassing almost one million clinicians and 26 million patients nationwide." | C (`a4380061`) | |
| 3 | "Irish public spending has risen by more than 50 per cent since 2020, a trend that isn't mirrored anywhere else in Europe." | B (`739230ee`) | |
| 4 | "In the September 2026 Saxony-Anhalt state election the AfD won the most seats and came within three seats of a single-party majority — the first time a far-right nationalist party has won the most seats in a German election since 1933." | B (`e916e351`) | |
| 5 | "As of 11 September 2026, EU-wide gas storage stocks are 67% full against a seasonal norm of 83%, pretty much the lowest on record for this time of year." | C (`31dac79a`) | |
| 6 | "Donald Trump has made almost 28,700 trades of securities with a total value of $898 million to $2.87 billion since 2025" | C (`8d7013a2`) | |
| 7 | "Cook Political Report, GS Strategy Group and New River Strategies surveyed 1,052 likely voters from September 8-11, 2026 across the 37 House districts Cook rates as competitive; the generic ballot in them is Democrats 49, Republicans 47, and Trump's job approval is 42-58." | B− (`50e08e0e`) | |
| 8 | "A team from University of Galway, with colleagues from France, placed 23 3D-printed reef structures on the seabed of the Porcupine Bank 200km off the Kerry coast, and in the Bay of Biscay off France." | B (`66a8fce1`) | |
| 9 | "A study comparing AI-generated and physician-generated clinical summaries found the AI summaries were preferred 36% of the time, physician summaries were preferred 19% of the time, and the rest were rated as no different." | B (`96ab8de1`) | |
| 10 | "Central Bank of Ireland research published in September 2026 shows multinational activity has been key to Ireland's economic outperformance in recent years, adding 1.2 per cent to annual economic growth since 2022." | C (`1139fbdb`) | |
| 11 | "The Letby inquiry has said the government must introduce a statutory barring system for NHS managers by September 2027." | B (`d60ea371`) | |
| 12 | "Atmospheric CO2 concentrations are now greater than 420 parts per million, compared to around 320 ppm when the decision was made to extract from the North Sea in the late 1960s." | C (`168a7af0`) | |
| 13 | "Europe's recent heatwaves are being caused by declining air pollution rather than climate change" | B− (`874ac2f2`) | |
| 14 | "Reform UK has been pledged £72m this week — £36m from Ben Delo and £36m from Christopher Harborne — more money than any party has had in the history of British democracy." | B+ (`77a6669f`) | |
| 15 | "AI triage through the NHS App reduced the number of people queuing on the phone at GP practices by 29 per cent in a Sussex pilot" | B− (`7bf6d175`) | |
| 16 | "2026 is the quietest year for wildfires in Europe by some distance" | B+ (`b951f3d3`) | |
| 17 | "2026 is the quietest year for wildfires in Europe by some distance" | B+ (`8186c399`) | |
| 18 | "The James Webb Space Telescope orbits the Earth every 90 minutes, has a 6.5-metre primary mirror and was launched in December 2021." | B (`08a0e26d`) | |
| 19 | "Sweden's decision not to impose a general lockdown caused it to have lower excess mortality in 2020-22 than every other European country." | B− (`e72bf789`) | |

## Grading (Claude, once the links are in)
- Graders are fresh agents, blind: they never see the 28 Sep or baseline grades, `audit/recipients/`, or any design doc. Brief: `audit/a_minus/2026-09-30_rerun/GRADER_BRIEF.md`.
- Checklist and grade table: unchanged from `audit/2026-09-24_a_minus_measurement.md` (H1–H5, S1–S9). Every failure names one pipeline stage.
- Each grader reads the owner payload (`tru8_get_result_raw`), the public payload (`/api/v1/checks/public/{id}?detailed=true`) and the rendered `/r/{id}` page (`cd web && node scripts/verify-page.mjs`).
- One file per record in `audit/a_minus/2026-09-30_rerun/`, same format as `2026-09-28_rerun/`.
- Then: the tally by check and by stage, compared with 28 Sep; the per-record change; the new largest bucket; and a note on the originator review's receipts across all 19.

## Rules
- Grade what the page shows a reader, not what the pipeline intended.
- A fault seen on a record is attributed to one stage; if two stages share it, name the earlier one.
- Judge fixes on general mechanisms, never on these 19 (`feedback_general_quality_not_outreach_set`).
