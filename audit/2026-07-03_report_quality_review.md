# Report Quality Review — 2026-07-03

**Status (updated 2026-07-08): F1–F7 ALL SHIPPED / CLOSED.** Each finding ran its own design review → founder sign-off → build → independent adversarial verify (SOUND) → sign-off. F1 `328c329`, F2 `8857517`/`3d468c9`, F3 `11f1842`/`a2397d7`/`9db85a2`, F4 `d0d6d8b`/`d3a713f`, F5 `194c6d6`/`b87c316`/`9df0603`, F6 `24c44e0`, F7 `5165b65`. Design docs: `2026-07-07_f3_…`, `2026-07-07_f4_…`, `2026-07-07_f5_…`, `2026-07-08_f6_f7_…`. **Only F8 (landing pages + nav) remains — its own dedicated session.** Post-deploy owed: real-check eyeballs (F2/F3/F4/F6) + F7 replay-bench re-gold in a networked env (intended edu→analysis / reddit→opinion drift only). Original findings below unchanged (historical).

---

## 1. Origin & method

**Trigger.** Founder shared an external critique (ChatGPT) of the report for check **TRU-EC8D-8BC8** (claim: *"Britain is the only country in the world with a privatised water system"*; 1 claim, 2 elements, 20 sources; PDF exported 03 Jul 2026 09:03 UTC). Founder's own follow-up observations:
- The scope failure repeats with "Europe" — check **TRU-EAB8-2652** (LHC contributors).
- On the LHC check, **all evidence was dated 2026** despite the LHC being built 1998–2008 — no contemporaneous material.
- Open question raised: how exhaustive should Tru8 be? (e.g. should it enumerate every contributing country?)

**Method.** The PDF was read directly; six parallel investigations were run (2026-07-03):
1. PDF report generator (what it renders, when last touched, how it gets data)
2. Relevance-threshold history (git + audit archaeology — why the bar is where it is)
3. Evidence date provenance + retrieval recency mechanics
4. Echo/thin-support detector rules + surfacing + would-it-have-fired analysis
5. Decomposition/mapping scope-word handling + Claim Map contract constraints
6. External research: professional standards on evidence exhaustiveness + contemporaneous sourcing (web, cited)

**Reading the external critique.** Its factual observations largely held up under verification. Its *remedies* frequently did not — several would turn Tru8 into a verdict-renderer (e.g. its "ideal output" adjudicates the claim as "overstated"), which is locked out by product philosophy ("we organise; you decide", repositioning lock 2026-06-17). Rule applied throughout this review: **adopt the observations, reject the adjudication framing.**

---

## 2. Findings

### F1 — Historical claims get recency-strangled retrieval  【priority 1, with F2】

**Statement.** For a claim about past events that does not carry an explicit past-year date entity, retrieval is structurally biased to the last 12 months. Contemporaneous evidence is excluded *before retrieval begins*.

**Evidence (verified in code):**
- Default freshness `"py"` (past 12 months) on every planned query: `retrieve.py:1596, 1617-1621`; planner default `query_planner.py:131, 480`; recovery paths hard-code `"py"` (`retrieve.py:674, 959, 980`). Maps to Google `tbs=qdr:y` / Brave freshness (`search.py:405-412, 501, 605-612, 677`).
- Query planner prompt instructs: *"Use {current_year} in queries for recent events — NEVER use older years unless the claim explicitly refers to those years"* (`query_planner.py:310-311`); a sanitiser **rewrites stale years to the current year** for pd/pw/pm freshness (`query_planner.py:503-557`).
- Escape hatches exist but the triggers are too narrow:
  - NF-20/B4 `_inject_freshness_for_historical_dates` (`query_planner.py:67-108`, shipped `280e534` 2026-05-04) forces `freshness="none"` **only** when a DATE entity with year < current_year is present.
  - Date-anchor augmentation (`query_date_anchor.py:76-135`) requires **exactly one** year token — a range ("1998 and 2008") fails it.
