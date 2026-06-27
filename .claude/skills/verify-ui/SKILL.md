---
name: verify-ui
description: >-
  Verify a frontend/UI change in the Tru8 web app actually works and stays
  on-design before calling it done — for routing, nav, marketing pages, layout,
  and copy changes where correctness is largely visual and behavioural rather
  than unit-testable. Use after building a UI slice, or when asked to "verify
  the UI", "check the page", "make sure the nav/routes work", or "confirm it's
  on-brand". Runs the build + the app, drives it with the browser, and checks
  six dimensions with evidence: build/compile, route resolution (no 404s), nav
  + link correctness, design-system adherence (Stitch tokens), positioning/copy
  compliance (no verdict language, evidence scoped), and accessibility + mobile.
  Distinct from `verify-implementation` (spec/quality/drift on any code) and
  `code-review` (bug-hunt a diff) — this one observes the rendered UI.
---

# Verify UI

Confirm a UI change *renders and behaves correctly and stays on-design*, with
evidence — never an assumption. A clean diff and a passing build are necessary
but not sufficient: the page must actually render, the routes must resolve, the
links must point where they claim, and the result must obey the Stitch design
system and the positioning copy rules. If a check was not run, say so; if it
failed, show the output/screenshot.

## Inputs
- The slice being verified (files changed) and its **shape/spec doc** if one
  exists (e.g. `audit/2026-06-17_homepage_nav_shape.md`).
- The **design + copy constraints**: `audit/2026-06-17_repositioning_agreements.md`
  §2 (tokens, typography, layout, voice §2.5), Part 1 (positioning), Part 4 (copy),
  §3.2.1 (routing). The Stitch style guide under `audit/track-c/stitch/` is the
  deeper reference.

## How to run the app
```bash
cd web
npm run build           # 1. must compile/typecheck clean (Next.js build)
npm run dev             # 2. dev server on http://localhost:3000 (run in background)
```
Drive it with the browser MCP tools (`browser_navigate`, `browser_snapshot`,
`browser_take_screenshot`, `browser_console_messages`, `browser_resize`). Use a
desktop viewport (≥1280px) and a mobile viewport (≥375px) for every route.

## The six checks (each needs evidence)

1. **Build / compile.** `npm run build` passes. Capture the result. A new type
   or build error is a FAIL; a pre-existing unrelated error must be named as such.

2. **Route resolution — no 404s.** Navigate every route the slice adds or links
   to. For the repositioning that means at least: `/`, `/developers`,
   `/developers#mcp` (anchor exists), `/api`, `/compare`, `/pricing`, `/research`,
   `/dashboard`. Each returns the page, not a 404/500. Screenshot proof.

3. **Nav + link correctness.** Every nav item and CTA points where the spec says
   (Product·API·MCP·Compare·Pricing·Docs; `Get API Key`→/developers,
   `Research App`→/research). Click each; confirm the destination. Confirm the
   primary CTAs **navigate** (do not open the auth modal). Confirm the mobile
   hamburger sheet opens, traps focus, closes on Esc, and lists the same links.

4. **Design-system adherence (Stitch).** Spot-check rendered styling: white
   surfaces, 1px zinc borders, **no shadows/gradients**, Inter + JetBrains Mono,
   orange `#EA580C` used only as accent (never a fill), mono micro-labels
   uppercase. No off-system colours. Flag any traffic-light verdict colouring.

5. **Positioning / copy compliance.** Read the rendered copy. MUST hold:
   no "verdict / confidence score / verified-true"; "verify the evidence" is OK;
   "evidence" is **scoped at first use** and uses bound forms (record/landscape),
   never bare-totalising; not "article-based"; no compliance/regulatory claims;
   dev-led primary with a quiet human path (no splash); US spelling on marketing/
   dev surfaces, UK on legal/product. Quote any offending line.

6. **Accessibility + mobile.** Single `<h1>` per page, section `<h2>`s; visible
   focus states; `aria-*` on the mobile sheet (`expanded`/`controls`/dialog);
   skip-to-content; legible contrast (watch `text-zinc-400` body copy). Mobile
   viewport: sections stack legibly, no orphaned consumer bottom-nav, sheet works.
   Check `browser_console_messages` for runtime errors/hydration warnings on each
   route.

## Output
A markdown report:
- **Verdict:** PASS / PASS-WITH-NITS / FAIL.
- Per-check result with evidence (command output, screenshot reference, quoted copy).
- **Must-fix** (blocks done) vs **nits** (non-blocking), each with file + concrete fix.
- What was NOT verified and why.

Do not commit or push. Stop the dev server when finished.
