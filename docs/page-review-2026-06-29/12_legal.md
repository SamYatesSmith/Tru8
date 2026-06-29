# Legal pages (privacy / terms / refund / cookie)
> Pre-launch page audit · researcher-buyer lens · 2026-06-29
> Ground truth = current code; every finding was adversarially verified against shipped source.
> This document supersedes nothing. It is the pre-launch review only.

**Buyer fit:** 3/5 — currently speaks to **mixed**

Legal pages are necessarily audience-neutral and serve the researcher fine — 'Research and journalism' is called out as a permitted use (terms-of-service:105) and the GDPR/erasure/portability rigour is exactly what a sourcing-conscious researcher wants to see. But the Terms tilt heavily developer/agent: an entire section 6 (API & Developer Usage) and 6.3 'Agent & Automated Usage' with x402/Skyfire/MCP language sits ahead of any researcher-facing framing. It does not mis-serve the researcher, but it mirrors the homepage's developer-first drift rather than the fixed researcher buyer.

**Verifier check:** Agree with "mixed / score 3" overall, with one correction. The legal pages are audience-neutral and serve the researcher well (Research and journalism is a named permitted use at terms-of-service:105; UK-GDPR rigour is exactly what a sourcing-conscious researcher wants). The dev/agent drift the reviewer flags is real and grounded: Terms section 6 (API & Developer Usage), 6.3 Agent & Automated Usage (terms:137-143), and the "Agent Commerce Gateway access (lookup, consensus, quick, full tiers)" line inside the Professional plan (terms:81) all tilt to a developer/agent audience and mirror the homepage drift. CORRECTION to the reviewer's reasoning: their headline strength claims company/contact identity is "consistent and complete across all four pages" — this is FALSE. Only privacy-policy and terms-of-service carry Trueight Ltd / 17090683 / ICO ZC110163 (verified: refund-policy and cookie-policy have zero matches for any of those tokens; they carry only the hello@trueight.com email). So the trust-signal completeness the reviewer leans on is two-of-four, not four-of-four.

**Overall:** The four legal pages are substantively solid trust signals: consistent company/contact identity (Trueight Ltd 17090683, ICO ZC110163, hello@trueight.com, London UK), thorough UK-GDPR coverage, and largely language-lock-compliant copy ("we organise; you decide", "descriptive labels, not quality judgments", no verdict/confidence language). For the researcher buyer who must defend sourcing, the correctness here is reassuring. The two real risks are a Terms section that advertises agent payment rails (x402/Skyfire) that are disabled in production, and a visual system that diverges from the shipped Stitch document-grammar (rounded cards, bold headings) — plus scattered US spellings on pages that should be UK throughout.

## Verified findings

### MAJOR

**[content] Terms advertise agent payment rails (x402, Skyfire) that are disabled in production**  _( confirmed )_
- **Evidence:** terms-of-service/page.tsx:141 — "The Agent Commerce Gateway (x402, Skyfire, prepaid credits) provides pay-per-use access for agents without a subscription". Verified backend/app/core/config.py:415 `SKYFIRE_ENABLED: bool = Field(False, ...)` and :428 `X402_ENABLED: bool = Field(False, ...)` — both default False; MEMORY records F-LEG-02/03 crypto+Skyfire rails False in prod.
- **Why it matters (buyer):** A legal page is where the researcher checks that what is promised is what is delivered. Advertising two payment methods that cannot actually be used is a factual misstatement in a contract document — the worst place to be inaccurate, and it undercuts the trust the whole legal bundle exists to build.
- **Fix:** Trim 6.3 to the rails that are live (prepaid credits) until x402/Skyfire are enabled, or qualify them as 'where enabled / subject to availability'. Confirm live rails with the founder before publishing.
- **Verifier:** Quote and config defaults confirmed exactly. A contract document asserting two payment methods that cannot be used is a real factual misstatement; major is justified. The page's BETA caveat (terms:24) only mildly mitigates — it does not license naming specific unavailable rails. Fix is sound and inside locks.

### MINOR

**[aesthetic] Legal layout diverges from the shipped Stitch document-grammar system**  _( adjusted )_
- **Evidence:** legal-page-layout.tsx:46 `bg-white border border-zinc-200 rounded-lg p-8 md:p-12` (rounded corners); :35 h1 `text-3xl md:text-4xl font-bold`; globals.css:362 `.prose-legal h2 { @apply text-3xl font-bold ... }`. No square corners, no font-normal/size-led hierarchy, no mono eyebrow, no 2px orange top rule.
- **Why it matters (buyer):** Consistency is itself a trust signal: a researcher who lands on the polished document-grammar marketing pages then hits a generic rounded-card legal page reads it as a lower-care surface. Legal pages legitimately carry lighter aesthetic weight, but they should still sit inside the same token system.
- **Fix:** Bring the legal shell onto Stitch tokens: drop `rounded-lg`, use font-normal headings sized by hierarchy, add a 2px orange top rule and a mono eyebrow/sheet label. Keep it minimal — no full spine needed.
- **Verifier:** Evidence confirmed exactly. Severity lowered major→minor: the reviewer themselves concedes legal pages legitimately carry lighter aesthetic weight, these are low-traffic audience-neutral surfaces, and nothing here violates a positioning lock — it is system-hygiene divergence, not a trust-breaking defect. Fix retained.

