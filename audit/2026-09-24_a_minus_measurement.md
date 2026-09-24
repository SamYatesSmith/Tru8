# A− measurement: how often does a record meet the bar a £20/month user expects?

**Opened 2026-09-24 (founder decision): sends are held until the A− rate is known and rising.**
Founder: *"For £20 pm I feel like users will accept a minimum of A−."* Of the 16 outreach records graded between 11 and 24 Sep, **none reached A−** (four B+, the rest B or below). The badges are now mostly right; the grades are lost around them.

## Method
1. **Grade set:** 19 stored public records. Each is graded from the public payload and the rendered `/r/` page. Nothing is re-run, so it is free.
2. **Blind grading:** graders do not read `audit/recipients/`, where the earlier outreach grades live.
3. **Attribution:** every deduction names one pipeline stage from the taxonomy below.
4. **Tally:** sum the deductions by stage. Fix the largest buckets first, then re-measure the same set. Re-measuring needs re-runs of the same inputs: about 19 subscription credits, founder's go.

⚠️ The 19 records span builds from 11 to 23 Sep. Some predate the supply fix (22 Sep) and the figure gate (23 Sep). This baseline measures **stored** quality. The current-build rate needs the re-run in step 4.

## The A− checklist

**Hard checks.** Any failure caps the record at **B**:
- **H1 Badges right.** Each element's state is what a careful reader of the retained sources would give it.
- **H2 No wrong directional reference.** No source is filed supports/challenges when its own text, as a reader sees it on click, does not bear that way. Wrong figure, period or scope all count.
- **H3 The authoritative source is present,** where one publicly exists for the claim (official register, filing, results page, the study itself). If it is absent and the record does not say so, it fails. If it is absent and a gap card names it, that counts as S-level (S9).
- **H4 Primary means primary.** No social post, tracker shell, off-topic official page, or news story in the PRIMARY tier.
- **H5 Summary agrees with the states.** The headline, orientation line and counters must not contradict the element badges (e.g. "evidence is mixed" with zero challenges).

**Soft checks.** Each failure costs one notch:
- **S1** No filler or trivially true premise element.
- **S2** Every unresolved / disputed / contextual card says why, on the page.
- **S3** The Notables headline source is the best supporting source for the claim.
- **S4** No duplicate hosts of one article; no echo counted twice.
- **S5** No off-topic rows (video, unrelated pages).
- **S6** No surface warts: raw HTML, relative dates ("6 days ago"), counters that disagree with each other, withheld interpretations on most rows.
- **S7** The claimant's or author's own piece is filed correctly: not as evidence of itself, and not mislabelled.
- **S8** A known rebuttal is found, where one exists.
- **S9** A missing authoritative source is named on the page (only if H3 was satisfied by disclosure).

**Grade:**

| Grade | Hard checks | Soft failures |
|---|---|---|
| **A** | all pass | 0 |
| **A−** | all pass | 1 |
| **B+** | all pass | 2–3 |
| **B** | one fails | or 4+ soft failures |
| **B−** | two fail | — |
| **C** | three or more fail, or the claim is mis-stated | — |

## Stage taxonomy (for attribution)
`extract` · `decompose` · `retrieve` (discovery: what never entered the pool) · `classify` (tier/type) · `map` (relationship) · `scope_gates` (a gate fired wrongly or missed) · `summary` (orientation, headline, counters) · `notables` · `video` · `render` (surface, cards, text).

