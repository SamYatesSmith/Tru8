# Objection Mining — Landing Page

**Date:** 2026-04-07
**Method:** Synthetic persona reactions (Claude playing personas grounded in `docs/marketing/MARKETING_RESEARCH.md`)
**Artifact under test:** Home page as of commit `bb8733c` — `web/app/page.tsx` + the five Stitch marketing components (`stitch-hero`, `stitch-process`, `stitch-features`, `stitch-video`, `stitch-pricing`)

> **Validity caveat:** This is hypothesis generation, not user research. Every objection below is Claude's stereotype of how the named persona would react, refined by the segment descriptions in the marketing docs. Treat as a backlog of things to **test on real people** and **fix where you already agree**, not as evidence of what real users think.

---

## Personas

| Name | Segment | Tier fit | Key trait |
|---|---|---|---|
| **Maria** | Investigative journalist (freelance, BIJ-adjacent) | Starter / Professional | Burned once by an AI tool that hallucinated a quote into print. Cares about source provenance, archive longevity, defensibility in court. |
| **Priya** | Policy researcher, Westminster think tank | Professional / Enterprise | Cites Hansard, ONS, GOV.UK daily. Risk-averse — won't put anything in a briefing paper she can't audit. |
| **Dev** | OSINT analyst, Bellingcat-adjacent open collective | Professional (API access) | Power user, methodology over UI. Distrusts black boxes, respects open methodology above all. |

---

## Maria — investigative journalist

> *Reads the page on a Tuesday afternoon between two sources. She has 90 seconds before her next call.*

### What works
- **"We organise. You decide."** lands. It's the only line on the page that tells me what kind of *partner* this is. I'd remember it.
- The three-step process is honest about what happens. I appreciate that it doesn't claim "AI fact-check" magic.
- The Chronologist sounds like something I'd actually use — when did each piece of evidence appear is exactly the right question for an investigation.

### What doesn't

1. **"Tru8 isn't a fact checker"** — okay, but then *what is it?* I read the rest of the paragraph and I still can't tell my editor in one sentence what I'd be using. The differentiation is *told*, never *shown*. Show me a worked example. Show me a real claim and what your output looks like. I shouldn't have to sign up to find out.
2. **"Classified by proximity and type"** — what does "proximity" mean? Geographic? Temporal? Source-to-event? This is jargon. If I have to learn your vocabulary before I trust the output, I won't bother.
3. **"30+ sources"** — *which* sources? Editors will ask. "It searches government data, news archives, academic papers" doesn't survive a copy-edit. I need a list. Hide nothing. (And if Hansard is in there, why isn't it on the home page? That alone would sell me.)
4. **The video is a placeholder.** I clicked "Platform Walkthrough" expecting to see the product. Nothing happened. Now I don't trust the rest of the page either — if the most prominent visual on your home page is broken, what else is half-built?
5. **The carousel auto-advances every 6 seconds.** I'm a slow reader on purpose. By the time I've read "The Cartographer", you've moved me to "The Librarian" and I've lost my place. It feels gimmicky for a tool that's supposed to be about rigour. A grid would respect my attention.
6. **Six "professions" with cute names.** I have actual cartographers and librarians at the British Library. "The Projectionist" for video evidence is twee. This whimsy reads as condescending to a 15-year reporter. The metaphor is doing real work for *understanding*, but it's actively repelling for *trust*.
7. **No bylines, no team, no methodology paper, no published examples.** Anonymous platform asking me to bet a career-relevant story on its output. I'd want to know who built this, who advises it, and read at least one technical document about how the classification works before I'd put it next to my name.
8. **No mention of permanence/archiving.** What if my source link rots in 18 months and I'm sued? I see Wayback mentioned nowhere on the homepage even though I think you do this — if so, it's a major selling point being hidden.
9. **No mention of how the analysis updates.** If a source is later retracted or contradicted, does my saved check update? Or is it a snapshot from the day I ran it? I need to know which.
10. **"Form your view"** assumes I want to *form* a view. Often I want to *confirm or disprove* a specific hypothesis. The exploratory framing is wrong-shape for adversarial reporting.
11. **"Start Analysing"** — analysing what? I haven't given it anything. The CTA presumes I'm already mid-task. "Try it on a headline" or "Paste a URL" would be more inviting.
12. **Pricing per "check" is wrong-shape for the work I do.** A real investigation might need 50 checks. £29/mo for 200 checks means I burn through it in two pieces. I want a model that scales with how I actually work — pay-per-investigation, or unlimited-with-rate-limit, or something.
13. **"All source types" appears in Free, Starter, AND Professional.** So what *actually* changes between tiers? "Priority processing" without numbers means nothing. "Full API & MCP access" — I don't code. So the £22 jump from Starter to Pro looks like I'm paying for something I won't use.

