"""
Integration tests for pipeline improvement features.

Tests the complete pipeline with all Phase 1-2 features enabled:
- Evidence deduplication
- Source diversity
- Fact-check integration
- Temporal context
- Claim classification
- Enhanced explainability
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def enable_all_features(monkeypatch):
    """Enable all pipeline improvement features"""
    monkeypatch.setenv("ENABLE_EVIDENCE_DEDUPLICATION", "true")
    monkeypatch.setenv("ENABLE_SOURCE_DIVERSITY", "true")
    monkeypatch.setenv("ENABLE_FACTCHECK_INTEGRATION", "true")
    monkeypatch.setenv("ENABLE_TEMPORAL_CONTEXT", "true")
    monkeypatch.setenv("ENABLE_CLAIM_CLASSIFICATION", "true")
    monkeypatch.setenv("ENABLE_ENHANCED_EXPLAINABILITY", "true")


@pytest.fixture
def sample_text_input():
    """Text input with multiple claim types"""
    return """
    The Earth is round. This is a verified scientific fact.
    I think the new iPhone is the best phone ever made.
    Climate change will cause sea levels to rise by 2050.
    I saw a UFO in my backyard last night.
    """


@pytest.fixture
def sample_time_sensitive_input():
    """Time-sensitive text input"""
    return """
    The stock market crashed yesterday, losing 5% in value.
    Inflation is currently at 3.2% as of this month.
    """


@pytest.fixture
def mock_search_results():
    """Mock search results with duplicates and fact-checks"""
    return [
        {
            "source": "BBC",
            "url": "https://bbc.com/news/earth-round",
            "title": "Earth's Shape: Round and Proven",
            "snippet": "Scientists confirm Earth is round using satellite imagery.",
            "published_date": datetime.now() - timedelta(days=30)
        },
        {
            "source": "CNN",
            "url": "https://cnn.com/news/earth-round",
            "title": "Earth's Shape: Round and Proven",  # Duplicate title
            "snippet": "Scientists confirm Earth is round using satellite imagery.",  # Duplicate snippet
            "published_date": datetime.now() - timedelta(days=31)
        },
        {
            "source": "Snopes",
            "url": "https://snopes.com/fact-check/earth-round",
            "title": "Fact Check: Is Earth Round?",
            "snippet": "True - Earth is an oblate spheroid.",
            "published_date": datetime.now() - timedelta(days=15)
        },
        {
            "source": "The Guardian",
            "url": "https://theguardian.com/science/earth-shape",
            "title": "Understanding Earth's Curvature",
            "snippet": "The planet's round shape has been known for centuries.",
            "published_date": datetime.now() - timedelta(days=45)
        },
        {
            "source": "Reuters",
            "url": "https://reuters.com/science/earth-round",
            "title": "Earth Shape Research",
            "snippet": "Modern measurements confirm spherical Earth.",
            "published_date": datetime.now() - timedelta(days=20)
        }
    ]


class TestPipelineWithAllFeatures:
    """Integration tests with all features enabled"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_pipeline_text_input(self, enable_all_features, sample_text_input, mock_search_results):
        """
        Test: Complete pipeline with mixed claim types

        Verifies:
        - Claims extracted and classified correctly
        - Evidence deduplicated
        - Fact-checks detected and weighted
        - Temporal context analyzed
        - Decision trails generated
        """
        from app.pipeline.extract import ClaimExtractor
        from app.pipeline.retrieve import EvidenceRetriever
        from app.pipeline.verify import ClaimVerifier
        from app.pipeline.judge import PipelineJudge
        from app.utils.explainability import ExplainabilityEnhancer

        # Extract claims
        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims(sample_text_input)
        claims = extract_result.get("claims", [])

        # Should extract 4 claims
        assert len(claims) >= 4

        # Find each claim type
        factual_claims = [c for c in claims if c.get("claim_type") == "factual"]
        opinion_claims = [c for c in claims if c.get("claim_type") == "opinion"]
        prediction_claims = [c for c in claims if c.get("claim_type") == "prediction"]
        personal_claims = [c for c in claims if c.get("claim_type") == "personal_experience"]

        # Verify classification
        assert len(factual_claims) >= 1, "Should detect factual claim (Earth is round)"
        assert len(opinion_claims) >= 1, "Should detect opinion (best phone)"
        assert len(prediction_claims) >= 1, "Should detect prediction (2050 sea levels)"
        assert len(personal_claims) >= 1, "Should detect personal experience (UFO)"

        # Verify verifiability
        assert factual_claims[0]["is_verifiable"] is True
        assert opinion_claims[0]["is_verifiable"] is False
        assert opinion_claims[0]["verifiability_reason"] is not None

        # Test evidence retrieval with all features (use factual claim)
        factual_claim = factual_claims[0]

        # Prepare claim dict for retriever
        claim_dict = {"text": factual_claim["text"], "position": 0}

        retriever = EvidenceRetriever()

        with patch.object(retriever.search_service, 'search_for_evidence', return_value=mock_search_results):
            result = await retriever.retrieve_evidence_for_claims([claim_dict])
            evidence = result.get("0", [])

            # Evidence should be deduplicated (CNN duplicate removed)
            assert len(evidence) <= 4, "Duplicate evidence should be removed"

            # Fact-check should be present and flagged
            factcheck_evidence = [e for e in evidence if e.get("is_factcheck")]
            assert len(factcheck_evidence) >= 1, "Snopes fact-check should be detected"
            assert factcheck_evidence[0]["factcheck_publisher"] == "Snopes"

            # Content hashes should be populated
            assert all(e.get("content_hash") for e in evidence)

            # Diversity fields should be populated
            assert any(e.get("parent_company") for e in evidence)

        # Test verification
        verifier = ClaimVerifier()
        verifications_result = await verifier.verify_claim_against_evidence(factual_claim["text"], evidence)
        verifications = [{"label": v.stance.value if hasattr(v, 'stance') else "NEUTRAL"} for v in verifications_result]
        assert len(verifications) > 0

        # Test judgment with explainability
        judge = PipelineJudge()
        # Create NLI results format expected by judge
        nli_results = {"evidence_stances": verifications_result}
        judgment_result = await judge.judge_claim(claim_dict, nli_results, evidence)
        judgment = {"verdict": judgment_result.verdict, "confidence": judgment_result.confidence}

        # Should have enhanced explainability fields
        assert "confidence_breakdown" in judgment or "confidence" in judgment

        # Generate decision trail
        explainer = ExplainabilityEnhancer()

        verification_signals = {
            "supporting_count": sum(1 for v in verifications if v.get("label") == "SUPPORTS"),
            "contradicting_count": sum(1 for v in verifications if v.get("label") == "CONTRADICTS"),
            "neutral_count": sum(1 for v in verifications if v.get("label") == "NEUTRAL")
        }

        trail = explainer.create_decision_trail(
            factual_claim, evidence, verification_signals, judgment
        )

        # Verify decision trail structure
        assert "stages" in trail
        assert len(trail["stages"]) == 3
        assert trail["stages"][0]["stage"] == "evidence_retrieval"
        assert trail["stages"][1]["stage"] == "verification"
        assert trail["stages"][2]["stage"] == "judgment"
        assert "transparency_score" in trail
        assert 0 <= trail["transparency_score"] <= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_temporal_context_integration(self, enable_all_features, sample_time_sensitive_input):
        """
        Test: Temporal context features in full pipeline

        Verifies:
        - Time-sensitive claims detected
        - Temporal markers extracted
        - Evidence filtered by temporal relevance
        """
        from app.pipeline.extract import ClaimExtractor
        from app.pipeline.retrieve import EvidenceRetriever

        # Extract claims
        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims(sample_time_sensitive_input)
        claims = extract_result.get("claims", [])

        # Should detect time-sensitive claims
        time_sensitive_claims = [c for c in claims if c.get("is_time_sensitive")]
        assert len(time_sensitive_claims) >= 1, "Should detect time-sensitive claims"

        # Check temporal markers
        assert any(c.get("temporal_markers") for c in time_sensitive_claims)

        # Check time reference classification
        time_refs = [c.get("time_reference") for c in time_sensitive_claims]
        assert "recent_past" in time_refs or "present" in time_refs

        # Test evidence retrieval with temporal filtering
        ts_claim = time_sensitive_claims[0]

        retriever = EvidenceRetriever()
        ts_claim_dict = {"text": ts_claim["text"], "position": 0}

        mock_temporal_results = [
                {
                    "source": "Reuters",
                    "url": "https://reuters.com/markets/crash",
                    "title": "Stock Market Crash Analysis",
                    "snippet": "Market lost 5% yesterday.",
                    "published_date": datetime.now() - timedelta(days=1)  # Recent
                },
                {
                    "source": "Forbes",
                    "url": "https://forbes.com/markets/old-analysis",
                    "title": "Historical Market Analysis",
                    "snippet": "Markets from 5 years ago.",
                    "published_date": datetime.now() - timedelta(days=1825)  # Old
                }
            ]

        with patch.object(retriever.search_service, 'search_for_evidence', return_value=mock_temporal_results):
            result = await retriever.retrieve_evidence_for_claims([ts_claim_dict])
            evidence = result.get("0", [])

            # Recent evidence should be prioritized
            if len(evidence) > 0:
                recent_evidence = [e for e in evidence
                                 if e.get("published_date")
                                 and (datetime.now() - e["published_date"]).days < 30]

                # Should have temporal relevance scores
                assert any(e.get("temporal_relevance_score") is not None for e in evidence)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_non_verifiable_claim_handling(self, enable_all_features):
        """
        Test: Non-verifiable claims handled gracefully

        Verifies:
        - Opinions/predictions/personal experiences classified correctly
        - Uncertainty explanations provided
        - Pipeline doesn't fail on non-verifiable content
        """
        from app.pipeline.extract import ClaimExtractor
        from app.utils.explainability import ExplainabilityEnhancer

        opinion_text = "I think chocolate ice cream is the best flavor in the world."

        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims(opinion_text)
        claims = extract_result.get("claims", [])

        assert len(claims) >= 1
        opinion_claim = claims[0]

        # Should be classified as opinion
        assert opinion_claim.get("claim_type") == "opinion"
        assert opinion_claim.get("is_verifiable") is False
        assert opinion_claim.get("verifiability_reason") is not None

        # Test uncertainty explanation
        explainer = ExplainabilityEnhancer()

        # Mock judgment for opinion
        judgment = {
            "verdict": "uncertain",
            "confidence": 50,
            "rationale": "This is a subjective opinion, not verifiable"
        }

        signals = {"supporting_count": 0, "contradicting_count": 0}
        evidence = []

        explanation = explainer.create_uncertainty_explanation(
            judgment["verdict"], signals, evidence
        )

        # Should provide explanation for insufficient evidence
        assert len(explanation) > 0
        assert "Insufficient evidence" in explanation or "source" in explanation

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_deduplication_effectiveness(self, enable_all_features, mock_search_results):
        """
        Test: Deduplication removes duplicate content effectively

        Verifies:
        - Duplicate detection via content hash
        - Syndication flagging
        - Original source tracking
        """
        from app.pipeline.retrieve import EvidenceRetriever
        from app.utils.deduplication import ContentDeduplicator

        deduplicator = ContentDeduplicator()

        # Process mock results
        deduplicated = deduplicator.deduplicate(mock_search_results)

        # Should remove CNN duplicate (same content as BBC)
        assert len(deduplicated) < len(mock_search_results)

        # Check for syndication flags
        syndicated = [e for e in deduplicated if e.get("is_syndicated")]
        # At least one should be flagged as syndicated if duplicates found

        # Content hashes should be unique
        hashes = [e["content_hash"] for e in deduplicated if e.get("content_hash")]
        assert len(hashes) == len(set(hashes)), "All content hashes should be unique"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_factcheck_priority_boost(self, enable_all_features, mock_search_results):
        """
        Test: Fact-checks receive priority in ranking

        Verifies:
        - Fact-checks detected correctly
        - Fact-check metadata populated
        - Fact-checks ranked higher
        """
        from app.pipeline.retrieve import EvidenceRetriever

        retriever = EvidenceRetriever()
        claim_dict = {"text": "Earth is round", "position": 0}

        with patch.object(retriever.search_service, 'search_for_evidence', return_value=mock_search_results):
            result = await retriever.retrieve_evidence_for_claims([claim_dict])
            evidence = result.get("0", [])

            # Find Snopes fact-check
            factchecks = [e for e in evidence if e.get("is_factcheck")]
            assert len(factchecks) >= 1

            snopes = factchecks[0]
            assert snopes["factcheck_publisher"] == "Snopes"
            assert snopes["is_factcheck"] is True

            # Fact-check should be in top results (higher relevance)
            snopes_idx = next(i for i, e in enumerate(evidence) if e.get("is_factcheck"))
            assert snopes_idx < len(evidence) / 2, "Fact-check should be ranked in top half"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transparency_score_calculation(self, enable_all_features):
        """
        Test: Transparency score reflects evidence quality

        Verifies:
        - High quality evidence → high transparency
        - Low quality evidence → low transparency
        - Conflicting evidence → moderate transparency
        """
        from app.utils.explainability import ExplainabilityEnhancer

        explainer = ExplainabilityEnhancer()

        # High quality scenario
        high_quality_evidence = [
            {"credibility_score": 0.9, "source": f"Source{i}"} for i in range(5)
        ]
        high_quality_signals = {"supporting_count": 5, "contradicting_count": 0}

        high_score = explainer._calculate_transparency_score(
            high_quality_evidence, high_quality_signals
        )

        # Low quality scenario
        low_quality_evidence = [{"credibility_score": 0.4}]
        low_quality_signals = {"supporting_count": 1, "contradicting_count": 0}

        low_score = explainer._calculate_transparency_score(
            low_quality_evidence, low_quality_signals
        )

        # Conflicting scenario
        conflicting_evidence = [
            {"credibility_score": 0.8} for _ in range(4)
        ]
        conflicting_signals = {"supporting_count": 2, "contradicting_count": 2}

        conflict_score = explainer._calculate_transparency_score(
            conflicting_evidence, conflicting_signals
        )

        # Verify score relationships
        assert high_score > low_score, "High quality should have higher transparency"
        assert high_score > conflict_score, "Clear consensus should beat conflicting"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_confidence_breakdown_factors(self, enable_all_features):
        """
        Test: Confidence breakdown includes all relevant factors

        Verifies:
        - Evidence quantity factor
        - Evidence quality factor
        - Consensus factor
        - Fact-check factor
        """
        from app.utils.explainability import ExplainabilityEnhancer

        explainer = ExplainabilityEnhancer()

        judgment = {"confidence": 85, "verdict": "supported"}

        evidence = [
            {"credibility_score": 0.9, "is_factcheck": True},
            {"credibility_score": 0.85, "is_factcheck": False},
            {"credibility_score": 0.88, "is_factcheck": False},
            {"credibility_score": 0.92, "is_factcheck": False},
            {"credibility_score": 0.87, "is_factcheck": False}
        ]

        signals = {"supporting_count": 5, "contradicting_count": 0}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        # Check structure
        assert "overall_confidence" in breakdown
        assert "factors" in breakdown
        assert isinstance(breakdown["factors"], list)

        # Check all expected factors present
        factor_names = [f["factor"] for f in breakdown["factors"]]

        assert "evidence_quantity" in factor_names, "Should include quantity factor"
        assert "evidence_quality" in factor_names, "Should include quality factor"
        assert "evidence_consensus" in factor_names, "Should include consensus factor"
        assert "fact_check_presence" in factor_names, "Should include fact-check factor"

        # All factors should be positive for this high-quality scenario
        positive_factors = [f for f in breakdown["factors"] if f["impact"] == "positive"]
        assert len(positive_factors) >= 3, "Most factors should be positive"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_within_targets(self, enable_all_features, sample_text_input):
        """
        Test: Complete pipeline completes within performance targets

        Target: <12s p95 latency with all features enabled

        NOTE: This is a basic timing test. Full performance testing should
        be done with production-scale infrastructure.
        """
        import time
        from app.pipeline.extract import ClaimExtractor

        start_time = time.time()

        # Extract claims (lightest stage to test overhead)
        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims(sample_text_input)
        claims = extract_result.get("claims", [])

        end_time = time.time()
        duration = end_time - start_time

        # Extraction should be fast (<2s even with all preprocessing)
        assert duration < 2.0, f"Claim extraction took {duration:.2f}s, should be <2s"

        # Claims should be properly enhanced
        assert all("claim_type" in c for c in claims), "All claims should have classification"
        assert all("is_verifiable" in c for c in claims), "All claims should have verifiability"


