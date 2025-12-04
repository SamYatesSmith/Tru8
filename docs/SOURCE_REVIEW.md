# Tru8 Source Review & Coverage Audit

> **Purpose:** Track evidence source coverage across all domains to systematically improve fact-checking quality.
>
> **Last Updated:** 2025-11-27

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Domains Covered** | 8 of ~15 potential |
| **API Integrations** | 15 active |
| **Credibility Tiers Defined** | 50+ categories |
| **Overall Coverage Depth** | Medium |

### Coverage Heat Map

| Domain | Web Search | API Integration | Depth | Priority |
|--------|------------|-----------------|-------|----------|
| Health/Medical | Good | PubMed, WHO | **Deep** | - |
| Science/Academic | Good | CrossRef, PubMed | **Deep** | - |
| UK Government | Good | ONS, Companies House, GOV.UK, Hansard | **Deep** | - |
| US Government | Moderate | FRED, GovInfo | **Medium** | Improve |
| Law/Legal | Moderate | GovInfo (US only) | **Shallow** | **HIGH** |
| Finance/Economics | Good | ONS, FRED | **Medium** | Improve |
| Sports | Good | Football-Data.org, Transfermarkt | **Medium** | - |
| Climate/Weather | Moderate | Met Office (scaffold) | **Shallow** | Medium |
| Demographics | Moderate | ONS | **Medium** | - |
| Entertainment | Poor | None | **None** | Future |
| Technology | Poor | None | **None** | Future |
| Politics | Web only | None | **None** | Future |

---

## Part 1: API Integrations (Authoritative Sources)

### 1.1 Fully Implemented APIs

#### Web Search Providers
| Provider | Coverage | Rate Limits | Status |
|----------|----------|-------------|--------|
| **Brave Search** | Global/All domains | 2.5s spacing, retry on 429 | **Active** |
| **SerpAPI (Google)** | Global/All domains | 2.5s spacing | **Active** |

#### UK Government APIs
| API | Domain | Data Types | Key Required | Status |
|-----|--------|------------|--------------|--------|
| **ONS** | Finance, Demographics | Economic stats, census, unemployment | No | **Active** |
| **Companies House** | Government, Finance | Company registration, directors, filings | Yes | **Active** |
| **GOV.UK Content** | Government, General | Policy documents, guidance | No | **Active** |
| **Hansard** | Government, Law | Parliamentary debates, voting records | No | **Active** |

#### US Government APIs
| API | Domain | Data Types | Key Required | Status |
|-----|--------|------------|--------------|--------|
| **FRED** | Finance | Economic data series, interest rates | Yes | **Active** |
| **GovInfo.gov** | Law | Federal statutes, legislation | Yes | **Active** |

#### Global Health & Science APIs
| API | Domain | Data Types | Key Required | Status |
|-----|--------|------------|--------------|--------|
| **PubMed (NCBI)** | Health, Science | Medical research, peer-reviewed | Optional | **Active** |
| **WHO** | Health | Global health indicators | No | **Active** |
| **CrossRef** | Science | Academic metadata, DOIs | No | **Active** |

#### General Knowledge APIs
| API | Domain | Data Types | Key Required | Status |
|-----|--------|------------|--------------|--------|
| **Wikidata** | General | Structured facts, entities | No | **Active** |

#### Sports APIs
| API | Domain | Data Types | Key Required | Status |
|-----|--------|------------|--------------|--------|
| **Football-Data.org** | Sports | League standings, teams, matches, top scorers | Yes | **Active** |
| **Transfermarkt** | Sports | Transfers, career stats, achievements, market values | No | **Active** |

### 1.2 Partially Implemented (Scaffolding Only)

| API | Domain | Issue | Action Needed |
|-----|--------|-------|---------------|
| **Met Office** | Climate | Returns placeholder only | Implement actual weather/climate queries |

### 1.3 Listed in Credibility JSON but NOT Implemented

These sources are rated for credibility but have no direct API integration:

| Source | Domain | Why Not Implemented |
|--------|--------|---------------------|
| Sportradar | Sports | Premium API, expensive |
| MusicBrainz | Entertainment | Not prioritized for MVP |
| US Census API | Demographics | Not implemented yet |
| UK Parliament API | Law | Hansard covers partially |

---

## Part 2: Domain Deep-Dive

### 2.1 Sports - GOOD

