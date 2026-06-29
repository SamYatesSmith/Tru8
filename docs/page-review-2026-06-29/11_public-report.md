# Public report  /r/[id]

> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 3/5 — currently speaks to **mixed** (researcher substance wrapped in a consumer-share frame)

The underlying substance is genuinely strong for the "show-your-working" researcher: per-claim for/against dispositions (supports/challenges/context filter pills in `LibrarianView`), a "Retrieval Transparency" receipt panel that names every *excluded* source and why (`RetrievalFunnel` — Duplicate / Satire / Extraction Failed / Not in map), named gaps in `ClaimSummaryPanel`, a tier/type classification ledger with call numbers, a stable reference id, a canonical permalink, and a real "Download Evidence Record (PDF)" export. That is exactly the defensible sourcing a researcher hands an editor. But the page is framed first as a *social share* artifact (WhatsApp share, "Reply on X", "Share your findings"), its first-glance summary leads with green/amber state colour, and — most tellingly for a *citable* artifact — it never exposes the tamper-evident `/verify` manifest that is supposed to make a Tru8 record defensible. So it half-speaks to the researcher and half to a consumer sharer.

**Overall:** Content depth is the page's strength and is close to right. The brand risks are (1) a green-supported / amber-disputed colour read at summary altitude that cuts against the "no verdict" core, (2) the absence of any verification/citation surface on the one page that is meant to be cited, and (3) a social-virality frame that dilutes the professional positioning. None are deep rewrites; all sit inside the locks.

## Verified findings

### MAJOR

**[content / positioning] The citable artifact never exposes its own verifiability**  _( confirmed )_
- **Evidence:** A repo-wide grep of the entire `/r/` path and `ClaimSummaryPanel` for `verify|manifest|tamper` returns nothing, and there is no `web/app/verify` route (`Glob web/app/verify/** → No files found`). The only trust/permanence affordances on the page are the share block and the disclaimer: _"Sources are gathered from publicly available material and classified automatically. Results should be used as a starting point for further research, not as definitive fact."_ (`public-report-client.tsx` L444-446).
- **Why it matters (buyer):** The researcher's reason to hand this URL to an editor is that the record is *fixed and checkable* — that the evidence set, classifications and exclusions can't be quietly edited later. The backend ships a tamper-evident manifest + `GET /verify/{check_id}`, but the public report — the exact surface meant to be cited — gives no link to it. The defensibility story is invisible at the point of citation.
- **Fix:** Add a small mono "Verification" line in the meta/footer region linking to the manifest check, worded strictly as the lock allows: "Tamper-evident record · verify integrity" → `/verify/{id}` (or the backend verify endpoint). Do not write "independently verifiable". Stay in zinc mono micro-label tokens; no new accent fill.

**[copy / positioning] First-glance summary reads as a green/amber verdict**  _( confirmed )_
- **Evidence:** In `ClaimSummaryPanel.tsx`, "Zone 2 — the answer" renders coloured element-state counts directly under the claim headline (L201-252) using `ELEMENT_STATE` text colours `supported: text-emerald-500`, `disputed: text-amber-500` (`ElementStateBadge.tsx` L20-21). On a single-claim public report this zone *is* the page-level summary the reader sees first.
- **Why it matters (buyer):** The buyer purchases "no verdict" as a *feature*. Green-supported / amber-disputed counts presented as "the answer" under the claim is exactly the traffic-light read the brand forbids ("never green/red/amber for supports/challenges"). The lock permits muted element-state colour only *inside* claim-map element context, not as a page-level summary; emerald-500/amber-500 at summary altitude pushes over that line.
- **Fix:** Desaturate the state counts at summary altitude — render them in zinc (e.g. `text-zinc-600` with the label carrying meaning) and reserve the emerald/amber element-state colour for *inside* the Map roster / Evidence element context where it is a genuine element indicator. Keep the counts and deep-links; only drop the colour at the "first-glance answer" level.

**[positioning / copy] Social-virality framing dilutes the professional citable artifact**  _( confirmed )_
- **Evidence:** The share block leads with consumer channels and copy: WhatsApp button (`handleShare('whatsapp')`, L416-422), "Reply on X" with _"Post your findings in the original thread"_ (L383-394), and the prompt _"Share your findings:"_ / _"Share as a new post:"_ (L398-399). The file header comment even states _"This is the landing page for all social shares."_ (`page.tsx` L8). There is no "cite this", permalink-copy-for-citation, or "how this was built / methodology" affordance framed for a professional reader.
- **Why it matters (buyer):** A journalist or policy researcher handing this to an editor wants citation/permanence/methodology cues, not a WhatsApp button and a Reply-on-X CTA. The current hierarchy reads as a consumer engagement tool, which undercuts the "research record" positioning the rest of the page earns.
- **Fix:** Keep share, but lead the block with the professional affordances — "Copy permalink" and "Download Evidence Record (PDF)" first, then a quieter "Share" row. Relabel _"Share your findings"_ to neutral "Share this record". Optionally add a "Cite" snippet (title · reference id · date · URL). No new tokens needed.

