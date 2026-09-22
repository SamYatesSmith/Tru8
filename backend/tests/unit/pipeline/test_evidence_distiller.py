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
        provenance = items[0]["text_provenance"]
        assert provenance["original_snippet"] == "Some snippet text"
        assert provenance["derived_text"] == "- Fact one.\n- Fact two."
        assert provenance["passages"][0]["text"] == LONG_TEXT

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

        # The retained windows are the receipt and survive a failed call intact.
        assert items[0]["text_provenance"]["passages"][0]["text"] == LONG_TEXT
        # The mapper is handed document text, not the short snippet (2026-09-22).
        assert items[0]["text"] != original_text
        assert items[0]["text_provenance"]["derivation"] == "retained_passages"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_distil_fallback_never_downgrades_existing_text(self):
        """The supply floor raises the mapper's text; it must never lower it.

        An item whose snippet already exceeds what the retained windows offer
        keeps the snippet — the floor exists to add context, not to trade one
        short extract for another.
        """
        distiller = EvidenceDistiller()
        original_text = "B" * 900  # longer than the single 600-char window
        items = [_make_evidence(text=original_text, full_text=LONG_TEXT)]

        mock_response = {"results": [{"index": 0, "facts": []}]}

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(mock_response, {"input_tokens": 100, "output_tokens": 10}),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] == original_text
        assert items[0]["content_basis"] != "retained_passages"

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
        """More than batch_size items should trigger multiple LLM calls."""
        distiller = EvidenceDistiller()
        distiller.batch_size = 2
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
        distiller.batch_size = 2
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

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_failed_batch_isolated_from_successful_batch(self):
        """D1 (concurrent batches): a batch that raises keeps snippets for
        ITS items only — sibling batches still apply their facts."""
        distiller = EvidenceDistiller()
        distiller.batch_size = 2
        items = [_make_evidence(full_text=LONG_TEXT) for _ in range(4)]

        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("simulated LLM failure")
            return (
                {
                    "results": [
                        {"index": 0, "facts": ["Fact A."]},
                        {"index": 1, "facts": ["Fact B."]},
                    ]
                },
                {"input_tokens": 50, "output_tokens": 20},
            )

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            side_effect=mock_call,
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        # Batch 1 (items 0-1) failed -> no model facts; supply floor applies
        assert items[0]["content_basis"] == "retained_passages"
        assert items[1]["content_basis"] == "retained_passages"
        # Batch 2 (items 2-3) succeeded -> model facts
        assert items[2]["content_basis"] == "distilled"
        assert items[3]["content_basis"] == "distilled"
        assert items[2]["text"] == "- Fact A."
        # _full_text cleaned up everywhere regardless
        assert all("_full_text" not in it for it in items)


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


# ============================================================
# Supply invariant (2026-09-22)
#
# Four production records reached a journalist-outreach send with correctness
# errors traced to ONE cause: the mapper is serialised `snippet or text`, and
# when distillation returns nothing that text is the item's original ~200-word
# claim-selected snippet — even though the whole article was fetched, windowed
# and is printed to the reader. Measured: the mapper saw 4,282 chars where the
# page showed 63,953 (record b1954873).
#
# Record: audit/2026-09-22_mapper_reads_framing_defect.md
# ============================================================


