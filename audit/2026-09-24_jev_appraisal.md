# Jev appraisal — could TypeSafe's "System One" model help the Tru8 pipeline?

2026-09-24. Desk appraisal only. No API call was made and nothing was spent.

## 1. What Jev is (from public sources, a week after launch)

- **Vendor:** TypeSafe AI (the founder wrote "Typeface"; the company is TypeSafe). Released 15 Sep 2026 in limited early access (waitlist), with a $40m seed round. It can also be reached through the Vercel AI Gateway with no waitlist.
- **It generates no text.** It returns typed decisions with probabilities:
  - **Choice:** pick one of ≤255 options.
  - **Score:** a rubric of ordered levels.
  - **Noul:** yes/no, returned as a probability.
  - Through Pydantic AI it also covers multi-select, `dict[Enum,bool]`, optional pick and nested models. `str`, unbounded numbers and `datetime` are **refused**.
- **Speed and cost:**
  - 70–500 ms per request, and many questions in one request take about as long as one.
  - $0.042 per 1M input tokens; output is free.
  - The vendor's 40–400× claims come from benchmarks its own team wrote, and it "cannot prove the price is unsubsidised".
- **Limits:**
  - Context is 64k tokens for state plus questions, and 32k for state plus the longest question.
  - No temperature. Option order can change the answer.
  - Retries return the same answer. No streaming.
- **Stated weaknesses** (Pydantic docs, Willison):
  - **Numbers, dates and counting.**
  - Multi-hop reasoning.
  - **Adversarial or injected content.**
  - **No explanation:** a number with no reason attached.
  - Compound questions give confident-looking guesses.
- **Unknowns:** no paper, no weights, no parameter count, nothing on data residency. The vendor is a seed-stage company, one week old.

## 2. Where Tru8 spends LLM calls, and the fit for each

| Stage (call site) | What it returns today | Jev fit | Why |
|---|---|---|---|
| EXTRACT `extract.py:907`, synthesis `:1219` | claim text | **None** | Generates text |
| Article classification `article_classifier.py:1103` | domain / jurisdiction labels | **Good** | A pure Choice |
| SELECT / rank `claim_selector.py:159` | ranking | **Fair** | Score per claim, but SELECT's open fault (the composite endpoint) is a decomposition problem, not a ranking one |
| Query planner `query_planner.py:456` | search queries | **None** | Generates text |
| DECOMPOSE + grounds + repairs (`claim_map_analyzer.py`, `opinion_symmetry.py`) | element questions | **None** for generation | Generates text |
| Detectors beside decomposition (atomicity, unstated quantity, direction fidelity, evaluative head, normative hint) | lexical yes/no | **Strong candidate** | These are yes/no judgements now made by regex. Memory records "a blocklist cannot close an open set" and a noisy normative boundary (P13/P18). Jev would detect; the existing repair call would still rewrite. |
| RELEVANCE `relevance_scorer.py:362` | 1–5 per item, up to 50 items | **Good** | A textbook Score. Today it is one large JSON call with a 60 s timeout. |
| CLASSIFY `evidence_classifier.py:1063` | tier × type | **Good, low gain** | A Choice, but the heuristic is already 93.7% accurate. The known variance (2 of 16 tiers flip on an identical pool) might fall, since Jev has no sampling. Needs measuring. |
| DISTIL `evidence_distiller.py:287` | fact sentences | **None** for output, **fair** as a filter | Cannot write facts. Could choose which retained windows reach the distiller (a noul per passage × element), the stage that starved the mapper on 22 Sep. Now partly covered by the mechanical supply floor. |
| MAP `claim_map_analyzer.py:2299` | supports/challenges/context per evidence × element, **with reasoning** | **Poor as a replacement, useful as a second rater** | See §3 |
| Scope review (flag off) | demote-only | Fair | A Choice, but it is under a flag that stays off |
| Fix 1 verdict-language gate (public caveats) | fail-closed lexical | **Strong candidate** | "Does this sentence adjudicate?" is one noul. It would also fix the case where the gate hides a negated limit ("confirm" inside a limit). |
| VIDEO recommender | no relevance floor | **Strong, low risk** | "Is this video about this claim?" as a noul. Fixes observation 5: off-topic videos on public records. |
| COMPARE `comparison.py:347`, query answer `query_answer.py:192` | prose | **None** | Generates text |

## 3. Why Jev must not replace the mapper

1. **Receipts.** The gates read the mapper's `reasoning`:
   - the figure gate uses it for `rests_on_a_figure`;
   - the recital gate uses it for the "confirms" veto.

   Every reference carries a reason (invariant 5). Jev returns no reason, so the gates would lose their input and the reader would lose the receipt.