**[accessibility] Pervasive low-contrast micro-text on a public document**  _( confirmed )_
- **Evidence:** The page leans heavily on `text-[9px]`/`text-[10px]` mono in `text-zinc-400` on white — e.g. the header meta row (`public-report-client.tsx` L207), the disclaimer at `text-[12px] text-zinc-400` (L444), every `EvidenceMetaStrip` label (`text-[9px] ... text-zinc-400`), the gaps list, and the `ViewSelector` subtitles. `zinc-400` (#A1A1AA) on white is ≈2.9:1 — below WCAG AA (4.5:1 for this size).
- **Why it matters (buyer):** This is the public, shareable, citable artifact — the one page guaranteed to be read by third parties (editors, on projectors, on mobile). The reference id, dates, source counts and disclaimer are core content, not chrome, and several are at the smallest size and lowest contrast on the page.
- **Fix:** Bump load-bearing micro-labels from `zinc-400` to at least `zinc-500`/`zinc-600`, and raise the disclaimer to `text-zinc-500` at `text-[13px]`. This is a token-wide pattern, so fix at the shared-component level (`EvidenceMetaStrip`, `DiagnosticFlag`, header) rather than per-page. Stays within zinc neutrals.

### MINOR

**[IA/SEO] Every auto-generated report is indexable with no thin-content guard**  _( confirmed )_
- **Evidence:** `generateMetadata` sets title/description/canonical/OG/Twitter and JSON-LD (`WebPage` + `Dataset`) but no `robots` directive (`page.tsx` L45-92, L103-125); every `/r/[id]` is indexable by default. The visibility memory explicitly warns that mass thin/auto content is penalised.
- **Why it matters (buyer):** Thousands of machine-generated report pages with near-identical structure indexed at once can read as a doorway/thin-content farm and harm the domain's already zero-authority SEO standing — the opposite of the visibility push's intent.
- **Fix:** Decide an indexing policy: either `noindex` on `/r/` (keep them shareable but not crawled) or index only a curated/featured subset. Self-canonical is already correct; the missing piece is the crawl decision.

**[aesthetic / copy] Reference id duplicated; "X" share uses the stale Twitter glyph**  _( confirmed )_
- **Evidence:** The reference id renders twice — once in the header (`REF: TRU-{...}`, L208) and again as "Reference" in `EvidenceMetaStrip` (L34-41). Separately, the "Share on X" button uses lucide's `Twitter` icon (L5, L407), and the meta `twitter.site` is `@tru8app`.
- **Why it matters (buyer):** On a document-grammar artifact, repeating the same id back-to-back looks like a template seam, and a bird glyph on an "X" button is a small but visible staleness tell on a brand-critical page.
- **Fix:** Drop the header `REF` line (keep the canonical one in `EvidenceMetaStrip`) or vice-versa. Swap the Twitter glyph for an X mark.

### NIT

**[accessibility] Heading order is non-sequential**  _( confirmed )_
- **Evidence:** `h1` report title (L204) → multi-claim `ClaimSectionCard` claim text is `h3` (`ClaimSectionCard.tsx` L79) → `ClaimSummaryPanel` claim headline is `h2` (`ClaimSummaryPanel.tsx` L197) → share/CTA `h3`. So `h3` can precede the first `h2`.
- **Why it matters (buyer):** Screen-reader users navigating by heading get a jumbled outline of a document that is otherwise well-structured.
- **Fix:** Make the multi-claim section cards `h2`/`h3`-consistent with the summary panel, or wrap the claim stack under a visually-hidden `h2`.

## Strengths to keep
- **Receipts are real and honest.** `RetrievalFunnel` ("Retrieval Transparency") names excluded sources by reason (Duplicate / Satire / Extraction Failed / "Not in map") and shows Examined → Organised → Excluded — exactly the "no hidden curation, every exclusion has a receipt" invariant a researcher needs.
- **For-and-against is first-class.** Disposition filter pills (supports/challenges/context) and element-state deep-links from the summary into a filtered Evidence lens let a reader pull up *only* the challenging evidence — the buyer's core job.
- **Genuine artifact affordances.** Stable `TRU-xxxx-xxxx` reference id, self-canonical permalink, `?view=`/`?rel=`/`?element=` deep-link persistence, and a no-auth "Download Evidence Record (PDF)" export make the page behave like a citable record.
- **Orientation stays mechanical and labelled.** The `DiagnosticFlag label="Orientation"` line is presented as a neutral derived read, not a verdict — compliant, keep.
- **On-brand document grammar.** Light theme, zinc neutrals, single orange accent used as a 2px top rule on the summary panel (not a fill), Inter + JetBrains Mono, 1px borders, no shadows — matches the Stitch lock.
- **Disclaimer is correctly non-verdict.** "Results should be used as a starting point for further research, not as definitive fact" — exactly the right frame; keep the wording.
