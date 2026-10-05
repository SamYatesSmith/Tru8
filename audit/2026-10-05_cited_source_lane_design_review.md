# Review: cited-source follow-up lane, design rev 1 (2026-10-05)

**Reviewer:** independent; did not write the design. No code changed.
**Reviewed:** `audit/2026-10-05_cited_source_lane_design.md` (rev 1), the probe artefacts in `audit/cited_source/`, the 30 Sep grades in `audit/a_minus/2026-09-30_rerun/`, and the code named below.

## Verdict: APPROVE WITH CHANGES (rev 2 required and re-reviewed before any paid step)

The idea is sound and is not a Phase D re-run. Copies name their source; rebuttals do not. The grades confirm the targets: #6, #15 and #17 each name the original the lane would look for (`6_02c8c252.md:14`, `15_018f9a18.md:15`, `17_802cebc9.md:14`).

Rev 1 is not buildable as written. Its inputs do not exist at its placement. Its fetch path would discard its own query. It would import more copies while the echo gate is off. The gap note has no presence test and nowhere to render. The eval reads text that production would not read. Six HIGH findings follow.

---

## HIGH

### H1. The lane's inputs do not exist where it runs
§2 places the lane before provenance capture and classification. §3 then reads three things those later stages produce:
- "non-primary pool items" and "a pooled PRIMARY item's host" need `tier`. Tier is set by `classify_batch` at `runner.py:2186`, after the lane.
- "`text_provenance.original_snippet` and passages" are written by `capture_text_provenance` at `runner.py:2133`, after the lane.
- The free probe filtered on `tier == "primary"` from finished pools (`extract_probe.py`, the `if it.get("tier") == "primary": continue` line). Production at this placement has no tier.

**Required:** pick one and restate §2–§3.
- (a) Preferred: move `copy_page_opening` and `capture_text_provenance` (runner.py:2124–2140) above the lane. Capture is idempotent (`text_provenance.py:91`), so the lane's new items are captured later in the same loop. The lane then reads stored passages and `original_snippet`. Drop every tier test. Replace "already present as PRIMARY" with a host/title identity test (see H4).
- (b) Or run the lane after classification, as `re_search.py` does. New items then need their own classify, distil and originator-review pass. That is a second-class path, which §2 says it avoids.

### H2. `retrieve_evidence_for_claims` would throw the lane's query away
§4 says the lane uses "the normal `EvidenceRetriever` fetch path" and cites `re_search.py:80-94` as precedent. The code does not support that.
- With `ENABLE_QUERY_PLANNING` on, `retrieve_evidence_for_claims` always calls the LLM planner and overwrites `claims[i]["query_plan"]` (`retrieve.py:769-910`, the write at `:910`). A supplied plan survives only if planning returns nothing. `re_search.py:80-94` is an example of this overwrite, not a working precedent.
- It also fires the government API adapters (`retrieve.py:1909`) under a 45 s per-claim wait (`:1920`).
- With fewer than 2 items it runs `_ensure_minimum_evidence` (`retrieve.py:691`, `:1045`), which is another planner call and more searches. A 3-result lane will usually trigger it.
- "Top 3 results per query" is not a parameter of that path. Ranking, filtering and `max_sources_per_claim` decide.

**Required:** specify a narrow helper. Use `SearchService.search_for_evidence` for the one query, as post-filter recovery already does (`runner.py:2032`). Then fetch the chosen URLs through the `EvidenceService` extract path with the runtime blocklist, `_already_pooled`, copy collapse against the existing pool (`retrieve._collapse_copy_candidates`), PDF guards and the lane's own deadline. Add a test that the query string issued equals the lane's built query.

### H3. The lane imports more copies and can meet the support floor on its own
The probe's own top results are mostly derivatives:
- #6: yahoo, democracynow, msn, fortune at ranks 2–5.
- #15, second query: BBC, LinkedIn, pharmaphorum, reddit. The release is not in the top 5.

