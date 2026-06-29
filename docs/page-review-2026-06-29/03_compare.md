# Compare  /compare
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 2/5 — currently speaks to **developer**

The conceptual spine is researcher-perfect: for-and-against, a disputed element with 4 supports vs 6 challenges left unresolved, receipts, archived URLs, 'We organise; you decide.' But the proof is delivered as verbatim JSON under a 'POST /agent/full' header with latency in milliseconds, the primary CTA is 'Read the API docs' to /developers, and there is no link to the human review console (/research). A journalist evaluating this page sees an engineer's API bake-off, not their own workflow. The substance is for them; the packaging is for the person integrating the API.

**Verifier check:** Largely correct, with one nuance. The reviewer's score of 2 / "speaks to developer" is well grounded: the proof surface is verbatim JSON in a dark terminal band under a `POST /agent/full — Response` header (response-tabs.tsx:66) with `200 OK · 40.4s` chips (json-panel.tsx:43), and the primary CTA is `Read the API docs` → /developers (page.tsx:163-169). Two caveats keep this honest: (1) the page does give the researcher ONE human path — the secondary CTA `See the live report` → /r/2484b9da-… (page.tsx:170-176, CHECK_ID is a real UUID at demo-data.ts:30, not a placeholder), so "no path" is slightly overstated — it is demoted, not absent; (2) /compare is intrinsically a competitive page against grounding APIs (Web IQ, Google check-grounding, Perplexity, Parallel) — developer products a journalist would never benchmark — so a dev lean is partly structural. The fix (promote /r/, add a human-readable rendering of the disputed element, link /research which does exist at app/research/page.tsx) is the right move within the fixed-buyer lens. The conceptual spine (for-and-against, a disputed element with 4 supports vs 6 challenges left unresolved, receipts, archived URLs, "We organise; you decide.") is genuinely researcher-perfect.

**Overall:** A sharp, honest comparison page whose ARGUMENT is exactly right for the researcher ("they return a score, Tru8 returns the landscape with the conflicts left visible") but whose DELIVERY is coded for developers: the centrepiece proof is raw JSON in a dark terminal band, the primary CTA is "Read the API docs", and the differentiator is buried in API fields rather than shown in a human-readable record. The language lock holds well — no "verdict", element states render in neutral accent not traffic-light colour, manifest framing is honest — but a "show-your-working" journalist or policy analyst cannot read the proof as shipped, and the page never offers them the human path.

## Verified findings

### MAJOR

**[positioning] Page is API/developer-coded; the researcher has no path and no rendered proof**  _( confirmed )_
- **Evidence:** Primary CTA `<Link href="/developers"> Read the API docs` (page.tsx:163-169); dark band header `POST /agent/full — Response` (response-tabs.tsx:66) with `200 OK · 40.4s` chip (json-panel.tsx:42-43); eyebrows 'Module — Raw Responses' (page.tsx:98). Only researcher destination is secondary 'See the live report' → /r/2484b9da-… (page.tsx:170-176). No link to /research (which exists at app/research/page.tsx).
- **Why it matters (buyer):** The fixed buyer is a 'show-your-working' journalist/analyst, not an API integrator. The whole proof surface (verbatim JSON, ms latency, endpoint names) reads as a developer bake-off; the one human-readable artefact they could actually defend their sourcing with (the rendered /r/ report) is demoted to a secondary button.
- **Fix:** Promote 'See the live report' to primary, keep 'Read the API docs' secondary, and add an explicit human path to /research. Point the researcher at the rendered evidence record, not the endpoint.
- **Verifier:** Confirmed in current source. Minor honesty correction folded into buyer_fit_check: a researcher path (the /r/ live report) does exist but is demoted; and /compare is structurally a dev-API benchmark page, so some dev lean is inherent. Major severity stands given the fixed-buyer lens.

**[content] The differentiator is buried in raw JSON the researcher can't parse**  _( confirmed )_
- **Evidence:** Tru8 advantage rendered only as a scrolling JSON blob in `max-h-[560px] overflow-y-auto` (json-panel.tsx:47). Payoff fields are real in demo-data.ts — `"state": "disputed"` (line 226), `"caveat": "mixed: 4 support / 6 disagree (weighted 8 vs 15)"` (line 204) — but embedded in a 700+ line payload (`_manifest` at line 711). Highlighter only tints matching keys in accent (json-panel.tsx:9-22).
- **Why it matters (buyer):** For a researcher the killer proof is exactly the disputed element — 4 sources support, 6 challenge, conflict left visible. As shipped that proof is legible only to someone who reads JSON. The page argues 'the structure is the product' but never shows the structure in human form on the page itself.
- **Fix:** Add a short human-readable rendering of the Tru8 result alongside the JSON (the three elements, the disputed one with its 4-vs-6 split, one receipt, one archived URL) in Stitch tokens. Keep the raw JSON for developers.
- **Verifier:** Confirmed. The single strongest researcher proof (the disputed element) is legible only to a JSON reader. Fix stays inside the locks.

