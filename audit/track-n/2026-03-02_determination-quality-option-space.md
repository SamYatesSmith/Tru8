# Tru8 — Determination Quality Option Space

**Date:** 2026-03-02
**Context:** Post-Track-M (trimmed). Transparency and provenance infrastructure complete. This document explores the option space for improving determination quality itself.

---

## 1. What the Real Forks Now Are

There are five genuinely distinct options. They are not a sequence. They are forks — each addresses a different part of the problem, each has different cost/complexity, and several interact in ways that affect which combination makes sense.

The forks are:

- **A.** Evaluate whether the mapping model is capable enough (gating question)
- **B.** Give the mapper more text, within the current architecture
- **C.** Move passage selection from claim-level to element-level (architecture change)
- **D.** Reduce noisy inputs before they reach the mapper
- **E.** Tighten what the mapper is asked to do and how its outputs are checked

These are not five steps. They are five directions. Some are complementary. Some are substitutes. Some make others unnecessary.

---

## 2. Option A — Model Evaluation as Gating Question

**What problem it solves:** The mapper runs on `gemini-2.5-flash-lite` (`config.py:42`). The fallback is `gpt-4o` (`config.py:282`), but that only fires on provider failure, not quality failure. Flash-lite is a cost/latency model doing the single highest-stakes reasoning step. If it can't reliably distinguish "this evidence directly confirms the claimed figure" from "this evidence discusses the same topic," then improving inputs is compensating for a reasoning ceiling.

**Main strength:** This is the cheapest thing to evaluate and the most consequential thing to know. You take 20-30 real pipeline outputs, run the same evidence through flash-lite, flash (non-lite), and gpt-4o, and compare the mapping quality. If flash-lite's relationship assignments and state labels are materially worse, you know early. If they're comparable, you know the model isn't the bottleneck and can focus on inputs.

**Main weakness:** It requires manual evaluation. There's no automated ground truth for "is this mapping correct." Someone has to read the evidence, read the element, and judge whether the mapping is correct. That's 20-30 checks across 3 models — maybe a day of work, not engineering work.

**Dependencies:** This option has no dependencies. Every other option depends on its answer. If the model is the bottleneck, Options B/C/D become mitigations rather than solutions. If the model is adequate, B/C/D become the main levers.

---

## 3. Option B — More Text to the Mapper (Simple Path)

**What problem it solves:** The mapper sees 400 characters per evidence item (`config.py:182`, applied at `claim_map_analyzer.py:324`). But the `text` field is already a compressed excerpt — `_find_relevant_snippet()` (`evidence.py:633-718`) selects the top 2-3 sentences (max 200 words) by word overlap or semantic similarity against the *claim*. So the mapper sees the first 400 chars of a ~200-word claim-relevant excerpt. For many evidence items, the substantive content (figures, dates, specific assertions) falls outside this window.

The simplest version: raise `EVIDENCE_SNIPPET_LENGTH` from 400 to 800 or 1000. The `text` field is typically 200 words (~1200 chars), so 800-1000 chars would capture most of the already-selected excerpt.

**Main strength:** Trivial to implement. One config change. Immediate effect. The mapper prompt already asks the LLM to "cite specific figures, dates, or entities" (`claim_map_analyzer.py:102`) — giving it text that actually contains those things is the minimum prerequisite for that instruction to work.

**Main weakness:** Both layers of selection are still claim-level, not element-level. The `_find_relevant_snippet()` function selects sentences relevant to the *claim as a whole*. If a claim decomposes into 3 elements, the selected sentences may be relevant to element 1 but not elements 2 or 3. More chars from the same claim-level excerpt doesn't fix this fundamental mismatch.

The other complication: longer per-evidence text means larger prompts. With 15-20 evidence items at 800 chars each, the mapping prompt grows from ~8K tokens to ~15K tokens. Flash-lite can handle this, but prompt size affects both cost and latency. The batch mapping path (`claim_map_analyzer.py:478-508`) — which processes multiple claims in one call with `max_tokens=8000` — would be more constrained.

