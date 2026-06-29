# Tru8 pre-launch page review — 2026-06-29

> **This section supersedes nothing.** It is a point-in-time, page-by-page audit of the public brand surface, run before pushing the project to market. Other review docs (`docs/marketing/LANDING_PAGE_REVIEW.md`, `audit/2026-06-1x_*`, `docs/DESIGN_SYSTEM.md`) are older and partly stale — do not blend them with this. Ground truth here is current code.

## How it was made
- **Lens:** the fixed researcher buyer (“show-your-working” journalists / analysts / policy researchers).
- **Scope:** marketing pages + the public report `/r/[id]`. (Logged-in dashboard out of scope.)
- **Method:** baseline derived from code → one reviewer per page (aesthetic / copy / content / positioning / IA / accessibility) → adversarial verification of every finding against current source → cross-page synthesis. Multi-agent workflow `tru8-page-review-2026-06-29`.
- **Staleness rule:** docs are intent only; live code + rendered page are the sole ground truth; doc-vs-code conflicts are themselves findings.

## Read order
1. [`_BASELINE.md`](./_BASELINE.md) — the real shipped design + positioning + forbidden-word scan.
2. [`00_SYNTHESIS.md`](./00_SYNTHESIS.md) — cross-page drift map, launch blockers, prioritized roadmap.
3. Per-page docs below.

## Pages

| # | Page | Buyer fit | Speaks to | Verified findings | Blockers |
|---|---|---|---|---|---|
| 01 | [Homepage  /](./01_home.md) | 3/5 | mixed | 10 | 0 |
| 02 | [Research front door  /research](./02_research.md) | 5/5 | researcher | 9 | 0 |
| 03 | [Compare  /compare](./03_compare.md) | 2/5 | developer | 8 | 0 |
| 04 | [Developers  /developers](./04_developers.md) | 4/5 | developer | 8 | 0 |
| 05 | [Pricing  /pricing](./05_pricing.md) | 4/5 | researcher | 6 | 1 |
| 06 | [About  /about](./06_about.md) | 2/5 | mixed | 9 | 0 |
| 07 | [Contact  /contact](./07_contact.md) | 3/5 | mixed | 7 | 0 |
| 08 | [Blog index  /blog](./08_blog.md) | 2/5 | developer | 8 | 0 |
| 09 | [Blog: first-public-release](./09_blog-first-public-release.md) | 3/5 | mixed | 9 | 0 |
| 10 | [Blog: evidence-research-for-agents](./10_blog-evidence-research-for-agents.md) | 2/5 | developer | 9 | 0 |
| 11 | [Public report  /r/[id]](./11_public-report.md) | 3/5 | mixed | 7 | 0 |
| 12 | [Legal pages (privacy / terms / refund / cookie)](./12_legal.md) | 3/5 | mixed | 8 | 0 |