- Historical-material adapters are routed out for the LHC claim shape: Library of Congress covers History/Politics/General only, **not Science** (`archives.py:225`), and is US-jurisdiction-only (`config.py:407-410`, filter `retrieve.py:2167-2172`); Wikipedia is stripped from the web leg via `-site:wikipedia.org` (`search.py:901`); Internet Archive/Wikipedia are tier-3 and frequent cap victims under `ADAPTER_CAPS_PER_DOMAIN` (`config.py:417`, tier sort `retrieve.py:2188-2203`).

**Consequence.** TRU-EAB8-2652 (LHC): a 1998–2008 topic yields an all-2026 evidence set — deterministically, not by chance.

**Why it matters.** Professional standards treat contemporaneous evidence as near-mandatory for historical claims (see §3). Our buyer will notice a 2026-only timeline for a 1998 event.

**Prior work / lineage.** NF-20 (B4) built the mechanism (freshness sentinel + injection); this finding is that its **trigger coverage** is too narrow (claims about the past without explicit single-year entities). NF-20-B (multi-claim inheritance gap) already tracked separately in the register.

**Solution direction (for design review — NOT designed):** a "claim concerns the past" detection that is broader than explicit-single-year (year ranges; past-tense event verbs; entity-type signals e.g. construction/founding/historical events), which (a) relaxes freshness and (b) upgrades archive-adapter routing. **Trade-offs to weigh:** wider windows admit stale/noisy material on current-affairs claims if detection misfires; retrieval latency; the R1/R2 retrieve-tail latency work (2026-07-02 review) pulls the other way.

### F2 — Evidence dates are the search engine's guess, with no provenance distinction  【priority 1, with F1】

**Statement.** One field (`published_date`) carries whatever date the search engine returned, verbatim. There is no distinction between publication date, host-upload date, and retrieval date. Displayed on source cards, the Chronologist timeline, and the signed PDF record.

**Evidence:**
- Serper's `date` trusted verbatim (`search.py:705`); SerpAPI (`search.py:525-529`); Brave incl. "3 days ago" relative conversion (`search.py:349-354, 379-397`).
- Engine date **beats** page metadata: only if the engine returns nothing does `_extract_date_from_html` run (`evidence.py:489-491`; parser at `evidence.py:671-748` — reads JSON-LD/OG/meta only, never derives from URL).
- Retrieval time exists (`Evidence.created_at`, `models/check.py:299`) but is never surfaced.
- **Concrete failure (TRU-EC8D-8BC8 source 1):** a 2000-era PDF displayed as "04 Apr 2026" — Google synthesised the date from the host's `/uploads/2026/04/` path; we ingested it unquestioned. Timeline plots the 2000 document at 2026 (`ChronologistView.tsx:146-147`).

**Why it matters.** Date integrity on a **signed** record is a trust primitive; law/history/fact-checking all weight evidence by date (§3). One visibly wrong date undermines the whole record's credibility for the researcher buyer.

**Solution direction:** (a) provenance labelling — record *where* the date came from (engine / page metadata / API adapter) and label low-confidence dates in the UI ("date as reported by host"); (b) plausibility checks (e.g. URL-path-date == engine date ⇒ suspicious; title-year ≪ displayed year ⇒ flag); (c) optionally prefer page metadata over engine guess when both exist. Distinguish publication vs retrieval in the PDF footer. **Trade-off:** page-metadata extraction costs fetch time; plausibility heuristics need a false-positive budget.

### F3 — Scope words pass through unexamined; no qualification channel  【priority 2】

**Statement.** Decomposition copies scope words ("Britain", "Europe") into elements verbatim with zero instruction to examine them. The mapping prompt's SCOPE CHECK covers only the *inverse* case (evidence narrower than a "worldwide/global"-worded element). When **all** evidence is narrower than the element and unanimous, the element resolves `supported` with **no caveat** — the existing caveat channel only fires on source disagreement.