## The 19 records
| # | Record | Claim / origin |
|---|---|---|
| 1 | `cb939365-6b57-4eee-a5fc-fc890016c43e` | Anapol (wave 1) |
| 2 | `e6e0c00d-17b4-4d9a-88c2-cf42b734daef` | Buck |
| 3 | `8a615dfc-6713-4bc4-a460-d02bdc7ad248` | Burke-Kennedy |
| 4 | `bff4f803-9ea8-489c-a703-03d518936579` | Katz (re-run 23 Sep) |
| 5 | `75ef5e70-3ea5-4ba7-8aaa-233527183a53` | Kennedy (re-run 23 Sep) |
| 6 | `26699bc7-e335-48d4-83e1-8ef571502252` | Legum (re-run 23 Sep) |
| 7 | `70ad9e13-f7e8-422c-8500-17e11c09c874` | Morris |
| 8 | `48fb0f58-1d2f-4aeb-a548-dad201188ae1` | O'Doherty |
| 9 | `81fc137d-7f27-4d6b-81da-66942e85aa69` | Panthagani |
| 10 | `1c90a8bb-0729-407a-b600-f86698327be3` | Taylor |
| 11 | `1ccc0eb9-7fc0-4b88-8ccf-9beab4d55874` | Tidman (re-run 23 Sep) |
| 12 | `b8cf098b-de0e-4cb1-902b-bd4571121b1c` | Turns |
| 13 | `bebfa026-8af6-429c-ae92-a403d9040be9` | McSweeney (wave 0) |
| 14 | `1ca0070f-5bdf-43c3-8470-0e09a463e17e` | Tapper |
| 15 | `a57b5494-faf9-481d-bea3-e7d41005e676` | TTE |
| 16 | `441144ac-499c-414f-8323-fc802c5092ed` | Viglione |
| 17 | `580fd5b4-82c5-44f3-ace7-dbaab4c812bd` | Seymour |
| 18 | `540481b1-c52c-4e8d-bdfe-3e49b8f12544` | JWST (Substack post 1) |
| 19 | `6ad65eb5-678f-40e2-830c-1c6179c3f315` | Sweden (Substack post 2) |

## Results
Per-record grading files: `audit/a_minus/<n>_<shortid>.md`. Tally below once all four graders report.

**Baseline, 2026-09-24: 0 of 19 at A−.** Grades: B+ 1 · B 5 · B− 5 · C 8. All 19 grading files were checked against their own record's claim text: 19/19 match, so the shared scratch folder did not cross any wires.

**Failures by check** (number of records, out of 19):

| Check | Records | What fails |
|---|---|---|
| S6 | 15 | counters disagree |
| S3 | 14 | wrong Notables headline |
| H2 | 13 | wrong directional ref |
| S5 | 13 | off-topic rows |
| S2 | 11 | card gives no reason |
| H4 | 11 | weak source in PRIMARY |
| S4 | 10 | duplicate hosts / echo |
| S7 | 7 | claimant's own piece counted |
| H1 | 6 | badge wrong |
| H3 | 6 | authoritative source missing |
| S1 | 5 | filler element |
| H5 | 3 | headline contradicts states |
| S8 | 1 | rebuttal missed |

**By stage** (total deductions / hard deductions / records touched):

| Stage | Total | Hard | Records |
|---|---|---|---|
| map | 24 | 15 | 16/19 |
| retrieve | 22 | 6 | 17/19 |
| render | 13 | 0 | 9/19 |
| notables | 12 | 0 | 12/19 |
| summary | 12 | 3 | 11/19 |
| classify | 12 | 11 | 12/19 |
| scope_gates | 11 | 3 | 8/19 |
| decompose | 6 | 1 | 6/19 |
| video | 3 | 0 | 3/19 |

**What-if (fixes assumed perfect; this is a ceiling, not a forecast):**

| Tier | Fixes | Records at A−/A |
|---|---|---|
| 1 | Surface: counters, card reasons, headline, Notables, video floor | 1/19 |
| 2 | + primary-tier floor, claimant's own piece never evidence of itself, host dedup, filler elements | 4/19 |
| 3 | + scope-gate misfires (interested-party on attribution claims, "Q3" periods) | 4/19 |
| 4 | + mapping: wrong directional refs and wrong badges | **12/19** |
| — | Remaining 7 | Blocked by retrieval: missing authoritative source, off-topic rows |

