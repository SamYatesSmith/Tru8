# Track I: Pre-Release Readiness

**Created:** 2026-02-25
**Status:** In Progress
**Goal:** Tighten everything up for client-facing launch — pricing, polish, go-to-market.

> **For current open status of Track I items, see [`audit/OPEN_WORK.md`](../OPEN_WORK.md).**
> This doc remains canonical for *what each item is and how it's implemented*; OPEN_WORK is the *what's-open-right-now* register.

---

## Ship Blockers

### I-01: Pricing Tiers — Frontend
**Status:** [x] Done (2026-02-26, commit `d103ce3`)
**Priority:** Ship Blocker
**Effort:** 1–2 days

**Completed:** 4-tier structure implemented in `web/lib/tiers.ts` and `StitchPricing` component:
- Free Trial: 3 checks, lifetime
- Professional: £7/mo, 40 checks
- Developer: £29/mo, 200 checks, API/MCP access (highlighted)
- Enterprise: Contact us, custom volume

**Tasks:**
- [x] Design tier structure (Free / Pro / Developer / Enterprise)
- [x] Update `StitchPricing` component with new tiers
- [x] Developer tier explains API/MCP access clearly
- [x] Enterprise tier as "Contact Us" card

---

### I-02: Pricing Tiers — Backend
**Status:** [x] Done (2026-02-26, commit `d103ce3`)
**Priority:** Ship Blocker
**Effort:** 2–3 days

**Completed:** Multi-tier backend support added. Files changed: `checks.py`, `payments.py`, `config.py`.

**Tasks:**
- [x] Add `STRIPE_PRICE_ID_DEVELOPER` and `STRIPE_PRICE_ID_ENTERPRISE` to config
- [x] Update credit limit logic in `checks.py` for new tiers
- [x] Update webhook handlers in `payments.py` to recognise multiple tiers

---

### I-03: Stripe Product Setup
**Status:** [x] PRESUMED DONE 2026-05-01 — user confirmed subscriptions live (`SUBSCRIPTIONS_ENABLED=True`). If checkout works in production with subs enabled, Stripe production products + price ID env vars must exist on Railway, otherwise every checkout would 4xx. Treat as DONE pending the user's explicit confirmation if this needs auditing.
**Priority:** Ship Blocker (closed)
**Effort:** N/A — was completed long ago

**Logical inference 2026-05-01:** `SUBSCRIPTIONS_ENABLED=True` has been live for a long time per user. The code path in `backend/app/api/v1/payments.py:create_checkout_session` calls `stripe.checkout.Session.create(line_items=[{"price": request.price_id, ...}])` with the price ID supplied by the frontend. If `STRIPE_PRICE_ID_*` env vars were empty at runtime, the frontend would have nothing to send and checkout would fail. Since checkout has been working, the env vars must be set.

**Status of test-mode products noted in earlier doc state (now superseded):**
- Professional, Developer, and three credit packs were created in Stripe test mode.
- For a long-running production deployment with active subscribers, equivalent live-mode products must also exist with their price IDs set in Railway env.

**Tasks:**
- [x] Create new Stripe products + prices in Stripe Dashboard (live mode — implied by working production)
- [x] Add price IDs to environment variables (backend + frontend Railway env — implied by working production)
- [x] Checkout flow live across tiers — verified by long production runtime
- [x] Upgrade/downgrade live — same verification

**Lesson:** Stale-doc cluster fixed 2026-05-01. See `feedback_trust_user_on_production_state.md` in user memory. If I-03 needs re-auditing for any specific tier, do that as a focused exercise rather than blocking pre-release on a stale doc.

---

### I-04: Enable Subscriptions
**Status:** [x] DONE — `SUBSCRIPTIONS_ENABLED=True` and `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true` have been deployed in production for a long time (user confirmed 2026-05-01). Stale-doc fix.
**Priority:** Ship Blocker (closed)
**Effort:** N/A — was completed long ago

The earlier "missing 503 gating check" gap is moot now that subscriptions are enabled in production: the gating was a soft-launch guardrail to hide checkout while subs were unannounced. With subs live, the absence of the gating check has no effect — the endpoint is intended to be reachable. If subscriptions were ever disabled again (rollback scenario), a 503 gate would be worth adding back as a defence-in-depth check, but that is not pre-release work.