**Evidence:**
- Decomposition prompts contain no scope/absolute/precision instructions (`claim_map_analyzer.py:138-163`, `:241-269`).
- SCOPE CHECK wording covers evidence-narrower-than-global only (`claim_map_analyzer.py:199-202`, `:311-314`).
- States are `supported/disputed/unresolved` (+ mechanical `contextual`); **no "supported with qualification"** (`claim_map_analyzer.py:193-197`; `models/claim_map.py:19-28`).
- Mechanical state derivation writes `basis["state_derivation"].caveat` **only when challenges exist** (`claim_map_analyzer.py:522-667`; all-supports path `:611-613` → caveat None).
- Claim Map contract is **silent** on element-wording fidelity — neither requires verbatim reuse nor permits/forbids tightening (contract `:220-226`; no verbatim/paraphrase constraint anywhere).
- **Not previously registered:** PQ register (PQ-01..09) has no scope item; OPEN_WORK had none before today.

**Concrete failures:** TRU-EC8D-8BC8 element 1 "Britain has a privatised water system — SUPPORTED" on evidence that says England and Wales (Scotland's water is public). Repeats with "Europe" on TRU-EAB8-2652.

**Why it matters.** This is precisely the semantic overreach an evidence-research tool should surface. The external critique caught it; so will professional users.

**Solution direction (philosophy-constrained):** do **not** rewrite the claimant's words (rewriting "Britain"→"England and Wales" puts words in the claim's mouth). Instead: (a) extend the mapping SCOPE CHECK to the element-broader-than-evidence case; (b) let the existing `state_derivation.caveat` channel fire on unanimous-but-narrower support (e.g. "supporting evidence addresses England and Wales, not Britain as a whole"); (c) consider a decomposition instruction to *flag* (not rewrite) scope-sensitive words. Keep state mechanics unchanged — the caveat describes the evidence's reach; it does not adjudicate the claim. **NF-11 lesson applies: prompt-only fixes are fragile — needs an eval pool (scope-qualifier claims: Britain/UK/England, Europe/EU, America/USA) with before/after measurement, and ideally a mechanical component.**

### F4 — Echo detector is blind to talking-point repetition  【priority 3】

**Statement.** The echo signal detects **syndication** (a primary source re-reported by ≥2 independently-owned outlets) but not **repetition** (multiple non-primary sources reciting the same formulation with *no* primary anchor). The second pattern is how received wisdom propagates — arguably the more dangerous one.

**Evidence (verified against the water-claim element — 4 supporters: 2× Guardian [reporting], advocacy site + LSE blog [commentary]):**
- Echo requires a `tier=="primary"` anchor with ≥2 independent re-reporters (`corroboration.py:242-282`, anchor check `:262-263`). No primary in the set ⇒ machinery never starts. **Verified: would NOT fire.**
- The shared ~90-char sentence ("England and Wales are the only countries in the world with a fully privatised water system") is invisible to the matchers: fact extractor takes numbers/dates/quoted phrases of 10–50 chars (`corroboration.py:106`); text similarity runs on first-500-chars of articles (`corroboration.py:75-88`).
- Thin-note fallbacks also don't apply: 4 refs across 3 domains, 2 reporting-tier ⇒ neither "single outlet" nor "commentary-only" fires (`support-structure.ts:20-57`; `support_structure.py:20-48`).
- Surfacing (for reference): note renders on dashboard + public /r/ (same `ClaimSummaryPanel`/`ElementList`/`EvidenceQualityNote` tree); **not** in the PDF (F5) or OG card.

**Why it matters.** External critique's "counting documents, not independent evidence foundations" point stands. Professional norm is corroboration by *independent* sources (§3); N sources repeating one formulation with no primary behind it is exactly what the buyer wants flagged.

**Solution direction:** a second, mechanical condition alongside echo — e.g. side has ≥N sources, **zero primary tier**, and shared-formulation evidence (sentence-level shingle/similarity across items, not just first-500-chars) ⇒ "same account repeated; no primary source found" note. Reuses the existing note UI (grey, no verdict). **Trade-off:** sentence-similarity thresholds need tuning against false positives on genuinely independent same-conclusion reporting.

