# Non-Sycophancy & Opinion-Handling — Discussion & Analysis

**Date:** 2026-07-14
**Purpose:** The "understand and decide" companion to the technical design note (`audit/2026-07-14_non_sycophancy_invariant.md`). Read *this* to get back into the headspace tomorrow; read *that* for the exact code seams and guarantees.
**Status:** Discussion only. Nothing built. Founder sign-off + three decisions gate the first line of work.

---

## 1. How we got here (the story in one page)

A real check exposed the whole thread. Someone submitted a single sentence:

> "The Warner, Paramount proposed merger is a real danger to American democracy."

The report that came back examined only one thing — *that a merger was proposed* — and never touched the point the person actually cared about (*is it a danger to democracy?*). Two things had gone wrong at once, and they turned out to be the same thing:

1. **Extraction kept the fact and silently dropped the opinion.** The sentence carried two propositions — an empirical one (a merger was proposed) and an evaluative one (it endangers democracy). The extractor is built to keep verifiable facts and discard opinion (Rule 6, "OBJECTIVE ONLY"), so the evaluative half never became a claim.
2. **No claim-selection step appeared.** With only one claim surviving, the pipeline switched to "focused mode" (`runner.py:845`, `entry_mode = "focused" if len(claims) == 1`) and ran straight through — the selection pause only exists when there are ≥2 claims. So the person never got the chance to say "no, research the *democracy* angle."

We checked the obvious worry first — **was this a political leaning?** It is not. The drop is content-neutral: the same rule discards "is a gift to freedom" exactly as readily as "is a danger to democracy", and the pipeline happily extracts political *facts* from every side (its own examples keep Trump, Biden, Boris Johnson, EU claims). The discriminator is *grammatical form* (fact vs. value judgement), not political direction. Verified in code, not asserted.

That opened a bigger, better question: **most of the public writes like this.** Ordinary people don't submit clean falsifiable statistics; they submit conclusions — "X is corrupt", "this policy is a disaster", "the merger threatens democracy" — and ask you to check the reasoning underneath. If Tru8 throws that away, its first impression with the public is hollow precisely where first impressions are made.

And *that* surfaced the deepest concern, which is now the spine of all of it:

> If we start researching the opinions people hand us, how do we guarantee we don't just go looking for evidence that **agrees**? An evidence platform that confirms whatever it's given is a disinformation amplifier — the one thing worth shutting the company down to avoid.

That worry is correct, and it comes first. Everything below is about making the answer *mechanical and provable*, not a promise.

---

## 2. The concepts worth being fluent in

### 2.1 Sycophancy is the existential failure mode
Large language models drift toward agreeableness by default — it is their single most-documented bias. For a chat assistant that's mildly annoying. For an evidence-research platform whose entire reason to exist is honest organising, it is fatal: a sycophantic pipeline makes lies *look* supported, and becomes a laundering machine for whatever nonsense it's fed. So "don't be sycophantic" isn't a polish item; it's the product thesis.

### 2.2 The fork that decides everything: Version A vs Version B
When you said "we don't platform lies", there were two ways to build it, pointing in opposite directions:

- **Version A — detect lies and refuse/bury them.** Sounds righteous; is actually the danger. It re-introduces a *verdict* — something decides what a lie is — and whoever tunes that becomes the arbiter. A lie-detector is just sycophancy toward its author. It breaks "We organise; you decide."
- **Version B — never let agreeableness distort the honest landscape.** Tru8 refuses to make a false claim *look* supported, but never stamps TRUE/FALSE. The truth surfaces because the *organising* is relentlessly symmetric: a false claim comes back visibly challenge-heavy, primary sources contradicting it, and the reader draws the conclusion. **The submitted claim is the starting context for an honest search, not a conclusion to defend.**

**You confirmed B.** The elegance of B is that it needs no arbiter — it only needs the search and the organising to be *honest and symmetric*. A false claim and a true claim get identical treatment; the difference in what comes back is the *evidence's* doing, not Tru8's.