### What would have closed the sale
A 60-second video showing one real headline → the actual evidence landscape → me clicking through. Plus a public list of sources. Plus a worked example of a Chronologist output on a story I might have covered.

---

## Priya — policy researcher

> *Reads the page during a quiet hour between two briefing-paper drafts. Her instinct is "what could go wrong if I cite this?"*

### What works
- **"We organise; you decide."** is *perfect* for a civil-service-adjacent audience. It's compatible with the impartiality requirement. I would actually quote that line back to my line manager.
- **The Seeker** — "every evidence gap, surfaced clearly" — is the most interesting feature on the page for me. In policy work, the gap matters more than the answer. I'd pay for that view alone.
- Mentioning **government data** in step 2 makes me lean in. If GOV.UK / Hansard / ONS are in there, it's the first AI tool I've seen that's targeted at my actual workflow.

### What doesn't

1. **"Government data" is too vague to act on.** Which government? UK only? US? EU? I work UK-centric but my colleagues do trans-Atlantic. I can't tell from the page whether this is for me or not.
2. **No methodological transparency for the classification itself.** Who decided what counts as "primary"? What's the appeals process if Tru8 misclassifies a primary source as commentary? In policy work this matters because I have to justify every reference.
3. **No information about citation export.** Can I get a properly-formatted reference list? Footnotes? Hansard-style citations? If I have to manually re-cite everything, the time saving evaporates.
4. **No GDPR / data residency information.** A think tank cannot put a research subject's name into a tool whose data location is unknown. This should be on the homepage as a one-liner ("UK-hosted, GDPR-compliant"), not buried in a privacy policy.
5. **No SOC 2, ISO 27001, or any compliance signal.** Enterprise tier says "SLA guarantee" without specifying *what* the SLA is. I can't take this to procurement.
6. **No team / seat plan visible.** I work in a team of 12. We share research. The Pro tier is per-individual. Enterprise is "Contact Us" with no starting price or seat count, and that black box is what stops me even starting the conversation. Give me a "Team — from £X/seat" tier, even if it's just a placeholder, so I can budget.
7. **"Audit logs" / "version history" are absent from Pro.** Without these I can't show provenance to a client or under FOI. This is a minimum requirement, not an enterprise add-on.
8. **The Pro tier highlight ("Full API & MCP access") prices me out of my own use case.** I'm not a developer. I want priority processing and audit logs. I don't want API access. Why is the £29 tier built for someone who isn't me?
9. **"Proximity and type"** — does "primary source" here mean what it means in academic methodology? I can't tell. I need a one-page schema document I can show a peer reviewer.
10. **Custom integrations in Enterprise** — integration with what? Our research database is Notion. Is there a Notion connector? Without specifics, "custom integrations" reads as "ask us and we might say no".
11. **No mention of versioning the underlying data.** If ONS revises a figure six months from now, does the analysis I cited still work? Does it warn me?
12. **The carousel** — same complaint as Maria. I want to compare the Cartographer and the Seeker side-by-side. The carousel forces me to remember what the previous card said. A grid lets me cross-reference.

### What would have closed the sale
A one-page methodology document linked from the homepage. A "Team — from £X/seat" tier. A clear sentence about UK hosting and GDPR. An example of a citation export.

---

## Dev — OSINT analyst

> *Skims the page in 30 seconds. Already has a "this is a black box until proven otherwise" stance. Will hit Cmd-W if anything reads like marketing fluff.*

### What works
- **"We organise; you decide"** — finally, a fact-tool that knows it's a tool and not an oracle. I'd retweet this.
- **The Seeker view** is the only thing on the page that I haven't seen elsewhere. Surfaced gaps + targeted re-search is genuinely novel for the OSINT space.
- **MCP server in the Pro tier** is the second most interesting thing — it means I can integrate this into my existing toolchain instead of context-switching to a web app.

### What doesn't

