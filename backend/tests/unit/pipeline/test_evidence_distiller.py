"""Evidence Distiller tests.

Tests for:
- Core distillation functionality (text replacement, fallbacks, cleanup)
- Response parsing (valid, malformed, out-of-range)
- Integration flags (quick mode, settings flag)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.pipeline.evidence_distiller import EvidenceDistiller


def _make_evidence(
    text="Some snippet text",
    full_text=None,
    title="Test Article",
    source="example.com",
    url="https://example.com/article",
    content_basis="full",
):
    """Create a minimal evidence dict for testing."""
    item = {
        "evidence_id": "ev-test-1",
        "text": text,
        "title": title,
        "source": source,
        "url": url,
        "content_basis": content_basis,
    }
    if full_text is not None:
        item["_full_text"] = full_text
    return item


LONG_TEXT = "A" * 600  # Above default min_text_length of 500


# ============================================================
# Core functionality
# ============================================================


class TestDistilCoreFunction:
    """Tests for core distillation behaviour."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_replaces_text_with_facts(self):
        """Distilled items should have text replaced with bullet-point facts."""
        distiller = EvidenceDistiller()
        items = [_make_evidence(full_text=LONG_TEXT)]

        mock_response = {"results": [{"index": 0, "facts": ["Fact one.", "Fact two."]}]}

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 100, "output_tokens": 50}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == "- Fact one.\n- Fact two."
        assert items[0]["_distilled"] is True
        assert items[0]["content_basis"] == "distilled"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_skips_items_without_full_text(self):
        """Items with _full_text=None should keep their original text."""
        distiller = EvidenceDistiller()
        original_text = "Original snippet"
        items = [_make_evidence(text=original_text)]  # No _full_text

        await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == original_text
        assert "_distilled" not in items[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_skips_short_articles(self):
        """Items with _full_text shorter than min_text_length should keep snippet."""
        distiller = EvidenceDistiller()
        distiller.min_text_length = 500
        original_text = "Original snippet"
        items = [
            _make_evidence(text=original_text, full_text="Short" * 20)
        ]  # 100 chars

        await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == original_text
        assert "_distilled" not in items[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_fallback_on_llm_failure(self):
        """When LLM returns (None, None), all items should keep their snippets."""
        distiller = EvidenceDistiller()
        original_text = "Original snippet"
        items = [_make_evidence(text=original_text, full_text=LONG_TEXT)]

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(None, None),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == original_text
        assert "_distilled" not in items[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_fallback_on_empty_facts(self):
        """When LLM returns empty facts for an item, keep the original snippet."""
        distiller = EvidenceDistiller()
        original_text = "Original snippet"
        items = [_make_evidence(text=original_text, full_text=LONG_TEXT)]

        mock_response = {"results": [{"index": 0, "facts": []}]}

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 100, "output_tokens": 10}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == original_text
        assert "_distilled" not in items[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_removes_full_text_after_processing(self):
        """_full_text should be removed from ALL items after processing."""
        distiller = EvidenceDistiller()
        items = [
            _make_evidence(full_text=LONG_TEXT),
            _make_evidence(text="No full text"),  # No _full_text
            _make_evidence(full_text="Short"),  # Below threshold
        ]

        mock_response = {"results": [{"index": 0, "facts": ["Fact."]}]}

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 100, "output_tokens": 50}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        for item in items:
            assert "_full_text" not in item

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_caps_facts_per_item(self):
        """Facts exceeding max_facts should be capped."""
        distiller = EvidenceDistiller()
        distiller.max_facts = 3
        items = [_make_evidence(full_text=LONG_TEXT)]

        many_facts = [f"Fact {i}." for i in range(10)]
        mock_response = {"results": [{"index": 0, "facts": many_facts}]}

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 100, "output_tokens": 50}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        # Should have exactly 3 facts
        lines = items[0]["text"].split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_handles_mixed_evidence(self):
        """Batch with some full text and some without should handle both correctly."""
        distiller = EvidenceDistiller()
        items = [
            _make_evidence(text="Snippet A", full_text=LONG_TEXT),
            _make_evidence(text="Snippet B"),  # No full text
            _make_evidence(text="Snippet C", full_text=LONG_TEXT),
        ]

        mock_response = {
            "results": [
                {"index": 0, "facts": ["Fact A."]},
                {"index": 1, "facts": ["Fact C."]},
            ]
        }

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 200, "output_tokens": 50}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        # Item 0 and 2 are distillable; item 1 is skipped
        assert items[0].get("_distilled") is True
        assert items[1]["text"] == "Snippet B"
        assert "_distilled" not in items[1]
        # Item 2 maps to distillable index 1 in the batch
        assert items[2].get("_distilled") is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_batch_splitting(self):
        """More than BATCH_SIZE items should trigger multiple LLM calls."""
        distiller = EvidenceDistiller()
        distiller.BATCH_SIZE = 2
        items = [_make_evidence(full_text=LONG_TEXT) for _ in range(5)]

        mock_response_2 = {
            "results": [
                {"index": 0, "facts": ["F1."]},
                {"index": 1, "facts": ["F2."]},
            ]
        }
        mock_response_1 = {
            "results": [
                {"index": 0, "facts": ["F3."]},
            ]
        }

        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return (mock_response_2, {"input_tokens": 100, "output_tokens": 50})
            return (mock_response_1, {"input_tokens": 100, "output_tokens": 50})

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            side_effect=mock_call,
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        # Should have made 3 calls (2+2+1)
        assert call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_token_usage_accumulated(self):
        """get_token_usage() should sum across multiple LLM calls."""
        distiller = EvidenceDistiller()
        distiller.BATCH_SIZE = 2
        items = [_make_evidence(full_text=LONG_TEXT) for _ in range(3)]

        mock_response = {
            "results": [{"index": 0, "facts": ["F."]}, {"index": 1, "facts": ["F."]}]
        }
        mock_response_1 = {"results": [{"index": 0, "facts": ["F."]}]}

        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (mock_response, {"input_tokens": 100, "output_tokens": 30})
            return (mock_response_1, {"input_tokens": 80, "output_tokens": 20})

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            side_effect=mock_call,
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        usage = distiller.get_token_usage()
        assert usage["input_tokens"] == 180
        assert usage["output_tokens"] == 50


