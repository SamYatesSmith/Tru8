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
    async def test_mixed_batch_adapter_kept_web_excluded(self, mock_llm_scores):
        """In a batch with both adapter and web-search items all at score=1,
        only adapter items survive. Demonstrates the Bills + Serper scenario
        from TRU-E545-4080 where the final evidence was web-only."""
        mock_llm_scores.set_score_sequence(
            lambda claims, ev, ctx: self._score_all_1(claims, ev, ctx)
        )

        evidence = {
            "0": [
                # 3 adapter items (Bills, Hansard, GOV.UK) — all must survive
                {
                    "url": "https://bills.parliament.uk/bills/195",
                    "title": "Equality Bill",
                    "snippet": "UK Parliament Bill, 2nd reading.",
                    "external_source_provider": "UK Parliament Bills",
                },
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
                # 2 web-search items — both must be dropped at score=1
                {
                    "url": "https://bamboohr.com/uk/blog/equality-act",
                    "title": "HR blog",
                    "snippet": "HR thoughts on the Act.",
                },
                {
                    "url": "https://www.dileaders.com/equality-act",
                    "title": "Business post",
                    "snippet": "Business advice post.",
                },
            ]
        }

        result = await score_evidence_batch(
            claims=["The Equality Act consolidated UK anti-discrimination law"],
            evidence=evidence,
            article_context="",
        )

        kept = result["0"]
        assert len(kept) == 3, "3 adapter items must survive"
        kept_providers = {ev["external_source_provider"] for ev in kept}
        assert kept_providers == {
            "UK Parliament Bills",
            "UK Parliament Hansard",
            "GOV.UK Content API",
        }
        for ev in kept:
            assert ev["relevance_scorer_bypass"] == "api_adapter_canonical_source"

        assert len(result.get("_excluded", [])) == 2
        excluded_urls = {ev["url"] for ev in result["_excluded"]}
        assert "bamboohr.com" in "|".join(excluded_urls)
        assert "dileaders.com" in "|".join(excluded_urls)

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
        # Empty string is falsy → no bypass → excluded as normal
        assert result["0"] == []
        assert len(result.get("_excluded", [])) == 1