Rev 1 keeps the top 3 per query and up to 4 per claim. Most of these would be further relays of the very original the pool already lacks.
- The echo gate is OFF in production (`config.py:764`, `ENABLE_ECHO_SCOPE_GATE=False`). Every added copy counts.
- S4 (echo/duplicates) is already the rising A− bucket (7 → 11 on 30 Sep).
- Arithmetic: `_STATE_TIER_WEIGHTS = {primary 3, reporting 2, commentary 1}` (`claim_map_analyzer.py:972`) against `FACTUAL_MIN_WEIGHTED_SUPPORT = 3` (`config.py:738`). Two reporting copies (weight 4), or three commentary items (weight 3), let the lane carry an element to `supported` alone. Phase D §2 set the rule: a lane must not be able to meet the floor by itself.
- `_already_pooled` only catches URL twins (`retrieve.py:171-185`), not syndicated reprints with new URLs.

**Required:**
- Keep a result only if it identifies as the cited body: the host label starts with a distinctive name token (the label-start rule in `interested_party.py:256-298`), or the title suffix names the host (`url_identity.suffix_names_host`), or the path or title contains the name or its acronym.
- Drop every other result with a URL-ledger receipt `stage=cited_source reason=not_cited_body`.
- Keep at most 1 item per name and at most 2 per claim.
- Run copy collapse of the new items against the existing pool.

