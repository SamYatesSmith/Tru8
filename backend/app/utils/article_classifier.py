"""
Article Classifier Module

LLM-based article-level classification that runs once per check,
replacing per-claim spaCy NER domain detection.

Architecture:
1. URL pattern cache (instant, permanent)
2. URL-specific cache (Redis, 24h TTL)
3. Primary LLM (gpt-4o-mini)
4. Fallback LLM (placeholder for future)
5. "General" domain fallback
"""

import re
import json
import logging
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import timedelta

from app.core.config import settings
from app.services.google_ai import call_google_ai

logger = logging.getLogger(__name__)

# Cache TTL for URL-specific classifications
CLASSIFICATION_CACHE_TTL = timedelta(hours=24)


@dataclass
class ArticleClassification:
    """Article classification result with dynamic context for evidence retrieval"""

    primary_domain: str  # Sports, Politics, Finance, etc.
    secondary_domains: List[str]  # For cross-domain articles
    jurisdiction: str  # UK, US, EU, Global
    confidence: int  # 0-100
    reasoning: str  # LLM explanation
    source: str  # "cache_pattern", "cache_url", "llm_primary", "llm_fallback", "fallback_general"

    # Dynamic context for evidence retrieval (Phase: Dynamic Context-Aware)
    temporal_context: str = ""  # "December 2024, mid-season Premier League"
    key_entities: List[str] = None  # ["Arsenal", "Chelsea", "Premier League"]
    evidence_guidance: str = ""  # "League standings change weekly after each matchweek"
    classification_failed: bool = (
        False  # True when all LLM methods failed, using fallback
    )

    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.key_entities is None:
            self.key_entities = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArticleClassification":
        """Create from dictionary"""
        return cls(
            primary_domain=data.get("primary_domain", "General"),
            secondary_domains=data.get("secondary_domains", []),
            jurisdiction=data.get("jurisdiction", "Global"),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", ""),
            source=data.get("source", "unknown"),
            temporal_context=data.get("temporal_context", ""),
            key_entities=data.get("key_entities", []),
            evidence_guidance=data.get("evidence_guidance", ""),
            classification_failed=data.get("classification_failed", False),
        )


# Valid domain categories (match existing API adapters)
VALID_DOMAINS = [
    "Sports",
    "Politics",
    "Finance",
    "Health",
    "Science",
    "Law",
    "Climate",
    "Weather",
    "Demographics",
    "Entertainment",
    "Animals",
    "History",
    "General",
]

# Valid jurisdictions
VALID_JURISDICTIONS = ["UK", "US", "EU", "Global"]


