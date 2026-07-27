# C3 capture test — findings & retrieval-quality defects (2026-07-09)

**Status:** C3 (/compare correction) **PARKED** on these findings. This doc is the canonical grounding for the follow-up **retrieval-quality investigation** (new session, own plan).
**Companion artefacts:** Tru8 check **TRU-C051-3024** (live: trueight.com/r/TRU-C051-3024, 200 OK; founder's PDF `c:\Users\james\Downloads\tru8-report-c0513024.pdf`) · Webcite capture `audit/2026-07-09_webcite_capture.json` (abridged; founder holds the full playground JSON) · June competitor audit `audit/2026-06-24_pricing_research_plan.md` (§B) · live re-verification of Webcite/scite/Factiverse in the 2026-07-09 session log (OPEN_WORK).

---

## 1. What was done (method)

C3 was to correct `/compare` (currently vs grounding APIs) toward the direct competitors. Rather than a claims table, we ran the founder-approved **capture test**: the SAME input through webcite.co's playground and Tru8's full pipeline, same day (2026-07-09), outputs verbatim.

**Input** (paragraph form — Webcite's bare-claim run failed twice with `"summary": "Verification error"` inside a `result: "unverified", confidence: 0` verdict; the paragraph run succeeded):

> Studies have long suggested that moderate alcohol consumption protects against heart disease, which is why many doctors historically recommended a daily glass of red wine.

## 2. Webcite's output (context — their side)

- Competent citations engine: ~30 sources, per-source stance + confidence, credibility scores, domain grouping, primary-source flags. Their index rides Google grounding (verbatim `vertexaisearch.cloud.google.com` redirect URLs leak through as sources).
- Deliverable: `result: "partially_false", confidence: 57` + a **self-refuting correction** — sub-claim *"Studies have long suggested that moderate alcohol consumption protects against heart disease"* marked **contradicted**, while their own cited snippet (mensjournal.com) reads *"while some older studies suggested a protective effect…"* — i.e. the citation affirms the sub-claim it is counted against. Classic conflation of "the claim reports a suggestion" vs "the suggestion is true" — the failure mode element decomposition + no-adjudication exist to prevent.
- Their quality warts (for fairness if ever published): wine-merchant blog as *supports, 95 confidence*; a stance explanation copy-pasted from a different source; scraped page chrome as a snippet; three key findings with three different denominators.

## 3. Tru8's output — the honest read (founder's verdict: "actually, pretty poor?" — partially right)

**Claim 01** ("Moderate alcohol consumption protects against heart disease", causal-interpretive, 4 elements) — **defensible**: real academic anchors (burden-of-proof study, Mendelian randomisation, PubMed/OpenAlex), element reasonings capture the true scientific state ("observational studies interpret as protective; Mendelian randomisation does not support") better than a `partially_false 57`. R7's orientation fix visible in prod output ("2 challenged with none supporting").

**Claim 02** ("Many doctors historically recommended a daily glass of red wine", empirical, 3 elements) — **poor pool**: sources = Reddit, TikTok, one Yale news page, for a claim whose literature (French-paradox era) is abundant. States correctly landed unresolved/disputed with **thin-sourcing flags** — the detector worked — but the retrieval underneath failed.

**The consolation that matters:** our record *diagnosed its own weakness* (named gap, thin flags, "lacking sufficient evidence") where Webcite emitted a confident verdict regardless. But a prospect comparing source columns sees Harvard/Mayo/AHA/Columbia on their side and TikTok on ours. **Hence: do not publish this pair.**

## 4. The two pipeline defects (the investigation's subject)

**F-R1 — WHO adapter noise in the shown pool.** Claim 01's pool contains THREE WHO "health indicator" policy pages ("National alcohol policy specifically involves young people activities", "Existence of operational policy/strategy/action plan…", "Standards of care for professionals…") classified PRIMARY/official-statement and mapped as *context* — near-zero topical value for the claim. Questions: what `llm_relevance_score` did these carry (F6 scorer rubric should have scored them low — did they score ≥ threshold, or slip past the scorer)? Is this the WHO adapter's query shape returning indicator-index pages (same class as the known UK-gov 0-yield / adapter query-shape ceiling)? Should the classifier's PRIMARY-tier assignment for generic indicator pages be revisited?

**F-R2 — historical-claim retrieval failure.** Claim 02's queries never reached the French-paradox / history-of-medical-advice literature and settled for social commentary (Reddit, TikTok). Questions: what queries did the planner emit for these elements (element 01 "historical records or testimonies exist…" is an odd, meta-shaped element — did decomposition shape doom retrieval)? Did recency steering / freshness defaults (F1 territory — hedge shipped `328c329`) suppress the older literature this claim NEEDS? Did academic adapters fire for claim 02 at all (its pool shows zero academic sources vs claim 01's five)?

**Also worth checking while in there:** why claim 02's pool is only 3 sources post-filter (filter cascade receipts for this check will say); whether coverage recovery ran for claim 02's unresolved element.

## 5. Investigation starting points (for the new agent)

1. Pull the check's telemetry + receipts: `TRU-C051-3024` — retrieval queries per element, filter cascade exclusions, `llm_relevance_score` per shown source (esp. the 3 WHO items), adapters fired per claim.
2. F-R1: trace WHO adapter query construction (`retrieve.py` + WHO adapter) for this claim's entities; check scorer scores on indicator pages; consider adapter-level filtering of indicator-index pages.
3. F-R2: trace decompose output for claim 02 (element shapes) + query planner windows (pd/pw/unwindowed — F1-D3 hedge behaviour on "historically" claims); check whether Semantic Scholar/OpenAlex/PubMed fired for claim 02.
4. Replay-bench discipline applies to any fix (`backend/scripts/replay_bench.py --all`); NF-11 rule: prefer mechanical fixes over prompt-only.
5. NOT in scope: Webcite anything — this is our pipeline. C3 publishing decision comes after (see §6).

## 6. C3 disposition

**PARKED.** The structural differentiation argument survives (their self-refuting verdict is the proof), but this specimen would platform our weakest dimension. Two revival routes, later, founder-gated:
- **Battlefield option:** rerun the capture test on a UK political/economic claim, where GOV.UK/Hansard/ONS/FRED primary documents sit in our column and outside their consumer-web index.
- Re-run this claim after F-R1/F-R2 fixes land.
The existing `/compare` page stays as-is (grounding-API layer comparison — honest, never claimed those were competitors). The scrapped table design + verified competitor facts (Webcite/scite/Factiverse, live-checked 2026-07-09) are preserved in the session log for whenever C3 revives.