# ============================================================
# Response parsing
# ============================================================


class TestDistilResponseParsing:
    """Tests for LLM response parsing edge cases."""

    @pytest.mark.unit
    def test_parse_valid_response(self):
        """Standard response should parse correctly."""
        distiller = EvidenceDistiller()
        raw = {"results": [{"index": 0, "facts": ["Fact 1.", "Fact 2."]}]}
        result = distiller._parse_response(raw, 1)
        assert result == [["Fact 1.", "Fact 2."]]

    @pytest.mark.unit
    def test_parse_out_of_range_index(self):
        """Out-of-range index entries should be silently ignored."""
        distiller = EvidenceDistiller()
        raw = {
            "results": [
                {"index": 0, "facts": ["Fact."]},
                {"index": 99, "facts": ["Bad."]},
            ]
        }
        result = distiller._parse_response(raw, 1)
        assert result == [["Fact."]]

    @pytest.mark.unit
    def test_parse_empty_response(self):
        """Empty dict should return None (no results key)."""
        distiller = EvidenceDistiller()
        result = distiller._parse_response({}, 2)
        assert result is None

    @pytest.mark.unit
    def test_parse_malformed_facts(self):
        """Non-string items in facts list should be filtered out."""
        distiller = EvidenceDistiller()
        raw = {
            "results": [{"index": 0, "facts": ["Good fact.", 123, None, "Another."]}]
        }
        result = distiller._parse_response(raw, 1)
        assert result == [["Good fact.", "Another."]]


# ============================================================
# Integration flags
# ============================================================


class TestDistilIntegrationFlags:
    """Tests for feature flag behaviour."""

    @pytest.mark.unit
    def test_distil_disabled_in_quick_mode(self):
        """QUICK_CONFIG should have enable_evidence_distillation=False."""
        from app.pipeline.runner import QUICK_CONFIG

        assert QUICK_CONFIG.enable_evidence_distillation is False

    @pytest.mark.unit
    def test_distil_disabled_by_settings_flag(self):
        """When ENABLE_EVIDENCE_DISTILLATION=False, distiller should still work
        but the runner skips the stage (tested here via config flag check)."""
        from app.pipeline.runner import PipelineConfig

        config = PipelineConfig(enable_evidence_distillation=False)
        assert config.enable_evidence_distillation is False

        # Default config has it enabled
        default = PipelineConfig()
        assert default.enable_evidence_distillation is True
