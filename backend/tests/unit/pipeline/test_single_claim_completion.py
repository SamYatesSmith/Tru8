"""D6 (structure plan 2026-10-07, S2): the single-claim mapping path must keep
the main-pass mapping when the completion stage fails or hangs, exactly as the
batch path does.

Before the fix, any exception from `_complete_unmapped_evidence` (completion
census, relationship review, echo reconcile) reached the outer `except` in
`map_evidence_to_elements`, whose `_fallback_mapping` wipes every ref. That
path serves every one-claim check, every batch-parse retry and every
Strengthen run.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline import claim_map_analyzer as cma
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

from tests.unit.pipeline.test_claim_map_analyzer import (
    _make_evidence_list,
    _make_google_response,
    _make_mapping_payload,
    _make_partial_claim_map,
)


def _client_returning(payload):
    client = AsyncMock()
    client.post.return_value = _make_google_response(payload)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


async def _map_with_completion(completion):
    claim_map = _make_partial_claim_map(2)
    evidence = _make_evidence_list(3)
    payload = _make_mapping_payload(["e1", "e2"], ["ev1", "ev2"])
    with patch(
        "app.pipeline.claim_map_analyzer.httpx.AsyncClient",
        return_value=_client_returning(payload),
    ), patch.object(ClaimMapAnalyzer, "_complete_unmapped_evidence", completion):
        return await ClaimMapAnalyzer().map_evidence_to_elements(claim_map, evidence)


def _ref_ids(result):
    return {r["evidence_id"] for e in result["elements"] for r in e["evidence_refs"]}


@pytest.mark.asyncio
async def test_a_failing_completion_keeps_the_main_pass_mapping():
    async def boom(self, claim_map, evidence_list):
        raise RuntimeError("completion exploded")

    result = await _map_with_completion(boom)
    assert _ref_ids(result) == {"ev1", "ev2"}
    assert result["metadata"]["mapping_model"] != "fallback"


@pytest.mark.asyncio
async def test_a_hanging_completion_is_cut_and_keeps_the_main_pass_mapping(
    monkeypatch,
):
    monkeypatch.setattr(cma, "_completion_timeout", lambda: 0.05)

    async def hang(self, claim_map, evidence_list):
        await asyncio.sleep(5)

    result = await _map_with_completion(hang)
    assert _ref_ids(result) == {"ev1", "ev2"}


@pytest.mark.asyncio
async def test_a_completion_that_succeeds_still_runs():
    seen = []

    async def ok(self, claim_map, evidence_list):
        seen.append(claim_map["claim_id"])

    result = await _map_with_completion(ok)
    assert seen == [result["claim_id"]]
    assert _ref_ids(result) == {"ev1", "ev2"}
