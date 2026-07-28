"""
Unit tests for Query Planning Agent.

Tests the LLM-powered query planning functionality for semantic claim understanding.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMQueryPlanner:
    """Test the LLMQueryPlanner class."""

    def test_validate_plans_normalizes_structure(self):
        """Test plan validation normalizes various response formats."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test with various input formats
        plans = [
            {
                "claim_index": 0,
                "queries": "Arsenal squad 2025",  # String instead of list
            },
            {
                "queries": [
                    "query1",
                    "query2",
                    "query3",
                    "query4",
                    "query5",
                ],  # Too many queries
            },
        ]

        validated = planner._validate_plans(plans, 2)

        # Check normalization
        assert len(validated) == 2

        # First plan - string converted to list
        assert isinstance(validated[0]["queries"], list)

        # Second plan - queries limited to 2
        assert len(validated[1]["queries"]) <= 2

    def test_validate_plans_handles_missing_fields(self):
        """Test plan validation handles missing fields gracefully."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {"claim_type": "match_result"},  # Missing claim_index, queries
        ]

        validated = planner._validate_plans(plans, 1)

        # Should fill in defaults
        assert validated[0]["claim_index"] == 0
        assert validated[0]["queries"] == []

    def test_validate_plans_filters_non_dicts(self):
        """Test plan validation filters out non-dict entries."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {"claim_type": "general", "queries": ["test"]},
            "invalid string entry",
            None,
            123,
            {"claim_type": "stats", "queries": ["another"]},
        ]

        validated = planner._validate_plans(plans, 5)

        # Should only have 2 valid dict entries
        assert len(validated) == 2


class TestRelevanceGateRemoved:
    """A5 regression guard — the in-planner Jaccard relevance gate was removed
    2026-04-23. It destroyed alphanumeric scientific identifiers (K2-18b, JWST-related
    terms) because the `[a-zA-Z]{4,}` tokenizer dropped them, producing 0.00 similarity
    on queries that were actually relevant. Downstream relevance_scorer.py is the
    real quality gate. These tests assert queries flow through _validate_plans
    untouched, so a future reintroduction of a token-overlap filter would fail here."""

    def test_alphanumeric_science_query_is_not_filtered(self):
        """Real-world K2-18b regression case: query with scientific alphanumeric
        identifiers and jargon survives validation even when literal token overlap
        with the claim text is zero. Pre-A5 this was the failure path."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {
                "claim_index": 0,
                "element_id": "e1",
                "queries": [
                    "K2-18b biosignature evidence",
                    "JWST K2-18b exoplanet biosignature findings",
                ],
                "freshness": "py",
            }
        ]
        element_texts = [
            (
                "K2-18b shows signs of life",
                "K2-18b has atmospheric signatures",
            )
        ]

        validated = planner._validate_plans(plans, 1, element_texts=element_texts)

        assert len(validated) == 1
        assert validated[0]["queries"] == [
            "K2-18b biosignature evidence",
            "JWST K2-18b exoplanet biosignature findings",
        ]

    def test_queries_with_zero_literal_overlap_survive(self):
        """Synthetic worst-case: claim and query share no 4+-letter ASCII tokens at all.
        Pre-A5 this would have been filtered to empty then backfilled to queries[:1]."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        plans = [
            {
                "claim_index": 0,
                "element_id": "e1",
                "queries": ["alpha beta gamma", "delta epsilon zeta"],
                "freshness": "py",
            }
        ]
        element_texts = [("foo bar baz qux", "red blue green yellow")]

        validated = planner._validate_plans(plans, 1, element_texts=element_texts)

        assert validated[0]["queries"] == ["alpha beta gamma", "delta epsilon zeta"]


