# Assertion ≠ evidence — the recital rule + interested-party gate

**Date:** 2026-08-13 · **Status:** DESIGN (founder-commissioned after TRU-018F-44AA; build not started)
**Register:** `audit/OPEN_WORK.md` 2026-08-13 entry. Pipeline-work ban (`audit/OUTREACH.md`)
lifted for THIS item only, by founder, same day — outreach sends are held until the
acceptance test below passes.

---

## 1. The incident

Live check `TRU-018F-44AA` (founder, mobile, 2026-08-13 07:54 UTC), claim
**"Donald Trump stopped 6 wars"** — a false, loudly-made political claim, the exact
genre Tru8 exists to organise honestly. The record returned:

> *"Of 4 elements examined, retrieved evidence predominantly supports all 4."*

All four elements `supported`. Verified from the raw claim map (not the PDF), with a
corrected evidence join (`ev-xxxx` ref ids ↔ evidence rows):

| El | Element | Final refs (post coverage-recovery) | State |
|---|---|---|---|
| e1 | Trump was president during a specific period | 1S(w2) | supported |
| e2 | ≥6 wars ongoing during his presidency | 3S(w7), 0C — while its own `uncertainty` says *"evidence indicates at least 4 wars, but the claim specifies at least six"* | supported |
| e3 | Trump's actions directly led to cessation in six wars | 8S(w16) vs 4C(w4) | supported |
| e4 | Cessation was a direct result of his actions | 5S(w9) vs 3C(w3); **`llm_state: "disputed"`, overridden by `supports_dominant_2x` at the exact `>=` boundary (6 vs 3 at derivation time)** | supported |

The support side of e3/e4, itemised:

- `whitehouse.gov` — *"I've solved six wars in six months"* (the claim itself, from the claimant) — **primary, weight 3**
- `whitehouse.gov` — *"365 WINS IN 365 DAYS"* — **primary, weight 3**
- `davidson.house.gov` — a congressman's endorsement press release (2019) — **primary, weight 3**
- BBC/CBS — mapper reasoning verbatim: *"states Trump claimed to have 'settled six wars'"* — **supports, weight 2 each**
- CFR — reasoning verbatim: *"touted Trump's success in **purportedly** ending eight global conflicts"* — **supports**
- StateDept on X — *"THE PRESIDENT OF PEACE: 8 wars ended in 8 months"* — **supports**

Against: PolitiFact (**"Pants on Fire"**), PRIO's peace researcher, CFR, samf.substack —
all **commentary, weight 1 each**. The claimant's own press office outweighed the
professional refutation 3:1 per item.

## 2. The defect, named

Two distinct laundering channels, and their relative importance was established by
counterfactual, not intuition:

**(a) Recital-as-support — the load-bearing one.** Evidence that *reports the claim
being made* ("Trump claimed…", "touted", "purportedly") was mapped `supports` for the
claim's own content. A claim's virality thereby becomes its evidence base — for ANY
claim prominent enough to check. Three of the four graded outreach records show the
same signature (NHS A−: 6 of 7 supports derive from 1 original; dairy C−: one trial +
its echo; Scotland C+: press echo dominant). This is the pipeline's most systematic
distortion: **the well-publicised side of any dispute over-scores.**

**(b) Interested-party-as-primary.** The tier ladder encodes *proximity to the event*
and spends it as *reliability*. For claims whose subject IS the source — every
government/company/campaign claim about its own record — proximity inverts: the
closest source is the interested one. No interested-party concept exists anywhere in
the pipeline (grep-verified 2026-08-13; an earlier session's grep for this had
errored and its "nothing found" was unverified).

**Counterfactual that fixes the priority order** (recomputed from final refs):
removing ONLY the whitehouse.gov items leaves e3 at w10 vs w4 → still `supported`.
The flip to `disputed` requires the recital supports out too. So (a) is primary,
(b) is necessary but not sufficient. Both ship; neither alone is the fix.

