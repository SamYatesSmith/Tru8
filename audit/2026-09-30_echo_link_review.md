# Review: echo links design (rev 1)

**Date:** 2026-09-30. **Reviewer:** independent agent (no code written, nothing spent). **Design:** `audit/2026-09-30_echo_link_design.md`.

## Verdict: APPROVE WITH CHANGES

The diagnosis is right and the change is well contained. The doc's safety argument ("a side never loses its original") is false on two paths, and the evaluation cannot see either of them. Fix H1 and H2 in the same build. Rework §6 as in H3 and M3 before the flag goes on.

---

## 1. Root causes (§3): correct, with two details

Checked by running the live `_extract_key_facts` (`backend/app/utils/corroboration.py:102`, `re.findall(r"\b\d+(?:\.\d+)?%?\b", text)`):

| input | result |
|---|---|
| `a 900m tower` | `set()` |
| `1,100 people` | `{'1', '100'}` |
| `36% of` | `{'36'}` |
| `£2.5bn` | `{'2'}` |

- Cause 1 is correct. There is no `\b` between a digit and a letter, so `900m` never matches.
- Cause 1 is also broader than the doc says. The `%?` never survives, because `\b` fails between `%` and a space, so the regex backtracks and "36%" becomes "36". `2.5bn` yields a spurious `2`.
- Cause 2 is correct. `_check_fact_overlap` (`:122-130`) is symmetric Jaccard, so a relay's extra figures penalise it.
- I could not re-run the §3 table itself because the stored pools are not in the repo.

## 2. Scope: correctly contained, but more changes downstream than the doc says

**Left untouched, as the doc says (provided `_extract_key_facts` itself is not edited and the new test is called only from `annotate_derivation_chains`):**
- corroboration groups: `apply_corroboration_boost` at retrieve time (`retrieve.py:2881`) persists `corroboration_group_id` and `corroborating_evidence_ids` (`runner.py:3336`), and `response_builder.py:124-125` emits them;
- the Cartographer (`computed_analytics._build_corroboration`);
- repetition clusters, which use their own shingles (`corroboration.py:391-521`).

**Who reads `derivation_chain`.** It is not persisted: it is not on the `Evidence` model and not in the API. It lives in memory between `runner.py:2313` and mapping. It has three readers:
1. `_index_evidence` (`claim_map_analyzer.py:1613-1620`) inverts it into `original_id`, which the echo gate uses (`:3233-3256`).
2. `_compute_element_basis` (`:1436-1440`) and `_compute_relationship_structure` (`:1368-1371`) turn it into `basis.support_structure/challenge_structure.derivation`. The echo note reads that (`support_structure.py:85-89`, `web/lib/support-structure.ts:37-41`).
3. Through those two, it also reaches:
   - element state;
   - `orientation` and `orientation_basis`, which are in the signed manifest payload;
   - `basis.echo_scope` receipts, which reach the public `/r/` and the PDF label "a copy of a source already counted" (`checks.py:2141`);
   - the relationship review's request, via which refs are still directional (see M5).

The doc should list all of these as what changes.

**Informational.** The basis is computed after the gates (`:2588` gates, then `:2608` basis). So on the side where the echo gate fires, the scoped derivatives drop out of `derivative_count`, and the echo note usually does not fire there. The receipt is the surface the reader sees, not the note. "The echo note keeps its contract" is literally true, but it will rarely show.

## 3. Can a new link move a state? Yes, both ways. "A side never loses its original" is not true end to end.

**How a link reaches the state.**
- A new link reaches `original_of` (`:1620`).
- `_echo_fires` returns True when a ref with `evidence_id == original` is currently directional on the same side (`:3239-3246`).
- The ref becomes `context` (`:3351`), then the state is derived from the remaining refs (`:2619`).
- Weights are primary 3, reporting 2, commentary 1 (`:971`). The rules are strict `>`-2× on both sides, and a close split reads `disputed` (`:1152-1160`).
- The floor is 3 for both claim types (`:1030-1038`, `config.py:730-744`).

**Floor.** On its own, echo cannot breach the floor on a support side. The original is primary (weight 3), and it must be counted for the gate to fire. That part of the claim holds.

**The 2× rule.** Echo can flip states through it, in both directions.
- Supports P + R + R (7) against one reporting challenge (2): `supported` (7 > 4).
- After two new links: 3 against 2, which is a close split, so `disputed`.
- One official source relayed widely, plus one outlet disagreeing, then reads `disputed`. That is the false-balancing that invariant #7 names. It may be the honest arithmetic, but the doc should name this path and §6 needs a bar for it (H3).
- The same holds on the challenge side.

