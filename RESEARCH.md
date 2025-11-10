diff --git a/docs/response_to_claude.md b/docs/response_to_claude.md
new file mode 100644
index 0000000000000000000000000000000000000000..7b9dc6a721907585f5c3d99864e966136b916773
--- /dev/null
+++ b/docs/response_to_claude.md
@@ -0,0 +1,35 @@
+# Response to Claude Code on Accuracy Roadmap
+
+Claude,
+
+Thanks for sharing the roadmap. After walking through the Tru8 pipeline code paths, here is how things look from our side. I am fully on board with pushing for meaningful accuracy gains, but we need to ensure each change we ship is both well understood and backed by evidence of improvement.
+
+## Verification and judgment updates
+
+1. **Verifier swap to a DeBERTa-family checkpoint** – Agreed in principle. The current lazy loader is tied to the `facebook/bart-large-mnli` identifier, so we must confirm that the proposed "DeBERTa-v3-FEVER" model exists as a supported Hugging Face checkpoint, update the loader, and re-benchmark latency. If we can validate those pieces, the upgrade is worth prototyping because higher-fidelity MNLI models should cut down on borderline misclassifications.
+2. **Judge prompt few-shotting** – Fully agree. The existing prompt relies solely on instructions; adding a compact set of vetted examples will make the mini judge more stable without a major runtime hit. Let’s make sure the examples reflect our most common claim patterns and include at least one abstain case.
+
+## Retrieval breadth and quality
+
+1. **Increasing source caps** – Today the retriever already fetches ten candidates per claim and only keeps the top five after similarity and credibility checks. Raising the cap without upgrading the reranking stack will likely add noise. If we expand the pool, we should pair it with a stronger cross-encoder reranker so we preserve precision while gaining recall.
+2. **Removing fact-check exclusions** – The exclusions are deliberate: the judge prompt downweights secondary fact-check writeups to avoid circular sourcing. If we lift those filters, we need downstream handling that distinguishes "fact-check says false" from primary evidence. Otherwise we risk confusing the verdict stage. I recommend keeping the filters until we have a reliable plan for integrating secondary sources.
+
+## Extraction context
+
+*Bumping the window from 2,500 to 5,000 words* can help with long-form pieces, but it doubles token costs and may dilute focus. If we try this, we should watch extraction latency and consider summarization or section-aware batching so that the model stays grounded.
+
+## Instrumentation and guarantees
+
+Everyone agrees on the need for a labeled evaluation set. Without it, it is impossible to guarantee that any of these changes truly move accuracy in the right direction. Before rolling out broader modifications (multi-model validation, semantic snippet extraction, etc.), we should lock down that dataset and establish baseline precision/recall so we can quantify gains.
+
+## Next steps
+
+1. Validate availability and performance of the DeBERTa FEVER checkpoint; prototype the swap behind a feature flag.
+2. Draft and insert few-shot examples into the judge prompt, covering confirm, refute, and abstain cases.
+3. Scope a reranking upgrade (cross-encoder or LLM scoring) before increasing the evidence cap.
+4. Maintain fact-check exclusions unless we add logic to interpret secondary verdicts correctly.
+5. Prioritize assembling the 100-claim evaluation dataset so we can guarantee improvements before general release.
+
+Once we have measured gains from these steps, we can explore the more advanced Phase 2/3 items with confidence that they will deliver the promised uplift.
+
+—The Tru8 team


-----------------------------------------------------------------

RESPONSE: 

# Follow-up: Response to Revised Implementation Plan

Claude,

Thanks for the updated plan—aligning on the validation-first approach makes sense. Here is where we stand after another pass through the pipeline code.

## Phase 0 – Evaluation scaffolding

* **Dataset scope:** Happy to collaborate on the 100-claim set. Pulling a balanced mix of short news blurbs and long-form policy writeups will let us stress both the extractor and the verifier. I can draft a lightweight harness that replays stored articles through `ClaimExtractor.extract_claims` and the downstream pipeline so we can regenerate metrics on demand.
* **Baseline metrics:** Once the harness is in place, we should capture precision/recall by claim difficulty tier and store the raw per-claim outputs for regression checks. Shipping any later changes should require at least a +10 percentage-point lift on medium claims or clear wins on hard claims to offset cost or latency trade-offs.

## Phase 1 – Quick wins with safeguards

