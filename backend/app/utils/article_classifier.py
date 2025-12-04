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

logger = logging.getLogger(__name__)

# Cache TTL for URL-specific classifications
CLASSIFICATION_CACHE_TTL = timedelta(hours=24)


@dataclass
class ArticleClassification:
    """Article classification result with dynamic context for evidence retrieval"""
    primary_domain: str           # Sports, Politics, Finance, etc.
    secondary_domains: List[str]  # For cross-domain articles
    jurisdiction: str             # UK, US, EU, Global
    confidence: int               # 0-100
    reasoning: str                # LLM explanation
    source: str                   # "cache_pattern", "cache_url", "llm_primary", "llm_fallback", "fallback_general"

    # Dynamic context for evidence retrieval (Phase: Dynamic Context-Aware)
    temporal_context: str = ""              # "December 2024, mid-season Premier League"
    key_entities: List[str] = None          # ["Arsenal", "Chelsea", "Premier League"]
    evidence_guidance: str = ""             # "League standings change weekly after each matchweek"

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
            evidence_guidance=data.get("evidence_guidance", "")
        )


# Valid domain categories (match existing API adapters)
VALID_DOMAINS = [
    "Sports", "Politics", "Finance", "Health", "Science",
    "Law", "Climate", "Weather", "Demographics", "Entertainment", "General"
]

# Valid jurisdictions
VALID_JURISDICTIONS = ["UK", "US", "EU", "Global"]


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
    (r".*gov\.uk.*", "Politics", "UK"),  # Generic gov.uk - MUST be AFTER specific subdomains

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
                evidence_guidance=""
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
- Climate (weather, environment, global warming, emissions)
- Demographics (population, census, migration, social statistics)
- Entertainment (movies, music, celebrities, arts, culture)
- General (if none of the above clearly fit)

ALSO IDENTIFY:
1. Any secondary domains (max 2) if the article crosses topics
2. Geographic jurisdiction: UK, US, EU, or Global
3. Temporal context: What time period does this article cover?
4. Key entities: Main people, organizations, or things mentioned (max 10)
5. Evidence guidance: What freshness and source types are needed to verify claims in this article?

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
    title: str,
    url: str,
    content: str,
    provider: str = "openai"
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
            content=content_preview or "No content available"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Tru8 fact-checking specialist. Always respond with valid JSON only, no markdown."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=300,   # Increased for new context fields
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Validate and sanitize response
        primary_domain = result.get("primary_domain", "General")
        if primary_domain not in VALID_DOMAINS:
            logger.warning(f"LLM returned invalid domain '{primary_domain}', defaulting to General")
            primary_domain = "General"

        secondary_domains = result.get("secondary_domains", [])
        secondary_domains = [d for d in secondary_domains if d in VALID_DOMAINS and d != primary_domain][:2]

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
            evidence_guidance=result.get("evidence_guidance", "")
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM classification response: {e}")
        raise
    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        raise


async def _classify_with_fallback_llm(
    title: str,
    url: str,
    content: str
) -> Optional[ArticleClassification]:
    """
    Placeholder for secondary LLM provider.

    TODO: Implement when second API key is configured.
    Currently returns None to trigger General fallback.

    Future options:
    - Anthropic Claude
    - Google Gemini
    - Open-source models
    """
    # Check if fallback provider is configured
    # Future: Check settings.FALLBACK_LLM_PROVIDER and settings.FALLBACK_LLM_API_KEY
    return None


async def classify_article(
    title: str,
    url: str,
    content: str
) -> ArticleClassification:
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
        logger.info(f"Article classified via URL pattern: {cached_pattern.primary_domain} ({url[:50]}...)")
        return cached_pattern

    # 2. Check URL-specific Redis cache (instant)
    cached_url = await get_cached_classification(url)
    if cached_url:
        logger.info(f"Article classified via URL cache: {cached_url.primary_domain} ({url[:50]}...)")
        return cached_url

    # 3. Primary LLM classification (gpt-4o-mini)
    try:
        classification = await _classify_with_llm(title, url, content, provider="openai")
        classification.source = "llm_primary"
        await cache_classification(url, classification)  # Cache for 24h
        logger.info(
            f"Article classified via LLM: {classification.primary_domain} "
            f"(confidence: {classification.confidence:.2f}, {url[:50]}...)"
        )
        return classification
    except Exception as e:
        logger.warning(f"Primary LLM classification failed: {e}")

    # 4. Fallback LLM (placeholder - returns None until configured)
    try:
        fallback_result = await _classify_with_fallback_llm(title, url, content)
        if fallback_result:
            fallback_result.source = "llm_fallback"
            await cache_classification(url, fallback_result)
            logger.info(f"Article classified via fallback LLM: {fallback_result.primary_domain}")
            return fallback_result
    except Exception as e:
        logger.warning(f"Fallback LLM classification failed: {e}")

    # 5. Ultimate fallback - General domain
    logger.warning(f"All classification methods failed, using General fallback for: {url[:50]}...")
    return ArticleClassification(
        primary_domain="General",
        secondary_domains=[],
        jurisdiction="Global",
        confidence=0,
        reasoning="Classification failed, using fallback",
        source="fallback_general",
        temporal_context="",
        key_entities=[],
        evidence_guidance=""
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
        evidence_guidance=""
    )
