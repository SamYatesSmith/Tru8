# Dissent discovery — live probe of Serper, Brave Goggles and alternatives (2026-09-02)

**Trigger:** the TTE send was held after a 15p re-run (`b0398fca`) lost the recipient's own critique
from the pool. Founder: *"run a search on serper.dev … it may have improved … there may be
something else that could definitively improve this sort of issue."*
**Method:** the 2026-08-20 rule — issue the query and read the results (pence, seconds), on the
claims whose rebuttal URL is KNOWN. ~40 Serper queries + ~15 Brave queries, well under 10p.
**Companion:** `2026-08-20_independent_source_lane_design_review.md` §9 (Phase D, 0/3, deleted).

## 1. The finding: the claim lane's date window is the killer

The pipeline's claim lane (`c0`) runs the claim text **once**, inheriting the first element plan's
freshness — `pm` (past month) on both TTE runs. The F1-D3 hedge unwindows only *position 1* of a
lane; the synthesised claim lane has one query, so **the plain claim text never runs unwindowed**
(`retrieve.py::_synthesise_claim_lane_plan`, `_hedged_query_freshness`).

Serper, **exact pipeline parameters** (`gl=gb`, `num=13`), 2026-09-02:

| case (known rebuttal) | unwindowed | `tbs=qdr:m` (what `c0` ran) | `qdr:m,sbd:1` | `qdr:y` |
|---|---|---|---|---|
| TTE — trusttheevidence.substack.com | **rank 3** (dated 7 Aug) | 6 results, ALL instagram/linkedin/facebook | 8, no TTE | 7, no TTE |
| Scotland — futureeconomy.scot/587 | **rank 3** (dated 1 Aug) | 4 results, ALL facebook | 7, no target | **rank 2** |

`facebook.com`, `instagram.com`, `linkedin.com` are on the runtime blocklist
(`domain_status_tracker.py`), so the windowed claim-lane results were **discarded in full**. On these
claims the claim lane contributed nothing, the element lanes searched in their own decomposed
vocabulary, and whether the critic appeared depended on run-to-run churn in those lanes. That is
the mechanism behind `11f54993` (critic present) vs `b0398fca` (critic absent).

⚠️ The 20 Aug review's "plain query ❌" on Scotland records no parameters (window, `gl`, `num`),
so the difference from today's rank 3 cannot be attributed — ranking drift or a windowed default.
Today's numbers are the ones to build on; re-probe before shipping.

## 2. Brave Goggles — a different RANKER, already in the stack

Brave is the chain's second provider and the key is set. The Web Search API accepts an inline
Goggle (`$boost` / `$downrank` / `$discard` by site or path). Same claims, `country=GB`, `count=13`:

| case | Brave plain | claimant-aware goggle¹ | **generic goggle²** |
|---|---|---|---|
| TTE | absent | **1, 2** (two TTE posts) | **2, 3** |
| Scotland | 2 | **1** | **2** |
| Dairy — gidmk.substack.com | absent | absent | absent |

¹ downrank the claimant domain (+ syndicators), boost substack/BMJ. ² no claimant knowledge:
boost `substack.com`, `ghost.io`, `medium.com`; downrank `facebook.com`, `instagram.com`.

The generic goggle needs nothing per claim. Brave's own `freshness=pm` keeps TTE (3, 5) and
correctly drops the 1 Aug Scotland post; Google's month window returned only blocked social links.

**Dairy stays unfound by every mechanism** — the rebuttal is framed "heart health" while the claim
is about weight; substack-boosted results are other nutrition Substacks. This is the framing
problem the 20 Aug review named; nothing here touches it. Honest ceiling: **2 of 3**.

## 3. Serper features assessed (nothing new that helps)

Endpoints now: search, news, images, videos, places, maps, shopping, scholar, patents,
autocomplete; responses carry `peopleAlsoAsk`, `relatedSearches`, knowledge graph. Tested:
- **/news** — no rebuttal on any case (news index = outlets, not Substacks).
- **relatedSearches / peopleAlsoAsk** — empty for every long claim query.
- **autocomplete** — numeric noise ("nhs app ai triage 2924"); useless for dissent.
- **`sbd:1` sort-by-date** — trade press and syndicators, no rebuttal.
- **/scholar** — academic only; not this problem.
Serper remains the right primary; it has not grown a dissent feature.

## 4. Alternatives priced against the no-Exa rule (cost per query is the constraint)

| service | what it adds | cost | verdict |
|---|---|---|---|
| Brave Goggles | custom re-rank on Brave's index | £0 extra (existing plan) | **use** |
| Kagi Search API (Small Web lens) | index of personal sites/newsletters | $12/1k ≈ 1p per query | over the rule for every check; maybe on-demand |
| DataForSEO Backlinks | pages that LINK to the claim's source URL — rebuttals cite what they rebut | ~$0.024/request ≈ 2p | over the rule per check; a natural Seeker "find responses" action at 1 credit |
| Tavily / Perplexity Sonar | agentic search that reformulates and reads | $5–8/1k + tokens | ruled out (2026-05-15 rule) |
| Google Programmable Search over a curated critics list | a hand-built index of factcheckers/think-tanks/newsletters | free tier 100/day | brittle list; not now |

## 5. Proposed builds (decision owed — nothing built)

**A. Unwindowed claim-lane twin (mechanical, tiny).** Give the claim lane a second query: the
same claim text with freshness `none`, so the F1-D3 hedge's guarantee finally covers the lane
that carries the claim's own words. +1 Serper query/check (~0.1p). Measured today: TTE rank 3,
Scotland rank 3. ⚠️ Changes every corpus claim's request set → **bench cassette drift, re-record
(~£0.80)** — and the bench cannot verify the change itself (25/40 URL churn); the proof is the
probe above plus a control-arm re-run of the two claims.

**B. Generic dissent goggle lane (design, small).** One Brave query per claim with the generic
goggle, its results fed through the normal pipeline with **≤2 fetch slots** (commentary weight 1
vs support floor 3 — the sycophancy ceiling from the 20 Aug review), direction-neutral (the mapper
decides supports/challenges; the lane only widens the pool). Measured today: 2/3 known cases.
Name it for what it does — "independent-publishing lane", never "challenge lane".

**C. Not solved:** framing-mismatch rebuttals (dairy). Only a reasoning step (model with search
tools) or backlinks reach it; both cost more than a check earns. Park; disclose on the page.

**Cheapest honesty fix, orthogonal:** the GAPS lens must stop saying "well covered" when the pool
holds no challenge and the supports trace to one original (the 2026-08-24 parked gap #3).

## 6. What this changes for send week
Nothing today: Viglione, Seymour, McSweeney go on their current records (dissent present).
TTE and Tapper wait for A (and ideally B), then a fresh run each.