**Current State:**
- Football-Data.org API provides real-time data (standings, matches, top scorers)
- Transfermarkt API provides historical data (transfers, career stats, achievements, market values)
- Source credibility covers 60+ sports domains

**Football-Data.org - Current vs Available:**

| Competition | Code | Currently Supported | Available |
|-------------|------|---------------------|-----------|
| Premier League | PL | Yes | Yes |
| La Liga | PD | Yes | Yes |
| Bundesliga | BL1 | Yes | Yes |
| Serie A | SA | Yes | Yes |
| Ligue 1 | FL1 | Yes | Yes |
| Champions League | CL | Yes | Yes |
| European Championship | EC | Yes | Yes |
| FIFA World Cup | WC | **Yes** | Yes |
| Championship (EFL) | ELC | **Yes** | Yes |
| Eredivisie | DED | **Yes** | Yes |
| Primeira Liga | PPL | **Yes** | Yes |
| Brasileirao | BSA | **Yes** | Yes |

**Data Types - Current vs Available:**

| Data Type | Currently Using | Available | Notes |
|-----------|-----------------|-----------|-------|
| League Standings | Yes | Yes | Full table with points, GD |
| Match Results | Yes | Yes | All competitions now supported |
| Team Info | Yes | Yes | Squad roster, staff |
| Player Stats | **Yes** | Yes | Via top scorers endpoint |
| Top Scorers | **Yes** | Yes | Goal rankings per season |
| Match Lineups | **NO** | Yes | Starting XI, substitutes |
| Head-to-Head | **NO** | Yes | Historical matchups |

**Other Sports - NO API Coverage:**

| Sport | Potential APIs | Priority |
|-------|---------------|----------|
| American Football | ESPN API, NFL Stats | Medium |
| Basketball | NBA API, Basketball-Reference | Medium |
| Tennis | ATP/WTA APIs | Low |
| Cricket | CricAPI, ESPN Cricinfo | Medium (UK market) |
| Formula 1 | Ergast API (free), F1 official | Low |
| Golf | PGA Tour API | Low |

**Transfermarkt API - Historical Data:**

| Data Type | Endpoint | Status |
|-----------|----------|--------|
| Player transfers | `/players/{id}/transfers` | **Active** |
| Career statistics | `/players/{id}/stats` | **Active** |
| Achievements/trophies | `/players/{id}/achievements` | **Active** |
| Market value history | `/players/{id}/market_value` | **Active** |
| Club profiles | `/clubs/{id}/profile` | **Active** |
| Club rosters | `/clubs/{id}/players` | **Active** |

**Credibility Sources (Web Search):**
- 60+ sports domains rated in credibility JSON
- Official governing bodies (FIFA, UEFA, etc.) at 0.93-1.0
- Sports data aggregators (Transfermarkt, etc.) at 0.82-0.92
- Sports news (ESPN, Sky Sports) at 0.85

**Action Items:**
- [x] Expand Football-Data.org to include World Cup, Championship, Eredivisie *(Done 2025-11-27)*
- [x] Add player statistics endpoint *(Done 2025-11-27 - via top scorers)*
- [x] Add top scorers endpoint *(Done 2025-11-27)*
- [x] Add Transfermarkt API for historical data *(Done 2025-11-27)*
- [ ] Consider ESPN API for broader sports coverage
- [ ] Consider cricket API for UK market
- [ ] Add match lineups endpoint
- [ ] Add head-to-head endpoint

---

### 2.2 Health/Medical - STRONG

**Current State:**
- PubMed API: 36M+ medical articles
- WHO API: Global health indicators
- Credibility: Academic (1.0), Scientific journals (0.95)

**Coverage Depth:**

| Data Type | Source | Status |
|-----------|--------|--------|
| Peer-reviewed research | PubMed | **Deep** |
| Global health stats | WHO | **Good** |
| Drug information | FDA (web only) | Medium |
| Clinical trials | ClinicalTrials.gov (not integrated) | **Gap** |
| UK health stats | NHS (web only) | Medium |

**Action Items:**
- [ ] Consider ClinicalTrials.gov API integration
- [ ] Consider OpenFDA API for drug data

---

### 2.3 Science/Academic - STRONG

**Current State:**
- CrossRef: Academic metadata, DOIs
- PubMed: Life sciences research
- Credibility: Academic (1.0), Scientific (0.95)

**Coverage Depth:**