### H4. The gap note cannot be computed as specified, and nothing would show it
**Presence test.** §6 says "no item from the cited body reached the pool (by host match or `cited_source` metadata)".
- There is no name→host map. "EFFIS" resolves to `forest-fire.emergency.copernicus.eu` and `joint-research-centre.ec.europa.eu`. "NHS England" resolves to `england.nhs.uk`. "preliminary official results" (#4) is not a body at all.
- `cited_source` metadata is set on every lane item, including the copies in H3. A yahoo reprint found by the Bloomberg query would mark Bloomberg "present" and suppress the note.
- #17 shows the opposite failure. A JRC page was already in the pool, but its retained text was a fire-danger legend with no burned-area figure, and it was unmapped (`17_802cebc9.md:14`). A host test would call EFFIS "already present". The lane would then skip the search and suppress the note on the very record it was built for.

**Surface.** §6 says the claim "gets a plain gap entry in the Seeker data". No such data exists.
- Seeker gaps are derived in the browser from element states (`SeekerView.tsx:104-122`). There is no backend gap list.
- `claim_map.metadata` reaches the API camelCased (`response_builder.py:70`), but no component reads a cited-source field.
- When every element is covered, the Seeker shows "Evidence mapped… Each element has supporting evidence mapped" (`SeekerView.tsx:213`). A "not retrieved" note beside that text would contradict it.
- Graders read the Gaps lens on `/r/` and quote its counter ("Gaps 0"). S9 credit needs the note there.

**Staleness.** Coverage recovery (Stage 5.1) and Strengthen can both add the original after the lane has run. A note computed at lane time would then say "not retrieved" about a source the page shows.

**Required:**
- Define presence as: a shown (not excluded) item, after mapping, whose host/title/path identifies the body by the H3 rule, and whose retained text contains the cue's figure or key term. Otherwise the note stands.
- Compute the note at the end of the run, after coverage recovery. Recompute it in `re_search.research_claim`.
- Specify the web component (dashboard and `/r/` from one component), its place in the Gaps lens, whether it counts in the Gaps counter, the wording of the "Evidence mapped" state when a note is present, the shared type, and tests on both hosts.
- Word the note from the verbatim cue, not the model's label: "Sources here attribute this to {name} ("{cue}"); that source is not in this record."

### H5. The eval measures the wrong input, and its "held-out" set is not held out
This is the echo H1 error again.
- Step 1 runs on stored production pools. Their text is `text_provenance` passages: lexical windows chosen by element terms (`text_provenance.py:29-83`), at most 8 × 900 chars. Their items carry post-classify tier.
- §3 says production reads "windows around attribution verbs" with no tier. Stored pools do not keep the full text, so those windows cannot be rebuilt from them. A precision figure from Step 1 would describe an input production never sees.
- The 41 pools were all read for `extract_probe.py` while the design was shaped, and the prompt was written knowing their names (Jim Mackey, Siegmund). Reporting the six separately does not make the other 35 held-out.

**Required:**
- Make the production input exactly what is stored: `original_snippet` plus the captured passages (this follows from H1 option a). Then Step 1 reads what production reads.
- Freeze the prompt and guards before Step 1.
- Measure precision on pools not read during design: production checks created after 2026-10-05, or bench corpus claims outside the 41. Report the 41 only as in-sample.

### H6. Following "X announced" imports X's self-report, and the gates do not reliably cover it (invariant #7)
- `kind = announcement` lands, by design, on the announcing body's own page. Its own figures about its own programme are an interested account.
- The interested-party gate arms only on the claim's named subjects, PERSON/ORG from `key_entities` (`interested_party.py:1-45`, `256-298`; `runner.attach_claim_subjects`).
- When the body is not a named subject (for example "AI triage cut phone queues by 29%"), its release enters as primary weight 3 and meets the floor alone.
- When the body is a subject, the gate may scope the original to context unless `released_subjects` finds a measurement or saying verb in the claim (`interested_party.py:369-420`). Whether the lane helps or is cancelled then depends on claim wording.
- #15 is the live example. The 28 Sep review names the missing sources as "NHS England release + OSR ruling on the 29%" (`2026-09-28_retrieval_h3_review.md:14`). The self-report is the half copies cite. The regulator's ruling is the half they do not, so the lane would fetch only the first.
- §7's "names are taken from any side" is true but weak. Pools are mostly copies of the claim's own story, so most names followed are the claim's own source.

**Required:**
- For `kind = announcement`, pass the cited name to the interested-party check as an ORG subject for that lane item. Leave the existing release rules unchanged.
- The eval reports, flag-on against flag-off, every element whose state changed, and the direction and tier of every lane item that got a directional ref.
- State in §7 that the lane mostly retrieves the claim's own source, and that this is accepted only because the gates above apply to it.

---

## MEDIUM

### M1. "5 of 5" overstates the probe
- #4 was found only by the German query, which §7 puts out of scope.
- #15's second query did not return the release in its top 5.
- #1's Harborne piece was at rank 9 on the first query, outside the design's top 3 (the second query found it at rank 2).
- No probe query had the §4 shape (a quoted `"{name}"` plus 12 claim content words). The probe queries were unquoted and hand-trimmed.

On the specified English queries, the honest figure is 4 of 5 by hand, and untested for the built query.
**Required:** restate §1. Step 2 must run the exact output of the §4 query builder.

### M2. Latency and cost are understated, and the binding limit is 180 s, not 300 s
- The stage is serial: the model call (≤25 s; the same model measured 3.5–15.8 s on the originator review), then search and fetch (≤30 s), then a relevance mini-batch (another LLM call).
- New items then add work to classify, distil, originator review, relationship review and mapping.
- The worst case is about 60 s or more. Rev 1 says 5–10 s.
- `/agent` full runs under `asyncio.wait_for(..., timeout=config.max_wall_time_seconds)` = 180 s (`runner.py:57`, `agent.py:933`). The hosted MCP stream dies at about 140 s.

**Required:**
- Add `stage_timings["cited_source"]`.
- Start the model call alongside post-filter recovery, since the two are independent.
- The eval reports p50/p95 for the stage and for total wall time, flag-on against flag-off.
- Cost every downstream call, not only the name call and Serper.

### M3. The relevance scorer will not drop "a different Bloomberg piece"
- `score_evidence_batch` excludes only score 1 (`relevance_scorer.py:748`). A same-topic but wrong article scores 2 or more and stays.
- The `raw_evidence_data` receipts for scorer exclusions are written by the runner (`runner.py:1932-1950`), not by the scorer. A mini-batch must write them too.

**Required:** rely on the H3 identity filter rather than the scorer, and write the scorer-exclusion receipts.

### M4. The quick-tier skip needs a declared limitation
QUICK_CONFIG reductions must map to a slug in `tier_limitations._FIELD_SLUGS`, or the drift guard fails and agents are not told.
**Required:** add `enable_cited_source_lane` to `PipelineConfig`, set it False in `QUICK_CONFIG`, and add a slug (e.g. `no_cited_source_lane`).

### M5. Truncation and allocation are unspecified (invariant #2)
- One call covers every claim × 20 items × 600 chars. With 12 claims that is about 144k chars.
- "≤ 6 per check" with up to 12 claims must pick winners.

**Required:**
- Use round-robin, never slicing, for prompt items across claims and for query allocation.
- Cap the prompt size.
- A malformed answer for one claim must not drop the others.

### M6. Shipping the gap-note flag first contradicts its own condition
§6 needs "the lane ran". §9 lets the note ship with the lane off.
**Required:** define the flag-off form. Extraction runs, there is no search, and the note says "not in this record", not "searched and not found".

### M7. Step 2 and Step 4 measure presence, not usefulness, and Step 4 has no control
- Grade #17 shows a JRC page that was present but useless.
- **Required for Step 2:** a hit is "the cited body's page is kept, and its retained passages contain the claim's figure or finding". URL rank alone is not a hit.
- **Required for Step 4:** run each of the six records twice, flag-off and flag-on, on the same day (the bench-noise rule). Grade H2 and S4 as well as H3, because H3 and H6 are regression risks.

---

## LOW

- **L1. The cache bump is not needed.** The evidence cache stores raw retrieval output before scoring (`workers/pipeline.py:296-320`). The lane runs on cache hits too. The bump is harmless, but §7 gives the wrong reason. Confirm that `_full_text` survives the Redis JSON round trip, or cache-hit runs will capture no passages.
- **L2. Evidence ids.** Use a lane prefix (`ev-cs-{pos}_{n}`), as post-filter recovery does (`ev-rpf-`), so receipts and logs can tell lane items apart.
- **L3. Echo work.** Lane items get `_elc.copy_page_opening` because they are added before `runner.py:2128`, which is good. The accepted cues ("according to a new Bloomberg analysis") are direct relay evidence. Store the item→name links so echo link confirmation can reuse them, not re-derive them.
- **L4. Guards.** Reject a name equal to the citing item's own outlet or host. Cap name and cue length. Cue on `/r/` is fine as verbatim source text; keep it short.
- **L5. Out of scope.** #2 (nothing cited) and #4 (needs a native-language query) stay out of scope. Say plainly that the lane cannot clear H3 on either; at best #4 earns S9 through the note.

---

## Checks that pass
- The runner line references are accurate: scoring 1900–1970, post-filter recovery 1972–2125, provenance and classification from 2121.
- The frozen-replay skip follows the existing `_is_frozen_evidence_replay` pattern.
- Placement before 2128 does give new items the same opening copy, echo opening, provenance, originator review, classification, distillation, scope gates and receipts. The "no second-class path" claim holds once H1 is resolved.
- The cue-verbatim and name-in-cue guards do stop invented strings. They do not stop wrong roles (quoted people, outlets), which only the eval can measure.
- `claim_map.metadata` written before mapping survives, because mapping mutates in place (the `attach_claim_jurisdiction` precedent, `runner.py:164-186`), and it reaches the API (`response_builder.py:70`).
- Skipping re-search is right. Strengthen supplies its own element lane (`retrieve.py:381-391`).
- Not a Phase D repeat: the lane follows a name the pool already holds, with no counter-framing.
- The flags default off, and `FLAGS.md` is regenerated in the same commit.

---

## Answers to §10

1. **Placement.** Right in principle. The lane needs the relevance-surviving pool text, so do not fold it into the first retrieval. The second round trip is acceptable if it is a narrow search-and-fetch (H2), not `retrieve_evidence_for_claims`. Overlap the model call with post-filter recovery to save time (M2).
2. **Model or mechanical names.** Keep the model call. Mechanical patterns missed EFFIS and returned quoted people. The guards stop invented names. The note should quote the verbatim cue, so what the reader sees is source text, not a model label. If the call fails, there is no note and a receipt (fail closed).
3. **New sycophancy paths.** Yes, three:
   - copies imported by the top-3 fetch while the echo gate is off (H3);
   - reporting or commentary results meeting the support floor alone (H3);
   - self-announcements by bodies that are not named subjects, which the interested-party gate never sees (H6).
   The recital gate does not help here. It scopes refs whose reasoning or text rests on a subject saying something, not the subject's own release.
4. **Targets and caps.**
   - **85% name precision** is a fair bar, but only on held-out pools (H5), with at least 40 accepted names, and with a reported 95% interval.
   - **60% retrieval** should count only "kept, and the retained text carries the finding" (M7), on at least 20 names.
   - **Caps:** 1 query per name; ≤ 6 queries per check, allocated round-robin; ≤ 1 kept item per name; ≤ 2 per claim, identity-filtered (H3).

---

## Re-review of rev 2 (2026-10-05)

**Reviewed:** §11 of the design, against the code named below. No code changed.

### Verdict: APPROVE WITH CHANGES

Rev 2 fixes the structure: placement, a narrow fetch, a frozen eval on stored text, and quick-tier, timing and receipts. Three of the new mechanisms are wrong as written, and each one reopens a rev 1 HIGH: the identity filter (H3), the presence test (H4) and copy collapse (H2). The fixes are short spec edits. Build A may start once N1–N3 are amended in the design. Only those paragraphs need re-review, and no paid step runs before then.

### Findings from rev 1

| # | Status | Evidence |
|---|---|---|
| H1 | Resolved | Capture returns early without `_full_text` (`text_provenance.py:93-95`). Post-filter recovery items are search snippets with no `_full_text` (`runner.py:2053`), so moving capture above them is safe and changes nothing for them. See N8 for the exact position. |
| H2 | Partly | The planner, adapters and top-up are gone. But the copy-collapse step is wrong (N3), and the fetch helper needs the details in N5. |
| H3 | Partly | The caps are right. Rules (b) and (c) of the identity filter let copies back in (N1). |
| H4 | Partly | Presence now needs a figure or key term. But the cue always contains the name, so any page from the body passes (N2). Build B's surface is specified, but not the Gaps counter's code (N6). |
| H5 | Resolved | Input is stored text only. Prompt frozen. Held-out local pools. There is a stop rule below 40 names. Dedup note in N7. |
| H6 | Partly | A per-item subject is feasible: the gate's `fires` lambda already receives the item (`claim_map_analyzer.py:3191`). The mechanics in N4 are missing. |
| M1 | Resolved | The query is unquoted, in the probe's shape. Step 2 runs the builder's exact output. The ceiling is stated (#1, #6, #15, #17). |
| M2 | Resolved | Stage timing, overlap with recovery, p50/p95 against 180 s, and every downstream call costed. |
| M3 | Resolved | The scorer is skipped and identity is the guard. Lane items then have no `llm_relevance_score`. Nothing downstream ranks on it, and recovery items are the same today. |
| M4 | Resolved | `enable_cited_source_lane` with slug `no_cited_source_lane`. |
| M5 | Resolved | Round-robin input and allocation, a 40k cap, and per-claim parse failure. |
| M6 | Resolved | The flag-off form is defined, with "not in this record" wording. |
| M7 | Resolved | Hit = kept and the passages carry the finding. Same-day off/on pairs. H2 and S4 graded. |
| L1 | Resolved | `cache.set` stores `json.dumps(data, default=str)` (`cache.py:85`), so the `_full_text` key survives. Pin it with a test. |
| L2 | Resolved | `ev-cs-{pos}_{n}`. |
| L3 | Resolved | `citing_ids` stored. |
| L4 | Resolved | Self-outlet guard and length caps. |
| L5 | Resolved | #2 and #4 are stated out of reach. |

### New findings

**N1 (HIGH). Identity rules (b) and (c) admit copies.**
- `url_identity.suffix_names_host(suffix, host)` asks whether a title suffix names *the page's own host* (`" - Fortune"` on fortune.com). It never looks at the cited name. Rule (b) as written passes almost every publisher page, including the yahoo, msn and fortune relays from the #6 probe.
- Rule (c) passes a copy whose slug or title names its source, e.g. `fortune.com/…/bloomberg-analysis-trump-stock-trades/`. Copies routinely do this.
- Rule (a) also needs care. `distinctive_tokens` does not lower-case (only `claim_subjects` does), so "NHS England" must be lower-cased first. It drops tokens under 4 characters and stop-listed ones (`bank`, `data`, `council`…), so ONS, WHO, IMF and CDC never match by host.

Required:
- Identity must rest on the host. Keep a result when either (a) the host's label-start matches a lower-cased distinctive token of the name, or (a′) an acronym the cue gives equals the host's registrable label (`ons.gov.uk`, `who.int`).
- Delete (b) as written. Allow a title suffix only when the suffix contains the name and `suffix_names_host` is true for that page.
- A path or title match alone never qualifies.
- Add fixture tests with the #6 relays (yahoo, msn, fortune, democracynow) as must-drop, and bloomberg.com, england.nhs.uk and the EFFIS host as must-keep.

**N2 (HIGH). "Already present" is satisfied by the name itself.**
- §11.4 and §11.8 count the body as present when a page passes identity and its stored text holds "a figure or key term from the cue".
- The guard requires the name to be inside the cue. Any page of the body names itself, so it passes.
- The #17 cue ("data collected by the European Forest Fire Information System (EFFIS)") has no figure. The JRC legend page names EFFIS. So it would read as present, the search would be skipped and the note suppressed. That is the rev 1 failure H4 was raised for.
- The #6 cue ("a new Bloomberg analysis finds") would let any Bloomberg page with the word "analysis" count.

Required:
- Key terms exclude the name's tokens, the citing verbs and stop words.
- Prefer the claim's own figures (numbers in the claim text). With no figure, require ≥ 2 of the claim's content terms in one passage.
- Add a test on the #17 JRC legend text that must read as not present.

**N3 (HIGH). `_collapse_copy_candidates` cannot collapse "against the pool", and if it could, it would drop the original.**
- It takes one list and reads `url`/`title`/`published_date` by `getattr` (`retrieve.py:196-214`). Pool items are dicts, so they present empty strings.
- It has no notion of a pooled item, and it rewrites the survivor's `_element_ids`, `_copy_fallbacks` and `_copy_receipts`.
- The underlying `choose_survivor` puts a pooled item first (`url_identity.py:471`). If a pooled relay and the lane's original formed one copy group, the original would be the one dropped.

Required:
- Drop the collapse step from §11.2. URL twins are already caught by `_already_pooled`, and the identity filter guarantees the kept item is the body's own page.
- If a lane original forms a copy group with pooled relays (use `url_identity.copy_groups` with dict accessors), keep the original and record the relay ids in `cited_source.citing_ids`. Never drop the original.

**N4 (MEDIUM). Per-item subject mechanics (H6).**
- Lower-case the name before `distinctive_tokens`.
- Add the item subject only when the name is not already a claim subject. Otherwise it is never in `released` and would override a release the claim earned (`released_subjects`, `interested_party.py:369`).
- Arm on the cue as well as on the model's `kind`: arm when the cue holds a statement verb (announced, said, statement, press release, claimed). A model label alone must not decide a safety gate.
- State the consequence. An announcement original matches prong 1 on its own host, which is the same label-start rule as identity (a). So it can only ever be context. That is the conservative outcome, and the eval should expect it.

**N5 (MEDIUM). Fetch helper details.**
- `_extract_with_fallback` needs only `self.evidence_extractor`, but it labels items `source_path="query_planning"` and defaults `_freshness` to `"py"` (`retrieve.py:2683`, `:2703`). Set `_freshness="none"` on each result and overwrite `source_path` to `cited_source`.
- It returns an `EvidenceSnippet`. The dict built from it must mirror `retrieve.py:2089-2113`, including `_full_text` and `date_basis`.
- A 403 or timeout returns a search-snippet fallback with no `_full_text`. Bloomberg graphics pages are a likely case. The PDF path (`evidence.py:425-456`) also sets no `_full_text`. Both items get no passages, so they can never count as present or as a Step 2 hit. State whether such an item uses up the name's single slot (recommended: it is kept, but the next identity-passing result is also tried within the deadline), and say that the note stands.
- Apply the blocklist and `_already_pooled` before the fetch, not after it.

**N6 (MEDIUM, Build B). The Gaps counter is one shared function.**
- Every surface counts gaps with `evidenceCoverage(elements)` in `web/lib/evidence-coverage.ts`: `ClaimSummaryPanel`, `seeker/SeekerView.tsx`, `seeker/CoverageMap.tsx`, and the `seeker-honesty` test. The A− S6 parity fix depends on that.

Required:
- To "count in the Gaps counter", extend that one function, for example with a separate `citedMissing` count. Do not add a count inside SeekerView alone.
- Say whether the summary panel's "N gaps" link includes it.
- Name the component under `web/components/evidence-views/seeker/`.

**N7 (LOW). Held-out pool hygiene.**
- The local DB holds repeated runs of the same claims (bench and dev). Dedupe by normalised claim text, report distinct claims, and compute the interval by claim.
- Only checks since `text_provenance` shipped (2026-09-09) carry stored text. The echo held-out found about 87 distinct local claims with verbatim text, so ≥ 40 accepted names is not assured. The stop rule covers this.
- Freeze the attribution-verb list used to choose input items, in the same commit as the prompt.

**N8 (LOW). Capture position.**
- M2's overlap starts the name call alongside post-filter recovery, and the call reads captured text. So capture must move above post-filter recovery, not merely "before the lane".
- Say so in §11.1. It is safe (see H1).

### Answer on the caps arithmetic
- With 1 per name and 2 per claim, two identity-true originals from different names can carry an element alone: two primaries give weight 6, or two reporting originals give 4, against a floor of 3.
- That is acceptable only because both are the cited bodies' own pages, which is the point of the lane. It holds only once N1 makes identity real.
- Rev 2's sentence "two reporting copies can never enter together" is true per name, not per claim. Reword it.

---

## Re-review of rev 2.1 (2026-10-05)

**Reviewed:** §12 of the design, against `interested_party.py`, `url_identity.py`, `retrieve.py` and the hosts in `audit/cited_source/probe_results.json`. No code changed.

### Verdict for Build A: APPROVE WITH CHANGES

N1–N3 are resolved. No HIGH item remains. The changes below are small. They can be made in the build commit without another design round, but each needs a test.

### Status of N1–N8

| # | Status | Evidence |
|---|---|---|
| N1 | Resolved | The filter now uses the host only. Probe hosts give the right answers under "every token": bloomberg.com and telegraph.co.uk keep (with "daily" and "the" generic). england.nhs.uk keeps. surreysussex.icb.nhs.uk drops ("england" not a label). nhsaccelerator.com drops (also "england"). effis.emergency.copernicus.eu keeps by rule 2. forest-fire.… and joint-research-centre.… drop. yahoo, msn, fortune and democracynow drop. See R2 and R3 for what to tighten. |
| N2 | Resolved | Presence needs the claim's figure, or 2 claim terms with the name's tokens excluded. Snippet-only and PDF items never count. The #17 legend fails both tests. |
| N3 | Resolved | Copy collapse is gone from the lane. `_already_pooled` plus host identity remains. |
| N4 | Partly | "Release wins" and kind-or-cue arming are in. The verb list is wrong (R1). |
| N5 | Partly | The conversion and `_full_text` test are in. The `source_path` step is in the wrong place (R4). |
| N6 | Resolved | `evidenceCoverage` is the single counter, and the component path is named. |
| N7 | Resolved | Dedup by claim text. An underpowered result stops the step. A top-up needs the founder's approval. |
| N8 | Resolved | Capture moves above post-filter recovery. |

### Remaining items

**R1 (MEDIUM). The arming verbs would cancel the lane's own data originals.**
- §12.5 arms the interested-party check on a cue containing "published", "released", "reported" or "wrote".
- The lane item's host matches the name by rule 1, which is the same label-start test as prong 1 (`interested_party.py:274-283`). So every armed item is scoped to `context`.
- "a new Bloomberg analysis published …" would scope Bloomberg's own analysis on #6. "ONS released figures" would scope ONS's own data. `released_subjects` treats exactly these measurement verbs as a release, not as interest (`interested_party.py:369` and the `_MEASUREMENT_ACT` list). A lane name is never a claim subject, so it never gets that release.
- "Delo wrote in the Daily Telegraph" (#1) arms the Telegraph, but the interested party there is Delo, the writer, not the paper.
- This is safe in direction but makes the lane inert on its own targets. The eval would then read a mechanism failure as "no effect".

Required: arm only on self-statement verbs: said, announced, stated, claimed, "press release", "statement". Drop published, released, reported and wrote. Keep `kind ∈ {announcement, filing}`. Add tests: the #6 and #1 cues must not arm, and "NHS England announced" must arm.

**R2 (LOW). Name the token function.**
- §12.1 says "≥ 3 chars" with its own generic list. `distinctive_tokens` uses ≥ 4 chars and `_STOP_TOKENS` (`interested_party.py:221-236`).
- The two differ. "nhs" survives only at ≥ 3. "department", "federal" and "bank" are dropped only by `_STOP_TOKENS`.
- Under "every token must match", keeping "department" would make "Department for Education" fail on education.gov.uk.

Required: write a new helper. It lower-cases, keeps tokens of ≥ 3 chars, and removes the union of `_STOP_TOKENS` and the §12.1 generic list. Do not call `distinctive_tokens` directly.

**R3 (LOW, recall; safe direction). Concatenated hosts fail "every token".**
- washingtonpost.com, bankofengland.co.uk and nytimes.com each fail rule 1, because only the first token starts a label.
- These are drops, so the error is safe, but it lowers the Step 2 hit rate.

Required:
- Also accept a host when the name, compacted (lower-case alphanumerics with connectors kept), is a prefix of one label.
- Rule 2 must match the registrable label, or the first label under a shared suffix, not any label. This stops 2–3 letter acronyms matching stray subdomains.
- Report rule-1/rule-2 misses separately in Step 2.

**R4 (LOW). `source_path` is overwritten inside the call.**
- `_extract_with_fallback` sets `metadata["source_path"] = "query_planning"` itself (`retrieve.py:2703`, and `:2756` on the fallback path).
- Setting it on the search result beforehand has no effect.

Required: overwrite `source_path` on the returned snippet's metadata after the call. Setting `_freshness = "none"` beforehand is correct.

**R5 (Build B, not blocking A). A host miss makes the note false.**
- §12.1 accepts that EFFIS's page on `forest-fire.…` is not matched.
- §12.2 then counts EFFIS as missing even when that page is shown with the figure. The note would say "not in this record" beside it.

Required before Build B: an alias list per name, filled from Step 2 misses. Or suppress the note when a shown item's title names the body and its passages carry the claim figure. That test is for the note only, never for retrieval.