**Dependencies:** Independent of D and E. Partially superseded by C (if you do element-targeted excerpting, the snippet length matters less because you're selecting different text anyway). Should be evaluated alongside A — if flash-lite can't reason well at 400 chars, more chars may or may not help, depending on whether the problem is input poverty or reasoning depth.

---

## 4. Option C — Element-Targeted Passage Selection

**What problem it solves:** The fundamental mismatch: evidence is selected and excerpted at the *claim* level, but mapped at the *element* level. `_find_relevant_snippet()` (`evidence.py:633`) uses embedding similarity or word overlap against the full claim. The decompose step then splits the claim into 1-5 elements. The mapper receives text that was selected for relevance to the whole claim and must figure out which parts address which elements.

Element-targeted excerpting would select different passages from the same source for different elements.

**Main strength:** This is the only option that addresses the *structural* mismatch. Every other option works within the current architecture where selection and mapping operate at different granularities. This one aligns them.

**Main weakness:** This is where the option space gets genuinely hard. There are three sub-variants, each with different trade-offs:

**C1: Pre-mapper element-targeted selection.** Before the mapping call, for each element, scan each evidence item's full `text` field and select the most relevant passage. This means running snippet selection N times per evidence item (once per element). With 3 elements and 20 evidence items, that's 60 selection operations instead of 20. If selection uses embeddings (`_extract_semantic_snippet`, `evidence.py:720`), that's 60 embedding calls. If it uses word overlap, it's cheaper but less accurate. Either way, this creates the element-level excerpts *before* the mapper, so the mapper sees per-element tailored text.

The complication: this requires the decompose step to run *before* snippet selection, which means restructuring the pipeline. Currently: retrieve → classify → map (which decomposes + maps in one stage). You'd need: retrieve → classify → decompose → per-element excerpt → map. That's a pipeline restructuring, not a config change.

**C2: Longer text to the mapper, let the model find relevant parts.** Send 1500-2000 chars per evidence item (or the full `text` field) and rely on the mapper to identify which parts address which elements. This avoids the pipeline restructuring but puts the passage-selection burden on the mapping model. Whether this works depends entirely on the model's capability — which brings you back to Option A.

**C3: Two-pass mapping.** First pass: map with current short snippets. Second pass: for elements that received evidence refs, re-examine those specific evidence items with longer, element-targeted text. Only the elements that got mapped (i.e., aren't `unresolved` with zero refs) get the second pass. This limits the cost multiplication — you're only doing detailed re-examination for the mappings that matter.

The complication with C3: it doubles the LLM calls for the mapping stage. It also raises a coherence question — if the second pass disagrees with the first (different relationship, different state), which wins?

**Dependencies:** C depends heavily on A. If flash-lite can't handle nuanced mapping at *any* input length, element-targeted excerpting helps less than expected. C1 requires pipeline restructuring. C2 requires a model capable of long-context reasoning. C3 requires a coherence strategy.

---

## 5. Option D — Reduce Noisy Inputs

**What problem it solves:** The relevance scorer excludes only score-1 items ("off-topic") at `relevance_scorer.py:631`. Score-2 items — defined as "Weakly relevant, same general domain but different specific topic" (`relevance_scorer.py:44`) — pass through to the mapper. So evidence about "economic trends affecting employment" can reach a mapper trying to evaluate "GDP growth was 0.5% in Q3." The mapper then has to decide what to do with tangentially relevant material, and may interpret a vague mention as support.

Two sub-variants:

**D1: Raise the exclusion threshold.** Exclude score-2 (and possibly score-3) evidence. This directly reduces noise — the mapper sees fewer items, all of which are at least "partially relevant" or better.

**D2: Flag weak evidence to the mapper.** Don't exclude score-2 items, but annotate them in the mapper prompt. Something like `[WEAK RELEVANCE]` before the text. This lets the mapper decide, with the information it needs to decide well.

**Main strength:** D1 is the simplest intervention that directly reduces the chance of false `supported` states. If the mapper never sees tangentially relevant evidence, it can't misinterpret it as supporting. D2 preserves coverage while adding a quality signal.

**Main weakness of D1:** Coverage loss. Some score-2 evidence might be relevant to a specific element even if the claim-level relevance score is low. The relevance scorer rates against the *full claim* (`relevance_scorer.py:29-31`), not against individual elements. An article that scores 2 against a multi-part claim might score 4 against one specific element. Cutting it removes that possibility.

**Main weakness of D2:** It relies on the mapper to use the flag correctly. The prompt already asks the model to assess relevance per-element. Adding a label saying "this is weakly relevant" may or may not change its behaviour — it depends on the model (back to Option A).

**Dependencies:** D1 is fully independent. D2 depends slightly on how much you trust the mapper to use quality signals (interacts with A). Neither depends on B or C.

---

## 6. Option E — Tighten State Semantics and Validation

**What problem it solves:** The mapper's state definitions are vague. "Predominantly supportive" and "no meaningful" evidence are subjective thresholds (`claim_map_analyzer.py:104-106`). The mapper's output is accepted at face value — `_parse_mapping_response()` validates evidence_ids and relationship enums but not whether the reasoning supports the state (`claim_map_analyzer.py:750-754`).

**Two parts:**

**E1: Prompt tightening.** Rewrite the state definitions to require specific conditions. For example: `supported` requires at least one evidence ref whose reasoning cites a specific fact (number, date, entity name) that directly addresses the element's assertion. If no ref does that, the state must be `unresolved`.

**E2: Post-mapper validation.** After the mapper returns, check whether the assigned state is plausible given the evidence refs. The lightest version: for `supported`/`disputed` elements, verify that at least one evidence_ref has a non-empty `reasoning` field. Heavier versions: check for shared named entities between reasoning and element text, or check that the number of `supports` refs is consistent with a `supported` state.

**Main strength of E1:** It's a prompt change — no code changes, no pipeline restructuring. It makes the mapper's task more precise, which helps regardless of model capability. Even a weaker model produces better outputs with clearer instructions.

**Main strength of E2:** It catches the most obvious failures. An element marked `supported` with zero evidence refs, or with refs that have no reasoning, is clearly wrong. Catching those is cheap.

**Main weakness of E1:** Tighter definitions make the output more honest but potentially less stable. If you require cited facts for `supported`, a claim that gets 4 slightly different evidence excerpts across two runs might flip between `supported` and `unresolved` depending on whether the specific figure appears in the truncated window. Stability matters for user trust — if the same claim produces different states on different runs, that's its own credibility problem.

**Main weakness of E2:** Anything beyond the lightest version (non-empty reasoning check) is a blunt instrument that produces false positives and false negatives. Shared entity matching sounds reasonable but fails on paraphrasing, and passes on coincidental matches. It creates a veneer of verification without delivering actual verification. The risk is that it gets treated as more than it is.

**Dependencies:** E1 is independent — you can tighten the prompt regardless of everything else. E2 is more useful *after* B or C (better inputs mean validation is checking better outputs rather than just downgrading everything to `unresolved`). E1 interacts with the stability concern — if you also do A and find that flash-lite is marginal, tighter prompts on a marginal model may increase flakiness.

---

## 7. Which Options Feel Foundational vs. Secondary

**Foundational:**

- **A (model evaluation)** is foundational because it determines the ceiling. Everything else is input preparation for a model call. If the model can't reason at the level required, input improvements are necessary but not sufficient. This should happen first.

- **B (more text)** is foundational in the sense that *something* about the input length must change. 400 characters of claim-level-selected text is not enough to evaluate element-level assertions. Whether you solve this via B (simple length increase), C1 (element-targeted pre-selection), C2 (longer text + model reasoning), or C3 (two-pass) is a design decision. But the status quo is clearly insufficient.

**Important but second-order:**

- **D1 (noise reduction)** is a genuine improvement that's quick and independent. It doesn't fix the core problem (the mapper's reasoning quality) but it removes a class of failure (false positives from tangential evidence). It's worth doing regardless of the other choices.

- **E1 (prompt tightening)** is similarly quick and independent. Better instructions help any model. The risk is stability degradation, but you can evaluate that empirically.

**Genuinely secondary:**

- **C (element-targeted excerpting)** is the most architecturally correct solution but also the most complex. It might be unnecessary if B + A shows that a better model with longer claim-level excerpts is already good enough. It might be essential if the claim-level/element-level mismatch turns out to be the dominant failure mode. You won't know which until you've done A and B.

- **E2 (post-mapper validation)** is the option most likely to sound better than it is. Its value is capped by how blunt the validation can be. The lightest version (non-empty reasoning check) is worth having. Anything heavier should be deferred until you have data on what the actual failure modes are.

- **D2 (flagging weak evidence)** depends entirely on the mapper model's ability to use quality signals, which you won't know until you've done A.

---

## 8. Where the Real Constraints Now Seem to Be

**The binding constraint is evaluation infrastructure, not engineering complexity.** The hardest part of this phase is not writing the code. It's knowing whether the code helped. There is no automated ground truth for mapping quality. You cannot write a test that says "this evidence should be mapped as `supports` for element 2." Every quality judgment requires a human reading the evidence and the element and deciding whether the mapping is correct.

This means the real bottleneck is: can you evaluate 20-30 pipeline outputs across model variants and input configurations quickly enough to make informed decisions? If yes, you can iterate through A → B → D1 → E1 efficiently. If no, you'll be shipping changes without knowing whether they helped, which is how you end up with infrastructure that looks good but doesn't move the trust needle.

**The cost/latency constraint is real but not yet binding.** Flash-lite is cheap. Moving to flash (non-lite) or gpt-4o for the mapping call increases cost per check by roughly 3-10x for that stage. Longer snippets increase prompt tokens. Element-targeted excerpting multiplies calls. None of these are prohibitive for the current volume, but they add up. The constraint becomes binding at scale, which means the model and architecture decisions made now have cost implications later.

**The stability constraint is underappreciated.** Every change that makes outputs more honest also makes them less stable. A mapper with longer snippets will produce slightly different mappings when the snippet window shifts. A mapper with tighter state definitions will flip between `supported` and `unresolved` more readily. A post-mapper validation layer will occasionally downgrade states that the mapper got right but couldn't justify legibly. Users and agents need consistent outputs from consistent inputs. Honesty and stability are in tension, and no option in this space resolves that tension cleanly.