| Data Type | Source | Status |
|-----------|--------|--------|
| Research metadata | CrossRef | **Deep** |
| Life sciences | PubMed | **Deep** |
| Physics/Math/CS | arXiv (web only) | Medium |
| Preprints | bioRxiv, medRxiv (web only) | Medium |

**Action Items:**
- [ ] Consider arXiv API for physics/CS research
- [ ] Consider Semantic Scholar API for citation analysis

---

### 2.4 Law/Legal - NEEDS IMPROVEMENT

**Current State:**
- GovInfo.gov: US federal statutes only
- Hansard: UK parliamentary debates
- Web search for case law

**Coverage Depth:**

| Jurisdiction | Statutes | Case Law | Regulations | Status |
|--------------|----------|----------|-------------|--------|
| US Federal | GovInfo API | Web only | Web only | **Medium** |
| US State | None | None | None | **Gap** |
| UK | legislation.gov.uk (web) | BAILII (web) | Web only | **Shallow** |
| EU | EUR-Lex (web only) | CURIA (web) | Web only | **Shallow** |

**Potential APIs:**
| API | Coverage | Free Tier |
|-----|----------|-----------|
| CourtListener | US case law | Yes (with limits) |
| Legislation.gov.uk API | UK statutes | Yes |
| EUR-Lex API | EU law | Yes |
| CanLII API | Canadian law | Limited |

**Action Items:**
- [ ] Implement UK Legislation.gov.uk API
- [ ] Consider CourtListener for US case law
- [ ] Consider EUR-Lex API for EU regulations

---

### 2.5 Finance/Economics - MODERATE

**Current State:**
- ONS: UK economic statistics
- FRED: US Federal Reserve data
- Web search for market news

**Coverage Depth:**

| Data Type | UK | US | Global |
|-----------|----|----|--------|
| Economic indicators | ONS | FRED | **Gap** |
| Company financials | Companies House | SEC (web) | **Gap** |
| Stock prices | Web only | Web only | **Gap** |
| Currency rates | Web only | Web only | **Gap** |

**Potential APIs:**
| API | Coverage | Free Tier |
|-----|----------|-----------|
| Alpha Vantage | Stock prices, forex | Yes (5 calls/min) |
| Yahoo Finance | Market data | Unofficial |
| World Bank API | Global indicators | Yes |
| ECB Data API | EU economic data | Yes |

**Action Items:**
- [ ] Consider World Bank API for global economic data
- [ ] Consider ECB Data API for EU statistics
- [ ] Consider Alpha Vantage for real-time market data

---

### 2.6 UK Government - STRONG

**Current State:**
- ONS: Statistics
- Companies House: Company data
- GOV.UK: Policy documents
- Hansard: Parliamentary records

**Coverage Depth:** **DEEP** - Best covered jurisdiction

**Action Items:**
- [ ] Ensure all APIs have proper error handling
- [ ] Monitor API deprecations

---

### 2.7 US Government - MODERATE

**Current State:**
- FRED: Economic data
- GovInfo: Legal statutes

**Coverage Gaps:**
| Agency | API Available | Implemented |
|--------|---------------|-------------|
| Census Bureau | Yes | No |
| SEC EDGAR | Yes | No |
| EPA | Yes | No |
| FDA | Yes | No |

**Action Items:**
- [ ] Implement Census Bureau API for demographics
- [ ] Consider SEC EDGAR for company filings

---

### 2.8 Climate/Weather - SHALLOW

**Current State:**
- Met Office: Scaffolding only (placeholder)
- Web search for climate news

**Coverage Gaps:**
| Data Type | Current | Needed |
|-----------|---------|--------|
| Weather forecasts | Placeholder | Met Office full implementation |
| Climate data | Web only | NOAA API |
| Historical weather | None | Open-Meteo API |

**Potential APIs:**
| API | Coverage | Free Tier |
|-----|----------|-----------|
| Met Office DataPoint | UK weather | Yes (5K/day) |
| Open-Meteo | Global weather/climate | Yes |
| NOAA APIs | US weather/climate | Yes |

**Action Items:**
- [ ] Complete Met Office implementation
- [ ] Consider Open-Meteo for global coverage

---

### 2.9 Entertainment - NOT COVERED

**Current State:** Web search only

**Potential APIs:**
| API | Coverage | Free Tier |
|-----|----------|-----------|
| TMDb | Movies, TV shows | Yes |
| MusicBrainz | Music metadata | Yes |
| Spotify API | Music | Yes (with auth) |
| IGDB | Video games | Yes |

