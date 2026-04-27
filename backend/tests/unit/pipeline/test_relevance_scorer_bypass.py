"""NF-07 regression guards for the relevance scorer's API-adapter bypass.

History:
- Original NF-07 (commit ec175d1, 2026-04-24): bypassed score=1 for any
  item with external_source_provider set. Motivated by TRU-E545-4080
  (Equality Act 2010): Bills adapter returned 5 topical bills, all
  scored 1 by snippet, all dropped — zero parliament.uk URLs in final.
- NF-07-hardening (commit 910c8e1, 2026-04-27): scoped via a frozen
  whitelist of 13 canonical-record providers after TRU-A3E8-3199 audit
  showed the unscoped bypass had a 12% real mapping rate (2 of 17
  bypassed items actually picked by the mapper).
- NF-07-v2 (this commit): replaced the frozen whitelist with adapter
  self-declaration. Each adapter declares
  `emits_structural_metadata: bool = False` on
  GovernmentAPIClient.__init__; the scorer queries the registry. New
  adapters self-classify; no central list to maintain.

These tests verify the SCORER respects whatever the adapter declares.
The contract that adapters declare correctly (e.g. Bills=True,
OpenAlex=False) is verified separately in tests covering each
adapter class.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.relevance_scorer import score_evidence_batch


# Provider-name → emits_structural_metadata. Reflects the current
# adapter declarations as of NF-07-v2 (commit landing this file).
# When new adapters are added/changed, update this map alongside the
# adapter class — the scorer test will then confirm the scorer
# delegates correctly.
_TEST_ADAPTER_DECLARATIONS = {
    # Canonical-record adapters (declare True)
    "UK Parliament Bills": True,
    "Companies House": True,
    "FRED": True,
    "ONS Economic Statistics": True,
    "World Bank": True,
    "WHO": True,
    "NOAA CDO": True,
    "WeatherAPI": True,
    "Open-Meteo": True,
    "Football-Data.org": True,
    "Transfermarkt": True,
    "GBIF": True,
    "Wikidata": True,
    # Search-shape adapters (declare False)
    "OpenAlex": False,
    "Semantic Scholar": False,
    "PubMed": False,
    "CrossRef": False,
    "Wikipedia": False,
    "Marketaux": False,
    "GOV.UK Content API": False,
    "UK Parliament Hansard": False,
    "Library of Congress": False,
    "Chronicling America": False,
    "Internet Archive": False,
}


@pytest.fixture(autouse=True)
def mock_adapter_declarations():
    """Autouse: patch the registry lookup so the scorer's test contract
    is decoupled from adapter registration plumbing (which depends on
    settings, API keys, etc.). Unknown providers default to False —
    same defensive behaviour as the production code path."""

    def _stub(provider):
        if not provider:
            return False
        return _TEST_ADAPTER_DECLARATIONS.get(provider, False)

    with patch(
        "app.pipeline.relevance_scorer._adapter_emits_structural_metadata",
        side_effect=_stub,
    ):
        yield


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


class TestNF07v2AdapterContract:
    """NF-07-v2 contract: each adapter class declares its own
    `emits_structural_metadata`. The scorer's tests above use a fixture
    map, but the SOURCE OF TRUTH is each adapter's __init__ call. This
    class instantiates each adapter and asserts the declaration matches
    the fixture map — so if anyone changes an adapter's declaration
    without updating the fixture (or vice versa), the test fails loudly.

    Disable autouse fixture for this class — these tests don't call the
    scorer; they introspect adapter classes directly.
    """

    @pytest.fixture(autouse=True)
    def _no_scorer_patch(self, monkeypatch):
        # No-op override of the module-level autouse fixture.
        # Re-stub _adapter_emits_structural_metadata as identity so any
        # accidental scorer call still works deterministically.
        pass

    def test_canonical_adapters_declare_true(self):
        """Each canonical-record adapter in the fixture map must instantiate
        cleanly and declare emits_structural_metadata=True. Catches drift
        between an adapter's declaration and the fixture's expectations."""
        from app.services.api_adapters import (
            CompaniesHouseAdapter,
            FREDAdapter,
            FootballDataAdapter,
            GBIFAdapter,
            NOAAAdapter,
            ONSAdapter,
            OpenMeteoAdapter,
            TransfermarktAdapter,
            UKParliamentBillsAdapter,
            WHOAdapter,
            WeatherAPIAdapter,
            WikidataAdapter,
            WorldBankAdapter,
        )

        canonical_adapter_classes = {
            "Companies House": CompaniesHouseAdapter,
            "FRED": FREDAdapter,
            "Football-Data.org": FootballDataAdapter,
            "GBIF": GBIFAdapter,
            "NOAA CDO": NOAAAdapter,
            "ONS Economic Statistics": ONSAdapter,
            "Open-Meteo": OpenMeteoAdapter,
            "Transfermarkt": TransfermarktAdapter,
            "UK Parliament Bills": UKParliamentBillsAdapter,
            "WHO": WHOAdapter,
            "WeatherAPI": WeatherAPIAdapter,
            "Wikidata": WikidataAdapter,
            "World Bank": WorldBankAdapter,
        }
        for api_name, cls in canonical_adapter_classes.items():
            adapter = cls()
            assert (
                adapter.api_name == api_name
            ), f"{cls.__name__} api_name should be {api_name!r}, got {adapter.api_name!r}"
            assert adapter.emits_structural_metadata is True, (
                f"{cls.__name__} must declare emits_structural_metadata=True "
                f"(NF-07-v2 contract)"
            )

    def test_search_shape_adapters_declare_false(self):
        """Adapters whose snippets are content text default to False
        (the GovernmentAPIClient base default). Pin a sample of them to
        catch any accidental opt-in."""
        from app.services.api_adapters import (
            CrossRefAdapter,
            GovUKAdapter,
            HansardAdapter,
            OpenAlexAdapter,
            PubMedAdapter,
            SemanticScholarAdapter,
        )

        for cls in (
            CrossRefAdapter,
            GovUKAdapter,
            HansardAdapter,
            OpenAlexAdapter,
            PubMedAdapter,
            SemanticScholarAdapter,
        ):
            adapter = cls()
            assert adapter.emits_structural_metadata is False, (
                f"{cls.__name__} must declare emits_structural_metadata=False "
                f"(content-text snippets get scorer's judgement)"
            )