def detect_jurisdiction_from_text(text: str) -> str:
    """Lightweight keyword-based jurisdiction detection for focused mode.

    Scans claim text for geographic indicators. Returns one of:
    UK, US, EU, Global. Defaults to Global (no country filter) when
    no clear geographic signal is found.

    No LLM call — pure keyword matching.
    """
    # Pad with spaces so boundary-aware patterns like " uk " match at start/end
    text_lower = f" {text.lower()} "

    us_patterns = [
        "united states",
        "u.s.",
        "u.s.a.",
        "usa ",
        "american ",
        "americans",
        " congress ",
        "senate ",
        "house of representatives",
        "white house",
        "pentagon",
        "capitol hill",
        "federal reserve",
        " the fed ",
        " fbi ",
        " cia ",
        " nsa ",
        "democrat",
        "republican",
        " gop ",
        "california",
        "texas",
        "new york",
        "florida",
        "washington dc",
        "washington d.c.",
        "medicare",
        "medicaid",
        "social security",
        " fda ",
        " cdc ",
        " epa ",
    ]

    uk_patterns = [
        "united kingdom",
        "u.k.",
        " uk ",
        "britain",
        "british",
        "england",
        "english",
        "scotland",
        "scottish",
        "wales",
        "welsh",
        "northern ireland",
        "parliament",
        "house of commons",
        "house of lords",
        "westminster",
        "downing street",
        "whitehall",
        " nhs ",
        "bank of england",
        "labour party",
        "conservative party",
        "tory",
        "tories",
        "ofsted",
        "ofcom",
        "premier league",
    ]

    eu_patterns = [
        "european union",
        " eu ",
        " eu,",
        " eu.",
        "european commission",
        "european parliament",
        "european council",
        "eurozone",
        "schengen",
        "brussels",
        "strasbourg",
        " gdpr",
        " euro ",
        "europe",
        "european",
        "france",
        "french",
        "germany",
        "german",
        "italy",
        "italian",
        "spain",
        "spanish",
        "netherlands",
        "dutch",
        "belgium",
        "belgian",
        "portugal",
        "portuguese",
        "greece",
        "greek",
        "poland",
        "polish",
        "sweden",
        "swedish",
        "denmark",
        "danish",
        "austria",
        "austrian",
    ]

    us_score = sum(1 for p in us_patterns if p in text_lower)
    uk_score = sum(1 for p in uk_patterns if p in text_lower)
    eu_score = sum(1 for p in eu_patterns if p in text_lower)

    max_score = max(us_score, uk_score, eu_score)
    if max_score == 0:
        return "Global"

    if us_score > uk_score and us_score > eu_score:
        return "US"
    elif uk_score > us_score and uk_score > eu_score:
        return "UK"
    elif eu_score > us_score and eu_score > uk_score:
        return "EU"
    else:
        return "Global"


