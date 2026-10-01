# Echo link confirmation: independent design review (2026-10-01)

**Design reviewed:** `audit/2026-10-01_echo_link_confirmation_design.md` (rev 1).
**Reviewer:** independent; did not write the design. No code changed.

## Verdict: APPROVE WITH CHANGES

The seam is right. `annotate_post_classify_structure` (`runner.py:1268-1300`) runs after classify and distil have both finished (`runner.py:2299`, `:2302`) and before mapping (`runner.py:2336-2342`, then `map_evidence_batch` at `:2482`). Nothing between them replaces the evidence dicts: the ledger snapshot copies (`dict(ev)`) but does not swap them, and `claim["evidence"] = claim_evidence` (`:2468`) passes the same objects to the analyzer. The per-claim evidence cache is restored at retrieve time (`workers/pipeline.py:296-320`), so chains are always computed on the live pool, never on a cached one. Cross-claim URL dedup (`runner.py:1813-1866`) runs earlier and only moves objects between lists.

But the design has four faults that must be fixed before the build. The worst: the text the model reads and the cue is checked against is **model-written**, not source text.

## HIGH

**H1. The "stored excerpt" is distilled model text, so the verbatim-cue guard checks nothing.**
- After distil, `ev["text"]` is the distiller's bullet list (`evidence_distiller.py:180-186`, provenance marked `model_generated_facts`), and `finalize_distilled_payload` copies it into `snippet` (`text_provenance.py`, `finalize_distilled_payload`). The distiller's own docstring says "Generated facts are not quotations" (`evidence_distiller.py:9`).
- The distiller is shown the claim and elements (`evidence_distiller.py:123-126`) and told to "Preserve original attribution (e.g. 'according to the ONS')". So two independent pages distilled against the same claim come out in similar words, and attributions are re-written in a canonical form. A "copied sentence" or "according to X" cue can be manufactured by the distiller.
- This also undercuts the "claim text NOT sent" rule: the excerpt is already claim-shaped.
- The originator review hit the same problem and solved it: "Never `text` (distillation rewrites it concurrently)" (`originator_review.py:157-163`); it copies the page opening before distil (`copy_page_opening`, `:131-140`, called at `runner.py:2135`).
- The 2026-10-01 labels were made on `e.snippet` from the DB (`audit/echo_precision/extract.py`, the SELECT), i.e. on distilled text for distilled items. The labeller judged relay from model rewrites.
- **Required:** the confirmer's input and the cue check use only verbatim source text: `text_provenance.original_snippet`, `text_provenance.passages`, and a claim-independent page opening copied before distil (reuse `copy_page_opening`, but not gated on `ENABLE_ORIGINATOR_REVIEW`, and under its own key since `classify_batch` pops `_page_opening`). Never `text`/`snippet` when `_distilled` is set. A pair with no verbatim text on either side is `not_inspected` with a receipt. The held-out labels in §6 step 2 must be made on the same verbatim text, not on `evidence.snippet`.

**H2. The note's "≥ 2 confirmed" rule is not what the readers compute.**
- The note fires on `originals >= 1 and derivative_count >= 2` for a side (`support_structure.py:85-87`, `support-structure.ts:41`).
- `derivative_count` counts on-side items whose id is in ANY chain in the pool (`claim_map_analyzer.py:1435-1441`, `:1371-1372`). It is not "copies of one original on this side".
- With chains at ≥ 1: two different primaries on the support side, each with one confirmed copy there, give `originals=2, derivative_count=2`, and the note says "Several of these sources repeat a single original report". False. A copy whose original sits on the other side also counts.
- The note feeds `side_quality_note`, which makes an element toppable via Strengthen (paid), and the PDF (`checks.py` `_element_quality_notes`).
- **Required:** keep two separate fields. Either (a) `derivation_chain` keeps today's meaning (≥ 2 confirmed copies) and the gate reads a new field (e.g. `confirmed_copies`, ≥ 1) in `_index_evidence`; or (b) the basis computes copies grouped by original, counting only copies whose original is counted on the same side, and both readers change in one parity-locked commit with new test cases. Option (a) leaves the frontend and parity tests untouched; prefer it. Add a test: two originals with one copy each on one side ⇒ no echo note.

