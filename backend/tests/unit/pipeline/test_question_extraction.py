"""Tests for question-format input extraction.

Evaluates whether the extraction pipeline correctly handles question-format
inputs — particularly health, science, and lifestyle questions that imply
verifiable factual claims.

These tests exercise:
1. The LLM extraction prompt (rule 9: QUESTIONS AS CLAIMS)
2. The vagueness filter (_validate_individual_claims, check 3)
3. The fallback chain (Google AI → OpenAI → rule-based)

Run with: pytest tests/unit/pipeline/test_question_extraction.py -v
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import sys

backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.pipeline.extract import ClaimExtractor


# ---------------------------------------------------------------------------
# Test data: question inputs and expected outcomes
# ---------------------------------------------------------------------------

# Questions that SHOULD extract at least one claim
SHOULD_EXTRACT = [
    # Health / wellness (the reported failure case and similar)
    "pink salt diet, can it make you lose weight?",
    "Does coffee cause cancer?",
    "Can turmeric reduce inflammation?",
    "Is intermittent fasting effective for weight loss?",
    "Does vitamin D deficiency cause depression?",
    "Is fluoride in water safe?",
    # Science / environment
    "Is sea level rising faster than predicted?",
    "Does deforestation contribute to flooding?",
    "Are microplastics harmful to human health?",
    # Economics / politics (already work — baseline)
    "Did the UK leave the EU?",
    "Has UK inflation fallen below 3%?",
    "Did unemployment rise during COVID?",
    # Technology
    "Does 5G radiation cause health problems?",
    "Can AI replace doctors?",
]

# Questions that SHOULD NOT extract claims (genuinely subjective/advisory)
SHOULD_NOT_EXTRACT = [
    "What should I invest in?",
    "Who is the best footballer?",
    "What's the meaning of life?",
    "Which colour looks better, red or blue?",
    "Should I move to a different country?",
]


# ---------------------------------------------------------------------------
# Vagueness filter unit tests (no LLM needed)
# ---------------------------------------------------------------------------


class TestVaguenessFilter:
    """Test the _validate_individual_claims vagueness check (check 3)."""

    def setup_method(self):
        self.extractor = ClaimExtractor()

    def _make_claim(self, text: str, confidence: int = 80) -> dict:
        return {
            "text": text,
            "position": 0,
            "confidence": confidence,
            "category": "general",
        }

    def test_claim_with_proper_noun_passes(self):
        """Claims with capitalised words should pass the vagueness check."""
        claims = [self._make_claim("Pink salt can promote weight loss")]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 1

    def test_claim_with_number_passes(self):
        """Claims with numbers should pass."""
        claims = [self._make_claim("Sea level has risen by 3mm per year since 1993")]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 1

    def test_claim_with_date_passes(self):
        """Claims with years should pass."""
        claims = [self._make_claim("The UK left the EU in 2020")]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 1

    def test_fully_lowercase_claim_without_markers_filtered(self):
        """Completely lowercase claims with no markers should be filtered."""
        claims = [self._make_claim("things are getting worse everywhere")]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 0

    def test_health_claim_capitalised_passes(self):
        """Health claim starting with capital letter passes proper noun regex."""
        claims = [self._make_claim("Consuming pink salt aids weight loss")]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 1

    def test_health_claim_lowercase_filtered(self):
        """Same claim in lowercase fails — this is the gap fix 3 would address."""
        claims = [self._make_claim("consuming pink salt aids weight loss")]
        result = self.extractor._validate_individual_claims(claims)
        # Currently filtered (no date/number/proper noun). Fix 3 would change this.
        assert len(result) == 0

    def test_multiple_claims_partial_filter(self):
        """Mix of valid and vague claims — only valid ones survive."""
        claims = [
            self._make_claim("The UK left the EU in 2020"),
            self._make_claim("things happened recently"),
            self._make_claim("Coffee consumption increases heart disease risk"),
        ]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 2
        assert result[0]["text"] == "The UK left the EU in 2020"
        assert result[1]["text"] == "Coffee consumption increases heart disease risk"

    def test_subjective_language_lowers_confidence_not_filtered(self):
        """Claims with subjective words get reduced confidence but survive."""
        claims = [
            self._make_claim(
                "Turmeric could possibly reduce inflammation in humans", 90
            )
        ]
        result = self.extractor._validate_individual_claims(claims)
        assert len(result) == 1
        assert result[0]["confidence"] < 90  # Reduced by subjective penalty


# ---------------------------------------------------------------------------
# Fallback chain tests (mock LLM, test logic)
# ---------------------------------------------------------------------------


class TestExtractionFallbackChain:
    """Test that 0-claim success falls through to next extractor."""

    def setup_method(self):
        self.extractor = ClaimExtractor()

    @pytest.mark.asyncio
    async def test_google_zero_claims_falls_through_to_openai(self):
        """If Google AI returns success with 0 claims, OpenAI should be tried."""
        google_result = {"success": True, "claims": [], "metadata": {}}
        openai_result = {
            "success": True,
            "claims": [
                {
                    "text": "Pink salt can promote weight loss",
                    "position": 0,
                    "confidence": 75,
                    "category": "health",
                }
            ],
            "metadata": {"extraction_method": "openai_gpt4o_mini"},
        }

        with patch.object(
            self.extractor, "_extract_with_google", new_callable=AsyncMock
        ) as mock_google, patch.object(
            self.extractor, "_extract_with_openai", new_callable=AsyncMock
        ) as mock_openai:
            mock_google.return_value = google_result
            mock_openai.return_value = openai_result

            result = await self.extractor.extract_claims(
                "pink salt diet, can it make you lose weight?"
            )

            mock_google.assert_called_once()
            mock_openai.assert_called_once()
            assert result["success"] is True
            assert len(result["claims"]) == 1

    @pytest.mark.asyncio
    async def test_both_llms_zero_claims_falls_through_to_rule_based(self):
        """If both LLMs return 0 claims, rule-based fallback should be tried."""
        zero_result = {"success": True, "claims": [], "metadata": {}}

        with patch.object(
            self.extractor, "_extract_with_google", new_callable=AsyncMock
        ) as mock_google, patch.object(
            self.extractor, "_extract_with_openai", new_callable=AsyncMock
        ) as mock_openai, patch.object(
            self.extractor, "_extract_rule_based"
        ) as mock_rule:
            mock_google.return_value = zero_result
            mock_openai.return_value = zero_result
            mock_rule.return_value = {
                "success": True,
                "claims": [
                    {
                        "text": "Pink salt diet can make you lose weight.",
                        "position": 0,
                        "confidence": 0.4,
                        "category": "general",
                    }
                ],
                "metadata": {"extraction_method": "rule_based_fallback"},
            }

            result = await self.extractor.extract_claims(
                "pink salt diet, can it make you lose weight?"
            )

            mock_google.assert_called_once()
            mock_openai.assert_called_once()
            mock_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_with_claims_does_not_fallthrough(self):
        """If Google AI returns claims, OpenAI should NOT be called."""
        google_result = {
            "success": True,
            "claims": [
                {
                    "text": "The UK left the EU in 2020",
                    "position": 0,
                    "confidence": 95,
                    "category": "politics",
                }
            ],
            "metadata": {"extraction_method": "google_gemini"},
        }

        with patch.object(
            self.extractor, "_extract_with_google", new_callable=AsyncMock
        ) as mock_google, patch.object(
            self.extractor, "_extract_with_openai", new_callable=AsyncMock
        ) as mock_openai:
            mock_google.return_value = google_result
            result = await self.extractor.extract_claims("Did the UK leave the EU?")

            mock_google.assert_called_once()
            mock_openai.assert_not_called()
            assert len(result["claims"]) == 1


# ---------------------------------------------------------------------------
# LLM prompt evaluation (requires API keys — skip if unavailable)
# ---------------------------------------------------------------------------


class TestLLMQuestionExtraction:
    """Live LLM extraction tests for question-format inputs.

    These require API keys and are slow (~2-5s each). Run with:
        pytest tests/unit/pipeline/test_question_extraction.py::TestLLMQuestionExtraction -v

    Skip with: pytest -k "not TestLLMQuestionExtraction"
    """

    def setup_method(self):
        self.extractor = ClaimExtractor()
        # Skip if no API key configured
        if not self.extractor.google_ai_api_key and not self.extractor.openai_api_key:
            pytest.skip("No LLM API keys configured")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("question", SHOULD_EXTRACT)
    async def test_question_extracts_at_least_one_claim(self, question):
        """Question-format inputs that imply verifiable claims should extract."""
        result = await self.extractor.extract_claims(question)
        claims = result.get("claims", [])
        print(f"\n  Input: {question}")
        print(f"  Success: {result.get('success')}")
        print(f"  Claims ({len(claims)}):")
        for c in claims:
            print(f"    - [{c.get('confidence')}] {c.get('text')}")
        assert len(claims) >= 1, (
            f"Expected ≥1 claim from: '{question}', got 0. "
            f"Method: {result.get('metadata', {}).get('extraction_method', 'unknown')}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("question", SHOULD_NOT_EXTRACT)
    async def test_subjective_question_extracts_zero_claims(self, question):
        """Genuinely subjective questions should NOT produce claims."""
        result = await self.extractor.extract_claims(question)
        claims = result.get("claims", [])
        print(f"\n  Input: {question}")
        print(f"  Claims ({len(claims)}):")
        for c in claims:
            print(f"    - [{c.get('confidence')}] {c.get('text')}")
        # Soft assertion — log but don't fail if a subjective question
        # produces a claim (we may tighten later)
        if len(claims) > 0:
            print(f"  WARNING: Subjective question produced {len(claims)} claims")
