"""Tests for Seeker explore mode — related claim discovery.

Covers:
- Context token extraction
- Related claim dict building
- Response sanitisation (privacy — no internal fields exposed)
- Explore response shape
"""

import pytest


class TestExtractContextTokens:
    def test_returns_empty_for_none(self):
        from app.services.explore import _extract_context_tokens

        assert _extract_context_tokens(None) == []

    def test_returns_empty_for_empty_string(self):
        from app.services.explore import _extract_context_tokens

        assert _extract_context_tokens("") == []

    def test_filters_stopwords(self):
        from app.services.explore import _extract_context_tokens

        tokens = _extract_context_tokens("the impact of climate change on the economy")
        assert "the" not in tokens
        assert "of" not in tokens
        assert "on" not in tokens
        assert "impact" in tokens
        assert "climate" in tokens

    def test_filters_short_words(self):
        from app.services.explore import _extract_context_tokens

        tokens = _extract_context_tokens("UK is a great place to be")
        # "UK" is only 2 chars, should be filtered
        assert "uk" not in tokens

    def test_limits_to_five_tokens(self):
        from app.services.explore import _extract_context_tokens

        tokens = _extract_context_tokens(
            "economic growth inflation unemployment productivity output trade deficit surplus"
        )
        assert len(tokens) <= 5

    def test_lowercases_tokens(self):
        from app.services.explore import _extract_context_tokens

        tokens = _extract_context_tokens("GDP Growth Rate")
        assert all(t == t.lower() for t in tokens)


class TestBuildRelatedClaim:
    def test_basic_structure(self):
        from app.services.explore import _build_related_claim

        claim_map = {
            "normalised_claim": "Test claim about GDP",
            "elements": [
                {"description": "GDP grew 2%", "state": "supported"},
                {"description": "In Q3 2025", "state": "unresolved"},
            ],
        }
        result = _build_related_claim(claim_map, "empirical", "abc123", ["gdp"])

        assert result["normalisedClaim"] == "Test claim about GDP"
        assert result["claimType"] == "empirical"
        assert len(result["elements"]) == 2
        assert result["elements"][0]["description"] == "GDP grew 2%"
        assert result["elements"][0]["state"] == "supported"
        assert result["elements"][1]["state"] == "unresolved"
        assert result["claimTextHash"] == "abc123"
        assert "gdp" in result["entityOverlap"]

    def test_empty_claim_map(self):
        from app.services.explore import _build_related_claim

        result = _build_related_claim({}, None, "hash", [])
        assert result["normalisedClaim"] == ""
        assert result["claimType"] is None
        assert result["elements"] == []
        assert result["entityOverlap"] == []

    def test_deduplicates_entity_overlap(self):
        from app.services.explore import _build_related_claim

        result = _build_related_claim(
            {"normalised_claim": "test", "elements": []},
            "empirical",
            "hash",
            ["uk", "uk", "gdp", "gdp"],
        )
        assert len(result["entityOverlap"]) == 2

    def test_missing_elements_key(self):
        from app.services.explore import _build_related_claim

        result = _build_related_claim(
            {"normalised_claim": "test"},
            "empirical",
            "hash",
            [],
        )
        assert result["elements"] == []

    def test_elements_with_none_state(self):
        from app.services.explore import _build_related_claim

        claim_map = {
            "normalised_claim": "test",
            "elements": [
                {"description": "Element without state"},
            ],
        }
        result = _build_related_claim(claim_map, "empirical", "hash", [])
        assert result["elements"][0]["state"] is None


class TestBuildExploreResponse:
    def test_strips_internal_fields(self):
        from app.services.explore import build_explore_response

        claims = [
            {
                "normalisedClaim": "Test",
                "claimType": "empirical",
                "elements": [],
                "consensus": None,
                "entityOverlap": ["uk"],
                "claimTextHash": "should_not_appear",
            }
        ]
        response = build_explore_response(claims)

        assert len(response["relatedClaims"]) == 1
        # claimTextHash is internal — must not appear in response
        assert "claimTextHash" not in response["relatedClaims"][0]
        assert response["mode"] == "explore"
        assert response["explorationBasis"] == "key_entities"

    def test_empty_claims_returns_gaps_mode(self):
        from app.services.explore import build_explore_response

        response = build_explore_response([])
        assert response["relatedClaims"] == []
        assert response["mode"] == "gaps"

    def test_preserves_consensus_data(self):
        from app.services.explore import build_explore_response

        claims = [
            {
                "normalisedClaim": "Claim with consensus",
                "claimType": "empirical",
                "elements": [{"description": "Test", "state": "supported"}],
                "consensus": {"independentChecks": 4, "stability": "stable"},
                "entityOverlap": [],
                "claimTextHash": "hash",
            }
        ]
        response = build_explore_response(claims)
        assert response["relatedClaims"][0]["consensus"]["independentChecks"] == 4
        assert response["relatedClaims"][0]["consensus"]["stability"] == "stable"

    def test_preserves_element_data(self):
        from app.services.explore import build_explore_response

        claims = [
            {
                "normalisedClaim": "Test",
                "claimType": None,
                "elements": [
                    {"description": "Element A", "state": "supported"},
                    {"description": "Element B", "state": "disputed"},
                ],
                "consensus": None,
                "entityOverlap": ["entity1"],
                "claimTextHash": "hash",
            }
        ]
        response = build_explore_response(claims)
        elements = response["relatedClaims"][0]["elements"]
        assert len(elements) == 2
        assert elements[0]["description"] == "Element A"
        assert elements[1]["state"] == "disputed"

    def test_multiple_claims(self):
        from app.services.explore import build_explore_response

        claims = [
            {
                "normalisedClaim": f"Claim {i}",
                "claimType": "empirical",
                "elements": [],
                "consensus": None,
                "entityOverlap": [],
                "claimTextHash": f"hash{i}",
            }
            for i in range(5)
        ]
        response = build_explore_response(claims)
        assert len(response["relatedClaims"]) == 5
        assert response["mode"] == "explore"
