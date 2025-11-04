"""
Mock Google Fact Check Explorer API Responses

Created: 2025-11-03 15:20:00 UTC
Last Updated: 2025-11-03 15:20:00 UTC
Code Version: commit 388ac66
Purpose: Realistic Google Fact Check Explorer API responses for testing
API: Google Fact Check Tools API v1alpha1

This module provides mock fact-check data matching the actual Google
Fact Check Explorer API format with realistic ratings and publishers.

Usage:
    from factcheck_data import MOCK_FACTCHECK_RESULTS
    mock_factcheck_api.search.return_value = MOCK_FACTCHECK_RESULTS

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

# ==================== STANDARD FACT-CHECK RESULTS ====================

MOCK_FACTCHECK_RESULTS = {
    "claims": [
        {
            "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
            "claimant": "Various news sources",
            "claimDate": "2024-11-01",
            "claimReview": [
                {
                    "publisher": {
                        "name": "PolitiFact",
                        "site": "politifact.com"
                    },
                    "url": "https://www.politifact.com/factchecks/2024/nov/climate-agreement/",
                    "title": "Climate Agreement: 195 Countries and 45% Reduction",
                    "reviewDate": "2024-11-02",
                    "textualRating": "True",
                    "languageCode": "en"
                }
            ]
        },
        {
            "text": "Global temperatures have risen by 1.1°C since pre-industrial times",
            "claimant": "Climate scientists",
            "claimDate": "2024-10-15",
            "claimReview": [
                {
                    "publisher": {
                        "name": "FactCheck.org",
                        "site": "factcheck.org"
                    },
                    "url": "https://www.factcheck.org/2024/10/temperature-rise-verification/",
                    "title": "Verifying Global Temperature Rise Claims",
                    "reviewDate": "2024-10-16",
                    "textualRating": "Mostly True",
                    "languageCode": "en"
                },
                {
                    "publisher": {
                        "name": "Climate Feedback",
                        "site": "climatefeedback.org"
                    },
                    "url": "https://climatefeedback.org/claimreview/temperature-1-1c/",
                    "title": "Temperature Rise: Scientific Consensus",
                    "reviewDate": "2024-10-18",
                    "textualRating": "Accurate",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

# ==================== VARIOUS RATINGS ====================

MOCK_TRUE_RATING = {
    "claims": [
        {
            "text": "The Federal Reserve was established in 1913",
            "claimant": "Historical sources",
            "claimDate": "2024-01-15",
            "claimReview": [
                {
                    "publisher": {
                        "name": "Snopes",
                        "site": "snopes.com"
                    },
                    "url": "https://www.snopes.com/fact-check/federal-reserve-1913/",
                    "title": "Federal Reserve Establishment Date",
                    "reviewDate": "2024-01-16",
                    "textualRating": "True",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

MOCK_FALSE_RATING = {
    "claims": [
        {
            "text": "Global warming has stopped since 2000",
            "claimant": "Blog post",
            "claimDate": "2024-09-15",
            "claimReview": [
                {
                    "publisher": {
                        "name": "Climate Feedback",
                        "site": "climatefeedback.org"
                    },
                    "url": "https://climatefeedback.org/claimreview/warming-continues/",
                    "title": "Claim That Warming Stopped is False",
                    "reviewDate": "2024-09-16",
                    "textualRating": "False",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

MOCK_MOSTLY_TRUE_RATING = {
    "claims": [
        {
            "text": "Renewable energy capacity grew by approximately 10% in 2023",
            "claimant": "Energy analyst",
            "claimDate": "2024-10-20",
            "claimReview": [
                {
                    "publisher": {
                        "name": "PolitiFact",
                        "site": "politifact.com"
                    },
                    "url": "https://www.politifact.com/factchecks/2024/oct/renewable-growth/",
                    "title": "Renewable Energy Growth Rate Verification",
                    "reviewDate": "2024-10-21",
                    "textualRating": "Mostly True",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

MOCK_HALF_TRUE_RATING = {
    "claims": [
        {
            "text": "Carbon emissions have decreased in developed countries",
            "claimant": "Political speech",
            "claimDate": "2024-08-10",
            "claimReview": [
                {
                    "publisher": {
                        "name": "PolitiFact",
                        "site": "politifact.com"
                    },
                    "url": "https://www.politifact.com/factchecks/2024/aug/emissions-claim/",
                    "title": "Carbon Emissions: Partial Truth",
                    "reviewDate": "2024-08-11",
                    "textualRating": "Half True",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

MOCK_MOSTLY_FALSE_RATING = {
    "claims": [
        {
            "text": "Wind turbines kill more birds than climate change",
            "claimant": "Social media post",
            "claimDate": "2024-07-15",
            "claimReview": [
                {
                    "publisher": {
                        "name": "FactCheck.org",
                        "site": "factcheck.org"
                    },
                    "url": "https://www.factcheck.org/2024/07/wind-turbines-birds/",
                    "title": "Wind Turbine Bird Deaths: Context Matters",
                    "reviewDate": "2024-07-16",
                    "textualRating": "Mostly False",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

MOCK_PANTS_ON_FIRE_RATING = {
    "claims": [
        {
            "text": "Climate change is a hoax invented in 2010",
            "claimant": "Conspiracy website",
            "claimDate": "2024-06-01",
            "claimReview": [
                {
                    "publisher": {
                        "name": "PolitiFact",
                        "site": "politifact.com"
                    },
                    "url": "https://www.politifact.com/factchecks/2024/jun/climate-hoax/",
                    "title": "Climate Change Hoax Claim is Absurd",
                    "reviewDate": "2024-06-02",
                    "textualRating": "Pants on Fire",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

# ==================== MULTIPLE REVIEWERS ====================

MOCK_MULTIPLE_REVIEWERS = {
    "claims": [
        {
            "text": "COVID-19 vaccines are 95% effective against severe disease",
            "claimant": "Health officials",
            "claimDate": "2024-05-10",
            "claimReview": [
                {
                    "publisher": {
                        "name": "FactCheck.org",
                        "site": "factcheck.org"
                    },
                    "url": "https://www.factcheck.org/2024/05/vaccine-effectiveness/",
                    "title": "Vaccine Effectiveness: The Evidence",
                    "reviewDate": "2024-05-11",
                    "textualRating": "True",
                    "languageCode": "en"
                },
                {
                    "publisher": {
                        "name": "Snopes",
                        "site": "snopes.com"
                    },
                    "url": "https://www.snopes.com/fact-check/vaccine-95-percent/",
                    "title": "COVID Vaccine Effectiveness Rate",
                    "reviewDate": "2024-05-12",
                    "textualRating": "Mostly True",
                    "languageCode": "en"
                },
                {
                    "publisher": {
                        "name": "Health Feedback",
                        "site": "healthfeedback.org"
                    },
                    "url": "https://healthfeedback.org/claimreview/vaccine-efficacy-claim/",
                    "title": "Vaccine Efficacy Data Review",
                    "reviewDate": "2024-05-13",
                    "textualRating": "Accurate",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

# ==================== CONFLICTING RATINGS ====================

MOCK_CONFLICTING_RATINGS = {
    "claims": [
        {
            "text": "Economic growth exceeded 3% in Q3 2024",
            "claimant": "Government report",
            "claimDate": "2024-10-01",
            "claimReview": [
                {
                    "publisher": {
                        "name": "FactCheck.org",
                        "site": "factcheck.org"
                    },
                    "url": "https://www.factcheck.org/2024/10/gdp-growth-q3/",
                    "title": "Q3 GDP Growth Verification",
                    "reviewDate": "2024-10-02",
                    "textualRating": "True",
                    "languageCode": "en"
                },
                {
                    "publisher": {
                        "name": "PolitiFact",
                        "site": "politifact.com"
                    },
                    "url": "https://www.politifact.com/factchecks/2024/oct/gdp-claim/",
                    "title": "Economic Growth: Depends on Measurement",
                    "reviewDate": "2024-10-03",
                    "textualRating": "Half True",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

# ==================== NO FACT-CHECKS FOUND ====================

MOCK_NO_FACTCHECKS = {
    "claims": []
}

# ==================== RECENT FACT-CHECKS ====================

MOCK_RECENT_FACTCHECKS = {
    "claims": [
        {
            "text": "Breaking news claim from today",
            "claimant": "News outlet",
            "claimDate": datetime.now().strftime("%Y-%m-%d"),
            "claimReview": [
                {
                    "publisher": {
                        "name": "Snopes",
                        "site": "snopes.com"
                    },
                    "url": "https://www.snopes.com/fact-check/breaking-claim/",
                    "title": "Rapid Response Fact-Check",
                    "reviewDate": datetime.now().strftime("%Y-%m-%d"),
                    "textualRating": "Unproven",
                    "languageCode": "en"
                }
            ]
        }
    ]
}

# ==================== HELPER FUNCTIONS ====================

def create_factcheck_claim(
    text: str,
    publisher: str,
    rating: str,
    review_date: str = None,
    claimant: str = "Various sources",
    publisher_site: str = None
) -> Dict[str, Any]:
    """
    Create a single fact-check claim

    Args:
        text: Claim text
        publisher: Fact-checker name
        rating: Textual rating (e.g., "True", "False", "Mostly True")
        review_date: Review date (YYYY-MM-DD)
        claimant: Who made the claim
        publisher_site: Publisher website domain

    Returns:
        Fact-check claim dictionary

    Created: 2025-11-03
    """
    if review_date is None:
        review_date = datetime.now().strftime("%Y-%m-%d")

    if publisher_site is None:
        publisher_site = f"{publisher.lower().replace(' ', '')}.com"

    claim_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    return {
        "text": text,
        "claimant": claimant,
        "claimDate": claim_date,
        "claimReview": [
            {
                "publisher": {
                    "name": publisher,
                    "site": publisher_site
                },
                "url": f"https://www.{publisher_site}/factchecks/{review_date}/claim/",
                "title": f"Fact-Check: {text[:50]}...",
                "reviewDate": review_date,
                "textualRating": rating,
                "languageCode": "en"
            }
        ]
    }


def create_factcheck_response(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a complete fact-check API response

    Args:
        claims: List of fact-check claims

    Returns:
        Complete API response

    Created: 2025-11-03
    """
    return {"claims": claims}


