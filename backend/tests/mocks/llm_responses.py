"""
Mock LLM Responses for Testing

Purpose: Realistic OpenAI API responses for claim extraction and query answering
Model: gpt-4o-mini-2024-07-18

This module provides mock responses matching the actual LLM output formats
used in the Tru8 pipeline. All responses are production-realistic.

Usage:
    from llm_responses import MOCK_CLAIM_EXTRACTION
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content=MOCK_CLAIM_EXTRACTION))]
    )
"""

import json
from typing import Dict, Any, List

# ==================== CLAIM EXTRACTION RESPONSES ====================

MOCK_CLAIM_EXTRACTION = json.dumps(
    {
        "claims": [
            {
                "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
                "position": 0,
                "subject_context": "Climate agreement",
                "key_entities": [
                    {"text": "195 countries", "type": "AMOUNT"},
                    {"text": "45%", "type": "AMOUNT"},
                    {"text": "2030", "type": "DATE"},
                    {"text": "carbon emissions", "type": "OTHER"},
                ],
                "temporal_markers": ["by 2030"],
                "time_reference": "future",
                "is_time_sensitive": True,
                "claim_type": "empirical",
            },
            {
                "text": "Global temperatures have risen by 1.1°C since pre-industrial times",
                "position": 1,
                "subject_context": "Climate change",
                "key_entities": [
                    {"text": "global temperatures", "type": "OTHER"},
                    {"text": "1.1°C", "type": "AMOUNT"},
                    {"text": "pre-industrial times", "type": "DATE"},
                ],
                "temporal_markers": ["since pre-industrial times"],
                "time_reference": "historical",
                "is_time_sensitive": False,
                "claim_type": "empirical",
            },
            {
                "text": "The agreement includes $100 billion in annual funding for developing nations",
                "position": 2,
                "subject_context": "Climate funding",
                "key_entities": [
                    {"text": "$100 billion", "type": "AMOUNT"},
                    {"text": "annual funding", "type": "OTHER"},
                    {"text": "developing nations", "type": "LOCATION"},
                ],
                "temporal_markers": ["annual"],
                "time_reference": "current",
                "is_time_sensitive": True,
                "claim_type": "empirical",
            },
            {
                "text": "Renewable energy capacity grew by 9.6% in 2023",
                "position": 3,
                "subject_context": "Renewable energy",
                "key_entities": [
                    {"text": "renewable energy capacity", "type": "OTHER"},
                    {"text": "9.6%", "type": "AMOUNT"},
                    {"text": "2023", "type": "DATE"},
                ],
                "temporal_markers": ["in 2023"],
                "time_reference": "specific_year",
                "is_time_sensitive": True,
                "claim_type": "empirical",
            },
        ]
    }
)

# Extraction with non-verifiable claim
MOCK_EXTRACTION_WITH_OPINION = json.dumps(
    {
        "claims": [
            {
                "text": "The climate targets are insufficient",
                "position": 0,
                "subject_context": "Climate policy",
                "key_entities": ["climate targets"],
                "temporal_markers": [],
                "time_reference": None,
                "is_time_sensitive": False,
                "claim_type": "value_judgment",
            }
        ]
    }
)

# Extraction with no claims
MOCK_EXTRACTION_EMPTY = json.dumps({"claims": []})

# Extraction with prediction
MOCK_EXTRACTION_PREDICTION = json.dumps(
    {
        "claims": [
            {
                "text": "Global temperatures will rise by 2°C by 2050",
                "position": 0,
                "subject_context": "Climate projection",
                "key_entities": ["global temperatures", "2°C", "2050"],
                "temporal_markers": ["by 2050"],
                "time_reference": "future",
                "is_time_sensitive": True,
                "claim_type": "causal",
            }
        ]
    }
)

# ==================== QUERY ANSWERING RESPONSES ====================

MOCK_QUERY_ANSWER_HIGH_CONFIDENCE = json.dumps(
    {
        "answer": "According to authoritative sources, 195 countries agreed to reduce carbon emissions by 45% "
        "by 2030 at the recent climate summit. This agreement was reached on November 1, 2024, and "
        "includes binding commitments from participating nations.",
        "confidence": 85,
        "sources": [
            "BBC News - Climate summit reaches historic agreement",
            "Reuters - World leaders commit to emissions cuts",
        ],
    }
)

