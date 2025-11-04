"""
Mock LLM Responses for Testing

Created: 2025-11-03 15:10:00 UTC
Last Updated: 2025-11-03 15:10:00 UTC
Code Version: commit 388ac66
Purpose: Realistic OpenAI API responses for claim extraction, judgment, and query answering
Model: gpt-4o-mini-2024-07-18

This module provides mock responses matching the actual LLM output formats
used in the Tru8 pipeline. All responses are production-realistic.

Usage:
    from llm_responses import MOCK_CLAIM_EXTRACTION
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content=MOCK_CLAIM_EXTRACTION))]
    )

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

import json
from typing import Dict, Any, List

# ==================== CLAIM EXTRACTION RESPONSES ====================

MOCK_CLAIM_EXTRACTION = json.dumps({
    "claims": [
        {
            "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
            "position": 0,
            "subject_context": "Climate agreement",
            "key_entities": ["195 countries", "45%", "2030", "carbon emissions"],
            "temporal_markers": ["by 2030"],
            "time_reference": "future",
            "is_time_sensitive": True,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Specific measurable claim with verifiable numbers and dates"
        },
        {
            "text": "Global temperatures have risen by 1.1°C since pre-industrial times",
            "position": 1,
            "subject_context": "Climate change",
            "key_entities": ["global temperatures", "1.1°C", "pre-industrial times"],
            "temporal_markers": ["since pre-industrial times"],
            "time_reference": "historical",
            "is_time_sensitive": False,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Scientific measurement with specific numerical value"
        },
        {
            "text": "The agreement includes $100 billion in annual funding for developing nations",
            "position": 2,
            "subject_context": "Climate funding",
            "key_entities": ["$100 billion", "annual funding", "developing nations"],
            "temporal_markers": ["annual"],
            "time_reference": "current",
            "is_time_sensitive": True,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Specific financial commitment that can be verified"
        },
        {
            "text": "Renewable energy capacity grew by 9.6% in 2023",
            "position": 3,
            "subject_context": "Renewable energy",
            "key_entities": ["renewable energy capacity", "9.6%", "2023"],
            "temporal_markers": ["in 2023"],
            "time_reference": "specific_year",
            "is_time_sensitive": True,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Historical statistic with specific year and percentage"
        }
    ]
})

# Extraction with non-verifiable claim
MOCK_EXTRACTION_WITH_OPINION = json.dumps({
    "claims": [
        {
            "text": "The climate targets are insufficient",
            "position": 0,
            "subject_context": "Climate policy",
            "key_entities": ["climate targets"],
            "temporal_markers": [],
            "time_reference": None,
            "is_time_sensitive": False,
            "claim_type": "opinion",
            "is_verifiable": False,
            "verifiability_reason": "Subjective evaluation without measurable criteria"
        }
    ]
})

# Extraction with no claims
MOCK_EXTRACTION_EMPTY = json.dumps({"claims": []})

# Extraction with prediction
MOCK_EXTRACTION_PREDICTION = json.dumps({
    "claims": [
        {
            "text": "Global temperatures will rise by 2°C by 2050",
            "position": 0,
            "subject_context": "Climate projection",
            "key_entities": ["global temperatures", "2°C", "2050"],
            "temporal_markers": ["by 2050"],
            "time_reference": "future",
            "is_time_sensitive": True,
            "claim_type": "prediction",
            "is_verifiable": False,
            "verifiability_reason": "Future prediction that cannot currently be verified"
        }
    ]
})

# ==================== JUDGMENT RESPONSES ====================

MOCK_JUDGMENT_SUPPORTED = json.dumps({
    "verdict": "supported",
    "confidence": 0.85,
    "rationale": "The claim is supported by multiple high-credibility sources including BBC News and Reuters. "
                 "Both sources confirm that 195 countries agreed to reduce carbon emissions by 45% by 2030 "
                 "at the recent climate summit. The sources are recent (within 24 hours), independent, "
                 "and have strong journalistic credibility. The numerical targets (195 countries, 45%, 2030) "
                 "are consistently reported across sources."
})

MOCK_JUDGMENT_CONTRADICTED = json.dumps({
    "verdict": "contradicted",
    "confidence": 0.78,
    "rationale": "The claim is contradicted by authoritative sources. According to NOAA and NASA data, "
                 "global temperatures have risen by 1.2°C since pre-industrial times, not 1.1°C as claimed. "
                 "The most recent scientific consensus (IPCC AR6) confirms the 1.2°C figure. "
                 "While the difference is small, the claim's specific numerical value is inaccurate."
})

MOCK_JUDGMENT_UNCERTAIN = json.dumps({
    "verdict": "uncertain",
    "confidence": 0.45,
    "rationale": "Evidence for this claim is mixed. While some sources suggest renewable energy capacity "
                 "grew significantly in 2023, the specific 9.6% figure cannot be confirmed. "
                 "The International Energy Agency reports growth between 8-11% depending on methodology. "
                 "There is insufficient authoritative consensus to support or contradict the exact percentage."
})

MOCK_JUDGMENT_INSUFFICIENT_EVIDENCE = json.dumps({
    "verdict": "insufficient_evidence",
    "confidence": 0.20,
    "rationale": "We found only 2 sources discussing this claim, both with low credibility scores (<0.60). "
                 "The minimum requirement of 3 high-quality sources was not met. Without additional "
                 "evidence from authoritative sources, we cannot make a reliable determination."
})

MOCK_JUDGMENT_CONFLICTING_EXPERTS = json.dumps({
    "verdict": "conflicting_expert_opinion",
    "confidence": 0.35,
    "rationale": "High-credibility sources provide conflicting information. NASA reports 1.2°C warming, "
                 "while the UK Met Office reports 1.1°C, and NOAA reports 1.15°C. All sources are "
                 "highly credible (>0.85) but disagree on the exact figure due to different methodologies "
                 "and measurement periods. Expert consensus is unclear."
})

MOCK_JUDGMENT_OUTDATED = json.dumps({
    "verdict": "outdated_claim",
    "confidence": 0.30,
    "rationale": "This claim refers to events from 2020, but the most recent available evidence is from 2018. "
                 "All retrieved sources are more than 2 years old relative to the claim's timeframe. "
                 "We cannot verify current or recent claims with outdated evidence."
})

# ==================== QUERY ANSWERING RESPONSES ====================

MOCK_QUERY_ANSWER_HIGH_CONFIDENCE = json.dumps({
    "answer": "According to authoritative sources, 195 countries agreed to reduce carbon emissions by 45% "
              "by 2030 at the recent climate summit. This agreement was reached on November 1, 2024, and "
              "includes binding commitments from participating nations.",
    "confidence": 85,
    "sources": [
        "BBC News - Climate summit reaches historic agreement",
        "Reuters - World leaders commit to emissions cuts"
    ]
})

MOCK_QUERY_ANSWER_LOW_CONFIDENCE = json.dumps({
    "answer": None,
    "confidence": 25,
    "related_claims": [
        "195 countries agreed to reduce carbon emissions by 45% by 2030",
        "Global temperatures have risen by 1.1°C since pre-industrial times",
        "Renewable energy capacity grew by 9.6% in 2023"
    ]
})

# ==================== OVERALL ASSESSMENT RESPONSES ====================

MOCK_OVERALL_ASSESSMENT = json.dumps({
    "overall_summary": "The article contains 4 verifiable claims about climate change and energy policy. "
                      "Most claims (75%) are well-supported by authoritative sources. The numerical data "
                      "regarding emissions targets and temperature increases is confirmed by multiple "
                      "high-credibility sources including government agencies and scientific organizations.",
    "credibility_score": 0.82,
    "key_findings": [
        "Strong consensus on climate agreement details (195 countries, 45% target)",
        "Minor discrepancy in temperature rise figure (1.1°C vs 1.2°C)",
        "Renewable energy growth figures align with IEA data"
    ],
    "concerns": [
        "One claim about temperature rise shows slight numerical inaccuracy",
        "Some financial commitment details lack independent verification"
    ]
})

# ==================== ERROR RESPONSES ====================

MOCK_LLM_ERROR_RESPONSE = {
    "error": {
        "message": "Rate limit exceeded",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded"
    }
}

MOCK_LLM_TIMEOUT_RESPONSE = {
    "error": {
        "message": "Request timeout",
        "type": "timeout",
        "code": "timeout"
    }
}

# ==================== HELPER FUNCTIONS ====================

def create_mock_llm_response(content: str, model: str = "gpt-4o-mini-2024-07-18") -> Dict[str, Any]:
    """
    Create a properly formatted mock LLM response

    Args:
        content: The content to return
        model: Model name

    Returns:
        Dict matching OpenAI API response format

    Created: 2025-11-03
    """
    return {
        "id": "chatcmpl-mock123",
        "object": "chat.completion",
        "created": 1699000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


def get_mock_extraction(num_claims: int = 4, include_opinion: bool = False) -> str:
    """
    Get a mock claim extraction response with specified characteristics

    Args:
        num_claims: Number of claims to include (1-12)
        include_opinion: Whether to include non-verifiable opinion

    Returns:
        JSON string with claim extraction

    Created: 2025-11-03
    """
    if num_claims == 0:
        return MOCK_EXTRACTION_EMPTY

    if include_opinion:
        return MOCK_EXTRACTION_WITH_OPINION

    # Default: return standard extraction
    return MOCK_CLAIM_EXTRACTION


def get_mock_judgment(verdict: str = "supported") -> str:
    """
    Get a mock judgment response with specified verdict

    Args:
        verdict: One of: supported, contradicted, uncertain,
                 insufficient_evidence, conflicting_expert_opinion, outdated_claim

    Returns:
        JSON string with judgment

    Created: 2025-11-03
    """
    verdict_map = {
        "supported": MOCK_JUDGMENT_SUPPORTED,
        "contradicted": MOCK_JUDGMENT_CONTRADICTED,
        "uncertain": MOCK_JUDGMENT_UNCERTAIN,
        "insufficient_evidence": MOCK_JUDGMENT_INSUFFICIENT_EVIDENCE,
        "conflicting_expert_opinion": MOCK_JUDGMENT_CONFLICTING_EXPERTS,
        "outdated_claim": MOCK_JUDGMENT_OUTDATED
    }

    return verdict_map.get(verdict, MOCK_JUDGMENT_SUPPORTED)


def get_mock_query_answer(high_confidence: bool = True) -> str:
    """
    Get a mock query answer response

    Args:
        high_confidence: If True, return direct answer (≥40% confidence)
                        If False, return related claims

    Returns:
        JSON string with query answer

    Created: 2025-11-03
    """
    if high_confidence:
        return MOCK_QUERY_ANSWER_HIGH_CONFIDENCE
    else:
        return MOCK_QUERY_ANSWER_LOW_CONFIDENCE


# ==================== PRODUCTION-REALISTIC TEST CASES ====================

# Test case: Complex article with multiple claim types
MOCK_COMPLEX_EXTRACTION = json.dumps({
    "claims": [
        # Factual, time-sensitive
        {
            "text": "The S&P 500 closed at 4,783.45 on November 1, 2024",
            "position": 0,
            "subject_context": "Stock market",
            "key_entities": ["S&P 500", "4,783.45", "November 1, 2024"],
            "temporal_markers": ["on November 1, 2024"],
            "time_reference": "specific_date",
            "is_time_sensitive": True,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Specific financial data with exact date and value"
        },
        # Opinion
        {
            "text": "This is the best economic policy in decades",
            "position": 1,
            "subject_context": "Economic policy",
            "key_entities": ["economic policy", "decades"],
            "temporal_markers": ["decades"],
            "time_reference": None,
            "is_time_sensitive": False,
            "claim_type": "opinion",
            "is_verifiable": False,
            "verifiability_reason": "Subjective evaluation lacking objective criteria"
        },
        # Prediction
        {
            "text": "Interest rates will rise by 0.5% in the next quarter",
            "position": 2,
            "subject_context": "Interest rates",
            "key_entities": ["interest rates", "0.5%", "next quarter"],
            "temporal_markers": ["next quarter"],
            "time_reference": "future",
            "is_time_sensitive": True,
            "claim_type": "prediction",
            "is_verifiable": False,
            "verifiability_reason": "Future prediction that cannot be verified currently"
        },
        # Historical fact
        {
            "text": "The Federal Reserve was established in 1913",
            "position": 3,
            "subject_context": "Federal Reserve",
            "key_entities": ["Federal Reserve", "1913"],
            "temporal_markers": ["1913"],
            "time_reference": "historical",
            "is_time_sensitive": False,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Well-established historical fact with specific date"
        }
    ]
})

# Test case: Meta-claim (article about fact-checking)
MOCK_META_CLAIM_EXTRACTION = json.dumps({
    "claims": [
        {
            "text": "PolitiFact rated the statement as 'Mostly True'",
            "position": 0,
            "subject_context": "Fact-check result",
            "key_entities": ["PolitiFact", "Mostly True"],
            "temporal_markers": [],
            "time_reference": None,
            "is_time_sensitive": False,
            "claim_type": "factual",
            "is_verifiable": True,
            "verifiability_reason": "Fact-check rating that can be verified from original source"
        }
    ]
})

# ==================== DOCUMENTATION ====================

"""
Usage Examples:

