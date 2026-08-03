# Design — peer-reviewed society journals are being tiered as commentary

**Date:** 2026-08-03
**Status:** DESIGN — for founder review. Not committed. Replay bench NOT yet run.
**Found by:** comparing `TRU-577F-AB3F` (03 Aug) against `2484b9da` (12 Jun) while
choosing which report to platform.

---

## 1. The defect

The New England Journal of Medicine is classified **commentary**.

`_ACADEMIC_PATTERNS` in `evidence_classifier.py` is an allowlist of academic
publisher domains. It contains `nature.com`, `thelancet.com`, `bmj.com`,
`jamanetwork.com`, `sciencedirect.com` and twenty others — but omits journals
published by **learned societies on their own domains**:

| Domain | Publication | Current tier |
|---|---|---|
| `nejm.org` | New England Journal of Medicine | commentary |
| `ahajournals.org` | AHA journals — *Circulation*, *Stroke* | commentary |
| `ajconline.org` | American Journal of Cardiology | commentary |

Confirmed by running the 18 URLs from `TRU-577F-AB3F` through
`_classify_heuristic`: it reproduces the shipped spread exactly (7 primary / 11
commentary / **0 reporting**), so this is the live behaviour, not a hypothesis.

In that check, an **AHA Scientific Statement in *Circulation*** — peer-reviewed,
the reference document on alcohol and cardiovascular disease — sits in the same
tier as a Drinkaware explainer.

## 2. Why the allowlist is the right lever (and where it isn't)

`_ACADEMIC_PATTERNS` is consumed at **two** sites:

1. `_classify_heuristic` — the fallback when the LLM returns nothing.
2. `_high_confidence_override` — which **beats the LLM's verdict** on URL
   identity, on the stated principle that *"sciencedirect.com IS an academic
   publisher… the tier is structural fact, not interpretation."*

(2) is the one that matters. In the normal path the LLM classifies and the
override corrects it. So adding a domain is not a new mechanism — it is applying
the mechanism already trusted for Nature and The Lancet to venues that are
academic publishers by exactly the same standard.

**The honest limitation, stated up front:** an allowlist cannot close an open
set. There are thousands of legitimate journals; this will always be incomplete,
and every future gap looks exactly like this one. The structural fix is a
publisher-identity signal — a DOI/Crossref lookup, or an ISSN registry — rather
than a hand-maintained list. That is a larger piece of work and is **not**
proposed here. This change buys correctness on the venues most likely to appear
in health, policy and science claims, and it should be understood as an
incremental patch to a list, not a solution to the classification problem.

## 3. Blast radius

Tier is not cosmetic. It is load-bearing in five places. Each was traced.

### 3.1 Element state derivation — REAL, and the largest effect

`claim_map_analyzer.py:832`:
```python
_STATE_TIER_WEIGHTS = {"primary": 3, "reporting": 2, "commentary": 1}
```

Upgrading an item commentary → primary **triples its weight** in the
supports-vs-challenges calculation that derives element state.

This is not theoretical. `TRU-577F-AB3F` element 02 currently reads:

> `mixed: 7 support / 7 disagree (weighted 13 vs 13)`

A dead tie. Re-tiering *any* ref on that element breaks it, and the element's
state (`disputed`) could change. **This change can flip element states, and on
the very report we are considering platforming.**

That is not a reason to avoid the change — a correctly-weighted tie-break is
better than a tie built on a misclassification — but it must be observed, not
assumed. See §5.

### 3.2 Grounds floor — REAL

`GROUNDS_MIN_WEIGHTED_SUPPORT=3` means a question-shaped element needs weighted
support ≥ 3. One primary source clears it alone (weight 3); one commentary does
not (weight 1). Upgrades will move some grounds elements from `unresolved` to
`supported`. This is the intended direction — the floor exists to stop a thin
commentary source badging an element `supported` — but it moves.

### 3.3 Thin-sourcing / support-structure notes — REAL

`support_structure.py:101` flags an element when
`primary == 0 and reporting == 0`. `TRU-577F-AB3F` element 01 currently carries
*"Only commentary-grade sources."* If any of its refs upgrade, **that flag stops
firing** — correctly, but it is a visible change on the report page.