# URL Pattern Cache (permanent, in-memory)
# IMPORTANT: More specific patterns MUST come BEFORE more general patterns!
# e.g., ons.gov.uk (Finance) must come before gov.uk (Politics)
URL_PATTERN_CACHE = [
    # ==================== SPECIFIC .GOV.UK SUBDOMAINS ====================
    # These MUST come before the generic gov.uk pattern
    (r".*ons\.gov\.uk.*", "Finance", "UK"),  # Office for National Statistics
    (r".*metoffice\.gov\.uk.*", "Climate", "UK"),  # Met Office weather
    (r".*legislation\.gov\.uk.*", "Law", "UK"),  # UK Legislation
    # ==================== SPORTS ====================
    (r".*bbc\.co\.uk/sport.*", "Sports", "UK"),
    (r".*bbc\.com/sport.*", "Sports", "UK"),
    (r".*skysports\.com.*", "Sports", "UK"),
    (r".*espn\.com.*", "Sports", "US"),
    (r".*espn\.co\.uk.*", "Sports", "UK"),
    (r".*theathletic\.com.*", "Sports", "Global"),
    (r".*transfermarkt\.(com|co\.uk).*", "Sports", "Global"),
    (r".*goal\.com.*", "Sports", "Global"),
    (r".*90min\.com.*", "Sports", "Global"),
    (r".*football-data\.co\.uk.*", "Sports", "UK"),
    (r".*premierleague\.com.*", "Sports", "UK"),
    (r".*football365\.com.*", "Sports", "UK"),
    (r".*fourfourtwo\.com.*", "Sports", "UK"),
    (r".*football-talk\.co\.uk.*", "Sports", "UK"),  # Football aggregator
    # ==================== POLITICS ====================
    (r".*bbc\.co\.uk/news/politics.*", "Politics", "UK"),
    (r".*bbc\.co\.uk/news/uk-politics.*", "Politics", "UK"),
    (r".*theguardian\.com/politics.*", "Politics", "UK"),
    (r".*politico\.(com|eu).*", "Politics", "Global"),
    (r".*parliament\.uk.*", "Politics", "UK"),
    (r".*congress\.gov.*", "Politics", "US"),
    (r".*whitehouse\.gov.*", "Politics", "US"),
    (
        r".*gov\.uk.*",
        "Politics",
        "UK",
    ),  # Generic gov.uk - MUST be AFTER specific subdomains
    # ==================== HEALTH ====================
    (r".*bbc\.co\.uk/news/health.*", "Health", "UK"),
    (r".*nhs\.uk.*", "Health", "UK"),
    (r".*who\.int.*", "Health", "Global"),
    (r".*cdc\.gov.*", "Health", "US"),
    (r".*pubmed\.ncbi\.nlm\.nih\.gov.*", "Health", "Global"),
    (r".*thelancet\.com.*", "Health", "Global"),
    (r".*bmj\.com.*", "Health", "UK"),
    # ==================== SCIENCE ====================
    (r".*bbc\.co\.uk/news/science.*", "Science", "UK"),
    (r".*nature\.com.*", "Science", "Global"),
    (r".*sciencemag\.org.*", "Science", "Global"),
    (r".*scientificamerican\.com.*", "Science", "US"),
    (r".*newscientist\.com.*", "Science", "UK"),
    (r".*arxiv\.org.*", "Science", "Global"),
    # ==================== FINANCE ====================
    (r".*ft\.com.*", "Finance", "Global"),
    (r".*bloomberg\.com.*", "Finance", "Global"),
    (r".*reuters\.com/business.*", "Finance", "Global"),
    (r".*wsj\.com.*", "Finance", "US"),
    (r".*economist\.com.*", "Finance", "Global"),
    (r".*bbc\.co\.uk/news/business.*", "Finance", "UK"),
    # ==================== CLIMATE ====================
    (r".*bbc\.co\.uk/news/science.*environment.*", "Climate", "UK"),
    (r".*noaa\.gov.*", "Climate", "US"),
    (r".*ipcc\.ch.*", "Climate", "Global"),
    # UK Climate Research Institutions
    (r".*ncas\.ac\.uk.*", "Climate", "UK"),  # National Centre for Atmospheric Science
    (r".*metoffice\.gov\.uk.*", "Climate", "UK"),  # Met Office (duplicate for safety)
    (r".*carbonbrief\.org.*", "Climate", "UK"),  # Carbon Brief
    (r".*climate\.gov.*", "Climate", "US"),  # NOAA Climate
    (r".*nasa\.gov.*climate.*", "Climate", "US"),  # NASA Climate
    (r".*copernicus\.eu.*climate.*", "Climate", "Global"),  # Copernicus Climate
    # ==================== ANIMALS ====================
    # Biodiversity & Conservation
    (r".*gbif\.org.*", "Animals", "Global"),
    (r".*iucnredlist\.org.*", "Animals", "Global"),
    (r".*iucn\.org.*", "Animals", "Global"),
    (r".*worldwildlife\.org.*", "Animals", "Global"),
    (r".*wwf\.panda\.org.*", "Animals", "Global"),
    # Pet & Veterinary
    (r".*aspca\.org.*", "Animals", "US"),
    (r".*akc\.org.*", "Animals", "US"),
    (r".*petmd\.com.*", "Animals", "Global"),
    (r".*merckvetmanual\.com.*", "Animals", "Global"),
    (r".*vcahospitals\.com.*", "Animals", "Global"),
    (r".*rspca\.org\.uk.*", "Animals", "UK"),
    (r".*pdsa\.org\.uk.*", "Animals", "UK"),
    (r".*thekennelclub\.org\.uk.*", "Animals", "UK"),
    # Zoos & Wildlife
    (r".*animaldiversity\.org.*", "Animals", "Global"),
    (r".*nationalzoo\.si\.edu.*", "Animals", "US"),
    (r".*sandiegozoo\.org.*", "Animals", "US"),
    (r".*zsl\.org.*", "Animals", "UK"),
    # ==================== HISTORY ====================
    # National Archives
    (r".*nationalarchives\.gov\.uk.*", "History", "UK"),
    (r".*archives\.gov.*", "History", "US"),
    (r".*bac-lac\.gc\.ca.*", "History", "Global"),
    (r".*naa\.gov\.au.*", "History", "Global"),
    # National Libraries
    (r".*loc\.gov.*", "History", "US"),
    (r".*bl\.uk.*", "History", "UK"),
    (r".*bnf\.fr.*", "History", "Global"),
    (r".*europeana\.eu.*", "History", "EU"),
    (r".*gallica\.bnf\.fr.*", "History", "Global"),
    # Major Museums
    (r".*si\.edu.*", "History", "US"),
    (r".*americanhistory\.si\.edu.*", "History", "US"),
    (r".*britishmuseum\.org.*", "History", "UK"),
    (r".*vam\.ac\.uk.*", "History", "UK"),
    (r".*metmuseum\.org.*", "History", "US"),
    # War & Military
    (r".*iwm\.org\.uk.*", "History", "UK"),
    (r".*nationalww2museum\.org.*", "History", "US"),
    (r".*ushmm\.org.*", "History", "Global"),
    (r".*yadvashem\.org.*", "History", "Global"),
    (r".*awm\.gov\.au.*", "History", "Global"),
    # Heritage Organizations
    (r".*historicengland\.org\.uk.*", "History", "UK"),
    (r".*english-heritage\.org\.uk.*", "History", "UK"),
    (r".*nationaltrust\.org\.uk.*", "History", "UK"),
    # Historical Societies
    (r".*history\.ac\.uk.*", "History", "UK"),
    (r".*historians\.org.*", "History", "US"),
    (r".*royalhistsoc\.org.*", "History", "UK"),
    # Genealogy
    (r".*familysearch\.org.*", "History", "Global"),
    (r".*ancestry\.(com|co\.uk).*", "History", "Global"),
    # Historical Reference
    (r".*oxforddnb\.com.*", "History", "UK"),
    (r".*historytoday\.com.*", "History", "Global"),
    # ==================== LAW ====================
    (r".*courtlistener\.com.*", "Law", "US"),
    (r".*caselaw\.findlaw\.com.*", "Law", "US"),
    (r".*bailii\.org.*", "Law", "UK"),
    (r".*supremecourt\.gov.*", "Law", "US"),
    (r".*judiciary\.uk.*", "Law", "UK"),
]


