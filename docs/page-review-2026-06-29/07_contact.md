# Contact  /contact
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 3/5 — currently speaks to **mixed**

A contact page is legitimately audience-neutral, so the lack of researcher-specific framing is not itself a defect. But it does nothing to reassure the show-your-working researcher that real human support stands behind the platform (no named team, no depth on data-handling a journalist/policy researcher might care about beyond a one-line GDPR mention). It also does not drift to developers/agents in the body. Net: safe but bland, a missed trust signal for a sourcing-conscious buyer.

**Verifier check:** Confirmed. /contact uses the shared LegalPageLayout and stays audience-neutral: the body (page.tsx:15-82) carries one contact path (hello@trueight.com), honest response-time SLAs (24-48h general, 30 days GDPR, 7-day escalation) and no developer/agent drift in the body — even though the global Navigation exposes API affordances. The reviewer's score of 3 ("safe but bland, a missed trust signal") is fair: nothing reassures the show-your-working researcher that real human support stands behind sourcing decisions (no named team, no data-handling depth beyond a one-line GDPR mention). It is language-lock clean (zero verdict/confidence/credibility framing). Net: legitimately neutral, not a defect by itself, but a missed trust opportunity.

**Overall:** A clean, functional contact/support page that is language-lock compliant and free of verdict framing, but it renders in the legacy "legal" layout (rounded cards, font-bold prose headings, no SheetHeaders / mono document-grammar) rather than the shipped Stitch system, so it reads as a different product surface than the homepage. It is audience-neutral toward the researcher buyer, and it carries one real content bug (a hardcoded "questions about this policy?" footer that is nonsensical and self-linking on Contact) plus a heading-order skip.

## Verified findings

### MAJOR

**[aesthetic] Page is off the shipped Stitch document-grammar system**  _( confirmed )_
- **Evidence:** Via LegalPageLayout: content container `bg-white border border-zinc-200 rounded-lg p-8 md:p-12` (line 46); h1 `text-3xl md:text-4xl font-bold` (line 35); prose-legal h2 `@apply text-3xl font-bold` (globals.css:363-365). No SheetHeader, no two-digit mono sheet numbers, no mono eyebrow, no 2px orange top rule, no mono left spine. rounded-lg + font-bold headings contradict the homepage's square-corner, font-normal, size-is-hierarchy grammar.
- **Why it matters (buyer):** Inconsistent shell makes the support surface feel bolted-on; reduces the composed, Stripe/Linear-grade impression the homepage sets, weakening trust at the exact moment a buyer is reaching out.
- **Fix:** Migrate legal/support pages onto the document-grammar shell: drop `rounded-lg`, use font-normal headings with size as the hierarchy lever, add a numbered SheetHeader + mono eyebrow. Treat as a system-wide legal-layout migration, not a one-off. needs human eye for the visual result.
- **Verifier:** Every cited class confirmed in current source (legal-page-layout.tsx:35,46; globals.css:363-365). The legacy shell genuinely diverges from the shipped Stitch system. Major is defensible because it affects every legal/support surface and undercuts the composed impression at a trust moment. Confirmed.

### MINOR

**[copy] Layout footer references a non-existent "policy" and self-links on the Contact page**  _( adjusted )_
- **Evidence:** legal-page-layout.tsx:54-62 unconditionally renders <p>"Have questions about this policy?"</p> with a "Contact Us" <Link href="/contact">. On /contact this loops the page to itself and asks about a "policy" that is not present; the same hardcoded "this policy" wording is also wrong on About/Refund surfaces that share the layout.
- **Why it matters (buyer):** A researcher evaluating whether to trust their sourcing to this tool notices broken self-referential dead-ends; it signals an unfinished, template-driven site rather than a maintained product.
- **Fix:** Make the footer CTA conditional in LegalPageLayout (hide when the current path is /contact, or gate via a prop), and soften the copy to "Questions about this page?" so it is correct across Contact/About/Refund. Stays inside locks (no forbidden language).
- **Verifier:** Grounded exactly as quoted (lines 54-62, unconditional render, href="/contact"). Real defect and the systemic "this policy" wrongness across legal pages is a fair point. Downgraded blocker-of-trust framing: on a single footer CTA the per-page buyer impact is minor, not major — it is polish, not a broken core path. Fix is sound and lock-safe.

**[accessibility] Heading order skips from h1 to h3 before the first h2**  _( confirmed )_
- **Evidence:** Layout renders h1 "Contact Us" (legal-page-layout.tsx:35). First in-content heading is `<h3 ...>Get in Touch</h3>` (page.tsx:27), which precedes the first `<h2>Business Information</h2>` (page.tsx:54). Outline order is h1 -> h3 -> h2.
- **Why it matters (buyer):** Screen-reader and outline navigation break for any researcher using assistive tech; also a minor SEO/structure smell.
- **Fix:** Promote "Get in Touch" to an h2 (it is in a not-prose block so it carries its own classes, so restyle as needed), keeping subsequent sections at h2 for a clean outline.
- **Verifier:** Confirmed in current source: page.tsx:27 is h3, page.tsx:54 is the first h2, h1 lives in the layout. Real heading-order skip. Minor is correct.

