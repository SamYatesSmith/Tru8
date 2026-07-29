# FP-01 — Academic / thesis research pipeline

**Date:** 2026-07-27
**Status:** ANALYSIS ONLY. Nothing committed. Cheap slice specced in §8; full build gated on §9.
**Question asked:** can we build a pipeline off what we already have that helps a student or academic
research a thesis or a proposed area of exploration — and is that a market for Tru8, or a partner product?

---

## 1. Short answer

**Yes to the pipeline — ~70% of it already exists.** The decompose stage, the grounds stage, the
Seeker, tier/type classification and the supports/challenges/context mapping are, between them, most of
a research-scoping tool. Three new pieces and a handful of config changes would get there.

**No to students as the buyer.** Undergraduates have no budget, need it for eight weeks once, and
predominantly want the one thing Tru8 refuses to do. PhD students are the best *users* but already have
institutional Scopus/Web of Science plus Elicit, Consensus, Scite, Research Rabbit and SciSpace — funded,
cheap, and holding the corpus Tru8 doesn't have.

**The thing worth testing is a different sale.** Tru8's differentiator here is not search, it's
**pedagogy**: a research tool that mechanically cannot agree with you. Every university is currently
anxious that AI flatters students. We have spent a month building a system that structurally can't
(evaluative-head detection, neutral grounds, mechanical orientation, no verdicts). Nobody in the
Elicit/Consensus cluster has that or wants it. That points at an **institutional or partner sale**
(academic-skills units, libraries, supervisors, academic-integrity vendors), not B2C students.

---

## 2. What already transfers

| Existing asset | Where | Thesis equivalent |
|---|---|---|
| Claim → 1–5 testable elements | `claim_map_analyzer.py` (DECOMPOSE) | Research question → investigable sub-questions. The thing students do worst. |
| Grounds stage — neutral open questions from evaluative claims | `opinion_symmetry.apply_grounds_stage` | Turning a value-laden thesis statement into questions that don't presuppose the answer. That is supervision meeting one. |
| Question-as-claim extraction | `extract.py` rule 9 | The input mode is already there — a question is accepted and made affirmative *without editorialising*. |
| Question typology | `claim_map.py::ClaimType` — `empirical / definitional / causal_interpretive / predictive / normative_flagged` | A ready-made classification of what *kind* of question the student is asking. |
| Scope tagging | `scope_sensitivity.py` — `{geographic, universal}` | "Your question says *all* / *first* / *only* — that's not establishable." Standard supervisory correction, already mechanical. |
| Seeker + `bounty_text` + targeted re-search | `re_search.py`, `evidence-views/seeker/` | Gap finder. Unresolved/thin sub-questions = candidate contributions. `bounty_text` is already a research-gap statement in all but name. |
| Tier × Type classification | `evidence_classifier.py` | Source criticism — assessed at every level from GCSE coursework to viva. |
| supports / challenges / context per element | mapping stage | "The literature is divided" — with the mechanism shown, not asserted. |
| Echo / thin-support / repetition detection | `support_structure.py`, `corroboration.py` | "Forty citations, one underlying study." A real research skill, already automated. |
| Receipts, Wayback archiving, signed manifest, `/verify` | `wayback_archive.py`, `manifest_signer.py`, `api/v1/verify.py` | A defensible, reproducible search audit trail. |
| Chronologist | `evidence-views/chronologist/` | Seminal → recent reading order. |
| **Non-sycophancy invariant** | Invariant 7; `evaluative_heads.py`; mechanical orientation derivation | The single most valuable property for education. See §7. |

## 3. What is actually missing — code-grounded

1. **The academic adapters are switched off for most disciplines.** Semantic Scholar
   (`academic.py:264`), OpenAlex (`academic.py:422`) and CrossRef (`academic.py:103`) gate to
   `{Science, Climate, Health}`; PubMed (`health.py:123`) to `{Health, Science, Animals}`.
   `VALID_DOMAINS` (`article_classifier.py:79`) has no Education, Sociology, Psychology,
   Economics-as-discipline, Philosophy, Literature or Engineering. **A history, education or sociology
   thesis gets zero scholarly sources today.** This is also a live defect for the *current* researcher
   buyer — a policy analyst researching education gets no academic evidence either.
2. **Recency bias runs the wrong way for literature review.** `_resolve_min_year` (`academic.py:29`)
   defaults to *now − 2 years*; the `HISTORICAL_MIN_YEAR = 1900` widening only fires on a lexical
   marker or an explicit older DATE entity. A literature review wants seminal-first by default.
3. **No citation graph.** `citationCount` and `venue` *are* already fetched (`academic.py:289`), but
   there's no reference/citation traversal, no seminal detection, no "who cites this and disagrees".