def _get_cache_key(url: str) -> str:
    """Generate cache key for URL"""
    # Normalize URL and hash it
    normalized = url.lower().strip()
    return f"article_class:{hashlib.md5(normalized.encode()).hexdigest()}"


async def get_cached_classification(url: str) -> Optional[ArticleClassification]:
    """Get classification from Redis cache"""
    if not url or not url.strip():
        return None  # No URL = no article identity to cache against

    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is None:
            return None

        cache_key = _get_cache_key(url)
        cached = await redis.get(cache_key)

        if cached:
            data = json.loads(cached)
            classification = ArticleClassification.from_dict(data)
            classification.source = "cache_url"  # Override source to indicate cache hit
            logger.debug(f"Cache hit for URL classification: {url[:50]}...")
            return classification

        return None
    except Exception as e:
        logger.warning(f"Failed to get cached classification: {e}")
        return None


async def cache_classification(url: str, classification: ArticleClassification) -> None:
    """Cache classification in Redis with 24h TTL"""
    if not url or not url.strip():
        return  # Don't cache empty-URL classifications — they'd collide

    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is None:
            return

        cache_key = _get_cache_key(url)
        data = json.dumps(classification.to_dict())
        await redis.setex(cache_key, CLASSIFICATION_CACHE_TTL, data)
        logger.debug(f"Cached classification for URL: {url[:50]}...")
    except Exception as e:
        logger.warning(f"Failed to cache classification: {e}")


def _check_url_pattern_cache(url: str) -> Optional[ArticleClassification]:
    """Check URL against pattern cache for instant classification"""
    if not url:
        return None

    url_lower = url.lower()

    for pattern, domain, jurisdiction in URL_PATTERN_CACHE:
        if re.match(pattern, url_lower):
            return ArticleClassification(
                primary_domain=domain,
                secondary_domains=[],
                jurisdiction=jurisdiction,
                confidence=95,
                reasoning=f"Matched URL pattern for {domain} content",
                source="cache_pattern",
                temporal_context="",  # Will be populated by LLM if cache miss
                key_entities=[],
                evidence_guidance="",
            )

    return None