`support_structure.py` is parity-locked with `support-structure.ts`. **No
frontend change is required**: the parity is over the *logic*, which reads
`tier_counts`, and the domain list lives nowhere near it. Verified by reading
both consumers.

### 3.4 Domain capping — SUBTLE, worth naming

`runner.py:269` builds demotion candidates from
`[ev for ev in items if ev.get("tier") in ("primary", "reporting")]`. Commentary
items are **not** demotion candidates. So an upgraded item becomes *eligible for
demotion* under the source-diversity cap — an upgrade can, in principle, cause an
item to be dropped from the shown pool. Low likelihood (the cap only bites when
one domain dominates), but it is a genuine second-order effect and the reason
this section exists.

### 3.5 Manifest signing — SAFE, confirmed

Per-evidence `tier`, `evidence_type` and `classification_method` **are** in the
signed canonical payload (`manifest_signer.py:89`). The question is whether this
change breaks `/verify` for historic checks. **It does not:**

- historic checks keep their **stored** tier values, so their canonical payload
  is unchanged and their signature still verifies;
- `compute_pipeline_fingerprint()` hashes only five *model* settings
  (`primary_llm`, `google_model`, `mapping_google_model`, `decomposition_model`,
  `analyzer_model`) — no domain list, so the fingerprint does not move either.

Only newly-run checks classify differently, which is the point.

### 3.6 Not affected

- Frontend Librarian heatmap — renders stored tiers; no change needed.
- Consensus / convergence — operates on claim text and element identity.
- Cost telemetry, retrieval, mapping prompts — untouched.

## 4. Proposed change

Extend `_ACADEMIC_PATTERNS` with peer-reviewed venues on their own domains.
Selection rule, applied strictly: **the domain must be a peer-reviewed journal or
a recognised academic publisher, such that URL identity alone settles the tier** —
the same bar `_high_confidence_override` already sets.

Deliberately **excluded**, and why:
- `mdpi.com` — peer-reviewed, but contested editorial standards; it would import
  an argument this change does not need to have.
- University news offices (`news.stanford.edu`, `publichealth.columbia.edu`) —
  these report *about* research and are correctly commentary/analysis today.
- Consumer health publications (`health.harvard.edu`, `heart.org`) — correctly
  commentary; they are not the peer-reviewed record.

That last pair matters: the fix must not sweep up every `.edu`-adjacent health
site. The August pool's 11 commentary items include several that are **correctly**
commentary, and the change should leave them alone. Expected effect on that pool
is **7 primary / 11 commentary → 9 primary / 9 commentary** — two items moved,
not eleven.

## 4a. BENCH RESULT — the design under-called §3.4, and the bench caught it

**Run 2026-08-03, classifier change ISOLATED (mapping-prompt change stashed):**

```
OVERALL: FAIL   98 ok, 2 warn, 3 fail        (baseline: 135 ok, 2 warn, 1 fail)

TRU-C1A0-0003   cassette_drift   22 misses / 55 hits
TRU-C1A0-0004   cassette_drift   22 misses / 45 hits
```

Attribution was established, not assumed. With the classifier change **also**
stashed, `TRU-C1A0-0003` runs **18 ok / 0 warn / 0 fail**. So the drift is caused
by this change.

**Why — and where §3.5 was wrong.** That section reasoned that cassettes would
stay valid because the classifier's own LLM request body is unchanged. True, but
irrelevant: tier feeds **domain capping** (§3.4), capping changes the *shown*
evidence pool, and the evidence pool is serialised into the **mapping prompt**.
A different pool is a different request body, which is a cassette miss.

So the second-order effect flagged as "low likelihood" in §3.4 is in fact the
dominant one, and it propagates further than that section allowed: not merely
"an item could be dropped", but "downstream request bodies change".

**Consequence:** this change requires a cassette **re-record and re-gold**, on the
same footing as the held mapping-prompt reframe. It cannot ride on the existing
recordings. §5.3 is superseded accordingly.

**Lesson for the register:** "my change only affects post-processing" is not a
cassette-safety argument on this pipeline. Anything touching tier, relevance or
the shown pool reaches the mapping prompt, because the pool IS part of that
prompt.

## 4b. STOP — the change fails a hard quality invariant. NOT SHIPPABLE as designed.