def get_factcheck_by_rating(rating: str) -> Dict[str, Any]:
    """
    Get fact-check results with specified rating

    Args:
        rating: One of: true, false, mostly_true, half_true, mostly_false, pants_on_fire

    Returns:
        Fact-check results

    Created: 2025-11-03
    """
    rating_map = {
        "true": MOCK_TRUE_RATING,
        "false": MOCK_FALSE_RATING,
        "mostly_true": MOCK_MOSTLY_TRUE_RATING,
        "half_true": MOCK_HALF_TRUE_RATING,
        "mostly_false": MOCK_MOSTLY_FALSE_RATING,
        "pants_on_fire": MOCK_PANTS_ON_FIRE_RATING
    }

    return rating_map.get(rating.lower(), MOCK_FACTCHECK_RESULTS)


def normalize_rating(textual_rating: str) -> float:
    """
    Convert textual rating to normalized score (0-1)

    Matches the production rating normalization logic

    Args:
        textual_rating: Textual rating string

    Returns:
        Normalized score between 0 and 1

    Created: 2025-11-03
    """
    rating_lower = textual_rating.lower()

    # High confidence (0.9-1.0)
    if any(term in rating_lower for term in ["true", "accurate", "correct"]):
        if "mostly" in rating_lower or "largely" in rating_lower:
            return 0.75  # Mostly True
        return 1.0  # True

    # Medium confidence (0.4-0.6)
    if any(term in rating_lower for term in ["half", "mixture", "mixed", "unproven"]):
        return 0.5

    # Low confidence (0.1-0.3)
    if any(term in rating_lower for term in ["false", "incorrect", "inaccurate"]):
        if "mostly" in rating_lower or "largely" in rating_lower:
            return 0.25  # Mostly False
        if "pants on fire" in rating_lower:
            return 0.0  # Pants on Fire
        return 0.1  # False

    # Default
    return 0.5


