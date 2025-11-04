"""
Sample Content Library for Testing

Created: 2025-11-03 15:25:00 UTC
Last Updated: 2025-11-03 15:25:00 UTC
Code Version: commit 388ac66
Purpose: Realistic sample content for testing all pipeline stages
Content: URLs, text, images, claims, evidence

This module provides comprehensive test data covering various
content types, claim categories, and verification scenarios.

Usage:
    from sample_content import SAMPLE_ARTICLE_TEXT, SAMPLE_CLAIMS

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

from typing import Dict, Any, List

# ==================== SAMPLE URLS ====================

SAMPLE_NEWS_URL = "https://www.bbc.com/news/science-environment-67890123"
SAMPLE_BLOG_URL = "https://climateblog.example.com/article-2024"
SAMPLE_ACADEMIC_URL = "https://www.nature.com/articles/s41586-024-12345"
SAMPLE_GOVERNMENT_URL = "https://www.noaa.gov/climate-data/report-2024"
SAMPLE_PAYWALL_URL = "https://www.nytimes.com/2024/11/01/climate-article"
SAMPLE_INVALID_URL = "https://nonexistent-website-xyz123.com/article"

# ==================== SAMPLE TEXT CONTENT ====================

# Standard article with multiple verifiable claims
SAMPLE_ARTICLE_TEXT = """
Climate Summit 2024: Historic Agreement Reached

GENEVA - In a landmark moment for global climate action, 195 countries have agreed to reduce carbon
emissions by 45% by 2030, marking the most ambitious climate target in history. The agreement was
reached after two weeks of intense negotiations at the Global Climate Summit.

Scientific Consensus

According to leading climate scientists, global temperatures have risen by 1.1°C since pre-industrial
times, with the rate of warming accelerating in recent decades. Dr. Sarah Johnson, lead climate
researcher at NASA, stated: "The evidence is overwhelming. We are seeing unprecedented changes in
our climate system."

Financial Commitments

The agreement includes a historic financial package of $100 billion in annual funding for developing
nations to transition to renewable energy sources. This represents a significant increase from previous
commitments and will be distributed through the Green Climate Fund.

Renewable Energy Growth

The International Energy Agency reports that renewable energy capacity grew by 9.6% in 2023, with
solar power leading the expansion. Wind energy installations increased by 50 gigawatts globally,
primarily in Asia and Europe.

Challenges Ahead

However, environmental groups argue that the targets are insufficient to limit warming to 1.5°C as
outlined in the Paris Agreement. Critics point to the lack of binding enforcement mechanisms and
question whether countries will meet their pledges.

The summit concluded with leaders emphasizing the urgency of climate action and the need for
immediate implementation of the agreed measures.
""".strip()

# Article with opinion and non-verifiable claims
SAMPLE_OPINION_ARTICLE = """
Why the Climate Agreement Falls Short

The recently concluded climate summit has produced an agreement that, frankly, doesn't go far enough.
While 195 countries committing to emissions reductions sounds impressive, the reality is that these
targets are woefully inadequate.

This is clearly the worst climate policy we've seen in decades. The 45% reduction target is arbitrary
and lacks scientific backing. We should be aiming for at least 70% reductions to have any hope of
preventing catastrophic warming.

Future generations will judge us harshly for this failure. It's obvious that political considerations
took precedence over scientific necessity. The summit was a missed opportunity to show real leadership
on climate change.
""".strip()

# Short text (edge case - too short)
SAMPLE_SHORT_TEXT = "Climate change is real."

# Long text (edge case - very long)
SAMPLE_LONG_TEXT = """
[This would be an extremely long article - 5000+ words covering multiple topics]
""" + " ".join([f"Paragraph {i} about climate science." for i in range(1, 200)])

# Text with predictions (not verifiable)
SAMPLE_PREDICTION_TEXT = """
Climate Forecast for 2050

By 2050, global temperatures will rise by 2.5°C according to current projections. Sea levels will
increase by 30 centimeters, affecting coastal cities worldwide. Extreme weather events will become
50% more frequent, and Arctic ice will disappear completely during summer months.

Renewable energy will comprise 80% of global energy production, and electric vehicles will dominate
transportation. These changes are inevitable based on current trends.
""".strip()

# Scientific/technical content
SAMPLE_TECHNICAL_TEXT = """
Carbon Sequestration Mechanisms in Tropical Rainforests

Recent studies utilizing LIDAR technology have quantified carbon storage rates in Amazonian forests
at 2.4 tons per hectare annually. The research, published in Nature Climate Change (DOI: 10.1038/s41558-024-01234),
measured 50,000 individual trees across 12 study sites.

