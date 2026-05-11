"""Regression tests for the position-keying contract in retrieve_evidence_for_claims.

Background — TRU-E317-4192 (2026-05-11) surfaced a cross-attribution bug:

  - `_retrieve_and_store` was keying `evidence_by_claim` by the enumerate
    index (0, 1, 2 for any input of three claims).
  - `_ensure_minimum_evidence` and every downstream consumer
    (runner.py result-building, workers/pipeline cache merge) look up
    evidence by `claim["position"]`.
  - When the selected positions were non-contiguous (e.g. [1, 3, 4] under
    the Step 4 UI cap of three), the keying mismatch routed each
    claim's evidence to the WRONG claim at save time, and
    `_ensure_minimum_evidence` then saw the supposedly-missing positions
    and fired recovery, doubling the keyset and creating empty rows on
    unselected claims.

The bug went unnoticed because every existing test in test_retrieve.py
uses sequential positions [0, 1, ...]; the cross-attribution only
manifests when the index sequence and position sequence diverge.

These tests pin the contract: evidence MUST be keyed by claim["position"],
regardless of order, contiguity, or starting offset.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.retrieve import EvidenceRetriever


def _make_claim(position: int, text: str = None):
    """Build a minimal claim dict with the given position."""
    return {
        "position": position,
        "text": text or f"Claim text for position {position}",
        "elements": [],
        "article_classification": {"primary_domain": "general"},
    }


def _make_single_claim_result(position: int):
    """Build a fake `_retrieve_evidence_for_single_claim` return value.

    Includes a position-tagged evidence URL so cross-attribution is
    detectable in assertions.
    """
    return {
        "filtered_evidence": [
            {
                "url": f"https://example.com/pos-{position}/article",
                "title": f"Result for position {position}",
                "snippet": f"Snippet at position {position}",
                "source": f"example.com",
                "relevance_score": 0.5,
            }
        ],
        "pre_weighting_evidence": [
            {"url": f"https://example.com/pos-{position}/article", "_pre": True}
        ],
        "raw_evidence": [
            {
                "url": f"https://example.com/pos-{position}/article",
                "is_included": True,
            }
        ],
        "claim_position": position,
        "claim_text": f"Claim text for position {position}",
        "search_results_count": 1,
    }


async def _stub_single_claim(claim, *_args, **_kwargs):
    """Stub that returns position-tagged evidence for whichever claim it gets."""
    return _make_single_claim_result(claim["position"])


@pytest.fixture
def retriever():
    """A retriever instance with recovery disabled so position-keying
    assertions aren't contaminated by `_ensure_minimum_evidence` firing
    real search calls. Recovery semantics get their own tests below."""
    r = EvidenceRetriever()
    r.MIN_EVIDENCE_PER_CLAIM = 0
    return r


# --------------------------------------------------------------------------- #
# Core regression: non-contiguous positions key correctly
# --------------------------------------------------------------------------- #


class TestPositionKeying:
    """Evidence must be keyed by claim['position'], not enumerate index."""

    @pytest.mark.asyncio
    async def test_non_contiguous_positions_key_by_position(
        self, retriever, monkeypatch
    ):
        """[1, 3, 4] in → keys "1", "3", "4" out (NOT "0", "1", "2")."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(1), _make_claim(3), _make_claim(4)]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        evidence_by_claim = result["evidence_by_claim"]
        # Strict assertion — keyset must be exactly {1, 3, 4}, not {0, 1, 2}.
        assert set(evidence_by_claim.keys()) == {"1", "3", "4"}, (
            f"Expected position-keyed dict {{1,3,4}}, got {set(evidence_by_claim.keys())}. "
            f"Index-keyed output indicates the bug has regressed."
        )

    @pytest.mark.asyncio
    async def test_evidence_attributed_to_correct_claim(self, retriever, monkeypatch):
        """Each claim's evidence must come back under THAT claim's position."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(1), _make_claim(3), _make_claim(4)]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        evidence_by_claim = result["evidence_by_claim"]
        # The stub embeds the position into the URL, so we can detect
        # cross-attribution: position=1's URL must NOT appear under "3" or "4".
        for pos_key, ev_list in evidence_by_claim.items():
            for ev in ev_list:
                assert f"pos-{pos_key}/" in ev["url"], (
                    f"Cross-attribution: claim at position {pos_key} got evidence "
                    f"{ev['url']!r} which belongs to a different position."
                )

    @pytest.mark.asyncio
    async def test_position_zero_works(self, retriever, monkeypatch):
        """Single claim at position 0 — the default case, must still work."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(0)]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        assert set(result["evidence_by_claim"].keys()) == {"0"}

    @pytest.mark.asyncio
    async def test_sequential_positions_still_correct(self, retriever, monkeypatch):
        """[0, 1, 2] in → keys "0", "1", "2" out — regression-safe path."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(0), _make_claim(1), _make_claim(2)]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        assert set(result["evidence_by_claim"].keys()) == {"0", "1", "2"}
        # Sanity: each claim still got its own evidence (no cross-mixing
        # even in the sequential case).
        for pos_key, ev_list in result["evidence_by_claim"].items():
            for ev in ev_list:
                assert f"pos-{pos_key}/" in ev["url"]

    @pytest.mark.asyncio
    async def test_single_high_position_keys_correctly(self, retriever, monkeypatch):
        """A single claim at position=4 keys as "4" — not "0" via index fallback."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(4)]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        assert set(result["evidence_by_claim"].keys()) == {"4"}
        assert "0" not in result["evidence_by_claim"]