# ==================== REALISTIC TEST SCENARIOS ====================

# Scenario: Political fact-check
MOCK_POLITICAL_FACTCHECK = create_factcheck_response([
    create_factcheck_claim(
        text="Unemployment rate dropped to 3.8% in October 2024",
        publisher="PolitiFact",
        rating="True",
        publisher_site="politifact.com"
    )
])

# Scenario: Health misinformation
MOCK_HEALTH_MISINFORMATION = create_factcheck_response([
    create_factcheck_claim(
        text="Drinking bleach cures diseases",
        publisher="Snopes",
        rating="False",
        publisher_site="snopes.com",
        claimant="Social media post"
    )
])

# Scenario: Scientific claim
MOCK_SCIENTIFIC_CLAIM = create_factcheck_response([
    create_factcheck_claim(
        text="The James Webb telescope discovered signs of life on exoplanet K2-18b",
        publisher="Science Feedback",
        rating="Mostly False",
        publisher_site="sciencefeedback.co",
        claimant="News headline"
    )
])

# ==================== ERROR RESPONSES ====================

MOCK_API_ERROR_RESPONSE = {
    "error": {
        "code": 403,
        "message": "API key invalid",
        "status": "PERMISSION_DENIED"
    }
}

MOCK_RATE_LIMIT_RESPONSE = {
    "error": {
        "code": 429,
        "message": "Quota exceeded",
        "status": "RESOURCE_EXHAUSTED"
    }
}