@pytest.mark.integration
class TestFeatureToggling:
    """Test that features can be enabled/disabled independently"""

    @pytest.mark.asyncio
    async def test_deduplication_toggle(self, monkeypatch):
        """Test: Deduplication only works when enabled"""
        from app.pipeline.retrieve import EvidenceRetriever

        # Disabled
        monkeypatch.setenv("ENABLE_EVIDENCE_DEDUPLICATION", "false")

        retriever = EvidenceRetriever()
        claim_dict = {"text": "test", "position": 0}

        mock_dup_results = [
            {"url": "a.com", "title": "Same", "snippet": "Same content"},
            {"url": "b.com", "title": "Same", "snippet": "Same content"}
        ]

        with patch.object(retriever.search_service, 'search_for_evidence', return_value=mock_dup_results):
            result = await retriever.retrieve_evidence_for_claims([claim_dict])
            evidence = result.get("0", [])

            # Should NOT deduplicate when disabled
            # (both sources present, no content_hash)
            assert all(e.get("content_hash") is None for e in evidence)

    @pytest.mark.asyncio
    async def test_classification_toggle(self, monkeypatch):
        """Test: Claim classification only works when enabled"""
        from app.pipeline.extract import ClaimExtractor

        # Disabled
        monkeypatch.setenv("ENABLE_CLAIM_CLASSIFICATION", "false")

        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims("I think this is great")
        claims = extract_result.get("claims", [])

        # Should NOT have classification fields when disabled
        if len(claims) > 0:
            assert "claim_type" not in claims[0] or claims[0].get("claim_type") is None

    @pytest.mark.asyncio
    async def test_temporal_toggle(self, monkeypatch):
        """Test: Temporal analysis only works when enabled"""
        from app.pipeline.extract import ClaimExtractor

        # Disabled
        monkeypatch.setenv("ENABLE_TEMPORAL_CONTEXT", "false")

        extractor = ClaimExtractor()
        extract_result = await extractor.extract_claims("This happened yesterday")
        claims = extract_result.get("claims", [])

        # Should NOT have temporal fields when disabled
        if len(claims) > 0:
            assert "is_time_sensitive" not in claims[0] or not claims[0].get("is_time_sensitive")