A third observation, recorded for §10 not fixed here: PolitiFact carries
`is_factcheck` yet weighed 1 against the claimant's press release at 3. We will not
score outlets (invariant #6) — the gate resolves this from the other side, by
demoting interested directional refs to context rather than promoting anyone.

## 3. Rule 1 — RECITAL (assertion ≠ evidence)

**Principle:** evidence that a claim *was made* is evidence of the making, not of the
content. It maps `context` for elements asserting that content. Only independent
verification or corroboration is directional. A source that both recites AND
independently checks (BBC's "Here's what the record shows") is mapped on the
direction of its *verification*, not its recital.

Two halves, F1's shape exactly (prompt rule + mechanical rule, because NF-11:
fragile behaviour needs a mechanical rule, and prompt-only failed us once already).

### 3a. Prompt half (all three mapping prompts: `MAPPING_PROMPT`, `BATCH_MAPPING`, completion)

Add to the rule family that already holds SCOPE / SPECIFICITY (and MODALITY if the
held reframe ships):

```
- RECITAL CHECK: Evidence that REPORTS a claim being made — by the claim's
  subject or anyone else ("X claimed", "X says", "X announced", "touted",
  "purportedly", direct quotation of the claimant) — supports only the fact
  that the claim was made, NOT its content. For an element asserting the
  claim's content, map such evidence "context". If the source independently
  verifies or contradicts part of the claim, map THAT finding directionally —
  the direction comes from the verification, never from the recital. A
  claimant's own statement is never evidence for its own content, whatever
  the source's tier.
```

⚠️ Prompt text changes drift every cassette (request signatures are keys). See §8
for sequencing against the held reframe.

### 3b. Mechanical half — recital gate (`app/utils/recital_scope.py`, flag `ENABLE_RECITAL_SCOPE_GATE`)

Fourth/fifth member of the `_apply_scope_gates` family. Arms on every element
(no pin needed — recital is possible anywhere). Fires on a directional ref when
**attribution framing without verification framing** is present, read from **two
texts, either sufficient**:

1. the indexed evidence text (title + snippet/distilled), and
2. **the ref's own `reasoning` string** — the mapper is contractually required to
   write one sentence per ref, and in the incident every recital-support's reasoning
   carried the attribution verb (*"states Trump claimed"*, *"quotes President Trump
   saying"*, *"touted"*). The mapper's stated reason is the most honest mechanical
   signal we have: if the model itself says the evidence is a recital, the label
   must not say `supports`.

Detection, conservative by construction (absent signal → no fire, the safe
direction):

- **Attribution markers** (case-insensitive, subject-anchored where a subject is
  known): `claimed|claims|says|said|announced|touted|boasted|asserted|declared`,
  `quotes .{0,40}(saying|as saying)`, `according to`, `purportedly|reportedly`.
- **Verification vetoes** — any of these in the same text suppresses the fire:
  `confirmed|verified|corroborat|records show|data show|figures show|found that|
  contradicts|disputes|fact.?check`. A veto means the source did its own work; the
  prompt half owns the finer judgement there.
- Never fires on `context` refs (nothing to do) and never deletes — re-label to
  `context` + receipt, like every gate.

Receipt (invariant #5), keyed `recital_scope`:
```json
{"marker": "claimed", "found_in": "reasoning", "excerpt": "states Trump claimed to have 'settled six wars'"}
```

Known limit, stated rather than hidden: reasoning wording is model-shaped, not
contract-locked. If a future model stops writing attribution verbs, the gate goes
quiet — safe direction, but silent. Mitigation: the evidence-text half fires
independently, and the corpus assertion in §9 pins current behaviour.

## 4. Rule 2 — INTERESTED PARTY gate (`app/utils/interested_party.py`, flag `ENABLE_INTERESTED_PARTY_GATE`)

**Principle:** a source **controlled by the claim's subject** cannot be directional
on that claim's elements. Its statements remain visible — tier untouched
(classification stays honest: it IS an official statement; invariant #6), relationship
re-labelled `context`, receipt written.

### Arming — the subject set

Mirror `attach_claim_jurisdiction` exactly: a module-level, unit-tested
`attach_claim_subjects(claim, claim_map)` in `runner.py` writes
`claim_map["metadata"]["subjects"]` from the claim's `key_entities`
(types PERSON / ORG; free text, lower-cased). One writer, every mapping path, and a
reader-without-writer failure (the retrieve.py lesson) is impossible to miss because
the gate arms only when subjects are present.

### Firing — is this domain controlled by a subject?

Two prongs, either sufficient; both conservative:

1. **Name-in-domain:** a distinctive subject token (≥4 chars, stop-listed against
   common words) appears in the evidence's registrable domain —
   `trumpwhitehouse.archives.gov` ⊃ "trump", `trump.org`, most company domains for
   claims naming the company. Misses metonyms (a claim about Musk vs `tesla.com`);
   an absent match means no fire, which is the safe direction.
2. **Executive-comms map:** a curated map of *political communications organs* →
   the office/administration they speak for, entity-term-matched against the subject
   set:
   ```python
   EXECUTIVE_COMMS: {
     "whitehouse.gov":                {"country": "US", "terms": ["white house", "trump", "administration", "president"]},
     "trumpwhitehouse.archives.gov":  {...},
     "state.gov":                     {...},
     "number10.gov.uk" / "pm.gov.uk": {"country": "UK", "terms": [...]},
   }
   ```
   **Deliberately NOT in the map:** statistics offices and central banks
   (`ons.gov.uk`, `bls.gov` — statistically independent, and already governed by the
   jurisdiction gate's philosophy), and legislature member sites (`davidson.house.gov`
   — a congressman endorsing is aligned, not controlled; the recital rule handles
   endorsement-shaped recitals). Incomplete by construction, exactly as
   `NATIONAL_OFFICIAL_DOMAINS` is; absent domain → no fire.

**Symmetric, like every gate:** it scopes a subject's self-praise out of `supports`
and a subject's self-serving denial out of `challenges`. For "Company X polluted the
river", the company's denial becomes context with a receipt — visible, never counted
as refutation. A gate that only fired one way would be the sycophancy mechanism
invariant #7 forbids.

Receipt, keyed `interested_party`:
```json
{"subject_matched": "donald trump", "domain": "whitehouse.gov", "prong": "executive_comms"}
```

## 5. Family integration and gate order

Both gates join `_armed_scope_gates` / `_apply_scope_gates`. **Order is behaviour**
(the first gate to fire owns the ref; one gate, one receipt — the `break` invariant):

> temporal → jurisdiction → measure → **interested-party** → **recital**

The existing three stay byte-identically where they are — their receipts and the
corpus `temporal_scoped_refs` assertion are pinned at tolerance 0, and appending new
gates after them is what makes this purely additive (the measure-gate argument,
re-used). Interested-party precedes recital because a domain match is the less
ambiguous signal (the jurisdiction-before-measure argument, re-used): when the White
House recites its own claim, "interested party" is the honest reason to record.

## 6. Projected effect on the incident (to be confirmed live, not assumed)

| El | Today | IP gate takes | Recital takes | Remaining | Projected |
|---|---|---|---|---|---|
| e3 | 8S(w16) v 4C(w4) | whitehouse ×2 (w6) | CBS, BBC, PRIO-s, CFR-s, StateDept (w7) | davidson w3 v w4 | **disputed** |
| e4 | 5S(w9) v 3C(w3) | whitehouse ×1 (w3) | PRIO-s, CFR-s (w2) | CBS+BBC w4 v w3 | **disputed** (close split) |

e1/e2 are decompose + coverage-recovery defects, out of scope here (§10) — but with
e3/e4 disputed the orientation line can no longer read "supports all 4".

## 7. What this deliberately does NOT do

- **Does not touch retrieval.** The missing-rebuttal failure (Macfarlane, Gid M-K —
  Substack/small-site rebuttals never entering the pool; and all nine of this
  check's queries phrased in the claim's direction) is a separate, open retrieval
  item. This design fixes what the mapper does with the pool it gets.
- **Does not score outlets or adjust tiers.** Classification stays descriptive.
- **Does not delete anything.** Context + receipt, always.

## 8. Build order and bench sequencing

**Phase 1 — mechanical (both gates). No cassette drift:** gates post-process
responses; request signatures are untouched. Ships behind its two flags with unit
tests + a fixture built verbatim from TRU-018F-44AA's refs/reasoning strings.
Corpus goldens that change state gain dated in-file notes (golden drift here is
attributable to the gates by construction). Bench baseline stays 143/13/5-comparable.

**Phase 2 — prompt (recital rule text). Full cassette re-record.** This collides
with the held mapping-prompt reframe (same rule family, same prompts, founder's
change). **Founder decision required:** (a) ship reframe + recital rule as ONE
prompt change, one re-record, or (b) sequentially with a re-record each, per the
2026-08-11 protocol (record clean → change → re-record → require green on replay
before trusting it). (b) is attributable; (a) is cheaper. Recommend **(b)** —
prompt-change effects on this pipeline have surprised us every single time.

## 9a. Acceptance run 1 — 2026-08-13, check `6f88a77f` (PARTIAL, gap found and closed)

Fresh full-tier run of the exact claim on deploy `ade5672` (15p; a first attempt
was served the stale cached record because **the MCP client dropped
`max_age_hours=0` on truthiness** — `tools.py:146`, the client-side twin of the
server bug fixed 2026-08-05; fixed in `d39b65d`, PyPI 1.0.5 release owed).

- **e3 → `disputed`** ✅ (was supported). **e2 carries the recital gate's first
  production receipt** — CFR "Trump claims to have…" scoped from supports,
  `found_in: reasoning` — so the mechanism is proven live.
- **e4 → still `supported`** ❌ — and the trace showed exactly why: the
  whitehouse.gov "365 WINS" release re-entered e3/e4 as a weight-carrying
  support via the **coverage-recovery merge**, which — like the completion
  census — merged refs and re-derived state WITHOUT running any gate. A
  pre-existing bypass for ALL five gates, not just the new pair. Worse, the
  completion pass's fresh basis recompute **destroyed main-pass gate receipts**.
- **Closed in `d39b65d`:** both merge paths now gate merged refs before state
  re-derivation and MERGE receipts (`_merge_scope_receipts`); two seam tests
  pin it (canned-LLM completion + recovery). e4 also sat on the
  `supports_dominant_2x` `>=` boundary AGAIN (4 vs 2) — the §10 boundary fix
  would independently have flipped it.
- Orientation moved "supports all 4" → "3 supported; 1 with conflicting
  evidence". Not yet honest enough: acceptance re-run owed on the deploy
  carrying `d39b65d`.

## 9b. Acceptance run 2 — 2026-08-13, check `83120010` (PASS on the crux)

Full-tier fresh run on deploy `4bb326a` (15p). Orientation:
*"Of 4 elements examined, 3 predominantly supported; 1 challenged with none
supporting."* Decompose split the crux differently this run (e3 "took actions
that officially concluded" / e4 "conclusion directly attributable"):

- **e4 (attribution — the claim's actual crux): `disputed`, rule
  `all_challenges` — 0 supports, 3 challenges** (PolitiFact, PRIO, samf). The
  LLM said disputed and the mechanics agree. The element that carried the
  propaganda now reads challenged with none supporting.
- **e3: gates fired comprehensively, with receipts** — `interested_party`
  scoped whitehouse.gov ×2 **including recovery ref `ev-rec-e1_2_7f37dde9`,
  live proof the `d39b65d` merge-path fix works in production**; `recital_scope`
  scoped 4 (both press recitals, CFR, the StateDept tweet), all
  `found_in: reasoning`. Residual: e3 reads `supported` off ONE remaining BBC
  ref (`all_supports`, sole_domain bbc.com) — the known §10 thin-support
  weakness, surfaced to users by the existing thin-sourcing annotation.
- e1/e2 `supported` is honest: he was president, and ≥6 conflicts existed —
  facts both sides agree on; the dispute was never there.

**Verdict: the record is no longer sycophantic.** A reader now sees the causal
attribution challenged with zero support and receipts explaining why the White
House's own statements do not count. Remaining §10 items (all_supports floor,
`>=` boundary, decompose duplicate/wording drift) are real but secondary.
**Next per §9.4: re-run + re-grade the three outreach records before any send.**

## 9. Acceptance

1. **The incident is the fixture:** re-run "Donald Trump stopped 6 wars" live after
   Phase 1. e3 and e4 MUST NOT read `supported`; the orientation MUST NOT read
   "predominantly supports all 4". The record should read as a live dispute —
   which is what it is.
2. Unit: gate order, one-gate-one-receipt (`break`), symmetry (a self-serving
   *challenge* is scoped identically), veto suppression, no-subject/no-domain
   no-fire paths.
3. Corpus: new assertions pinning `interested_party` / `recital_scope` receipt
   counts on affected goldens (mutation-check them: assert they FAIL with the flags
   off, the TRU-C1A0-0005 lesson).
4. Regression: NHS (`11f54993`), Scotland (`7a6a4b91`), dairy (`c2bfbb8c`) re-run;
   expect echo-derived supports to scope down. Grades re-assessed before any send.
5. **Outreach unhold** only after 1 and 4.

## 10. Adjacent defects recorded here, fixed elsewhere (register: OPEN_WORK 2026-08-13)

- `supports_dominant_2x` uses `>=` and can overturn an LLM `disputed` on an exact
  boundary tie (e4 did). Change to `>`, and consider never overriding an LLM
  `disputed` downward at all.
- `uncertainty` is print-only: an element whose own note contradicts its state can
  still read `supported` (e2). Make it load-bearing or stop printing it.
- Decompose guards: presupposition elements (e1), near-duplicate pairs (e3≈e4)
  inflate the orientation denominator.
- Coverage recovery (5.1) re-derives state but leaves `tier_breakdown` /
  `relationship_breakdown` / `support_structure` stale — the signed audit trail
  disagrees with itself (e1: breakdown says 4 context/0 supports; state says 1S).
- Retrieval: claim-direction query phrasing + small-site rebuttal absence.

## 11. Rollback

`ENABLE_INTERESTED_PARTY_GATE=False` / `ENABLE_RECITAL_SCOPE_GATE=False`,
independently, like every gate. The prompt half rolls back only by revert +
re-record (prompts are not flagged) — one more reason Phase 1 ships first.