**Path A: the relationship review can remove the original after echo has fired (HIGH, H1).**
- The review runs after the main pass (`:3468-3470`, default ON).
- `plan_review` sends only refs that are still directional (`relationship_scope_review.py:252-256`), so echo-scoped derivatives are never reviewed.
- It demotes on `unknown` as well as `mismatch` (`:690-698`), then re-derives state (`:717-722`).
- Nothing brings the echo-scoped derivatives back.
- Worked example: the original P is the only counted support, and two relays are echo-scoped. The review returns `unknown` on P because P's snippet does not state the figure. This is plausible: the PMC snippet vs Wisedocs' plain "45%… 36%". The side is now empty, and the element goes from `supported` to `unresolved`/`contextual`.
- Without the new links, the relays would have been reviewed themselves and could have kept the element supported (2 + 2 = 4 ≥ 3).

**Path B: the order in which gates run over refs (pre-existing; new links make it fire more often).**
- `_apply_scope_gates` loops ref by ref, then gate by gate (`:3328-3373`). It does not run each gate across all refs.
- Echo reads the original's live state. If a derivative comes before its original in `evidence_refs`, echo fires while the original is still directional.
- The original is then reached later and taken by an earlier-listed gate (temporal, jurisdiction, measure, recital, date, same-study…).
- Result: both are `context`, and the content is gone from the side.

## 4. Risks the doc misses

**HIGH, H2: a derivative linked to two primaries.**
- `_index_evidence` keeps the first primary in pool order (`original_of.setdefault(did, oid)`, `:1620`).
- A new link can give an existing derivative a second, earlier primary that is not counted on the element. The gate then stops firing where it fired before.
- So "every old link is kept (union)" does not mean every old scoping is kept.
- Relays that carry many figures (roundups, citing papers) will clear 50 % containment for several primaries.
- Fix:
  - hold `original_ids` as an ordered set;
  - fire when any of them is counted on the side;
  - name the counted one in the receipt;
  - in §6.4, report lost scopings as well as new ones.

**MEDIUM, M1: false links from the figure test itself.**
- **The text it reads is not the page.**
  - At `runner.py:2313`, `text` is usually the distiller's model-generated, element-guided bullets (`evidence_distiller.py:180`), or passage fallback (`:236`).
  - Distillation pulls the claim's own figures out of every page, so independent sources share claim figures by construction.
  - Require at least one shared distinctive figure that is not in the claim or element text, or at least measure how often shared ⊆ claim figures (§6).
- **Round numbers.**
  - Excluding only 0–9 leaves 10, 12, 20, 24, 50, 100, 1000 and "50%".
  - A primary with exactly two distinctive figures links anything that shares both.
  - Require either the primary to have ≥ 3 distinctive non-year figures, or ≥ 1 shared figure that is "specific" (has a decimal, or ≥ 3 significant digits and is not a multiple of 10).
- **Units.**
  - `900m` can be metres or £ million. "36%" and "36 per cent" must match.
  - Specify that tokens compare as normalised values: unit stripped, scale words applied (`m`/`bn`/`million`), `per cent`→`%`.
  - The §5 prototype output ({80, 100, 600, 900, 1100}) suggests bare values, but §4 reads as if units are kept.
- **Page noise.** Day-of-month in dates ("30 September"), "24/7", "© 2025", "Top 10", phone and page numbers.
  - Treat a number inside a date phrase like a year.
  - Define "ordinal/list noise" concretely.
- **Third-body relays.** Covered in §5: correct direction, wrong original named. It still needs the receipt fix in M2.

