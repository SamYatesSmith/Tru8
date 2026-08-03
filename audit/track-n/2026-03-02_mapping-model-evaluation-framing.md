# Tru8 — Mapping Model Evaluation Framing

**Date:** 2026-03-02
**Status:** Pre-evaluation design
**Purpose:** Lock down how to run the model-quality comparison so the result is decision-useful.

---

## 1. Why This Comparison Now Makes Sense

The mapper (`claim_map_analyzer.py:295-362`) is the single LLM call that produces every evidence_ref, every relationship label, every reasoning sentence, and every element state. Everything downstream — orientation, landscape, Seeker unknowns — is mechanical derivation from this call's output.

The mapper currently runs on `gemini-2.5-flash-lite` (`config.py:42`), a cost/latency-optimised model. The fallback to `gpt-4o` (`config.py:282`) only fires on provider failure — it's an availability fallback, not a quality gate.

Before investing in architectural changes (element-targeted excerpting, noise reduction, state-semantic tightening), we need to know whether the current model can do the job *at all* with adequate inputs, or whether model capability is itself the primary constraint.

This is the cheapest question to answer and the most consequential. If flash-lite is materially underpowered, then input improvements become compensations. If flash-lite is adequate, the work focuses on inputs and prompts.

---

## 2. What Must Be Held Constant

For the comparison to be fair, the two model runs must differ *only* in which model produces the mapping. Everything else must be identical.

**Held constant:**

| Element | How | Why |
|---------|-----|-----|
| **Input claim text** | Same 25 claims for both models | Eliminates claim-difficulty variance |
| **Decomposed elements** | Pre-decompose once, reuse | The decompose step uses a separate model call (`decomposition_model`, `config.py:278`). Decomposition quality is not what we're testing. Use gpt-4o for all decompositions to ensure consistent, high-quality elements across both runs. |
| **Evidence list** | Same evidence items, same order | Eliminates retrieval variance. Use evidence already retrieved by real pipeline runs. |
| **Evidence text presented** | Same snippet truncation (400 chars) | Tests model reasoning ability on identical inputs. Do NOT increase snippet length for this comparison — that confounds model quality with input quality. |
| **Prompt** | Identical `MAPPING_PROMPT` (`claim_map_analyzer.py:75-109`) | Same instructions, same state definitions, same examples |
| **Temperature** | 0.2 for both (`config.py:284`) | Minimises non-determinism |
| **Max tokens** | 4000 for both (`config.py:285`) | Same output budget |
| **Validation** | Same `_validate_evidence_refs()` and `_parse_mapping_response()` logic | Same post-processing |

**What varies:**

| Element | Flash-lite run | GPT-4o run |
|---------|----------------|------------|
| Mapping model | `gemini-2.5-flash-lite` | `gpt-4o` |
| Provider path | `_call_google()` | `_call_openai()` with `model="gpt-4o"` |

**Claim selection criteria:**

The 25 claims should be drawn from real completed checks and should cover the range of difficulty the pipeline actually encounters:

- ~8 straightforward factual claims (single verifiable assertion, clear evidence exists)
- ~8 multi-element claims (2-4 elements, mixed evidence quality)
- ~5 claims where evidence is tangential or ambiguous (tests state assignment under uncertainty)
- ~4 claims from specialist domains (economic data, legal, health) where precision matters

