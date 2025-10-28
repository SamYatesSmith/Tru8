# Credibility Framework Discussion & Analysis

## Executive Summary

This document analyzes three concerns raised after testing the improved pipeline (check 87a8857c):
1. Evidence display bug for abstention verdicts
2. Static credibility list excluding independent journalists
3. Rigid credibility scoring creating perception of bias

---

## 🎯 FINAL RECOMMENDED STRATEGY: Progressive Curation Approach

**Key Insight:** Hiding individual credibility scores from users gives us freedom to iteratively build a proprietary source database tailored to our users' needs.

### Core Strategy

**Phase 1: Hide Scores, Expand Coverage (This Week)**
1. **Remove all numerical scores from UI** - Show qualitative labels only ("Expert Source", "Verified Source", "General Source")
2. **Expand static source list from 227 → 300+** by adding:
   - Primary documents (govinfo.gov, archives.gov, legislation.gov.uk, congress.gov)
   - Academic publishers (Oxford, Cambridge, MIT Press, Harvard Press)
   - Digital archives (JSTOR, ProQuest, HathiTrust, archive.org)
   - Investigative nonprofits (ProPublica already included, add Intercept, Bureau of Investigative Journalism)
3. **Implement unknown source tracking** - Log every unknown domain with frequency, topic context

**Phase 2: Progressive Database Growth (Weekly Curation)**
4. **Admin dashboard** showing "Trending Unknown Sources"
   - "substack.com/heathercoxrichardson appeared in 8 checks this week"
   - Research journalist credentials, decide credibility tier, add to database
5. **Topic-based expansion alerts**
   - "Climate claims increasing → Review specialized climate sources"
   - "Legal claims increasing → Add more law review journals"
6. **Monthly category expansion**
   - Month 1: +20 primary document sources
   - Month 2: +15 academic publishers
   - Month 3: +10 subject-matter expert platforms
   - Month 4: +10 international specialist outlets

**Phase 3: Intelligent Assessment (LLM + Multi-Signal)**
7. **Multi-signal algorithm** for unknowns (no LLM cost):
   - Domain age, HTTPS, author bylines, primary source citations, correction policies
   - Raises unknowns from flat 0.6 → dynamic 0.5-0.85
8. **LLM-based assessment** for high-potential sources (>0.7 from multi-signal):
   - Research author credentials, publication history, peer recognition
   - Cache results 90 days
   - Cost: ~$0.005-0.01 per unknown source
9. **Retroactive updates** - When new source added, update past checks using it (users never see change)

**Why This Approach Wins:**
- ✅ **No recurring API costs** ($1k/month NewsGuard avoided)
- ✅ **Proprietary knowledge** tailored to YOUR users' claim patterns
- ✅ **No controversy** - users never see individual scores changing
- ✅ **Covers books, documents, specialists** - not just online news
- ✅ **Learns from usage** - discovers important sources organically
- ✅ **Scales efficiently** - start small, grow as needed

**Current Gap Analysis:**
- 227 online news sources ✓
- Primary documents (legislation, court rulings) ❌
- Books (academic, historical texts) ❌
- Specialist publications (climate, tech policy, regional experts) ❌
- Independent journalists (Substack, personal sites) ❌
- International voices outside Western mainstream ❌

**After 6 months:** 350+ curated sources covering news, primary docs, books, specialists, with ongoing organic growth driven by user behavior.

---

## Detailed Options Analysis

*The sections below document all options considered. The progressive curation approach above synthesizes the best elements of each.*

---

## Issue #1: Evidence Display Bug Investigation

### User Report
"Some abstention verdicts (insufficient_evidence, conflicting_expert_opinion) don't show headlines or URLs in evidence dropdowns, but some do."

### Investigation Results

**Database Verification:**
```sql
-- Checked all 6 abstention verdict claims
-- Result: 0 missing titles, 0 missing URLs across all evidence
```