MOCK_QUERY_ANSWER_LOW_CONFIDENCE = json.dumps(
    {
        "answer": None,
        "confidence": 25,
        "related_claims": [
            "195 countries agreed to reduce carbon emissions by 45% by 2030",
            "Global temperatures have risen by 1.1°C since pre-industrial times",
            "Renewable energy capacity grew by 9.6% in 2023",
        ],
    }
)

# ==================== ERROR RESPONSES ====================

MOCK_LLM_ERROR_RESPONSE = {
    "error": {
        "message": "Rate limit exceeded",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded",
    }
}

MOCK_LLM_TIMEOUT_RESPONSE = {
    "error": {"message": "Request timeout", "type": "timeout", "code": "timeout"}
}

# ==================== HELPER FUNCTIONS ====================


def create_mock_llm_response(
    content: str, model: str = "gpt-4o-mini-2024-07-18"
) -> Dict[str, Any]:
    """Create a properly formatted mock LLM response."""
    return {
        "id": "chatcmpl-mock123",
        "object": "chat.completion",
        "created": 1699000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


def get_mock_extraction(num_claims: int = 4, include_opinion: bool = False) -> str:
    """Get a mock claim extraction response with specified characteristics."""
    if num_claims == 0:
        return MOCK_EXTRACTION_EMPTY

    if include_opinion:
        return MOCK_EXTRACTION_WITH_OPINION

    return MOCK_CLAIM_EXTRACTION


def get_mock_query_answer(high_confidence: bool = True) -> str:
    """Get a mock query answer response."""
    if high_confidence:
        return MOCK_QUERY_ANSWER_HIGH_CONFIDENCE
    else:
        return MOCK_QUERY_ANSWER_LOW_CONFIDENCE


# ==================== PRODUCTION-REALISTIC TEST CASES ====================

# Test case: Complex article with multiple claim types
MOCK_COMPLEX_EXTRACTION = json.dumps(
    {
        "claims": [
            {
                "text": "The S&P 500 closed at 4,783.45 on November 1, 2024",
                "position": 0,
                "subject_context": "Stock market",
                "key_entities": ["S&P 500", "4,783.45", "November 1, 2024"],
                "temporal_markers": ["on November 1, 2024"],
                "time_reference": "specific_date",
                "is_time_sensitive": True,
                "claim_type": "empirical",
            },
            {
                "text": "This is the best economic policy in decades",
                "position": 1,
                "subject_context": "Economic policy",
                "key_entities": ["economic policy", "decades"],
                "temporal_markers": ["decades"],
                "time_reference": None,
                "is_time_sensitive": False,
                "claim_type": "value_judgment",
            },
            {
                "text": "Interest rates will rise by 0.5% in the next quarter",
                "position": 2,
                "subject_context": "Interest rates",
                "key_entities": ["interest rates", "0.5%", "next quarter"],
                "temporal_markers": ["next quarter"],
                "time_reference": "future",
                "is_time_sensitive": True,
                "claim_type": "causal",
            },
            {
                "text": "The Federal Reserve was established in 1913",
                "position": 3,
                "subject_context": "Federal Reserve",
                "key_entities": ["Federal Reserve", "1913"],
                "temporal_markers": ["1913"],
                "time_reference": "historical",
                "is_time_sensitive": False,
                "claim_type": "empirical",
            },
        ]
    }
)

# Test case: Meta-claim (article about fact-checking)
MOCK_META_CLAIM_EXTRACTION = json.dumps(
    {
        "claims": [
            {
                "text": "PolitiFact rated the statement as 'Mostly True'",
                "position": 0,
                "subject_context": "Fact-check result",
                "key_entities": ["PolitiFact", "Mostly True"],
                "temporal_markers": [],
                "time_reference": None,
                "is_time_sensitive": False,
                "claim_type": "empirical",
            }
        ]
    }
)