**[copy] US spellings leak onto UK legal pages**  _( confirmed )_
- **Evidence:** privacy-policy:49 "(anonymized)" vs privacy-policy:213 "anonymise" in the same file; terms-of-service:217 "anonymized data", :53 "unauthorized access"; cookie-policy:118 "Customize". Rubric locks legal pages to UK spelling.
- **Why it matters (buyer):** Mixed locale within a single document reads as inattentive — and a researcher scrutinising a privacy contract notices. The same word appears both ways ('anonymise' vs 'anonymized') in one file.
- **Fix:** Normalise to UK across all four: anonymise/anonymised, unauthorised, customise.
- **Verifier:** All five instances verified in current source (reviewer cited privacy:214 for 'anonymise'; actual line is 213 — trivial off-by-one, the word is present). The same word appearing both ways in privacy-policy is a genuine inattention signal on a contract page. Confirmed minor.

**[ia] Inconsistent metadata title suffixing across the four pages**  _( confirmed )_
- **Evidence:** privacy-policy:5 `title: 'Privacy Policy'` and terms-of-service:4 `title: 'Terms of Service'` (no suffix); refund-policy:4 `title: 'Refund Policy | Tru8'` and cookie-policy:5 `title: 'Cookie Policy | Tru8'`. Verified app/layout.tsx:29 `template: '%s | Tru8'`.
- **Why it matters (buyer):** Search snippets and browser tabs render inconsistently, and if a root layout title template also applies, the two suffixed pages risk doubling to 'Refund Policy | Tru8 | Tru8'.
- **Fix:** Rely on the layout title template and drop the inline '| Tru8' from refund-policy and cookie-policy so all four are uniform.
- **Verifier:** Confirmed and strengthened: the reviewer hedged 'if a root layout title template also applies' — it DOES (layout.tsx:29). So refund-policy and cookie-policy actually render the doubled title 'Refund Policy | Tru8 | Tru8' / 'Cookie Policy | Tru8 | Tru8'. This is a real rendered bug, not just inconsistency. Stays minor (title tag only).