**MEDIUM, M2: the receipt does not say why a ref was linked (invariant #5).**
- The echo receipt is `{"original_id": ...}` (`:3256`), and the reader's label asserts "a copy of a source already counted" (`checks.py:2141`).
- For a figure heuristic, put the evidence in the receipt: the link basis (`similarity` | `figures`) and the shared figures.
- Carry this in a parallel map on the primary, e.g. `derivation_links: {did: {basis, shared}}`.

**MEDIUM, M5: bench and cassettes.**
- Mapping request bodies do not read chains, so mapping cassettes are not re-keyed. I found no reader of `derivation_chain` outside the analyzer's basis and gate code.
- The relationship-review request is built from the refs that are still directional, so on every bench claim where a new link scopes a support its signature changes. Expect cassette drift there.
- Re-recording is paid, so it needs the founder's approval first.
- Tolerance-0 goldens on support counts and echo receipts may also move. Never commit `--update-golden` output raw.
- §6.5 "expect only echo-receipt / support-count changes" should say this.

**LOW.**
- Recovery items (`ev-rec-*`) and re-search pools carry no chains (`:1519-1521`, `:3860-3862`), so relays retrieved there stay out of reach.
- The same-study gate sits before echo and keys only on DOI/PMID/PMC, so there is no double ownership (the `break` holds). The two do not conflict.
- The retrieve-time `_extract_key_facts` bug stays live in the corroboration groups the Cartographer shows. Record it in `OPEN_WORK.md` as known and out of scope.

## 5. Evaluation (§6): the right shape, but it misses both failure paths

**H3 (HIGH): the state replay in §6.4 cannot see H1 and has no pass bar.**
- Stored claim maps are already gated and already reviewed.
- Rebuilding the pre-gate relationships from each receipt's `was` field is possible, but a replay with no model cannot reproduce the relationship review. The review is exactly where Path A bites.
- Required:
  - (a) fix H1 first;
  - (b) replay by re-running the whole mapping-parse path with stored refs. The review decision for any newly unscoped or never-reviewed pair must be marked as unknown, not assumed;
  - (c) set a bar: zero `supported → unresolved/disputed` flips judged wrong, with each listed by rule (`close_split`, floor).

**M3 (MEDIUM): sample, blinding and recall.**
- **Held-out means held out by claim, not by check ID.** A− re-measure 3 re-ran the 19 claims today, so the "40 most recent checks" will contain those claims. Exclude by normalised claim text.
- **Minimum sample.** Require n ≥ 30 new pairs, and extend the pool until you have them. With 8 pairs, "≥ 90 %" means nothing. Report a lower confidence bound.
- **What the labeller sees.** Show the original snippet or retained passages and the URL, not only the distilled bullets. From bullets nobody can judge whether B has its own basis.
- **Control.** Mix in an equal number of old-link pairs, labelled blind. The old test's precision (0.35 similarity over the first 500 characters, Jaccard including years) has never been measured, and it is the baseline this change is judged against.
- **Recall.** §6 measures precision only.
  - Add a blind S4-style pass on the held-out pools: find relays counted as independent, and measure the share the new links catch.
  - Also classify all 11 S4 fails from re-measure 3 by mechanism: figure relay; duplicate host of one article (a different S4 cause); primary-tier relay; original not counted on the side; recovery item.
  - The doc analyses 2 of 11. It shows no evidence that #13 or #19 are this class, so "cheapest route" is not yet shown.
- **Bench (§6.5).** Run a control arm (flag off twice) before reading any pool difference (CLAUDE.md, 2026-08-20).
- **Tests to add to §6.6:**
  - a derivative placed before its original, with the original taken by an earlier gate;
  - the review demoting the original;
  - a derivative with two primaries, where the earlier one is not on the side;
  - common round numbers only (10, 50, 100);
  - a primary with exactly two figures;
  - `900m` metres vs `£900m`;
  - "36 per cent" vs "36%".

## 6. The open questions (§7)

**Q1: fallback to an attribution cue for a figure-less original?**
- Not in this build.
- First count how many held-out S4 misses have a figure-less original.
- If it matters, build it as its own flag. Take the cue from the primary's organisation name (title, or registrable-domain label) and require an explicit attribution pattern ("according to X", "X said", "in a statement, X").

**Q2: should one derivative be enough for the gate?**
- Logically yes. One copy counted beside its counted original is double counting, whatever the number of copies. That is the NHS failure at n = 1.
- But make it a separate step with its own flag. It multiplies firing on the old, never-measured similarity links too.
- Do it only after H1 is fixed and the old-link precision is measured (M3).
- Keep the note at ≥ 2.

## Findings, ranked

| # | Rank | Finding |
|---|---|---|
| H1 | HIGH | The side can lose its original and every copy of it: the review demotes the original after echo has fired (`:3468`, review `:690-722`), and ref-by-ref gate order lets a later gate take the original (`:3328-3373`). Fix it in this build by releasing echo-scoped refs whose original is no longer counted, and by running echo after the other gates across all refs. |
| H2 | HIGH | A derivative with two primaries keeps the first in pool order (`:1620`). New links can switch off existing scopings. Use a set of originals and fire when any is counted. |
| H3 | HIGH | The §6.4 replay cannot reproduce the review and has no pass bar. The supported→disputed path through close_split (invariant #7 false-balancing) is not named. |
| M1 | MEDIUM | False links: the test reads distilled text that carries the claim's own figures, plus round numbers, ambiguous units and date days. Tighten the rule and specify how values are normalised. |
| M2 | MEDIUM | The receipt does not say why a ref was linked. Add the link basis and the shared figures. |
| M3 | MEDIUM | §6 needs: held out by claim; n ≥ 30; labellers shown page text; old-link control; a recall/S4 measurement; all 11 S4 fails classified by mechanism. |
| M5 | MEDIUM | Relationship-review cassettes will drift where new links fire. The re-record is paid, so ask the founder first. Golden pins may move. |
| L | LOW | The `%?` regex is dead and `£2.5bn`→`2`. Recovery and re-search pools have no chains. The echo note rarely shows where the gate fires. Log the retrieve-time corroboration bug in `OPEN_WORK.md`. |
