# Homepage  /
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 3/5 — currently speaks to **mixed**

Content lenses (Record differentiators, Compare teaser, FAQ) are precisely tuned to the show-your-working researcher — for-and-against, receipts, gaps named, no verdict. But the conversion frame is developer-first: the single black primary CTA in the hero and in the nav is 'Get API Key' (→/developers, fires get_api_key_click), the human/Research App path is a quiet underlined link 'Need the human review console? Open the Research App', and sheet 03 is a full-bleed dark JSON+curl developer wall. A policy researcher landing here is told to fetch an API key before being told this is for them.

**Verifier check:** Largely accurate, with one load-bearing correction. The reviewer's "mixed / dev-led frame, researcher-grade substance" read is confirmed in current source: both filled CTAs are "Get API Key" → /developers (stitch-hero.tsx:59-70 and navigation.tsx:100-106), the researcher path is a quiet underlined link "Open the Research App" → /research (stitch-hero.tsx:81-89), and sheet 03 is a full-bleed dark API/JSON wall (stitch-developer-showcase.tsx:84). Meanwhile the Record ledger, Compare teaser and FAQ are precisely the show-your-working substance the researcher needs. IMPORTANT CONTEXT the reviewer omits: per project memory (release plan 2026-06-23, fc03ced) the homepage `/` is DELIBERATELY developer-led and the researcher-led variant ships at `/research` ("`/`+nav untouched"). So the dev-first frame on `/` is an intentional, founder-set config — not an accidental drift. The rubric's fixed lens still makes flagging the drift legitimate, but any fix that wholesale flips `/`'s primary CTA must be raised as a founder decision against the two-variant strategy, not asserted as a defect to silently fix. Net buyer-fit on THIS page for the researcher: genuinely mixed (score ~3 is fair), with the caveat that the researcher is intended to be served at /research.

**Overall:** The homepage is a beautifully executed document-grammar system with genuinely researcher-grade SUBSTANCE — the Differentiators ledger (echo detection, measured source diversity, per-source provenance, four states incl. contextual, exclusion receipts) and the FAQ are exactly the "show-your-working" proof the journalist/analyst buyer needs, and language-lock compliance is strong (no verdict, "We organize; you decide", object is always the record). But the FRAME is developer-led: the primary hero and nav CTA is "Get API Key" → /developers, the researcher path is demoted to an underlined text link, and a full dark API/JSON band sits at sheet 03 of 6. The page proves itself to the researcher in its content while its top-of-funnel calls to action speak to an agent builder.

## Verified findings

### MAJOR

**[positioning] Both primary CTAs target developers; the researcher buyer is demoted to a text link**  _( adjusted )_
- **Evidence:** Confirmed in current source: stitch-hero.tsx:59-70 filled black primary button 'Get API Key' → /developers (capture('get_api_key_click', { surface: 'hero' })); the researcher path is a muted sentence at lines 81-89 'Need the human review console? Open the Research App' (underlined link → /research). navigation.tsx:100-106 the only filled nav CTA is also 'Get API Key' → /developers; 'Research App' (93-99) is a bordered/ghost link. Note: the hero's SECONDARY button is actually 'See a Sample' → #preview (71-77), not a researcher CTA as the reviewer implies.
- **Why it matters (buyer):** The fixed buyer is a journalist/analyst/policy researcher for whom 'no verdict' is the feature. Leading every conversion path with 'Get API Key' tells them this product is not built for their hands-on console workflow, and asks them to think like an integrator before they've been told the page is for them.
- **Fix:** The observation is correct and worth raising, but the fix must respect the SHIPPED two-variant strategy (per release-plan memory: `/` is intentionally dev-led, the researcher-led variant is `/research`). Do NOT silently flip `/`'s primary CTA. Either (a) raise the homepage framing as an explicit founder decision, or (b) within the dev-led frame, elevate the researcher path from an underlined sentence to at least a ghost button so the journalist/analyst sees a clear console entry without abandoning the API audience. Confirm with founder before reordering.
- **Verifier:** Real and grounded — both filled CTAs are dev-targeted and the researcher path is demoted. Adjusted (not confirmed) because the recommended wholesale CTA swap conflicts with the deliberate `/` dev-led vs `/research` researcher-led config; the fix should respect that strategy rather than override it. Also corrected the reviewer's mis-statement that the hero's secondary slot is the researcher path — it is 'See a Sample'.