**[accessibility] Low-contrast zinc-400 back link and muted footer text**  _( confirmed )_
- **Evidence:** legal-page-layout.tsx:27 back link `text-zinc-400 hover:text-zinc-900`; :39 'Last Updated' and :54 'Have questions about this policy?' use `text-zinc-500`. zinc-400 (#a1a1aa) on white ≈ 2.6:1, fails WCAG AA for normal text.
- **Why it matters (buyer):** zinc-400 on white is borderline for WCAG AA on small text; the primary 'Back to Home' affordance should be reliably legible.
- **Fix:** Raise the resting back-link colour to zinc-500/zinc-600 (it already darkens to zinc-900 on hover). zinc-500 on white ≈ 4.6:1, passes AA.
- **Verifier:** All three class references confirmed exactly. The primary 'Back to Home' affordance failing AA at rest is a real, fixable a11y issue. Confirmed minor; needs_human_eye flag is appropriate for the borderline zinc-500 body text.

**[content] Terms still declare public BETA while marketing positions a launched product**  _( confirmed )_
- **Evidence:** terms-of-service:24 "BETA STATUS: Tru8 is currently in public beta. Features, pricing, and availability may change ..." while the homepage ships a 'Get API Key' primary CTA and live priced plans.
- **Why it matters (buyer):** A researcher evaluating reliability reads 'public beta' as 'results and availability are not yet dependable' — a mixed signal against the confident marketing. Decide which is true and align.
- **Fix:** Either keep the beta caveat and soften the marketing's launched tone, or retire 'public beta' if GA. Founder call.
- **Verifier:** Quote confirmed at terms:24. Genuine cross-surface tension a reliability-conscious researcher would notice. Confirmed minor; correctly framed as a founder decision, no lock implications.

### NIT

**[copy] Hard-coded prices and per-check pence maths duplicated in Terms**  _( adjusted )_
- **Evidence:** terms-of-service:68 "40 checks per month (~18p per check)" and :77 "200 checks per month (~15p per check)"; plans £7/£29 match lib/tiers.ts (price 7 credits 40; price 29 credits 200). Maths: 7/40=17.5p, 29/200=14.5p — rounding correct.
- **Why it matters (buyer):** Two sources of truth for price drift apart over time; and the '~18p/~15p per check' COGS-style framing is not part of the customer-facing value story, so it reads oddly in a contract. Currency/price numbers are also founder-gated.
- **Fix:** Drop the per-check pence derivations (the COGS-style framing appears nowhere customer-facing). Keep the plan names and the £7/£29 figures — these are legitimate contract terms and match the live pricing config.
- **Verifier:** Adjusted on two counts. (1) Severity minor→nit. (2) The reviewer's fix overreaches: the price NUMBERS are not invented or ungated — they exactly match shipped lib/tiers.ts and the live pricing cards, and a subscription contract legitimately states its price, so stripping GBP figures from Terms would be wrong. The genuine oddity is only the '~18p/~15p per check' derivation. Founder-confirm note retained as caution, not as a directive to remove prices.

**[aesthetic] Legal link colour hard-codes hex instead of the accent token**  _( confirmed )_
- **Evidence:** globals.css:387 `.prose-legal a { @apply text-[#EA580C] hover:text-[#c2410c] ... }` while cookie-preferences-button.tsx:17 uses `text-accent`.
- **Why it matters (buyer):** Same value today, but a literal hex bypasses the token and will drift if the accent ever changes; minor system-hygiene inconsistency.
- **Fix:** Use `text-accent` plus an accent-derived hover to match the rest of the system.
- **Verifier:** Both references confirmed exactly (link rule is line 387, reviewer said 386 — adjacent). Pure system-hygiene; correctly rated nit. Note: app/layout.tsx themeColor is #f27907, distinct from the #EA580C accent, so tokenising avoids a third hardcoded orange drifting — minor extra reason to apply.

## Additional issues caught in verification

**[MINOR · content] Refund and Cookie policies omit the company-identity block that Privacy and Terms carry**
- **Evidence:** privacy-policy:186 and terms-of-service:283 both state 'Trueight Ltd (company number 17090683)' + ICO ZC110163. refund-policy and cookie-policy contain NONE of these (verified: zero matches for 'Trueight Ltd | 17090683 | ZC110163' in both files); their Contact sections (refund-policy:77-81, cookie-policy:170-174) carry only hello@trueight.com. For the sourcing-conscious researcher, a refund/cookie contract with no named legal entity is a weaker trust signal than the other two pages set up.
- **Fix:** Add a one-line legal-entity footer to refund-policy and cookie-policy (Trueight Ltd, company number 17090683, trading as Tru8, London UK) so identity is genuinely consistent across all four. This also corrects the reviewer's overstated 'complete across all four pages' strength.

**[MINOR · copy] Cookie policy 3.2 lists two duplicate manage-preferences bullets, one with an inaccurate '(when logged in)' qualifier**
- **Evidence:** cookie-policy:124-132 — bullet 1 'Clicking "Cookie Preferences" in the footer' (a working CookiePreferencesButton), then bullet 2 'Using the Cookie Preferences button in the website footer (when logged in)'. The two bullets describe the same control, and the consent banner is not gated on auth, so '(when logged in)' is misleading. A privacy-attentive reader parsing how to exercise the opt-out reads the contradictory pair as carelessness on the exact mechanism the page exists to explain.
- **Fix:** Collapse to a single bullet pointing at the footer Cookie Preferences button and drop the '(when logged in)' qualifier.

**[MINOR · positioning] Terms names the 'consensus' tier publicly inside a subscription plan, against the 'Consensus quiet' lock and adding agent drift**
- **Evidence:** terms-of-service:81 — Professional Plan includes 'Agent Commerce Gateway access (lookup, consensus, quick, full tiers)'. MEMORY repositioning-settled lock: 'Consensus quiet'. This surfaces the consensus tier by name and embeds agent-gateway tiering inside a human subscription description, re-centring copy a researcher reads about their own plan onto the agent/developer audience.
- **Fix:** Describe the Professional plan in researcher/customer terms (e.g. 'API and MCP access'); keep agent-gateway tier names out of the human plan copy and avoid surfacing 'consensus' until that lock is lifted. Founder-confirm.

## Strengths to keep
- Company and contact identity is consistent and complete across all four pages: Trueight Ltd (17090683), ICO registration ZC110163, hello@trueight.com, London UK — exactly the verifiable detail a sourcing-conscious researcher looks for.
- Language-lock compliant: terms-of-service:194-196 frames classifications as 'descriptive labels, not quality judgments' and 'Do not constitute Tru8's endorsement or criticism'; receipts for exclusions are disclosed (terms 199-203); no verdict/confidence/credibility-score language anywhere.
- UK-GDPR coverage is genuinely thorough — legal-basis table, all data-subject rights with concrete action paths, retention schedule, SCCs for international transfers, and ICO complaint route with full address.
- Privacy policy transparently discloses the Gemini AI processor relationship and the Cross-User Consensus aggregation (sections 5.5 and 14) — honest about how submitted content is handled, which matters to a researcher.
- Consistent canonical metadata (alternates.canonical) on all four routes, and all four are correctly linked from the footer.
- Refund and cancellation terms are internally consistent (14-day money-back + EU 14-day withdrawal in refund-policy mirror the 'no partial-month refunds' clause in terms-of-service:253).