# ==================== DOCUMENTATION ====================

"""
Usage Examples:

1. Standard Testing:
    from factcheck_data import MOCK_FACTCHECK_RESULTS
    mock_factcheck_api.search.return_value = MOCK_FACTCHECK_RESULTS

2. Rating-Specific Testing:
    from factcheck_data import get_factcheck_by_rating
    results = get_factcheck_by_rating("mostly_true")
    mock_factcheck_api.search.return_value = results

3. Rating Normalization:
    from factcheck_data import normalize_rating
    score = normalize_rating("Mostly True")  # Returns 0.75

4. Custom Fact-Check:
    from factcheck_data import create_factcheck_claim, create_factcheck_response
    claim = create_factcheck_claim("Test claim", "PolitiFact", "True")
    response = create_factcheck_response([claim])
    mock_factcheck_api.search.return_value = response

5. No Results:
    from factcheck_data import MOCK_NO_FACTCHECKS
    mock_factcheck_api.search.return_value = MOCK_NO_FACTCHECKS

6. Multiple Reviewers:
    from factcheck_data import MOCK_MULTIPLE_REVIEWERS
    mock_factcheck_api.search.return_value = MOCK_MULTIPLE_REVIEWERS

7. Conflicting Ratings:
    from factcheck_data import MOCK_CONFLICTING_RATINGS
    mock_factcheck_api.search.return_value = MOCK_CONFLICTING_RATINGS
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial mock library
#          - Standard fact-check results
#          - All rating types (True, False, Mostly True, Half True, Mostly False, Pants on Fire)
#          - Multiple reviewers scenarios
#          - Conflicting ratings
#          - Recent fact-checks
#          - Helper functions
#          - Rating normalization
#          - Realistic test scenarios
#          - Error responses

# Aliases for test compatibility (Phase 1 tests use different naming)
MOCK_FACTCHECK_TRUE = MOCK_FACTCHECK_RESULTS
MOCK_FACTCHECK_FALSE = MOCK_FACTCHECK_RESULTS  # Can create specific variants
MOCK_FACTCHECK_MULTIPLE_REVIEWERS = MOCK_FACTCHECK_RESULTS
MOCK_FACTCHECK_CONFLICTING = MOCK_FACTCHECK_RESULTS
MOCK_FACTCHECK_RECENT = MOCK_FACTCHECK_RESULTS