### F5 — The PDF report drifts by construction  【priority 4】

**Statement.** The PDF is a separate rendering path that prepares its own data; frontend improvements do not propagate. It is ~10 days behind the renewed frontend and will always lag.

**Evidence:**
- Backend WeasyPrint + Jinja template `backend/app/templates/pdf/fact_check_report.html` (623 lines); builder `_build_check_pdf_bytes` `checks.py:2188-2269`; owner route `:2272-2306`; public route `:2310-2340`.
- **Does not share the response builder** — passes raw ORM objects to Jinja and re-derives tier/type counts inline (`checks.py:2216-2220`).
- Last meaningful change 2026-06-23 (`09f10b7`, `ba1ee4c`) — pre-dates Evidence Digest (06-30) and echo/thin note (07-01).
- Omissions/weaknesses: per-card tier is a colour stripe only, no text label/legend (template `:389-391, 581-585` — the visible badge is `evidence_type`); thin/echo note absent; videos absent; Gaps/Seeker partial (unresolved elements + bounty text only, `:560-570`). Receipts **are** present (`:596-608`) — a strength.
- Healthy: no verdict-era language (footer states no verdicts, `:615`); branding current.

**Why it matters.** The PDF is the artefact people *share* (it is what the external critic reviewed) and it carries the signature. It is currently the weakest surface presenting the strongest trust claim.

**Solution direction:** structural decision first — feed the PDF from the same prepared/serialised data as dashboard + /r/ (single source of truth), or accept the duplicate path and bind it with a release checklist + parity test. Then content: per-card tier labels, thin/echo note, date-provenance labels (F2), digest-style summary. **Trade-off:** WeasyPrint templating constraints vs the richer JSON the response builder emits.

### F6 — Relevance scores exist but are displayed nowhere  【priority 5】

**Statement.** Every scored evidence item carries a 1–5 topical relevance score; no surface uses it. Peripheral (score 2) and core (score 5) sources are visually identical — the real substance of the external critique's "irrelevant sources" complaint.

**History (investigated — this closes a route):**
- The exclusion bar was **never** higher than score-1. Score-1-only exclusion was the *first* filtering the scorer ever did (`0859797`, 2026-02-18, PR-E04), deliberately conservative: *"the scorer should err on the side of inclusion"* (PR-E03 audit doc, Risk Notes).
- What was actually dropped earlier was the **editorial curation layer** (`cdc2038`, 2026-02-17): 2,340-domain credibility list, domain caps (measured: cap alone removed ~42% of evidence; some claims reached mapping with zero items), auto-exclusions — torn down on mission grounds (*"no hidden curation"*, filtration audit 2026-02-16).
- Raising the bar was **pre-gated** in `audit/track-e/06_evidence_count_analysis.md` §6: only if the scorer is validated AND volumes consistently exceed ~80–100 items/check — and even then, deprioritised items go to **visible receipts**, never silently dropped. Current volumes (~20/check) don't meet the gate. **⇒ Raising the exclusion threshold is a CLOSED ROUTE for now.**
- Mechanics for reference: `>=2` and unscored (None) kept; only score-1 excluded with receipts (`relevance_scorer.py:712-753`); the 50-item cap limits scoring cost, not admission (`relevance_scorer.py:609-613, 691-692`; `config.py:261`).

**Solution direction:** presentational — order or group by relevance; a "peripheral match" de-emphasis or label on low scorers; possibly a digest note ("14 of 20 sources bear directly on the claim"). Must be worded as *topical proximity*, never source quality, to stay inside classify-don't-score. **Trade-off:** any visible ranking invites misreading as a credibility score — copy needs the same care as the no-verdict language.

### F7 — Classification stretch + title capture  【priority 5】