**Priority:** Low for MVP

---

### 2.10 Technology - NOT COVERED

**Current State:** Web search only

**Credibility sources exist** for:
- Technical standards (IETF, W3C, ISO)
- Documentation (MDN, official docs)

**No API integration** - rely on authoritative web sources

**Priority:** Low for MVP

---

## Part 3: Source Credibility Summary

### Tier 1 Sources (0.85-1.0)

| Category | Credibility | Count |
|----------|-------------|-------|
| Academic (.edu, .ac.uk) | 1.0 | 19 domains |
| Primary Documents | 1.0 | 15 domains |
| Transportation Safety | 1.0 | 1 domain |
| Athletics/Sports Governing | 1.0 | 15+ domains |
| Scientific Journals | 0.95 | 18 domains |
| Government APIs | 0.95 | 16 domains |
| Academic Publishers | 0.95 | 15 domains |
| News Tier 1 | 0.9 | 10 domains |
| Legal | 0.9 | 12 domains |

### Tier 2 Sources (0.70-0.84)

| Category | Credibility | Count |
|----------|-------------|-------|
| Financial | 0.82 | 11 domains |
| News Tier 2 | 0.80 | 60+ domains |
| Sports Data Aggregators | 0.82 | 8 domains |
| Reference | 0.85 | 8 domains |

### Excluded/Flagged Sources

| Category | Credibility | Auto-Exclude |
|----------|-------------|--------------|
| Social Media | 0.3 | Yes |
| Satire | 0.0 | Yes |
| State Media | 0.5 | No (flagged) |
| Blacklist | 0.2 | No (flagged) |

---

## Part 4: Priority Action Items

### HIGH Priority (Next Sprint)

- [x] **Sports:** Expand Football-Data.org competitions (WC, ELC, DED) *(Done 2025-11-27)*
- [x] **Sports:** Add player statistics and top scorers endpoints *(Done 2025-11-27)*
- [x] **Sports:** Add Transfermarkt for historical data *(Done 2025-11-27)*
- [ ] **Legal:** Implement UK Legislation.gov.uk API
- [ ] **Climate:** Complete Met Office implementation

### MEDIUM Priority (Following Sprint)

- [ ] **Finance:** Add World Bank API for global economic data
- [ ] **Legal:** Consider CourtListener for US case law
- [ ] **Health:** Consider ClinicalTrials.gov API
- [ ] **Sports:** Consider ESPN API for broader coverage

### LOW Priority (Future)

- [ ] Entertainment APIs (TMDb, MusicBrainz)
- [ ] Technology standards APIs
- [ ] Additional regional news sources

---

## Part 5: Metrics to Track

### Coverage Metrics
- % of claims with API-sourced evidence
- % of claims with only web search evidence
- Average credibility score of evidence per domain

### Quality Metrics
- Verdict accuracy by domain (requires ground truth)
- User feedback by domain
- Evidence freshness by domain

### Source Health
- API uptime per provider
- Rate limit hits per provider
- Cache hit rates

---

## Appendix A: API Key Requirements

| API | Environment Variable | Required |
|-----|---------------------|----------|
| Brave Search | `BRAVE_API_KEY` | Yes |
| SerpAPI | `SERP_API_KEY` | Yes |
| Companies House | `COMPANIES_HOUSE_API_KEY` | Yes |
| FRED | `FRED_API_KEY` | Yes |
| GovInfo | `GOVINFO_API_KEY` | Yes |
| Met Office | `MET_OFFICE_API_KEY` | Yes |
| Football-Data.org | `FOOTBALL_DATA_API_KEY` | Yes |
| PubMed | `PUBMED_API_KEY` | Optional |

---

## Appendix B: Adding New Sources

### To add a new API source:

1. Create adapter class in `backend/app/services/api_adapters.py`
2. Implement `is_relevant_for_domain()`, `search()`, `_transform_response()`
3. Register in `initialize_adapters()`
4. Add domain keywords to `backend/app/utils/claim_classifier.py`
5. Add credibility ratings to `backend/app/data/source_credibility.json`
6. Add API key to `backend/app/core/config.py`
7. Document in this file

### To add credibility ratings only (web search):

1. Add domain patterns to `backend/app/data/source_credibility.json`
2. Specify tier, credibility score, and any risk flags

---

*This document should be updated whenever source coverage changes.*
