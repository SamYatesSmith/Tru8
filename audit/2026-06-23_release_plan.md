# Tru8 — Reposition + Release Plan (2026-06-23)

**Status:** ACTIVE. Supersedes the 2026-06-22 mothball default (`audit/2026-06-22_strategic_decision.md`).
**Method:** one long working session — strategic re-examination → fresh competitor analysis anchored to Tru8's *actual* output → repositioning → build started under a gated design→verify→sign-off loop.

---

## Why this supersedes the mothball

The 2026-06-22 session concluded "no reachable venture-scale market" and defaulted to mothball-and-harvest. On 2026-06-23 the founder rejected the framing:

- The goal was **never venture scale.** It is **£30k revenue / £15k profit** — replace a £15k/yr side-job + stand as a portfolio credential. So "niche / lifestyle" is the **target**, not a disqualifier. £30k ≈ ~100–250 paying customers, not a market.
- The founder **is willing to do marketing.** A wrong "won't market" assumption had been quietly skewing the prior analysis pessimistic. Removing it puts the human-research buyer back on the table.

So: **make Tru8 competitive and release it to a specific buyer**, not mothball it.

## Positioning (locked this session)

- **Buyer:** the **"show-your-working" researcher** — journalists, analysts, policy/comms researchers, serious independent writers. People who must *see* the evidence for and against a claim and *defend* their sourcing. For them, **no-verdict is a feature**, not a limitation.
  - *Higher-ACV alternative noted, not chosen:* litigation/compliance **"evidence-of-record"** (billed-through, 1:1 outreach). The fallback if the prosumer funnel won't convert.
- **What Tru8 actually outputs (the anchor — everything is measured against this):** a claim / question / article URL → decompose into sub-elements → search **open public sources** (web + ~30 gov/legal/academic/economic/health APIs) → classify each source by **tier** (primary/reporting/commentary) and **type** (data/official/news/analysis/opinion/academic) → tag each **supports / challenges / context** per sub-element → a **classified, sourced evidence map**, receipts for exclusions, signed record, and **deliberately NO verdict.**
- **Real competitors (anchored to that exact output):**
  - **Webcite** — closest *mechanically*: per-source stance + source-type classification + reliability. But it **adds a verdict**. Agent/API-first, $20/mo.
  - **Factiverse** — closest *philosophically*: supporting-vs-disputing, softens on contested. But it **predicts veracity**. Newsrooms, €25/mo.
  - **scite.ai** — no-verdict supports/contrasts, but **academic-only**.
  - **NOT competitors:** Perplexity / Lenz / Originality (verdict/answer engines). DD/OSINT firms (Kroll, S-RM, Xapien) are a **different product** — entity-risk from authoritative records, not claim-evidence. Do **not** chase them.

## Honest caveats (carry forward — do not lose)

