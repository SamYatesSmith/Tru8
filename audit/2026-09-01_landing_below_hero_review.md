# Landing page below the new hero — section review (2026-09-01)

> Companion to `audit/2026-09-01_claim_field_front_door_review.md`. The hero is
> being reworked (canvas: centred animated mark → "Context, not verdicts." →
> lede → claim field with the mark as the go tile → footer row). This reviews
> what sits BENEATH it on `web/app/page.tsx`, read from source and the live page
> (www.trueight.com, 2026-09-01). **Review only — nothing changed.**

## Current order (page.tsx) and what each does

| # | Component | Heading | Job today | With the new hero |
|---|---|---|---|---|
| — | `stitch-hero` | Evidence, not verdicts. | Button CTA + sample | **Becomes the field** |
| 00 | `stitch-why` | Most tools hand you a conclusion. | Category argument + comparison table (APIs → list · evals → score · fact-checkers → verdict · Tru8 → record) | Argues before it shows. Too early for a visitor who has a field in front of them |
| 01 | `stitch-record` | Not a verdict. A structured evidence record. | Six-row anatomy of the record + manifest | The right first section — *what will I get?* |
| 02 | `stitch-product-preview` | The summary, then the lenses. | Real screenshots: summary + 3 lenses + "also inside" line | Strongest proof on the page; long |
| 03 | `stitch-process` | One submission, a retainable record. | 4 steps | Step 01 ("Submit") is now demonstrated by the hero |
| 04 | `stitch-edges` | An honest record has edges. | 4 honest limits | Keep; first edge duplicates the headline |
| 05 | `stitch-developer-showcase` | The same record, structured for agents. | API/MCP/webhooks, £0.02 | Fine where it is |
| — | `stitch-faq` | What Tru8 does — and what it deliberately does not. | 5 Q&A + JSON-LD + 2 blog links | Keep Q&A; blog links stale (Jan/Mar) |
| — | `stitch-closing-cta` | See the record for your claim. | Button → dashboard | **Contradicts the top** — must be the field again |

## Findings

1. **"Not a verdict" is said five times.** Hero headline, 01's heading, 04's
   first edge, FAQ Q2, and 00's whole premise. Once the headline carries it,
   01's heading should describe the record ("A structured evidence record,
   every time."), 04's first edge should go, and 00 becomes optional.
2. **The order argues before it shows.** Field → "Most tools hand you a
   conclusion" asks a stranger to accept a category critique before seeing a
   single result. Move 00 below the proof (or fold its table into `/compare`
   and keep only the "See the full comparison" link in the FAQ).
3. **The closing CTA sends people away from the page that has the field.**
   "Start a check" → `/dashboard/new-check` → auth modal. Reuse the hero's
   field component at the foot (same ring, same tile) so the page ends the way
   it starts. This is the one structural change I would insist on.
4. **Timing is stated three ways.** Live microline "~90 seconds", OUTREACH.md
   "~3 minutes", the canvas "about two minutes" (since removed). Read `stage_timings_s` from
   recent prod checks and use ONE figure everywhere (hero footer row, 04 Edges,
   FAQ).
5. **03 How it works can shrink.** Four cards say what 01 + the field already
   say. A single strip (Submit · Decompose · Retrieve · Return) under 01, or
   delete and let 02's screenshots carry it.
6. **02 Inside a check is proof — make it earlier and shorter.** Summary + two
   lenses is enough on the homepage; each screen should link to the *live*
   sample record, not only "view full size" (their own rule: proof, not
   pictures). The "also inside" line covers the rest.
