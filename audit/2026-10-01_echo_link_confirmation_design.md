# Echo link confirmation: a model confirms each copy link (design, rev 1)

**Status:** design only. Nothing is built. Paid evaluation steps each need founder approval.
**Why:** `audit/2026-10-01_echo_link_precision.md`. The mechanical link (`corroboration.find_corroborating_sources` → `_detect_derivation_chains`) is a real relay 24% of the time pool-wide and 32% of the time where the echo gate actually scoped a source. Both the echo gate (`ENABLE_ECHO_SCOPE_GATE`) and the grey echo note (`ENABLE_DERIVATION_CHAINS`) are OFF since 2026-10-01. This design brings them back on links a model has confirmed.
**Difficulty:** 3 (new model stage, a pipeline seam, invariants #5 and #7). Plan → independent review → founder approval → build.

## 1. Goal and non-goals
- **Goal:** a copy link (primary A ← derivative B) exists only when a model, shown both excerpts, says B's content derives from A AND quotes the words in B that show it. The gate and the note then read only confirmed links.
- **Targets (held-out, §6):** of links the stage confirms, ≥ 90% are labelled relay, with ≤ 1 independent per 20 confirmed. Recall ≥ 60% of labelled relays among candidates.
- **Non-goals:** finding relays the mechanical detector misses (figure relays with units such as `900m`, attribution-only relays: S4 rows #8, #9, #11, #13). That is a candidate-recall problem and comes after precision is fixed. Wire syndication across hosts (#4, #6) and same-site index pages (#15) are other mechanisms (`2026-09-30_echo_link_design.md` §8).

## 2. Where it runs
One seam, so nothing downstream changes:

```
classify + distil (concurrent)
  → annotate_post_classify_structure(evidence)        runner.py
       candidates = mechanical links, primary A ↔ reporting/commentary B, same pool
       NEW: confirm_echo_links(candidates)  → model verdict per pair
       write derivation_chain on A = confirmed Bs only
  → mapping → scope gates (echo reads chains) → relationship review → basis (note reads chains)
```

- **Why pool-level, not per element:** the chain is pool-level already, both readers consume it unchanged, and the gate's existing safety machinery (`_restore_orphaned_echoes`, the review of restored copies, the 2026-09-30 fix) stays exactly as it is.
- **Candidate threshold drops to ≥ 1 derivative** (from ≥ 2). The ≥ 2 rule was a crude precision guard; confirmation replaces it. The gate fires on one confirmed copy of a counted original. **The note keeps ≥ 2 confirmed derivatives**, which is its meaning ("re-reported by two or more").
- **Latency:** sequential in v1, one call for most checks (§4 sizes it). If it adds more than ~5 s at p90, the follow-up runs it concurrently with mapping and joins it before the gates. That join is not in v1.

## 3. The model call
- **Model:** `ECHO_LINK_MODEL`, default `gemini-3.7-flash` (the relationship and originator reviews' model; flash-lite failed the originator eval). Output cap 8192: thinking tokens count against it (originator eval 2 lost 35–40 items to a smaller cap).
- **Batching:** ≤ 6 pairs per call, ≤ 24 pairs per check (`ECHO_LINK_MAX_PAIRS`), 40 s per call, calls concurrent. Over the cap, pairs are taken in order of link strength (more shared non-year facts first, then text similarity). Pairs not inspected get no link and a receipt.
- **Input per pair:** for A and B: publisher host, URL, title, published date, the stored excerpt (≤ 1,000 chars) and up to two `text_provenance` passages. Source text is marked as untrusted data. **The claim text is NOT sent** (COMPARE-tab lesson: a model shown the claim starts judging it).
- **Question:** "Does B's content here come from A: a quote, summary or re-report of A's own finding, figures, statement, release or study? Sharing a topic, a year, a common fact or a date is not enough."
- **Output, per pair:** `verdict` ∈ {`relay`, `independent`, `unclear`}; `cue`: a verbatim span of **B** (≤ 200 chars) showing the derivation (an attribution such as "according to NASA", a copied sentence, the same named release); `reason` ≤ 1 sentence.
- **Mechanical guard (fail closed):** a `relay` counts only if `cue` is found verbatim in B's text (whitespace- and case-normalised). Otherwise it is downgraded to `unclear`. `unclear`, `independent`, timeout, invalid JSON or any error means **no link**. The failure direction is today's behaviour: both sources count.

## 4. Size and cost (measured on local pools, free)
- 741 candidate pairs across 317 pools at ≥ 2; 137 pools have any. Lowering to ≥ 1 adds pairs; the count is re-measured in step 1 of §6 before any spend.
- Estimate: median 0 pairs per check, about 5 in pools that have any, so one call. Relationship review costs ~1p per check on the same model with a larger payload, so this should be well under 1p per check. **Quote the real figure from the eval's per-call token counts, not this estimate** (originator lesson: measure one unit's cost first).

## 5. Receipts (invariant #5)
- Each candidate pair gets a record in the claim map's `metadata.echo_links`: `{original_id, derivative_id, verdict, cue, reason, status}`, with `status` one of `confirmed`, `rejected`, `unclear`, `cue_not_found`, `not_inspected`, `failed`. Plus run totals and seconds.
- The echo gate's receipt (`basis.echo_scope`) gains the confirming `cue`, so a reader sees why a source was treated as a copy.
- **Public payload:** `metadata.echo_links` follows the same exposure as `scopeReview` (owner payload). The `cue` is verbatim source text, so it is safe for `/r/`. Model `reason` text is NOT public (Track Q rule: model free text on the public record is gated fail-closed).

## 6. Evaluation (held-out; paid steps need founder approval)
1. **Free:** re-run candidate generation at ≥ 1 over the 317 local pools. Count pairs per pool (cost basis). Exclude every pair in the 121 already labelled; those were read while writing this design and serve as the **dev set** only.
2. **Free (subagent time only):** a fresh blind labeller labels 120 held-out pairs, ≤ 2 per pool, stratified across text-rule and fact-rule candidates. Same rubric as 2026-10-01. **The founder audits 20 of them** (as the originator labels were audited); disagreements are reported and fixed before scoring.
3. **Paid (~£0.10–0.20, ask first):** run the stage on the held-out pairs twice (flip rate). Score: confirmed precision, independents per 20 confirmed, recall, cue-not-found rate, failures, p90 seconds, tokens per pair → real cost per check.
4. **Free:** state replay on stored claim maps with the confirmed chains (gate on): list every element state change, read each one.
5. **Bench:** `--all` with flags on vs off, `--record-missing` for the new calls (paid, small, ask first). Expect only echo receipts and support counts to move.
6. **Paid (~2p, ask first):** two local live checks, both receipts read.
7. Switch on (`ENABLE_ECHO_LINK_CONFIRMATION`, `ENABLE_DERIVATION_CHAINS`, `ENABLE_ECHO_SCOPE_GATE`, all three together), push, and read the first production check's `echo_links`.

**Fail ⇒ stays off.** If precision misses 90%, there is no threshold tuning on the held-out set; a new held-out draw is needed after any change.

## 7. Flags
- `ENABLE_ECHO_LINK_CONFIRMATION` (new, default False). When it is off, chains are written only if `ENABLE_DERIVATION_CHAINS` is on, unconfirmed (today's old behaviour, kept only as a rollback lever).
- **Guard:** a startup log warning when `ENABLE_ECHO_SCOPE_GATE` or `ENABLE_DERIVATION_CHAINS` is on while confirmation is off. That is the measured low-precision configuration.
- `audit/FLAGS.md` is regenerated in the same commit.

## 8. Risks
- **The model agrees too readily** ("both mention JWST's mirror"). The verbatim cue and the explicit not-enough list are the guards; the held-out precision target is the test.
- **Well-known facts** (launch dates, physical constants): the 2026-10-01 labeller split on these. The rubric must settle it before labelling. Proposed: a relay only if B shows copying or attribution to A. A common fact stated in common words is independent.
- **Excerpt starvation:** the excerpt may omit the attribution that sits elsewhere on B's page. That gives a false `unclear`, which is the safe direction. Recall may suffer; measure it.
- **Symmetry (invariant #7):** the stage never sees relationship direction, and the gate scopes supports and challenges alike, so nothing here can favour a side.
- **Order invariants:** echo stays the LAST gate. `_SCOPE_RECEIPT_KEYS` is unchanged (`echo_scope` is already registered).

## 9. Questions for the reviewer
1. Pool-level confirmation (all candidates, ~5 pairs) or confirm only the pairs the gate would actually scope (fewer calls, but the gate then needs an async step inside mapping)?
2. Is dropping the candidate threshold to ≥ 1 safe for the note, given that the note keeps ≥ 2 confirmed?
3. Is the verbatim-cue guard too strict for real copies that paraphrase without attribution?

---

## 10. Rev 2: every review finding taken (`2026-10-01_echo_link_confirmation_review.md`, APPROVE WITH CHANGES, 4 HIGH)
Where rev 2 and §§1–9 disagree, rev 2 wins.

**H1, verbatim text only.** The confirmer reads, and every cue check uses, only verbatim source text: `text_provenance.original_snippet`, `text_provenance.passages`, and a claim-independent page opening copied before distil. That reuses `copy_page_opening` under its own key, not gated on the originator flag. It never reads `text`/`snippet` on a `_distilled` item. A pair with no verbatim text on either side gets `not_inspected: no_verbatim_text`. **Consequence for the 2026-10-01 measurement:** 47/80 and 36/41 of its labelled pairs were distilled text. A re-label on verbatim text (48 pairs where both sides have it) is running; §11 records the result and whether the gate-off decision still holds.

**H2, two fields.** `derivation_chain` keeps today's meaning: ≥ 2 confirmed copies, read by the note, so the frontend and parity tests are unchanged. The gate reads a new field, `confirmed_copies` (≥ 1), through `_index_evidence`. A new test: two originals with one copy each on one side ⇒ no echo note.

**H3, Strengthen keeps the links.** Confirmed records persist in `metadata.echo_links` (original_id, derivative_id, status, extent). `research_claim` rebuilds both fields from them before re-mapping, with no model call. New re-search candidates get `not_inspected: re_search`. A new test: a Strengthen run keeps an echo-scoped copy scoped.

**H4, public payload.** `reason` is never stored in claim-map metadata. Only `status`, `extent`, `cue_kind` and the verbatim `cue` are stored. A test asserts the `/r/` JSON for `echoLinks` has no `reason`. **Separate founder item:** `scopeReview.pairs[*].reasoning` (relationship review model text) is on `/r/` today (`response_builder.py:56-74`, `checks.py:2953`).

**M1, extent.** The output adds `extent` ∈ {`whole`, `part`}. The gate fires only on `whole`; the note counts both. The labels record extent; the partial-relay rate is reported.

**M2, cue kinds with mechanical checks.** `cue_kind` ∈ {`attribution`, `copied_text`, `named_document`}:
- `attribution`: the cue names A's publisher, host label, or a body named in A's title.
- `copied_text`: ≥ 40 normalised chars, present in BOTH A's and B's verbatim text.
- `named_document`: present in A's title or text.

Every cue is ≥ 12 chars. Any failed check ⇒ `cue_not_found` ⇒ no link.

**M3, evaluation.** ≥ 300 held-out pairs (labelling is free) from pools with NO dev-set pair. Stratified by rule and by "the gate would scope it". Labelled on verbatim text. **Pass:** Wilson 95% lower bound ≥ 80% AND point estimate ≥ 90% on confirmed links; recall reported; flip rate ≤ 5% between two runs. The founder audits ≥ 40 labels, weighted to confirmed pairs. Cost estimate: ≈ 300 pairs / 6 per call ≈ 50 calls × 2 runs on 3.7-flash, about £0.30–0.60. A real per-call figure is quoted after the first 6 calls, before the rest run.

**M4, latency.** An overall stage deadline of 45 s; any rest → `not_inspected: deadline`. The stage time goes in `stage_timings`. **v1 overlaps the stage with mapping:** it starts after classify and joins before the gate passes. The design for that join comes in the build plan, with its own review.

**M5, replays.** Under frozen evidence replay, links rebuild from stored `echo_links` with no call. Pair order is (strength desc, original_id, derivative_id). New requests are recorded with `--record-missing` (ask first).

**L1** mechanical date check: when both dates are on the trusted `date_basis` allowlist and B predates A by > 1 day ⇒ `rejected: predates`. **L2** the index keeps the first confirmed original per copy, and the `echo_scope` cue comes from that same pair. "Any original" (review H2 of 30 Sep) stays out. **L3** both fields are cleared on every item before writing. **L5** reports stored before 2026-10-01 keep their old signed notes and receipts; they are not rewritten.

**L4, flag matrix (`CONF` = `ENABLE_ECHO_LINK_CONFIRMATION`, `CH` = `ENABLE_DERIVATION_CHAINS`, `GATE` = `ENABLE_ECHO_SCOPE_GATE`).**

| CONF | CH | GATE | Behaviour |
|---|---|---|---|
| off | off | off | Today. No links, no note, no gate. |
| on | off | off | Stage does NOT run (no reader; no spend). |
| on | on | off | Confirmed chains (≥ 2) → note only. |
| on | off | on | Confirmed copies (≥ 1) → gate only. |
| on | on | on | Target. |
| off | on / any | any | Unconfirmed legacy links (rollback only); startup warning. |

## 11. Re-label on verbatim text (H1 check, free)
48 of the 121 labelled pairs have verbatim text on both sides. A fresh blind labeller re-labelled them on `original_snippet` + passages.
- Verbatim: **13 relay / 35 independent**. The same pairs on distilled text: 23 / 25. All 10 disagreements went relay → independent; there were none the other way.
- Scoped subset (pairs the gate actually removed): 10 relay / 17 independent on verbatim text (37%).
- **Distillation made independent pages look like copies, not the reverse.** This matches the review's H1 point (claim-shaped rewrites converge). So the 24–32% figure was, if anything, generous. The gate-off decision stands.
