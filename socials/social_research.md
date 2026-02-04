GOAL
Audit the current state of “Social Sharing / Integrations” in the codebase and produce a concise status report:
1) what exists today (implemented + working),
2) what is partially implemented,
3) what is missing,
4) exact next steps + file locations.

SCOPE (V1 targets)
- X share (link + OG card at minimum; auto-post only if already implemented)
- WhatsApp share (link-based)
- LinkedIn share (link-based)
- Slack/Discord: link unfurl only (OG tags), not bots
- Explicitly flag if any Facebook/IG/TikTok/Reddit integrations exist (shouldn’t, but verify)

OUTPUT FORMAT (keep it tight)
Return ONE markdown doc named: docs/social-sharing-audit.md with:
A) Summary (5 bullets max)
B) Current capabilities table:
   - Feature | Status (Done/Partial/None) | Where (file paths) | Notes
C) Inventory of relevant routes/components:
   - API endpoints (paths, handlers)
   - Frontend pages/components (share UI)
   - Metadata/SEO/OG generation (Next.js/head, middleware)
   - Any background jobs (queues, workers) related to posting
D) Evidence:
   - Grep results (short excerpts) showing key integration points
E) Gaps + TODOs:
   - Ordered checklist, highest impact first
F) Quick “definition of done” for V1 sharing

METHOD (do this systematically)
1) Repo map:
   - list top-level apps/services (e.g., backend, web) and confirm frameworks (Next.js, Django/FastAPI etc.)
2) Search for sharing keywords and providers:
   - “share”, “social”, “twitter”, “x.com”, “intent”, “whatsapp”, “linkedin”, “og:”, “OpenGraph”, “meta property”, “unfurl”, “slack”, “discord”, “embed”, “preview”, “cards”
3) Identify where public report pages exist (the URLs users would share).
4) Confirm OG tags actually render server-side (important for Slack/Discord/X previews).
5) Confirm environment/config:
   - any API keys for X/LinkedIn etc. (should be absent unless auto-post exists)
6) Run minimal checks if available:
   - unit tests for SEO/head tags
   - quick local render / curl of a public report URL and show returned meta tags.

CONSTRAINTS
- Do not implement anything yet.
- Do not refactor.
- Only inspect, summarize, and propose next steps with exact file paths.
- If anything is ambiguous, note it explicitly and propose how to verify quickly.

DELIVERABLE
Create docs/social-sharing-audit.md and print it to the console at the end.