class TestFixHallucinatedYears:
    """Test _fix_hallucinated_years — must rewrite LLM artefacts but preserve
    years the user typed in the claim."""

    def test_rewrites_genuine_hallucination_when_claim_has_no_year(self):
        """Year absent from claim → treated as LLM hallucination, rewritten."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        queries = ["ECB interest rate decision 2024"]
        result = planner._fix_hallucinated_years(
            queries, current_year=2026, claim_text="ECB raised interest rates"
        )
        assert result == ["ECB interest rate decision 2026"]

    def test_preserves_year_when_claim_references_it(self):
        """Year present in claim → intentional historical reference, preserved."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        queries = ["ECB interest rate decision 2024"]
        result = planner._fix_hallucinated_years(
            queries,
            current_year=2026,
            claim_text="The ECB raised interest rates in September 2024",
        )
        assert result == ["ECB interest rate decision 2024"]

    def test_preserves_multiple_explicit_years(self):
        """Claim referencing a year range — both years preserved."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        queries = ["inflation comparison 2023 vs 2024"]
        result = planner._fix_hallucinated_years(
            queries,
            current_year=2026,
            claim_text="Inflation was higher in 2024 than 2023",
        )
        assert result == ["inflation comparison 2023 vs 2024"]

    def test_rewrites_some_preserves_others(self):
        """Claim mentions 2024 only → 2024 preserved, 2025 still rewritten."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        queries = ["event in 2024 followed by impact in 2025"]
        result = planner._fix_hallucinated_years(
            queries,
            current_year=2026,
            claim_text="Something happened in 2024",
        )
        assert result == ["event in 2024 followed by impact in 2026"]

    def test_empty_claim_text_falls_back_to_original_behaviour(self):
        """No claim text → behaves as before: all recent years rewritten."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        queries = ["story from 2024"]
        result = planner._fix_hallucinated_years(
            queries, current_year=2026, claim_text=""
        )
        assert result == ["story from 2026"]


class TestQueryPlannerIntegration:
    """Integration tests for query planner with mocked LLM."""

    @pytest.mark.asyncio
    async def test_plan_queries_batch_success(self):
        """Test successful batch query planning."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Mock the httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """{"plans": [
                        {
                            "claim_index": 0,
                            "queries": ["Arsenal squad 2025", "Viktor Gyokeres Arsenal"],
                            "freshness": "pw",
                            "reasoning": "Current squad data"
                        }
                    ]}"""
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [
                {
                    "text": "Arsenal has Viktor Gyokeres in their squad",
                    "claim_index": 0,
                    "elements": [
                        {
                            "element_id": "e1",
                            "description": "Viktor Gyokeres is in Arsenal's squad",
                        }
                    ],
                }
            ]
            result = await planner.plan_queries_batch(claims)

            assert result is not None
            assert len(result) == 1
            assert result[0]["element_id"] == "e1"
            assert len(result[0]["queries"]) == 2

    @pytest.mark.asyncio
    async def test_plan_queries_batch_no_api_key(self):
        """Test graceful handling when API key is missing."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        planner.openai_api_key = None  # Simulate missing key

        claims = [{"text": "Some claim"}]
        result = await planner.plan_queries_batch(claims)

        # Should return None when no API key
        assert result is None

    @pytest.mark.asyncio
    async def test_plan_queries_batch_empty_claims(self):
        """Test handling of empty claims list."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        result = await planner.plan_queries_batch([])

        # Should return empty list for empty input
        assert result == []

    @pytest.mark.asyncio
    async def test_plan_queries_batch_timeout_fallback(self):
        """Test fallback on timeout."""
        from app.utils.query_planner import LLMQueryPlanner
        import httpx

        planner = LLMQueryPlanner()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [
                {
                    "text": "Test claim",
                    "claim_index": 0,
                    "elements": [{"element_id": "e1", "description": "Test element"}],
                }
            ]
            result = await planner.plan_queries_batch(claims)

            # Should return None on timeout (triggering fallback)
            assert result is None


class TestQueryPlannerSingleton:
    """Test the query planner singleton."""

    def test_get_query_planner_returns_same_instance(self):
        """Test singleton pattern."""
        from app.utils.query_planner import get_query_planner

        planner1 = get_query_planner()
        planner2 = get_query_planner()

        assert planner1 is planner2


class TestDynamicFreshness:
    """Test dynamic freshness system (replaced hardcoded claim types)."""

    def test_freshness_validation_in_plans(self):
        """Test that freshness values are validated in query plans."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()

        # Test plans with various freshness values
        plans = [
            {"claim_index": 0, "queries": ["test"], "freshness": "pw"},  # Valid
            {
                "claim_index": 1,
                "queries": ["test"],
                "freshness": "invalid",
            },  # Invalid -> py
            {"claim_index": 2, "queries": ["test"]},  # Missing -> py
        ]

        validated = planner._validate_plans(plans, 3)

        assert validated[0]["freshness"] == "pw"
        assert validated[1]["freshness"] == "py"  # Default for invalid
        assert validated[2]["freshness"] == "py"  # Default for missing

    def test_valid_freshness_values(self):
        """Test all valid freshness values are accepted."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        valid_values = ["pd", "pw", "pm", "py", "2y"]

        for freshness in valid_values:
            plans = [{"claim_index": 0, "queries": ["test"], "freshness": freshness}]
            validated = planner._validate_plans(plans, 1)
            assert validated[0]["freshness"] == freshness

    def test_default_freshness_function(self):
        """Test get_freshness_for_claim_type returns default values."""
        from app.utils.query_planner import get_freshness_for_claim_type

        # All claim types should return the same DEFAULT_FRESHNESS now
        result = get_freshness_for_claim_type("any_type")
        assert result["brave_freshness"] == "py"
        assert result["max_age_days"] == 365

    def test_check_evidence_staleness_with_freshness(self):
        """Test evidence staleness check uses freshness parameter."""
        from app.utils.query_planner import check_evidence_staleness
        from datetime import datetime

        # Test with fresh evidence and strict freshness
        result = check_evidence_staleness(
            evidence_date="2025-12-01",
            freshness="pw",  # Past week
            reference_date=datetime(2025, 12, 2),
        )
        assert result["is_stale"] is False
        assert result["max_age_days"] == 7

        # Test with stale evidence and strict freshness
        result = check_evidence_staleness(
            evidence_date="2025-11-01",
            freshness="pw",  # Past week
            reference_date=datetime(2025, 12, 2),
        )
        assert result["is_stale"] is True

        # Test with lenient freshness
        result = check_evidence_staleness(
            evidence_date="2025-11-01",
            freshness="py",  # Past year
            reference_date=datetime(2025, 12, 2),
        )
        assert result["is_stale"] is False


class TestArticleContextIntegration:
    """Test article context is passed to query planner."""

    @pytest.mark.asyncio
    async def test_plan_queries_with_article_context(self):
        """Test query planning receives article context."""
        from app.utils.query_planner import LLMQueryPlanner
        from unittest.mock import MagicMock

        planner = LLMQueryPlanner()

        # Mock the httpx client to capture the request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """{"plans": [
                        {
                            "claim_index": 0,
                            "queries": ["test query"],
                            "freshness": "pw",
                            "reasoning": "Fast-changing data"
                        }
                    ]}"""
                    }
                }
            ]
        }

        captured_request = {}

        async def capture_post(*args, **kwargs):
            captured_request.update(kwargs.get("json", {}))
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = capture_post
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            claims = [
                {
                    "text": "Test claim",
                    "claim_index": 0,
                    "elements": [{"element_id": "e1", "description": "Test element"}],
                }
            ]
            article_context = {
                "primary_domain": "Politics",
                "temporal_context": "December 2024 election coverage",
                "key_entities": ["Congress", "Senate"],
                "evidence_guidance": "Use official government sources",
            }

            result = await planner.plan_queries_batch(
                claims, article_context=article_context
            )

            # Verify article context was included in the prompt
            user_message = captured_request.get("messages", [{}])[-1].get("content", "")
            assert "Politics" in user_message
            assert "December 2024" in user_message
            assert "Congress" in user_message


# ── B4: mechanical freshness injection from typed entities ──────────────


class TestExtractMaxYearFromEntities:
    """B4 helper: latest 4-digit year from DATE-typed entities."""

    def test_returns_none_for_empty_list(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        assert _extract_max_year_from_entities([]) is None

    def test_returns_none_for_no_date_entities(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [
            {"text": "BP plc", "type": "ORG"},
            {"text": "London", "type": "LOCATION"},
        ]
        assert _extract_max_year_from_entities(entities) is None

    def test_extracts_single_year(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [{"text": "19 July 2022", "type": "DATE"}]
        assert _extract_max_year_from_entities(entities) == 2022

    def test_extracts_year_only_text(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [{"text": "2022", "type": "DATE"}]
        assert _extract_max_year_from_entities(entities) == 2022

    def test_returns_max_across_multiple_dates(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [
            {"text": "2018", "type": "DATE"},
            {"text": "December 2024", "type": "DATE"},
            {"text": "March 2020", "type": "DATE"},
        ]
        assert _extract_max_year_from_entities(entities) == 2024

    def test_ignores_non_year_numbers(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        # 1234 is not a year (regex matches 19xx/20xx only)
        entities = [{"text": "1234 cases", "type": "DATE"}]
        assert _extract_max_year_from_entities(entities) is None

    def test_case_insensitive_type_match(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [{"text": "2022", "type": "date"}]
        assert _extract_max_year_from_entities(entities) == 2022

    def test_skips_malformed_entities(self):
        from app.utils.query_planner import _extract_max_year_from_entities

        entities = [
            "not a dict",
            {"type": "DATE"},  # missing text
            {"text": "2022", "type": "DATE"},  # the only valid one
            None,
        ]
        assert _extract_max_year_from_entities(entities) == 2022


class TestInjectFreshnessForHistoricalDates:
    """B4: post-LLM freshness override for historical claims."""

    def test_overrides_py_to_none_for_historical_year(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [
            {"claim_index": 0, "freshness": "py", "queries": ["BP profit 2022"]},
        ]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [{"text": "2022", "type": "DATE"}],
            }
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "none"

    def test_does_not_override_for_current_year(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [{"claim_index": 0, "freshness": "py"}]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [{"text": "March 2026", "type": "DATE"}],
            }
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "py"

    def test_does_not_override_when_no_date_entity(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [{"claim_index": 0, "freshness": "py"}]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [{"text": "BP plc", "type": "ORG"}],
            }
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "py"

    def test_does_not_override_when_no_entities_field(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [{"claim_index": 0, "freshness": "py"}]
        claims = [{"claim_index": 0}]  # no key_entities at all
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "py"

    def test_overrides_only_matching_claim_index(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [
            {"claim_index": 0, "freshness": "py"},
            {"claim_index": 1, "freshness": "pw"},
        ]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [{"text": "2022", "type": "DATE"}],
            },
            {
                "claim_index": 1,
                "key_entities": [{"text": "2026", "type": "DATE"}],
            },
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "none"  # historical, overridden
        assert result[1]["freshness"] == "pw"  # current year, untouched

    def test_no_op_when_no_claim_has_year(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [{"claim_index": 0, "freshness": "py"}]
        claims = [{"claim_index": 0, "key_entities": []}]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "py"

    def test_idempotent_when_already_none(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        plans = [{"claim_index": 0, "freshness": "none"}]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [{"text": "2022", "type": "DATE"}],
            }
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        assert result[0]["freshness"] == "none"


class TestB4InjectOnPropagatedDates:
    """NF-20-B canonical fix (2026-05-12) — extract.py's
    `_propagate_article_dates` injects article-level DATEs into
    dateless claims with provenance ``source="article_inheritance"``.
    This wired-seam test feeds the post-propagation shape into B4 and
    locks the behaviour: freshness inject fires on inherited DATEs
    just as it does on LLM-emitted ones, because the inject function
    only reads ``type`` and ``text``.

    The reference data is TRU-E4C5-E295 (GBR coral 2026-05-12): claim 0
    had March 2024 DATE; claims 1-3 did not. Pre-fix, B4 inject only
    fired on claim 0 and claims 1-3 kept freshness="py", filtering out
    original-period content (March 2024 is ~26 months stale as of
    May 2026)."""

    def test_inherited_dates_trigger_freshness_inject(self):
        from app.utils.query_planner import _inject_freshness_for_historical_dates

        # All four claims now have a DATE entity — claim 0 has its own,
        # claims 1-3 have inherited entries carrying the provenance
        # flag. Inject must fire on ALL of them.
        plans = [
            {"claim_index": 0, "freshness": "py", "queries": ["GBR bleaching 2024"]},
            {"claim_index": 1, "freshness": "py", "queries": ["GBRMPA surveys"]},
            {"claim_index": 2, "freshness": "py", "queries": ["Coral Sea anomaly"]},
            {"claim_index": 3, "freshness": "py", "queries": ["AIMS attribution"]},
        ]
        claims = [
            {
                "claim_index": 0,
                "key_entities": [
                    {"text": "Great Barrier Reef", "type": "LOCATION"},
                    {"text": "March 2024", "type": "DATE"},
                ],
            },
            {
                "claim_index": 1,
                "key_entities": [
                    {"text": "GBRMPA", "type": "ORG"},
                    {"text": "two-thirds", "type": "AMOUNT"},
                    {
                        "text": "March 2024",
                        "type": "DATE",
                        "source": "article_inheritance",
                    },
                ],
            },
            {
                "claim_index": 2,
                "key_entities": [
                    {"text": "1.5°C", "type": "AMOUNT"},
                    {"text": "Coral Sea", "type": "LOCATION"},
                    {
                        "text": "March 2024",
                        "type": "DATE",
                        "source": "article_inheritance",
                    },
                ],
            },
            {
                "claim_index": 3,
                "key_entities": [
                    {"text": "AIMS", "type": "ORG"},
                    {
                        "text": "March 2024",
                        "type": "DATE",
                        "source": "article_inheritance",
                    },
                ],
            },
        ]
        result = _inject_freshness_for_historical_dates(
            plans, claims, current_year=2026
        )
        # All four plans now have freshness="none" — historical
        # event, original-period content allowed through.
        for plan in result:
            assert plan["freshness"] == "none", (
                f"plan claim_index={plan['claim_index']} kept "
                f"freshness={plan['freshness']!r} — propagation broken"
            )

    def test_provenance_flag_does_not_affect_year_extraction(self):
        # Defensive: the provenance flag is an extra key; the year
        # extractor must ignore it and work identically to LLM-emitted
        # DATEs.
        from app.utils.query_planner import _extract_max_year_from_entities

        with_flag = [
            {"text": "March 2024", "type": "DATE", "source": "article_inheritance"}
        ]
        without_flag = [{"text": "March 2024", "type": "DATE"}]
        assert (
            _extract_max_year_from_entities(with_flag)
            == _extract_max_year_from_entities(without_flag)
            == 2024
        )


class TestValidateFreshnessNoneIsAccepted:
    """B4: 'none' is now a valid freshness value."""

    def test_validate_plans_accepts_none_freshness(self):
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        plans = [
            {
                "claim_index": 0,
                "element_id": "e1",
                "queries": ["historical query"],
                "freshness": "none",
                "reasoning": "Historical event",
            }
        ]
        validated = planner._validate_plans(plans, 1)
        assert validated[0]["freshness"] == "none"


class TestBatchCapacityAndAttribution:
    """Phase 2 (2026-07-27) — a batch is now up to 30 element plans, not 5.

    Design: audit/2026-07-27_phase2_element_retrieval_build_design.md
    """

    def test_planning_token_budget_scales_with_element_count(self):
        from app.utils.query_planner import _planning_max_tokens

        # One element: unchanged from the pre-Phase-2 constant.
        assert _planning_max_tokens(1) == 3000
        assert _planning_max_tokens(5) == 3000
        # A wired batch (5 claims x 6 lanes) must ask for more than 3000, or
        # google_ai's truncation REPAIR silently returns a short plans list
        # and the tail elements lose their queries with no failure.
        assert _planning_max_tokens(30) > 3000
        # Bounded.
        assert _planning_max_tokens(1000) == 8000

    @pytest.mark.asyncio
    async def test_google_call_receives_the_scaled_budget(self):
        from app.utils.query_planner import LLMQueryPlanner, _planning_max_tokens

        planner = LLMQueryPlanner()
        planner.google_ai_api_key = "test-key"
        planner.openai_api_key = "test-key"

        claims = [
            {
                "text": f"claim {c}",
                "claim_index": c,
                "elements": [
                    {"element_id": f"e{e}", "description": f"ground {c}-{e}"}
                    for e in range(6)
                ],
            }
            for c in range(5)
        ]

        captured = {}

        async def _fake_call(prompt, **kwargs):
            captured.update(kwargs)
            return {"plans": []}

        with patch("app.utils.query_planner.call_google_ai", _fake_call):
            await planner.plan_queries_batch(claims)

        assert captured["max_tokens"] == _planning_max_tokens(30)
        assert captured["max_tokens"] > 3000

    @pytest.mark.asyncio
    async def test_openai_fallback_receives_the_scaled_budget(self):
        """Criterion 12 says BOTH providers, and the fallback is the one that
        matters most: it runs when Gemini is down, which is exactly when a
        silent short-plans truncation would be hardest to attribute."""
        from app.utils.query_planner import LLMQueryPlanner, _planning_max_tokens

        planner = LLMQueryPlanner()
        planner.google_ai_api_key = None  # force the OpenAI fallback path
        planner.openai_api_key = "test-key"

        claims = [
            {
                "text": f"claim {c}",
                "claim_index": c,
                "elements": [
                    {"element_id": f"e{e}", "description": f"ground {c}-{e}"}
                    for e in range(6)
                ],
            }
            for c in range(5)
        ]

        captured = {}

        class _FakeResponse:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": '{"plans": []}'}}]}

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, headers=None, json=None):
                captured.update(json or {})
                return _FakeResponse()

        with patch(
            "app.utils.query_planner.httpx.AsyncClient",
            lambda *a, **k: _FakeClient(),
        ):
            await planner.plan_queries_batch(claims)

        assert captured["max_tokens"] == _planning_max_tokens(30)
        # Literal, not the function it pins: an assertion written against the
        # helper it is meant to protect passes under any mutation of it.
        assert captured["max_tokens"] > 3000

    def test_year_fix_attributes_plans_by_element_key_not_position(self):
        """Plan ORDER is the LLM's choice; attribution must not depend on it."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        current_year = __import__("datetime").datetime.now().year
        historical_year = current_year - 2

        element_texts = {
            (0, "e1"): (f"A claim about the {historical_year} floods", "ground A"),
            (1, "e1"): ("A claim with no year at all", "ground B"),
        }

        # Returned in the reverse order the elements were listed in.
        plans = [
            {
                "claim_index": 1,
                "element_id": "e1",
                "queries": [f"unrelated {historical_year} figures"],
                "freshness": "pm",
            },
            {
                "claim_index": 0,
                "element_id": "e1",
                "queries": [f"{historical_year} floods damage"],
                "freshness": "pm",
            },
        ]

        validated = planner._validate_plans(plans, 2, element_texts)

        by_key = {(p["claim_index"], p["element_id"]): p for p in validated}
        # Claim 0 typed the year: preserved.
        assert str(historical_year) in by_key[(0, "e1")]["queries"][0]
        # Claim 1 did not: treated as a hallucinated year and rewritten.
        assert str(current_year) in by_key[(1, "e1")]["queries"][0]

    def test_positional_element_texts_still_supported(self):
        """Legacy callers pass a list; behaviour must be unchanged for them."""
        from app.utils.query_planner import LLMQueryPlanner

        planner = LLMQueryPlanner()
        current_year = __import__("datetime").datetime.now().year
        historical_year = current_year - 2

        validated = planner._validate_plans(
            [
                {
                    "claim_index": 0,
                    "element_id": "e1",
                    "queries": [f"{historical_year} floods damage"],
                    "freshness": "pm",
                }
            ],
            1,
            [(f"A claim about the {historical_year} floods", "ground A")],
        )

        assert str(historical_year) in validated[0]["queries"][0]
