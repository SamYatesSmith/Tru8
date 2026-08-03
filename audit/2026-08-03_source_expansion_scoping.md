# Scoping — replacing Companies House, and what CrossRef is actually for

**Date:** 2026-08-03
**Status:** SCOPING — for founder decision. Nothing built.
**Trigger:** founder: *"I don't really ever see the point in the Companies House
API… it could be replaced by something genuinely useful that expands Trueight's
knowledge."* Then, before building: *"BUT FIRST, let's understand why we removed
it?"* — which changed the recommendation.

---

## 1. Why CrossRef was removed — the real reasons, in order

There are **two** decisions, and only the second is well-reasoned.

**PQ-06, 2026-03-05 (`90e8810`).** The commit reads:

> *"Unregister Alpha Vantage (25 req/day unusable) and CrossRef (redundant)"*

Note the asymmetry. Alpha Vantage got a **measured** reason — a hard quota number
that makes it unusable. CrossRef got a **word**. The code comment expands it to
*"redundant with Semantic Scholar + OpenAlex"*, but no measurement is cited
anywhere in PQ-06, and the scorecard corpus was edited to *remove* the scrapped
adapters rather than to demonstrate they were redundant.

**The 2026-04-23 adapter coverage review** (in `_archive/`) revisited it and
reached a far stronger conclusion, which is the one that actually matters:

> *"CrossRef decommissioned — its reactivation would add only a fourth
> DOI-registry client, not a fourth **independent** source."*

And it named the underlying structural problem:

> *"4 adapters **looks** strong, but S2+OpenAlex+PubMed all index the same
> underlying publications via DOI/PMID. Loss of DOI access ⇒ 3 of 4 degrade
> together."* — Health independence rated **"Medium-to-Low (hidden)"**

**That reasoning is correct and should stand.** Adding CrossRef as an evidence
source would inflate the adapter count while adding nothing to source
independence — the thing that actually protects an evidence landscape.

## 2. So my recommendation was wrong as stated

I proposed "wire CrossRef back in". Read as re-registering `CrossRefAdapter` as
a retrieval source — the obvious reading — that is **precisely what the April
review argues against**, and I would have re-introduced a decision the project
had already made correctly, on better evidence than I had.

**Do not re-register `CrossRefAdapter`.**

## 3. The distinction that does survive

The purpose I actually want CrossRef for is **not retrieval**. It is
**DOI → publisher identity**, to fix the tier-classification defect found today
(NEJM and an AHA Scientific Statement in *Circulation* both classified
`commentary`).

That use is untouched by the independence argument, because:

- it adds **no evidence items** to the pool — nothing to be redundant *with*;
- it runs against URLs that arrived by **web search**, which Semantic Scholar,
  OpenAlex and PubMed cannot classify (they only know items they indexed, keyed
  by their own IDs); and
- it is a **metadata lookup**, not a source, so it never counts toward adapter
  coverage or independence.

Live-verified against the exact DOI that was misclassified:

```
GET api.crossref.org/works/10.1161/CIR.0000000000001341
  publisher : Ovid Technologies (Wolters Kluwer Health)
  container : Circulation
  type      : journal-article
  ISSN      : 0009-7322, 1524-4539
```

`type: journal-article` + a registered ISSN is a **mechanical** peer-reviewed-venue
signal. It replaces the hand-maintained allowlist that the tier design already
concedes is *"incomplete by construction"* — and it generalises to journals nobody
has thought to list.

**Proposed shape:** a narrow DOI-resolution utility consumed by
`evidence_classifier` only. Not an adapter, not registered, not in the registry.

⚠️ It does **not** dissolve the source-diversity blocker from
`2026-08-03_journal_tier_classification_design.md` §4b. Correcting a tier by DOI
still moves the tier, which still moves the mapper's citations. That blocker is
about the *consequence* of re-tiering, not the *means*, and must be solved either
way.

## 4. Verified API facts

| | Crossref | Eurostat | OECD |
|---|---|---|---|
| Key required | **No** | No | No |
| Cost | Free | Free | Free |
| Verified live today | ✅ HTTP 200 | — | — |
| Rate limits | **From 1 Dec 2025:** public 5/s single, 1/s lists, 1 concurrent · polite (`mailto`) **10/s single, 3/s lists, 3 concurrent** | None published; docs advise 1–2/s | None published |
| Throttle signalling | `x-rate-limit-limit` + `x-rate-limit-interval` headers — back off on signal, not guesswork | — | — |
| Format | REST/JSON | SDMX + JSON-stat | SDMX |
| Integration cost | **Near zero** — client already exists at `academic.py:143-212` | Medium — SDMX parsing | Medium-High — SDMX |

## 5. What should actually replace Companies House

The April review already contains the gap analysis, so this need not be guessed.
Documented gaps, verbatim:

- **Finance** — *"No Eurostat / OECD / ECB / BoJ / RBI"*
- **Politics** — *"None for EU/rest of world"*
- **Law** — *"No EU / case law (BAILII, CURIA, CourtListener)"*
- **Health** — *"No Europe PMC, no CDC, no NIH direct, no Cochrane"*
- **Demographics** — *"No US Census Bureau"*

The sharpest candidate is **not** another academic index. Health and Science are
rated low-independence precisely because everything there rides the DOI backbone.
The highest-value addition is therefore a source of a **different kind**: an
official health authority (CDC / NIH direct) or systematic-review evidence
(Cochrane), neither of which degrades when DOI access does.

Eurostat/OECD remain the strongest *coverage* additions — the EU/rest-of-world
hole is real and named in three separate rows.

## 6. Recommendation

1. **Do not re-register `CrossRefAdapter`.** The April reasoning stands.
2. **Do add a DOI→publisher utility** for the classifier. Cheap, keyless,
   verified, and it converts a permanently-incomplete allowlist into a mechanical
   rule. Gate it behind the §4b diversity work, which blocks any re-tiering.
3. **Drop Companies House** by clearing `COMPANIES_HOUSE_API_KEY` — the registry
   is already conditional (`api_adapters/__init__.py:110`), so no code change and
   no deploy. This also stops the 401s.
4. **Choose its replacement from data, not instinct.** The Seeker's
   known-unknowns and M-02 gap enrichment already record what checks fail to find.
   A few real checks will name the missing source better than this document can.

## 7. Housekeeping found on the way

`CrossRefAdapter` has been **actively maintained since it was deregistered** —
a year-window bug fixed in June (`2026-06-15_pipeline_should_vs_is.md`) and
temporal-marker wiring added in July (`2026-07-09_retrieval_quality_plan.md`),
both with tests — for code that never executes. Either it becomes the DOI utility
above, or it should be deleted. Maintaining a dead adapter costs real attention
and quietly implies a source that is not there.

Same class of problem as `ENABLE_DOMAIN_CAPPING` in `.env`, which is referenced
nowhere in `app/`.
