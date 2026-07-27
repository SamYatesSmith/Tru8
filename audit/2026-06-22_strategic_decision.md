# Tru8 — Strategic Decision: Mothball Core, Two Conditional Niche Wedges

**Date:** 2026-06-22
**Status:** DECISION RECORDED. Core venture = mothball. Two validate-first niche options remain open to the founder.
**Method:** One long working session — adversarial grilling (`/grill-me`) + a built-and-run independence experiment + six market/feasibility research agents over two rounds. Findings cross-checked; evidence vs inference separated throughout.

---

## TL;DR

There is **no reachable, venture-scale paying market for Tru8's core IP** (the evidence-verification / claim-mapping / evidence-landscape engine). Every buyer that pays for "auditable / verified / structured evidence" is enterprise, regulated, and owned by funded incumbents; every buyer a solo bootstrapped founder can reach either has no budget line or is being commoditised by generalist AI.

**Decision: mothball the core as a standalone venture.** Two conditional, niche, *validate-first* wedges survive — neither venture-scale, both requiring buyer conversations before any code:
1. **UK procurement / tender monitoring for SMEs** — best income odds; uses Tru8's *plumbing + the founder's skills*, NOT its core IP; mundane.
2. **"Verifiable evidence dossier" for OSINT investigators / small-firm litigation / journalists** — the only path that uses Tru8's *core IP* (multi-source research + tamper-evident provenance); low-ACV, crowded (Hunchly/Page Vault), and gated on a forensic-admissibility bar.

**Default recommendation:** mothball-and-harvest (open-source credential + personal research tool) unless one wedge genuinely appeals — then validate it (5–10 buyer conversations) before building.

---

## How we got here (what was tested and killed)

The session started as a positioning pressure-test and progressively killed every commercial framing on evidence:

1. **AEO/content-grounding vendors as the buyer** → they treat verification as a commodity API call (rent from Parallel); partner channel, not buyer.
2. **"Verification infrastructure" positioning** → unsearchable, unbudgeted category; "verification" collides with identity/insurance SaaS; the historic fact-checking buyer is exiting (Meta out, IFCN 76% in crisis).
3. **The "independence / echo epidemic" idea** (the most attractive new thesis) → **built and tested on a branch; killed on evidence.** See below.
4. **Builder/dev verification demand** → trust budget goes to *self-operated* eval/guardrails (Braintrust $800M, Exa $2.2B, Parallel $2B); 40s latency disqualifies inline; builders want pass/fail not a dossier; build-in-house wins.
5. **Content-operator verify-before-publish** → revealed WTP is for *humans* ($60–72/hr); cheap tools ($20–30) set the ceiling; brand money flows to monitoring + remediation, not proof.
6. **Auditable deep research** → generic deep research is commoditised inside $20/mo ChatGPT/Perplexity/Gemini; the segments that pay for *auditable* research (DD/KYC, OSINT, eDiscovery, pharma MLR, financial, regulatory) are enterprise-gated, funded-incumbent-owned.

## The independence experiment (branch: `experiment/independence-detector`)

Rather than argue the most attractive idea, we **built the minimum detector and measured it** — committed on an isolated branch, never merged, never deployed.

- S1: three-bucket detector (reproduction / shared-input / independent), no-score honesty rails, keystone fixtures green (7 reposts → 1 origin; 2 appraisals of one source → kept + flagged).
- S2/S3: measured 291 distinct DB claims → ~0% reproduction collapse. **Null — but Tru8's pool is engineered for diversity, so wrong corpus.**
- S4 (fork A): raw naive-search vs Tru8 pool, matched, 30 claims, 3 axes. **No support for the echo-epidemic thesis** (raw search is *more* domain-diverse, not less; no raw>Tru8 gap on any axis).
- **Verdict: earned mothball of the independence idea.** Detecting "many domains, one origin" needs full-content + citation-graph mining — a major build with poor EV and no buyer. Detail: `backend/scripts/independence/FINDINGS.md`.
- **Method win:** killed the most attractive idea in one session, on a branch, before any market spend.

## The demand research (six agents, two rounds)

Round 1 (buyer-side): builder demand = NO; content-operator demand = NO. Only survivor across both = enterprise/regulated buyer who can't self-certify (a different company's GTM).

Round 2 (idea-fit, market-first): 
- **Auditable deep research** → CONDITIONAL, leaning against. Generic = commoditised by labs; provenance is real-but-unmonetised-standalone; paying segments enterprise-gated. Only solo-reachable door = low-ACV OSINT/small-firm-legal capture (Hunchly $129–169/yr, Page Vault $195/mo + $199–349/capture).
- **Vertical demand** → ONE survivor: UK procurement/tender intelligence for SMEs. Monitoring (not research) of a bounded gov feed; generalist AI structurally weak at it; funded incumbents (Stotles £475/mo $13M Series A, Tussell) vacated the SME band; solo-reachable PLG/SEO at £49–149/mo; free gov API. Due diligence = no-go (Companies-House-only fatal; DueDil collapsed). Policy/public affairs = deprioritise (£0-floored, AI table-stakes).
- **Architecture feasibility** → deep-research pivot is a MEDIUM build (new orchestrator + synthesis stage on a reusable services layer, ~60–70% exists). `re_search.py` is ~30% of an agentic loop. BUT feasible ≠ sellable; the market is squeezed.

## The two conditional survivors (detail)

| | Procurement monitoring | OSINT/litigation evidence dossier |
|---|---|---|
| Uses core IP? | No (plumbing + skills) | Yes (research + provenance — the intersection capture-vendors and labs both miss) |
| WTP | £49–149/mo, proven | ~$130–350/yr or per-capture, low ACV |
| Defensibility | Strong (AI weak at monitoring) | Real but crowded (Hunchly/Page Vault/ProofSnap) |
| Hidden bar | Mundane; new product | Forensic admissibility (FRE 901 / chain-of-custody) — current Wayback+HMAC may not clear it |
| Scale | Niche/lifestyle | Niche/lifestyle |

## The meta-lesson (the actual root cause)

The binding constraint across every dead end was **build-led, not demand-led** development colliding with a founder rule of "won't market/validate until the product is finished" — while "finished" can't be defined without demand signal. Every differentiator hunt (AEO, independence, deep research) was an attempt to find a buyer who would arrive *without being sold to*. The research says that buyer doesn't exist. **Correction carried forward: validate demand before building, for whatever comes next.**

## Artifacts & pointers

- Experiment branch: `experiment/independence-detector` (parked, committed, never merged): `S1` detector, `S2/S3` harness, `S4` raw-compare, `FINDINGS.md`. Main never touched.
- This doc is the canonical record. The six agent memos are session-transient.
- Open decision for the founder: **harvest** (default) / **validate-procurement** / **validate-the-dossier**.