### 2.3 How "no verdict" and "don't platform lies" reconcile
They look like they're in tension. They aren't, once you see B. Tru8 never says "false" — but it also never lets the landscape *misrepresent the weight and direction of the real evidence*. "The earth is flat" should come back overwhelmingly challenged, because that's what the real record shows, without a "FALSE" stamp anywhere. "Don't platform lies" = "never let sycophancy flatter a claim past what the evidence supports." That's mechanically enforceable and stays true to the no-verdict lock.

### 2.4 Why this must be mechanical, never a prompt
This is the load-bearing engineering principle (project lesson **NF-11**). You cannot ask the LLM to police its own agreeableness — that's the fox guarding the henhouse, because agreeableness *is* the drift you're guarding against. Every guarantee has to live in code: how queries are built, how evidence is filtered, how state is counted. Prompt text can be belt-and-braces on top, never the enforcement layer.

---

## 3. What the code actually does (the honest picture)

The reassuring headline: **the judge is already honest — it just only ever sees one side of the file.**

**Already mechanically non-sycophantic (downstream of retrieval):**
- Element state is recomputed by *tier-weighted counting* of supports vs. challenges, and the LLM's own verdict is thrown away (`claim_map_analyzer.py:603-804`).
- Commentary that merely agrees is demoted to "context", not "supports".
- Orientation prose is pure counting, with the false-balance fix already shipped (`46163a2`: a challenges-only claim reads "challenges it, with none supporting", not the softer "both supports and conflicts").
- A claim's own source domain is barred from corroborating it (`retrieve.py:264-268`).

**The leak — entirely in retrieval:**
- There is **no challenge-seeking query anywhere in the pipeline** (verified by exhaustive grep across every query path). Every one of the 2–5 queries per element restates the claim *in its own framing* — the planner is literally told to "use EXACT names, numbers, and entities from the element description."
- So the pool's balance is whatever the open web happens to return for a claim-shaped query. For viral misinformation that believers keep restating, the honest judge counts an honestly one-sided pool — and the landscape looks supported. **The judge is fair; the evidence-gathering only ever briefed one side.**

**A subtlety worth remembering:** the filters are currently stance-symmetric only *by accident* — they all run before "stance" even exists in the data. Nothing stops a future stage from breaking that silently, so it needs a test to lock it.

---

## 4. The solution space (with the trade-offs)

### 4.1 The core fix — a mechanical "challenge lane"
Per element, mechanically issue at least one *challenge-framed* query alongside the topical ones, so the pool structurally contains both sides **before any LLM sees it**. It slots into an existing seam in retrieval (right next to the "class augmentation" compensator already running) and fits inside the current 5-query-per-element budget.

The key mental model: **the challenge lane does not bias *toward* challenge — it *removes* a bias.** Today the search is one-sided by construction; the lane makes it two-sided. If the claim is true, the lane returns weak or fringe material that the tier-weighted counting correctly declines to act on. Balance then comes from the evidence itself, through the honest judge we already have.

### 4.2 The receipt — a one-sided-pool tripwire
If a claim comes back heavy-supports / near-zero-challenges, flag *the search*, not the claim: either "we searched the other side and found nothing that mapped" (informative, honest) or "the challenge search returned nothing — this absence is unverified." It reuses the existing grey no-verdict note channel (same as the thin/echo/repetition notes). It describes the *search record*, never adjudicates the claim — that's the guardrail against it drifting into a verdict.

### 4.3 The lock — filter symmetry as a test
Codify what we found: no filter may condition on stance, and no filtering runs after stance is assigned. Enforced by a mirrored-pool test (swap supports/challenges labels, assert identical keep/drop). Cheap, and it protects the accidental symmetry from a future regression.

### 4.4 The proof — a red-team disinformation bench as a build gate
A battery of canonical known-false claims (vaccines→autism, 5G→COVID, 2020 election stolen, etc.) must *each* produce a challenge-dominant landscape with primary contradiction — and their negations must come back symmetrically honest. It runs on every pipeline change, forever, and **failing it fails the build.** This is how "we don't platform lies" stops being a value statement and becomes a test. (It fits the existing replay-bench discipline. One dependency: the standing F7 re-gold debt currently blocks bench-gating generally and must be cleared first.)