1. Basic Mocking:
    from llm_responses import MOCK_CLAIM_EXTRACTION
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content=MOCK_CLAIM_EXTRACTION))]
    )

2. Dynamic Responses:
    from llm_responses import get_mock_judgment
    content = get_mock_judgment(verdict="contradicted")
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content=content))]
    )

3. Testing Error Handling:
    from llm_responses import MOCK_LLM_ERROR_RESPONSE
    mock_client.chat.completions.create.side_effect = Exception(
        json.dumps(MOCK_LLM_ERROR_RESPONSE)
    )

4. Full Response Format:
    from llm_responses import create_mock_llm_response, MOCK_CLAIM_EXTRACTION
    response = create_mock_llm_response(MOCK_CLAIM_EXTRACTION)
    mock_client.chat.completions.create.return_value = response
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial mock library
#          - Claim extraction responses (standard, opinion, empty, prediction)
#          - Judgment responses (all 6 verdict types)
#          - Query answering responses
#          - Overall assessment responses
#          - Error responses
#          - Helper functions
#          - Production-realistic test cases

# Aliases for test compatibility (Phase 1 tests use different naming)
MOCK_JUDGMENT_INSUFFICIENT = MOCK_JUDGMENT_INSUFFICIENT_EVIDENCE
MOCK_JUDGMENT_NOT_VERIFIABLE = MOCK_JUDGMENT_INSUFFICIENT_EVIDENCE  # Can reuse or create specific
MOCK_JUDGMENT_CONFLICTING = MOCK_JUDGMENT_CONFLICTING_EXPERTS
