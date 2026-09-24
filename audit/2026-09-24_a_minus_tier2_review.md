# A− tier 2: independent design review

**Date:** 2026-09-24. **Reviews:** `audit/2026-09-24_a_minus_tier2_design.md`.
**Method:** every claim in the design was checked against the code (file:line below). All 19 public payloads were fetched (`/checks/public/<id>?detailed=true`, curl, free) and each rule was replayed offline against them: which rows it touches, which grader fails it clears, and which element states it moves (state recomputed with `_derive_element_state_with_authority`'s rules, weights 3/2/1, floor 3). No Tru8 checks were run and no code was changed.

## 0. Verdict in one paragraph

**APPROVE WITH CHANGES overall.** The intent is right: act on the source or the element, never on a direction. But the design has four factual errors that change what gets built:
- **A1** is not a new rule. A social-media floor already exists; it misses `threads.com`.
- **A2 as scoped** ("specialist adapters") reaches 2 of the ~14 offending PRIMARY rows. Almost all are web or coverage-recovery items, and they are all unmapped.
- **C1** assumes one global URL tracker. There are six raw-string URL checks.
- **D** routes repairs through `_repair_questions`, which never runs on any of the five filler records.

On the 19 records, the design as written clears H4 on **2/11** records and S4 on **2/10**. The revised builds below clear H4 on **7/11** and S4 on **4/10 fully (plus #13 mostly)**, with **one** state change, which the founder must accept.

---

## Build A: primary means primary (H4, 11 records)

### Facts checked
- Tier is set in `backend/app/pipeline/evidence_classifier.py`, in this order:
  1. The LLM classifies.
  2. `_high_confidence_override` (`:543`) forces data portals, academic publishers and gov domains.
  3. `_apply_quality_floor` (`:621`) runs last and forces tabloid, social, blog, infrastructure, low-authority-firm and preprint items down.
- **News-domain list: it exists.** `_WIRE_SERVICES` (`:300-320`) holds Reuters, BBC, Guardian, FT, Bloomberg and others. It is used **only** by the heuristic fallback (`_classify_heuristic`, `:505`), never as a floor. So an LLM "primary" verdict on a Guardian URL stands. All 19 records' PRIMARY rows are `classificationMethod: llm` (or `llm+override`).
- **A social floor already exists.** `_SOCIAL_MEDIA` (`:350-354`) plus `social_media_floor` (`:645-657`). The regex has `threads\.net` but not `threads\.com`, where Threads now lives. The Brilliant Maps post (#4, `ev-6783185ed792`) and the thejournal repost (#8, `ev-1e570ad8369f`, `reporting`) are both `threads.com`. LinkedIn and Bluesky are also absent. YouTube is in `_REFERENCE_PLATFORMS` (heuristic only, no floor).
- Tier enters the mapping prompt as `[Tier: …]` (`claim_map_analyzer.py:1774, 2003, 3395, 3623`). **Any tier change re-keys the mapping cassette** of every corpus claim that has an affected item, not only `_STATE_TIER_WEIGHTS` (`:957`).

### The offending PRIMARY rows, from the payloads

| # | Offending PRIMARY rows | Mapped? | Cleared by (revised) |
|---|---|---|---|
| 3 | CBP-8046 pdf, CBI bulletin, oireachtas tracker, tradingeconomics, statista | all **unmapped** | A2′ |
| 4 | Threads Brilliant Maps | context e3 | A1′ |
| 5 | global-energy-flow tracker (context e1); Energy Aspects (unmapped) | mixed | **not cleared** |
| 6 | World Bank (adapter, unmapped); Guardian, abcnews.com (both `ev-rec`, context) | mixed | A2′ + A3′ |
| 8 | cordis, sfi.ie | unmapped | A2′ |
| 10 | Commons Library (`llm+override`), Bank of Ireland shell | unmapped | A2′ |
| 11 | bmj.com news piece (`llm+override`, academic), **supports e3** | mapped | **not cleared** (see A3) |
| 12 | Statista, **supports e2** | mapped | aggregator cap (state change) |
| 13 | hadea, Copernicus air quality | unmapped | A2′ |
| 16 | Open-Meteo (adapter, unmapped); **WWF challenges e1** | mixed | **not cleared** (A5 = no rule) |
| 17 | EFFIS shell, Lancet smoke (unmapped); **Copernicus "hottest month" challenges e1** | mixed | **not cleared** (it is an H2 map fault) |

### A1: social posts. **APPROVE WITH CHANGES** (difficulty 1, not 3)
- Add `threads\.com`, `linkedin\.com` and `bsky\.app` to `_SOCIAL_MEDIA`. That is the whole build. It clears **#4**. It also demotes #8's Threads repost from reporting to commentary (e1 weight 20 → 19, no state change).
- **Do not floor YouTube.** YouTube is a host, not an author. A broadcaster's own upload is reporting, and #1's YouTube support is `reporting`. If anything, cap YouTube at "never primary". No H4 case on this set needs it.
- Risk: none on the bench. No `threads.com` or `linkedin` URL appears in `tests/replay_corpus`.

### A2: off-topic officials. **APPROVE WITH CHANGES: rescope to all unmapped items, rendered on read**
- Option (ii) is limited to "specialist adapters". Only 2 of the offending unmapped rows have an `externalSourceProvider` (World Bank #6, Open-Meteo #16). Everything else is web or `ev-rec-*` recovery. **As scoped, A2 clears no record on its own.**
- The frontend deliberately shows unmapped items in the heatmap and ledger with no badge (`web/components/evidence-views/librarian/LibrarianView.tsx:111-118`, citing "no hidden curation").
- **Revised A2′:** at render, move every `receiptStatus: 'unmapped'` item, from any origin, out of the tier bands into a visible, counted group.
  - Label it **"Gathered — not mapped to any part of the claim"**, never "not related". #2's unmapped CMS Strategy Refresh and Reports to Congress are on-topic (the grader passed S5 and failed H3 because they were *not* mapped). A "not related" label would be false.
- Why this is the better route:
  - It is frontend-only and applies on read to every stored record.
  - No pipeline change, no state change (unmapped refs carry no weight), no bench, and no manifest effect. It changes display grouping, not `content_basis` or tier.
  - Invariant #5 holds because nothing is hidden.
- Counters must reuse tier 1's definitions (S6 was the most-failed check).
- **Clears H4 on #3, #8, #10 and #13 by itself**, and on #6 together with A3′.

### A3: news outlets in PRIMARY. **APPROVE WITH CHANGES**
- Implement it as a last-pass cap (primary → reporting only; never raise a lower tier) that reuses `_WIRE_SERVICES`. It sits beside `_apply_quality_floor`, after `_high_confidence_override`.
- Add `abcnews\.com`. The list has only `abcnews.go.com`, and #6's row is `abcnews.com/Politics/...`.
- **It does not reach #11.** `bmj.com` is in `_ACADEMIC_PATTERNS` (`:276`), and the override forces it to primary/academic (`llm+override`). A BMJ news-versus-research rule needs its own path-level design. The design's own risk note ("pure news outlets only") already excludes it. Say so, and stop counting #11 as an A3 case.
- Replayed: 2 rows change (#6 Guardian, ABC), both `context`. **0 state changes.**
- Bench: `bbc.co.uk` and Guardian URLs sit in corpus goldens. Run the bench, because any primary-tier wire item there re-keys mapping.

### A4: shell detection. **REWORK → replace with an aggregator cap, or drop it**
- All three named shells (oireachtas #3, Bank of Ireland #10, EFFIS #17) are **unmapped**. A2′ already clears them. A word-count shell rule clears **no additional record**, and it is the fragile kind of rule (thresholds, navigation tokens).
- The actual residual is **aggregators**. Statista is mapped on #12, and tradingeconomics and statista appear on #3.
- An explicit cap (statista, tradingeconomics → reporting) clears **#12**. But it **flips #12 e2 supported → unresolved**: Statista was its only support, and weight 3 → 2 falls below floor 3. The grader did not fault e2. This is honest (the record NOAA itself is absent), but the founder must accept it.
- Both domains are in the TRU-C1A0-0001 and 0005 url ledgers. 0005 carries the tolerance-0 `temporal_scoped_refs` pin. Bench required.

### A5: campaign NGOs. **APPROVE (no rule)**
Agreed. #16's WWF row is an H2 mapping fault, so it belongs to tier 4.

**H4 expected gain:** design as written **2/11** (#4, #6); revised **7/11** (#3, #4, #6, #8, #10, #12, #13). Not reachable in tier 2: #5 (commercial tracker), #11 (BMJ), #16 (WWF), #17 (a mapped off-topic Copernicus page).

---

## Build B: the claimant's own piece (S7, "7 records")

### Facts checked
- **S7 is 6 records, not 7.** #15's S7 is a type mislabel: TTE's Substack investigation is pinned to `opinion` by `blog_platform_floor` (`evidence_classifier.py:659`). That is the known "rigour has no channel" fault. B does not touch it.
- The six own-piece rows are:
  - #1 theconversation → supports e1
  - #3 irishtimes column → supports e1
  - #7 gelliottmorris → supports e3
  - #8 irishtimes → supports e1
  - #9 youcanknowthings → supports e1 to e4
  - #11 hsj → supports e2
- Text submissions carry `sourceUrl: null` (payload #1). Confirmed.
- `_source_exclusion` (`retrieve.py:138`) is **not** a receipted exclusion. `"skip"` is a bare `continue` at `retrieve.py:2217` and `:2288`, with no ledger entry. It also runs only on the web-search merge paths, so adapter items and coverage-recovery items (`runner.py:1968`) bypass it.
- The evidence cache key is the **claim text only** (`services/cache.py:174-181`). A retrieval-time exclusion would therefore be defeated by a cached pool built without the origin URL, for 24 hours.
- The design also contradicts itself: it says "treated exactly like a URL submission (excluded)" and then recommends "visible, labelled, weightless". `_source_exclusion` does the former.

### B1: optional "where is this claim from?" URL. **APPROVE WITH CHANGES**
- Add a **separate field** (`claim_origin_url`). Do not reuse `content.metadata.url`, which drives ingest, `claim["source_url"]` (`extract.py:671`), the article domain and the adapter caps.
- Implement "visible, labelled, weightless" as a **scope gate at mapping**, not at retrieval. Call it `claim_origin_scope`: a directional ref whose evidence is the origin page becomes `context`, with a receipt.
  - It is symmetric by construction: it scopes supports and challenges alike.
  - Add the key to `_SCOPE_RECEIPT_KEYS` (`claim_map_analyzer.py:1536`), or both merge paths drop its receipts.
  - Do not displace temporal from first place (a test-pinned invariant). The gate never arms on the bench corpus, which has no origin URLs, so any slot after temporal is bench-neutral.
  - A mapping-stage gate is immune to the evidence cache.
- The page match must use C1's canonical key. `_same_page` (`retrieve.py:123`) would miss bbc.co.uk ↔ bbc.com and AMP forms.
- **Attribution claims:** when the claim is "X said Y" and the origin page *is* X's own document (an inquiry report, a central-bank bulletin), weightless is wrong for the attribution element. Label the field "the article where you read this claim". Record in the design that an origin page matching the claim's `claimant` is exempt on the attribution element.
- **Replayed with the six origin rows made context: 0 state changes.** #3 e1 moves from unresolved to contextual (it had 1 commentary support, now 0). But margins are thin: #1 e1, #9 e2 to e4 and #11 e2 all land **exactly on floor 3**. If this ships together with a YouTube floor or other demotions, #1 e1 flips. Replay them together.

### B2: widen restatement matching. Agree: rejected.

### B3: outreach path. **APPROVE WITH CHANGES: pass the claim's ORIGIN, never "the recipient's piece"**
- On #13 the recipient's piece (Carbon Brief) **is the rebuttal**, and the grader passed S7 because it is filed as a challenge. On #15 the recipient (TTE) is the rebutter too.
- The design's wording, "the recipient's piece URL is known … pass it as B1's field", would neutralise the rebuttal on exactly these records. That is the sycophancy failure invariant #7 forbids.
- The send sheet must record the claim's origin separately from the recipient's own piece.

**Real-user caveat:** B helps a real user only if they fill the field. Log the fill rate. On outreach it clears S7 on **6/6**.

---

## Build C: one article counts once (S4, 10 records)

### Facts checked
- **There is no single "global URL tracker".** URL dedup is a raw-string `in` test at six sites:
  - `retrieve.py:2198/2223`: search merge
  - `retrieve.py:2292`: freshness fallback
  - `retrieve.py:1008/1160`: adapter pool
  - `retrieve.py:1489`: adapter pool
  - `runner.py:1968`: coverage recovery
  - `runner.py:2532`: re-search
- #14's duplicate came in through recovery (`ev-rec-e3_4_a485cfc3` is the bbc.com twin of `ev-76886d34b83b`, bbc.co.uk). A key applied only "before the tracker" at the search merge would have missed it.
- A content deduplicator already runs: `EvidenceDeduplicator` at `retrieve.py:2664`, exact hash plus 95% similarity, **with** ledger receipts (`filter_stage="dedup"`, `:2670-2676`). It compares search snippets, which differ per page. That is the natural home for the canonical key and its receipts.

### C1: canonical URL key. **APPROVE WITH CHANGES**
- Build one `canonical_url_key()` in `app/utils/`, used at all six sites and by `_same_page`.
- Use it for **equality only; never rewrite the stored URL.** bbc.co.uk URLs sit in four corpus goldens' `url_ledger_flat` Jaccard sets (018F, 93DD, A3E8, 0005). Rewriting them would drop the Jaccard scores.
- Keep the first-seen form, and write the dropped URL as a `filter_stage` receipt.
- For academic items, key on DOI, PMID or PMC through the existing `study_identifier` (the same-study gate's identity) instead of a `/doi/epdf/` special case.
- **As designed** (alias hosts, epdf, `-N` slug), S4 clears on **#9 and #14 only**. #8 collapses the Galway `-1` twin, but its Threads and publicnow reposts remain. RocketNews collapses 5 → 1 on #13 (the stems match once the `/2026/07/` and `/2026/08/` directories are ignored), but Carbon Brief remains beside it.
- **Efficiency:** keying before fetch frees fetch slots. RocketNews alone took 5 of the 40 slots and 5 distil calls.

### C2: echo misses. **REWORK: the trace is done here; design from it**
Root causes, from the code and the payloads:
1. **The echo can only have a PRIMARY original.** `_detect_derivation_chains` (`utils/corroboration.py:242`) skips any item whose `tier != "primary"`. Carbon Brief (#13), the Guardian (#1), Bloomberg (#6) and thejournal (#8) are all `reporting`, so no chain exists and `_echo_fires` (`claim_map_analyzer.py:3062`) has nothing to match.
2. **It compares distilled text.** `find_corroborating_sources` compares the first 500 characters of `text`/`snippet`, and these are per-item LLM distillations. Measured similarity:

   | Pair | Text similarity | Fact overlap |
   |---|---|---|
   | RocketNews vs Carbon Brief (#13) | 0.03–0.11 | 0.0 |
   | AFP pair (#17) | 0.42 on snippets, 0.26 full | 0.25 |

   Copies of one article look independent.
3. **Same-domain copies are never compared.** `_get_ownership_group` defaults to the domain, and same-group pairs are skipped. RocketNews ×5, politicspa ×2, Galway ×2 and BBC ×2 are therefore invisible.
4. **The original must be counted on the same element and the same side.** On #13, e2 holds three RocketNews copies and no Carbon Brief, so even a working chain leaves all three directional.
5. **The same detector gives a false echo.** #12: nature.org and earthspace.nyc were scoped as echoes of the Gondwana paper on a single shared number, **"420", which is the claim's own figure** (fact Jaccard 0.25 and 0.5). That caused #12's **H1 hard fail** (supported → disputed via `close_split`). Fixing it is worth more than most of tier 2: it is a hard check.

**Revised C2 design, for re-review:**
- A **copy key** is the union of three signals:
  - C1's canonical URL;
  - a same-host slug stem;
  - normalised-title equality, or prefix equality of at least 6 words when one title is SERP-truncated with "…", after stripping the " - Site" suffix and ignoring shell titles ("Reddit", "September - University of Galway", tag pages).
- Titles exist before fetch, so apply the key at the search merge and at recovery: **collapse, with a receipt**.
- Choose the survivor deterministically. Prefer the domain the title suffix names (the Carbon Brief title versus "- RocketNews"), then the earliest `published_date`, then claim-lane rank. Keeping the reprint and dropping the original would be a quality loss.
- Separately, exclude from fact overlap any figure that appears in the claim or element text, and require at least 2 shared facts. This closes the #12 false echo.
- **Not mechanically reachable. Accept them and say so:**
  - AFP #17: the courthousenews copy converts units and changes the title.
  - The X teaser #1: an editor's post is a separate utterance.
  - Threads and publicnow reposts (#8), and truthout, biggo and independent re-reporting Bloomberg (#6): these are true echo, and they need a non-primary original. Leave that to a later change to the echo rule, not tier 2.
- **Expected S4 gain with C1 + the copy key:** #7 (politicspa titles identical), #9, #14 and #19 (three repository pairs by title prefix) clear fully; #13 mostly (sigmaearth and Reddit remain); #6 loses the bgov pair (same slug) but keeps its echoes. **4/10 full.** #12 H1 also clears through the fact-overlap fix.
- Direction: the rule is symmetric by construction. In #13 it removes challenge weight.

---

## Build D: filler elements (S1, 5 records). **REWORK; build after tier 4**

### Facts checked
- **The named hook is wrong.** `_repair_questions` (`pipeline/opinion_symmetry.py:289`) belongs to the **grounds** (normative) path. All 19 records are `empirical` or `causal_interpretive`, and none carries grounds metadata. The factual path's repair call is `_repair_lost_direction` (`claim_map_analyzer.py:2351`), which already handles one fail-safe 1→1 repair per claim. Any repair for D belongs there.
- **Rule (b)** ("the claim has figures, this element has none, a sibling has them") fires on **8 elements** across the 19. Only 3 are true filler: #9 e1, #11 e1, #15 e2. It also flags:
  - #14 e3, the contested historic comparison;
  - #11 e2, the recommendation itself;
  - #10 e2, #15 e1 and #9 e4, all real conjuncts.

  That is 3/8 precision. It would "repair" or drop the claim's crux.
- **Rule (a)** (restatement by overlap) as token Jaccard ≥ 0.5 fires on **22 elements**, including legitimate parallel conjuncts (Delo/Harborne, the CMS figures). Heatwave e1 ↔ e3 scores 0.50, the same as Delo ↔ Harborne. It is not separable lexically.
- "Order contested elements first" cannot be done at decomposition, because states do not exist yet. It is a **render-only** change.
- Element ids feed `canonical_element_id` (`core/manifest_signer.py:58`). Rewriting or dropping elements changes signed ids on new checks, which is acceptable but should be noted. Every decomposition change re-keys every cassette.

### Changes required
- Replace (a) and (b) with narrow detectors, each routed through the **direction-repair call**:
  1. **Figure-stripped quantity:** an element that names the claim's measured quantity ("the number of people queuing") without the figure the claim attaches to it. Repair 1→1 ("fell by 29%"). This is TTE.
  2. **Causal duplicate:** two elements that both pass `_is_causal_link` with the same cause and effect tokens. Drop the less specific one. This is the heatwaves e3.
  3. A generic-predicate premise ("made a statement or recommendation regarding", "directly compared") fires only with the NF-11 caveat, because the lexicon is an open set. Measure its firing rate on the 19 and on the corpus before building.
- Keep true premises (Sweden), per the founder recommendation. Note that S1 then stays failed on #19 under the current checklist. Either amend the checklist or accept it.
- Worth it: at most 3–4 of 19 records, a soft check, and a full cassette re-key plus control arm. **It should come last, after the tier-4 mapping work.**

---

## Cross-cutting invariant risks

1. **The mechanisms are symmetric, but their effect on states is not.** `_derive_element_state_with_authority` (`claim_map_analyzer.py:1132-1162`) applies the weight floor to `supported` only. A single commentary challenge still yields `disputed` (`all_challenges`). Every tier-2 rule removes weight (a cap, a context gate, a collapse), so it can move a supported element to unresolved but can never move a challenged one. This is not a sycophancy hazard, but it tilts sceptical. The offline replay must report state changes **by direction**, and the founder should know the net is one-way. A challenge floor is out of scope, but it should be named.
2. **Cassette re-keying:**
   - A tier change alters `[Tier: …]` in the mapping prompt.
   - A copy collapse changes the item set.
   - D changes decomposition.

   Only A1′, A2′ (frontend) and the B gate (it never arms on the corpus) are bench-neutral. Run the bench, with a control arm, for A3, the aggregator cap and C.
3. **Receipts (invariant #5):**
   - C1 and C2 must write `filter_stage` ledger receipts, the way `EvidenceDeduplicator` does.
   - B must not reuse the receipt-less `"skip"`.
   - A2′ must keep items visible and counted.
4. **Signed manifest:** A2′ is display-only, so there is no manifest effect. A, B and C change what is signed on **new** checks only. Stored records are unaffected.
5. **Tolerance-0 pins:** no rule here touches temporal, recital or interested-party receipts on 0005 or 018F. But 0005's pool contains statista and tradingeconomics, so the aggregator cap can re-key its mapping. Confirm `temporal_scoped_refs` holds.

## Missing options the design should add
- **A2′ at render for all unmapped items.** This is the single cheapest large H4 gain.
- **Title and slug copy key before fetch.** It closes most of S4 and saves fetch slots (efficiency).
- **The fact-overlap false-echo fix.** It clears a hard check on #12. Tier 2 does not list it.
- A BMJ news-path rule and a commercial-tracker rule (#5, #11). Note them as open, not claimed.

## Verdicts

| Build | Verdict | One-line change |
|---|---|---|
| A1 | APPROVE WITH CHANGES | Add `threads.com`, `linkedin`, `bsky` to the existing `_SOCIAL_MEDIA` floor; do not floor YouTube |
| A2 | APPROVE WITH CHANGES | Render-level, all unmapped items, label "not mapped", not "not related" |
| A3 | APPROVE WITH CHANGES | Primary → reporting cap from `_WIRE_SERVICES` plus `abcnews.com`; does not fix #11 |
| A4 | REWORK | Drop shell detection (0 extra clears); aggregator cap instead, founder accepts #12 e2 → unresolved |
| A5 | APPROVE | No rule |
| B1 | APPROVE WITH CHANGES | Separate field; symmetric mapping-stage gate in `_SCOPE_RECEIPT_KEYS`; not `_source_exclusion` |
| B2 | APPROVE (rejection) | — |
| B3 | APPROVE WITH CHANGES | Pass the claim's ORIGIN, never the recipient's piece (#13, #15 are rebuttals) |
| C1 | APPROVE WITH CHANGES | One key at all six sites; equality only, never rewrite URLs; DOI through `study_identifier` |
| C2 | REWORK | Use the trace above: copy key before fetch plus the fact-overlap fix; return for review |
| D | REWORK | Wrong hook; (a)/(b) over-fire; narrow detectors via `_repair_lost_direction`; build last |

**Overall: APPROVE WITH CHANGES.**

## Ranked build order
1. **A1′ + A2′.** A regex line and a frontend grouping. H4 on 5 records (#3, #4, #8, #10, #13), zero state changes, no bench.
2. **A3′.** The wire cap plus `abcnews.com`. Clears #6 (with A2′). Bench.
3. **C1 + C2 copy key + fact-overlap fix, as one build.** S4 on 4 records plus #13 mostly, H1 on #12, fewer wasted fetch slots. Bench with a control arm.
4. **B1 + B3** as a mapping gate plus the field. S7 on 6 outreach records, 0 state changes, but replay it together with 1–3 because of the floor-3 margins.
5. **Aggregator cap.** Only after the founder accepts #12 e2 → unresolved.
6. **D (reworked).** After tier 4, with its own firing-rate measurement.
