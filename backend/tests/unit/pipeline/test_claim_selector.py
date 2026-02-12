"""Tests for PR-B02: ClaimSelector — article-mode claim ranking and selection."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.claim_selector import ClaimSelector


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_google_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]
    }
    return resp


def _make_claims(count: int = 6) -> list[dict]:
    return [{"text": f"Claim number {i}", "position": i} for i in range(count)]


def _make_ranking_payload(count: int = 6) -> dict:
    return {
        "ranked_claims": [
            {
                "claim_index": i,
                "significance_score": round(1.0 - (i * 0.15), 2),
                "significance_rank": i + 1,
            }
            for i in range(count)
        ]
    }


def _make_article_context() -> dict:
    return {
        "domain": "politics",
        "classification": "news_article",
        "excerpt": "A long article about policy changes...",
    }


# ── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestClaimSelectorRanking:

    @patch("app.pipeline.claim_selector.httpx.AsyncClient")
    async def test_rank_returns_all_claims(self, mock_client_cls):
        """No claims are dropped during ranking."""
        claims = _make_claims(6)
        payload = _make_ranking_payload(6)

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        selector = ClaimSelector()
        result = await selector.rank_claims_by_significance(
            claims, _make_article_context()
        )

        assert len(result) == 6

    @patch("app.pipeline.claim_selector.httpx.AsyncClient")
    async def test_rank_adds_significance_fields(self, mock_client_cls):
        """significance_score and significance_rank are present on each claim."""
        claims = _make_claims(4)
        payload = _make_ranking_payload(4)

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        selector = ClaimSelector()
        result = await selector.rank_claims_by_significance(
            claims, _make_article_context()
        )

        for claim in result:
            assert "significance_score" in claim
            assert "significance_rank" in claim
            assert 0.0 <= claim["significance_score"] <= 1.0
            assert isinstance(claim["significance_rank"], int)

    @patch("app.pipeline.claim_selector.httpx.AsyncClient")
    async def test_rank_fallback_on_failure(self, mock_client_cls):
        """LLM failure → position-order fallback with scores."""
        resp = MagicMock()
        resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.post.return_value = resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        claims = _make_claims(4)
        selector = ClaimSelector()
        result = await selector.rank_claims_by_significance(
            claims, _make_article_context()
        )

        assert len(result) == 4
        # Position order: rank 1, 2, 3, 4
        ranks = [c["significance_rank"] for c in result]
        assert ranks == [1, 2, 3, 4]


class TestClaimSelectorSelection:

    def test_select_caps_at_max(self):
        """At most MAX_SELECTED_CLAIMS claims get is_selected=True."""
        claims = _make_claims(8)
        for i, c in enumerate(claims):
            c["significance_rank"] = i + 1
            c["significance_score"] = round(1.0 - (i * 0.1), 2)

        selector = ClaimSelector()
        result = selector.select_claims(claims, max_selected=5)

        selected = [c for c in result if c["is_selected"]]
        not_selected = [c for c in result if not c["is_selected"]]
        assert len(selected) == 5
        assert len(not_selected) == 3

    def test_select_marks_is_selected(self):
        """Top N get is_selected=True, rest get False."""
        claims = _make_claims(4)
        for i, c in enumerate(claims):
            c["significance_rank"] = i + 1
            c["significance_score"] = round(1.0 - (i * 0.2), 2)

        selector = ClaimSelector()
        result = selector.select_claims(claims, max_selected=2)

        for claim in result:
            assert "is_selected" in claim

        selected_ranks = [c["significance_rank"] for c in result if c["is_selected"]]
        assert 1 in selected_ranks
        assert 2 in selected_ranks

    def test_select_single_claim_focused_mode(self):
        """Single claim is always selected (focused mode)."""
        claims = [
            {"text": "Only claim", "significance_rank": 1, "significance_score": 1.0}
        ]

        selector = ClaimSelector()
        result = selector.select_claims(claims, max_selected=5)

        assert len(result) == 1
        assert result[0]["is_selected"] is True
