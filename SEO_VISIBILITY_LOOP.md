# SEO / Visibility Maintenance Loop — runbook for the weekly cloud agent

This file is the self-contained brief for the `tru8-visibility-loop` scheduled
agent. The agent starts with zero context beyond the cloned repo, so everything
it needs is here. (The richer human plan lives in `audit/2026-06-27_visibility_plan.md`,
but `audit/` is gitignored and NOT in the checkout — do not rely on it.)

**Context.** Tru8 is an AI evidence-research platform. The web app is a Next.js 14
App Router project in `web/`. Workflow is trunk-based: commits to `main`
auto-deploy to **production** via Railway. Live site: https://www.trueight.com.
You can deploy to production — **safety first**.

---

## STEP 1 — Health check (ALWAYS run first; report PASS/FAIL for each)

1. `curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' https://trueight.com/`
   → expect **308** redirecting to `https://www.trueight.com/`
2. `curl -sS -o /dev/null -w '%{http_code}' https://www.trueight.com/sitemap.xml`
   → expect **200**
3. `curl -sS https://www.trueight.com/robots.txt`
   → expect a `User-Agent: GPTBot` AI-bot block **and** a `Sitemap:` line
4. `cd web && npm install && npm run build` → expect **exit 0** (23+ routes compile)

If ANY health check FAILS: do **not** attempt a backlog item. Report the failure
as the priority finding and STOP.

---

## STEP 2 — Implement exactly ONE on-site backlog item (only if health is green)

Pick the **first** item below that is **not already done** (inspect the code to
decide). Implement only that one, to a high standard.

1. **`/r/[id]` report pages** (`web/app/r/[id]/`): ensure clean server-rendered
   HTML, indexable, an answer-first summary high in the DOM, sound heading
   hierarchy. Improve the existing JSON-LD only if clearly incomplete.
2. **Answer-first opening paragraph** (a concise direct answer, ~40–80 words) placed
   high on `/research`, `/compare`, and `/developers` — the structure AI answer
   engines quote. One page per run is fine.
3. **FAQ + FAQPage JSON-LD** on `/developers` and `/pricing`. Mirror the existing
   pattern in `web/components/marketing/stitch-faq.tsx` (a server component that
   renders visible Q&A + a `FAQPage` `application/ld+json` script). Reuse, don't
   reinvent.
4. **Internal linking** — add a few genuinely useful contextual links between the
   marketing pages and the two blog posts (`web/app/blog/*`).
5. **Core Web Vitals** — find a marketing component marked `'use client'` that has
   no real interactivity and convert it to a server component. One per run.

---

## VERIFY before committing

- `cd web && npm run build` must exit 0.
- For copy/markup changes, confirm the change is present in the rendered HTML:
  `cd web && (PORT=3100 npm run start &) ; sleep 6 ; curl -sS http://localhost:3100/<route> | grep -i '<expected text>'`
  then stop the server.
- If the build fails, or you are not confident the change is correct and safe,
  make **NO commit** — revert your edits and report what you tried.

## COMMIT (trunk-based)

- One bounded change per run. Commit directly to `main` and push (Railway deploys).
- Conventional message, e.g. `feat(web): SEO — answer-first opener on /compare`.
- End the commit message with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Only `git add` the specific files you changed — never `git add -A` (it sweeps in
  untracked local-only files).

## STEP 3 — If no backlog item remains

Make NO code changes. Report status + the single next **off-site** action the
founder should take (these are theirs, not yours): GSC indexing requests, Bing
Webmaster Tools, authentic brand mentions on Reddit/Hacker News, Wikipedia
references where legitimately relevant, SaaS/AI directory listings.

---

## HARD CONSTRAINTS — do not violate

- **Never** generate mass/automated marketing content or programmatic/template
  pages. Google penalises "scaled content abuse" (50–90% traffic drops in 2026).
  Quality, single, vetted changes only.
- **Positioning locks:** no verdict language; never colour evidence
  supports/challenges green/red/amber ("we organize; you decide"). Use "research",
  not "verification", in positioning/marketing copy. Do **not** rename the
  functional `/verify/{id}` manifest endpoint or the "Verification Record" tier.
  US spelling on marketing pages ("organize"). Terminology: "evidence research",
  "analysis" — never "fact-checking" or "verdict".
- Report a short summary every run (health results + what you changed or why not).