4. **No corpus depth.** We search *open* sources. Scholarly literature is substantially paywalled.
   This is structural and it is what decides the market question in §7.
5. **Wrong metadata vocabulary for scholarship.** A preprint and a *Nature* RCT are both "primary".
   No study design, sample size, peer-review status, retraction flag.
6. **No reference-manager export** (BibTeX / RIS / CSL-JSON). PDF export exists; this doesn't.
7. **Wrong unit of work.** A check is one-shot; a thesis is a workspace over months. Credits-per-check
   is the wrong meter for a project that accumulates.
8. **Scholarly PDF handling is deliberately throttled** — 20MB cap and a module-wide semaphore of 1
   (`pdf_evidence.py`, after the 2026-07-23 OOM incident). Correct for evidence; a bottleneck for
   full-text literature work. Do not casually relax it — that guard exists because a 7.8MB treaty PDF
   OOM-killed the container.

## 4. The pipeline

```
INGEST      research question / draft proposal / reading list        MODIFY (small)
FRAME       question typology + answerability + scope tagging        NEW (small)
            └ reuse ClaimType enum + scope_sensitivity.py
DECOMPOSE   question → 3–8 sub-questions, non-presupposing           REUSE (grounds stage as-is)
RETRIEVE    scholarly mode: adapters ungated, seminal-first window   MODIFY (small)
CLASSIFY    + study design, peer-review status, venue, retraction    MODIFY (medium)
MAP         paper → sub-question: supports / challenges / context    REUSE
ORIENT      per sub-question: settled / contested / thin / silent    REUSE (mechanical)
GAP         Seeker: silent + thin sub-questions = candidate gaps     REUSE
SCOPE       mechanical advice — "4 of 6 settled, narrow here;        NEW (small)
            2 silent, gap or dead end". No verdicts, no adjudication.
EXPORT      annotated bibliography, gap register, reading order,     NEW (small)
            BibTeX, signed search record
```

**The SCOPE stage must stay mechanical.** It reports the *shape* of the evidence per sub-question and
never adjudicates the question — same discipline as orientation derivation. "Settled / contested /
thin / silent" describes the record, not the truth. Invariant 7 applies unchanged: a thesis whose
literature is genuinely one-sided **should** look one-sided.

## 5. Market read

**Segments, honestly:**

| Segment | Fit as user | Fit as buyer |
|---|---|---|
| GCSE / A-level EPQ / IB Extended Essay | Good — the process-documentation requirement fits receipts almost too neatly | **Poor direct.** Under-18 data, safeguarding, DPA/children's code, school procurement cycles. Partner-only. |
| Undergraduate dissertation | High volume | **Poor.** £0 budget, eight-week need, wants the thing we refuse to do. |
| Masters / PhD | **Best user.** Values gap-finding; supervisor demands a defensible search | Weak. Small allowances; already served by funded incumbents with better corpora. |
| Academic-skills / library / learning-development units | — | **Best.** Real budget lines. "Teaches source criticism, produces an auditable log, writes nothing" is literally their brief. Slow (6–18mo), needs SSO, accessibility, DPIA. |
| Supervisors / teachers as buyer | — | **Interesting.** Budget-holding, low usage volume, easy to demo: *"bring me your evidence map before our meeting."* |

**Competition — name it plainly:** Elicit, Consensus, Scite, Research Rabbit, Connected Papers,
Litmaps, Undermind, SciSpace, Semantic Scholar itself, and free-tier ChatGPT/Gemini deep research.
Zotero (free) owns the workflow. **Note the sting: `scite.ai` does supports/contrasts on citations —
our own release plan filed it as "not a competitor, academic-only". The moment we go academic, it
becomes the direct competitor.**

**We will not win "find me the papers."** We don't have the corpus and buying it is out of scope.

## 6. Where the wedge actually is

The wedge is **the tool that won't agree with you**, sold to people whose job is to make students
think. Concretely, the things no competitor is trying to do:

- The grounds stage refuses to presuppose the answer to the student's own question.
- Orientation is derived mechanically from evidence states — there is no model opinion to flatter.
- The evaluative-head detector catches a value judgement masquerading as a finding (the exact failure
  mode of a weak thesis statement).
- Echo / thin-support detection shows "forty citations, one study".
- Receipts + signed record make the search itself examinable.

That is a **teaching instrument**, not a discovery engine. It's also, incidentally, a stronger
portfolio credential than another evidence API.

## 7. Recommendation

1. **Build it as a mode inside Tru8, not a separate product.** `?mode=scholarly` costs a flag; a second
   brand costs a company, and doubles a marketing load already stretched against a £30k target.
2. **Ship the cheap slice now (§8) regardless of the market question** — it fixes a live retrieval
   defect for the *current* buyer.
