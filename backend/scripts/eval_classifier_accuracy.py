#!/usr/bin/env python3
"""PQ-08 Measurement: Heuristic vs LLM Classification Accuracy.

Builds a corpus of 100 realistic evidence items from diverse sources,
classifies each with the heuristic, then with the LLM, and compares.

Usage:
    python scripts/eval_classifier_accuracy.py              # Full run (LLM calls)
    python scripts/eval_classifier_accuracy.py --heuristic-only  # Heuristic analysis only (free)

Output:
    - Per-item comparison table
    - Agreement rate (tier, type, both)
    - Confusion matrices
    - Heuristic bias analysis (default fallthrough rate)
"""

import asyncio
import json
import sys
import os
from collections import Counter
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.evidence_classifier import (
    _classify_heuristic,
    EvidenceClassifier,
    VALID_TIERS,
    VALID_TYPES,
)


# -- Corpus: 100 realistic evidence items across all domains --------------
# Each item has: title, url, source, snippet
# Manually labelled with expected_tier and expected_type as ground truth

EVIDENCE_CORPUS = [
    # -- PRIMARY / DATA (items 0-14) --------------------------------------
    {
        "title": "Consumer Price Inflation, UK: January 2026",
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/january2026",
        "source": "ons.gov.uk",
        "snippet": "The Consumer Prices Index (CPI) rose by 3.0% in the 12 months to January 2026, down from 3.2% in December.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Employment Situation Summary — January 2026",
        "url": "https://www.bls.gov/news.release/empsit.nr0.htm",
        "source": "bls.gov",
        "snippet": "Total nonfarm payroll employment increased by 256,000 in January, and the unemployment rate was 4.1 percent.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "GDP (current US$) — World Bank Open Data",
        "url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        "source": "worldbank.org",
        "snippet": "GDP at purchaser's prices is the sum of gross value added by all resident producers in the economy.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "UNRATE: Unemployment Rate — FRED",
        "url": "https://fred.stlouisfed.org/series/UNRATE",
        "source": "fred.stlouisfed.org",
        "snippet": "The unemployment rate represents the number of unemployed as a percentage of the labor force. Seasonally Adjusted.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Global Health Observatory: Life Expectancy",
        "url": "https://data.who.int/indicators/i/9169839/5",
        "source": "data.who.int",
        "snippet": "Healthy life expectancy (HALE) at birth (years). Global average: 63.3 years (2024).",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "NOAA National Temperature Index — January 2026",
        "url": "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/national/time-series",
        "source": "ncei.noaa.gov",
        "snippet": "The January 2026 temperature for the contiguous US was 33.4°F, 3.2°F above the 20th century average.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Eurostat: Annual inflation rate — Euro area",
        "url": "https://ec.europa.eu/eurostat/documents/2995521/18221444/2-01032026-AP-EN.pdf",
        "source": "eurostat.ec.europa.eu",
        "snippet": "Euro area annual inflation is expected to be 2.4% in February 2026, down from 2.8% in January.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Premier League Standings 2025-26",
        "url": "https://www.transfermarkt.com/premier-league/tabelle/wettbewerb/GB1",
        "source": "transfermarkt.com",
        "snippet": "Arsenal: 65 pts, Liverpool: 63 pts, Manchester City: 58 pts. Matchday 28.",
        "expected_tier": "primary",
        "expected_type": "data",
        "external_source_provider": "Transfermarkt",
    },
    {
        "title": "Species occurrence data: Panthera leo",
        "url": "https://www.gbif.org/species/5219404",
        "source": "gbif.org",
        "snippet": "Panthera leo Linnaeus, 1758. Kingdom: Animalia. 152,847 occurrence records. Conservation: Vulnerable (IUCN).",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Wikidata: Douglas Adams (Q42)",
        "url": "https://www.wikidata.org/wiki/Q42",
        "source": "wikidata.org",
        "snippet": "Douglas Noël Adams (11 March 1952 – 11 May 2001) was an English author, humorist, and screenwriter.",
        "expected_tier": "primary",
        "expected_type": "data",
        "external_source_provider": "Wikidata",
    },
    {
        "title": "UK House Price Index: December 2025",
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/housepriceindex/december2025",
        "source": "ons.gov.uk",
        "snippet": "Average UK house prices increased by 4.8% in the 12 months to December 2025 (provisional estimate).",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "IMF World Economic Outlook Database",
        "url": "https://www.imf.org/en/Publications/WEO/weo-database/2025/October",
        "source": "imf.org",
        "snippet": "Real GDP growth projections for 2026. Advanced economies: 1.8%, Emerging markets: 4.2%, World: 3.3%.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Sea Level Trends — NOAA Tides & Currents",
        "url": "https://tidesandcurrents.noaa.gov/sltrends/sltrends.html",
        "source": "tidesandcurrents.noaa.gov",
        "snippet": "The graphs show monthly mean sea level without the regular seasonal fluctuations due to coastal ocean temperatures.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "COVID-19 Data Explorer — Our World in Data",
        "url": "https://ourworldindata.org/explorers/coronavirus-data-explorer",
        "source": "ourworldindata.org",
        "snippet": "Cumulative confirmed COVID-19 deaths per million people. Data sources: WHO, JHU CSSE.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "ArXiv: Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "source": "arxiv.org",
        "snippet": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    # -- PRIMARY / OFFICIAL STATEMENT (items 15-29) -----------------------
    {
        "title": "PM statement on the Spring Budget 2026",
        "url": "https://www.gov.uk/government/speeches/pm-statement-spring-budget-2026",
        "source": "gov.uk",
        "snippet": "The Prime Minister made a statement to the House of Commons on the Spring Budget 2026.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Bank of England Monetary Policy Summary, March 2026",
        "url": "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/march-2026",
        "source": "bankofengland.co.uk",
        "snippet": "The MPC voted by a majority of 7-2 to maintain Bank Rate at 4.5%.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Hansard: Immigration Bill Second Reading",
        "url": "https://hansard.parliament.uk/commons/2026-02-15/debates/abc123/ImmigrationBill",
        "source": "hansard.parliament.uk",
        "snippet": "The Secretary of State for the Home Department (Yvette Cooper): I beg to move, That the Bill be now read a Second time.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Executive Order on AI Safety",
        "url": "https://www.whitehouse.gov/briefing-room/presidential-actions/2025/10/30/executive-order-ai",
        "source": "whitehouse.gov",
        "snippet": "By the authority vested in me as President by the Constitution and the laws of the United States of America.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "WHO Director-General Opening Remarks at Press Briefing",
        "url": "https://www.who.int/director-general/speeches/detail/who-director-general-opening-remarks-20260301",
        "source": "who.int",
        "snippet": "Good morning. Thank you for joining today's briefing on the global health situation.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "SEC Charges Company with Securities Fraud",
        "url": "https://www.sec.gov/litigation/litreleases/2026/lr25890.htm",
        "source": "sec.gov",
        "snippet": "The Securities and Exchange Commission today charged XYZ Corp. with making materially misleading statements.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "UK Supreme Court Judgment: Smith v Jones [2026] UKSC 12",
        "url": "https://www.supremecourt.uk/cases/uksc-2025-0145.html",
        "source": "supremecourt.uk",
        "snippet": "LORD REED (with whom Lady Arden, Lord Lloyd-Jones, Lord Briggs and Lady Rose agree).",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "European Central Bank: Press Conference — March 2026",
        "url": "https://www.ecb.europa.eu/press/pressconf/2026/html/ecb.is260306.en.html",
        "source": "ecb.europa.eu",
        "snippet": "The Governing Council decided to lower the three key ECB interest rates by 25 basis points.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Companies House: Apple Inc UK Ltd — Filing History",
        "url": "https://find-and-update.company-information.service.gov.uk/company/01234567/filing-history",
        "source": "company-information.service.gov.uk",
        "snippet": "Annual accounts filed 2025-12-31. Confirmation statement filed 2026-01-15.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Public Health England: Measles Surveillance Report",
        "url": "https://www.gov.uk/government/publications/measles-deaths-by-age-group-from-1980-to-2013-ons-data",
        "source": "gov.uk",
        "snippet": "Lab-confirmed measles cases in England: Quarter 4 2025. Total cases: 287. Age distribution attached.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Legislation.gov.uk: Climate Change Act 2008",
        "url": "https://www.legislation.gov.uk/ukpga/2008/27/contents",
        "source": "legislation.gov.uk",
        "snippet": "An Act to set a target for the year 2050 for the reduction of targeted greenhouse gas emissions.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Congressional Record: Senate Floor Debate on Infrastructure",
        "url": "https://www.congress.gov/congressional-record/2026/02/20/senate-section/article/S1234",
        "source": "congress.gov",
        "snippet": "Mr. SCHUMER. Mr. President, I rise today to discuss the critical infrastructure needs of our nation.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "GovInfo: Public Law 118-50 — CHIPS and Science Act",
        "url": "https://www.govinfo.gov/content/pkg/PLAW-118publ50/html/PLAW-118publ50.htm",
        "source": "govinfo.gov",
        "snippet": "An Act To provide for research and development, and for other purposes.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "NHS England: National Cancer Waiting Times",
        "url": "https://www.england.nhs.uk/statistics/statistical-work-areas/cancer-waiting-times/",
        "source": "england.nhs.uk",
        "snippet": "In December 2025, 76.3% of patients received their first cancer treatment within 62 days of GP referral.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Federal Reserve Press Release: FOMC Statement March 2026",
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260319a.htm",
        "source": "federalreserve.gov",
        "snippet": "The Committee decided to maintain the target range for the federal funds rate at 4-1/4 to 4-1/2 percent.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    # -- PRIMARY / ACADEMIC (items 30-39) ---------------------------------
    {
        "title": "Efficacy of mRNA vaccines against severe COVID-19 outcomes",
        "url": "https://pubmed.ncbi.nlm.nih.gov/38123456/",
        "source": "pubmed.ncbi.nlm.nih.gov",
        "snippet": "In this meta-analysis of 42 studies, mRNA vaccines demonstrated 91.3% effectiveness against hospitalisation.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "Climate tipping points reassessed using palaeoclimate data",
        "url": "https://www.nature.com/articles/s41586-025-08234-1",
        "source": "nature.com",
        "snippet": "Here we show that several key tipping elements have lower thresholds than previously estimated.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "The economic impact of artificial intelligence on labour markets",
        "url": "https://academic.oup.com/restud/article/2025/04/ai-labour/abc123",
        "source": "academic.oup.com",
        "snippet": "We find that AI adoption leads to a 12-23% productivity increase in affected sectors but displaces 8-14% of routine tasks.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "IPCC AR6 Synthesis Report: Summary for Policymakers",
        "url": "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_SPM.pdf",
        "source": "ipcc.ch",
        "snippet": "Human activities, principally through emissions of greenhouse gases, have unequivocally caused global warming.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "Semantic Scholar: Deep learning for protein structure prediction",
        "url": "https://api.semanticscholar.org/graph/v1/paper/abc123",
        "source": "semanticscholar.org",
        "snippet": "We present a method that predicts protein 3D structure with atomic accuracy from primary sequence alone.",
        "expected_tier": "primary",
        "expected_type": "academic",
        "external_source_provider": "Semantic Scholar",
    },
    {
        "title": "The Lancet: Global burden of disease study 2024",
        "url": "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(25)01234-5/fulltext",
        "source": "thelancet.com",
        "snippet": "The Global Burden of Disease study provides a comprehensive assessment of mortality and disability from major diseases.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "OpenAlex: Machine learning approaches for climate prediction",
        "url": "https://api.openalex.org/works/W4567890123",
        "source": "openalex.org",
        "snippet": "We review recent applications of machine learning to weather and climate prediction.",
        "expected_tier": "primary",
        "expected_type": "academic",
        "external_source_provider": "OpenAlex",
    },
    {
        "title": "JAMA: Effectiveness of booster vaccination in elderly patients",
        "url": "https://jamanetwork.com/journals/jama/fullarticle/2801234",
        "source": "jamanetwork.com",
        "snippet": "Among adults aged 65 years or older, receipt of an mRNA COVID-19 booster dose was associated with lower risk.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "Science: Rapid Antarctic ice sheet loss accelerating",
        "url": "https://www.science.org/doi/10.1126/science.abc1234",
        "source": "science.org",
        "snippet": "We find that Antarctic ice loss has tripled over the past decade, contributing 0.7mm per year to sea level rise.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    {
        "title": "JSTOR: The Political Economy of Trade Policy",
        "url": "https://www.jstor.org/stable/12345678",
        "source": "jstor.org",
        "snippet": "This paper examines the determinants of trade policy in advanced democracies.",
        "expected_tier": "primary",
        "expected_type": "academic",
    },
    # -- REPORTING / NEWS (items 40-64) -----------------------------------
    {
        "title": "UK inflation falls to 3% as food prices ease",
        "url": "https://www.bbc.co.uk/news/business-68123456",
        "source": "bbc.co.uk",
        "snippet": "UK inflation fell to 3.0% in January, down from 3.2% in December, driven by easing food prices.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Fed holds rates steady amid economic uncertainty",
        "url": "https://www.reuters.com/markets/us/fed-holds-rates-steady-2026-03-19-abc123",
        "source": "reuters.com",
        "snippet": "The Federal Reserve left interest rates unchanged on Wednesday, citing persistent inflation concerns.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Arsenal close in on Premier League title with win over Liverpool",
        "url": "https://www.bbc.co.uk/sport/football/68234567",
        "source": "bbc.co.uk",
        "snippet": "Arsenal moved five points clear at the top of the Premier League with a dominant 3-0 win over Liverpool.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "China's economic growth slows to 4.2% in Q4",
        "url": "https://www.ft.com/content/abc12345-def6-7890-ghij-klmnopqrstuv",
        "source": "ft.com",
        "snippet": "China's economy grew at its slowest pace in two years during the fourth quarter of 2025.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Immigration bill faces Lords revolt over asylum provisions",
        "url": "https://www.theguardian.com/uk-news/2026/mar/01/immigration-bill-lords-revolt",
        "source": "theguardian.com",
        "snippet": "Cross-party peers are threatening to defeat the government on key asylum provisions in the immigration bill.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Tesla announces $25,000 electric car for 2027",
        "url": "https://www.cnbc.com/2026/02/28/tesla-announces-25000-electric-car.html",
        "source": "cnbc.com",
        "snippet": "Tesla CEO Elon Musk unveiled plans for a $25,000 compact electric vehicle at the company's investor day.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "NHS waiting list hits new record of 8.1 million",
        "url": "https://www.bbc.co.uk/news/health-68345678",
        "source": "bbc.co.uk",
        "snippet": "The number of people waiting for NHS hospital treatment in England has reached a new record of 8.1 million.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "AP: Wildfire destroys 500 homes in California",
        "url": "https://apnews.com/article/california-wildfire-homes-destroyed-abc123",
        "source": "apnews.com",
        "snippet": "A fast-moving wildfire fueled by strong winds destroyed at least 500 homes in Southern California on Tuesday.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "EU agrees landmark AI regulation framework",
        "url": "https://www.reuters.com/technology/eu-ai-regulation-framework-2026-abc123",
        "source": "reuters.com",
        "snippet": "The European Union agreed on Tuesday to a comprehensive framework for regulating artificial intelligence.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Boeing workers vote to end strike after new deal",
        "url": "https://www.washingtonpost.com/business/2026/03/02/boeing-strike-end-deal/",
        "source": "washingtonpost.com",
        "snippet": "Boeing machinists voted overwhelmingly to accept a new contract, ending a six-week strike.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    # Non-wire-service news sources (these test the heuristic default fallthrough)
    {
        "title": "Inside the race to build quantum computers",
        "url": "https://www.wired.com/story/inside-race-build-quantum-computers/",
        "source": "wired.com",
        "snippet": "Three companies are leading the charge to build a practical quantum computer that can solve real-world problems.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Climate scientists warn of accelerating Arctic ice loss",
        "url": "https://www.independent.co.uk/climate-change/arctic-ice-loss-accelerating-b2456789.html",
        "source": "independent.co.uk",
        "snippet": "Leading climate scientists have issued a stark warning about the accelerating rate of Arctic sea ice loss.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Politico: EU trade deal negotiations stall over agriculture",
        "url": "https://www.politico.eu/article/eu-trade-deal-agriculture-stall/",
        "source": "politico.eu",
        "snippet": "Negotiations between the EU and Mercosur have stalled again over agricultural concessions.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "ProPublica investigation: Hospital pricing transparency failures",
        "url": "https://www.propublica.org/article/hospital-pricing-transparency-failures",
        "source": "propublica.org",
        "snippet": "Our analysis of 1,000 hospitals found that fewer than 25% comply with federal pricing transparency requirements.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Sky News: UK energy bills to rise by 6.4% in April",
        "url": "https://news.sky.com/story/uk-energy-bills-rise-april-2026-13456789",
        "source": "news.sky.com",
        "snippet": "Household energy bills will rise by 6.4% from April, Ofgem has confirmed, taking the typical annual bill to £1,738.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "ESPN: Liverpool complete record £90m transfer",
        "url": "https://www.espn.com/soccer/story/liverpool-record-transfer-abc123",
        "source": "espn.com",
        "snippet": "Liverpool have completed the signing of midfielder for a club-record fee of £90 million.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "The Atlantic: How AI is reshaping the legal profession",
        "url": "https://www.theatlantic.com/technology/archive/2026/02/ai-legal-profession/abc123/",
        "source": "theatlantic.com",
        "snippet": "Law firms are rapidly adopting AI tools that can review contracts, draft briefs, and predict case outcomes.",
        "expected_tier": "reporting",
        "expected_type": "analysis",
    },
    {
        "title": "Channel 4 News: Exclusive — leaked government report on NHS",
        "url": "https://www.channel4.com/news/exclusive-leaked-government-report-nhs",
        "source": "channel4.com",
        "snippet": "Channel 4 News has obtained a leaked government report showing NHS funding shortfalls of £12bn by 2028.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Investigate Europe: Tax havens cost EU €150bn per year",
        "url": "https://www.investigate-europe.eu/posts/tax-havens-eu-150bn",
        "source": "investigate-europe.eu",
        "snippet": "Our cross-border investigation found that EU member states lose approximately €150 billion annually to tax havens.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "The Economist: Japan's demographic time bomb",
        "url": "https://www.economist.com/asia/2026/02/15/japans-demographic-time-bomb",
        "source": "economist.com",
        "snippet": "Japan's population fell by 831,000 in 2025, the largest annual decline on record.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    # -- COMMENTARY / OPINION (items 65-79) -------------------------------
    {
        "title": "Opinion: The Bank of England is making a terrible mistake",
        "url": "https://www.ft.com/content/opinion-bank-england-mistake-abc123",
        "source": "ft.com",
        "snippet": "By keeping rates too high for too long, the Bank risks choking off the recovery before it has properly begun.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "The Guardian view on the immigration bill: a missed opportunity",
        "url": "https://www.theguardian.com/commentisfree/2026/feb/28/guardian-view-immigration-bill",
        "source": "theguardian.com",
        "snippet": "This editorial argues that the government's immigration bill fails to address the root causes of irregular migration.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Column: Why the Premier League needs a salary cap",
        "url": "https://www.bbc.co.uk/sport/football/columns/68456789",
        "source": "bbc.co.uk",
        "snippet": "The growing financial disparity between clubs is destroying competitive balance. A salary cap is the only solution.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Paul Krugman: The inflation scare was overblown",
        "url": "https://www.nytimes.com/2026/02/25/opinion/krugman-inflation-overblown.html",
        "source": "nytimes.com",
        "snippet": "The prophets of persistent inflation have been proven wrong, again. It's time to admit the Fed got it right.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Analysis: What the US election results mean for global trade",
        "url": "https://www.bbc.co.uk/news/world-us-analysis-68567890",
        "source": "bbc.co.uk",
        "snippet": "The election outcome will have profound implications for trade policy, alliances, and the global economic order.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Substack: The case for nuclear power in the UK",
        "url": "https://energyanalyst.substack.com/p/case-for-nuclear-power-uk",
        "source": "energyanalyst.substack.com",
        "snippet": "If the UK is serious about net zero, it needs to invest heavily in new nuclear capacity. Here's why.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Medium: Why remote work is here to stay",
        "url": "https://medium.com/@workplace-trends/why-remote-work-is-here-to-stay-abc123",
        "source": "medium.com",
        "snippet": "The data is clear: companies that force return-to-office are losing their best talent.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "IFS briefing note: Distributional impact of the Budget",
        "url": "https://ifs.org.uk/publications/distributional-impact-spring-budget-2026",
        "source": "ifs.org.uk",
        "snippet": "This analysis examines who gains and who loses from the measures announced in the Spring Budget 2026.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Chatham House: The future of UK-EU relations",
        "url": "https://www.chathamhouse.org/2026/02/future-uk-eu-relations",
        "source": "chathamhouse.org",
        "snippet": "This research paper explores three scenarios for the evolution of UK-EU relations over the next decade.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Blog: My experience with the NHS mental health crisis",
        "url": "https://mentalhealthblogger.wordpress.com/2026/02/28/nhs-mental-health-crisis",
        "source": "wordpress.com",
        "snippet": "After waiting 18 months for therapy on the NHS, I want to share my experience and call for better funding.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Brookings: AI regulation — lessons from the EU approach",
        "url": "https://www.brookings.edu/articles/ai-regulation-lessons-eu-approach/",
        "source": "brookings.edu",
        "snippet": "The EU AI Act offers valuable lessons for US policymakers considering their own regulatory framework.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Op-ed: It's time to ban private jets",
        "url": "https://www.washingtonpost.com/opinions/2026/03/01/ban-private-jets-climate/",
        "source": "washingtonpost.com",
        "snippet": "While ordinary citizens are asked to reduce their carbon footprint, the ultra-wealthy fly in private jets.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "The Spectator: Why net zero is a fantasy",
        "url": "https://www.spectator.co.uk/article/why-net-zero-is-a-fantasy/",
        "source": "spectator.co.uk",
        "snippet": "The government's net zero targets are unachievable without either nuclear expansion or economic contraction.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "RAND Corporation: Military AI capabilities assessment",
        "url": "https://www.rand.org/pubs/research_reports/RR-A1234-1.html",
        "source": "rand.org",
        "snippet": "This report assesses the current state of AI capabilities in military applications across NATO nations.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "The Conversation: Why university tuition fees should be scrapped",
        "url": "https://theconversation.com/why-university-tuition-fees-should-be-scrapped-234567",
        "source": "theconversation.com",
        "snippet": "As an education policy researcher, I argue that the current tuition fee system creates inequality.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    # -- EDGE CASES / TRICKY ITEMS (items 80-99) -------------------------
    {
        "title": "Wikipedia: Climate change",
        "url": "https://en.wikipedia.org/wiki/Climate_change",
        "source": "wikipedia.org",
        "snippet": "In common usage, climate change describes global warming—the ongoing increase in global average temperature.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Internet Archive: Wayback Machine capture of deleted government page",
        "url": "https://web.archive.org/web/20250615/https://www.gov.uk/deleted-policy",
        "source": "web.archive.org",
        "snippet": "Archived copy of government policy document that has since been removed from the official website.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "Library of Congress: Newspaper archives — Chicago Tribune 1942",
        "url": "https://chroniclingamerica.loc.gov/lccn/sn83045396/1942-12-08/ed-1/",
        "source": "chroniclingamerica.loc.gov",
        "snippet": "Historical newspaper page from the Chicago Tribune, December 8, 1942.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "Reddit: Discussion about UK energy prices",
        "url": "https://www.reddit.com/r/UKPersonalFinance/comments/abc123/energy_prices_going_up/",
        "source": "reddit.com",
        "snippet": "Just got my new energy bill — it's gone up 15% since last quarter. Anyone else seeing similar increases?",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "Twitter/X: Official WHO announcement",
        "url": "https://x.com/WHO/status/1234567890",
        "source": "x.com",
        "snippet": "WHO announces updated guidelines for COVID-19 vaccination in 2026.",
        "expected_tier": "primary",
        "expected_type": "official_statement",
    },
    {
        "title": "FactCheck.org: Biden's claim about job creation",
        "url": "https://www.factcheck.org/2026/02/bidens-misleading-job-creation-claim/",
        "source": "factcheck.org",
        "snippet": "The president's claim that 'we've created 15 million jobs' omits important context about pandemic recovery.",
        "expected_tier": "reporting",
        "expected_type": "analysis",
        "is_factcheck": True,
    },
    {
        "title": "ClinicalTrials.gov: Phase 3 Study of New Alzheimer's Drug",
        "url": "https://clinicaltrials.gov/ct2/show/NCT05678901",
        "source": "clinicaltrials.gov",
        "snippet": "A Phase 3, Randomized, Double-Blind Study to Evaluate the Efficacy and Safety of Drug X in Alzheimer's.",
        "expected_tier": "primary",
        "expected_type": "data",
    },
    {
        "title": "TechCrunch: Startup raises $500M for AI drug discovery",
        "url": "https://techcrunch.com/2026/02/27/startup-raises-500m-ai-drug-discovery/",
        "source": "techcrunch.com",
        "snippet": "AI-powered drug discovery startup has raised $500 million in Series D funding led by Andreessen Horowitz.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "ONS: Population estimates, mid-2025",
        "url": "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates",
        "source": "ons.gov.uk",
        "snippet": "The population of England and Wales was estimated to be 60.9 million in mid-2025.",
        "expected_tier": "primary",
        "expected_type": "data",
        "external_source_provider": "ONS Economic Statistics",
    },
    {
        "title": "Full Fact: Is the NHS really in crisis?",
        "url": "https://fullfact.org/health/nhs-crisis-2026/",
        "source": "fullfact.org",
        "snippet": "Claims about the NHS being 'in crisis' need context. Here's what the data actually shows.",
        "expected_tier": "reporting",
        "expected_type": "analysis",
    },
    {
        "title": "YouTube: Climate scientist explains tipping points",
        "url": "https://www.youtube.com/watch?v=abc123def456",
        "source": "youtube.com",
        "snippet": "Professor explains the latest research on climate tipping points and what they mean for the planet.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "Forbes: The billionaires getting richer from AI",
        "url": "https://www.forbes.com/sites/ai-billionaires-richer-2026/",
        "source": "forbes.com",
        "snippet": "Tech billionaires have seen their wealth increase by an average of $12 billion in 2025 thanks to AI investments.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "NPR: What the new trade tariffs mean for consumers",
        "url": "https://www.npr.org/2026/03/01/new-trade-tariffs-consumers",
        "source": "npr.org",
        "snippet": "The newly announced tariffs on Chinese imports will likely raise prices on electronics and clothing.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Al Jazeera: Flooding displaces millions in Bangladesh",
        "url": "https://www.aljazeera.com/news/2026/2/28/flooding-displaces-millions-bangladesh",
        "source": "aljazeera.com",
        "snippet": "Severe flooding has displaced an estimated 3.2 million people in southeastern Bangladesh.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Vox: Explainer — what is the debt ceiling and why does it matter?",
        "url": "https://www.vox.com/policy/2026/3/1/debt-ceiling-explainer",
        "source": "vox.com",
        "snippet": "The debt ceiling is the maximum amount the US government can borrow. Here's why it matters.",
        "expected_tier": "commentary",
        "expected_type": "analysis",
    },
    {
        "title": "BBC News: Breaking — earthquake strikes central Turkey",
        "url": "https://www.bbc.co.uk/news/world-europe-68678901",
        "source": "bbc.co.uk",
        "snippet": "A magnitude 6.4 earthquake has struck central Turkey, with reports of buildings collapsing.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "New Statesman: Labour's broken promises on housing",
        "url": "https://www.newstatesman.com/politics/2026/03/labours-broken-promises-housing",
        "source": "newstatesman.com",
        "snippet": "Labour pledged 300,000 new homes a year. Two years in, they're building fewer than the Conservatives managed.",
        "expected_tier": "commentary",
        "expected_type": "opinion",
    },
    {
        "title": "CarbonBrief: Analysis — global CO2 emissions in 2025",
        "url": "https://www.carbonbrief.org/analysis-global-co2-emissions-2025",
        "source": "carbonbrief.org",
        "snippet": "Global CO2 emissions reached a new record high of 37.4 billion tonnes in 2025, a 0.8% increase on 2024.",
        "expected_tier": "reporting",
        "expected_type": "analysis",
    },
    {
        "title": "Sky Sports: Match report — Arsenal 3-0 Liverpool",
        "url": "https://www.skysports.com/football/arsenal-vs-liverpool/report/234567",
        "source": "skysports.com",
        "snippet": "Arsenal produced a dominant display to beat Liverpool 3-0 at the Emirates and extend their lead.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
    {
        "title": "Bellingcat: Satellite imagery reveals new military buildup",
        "url": "https://www.bellingcat.com/news/2026/03/01/satellite-imagery-military-buildup/",
        "source": "bellingcat.com",
        "snippet": "New satellite imagery obtained by Bellingcat shows a significant military equipment buildup near the border.",
        "expected_tier": "reporting",
        "expected_type": "news_reporting",
    },
]

assert len(EVIDENCE_CORPUS) >= 90, f"Expected ~100 items, got {len(EVIDENCE_CORPUS)}"


# -- Analysis functions ---------------------------------------------------


def run_heuristic_analysis():
    """Run heuristic classifier on all 100 items and compare to expected."""
    results = []

    for i, item in enumerate(EVIDENCE_CORPUS):
        h_tier, h_type = _classify_heuristic(item)
        expected_tier = item["expected_tier"]
        expected_type = item["expected_type"]

        results.append(
            {
                "index": i,
                "title": item["title"][:60],
                "url_domain": item.get("source", "")[:25],
                "expected_tier": expected_tier,
                "expected_type": expected_type,
                "heuristic_tier": h_tier,
                "heuristic_type": h_type,
                "tier_match": h_tier == expected_tier,
                "type_match": h_type == expected_type,
                "both_match": h_tier == expected_tier and h_type == expected_type,
            }
        )

    return results


def print_heuristic_report(results):
    """Print detailed heuristic accuracy report."""
    total = len(results)
    tier_correct = sum(1 for r in results if r["tier_match"])
    type_correct = sum(1 for r in results if r["type_match"])
    both_correct = sum(1 for r in results if r["both_match"])

    print("\n" + "=" * 80)
    print("PQ-08 MEASUREMENT: Heuristic vs Ground Truth Classification")
    print("=" * 80)

    print(f"\n{'Metric':<35} {'Score':>8} {'Rate':>8}")
    print("-" * 55)
    print(
        f"{'Tier correct':<35} {tier_correct:>5}/{total:<3} {tier_correct/total*100:>6.1f}%"
    )
    print(
        f"{'Type correct':<35} {type_correct:>5}/{total:<3} {type_correct/total*100:>6.1f}%"
    )
    print(
        f"{'Both correct':<35} {both_correct:>5}/{total:<3} {both_correct/total*100:>6.1f}%"
    )

    # Tier confusion matrix
    print(f"\n{'-' * 55}")
    print("TIER CONFUSION MATRIX (rows=expected, cols=heuristic)")
    print(f"{'-' * 55}")
    tiers = ["primary", "reporting", "commentary"]
    tier_matrix = {e: {h: 0 for h in tiers} for e in tiers}
    for r in results:
        tier_matrix[r["expected_tier"]][r["heuristic_tier"]] += 1

    print(f"{'':>15} {'primary':>12} {'reporting':>12} {'commentary':>12}")
    for expected in tiers:
        row = f"{expected:>15}"
        for heuristic in tiers:
            count = tier_matrix[expected][heuristic]
            row += f" {count:>11}"
        print(row)

    # Type confusion matrix
    print(f"\n{'-' * 70}")
    print("TYPE CONFUSION MATRIX (rows=expected, cols=heuristic)")
    print(f"{'-' * 70}")
    types = [
        "data",
        "official_statement",
        "news_reporting",
        "analysis",
        "opinion",
        "academic",
    ]
    type_matrix = {e: {h: 0 for h in types} for e in types}
    for r in results:
        type_matrix[r["expected_type"]][r["heuristic_type"]] += 1

    abbrev = {
        "data": "data",
        "official_statement": "official",
        "news_reporting": "news",
        "analysis": "analysis",
        "opinion": "opinion",
        "academic": "academic",
    }
    print(f"{'':>12}", end="")
    for t in types:
        print(f" {abbrev[t]:>9}", end="")
    print()
    for expected in types:
        print(f"{abbrev[expected]:>12}", end="")
        for heuristic in types:
            count = type_matrix[expected][heuristic]
            print(f" {count:>9}", end="")
        print()

    # Misclassifications detail
    misses = [r for r in results if not r["both_match"]]
    print(f"\n{'-' * 80}")
    print(f"MISCLASSIFICATIONS ({len(misses)} items)")
    print(f"{'-' * 80}")
    for r in misses:
        exp = f"{r['expected_tier']}/{r['expected_type']}"
        got = f"{r['heuristic_tier']}/{r['heuristic_type']}"
        mark_t = "" if r["tier_match"] else " [TIER]"
        mark_y = "" if r["type_match"] else " [TYPE]"
        print(f"  [{r['index']:>2}] {r['title']:<55}")
        print(f"       Expected: {exp:<30}  Got: {got}{mark_t}{mark_y}")

    # Default fallthrough analysis
    defaults = [
        r
        for r in results
        if r["heuristic_tier"] == "commentary"
        and r["heuristic_type"] == "news_reporting"
    ]
    expected_defaults = [
        r
        for r in defaults
        if r["expected_tier"] == "commentary" and r["expected_type"] == "news_reporting"
    ]
    print(f"\n{'-' * 55}")
    print("DEFAULT FALLTHROUGH ANALYSIS")
    print(f"{'-' * 55}")
    print(f"Items hitting default (commentary/news_reporting): {len(defaults)}")
    print(
        f"  Of which correctly classified:                    {len(expected_defaults)}"
    )
    print(
        f"  Of which INCORRECTLY classified (masked):         {len(defaults) - len(expected_defaults)}"
    )
    if defaults:
        print(
            f"  Default fallthrough rate:                         {len(defaults)/total*100:.1f}%"
        )
        if len(defaults) > len(expected_defaults):
            print(
                f"\n  Masked misclassifications (should NOT be commentary/news_reporting):"
            )
            for r in defaults:
                if not (
                    r["expected_tier"] == "commentary"
                    and r["expected_type"] == "news_reporting"
                ):
                    exp = f"{r['expected_tier']}/{r['expected_type']}"
                    print(f"    [{r['index']:>2}] {r['title']:<55} (expected: {exp})")


async def run_llm_comparison(results):
    """Run LLM classifier on all items and compare with heuristic."""
    classifier = EvidenceClassifier()

    # Classify all 100 items with LLM
    items_for_llm = []
    for item in EVIDENCE_CORPUS:
        items_for_llm.append(
            {
                "title": item["title"],
                "url": item["url"],
                "source": item.get("source", ""),
                "snippet": item.get("snippet", ""),
                "external_source_provider": item.get("external_source_provider"),
                "is_factcheck": item.get("is_factcheck"),
            }
        )

    classified = await classifier.classify_batch(items_for_llm)

    # Compare
    llm_results = []
    for i, (item, classified_item) in enumerate(zip(EVIDENCE_CORPUS, classified)):
        h_tier, h_type = _classify_heuristic(item)
        l_tier = classified_item.get("tier", "unknown")
        l_type = classified_item.get("evidence_type", "unknown")

        llm_results.append(
            {
                "index": i,
                "title": item["title"][:55],
                "expected_tier": item["expected_tier"],
                "expected_type": item["expected_type"],
                "heuristic_tier": h_tier,
                "heuristic_type": h_type,
                "llm_tier": l_tier,
                "llm_type": l_type,
                "h_tier_correct": h_tier == item["expected_tier"],
                "l_tier_correct": l_tier == item["expected_tier"],
                "h_type_correct": h_type == item["expected_type"],
                "l_type_correct": l_type == item["expected_type"],
                "h_both_correct": h_tier == item["expected_tier"]
                and h_type == item["expected_type"],
                "l_both_correct": l_tier == item["expected_tier"]
                and l_type == item["expected_type"],
                "h_l_tier_agree": h_tier == l_tier,
                "h_l_type_agree": h_type == l_type,
            }
        )

    # Print comparison
    total = len(llm_results)
    print("\n" + "=" * 80)
    print("PQ-08 MEASUREMENT: Heuristic vs LLM vs Ground Truth")
    print("=" * 80)

    h_tier_acc = sum(1 for r in llm_results if r["h_tier_correct"])
    l_tier_acc = sum(1 for r in llm_results if r["l_tier_correct"])
    h_type_acc = sum(1 for r in llm_results if r["h_type_correct"])
    l_type_acc = sum(1 for r in llm_results if r["l_type_correct"])
    h_both_acc = sum(1 for r in llm_results if r["h_both_correct"])
    l_both_acc = sum(1 for r in llm_results if r["l_both_correct"])
    agree_tier = sum(1 for r in llm_results if r["h_l_tier_agree"])
    agree_type = sum(1 for r in llm_results if r["h_l_type_agree"])

    print(f"\n{'Metric':<35} {'Heuristic':>12} {'LLM':>12} {'Gap':>10}")
    print("-" * 72)
    print(
        f"{'Tier accuracy':<35} {h_tier_acc/total*100:>10.1f}% {l_tier_acc/total*100:>10.1f}% {(l_tier_acc-h_tier_acc)/total*100:>+9.1f}%"
    )
    print(
        f"{'Type accuracy':<35} {h_type_acc/total*100:>10.1f}% {l_type_acc/total*100:>10.1f}% {(l_type_acc-h_type_acc)/total*100:>+9.1f}%"
    )
    print(
        f"{'Both correct':<35} {h_both_acc/total*100:>10.1f}% {l_both_acc/total*100:>10.1f}% {(l_both_acc-h_both_acc)/total*100:>+9.1f}%"
    )
    print(f"\n{'Heuristic-LLM agreement (tier)':<35} {agree_tier/total*100:>10.1f}%")
    print(f"{'Heuristic-LLM agreement (type)':<35} {agree_type/total*100:>10.1f}%")

    # Where LLM wins and heuristic loses
    llm_wins = [
        r for r in llm_results if r["l_both_correct"] and not r["h_both_correct"]
    ]
    h_wins = [r for r in llm_results if r["h_both_correct"] and not r["l_both_correct"]]

    print(f"\n{'-' * 80}")
    print(f"LLM correct, heuristic wrong: {len(llm_wins)} items")
    for r in llm_wins[:15]:
        print(f"  [{r['index']:>2}] {r['title']}")
        print(
            f"       H: {r['heuristic_tier']}/{r['heuristic_type']}  L: {r['llm_tier']}/{r['llm_type']}  Expected: {r['expected_tier']}/{r['expected_type']}"
        )

    print(f"\nHeuristic correct, LLM wrong: {len(h_wins)} items")
    for r in h_wins[:10]:
        print(f"  [{r['index']:>2}] {r['title']}")
        print(
            f"       H: {r['heuristic_tier']}/{r['heuristic_type']}  L: {r['llm_tier']}/{r['llm_type']}  Expected: {r['expected_tier']}/{r['expected_type']}"
        )

    usage = classifier.get_token_usage()
    print(
        f"\nLLM token usage: {usage['input_tokens']:,} input + {usage['output_tokens']:,} output"
    )

    return llm_results


def main():
    heuristic_only = "--heuristic-only" in sys.argv

    # Always run heuristic analysis
    results = run_heuristic_analysis()
    print_heuristic_report(results)

    if not heuristic_only:
        print(
            "\n\nRunning LLM comparison (requires GOOGLE_AI_API_KEY or OPENAI_API_KEY)..."
        )
        llm_results = asyncio.run(run_llm_comparison(results))

        # Save results
        output_path = (
            Path(__file__).parent.parent / "data" / "pq08_classifier_comparison.json"
        )
        with open(output_path, "w") as f:
            json.dump(llm_results, f, indent=2)
        print(f"\nResults saved to {output_path}")
    else:
        print(
            "\n\n(Skipping LLM comparison — run without --heuristic-only for full analysis)"
        )


if __name__ == "__main__":
    main()