Re-recording resolved the cassette drift, and a different failure appeared:

```
[FAIL] v3:top_domain_share.claim=0    top_domain_share=0.47 above Poor cap 0.45
```

Attribution was established by a **controlled pair** — two live re-records of the
same corpus claim under identical fresh-pool conditions, differing only in the
classifier:

| Classifier | `top_domain_share` | Bench |
|---|---|---|
| **old** (HEAD) | **0.32** | 17 ok · 1 warn · **0 fail** |
| **new** (this change) | **0.47** | 15 ok · 2 warn · **1 FAIL** |

The change moves source concentration from the "Mediocre" band into **Poor**,
breaching a hard invariant. Six items on that claim move commentary → primary
(`tier_commentary` 8→2, `tier_primary` 10→16), and the shown pool ends up
dominated by a single domain.

Two attempts at cheaper attribution were rejected as unsound and are recorded so
nobody repeats them:

- Replaying the *old* cassette under the new code — fails as drift, since the
  evidence pool feeds the mapping prompt.
- Replaying the *new* cassette under the old code — **also** fails as drift, 22
  misses. Once tier can move the pool, a cassette is bound to the code version
  that recorded it. Only a matched live pair attributes anything.

**The corpus was restored** (`git checkout -- backend/tests/replay_corpus/`) and
re-verified at baseline (18 ok, PASS) before this was written. No recording was
left mutated.

### What must NOT happen next

Relax the 0.45 cap, or re-gold the invariant to accept 0.47. That is weakening a
guard so a change can pass — the same move the replay-bench README already
forbids for missed evidence fetches, on the grounds that it degrades the drift
guard corpus-wide. The invariant is not the problem here.

### Mechanism — FOUND. It is not domain capping.

The earlier hypothesis (domain capping) was **wrong**, and provably so:
`_apply_domain_concentration_cap` demotes **tier** and explicitly leaves items in
place — *"Items remain visible (no hidden curation — receipts trail the
decision)"*. A function that changes no item's presence cannot change a domain
**share**.

The actual chain:

1. `top_domain_share` is computed by `_compute_claim_quality_signals` over
   **MAPPED items only** — the evidence the mapper chose to `evidence_refs`.
2. The mapping prompt **shows the mapper every item's tier** —
   `f"[Tier: {ev.get('tier')}] "` at `claim_map_analyzer.py:1465, 1683, 2278,
   2465` — and instructs it to use them: *"DATA PROVENANCE: Each evidence item
   shows [Tier] and [Type]"* (`:322`, `:582`).
3. Relabelling six items commentary → primary therefore does two things at once:
   it changes the **prompt text** (→ the cassette miss, finding ①) and it changes
   **which evidence the model references** (→ a different mapped set, finding ②).
4. Those items concentrate on one domain, so the mapped set concentrates:
   0.32 → 0.47.

The mapper is doing exactly what it is told: weighting provenance. Given
more-authoritative labels, it cited those sources more.

### The real, pre-existing defect this exposed

**Nothing enforces domain diversity on the mapped set.** `top_domain_share` is an
*observed* invariant in the bench with no *mechanism* upholding it in the
pipeline:

- `_apply_domain_concentration_cap` acts on the **shown** set, and only relabels
  tier — it cannot affect which items the mapper cites.
- `ENABLE_DOMAIN_CAPPING` exists in `backend/.env` but is **referenced nowhere in
  `app/`** — a dead flag, and worth deleting so it stops implying a protection
  that does not exist.

So the bench has been passing this invariant by luck of pool composition, not by
design. This change did not create the fragility; it revealed it. Any future
change that shifts tier — the Gemini migration will, since classification moves
with the model — can trip the same wire.

### Options, scoped