### MINOR

**[aesthetic] Full dark band + bespoke 'Module —' eyebrows diverge from the light document-grammar system**  _( confirmed )_
- **Evidence:** `<section className="py-20 md:py-28 bg-zinc-950 text-zinc-100">` (page.tsx:94); panels `border border-zinc-800 bg-black` (json-panel.tsx:37). Eyebrows use 'Module — Comparison/Capabilities/Raw Responses/The Obvious Question' (page.tsx:72,87,98,117) rather than numbered SheetHeaders, and the page omits the homepage left mono spine / 2px orange top rule / inset frame.
- **Why it matters (buyer):** Cross-page consistency is part of the Stripe/Linear/Vercel restraint bar; a researcher landing here from the homepage meets a different visual grammar (dark terminal + 'Module —' labels) that reads as a separate template. Dark code panels are a defensible convention, but the full-section dark wrap and the divergent chrome should be a deliberate, confirmed choice.
- **Fix:** Adopt the homepage chrome (numbered SheetHeaders, top rule, spine) and let only the code panels go dark, OR confirm the dark 'raw responses' band is sanctioned art direction. At minimum align the eyebrow grammar.
- **Verifier:** Confirmed in code. Genuinely needs a human eye for the final art-direction call (a dark terminal panel is a defensible convention), but the divergence from the rest of the site is real. Minor is right.

**[copy] UK spelling 'organise' on a US marketing page, inconsistent with the homepage**  _( confirmed )_
- **Evidence:** 'We organise; you decide.' (page.tsx:142) and the same UK spelling in the FAQPage JSON-LD answer (page.tsx:43). Homepage ships US 'We organize; you decide.' (stitch-hero.tsx:55; also stitch-faq.tsx:8,20).
- **Why it matters (buyer):** The signature tagline is the one line a researcher will remember and quote; having it spelled two different ways across marketing pages undercuts the composed, deliberate impression. The lock is US on marketing, UK on product/legal.
- **Fix:** Change to 'We organize; you decide.' in both the visible copy (page.tsx:142) and the JSON-LD answer (page.tsx:43) to match the homepage. Lock = US on marketing.
- **Verifier:** Confirmed exactly — verified the homepage uses US spelling, so the inconsistency is real. Good catch on the signature line.

**[accessibility] Low-contrast text traps on white and on black**  _( confirmed )_
- **Evidence:** Back link `text-zinc-400 hover:text-zinc-900` on white (page.tsx:64) ≈2.6:1; Web IQ disclaimer `text-zinc-600` on black (response-tabs.tsx:157); panel footers `text-zinc-500 text-[10px]` on black (json-panel.tsx:55). All fail WCAG AA for small text.
- **Why it matters (buyer):** A research audience skews toward careful readers and accessibility-conscious institutions; sub-AA body/label contrast is both an exclusion and an off-brand sloppiness against the restraint bar.
- **Fix:** Lift the back link to zinc-500/600 (it already darkens to zinc-900 on hover), and raise dark-panel disclaimer/footer text to at least zinc-400 on black to clear AA at these sizes.
- **Verifier:** Confirmed at the cited lines. Real AA failures.

**[accessibility] Tab pattern is half-wired — missing tabpanel roles, aria-controls and arrow-key nav**  _( confirmed )_
- **Evidence:** Buttons carry `role="tab"` + `aria-selected` inside `role="tablist"` (response-tabs.tsx:46-61), but the rendered JsonPanel/Web IQ wrappers have no `role="tabpanel"`, no `id`, no `aria-labelledby`/`aria-controls`, and there is no Arrow-key handling.
- **Why it matters (buyer):** Screen-reader and keyboard users comparing the five API responses get an incomplete relationship between tab and content; the very audience that values rigour is the one most likely to use assistive tech.
- **Fix:** Add `role="tabpanel"` + `id` + `aria-labelledby` to each panel and `aria-controls` to each button, and implement arrow-key navigation — or drop the explicit tab roles for plain buttons + a labelled region.
- **Verifier:** Confirmed. The ARIA tabs contract is genuinely incomplete in current source.

### NIT

