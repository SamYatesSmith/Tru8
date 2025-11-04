"""
Tru8 Testing Mocks Package

Created: 2025-11-03 15:35:00 UTC
Last Updated: 2025-11-03 15:35:00 UTC
Code Version: commit 388ac66

This package provides production-realistic mock data for testing:
- LLM responses (OpenAI)
- Search results (Brave/SERP API)
- Fact-check data (Google Fact Check Explorer)
- Sample content (articles, claims, evidence)
- Database fixtures (users, checks, claims, evidence)

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

__version__ = "1.0.0"
__author__ = "Tru8 Testing Team"
__created__ = "2025-11-03"

# Import key components for easy access
try:
    from .llm_responses import (
        MOCK_CLAIM_EXTRACTION,
        MOCK_JUDGMENT_SUPPORTED,
        MOCK_QUERY_ANSWER_HIGH_CONFIDENCE,
        get_mock_extraction,
        get_mock_judgment,
        get_mock_query_answer
    )
except ImportError:
    pass

try:
    from .search_results import (
        MOCK_SEARCH_RESULTS,
        MOCK_HIGH_CREDIBILITY_RESULTS,
        get_search_results_by_credibility
    )
except ImportError:
    pass

try:
    from .factcheck_data import (
        MOCK_FACTCHECK_RESULTS,
        get_factcheck_by_rating,
        normalize_rating
    )
except ImportError:
    pass

try:
    from .sample_content import (
        SAMPLE_ARTICLE_TEXT,
        SAMPLE_CLAIMS,
        SAMPLE_EVIDENCE,
        get_sample_content,
        get_sample_claims,
        get_sample_evidence
    )
except ImportError:
    pass

try:
    from .database import (
        create_test_user,
        create_test_check,
        create_test_claim,
        create_test_evidence,
        create_check_with_full_pipeline_data,
        cleanup_test_data
    )
except ImportError:
    pass

__all__ = [
    # LLM Responses
    "MOCK_CLAIM_EXTRACTION",
    "MOCK_JUDGMENT_SUPPORTED",
    "MOCK_QUERY_ANSWER_HIGH_CONFIDENCE",
    "get_mock_extraction",
    "get_mock_judgment",
    "get_mock_query_answer",
    # Search Results
    "MOCK_SEARCH_RESULTS",
    "MOCK_HIGH_CREDIBILITY_RESULTS",
    "get_search_results_by_credibility",
    # Fact-Check Data
    "MOCK_FACTCHECK_RESULTS",
    "get_factcheck_by_rating",
    "normalize_rating",
    # Sample Content
    "SAMPLE_ARTICLE_TEXT",
    "SAMPLE_CLAIMS",
    "SAMPLE_EVIDENCE",
    "get_sample_content",
    "get_sample_claims",
    "get_sample_evidence",
    # Database
    "create_test_user",
    "create_test_check",
    "create_test_claim",
    "create_test_evidence",
    "create_check_with_full_pipeline_data",
    "cleanup_test_data"
]