**[content] Console preview labels the views by PROFESSION, violating the action-names lock**  _( confirmed )_
- **Evidence:** stitch-product-preview.tsx PANELS: label 'Librarian' (30), 'Cartographer' (46), 'Seeker' (62), 'Chronologist' (78). Rendered as the primary mono caption-rail label at line 186 ({panel.label}) and in every screenshot header at line 219 ({panel.label} view — Dashboard).
- **Why it matters (buyer):** The positioning lock and the team's own durable rule (feedback_action_names_not_professions) require user-facing copy to name the six views by ACTION — Evidence · Sources · Timeline · Gaps · Map · Video — with profession names internal/subtitle only. 'Librarian view' / 'Cartographer view' is opaque jargon to a first-time researcher and reads as cute-internal, undercutting the credibility the rest of the page earns.
- **Fix:** Relabel panels by action per the durable rule (feedback_action_names_not_professions): Librarian→'Sources', Cartographer→'Map', Seeker→'Gaps', Chronologist→'Timeline'. If the profession name is wanted for flavour, demote it to a small subtitle, never the caption-rail label or screenshot header. Stays inside Stitch tokens (mono label unchanged).
- **Verifier:** Confirmed exactly as quoted. Clear, prominent violation of the action-names lock on a high-read homepage section; severity major is defensible because it directly contradicts a durable team rule and reads as opaque internal jargon to a first-time researcher.

**[copy] Hero narrows the product to 'AI-generated content', excluding the researcher's everyday input**  _( confirmed )_
- **Evidence:** stitch-hero.tsx:50-52 'Tru8 decomposes AI-generated content into checkable claims and returns a structured evidence record'. Contradicted two sheets later: stitch-process.tsx:13 'Send AI-generated text, a URL, or a single claim' and stitch-faq.tsx:20 'You submit a URL or a claim'.
- **Why it matters (buyer):** A policy researcher or journalist mostly checks human-published claims, URLs and documents — not AI output. The hero's 'AI-generated content … before it ships' frames the tool for an AI-pipeline operator and contradicts the broader, correct scope stated two sections later. The narrowing pushes the fixed buyer away at the most-read line on the page.
- **Fix:** Broaden the hero sub to match the product and FAQ, e.g. lead with the claim/URL the researcher actually has: 'Tru8 decomposes any factual claim, URL or AI-generated passage into checkable elements and returns a structured evidence record…'. Currency-neutral, no forbidden language, keeps the 'before it ships' tension if desired.
- **Verifier:** Confirmed and grounded; the internal contradiction with Process and FAQ is real. The narrowing happens at the most-read line on the page and tilts the hero toward an AI-pipeline operator over the fixed researcher buyer. Major is justified.

### MINOR

**[ia] A full dark developer API band occupies prime mid-page real estate (sheet 03 of 6)**  _( confirmed )_
- **Evidence:** stitch-developer-showcase.tsx:84 'bg-zinc-950 text-zinc-100'; SheetHeader number '03' label 'API' refText 'POST /agent/*' (86); full SAMPLE_RESPONSE JSON, SAMPLE_CURL block and 'Read the docs' CTA. It is the only inverted section, placed before the Console preview (sheet 05) and FAQ.
- **Why it matters (buyer):** Section order leads the researcher Record→Process→[dark API JSON wall]→Console. The single most visually dominant block is raw developer integration content; the human console preview that would actually convert this buyer sits below it.
- **Fix:** For the homepage, either interleave the human Console preview before the dark API band, or visually subordinate the API section (not full-bleed-dark) so it reads as 'also available via API'. Keep the full dark treatment for /developers. Note: because `/` is intentionally dev-led, raise this as a framing choice with the founder rather than a unilateral reorder.
- **Verifier:** Confirmed and grounded. Minor is the right severity. Caveat noted: the dark API centrepiece is partly by design on the dev-led homepage, so the fix is a judgement call for the founder.

