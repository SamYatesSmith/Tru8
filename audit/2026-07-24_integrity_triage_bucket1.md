# Integrity triage — bucket ① (scoped design note)

**Opened:** 2026-07-24, off the decoupling live battery (`audit/2026-07-23_decoupling_live_test_plan.md`).
**Status:** DESIGN — nothing built. Founder sign-off before any code.
**Scope discipline:** three cheap, unambiguous, *actively-distorting* defects only. Not
the pool-quality lift (P4/P12/P14/P15/P19), not the value-predicate/D1 design
problems (P1/P3/P11/P13 — those go to a separate design review, see §5).

The unifying property of this bucket: each one makes the report **say something
untrue to a skim reader** by a mechanical slip, and each has a mechanical fix that
does **not** touch the retrieval/mapping quality lane. High integrity value per unit
of build risk.

---

## Item A — Self-sourcing: a claim evidencing itself (P16)

**Symptom.** The submitted article is retrieved by web search and mapped as a
**support** for its own claim. An article cannot be evidence for its own assertion.

**Evidence.**
- T5 `TRU-0CA7-E3A1` — the submitted BBC URL (`bbc.com/cwyq93j34lgo`) mapped as SUPPORTING claim 05.
- T6 `TRU-940B-2A15` (aggravated) — claim 11 e02 carried a **+SUPPORTED** badge whose **sole** support was the submitted article (`bbc.com/cvgjp79m42go`). A state resting entirely on self-citation.

**Root cause (grounded).** Cross-element URL dedup runs on `seen_urls` in
`backend/app/pipeline/retrieve.py:1694-1729`, and the pool already threads an
`existing_urls` exclusion set (`:641`, `:950`). Nothing seeds that set with the
**submitted** URL (or its canonical/AMP/syndicated variants), so when a general web
search re-surfaces the source article it enters the pool like any third-party source.

**Proposed fix.** Seed the pool-exclusion set at ingest with the submitted URL and its
canonical form. Two design options — **founder to pick**:
- **(A1) Hard-exclude** the submitted URL from the evidence pool entirely. Simplest; guarantees no self-support.
- **(A2) Demote to context** with an explicit provenance note ("this is the submitted source"). Keeps it visible but never lets it drive a state.

Recommendation: **A2** — it's more honest (the reader sees the source was considered
and why it's not counted) and it composes with the receipts invariant (#5: every
exclusion has a receipt). A1 risks a silent disappearance that looks like curation.

**Constraint / watch.** Canonicalisation must catch syndication (AMP, `m.`, tracking
params, mirror domains) or the exclusion is trivially bypassed. Start with exact +
canonical-URL match; log near-misses for a later syndication pass — **do not** silently
drop suspected mirrors (that would be hidden curation).

**Test.** Submit a URL check; assert the submitted URL appears in the pool as `context`
with the provenance note (A2) or is absent (A1), and never in any element's
`supports`/`challenges`. Regression: a *third-party* article at the same domain is
unaffected.

---

## Item B — Badge contradicts its own prose (P2, the `cad0020` class)

**Symptom.** An element wears a directional badge (**+SUPPORTED** / **±DISPUTED**) while
the mapper note on the supporting evidence says the link **is not established**. The
badge is what a skim reader trusts; it overstates the evidence.

**Evidence.**
- T1 `TRU-1795-FFC5` e05 — **+SUPPORTED** while its own note says the causal link is not established.
- Same class as the historical `cad0020` bug (a challenges-only element wearing "±Disputed").

**Root cause (grounded).** Element **state** is derived mechanically from
`evidence_refs` (counts of supports/challenges), while the human-readable **note** is
produced separately (`backend/app/pipeline/support_structure.py` owns the
thin/echo/repetition note payloads, locked character-for-character). There is no
**parity gate** asserting that a `+SUPPORTED` state is compatible with a note that
disclaims the link. The two channels can disagree.

**Proposed fix.** A mechanical parity check at orientation time: if the evidence
backing a directional state carries a "link-not-established" / thin caveat on the
*driving* refs, either (B1) downgrade the state to `context`/`insufficient`, or (B2)
surface the caveat on the badge itself (e.g. "+Supported · qualified"). **Founder pick.**