1. The differentiation (no-verdict + breadth + receipts/provenance) is **real but configuration-level, not category-level** — Webcite could close most of the gap with a "no-verdict mode." It is not a durable moat.
2. **"No-verdict" tracks the lowest-WTP end of the field** (pure no-verdict tools = $10–60/yr consumer apps; the tools that monetise give verdicts). This is a modest, contestable niche → execute and measure, don't over-believe it.
3. **Agent-future thesis** (the founder's original): humans squeezed out, agents buy structured evidence. Plausible *directionally* but pays ~£0 now (x402 ~$28k/day, falling, ~half wash-traded; no verification budget line for devs). Correct play: **hold it as a near-zero-cost option** (keep MCP/API/rails live + listed), do **NOT** invest more into it now.

---

## The release plan — release = items 0–4 done

| # | Item | Status |
|---|------|--------|
| **0** | **Integrity (BLOCKER)** — homepage sold "tamper-evident signed manifest" but the HMAC overclaims (shared-secret → server-attested not third-party; self-clocked timestamp; hashes metadata not content). **Prod signing VERIFIED ON** (live `GET /verify/2484b9da-…` → `valid:true`, kid `tru8-2026-03`, HMAC-SHA256, integrity recompute matches — 2026-06-23) → no turn-on work, no migrations. **Action taken:** softened "tamper-evident" → "signed" across Tier 1 website (homepage meta/JSON-LD, layout, record-footer, llms.txt ×2, developers card) + Tier 2 public API docs (README, OpenAPI top-level + 2 schema descriptions, `/verify` docstring); replaced "verify results haven't been modified" → "verify the signed fields haven't changed since signing"; retained code comment that *denies* tamper-evidence + points to item 6. Internal backend code comments left out of scope. | **DONE + SHIPPED `1e2f451`.** Independently verified PASS (grep clean, no forbidden words, `/verify` accurate, web tsc + build exit 0 / 28 routes). |
| **1** | **The record** — enrich the PDF with receipts (excluded sources), gaps (Seeker def: no-refs OR unresolved; **not** contextual), signed-record/verify line (when a manifest exists), 4th contextual state; one shared render helper `_build_check_pdf_bytes`; public download on `/r/` via `GET /checks/public/{id}/export/pdf` (mirrors `get_public_check`, F-SEC-06 safe). | **DONE + SHIPPED `ba1ee4c`.** Gaps→Seeker alignment follow-up: **COMMITTED + PUSHED `09f10b7`** (template only; matches `SeekerView.tsx:62-67`; 8/8 render-proof). |
| **2** | **Positioning** — homepage dev/agent-led → researcher-led ("see the evidence for and against — show your working"); console primary, API quiet; explicit contrast vs verdict tools; keep a real limitations note. Reverses the 2026-06-17 API-led lock → ship as a reversible `/research`-led variant + measure before flipping. LEAST reversible → after 0/1. | **DONE + SHIPPED `fc03ced`** (reversible variant: `/research` rebuilt researcher-led — for/against block, verdict-contrast→/compare, six professions, honest limitations note, closing CTA + quiet API footnote; primary CTA instrumented `research_start_click`; OG card + sitemap date fixed). **`/` + nav deliberately UNTOUCHED** (byte-identical) — the flip of `/` is deferred until the funnel measures. Independently verified 10/10 + tsc/build 0 + rendered-HTML check. NOT machine-verified: pixel/mobile (browser MCP down). |
| **3** | **Funnel & packaging** — low-friction first run → soft paywall at export/share/volume; reconcile subs (may be beta-waitlisted); repackage tiers around researcher value (export, signed record, receipts, breadth) not "200 checks + API"; **keep `/agent` + MCP alive** (reduce prominence only). | **PENDING** |
| **4** | **Proof & discovery** — 5–10 worked sample-report gallery; confirm `/r/` pages indexable (already OG + JSON-LD). | **PENDING** |
| **5** | **Measurement** — Phase-1 PostHog funnel instrumentation. | **DONE (code) `ba1ee4c`.** USER must set `NEXT_PUBLIC_POSTHOG_KEY` in Railway or events no-op (safe). |
| **6** | **Deeper credibility (post-release)** — independent timestamp (RFC-3161/eIDAS) + content hashing → only *then* may say "tamper-evident". Improve the terse orientation/summary line (replay-bench acceptance). | **LATER** |

## Working method (founder-demanded — skill `phased-build-loop`)

Every phase: **design** (no code, frozen testable acceptance criteria) → **USER approval** → **build** → **INDEPENDENT verify with evidence** (render-proofs, builds, a reviewer that didn't build it) → **fix-loop** → **USER sign-off**. One phase at a time; the verifier re-derives pass/fail, never inherits the builder's claims.

**Lesson (trust was lost mid-session and rebuilt):** READ the actual code **before** designing — designing from memory produced a proposed *duplicate* export and a *non-existent* "security gate" that the founder caught, not the review. Verify with **evidence, not assertion**. Make my own implementation calls; don't offload decisions to the founder.

## Next agent — start here

**Items 0 + 1 + 2 are now shipped.** Done 2026-06-23 (cont.): gaps-fix `09f10b7`; item 0 copy softening `1e2f451`; **item 2 researcher-led `/research` `fc03ced`** (reversible variant; `/` + nav untouched; funnel instrumented to measure before flipping). All pushed to `main`, Railway auto-deploying.

Next under the phased-build-loop:
1. **Item 3 — Funnel & packaging** (low-friction first run → soft paywall at export/share/volume; reconcile subs; repackage tiers around researcher value). **PRICING GUARD: no display price yet** — internal COGS work owed; use value-framing + placeholder/waitlist, founder-gated (memory `project-pricing-not-set-2026-06-23`).
2. Item 4 (proof/discovery — sample-report gallery; confirm `/r/` indexable).
3. **The deferred `/` flip:** once `research_app_click → research_start_click → dashboard` shows researcher demand, flip the `/` homepage + nav researcher-primary / API-quiet. Hold until data.
4. Commit the `phased-build-loop` skill (`.claude/skills/phased-build-loop/`) if wanted — left untracked.
5. Founder actions open: set `NEXT_PUBLIC_POSTHOG_KEY` in Railway (item 5 + item 2 funnel no-op until then); optional local pixel/mobile eyeball of `/research` (browser MCP was down this session).
6. Git: on `main`; `fc03ced` is live (HEAD).

**Verify post-deploy (optional):** after Railway redeploys web, the homepage record footer should read "Signed record of exactly what was returned." and `https://www.trueight.com/llms.txt` should no longer contain "tamper-evident".