**Reading.** Mapping is the binding constraint: until wrong refs stop, no amount of surface work gets past about 4/19. The cheap mechanical tiers still matter, because every record needs them before mapping fixes can show. Retrieval sets the final ceiling, at about 12/19 on this set.

## Tier 1 — built 2026-09-24 (uncommitted at time of writing)
| Fix | Check | Status |
|---|---|---|
| "Evidence is mixed" only when an element is disputed, or supported beside challenged (`derive_orientation`) | H5 | Built. Applies to **new checks only**: orientation text is stored at run time |
| "N bear directly" = sources filed supports/challenges (same join as the bar); element coverage + Gaps link use the Gaps lens's own definitions ("1 gap · 1 needs review"); Reviewed never below Organised; `cleanTitle` strips markup, `[PDF]` and "- YouTube" | S6 | Built, frontend, applies on read to every record |
| "Why ·" line on every unresolved / contextual / disputed card, from `state_derivation` counts, never model text (`lib/element-reason.ts`); passes the no-verdict gate by test | S2 | Built, frontend, on read |
| Video relevance floor: title + description must share max(2, 25%) of the claim's content words, capped at the claim's own word count | S5 (video) | Built, backend, new checks. 9/9 stored videos classified right (2 kept, 7 dropped) |
| Notables re-ranking | S3 | **Dropped after measurement.** Five variants (elements-count, tier, social exclusion) scored against the source each grader named: best 6/12, identical to the current rule; the one first built scored 5/12 (it promoted Warren's press release and a parenting site). Notables misses come from the best source not being filed as support (map) or being mis-tiered (classify), so it moves to tier 2/4 |

Verification: frontend 208 tests pass + typecheck clean; backend unit 3,945 pass / 44 skipped; orientation and video changes mutation-checked; rendered locally against the prod API on Legum, Kennedy and JWST.


## Tier 2 — Build A (primary means primary), built 2026-09-24
Design: `audit/2026-09-24_a_minus_tier2_design.md`. Review: `audit/2026-09-24_a_minus_tier2_review.md` (APPROVE WITH CHANGES). Founder-approved, including the #12 state change.

**What was built:**
- `_SOCIAL_MEDIA` gains `threads.com`, `linkedin.com` and `bsky.app`.
- A host-anchored last-pass cap, primary → reporting, for `_WIRE_SERVICES` news outlets (plus `abcnews.com`) and for aggregators (statista, tradingeconomics). Methods `news_outlet_cap` / `aggregator_cap`. Lower-only.
- **Frontend:** items mapped to no element leave the tier bands. They are listed in a visible, counted "Gathered — not mapped to any part of the claim" group, and the digest footer counts tiers over mapped sources plus "N not mapped".

**Replay on the 19 stored payloads:**
- 7 items change tier (#6 ×2, #8, #3 ×2, #12, #4).
- One state change: #12 e2 supported → unresolved, as approved.

**Bench:**
- Build A vs a control arm (the same bench without the classifier change):
  - Build A re-keys TRU-C1A0-0001 and 0005, as predicted. Both were patched with `--record-missing` and replay cleanly: 0001 19/0/0; 0005 18/0/3, the same three fails as the control.
  - 0005's `temporal_scoped_refs` pin is UNEXERCISED in BOTH arms, because the off-period gianlucabenigno source is absent from the pool. This pre-exists Build A.
- 82CF and 93DD drift in both arms, the known order-dependent drift.
- **Found, not Build A:** 018F `recital_scoped_refs` is off by 1 in both arms whenever 018F replays. Most likely `3c6aff4` (the recital claim-wording path, 23 Sep). Owed: re-pin after inspection.

**Tests:** classifier tests pass and are mutation-checked; frontend 211 pass plus typecheck.

**Grader note.** Harsher than the outreach passes: Katz B → C, Kennedy B → B−, Legum B → C. They are consistent across graders on the same faults. Treat the absolute grades as strict and the relative buckets as the finding.