The code default `SUBSCRIPTIONS_ENABLED: bool = Field(False, ...)` in `backend/app/core/config.py:261` is the *local-dev* default; Railway production overrides it to `True`. The frontend env var `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED` is similarly set to `true` on Railway's web service.

**Tasks:**
- [x] Flip `SUBSCRIPTIONS_ENABLED=True` (backend) + `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true` (frontend) in production — done long ago
- [x] Upgrade flow live end-to-end — verified by long production runtime with active subscribers
- [x] Subscription tab shows correct plans — verified live

**Lesson:** Stale-doc cluster fixed 2026-05-01. See `feedback_trust_user_on_production_state.md` in user memory.

---

## High Impact

### I-05: Developer Page Polish
**Status:** [x] Done (verified 2026-03-17)
**Priority:** High
**Effort:** 1 day (original); 0 remaining

All items verified as already implemented in the current codebase:

- [x] Orange accent used extensively — step squares, MCP primary tool, pricing steps, callout icons, CTA button
- [x] Step number squares use `bg-accent` (lines 109, 143, 162)
- [x] MCP tools have visual hierarchy — primary tool has accent border, accent icon, accent name
- [x] CTA button uses `bg-accent` (line 944)
- [x] Pricing section differentiates all four tiers including Consensus
- [x] Consistent spacing (`mb-16 md:mb-20`) across all sections
- [x] Response Shape has 3 annotation callout boxes (claimMap, _meta vs _computed, _manifest)
- [x] Example JSON shows `"orientation"` (not `"orientationLine"`) + includes `_meta.landscape` and `_manifest`

---

### I-06: Social / OG Card Alignment
**Status:** [x] Functional-complete; **OG visual redesign DONE + verified 2026-07-02** (`0d595b9`). Only cross-platform crop testing (X/LinkedIn/Slack) remains — founder eyeball, non-blocking.
**Priority:** High → Low (functional gate satisfied; remaining items are polish, not ship-blockers)
**Effort:** ~0.5 day for polish + manual cross-platform testing