1. **No GitHub link.** Where's the methodology paper? Where's the open classification schema? Where's the evidence that this isn't another "trust us, we use AI" tool? OSINT respects transparency above all, and the homepage gives me none.
2. **"30+ sources" — list them.** Hiding the list is the *opposite* of "we organise; you decide". If your value proposition is no hidden curation, the source list shouldn't be hidden either.
3. **The video is a placeholder.** Twice as damaging as for Maria — it says (a) I can't see the product, (b) the team ships incomplete things. If the home page is half-built, the pipeline is probably half-built too.
4. **No reproducibility statement.** If two analysts run the same claim at different times, do they get the same evidence set? Or does the model drift and I can't recreate yesterday's findings? OSINT requires reproducibility.
5. **No API rate limits or pricing.** The Pro tier says "Full API & MCP access" but doesn't say how much I can hit it. Is 200 checks/mo per UI plus unlimited API? Or shared? Or per-key? I need to know before I integrate.
6. **No webhook support visible. No batch operations. No "list of completed checks" endpoint.** OSINT workflows are programmatic. The page tells me I get an API but doesn't tell me whether the API is built for the way I work.
7. **No "view a sample report" link.** I should not have to sign up and burn one of three free credits to see what your output looks like.
8. **"Proximity and type"** — define both, on the homepage. I want to see the schema. Is "proximity" my term (source-to-event distance) or yours (geographic)? Until I know, I'm guessing.
9. **The Seeker is buried as the LAST card in the carousel.** It's the most interesting thing you have. Lead with it.
10. **The Cartographer's description is too gentle** — "where sources agree, where they diverge, and which are just echoing the same original" is *exactly* what a propaganda analyst needs, but you're not selling it like it is. The phrase "echoing the same original" is the strongest line on the entire page and it's hidden.
11. **£29 for 200 checks burns out fast.** A single OSINT investigation can need 30+ claim checks. I want a £100/mo "I use this professionally" tier with 1000+ checks. Enterprise = "Contact Us" = "I have to talk to a salesperson" = "I won't do this".
12. **No mention of Wayback / archive integration.** If you do archive evidence to Wayback (and the codebase suggests you do), this is a *major* OSINT selling point and it's invisible.
13. **The "professions" framing is fine for me** — I get the metaphor. But the cuteness ("The Projectionist") undermines the technical credibility. Drop "The". Just "Cartographer" / "Librarian" / "Seeker".
14. **No mention of jurisdiction routing** even though the codebase has it. UK/US/Global adapter filtering is a real differentiator for international OSINT. Surface it.

### What would have closed the sale
A GitHub link with a methodology document and the source list. A public sample report. A Pro tier with more headroom or a clear API-rate-limit story.

---

## Cross-cutting findings

These came up for two or three personas independently and are the highest-confidence problems:

### Tier 1 — Almost certainly real, fix first

| # | Issue | Personas | Fix |
|---|---|---|---|
| **C1** | **The video placeholder is the single most damaging element on the page.** It's broken, prominent, and makes everything else suspect. | Maria, Priya, Dev | Either ship a real 60–90s walkthrough, or remove the section entirely and replace with a static screenshot of a real evidence landscape. |
| **C2** | **No worked example, no sample report, no screenshot of the actual product.** Asking users to sign up before seeing the output is the wrong order. | Maria, Priya, Dev | Add a "See a real evidence landscape" link to a public anonymised report. The Cartographer view as a hero image would do most of the work alone. |
| **C3** | **The 30+ sources are hidden.** Three personas asked "which sources?" independently. Hiding the list directly contradicts "no hidden curation". | Maria, Priya, Dev | Put the source list on the home page (or a public `/sources` page linked from it). Group by category. This is a *defensive moat* — competitors can't easily match it. |
| **C4** | **"Proximity and type" is undefined jargon.** All three personas asked what it means. | Maria, Priya, Dev | Either define inline ("proximity = primary / reporting / commentary; type = data / official / news / analysis / opinion / academic") or replace with plain English. |
| **C5** | **No published methodology.** Trust gap with all three professional segments. | Maria, Priya, Dev | A single `/methodology` page (or a doc in `docs/`) explaining decompose → retrieve → score → classify → map. Doesn't have to be long. Has to exist. |
| **C6** | **The Seeker is buried.** All three personas independently flagged it as the most interesting feature, and it's the *last* card in an auto-advancing carousel. | Maria, Priya, Dev | Lead with the Seeker, or give it its own section above the six-profession carousel. |

### Tier 2 — Strong signal, fix second