Pull these from the database: `Claim.claim_map IS NOT NULL AND Check.status = 'completed'`. Each claim needs its associated evidence list (from the `Evidence` table or from the claim's pipeline data).

---

## 3. What Should Be Judged in the Outputs

The evaluation is manual. For each of the 25 claims × 2 models, a human reads:
- the element descriptions
- the evidence snippets
- the model's mapping output (evidence_refs with relationships and reasoning, plus state)

And scores on **four dimensions:**

### 3a. Relationship accuracy

For each evidence_ref, is the assigned relationship (supports / challenges / context) correct?

Score per ref:
- **Correct** — the relationship matches what the evidence actually says relative to the element
- **Defensible** — the relationship is arguable but not the most natural reading
- **Wrong** — the evidence clearly doesn't have the claimed relationship to the element

Aggregate: count of Correct / Defensible / Wrong across all refs for that claim.

### 3b. Reasoning quality

For each evidence_ref, does the `reasoning` field accurately describe what the evidence says and why the relationship applies?

Score per ref:
- **Grounded** — reasoning cites specific content from the snippet and correctly explains the relationship
- **Vague** — reasoning is directionally right but doesn't cite specifics ("this article discusses the topic")
- **Fabricated** — reasoning references content not in the snippet, or misrepresents what the snippet says

Aggregate: count of Grounded / Vague / Fabricated.

### 3c. State correctness

For each element, is the assigned state (supported / disputed / unresolved) the right call given the evidence actually presented?

Score per element:
- **Correct** — the state accurately reflects the evidence-element relationship
- **Overconfident** — state is `supported` or `disputed` but evidence doesn't justify that level of confidence
- **Underconfident** — state is `unresolved` but evidence clearly supports or challenges
- **Wrong** — state is the opposite of what evidence shows (e.g., `supported` when evidence challenges)

### 3d. Evidence coverage

Did the model map all the evidence that should have been mapped, or did it ignore relevant items?

Score per claim:
- **Complete** — all relevant evidence items received refs to appropriate elements
- **Partial** — some relevant evidence items were not mapped to any element
- **Sparse** — significant relevant evidence was ignored

---

## 4. What Would Count as a Meaningful Difference

The comparison is not about perfection. It's about whether the models produce *materially different quality* on the mapping task.

### "Much the same" (flash-lite is adequate)

- Relationship accuracy: both models get ≥80% Correct, <5% Wrong
- Reasoning quality: both models get ≥60% Grounded, <10% Fabricated
- State correctness: both models get ≥75% Correct, <10% Overconfident
- No systematic pattern where one model is consistently better on harder claims

If this is the result: **model is not the bottleneck.** Focus shifts to input quality (Options B, C, D) and prompt tightening (Option E1).

### "Materially better" (flash-lite is the constraint)

- GPT-4o gets ≥15 percentage points more Correct relationships than flash-lite
- GPT-4o produces ≥20 percentage points more Grounded reasoning
- GPT-4o has materially fewer Overconfident states
- The gap is most pronounced on multi-element and ambiguous claims (the hard cases)

If this is the result: **model upgrade is necessary.** The question then becomes cost/latency trade-off — whether to use gpt-4o for all mapping, or an intermediate model (gemini-2.5-flash non-lite, or gpt-4o-mini), or a selective upgrade (use gpt-4o only for claims with >2 elements or >10 evidence items).

### "Mixed" (model matters for some claim types)

- Flash-lite is adequate for simple factual claims (1-2 elements, clear evidence)
- GPT-4o is materially better on complex claims (3+ elements, ambiguous evidence)
- Reasoning quality gap exists but is moderate (10-15 percentage points)

If this is the result: **consider a tiered approach.** Use flash-lite for simple claims (cost efficiency) and a stronger model for complex claims (quality where it matters). Complexity can be estimated from element count and evidence count before the mapping call.

---

## 5. Whether This Now Becomes the Gating Question

**Yes.** This evaluation should gate deeper determination-quality work.

The logic:

1. If flash-lite is adequate (the "much the same" result), the next track focuses on **input quality**: raise snippet length (Option B), reduce noise (Option D1), tighten prompts (Option E1). These are relatively cheap changes that improve what the model sees without changing the model itself. Element-targeted excerpting (Option C) can be evaluated later if input improvements aren't enough.

2. If flash-lite is the constraint (the "materially better" result), the next track **starts with a model upgrade** for the mapping call, then layers input improvements on top. The cost/latency implications need to be worked through, but the quality argument is clear.

3. If the result is mixed, the next track implements **selective model routing** — use the stronger model where it matters — plus input improvements.

In all three cases, the evaluation result determines *what to build next*. Without it, you're choosing between Options B/C/D/E based on intuition rather than evidence. The whole point of Tru8 is that decisions should be evidence-grounded. This one should be too.

---

## 6. Evaluation Mechanics

### Data collection

Build an evaluation harness that:

1. Accepts a list of claim IDs (from completed checks in the database)
2. For each claim, extracts: normalised claim text, decomposed elements, evidence list with full text/snippets
3. Constructs the identical mapping prompt that `map_evidence_to_elements()` would build
4. Sends the prompt to flash-lite and gpt-4o separately (sequentially, to avoid rate issues)
5. Records both raw JSON responses and the parsed/validated output
6. Writes results to a structured output file for human scoring

### Output format

Store results in `backend/audit/track-n/evaluation/` with:

```
evaluation/
  claims.json           # The 25 selected claims with evidence
  results_flash_lite.json   # Raw + parsed mapper output per claim
  results_gpt4o.json        # Raw + parsed mapper output per claim
  scoring_sheet.json        # Human scores (filled in manually)
  summary.md                # Final analysis and recommendation
```

Each result file per claim should contain:
- `claim_id`, `normalised_claim`
- `elements` (the decomposed elements used as input)
- `evidence_items` (the evidence list used as input, with the 400-char truncated text)
- `prompt` (the exact prompt sent to the model — for reproducibility)
- `raw_response` (the model's JSON output before validation)
- `parsed_output` (after `_parse_mapping_response` / `_validate_evidence_refs`)
- `model_used`, `token_usage`

### Human scoring

The scoring sheet should be a JSON file with one entry per claim per model, containing:
- Per evidence_ref: `{evidence_id, relationship_score, reasoning_score}`
- Per element: `{element_id, state_score}`
- Per claim: `{coverage_score}`
- Free-text `notes` field for qualitative observations

### Timeline

This evaluation should be completable in 2-3 sessions:
- Session 1: Build harness, select claims, run both models (~2-3 hours engineering)
- Session 2: Human scoring of 50 outputs (25 claims × 2 models) (~3-4 hours reading)
- Session 3: Compile results, write summary, make recommendation (~1-2 hours)

The engineering work is small. The human evaluation is the real cost, but it's a one-time investment that determines the direction of the next track.

---

## 7. What This Evaluation Does NOT Answer

This comparison tests model capability on the mapping task with **current inputs** (400-char claim-level snippets). It does not test:

- Whether longer snippets would help either model (that's a follow-up evaluation if the model is adequate)
- Whether element-targeted excerpting changes the picture (that's Option C, after A)
- Whether different prompt wording improves results (that's Option E1, independent)
- Whether noise reduction helps (that's Option D, independent)

Each of those is a separate, smaller evaluation that can be run after this one. But this one comes first because model capability sets the ceiling for everything else.