7. **04 Edges — swap the duplicated edge for the missing one.** Drop "Not a
   verdict."; add the edge the field newly implies away: it is not instant
   (state the one figure from #4). Keep public-only · focused claims · snapshot.
8. **Eyebrow dropped in the new hero** ("Evidence research — not
   fact-checking"). The category line then lives in `<title>`, JSON-LD and
   FAQ Q1/Q2 — acceptable, and 01's eyebrow can carry "Evidence research" if
   it is missed.
9. **Scroll-reveal left sections blank in several captures** (keyboard
   PageDown, live page). If reveal starts at `opacity: 0`, content is invisible
   to slow devices, screenshot unfurlers and possibly crawlers until the
   observer fires. Verify `scroll-reveal.tsx` renders visible without JS /
   before intersection; not a conclusion, a check.
10. **FAQ "From the blog"** — two posts, newest March. On the homepage it reads
    as a dead blog. Keep the posts, drop the block from `/` until there is a
    third.

## Proposed order

```
HERO (field, mark as go tile)
01  THE RECORD          — "A structured evidence record, every time."
02  INSIDE A CHECK      — summary + 2 lenses, each linked to the live sample
04  EDGES               — public-only · focused claims · snapshot · takes ~N min
00  WHY NOT A VERDICT?  — comparison table (or move to /compare, link from FAQ)
05  FOR DEVELOPERS      — unchanged
FAQ                     — 5 Q&A, JSON-LD kept, blog block removed
CLOSE                   — the field again (shared component), sample link beneath
```

03 How-it-works: folded into a one-line strip under 01, or removed.

## Locks this respects
- D3 language lock (no verdict/score language anywhere above) · D-R4 single
  front door, no splash · "proof, not pictures" (sample record linked from the
  screens) · UK spelling.

## What it would touch (when built)
`web/app/page.tsx` (order), `stitch-record.tsx` (heading), `stitch-edges.tsx`
(edge swap), `stitch-product-preview.tsx` (trim + sample links),
`stitch-process.tsx` (fold/remove), `stitch-why.tsx` (retitle/move),
`stitch-faq.tsx` (drop blog block), `stitch-closing-cta.tsx` (becomes the
field), `sitemap.ts` lastmod for `/`. Verify with `/verify-ui` after.

## Decisions — founder, 2026-09-01 (same day)

1. **"Not a verdict" → exactly twice:** hero headline + FAQ Q2 (JSON-LD). Removed from 01's heading, 04's first edge; 00 folds away.
2. **00 + 01 FOLD into one sheet, "01 THE RECORD":** heading *"What comes back."*; sub *"A structured evidence record, every time: what supports each part of the claim, what challenges it, what's missing, and what was set aside and why."*; body = the six-row anatomy + manifest; closing line replaces the 00 table — *"Not a list of sources, not a score — the record."* (the third clause, "not a verdict", was cut: it would have made the word's third appearance; the headline and FAQ Q2 already carry it) → "See the full comparison →" (`/compare` keeps the table).
3. **Closing CTA = the hero field again** (shared component).
4. **Timing = "under a minute", everywhere** (founder: 30–60 s these days). ~~Hero footer row~~ (added by me, removed at the founder's request after launch — the footer row is "· Free to try ·" as on the canvas), new Edge *"Takes under a minute — not instant."*, FAQ, live hero's "~90 seconds" on rebuild. OUTREACH.md "~3 minutes" corrected in this commit.
5. **Order:** HERO → **02 Inside a check** (proof first; summary + 2 lenses linked to the live sample) → 01 Record (folded) → 04 Edges → 05 Developers → FAQ (blog block off) → CLOSE (field). **03 How-it-works removed.**

Status: **BUILT 2026-09-01 (same day), verified locally, committed on main, NOT pushed** (push = Railway deploy; founder's call).

## Build + verification record (2026-09-01)
- **Files:** `web/components/marketing/claim-field.tsx` (new, shared by hero + close), `stitch-hero.tsx`, `stitch-closing-cta.tsx`, `stitch-record.tsx` (fold), `stitch-product-preview.tsx` (sheet 01, summary + 2 lenses, live-sample links), `stitch-edges.tsx` (sheet 03, edge swap), `stitch-developer-showcase.tsx` (04), `stitch-faq.tsx` (timing Q in, blog block out, Q1 trimmed), `app/page.tsx` (order), `app/globals.css` (ring/halo/well/go), `app/sitemap.ts`, `app/about/page.tsx` (`/#how-it-works` → `/#record`), `lib/analytics.ts` (`claim_field_submit`), `middleware.ts` (redirect_url keeps the query), `app/dashboard/new-check/page.tsx` (`?text=`/`?url=` prefill + `run=1` auto-submit, params stripped before the run), `design/mobius-mark/build_assets.py` (+ `tru8-mark-dark{,-static}.svg` — the same object, opacities lifted 0.30–1.0). Deleted: `stitch-why.tsx`, `stitch-process.tsx`, `start-check-link.tsx`.
- **Checks:** `tsc --noEmit` clean · `next lint` no new warnings · `next build` clean · vitest 12 files / 111 pass · single `<h1>`, six `<h2>` · console: only Clerk dev-key warnings · routes `/ /about /compare /pricing /developers` 200.
- **Behaviour, observed on the running app:** signed-out `GET /dashboard/new-check?text=…&run=1` → `307 /?auth_redirect=true&redirect_url=%2Fdashboard%2Fnew-check%3Ftext%3D…%26run%3D1` (query survives) · signed-in submit from the hero lands on new-check with the claim in the CLAIM tab · `run=1` fires the submit and is stripped from the address bar first (proved with a 9-char claim: "Text must be at least 10 characters", nothing spent).
- **Evidence:** `design/preview/2026-09-01_home_hero_field_desktop.jpg`, `…_home_record_folded_desktop.jpg`, `…_home_edges_desktop.jpg`, `…_new_check_prefilled_from_field.jpg`, `…_new_check_autorun_triage_stop.jpg`.
- **Not verified:** mobile viewport in-browser (the extension window would not resize below desktop; layout is the same responsive classes as before + the mobile canvas), the full signed-out → sign-in → auto-run round trip (needs a signed-out Clerk session; the two halves were proved separately), and `/r/…?view=` sample links against prod (local DB lacks that record).
- **Flag:** headline colour `#B2B2BA` is the founder's canvas choice; it measures ~2.1:1 on white, under the 3:1 large-text floor. One token to change.
- **Copy:** "verdict" now appears twice in visible page text — the headline and FAQ Q5 (where it answers "Does Tru8 use AI to decide what is true?"). FAQ Q1's "Tru8 does not issue a verdict." was redundant beside the tagline and was cut. The `<meta>` description still carries "No verdict".


## Security + bug pass 1 — 2026-09-01 (founder: "/loop to verify … air tight security wise")

Threat model read against the diff, then verified on the running app (signed-out session).

| # | Finding | Severity | Fix | Verified |
|---|---|---|---|---|
| S1 | **Open redirect via `?redirect_url=`** — `page.tsx` passed the raw query value to Clerk's `forceRedirectUrl`, which trusts the app. `/?auth_redirect=true&redirect_url=https://evil.example` would sign a visitor in on our modal and land them off-site (`//host` and `/\host` too). Pre-existing, but the front-door change made this param load-bearing. | High | `lib/safe-redirect.ts` `safeInternalPath()` — string, single leading `/`, second char not `/` or `\`, no whitespace/control chars, ≤2048, resolves on a fixed origin; else `undefined` → modal default `/dashboard`. 16 unit cases. | Probe on the running app: `redirect_url=https%3A%2F%2Fevil.example%2F` → landed on `/dashboard`. |
| S2 | **Drive-by spend via `?text=…&run=1`** — a link anyone could send a signed-in user; one click spent a credit with no further action. | High | Claim moved OUT of the URL into a single-use, tab-scoped **intent** (`lib/claim-intent.ts`, sessionStorage, 30-min TTL, consumed on first read). `run=1` auto-submits only when an intent this tab wrote exists; a bare `?run=1` is stripped and does nothing. `?text=` support removed; legacy `?url=` prefill kept (no auto-run). | Bare `/dashboard/new-check?run=1` → empty form, URL stripped, no API call (api.log). |
| S3 | **Claim text leaked into URLs** → server logs (seen in dev.log), PostHog `$current_url`, Sentry breadcrumbs, Referer. | Medium | Same fix as S2 — the URL is now `/dashboard/new-check?run=1`, nothing else. Analytics event carries only `input_type`/`surface`/`signed_in`. | Signed-out submit: intent present in sessionStorage, URL `/` with no claim. |
| B1 | **Field stuck disabled after the signed-out bounce** — the same `ClaimField` instance stays mounted through `/` → bounce → `/?auth_redirect…`, so `busy` never reset; closing the modal left a dead field. | Medium | `useEffect(() => setBusy(false), [searchParams])` — any query change re-arms it. | Textarea + go button `disabled: false` with the modal open and after Escape; typed claim still in the field. |
| — | XSS via prefilled text: React-escaped controlled inputs, no `dangerouslySetInnerHTML` on the path. Double-spend on refresh: params replaced before the run; `pendingRun` single-shot; `isSubmitting` guard. CSRF: the run needs the tab's own sessionStorage. | — | No change needed. | Code read. |

Trade-off recorded: sessionStorage is tab-scoped — a sign-in completed in another tab (email magic link) opens the console form empty rather than prefilled. Graceful miss, never a wrong run.

Checks after the pass: vitest **14 files / 123 tests** (two new suites), `tsc` clean, `next lint` clean on touched files, `next build` clean. Not verified: the post-sign-in half of the round trip (needs credentials); the sanitiser is unit-tested and the fallback was observed.

## Security + bug pass 2 — 2026-09-01 (fresh read of 17a6843 + 8dd68cc)

Walked every seam the fixes themselves introduced. **Nothing new in the change.** One adjacent, pre-existing tightening taken as defence in depth.

- **Intent lifecycle:** consumed on the first effect run; StrictMode's double-invoke and the `router.replace` re-run both see it gone and do nothing; `pendingRun` survives as state; the run effect reads the latest `handleSubmit`. Back after a run lands on the clean `/dashboard/new-check` with nothing to re-fire.
- **Intent without `run`** (bounced, dismissed the modal, later opened Start a check): prefill only, no spend. **Intent + stale-session reset** (modal signs a wedged client out, `auth-modal.tsx:57`): the intent outlives the reset and runs once after re-sign-in — correct, it is the visitor's own claim. Two tabs: separate storage, no crosstalk.
- **`safeInternalPath` edge cases:** `/dashboard/../..//host` and `/%2F%2Fhost` normalise on-origin; `/@host`, `/dashboard?x=//host` are paths; nested `?auth_redirect=true` inside `redirect_url` cannot loop (dashboard pages ignore it). Only consumer of `redirect_url` is `page.tsx` → `Navigation` → `AuthModal` (git grep).
- **`useSearchParams` in `ClaimField`:** `/` is server-rendered per request (it reads `searchParams`), so no static-render Suspense bail-out; build clean.
- **Taken (pre-existing, adjacent — B2):** the console form's `isValidUrl` accepted any scheme (`javascript:`, `file:`, `ftp:`) because `new URL()` alone does; the hero field already insists on `https?://`. Now http(s) only on the legacy `?url=` path too.

Checks: vitest 123 pass · `tsc` clean · lint clean on touched files · `next build` clean. **Loop closed here:** a full pass found nothing new in the change; the one edit was a hardening outside it.

## Post-launch fix — the console form flashed before the run (2026-09-01)

Founder, on prod: a signed-in submit from the hero showed the console form for ~1 s before the check started — the auto-run hopped through `/dashboard/new-check?run=1` (page render + the dashboard layout's server-side usage fetch), then fired. Read as mis-routing.

- **Signed in → no hop.** `ClaimField` now creates the check itself (`apiClient.createCheckStreaming`, the same call the console makes) and goes straight to `/dashboard/check/<id>?fresh=true`; a mono "Starting your check" status sits under the field meanwhile. Failures: limit/access → `/dashboard/new-check` (the saved intent prefills; the page's own banner explains); anything else → inline error, field re-armed. The intent is cleared on success so a later console visit is not prefilled with a claim already run.
- **Post-sign-in arrival with a pending run → never the form.** `new-check` renders a "Starting your check" panel (mark, status, the claim) until the check page takes over; the form returns only if something stops the run, with its message.
- Not observable here (needs a signed-in session in the extension); typecheck, lint, tests, build clean. Founder to confirm on prod.

## Post-launch fix — section rhythm (2026-09-01)

Founder, on prod: gaps and transitions between sheets were inconsistent. Cause: every sheet carried its own full-bleed `border-t` at the section edge AND the SheetHeader's container-width rule further down, with a different top/bottom padding per sheet (`py-24/32`, `py-28/40`, `py-20/28`) — two lines per boundary with 100–160 px of empty band between, and no two gaps equal. Record and Edges were both `zinc-50`, so that boundary had no band change at all.

**One rule now:** a sheet's ONLY divider is its SheetHeader rule, at the very top of the section (`pt-0`), so the background band changes colour on that line; the gap between sheets is the previous sheet's bottom padding, identical everywhere (`pb-24 md:pb-32`); no section `border-t`. Bands alternate white → zinc-50 → white → zinc-950 → white → dot-grid. The FAQ joined the document grammar as sheet 05 (it had its own eyebrow + rule). The closing section, which mirrors the hero and has no header, keeps one `zinc-200` rule. Verified on the dev build at each of the six boundaries.

## Post-launch fix — no screen that states the claim (2026-09-01)

Founder, on prod, signed in: after the direct-submit fix a submit still landed on a screen showing the claim. Cause: a fast paste-and-Enter beat Clerk's client load, so the field read `isSignedIn` as falsy and took the signed-out route (`/dashboard/new-check?run=1`), where the interstitial panel showed the claim. Two changes: (1) the field waits for Clerk (≤3 s, reading the live `window.Clerk` client) before choosing a route, so signed-in submits go straight to the check; (2) the interstitial — the founder's stated worst case — is now the animated mark alone, centred, with status text for screen readers only. No claim, no copy.