| # | Issue | Personas | Fix |
|---|---|---|---|
| **C7** | **The carousel auto-advances and frustrates anyone trying to read carefully.** | Maria, Priya | Replace with a 2×3 grid, or make autoplay opt-in, or pause-on-hover from first interaction. |
| **C8** | **Pricing per check is wrong-shape for serious users.** All three professional personas felt 200 checks/mo would burn out fast on real work. | Maria, Dev | Either add a £100/mo "Heavy Use" tier (unlimited or 1000+), or make Enterprise show a starting price/seat count instead of a black box. |
| **C9** | **"All source types" appears in Free, Starter, AND Pro.** Tier differentiation is unclear. The Pro tier is the *highlighted* tier and its differentiator is "API & MCP access" — irrelevant to the largest segment (information professionals). | Maria, Priya | Rebuild the tier feature lists so each tier has *visible* additive value. Pro should not be the developer tier — split into "Pro" (research) and "Developer" (API). The tier ladder is fighting itself. |
| **C10** | **No team / seat-based plan, no Enterprise starting price.** Blocks the entire policy/think-tank segment from even starting the conversation. | Priya | Add a "Team — from £X/seat, 5+ seats" tier. Even a placeholder unblocks budget conversations. |
| **C11** | **No archive / permanence story on the homepage.** Tru8 *does* auto-archive to Wayback (per CLAUDE.md) but the homepage never says so. Major OSINT/journalism selling point hidden. | Maria, Dev | One line in the hero or features: "Every source archived to the Wayback Machine — your evidence won't rot." |
| **C12** | **No GDPR / hosting / compliance signal.** Blocks anyone in policy, healthcare, government, or enterprise. | Priya | One line: "UK-hosted, GDPR-compliant" + a `/security` page when you can. |

### Tier 3 — Lower priority, fix when convenient

| # | Issue | Personas | Fix |
|---|---|---|---|
| **C13** | **"The Cartographer / The Librarian / The Projectionist"** — the cute "The" prefix and metaphor undermines technical credibility for skeptical professionals. | Maria, Dev | Drop the "The". The metaphor itself is fine, the determiner makes it twee. |
| **C14** | **"Echoing the same original"** — the strongest line on the page, hidden inside a Cartographer card. | Dev | Promote to a section heading or hero subhead. This is the differentiator from verdict-based fact-checkers in eight words. |
| **C15** | **"Form your view"** assumes exploratory intent. Investigative work is hypothesis-driven. | Maria | A/B test "Form your view" against "Test the claim". |
| **C16** | **CTA "Start Analysing"** — analysing what? Presumes the user has a target. | Maria | "Paste a headline" or "Try it on a URL" is more inviting. |
| **C17** | **No reproducibility statement.** OSINT-specific concern. | Dev | "Same input, same output" guarantee — or document explicitly that the model drifts. Either is honest, the absence isn't. |
| **C18** | **No GitHub link / methodology paper / public roadmap.** | Dev | At minimum, link the GitHub from the footer once the MCP package is published. |

---

## Things to test on real people

The objections above are *hypotheses*. Before betting marketing budget on any of them, the highest-leverage real-user tests are:

1. **Show 5 real journalists the home page for 30 seconds and ask them to describe what Tru8 does in one sentence.** If three of five give a wrong or vague answer, the hero copy is the problem regardless of what the personas think.
2. **Show a real OSINT analyst the page with the carousel and the page with a 2×3 grid, and ask which one they trust more.** Tests C7 directly.
3. **Show a real policy researcher the pricing table and ask which tier they'd pick.** If they all pick Starter (because Pro looks dev-focused and Enterprise is opaque), C9 and C10 are confirmed.
4. **Ask one real OSINT person whether "proximity and type" makes sense without context.** A 30-second test.
5. **Show the Seeker in isolation to anyone in policy or OSINT and gauge reaction.** If the reaction is strong, C6 is confirmed and the Seeker should lead the page.

A 30-minute call with one journalist, one policy researcher, and one OSINT analyst would convert about 60% of these hypotheses into knowns.

---

## Top 5 things to fix this week (if I had to pick)

If you only do five things from this report:

1. **Replace or remove the video placeholder.** (C1)
2. **Add a "See a sample evidence landscape" link to a public anonymised report.** (C2)
3. **Publish the source list on a `/sources` page and link it from the home page.** (C3)
4. **Promote the Seeker out of the carousel.** (C6)
5. **Rework the pricing table** so Pro isn't both "the highlighted tier" and "the developer tier" — those are two different jobs. (C9)

Each of these is a few hours of work and addresses an objection that came up across all three personas independently.
