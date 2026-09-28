# PRIMARY tier review — 2026-09-28 (A− H4)

**Question:** why do 10 of 18 re-measured records still put weak sources in PRIMARY after Build A (`173a26c`)?
**Data:** 91 PRIMARY items across the 18 re-run pools (of 286 items). Graders' H4 findings are in `audit/a_minus/2026-09-28_rerun/`. The dump script's output is in the session scratchpad. Nothing was re-run for this review.

## What is wrong, by cause
| Class | Items | Records | Cause in code |
|---|---|---|---|
| **A. Third-party trackers and live dashboards** | oireachtasconnect, voltstack ×2, global-energy-flow ×2, energyriskiq, tracefour, projectcuria, inquirytracker.uk, orbitalradar ×2 (+ climatechangetracker, not flagged) | #3 #5 #6 #11 #18 | The LLM reads a page of figures as `primary/data`. The only cap is a 2-host aggregator list (`_AGGREGATOR_HOST`: statista, tradingeconomics). |
| **B. Adapter results forced primary** | Wikipedia (#19); Open-Meteo, NOAA CDO (#12, also off-topic) | #12 #19 | `_high_confidence_override` and `_classify_heuristic` return `primary` for **any** `external_source_provider`. So the Wikipedia adapter is primary/data, while a wikipedia.org URL from web search is commentary. No quality floor covers `_REFERENCE_PLATFORMS`. |
| **C. URL identity over-reach** | bmj.com news story by C Dyer (`llm+override`); `go.nature.com` shortlink that is really Carbon Brief | #11 #13 | `_ACADEMIC_PATTERNS` treats every bmj.com / nature.com URL as academic, including news sections and shortlinks. The BMJ override *raised* the LLM's verdict. |
| **D. LLM judgment on non-originators, mostly UNMAPPED** | KFF explainers ×2, hcttf trade coalition, UnitedHealth white paper, off-topic AAP article, lloydsbanktrade, libretexts course page (mapped) | #2 #6 #10 #12 | No mechanical signal. Build A moved unmapped rows out of the tier bands, but each row still shows a "Primary" badge, and graders count it. |
| **E. Unreadable page** | gas.kyos.com: an unrendered `{{ template }}`, "No current data available" | #5 | Classified as primary/data on its title alone. |

## Rejected: "primary only where publisher identity proves it"
Simulated on the 91 items (keep if a gov/academic/data-portal pattern matches, or if the host is the claim's own subject):
- It demotes 38 items. It catches every class A and D item.
- It also demotes about 12 genuine primaries: cso.ie ×3, oecd.org, thirlwall.public-inquiry.uk, centralbank.ie, worldweatherattribution.org, globalcarbonbudget.org, research.rug.nl, esawebb.org, portal.research.lu.se, esd.copernicus.org.
- It still misses classes B and C.

The identity patterns are too UK/US-centric to be a whitelist. Rejected.

## Proposed build (lower-only, like Build A)
1. **A: tracker cap.** Cap primary at reporting when the title or URL carries `tracker | live | today | updated daily`, unless the host matches the gov / academic / data-portal patterns (which keeps JRC, ECDC and gov trackers). Propagate within the pool: once one page on a host trips the cap, cap the host's other pages too (GEF trajectory, orbitalradar `/satellites/`).
2. **B: adapters.** The Wikipedia provider gets reference treatment (commentary/analysis), and `_REFERENCE_PLATFORMS` joins the quality floor. Off-topic weather adapters (a North Sea forecast at Long Island coordinates for a CO2 claim) are a routing bug, logged separately under S5.
3. **C: identity override.** The URL-identity override never *raises* an LLM `reporting` verdict on mixed publishers (bmj.com, nature.com, science.org). Shortlink hosts (`go.nature.com`, etc.) never count as academic identity.
4. **E:** an unreadable-template page cannot be primary.

**Expected H4 effect on the 10 failing records:** clears #5, #11, #13, #18, #19. #11 and #18 would become B+, since H4 was their only hard fail. #2, #3, #6, #10 fail only on unmapped rows (class D). #12 keeps the libretexts row.

**Open decision (D):** should an unmapped row carry a tier badge at all? If it should not, #3 reaches A− (only S5 would remain), and #2, #6, #10 clear H4.

Verification owed: unit tests with mutants, the replay bench against a control arm (tier changes re-key cassettes), and a replay on the 18 stored payloads.

## As built — 2026-09-28 (founder: "build it")
All in `backend/app/pipeline/evidence_classifier.py`. Everything is lower-only and last-pass.

**Per-item caps, in `_apply_primary_cap`:**
- Order: news → aggregator → shortlink → (identity exemption) → unrendered → tracker.
- `shortlink_cap`: `go.nature.com`, `bit.ly`, `t.co` and similar. The publisher behind a shortlink is unknown, so it cannot be primary.
- **Identity exemption:** a host matching the gov / academic / data-portal patterns is never capped by the rules below it.
- `unrendered_cap`: text holding a `{{ … }}` template.
- `tracker_cap`: the title matches `tracker|live|today|updated daily|real-time`, or `tracker` appears in the host or path.

**Other rules:**
- `tracker_host_cap`: a pool pass inside `classify_batch`. Once a host is capped as a tracker, its other PRIMARY pages are capped too.
- `reference_floor`: a `_REFERENCE_PLATFORMS` URL (Wikipedia, YouTube) at primary becomes commentary/analysis, whichever adapter it came from.
- `_keeps_news_verdict`: on bmj.com, nature.com and science.org, the URL-identity override no longer raises an LLM **reporting** verdict. A commentary verdict is still overridden, because the known failure is the LLM under-calling journals.

**Tests:** 25 new in `tests/unit/pipeline/test_e06_classifier.py`, including a wiring test through `classify_batch`. 8/8 mutants are killed: each rule removed, the identity exemption removed, lower-only removed.

**Replay on the 18 re-run pools** (the tier caps, without the LLM):
- 14 tier changes, all intended: #3 ×1, #5 ×6, #6 ×1, #11 ×1, #12 ×1 (climatechangetracker), #13 ×1, #18 ×2, #19 ×1.
- **0 element state changes.**
- Not demoted: JRC, CSO, Cook, NASA, whereyourmoneygoes.gov.ie, OWID.
- The BMJ override change needs the LLM's own verdict, so it is covered by tests only.
- Not caught, as expected: projectcuria (unmapped), class D rows, and the off-topic weather adapters (a routing bug, logged under S5).


## Decision — 2026-09-28 (founder)
Class D: unmapped rows **keep** their tier badge. The H4 check still applies to them, so class D is fixed in the classifier, not by hiding the label.