Methodology involved spectral analysis at 532nm and 1064nm wavelengths, with canopy height models
derived from point cloud data. Results indicate 15% higher sequestration rates than previously estimated
using traditional ground-based methods.
""".strip()

# ==================== SAMPLE CLAIMS ====================

SAMPLE_CLAIMS = [
    {
        "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
        "position": 0,
        "subject_context": "Climate agreement",
        "key_entities": ["195 countries", "45%", "2030", "carbon emissions"],
        "is_verifiable": True,
        "claim_type": "factual",
        "temporal_markers": ["by 2030"],
        "is_time_sensitive": True
    },
    {
        "text": "Global temperatures have risen by 1.1°C since pre-industrial times",
        "position": 1,
        "subject_context": "Climate change",
        "key_entities": ["global temperatures", "1.1°C", "pre-industrial times"],
        "is_verifiable": True,
        "claim_type": "factual",
        "temporal_markers": ["since pre-industrial times"],
        "is_time_sensitive": False
    },
    {
        "text": "The agreement includes $100 billion in annual funding for developing nations",
        "position": 2,
        "subject_context": "Climate finance",
        "key_entities": ["$100 billion", "annual", "developing nations"],
        "is_verifiable": True,
        "claim_type": "factual",
        "temporal_markers": ["annual"],
        "is_time_sensitive": True
    },
    {
        "text": "Renewable energy capacity grew by 9.6% in 2023",
        "position": 3,
        "subject_context": "Renewable energy",
        "key_entities": ["renewable energy capacity", "9.6%", "2023"],
        "is_verifiable": True,
        "claim_type": "factual",
        "temporal_markers": ["in 2023"],
        "is_time_sensitive": True
    }
]

# Claims with various types
SAMPLE_MIXED_CLAIMS = [
    {
        "text": "195 countries agreed to emissions cuts",
        "claim_type": "factual",
        "is_verifiable": True
    },
    {
        "text": "The climate targets are insufficient",
        "claim_type": "opinion",
        "is_verifiable": False
    },
    {
        "text": "Temperatures will rise by 2°C by 2050",
        "claim_type": "prediction",
        "is_verifiable": False
    }
]

# ==================== SAMPLE EVIDENCE ====================

SAMPLE_EVIDENCE = [
    {
        "source": "BBC News",
        "url": "https://www.bbc.com/news/science-environment-67890123",
        "title": "Climate Summit 2024: 195 Countries Agree to Historic Emissions Cuts",
        "snippet": "195 countries have committed to reducing carbon emissions by 45% by 2030...",
        "published_date": "2024-11-01",
        "relevance_score": 0.95,
        "credibility_score": 0.90,
        "tier": "tier1_news",
        "is_factcheck": False,
        "domain": "bbc.com"
    },
    {
        "source": "Reuters",
        "url": "https://www.reuters.com/climate/agreement-2024",
        "title": "World Leaders Commit to 45% Carbon Reduction Target",
        "snippet": "Agreement includes binding targets for 45% carbon reduction by 2030...",
        "published_date": "2024-11-01",
        "relevance_score": 0.92,
        "credibility_score": 0.88,
        "tier": "tier1_news",
        "is_factcheck": False,
        "domain": "reuters.com"
    },
    {
        "source": "The Guardian",
        "url": "https://www.theguardian.com/environment/2024/nov/climate",
        "title": "Climate Agreement Reaches 195 Countries",
        "snippet": "195 countries sign agreement with 45% emissions reduction target...",
        "published_date": "2024-11-01",
        "relevance_score": 0.90,
        "credibility_score": 0.85,
        "tier": "tier1_news",
        "is_factcheck": False,
        "domain": "theguardian.com"
    },
    {
        "source": "NASA",
        "url": "https://climate.nasa.gov/vital-signs/global-temperature",
        "title": "Global Temperature Data",
        "snippet": "Global average temperatures have increased by 1.2°C since pre-industrial times...",
        "published_date": "2024-10-20",
        "relevance_score": 0.88,
        "credibility_score": 0.95,
        "tier": "academic",
        "is_factcheck": False,
        "domain": "nasa.gov"
    },
    {
        "source": "PolitiFact",
        "url": "https://www.politifact.com/factchecks/2024/nov/climate-agreement/",
        "title": "FACT CHECK: Climate Agreement Claims",
        "snippet": "The claim that 195 countries agreed to 45% emissions cuts is True...",
        "published_date": "2024-11-02",
        "relevance_score": 0.93,
        "credibility_score": 0.92,
        "tier": "factcheck",
        "is_factcheck": True,
        "domain": "politifact.com",
        "factcheck_rating": "True"
    }
]

# ==================== IMAGE CONTENT ====================

SAMPLE_IMAGE_PATH = "/tmp/test_climate_chart.png"
SAMPLE_IMAGE_CONTENT = "Mock image binary data"
SAMPLE_OCR_TEXT = """
Climate Data Visualization
Global Temperature Anomaly 1880-2024
+1.2°C above baseline
Source: NASA GISS
"""

# ==================== VIDEO CONTENT ====================

SAMPLE_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SAMPLE_VIDEO_ID = "dQw4w9WgXcQ"
SAMPLE_TRANSCRIPT = [
    {"text": "Welcome to today's climate report.", "start": 0.0, "duration": 3.5},
    {"text": "Global temperatures have risen significantly.", "start": 3.5, "duration": 4.0},
    {"text": "Scientists confirm 1.1 degrees Celsius of warming.", "start": 7.5, "duration": 4.5},
    {"text": "This is based on data from multiple sources.", "start": 12.0, "duration": 3.8}
]

# ==================== USER QUERIES (Search Clarity) ====================

SAMPLE_USER_QUERIES = [
    "How many countries agreed to the climate deal?",
    "What is the temperature increase since pre-industrial times?",
    "How much funding is included in the agreement?",
    "When is the emissions reduction deadline?",
    "What percentage of emissions will be reduced?"
]

# ==================== METADATA ====================

SAMPLE_METADATA = {
    "title": "Climate Summit 2024: Historic Agreement Reached",
    "author": "Jane Smith",
    "date": "2024-11-01",
    "url": SAMPLE_NEWS_URL,
    "publisher": "BBC News",
    "word_count": 450
}

# ==================== TEST SCENARIOS ====================

# Scenario 1: All claims supported
SCENARIO_ALL_SUPPORTED = {
    "content": SAMPLE_ARTICLE_TEXT,
    "claims": SAMPLE_CLAIMS,
    "evidence": SAMPLE_EVIDENCE,
    "expected_verdict": "supported"
}

# Scenario 2: Mixed verdicts
SCENARIO_MIXED_VERDICTS = {
    "content": SAMPLE_OPINION_ARTICLE,
    "claims": SAMPLE_MIXED_CLAIMS,
    "expected_verdicts": ["supported", "uncertain", "insufficient_evidence"]
}

# Scenario 3: Insufficient evidence
SCENARIO_INSUFFICIENT_EVIDENCE = {
    "content": "A very obscure claim about a niche topic with no mainstream coverage.",
    "expected_verdict": "insufficient_evidence"
}

# Scenario 4: Time-sensitive claim
SCENARIO_TIME_SENSITIVE = {
    "content": "The S&P 500 closed at 4,783.45 today.",
    "is_time_sensitive": True,
    "expected_challenge": "temporal_relevance"
}

# Scenario 5: Non-verifiable (predictions)
SCENARIO_PREDICTIONS = {
    "content": SAMPLE_PREDICTION_TEXT,
    "expected_claim_types": ["prediction"],
    "expected_verdict": "non_verifiable"
}

# ==================== EDGE CASES ====================

# Empty content
SAMPLE_EMPTY_CONTENT = ""

# Only whitespace
SAMPLE_WHITESPACE_CONTENT = "   \n\n   \t  \n  "

# Special characters
SAMPLE_SPECIAL_CHARS = """
Climate data: 1.1°C ±0.2°C (95% CI)
CO₂ levels: 420 ppm
Δ temperature: +1.2°C
Arctic sea ice: ↓15% per decade
"""

# Unicode and emojis
SAMPLE_UNICODE_CONTENT = """
🌍 Climate Summit 2024 🌡️

