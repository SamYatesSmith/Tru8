"""NF-07 regression guards for the relevance scorer's API-adapter bypass.

Observed on TRU-E545-4080 (Equality Act 2010 production check): the UK
Parliament Bills adapter returned 5 topical bills, the LLM scorer
judged all 5 snippets as irrelevant (score=1), and they were excluded
before reaching the classifier. Final evidence contained zero
parliament.uk URLs despite SC-15 firing correctly.

Root cause: the scorer judges snippet content ("does this text address
the claim?") while API adapters return items where the URL identity is
the claim-relevant signal. Synthesised metadata snippets from Bills,
Hansard's fallback path, and LoC's Collections path assert nothing
about the claim's content — they describe procedural status.

Fix: items with `external_source_provider` set are bypassed by the
score=1 exclusion step. They still get their score annotated for
downstream ordering, but they reach the classifier (which correctly
tiers them as primary via URL identity).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.relevance_scorer import score_evidence_batch


class TestRelevanceScorerNF07Bypass:
    """API-adapter items with score=1 are kept; raw web-search items are dropped."""

    @pytest.fixture
    def mock_llm_scores(self):
        """Patch both scoring backends + cache helpers so tests drive scores
        deterministically. score_evidence_batch tries Google first, falls back
        to OpenAI — patch both so we don't accidentally hit either real API.
        """
        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            new_callable=AsyncMock,
        ) as mg, patch(
            "app.pipeline.relevance_scorer._score_with_llm",
            new_callable=AsyncMock,
        ) as ml, patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Expose a helper that sets both backends to the same side_effect
            def set_score_sequence(fn):
                mg.side_effect = fn
                ml.side_effect = fn

            mg.set_score_sequence = set_score_sequence
            yield mg

    def _score_all_1(self, claims, all_evidence, article_context):
        """Helper: return score=1 for every item (simulates scorer rejecting all)."""
        return [
            {
                "evidence_index": i,
                "score": 1,
                "rationale": "off-topic",
                "relevant_claims": [],
            }
            for i in range(len(all_evidence))
        ]

    @pytest.mark.asyncio
    async def test_api_adapter_item_kept_despite_score_1(self, mock_llm_scores):
        """An item from UK Parliament Bills that scores 1 must stay in the
        evidence list — its URL identity is the primary-tier signal, not the
        synthesised snippet."""
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: self._score_all_1(claims, ev, ctx)
        )

        evidence = {
            "0": [
                {
                    "url": "https://bills.parliament.uk/bills/195",
                    "title": "Equality Bill",
                    "snippet": "UK Parliament Bill, 2nd reading in Commons.",
                    "external_source_provider": "UK Parliament Bills",
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["The Equality Act consolidated UK anti-discrimination law"],
            evidence=evidence,
            article_context="",
        )

        assert len(result["0"]) == 1, "Bills item must survive score=1 bypass"
        kept = result["0"][0]
        assert kept["llm_relevance_score"] == 1
        assert kept["relevance_scorer_bypass"] == "api_adapter_canonical_source"
        assert kept.get("receipt_status") != "excluded"
        assert "_excluded" not in result or not result.get("_excluded")

    @pytest.mark.asyncio
    async def test_web_search_item_excluded_at_score_1(self, mock_llm_scores):
        """A web-search item (no external_source_provider) with score=1 still
        gets excluded per the existing behaviour — bypass only applies to
        canonical API adapters."""
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: self._score_all_1(claims, ev, ctx)
        )

        evidence = {
            "0": [
                {
                    "url": "https://some-blog.example.com/post",
                    "title": "Random post",
                    "snippet": "Unrelated content about kittens.",
                    # no external_source_provider → this is a web-search item
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["The Equality Act consolidated UK anti-discrimination law"],
            evidence=evidence,
            article_context="",
        )

        assert result["0"] == [], "Web-search item with score=1 must be excluded"
        assert "_excluded" in result
        assert len(result["_excluded"]) == 1
        assert result["_excluded"][0]["exclusion_reason"] == "irrelevant"

    @pytest.mark.asyncio
    async def test_mixed_batch_canonical_kept_others_excluded(self, mock_llm_scores):
        """NF-07-hardening (2026-04-27): with a mixed batch all at score=1,
        only canonical-record-provider items survive (Bills, GBIF). Search-
        shape adapters (OpenAlex, Wikipedia, GOV.UK Content API, Hansard,
        LoC) join web-search items in the excluded bucket because their
        snippets are content text — when the scorer says irrelevant, it
        really is irrelevant. Pre-hardening this test asserted Hansard +
        GOV.UK survived; that was the regression TRU-A3E8-3199 surfaced.
        """
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: self._score_all_1(claims, ev, ctx)
        )

        evidence = {
            "0": [
                # Canonical-record providers (whitelisted) — must survive
                {
                    "url": "https://bills.parliament.uk/bills/195",
                    "title": "Equality Bill",
                    "snippet": "UK Parliament Bill, 2nd reading.",
                    "external_source_provider": "UK Parliament Bills",
                },
                {
                    "url": "https://www.gbif.org/species/2418436",
                    "title": "Carcharodon carcharias",
                    "snippet": "Scientific classification: Animalia > Chordata.",
                    "external_source_provider": "GBIF",
                },
                # Search-shape adapters (NOT whitelisted) — must be excluded
                {
                    "url": "https://hansard.parliament.uk/Lords/2009-11-01/debates/x",
                    "title": "Equality Bill debate",
                    "snippet": "UK Parliament Lords debate.",
                    "external_source_provider": "UK Parliament Hansard",
                },
                {
                    "url": "https://www.gov.uk/guidance/equality-act-2010",
                    "title": "Equality Act guidance",
                    "snippet": "Guidance on the Equality Act.",
                    "external_source_provider": "GOV.UK Content API",
                },
                {
                    "url": "https://doi.org/10.1234/some-paper",
                    "title": "Off-topic paper",
                    "snippet": "Paper abstract content.",
                    "external_source_provider": "OpenAlex",
                },
                {
                    "url": "https://en.wikipedia.org/wiki/Greenland_shark",
                    "title": "Greenland shark",
                    "snippet": "The Greenland shark is a large shark.",
                    "external_source_provider": "Wikipedia",
                },
                # Web-search items (no provider) — also excluded
                {
                    "url": "https://bamboohr.com/uk/blog/equality-act",
                    "title": "HR blog",
                    "snippet": "HR thoughts on the Act.",
                },
            ]
        }

        result = await score_evidence_batch(
            claims=["The Equality Act consolidated UK anti-discrimination law"],
            evidence=evidence,
            article_context="",
        )

        kept = result["0"]
        kept_providers = {ev.get("external_source_provider") for ev in kept}
        assert kept_providers == {"UK Parliament Bills", "GBIF"}
        for ev in kept:
            assert ev["relevance_scorer_bypass"] == "api_adapter_canonical_source"

        assert len(result.get("_excluded", [])) == 5
        excluded_providers = {
            ev.get("external_source_provider") for ev in result["_excluded"]
        }
        # Hansard / GOV.UK / OpenAlex / Wikipedia all excluded; web item has None
        assert excluded_providers == {
            "UK Parliament Hansard",
            "GOV.UK Content API",
            "OpenAlex",
            "Wikipedia",
            None,
        }

    @pytest.mark.asyncio
    async def test_adapter_item_with_score_gte_2_unchanged(self, mock_llm_scores):
        """Adapter items with score >= 2 are kept normally — the bypass is
        only about score=1 exclusion, not a change to general scoring behaviour."""
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: [
                {
                    "evidence_index": 0,
                    "score": 4,
                    "rationale": "on-topic",
                    "relevant_claims": [0],
                }
            ]
        )

        evidence = {
            "0": [
                {
                    "url": "https://bills.parliament.uk/bills/195",
                    "title": "Equality Bill",
                    "snippet": "UK Parliament Bill.",
                    "external_source_provider": "UK Parliament Bills",
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["Equality Act consolidated UK law"],
            evidence=evidence,
            article_context="",
        )

        kept = result["0"][0]
        assert kept["llm_relevance_score"] == 4
        # No bypass marker — item passed on its own merits
        assert "relevance_scorer_bypass" not in kept

    @pytest.mark.asyncio
    async def test_empty_external_source_provider_string_does_not_bypass(
        self, mock_llm_scores
    ):
        """Defensive: an empty-string provider (shouldn't happen in practice
        but might if an adapter misconfigures) doesn't trigger the bypass."""
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: self._score_all_1(claims, ev, ctx)
        )

        evidence = {
            "0": [
                {
                    "url": "https://example.com/x",
                    "title": "x",
                    "snippet": "x",
                    "external_source_provider": "",  # falsy
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["claim"],
            evidence=evidence,
            article_context="",
        )
        # Empty string isn't in the whitelist → no bypass → excluded as normal
        assert result["0"] == []
        assert len(result.get("_excluded", [])) == 1


class TestNF07HardeningWhitelist:
    """NF-07-hardening (2026-04-27) regression guards.

    The original NF-07 bypassed any item with `external_source_provider` set,
    on the assumption that adapter URL identity overrode snippet judgement.
    Audit of TRU-A3E8-3199 (great white sharks) showed the bypass was
    keeping irrelevant OpenAlex/Wikipedia content snippets at score=1, with
    only a 12% real mapping rate across 17 production bypassed items.

    The fix scopes the bypass to a whitelist of canonical-record providers
    whose snippets are STRUCTURED METADATA (taxonomic hierarchy, bill
    stage, observation data) — for these the original NF-07 reasoning
    holds. Search-shape providers whose snippets are CONTENT TEXT lose the
    bypass: when the scorer judges content text irrelevant, it really is.
    """

    @pytest.fixture
    def mock_score_1(self):
        """Score every item as 1 deterministically."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.pipeline.relevance_scorer._score_with_google",
            new_callable=AsyncMock,
        ) as mg, patch(
            "app.pipeline.relevance_scorer._score_with_llm",
            new_callable=AsyncMock,
        ) as ml, patch(
            "app.pipeline.relevance_scorer._get_cached_relevance_scores",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.pipeline.relevance_scorer._cache_relevance_scores",
            new_callable=AsyncMock,
            return_value=None,
        ):
            score_fn = lambda claims, ev, ctx: [
                {
                    "evidence_index": i,
                    "score": 1,
                    "rationale": "off-topic",
                    "relevant_claims": [],
                }
                for i in range(len(ev))
            ]
            mg.side_effect = score_fn
            ml.side_effect = score_fn
            yield

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider",
        [
            "UK Parliament Bills",
            "Companies House",
            "FRED",
            "ONS Economic Statistics",
            "World Bank",
            "WHO",
            "NOAA CDO",
            "WeatherAPI",
            "Open-Meteo",
            "Football-Data.org",
            "Transfermarkt",
            "GBIF",
            "Wikidata",
        ],
    )
    async def test_canonical_record_providers_still_bypass(
        self, mock_score_1, provider
    ):
        """Whitelist providers must still receive the score=1 bypass.
        Each parameter is a provider that emits structured-metadata
        snippets where URL identity is the primary-tier signal."""
        evidence = {
            "0": [
                {
                    "url": f"https://example.com/{provider}",
                    "title": f"{provider} item",
                    "snippet": "Structural metadata, not content text.",
                    "external_source_provider": provider,
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["test claim"],
            evidence=evidence,
            article_context="",
        )
        assert len(result["0"]) == 1, f"{provider} must keep bypass"
        assert (
            result["0"][0]["relevance_scorer_bypass"] == "api_adapter_canonical_source"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider",
        [
            "OpenAlex",  # paper abstracts (TRU-A3E8-3199 noise: 3 items)
            "Semantic Scholar",  # paper abstracts
            "PubMed",  # paper abstracts
            "CrossRef",  # paper metadata
            "Wikipedia",  # article intros (TRU-A3E8-3199 noise: 5 items)
            "Marketaux",  # news snippets
            "GOV.UK Content API",  # page descriptions (TRU-A0C5-05DB: 6 of 7 noise)
            "UK Parliament Hansard",  # debate text snippets
            "Library of Congress",  # mixed item descriptions
            "Chronicling America",  # newspaper text
            "Internet Archive",  # archived page content
        ],
    )
    async def test_search_shape_providers_excluded_at_score_1(
        self, mock_score_1, provider
    ):
        """Search-shape providers no longer bypass score=1 — their
        snippets are content text that the scorer is reading correctly.
        Pre-hardening these all flowed through the bypass and polluted
        the mapper input; this test pins the corrected behaviour."""
        evidence = {
            "0": [
                {
                    "url": f"https://example.com/{provider}",
                    "title": f"{provider} item",
                    "snippet": "Content text the scorer rated 1.",
                    "external_source_provider": provider,
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["test claim"],
            evidence=evidence,
            article_context="",
        )
        assert result["0"] == [], f"{provider} must NOT bypass under hardening"
        assert len(result.get("_excluded", [])) == 1
        assert result["_excluded"][0]["exclusion_reason"] == "irrelevant"

    @pytest.mark.asyncio
    async def test_unknown_provider_does_not_bypass(self, mock_score_1):
        """Defensive: an unknown provider name (e.g. typo, new adapter
        not yet whitelisted) does not get the bypass. Worst-case behaviour
        is "exclude valid item" rather than "leak noise" — keeps the
        whitelist explicit."""
        evidence = {
            "0": [
                {
                    "url": "https://example.com/x",
                    "title": "Unknown adapter",
                    "snippet": "x",
                    "external_source_provider": "Brand New Adapter Not Yet Whitelisted",
                }
            ]
        }
        result = await score_evidence_batch(
            claims=["claim"],
            evidence=evidence,
            article_context="",
        )
        assert result["0"] == []
        assert len(result.get("_excluded", [])) == 1
