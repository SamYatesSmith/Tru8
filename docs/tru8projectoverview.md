# Tru8 — MVP Project Overview

## 1. One-Liner & Value Proposition
**Tru8** lets users share a screenshot, link, text, or short video.  
It extracts atomic claims, retrieves dated evidence, runs fact verification,  
and returns verdicts: **Supported / Contradicted / Uncertain** with confidence percentages and citations.

**Why?** Instant, explainable fact checks with sources and dates, ready to share.

---

## 2. Target Users
- **Everyday sharers**: sanity-check viral posts before forwarding.
- **Teachers/students**: classroom media-literacy checks.
- **Comms/social teams, journalists**: quick pre-publication verification.
- **Initial revenue goal**: ~300 paying users → ~£1,500/month net.

---

## 3. Supported Inputs & Outputs
- **Inputs**:  
  - URL (articles, posts)  
  - Screenshot / image (via OCR)  
  - Short video link (YouTube/Vimeo transcript; Whisper fallback)  

- **Outputs**:  
  - Claim cards with verdicts, confidence %, citations (`publisher · date`), one-line rationale.  
  - Quick mode only at launch (Deep mode behind feature flag).

---

## 4. Design System
**Color palette:**  
- Dark Indigo `#2C2C54` (base surface / header)  
- Deep Purple-Grey `#474787` (cards / secondary surface)  
- Cool Grey `#AAABB8` (muted text, borders)  
- Light Grey `#ECECEC` (background / contrast)

**Semantic colors:**  
- Supported → Green `#1E6F3D`  
- Contradicted → Red `#B3261E`  
- Uncertain → Amber `#A15C00`

**Type scale:**  
- H1 36/44, H2 28/36, Section 20/28, Body 16/24, Caption 14/20

**Components:** Verdict Pill (✓/!/?) · Confidence % · Citation Chip (`Publisher · Date`) · Evidence Drawer · Usage Bar · Progress Stepper

**UI principles:** Clean, precise, minimal; strong visual hierarchy; accessible (WCAG AA); dark-leaning with Light Mode toggle later.

---

## 5. Tech Stack (stable & quick-release)

**Mobile:** React Native + Expo  
- UI: Tamagui or NativeWind  
- Navigation: expo-router  
- Auth: Clerk  
- Purchases: RevenueCat (IAP abstraction for iOS/Android)  
- Notifications: Expo Notifications  
- Analytics: PostHog; Errors: Sentry  

**Web:** Next.js (App Router) + Tailwind + Radix UI  
- Auth: Clerk  
- Payments: Stripe Billing/Checkout  
- Realtime: SSE (fallback polling)

**Backend:** FastAPI + Uvicorn  
- Jobs: Celery + Redis  
- DB: Postgres (SQLModel/SQLAlchemy)  
- Blobs: S3/Cloudflare R2  
- Vector: Qdrant (managed or Docker)  
- Search: Brave/SerpAPI (licensed)  
- HTML→Text: trafilatura + readability-lxml, bleach sanitisation  
- OCR: Tesseract (server)  
- Transcripts: YouTube Transcript API, fallback Whisper API  
- Embeddings: e5-small or bge-small (Sentence-Transformers)  
- Verifier (NLI): DeBERTa v3 MNLI (ONNX Runtime)  
- LLM (extractor/judge): cloud-hosted instruction model (text-only for MVP)  
- Observability: OpenTelemetry + Prometheus; Sentry

---

## 6. Verification Pipeline
1. **Ingest** → Fetch/parse URL, sanitize; OCR for images; transcript for video  
2. **Extract claims (LLM)** → JSON schema, ≤12 claims Quick mode  
3. **Retrieve evidence** → Search → fetch pages → extract dated snippets → embed → rank → top-5  
4. **NLI verify** → claim + snippet → support/contradict/insufficient → aggregate with recency/credibility weighting  
5. **Judge (LLM)** → 2–3 sentences; cite 2–3 strongest sources; return verdict + rationale  
6. **Calibrate** → map raw scores → confidence % (Platt/Isotonic)  
7. **Persist + bill** → store results; finalise credits; push notification

**Safety:**  
- Respect robots.txt, paywalls (metadata only if blocked)  
- Strip scripts, block prompt injection  
- Conservative labels (Supported / Contradicted / Uncertain)  
- GDPR endpoints; purge uploads after 30 days (unless saved)

---

## 7. Monetisation & Plans
- **Starter £6.99/mo** — 120 Quick checks  
- **Pro £12.99/mo** — 300 checks; unlock Deep mode (hidden initially)  
- **Add-on pack** — 100 credits for £8  

**Credits:**  
- Quick = 1 credit (≤2.5k words / ≤8 min video / ≤6 MB image)  
- Deep = 3–5 credits (hidden at launch)  

**Compliance:**  
- Mobile: RevenueCat (StoreKit/Play Billing)  
- Web: Stripe; backend normalises entitlements  
- Backend enforces entitlements & rate limits

---

## 8. Development Roadmap (6–8 weeks)

**Week 1** – Repos, FastAPI skeleton, Postgres migrations, Redis/Celery, Clerk + RevenueCat/Stripe test, Sentry/PostHog wired  
**Week 2** – Ingest (URL fetch + OCR + transcript), UI skeleton (Login, New Check, Progress, History), mock `/checks`  
**Week 3** – Claim extraction + JSON validation, search provider integration, snippet extractor, embeddings + Qdrant  
**Week 4** – NLI (ONNX), aggregation, judge prompt, end-to-end verdict cards, SSE + push notifications  
**Week 5** – Credits reservation/finalisation, usage bar, RevenueCat entitlements, Stripe webhooks  
**Week 6** – Hardening: sanitisation, guardrails, calibration, error states, privacy/terms, TestFlight/Play Internal testing  
**Week 7–8** – Buffer: token optimisation, dashboards, polish, app store listings  

**Feature flags (MVP-off):** Deep mode, reverse-image search, long-video path, Light theme, Local-only privacy mode

---

## 9. Acceptance Criteria
- Submitting a BBC article or screenshot yields 4–10 claim cards with ≥2 dated citations, verdict + confidence % within <10s  
- Credits decrement and usage visible; push notification on completion  
- iOS/Android IAP entitlements enforced via RevenueCat; Stripe web entitlements match  
- Accessibility: AA contrast, labelled verdicts/citations, reduced motion supported  
- Sentry: no P0s during 48h beta run; Admin dashboard shows tokens/check, cache hit-rate

---

## 10. Risks & Mitigations
- **COGS creep** → strict caps, caching, cheap→premium cascade  
- **Paywalls** → show headline + alt sources, explain limitation  
- **Defamation** → avoid “False”; use Contradicted/Uncertain + dates, allow reports  
- **Adoption** → free tier (3 checks/week), TikTok demos, educator outreach  
- **Legal** → decision-support disclaimer, GDPR compliance, data retention policy

---

## 11. Post-MVP Roadmap
- Deep mode (long articles/videos)  
- Reverse-image provenance checks  
- Classroom packs (bulk licences via Apple School Manager / Google EDU)  
- Browser extension (send-to-Tru8)  
- Local-only privacy mode (flagged)  
- Light theme toggle  

---

## 12. Goal
Release **Tru8** quickly to app stores and web, prove subscription + credit model,  
generate ~£1,500/month net from ~300 paying users.  
Use this as a **launch experience** and revenue milestone before scaling larger projects.