**[positioning] 'confidence' terminology surfaces in the shipped JSON (one Tru8 field, one competitor field)**  _( adjusted )_
- **Evidence:** Tru8 payload shows `"queryConfidence": null` (demo-data.ts:72); Parallel capture shows `"confidence": "medium"` (demo-data.ts:833). Both render verbatim.
- **Why it matters (buyer):** The language lock forbids confidence scores in user-facing copy; the Parallel field is fair verbatim competitor output (and usefully contrasts Tru8's no-score stance), but `queryConfidence` is a Tru8 field name leaking the forbidden frame into the product's own showcased payload.
- **Fix:** Leave the competitor's `confidence` as-is (verbatim is the point and usefully contrasts Tru8's no-score stance). For Tru8's own payload, flag `queryConfidence` to the founder as a field-name lock check — do not invent a rename on this page.
- **Verifier:** Real and correctly grounded, but severity lowered minor→nit: the value is null (no confidence number ever displays), it is an API field name not user-facing copy, and renaming is a backend API decision out of scope for a page review. The reviewer already framed it as a note-not-change, which is the right posture.

**[aesthetic] Capability table forces horizontal scroll on mobile**  _( confirmed )_
- **Evidence:** `<table className="w-full text-left border-collapse min-w-[760px]">` inside `overflow-x-auto` (comparison-table.tsx:142-143).
- **Why it matters (buyer):** The capability matrix is the fastest at-a-glance proof; on a phone it requires sideways scrolling, so the headline contrast (Tru8 column vs the four 'no's) may not be visible in one view.
- **Fix:** Confirm the mobile experience visually; consider a stacked/transposed mobile layout so the Tru8-vs-rest contrast reads without sideways scroll.
- **Verifier:** Confirmed in code; nit + needs-human-eye is the right call. The 5-column matrix on a phone will need horizontal scroll.

## Additional issues caught in verification

**[MINOR · accessibility] Capability-table 'No' / 'Unverified' marks are near-invisible (zinc-300/zinc-400 icons), defeating the table's whole purpose**
- **Evidence:** The 'No' Minus icon is `text-zinc-300` (#d4d4d8 ≈1.4:1 on white) and the 'Unverified' HelpCircle is `text-zinc-400` (≈2.6:1) — comparison-table.tsx:125-130. WCAG 1.4.11 requires 3:1 for non-text/graphical UI components; both fail. The table's headline argument is Tru8's accent ticks vs four columns of 'no', yet those 'no' marks are the faintest thing on the page. The reviewer's a11y findings covered text and tabs but missed icon (non-text) contrast.
- **Fix:** Raise the No/Unverified icons to at least zinc-500 on white so the Tru8-vs-rest contrast actually reads and the graphical marks clear the 3:1 non-text bar. Keep the accent reserved for the Tru8 'yes'.

**[MINOR · aesthetic] Bold-word emphasis is used on every section heading, breaking the 'reserved for hero h1' document-grammar**
- **Evidence:** `<span className="font-bold">` appears in the h1 (page.tsx:75, permitted) AND the dark-band h2 (101), the Obvious-Question h2 (122) and the closing h3 (153). The design language reserves bold-word emphasis for hero h1 + preview panels, using SIZE as the hierarchy lever; here it is the default treatment for every heading. The dark-band h2 also uses `font-extralight` (page.tsx:100) — another weight deviation from the font-normal grammar.
- **Fix:** Drop bold-word emphasis to the hero h1 only; let size carry hierarchy on the section h2/h3. Normalise the dark-band h2 to font-normal to match the system.

## Strengths to keep
- Language lock is well held: no 'verdict' anywhere in shipped copy; element states ('disputed'/'supported') render in neutral accent via the JSON highlighter (json-panel.tsx HIGHLIGHT_KEYS) rather than green/red traffic-light colour; manifest framed honestly as 'Signed manifest + public verify URL', not 'independently verifiable'.
- Genuinely honest, competitor-respectful tone: 'These are strong APIs doing exactly what they're built for' and 'Parallel's deeper processors run for minutes and return genuinely deeper research' (page.tsx:131-138) pre-empt the obvious objection instead of strawmanning rivals.
- Transparent methodology builds exactly the trust the researcher buyer demands: same claim, same day, responses verbatim; disclosed abridgement policy; Google check-grounding fed Tru8's own 17 retrieved sources as facts; Parallel processor 'core' chosen deliberately (demo-data.ts header + panel footers).
- Web IQ handled with integrity — 'No response available', waitlist-gated, marked Unverified (HelpCircle) in the table rather than faked (response-tabs.tsx:142-163).
- The disputed-element JSON is the single best piece of researcher proof on the whole site: a real claim where 4 sources support and 6 challenge, with the conflict and an 'evolving consensus' uncertainty note left visible — the 'no verdict' value made concrete.
- Strong SEO/IA hygiene: canonical, OG + Twitter cards, /api/og/compare image, and a FAQPage JSON-LD whose answer mirrors the visible 'Obvious Question' prose (page.tsx:34-47) rather than injecting unseen content.
- Headline is crisp and on-voice: 'Grounding APIs check sentences. Tru8 maps evidence.' and the closing 'Different layer, not a faster horse.'
