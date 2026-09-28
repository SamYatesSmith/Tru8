# Retrieval: authoritative source missing (H3) on the 2026-09-28 re-measure

**Size:** H3 failed on 7 of 18 records (#2, #4, #5, #6, #7, #13, #15). It is the largest remaining cap on A− after mapping. **Source:** the stored query plans (`claimMap.metadata.queryPlan`) and the pools of the re-run payloads. The investigation was free.

## Per record
| # | Missing source | In pool? | Queries | Reading |
|---|---|---|---|---|
| 4 | Saxony-Anhalt returning officer's results page (6 Sep) | no | 7 queries, **all `pw`** | **Window.** Searched on 28 Sep with a past-week window, so the results page (and most coverage) fell outside it. |
| 5 | GIE AGSI+ data for 11 Sep | no | 9 queries: 8 `pw`, 1 `pm`, 1 `none` | **Window**, plus AGSI is a data app that search ranks poorly. |
| 7 | Cook's own write-up with 42/58 (8–11 Sep poll) | the results page yes; the write-up no (403 to the grader) | 7 queries, **all `pw`** | **Window**, plus a paywalled or blocked page. |
| 2 | NEJM "CMS Innovation Center at 10 Years" (2021) | only as a ResearchGate copy (commentary, unmapped) | 7, `none` | **Discovery/paywall:** the journal page was never returned; the copy was, and was left unmapped. |
| 6 | Trump's own OGE Form 278e | no | 7, `none` | **Vocabulary:** no query says "OGE", "278e" or "financial disclosure report". |
| 13 | GRL 10.1029/2026GL122424 | a *different* GRL paper (GL125079) is | 8, mixed | **Discovery:** the right study was not found; a neighbour was. |
| 15 | NHS England release + OSR ruling on the 29% | no | 8, `py`/`none` | **Discovery:** the queries are reasonable, and the results were not stored. Needs a query probe. |

## Fixed today: dated events outside the window (#4, #5, #7)
- **What was missing:** B4 (`_inject_freshness_for_historical_dates`) widens the window only for claims about **earlier years**. Nothing widened it for an event earlier **this** year that was older than the window the planner chose. The pd/pw exemption also stops the unwindowed twin and the hedge from rescuing such lanes.
- **The rule:** `query_planner._widen_freshness_for_dated_events` reads the claim's earliest stated month in the current year (month-level periods, plus "September 8-11, 2026"-style day ranges) and widens the window just enough to reach its first day: pd → pw → pm → py → 2y. It is widen-only and per claim.
- `RETRIEVAL_CACHE_VERSION` is bumped to `2026-09-28` in the same commit (piece 3 rule).
- ⚠️ **Honesty note:** part of this failure is an artefact of the re-measure. These claims were first checked within days of their events, when `pw` was reasonable, and were re-run weeks later. A real user submitting a claim about a 3-week-old event would hit the same wall, so the fix is genuine. Its effect on the A− rate is measured only by re-running the same claims.

**Verified by probe:** see the last section. It clears #7, improves #4's pool, and does not help #5.

## Not fixed (named)
- **#6 vocabulary:** an official-filing lane ("financial disclosure report" / OGE) for claims about a public official's disclosed holdings. Needs design.
- **#2 paywall/copy:** a repository copy of a paper should be linked to its publisher record, not left as unmapped commentary. It relates to Build C (copy identity).
- **#13, #15 discovery:** the same class as Phase D. Do not attempt a query-side fix without first reading actual result lists.

## Probe: past week vs past month (founder-approved, 12 Serper calls, 2026-09-28)
The same queries as the stored plans, run with `pw` and then with `pm`:
- **#7: fixed.** With `pm`, Cook's own write-up ("new-battleground-district-poll-shows", rank 2–3) and the September methodology PDF (rank 1) are returned. With `pw` only the results page came back.
- **#4: the pool improved, H3 is not fixed.**
  - `pw` returned junk: Facebook posts, Medium, Wikipedia "Bauhaus", Britannica on the Soviet Union.
  - `pm` returns the real coverage: BBC, Time, DW, CS Monitor.
  - The returning officer's results page appears in **neither**. It is German-language, and every query is English. That needs a jurisdiction-native query lane (not built; needs design).
- **#5: no help.** GIE appeared once, as its homepage at rank 6, and only under `pw`. `pm` gave a mixed set (LinkedIn, X, low-grade aggregators). AGSI+ is a data app that search does not rank. The route to it is a GIE AGSI+ API adapter (not built).

**Net:** the widening is right, and it improves #4's pool a great deal, but it clears H3 on one record (#7) of three.
**What this points to for H3:**
- a native-language query lane for foreign official results (#4);
- an AGSI adapter (#5);
- an official-filing vocabulary lane (#6).
