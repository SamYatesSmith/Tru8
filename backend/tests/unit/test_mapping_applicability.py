from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    ClaimMapAnalyzer, DECOMPOSITION_PROMPT, BATCH_DECOMPOSITION_PROMPT,
)
from app.services.mapping_applicability import APPLICABILITY_RULES, DECOMPOSITION_SCOPE_RULES


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
    rules = (
        DECOMPOSITION_SCOPE_RULES
        if label in ("decomposition", "batch_decomposition")
        else APPLICABILITY_RULES
    )
    assert prompt == ("original\n" + rules if enabled else "original")


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("batch", [False, True])
async def test_candidate_removes_conflicting_split_rule(monkeypatch, enabled, batch):
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", enabled)
    analyzer = ClaimMapAnalyzer()
    analyzer.google_ai_api_key = "test-only"
    analyzer._call_google = AsyncMock(return_value=({}, {}))
    original = BATCH_DECOMPOSITION_PROMPT if batch else DECOMPOSITION_PROMPT
    await analyzer._call_llm(original, 0, 100, "batch_decomposition" if batch else "decomposition")
    actual = analyzer._call_google.call_args.args[0]
    if enabled:
        assert "alongside the cause and the effect" not in actual
        assert DECOMPOSITION_SCOPE_RULES in actual
    else:
        assert actual == original