**[accessibility] Decorative icons lack aria-hidden**  _( confirmed )_
- **Evidence:** Mail icons at page.tsx:24 and page.tsx:35, and MapPin at page.tsx:57 (`<MapPin className="text-accent flex-shrink-0" size={18} />`) render with no aria-hidden; the visible email text and "Location:" label already convey meaning.
- **Why it matters (buyer):** Minor noise for screen-reader users; cheap to fix.
- **Fix:** Add `aria-hidden="true"` to the decorative Mail/MapPin icons.
- **Verifier:** All three icon usages confirmed at the cited lines with no aria-hidden. Correct and cheap. Minor is right.

**[content] No structured contact data (ContactPoint / Organization JSON-LD)**  _( confirmed )_
- **Evidence:** page.tsx exports only `metadata` (title/description/canonical, lines 4-8); no JSON-LD script. The email (hello@trueight.com), support hours and London location are good ContactPoint candidates.
- **Why it matters (buyer):** Light-touch SEO/IA gap: the email, support hours and London location are good candidates for ContactPoint structured data, aiding discoverability for a new zero-authority domain.
- **Fix:** Add an Organization/ContactPoint JSON-LD block (email hello@trueight.com, areaServed, contactType: customer support) consistent with the site's existing schema approach. Note for the founder; light-touch, not urgent.
- **Verifier:** Confirmed: page.tsx contains only the metadata export and no structured-data block. Reasonable light-touch IA/SEO gap for a zero-authority domain. Minor is appropriate.

### NIT

**[aesthetic] Lone orange icon spends accent budget outside the document grammar**  _( confirmed )_
- **Evidence:** page.tsx:57 `<MapPin className="text-accent flex-shrink-0" size={18} />` is the only orange element on the page, used as an icon tint next to "Location: London, UK" rather than as a hairline rule/registration mark. (prose-legal links are also orange via globals.css:386, but there are no inline links in this page's body.)
- **Why it matters (buyer):** Per the self-policed accent discipline, orange is a mark/rule not an arbitrary icon tint; a stray accent looks decorative rather than systemic.
- **Fix:** Render MapPin in zinc (zinc-400/500) like the surrounding text, or reserve orange for a rule/registration glyph consistent with the Stitch accent discipline.
- **Verifier:** Confirmed: line 57 is the only orange mark in the rendered body. Per the accent-as-stroke/mark discipline this is a fair nit. Confirmed.

**[copy] Office hours hardcode "GMT" year-round**  _( confirmed )_
- **Evidence:** page.tsx:67 "Our support team operates Monday-Friday, 9:00 AM - 5:00 PM GMT (UK time)." The UK observes BST (UTC+1) ~half the year, so "GMT" is literally wrong in summer.
- **Why it matters (buyer):** A precision-minded researcher/journalist may notice the timezone slip; small but it's a credibility detail on a page about being reachable.
- **Fix:** Use "UK time (GMT/BST)" or "London time" to stay accurate across the year.
- **Verifier:** Confirmed verbatim at page.tsx:67. Legitimate precision nit for a detail-minded researcher buyer. Confirmed.

## Additional issues caught in verification

**[MINOR · accessibility] Back-to-Home link uses zinc-400 — low-contrast text trap**
- **Evidence:** legal-page-layout.tsx:27 renders the "Back to Home" link as `text-zinc-400 hover:text-zinc-900` with a 20px ArrowLeft icon and `text-sm` label (lines 25-31). zinc-400 (#a1a1aa) on the white page background (`bg-white`, line 22) is ~2.6:1 contrast, below the WCAG AA 4.5:1 threshold for this small text. This is exactly the zinc-400 low-contrast trap the design brief warns about, and it appears on every legal/support page via the shared layout.
- **Fix:** Raise the resting colour to at least zinc-500 (or zinc-600) so the back affordance meets AA; keep the hover:text-zinc-900. Shared-layout fix, benefits all legal pages.

## Strengths to keep
- Language-lock clean: zero verdict/confidence/credibility language; nothing on the page contradicts "We organize; you decide."
- No positioning drift in the body — it stays audience-neutral and does not lean developer/agent despite the global nav exposing Get API Key.
- Single, unambiguous contact path (hello@trueight.com) with explicit, honest response-time expectations (24-48h general, 30 days GDPR) and a concrete escalation ladder — reassuring substance for a buyer who needs accountability.
- Consistent zinc neutral palette and 1px borders; no drop-shadows or gradients, broadly within the shipped token family even via the legacy layout.
- Skip link, focus-visible outline and back-to-home affordance inherited from the shared layout.