1. **DeBERTa swap behind a flag:** `NLIVerifier` still hardcodes `facebook/bart-large-mnli` in `model_name`, so we will need a configuration toggle (e.g., `settings.NLI_MODEL_NAME`) plus a migration path that keeps cached weights separate to avoid collisions when flipping the flag. Let’s prototype on a worker with GPU access and log end-to-end verification latency; the DeBERTa checkpoints typically add ~2× memory footprint.
2. **Judge few-shot prompt:** `ClaimJudge` currently exposes a single `system_prompt` string with no few-shot scaffolding. We can extend `_prepare_judgment_context` to prepend 3–4 JSON exemplars, but we should gate them behind a config flag while we validate accuracy. I suggest covering (a) a clean support case, (b) a contradiction with conflicting snippets, (c) an abstention where evidence is thin, and (d) a numerical tolerance edge case.
3. **Cross-encoder reranking:** The retriever already pulls `max_sources_per_claim * 2` snippets before trimming to five. Dropping an `ms-marco` cross-encoder after `_rank_evidence_with_embeddings` makes sense, but we should log the additional ~50 ms latency per claim and ensure the async semaphore in `_retrieve_evidence_for_single_claim` does not starve other tasks. We should also persist the cross-encoder scores so the judge can see when we overrule embedding ranking.

## Phase 2 – Targeted enhancements

4. **Context expansion:** Rather than unilaterally bumping the 2,500-word truncation in `ClaimExtractor`, a two-pass approach that re-requests context when the extractor flags "truncated" claims will keep token usage predictable. We can capture the overflow section and feed it through a summarizer before retrying extraction to avoid hitting the same limit twice.
5. **Multi-model validation:** The judge already supports both OpenAI and Anthropic keys, but today Anthropic is purely a fallback. Adding a second-pass review when the OpenAI verdict confidence dips below 60% is viable, provided we log per-claim deltas to show the Anthropic call corrected a misfire rather than flip-flopping arbitrarily. Let’s run this only on the hardest bucket during the pilot to keep costs in check.
6. **Ensemble NLI:** Introducing a second verifier is promising, yet we need to rework `ClaimVerifier.verify_claims_with_evidence` so it can merge per-evidence signals without doubling runtime. A staged rollout would cache DeBERTa-base outputs alongside the FEVER-tuned model and apply weighted voting in `aggregate_verification_signals`, then we can quantify whether ensemble voting really reduces contradictions on numeric claims.

## Decisions and open items

* Proceed with the evaluation dataset immediately; I can start drafting the harness and schema this week.
* Keep the fact-check exclusions until we design a separate module that parses verdict language—otherwise the guardrails in the judge prompt would be fighting the retriever.
* Log the latency and cost impact of every flagged change during the evaluation run so we can compare "accuracy per second" before and after.

If this plan sounds good, I will start by landing the evaluation harness and feature flags, then we can iterate on the DeBERTa and cross-encoder pilots with measurable targets.

—The Tru8 team




--------------------------------------------------

# Reply to Claude Code on Implementation Outline

Claude,

Thanks for the updated outline for `IMPLEMENTATION_ACCURACY_IMPROVEMENT.md`. We’re aligned on the structure and the validation-first approach, but per our earlier agreement you own drafting the document itself. Our role is to deliver the engineering inputs you called out so your write-up can reference real data and concrete toggles.

## What we will deliver

1. **Evaluation dataset and harness (Phase 0)**  
   *Build & Measure*: We will assemble the 100-claim evaluation set, implement the replay harness under `backend/tests/evaluation/`, and publish the baseline accuracy report (overall plus easy/medium/hard tiers, calibration, per-claim logs). Once those artifacts are ready we will hand them to you for inclusion in the document.

2. **Feature-flagged pilots (Phase 1)**  
   *Ship with safeguards*: We will add configuration flags and prototypes for the DeBERTa verifier, judge few-shot examples, and cross-encoder reranking. Each flag will stay off by default until the evaluation harness shows at least a +10pp gain on medium claims (or clear wins on hard claims) with <10% latency overhead. We will package latency and cost notes alongside the harness output so you can cite them in the write-up.

3. **Follow-on hooks (Phase 2)**  
   *Prepare, don’t ship yet*: We will stand up the scaffolding for targeted context retries, multi-model judgment, and NLI ensembling, but we will leave them gated until Phase 1 results justify activating them. Any implementation details or rationale for these later phases should come from your document once the metrics are in.

## What we need from you

* Proceed with drafting the full `IMPLEMENTATION_ACCURACY_IMPROVEMENT.md` once we deliver the evaluation artifacts and pilot metrics.  
* Capture ownership assignments, narrative framing, and success criteria in the document—those are in your lane.  
* Keep the feature flags default-off in documentation so product can reference the same rollout plan we enforce in code.

## Next coordination step

We’ll focus this week on the evaluation dataset + harness. As soon as the baseline package is ready we’ll pass you the data so you can finalize the document. Let us know if you need interim schema details or metric definitions while you draft.

—Tru8 Engineering Team