| Claim Position | Verdict | Evidence Count | Missing Titles | Missing URLs |
|---|---|---|---|---|
| 0 | conflicting_expert_opinion | 3 | 0 | 0 |
| 2 | conflicting_expert_opinion | 3 | 0 | 0 |
| 3 | insufficient_evidence | 1 | 0 | 0 |
| 5 | insufficient_evidence | 3 | 0 | 0 |
| 6 | insufficient_evidence | 1 | 0 | 0 |
| 7 | insufficient_evidence | 2 | 0 | 0 |

**API Code Review:**
- `backend/app/api/v1/checks.py:334-346` - Returns ALL evidence without verdict-based filtering
- No conditional logic based on verdict type

**Frontend Code Review:**
- `web/app/dashboard/check/[id]/components/claims-section.tsx:188-196` - Displays `evidence.title` and `evidence.url` directly
- No conditional rendering based on verdict type
- Evidence sorted by fact-check priority and relevance, but all displayed

**Sample Evidence Data:**
```
Claim 7 (insufficient_evidence):
  Title: House Democrats request details on White House ballroom from President Trump - CBS News
  URL: https://www.cbsnews.com/news/house-democrats-request-trump-ballroom-details/

Claim 6 (insufficient_evidence):
  Title: East Wing demolition highlights loopholes in preservation law - Roll Call
  URL: https://rollcall.com/2025/10/24/east-wing-demolition-highlights-loopholes-in-preservation-law/
```

### Conclusion

**NOT A BUG** - All evidence data is complete in database, correctly returned by API, and properly rendered by frontend.

**Possible Explanations:**
1. **User perception** - Some evidence snippets may be long/complex, making UI appear broken
2. **Character encoding** - Found one instance of `�` character (Unicode replacement) in title
3. **Different check** - User may have been viewing older check (4e3aee4f) which had empty context fields
4. **Browser caching** - Old data cached in browser

**Recommendation:** Mark as resolved. Monitor user reports for specific reproducible cases.

---

## Issue #2: Static Credibility List Limitations

### User Concern
> "Are we limiting ourselves by having a set credibility list? I am nervous about not accounting for world class independent journalistic fact checkers. People that dedicate their lives to truth finding will never be heard by Tru8... which will always be a flaw."

### Current System Analysis

**What's Included:**
```json
{
  "news_tier2": {
    "credibility": 0.8,
    "domains": [
      "theguardian.com",
      "washingtonpost.com",
      "nytimes.com",
      "propublica.org",  // ← Non-profit investigative journalism
      ...
    ]
  },
  "factcheck": {
    "credibility": 0.95,
    "domains": [
      "snopes.com",
      "factcheck.org",
      "fullfact.org",
      ...
    ]
  }
}
```

**What's Missing:**
- ❌ Independent journalist platforms (Substack, Medium, Ghost)
- ❌ Freelance investigative journalists' personal websites
- ❌ Small/regional investigative outlets
- ❌ Specialized topic-focused journalism (e.g., environmental, tech policy)
- ❌ Emerging credible sources
- ❌ International independent journalism not yet on radar

**Default Behavior:**
Unknown sources → `"general"` tier → `credibility: 0.6`

This means:
- Pulitzer Prize winner publishing on personal blog: **0.6 credibility**
- Daily Mail tabloid (explicitly listed): **0.55 credibility**
- Result: Independent expert rated nearly identical to sensationalist tabloid

### The Fundamental Problem

The static list creates a **credibility establishment bias**:
1. Favors institutional sources over individual expertise
2. Assumes domain name determines quality (not author credentials)
3. Can't adapt to emerging credible voices
4. Penalizes independent journalism as "unverified"

### Potential Solutions - Spectrum Analysis

#### Option A: Hybrid Static + Dynamic System

**Approach:** Keep static list for known sources, add dynamic assessment for unknown domains

**Dynamic Assessment Methods:**
1. **LLM-Based Source Evaluation**
   - Use Claude/GPT to analyze:
     - Author credentials (LinkedIn, Google Scholar)
     - Publication history and citations
     - Peer recognition/awards
     - Topic expertise
   - Generate credibility score with reasoning
   - Cache results for 30 days