195 countries 🤝 agreed to reduce emissions by 45% 📉 by 2030 ⏰

Scientists confirm 🔬 1.1°C 🌡️ warming since pre-industrial times ⚠️
"""

# HTML content (needs sanitization)
SAMPLE_HTML_CONTENT = """
<html>
<head><title>Climate Article</title></head>
<body>
<h1>Climate Summit</h1>
<p>195 countries agreed to <strong>reduce emissions</strong> by 45%.</p>
<script>alert('xss')</script>
<p>Global temperatures have risen by 1.1°C.</p>
</body>
</html>
"""

# Very long single sentence
SAMPLE_LONG_SENTENCE = "The global climate summit, which was attended by representatives from 195 countries including the United States, China, India, and all member states of the European Union, concluded after two weeks of intensive negotiations with an agreement to reduce carbon emissions by 45 percent by the year 2030, which scientists say is necessary but may not be sufficient to limit global warming to 1.5 degrees Celsius above pre-industrial levels as outlined in the Paris Agreement that was signed in 2015."

# ==================== HELPER FUNCTIONS ====================

def get_sample_content(content_type: str = "article") -> str:
    """
    Get sample content by type

    Args:
        content_type: One of: article, opinion, short, long, prediction, technical, empty

    Returns:
        Sample content string

    Created: 2025-11-03
    """
    content_map = {
        "article": SAMPLE_ARTICLE_TEXT,
        "opinion": SAMPLE_OPINION_ARTICLE,
        "short": SAMPLE_SHORT_TEXT,
        "long": SAMPLE_LONG_TEXT,
        "prediction": SAMPLE_PREDICTION_TEXT,
        "technical": SAMPLE_TECHNICAL_TEXT,
        "empty": SAMPLE_EMPTY_CONTENT,
        "whitespace": SAMPLE_WHITESPACE_CONTENT,
        "special_chars": SAMPLE_SPECIAL_CHARS,
        "unicode": SAMPLE_UNICODE_CONTENT,
        "html": SAMPLE_HTML_CONTENT
    }

    return content_map.get(content_type, SAMPLE_ARTICLE_TEXT)


def get_sample_claims(num_claims: int = 4, claim_type: str = "factual") -> List[Dict[str, Any]]:
    """
    Get sample claims

    Args:
        num_claims: Number of claims to return
        claim_type: Filter by type (factual, opinion, prediction, mixed)

    Returns:
        List of claim dictionaries

    Created: 2025-11-03
    """
    if claim_type == "mixed":
        return SAMPLE_MIXED_CLAIMS[:num_claims]

    filtered = [c for c in SAMPLE_CLAIMS if c.get("claim_type") == claim_type]
    return filtered[:num_claims]


def get_sample_evidence(credibility_level: str = "high", count: int = 5) -> List[Dict[str, Any]]:
    """
    Get sample evidence filtered by credibility

    Args:
        credibility_level: high (>0.85), medium (0.60-0.85), low (<0.60)
        count: Number of evidence items

    Returns:
        List of evidence dictionaries

    Created: 2025-11-03
    """
    if credibility_level == "high":
        filtered = [e for e in SAMPLE_EVIDENCE if e["credibility_score"] >= 0.85]
    elif credibility_level == "medium":
        filtered = [e for e in SAMPLE_EVIDENCE if 0.60 <= e["credibility_score"] < 0.85]
    elif credibility_level == "low":
        filtered = [e for e in SAMPLE_EVIDENCE if e["credibility_score"] < 0.60]
    else:
        filtered = SAMPLE_EVIDENCE

    return filtered[:count]


# ==================== DOCUMENTATION ====================

"""
Usage Examples:

