# Decoupling Build Plan — Opinion & Blanket Claims (Phase 1) + Reactive Non-Sycophancy Floor (Phase 2)

**Date:** 2026-07-15
**Status:** DRAFT, amended 2026-07-16 (§15: v3 transcript findings, gate v4, Artefact-1 pool probe, resequencing, founder decision table) — awaiting founder design-review. Artefact-0 stands at v3 = 4/5, NOT green.
**Supersedes the sequencing of:** `audit/2026-07-14_non_sycophancy_invariant.md` (philosophy unchanged; that doc put the universal challenge lane FIRST — this plan inverts it: **decoupling leads, the non-sycophancy floor becomes a reactive backstop**).
**Origin:** prod check TRU-1928-D5F6 ("The Warner, Paramount proposed merger is a real danger to American democracy") returned only the empirical half; the evaluative point was dropped.

---

## 1. The change in one paragraph

Today, extraction discards opinion/evaluative claims (Rule 6, OBJECTIVE ONLY, `extract.py:138`), so a blanket statement is either gutted to whatever plain fact hides inside it or dropped entirely. This plan keeps the opinion, reframes it into an **affirmative normative claim** (a sibling of the shipped Rule 9 vaping precedent, `extract.py:152`), and **decomposes it into the empirical sub-questions ("routes") whose answers inform the judgement** — never adjudicating the judgement itself. The value predicate ("is a danger", "is a disaster") never becomes an element. A reframe receipt tells the reader we researched the grounds and the leap to the verdict is theirs.

---

## 2. The trigger — crisp and testable

A claim takes the decoupling path **iff its main predicate is an evaluative/normative judgement that rests on measurable grounds but is not itself directly measurable.**

Two-stage detection (extraction reframes; decompose routes):

- **Extraction (prompt rule + mechanical backstop):** detect an evaluative predicate and, instead of dropping, emit the AFFIRMATIVE normative claim with `claim_type` hint `normative_flagged`. Direction is never editorialised (same discipline as Rule 9: "Is vaping safe?" → "Vaping is safe", never "Vaping is not safe").
- **Decompose:** claims classified `normative_flagged` (`claim_map.py:16`, already a live enum) get the empirical-routes decomposition (§4).

**Positive triggers (MUST decouple):** "X is a danger to democracy", "the policy is a disaster", "Y is corrupt", "Z is the best/worst", "the situation is a genocide", "this is a gift to freedom". Evaluative predicate on a named subject.

**Negative triggers (MUST NOT decouple — normal empirical path):** "GDP grew 2% in Q3", "the merger was proposed", "inflation fell below 3%", "vaccines cause autism", "the 2020 election was stolen". These are grammatically flat *facts* (even when false). Flat-fact falsehoods are **not** this feature's job — they are Phase 2's (the reactive one-sidedness detector). This boundary is the single most important thing to get right: over-fire and we decouple plain facts into woolly sub-questions; under-fire and we miss the founder's cases.