# --------------------------------------------------------------------------- #
# Exception path: keying must still use position
# --------------------------------------------------------------------------- #


class TestExceptionPathKeying:
    """The exception branch in _retrieve_and_store also keys by position."""

    @pytest.mark.asyncio
    async def test_exception_keys_by_position_not_index(self, retriever, monkeypatch):
        """When _retrieve_evidence_for_single_claim raises, the empty-list
        fallback should still land at the correct position key."""
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(3)]

        async def _raising_stub(*args, **kwargs):
            raise RuntimeError("simulated downstream failure")

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_raising_stub,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        assert "3" in result["evidence_by_claim"]
        assert result["evidence_by_claim"]["3"] == []
        # Crucially: empty-list does NOT land under "0".
        assert "0" not in result["evidence_by_claim"]


# --------------------------------------------------------------------------- #
# Legacy list-format path: keying must still use position
# --------------------------------------------------------------------------- #


class TestLegacyListPathKeying:
    """If _retrieve_evidence_for_single_claim returns a list (legacy
    backward-compat), keying still uses position."""

    @pytest.mark.asyncio
    async def test_legacy_list_keys_by_position(self, retriever, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        claims = [_make_claim(2)]

        async def _list_returning_stub(claim, *_args, **_kwargs):
            # Legacy format — bare list of evidence dicts.
            return [
                {
                    "url": f"https://example.com/pos-{claim['position']}/legacy",
                    "snippet": "legacy",
                }
            ]

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_list_returning_stub,
        ):
            result = await retriever.retrieve_evidence_for_claims(claims)

        assert "2" in result["evidence_by_claim"]
        assert "0" not in result["evidence_by_claim"]
        assert len(result["evidence_by_claim"]["2"]) == 1


# --------------------------------------------------------------------------- #
# Integration with _ensure_minimum_evidence: no spurious recovery
# --------------------------------------------------------------------------- #


class TestRecoveryNoLongerSpuriouslyFires:
    """Pre-fix, _ensure_minimum_evidence saw position keys "3" and "4" as
    missing (because they were stored under index keys "1" and "2"), and
    fired recovery. Post-fix, evidence is keyed by position and recovery
    only fires for genuinely-empty claims."""

    @pytest.mark.asyncio
    async def test_well_supplied_non_contiguous_claims_skip_recovery(
        self, retriever, monkeypatch
    ):
        monkeypatch.setattr("app.core.config.settings.ENABLE_QUERY_PLANNING", False)
        # Set MIN_EVIDENCE_PER_CLAIM to 0 so the recovery branch never
        # qualifies — we're testing that the keying-driven false-trigger
        # path is gone.
        monkeypatch.setattr(retriever, "MIN_EVIDENCE_PER_CLAIM", 0)

        claims = [_make_claim(1), _make_claim(3), _make_claim(4)]
        recovery_called = []

        async def _track_recovery(*args, **kwargs):
            recovery_called.append(kwargs.get("claim_position", "?"))
            return [], []

        with patch.object(
            retriever,
            "_retrieve_evidence_for_single_claim",
            side_effect=_stub_single_claim,
        ), patch.object(
            retriever,
            "_recover_evidence_for_claim",
            side_effect=_track_recovery,
        ):
            await retriever.retrieve_evidence_for_claims(claims)

        # Recovery must not fire when MIN_EVIDENCE_PER_CLAIM=0 (all claims
        # have ≥1 evidence item from the stub, and the floor is 0).
        assert recovery_called == [], (
            f"Recovery fired spuriously: {recovery_called}. Indicates the "
            f"position-keying fix has regressed and _ensure_minimum_evidence "
            f"is seeing false-missing positions."
        )
