# Future Path — ideas, opportunities, deliberately-deferred work

**Created 2026-07-27.** This folder is where Tru8's *future* lives: product opportunities we haven't
committed to, improvements we've chosen not to build yet, and pipelines that could exist off the
back of what already ships.

## What this folder is (and is not)

| Folder | Holds | Rule |
|---|---|---|
| `audit/OPEN_WORK.md` | What is **open right now** | **Single source of truth.** Edit it FIRST on every ship/open. |
| `audit/future/` (this) | What we **might do, later** — not started, not committed | A place to think, not a queue. Nothing here is promised. |
| `audit/_archive/` | What is **done or superseded** | Never resurrect anything in `_archive/` as a live plan — it's history. |

**The protocol that matters:** if an item here becomes active work, it graduates — a row goes into
`OPEN_WORK.md`, and the doc in this folder becomes that row's detail doc. It does **not** get tracked
in two registers. Items below marked *(pointer)* are already owned by `OPEN_WORK.md` and are listed
here only so this folder is a complete browsing surface for "what could come next".

## The discipline for anything in here

Every item carries a **trigger** — the thing that would have to be true before we build it. This is
deliberate: the 2026-06-22 strategic session killed six plausible commercial framings on evidence,
and the standing lesson is *validate demand BEFORE build*. An idea without a trigger is a daydream
with a filename.

Each entry should state: **what · why not now · trigger · rough effort · where the detail lives.**

---

## Class A — Opportunities (this folder is their home)

| ID | Idea | Why not now | Trigger | Effort |
|---|---|---|---|---|
| **FP-01** | **Academic / thesis research pipeline** — a scoping mode that turns a research question into sub-questions, maps the literature as settled/contested/thin/silent, and surfaces the gap. Buyer is likely *institutional* (academic-skills / library / supervisors), not students. | Pre-release; funnel unmeasured; corpus depth is a structural weakness vs Elicit/Consensus/Scite. | Cheap slice ships regardless (it fixes a live defect). Full build gated on 5–10 buyer conversations finding a budget line. | Slice ~3–5 days · full ~3 weeks + citation graph ~1 month | [2026-07-27_academic_research_pipeline.md](2026-07-27_academic_research_pipeline.md) |
| **FP-02** | **UK procurement / tender monitoring for SMEs** — monitoring a bounded gov feed. Uses Tru8's plumbing + founder skills, *not* its core IP. Best income odds of the 2026-06-22 survivors; mundane. | Different product; would compete with the release for attention. | Only if the researcher funnel fails to convert after real distribution effort. | New product | `audit/2026-06-22_strategic_decision.md` |
| **FP-03** | **OSINT / small-firm-litigation evidence dossier** — the only 2026-06-22 survivor that uses the core IP (multi-source research + provenance). | Gated on a forensic-admissibility bar (FRE 901 / chain-of-custody) that Wayback + HMAC may not clear. Crowded (Hunchly, Page Vault). | FP-05 done (real timestamping) **and** an admissibility answer. | Medium | `audit/2026-06-22_strategic_decision.md` |
| **FP-04** | **Data lifecycle as a product surface** — curated export, labelled corpus split, analytics layer. Needed for eval work; potentially a surface in its own right. | No buyer identified; eval need is currently met ad-hoc. | An eval workstream that needs it, or a partner asking for corpus. | Medium | Thread 3, `OPEN_WORK.md` |
| **FP-06** | **Citation graph** — forward/backward traversal via Semantic Scholar/OpenAlex; seminal-paper detection; "who cites this and disagrees". The one genuinely large build behind FP-01. | Large; only pays off if FP-01 validates. `citationCount` + `venue` are *already* fetched (`academic.py:289`) so a cheap seminal signal exists without the graph. | FP-01 validated. | ~1 month | [2026-07-27_academic_research_pipeline.md](2026-07-27_academic_research_pipeline.md) §6 |
| **FP-07** | **Mobile-native evidence views** — the six views need fundamentally different UIs on mobile, not responsive desktop. | Desktop-first buyer; no mobile traffic data. | Mobile share of real traffic proves it matters. | Medium | memory `feedback_mobile_different_ui` |

## Class B — Deferred engineering *(pointer — owned by `OPEN_WORK.md`)*

| ID | Item | Gate |
|---|---|---|
| **FP-08** | **Independent timestamping** — RFC-3161 / eIDAS + content hashing. Only *then* may we say "tamper-evident". | Post-release. Release plan item 6. |
| **FP-09** | **Track P adapter candidates** — P0a ECB SDW · P0b Europe PMC · P2 SEC EDGAR · P3 Eurostat · P4 fact-check aggregators · P5 Tech/Industry (AI-compute claims are not marketing-viable until P5 ships). | `OPEN_WORK.md` §Track P |
| **FP-10** | **Deferred retrieval remedies** — R2b (consolidate temporal signalling into one mechanical tag) · R2d (let a thin/zero-primary pool trigger recovery regardless of claim count) · R2g (PubMed reduced-term retry on zero hits). | `audit/2026-07-09_retrieval_quality_plan.md` |
| **FP-11** | **Broad-temporal-scope widener** — "since X" / "over the past decade" should query the full range, not the most-specific DATE. | NF-18 Phase 2 follow-up, `OPEN_WORK.md` |
| **FP-12** | **D1 decoupling hardening** — one-sided-pool tripwire / per-element evidence floor / disconfirm-aware recovery. DEFERRED *and evidenced* (T8 B probe passed). | `audit/DECOUPLING_STATE.md` |
| **FP-13** | **Latency tail** — A1 quick-tier lite mapping (likely unnecessary post budget-0) · R1/R2 retrieve dechaining. | Gated on prod `stage_timings_s` distribution. |
| **FP-14** | **Cost control Phase 3+/4.x** — mapper-fallback alarm, per-check budget kill switch, six data-gated hypotheses. | Post-launch, data-gated. |
| **FP-15** | **F8 results consolidation M2/M3** — one Evidence home; elevate the element spine. | Parked after C1–C4 shipped. |
| **FP-16** | **Small parked items** — PQ-10 JSON-repair on the mapper · demo video (I-15). | `OPEN_WORK.md` §Parked |

---

## Adding an item

1. If it's a genuine *opportunity* (Class A): write a dated doc here, add a row above with a trigger.
2. If it's *deferred engineering* already tracked in `OPEN_WORK.md` (Class B): add a pointer row only —
   do not restate its state here, or the two will drift.
3. When it goes live: add the `OPEN_WORK.md` row, and leave the doc here as its detail doc.
