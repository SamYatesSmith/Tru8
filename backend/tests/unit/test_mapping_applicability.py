from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.services.mapping_applicability import APPLICABILITY_RULES


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "label",
    [
        "mapping",
        "batch_mapping",
        "map_completion",
        "recovery_mapping",
        "passage_review",
        "decomposition",
        "batch_decomposition",
    ],
)
async def test_rules_reach_provider_only_for_enabled_relationship_calls(
    monkeypatch, enabled, label
):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", enabled)
    analyzer = ClaimMapAnalyzer()
    analyzer.google_ai_api_key = "test-only"
    analyzer._call_google = AsyncMock(return_value=({}, {}))
    await analyzer._call_llm("original", 0, 100, label)
    prompt = analyzer._call_google.call_args.args[0]
    should_append = enabled and label not in ("decomposition", "batch_decomposition")
    assert prompt == (
        "original\n" + APPLICABILITY_RULES if should_append else "original"
    )
