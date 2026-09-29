# Brief for the next session: PRIMARY means originator (classification, class D)

**Written:** 2026-09-29, end of day, for the agent picking this up on 2026-09-30.
**Founder's instruction:** "We'll do the classification with tomorrow's agent."
**Status:** nothing designed or built yet. This is difficulty ≥ 3, so the first deliverable is a DESIGN, then an independent review, then founder approval, and only then a build.

## 1. The goal, stated the founder's way
Raise the pipeline in general. Do not target the outreach records.
- The 19 A− records (`audit/2026-09-24_a_minus_measurement.md`) are how we FIND fault classes. They are not the target.
- A fix must be a general mechanism. Lists of hosts or organisations tuned to what those 19 records contained are the failure mode to avoid.
- Judge the fix on data it was not tuned on.

(Memory: `feedback_general_quality_not_outreach_set.md`.)

## 2. The fault
**H4: "weak source in PRIMARY" was the largest hard fail on the 28 Sep re-measure (10 of 18 records).**
- Round 2 (`b7a3d8f`, 28 Sep) fixed the mechanical classes: trackers, reference adapters, shortlinks, unrendered templates, and the URL-identity override raising a news story.
- What remains is **class D**: the LLM classifier calls a **non-originator** primary. Examples from the re-run pools:
  - KFF explainers (×2);
  - hcttf (a trade coalition);
  - a UnitedHealth white paper;
  - an off-topic AAP article;
  - lloydsbanktrade.com (a commercial country-profile page quoting EU Commission forecasts);
  - a libretexts course page.
- No mechanical signal catches these today.
- Evidence and classes A–E: `audit/2026-09-28_primary_tier_review.md`. Read it first.

