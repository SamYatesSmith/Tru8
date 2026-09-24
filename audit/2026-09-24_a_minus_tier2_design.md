# A− tier 2: design, for review before any build

**Date:** 2026-09-24.
**Status:** DRAFT, awaiting independent review and founder approval.
**Rule:** founder, 2026-09-24. Anything rated difficulty 3 or above is planned and design-reviewed before it is built.

**Parent:** `audit/2026-09-24_a_minus_measurement.md`, which has the checklist, the 19 graded records (`audit/a_minus/`) and the what-if analysis.

## 0. What tier 2 is for

Tier 2 targets four soft or hard checks on the A− list:

| Check | What fails | Records |
|---|---|---|
| H4 | A non-primary source sits in PRIMARY | 11/19 |
| S7 | The claimant's or author's own piece is counted as evidence of itself | 7/19 |
| S4 | The same article on two hosts, or a reprint, is counted twice | 10/19 |
| S1 | A filler element: a trivially true premise | 5/19 |

The what-if puts tiers 1–2 together at about **4/19 A−**. Mapping (tier 4) is what moves it to 12/19. So tier 2 is necessary groundwork, not the prize. Each build below must earn its place on the measured cases, and must not break a tolerance-0 bench pin.

Every mechanism here must be **symmetric** (invariant #7). A rule that only demotes supports, or only challenges, is a direction bias. All four builds act on the SOURCE or the ELEMENT, never on a relationship's direction.

---

## Build A — Primary means primary (H4, 11 records). Difficulty 3.

**Measured kinds**, from the grading files:

| Kind | Examples | Records |
|---|---|---|
| A1 Social post as PRIMARY | Threads "Brilliant Maps" (primary/data) | 4 |
| A2 Off-topic official page in PRIMARY, usually UNMAPPED | World Bank "Trade (% of GDP)"; cordis 2009; sfi.ie; Commons Library GDP; hadea/Copernicus; Open-Meteo 7-day forecast; Lancet smoke | 6, 8, 10, 13, 16, 17 |
| A3 News write-up as PRIMARY | Guardian "according to a Guardian analysis"; ABC; BMJ news piece labelled Academic | 6, 11 |
| A4 Aggregator or page shell as PRIMARY | Statista; EFFIS tracker shell; a Bank of Ireland homepage shell | 10, 12, 17 |
| A5 Campaign NGO release as PRIMARY/official | WWF | 16 |

**Where tier comes from:** `evidence_classifier.py`, batched LLM plus a heuristic, 93.7% on its own benchmark. Tier feeds `_STATE_TIER_WEIGHTS` (primary 3 / reporting 2 / commentary 1). **Every tier change here can move element states**, so it is a scoring change, not a label change.

**Proposed rules.** All are mechanical and applied after classification. Each writes `classification_basis.override` with a receipt.
- **A1 — cap social platforms at `commentary`.** Covers threads, x, twitter, tiktok, reddit, facebook, instagram, linkedin and youtube. Exception: an official account is not detectable reliably, so it gets no exception. Rationale: a post is never the record. Where it carries a record (a screenshot of a filing), the filing is the primary.
- **A3 — cap known news-outlet domains at `reporting`.** Uses the existing news-domain lists used by the classifier heuristic (to be located and verified). A news organisation's own analysis is reporting.
- **A4 — shell detection.** Demote a PRIMARY item whose retained text is boilerplate (below N content words, or dominated by navigation tokens) to `commentary`? **Open question:** alternatively, exclude it with a receipt. It carries no information either way.
- **A2 — off-topic, unmapped specialist-API items.** These are not a tier error: a World Bank page IS primary data, just not about the claim. **Two options, founder call:**
  - (i) Leave them. They are unmapped, so they move no state. Only the tier counts and the ledger show them.
  - (ii) Move unmapped items from specialist adapters out of the shown set, into a receipt-bearing "gathered, not related to any part" group (invariant #5 satisfied by the receipt).
  - Recommended: (ii). The fault lives in the adapters' relevance, and (ii) is honest about that without deleting anything.
- **A5 — campaign NGOs.** No rule proposed. "WWF said X" makes WWF's own release the primary record of the saying, and the interested-party gate already exists for claims about the NGO's own subject. Recommend leaving this to tier 4 (mapping), where the actual fault was: a campaign release filed as a CHALLENGE on a statistic.

**Risks:**
- Tier caps change weights, so an element can move supported → unresolved (floor 3).
- The domain lists must be precise. A cap on `nature.com` news pages must not cap Nature papers. Path-level rules are fragile, so news-domain caps apply only to pure news outlets.

**Measurement before build (free):** apply A1/A3/A4 to the 19 stored payloads offline. Count, per rule, the H4 fails cleared and any state that would change. List each state change for review.

---

## Build B — The claimant's own piece is never evidence of itself (S7, 7 records). Difficulty 3.

**Premise checked, 2026-09-24.** The recital restatement check (`claim_restatement_match`, strengthened by `3c6aff4` the evening of 23 Sep, after most of these records were run) was replayed on the six own-piece rows. **It catches 2 of 6:** The Conversation and youcanknowthings, which state the claim near-verbatim. The other four are:
- Irish Times ×2: the claim paraphrases the column.
- gelliottmorris: a partial quote.
- HSJ: a paywalled 116-char snippet.

So the text-matching path cannot close S7. The pipeline does not know which page the claim came from. **Text submissions carry no `sourceUrl`.**

**Options:**
- **B1 — "Where is this claim from?" (optional URL beside the claim field).** The page is then treated exactly like a URL submission's page: excluded as evidence with a receipt, and its domain-mates tagged (`retrieve._source_exclusion`, which exists and works). Product change. It aligns with the commercial assessment's "author-supplied sources". **Open question:** exclude the page, or keep it visible, labelled "the claim's source", but never directional? Recommended: the latter. The reader sees it and it counts for nothing.
- **B2 — widen restatement matching** (lower thresholds, paraphrase). Rejected. `claim_restatement_match` is deliberately high-precision, and loosening it hides genuine evidence that quotes the claim (invariant #7 both ways).
- **B3 — agent/outreach path:** the recipient's piece URL is known when the record is run. Pass it as B1's field. Free once B1 exists.

**Recommendation:** B1 + B3. No change to the recital gate.

---

## Build C — One article counts once (S4, 10 records). Difficulty 2–3.

**Measured kinds:**
- **C1 — the same article on two hosts or URL forms.** `bbc.co.uk` ↔ `bbc.com` with the same article id; Wiley `/doi/` ↔ `/doi/epdf/`; `bloomberg.com` ↔ `news.bgov.com`; `universityofgalway.ie …reefs` ↔ `…reefs-1`; politicspa on two paths; resultsense tag-index pages. Invariant #1 (URLs tracked globally) is breached in spirit.
- **C2 — syndicated reprints and teasers counted as separate sources on one side.**
  - RocketNews ×5 of Carbon Brief (record 13).
  - AFP on phys.org + courthousenews (17).
  - A Guardian editor's X teaser beside the Guardian scoop (1).
  - A Threads repost of thejournal.ie (8).
  - The existing echo scope gate (Shape B, `ENABLE_ECHO_SCOPE_GATE`) exists to catch C2 and **missed every one of these**. Why is not yet known.

**Proposed:**
- **C1 — canonical URL key before the global URL tracker.** Host aliases (bbc.co.uk→bbc.com, a short explicit list), known URL-form variants (`/doi/epdf/` → `/doi/`), and a trailing `-N` duplicate-slug rule only when the stems match exactly. Duplicates collapse to one item. The dropped URL goes into a receipt on the kept item.
- **C2 — diagnose first, no design yet.** Trace why the echo gate did not fire on RocketNews (identical text, one domain), AFP (identical wire copy) and the X teaser. The answer decides whether this is a threshold, a precondition (e.g. the original must be counted on the same side, or the tier ordering), or text supply (snippet-only reprints). **This sub-item returns to design review with the trace.**

**Risk:** a wrong alias merges two different articles. Keep the alias list explicit and small, and require identical path ids.

---

## Build D — No filler elements (S1, 5 records). Difficulty 3–4.

**Measured:**
- "made a statement or recommendation regarding the government" (Tidman)
- "A study directly compared AI-generated … summaries" (Panthagani)
- "The number of people queuing … changed" (TTE — this one also strips the claim's figure)
- "Sweden chose not to impose a general lockdown" (Sweden)
- e3 restating e1 (heatwaves)

The 2026-09-10 prompt rule (`MATCH THE CLAIM'S OWN SPECIFICITY`) and the premise-element guidance did not stop these. **A prompt-only fix has already failed once (NF-11 lesson).**

**The judgement is not purely mechanical.** "Sweden chose not to lock down" is a real conjunct of a causal claim, uncontested but not false filler. Removing it changes what the page says was examined. Two defensible definitions:
- **(a) Filler = an element entailed by, or restating, another element.** Heatwaves e3 ↔ e1. This is detectable by overlap, and dedup keeps the more specific one.
- **(b) Filler = an element carrying none of the claim's distinctive content** (figures, the contested predicate, named quantities) when a sibling carries it. The TTE and Tidman cases. Detectable: the claim has figures, this element has none, and a sibling has them.

**Proposed:** detect (a) and (b) mechanically at decomposition. Route them through the existing `_repair_questions` repair call to rewrite 1→1, or drop the element when the set stays ≥1 and a sibling covers it. Record `metadata.decomposition.filler_removed`.

**Open question for the founder:** should an uncontested true premise (Sweden) stay, as honest structure? The graders marked it filler because it takes the "Supported" badge and the Notables slot. Recommended: keep true premises, but order elements so the contested ones come first. That is a cheap render or decomposition-order change, not a deletion. Only (a) restatements and (b) figure-stripped duplicates are removed.

**Risk:** the highest in tier 2. It changes decomposition, which re-keys every cassette. It needs a bench re-record and a control arm. Recommend building D last, after A–C.

---

## Order, cost, verification

1. **C1** (smallest, pure dedup).
2. **A1/A3** (domain caps).
3. **A2 option (ii)** if approved.
4. **A4** (shell).
5. **B1/B3** (product field).
6. **C2** (after the echo trace).
7. **D** (after its own review).

For each build:
- A free offline replay on the 19 stored payloads, reporting fails cleared and states changed.
- Unit tests, mutation-checked.
- A bench run for anything that touches the pipeline, with a control arm where retrieval or decomposition changes.

Then one re-run of the 19 inputs (about 19 subscription credits, founder's go) and a re-grade with the same checklist.

## Founder decisions needed

1. A2: show unmapped specialist-API items, or move them into a receipted "not related" group? **Recommended: move, with a receipt.**
2. B1: add an optional "where is this claim from?" URL field? Should that page stay visible but non-directional, or be excluded? **Recommended: add the field; keep the page visible, labelled, weightless.**
3. D: keep uncontested true premises, reordered after contested elements? **Recommended: yes.**

---

## Review outcome: 2026-09-24 (`audit/2026-09-24_a_minus_tier2_review.md`)

**Verdict: APPROVE WITH CHANGES.** Four of the draft's factual claims were wrong, and correcting them changes what gets built. On the 19 records, the draft as written clears H4 on 2/11 and S4 on 2/10. The revised builds clear **H4 on 7/11** (one state change: #12 e2 supported → unresolved, founder to accept) and **S4 on 4/10**.

**Revised builds** (these supersede the sections above):
- **A1:** a social floor already exists. Add `threads.com`, which it misses (`evidence_classifier.py:350`). Do NOT add YouTube.
- **A2:** move EVERY unmapped item out of the PRIMARY band on the page, whatever adapter it came from; only 2 of about 14 offenders were specialist-API items. Label the group **"not mapped"**, not "not related": #2's unmapped rows are on-topic.
- **A3:** reuse `_WIRE_SERVICES` as the cap and add `abcnews.com`. It cannot fix BMJ (#11), which is forced to academic.
- **A4:** REWORK. Shell detection clears nothing that A2 does not; cap aggregators (Statista) instead.
- **A5:** no rule (as proposed).
- **B1:** a separate "where is this claim from?" field, applied as a **mapping-stage** gate with a receipt. `_source_exclusion` drops the page with no receipt, and the evidence cache ignores it.
- **B3:** must pass the claim's **ORIGIN**, never the recipient's piece. On #13 and #15 the recipient's piece is the rebuttal, and making it weightless would be sycophantic.
- **C1:** there are six URL-dedup sites (the recovery path included), not one tracker. The canonical key must go into all of them.
- **C2:** REWORK, now traced.
  - The echo gate only fires when the original is PRIMARY.
  - It compares separately summarised text (RocketNews vs Carbon Brief similarity 0.03–0.11), so reprints never match.
  - It creates false echoes on the claim's own figure: #12's hard fail.
  - New design: a pre-fetch copy key (URL / slug / title) plus a fix to the overlap test.
- **D:** REWORK. `_repair_questions` runs only on opinion (grounds) claims, and none of the five filler records is one. The draft rules flag 8 and 22 elements; rule (b) is right on 3 of 8 and flags #14's contested core. Back to design.