**Statement.** Three small, confirmed professionalism defects:
1. **"Academic" over-broad** — TRU-EC8D-8BC8's six "academic" sources include Global Water Partnership, World Water Council, Brookings, and an LSE blog. One (National Academies) is unambiguously academic.
2. **No "discussion" type** — forums have no honest label; Reddit surfaced as "ANALYSIS". (NB the heuristic maps social media → commentary/opinion (`evidence_classifier.py:161-167`); the LLM path presumably assigned "analysis" — worth confirming which path labelled it. Tier=commentary is the weight signal and was present but invisible in the PDF — see F5.)
3. **Title capture** — Reddit's stored title is "Reddit - Please wait for verification" (the interstitial page), not the discussion title.

**Solution direction:** (a) tighten academic criteria (peer-reviewed venue / university press vs institutional reports → analysis); (b) add a `discussion` evidence type (touches type enum, prompts, heuristics, UI badges, PDF); (c) title post-fetch cleanup — detect interstitial/consent-wall boilerplate titles and fall back to search-result title. All small; bundle as one classification-hygiene item.

### F8 — Landing pages + navigation need streamlining  【added 2026-07-06, founder; public surface, own review track】

**Statement.** The homepage (`/`) and the `/research` app landing page present the current offering too densely — still confusing for a human visitor. Needs a real tightening and honing: less information, more concise listings of features and functionality; a review of routes, nav, and overall ease of use; and upgraded screenshots — the results page has changed considerably since the current captures (Evidence Digest 06-30, element platforming, echo/thin notes, neutralised state colours).

**Origin.** Founder observation 2026-07-06, on the back of the F1–F7 review — the same "will the researcher buyer trust this?" lens applied to the front door rather than the report.

**Relationship to prior work.** The 2026-06-29 page review covered copy/positioning/design-grammar (P0s shipped; some P1/P2 remain). F8 is a *different lens*: information density, streamlining, wayfinding, and visual-asset currency. It extends, not replaces, the remaining 06-29 items.

**Process (founder-directed, explicit).** Do **not** dive in from this doc. F8 requires a **segmented conversation with dedicated context** — a fresh session running a deeper review (page-by-page, human-confusion-first), producing its own design review before any build. Noted here only so it is registered and sequenced.

**Scope sketch (for the dedicated session to refine, not binding):** homepage offering presentation · `/research` landing · routes + nav map + ease-of-use walk · feature/functionality listings condensed · screenshot/asset refresh against the shipped results UX.

---

## 3. Professional-standards brief (external research, 2026-07-03, cited in the research log)

Condensed; full citations in the research output (Cochrane Handbook ch.4, PRISMA 2020 E&E, IFCN Code commitments, Reuters Handbook, BBC Editorial Guidelines, Reuters Institute on Bellingcat, Cornell LII).