| # | Option | Assessment |
|---|---|---|
| A | **Diversity constraint on `evidence_refs`** — cap refs per domain at mapping, or enforce post-hoc | Directly fixes the invariant. ⚠️ Post-hoc ref removal is **hidden curation** — it would drop evidence the mapper judged relevant with no receipt, breaching invariant #5. Would need a receipt trail. |
| B | **Prompt-level diversity instruction** — tell the mapper to avoid over-citing one domain | Cheap, no architecture change. ⚠️ Prompt-only, and `feedback_nf11_prompt_only_failed` says fragile behaviours need a *mechanical* rule. Unreliable alone; possibly fine as a supplement. |
| C | **Retrieval-side domain cap** — bound how many items one domain contributes to the pool | Fixes the cause rather than the symptom, and a thin pool cannot concentrate a mapped set. ⚠️ Interacts with the element-lane fetch budget (weighted round-robin, claim lane 2:1) and could starve legitimately dominant sources — on a legal claim, `legislation.gov.uk` *should* dominate. |
| D | **Stop showing tier to the mapper** | Removes the coupling entirely. **Rejected** — provenance weighting is deliberate and load-bearing for mapping quality. |
| E | **Make the invariant tier-aware** — allow higher concentration when the dominant domain is primary-tier | Arguably the *honest* reading: 47% from NEJM is not the same failure as 47% from one blog. ⚠️ Risks becoming a way to explain away real concentration. |

### What the next session must establish FIRST

1. **Which domain dominated** in the failing run, and whether its items were among
   the six re-tiered. Not captured — the run was not kept. One live record with
   `--verbose` settles it, and the answer decides between (C) and (E).
2. Whether other corpus claims sit near the 0.45 cap, i.e. how much slack the
   invariant currently has across the corpus.
3. Whether `top_domain_share` should be measured on the mapped set at all, or on
   the shown set — the mapped set is a *model output*, which makes the invariant
   a check on the LLM's citation behaviour rather than on retrieval.

Only then choose between A/B/C/E. Deciding now would be guessing.

### Options

1. **Hold the change.** The classification defect stays (NEJM remains commentary),
   but no invariant is breached. Zero risk, zero benefit.
2. **Understand the capping interaction first**, then fix classification and
   capping together as one piece of work. Correct, and larger than a list edit.
3. Ship classification + relax the cap. **Rejected**, see above.

Recommendation: **(2)**, as its own scoped session. The unit-level change is
sound and fully tested; what is missing is the interaction with source diversity,
and that deserves designing rather than patching under time pressure.

## 5. Verification plan

1. **Unit tests** — each added domain asserted primary/academic through
   `_classify_heuristic` *and* `_high_confidence_override`, plus negative tests
   pinning that the correctly-commentary domains stay put.
2. **Mutation** — remove the additions; the new tests must fail.
3. ~~**Replay bench `--all`** against existing cassettes~~ — **SUPERSEDED by §4a.**
   Run, and it FAILED: the change moves the shown evidence pool and therefore the
   mapping request body, so the cassettes no longer match. A **live re-record +
   re-gold** is required, and golden drift must be **inspected, not
   blanket-accepted** — per the F7 lesson that re-golding can silently delete a
   guard rather than merely update it.

   **Sequencing matters.** The mapping-prompt reframe is also awaiting a
   re-record. Recording both together would make the resulting golden drift
   unattributable — the same reason the two were separated for the run above.
   Record the classifier change first, inspect, gold; then the prompt change,
   separately. Two live runs, roughly $0.25 each.
4. **Re-run `TRU-577F-AB3F`** after deploy and diff the element states against
   the run reviewed today. §3.1 predicts element 02's tie may break; whichever
   way it lands, the outcome should be recorded rather than discovered later.

## 6. SOT updates owed

| Doc | Change |
|---|---|
| `audit/OPEN_WORK.md` | Register entry — this design + outcome |
| `.claude/CLAUDE.md` | `evidence_classifier.py` row cites *"93.7% accuracy"* |
| `audit/PIPELINE_QUALITY_DISCUSSION.md` | Source of the 93.7% figure (§ table, +51.6pp) |

**The 93.7% figure must NOT be restated as improved.** It was measured on a
specific labelled set during Track N. This change is not evaluated against that
set, so the honest note is that the figure predates it and the added domains were
not in scope — not a new number. Claiming an improvement we did not measure is
the exact failure this project keeps correcting.

## 7. Recommendation

Ship §4 behind the §5 gate. The defect is real, the lever is the one already
trusted for equivalent venues, and the largest blast-radius item (§3.1) moves
element states in the *correct* direction — a peer-reviewed society statement
should outweigh a consumer explainer.

Hold the platforming screenshots until after this deploys, so the Librarian
heatmap shown to strangers is not the one that files NEJM under commentary.
