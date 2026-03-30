"""Tests for checks API helpers: serialization, validation, and camelCase conversion.

Covers _sanitize_strings, _claim_map_to_camel_case, _convert_element,
_serialize_evidence, safe_json_dumps, and _validate_and_create_check.
"""

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.checks import (
    _sanitize_strings,
    _claim_map_to_camel_case,
    _convert_element,
    _serialize_evidence,
    safe_json_dumps,
    _validate_and_create_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(**overrides):
    """Create a mock Evidence object with all required attributes."""
    defaults = {
        "id": 1,
        "evidence_id": "ev-123",
        "source": "example.com",
        "url": "https://example.com/article",
        "title": "Test Article",
        "snippet": "Test snippet",
        "published_date": None,
        "relevance_score": 0.85,
        "tier": "primary",
        "evidence_type": "news",
        "receipt_status": "shown",
        "corroboration_group_id": None,
        "corroborating_evidence_ids": None,
        "is_factcheck": False,
        "external_source_provider": None,
        "source_type": "web",
        "archived_url": None,
        "factcheck_publisher": None,
        "factcheck_rating": None,
        "context_before": None,
        "context_after": None,
        "llm_relevance_score": None,
        "classification_method": None,
        "content_basis": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_body(**overrides):
    """Create a mock request body for _validate_and_create_check."""
    defaults = {
        "input_type": "text",
        "content": "The earth is flat",
        "url": None,
        "file_path": None,
        "user_query": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_user(**overrides):
    """Create a mock User with standard attributes."""
    defaults = {
        "id": "user-1",
        "email": "test@example.com",
        "credits": 10,
        "total_credits_used": 0,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# _snake_to_camel (tested indirectly via _claim_map_to_camel_case)
# ---------------------------------------------------------------------------


class TestSnakeToCamel:
    """Test the internal _snake_to_camel conversion via public functions."""

    def test_single_word(self):
        result = _claim_map_to_camel_case({"name": "value"})
        assert "name" in result

    def test_two_words(self):
        result = _claim_map_to_camel_case({"claim_id": "c1"})
        assert "claimId" in result
        assert "claim_id" not in result

    def test_three_words(self):
        result = _claim_map_to_camel_case({"evidence_refs_count": 5})
        assert "evidenceRefsCount" in result
        assert "evidence_refs_count" not in result


# ---------------------------------------------------------------------------
# _sanitize_strings
# ---------------------------------------------------------------------------


class TestSanitizeStrings:
    def test_sanitize_strings_nested(self):
        mojibake = "\u2019".encode("utf-8").decode("latin-1")
        data = {"a": [{"b": mojibake}]}
        result = _sanitize_strings(data)
        assert result == {"a": [{"b": "\u2019"}]}

    def test_sanitize_strings_passthrough(self):
        assert _sanitize_strings(42) == 42
        assert _sanitize_strings(None) is None
        assert _sanitize_strings(3.14) == 3.14
        assert _sanitize_strings(True) is True


# ---------------------------------------------------------------------------
# _claim_map_to_camel_case
# ---------------------------------------------------------------------------


class TestClaimMapToCamelCase:
    def test_claim_map_to_camel_case_keys(self):
        cm = {"normalised_claim": "test", "claim_id": "c1", "claim_type": "empirical"}
        result = _claim_map_to_camel_case(cm)
        assert "normalisedClaim" in result
        assert "claimId" in result
        assert "claimType" in result
        assert result["normalisedClaim"] == "test"

    def test_claim_map_to_camel_case_elements(self):
        cm = {
            "claim_id": "c1",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "Test",
                    "evidence_refs": [
                        {"evidence_id": "ev-1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ],
        }
        result = _claim_map_to_camel_case(cm)
        elem = result["elements"][0]
        assert "elementId" in elem
        assert "evidenceRefs" in elem
        assert elem["evidenceRefs"][0]["evidenceId"] == "ev-1"

    def test_claim_map_to_camel_case_metadata(self):
        cm = {
            "claim_id": "c1",
            "metadata": {"decomposition_model": "test-model", "element_count": 3},
        }
        result = _claim_map_to_camel_case(cm)
        meta = result["metadata"]
        assert "decompositionModel" in meta
        assert "elementCount" in meta
        assert meta["decompositionModel"] == "test-model"

    def test_empty_claim_map(self):
        assert _claim_map_to_camel_case(None) is None
        assert _claim_map_to_camel_case({}) == {}

    def test_claim_map_with_none_values(self):
        cm = {"claim_id": "c1", "orientation": None, "normalised_claim": None}
        result = _claim_map_to_camel_case(cm)
        assert result["orientation"] is None
        assert result["normalisedClaim"] is None


# ---------------------------------------------------------------------------
# _convert_element
# ---------------------------------------------------------------------------


class TestConvertElement:
    def test_convert_element_refs(self):
        elem = {
            "element_id": "e1",
            "evidence_refs": [
                {"evidence_id": "ev-1", "relationship": "supports"},
                {"evidence_id": "ev-2", "relationship": "challenges"},
            ],
            "state": "supported",
        }
        result = _convert_element(elem)
        assert "elementId" in result
        assert "evidenceRefs" in result
        assert len(result["evidenceRefs"]) == 2
        assert result["evidenceRefs"][0]["evidenceId"] == "ev-1"
        assert result["evidenceRefs"][1]["relationship"] == "challenges"

    def test_element_with_empty_refs(self):
        elem = {
            "element_id": "e1",
            "evidence_refs": [],
            "state": "unresolved",
        }
        result = _convert_element(elem)
        assert result["evidenceRefs"] == []

    def test_convert_element_non_dict(self):
        assert _convert_element("not a dict") == "not a dict"
        assert _convert_element(None) is None


# ---------------------------------------------------------------------------
# _serialize_evidence
# ---------------------------------------------------------------------------


class TestSerializeEvidence:
    def test_serialize_evidence_standard(self):
        ev = _make_evidence()
        result = _serialize_evidence(ev)
        assert result["id"] == 1
        assert result["evidenceId"] == "ev-123"
        assert result["source"] == "example.com"
        assert result["url"] == "https://example.com/article"
        assert result["title"] == "Test Article"
        assert result["snippet"] == "Test snippet"
        assert result["relevanceScore"] == 0.85
        assert result["tier"] == "primary"
        assert result["evidenceType"] == "news"
        assert result["receiptStatus"] == "shown"
        assert result["isFactcheck"] is False
        assert result["sourceType"] == "web"
        # Factcheck detail fields should NOT be present by default
        assert "factcheckPublisher" not in result
        assert "factcheckRating" not in result

    def test_serialize_evidence_factcheck_detail(self):
        ev = _make_evidence(
            is_factcheck=True,
            factcheck_publisher="PolitiFact",
            factcheck_rating="True",
            context_before="Before text.",
            context_after="After text.",
        )
        result = _serialize_evidence(ev, include_factcheck_detail=True)
        assert result["factcheckPublisher"] == "PolitiFact"
        assert result["factcheckRating"] == "True"
        assert result["contextBefore"] == "Before text."
        assert result["contextAfter"] == "After text."

    def test_serialize_evidence_missing_fields(self):
        ev = _make_evidence(
            published_date=None,
            corroboration_group_id=None,
            corroborating_evidence_ids=None,
            external_source_provider=None,
            archived_url=None,
        )
        result = _serialize_evidence(ev)
        assert result["publishedDate"] is None
        assert result["corroborationGroupId"] is None
        assert result["corroboratingEvidenceIds"] is None
        assert result["externalSourceProvider"] is None
        assert result["archivedUrl"] is None

    def test_serialize_evidence_published_date_format(self):
        ev = _make_evidence(published_date=datetime(2026, 1, 15, 12, 0, 0))
        result = _serialize_evidence(ev)
        assert result["publishedDate"] == "2026-01-15T12:00:00"


# ---------------------------------------------------------------------------
# safe_json_dumps
# ---------------------------------------------------------------------------


class TestSafeJsonDumps:
    def test_safe_json_dumps_ascii(self):
        data = {"text": "caf\u00e9", "count": 3}
        result = safe_json_dumps(data)
        # Must be valid JSON
        parsed = json.loads(result)
        assert parsed["count"] == 3
        # ensure_ascii=True means non-ASCII chars are escaped
        assert "\\u" in result or all(ord(c) < 128 for c in result)
        # No extra whitespace (compact separators)
        assert " " not in result.replace("caf", "")  # separators have no spaces

    def test_safe_json_dumps_mojibake_fixed(self):
        mojibake = "\u2019".encode("utf-8").decode("latin-1")
        data = {"quote": mojibake}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        # The mojibake should be fixed back to the right single quotation mark
        assert parsed["quote"] == "\u2019"


# ---------------------------------------------------------------------------
# _validate_and_create_check
# ---------------------------------------------------------------------------


class TestValidateAndCreateCheck:
    """Tests for the async _validate_and_create_check function."""

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_url_type_requires_url(self, mock_get_user):
        mock_get_user.return_value = _make_user()
        mock_session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(input_type="url", url=None)

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_create_check(body, {"sub": "user-1"}, mock_session)
            assert exc_info.value.status_code == 400
            assert "URL is required" in str(exc_info.value.detail)

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_text_type_requires_content(self, mock_get_user):
        mock_get_user.return_value = _make_user()
        mock_session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(input_type="text", content=None)

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_create_check(body, {"sub": "user-1"}, mock_session)
            assert exc_info.value.status_code == 400
            assert "Content is required" in str(exc_info.value.detail)

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_search_clarity_max_200(self, mock_get_user):
        mock_get_user.return_value = _make_user()
        mock_session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(user_query="x" * 201)

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_create_check(body, {"sub": "user-1"}, mock_session)
            assert exc_info.value.status_code == 400
            assert "200 characters" in str(exc_info.value.detail)

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_invalid_input_type(self, mock_get_user):
        mock_get_user.return_value = _make_user()
        mock_session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(input_type="invalid")

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_create_check(body, {"sub": "user-1"}, mock_session)
            assert exc_info.value.status_code == 400
            assert "Invalid input type" in str(exc_info.value.detail)

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_creates_check_record(self, mock_get_user):
        mock_user = _make_user()
        mock_get_user.return_value = mock_user
        mock_session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(input_type="text", content="The earth is flat")

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            user, check = await _validate_and_create_check(
                body, {"sub": "user-1"}, mock_session
            )

        assert user is mock_user
        # session.add should have been called with the Check
        mock_session.add.assert_called_once()
        created_check = mock_session.add.call_args[0][0]
        assert created_check.input_type == "text"
        assert created_check.status == "processing"
        assert created_check.credits_used == 1
        assert created_check.user_id == "user-1"
        mock_session.commit.assert_awaited_once()

    @patch("app.api.v1.checks.get_or_create_user", new_callable=AsyncMock)
    async def test_credit_exhausted_raises_402(self, mock_get_user):
        mock_user = _make_user(credits=0, total_credits_used=3)
        mock_get_user.return_value = mock_user
        mock_session = AsyncMock()

        # No subscription
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_sub_result)

        body = _make_body(input_type="text", content="claim text")

        with patch("app.api.v1.checks.settings") as mock_settings:
            mock_settings.DEBUG = False
            mock_settings.BETA_TESTER_EMAILS = []
            mock_settings.ADMIN_EMAILS = []
            mock_settings.ENABLE_SEARCH_CLARITY = True

            with pytest.raises(HTTPException) as exc_info:
                await _validate_and_create_check(body, {"sub": "user-1"}, mock_session)
            assert exc_info.value.status_code == 402
            assert "Free trial exhausted" in str(exc_info.value.detail)