2. **Its weaknesses are exactly our open failures.** Kennedy and Legum failed on numbers, dates and summed part-periods. Jev's documentation names numbers, dates and counting as weak points.
3. **Evidence is untrusted web text.** "No adversarial resistance" means a page could steer its own relationship label.
4. **Probabilities must never reach the reader as scores** (invariant 6, classify don't score). They may drive internal routing only.

**As a second rater:** run Jev beside Gemini on every (element, evidence) pair. That is about 200 questions per claim, at a fraction of a penny. Where they disagree with high confidence, flag the pair, re-map it, or hold the record from outreach. This targets the variance traced on 11 Sep and the correctness gate the send procedure lacks (OPEN_WORK item 2), without changing a single state by itself.

## 4. What Jev does not do

- **Nothing for the 16 Oct Gemini 2.5 deadline.** Every text stage still needs an LLM.
- **Money is not the prize.** A check costs about 1.2p, and the classify and relevance calls are a small share of that. The possible gains are **latency** (relevance about 7.5 s serial; classify about 2 s, hidden behind distil; see §6), **determinism** (no sampling) and **cheap brittle detectors turned into calibrated ones**.
- **Vendor risk.** One week old, early access, no data-residency statement. Any use must pin a version (`jev-1.13.0`, never `jev-latest`) and fall back to the current path. That is the same pattern as today's Google → OpenAI chain.

## 5. Recommendation

Do not adopt Jev for any production stage yet. Run one small offline evaluation on stored records. It costs pennies of Jev API, and the ask-before-spending rule applies.

1. **Verdict-language gate:** Jev noul vs the current lexical gate on the stored caveat corpus. Count what the lexical gate leaks and what it wrongly hides.
2. **Video relevance:** a noul on the stored video cards from the 21 Sep batch, where the off-topic ones are known.
3. **Mapping second rater:** replay the 66 stored records. Does high-confidence Jev disagreement land on the known-wrong references (Legum, Kennedy, TTE)?

It is worth a build only if (3) finds the known errors with few false alarms. That would make it the correctness gate the outreach procedure lacks. (1) and (2) are small public-surface fixes either way.

## Sources
- https://pydantic.dev/docs/ai/models/typesafe/ (types, limits, context, behaviour caveats)
- https://simonwillison.net/2026/Sep/21/jev/ (pricing, numbers/dates/adversarial weakness)
- https://en.wikipedia.org/wiki/Jev_(AI_model)
- https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/ (benchmark caveats, availability)

## 6. Predicted gains (added 2026-09-24, unmeasured; each is a prediction for the offline test to confirm or kill)

Baselines are measured (`audit/2026-07-02_pipeline_timing_context.md`): full check about 60 s (p90 63 s on 2026-09-09) · relevance about 7.5 s, serial · classify about 2 s per batch, running concurrently with distil (about 10 s), so it is off the critical path · check cost about 1.2p.

| # | Use | Physical gain (predicted) | Level /5 | Confidence |
|---|---|---|---|---|
| 1 | Mapping second rater | Flags some wrong references before a record ships. If it works, it catches a share of known-wrong references (Legum, Kennedy, TTE class) and could have held about 1–2 of the 4 flawed wave-1 records. Cost +0.2–0.3p per claim, +0.5 s in parallel | 4 if it works | Low (30–40%). Jev is weak on numbers, and those errors were numeric |
| 2 | Video relevance floor | Off-topic videos seen on 2 of 12 records (21 Sep) → most removed. About 15% of public records get cleaner | 2 | High |
| 3 | Verdict-language gate | Fewer verdict leaks onto public pages and fewer hidden limits (Turns, Taylor). Unmeasured count, probably a few per 10 records | 2–3 | Medium |
| 4 | Relevance scoring | About 7 s off a 60 s check (−12%). Removes a 60 s timeout risk | 2 | Medium (the 1–5 rubric fits; quality needs a match test) |
| 5 | Opinion / evaluative detectors | A noisier boundary (P13/P18) made steadier. Atomicity and quantity already read 0% after fixes, so little left there | 1–2 | Medium |
| 6 | Classify | 0 s wall-clock (hidden behind distil). Possibly fewer tier flips on replay (2 of 16 today) | 1 | Low |
| 7 | Cost | Under 0.1p saved per check; #1 would ADD about 0.25p | 0 | High |

**Total if all hold:** about 7 s faster (60 → 53 s), cleaner public pages on about 1 in 5 records, and possibly a correctness screen for outreach. No money saved. The only item worth a real build is #1, and it is also the least likely to work.