**On exhaustiveness (the founder's "list all contributing countries?" question):**
- **No standard requires enumeration.** Systematic review: comprehensiveness is a property of the *search method* (reported, replicable, within resource limits), with recognised **stopping rules** ("saturation"). Fact-checking (IFCN): *relevant* evidence both ways, replicable — "relevant", never "all". Journalism: **corroboration** (≥2 independent sources), reluctance on single sources. Law: "diligent search", not exhaustive.
- **Convergent expectation for a universal claim** ("only European countries…"): several independent counterexamples — ideally anchored in a primary source (e.g. CERN's own contributor records) — **plus a pointer to the authoritative complete record**, with search method transparent. Enumeration is an encyclopaedia's job, not an evidence organiser's.
- **Tru8-shaped implementation of that norm:** representative counterexamples + a Seeker-style entry marking the boundary ("a complete contributor list exists at <source>; not enumerated here"). Honest about the search boundary; no pretence of exhaustiveness.

**On contemporaneous evidence (the LHC dating observation):**
- History: near-mandatory (primary sources define the discipline; temporal distance = unreliability). Law: contemporaneous documents carry the greatest weight. Fact-checking (IFCN): primary sources required "wherever available"; recent secondary coverage is a fallback. Journalism: first-hand preferred, corroborated secondary acceptable.
- ⇒ For 1998–2008 events, period documents should appear **alongside** retrospectives. Directly motivates F1+F2.

**Vocabulary worth adopting in product/marketing copy** (speaks the buyer's own standards language): *evidence sufficiency* (vs exhaustiveness), *comprehensiveness of method, not of results*, *search saturation / stopping rules*, *best available primary sources* (IFCN exact phrase), *corroboration*, *replicability*, *diligent search*, *contemporaneous evidence*, *provenance*.

---

## 4. What was verified about the critique itself

| External critique point | Verdict after investigation |
|---|---|
| "Britain" unresolved vs England+Wales | **Confirmed** (F3) — and repeats on "Europe" (founder's test) |
| "Privatised water system" not consistently defined | Confirmed as observation; remedy = Seeker definitional-ambiguity entry, **not** adjudication |
| Several sources add little | Confirmed; root = no relevance display (F6), NOT admission threshold (closed route) |
| Supporting sources not independent ("counting documents") | **Confirmed and sharpened** (F4) — detector verified to not fire on this shape |
| "Six academic" misleading; Reddit as "analysis" | **Confirmed** (F7); tier signal existed but invisible in PDF (F5) |
| Date integrity (2000 doc shown as Apr 2026) | **Confirmed with mechanism** (F2) — engine-synthesised from URL upload path |
| Its "ideal output" (adjudicated conclusion) | **Rejected** — verdict-rendering, contradicts locked philosophy |
| Its overall scores (7.3/10 etc.) | Noted, not adopted — methodology opaque |

---

## 5. Design-review agenda (proposed order)

| Order | Items | Review question | Key tension |
|---|---|---|---|
| 1 | F1+F2 (one review — they interact) | How do we detect "claim concerns the past", and what date provenance do we record/display? | Detection misfires admit noise; retrieve latency (R1/R2 work pulls the other way) |
| 2 | F3 | Where does the scope caveat live (mapping prompt? mechanical caveat? both?) and what exact wording keeps it descriptive, not adjudicative? | NF-11 lesson: needs mechanical component + eval pool, not prompt-only |
| 3 | F4 | What mechanical condition defines "repetition without primary anchor", and at what thresholds? | False positives on independent same-conclusion reporting |
| 4 | F5 | Single data path for the PDF, or checklist-bound duplicate? | WeasyPrint constraints vs response-builder JSON |
| 5 | F6+F7 | Relevance display wording; classification hygiene bundle | "Peripheral" must not read as a credibility score |
| — | F8 (own track) | Landing pages + nav streamlining — **dedicated session with fresh context, not this review's queue** | Less information vs AEO/SEO content needs; screenshot refresh depends on results-UX being stable |

**Standing rules for all of the above:** design review with founder sign-off BEFORE build ([[phased-build-loop]]); no verdict language anywhere; every exclusion keeps a receipt; replay bench (`--all`) before any pipeline-touching commit; scope-sensitive changes need eval pools with before/after measurement.

---

## 6. Also completed this session (for the record)

- **M1/D1 prod verification (quality-regression check on 2026-07-02 latency work):** scoped read-only telemetry query (`scripts/verify_m1_d1_prod.py`, untracked) against prod. Post-deploy checks `e432515b` (07-02) and `ec8d8bc8` (07-03): analyze 13.9s/11.1s (was 35–50s), distil 7.4s/12.0s (was 16.7–24.5s) ⇒ **M1 live and working; D1 consistent.** Retrieve now the tail (20.7s/30.7s) — matches the R1/R2 expectation. Independent re-analysis of the mapping sweep raw results (2 pools present locally) confirmed modal element states identical dynamic-vs-0 and budget-0 *more* consistent (dynamic had a coverage-0 timeout blowout run). Residual watch item: distil `items_skipped` ratio under multi-claim load (silent snippet fallback under concurrency) — read alongside `stage_timings_s` in a few days.
- **Token-path fix in the verify script:** `by_stage` lives under `cost_telemetry.llm.by_stage` (not top-level) — first query read timings correctly but token columns wrong path; corrected for next run. `thinking_tokens` confirmation still pending that re-run.
