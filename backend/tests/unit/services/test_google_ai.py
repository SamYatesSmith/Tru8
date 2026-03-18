"""
Tests for app.services.google_ai — Gemini client, JSON repair, retry logic.

Covers:
  - _try_parse_json (6 tests)
  - _jittered_delay (3 tests)
  - call_google_ai (4 tests)
  - call_google_ai_with_usage (1 test)
"""

import asyncio
import json

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.google_ai import (
    _try_parse_json,
    _jittered_delay,
    call_google_ai,
    call_google_ai_with_usage,
    _MAX_DELAY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gemini_response(
    text: str, status: int = 200, usage: dict | None = None
) -> MagicMock:
    """Build a mock httpx.Response that looks like a Gemini API reply."""
    body: dict = {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
    }
    if usage is not None:
        body["usageMetadata"] = usage
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body
    resp.headers = {}
    return resp


def _error_response(status: int, retry_after: str | None = None) -> MagicMock:
    """Build a mock httpx.Response for error codes (429, 503, etc.)."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.headers = {}
    if retry_after is not None:
        resp.headers["retry-after"] = retry_after
    return resp


# ---------------------------------------------------------------------------
# TestTryParseJson
# ---------------------------------------------------------------------------


class TestTryParseJson:
    """Tests for the JSON repair utility."""

    def test_parses_clean_json(self):
        result = _try_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_strips_markdown_fences(self):
        text = '```json\n{"name": "test", "count": 42}\n```'
        result = _try_parse_json(text)
        assert result == {"name": "test", "count": 42}

    def test_removes_trailing_commas(self):
        text = '{"a": 1, "b": [2, 3,],}'
        result = _try_parse_json(text)
        assert result is not None
        assert result["a"] == 1
        assert result["b"] == [2, 3]

    def test_repairs_truncated_json(self):
        # Unterminated string + unclosed brace
        text = '{"a": "val'
        result = _try_parse_json(text)
        # Should repair by closing the string and brace
        assert result is not None
        assert result["a"] == "val"

    def test_returns_none_for_garbage(self):
        result = _try_parse_json("this is not json at all, just random text")
        assert result is None

    def test_handles_nested_json(self):
        nested = {
            "outer": {
                "inner": [1, 2, {"deep": True}],
                "flag": False,
            },
            "list": ["a", "b"],
        }
        text = json.dumps(nested)
        result = _try_parse_json(text)
        assert result == nested


# ---------------------------------------------------------------------------
# TestJitteredDelay
# ---------------------------------------------------------------------------


class TestJitteredDelay:
    """Tests for the exponential backoff delay computation."""

    def test_increases_with_attempt(self):
        """Later attempts should have a higher *base* delay (though jitter adds randomness)."""
        # Run many samples to compare statistical tendency
        samples_early = [_jittered_delay(0) for _ in range(200)]
        samples_late = [_jittered_delay(3) for _ in range(200)]
        avg_early = sum(samples_early) / len(samples_early)
        avg_late = sum(samples_late) / len(samples_late)
        assert avg_late > avg_early

    def test_respects_retry_after(self):
        """When retry_after is provided, the delay should be at least that value."""
        retry_floor = 10.0
        for _ in range(50):
            delay = _jittered_delay(0, retry_after=retry_floor)
            assert delay >= retry_floor

    def test_capped_at_max(self):
        """Delay must never exceed _MAX_DELAY (30s)."""
        for attempt in range(10):
            for _ in range(20):
                delay = _jittered_delay(attempt, retry_after=100.0)
                assert delay <= _MAX_DELAY


# ---------------------------------------------------------------------------
# TestCallGoogleAi
# ---------------------------------------------------------------------------


class TestCallGoogleAi:
    """Tests for the main call_google_ai function (mocked httpx)."""

    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        """Ensure settings has API key and model for every test."""
        with patch("app.services.google_ai.settings") as mock_settings:
            mock_settings.GOOGLE_AI_API_KEY = "test-key-123"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash-lite"
            yield mock_settings

    @pytest.fixture(autouse=True)
    def _patch_sleep(self):
        """Eliminate real sleeps during retry back-off."""
        with patch(
            "app.services.google_ai.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            self.mock_sleep = mock_sleep
            yield

    @pytest.fixture(autouse=True)
    def _patch_client(self):
        """Replace the lazy HTTP client with a mock."""
        self.mock_client = AsyncMock(spec=httpx.AsyncClient)
        with patch("app.services.google_ai._get_client", return_value=self.mock_client):
            yield

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """A 200 response with valid JSON is parsed and returned."""
        self.mock_client.post.return_value = _gemini_response('{"answer": 42}')

        result = await call_google_ai("What is the answer?")

        assert result == {"answer": 42}
        self.mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """httpx.TimeoutException should return None immediately (no retry)."""
        self.mock_client.post.side_effect = httpx.TimeoutException("timed out")

        result = await call_google_ai("slow prompt", timeout=5)

        assert result is None
        # Only one call — timeouts are not retried
        assert self.mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        """A 429 on the first attempt should trigger a retry; success on second attempt."""
        self.mock_client.post.side_effect = [
            _error_response(429, retry_after="1"),
            _gemini_response('{"retried": true}'),
        ]

        result = await call_google_ai("rate limited prompt")

        assert result == {"retried": True}
        assert self.mock_client.post.call_count == 2
        # Verify sleep was called for the backoff
        self.mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_after_max_retries(self):
        """When all 5 retry attempts return 429, function returns None."""
        self.mock_client.post.return_value = _error_response(429)

        result = await call_google_ai("always failing prompt")

        assert result is None
        assert self.mock_client.post.call_count == 5

    @pytest.mark.asyncio
    async def test_includes_usage_stats(self):
        """call_google_ai_with_usage returns (parsed, usage_dict) on success."""
        usage_meta = {"promptTokenCount": 100, "candidatesTokenCount": 50}
        self.mock_client.post.return_value = _gemini_response(
            '{"data": "ok"}',
            usage=usage_meta,
        )

        parsed, usage = await call_google_ai_with_usage("prompt with usage")

        assert parsed == {"data": "ok"}
        assert usage == {"input_tokens": 100, "output_tokens": 50}