2. **Citation Analysis**
   - Count how many tier1/tier2 sources cite this author
   - Cross-reference patterns (do reputable outlets link to them?)
   - Academic citation metrics (H-index for researchers)

3. **Content Quality Indicators**
   - Presence of primary sources
   - Fact-check references
   - Correction/transparency policies
   - Byline/author attribution

**Implementation:**
```python
def get_credibility(source: str, url: str, content: str = None):
    # Try static list first
    static_result = match_static_tier(domain)
    if static_result["tier"] != "general":
        return static_result

    # Unknown source - use dynamic assessment
    if settings.ENABLE_DYNAMIC_CREDIBILITY:
        return dynamic_credibility_assessment(url, content)
    else:
        return {"tier": "general", "credibility": 0.6}
```

**Pros:**
- Recognizes independent expertise
- Adapts to new credible sources
- Maintains speed for known sources

**Cons:**
- LLM calls = cost/latency per unknown source
- Cache management complexity
- Risk of LLM hallucinating author credentials

---

#### Option B: Third-Party Credibility APIs

**Services Available:**
1. **NewsGuard** (newsguardtech.com)
   - Human-reviewed news source ratings
   - Covers 8,500+ news sources
   - API available (~$1,000/mo for API access)
   - Includes misinformation tracking

2. **Media Bias/Fact Check API**
   - Community + expert reviews
   - Credibility + bias ratings
   - Free tier available

3. **Meltwater Media Intelligence**
   - Media reputation scoring
   - Enterprise pricing

**Implementation:**
```python
def get_credibility(source: str, url: str):
    static = match_static_tier(domain)
    if static["tier"] != "general":
        return static

    # Query NewsGuard API
    newsguard_score = newsguard_api.get_rating(domain)
    if newsguard_score:
        return map_newsguard_to_credibility(newsguard_score)

    return {"tier": "general", "credibility": 0.6}
```

**Pros:**
- Professional human review
- Regularly updated
- Lower latency than LLM
- Authoritative source

**Cons:**
- Recurring cost ($1,000+/month)
- Still may miss niche independent journalists
- Dependency on third-party service
- May have own biases

---

#### Option C: Community + Editorial Review System

**Approach:** User submission system with internal review process

**Workflow:**
1. User encounters unknown source during check
2. Option to "Submit source for review"
3. Internal team reviews within 48 hours
4. Add to `source_credibility.json`
5. Retroactively update past checks using that source

**Enhanced with:**
- Voting system (trusted users vote on source credibility)
- Wikipedia-style edit history
- Quarterly review of all sources

**Pros:**
- Low tech complexity
- Human judgment on nuanced cases
- Community involvement
- Full control

**Cons:**
- Manual labor intensive
- 48-hour lag for new sources
- Doesn't scale beyond MVP
- Subjective judgment variations

---

#### Option D: Multi-Signal Scoring Algorithm

**Approach:** Combine multiple objective signals without LLM

**Signals:**
```python
credibility_signals = {
    "domain_age": get_domain_registration_age(domain),  # Older = more established
    "https_enabled": url.startswith("https"),
    "author_byline": has_author_attribution(content),
    "correction_policy": has_corrections_page(domain),
    "about_page": has_about_page(domain),
    "contact_info": has_contact_page(domain),
    "primary_sources": count_cited_sources(content),
    "fact_check_references": contains_factcheck_links(content),
    "social_verification": twitter_verification(author),  # Blue check (pre-2023)
    "wikipedia_page": has_wikipedia_page(domain),
}

def calculate_dynamic_credibility(signals):
    base = 0.5

    if signals["domain_age"] > 5 years: base += 0.1
    if signals["author_byline"]: base += 0.05
    if signals["primary_sources"] > 3: base += 0.1
    if signals["correction_policy"]: base += 0.05
    if signals["https_enabled"]: base += 0.05
    # ... etc

    return min(0.85, base)  # Cap at 0.85 (below tier1 news)
```