1. Basic Content:
    from sample_content import SAMPLE_ARTICLE_TEXT, SAMPLE_CLAIMS
    extractor = ClaimExtractor()
    claims = extractor.extract(SAMPLE_ARTICLE_TEXT)

2. Type-Specific Content:
    from sample_content import get_sample_content
    opinion_text = get_sample_content("opinion")
    prediction_text = get_sample_content("prediction")

3. Evidence Testing:
    from sample_content import get_sample_evidence
    high_cred = get_sample_evidence("high", count=3)
    low_cred = get_sample_evidence("low", count=2)

4. Claim Testing:
    from sample_content import get_sample_claims
    factual_claims = get_sample_claims(num_claims=2, claim_type="factual")
    mixed_claims = get_sample_claims(num_claims=3, claim_type="mixed")

5. Scenario Testing:
    from sample_content import SCENARIO_ALL_SUPPORTED
    result = pipeline.process(SCENARIO_ALL_SUPPORTED["content"])
    assert result.verdict == SCENARIO_ALL_SUPPORTED["expected_verdict"]

6. Edge Cases:
    from sample_content import SAMPLE_EMPTY_CONTENT, SAMPLE_UNICODE_CONTENT
    test_empty(SAMPLE_EMPTY_CONTENT)
    test_unicode(SAMPLE_UNICODE_CONTENT)
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial sample content library
#          - Sample URLs (news, blog, academic, government)
#          - Sample text content (article, opinion, short, long, prediction, technical)
#          - Sample claims (factual, opinion, prediction)
#          - Sample evidence (various credibility levels)
#          - Image and video content
#          - User queries (Search Clarity)
#          - Test scenarios
#          - Edge cases (empty, unicode, HTML, special chars)
#          - Helper functions