**Codified-test criterion (D2, DECIDED 2026-07-16):** a predicate with a **codified, adjudicable test** — statute, regulator, court — is **empirical**, however evaluative it sounds: "anticompetitive", "illegal", "unconstitutional", "defamatory", "in breach of contract". The boundary is a *criterion applied per-claim by the classifier*, never a label list — the named labels exist only in the test battery as pinned edges. Coverage of unbounded vocabulary comes from the criterion plus graceful failure on misclassification (normative→empirical misread = today's shipped behaviour, never worse; empirical→normative misread = a woolly-but-honest decomposition + 2–3 cheap extra calls — neither failure mode produces a verdict or hides anything).

**Mechanical backstop (NF-11 compliance):** detection is a language task (prompt), but the *output* is mechanically checked — **no element may contain the raw evaluative predicate** (assert the value-word set does not appear in any element description), and the routes are surfaced in the reframe receipt so a bad decomposition is *visible*, never hidden. The keyword list (`extract.py:1340`) is extended as a tripwire, not the primary detector.

---

## 3. The value/verdict boundary (the non-arbitration guarantee)

The value predicate is researched *through* its routes, never as an element. Concretely:

- `normalised_claim` may retain the normative phrasing (for display + the receipt).
- `elements[]` are **all empirical** — each a measurable sub-question.
- Orientation stays mechanical (already true, `claim_map_analyzer.py:476-534`): the claim-level "state" is never "the opinion is true"; it is the honest roll-up of the empirical routes' states, and the reframe receipt explicitly hands the evaluative leap to the reader.

---

## 4. Route quality — proven on paper (the de-risk)

The risky 20% is choosing GOOD empirical routes. Below are hand-drafted routes for real cases, so route quality is judged before any code is wired. Each shows the **reframe**, the **routes (elements)**, the **receipt**, and the **failure mode** (bad routes to avoid).

### 4.1 "The Warner–Paramount merger is a real danger to American democracy"
- **Reframe (normative_flagged):** "The proposed Warner Bros–Paramount merger endangers American democracy."
- **Routes (elements, all empirical):**
  1. Does the merger increase concentration of US news/media ownership (market share, count of independent owners before/after)?
  2. Has the merger drawn antitrust scrutiny or regulatory challenge (DOJ/FTC filings, statements)?
  3. What news-audience share would the combined entity control?
  4. What is the documented record of comparable media consolidations' effects on editorial independence / local news?
- **Receipt:** "We researched the merger's scale, ownership concentration, antitrust exposure, and the record of comparable consolidations. Whether that amounts to 'a danger to democracy' is your judgement."
- **Failure mode (reject):** "Democracy is fragile" (not about the merger); "The merger is bad" (restates the value judgement); "Americans worry about media" (opinion-poll proxy dodging the substance).

### 4.2 "The situation in Gaza is a genocide" (hardest case — contested legal label)
- **Reframe (normative_flagged):** "The situation in Gaza constitutes genocide."
- **Routes (elements, all empirical):**
  1. Scale and sources of documented civilian casualties (named bodies, with tier).
  2. Is humanitarian aid access documented as restricted, and by whom reported?
  3. Are there documented on-record statements of intent by officials?
  4. Scale of documented population displacement.
  5. Status of the ICJ proceedings / provisional measures (primary: court filings/orders).
- **Receipt:** "We researched the documented casualties, aid access, official statements, displacement, and the status of legal proceedings. Whether these meet the legal definition of genocide is under adjudication and is yours to weigh — we do not rule on the label."
- **Why it matters:** the method holds on the sharpest case *and* stays non-arbitrating — the empirical substrate is anchorable in primary sources; the label stays the reader's leap. This is the concrete proof of the "grade structure, not stance" principle.

### 4.3 "The government's immigration policy is a disaster" (everyday opinion)
- **Reframe:** "The government's immigration policy is a disaster." (normative_flagged)
- **Routes:** (1) the policy's stated targets; (2) measured outcomes vs targets (backlog, cost, throughput numbers); (3) documented implementation problems; (4) comparative/expert assessments of outcomes.
- **Receipt:** "We researched the policy's targets, measured outcomes, and documented problems. Whether that amounts to 'a disaster' is your call."
- **Failure mode (reject):** "Immigration is controversial"; "The government is incompetent" (generalises off the policy).

### 4.4 Boundary case that must NOT trigger — "vaccines cause autism"
Flat empirical falsehood → normal decompose (empirical), NOT this path. Its one-sided-pool risk (echo chamber) is **Phase 2's** job, not decoupling's. Included here to lock the trigger boundary.

**Verdict on route quality — CORRECTED after independent verification (§12).** The routes above are empirical and on-subject, but that is NOT the same as safe. Independent verification (B1) found the deeper flaw: **these routes were chosen by a sympathetic author and every one enumerates a ground on which the claim could be TRUE** ("does it increase concentration?", "effects on editorial independence?") — none frames the disconfirming side ("what regulatory safeguards constrain it?", "is US media pluralism structurally resilient?"). Decomposing "X is a danger" into "the ways X could be a danger" **adopts the claim's own frame** — which reintroduces the exact confirmatory bias this whole effort exists to prevent, only moved upstream into route SELECTION. So §4 does NOT prove execution risk is bounded; it proves the routes can be empirical. The unproven, load-bearing question is whether route *selection* stays symmetric — and that is precisely what the Artefact-0 eval must test ADVERSARIALLY (§12).

---

## 5. File-level changes

### Phase 1 — decoupling (the value)
| # | Change | File | Size |
|---|--------|------|------|
| 1 | Extraction: reframe evaluative predicate → affirmative normative claim (extend Rule 6/9); do not drop | `extract.py` — **Rule 6/9 PROMPT is the fix site** (the drop is prompt-level; validation `~1339` only *de-weights* a 12-word hedge list that excludes "danger/disaster/genocide", so it is NOT where the drop happens) | Small |
| 2 | Decompose: add normative-specific guidance to `DECOMPOSITION_PROMPT` / `BATCH_DECOMPOSITION_PROMPT` — "decompose the normative claim into the empirical sub-questions whose answers inform the judgement; the value predicate is never an element" (`claim_map_analyzer.py:145-170, 253-`) | `claim_map_analyzer.py` (prompt) | **Medium — the hard part** |
| 3 | Reframe receipt surfaced as a no-verdict note (parity-locked `support_structure.py` ↔ `support-structure.ts`) | analyzer + frontend | Small |
| 4 | Mode gate: a decoupled single opinion claim offers a redirect/confirm step instead of silently running `focused` (`runner.py:845`) | `runner.py` + claim-selection UI | Small–Medium |
| 5 | Per-element source floor for decomposed opinion claims (guard against ranking-cap starvation, §6) | `retrieve.py` (~`1496`) / `relevance_scorer.py` (~`328`) | Small |

### Phase 2 — reactive non-sycophancy backstop (separable, ships later)
- One-sidedness detector reading existing `state_basis.supports_count/challenges_count` (`claim_map_analyzer.py:793`) in **shadow mode** (record only, zero behaviour change) → measure real blast radius over ~1 week → then reactive challenge re-query via the **existing** re-search / Stage 5.1 coverage-recovery seam, fired only on tripped pools.

**Untouched:** scoring, mapping-core counting, the empirical fast path, the frontend broadly.

---

## 6. Claims & sources — the limit answer

- **Claim count unchanged.** Decoupling adds *elements inside one claim*, not claims. Per-check claim cap untouched.
- **Elements within existing cap.** Opinion claims sit near `MAX_ELEMENTS_PER_CLAIM = 5` (`config.py:370`, enforced `claim_map_analyzer.py:1661`). No new element ceiling.
- **Retrieval fits existing caps.** 5 elements × 2 queries = 10 searches ≤ `max_sources_per_claim = 20` (`runner.py:52`; quick = 8, `:67`).
- **The real risk = starvation under the ranking caps.** Two per-claim caps apply: `MAX_EVIDENCE_FOR_RANKING` = **60** (`retrieve.py:1496`, `config.py:358`) and `LLM_RELEVANCE_MAX_EVIDENCE` = **50** (`relevance_scorer.py:328` — the "max 50 items" scorer cap). A 5-element opinion claim shares those slots across five routes rather than one or two. **The directional starvation risk is real** (each route can come back thin); the exact "~10 vs ~25/route" split is illustrative only — mapping assigns each item to its single best-fit element, it does not evenly divide N across elements. **Fix = a per-element floor for decomposed opinion claims (change 5), NOT a higher global cap.** A genuine change, flagged, not free.

---

## 7. Cost & latency

- **COGS rises on opinion/blanket claims only** (more elements → more searches); plain facts unchanged. Phase 2 spends only on tripped pools. The "flat cost on normal checks" property holds.
- **Latency:** opinion claims slower (more elements retrieved concurrently → sub-linear, single-digit seconds); plain facts unchanged. Phase 2 adds a second retrieval round only on trips.

---

## 8. Testing & benchmarking

- **New: opinion→routes eval (build this FIRST).** Input opinion → expected empirical routes, scored like the mapping sweeps (`mapping_budget_sweep.py` pattern). Runs on Gemini (`gemini-2.5-flash-lite`) — **not** blocked by the dead OpenAI key. Gate: routes must be empirical, on-subject, primary-anchorable across the §4 battery before any wiring.
- **Mechanical trigger tests:** the §2 positive/negative battery asserts correct fire/no-fire; a `no-evaluative-predicate-in-any-element` assertion locks the value/verdict boundary.
- **Replay-bench churn:** new claim shapes → new cassettes to record. Recording needs a networked env with a working Google key. The standing F7 re-gold debt must be cleared/side-stepped so the gate is real.
- **Parity test:** the new receipt note in `support_structure.py` ↔ `support-structure.ts`.

---

## 9. Risks & mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Bad decomposition = confidently researching the WRONG question** (worse than today's silent drop — looks authoritative) | High | Prove routes on paper (§4, done) + run the eval BEFORE wiring + receipt makes routes visible so a bad one is catchable |
| Trigger over/under-fires | Med | Crisp §2 definition + positive/negative test battery as a gate |
| Route selection is prompt work (drift, NF-11) | Med | Mechanical backstop on the OUTPUT (no evaluative predicate in elements; receipt exposes routes) — prevention is on output, detection is prompt |
| Ranking-cap starvation | Med | Per-element floor (change 5) |
| Bench recording blocked by API keys | Med | Decompose eval uses Gemini (unblocked); resolve Google key for full replay recording |

---

## 10. Open decisions for the founder

1. **Trigger boundary sign-off** — approve the §2 positive/negative battery (esp. that flat-fact falsehoods route to Phase 2, not here).
2. **Receipt wording** — the reframe note is user-facing and philosophically load-bearing (hands the verdict to the reader). Founder-lock it, like the F3 caveats.
3. **Gaza-class contested-label handling** — confirm the §4.2 approach (decompose to empirical substrate + "under adjudication; we do not rule on the label") is the intended stance.
4. **Sequence** — confirm decoupling (Phase 1) ships before the Phase 2 backstop, with Phase 2's detector running in shadow mode alongside from day one.

---

## 11. Build sequence (phased-build-loop) — SUPERSEDED 2026-07-16 by §15.4

Original sequence kept for the record; the amended sequence in §15.4 (a) inserts Artefact-1 (pool-balance probe) between the eval gate and Phase 1a as the evidence that decides B4, (b) moves change 4 to co-ship with Phase 1a (it depends on the reframe existing — it confirms the *decoupled* claim, so it cannot ship first as a standalone), and (c) names the F7 re-gold debt as an explicit parallel critical-path track.

1. **Artefact 0 (now):** opinion→routes eval + run it on the §4 battery. Eyeball routes. *Gate: routes good → proceed; woolly → stop and fix the prompt.*
2. **Phase 1a:** extraction reframe + trigger battery (changes 1, trigger tests).
3. **Phase 1b:** normative decompose guidance + no-evaluative-predicate lock (change 2).
4. **Phase 1c:** receipt note + parity (change 3) + per-element floor (change 5).
5. **Phase 1d:** mode-gate redirect (change 4).
6. **Phase 2:** detector in shadow mode → measure → reactive remediation.

Each phase: design → founder approval → build → independent verification with evidence → sign-off.

---

## 12. Independent verification findings (2026-07-15)

An independent adversarial pass verified every code claim and attacked the design. Result: **factual spine sound; two factual corrections applied; one core risk was OVERSTATED as de-risked and is not.**

**Factual corrections (applied above):**
- The "50-item ranking cap" conflated two constants: `MAX_EVIDENCE_FOR_RANKING` = 60 (`retrieve.py:1496`) and `LLM_RELEVANCE_MAX_EVIDENCE` = 50 (`relevance_scorer.py:328`). Directional starvation logic survives; arithmetic is illustrative. (§6 fixed.)
- Change 1's fix site is the Rule 6/9 **prompt**, not validation `~1339` (which only de-weights a hedge-word list that excludes "danger/disaster/genocide"). (§5 fixed.)
- All other code claims CONFIRMED: `normative_flagged` live-but-inert enum; no normative decompose guidance today; `MAX_ELEMENTS_PER_CLAIM=5`; `max_sources_per_claim=20/8`; focused-mode pause skip at `runner.py:845`; `supports_count/challenges_count` in state_basis; decompose primary path = Gemini `gemini-2.5-flash-lite` (OpenAI is fallback → eval unblocked *while `GOOGLE_AI_API_KEY` is set*); support_structure parity pair real.

**Design criticisms to carry INTO the design-review (not buried):**
- **B1 (most severe) — decomposition is itself confirmatory.** Route SELECTION adopts the claim's frame (all routes enumerate grounds the claim could be true). This is a NEW sycophancy surface that neither the original floor nor Phase 2's per-element symmetric retrieval addresses (Phase 2 balances each route's *pool*; it does not balance the *choice* of routes). **The fix must live in Phase 1:** the decomposition must select the routes a NEUTRAL analyst would ask — including disconfirming ones — and the Artefact-0 eval must test route *symmetry* adversarially, not just route empiricalness.
- **B2 — the "no evaluative predicate in any element" backstop is word-hygiene, not a route-quality gate.** The draft's own named failure modes pass it. It catches crude restatement only; it does NOT bound the B1 risk. Do not bill it as the mitigation for "researching the wrong question."
- **B3 — the trigger boundary is sorted by intuition, not by the "grammatically flat" criterion.** "The 2020 election was stolen" (NEGATIVE) and "Y is corrupt" (POSITIVE) share grammar; Rule 9 treats "safe" as empirical while §2 treats "danger" as evaluative — same risk-word family, opposite handling. Ambiguous real inputs ("the policy failed", "X is illegal", "the merger is anticompetitive") are not adjudicated by the boundary as written. Needs a sharper criterion + the battery as the arbiter.
- **B4 — this plan reverses a founder-LOCKED priority.** The non-sycophancy invariant "ranks ABOVE opinion-handling"; this plan leads with opinion-handling and demotes the floor to reactive/Phase-2/shadow-mode. Given B1 (decomposition adds a confirmatory surface), shipping Phase 1 alone could make the originating problem WORSE, not better. This needs explicit founder blessing, foregrounded — not open-decision-4.
- **B5 — Gaza route selection encodes the legal test.** Choosing "statements of intent" as a route imports the Genocide Convention's specific-intent element — i.e. the route SET is a theory of what the label means, even while disclaiming the label. Sharpest edge of open-decision 3.

**Verifier's overall verdict:** enter the design-review, but the founder must be told the design has an **unproven core risk (B1/B2), not a de-risked one**, and that it **re-orders a locked priority (B4)**. Artefact-0's real job is to prove route selection stays non-confirmatory — adversarially, not author-selected.

---

## 13. Artefact-0 results (2026-07-15) — RAN on real Gemini path

Script: `backend/scripts/decompose_symmetry_eval.py` (baseline prompt vs a symmetry-disciplined CANDIDATE prompt vs an adversarial red-team "what disconfirming dimension is missing?" critic). 8-claim battery, real `gemini-2.5-flash-lite`. Transcript: `backend/scripts/.decompose_symmetry_eval.json`.

**Result 1 — the trigger boundary largely WORKS.** The candidate classified all four evaluative claims `normative_flagged` (danger-to-democracy, is-a-genocide, is-a-disaster, is-a-triumph) and **correctly kept the boundary negatives empirical** — including the critical disinfo case "the 2020 election was stolen" (→ empirical, routes to Phase 2, NOT decoupling) and "UK inflation fell below 3%". The only genuine wobble is B3's legal-empirical edge: "the merger is anticompetitive" → normative_flagged (defensible but debatable). §2's boundary is in better shape than feared.

**Result 2 — B1 is CONFIRMED, and prompt-only symmetry FAILS.** The red-team flagged **every evaluative candidate `skewed_to_confirm`**, *despite* the candidate prompt explicitly ordering symmetric, disconfirming-inclusive route selection. Concrete misses it named (all real):
- Warner/Paramount: omitted the counterbalancing role of independent media, the actual historical impact of comparable mergers, efficiencies/investment.
- Gaza: the candidate **dropped `intent`/mens rea entirely** — which the *baseline* decomposition actually kept — plus proportionality, efforts to limit casualties, alternative explanations. (Note: this INVERTS verification B5 — the risk was importing the legal test; the actual failure was dropping its hardest element.)
- Immigration/trade-deal: omitted policy successes / cost-of-living / job-displacement — i.e. skewed toward the CLAIM's direction, symmetric across positive- and negative-valence opinions (so the skew is claim-confirmatory, NOT political — content-neutral, consistent with the origin diagnosis).

**Conclusion:** this is a *successful* Artefact-0 — it proved, before any build, that **route-selection symmetry cannot be achieved by prompt instruction alone** (exactly lesson NF-11). The de-risk failed in the good way: cheaply, on paper.

**Result 3 — the red-team critic over-fires and is not a drop-in gate.** It also flagged plain empirical facts (inflation, election-stolen) as "skewed" by demanding base-rates/confounders they don't need. So it is a useful *surfacing* tool for eyeballing, but as an automated gate it must be scoped to `normative_flagged` claims only and calibrated. (B2's warning applies to my own critic.)

### What this means for the build
Prompt-only symmetry is out. Route-selection symmetry needs a **mechanical second stage**, not an instruction. Candidate approaches to weigh at design-review:
- **(i) Completeness-critic pass in-pipeline** — decompose → adversarial critic names missing disconfirming dimensions → merge (mirrors the existing `_complete_unmapped_evidence` second-pass pattern). Adds one LLM call on normative claims only.
- **(ii) Bidirectional-by-construction routes** — phrase each dimension as inherently two-directional and lean on Phase 2's symmetric retrieval to balance each dimension's pool; residual risk = whole-dimension OMISSION (the Gaza `intent` drop), which (i) is designed to catch.
- **(iii) Don't drop structural elements** — a normative decomposition must not lose an element the empirical/definitional decomposition would have kept (Gaza intent). A mechanical union/floor check.

Recommended: **(i)+(iii)** — a scoped completeness-critic + a no-dropped-structural-element guard — is the mechanical backstop the prompt alone cannot be. This is now the Phase-1b design question, and it must clear the same eval before wiring.

---

## 14. Artefact-0 v2 results (2026-07-15) — mechanical second stage: MIXED, and the GATE itself is flawed

Script: `backend/scripts/decompose_symmetry_eval_v2.py` (candidate decompose → **scoped to normative_flagged only** → completeness-critic → revise → re-critic). Transcript: `.decompose_symmetry_eval_v2.json`.

**Scoping worked.** Empirical claims (election-stolen, inflation, policy-failed) were correctly skipped — no critic, fixing v1's over-fire.

**Flip result: only 1/5 normative claims flipped skewed→balanced, and one REGRESSED.**
- trade-deal "triumph": skewed → **balanced** ✅ (the one clean success).
- Warner/democracy, Gaza, immigration: revise **visibly improved** the routes (Gaza kept `intent` AND added human-shields / proportionality / cross-conflict comparison; immigration added successes/alternatives; trade-deal added job-displacement/distribution) — yet the critic **still returned skewed_to_confirm**.
- "anticompetitive": **balanced → skewed** — revise *dropped* the regulatory-safeguards element it should have kept. (Guarantee (iii) failing: revise mutated by replacement, not union.)

**The meta-finding — the red-team critic is NOT a valid pass/fail gate.** It is an insatiable goalpost-mover: on the origin case, v2 added the exact efficiency/investment dimensions the critic demanded, and it then named five *new* missing dimensions. The critic conflates **"not exhaustive"** with **"skewed to confirm"** — but a ≤5 dimension set can NEVER be exhaustive, so the critic will almost always say "skewed." Its verdict measures completeness, not directional balance. Therefore "critic flips to balanced" was the wrong green-light test, and my proposal of it was flawed.

**What is actually true (eyeball):** the revise stage genuinely makes routes more balanced and more neutrally phrased ("the net change in X considering both creation and displacement"). The DIRECTION of the fix is right; the MEASUREMENT was wrong, and revise needs a mechanical union guard so it cannot drop a good element.

### Corrected next test (proposed — needs founder approval before it becomes "the path")
1. **Replace the gate metric.** Stop asking "what's missing" (unbounded). Instead score **directional lean per dimension** — classify each final dimension as confirm-leaning / neutral / disconfirm-leaning (a simpler, lower-drift classification than open-ended critique). Success = the set is not confirm-dominated AND phrasing is neutral/bidirectional. This measures symmetry, not exhaustiveness.
2. **Make (iii) mechanical.** Revise must UNION (never drop) structural/disconfirming elements — enforced in code, not left to the LLM (fixes the anticompetitive regression).
3. Re-run the battery; green light = confirm-dominance eliminated across all normative cases, no element regressions.

**Status: path DIRECTION looks right, GATE was wrong; not yet green.** Continuity docs updated with this log; memory index update HELD pending founder approval that the corrected test (1–3) is the right path.

*(2026-07-16: the corrected test was founder-approved and ran as v3 — results and the gate's newly-found blind spots in §15.1; the gate itself is revised to v4 in §15.2.)*

---

## 15. Plan amendment (2026-07-16) — v3 results, gate v4, Artefact-1, resequencing

**Provenance:** independent review of the whole thread (problem → resources → solution), commissioned by the founder 2026-07-16. §1–§10 (philosophy, trigger, value/verdict boundary, file-level changes, caps, cost, risks) stand unchanged. What changes: the gate, one missing evidence step, the sequencing, and the decision framing.

### 15.1 Artefact-0 v3 results (ran 2026-07-15 18:54, transcript `.decompose_symmetry_eval_v3.json`) — 4/5, NOT green

Script: `backend/scripts/decompose_symmetry_eval_v3.py` (directional-lean gate + mechanical union guard, per the §14 corrected test, founder-approved).

**Wins:** origin case rebalanced (v1 3-confirm-dominated → final 2 confirm / 3 neutral, PASS); Gaza all-neutral PASS; immigration PASS after full replacement; trade-deal PASS via clean union + one explicit disconfirm addition (job-displacement). Scoping held again: all four boundary/ambiguous empirical claims (election-stolen, inflation, policy-failed) skipped correctly.

**Fail:** "anticompetitive" — still confirm-dominated (3 confirm / 2 disconfirm) after rebalance. Note this is also B3's boundary wobble: arguably a legal-*empirical* claim that should never enter this path (→ decision D2, §15.5).

**Four NEW findings from reading the transcript (not visible in the pass/fail counts):**

- **F-A — subject drift, a gate blind spot.** Immigration: the union kept ZERO v1 elements, so all five finals were LLM-fresh — and they wandered off *the government's policy* onto immigration generally ("crime in areas with high immigrant populations" is not about the policy, and is itself politically loaded; "perceived impact… on social cohesion" is the opinion-poll proxy §4.3 explicitly names as a failure mode). The lean gate passed it: **balance was achieved at the cost of on-subject-ness.** A gate that can pass a bad decomposition is not yet a gate.
- **F-B — the union guard fails unsafe.** `_lean`'s defensive default on a malformed classifier response is `["confirm"] * n`, which condemns *every* element to replacement — the exact opposite of the guard's stated promise ("a good element can never be dropped"). On classifier failure the default must PRESERVE (treat as neutral / keep all), never condemn. Related honesty note: the guard is mechanical in code, but its *input* is an LLM lean classification — a mislabelled-confirm good element can still be silently replaced. NF-11 re-enters through the side door; the guard should be described as "mechanical over an LLM signal", not "fully mechanical".
- **F-C — structural omission is unguarded.** Gaza v3 passes with five actus-reus routes and NO intent element — the exact drop the v1 red-team caught (§13), and the baseline decomposition had actually kept it. The union guard prevents drops *from v1*; it cannot add what v1 never had. B5 also persists in the passing set: the route set imports the Genocide Convention's test wholesale (see decision D4).
- **F-D — the one failure may be a trigger problem, not a rebalance problem.** If "anticompetitive"-class legal labels are classified empirical (D2), the v3 failure dissolves without touching the rebalance machinery.

### 15.2 Gate v4 (Artefact-0 v4 spec — fix the gate, then re-run)

Per normative claim, ALL must pass; boundary negatives must still skip:

1. **Directional balance** (unchanged from v3): final set not confirm-dominated (`confirm ≤ neutral + disconfirm`).
2. **On-subject anchoring** (NEW, answers F-A): the lean-classify call additionally returns `on_subject` per element (one call, two labels — same shape, no extra latency); the gate fails on any off-subject element; the union guard keeps only non-confirm AND on-subject elements; the rebalance prompt gains an explicit anchor line ("every dimension must be specifically about <subject>, never its general topic area").
3. **Structural coverage** (NEW, answers F-C — guarantee (iii) made concrete): run the BASELINE decomposition alongside (already free — v1/v2/v3 all did); any baseline element classified non-confirm + on-subject that is absent from the final set is a structural drop → fail. (This is exactly what would have caught the Gaza intent drop: the baseline kept it.) The open-ended completeness-critic stays as a non-gating eyeball column only — §14 proved it invalid as a pass/fail signal.
4. **Fail-safe defaults** (NEW, answers F-B): lean-classifier failure → preserve all elements (treat as neutral); rebalance failure → final = kept + v1 remainder; the pipeline stage must never emit an empty element set.

**Green light:** every in-scope normative claim passes 1–3 (with the battery adjusted per D2), zero off-subject elements, zero structural drops, empirical boundary cases untouched. Then — and only then — the same machinery is what Phase 1b wires in-pipeline (the eval artefact IS the design).

### 15.3 Artefact-1 — pool-balance probe (the evidence that decides B4)

**The plan's central unproven bet:** that neutrally-phrased, two-directional routes yield *balanced evidence pools* through the existing topical retrieval — with no challenge lane. This bet is what justifies demoting the founder-LOCKED "floor first" priority to reactive Phase 2 (verification B4). It is currently held on plausibility alone. Test it for the price of a few checks:

- **Script:** `backend/scripts/pool_balance_probe.py` (sibling of the eval scripts / `retrieval_capture_pull.py`). Read-only against the codebase; real provider calls.
- **Input:** 2–3 gate-v4-passing route sets from the transcript (origin case + one negative-valence + one positive-valence opinion), built as synthetic claim maps.
- **Run:** element-level retrieval → relevance scoring → mapping on the real path. **Contrast condition:** the same claims run raw (as today's pipeline would treat them) for comparison. Local first; `railway run` fallback if local search keys fail (LLM-locally is proven by the v1–v3 runs).
- **Read:** per-element `state_basis` supports/challenges/context counts + tier mix + which routes' pools came back one-sided. Qualitative, transcript-recorded, founder-eyeballed — a probe, not a bench.
- **Decision rule (this is D1):**
  - Pools come back plausibly two-sided → **B4 inversion accepted with evidence**; Phase 2 stays reactive; proceed to Phase 1a.
  - Pools come back systematically supports-only → **the floor cannot be reactive for this feature**; the 07-14 challenge lane is pulled into Phase 1 **scoped to normative claims only** (a middle path: ~2–5 extra searches per opinion claim, zero cost on empirical checks — far cheaper than the universal lane, honest to the locked priority).

### 15.4 Amended build sequence

0. **F7 re-gold — parallel track, explicit critical path.** It blocks bench-gating *generally*; both this feature's cassettes (§8) and the future red-team bench depend on it. Nothing bench-gated is real until it clears.
1. **Artefact-0 v4:** gate fixes (§15.2) + battery re-run (battery adjusted per D2). *Gate: green as defined.*
2. **Artefact-1:** pool-balance probe (§15.3). *Gate: D1 decided on its evidence.*
3. **Phase 1a:** extraction reframe + trigger battery (change 1) **+ change 4 co-ships** (single-opinion confirm/redirect step — CORRECTION to the 2026-07-16 review: change 4 depends on the reframe existing, since what it confirms is the *decoupled* claim; it is not independently front-shippable. It is promoted from "last, optional-feeling 1d" to "required at 1a", because for pure single-opinion inputs the confirm step + receipt is the only visibility the user gets).
4. **Phase 1b:** normative decompose guidance + the v4-proven mechanical symmetry stage wired in-pipeline (change 2 — still the hard part).
5. **Phase 1c:** reframe receipt + parity (change 3) + per-element floor (change 5; seams verified 2026-07-16: `_fair_select_evidence` round-robins per *claim* at `relevance_scorer.py:204`, ranking cap interleaves web/API at `retrieve.py:1496-1518` — neither is per-element today, so the floor is a genuine new mechanism, small but real).
6. **Phase 2:** per the D1 outcome — reactive backstop in shadow mode, OR the scoped challenge lane if Artefact-1 failed.

Each phase: design → founder approval → build → independent verification with evidence → sign-off (unchanged).

### 15.5 Founder decision table (supersedes §10's framing; nothing proceeds past Artefact-0 v4 without D1–D2)

| # | Decision | Recommendation | Blocks |
|---|----------|----------------|--------|
| **D1** | **B4 — the sequencing inversion.** ⚠ UPDATED 2026-07-16: Artefact-1 RAN + was independently verified, but its pre-registered pass/fail rule proved unsound (P4 — stance counts unreliable on dimension elements), so the result is a CONDITIONAL, not a pass: see §15.8 for the full framing. Option A (recommended) = reactive Phase 2 under three hard conditions (disconfirm-route-aware recovery + per-element floor + tripwire receipt on empty disconfirm routes); Option B = scoped challenge lane into Phase 1. | **A**, with the §15.8 conditions as commitments | Phase 1a |
| **D2** | **✅ DECIDED 2026-07-16 — the codified-test CRITERION** (not a label list; founder's coverage concern resolved by criterion form): a predicate with a codified, adjudicable test (statute, regulator, court) is **empirical**, however evaluative it sounds. Full wording + graceful-failure rationale in §2. Dissolves the v3 "anticompetitive" failure at the trigger; battery keeps the named cases as pinned edges and grows on prod misfires | — | Artefact-0 v4 |
| **D3** | **Receipt wording** — user-facing, philosophically load-bearing ("we researched the grounds; the judgement is yours"). | Draft at Phase 1c, founder-locked like the F3 caveats | Phase 1c ship |
| **D4** | **Gaza-class handling** — confirm §4.2, now with eyes open to B5's sharpest form: the structural-coverage guard (§15.2.3) will *deliberately* keep legal-framework elements (intent) as routes. That IS the "empirical substrate" position — routes may mirror the legal test's elements while the label stays the reader's. | Confirm, with the "under adjudication; we do not rule on the label" receipt line | Phase 1b |
| **D5** | **Change 4 form** — confirm-pause on decoupled single-opinion claims vs a passive note. | Confirm-pause (the origin failure was silence; a note can still be missed) | Phase 1a |
| **D6** | **In-pipeline cost** — +2–3 flash-lite calls (lean/on-subject classify + rebalance) on normative claims ONLY; empirical checks byte-identical. | Accept — this is the cheap end of the solution space and honours the "less cost-increasing" constraint | Phase 1b |

### 15.6 What this amendment does NOT change (see §15.7 for the v4 run record)

The philosophy (Version B, no-verdict, value predicate never an element), the trigger definition (§2), the file-level change list (§5), the caps analysis (§6), the risk table (§9), and the phased-build-loop discipline all stand. The 07-14 invariant remains the ranking authority: if D1's evidence goes against the inversion, the floor comes back into Phase 1 — scoped, not abandoned.

---

## 15.7 Artefact-0 v4 results (2026-07-16) — 🟢 GREEN, two consecutive runs

Script `backend/scripts/decompose_symmetry_eval_v4.py`, transcript `.decompose_symmetry_eval_v4.json` (second run's). Three revisions were needed to get an honest green — each a real finding, recorded so the in-pipeline stage (Phase 1b) inherits them:

- **rev 1 (as specced §15.2):** ran 2/4. Boundary 8/8 immediately — **D2's codified-test criterion works**: "anticompetitive" → empirical on every run since. But two classifier calibration gaps: comparator/base-rate dimensions flagged off-subject (the §4.1 route-4 shape the plan *wants*), and open measurements ("the impact of X on wages") labelled confirm.
- **rev 2 (calibration + two design changes):** contrast examples added to the classifier prompt (comparator = on-subject; drift-that-replaces-the-subject = off-subject; open measurement = neutral). Plus, driven by observed intra-run label flapping (the same element judged on-subject when added, off-subject at the final check): **sticky labels** (each element classified once, labels carried) and a **bounded retry loop** (≤3 rounds; only bad ADDITIONS are ever dropped — the union promise holds; off-subject or balance-breaking additions are filtered mechanically). Balance + on-subject thereby hold **by construction**, so the honest failure mode moves to *fill*. In-pipeline this loop is **"converge or disclose"** — a live check can never fail; an unconverged design surfaces in the reframe receipt. Ran 3/4 (Gaza balanced/covered but 4-of-5 slots filled).
- **rev 3 (breadth floor — JUDGEMENT CALL, flagged for design review):** the contract allows 1–5 elements, so a 4-dim balanced design beats a 5-dim skewed one; requiring exactly-target-size was stricter than the product. Floor set to **≥3 dimensions**, unfilled-vs-target reported as a warning, never a gate fail. **Founder should ratify or move this number.**

**Result: two consecutive GREEN runs — 4/4 normative (balance + fill + structural coverage; on-subject by construction) and 8/8 boundary each time.** Sample quality (run 3, eyeballed): Gaza = casualty scale vs baselines / IHL alignment of stated objectives / international legal investigations / aid access / historical context — balanced, on-subject, no verdict anywhere; origin case includes regulatory safeguards (disconfirm), historical precedents (comparator), and approval status alongside the concentration/influence grounds.

**Honesty notes:** (1) run-to-run variance is real — decompose runs at temperature, so element sets differ per run; the claim being made is "the machinery converges green", proven twice consecutively, not "output is deterministic". (2) Green here proves route-design symmetry ONLY — it says nothing about whether balanced routes retrieve balanced POOLS. That is Artefact-1's job (§15.3), which is the next step and the evidence for D1.

---

## 15.8 Artefact-1 results (2026-07-16) — RAN + INDEPENDENTLY VERIFIED; D1 goes to the founder as a CONDITIONAL

**What ran:** `backend/scripts/pool_balance_probe.py`, transcript `.pool_balance_probe.json`. Three claims × two conditions (v4 gate-green balanced routes vs the baseline shipped-shape decomposition) through the REAL retrieval → scoring → mapping path (verifier-confirmed genuine: real `EvidenceRetriever` with planner/augmentation/filters/API adapters, real content-hashed evidence ids `retrieve.py:1538`, real mechanical state derivation — `rule_applied` values prove it). Environment: local, Redis up, `RETRIEVE_CLAIM_TIMEOUT_S=240` (new env knob in `retrieve.py`, default 45 → prod byte-identical; uncommitted, founder keep/revert call), CLASSIFY omitted (all tiers unclassified — symmetric across conditions), coverage recovery / Stage 3.8 / factcheck not exercised. A first run at the prod 45s budget was DISCARDED as invalid (web lane starved on every condition — environment artefact, not signal).

**Results (claim-level supports/challenges/context):**

| Claim | Balanced | Baseline |
|---|---|---|
| Warner–Paramount "danger to democracy" | 13 / 4 / 8 | 15 / 12 / 10 |
| Immigration "disaster" | 5 / 1 / 13 | **16 / 0 / 9** |
| Trade deal "triumph" | 14 / 0 / 4 | 7 / 1 / 10 |

**Verified findings (independent adversarial verification, same day; author's read corrected in two places):**

- **P1 — Retrieval is NOT structurally challenge-blind (existence proof, CONFIRMED).** The "merger will be approved" element drew an 11-challenge pool through purely topical queries (the real merger was abandoned; the evidence said so); immigration economics came back a genuine close_split. **D1's hard-fail branch ("systematically supports-only") is NOT triggered.**
- **P2 — Balanced route DESIGN does not guarantee balanced route EVIDENCE (WEAKENED from the author's broader claim).** Author's "disconfirm routes under-populate" was an overread: 2 of 3 disconfirm routes populated well (origin safeguards 7 items; immigration human-rights 7 items); the trade-deal disconfirm route (0/0/1) is the one real instance, and the probe CANNOT attribute it — all six conditions hit the per-claim 20 cap with no per-item receipts recorded, so world-emptiness vs cap/scorer squeeze-out is undecidable. The cap and interleave are per-CLAIM, not per-element (`retrieve.py:1499-1522`) — the live alternative explanation, and exactly what the Phase 1c per-element floor (change 5) exists to fix.
- **P3 — The baseline shape IS the sycophancy machine, live (CONFIRMED, magnitude an upper bound).** Today's decomposition gave "the policy is a disaster" a 16/0 confirm-shaped landscape — its confirmatory chain ("has led to demonstrably negative consequences") fully supported. Deflations: 8 of the 16 sit on a trivially-true setup element; an unnamed policy inflates one-sidedness vs a real named policy that attracts defence coverage. Direction real; the balanced condition on the identical claim was not confirm-shaped (5/1/13).
- **P4 — Mapper stance semantics are UNSOUND on dimension-shaped elements (CONFIRMED, and worse than first read).** `MAPPING_PROMPT` defines elements as assertions (`claim_map_analyzer.py:172-228`); on neutral "the extent to which…" elements the mapper has no correct label and both coerces (trade: 14/0 across neutral measurements, all `supported` — semantically meaningless) and is INCONSISTENT (same phrasing went context-heavy on immigration, supports-heavy on trade). Corollary: claim-level stance totals are meaningless without lean-weighting — 5 "supports" on a disconfirm route (safeguards exist) count AGAINST the parent claim. **Structure-over-stance is the only coherent reading, and the §15.3 decision rule's own metric is therefore unsound for balanced route sets — the probe partially invalidated its own readout instrument. MUST feed Phase 1b design: either elements ship as assertion-shaped pairs, or MAPPING_PROMPT gains dimension semantics.**

**Recorded methodology caveats:** element-count confound (5 vs 3-4 per condition; claim-level totals comparable, per-element densities not); `claim_type` difference verified INERT (no behavioural branch anywhere in `app/`); n=3, single run — kills rate-shaped claims, fine for existence proofs; vague synthetic referents ("the new trade deal") materially threaten the trade-deal instance and inflate P3's magnitude; 240s budget means absolute pool richness doesn't transfer to prod at 45s — the balanced-vs-baseline CONTRAST does.

### D1 — the decision as the data actually frames it (FOUNDER DECIDES; §15.3's pre-registered rule cannot be applied as written because of P4)

- **Option A (recommended): reactive Phase 2, as HARD CONDITIONS, not a pass.** (i) coverage-recovery/re-search made **disconfirm-route-aware** — under-evidenced disconfirm routes become priority recovery targets (NEW machinery: today's recovery is claim-level; its ability to fill an empty disconfirm route is UNPROVEN — if the world lacks the material, no recovery conjures it); (ii) the per-element floor (Phase 1c change 5) — the cap squeeze-out P2 couldn't rule out; (iii) the one-sided-pool tripwire receipt (07-14 design §3c) fires on empty disconfirm routes, so an unfilled counterweight is always VISIBLE, never silent.
- **Option B: the scoped challenge lane enters Phase 1** (normative claims only — the 07-14 fallback). Costs land on the retrieve tail (the latency long pole); P1 removed its strongest justification, but 1-in-3 balanced pools coming back supports-only at n=3 is the honest argument that remains for it.

Author's recommendation: **A**, because P1 defeats the structural-blindness premise and A's three conditions convert every observed failure mode into either a fix (floor), a targeting rule (recovery), or a receipt (tripwire). But the verifier's framing stands: this is a MODIFIED decision rule over a founder-LOCKED priority — it needs your signature, not my inference.

**✅ D1 SIGNED BY FOUNDER 2026-07-16: OPTION A.** Reactive Phase 2 stands, with the three conditions as HARD COMMITMENTS of Phase 2/1c scope: (i) disconfirm-route-aware recovery (Phase 2 — machinery to be designed, its fill-capability honestly unproven); (ii) per-element source floor (Phase 1c change 5); (iii) one-sided-pool tripwire receipt fires on empty disconfirm routes (Phase 2, per 07-14 design §3c — an unfilled counterweight is always visible, never silent). Breadth-floor-3 and converge-or-disclose ratified in the same sign-off ("proceed as planned"). Build proceeds to Phase 1a.

---

## 16. PHASE 1A DESIGN (2026-07-16) — awaiting founder approval

**Scope:** change 1 (extraction reframe) + change 4 (single-opinion confirm step) + trigger battery. Session artefacts committed `8f50b5f`.

### 16.1 The sequencing hazard that reshapes 1a — FLAG-GATED, OFF until 1b

Shipping 1a alone would make the origin problem WORSE, not better: a retained opinion would flow into the SHIPPED decompose prompt — which P3 just proved is the 16/0 confirmation machine. Opinions would go from *silently dropped* to *confirmatorily researched*. Therefore the extraction reframe ships behind **`ENABLE_OPINION_REFRAME` (env, default OFF → extraction prompt byte-identical to today)** and is flipped on only when 1b (the eval-proven symmetric decompose stage) is live. Same operational pattern as `MAPPING_THINKING_BUDGET` / the planned challenge-lane flag. 1a can therefore be built, verified, and committed safely on trunk without waiting.

### 16.2 Change 1 — extraction reframe (`extract.py`, prompt + parser)

- **Prompt:** Rule 6 gains an EVALUATIVE CLAIMS branch (flag-gated text): when the input's MAIN predicate is an evaluative judgement on a named subject resting on measurable grounds ("is a danger to", "is a disaster", "is corrupt"), do NOT discard — emit it as a self-contained AFFIRMATIVE claim preserving the author's own direction and value predicate (sibling of Rule 9's affirmative discipline: never editorialise, never negate, positive and negative valence handled identically), marked `"type_hint": "normative"`. The D2 codified-test criterion is stated here too (anticompetitive/illegal/etc. → NOT hinted — plain claims). Still dropped: subjective flavour with no named subject or measurable grounds; Rule 9's advisory/preference exclusions unchanged. Incidental subjective adjectives inside factual claims are still cleaned — it is the main-predicate evaluative CLAIM that is retained.
- **Schema/parser:** claims gain optional `type_hint` (absent = today's behaviour). The check-4 subjective-word pass (`extract.py:~1339`) must be verified to only de-weight, never drop, hinted claims — pinned by unit test.
- **Bounded blast radius (the NF-11 story for a prompt change):** the hint's only effects are (a) the confirm-pause trigger and (b) a NON-BINDING hint to decompose — whose own D2-criterion classification (eval-proven, 8/8 boundary) remains the authority. A wrong hint mis-fires a pause at worst; it can never distort a landscape.

### 16.3 Change 4 — confirm step (`runner.py:845` area + claim-selection UI)

- **Trigger:** single-claim check AND `type_hint == "normative"` (and flag on) → pause in `waiting_for_selection` instead of running straight through focused mode. D5 decided: confirm-pause, not a passive note.
- **Two implementation candidates, decided at build after tracing every `entry_mode` branch:** (a) set `entry_mode="article"` for this case so the EXISTING pause + selection UI carry it (must verify the selection UI renders acceptably with one claim and no downstream focused-mode assumption breaks); (b) a focused-mode pause variant. Prefer (a) if the branch-trace is clean — zero new state machinery.
- **Copy** ("We kept your point as a researchable claim — confirm to research its empirical grounds, or rephrase") is FOUNDER-LOCKED before ship, same regime as the F3 caveats/D3 receipt.

### 16.4 Trigger battery + tests

- **Extraction eval** (new script, `decompose_symmetry_eval` pattern, real LLM): §2 battery + extraction-specific cases — the ORIGIN SHAPE (one sentence carrying fact + opinion → must yield BOTH claims), positive-valence twin ("gift to freedom" — preserved, never inverted), codified-test negatives (no hint), flat-fact negatives (unchanged), advisory questions (still dropped). Run with flag ON and OFF (OFF must be byte-identical behaviour).
- **Unit tests** (no LLM): parser round-trips `type_hint`; validation never drops a hinted claim; runner gate fires on exactly (1 claim ∧ hint ∧ flag) and nothing else.
- **Replay bench:** `--all` before commit. With the flag OFF in the bench env, extraction requests are byte-identical → zero cassette drift expected; any drift = a bug in the gating, loud. (Cassette re-record for flag-ON behaviour joins the F7 re-gold session.)

### 16.4a BUILD RECORD (2026-07-16, same session — §16 approved by founder)

- **Built:** `config.py` +`ENABLE_OPINION_REFRAME` (default False); `extract.py` `_RULE6_ANCHOR`/`_OPINION_REFRAME_RULE` + flag-gated insertion in `__init__` (anchor-drift fails LOUD, applies nothing) + `ExtractedClaim.type_hint` (schema is local-validation only — `response_format json_object`, so zero request drift) + both dict builders carry the hint; `runner.py` NEW pure `derive_entry_mode(claims)` (single normative-hinted claim → "article" = the confirm pause) + SSE `typeHint` (additive). Hint is transient phase-1 state (not a DB column) — acceptable: decompose re-classifies from text (authority), 1b needs no cross-pause hint.
- **Unit tests:** `tests/unit/pipeline/test_opinion_reframe.py` — 11/11 (flag OFF byte-identity incl. remove-rule-reproduces-OFF; insert-once-at-anchor; format-safety; hint round-trip; validation de-weights-never-drops a hinted claim; entry-gate truth table).
- **Trigger battery:** `scripts/extraction_reframe_eval.py` (real Gemini path) — **🟢 GREEN, 8/8 gating + flag-off control**: all four opinions hinted with direction preserved verbatim (both valences); compound two-assertion case yields fact PLAIN + opinion HINTED (the origin fix demonstrated); election-stolen/plain-fact/anticompetitive all plain (D2 holds at extraction); **flag-off origin control = today's behaviour reproduced (opinion vanishes, no hint)**.
- **NEW pre-existing defect found (out of 1a scope, flag-independent, VERIFIED with flag off): F-EXTRACT-FALLBACK** — when the LLM correctly returns 0 claims (e.g. advisory question "What should I invest in?"), `extract_claims` treats success-with-0-claims as failure and cascades to the rule-based fallback, which junk-extracts the raw sentence. Happens in prod today. Candidate fix (own slice, NOT 1a): treat LLM 0-claims as a valid "no verifiable claim" outcome — needs care (0-claims may also be a spurious LLM miss that the cascade currently rescues). Tabled for founder.

### 16.5 Verification & sign-off — INDEPENDENT VERIFY DONE (2026-07-16): SOUND-WITH-NITS, all required fixes APPLIED

**Verifier verdict: SOUND-WITH-NITS** — flag-off byte-identity PROVEN on both LLM request paths (no schema transmission; signed-manifest fingerprint unaffected); entry gate a faithful semantic replacement (incl. len==0 edge); 1-claim article path safe end-to-end (ClaimSelector short-circuits ≤1; PATCH accepts a single selection; phase2 needs no hint; selection UI renders 1 claim with correct pluralisation; ledger semantics unchanged — debit at submission both modes); agent API auto-selects on pause so a flag-ON agent submission can never hang.

**Defect D-1 (found + FIXED same session, both halves, pinned by tests):** extraction cache was keyed only on content+model → a flag flip served the OTHER prompt's claims for up to 6h (hinted claims firing the pause AFTER rollback; stale unhinted extractions after flip-ON). Fix: (i) `derive_entry_mode`'s hint branch also requires `ENABLE_OPINION_REFRAME` (rollback = today's behaviour unconditionally); (ii) extraction cache identity gains a `+reframe` fingerprint when the flag is on (flag off = key untouched). Tests 13/13 (+2: flag-off-hint→focused; cache-key fingerprint) + 110 adjacent runner/extract tests pass.

**Other verifier fixes applied:** replay bench RAN post-snapshot — **54 ok / 1 warn / 5 fail = byte-identical to the documented pre-existing F7 baseline (same 2/47 + 6/122 miss counts), zero new drift**; overstated "never drops" wording corrected in the build record + test docstring (only CHECK 4 never drops — checks 1-3 can still drop/strip a hinted procedural-negative shape like "X failed to…" → **1b battery case**); NIT-5 closed with a RECORDED flag-off advisory control in the eval transcript (junk-extraction reproduced flag-off — F-EXTRACT-FALLBACK evidence now on file).

**Carried into Phase 1b / confirm-copy design (non-blocking for 1a, flag off):** NIT-3 the confirm step currently renders the GENERIC selection screen — the founder-locked tailored copy is unbuilt and nothing consumes `typeHint` in the UI yet (founder eyeball sharpened this: a single-claim confirm should not wear the "select up to 3" apparatus — greyed card + "Investigate 0 claims"; proper single-claim confirm layout wanted); NIT-4 `typeHint` reaches the UI only via live SSE (lost on page refresh — needs persistence or re-derivation when the tailored copy ships); NIT-6 email/PDF label a single-opinion check "Article mode" (cosmetic); NIT-2 non-string `type_hint` from the LLM fails pydantic → fallback cascade (theoretical).

**Founder eyeball record (2026-07-16, 4 live local checks):** gate perfect (5810E18F + 4E16197E hinted→paused; EDAD11AE + 41DE5B86 plain→focused; DB-verified); D2 held at both layers; the two opinion checks are **P3 live** — immigration decomposed to the confirmatory chain incl. the VALUE PREDICATE AS AN ELEMENT ("severe enough to be characterised as a 'disaster'", +9/−1 supported) → the standing justification for flag-off-until-1b, and the checks become 1b test fixtures. **NEW pre-existing finding (own slice, logged): F-MAP-CENTROID** — Map view draws each source once at the centroid of its element columns (`EvidenceMap.tsx:251-264`); an element whose refs are 100% shared renders as an EMPTY column (immigration el-3: 11 refs, all shared → blank column read as "unevidenced"). Not a data bug; a visual-honesty defect, acute under chain-shaped decompositions. Recommended fix: explicit "N sources (shared with …)" marker in pulled-away columns.

**✅ PHASE 1A CLOSED (2026-07-16): founder eyeball done (4 live checks, record above) → SIGNED OFF → COMMITTED `585818d`, pushed (prod-inert: flag OFF, prod CSP byte-identical).** Phase 1b designed in §17 (same session, founder said proceed); the flag flips in prod only after 1b ships.

---

## 17. PHASE 1B DESIGN (2026-07-16) — awaiting founder approval

**Scope:** plan §5 change 2 + §15.4 step 4 — the v4-proven symmetry stage IN-PIPELINE, the P4 mapping-semantics resolution, the tailored single-claim confirm UI, and the carried 1a nits. Out of scope (later phases, unchanged): receipt rendering + parity + per-element floor (1c), disconfirm-route-aware recovery + tripwire (Phase 2), F-MAP-CENTROID, F-EXTRACT-FALLBACK.

### 17.1 Trigger + seam

One hook, after `decompose_claims_batch` (`runner.py:1287`): for each claim whose fresh claim_map has `claim_type == normative_flagged` AND `settings.ENABLE_OPINION_REFRAME` — run the symmetry stage, which REBUILDS that claim_map's elements before factcheck/retrieve read them. Flag off → no new code path; flag on + empirical claim → byte-identical. **Free baseline:** the shipped decompose has already run (it IS what classified the claim), so its elements are the structural-coverage baseline at zero extra cost — the v4 eval's second decompose call disappears in-pipeline.

### 17.2 P4 RESOLVED — recommendation: ASSERTION-SHAPED ELEMENTS (option C)

The stage's final elements are **testable assertions, not open questions** — e.g. not "the impact of the deal on employment" but "The trade deal increased employment for British workers" [claim-direction] alongside "The trade deal displaced jobs in exposed sectors" [counter-direction]. Balance is enforced **across assertion directions** (claim-direction count ≤ counter + neutral — the v4 gate arithmetic applied to direction). Why C over the alternatives:

- **MAPPING_PROMPT untouched** — the single biggest blast-radius risk in 1b is removed. The mapper was built for assertions; supports/challenges become natively meaningful again, dissolving P4's coercion instead of patching it. States, tier weighting, census discipline: all unchanged.
- Option A (paired pro/con elements per dimension) doubles element count against the 5-cap; option B (dimension semantics taught to the mapper) rewrites the most safety-critical prompt in the pipeline and re-opens the F7-style cassette surface.
- The value predicate STILL never appears in any element (mechanical word-check retained from §2).

**The one consequence needing design care — direction-aware roll-up:** with mixed-direction assertions, a *counter*-assertion in state `supported` is evidence AGAINST the parent claim. `derive_orientation`'s current prose ("evidence predominantly supports all N elements") would mislead. Fix (mechanical, 46163a2 precedent): each element's `basis` gains `direction: claim|counter|neutral` (persisted from the stage's sticky labels — receipt-grade); `derive_orientation` gets a normative branch that counts BY DIRECTION and renders direction-aware prose ("the claim's grounds drew support; so did the countervailing factors" style — exact wording FOUNDER-LOCKED, D-1b-2 below). State vocabulary untouched; no LLM anywhere in the roll-up.

### 17.3 The stage (mechanical; the committed v4 eval is the reference implementation)

Per normative claim: (1) normative-branch decompose call (the eval's CANDIDATE prompt + D2 criterion, assertion-shaped output per §17.2); (2) ONE combined assess call labels candidate + baseline elements (direction + on_subject; sticky — each element labelled once; fail-safe = preserve, never condemn); (3) union guard keeps non-claim-direction-dominated, on-subject candidates + uncovered baseline structural elements (coverage call); (4) bounded rebalance ≤3 rounds, subject-anchored, only bad ADDITIONS ever dropped; (5) cap 5, breadth floor 3, never empty. **Converge-or-disclose:** non-convergence NEVER fails the check — `claim_map.metadata.symmetry = {balanced, rounds, unfilled_slots, directions}` is persisted receipt-grade; 1c renders it in the reframe receipt (1b stores, 1c shows).

**Cost honesty (vs D6's accepted "+2–3 calls"):** typical path = 4 flash-lite calls per NORMATIVE claim (decompose + assess + coverage + 1 rebalance); worst case with retries ≈ 8. Above the D6 envelope — flagged, not smuggled. Empirical claims: zero. Latency: ~3–8s added to the decompose stage on opinion claims only. **D-1b-1: founder accepts the revised envelope (or caps retries at 1).**

### 17.4 Confirm-step UI (carried NIT-3/NIT-4)

Single-claim confirm layout replaces the generic selection apparatus when `status == waiting_for_selection AND claims.length == 1` — **the length IS the signal** (a 1-claim pause only exists via the hint), which solves NIT-4's page-refresh loss with zero persistence work. Layout: the claim quoted as a card + primary "Research this claim" + secondary "Rephrase instead" (back to submit). Copy draft for founder-lock (D-1b-2): *"We've kept your point as a researchable claim. We'll research its empirical grounds — the judgement stays yours."*

### 17.5 Testing & gates

Unit: stage mechanics, fail-safes, direction metadata, orientation normative branch, value-predicate word-lock, "X failed to…" hinted-shape battery case (carried). Eval: the v4 battery re-run THROUGH the pipeline stage function (adapt `decompose_symmetry_eval_v4.py` to call it — the gate and the product can no longer drift apart). Fixtures: re-run 4E16197E + 5810E18F locally flag-on → landscapes must show direction-mixed assertions, no value-predicate element, honest roll-up prose. Bench: flag OFF = zero cassette drift (same guarantee as 1a, same test pattern). Web tests: confirm layout renders on 1-claim pause, generic selection on ≥2.

### 17.6 Founder decisions (block build)

| # | Decision | Recommendation |
|---|---|---|
| D-1b-1 | Cost envelope: typical 4 / worst ~8 flash-lite calls per normative claim (vs D6's 2–3) | Accept (normative-only, seconds, flash-lite pennies); else cap retries at 1 |
| D-1b-2 | Founder-locked wording: direction-aware orientation prose + confirm-step copy | Approve drafts at build, lock before ship (F3-caveat regime) |
| D-1b-3 | P4 = option C (assertion-shaped elements; MAPPING_PROMPT untouched; direction-aware roll-up) | **C** — smallest blast radius, dissolves rather than patches |

Re-entry protocol + full history: `audit/OPEN_WORK.md` 2026-07-16 handoff block.

**✅ DECISIONS (founder, 2026-07-16, after a full cost/efficiency assessment — see §18): D-1b-1 cost ACCEPTED (~0.15–0.3p per opinion check, opinion-only; single-claim checks are the ~3p cheap end); D-1b-3 = OPTION C (assertion-shaped elements, MAPPING_PROMPT untouched); D-1b-2 wordings drafted at build, FOUNDER-LOCKED before ship.**

**⛔ BUILD HALTED 2026-07-16 — CRITICAL FINDING, see §19. Option C as built manufactures FALSE BALANCE (reverse sycophancy). Direction-forcing to be scrapped; the invariant needs a false-balance clause. Resumes tomorrow after founder consideration. Slice-1 module + eval built + UNCOMMITTED; nothing wired.**

## 18. Cost/efficiency assessment (2026-07-16) — grounds the 1b cost consent

Founder challenged the cost basis. Full LLM-call inventory (Explore agent, code-grounded) + real telemetry from 4 completed local checks (`Check.cost_telemetry` JSONB, `cost_constants.py`):
- **Measured single-claim check ≈ 1.25p LLM** (reconciled exactly against stored tokens). **Mapping stage (gemini-2.5-flash) = ~64% of it** — the top efficiency lever; thinking already off in prod (July). Distiller = most tokens but flash-lite so cheap.
- **All-in single-claim ≈ 2.5–3p** (adds ~0.4p uncounted OpenAI stages + ~0.5–1.5p *estimated* search).
- **CORRECTION on record:** the earlier "10–15p/check" was wrong for single-claim checks; it plausibly applies only to FULL 5-claim article checks (per-claim stages ×5) — unmeasured.
- **Instrumentation gap (flagged in code since June, never finished):** web-search cost + 3 OpenAI stages (query-planning/relevance/article-classification) not in telemetry. Honest next efficiency step = finish instrumentation, THEN test the mapping-model lever (flash-lite for mapping). Logged as **project_cost_efficiency (owed)**; NOT blocking 1b.
- 1b cost fits comfortably: opinion checks are single-claim (~3p) and 1b adds ~0.15–0.3p.

---

## 19. ⛔ CRITICAL FINDING — FALSE BALANCE (2026-07-16) — build halted, resumes tomorrow

**The single most important finding in this whole thread. Founder-flagged, live-eval-proven. Read this before touching Phase 1b again.**

### What happened
The in-pipeline symmetry stage (slice 1) was built (option C, assertion-shaped) and run on the real Gemini path via `scripts/opinion_symmetry_eval.py` (transcript `.opinion_symmetry_eval.json`). It caught, BEFORE any wiring, that the stage **over-corrects into the OPPOSITE bias**:

| Claim | claim-side | counter-side | neutral |
|---|---|---|---|
| Immigration "disaster" | 0 | 5 | 0 |
| Warner "danger to democracy" | 0 | 4 | 1 |
| Gaza "genocide" | 0 | 4 | 1 |
| Trade "triumph" | 2 | 3 | 0 |

"The immigration policy is a disaster" decomposed into **five assertions all arguing it is NOT a disaster.** Worst of all, **"The situation in Gaza is a genocide" produced counter-assertions that read as denialist advocacy** ("Hamas intentionally targeted civilian infrastructure", "civilian deaths comparable to or lower than other conflicts", "Israel took measures to minimise casualties"). On the gravest, best-evidenced claim in the battery, the stage manufactured a one-sided brief AGAINST the claim.

### Founder's line (the values decision to be locked)
> There IS a genocide in Gaza. Manufacturing a "balanced" denialist frame is **platforming bullshit**. On a well-evidenced grave matter, forced symmetry is not neutrality — it is FALSE BALANCE, and false balance is a distortion just as much as sycophancy.

**The enemy is DISTORTION IN EITHER DIRECTION — confirmation AND false balance.** On a well-evidenced claim the honest landscape SHOULD look one-sided; that is correct, not a bug to be balanced away.

### Root cause (diagnosed)
Balance was put in the **WRONG LAYER.** Option C as built forces the ROUTES into a for/against split ("generate a counter for every claim assertion"), which *structurally requires* manufacturing the opposing framing regardless of evidence. This is exactly what the original non-sycophancy design **already rejected** (`2026-07-14_non_sycophancy_discussion.md` §4.6: "manufacturing a counter-opinion the user never expressed is itself an editorial act"). The honest design puts symmetry in **retrieval** (search both sides — D1 Option A challenge/recovery machinery) and honesty in **mapping** (mechanical tier-weighted counting of the REAL evidence). Decomposition's job is to pick the RIGHT neutral empirical grounds, never to pre-stack them for-and-against.

### Redesign direction (FOR FOUNDER CONSIDERATION — not yet decided)
1. **Scrap direction-forcing.** Normative decomposition = the NEUTRAL empirical/legal grounds of the question (the §4.2 Gaza routes: documented casualties, statements of intent, aid restriction, displacement, ICJ status) — measurable sub-questions, NOT for/against assertions. No `_claim_dominated` / counter-inclusion mechanism.
2. **Balance/honesty come from the D1 Option A machinery already signed off** — symmetric retrieval + honest mechanical mapping + tier weighting (primary sources outweigh commentary) + the one-sided-pool tripwire. On a true grave claim, the grounds come back heavily supported by authoritative primary sources and the landscape reflects that WITHOUT a verdict stamp.
3. **Sharpen the invariant (proposed Critical-Invariant refinement, founder-word-lock):** the pipeline must never manufacture doubt or support the evidence does not warrant; balance lives in the EVIDENCE, never in forced route symmetry. False balance is forbidden equally with sycophancy.
4. **Open question for tomorrow:** how "neutral grounds + honest weighting" reconciles with the no-verdict lock on charged claims — the landscape may point unmistakably one way; confirm that is the intended, correct behaviour (it is honesty, not adjudication).

### Build state at halt (nothing committed, nothing wired)
- `app/pipeline/opinion_symmetry.py` — slice-1 module. Plumbing sound (fail-safe, never-empty, structural coverage, metadata.symmetry); **the direction-forcing CORE must be reworked** per redesign #1. UNCOMMITTED.
- `tests/unit/pipeline/test_opinion_symmetry.py` — 7 pass; will need rewriting for the neutral-grounds design. UNCOMMITTED.
- `scripts/opinion_symmetry_eval.py` + `.opinion_symmetry_eval.json` — the eval that caught this; keep as the regression witness. UNCOMMITTED.
- Gate bugs noted (secondary): `_claim_dominated` is one-sided (passes all-counter sets); value-word check false-flags assertions that merely negate the label. Both moot if direction-forcing is scrapped.
- 1a (shipped `585818d`, flag OFF) is UNAFFECTED and safe.

### Resume tomorrow
Founder considers the redesign direction + the invariant refinement → align → rework the stage around neutral grounds → re-run the eval (Gaza must NOT produce a denialist brief; a true grave claim's grounds must come back honestly, not artificially split) → then wiring. Method: phased-build-loop.

---

## 20. §19 DIAGNOSIS CORRECTED + FOUNDER SCOPE RULING — MINIMAL 1B (2026-07-17)

### 20.1 The discriminating eval (ran 2026-07-17, real Gemini path)

§19 said "direction-forcing is the root cause". That didn't fit the evidence — direction-forcing was already in v4 (green twice) and produced Artefact-1's balanced pools. What changed in option C was the output SHAPE: assertions instead of open questions. So a single-variable test was run: `scripts/opinion_symmetry_eval_questions.py` monkeypatches ONLY the four prompts to question-shape; the union guard, rebalance loop, `_claim_dominated`, fail-safes are byte-identical to the halted module. Transcript `.opinion_symmetry_eval_questions.json`.

**Result — the Gaza denialist brief is GONE with the same direction machinery:**

| Claim | Assertion arm (§19) | Question arm |
|---|---|---|
| Gaza "genocide" | 0 claim / 4 counter / 1 neutral — denialist brief | 2 / 2 / 1 — §4.2's intended routes (ICJ accusations + evidence cited; stated objectives vs legal thresholds of genocide) |
| Immigration "disaster" | 0 / 5 / 0 | 0 / 2 / 3 |
| Warner "danger" | 0 / 4 / 1 | 1 / 1 / 3 |
| Trade "triumph" | 2 / 3 / 0 | 2 / 2 / 1 |

**Corrected diagnosis:** the primary toxin was ASSERTION SHAPE — a counter-direction *question* ("what measures, if any, were taken to minimise civilian harm?") invites evidence either way; a counter-direction *assertion* ("Israel took measures to minimise casualties") is a manufactured talking point handed to a mapper that only seeks support. Option C's shape choice (the P4 assertion fork) manufactured the advocacy; §19 diagnosed one layer too high. The P4 fork not taken — dimension semantics in MAPPING_PROMPT — is the live one.

### 20.2 What the shape fix does NOT solve (three surviving findings)

1. **Whataboutism enters via the forced counter-slot.** Gaza's question arm still drew "documented instances of Hamas targeting Israeli civilians / using human shields" — literally about Gaza (on_subject passes) but a deflection from the question asked. Both arms produced it; both times through the counter-quota. Remove the forcing → the inviting mechanism goes. No mechanical detector yet; the eval battery watches for recurrence.
2. **The claim side gets zeroed.** Immigration: 0 claim / 2 counter / 3 neutral — no route for backlog/cost/missed-targets (§4.3's own grounds). Cause is `opinion_symmetry.py:250`: the union guard keeps only `d != "claim"` — it doesn't balance claim-direction elements, it DELETES them, and they can re-enter only while balance already holds (line 290). The stage is structurally incapable of a claim-dominant set even when honest. False balance surviving in question form.
3. **`_claim_dominated` is one-directional — the old invariant compiled into code.** It scored Gaza's 0/4/1 denialist brief `balanced=True`. Built to catch sycophancy only, it enforces counter-skew and reports it as success. The §19 finding was caught by founder eyes, not machinery. Strongest evidence for the false-balance clause: any balance gate must fail TWO-SIDED.

Also confirmed: final element sets are SHAPE-MIXED (baseline assertions carried in beside generated questions — e.g. "The proposed merger will be approved" inside a question set), so the P4 mapper fix is required regardless of decompose shape.

### 20.3 Founder ruling (2026-07-17) — the standard

1. **Control the mechanical; disclose the judgement.** LLM judgement (route selection, lean) is not reliably controllable — v1 proved prompt-only fails, option C proved mechanical forcing overshoots. Mechanical guards and retrieval/mapping symmetry are controlled; LLM lean is disclosed (receipt), never edited.
2. **Less change, at this stage, is better.** Pre-release, shared-path pipeline logic is NOT touched. Everything ships flag-gated to hinted claims only; flag off = byte-identical behaviour everywhere. Deeper machinery queues post-release.
3. **Evidence selection is the company's signature.** No silent editing of research questions; any lean is shown, never corrected in secret, never faked in either direction.

### 20.4 Minimal 1b — the locked scope

**Build (all gated to `ENABLE_OPINION_REFRAME` + hinted claims; empirical path byte-identical):**
- **(a)** Normative decompose branch: neutral QUESTION-shaped empirical grounds (§4.2/§4.3 route style). No direction quotas, no counter-slot, no rebalancing.
- **(b)** Mechanical guards on that branch only: value-predicate word-lock (with a legal-label exemption — D2: "genocide" must be researchable by name; the 07-17 run false-flagged Gaza's two best routes), on-subject, structural coverage vs baseline, breadth floor 3, never-empty, fail-safe (stage failure → baseline untouched + disclosed).
- **(c)** MAPPING_PROMPT dimension semantics, GATED to hinted claims (the P4 fork not taken). Non-negotiable companion: question-shaped and mixed-shape elements otherwise produce meaningless stance counts (P4: coercion + inconsistency, §15.8).
- **(d)** Single-claim confirm layout/copy (carried NIT-3/NIT-4; founder locks wording).

**Killed:** the rebalancing apparatus — union guard, rebalance loop, `_claim_dominated` as a gate, direction quotas, `basis.direction` as an editing signal, direction-aware roll-up. Grep-verified 2026-07-17: nothing in `app/` imports `opinion_symmetry` (never wired); removal surface = uncommitted files only.

**Kept as witnesses:** `scripts/opinion_symmetry_eval.py` + `.json` (the failing assertion-arm transcript) and `scripts/opinion_symmetry_eval_questions.py` + `.json` (the discriminating run). The reworked eval becomes the 1b gate: Gaza must return §4.2-grade routes, no denialist brief, no value-predicate element, breadth ≥3 — and the battery is eyeballed for whataboutism each run.

**Deferred post-release (D1 hard commitments STAND, they queue):** direction labels as disclosure-only receipt signal; one-sided-pool tripwire; per-element floor (1c); disconfirm-route-aware recovery (Phase 2); F-MAP-CENTROID; F-EXTRACT-FALLBACK; cost-efficiency work.

**Invariant refinement (founder wording owed, then into CLAUDE.md as Critical-Invariant #7):** never agree by default AND never manufacture doubt or support the evidence does not warrant — false balance is forbidden equally with sycophancy; balance lives in the EVIDENCE, never in forced route symmetry; any balance gate must fail two-sided.

### 20.5 Definitive process (founder-required 2026-07-17 — anti-drift discipline)

Method: phased-build-loop, per slice. **No slice starts before the previous slice's founder sign-off.** Every slice runs: **DESIGN (written, in this doc) → FOUNDER APPROVAL → BUILD → TESTS + EVAL GATES → INDEPENDENT VERIFICATION (fresh agent, adversarial, never the builder) → FOUNDER SIGN-OFF.**

- **Slice 1 — REMOVAL (exceptional care, own verification pass).** Rework `opinion_symmetry.py` down to the surviving skeleton (stage seam, fail-safe, `_write_elements`, guards); delete the rebalancing core; rewrite `test_opinion_symmetry.py`. Verifier proves: nothing in `app/` referenced the deleted symbols (grep evidence), full unit suite green, replay bench zero-drift, flag-off behaviour byte-identical.
- **Slice 2 — decompose branch + guards (a+b).** Gate: reworked Gaza battery green + eyeball, extraction battery still 8/8, bench zero-drift.
- **Slice 3 — mapper dimension semantics (c).** Gate: mapping outputs on question-shaped fixtures (4E16197E, 5810E18F) coherent; empirical-claim mapping byte-identical with flag off; bench zero-drift.
- **Slice 4 — confirm UI copy (d).** Founder locks wording before build; verify-ui pass.
- **Model discipline (founder-required): the correct model for the correct phase.** Design + independent verification on the highest-reasoning model available (Fable 5 / Opus-tier) — these phases catch what cheap passes miss (the §19 catch and the two Artefact-1 corrections were verification-phase saves). Mechanical build steps may run on the session default. Verifier ALWAYS a fresh context — the builder never verifies its own slice (phased-build-loop rule).
- **Eval gates on every slice:** unit suite, the reworked opinion battery, extraction battery, replay bench (F7 debt noted — 5 pre-existing fails are the known baseline; ZERO NEW drift is the gate).
- **Flag flips ONLY after all four slices verify + founder signs.** Rollback at every point = flag off (unconditionally today's behaviour, D-1 cache-key fix already shipped in 1a).

### 20.6 SLICE 2 DESIGN (2026-07-17 — recorded before build per §20.5; founder on auto, standing "proceed" 2026-07-17)

Slice 1 shipped (commit follows the verify record: independent verdict SOUND after 3 NIT fixes; suite 2,429/0; pipeline dir 919/0). Slice 2 = the behaviour.

**(1) Prompt reshape (`opinion_symmetry.py`).** `NORMATIVE_DECOMPOSE_PROMPT` → 3-5 OPEN QUESTIONS about the named subject (ported from the proven discriminating-run prompt MINUS its direction-forcing bullets): each question open and empirically answerable, must not presuppose its answer or assert anything, never asks the value judgement itself; "open such that evidence could answer either way" is the shape property — NO direction quotas, NO counter-slot (§20.2 finding 1). Frame-adoption risk (§4 line 79) is watched by the eval battery, not edited by machinery (founder ruling: disclosure labels deferred post-release).

**(2) Mechanical value-predicate lock (new, in the kept-filter).** Deterministic restatement check, no LLM: normalise claim + element (lowercase, strip punctuation/stopwords/question-words); an element whose content words ⊇ the claim's content words while adding <2 new ones is a RESTATEMENT of the judgement → dropped, logged. The legal-label exemption (D2) is emergent: "What is the status of ICJ proceedings on genocide?" adds content words and passes; bare "Is the situation in Gaza a genocide?" does not and is dropped. Fail-safe: if the lock (with on-subject) empties the set, the existing never-empty fallback keeps the baseline and `grounds.converged=false` discloses it — a check never fails here.

**(3) Wiring (`runner.py` `_do_decompose`, ~line 1287).** After `claim["claim_map"] = results[claim_id]`: `if settings.ENABLE_OPINION_REFRAME and claim.get("type_hint") == "normative": claim["claim_map"] = await apply_grounds_stage(...)`. Empirical claims and flag-off = byte-identical (condition false, zero code executed). `type_hint` flows from the extract dict builders (extract.py:546/684) — build verifies it survives the phase-1 state restore (runner.py:1114).

**(3a) BUILD AMENDMENT — the hint did NOT survive the pause (caught during build, 2026-07-17).** `type_hint` was memory+SSE only; the hinted flow ALWAYS takes the selection pause (1a confirm step, D5), and the phase-2 resume reloads claims from the DB (runner.py:1195-1217) WITHOUT it — so the wiring's gate could never fire on the only path a hinted claim takes. `entry_mode` can't re-derive it (confirm step persists as plain "article"). Fix: persist `claim.type_hint` (nullable varchar16, additive migration `claim_type_hint`, revises `billing_interval`; both Claim() write sites + the phase-2 reload dict). Also the root fix for carried NIT-4 (typeHint on page refresh). Flag off → extract emits no hint → column NULL, nothing reads it.

**(4) F3 scope re-tag (slice-1 verify observation).** `_write_elements` calls `app.utils.scope_sensitivity.apply_scope_flags` on the rebuilt elements — the tagger runs inside the stage so no wiring order can lose scope_flags. (Baseline tagging at claim_map_analyzer.py:1684/1815 is untouched.)

**(5) Types.** `ClaimMapMetadata` gains optional `grounds` (additive, F-R2e `query_plan` precedent). ClaimMap is a TypedDict — runtime dicts, no model changes.

**(6) Eval gate (NEW `scripts/opinion_grounds_eval.py` — the frozen witnesses stay frozen).** Battery = the 4 §20.1 claims through real decompose → real stage. Mechanical gates per case: breadth ≥3; zero restatement leaks (the lock's own check + per-case value words); ≥80% question-shaped elements; on-subject flags printed. Recorded-not-gated: Gaza must show claim-side grounds (§4.2 routes) — eyeballed and transcribed; whataboutism eyeball per §20.2. GREEN = mechanical gates pass on 2 consecutive runs (v4 precedent).

**(7) Test/bench gates.** New unit tests: flag off → stage never called; flag on + normative hint → called; flag on + no hint → not called; restatement lock (drop, exemption, fail-safe); scope_flags present on rebuilt elements. Then: full pipeline dir, extraction battery 8/8 (unchanged code, confirm), replay bench flag-off ZERO NEW drift (runner is now touched — the bench matters from this slice on), full unit suite. Independent fresh-agent verification, then commit.

### 20.7 SLICE 3 DESIGN (2026-07-17 — recorded before build; founder on auto). SLICE 2 SHIPPED: build per §20.6 + (3a); independent verify SOUND after 3 NIT fixes (wrapped-duplicate dedup, lock-collapse disclosure `converged=false`, wrap-phrase stopwords) + pre-empted rstrip charset bug; grounds eval GREEN 4/4 ×2 twice (runs 2-3 pre-fix, 4-5 post-fix); Gaza independently eyeballed = §4.2 routes, zero whataboutism/denialism; bench stash-proven zero new drift; suite 2,440/0. Two standing observations: deploy-order (migration before code — entrypoint.sh handles), subset-anchored lock passes SHORTENED restatements of long claims (prompt + eval eyeball carry those).

**Slice 3 = the P4 fix (§20.4(c)): mapping semantics for question-shaped elements, gated to grounds claims.**

- **Gate = `claim_map.metadata.grounds.applied is True`** — the claim_map carries its own marker (written only by the grounds stage, which only runs flag-on + hinted). No type_hint threading; flag off → key absent → every prompt byte-identical (bench-safe).
- **Change: a GROUNDS_MAPPING_ADDENDUM block** appended to MAPPING_PROMPT at BOTH single-claim sites (map_evidence_to_elements ~:1138 and recovery mapping ~:2116) when the gate is true. Semantics (dimension-aware, counts unchanged): "supports" = evidence substantively ANSWERS the question / documents the ground; "challenges" = evidence disputes the ground's substance or premise; "context" unchanged; states keep mechanical meaning over the counts ("supported" = ground well-documented); never treat the question as an assertion to confirm, never infer the parent claim's truth. Downstream (state derivation, orientation, frontend) untouched — the P4 fix is prompt-semantics only, the counting machinery already works.
- **Batch mapping partition:** a multi-claim article check CAN contain a hinted claim (Rule 6 hints per-claim), and batch mapping would miss the addendum. Fix: in the batch path, grounds-applied claim_maps are routed individually through map_evidence_to_elements (which applies the addendum); the rest batch as today. Flag off → nothing partitioned → byte-identical.
- **Gates:** unit tests (prompt byte-identity for non-grounds maps; addendum present iff grounds.applied; batch partition routes grounds claims individually, stub-driven); NEW live eval `scripts/grounds_mapping_eval.py` — grounds decompose (live) for Gaza + immigration, CURATED synthetic evidence with known leans, live mapping; mechanical checks (all element_ids present, valid states/relationships, refs resolve) + printed output for coherence eyeball; ×2 consecutive. Then full pipeline dir + bench zero new drift + suite. Independent verify, then commit.


### 20.8 SLICE 4 DESIGN + DRAFT COPY (2026-07-17 — DESIGN ONLY; build blocked on founder wording lock per §20.5)

**Scope (carried NIT-3 + NIT-4):** the single-claim confirm step currently wears the full "select up to 3" apparatus (greyed card, "Investigate 0 claims" — founder screenshot, 07-16 session). Slice 4 gives it a proper confirm layout.

**Design:**
1. **Detection:** selection page renders CONFIRM variant when the check has exactly 1 claim AND it carries `typeHint == "normative"` (SSE) — with a backend companion: expose the now-persisted `claim.type_hint` in the claims payload the selection page loads, so the variant survives a page refresh (NIT-4 root fix — the column shipped in slice 2; only the API surfacing remains).
2. **Layout:** single card, no checkbox/counter apparatus; the claim verbatim under a "Your claim" label; explanation line (copy below); primary CTA proceeds (fires the existing selection endpoint with the single claim), secondary = edit/cancel. No new endpoints.
3. **Language-lock compliance:** no verdict words, no "verify"; evidence-research framing; UK English; "the judgement stays yours" register.

**Draft copy — FOUNDER PICKS/EDITS ONE (nothing builds until locked):**
- **Option A (research-framing):** Heading "Confirm your check." Body: "You've submitted an opinion-shaped claim. Tru8 doesn't judge opinions — it researches the evidence around them. We'll investigate the measurable grounds behind this claim and organise what the evidence shows. You decide what it adds up to." CTA "Research the evidence" / secondary "Edit claim".
- **Option B (grounds-framing):** Heading "This reads as an opinion." Body: "Tru8 researches evidence; it doesn't adjudicate opinions. We'll break this claim into neutral, checkable questions — the grounds a careful researcher would examine — and organise the evidence for each. The judgement stays yours." CTA "Start the research" / secondary "Edit claim".
- **Option C (minimal):** Heading "Ready to research." Body: "We'll research the evidence behind this claim's measurable grounds and show you the landscape. We organise; you decide." CTA "Confirm and research" / secondary "Edit claim".

**Out of scope (recorded, queued):** NIT-6 email/PDF "Article mode" wording (cosmetic); F-MAP-CENTROID (own frontend slice).
**Gates when built:** verify-ui pass (build, route, confirm variant renders on a hinted check, refresh survival, no-verdict language check); flag-off = today's selection page byte-identical (variant requires the hint, which only exists flag-on).