**Pros:**
- No LLM cost
- Fast/deterministic
- Objective metrics
- Transparent scoring

**Cons:**
- Surface-level analysis (can't evaluate journalism quality)
- Gameable by bad actors
- Misses context (satire sites have "about" pages too)
- Won't recognize true expertise

---

### Recommended Approach: Hybrid A + D

**Phase 1 (Immediate - 1 week):**
- Implement **Option D** (Multi-Signal Algorithm)
- Raises unknown sources from flat 0.6 to 0.5-0.85 based on objective signals
- No LLM cost, fast, deterministic

**Phase 2 (2-4 weeks):**
- Add **Option A** (LLM-based assessment) for:
  - Sources with author bylines
  - Content with primary source citations
  - Domains scoring >0.7 from Phase 1 signals
- Cache aggressively (90 days)
- LLM prompt:
  ```
  Analyze this article source:
  Domain: {domain}
  Author: {author_name}
  Article: {title}

  Research:
  1. Author credentials and expertise
  2. Publication history/reputation
  3. Citations by reputable outlets
  4. Awards/recognition

  Return credibility score (0.5-0.9) with reasoning.
  ```

**Phase 3 (Post-MVP):**
- Integrate **Option B** (NewsGuard API) if budget allows
- Use as final arbiter for controversial sources
- Override LLM assessment when available

**Fallback Chain:**
```
Static List → NewsGuard API → Multi-Signal → LLM → Default (0.6)
```

---

## Issue #3: Credibility Scoring Rigidity & Transparency

### User Concern
> "The weight/credibility we are assigning assumes quality based on establishment. A more dynamic system may be required. Either way, I don't know if it's wise to show the user the credibility scores. It implies bias from Tru8's perspective. This is likely to narrow our audience if we SHOW the user preference."

### Current System

**Fixed Tier Scores:**
```
Scientific journals:  1.0
Academic:             1.0
Fact-checkers:        0.95
Tier1 news (BBC/AP):  0.9
Government:           0.85
Tier2 news (Guardian):0.8
Tabloids:             0.55
State media:          0.5
```

**Displayed to User:**
`web/app/dashboard/check/[id]/components/claims-section.tsx:221-225`
```tsx
<span className="font-medium">
  {evidence.credibilityScore
    ? `${(evidence.credibilityScore * 10).toFixed(1)}/10`
    : `${(evidence.relevanceScore * 10).toFixed(1)}/10`}
</span>
```

User sees: **"The Guardian · Oct 2025 · 8.0/10"**

### The Problems

#### Problem 3A: Establishment Bias Perception

**Reality of Journalism:**
- NYTimes (0.8) has published corrections, retractions, major errors
- Small investigative outlet may have perfect track record
- Veteran journalist at tabloid > junior reporter at tier1

**Rigid scoring assumes:**
- Domain = quality (false)
- Institutional backing = better journalism (sometimes false)
- Tabloid = always lower quality (sometimes false)

**User's concern is valid:** Showing "8.0/10" for Guardian but "5.5/10" for Daily Mail makes Tru8 appear to endorse political positions.

#### Problem 3B: Perception vs. Reality Tradeoff

**Arguments FOR showing scores:**
- Transparency builds trust
- Users deserve to know why verdicts were reached
- Educational - teaches media literacy
- Differentiates Tru8 from "black box" AI

**Arguments AGAINST showing scores:**
- Appears politically biased (BBC 9.0 vs. Fox News not listed)
- Reduces complex journalism quality to single number
- Users may reject valid evidence due to source prejudice
- Creates defensiveness in users who trust downweighted sources

**Industry Comparison:**

| Platform | Source Credibility Display |
|---|---|
| Google News | No scores shown, just source name |
| Apple News | Curates sources, no scores |
| Perplexity AI | Shows sources, no credibility scores |
| ChatGPT | Cites sources, no ranking |
| Ground News | Shows bias/factuality explicitly (their USP) |

**Key Insight:** Most platforms hide credibility scoring, focusing on source diversity instead.

---

### Proposed Solutions

#### Solution 1: Hide Numerical Scores, Show Qualitative Tiers

**Change UI from:**
```
The Guardian · Oct 2025 · 8.0/10
```

**To:**
```
The Guardian · Oct 2025 · Verified News Source
```

**Tier Labels:**
- `1.0-0.9`: "Expert Source" (scientific, academic)
- `0.89-0.8`: "Verified News Source" (tier1/tier2 news)
- `0.79-0.6`: "General News Source"
- `<0.6`: "Unverified Source"
- Satire: "Satirical Content"

**Pros:**
- Less precise = less controversial
- Conveys credibility without numerical judgment
- Reduces "score shopping" behavior
- Still transparent about source quality

**Cons:**
- Less granular information
- May still provoke "who decides what's verified?" questions

---

#### Solution 2: Show Methodology, Hide Individual Scores

**Approach:**
- Create `/methodology` page explaining credibility framework
- Show aggregate credibility in overall check summary
- Individual evidence shows: Source · Date · [Hidden score used internally]

**Check-Level Display:**
```
Overall Credibility: 8.2/10
Based on 15 evidence sources:
- 3 expert sources
- 8 verified news sources
- 4 general sources
```

**Evidence-Level Display:**
```
The Guardian · Oct 2025
```

**Pros:**
- Transparency at aggregate level
- Individual source politics avoided
- Educates users on process without prescribing judgment
- Less defensive user reactions

**Cons:**
- Users may want source-level granularity
- Less actionable for evaluating individual evidence

---

#### Solution 3: User-Controlled Transparency

**Approach:** Let users choose their preference

**Settings Toggle:**
```
☐ Show credibility scores for sources
  Advanced users: See detailed scoring for each source.
  May help evaluate evidence quality.

☑ Hide credibility scores
  Default: Scores used internally but not displayed.
  Reduces perception of bias.
```

**Pros:**
- User choice respects different preferences
- Power users get granular data
- General users avoid score controversies
- A/B test to see which drives better engagement

**Cons:**
- Adds UI complexity
- May confuse users ("what am I missing?")
- Requires settings infrastructure

---

#### Solution 4: Context-Aware Display

**Approach:** Show scores only when helpful, hide when controversial

**Logic:**
```typescript
function shouldShowCredibilityScore(evidence) {
  // Show for very high credibility (builds trust)
  if (evidence.credibilityScore >= 0.9) return true;

  // Show for very low credibility (warning)
  if (evidence.credibilityScore <= 0.4) return true;

  // Hide for mid-range (0.5-0.89) - avoids controversy
  return false;
}
```

**Display Examples:**
- Nature.com (1.0) → "Nature · Oct 2025 · **Expert Source (10/10)**"
- The Guardian (0.8) → "The Guardian · Oct 2025" *(score hidden)*
- Infowars (0.2) → "Infowars · Oct 2025 · ⚠️ **Low Credibility (2/10)**"

**Pros:**
- Highlights extremes, avoids mid-range politics
- Warnings protect users from misinformation
- Recognition rewards high-quality sources
- Reduces controversy for "good enough" sources

**Cons:**
- Inconsistent UX (some have scores, some don't)
- Users may infer hidden scores are "bad"
- Complex logic to maintain

---

### Recommended Solution: Combination 1 + 2

**Implementation:**

**1. Evidence Display (Solution 1 - Qualitative):**
```tsx
The Guardian · Oct 2025 · Verified News Source
Nature.com · Sept 2025 · Expert Source
Daily Mail · Oct 2025 · General Source
```

**2. Check-Level Summary (Solution 2 - Aggregate):**
```tsx
Evidence Quality Assessment
━━━━━━━━━━━━━━━━━━━━━━━━
• 4 Expert Sources (scientific journals, fact-checkers)
• 8 Verified News Sources (international & national news)
• 3 General Sources

Overall Evidence Credibility: 8.4/10
```

**3. Methodology Page:**
- Link to `/methodology` explaining tier system
- Full transparency on how sources categorized
- Acknowledge limitations and update process
- Invite source submissions for review

**Benefits:**
- Removes numerical controversy from individual sources
- Maintains transparency at aggregate level
- Educates users on quality signals without prescribing judgment per source
- Reduces perception of political bias

---

## Summary of Recommendations

### Issue #1: Evidence Display Bug
**Status:** ✅ **RESOLVED** - No technical bug found, all data present and correct

---

### Issue #2: Independent Journalist Coverage

**Immediate Action (Week 1):**
1. Implement **Multi-Signal Algorithm** (Option D)
   - Analyze domain age, HTTPS, author bylines, citations
   - Raise unknown sources from flat 0.6 to dynamic 0.5-0.85
   - File: `backend/app/services/dynamic_credibility.py`

**Near-Term (Weeks 2-4):**
2. Add **LLM-Based Assessment** (Option A) for high-potential unknowns
   - Use Claude to research author credentials
   - Cache results for 90 days
   - Only invoke for sources scoring >0.7 from multi-signal

**Post-MVP:**
3. Integrate **NewsGuard API** (Option B) if budget allows
   - Professional human review
   - Regular updates
   - Override LLM when available

**Fallback Chain:**
```
Static List → NewsGuard → Multi-Signal → LLM → Default (0.6)
```

---

### Issue #3: Credibility Transparency

**Immediate Action (Week 1):**
1. **Replace numerical scores with qualitative labels** (Solution 1)
   - Expert Source (0.9-1.0)
   - Verified News Source (0.8-0.89)
   - General Source (0.6-0.79)
   - Unverified Source (<0.6)

2. **Add check-level aggregate display** (Solution 2)
   - Show evidence tier distribution
   - Show overall credibility score
   - Remove individual source scores

3. **Create methodology page**
   - Full transparency on credibility system
   - Acknowledge limitations
   - Explain tier definitions
   - Source submission process

**Example Evidence Display:**
```
BEFORE (now):
The Guardian · Oct 2025 · 8.0/10

AFTER (proposed):
The Guardian · Oct 2025 · Verified News Source
```

**Example Check Summary:**
```
Evidence Quality: 8.4/10

15 sources analyzed:
• 4 Expert Sources
• 8 Verified News Sources
• 3 General Sources

View our methodology →
```

---

## Implementation Priority

### Sprint 1 (This Week)
- [ ] Replace credibility scores with qualitative labels (frontend)
- [ ] Add check-level aggregate display (frontend)
- [ ] Create `/methodology` page explaining system

### Sprint 2 (Next Week)
- [ ] Implement multi-signal credibility algorithm (backend)
- [ ] Test with sample unknown sources
- [ ] Update credibility display to show dynamic results

### Sprint 3 (Weeks 3-4)
- [ ] Add LLM-based credential research for unknowns
- [ ] Implement caching system
- [ ] Add admin dashboard to review LLM assessments

### Post-MVP
- [ ] Evaluate NewsGuard API integration
- [ ] Build community source submission system
- [ ] Quarterly review process for credibility list

---

## Open Questions for Discussion

1. **Qualitative labels:** Do the proposed tier names ("Expert Source", "Verified News Source") feel appropriate? Alternative suggestions?

2. **Aggregate display:** Should check-level credibility be prominent or hidden in expandable section?

3. **LLM assessment cost:** At ~$0.02 per check currently, adding LLM credibility checks might add $0.005-0.01 per unknown source. Acceptable?

4. **NewsGuard budget:** $1,000/mo for API access. Worth it for MVP or post-revenue?

5. **User testing:** Should we A/B test "show scores" vs "hide scores" with early users to measure impact on trust/engagement?

6. **Dynamic scoring floor:** Should unknown sources be capped at 0.85 (below tier1) or allowed to reach 0.95 if LLM finds exceptional credentials?

---

*Document prepared: 2025-10-28*
*Ready for stakeholder review and decision*