Recommendation: **B2** — it preserves the mechanical state derivation (invariant #4:
`evidence_refs` is source of truth; don't let prose silently rewrite counts) while
stopping the badge from *overstating*. B1 risks the inverse distortion (understating a
genuinely-supported element because one note hedged).

**Constraint / watch.** Must be a **mechanical** rule keyed off the existing note
metadata, not an LLM re-judge. Reuse `element_has_quality_note()` /
`side_quality_note()` (`support_structure.py:63-127`) as the signal source — they
already compute exactly this.

**Test.** Construct an element whose sole support carries a "not established" note;
assert the rendered badge is qualified (B2) or the state is `context` (B1). Parity
lock: `support_structure.py` ↔ `support-structure.ts` stays byte-identical.

---

## Item C — Internal machinery labels on the user-facing report (P7, P18)

**Symptom.** Internal pipeline vocabulary surfaces on the report face:
- "**NORMATIVE FLAGGED**" on a claim card (T6 — the internal hint name leaking).
- A normative claim displayed as "**EMPIRICAL**" (T1, and T7 below — the claim-type badge shows the wrong/internal register).

Neither is user language; the first is machinery, the second is inaccurate.

**Evidence.** T1 `TRU-1795-FFC5` (normative shown "EMPIRICAL"), T6 `TRU-940B-2A15`
("NORMATIVE FLAGGED" on the card), T7 `TRU-2DB7-797A` (evaluative claim badged
"EMPIRICAL" — §T7 grade).

**Root cause (candidate — confirm at build).** The claim-type badge renders the raw
internal classification/hint enum rather than a user-facing register. Candidate
surfaces: `web/components/claim-map/claim-type-badge.tsx` and the claim summary panel
(`web/components/evidence-views/ClaimSummaryPanel.tsx`). The `normative` hint is an
*internal* routing signal (Rule 6) that should never render verbatim.

**Proposed fix.** Suppress internal hint/label vocabulary from all user-facing surfaces.
Either drop the register badge for hinted-normative claims, or map internal enums →
a small user-facing vocabulary. Cosmetic, near-zero behavioural risk — but do it as a
**display-only** change; do not touch the hint's routing role.

**Constraint / watch.** Display-only. The `normative` hint must keep driving the grounds
stage exactly as now — this item changes what the *reader* sees, nothing upstream.

**Test.** Snapshot a hinted-normative claim's card; assert no "NORMATIVE"/"FLAGGED"
string and no misleading "EMPIRICAL" register renders. Behavioural regression: grounds
stage still fires (element questions still open-form).

---

## Sequencing & effort

| Item | Lane | Effort | Risk | Blocked on T7/T8? |
|---|---|---|---|---|
| A — self-sourcing exclusion | retrieval (pool seed) | S | low | no |
| B — badge/prose parity | orientation (mechanical gate) | S–M | low | no |
| C — label leaks | frontend (display) | XS | ~none | no |

None is blocked on the remaining battery checks — all three can build now. Suggested
order: **C** (trivial warm-up, removes the most visible embarrassment) → **A** (clean
integrity win) → **B** (needs the founder pick B1 vs B2).

Method: `phased-build-loop` — design (this note) → founder approval → build → independent
verify with evidence → sign-off, one item at a time.

## §5 — explicitly NOT in this bucket (routed elsewhere)

- **P1 / P11 / P13 value-predicate & frame leak, P20 disclosure gap, P21 badge/orientation
  semantics** → **decoupling design review** (now the top design priority — these are the
  reframe's own downstream read-layer distortions, all hitting invariant #7 at the
  most-read layer). Constrained by the removed forced-counter-slot (any remedy must not
  reintroduce it). See battery log P20/P21.
- **P3 D1 one-sided-pool hardening** → **KEEP DEFERRED.** T8 (`TRU-21DE-A158`) was the
  probe built to expose it; the pool was strong and mapping honest, the tripwire was not
  needed. Not worth spending here yet.
- **P4 / P12 / P14 / P15 / P19 pool quality** → named retrieval-side backlog (F1/F7
  families), a real lift, not triage. (T8 confirms it's topic-dependent: a well-covered
  UK-NHS topic gave a strong pool; the drift shows up on obscure/unanchored subjects.)