### 4.5 The feature this unlocks — opinion-handling, built on top
Once the floor exists, we can safely do the thing that started all this: treat an opinion as a *researchable question*. The locked Claim Map contract *already* has a `normative_flagged` claim type ("may decompose into empirical sub-elements") — it's dead code today because extraction drops opinions before decomposition sees them. The plan: keep the opinion as an affirmative claim (a sibling of the shipped Rule 9 that already turns "Is vaping safe?" → "Vaping is safe, evidence shows both sides"), decompose it into empirical proxies (media concentration, competition, antitrust exposure), and let the symmetric supports/challenges layer deliver the balance. The value predicate ("is dangerous") *never* becomes an element — we research the grounds; the leap from grounds to judgement stays with the reader, with a visible reframe receipt ("we researched the empirical basis; whether it amounts to 'a danger' is yours to judge").

**Why order matters:** opinion-handling *without* the challenge lane would be a sycophancy amplifier — opinion-shaped claims attract opinion-shaped pools that mostly agree. So: floor first, feature second.

### 4.6 Alternatives considered and rejected
- **Detect-and-refuse lies (Version A):** re-introduces a verdict / arbiter. Rejected on principle.
- **Generate an explicit opposing opinion and research both:** doubles cost, and *manufacturing* a counter-opinion the user never expressed is itself an editorial act. The symmetric supports/challenges layer already delivers balance from the single affirmative claim — Rule 9's shipped behaviour is the existence proof.

---

## 5. The decisions that are genuinely yours (for tomorrow)

Everything else is engineering. These three are values calls:

1. **The wording of the challenge query — the big one.** A user-invisible term set decides what "search the other side" *means*. `"debunked"` is out — it's a verdict in query form. Candidates: `"criticism"`, `"evidence against"`, `"disputed"`, `"fact check"` (I'd keep "fact check" off — too verdict-adjacent tonally). Proposal: a small neutral set, settled by a quick eval, **but you approve the final terms.**
2. **Do you consciously accept "less tidy" landscapes for true claims?** The challenge lane will pull some fringe denial content into pools for well-established claims (vaccine safety → anti-vax blogs). Tier-weighting defends the *state*, but a true claim may now show an honest, visible challenge column. I read that as the product working as designed — but it's your call to own, not mine to assume.
3. **The red-team bench's claim list is an editorial act — in the tests, not the product.** Choosing "known-false" claims to gate the build encodes a truth judgement *in the test suite* (which is fine — tests may know what the product must never assert). But the list must be canonical, consensus-sourced, and founder-approved, so nobody can say the gate smuggles a worldview into the pipeline.

Smaller ones, notable but not blocking: cost/latency (+1 query per element ≈ class-augmentation magnitude; land behind a flag, default on); non-web government/academic adapters stay one-sided in phase one (structured primary sources are inherently the challenge lane for false numeric claims).

---

## 6. Where to pick up tomorrow

Suggested first move (lowest risk, no behaviour change): **lock the filter-symmetry and orientation tests** (§4.3, §4.4 of the design note) while the challenge-query wording is being settled. Then, in order: the challenge lane → the tripwire receipt → record the red-team bench and make it gate → *then* start the opinion-handling design on top.

To re-enter: read §1–§2 here to reload the *why*, then the design note §2–§3 for the *where*. The one line to remember: **the judge is honest; we just have to stop briefing only one side.**

---

## 7. Pointers
- **Technical design note (companion):** `audit/2026-07-14_non_sycophancy_invariant.md` — exact seams, guarantees, bench spec.
- **Memory:** `project_non_sycophancy_invariant_2026_07_14.md` — the locked decision + resume state.
- **Register:** `audit/OPEN_WORK.md` — 2026-07-14 entry.
- **Neighbours:** `audit/2026-07-09_retrieval_quality_plan.md` (the challenge lane extends this retrieval work; deferred remedies R2b/g/d live there); `audit/track-b/2026-02-12_claim-map-contract.md` (`normative_flagged` §2, extraction hint §8 — the opinion-handling substrate); `.claude/CLAUDE.md` Critical Invariants (proposed addition #7 "Never agree by default" — a sign-off action, not yet made).
- **Origin check:** TRU-1928-D5F6 (dropped "danger to democracy"; report `tru8-report-1928d5f6.pdf`).