# LLM Classification prompt template
CLASSIFICATION_PROMPT = """You are a Tru8 fact-checking specialist specializing in content classification.

CURRENT DATE CONTEXT:
Today's date is {current_date} (Year: {current_year}).
Use this to understand the temporal context of the article.

TASK:
Analyze this article and classify it for fact-checking evidence retrieval.

Article Title: {title}
Article URL: {url}
Article Preview:
{content}

DOMAIN CATEGORIES:
Classify this article into exactly ONE primary domain from this list:
- Sports (athletics, football, basketball, any competitive games)
- Politics (government, elections, policy, legislation, international relations)
- Finance (economics, markets, business, trade, employment, GDP)
- Health (medicine, diseases, healthcare, wellness, medical research)
- Science (research, technology, physics, chemistry, biology, space)
- Law (legal cases, court rulings, regulations, legal analysis)
- Climate (environment, global warming, emissions, climate science)
- Weather (meteorology, forecasts, storms, atmospheric conditions)
- Demographics (population, census, migration, social statistics)
- Animals (wildlife, pets, species, conservation, veterinary, biodiversity)
- History (historical events, archives, museums, heritage, genealogy)
- Entertainment (movies, music, celebrities, arts, culture)
- General (if none of the above clearly fit)

ALSO IDENTIFY:
1. Any secondary domains (max 2) if the article crosses topics
2. Geographic jurisdiction: UK, US, EU, or Global
3. Temporal context: What time period does this article cover?
4. Key entities: Main people, organizations, or things mentioned (max 10)
5. Evidence guidance: What freshness and source types are needed to verify claims in this article?

JURISDICTION DETECTION PRIORITY (apply in order, highest first):
1. Explicit country / region named in the claim ("the UK", "United Kingdom",
   "Britain", "the US", "United States", "the EU", "European Union", "France",
   "Germany"). When present, this signal is decisive.
2. Jurisdiction-specific government, regulatory, or listed-corporate entities
   (e.g. "UK Parliament", "Hansard", "the NHS", "BP plc", "Tesco plc";
   "US Congress", "Federal Reserve", "the SEC", "Apple Inc", "ExxonMobil";
   "European Commission", "ECB"). The entity's home jurisdiction wins, even
   if the claim mentions a different currency or operating region.
3. Geographic adjectives ("British", "American", "European", "French").
4. Currency symbols and codes ("$", "GBP", "EUR", "USD", "£", "€") — USE WITH
   CAUTION. Companies routinely report multinationally in any currency.
   Currency alone is NOT a jurisdiction signal. If a currency symbol is the
   only geographic cue and the entity is not jurisdiction-specific, prefer
   "Global". Never let a currency symbol override a higher-priority signal.

Apply ties by locus of the event: where the action takes place / where the
ruling is issued / which regulator is acting. Entity origin is the tiebreaker
when locus is unclear.

HANDLING UNCERTAINTY:
If the article spans multiple domains or is ambiguous:
- Use "General" as primary_domain
- List specific domains in secondary_domains
- Set confidence below 50
- Explain the ambiguity in reasoning

EXAMPLES:

Example 1 - Sports Article:
Input: Article about Arsenal's Premier League standings
Output: {{
    "primary_domain": "Sports",
    "secondary_domains": [],
    "jurisdiction": "UK",
    "confidence": 95,
    "reasoning": "Clear Premier League football article with team standings",
    "temporal_context": "December 2025, mid-season Premier League",
    "key_entities": ["Arsenal", "Premier League", "Mikel Arteta"],
    "evidence_guidance": "League standings change weekly - need pw (past week) freshness"
}}

Example 2 - Cross-Domain Article:
Input: Article about government climate policy impact on businesses
Output: {{
    "primary_domain": "Politics",
    "secondary_domains": ["Climate", "Finance"],
    "jurisdiction": "UK",
    "confidence": 75,
    "reasoning": "Policy article with climate and economic implications",
    "temporal_context": "2025 legislative session",
    "key_entities": ["UK Government", "Net Zero", "Carbon Tax"],
    "evidence_guidance": "Policy documents and official announcements - pm (past month) freshness"
}}

Example 3 - History Article:
Input: Article about the rise of fascism in 1930s Europe
Output: {{
    "primary_domain": "History",
    "secondary_domains": ["Politics"],
    "jurisdiction": "EU",
    "confidence": 90,
    "reasoning": "Article discusses historical political movements from the 1930s",
    "temporal_context": "1930s Europe, pre-World War II period",
    "key_entities": ["fascism", "Nazi Party", "Mussolini", "1930s"],
    "evidence_guidance": "Historical claims require academic sources, archives, and established historical records"
}}

Example 4 - Animals Article:
Input: Article about endangered species population decline
Output: {{
    "primary_domain": "Animals",
    "secondary_domains": ["Science"],
    "jurisdiction": "Global",
    "confidence": 85,
    "reasoning": "Article focuses on wildlife conservation and species data",
    "temporal_context": "Current conservation status with historical population trends",
    "key_entities": ["IUCN", "endangered species", "conservation"],
    "evidence_guidance": "Wildlife claims require authoritative sources like IUCN Red List, GBIF, or peer-reviewed journals"
}}

Example 5 - Currency-Mismatch Trap:
Input: BP plc reported record profits of $40 billion in 2022.
Output: {{
    "primary_domain": "Finance",
    "secondary_domains": [],
    "jurisdiction": "UK",
    "confidence": 90,
    "reasoning": "BP plc is a UK-listed company; the '$' figure is a reporting choice, not a jurisdiction signal. Entity origin (priority 2) overrides currency symbol (priority 4).",
    "temporal_context": "Full-year 2022 results",
    "key_entities": ["BP plc", "United Kingdom"],
    "evidence_guidance": "UK regulatory filings (Companies House), London Stock Exchange disclosures, financial press"
}}

Example 6 - Currency-Mismatch Trap (symmetric):
Input: ExxonMobil reported record profits of GBP 50 billion in 2022.
Output: {{
    "primary_domain": "Finance",
    "secondary_domains": [],
    "jurisdiction": "US",
    "confidence": 90,
    "reasoning": "ExxonMobil is a US-listed company; 'GBP' is a reporting choice, not a jurisdiction signal. Entity origin (priority 2) overrides currency symbol (priority 4).",
    "temporal_context": "Full-year 2022 results",
    "key_entities": ["ExxonMobil", "United States"],
    "evidence_guidance": "SEC filings, NYSE disclosures, US financial press"
}}

RESPONSE FORMAT:
Respond in JSON format:
{{
    "primary_domain": "domain_name",
    "secondary_domains": ["domain1", "domain2"],
    "jurisdiction": "UK|US|EU|Global",
    "confidence": 0-100,
    "reasoning": "One sentence explanation",
    "temporal_context": "Time period the article covers",
    "key_entities": ["Entity1", "Entity2", "Entity3"],
    "evidence_guidance": "Guidance for evidence retrieval"
}}

Return ONLY valid JSON, no additional text."""