3. **Validate before building anything past the slice (§9).**
4. **The serious commercial version is the partner route** — Tru8 as the evidence-mapping and integrity
   engine inside someone who already owns distribution and corpus (academic-integrity vendor, library
   /discovery vendor, exam-board-adjacent publisher). The API, MCP server, signed manifests and
   `/verify` endpoint are already the right shape for OEM.
5. **Do not let this delay release.** Track I is open, distribution untested, the researcher funnel has
   never been measured. The slice is safe; the pivot is not.

## 8. The cheap slice — phased build spec

Run under `phased-build-loop`: design → approval → build → independent verify with evidence → sign-off.
Each phase is independently shippable and independently revertible.

### Phase S1 — Ungate scholarly retrieval *(highest value, smallest diff)*

**What:** add a `scholarly_mode` signal that bypasses `is_relevant_for_domain` for Semantic Scholar,
OpenAlex, CrossRef and PubMed; widen `VALID_DOMAINS` with the missing disciplines.

- Adapter change is a guard bypass, not a rewrite — `search()` already early-returns on the gate.
- Widening `VALID_DOMAINS` touches the classifier's prompt vocabulary and the jurisdiction/adapter
  routing map — check `claim_keyword_router.py` and `JURISDICTION_ADAPTERS` for domain assumptions
  before landing.
- **Blast-radius note:** this changes which adapters fire for *existing* checks in the widened domains.
  Bench before/after (`replay_bench.py --all`) and expect golden refreshes.

**Acceptance:** a sociology/history/education claim returns ≥1 Semantic Scholar or OpenAlex item where
it returned 0 before; the 5 bench corpus claims show no regression; unit test on the bypass seam
(the *wired* path, not the two halves — NF-18 lesson).

### Phase S2 — Seminal-first windowing

**What:** in scholarly mode, `_resolve_min_year` defaults wide (literature floor) rather than
*now − 2y*; recency becomes an ordering signal via the already-fetched `citationCount`, not a filter.

**Acceptance:** a claim with no DATE entity retrieves pre-2020 foundational work in scholarly mode and
retains current behaviour outside it. Guard: no change to the non-scholarly path — assert it.

### Phase S3 — Reference-manager export

**What:** BibTeX / RIS / CSL-JSON export alongside the existing PDF export. Reuse the public-export
route pattern (`GET /checks/public/{id}/export/pdf`).

**Acceptance:** exported file imports cleanly into Zotero; DOIs preserved where present; archived URL
included where present.

**Rough cost:** S1 ~1–2 days incl. bench, S2 ~1 day, S3 ~1–2 days.

### Not in the slice

FRAME, SCOPE, study-design metadata, the workspace model, and the citation graph (FP-06). All gated
on §9.

## 9. The validation gate

Before anything past S3. The question to test is **not** "would this help students" — everyone says yes
and it means nothing. The question is:

> **Who has a budget line today, and what is it currently spent on?**

Five to ten conversations: two dissertation supervisors, two academic-skills librarians, two EPQ/IB
coordinators, one academic-integrity officer, one edtech/integrity vendor (partner probe).

**Kill criteria — say these out loud before starting so the result can't be rationalised:**

- No identifiable budget line, or the budget already goes to Turnitin-class tooling with no room → stop
  at S3 and keep it as a retrieval improvement.
- Interviewees ask primarily for *summarisation or drafting* → wrong product, and we won't build it.
- Institutional requirements (SSO, WCAG/VPAT, DPIA, procurement) exceed what a solo founder can service
  → partner route only, never direct.

## 10. Risks

- **Corpus gap is structural.** Anything positioned as "find the literature" loses to incumbents.
- **Scite becomes a direct competitor** the moment we enter this space.
- **Timing.** This is an attractive framing arriving mid-release. The 2026-06-22 session killed six
  equally plausible framings; the standing lesson is validate first.
- **Academic integrity is a hard edge, not a marketing line.** If we sell into education, "we do not
  write your thesis" has to be true at the product level and stay true under pressure. It currently is —
  don't trade it.
- **PDF throttle.** Any move toward full-text scholarship re-opens the OOM class closed on 2026-07-23.

## 11. Unverified claims in this document

Per the validate-before-present rule, these were **not** checked and must be verified before use in any
pitch or plan:

- Cohort sizes for EPQ / IB Extended Essay.
- Competitor pricing and feature sets (Elicit, Consensus, Scite, Research Rabbit, SciSpace, Undermind).
- Institutional budget ranges for academic-skills / library tooling.
- The claim that universities are currently procuring against AI-sycophancy concerns — plausible and
  widely discussed, but unmeasured here.

Everything in §2, §3 and §4 is code-grounded and was read at the file:line references given.
