"""Tests for the Gemini 2.5 -> 3.x thinking-control seam (2026-08-25).

Gemini 2.5 takes ``thinkingConfig.thinkingBudget`` (int). Gemini 3.x rejects
that field with a hard 400 and takes ``thinkingLevel`` (string) instead. Both
directions were verified live on 2026-08-01.

Why this file is worth its weight: ``call_google_ai_with_usage`` returns None on
any terminal non-429/503 WITHOUT retry, and every mapping caller then silently
falls through to the OpenAI path. A model-string change without this branch
would be loud in logs and invisible in the product. These tests pin the branch
so the migration cannot regress into that failure.

The FIRST test class is the important one: the 2.5 request body must stay
byte-identical, because every replay-bench cassette was recorded against it.
"""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.google_ai import (
    _GEMINI3_DEFAULT_FLOOR,
    _GEMINI3_THINKING_FLOOR,
    _is_gemini_3,
    _thinking_config,
    call_google_ai_with_usage,
)


# ---------------------------------------------------------------------------
# Gemini 2.5 — unchanged, byte-identical. Cassettes depend on this.
# ---------------------------------------------------------------------------


class TestGemini25Unchanged:
    def test_budget_zero_still_sends_thinking_budget(self):
        """thinking_budget=0 on 2.5 must still emit the int field, not a level."""
        assert _thinking_config("gemini-2.5-flash", 0) == {"thinkingBudget": 0}

    def test_positive_budget_passes_through_verbatim(self):
        assert _thinking_config("gemini-2.5-flash", 1024) == {"thinkingBudget": 1024}

    def test_flash_lite_matches_flash(self):
        assert _thinking_config("gemini-2.5-flash-lite", 0) == {"thinkingBudget": 0}

    def test_none_budget_omits_the_block_entirely(self):
        """None means omit, so the API default applies and bodies stay stable."""
        assert _thinking_config("gemini-2.5-flash", None) is None

    def test_never_emits_thinking_level_on_25(self):
        """thinkingLevel is a hard 400 on 2.5 — it must never appear."""
        for budget in (0, 1, 1024):
            assert "thinkingLevel" not in _thinking_config("gemini-2.5-flash", budget)


# ---------------------------------------------------------------------------
# Gemini 3.x — thinkingLevel only. thinkingBudget is a hard 400 here.
# ---------------------------------------------------------------------------


class TestGemini3UsesLevel:
    @pytest.mark.parametrize(
        "model",
        [
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.1-flash-lite",
        ],
    )
    def test_never_emits_thinking_budget_on_3x(self, model):
        """The regression that would 400 every call and fall silently to OpenAI."""
        for budget in (0, 1, 1024):
            cfg = _thinking_config(model, budget)
            assert "thinkingBudget" not in cfg, f"{model} would 400 on thinkingBudget"
            assert "thinkingLevel" in cfg

    def test_zero_budget_maps_to_the_models_floor(self):
        """thinking_budget=0 is our 'thinking off' intent -> lowest level available."""
        assert _thinking_config("gemini-3.5-flash-lite", 0) == {
            "thinkingLevel": "minimal"
        }

    def test_unprobed_model_falls_back_to_low_not_minimal(self):
        """3.7-flash documents only low/medium/high — guessing 'minimal' would 400.

        Erring high costs latency; erring low costs a 400 and a silent fallback.
        The default must therefore be the conservative one.
        """
        assert _thinking_config("gemini-3.7-flash", 0) == {"thinkingLevel": "low"}
        assert _GEMINI3_DEFAULT_FLOOR == "low"

    def test_positive_budget_means_thinking_on(self):
        """The MAPPING_THINKING_BUDGET=0 -> =1024 rollback path must still work."""
        cfg = _thinking_config("gemini-3.5-flash-lite", 1024)
        assert cfg == {"thinkingLevel": "low"}

    def test_none_budget_omits_the_block_on_3x_too(self):
        assert _thinking_config("gemini-3.5-flash-lite", None) is None

    def test_every_floor_entry_is_a_valid_level_string(self):
        valid = {"minimal", "low", "medium", "high"}
        for model, level in _GEMINI3_THINKING_FLOOR.items():
            assert level in valid, f"{model} floor {level!r} is not a valid level"


# ---------------------------------------------------------------------------
# Model detection — the failure mode of guessing wrong is a 400 on every call.
# ---------------------------------------------------------------------------


class TestModelDetection:
    @pytest.mark.parametrize(
        "model",
        ["gemini-3.5-flash-lite", "gemini-3.7-flash", "GEMINI-3.6-FLASH", "gemini-3"],
    )
    def test_detects_gemini_3(self, model):
        assert _is_gemini_3(model) is True

    @pytest.mark.parametrize(
        "model",
        ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "", None],
    )
    def test_rejects_non_gemini_3(self, model):
        assert _is_gemini_3(model) is False

    def test_tolerates_whitespace(self):
        assert _is_gemini_3("  gemini-3.5-flash-lite  ") is True


# ---------------------------------------------------------------------------
# Wired: the config must reach the actual request body, not just the helper.
# ---------------------------------------------------------------------------


def _ok_response() -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
    }
    return resp


class TestWiredIntoRequestBody:
    """Testing the helper alone would pass while the call site still sent the
    old field — the exact shape of defect that hid the element-retrieval seam."""

    @pytest.mark.asyncio
    async def test_3x_request_body_carries_level_not_budget(self):
        client = MagicMock()
        client.post = AsyncMock(return_value=_ok_response())
        with patch(
            "app.services.google_ai._get_client", AsyncMock(return_value=client)
        ), patch("app.services.google_ai.settings") as mock_settings:
            mock_settings.GOOGLE_AI_API_KEY = "test-key"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-3.5-flash-lite"
            await call_google_ai_with_usage(
                "prompt", model="gemini-3.5-flash-lite", thinking_budget=0
            )
        body = client.post.call_args.kwargs["json"]
        cfg = body["generationConfig"]["thinkingConfig"]
        assert cfg == {"thinkingLevel": "minimal"}
        assert "thinkingBudget" not in cfg

    @pytest.mark.asyncio
    async def test_25_request_body_is_unchanged(self):
        client = MagicMock()
        client.post = AsyncMock(return_value=_ok_response())
        with patch(
            "app.services.google_ai._get_client", AsyncMock(return_value=client)
        ), patch("app.services.google_ai.settings") as mock_settings:
            mock_settings.GOOGLE_AI_API_KEY = "test-key"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-2.5-flash"
            await call_google_ai_with_usage(
                "prompt", model="gemini-2.5-flash", thinking_budget=0
            )
        body = client.post.call_args.kwargs["json"]
        assert body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}

    @pytest.mark.asyncio
    async def test_no_thinking_block_when_budget_is_none(self):
        client = MagicMock()
        client.post = AsyncMock(return_value=_ok_response())
        with patch(
            "app.services.google_ai._get_client", AsyncMock(return_value=client)
        ), patch("app.services.google_ai.settings") as mock_settings:
            mock_settings.GOOGLE_AI_API_KEY = "test-key"
            mock_settings.GOOGLE_LLM_MODEL = "gemini-3.5-flash-lite"
            await call_google_ai_with_usage("prompt", model="gemini-3.5-flash-lite")
        body = client.post.call_args.kwargs["json"]
        assert "thinkingConfig" not in body["generationConfig"]
