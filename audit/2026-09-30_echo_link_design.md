# Echo links: find relays that the similarity test misses (design, rev 1)

**Date:** 2026-09-30. **Difficulty:** 3 (shared detector; a new link can move a badge). **Status:** design, awaiting review and founder approval. Nothing built.

## 1. Problem
A− re-measure 3 (`audit/2026-09-24_a_minus_measurement.md`, last section): **S4 (duplicates / echo) rose from 7 to 11 of 19 records.** It is the only fail on the one A− record (#19) and one of two on #8, #9 and #13. It is the cheapest route to more A− records, but the fix must be general (judged on held-out pools, not on these records).

## 2. How echo works today
- `corroboration.annotate_derivation_chains` (post-classify) writes `derivation_chain` onto a PRIMARY item when **≥2** REPORTING/COMMENTARY items "corroborate" it.
- "Corroborate" = `find_corroborating_sources`: different ownership group AND (`SequenceMatcher` ratio of the first 500 chars ≥ 0.35 **or** Jaccard of `_extract_key_facts` ≥ 0.3).
- The echo scope gate (`claim_map_analyzer._echo_fires`) re-labels a derivative's directional ref to `context` when its original is counted on the same side. It reads only those chains.

## 3. Measured misses (free, from the stored snippets)
Re-running the detector on the saved snippets reproduces production exactly (#8 linked irishnews, independent, fishingnews; #9 linked Stanford HAI, youcanknowthings), so the numbers below are what production saw.

| Record | Relay | vs original | text sim | fact Jaccard | why missed |
|---|---|---|---|---|---|
| #8 | timesofindia ("According to the University of Galway…") | universityofgalway.ie | 0.04 | 0.00 | the original has **no extracted facts at all** |
| #8 | 3dprintingindustry | universityofgalway.ie | 0.06 | 0.00 | same |
| #9 | Wisedocs ("A recent study out of Stanford found… 45%… 36%") | PMC study | 0.06 | 0.25 | Jaccard penalises the relay's extra, unrelated figures |
| #9 | JAMIA Open (quotes "up to 36%… 45%", cites the study) | PMC study | 0.03 | 0.40 | tier is PRIMARY; derivatives must be reporting/commentary |

**Root causes:**
1. **`_extract_key_facts` misses every number with a unit attached.** `\b\d+\b` cannot match "900m", "1100m", "600kg" or "80cm" (no word boundary between digit and letter), and "1,100" splits into "1" and "100". The Galway release states four figures and yields an empty set.
2. **Jaccard is the wrong measure for a relay.** A relay carries the original's figures *plus its own*. Wisedocs shares {36, 45} of PMC's {19, 36, 45, 4} but adds {23, 58, 2024, 10}, so 2/8 = 0.25.

## 4. Proposed change
A second, derivation-only link test, **added to** (never replacing) the existing corroboration links inside `annotate_derivation_chains`. Corroboration groups, the retrieve-time pass and repetition clusters are untouched.

`_relays_figures(primary, other) -> bool`, true when all hold:
- different ownership group (as today);
- `other.tier` in {reporting, commentary} (as today);
- with `_distinctive_figures(text)`: numbers **with attached units allowed** (`900m`, `600kg`, `36%`), thousands separators normalised (`1,100` → `1100`), decimals kept; **excluded**: single digits 0–9 and ordinal/list noise;
- the two share **≥ 2 distinctive figures**, and those shared figures cover **≥ 50 % of the primary's** distinctive figures (containment over the original, not Jaccard);
- years (1900–2099) may be shared but **do not count toward the minimum of 2** (they coincide across unrelated pages).

The chain rule (≥2 derivatives per primary) is kept, so the echo note and the gate keep their current contract.

**Out of scope, deliberately:**
- **Primary-tier relays (JAMIA).** Demoting a primary as a copy needs a decision about which primary is the original; two primaries sharing figures is often an official source and its regulator. Mapping or relationship review is the better owner (the JAMIA ref relays another study's result, which is a mapping-scope error).
- Wording-only relays with no shared figures (an attribution cue such as "According to <publisher>"). Measure first; see §7.

**Symmetry (invariant #7):** the gate scopes challenge-side echoes exactly as support-side; nothing here reads direction.

**Flag:** `ENABLE_ECHO_FIGURE_LINKS` (default ON only after §6 passes). Rollback = flag off.

## 5. Expected effect and risk
- **Prototype, measured on the stored snippets (free):** the Galway release now yields {80, 100, 600, 900, 1100}. New links: timesofindia, 3dprintingindustry and **siliconrepublic** (all five figures each; siliconrepublic was not flagged by the grader, so it is exactly the kind of pair §6 must label). rte and irishtimes (one shared figure) stay unlinked. PMC yields {19, 36, 45}; Wisedocs ({36, 45}) links; Stanford HAI and youcanknowthings still link; JAMIA ({36, 45}) stays unlinked because it is PRIMARY. Every old link is kept (union).
- **State movement:** the gate only fires when the original is counted on the same side, so a side never loses its original. A state can still move where the floor counts weighted refs (a support side losing reporting weight). §6 measures it rather than assumes.
- **False links, the main risk:** two outlets reporting the same official figures, where the pool's primary is a *different* body that also quotes them (e.g. a regulator restating ONS CPI). Linking the outlet to the regulator still counts the figure once, so the direction is right; the receipt names the wrong original. §6 counts these.
- Wrongly scoped *independent* confirmation (an outlet that measured the same figure itself) is rare but is the real harm. §6 labels for it.

## 6. Evaluation (free except where stated; held-out; nothing on the 19 records counts)
1. **Pools:** the 40 most recent completed production checks not in the A− 19, read-only from the production DB (`railway ssh`, one SELECT of evidence rows and claim maps; **needs founder approval** — it reads production).
2. **Links:** run old vs new `annotate_derivation_chains` on each pool; list every NEW (primary, derivative) pair.
3. **Blind labels:** a fresh agent, shown only the two snippets and URLs, labels each new pair `relay` (B repeats A's content) / `independent` (B has its own basis for the figures) / `unclear`. **Pass:** ≥ 90 % of labelled new pairs are `relay`, and ≤ 1 `independent` pair per 20.
4. **State replay:** re-run the scope-gate pass on the stored claim maps with and without the new chains (free, no model). Report every element state change; each must be read and judged right before switching on.
5. **Bench:** `replay_bench.py --all` flag on vs off. Expect only echo-receipt / support-count changes; anything else is investigated.
6. **Unit tests:** #8 and #9 fixtures (positive), plus negatives: shared year only; one shared figure; single digits only; same ownership group; primary-tier relay stays unlinked.

## 7. Open questions for the reviewer
- Is ≥ 2 shared + ≥ 50 % containment the right bar, or should a pool with a figure-less original (e.g. a qualitative press release) fall back to an attribution cue (`according to <primary's publisher>`)? The cue needs a publisher name the item does not reliably carry, so it is not proposed yet.
- Should one derivative (not ≥ 2) be enough for the *gate* while the note keeps ≥ 2? Today a single relay counted beside its original is never scoped.

## 8. Review outcome and S4 by mechanism (added after review)
**Review:** `audit/2026-09-30_echo_link_review.md`, APPROVE WITH CHANGES. Its two HIGH safety findings were checked in code and hold:
- The relationship review runs AFTER the gates (`claim_map_analyzer.py:3467-3470`) and can demote an original after echo has already scoped its copies. Nothing restores the copies, so a side can lose its original and every copy of it.
- The gate driver walks refs in order and reads other refs' live state (`:3328-3373`). A copy can be scoped against an original that a later gate then removes.
- Both exist today; more links make them fire more often. Any build must include a reconciliation pass after the gates and the review that restores copies whose originals are no longer counted, plus a set of originals per copy (review H2).

**All 11 S4 fails by mechanism** (from the blind grade files). This design covers only the figure-relay row:

| Mechanism | Records | Likely fix | Difficulty |
|---|---|---|---|
| Same page under tracking-parameter URL variants (`srsltid`, `?eafs_enabled=false`) | #5, #12, #14 | URL canonicalisation before dedup | 1–2 |
| Wire / syndicated article on several hosts (Reuters on nikkei + cnbc; Lexology = Browne Jacobson; advisorhub = Bloomberg Law) | #4, #6, #11 (part) | near-identical-text host dedup | 2–3 |
| Figure relay of a counted original | #8, #9 (Wisedocs; JAMIA is PRIMARY and stays) | this design | 3 |
| Relay with no shared figures (summaries of the Carbon Brief factcheck; an X post promoting HSJ) | #13, #11 (part) | attribution cue | 3+ |
| A site's tag/index page repeating its own article | #15 | same-site index-page detection | 2 |
| One study on two hosts without a shared DOI | #19 | same-study gate: title/author match | 3 |

**Grade lift, honestly:** a B+ becomes A− only if one of its two soft fails goes. On that test this design lifts **#8 only** (#9 keeps its JAMIA relay; #13 needs the attribution cue). The URL-variant fix lifts no grade (#5, #12 and #14 have hard fails) but is cheap and removes visible duplicates on three of 19 records. #19's only fail (A− → A) is the same-study row.

## 9. Built: the safety fix only (founder choice 2026-09-30: "safety holes first")
The figure-relay links (§4) are NOT built. What was built closes the two ways a side could lose an original and every copy of it.

- **Ref order (review H1, part 2).** `_apply_scope_gates` runs in three passes over all refs: the gates before echo, echo, then the gates after it (`fact_applicability`, flag-only). Echo now sees every earlier gate's outcome on every ref, so a copy is never scoped against an original that a later gate removes. Precedence is unchanged and one gate still owns each ref.
- **Later demotion (review H1, part 1).** `_restore_orphaned_echoes` runs after the relationship review, in completion and in recovery. It puts back each echo-scoped copy whose original no longer counts on its side, records it under `echo_scope.restored` (invariant #5) and re-derives basis and state. Symmetric: it reads `was`. **Restored copies are then reviewed themselves** (`review_relationship_scope(..., only=...)`), because a copy relays the content the review just rejected in its original. If that review fails or is cancelled, the restore is undone.
- **Verifier fixes (independent verification, PASS WITH FIXES):** the review treats pairs decided in ANY earlier run as settled (`prior_runs`), not only the latest; the completion timeout covers the second review call; receipts are built before the relabel (echo's entry reads the ref's side; recital receipts now agree with `fires`, which can change recital receipt content on challenge refs); receipt merges keep `restored`; the bench nets restored copies out of `echo_scoped_refs` (`[ECHO RESTORED]` log line).
- **Review H2 (match a copy against any of its originals): built, measured, backed out.** On corpus 0004 it scoped Wikipedia and two blogs as "copies" of a UNCTAD page because they share the date "August 16, 2022". It widens the gate over weak links whose precision has never been measured. Deferred until the link detector is measured (§6 control arm); pinned by `test_copy_of_two_originals_is_matched_on_the_first_only`.
- **Tests:** `tests/unit/pipeline/test_echo_orphans.py` (13), every part mutation-checked (10/10 mutants killed across the two rounds). A chain of copies (A→B→C, verifier note 6) cannot occur: chains live only on PRIMARY items and derivatives must be REPORTING/COMMENTARY.
- **Bench:** before H2 was backed out, 0004 and 5647 drifted. After: 0004 replays clean. 5647 drifts by exactly one new request, the re-review of a restored copy: the review demoted the RMetS paper on "London 40.3°C" ("mentions that temperatures exceeded 40°C somewhere in the UK … does not specify London"), and its copy (internetgeography, commentary) came back for its own review. That is the designed path firing on the corpus; the cassette needs one `--record-missing` pass (a paid model call, founder approval).