**[copy] UK spelling 'judgement' on a marketing page (lock = US on marketing)**  _( confirmed )_
- **Evidence:** stitch-faq.tsx:24 'leaves the judgement to you' and :36 'The judgement stays with you.' The rest of the marketing surface uses US spelling ('organize', 'organizes' — e.g. stitch-faq.tsx:20, stitch-hero.tsx:55).
- **Why it matters (buyer):** Mixed locale on the same page reads as inattentive to a professional researcher who scrutinises sourcing and detail. The lock specifies US spelling on marketing/dev pages.
- **Fix:** Change both to 'judgment'. Sweep the marketing/ components for other UK leaks; product UI and legal pages stay UK per the locale lock.
- **Verifier:** Confirmed exactly. Minor is correct (reviewer's JSON tags it minor though the prose says nit — minor is right).

**[content] Console section promises six views but shows four**  _( confirmed )_
- **Evidence:** stitch-product-preview.tsx:113 SheetHeader refText '6 VIEWS' and :120 copy 'six ways to read the evidence', but PANELS (27-92) contains only four entries (Librarian, Cartographer, Seeker, Chronologist). Correspondent/Evidence and Projectionist/Video are absent.
- **Why it matters (buyer):** A detail-oriented buyer notices the count mismatch; it reads as either an unfinished section or an over-claim. Either erodes the precision the brand sells.
- **Fix:** Either add the two missing panels (Evidence/Correspondent and Video/Projectionist) or change copy to 'four of the six ways' and drop the hard '6 VIEWS' ref so the claim matches what is shown.
- **Verifier:** Confirmed and grounded. The count mismatch is real and reads as an over-claim or unfinished section to a detail-oriented buyer. Minor.

**[accessibility] Several mono labels use zinc-300/zinc-400 below AA contrast on white**  _( confirmed )_
- **Evidence:** stitch-product-preview.tsx:221 route hint 'text-zinc-300'; stitch-hero.tsx:101 'chk_8f3a · sample' text-zinc-400; stitch-record.tsx:103 ('claimMap · _meta · _manifest') and :167 (MANIFEST_REF 'landscapeHash · hmac-sha256 · /verify/{id}') both text-zinc-400 on white/zinc-50.
- **Why it matters (buyer):** Low-vision researchers (and anyone on a bright screen) cannot read the datasheet refs and route hints. They are decorative-leaning, but some (manifest ref, sample id) carry real meaning.
- **Fix:** Bump load-bearing mono refs (manifest ref, sample id) to at least zinc-500 (≈4.8:1, passes AA). Purely decorative hints may stay lighter but avoid zinc-300 for any text conveying meaning. Needs a human eye / contrast checker to confirm exact ratios.
- **Verifier:** Confirmed; the cited classes and lines all match current source. Some are decorative, some (manifest ref, route) carry meaning, so a real accessibility concern. Minor + needs-human-eye is appropriate.

**[ia] JSON-LD types the product as DeveloperApplication, reinforcing the dev frame for search/AI engines**  _( confirmed )_
- **Evidence:** page.tsx:46-53 SoftwareApplication node: applicationCategory 'DeveloperApplication', url '${baseUrl}/developers', description 'Evidence research API and MCP server for AI agents. Decomposes factual AI output…'.
- **Why it matters (buyer):** For AI answer engines and rich results, the homepage's structured data positions Tru8 as a developer tool, not research infrastructure for journalists/analysts — pushing the wrong audience signal in exactly the surfaces (AI Overviews/Perplexity) where the researcher buyer discovers tools.
- **Fix:** Broaden the schema: keep a SoftwareApplication node but set applicationCategory to a research/utility category and point its url at / (or add a second node for the Research App). Lead the description with the researcher use-case, mention the API second. Stays inside the honest-framing lock.
- **Verifier:** Confirmed and grounded. For AI answer engines (where the researcher discovers tools) the structured data signals a developer tool. Minor. Same caveat as elsewhere: partly aligned with the deliberate dev-led `/`, so balance against the /research node.

### NIT

**[aesthetic] FAQ breaks the numbered document grammar**  _( confirmed )_
- **Evidence:** Every section uses SheetHeader with a number (Record 01, Process 02, API 03, Compare 04, Console 05; Problem 00) except stitch-faq.tsx:69-71, which uses a bare eyebrow 'Common Questions' with no sheet number, orange registration glyph or datasheet ref.
- **Why it matters (buyer):** The document-grammar consistency is a core trust signal of the design; the final section silently dropping it is a small seam a meticulous buyer registers.
- **Fix:** Wrap the FAQ in a SheetHeader (e.g. number '06', label 'Questions', refText 'FAQ') to complete the document series and keep the document-grammar trust signal intact.
- **Verifier:** Confirmed; FAQ does not import or use SheetHeader. Nit is correct severity.

**[copy] 'before it ships' leans on a content-ops/deploy metaphor**  _( confirmed )_
- **Evidence:** stitch-hero.tsx:42 emphasised 'before it ships.'; also layout.tsx:41 (openGraph) and :54 (twitter) descriptions 'before it ships'.
- **Why it matters (buyer):** 'Ships' is software/content-pipeline language; a journalist or policy researcher 'publishes', a policy analyst 'briefs'. It subtly tilts the hero toward an AI-builder reader, compounding the dev drift.
- **Fix:** Consider a buyer-neutral verb for the researcher — 'before you publish.' or 'before you cite it.' — preserving the pre-publication tension while speaking the researcher's vocabulary. It is the signature line, so confirm with the founder before changing.
- **Verifier:** Confirmed and grounded; phrase appears in hero and both social cards. Genuinely a nit and subjective, but it does compound the dev-leaning frame. Reviewer correctly flags founder sign-off.

## Additional issues caught in verification

**[MINOR · copy] Page meta description and social cards narrow the product to 'AI output', the same defect as the hero but on the SEO/share surface**
- **Evidence:** page.tsx:18 description 'Research the evidence behind factual AI output before it ships. Tru8 turns AI content into checkable claims…'; layout.tsx:41 and :54 openGraph/twitter descriptions 'Research the evidence behind factual AI output before it ships.' This is the snippet the researcher sees in Google/AI Overviews and link previews — and it omits the URL/claim input that Process (stitch-process.tsx:13) and FAQ (stitch-faq.tsx:20) confirm.
- **Fix:** Broaden the meta + OG/twitter descriptions to lead with 'any factual claim, URL or AI passage' so the search/share snippet matches the actual product scope and speaks to the researcher's real inputs. Keep it currency-neutral; no forbidden language.

**[MINOR · copy] Differentiators ledger says each source is 'scored', in mild tension with the no-credibility-score positioning the FAQ asserts**
- **Evidence:** stitch-record.tsx:33-34 row 03 'Per-source provenance — How each source was classified and scored, and from what — full text, snippet or API.' Meanwhile stitch-faq.tsx:36 states the AI 'never scores credibility' and the positioning lock forbids credibility/confidence scores and the 'classify, don't score' invariant. The unqualified word 'scored' next to 'classified' can read to a researcher as a per-source credibility score.
- **Fix:** Disambiguate to make clear it is topical relevance, not credibility — e.g. 'How each source was classified and how its relevance was judged, and from what — full text, snippet or API', or drop 'scored' in favour of 'assessed for relevance'. Keeps the honest-framing lock and removes the apparent contradiction with the FAQ.

**[NIT · content] Console preview exposes a raw bracketed internal route '/dashboard/check/[id]?view=librarian' to users**
- **Evidence:** stitch-product-preview.tsx:31/47/63/79 route values like '/dashboard/check/[id]?view=librarian' are rendered in the screenshot header at line 221-223 ({panel.route}, text-zinc-300, hidden sm:inline). The literal Next.js dynamic-segment placeholder '[id]' is shown verbatim, and the query param re-surfaces the profession name ('?view=librarian').
- **Fix:** Render a clean illustrative path (e.g. '/dashboard/check/…?view=sources') instead of the literal '[id]' bracket and the profession query value. A detail-oriented researcher reads the raw '[id]' as an unfinished/leaked internal detail, undercutting the precision the page sells. (Also rolls up the action-names fix from verified finding 2.)

## Strengths to keep
- Differentiators ledger (echo detection, source diversity measured, per-source provenance, four states incl. contextual, exclusion receipts) is exactly the show-your-working substance the researcher buyer needs — concrete, defensible, no scoring.
- Strong language-lock discipline: 'Not a verdict. A structured evidence record.', 'We organize; you decide.' throughout, object is always the evidence/record, manifest described as 'Signed record' / HMAC without overstating tamper-evidence.
- FAQ is genuinely researcher-tuned: 'show your working', receipts for inclusions and exclusions, explicit 'AI … never scores credibility and never issues a verdict', honest 'confirm the signed fields have not changed' rather than overclaiming.
- Compare teaser line 'Most tools hand you a conclusion. Tru8 hands you the evidence behind it.' is a sharp, on-message differentiator, and the single accent-rule emphasised final row is on-system.
- Document-grammar system (numbered SheetHeaders, mono eyebrows, 2px orange top rule, vertical left spine, single rotated-square accent glyph, 1px borders, no gradients/shadows) is cohesive and restrained at Stripe/Linear/Vercel level.
- Accessibility fundamentals are solid: skip link, focus trap + Esc + focus-return on the mobile sheet, ordered headings, detailed descriptive alt text on every screenshot, neutral-zinc 'supported' token in the hero record (no green verdict leak).