class TestDistilSupplyInvariant:
    """An item whose full text was fetched must never reach the mapper as a
    bare original snippet."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_facts_fall_back_to_retained_passage_not_snippet(self):
        """Empty fact list: the item keeps document text, not its short snippet.

        Was the defect: `facts: []` was indistinguishable from success for the
        mapper, and the 605-char snippet of a 23,788-char inquiry report is what
        decided the element.
        """
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

        assert items[0]["text"] != original_text
        assert len(items[0]["text"]) > len(original_text)
        # Receipt must explain what the mapper was given.
        assert items[0]["text_provenance"]["derivation"] == "retained_passages"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_llm_failure_falls_back_to_retained_passage(self):
        """A failed call must not silently downgrade the item to its snippet."""
        distiller = EvidenceDistiller()
        original_text = "Original snippet"
        items = [_make_evidence(text=original_text, full_text=LONG_TEXT)]

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(None, None),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["text"] != original_text
        assert items[0]["text_provenance"]["derivation"] == "retained_passages"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fallback_never_writes_snippet_field(self):
        """The classifier reads `snippet` concurrently — distil writes `text` only.

        runner.py documents these stages as writing disjoint fields.
        """
        distiller = EvidenceDistiller()
        items = [_make_evidence(full_text=LONG_TEXT)]
        items[0]["snippet"] = "classifier reads this"

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new_callable=AsyncMock,
            return_value=(None, None),
        ):
            await distiller.distil_evidence_for_claim("Test claim", items)

        assert items[0]["snippet"] == "classifier reads this"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_elements_reach_the_prompt_with_passage_mapping_off(self):
        """The elements are the point: a fact bearing on element 3 alone is what
        decides element 3. They were gated behind ENABLE_PASSAGE_MAPPING, which
        is off in production."""
        from app.core.config import settings

        distiller = EvidenceDistiller()
        items = [_make_evidence(full_text=LONG_TEXT)]
        elements = [
            {"element_id": "e1", "description": "Bank Rate was cut in September."},
            {"element_id": "e2", "description": "The cut was 25 basis points."},
        ]

        captured = {}

        async def _capture(prompt, **kwargs):
            captured["prompt"] = prompt
            return ({"results": [{"index": 0, "facts": ["Fact."]}]}, {})

        assert settings.ENABLE_PASSAGE_MAPPING is False, "guards the default path"

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage",
            new=_capture,
        ):
            await distiller.distil_evidence_for_claim(
                "Test claim", items, elements=elements
            )

        assert "The cut was 25 basis points." in captured["prompt"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_prompt_rule_is_symmetric(self):
        """Invariant 7: the extraction rule must not favour one direction.

        A rule preferring contradicting facts is a supply-side bias, exactly as
        a rule preferring confirming ones would be.
        """
        from app.pipeline.evidence_distiller import DISTIL_PROMPT

        lowered = DISTIL_PROMPT.lower()
        assert "confirming or contradicting" in lowered
        for biased in (
            "prefer them over",
            "most valuable — never omit",
        ):
            assert biased not in lowered


class TestDistilLongDocumentInput:
    """A document longer than MAX_ARTICLE_CHARS is read by its retained windows,
    not by a leading slice (2026-09-22).

    Measured cause: the Thirlwall summary report is 23,788 chars and the sentence
    that settled the element sits at offset 11,676 — outside the first 8,000, so
    no prompt rule could reach it.
    """

    @staticmethod
    def _long_item_with_late_marker():
        from app.services.text_provenance import capture_text_provenance
        from app.pipeline.evidence_distiller import MAX_ARTICLE_CHARS

        marker = "UNIQUEMARKERSENTENCE"
        filler = "The inquiry considered evidence about hospital governance. "
        head = (filler * 400)[:MAX_ARTICLE_CHARS + 500]
        text = head + " " + marker + " governance findings follow. " + filler * 20
        assert text.index(marker) > MAX_ARTICLE_CHARS, "marker must be past the slice"

        item = _make_evidence(full_text=text)
        capture_text_provenance(
            item,
            "Claim about hospital governance",
            [{"element_id": "e1", "description": "UNIQUEMARKERSENTENCE governance findings"}],
        )
        return item, marker

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_late_sentence_reaches_the_prompt_when_enabled(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ENABLE_DISTIL_PASSAGE_INPUT", True)
        item, marker = self._long_item_with_late_marker()
        assert marker in "\n\n".join(
            p["text"] for p in item["text_provenance"]["passages"]
        ), "precondition: the window selector retained the marker"

        captured = {}

        async def _capture(prompt, **kwargs):
            captured["prompt"] = prompt
            return ({"results": [{"index": 0, "facts": ["Fact."]}]}, {})

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage", new=_capture
        ):
            await EvidenceDistiller().distil_evidence_for_claim("Claim", [item])

        assert marker in captured["prompt"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_late_sentence_absent_when_flag_off(self, monkeypatch):
        """Rollback path: the old leading-slice behaviour, unchanged."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "ENABLE_DISTIL_PASSAGE_INPUT", False)
        monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", False)
        item, marker = self._long_item_with_late_marker()

        captured = {}

        async def _capture(prompt, **kwargs):
            captured["prompt"] = prompt
            return ({"results": [{"index": 0, "facts": ["Fact."]}]}, {})

        with patch(
            "app.pipeline.evidence_distiller.call_google_ai_with_usage", new=_capture
        ):
            await EvidenceDistiller().distil_evidence_for_claim("Claim", [item])

        assert marker not in captured["prompt"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_short_document_is_unaffected(self, monkeypatch):
        """Below the ceiling the slice IS the document — the flag changes nothing."""
        from app.core.config import settings

        item = _make_evidence(full_text="Short body. " * 60)  # ~720 chars
        prompts = {}

        async def _capture(prompt, **kwargs):
            prompts[settings.ENABLE_DISTIL_PASSAGE_INPUT] = prompt
            return ({"results": [{"index": 0, "facts": ["Fact."]}]}, {})

        for flag in (True, False):
            monkeypatch.setattr(settings, "ENABLE_DISTIL_PASSAGE_INPUT", flag)
            fresh = dict(item)
            fresh.pop("text_provenance", None)
            with patch(
                "app.pipeline.evidence_distiller.call_google_ai_with_usage",
                new=_capture,
            ):
                await EvidenceDistiller().distil_evidence_for_claim("Claim", [fresh])

        assert prompts[True] == prompts[False]