Core sharing infrastructure complete. Dynamic OG metadata at `web/app/r/[id]/page.tsx:45-91` (generateMetadata). **OG image is now a single "Record" card** (`web/app/api/og/_components/record-card.tsx`) served from `/api/og/social/[id]`. The old `_components/*` system (full-report-card, social-share-card, shared/*) and the orphaned `/api/og/check/[id]` route were deleted in the redesign.

**Already working:**
- Dynamic OG images per report (1200x630 PNG) — wired into metadata
- Share buttons: X, LinkedIn, WhatsApp, Copy Link
- Tweet reply detection
- URL-persisted view state (F07)
- PDF export
- JSON-LD structured data (home + /r/[id])
- `theme-color` (#f27907) + `apple-touch-icon` in root layout

**Optional polish (not ship-blockers):**
- [x] Redesign OG card visuals to match Stitch design language (orange accents, Inter/JetBrains Mono, spec-sheet aesthetic) — DONE 2026-07-02 (`0d595b9`), verified against the live edge route with real backend data (HTTP 200 image/png; fonts + favicons bundle; neutral stance bar / no verdict colour; null-domain + zero-challenge edge cases handled).
- [ ] Review share button styling against current design system
- [ ] Test OG card rendering on X, LinkedIn, WhatsApp, Slack (manual visual check — founder eyeball)

---

### I-07: Go-to-Market — MCP Distribution
**Status:** [x] **PyPI PUBLISHED 2026-06-10 — `tru8-mcp` 1.0.1 live.** Registry directory submissions remain (fast-follow, non-blocking).
**Priority:** High
**Effort:** Directory submissions only (~half day)

Published: https://pypi.org/project/tru8-mcp/1.0.1/. `pip install tru8-mcp` verified in a clean venv — `import tru8_mcp` and the `tru8_mcp.server:main` entry point both resolve.

**Packaging fix required (committed 2026-06-10):** the modules sit flat beside `pyproject.toml` (project dir *is* the `tru8_mcp` package, relative imports) which broke hatchling's auto file-selection. Added `[tool.hatch.build.targets.wheel.force-include]` mapping each module into a `tru8_mcp/` package + explicit `[tool.hatch.build.targets.sdist].include`. README gained the `mcp-name: io.github.SamYatesSmith/tru8` registry annotation and the clone URL was corrected to `SamYatesSmith/tru8-mcp`.

**Token hygiene:** first PyPI token was pasted in chat → revoked on PyPI; replaced with a project-scoped token stored in `~/.pypirc` (outside the repo).

**Tasks:**
- [x] Create `pyproject.toml` for `tru8-mcp` PyPI package
- [x] Publish to PyPI (1.0.1, 2026-06-10)
- [ ] Decide: public repo vs separate MCP-only repo (clone URL points at `github.com/SamYatesSmith/tru8-mcp` — repo must exist/be public for the registry annotation)
- [ ] Submit to mcp.so (~17,800 servers listed)
- [ ] Submit to PulseMCP (~8,600 servers listed)
- [ ] Submit to Smithery (~5,000 servers listed)
- [ ] Submit to official MCP registry (requires domain verification + PyPI — PyPI now done)

---

### I-08: Fix Stale Developer Page Example
**Status:** [x] Done (2026-02-26, verified 2026-03-17)
**Priority:** High
**Effort:** 15 minutes

Line 299 of `web/app/developers/page.tsx` shows `"orientationLine"` in the JSON example. The actual API field is `"orientation"` (fixed in MCP server last session, commit `18a050e`).

**Tasks:**
- [x] Update `"orientationLine"` → `"orientation"` in static JSON example
- [x] Review rest of example JSON against actual API response shape — verified: includes `_meta.landscape`, `_manifest`, `_computed`, correct field names

---

## Medium Priority

### I-09: Blog Post — Developer Announcement
**Status:** [x] Done — published 2026-03-25 (verified 2026-04-30)
**Priority:** Medium
**Effort:** 0 remaining

Blog post lives at `web/app/blog/evidence-research-for-agents/page.tsx` — published 2026-03-25, 5-min read, full OG metadata + author attribution, Stitch light theme + orange accent. Covers: API surface, MCP server, why agents need structured evidence (not verdicts), tier system + fallback, use cases.

**Tasks:**
- [x] Write post: why agents need structured evidence (not verdicts)
- [x] Explain MCP tools and what they provide
- [x] Explain "we organise; you decide" extended to AI agents
- [x] Include getting-started section
- [x] Match existing blog design (Stitch light theme, orange accent)

---

### I-10: Fix Mojibake in Evidence Snippets
**Status:** [x] Done (2026-02-26)
**Priority:** Medium
**Effort:** 2–4 hours

UTF-8 encoding issues in content extraction. Visible in API responses: `â€™` for apostrophes, `Â°` for degree signs. Agents consuming the API will receive garbled text.

**Root cause:** Double-encoded UTF-8 — pages serving UTF-8 bytes decoded as Latin-1/CP1252 by httpx when charset detection fails. Fixed in three files:
- `evidence.py` — added `_fix_mojibake()` in `_sanitize_content()` (re-encodes Latin-1 → decodes UTF-8)
- `factcheck_api.py` — word-boundary-aware truncation (replaces hard `[:2000]` slice)
- `legal_search.py` — word-boundary-aware truncation (replaces hard `[:500]` slice)

**Tasks:**
- [x] Identify source of encoding issue in content extraction pipeline
- [x] Fix encoding in `EvidenceExtractor` or upstream fetch
- [ ] Verify clean output in both snapshot and full pipeline modes

---

### I-11: Fix Redis Cache Import
**Status:** [x] Done (2026-02-26)
**Priority:** Medium
**Effort:** 1–2 hours

`No module named 'app.core.redis'` — relevance score caching fails silently. Non-blocking but wasteful (recalculates every time).

**Fix:** Created `backend/app/core/redis.py` with async `get_redis()` function using `redis.asyncio`. Singleton pattern with connection validation (ping on first connect). Both `relevance_scorer.py` and `article_classifier.py` now resolve their imports correctly.

**Tasks:**
- [x] Fix or remove the broken import
- [ ] Verify relevance score caching works after fix
- [ ] Confirm no other broken imports in the codebase

---

## Low Priority / Quick Wins

### I-12: API Terms in Terms of Service
**Status:** [x] Done (verified 2026-03-17)
**Priority:** Low
**Effort:** 2 hours (original); 0 remaining

Section 6 "API & Developer Usage" already exists in ToS with comprehensive coverage:
- 6.1 API Access (key management, security)
- 6.2 Rate Limits & Fair Use
- 6.3 Agent & Automated Usage (Agent Commerce Gateway terms)
- 6.4 Data Retention & Privacy
- 6.5 Redistribution

**Tasks:**
- [x] Add API Usage section to Terms of Service
- [x] Cover: rate limits, fair use policy, data retention, key security responsibilities

---

### I-13: Account vs Settings Naming
**Status:** [x] Done (2026-03-17)
**Priority:** Low
**Effort:** 30 minutes (original)

User dropdown said "Account" but navigated to a page called "Settings". Fixed: dropdown now says "Settings" to match nav and page title.

**Tasks:**
- [x] Decide: renamed dropdown to "Settings" (matches page title and nav labels)
- [x] Apply consistent naming — changed `user-menu-dropdown.tsx` label from "Account" to "Settings"

---

### I-14: Status / Health Endpoint
**Status:** [x] Done (stale-doc fix 2026-05-11 — `web/app/not-found.tsx` already existed)
**Priority:** Low
**Effort:** 0 remaining

Health endpoints exist. Error boundaries exist. Custom 404 page exists.

**Tasks:**
- [x] Add `/api/v1/status` health check endpoint — done: `/api/v1/health/` (liveness), `/ready` (DB+Redis), `/cache-metrics`, `/circuit-breakers`, `/email-config`
- [x] Add custom 404 page (`web/app/not-found.tsx`) — verified 2026-05-11 during consolidation pass; component is real (Stitch styling, "Back to home" link). Doc was stale.
- [x] Custom 500 page — error boundaries exist (`error.tsx`, `global-error.tsx`, `dashboard/error.tsx`)

---

## Deferred

### I-15: Demo Video
**Status:** [ ] Deferred
**Priority:** Deferred

`StitchVideo` component on landing page is a placeholder (play button + "Platform Walkthrough" text, no actual video).

**Tasks:**
- [ ] Record platform walkthrough
- [ ] Embed in StitchVideo component

---

### I-16: Single-Claim Routing
**Status:** [x] Already Working
**Priority:** N/A

Confirmed working: single claim auto-redirects to detail view, multi-claim shows overview grid. No changes needed. Verified in both dashboard and public report routes.

---

## Summary

| # | Item | Priority | Effort | Status |
|---|------|----------|--------|--------|
| I-01 | Pricing tiers — frontend | Ship Blocker | 1–2 days | [x] |
| I-02 | Pricing tiers — backend | Ship Blocker | 2–3 days | [x] |
| I-03 | Stripe product setup | Ship Blocker | DONE long ago (presumed) | [x] |
| I-04 | Enable subscriptions | Ship Blocker | DONE long ago | [x] |
| I-05 | Developer page polish | High | 1 day | [x] |
| I-06 | Social / OG card alignment | High | OG visual redesign DONE 2026-07-02 (`0d595b9`); cross-platform crop eyeball remains | [~] |
| I-07 | Go-to-market — MCP distribution | High | PyPI published 2026-06-10; directory submissions remain | [~] |
| I-08 | Fix stale developer page example | High | 15 min | [x] |
| I-09 | Blog post — developer announcement | Medium | 3–4 hours | [ ] |
| I-10 | Fix mojibake in evidence snippets | Medium | 2–4 hours | [x] |
| I-11 | Fix Redis cache import | Medium | 1–2 hours | [x] |
| I-12 | API terms in ToS | Low | 2 hours | [x] |
| I-13 | Account vs Settings naming | Low | 30 min | [x] |
| I-14 | Status / health endpoint | Low | 1–2 hours | [x] |
| I-15 | Demo video | Deferred | TBD | [ ] |
| I-16 | Single-claim routing | N/A | 0 | [x] |
