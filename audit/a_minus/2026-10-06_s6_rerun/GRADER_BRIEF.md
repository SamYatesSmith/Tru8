# Grader brief — A− re-measure 3 (2026-09-30)

You grade ONE Tru8 record against the A− checklist below and write one file. You are one of several blind graders.

## Blindness (breaking any of these invalidates your grade)
- Do NOT read: `audit/recipients/`, any file in `audit/a_minus/` other than this brief, `audit/2026-09-24_a_minus_measurement.md`, `audit/2026-09-30_a_minus_remeasure_plan.md`, `audit/OPEN_WORK.md`, or any design/review doc in `audit/`. They contain earlier grades or the fixes' intentions.
- Do not read other graders' files in this folder.
- Grade what the page shows a reader, not what the pipeline intended.

## What you read (adapted 2026-10-06: LOCAL pipeline runs)
- **Owner payload:** `audit/a_minus/2026-10-06_s6_rerun/payloads/<name>.json`, the full owner response for the check, saved from the LOCAL pipeline. It is large, so query it with Python. Each element's `evidenceRefs[].reasoning` and each evidence row's fields are what a reader sees on click.
- There is no public payload or rendered page for these runs. Grade surface checks (S6) from the payload's own text: titles, dates, captured text, counters, notes and reasoning. **Videos were not run in this harness. Do not fail or pass S6 on videos; say "videos not in scope".**
- **The open web** (search and fetch) to judge H1, H3 and S8: is the claim true, does an authoritative source exist, is there a known rebuttal.

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

## Output
Write `audit/a_minus/2026-10-06_s6_rerun/<n>_<first 8 chars of the check id>.md` in exactly this shape:

```
# #<n> <8-char id> — <short claim>, re-run 6 Oct (local)

Graded 2026-10-06, blind, from the saved owner payload.

**Claim as analysed:** "<claim text>" (Faithful / not faithful to the input, and why.)

**Element states:**
- e1 <description>: **<State>** (<n> supports, <n> challenges, <n> context)

## Hard checks
- **H1 PASS/FAIL (<stage>).** <evidence, quoting source text>
- **H2 …** · **H3 …** · **H4 …** · **H5 …**

## Soft checks
- **S1 … S9** PASS / FAIL (<stage>) / N-A, each with one line of evidence.

Also noted, with no check failed: <anything a maintainer should know>

## Grade: **<A/A−/B+/B/B−/C>** (<hard fails>; <soft fails>)

**Single change that would most lift this record:** <one sentence>
```

Rules: every FAIL names exactly one stage from the taxonomy; quote the source text you relied on; when unsure between PASS and FAIL, say so and pick the reading a careful paying reader would take.