**H3. Strengthen (re-search) silently drops every chain, so the paid action the note invites undoes the echo accounting.**
- Chains are not persisted: the `Evidence` model has `corroboration_group_id` and `corroborating_evidence_ids` only (`models/check.py:407-414`), no `derivation_chain`.
- `research_claim` re-maps the whole pool from DB rows (`re_search.py:128-136`) and never calls `annotate_post_classify_structure`. So after a Strengthen run the echo gate is silent, copies count again, the echo note vanishes, and `metadata.echo_links` (carried over by `copy.deepcopy`, `re_search.py:45`) still says "confirmed" for links no gate applied. The receipt then misdescribes the report (invariant #5).
- **Required:** persist confirmed links (the `metadata.echo_links` records are enough: original_id, derivative_id, status) and, in `research_claim`, rebuild the chain fields on `existing` from the confirmed records before mapping, with no new model call. New candidates either go through confirmation against existing primaries or get `not_inspected: re_search` receipts. Add a test that a Strengthen run keeps an echo-scoped copy scoped.

**H4. The privacy premise is wrong: claim-map metadata is public, including `scopeReview`.**
- `_claim_map_to_camel_case` copies every `metadata` key as-is (`response_builder.py:56-74`). The public report endpoint `get_public_check` (`checks.py:2827`, no auth) returns it (`checks.py:2953-2955`).
- So `scopeReview` is not "owner payload": it is on `/r/` today, with the model's per-pair `reasoning` (`relationship_scope_review.py:200-211`, stored at `:387`). `metadata.echo_links.reason` would be public too, against the rule the design cites.
- **Required:** do not store `reason` in claim-map metadata, or add an explicit strip of `echoLinks[*].reason` in the public path with a test that `/r/` JSON carries no `reason`. Raise the existing `scopeReview.pairs[*].reasoning` exposure with the founder as a separate item; it is the same rule.

## MEDIUM

**M1. A pool-level "relay" can hide independent content on the element that matters.**
- The model judges "does B's content come from A" over the whole excerpt. The gate then scopes B on every element where A is counted on the same side (`claim_map_analyzer.py:3324-3346`). If B relays A's figure AND adds its own data or an independent expert on the same side, B's independent support is hidden as "echo".
- **Required:** add `extent` ∈ {`whole`, `part`} to the output. The gate fires only on `whole`; the note may use both. The eval labels must record extent, and the partial-relay rate must be reported.

**M2. The verbatim cue proves the span exists in B, not that it shows derivation.**
- A model can quote B's sentence "JWST's mirror is 6.5 metres" as its cue. It is verbatim in B and proves nothing.
- The design sets no minimum length; the originator review uses 12-600 chars (`originator_review.py:40`, `:223`).
- **Required:** a `cue_kind` ∈ {`attribution`, `copied_text`, `named_document`} with a mechanical check per kind: `attribution` must name A's publisher, host or a body named in A's title; `copied_text` must be ≥ 40 normalised chars and also appear in A's verbatim text; `named_document` must appear in A's title or text. Minimum cue length 12. A failed check ⇒ `cue_not_found`.

**M3. The evaluation cannot show the target with the planned n, and has leakage.**
- At the measured relay base rate (24%), 120 pairs give about 29 relays and, at 60% recall, about 17-20 confirmed. "≤ 1 independent per 20 confirmed" is then a single point; with 1/20 the 95% upper bound is about 24%.
- Held-out pairs come from the same 317 pools as the 121-pair dev set. Pools share sources; prompt examples tuned on the dev set will see the same A and B pages.
- Labels come from a model labeller, judged against a model confirmer: errors correlate. A 20-pair founder audit is thin.
- Stratification is by rule only. The harm surface is pairs the gate would scope (sample B in the precision doc: same element, same side).
- **Required:** label ≥ 300 held-out pairs (labelling is free) from pools with no dev-set pair; stratify by rule AND by "gate would scope it"; report the Wilson lower bound and pass only if it is ≥ 80% with the point estimate ≥ 90%; label on verbatim text (H1); the founder audits at least 40, weighted to model-confirmed pairs. Set a flip-rate limit for step 3 (e.g. ≤ 5% of pairs change verdict between runs).

**M4. The 5 s latency threshold will be breached by the first call.**
- One 3.7-flash call with thinking takes several seconds to tens of seconds (the relationship review reports 7 s to 25 s per call, `relationship_scope_review.py:17-24`). Any check with a pair will exceed 5 s at p90.
- The stage sits outside `analyze_timeout` (`runner.py:2461`) and has no overall deadline. Worst case 40 s per call, inside the 300 s watchdog.
- **Required:** an overall stage deadline (e.g. 45 s, then remaining pairs `not_inspected`), stage time in `stage_timings`, and an honest budget stated from the step-3 measurement. Plan the overlap with mapping now (start after classify, join before the gates inside `map_evidence_batch`), because v1 will likely need it.

**M5. Determinism and replays.**
- `annotate_post_classify_structure` runs even under frozen evidence replay (`runner.py:2341`, no `_is_frozen_evidence_replay` check). The new model call would run, and spend, on frozen replays and give a different chain set.
- Batch composition affects request bodies (cassette keys). Ties in "link strength" need a fixed tie-break.
- **Required:** under frozen replay, rebuild chains from stored `echo_links` and make no call. Order pairs by (strength, original_id, derivative_id). Record every new request with `--record-missing` (ask first).

## LOW

**L1. No date sanity check.** A B published well before A cannot relay A. Add: if both dates are on the trusted `date_basis` allowlist and B predates A by > 1 day, the pair is `rejected` mechanically with a receipt.

**L2. First-original-only and the cue lookup.** `_index_evidence` keeps the first original per copy (`claim_map_analyzer.py:1705-1709`). The design does not say whether review H2 (any of its originals) returns once links are confirmed. Decide it, and make the cue in `echo_scope` come from the same pair the index kept.

**L3. Chains are merged, not replaced.** `annotate_derivation_chains` writes chains it finds but never clears old ones when the flag is on (`corroboration.py:544-547`). The new stage must clear `derivation_chain` (and any new field) on every item first, then write.

**L4. Flag matrix.** State what happens for each combination of the three flags, in particular confirmation ON with both readers OFF (spend with no effect: the stage should not run).

**L5. Stored checks.** Element `basis` is persisted and signed (`manifest_signer.py:154-157`). Echo notes and echo receipts written before 2026-10-01 on unconfirmed links stay on old reports. Say so in the design; do not rewrite signed reports.

## Checks that pass
- Echo stays the LAST gate: the driver splits passes at `echo_scope` (`claim_map_analyzer.py:3413-3416`); the design adds no gate.
- `echo_scope` is already in `_SCOPE_RECEIPT_KEYS` (`claim_map_analyzer.py:1651`); a new `cue` field inside entries survives `_merge_scope_receipts` and `restored`.
- Recovery items carry no chains (`claim_map_analyzer.py:3958`, comment at `:3980-3983`), so the gate is silent there. Safe direction; unchanged.
- Originator review runs inside classify before this seam, so candidates use final tiers.
- Symmetry: the gate reads side, never direction. Holds, subject to M1.

## Answers to §9

1. **Pool-level or only the pairs the gate would scope?** Pool-level, for v1. Gate-only needs an async step inside mapping, between the gate passes, and the note needs pool-level links anyway. Add `extent` (M1) so a partial relay does not hide independent content. Revisit if step 3 shows cost or latency trouble.

2. **Is ≥ 1 safe for the note if the note keeps ≥ 2 confirmed?** Not as written. The readers count copies across the pool and across sides, not per original (H2). Safe only with a separate field for the gate (option a) or a per-original count read by both parity twins (option b).

3. **Is the verbatim cue too strict for paraphrased copies?** No. It is too weak, not too strict (M2). A paraphrase with no attribution and no copied text cannot be told from independent reporting of the same fact; treating it as `unclear` (both count) is the honest default. Measure the recall cost in the eval rather than loosening the guard.