**Founder decisions already made. Do not re-open them:**
- Unmapped rows KEEP their tier badge (28 Sep), so class D must be fixed in the classifier, not by hiding the label.
- Tier describes proximity, not quality (invariant #6, "classify, don't score").
- "Primary only where publisher identity proves it" was **simulated and rejected** (§ "Rejected" in the tier review). It demoted about 12 genuine primaries (cso.ie ×3, oecd.org, centralbank.ie, thirlwall inquiry, globalcarbonbudget, esawebb, university repositories…) and the patterns are too UK/US-centric. Don't rebuild a whitelist.

## 3. The idea to design (a direction, not settled)
**Primary = the source ORIGINATED the finding:** its own data, its own study, its own official record or decision. A page that explains, summarises or republishes someone else's figures is not primary, however official it looks.

The design must answer:
1. **Signal.** What tells originator from relayer without a host list?
   - Candidates: the text cites another body as the source ("according to…", "data from…", "the Commission forecasts…"); the publisher is not the body named as producing the figure; the page type (explainer / FAQ / course page / country profile).
   - Consider asking the classifier model for the originating body and comparing it with the publisher. Structured output, fail-closed.
2. **Direction.** It is **lower-only** (primary → reporting/commentary), as Build A and round 2 are. It never promotes.
3. **Must-survive set.** The 12 genuine primaries above must stay primary. So must JRC, CSO, Cook's own poll page, NASA, OWID, whereyourmoneygoes.gov.ie, and the not-demoted list in the tier review.
4. **State effects.** Tier feeds `_STATE_TIER_WEIGHTS`, so a tier change can change element states. Report every state change, in both directions.

## 4. Code map
All in `backend/app/pipeline/evidence_classifier.py` (1,275 lines):

| Symbol | Line | Role |
|---|---|---|
| `CLASSIFICATION_SYSTEM_PROMPT` / `_USER_PROMPT` | ~48 | The LLM prompt. Tier definitions live here. |
| `_ACADEMIC_PATTERNS` | ~271 | URL identity for academic hosts |
| `_REFERENCE_PLATFORMS` | ~376 | Wikipedia/YouTube reference floor (round 2) |
| `_classify_heuristic` | ~455 | Heuristic fallback |
| `_high_confidence_override` | ~547 | URL-identity overrides of the LLM verdict |
| `_AGGREGATOR_HOST` | ~634 | 2-host aggregator cap |
| `_apply_primary_cap` | ~692 | Lower-only caps: news → aggregator → shortlink → identity exemption → unrendered → tracker |
| `_keeps_news_verdict` | ~741 | Round 2: the identity override never raises an LLM *reporting* verdict on bmj/nature/science |
| `classify_batch` | ~887 | Batch entry point; also runs the round-2 `tracker_host_cap` pool pass |

Tests: `tests/unit/pipeline/test_e06_classifier.py` (round 2 added 25, including a wiring test through `classify_batch`). Existing accuracy script: `backend/scripts/eval_classifier_accuracy.py` (100 hand-labelled items; `--heuristic-only` is free).

## 5. Data you can use
- **The 18 re-run pools** (28 Sep, production `9aff4ea`). Grades are in `audit/a_minus/2026-09-28_rerun/` (8-char check-id prefixes).
  - Full ids come from `GET /api/v1/checks?limit=N` with the founder's key.
  - The public payload (`GET /api/v1/checks/public/{id}?detailed=true`) needs no key, but it 403s Python's default user-agent, so set a `User-Agent`.
  - The founder authorised using the key from `~/.claude.json` on 29 Sep. Read it inside scripts and never print it.
  - The helper pattern is in the 29 Sep session scratchpad; it is simple to rewrite.
- **Held-out data for this fault:** none is labelled for tier yet. Plan one, e.g. label PRIMARY items from pools the fix was not tuned on: the 9 Astra regrade runs in `tmp/astra-regrade-*/<record>/owner.json`, which are free and local. Label blind if you can.
- **Replay on stored pools** (tier caps without the LLM) is how round 2 measured "14 tier changes, 0 state changes". Do the same.

## 6. Rules that bite
- **Ask the founder before EVERY paid run**, however small. State the estimate first. Measure costs; don't guess. On 29 Sep a "3p a call" guess was 4× too high.
- **Replay bench before any pipeline-quality commit:** `cd backend && python scripts/replay_bench.py --all`, with `docker-compose up -d` first.
  - Current state: `139 ok / 8 warn / 11 fail / 5 unexercised` + known drift on 5647 and 82CF. **93DD also drifts in `--all` runs but replays clean alone. That is noise; confirm by running it singly.**
  - The canonical record is the header of `tests/replay_corpus/README.md`.
  - **Tier changes can re-key cassettes; use a control arm** (the same run with your change off) before attributing any difference.
- Use `--record-missing` to patch cassettes. Order-sensitive prompts may need **two passes** to converge. Never commit raw `--update-golden` output.
- Unit suite: `pytest tests/unit -q --no-cov -p no:warnings`. It was 4,268 passing at the end of 29 Sep, about 80 s with Docker up and about 11 min without.
- **Mutation-check every new rule.** Remove it, and a test must fail.
- **Verify live before calling it done.** On 29 Sep the relationship review passed a held-out eval and then failed its first live check. Real text has shapes your labels don't.
- Replies to the founder: short, plain, one decision at a time (global CLAUDE.md).

## 7. What changed on 29 Sep (so nothing surprises you)
- **A1′ recital instrument skip is live** (`7592e42`): "according to the toplines" and "the poll said" are no longer recitals.
- **The relationship review is ON by default** (`43c757a`): supports only, `RELATIONSHIP_REVIEW_MODEL=gemini-3.7-flash`, demote-on-unknown, 40 s per call, about 1p per check.
  - It was rolled back once the same day after a parser fault. The fixes are in `ac071e6`: year ranges are not counts, and a silent count never demotes.
  - Two live checks pass. **Watch its demotions on real checks** (`claimMap.metadata.scopeReview.pairs`).
- **Figure parser (`app/utils/figure_scope.py`):** year-range tails are not counts, and a function word after a number ends the counted phrase.
- **Parked, waiting on the founder:**
  - A2, the measuring-organisation release. Extraction's `claimant` cannot separate a central bank from a campaign, so a new extraction field is needed.
  - Family B, the sibling re-offer.
- **Housekeeping:** `backend/.env` holds a LIVE Stripe key. The config guard discards it; the founder has been told.