async def _classify_with_llm(
    title: str, url: str, content: str, provider: str = "openai"
) -> ArticleClassification:
    """
    Classify article using LLM (gpt-4o-mini) with dynamic context for evidence retrieval.

    Cost: ~$0.0002 per article
    - Input: ~700 tokens (prompt + title + preview)
    - Output: ~100 tokens (JSON response with context fields)
    """
    try:
        import openai
        from datetime import datetime

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Get current date for temporal context
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = now.strftime("%Y")

        # Truncate content to ~1500 chars to keep costs low
        content_preview = content[:1500] if content else ""

        prompt = CLASSIFICATION_PROMPT.format(
            current_date=current_date,
            current_year=current_year,
            title=title or "Unknown Title",
            url=url or "Unknown URL",
            content=content_preview or "No content available",
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Tru8 fact-checking specialist. Always respond with valid JSON only, no markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=300,  # Increased for new context fields
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Validate and sanitize response
        primary_domain = result.get("primary_domain", "General")
        if primary_domain not in VALID_DOMAINS:
            logger.warning(
                f"LLM returned invalid domain '{primary_domain}', defaulting to General"
            )
            primary_domain = "General"

        secondary_domains = result.get("secondary_domains", [])
        secondary_domains = [
            d for d in secondary_domains if d in VALID_DOMAINS and d != primary_domain
        ][:2]

        jurisdiction = result.get("jurisdiction", "Global")
        if jurisdiction not in VALID_JURISDICTIONS:
            jurisdiction = "Global"

        confidence = int(result.get("confidence", 80))
        confidence = max(0, min(100, confidence))  # Clamp to 0-100

        # Extract new dynamic context fields
        key_entities = result.get("key_entities", [])
        if isinstance(key_entities, list):
            key_entities = [str(e) for e in key_entities[:10]]  # Limit to 10 entities
        else:
            key_entities = []

        return ArticleClassification(
            primary_domain=primary_domain,
            secondary_domains=secondary_domains,
            jurisdiction=jurisdiction,
            confidence=confidence,
            reasoning=result.get("reasoning", "Classified by LLM"),
            source="llm_primary",
            temporal_context=result.get("temporal_context", ""),
            key_entities=key_entities,
            evidence_guidance=result.get("evidence_guidance", ""),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM classification response: {e}")
        raise
    except Exception as e:
        # Log detailed error information for debugging
        import traceback

        logger.error(
            f"LLM classification failed for URL '{url[:100]}': {type(e).__name__}: {e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise


async def _classify_with_fallback_llm(
    title: str, url: str, content: str
) -> Optional[ArticleClassification]:
    """
    Primary LLM classification using Google AI (Gemini).

    Uses Gemini 2.5 Flash-Lite for fast, cost-effective classification.
    Falls back to OpenAI if Google API is unavailable.
    """
    try:
        from datetime import datetime

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = now.strftime("%Y")

        content_preview = content[:1500] if content else ""

        prompt = CLASSIFICATION_PROMPT.format(
            current_date=current_date,
            current_year=current_year,
            title=title or "Unknown Title",
            url=url or "Unknown URL",
            content=content_preview or "No content available",
        )

        full_prompt = f"You are a Tru8 fact-checking specialist. Always respond with valid JSON only, no markdown.\n\n{prompt}"

        result_data = await call_google_ai(
            full_prompt,
            temperature=0.1,
            max_tokens=300,
            timeout=30,
        )
        if result_data is None:
            return None

        # Validate and sanitize
        primary_domain = result_data.get("primary_domain", "General")
        if primary_domain not in VALID_DOMAINS:
            primary_domain = "General"

        secondary_domains = result_data.get("secondary_domains", [])
        secondary_domains = [
            d for d in secondary_domains if d in VALID_DOMAINS and d != primary_domain
        ][:2]

        jurisdiction = result_data.get("jurisdiction", "Global")
        if jurisdiction not in VALID_JURISDICTIONS:
            jurisdiction = "Global"

        confidence = int(result_data.get("confidence", 70))
        confidence = max(0, min(100, confidence))

        key_entities = result_data.get("key_entities", [])
        if isinstance(key_entities, list):
            key_entities = [str(e) for e in key_entities[:10]]
        else:
            key_entities = []

        return ArticleClassification(
            primary_domain=primary_domain,
            secondary_domains=secondary_domains,
            jurisdiction=jurisdiction,
            confidence=confidence,
            reasoning=result_data.get("reasoning", "Classified by Google AI fallback"),
            source="llm_fallback",
            temporal_context=result_data.get("temporal_context", ""),
            key_entities=key_entities,
            evidence_guidance=result_data.get("evidence_guidance", ""),
        )

    except Exception as e:
        logger.error(f"Google AI fallback classification failed: {e}")
        return None


async def classify_article(title: str, url: str, content: str) -> ArticleClassification:
    """
    Classify article with multi-tier fallback:
    1. URL pattern cache (instant)
    2. URL-specific cache (instant, Redis)
    3. Primary LLM (gpt-4o-mini)
    4. Fallback LLM (placeholder)
    5. "General" fallback

    Args:
        title: Article title
        url: Article URL
        content: Article content (first ~2000 chars)

    Returns:
        ArticleClassification with domain, jurisdiction, confidence
    """
    # 1. Check URL pattern cache (instant)
    cached_pattern = _check_url_pattern_cache(url)
    if cached_pattern:
        logger.info(
            f"Article classified via URL pattern: {cached_pattern.primary_domain} ({url[:50]}...)"
        )
        return cached_pattern

    # 2. Check URL-specific Redis cache (instant)
    cached_url = await get_cached_classification(url)
    if cached_url:
        logger.info(
            f"Article classified via URL cache: {cached_url.primary_domain} ({url[:50]}...)"
        )
        return cached_url

    # 3. Primary LLM classification (Google Gemini)
    try:
        classification = await _classify_with_fallback_llm(title, url, content)
        if classification:
            classification.source = "llm_primary"
            await cache_classification(url, classification)  # Cache for 24h
            logger.info(
                f"Article classified via Google Gemini: {classification.primary_domain} "
                f"(confidence: {classification.confidence:.2f}, {url[:50]}...)"
            )
            return classification
    except Exception as e:
        logger.warning(f"Primary LLM (Google) classification failed: {e}")

    # 4. Fallback LLM (OpenAI gpt-4o-mini)
    try:
        fallback_result = await _classify_with_llm(
            title, url, content, provider="openai"
        )
        if fallback_result:
            fallback_result.source = "llm_fallback"
            await cache_classification(url, fallback_result)
            logger.info(
                f"Article classified via OpenAI fallback: {fallback_result.primary_domain}"
            )
            return fallback_result
    except Exception as e:
        logger.warning(f"Fallback LLM (OpenAI) classification failed: {e}")

    # 5. Ultimate fallback - General domain
    logger.warning(
        f"[CLASSIFICATION FALLBACK] All classification methods failed for: {url[:100]}\n"
        f"  - Title: {title[:100] if title else 'EMPTY'}\n"
        f"  - Content length: {len(content) if content else 0} chars\n"
        f"  - Using 'General' domain with confidence=0"
    )
    return ArticleClassification(
        primary_domain="General",
        secondary_domains=[],
        jurisdiction="Global",
        confidence=0,
        reasoning="Classification failed - LLM unavailable, using fallback",
        source="fallback_general",
        temporal_context="",
        key_entities=[],
        evidence_guidance="",
        classification_failed=True,  # Explicit flag for downstream handling
    )


def classify_article_sync(title: str, url: str, content: str) -> ArticleClassification:
    """
    Synchronous wrapper for classify_article.
    Uses URL pattern cache only (no async Redis/LLM calls).
    Falls back to General if no pattern match.
    """
    # Check URL pattern cache (instant, no async required)
    cached_pattern = _check_url_pattern_cache(url)
    if cached_pattern:
        return cached_pattern

    # In sync context, we can't use Redis or LLM
    # Return General fallback
    return ArticleClassification(
        primary_domain="General",
        secondary_domains=[],
        jurisdiction="Global",
        confidence=0,
        reasoning="Sync classification - URL pattern not matched",
        source="fallback_general",
        temporal_context="",
        key_entities=[],
        evidence_guidance="",
    )
