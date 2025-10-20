import pytest
from app.utils.explainability import ExplainabilityEnhancer


class TestExplainabilityEnhancer:
    """Test explainability and transparency features"""

    @pytest.fixture
    def explainer(self):
        return ExplainabilityEnhancer()

    @pytest.fixture
    def sample_evidence(self):
        return [
            {"source": "BBC", "url": "bbc.com/1", "credibility_score": 0.9, "is_factcheck": False},
            {"source": "Reuters", "url": "reuters.com/1", "credibility_score": 0.9, "is_factcheck": False},
            {"source": "Snopes", "url": "snopes.com/1", "credibility_score": 0.95, "is_factcheck": True},
            {"source": "AP News", "url": "apnews.com/1", "credibility_score": 0.85, "is_factcheck": False}
        ]

    @pytest.fixture
    def sample_judgment(self):
        return {
            "verdict": "supported",
            "confidence": 85,
            "rationale": "Multiple reliable sources confirm the claim"
        }

    @pytest.fixture
    def sample_signals(self):
        return {
            "supporting_count": 3,
            "contradicting_count": 1,
            "neutral_count": 0
        }

    def test_create_decision_trail(self, explainer, sample_evidence, sample_judgment, sample_signals):
        """Test: Creates complete decision trail"""
        claim = {"text": "Test claim", "position": 0}

        trail = explainer.create_decision_trail(
            claim, sample_evidence, sample_signals, sample_judgment
        )

        assert "stages" in trail
        assert len(trail["stages"]) == 3  # Retrieval, verification, judgment
        assert trail["stages"][0]["stage"] == "evidence_retrieval"
        assert trail["stages"][1]["stage"] == "verification"
        assert trail["stages"][2]["stage"] == "judgment"
        assert "transparency_score" in trail
        assert 0 <= trail["transparency_score"] <= 1

    def test_decision_trail_evidence_details(self, explainer, sample_evidence, sample_judgment, sample_signals):
        """Test: Decision trail includes evidence details"""
        claim = {"text": "Test claim"}
        trail = explainer.create_decision_trail(claim, sample_evidence, sample_signals, sample_judgment)

        evidence_stage = trail["stages"][0]
        assert "Found 4 sources" in evidence_stage["result"]
        assert evidence_stage["details"]["unique_domains"] == 4
        assert evidence_stage["details"]["avg_credibility"] > 0.8
        assert evidence_stage["details"]["factcheck_sources"] == 1

    def test_transparency_score_sufficient_evidence(self, explainer):
        """Test: High transparency score with sufficient quality evidence"""
        evidence = [
            {"credibility_score": 0.9} for _ in range(5)
        ]
        signals = {"supporting_count": 4, "contradicting_count": 0}

        score = explainer._calculate_transparency_score(evidence, signals)
        assert score >= 0.8  # High score for clear evidence

    def test_transparency_score_insufficient_evidence(self, explainer):
        """Test: Lower transparency score with insufficient evidence"""
        evidence = [{"credibility_score": 0.6}]
        signals = {"supporting_count": 1, "contradicting_count": 0}

        score = explainer._calculate_transparency_score(evidence, signals)
        assert score < 0.7  # Lower score for insufficient evidence

    def test_transparency_score_conflicting_evidence(self, explainer):
        """Test: Transparency score accounts for conflicting signals"""
        evidence = [{"credibility_score": 0.8} for _ in range(4)]
        signals = {"supporting_count": 2, "contradicting_count": 2}

        score = explainer._calculate_transparency_score(evidence, signals)
        # No bonus for clear consensus
        assert score <= 0.8

    def test_uncertainty_explanation_insufficient_evidence(self, explainer):
        """Test: Explains uncertainty due to insufficient evidence"""
        evidence = [{"url": "a.com"}]
        signals = {"supporting_count": 1, "contradicting_count": 0}

        explanation = explainer.create_uncertainty_explanation("uncertain", signals, evidence)
        assert "Insufficient evidence" in explanation
        assert "1 source" in explanation

    def test_uncertainty_explanation_conflicting(self, explainer):
        """Test: Explains uncertainty due to conflicting evidence"""
        evidence = [{"url": f"{i}.com"} for i in range(4)]
        signals = {"supporting_count": 2, "contradicting_count": 2}

        explanation = explainer.create_uncertainty_explanation("uncertain", signals, evidence)
        assert "Conflicting evidence" in explanation
        assert "2 supporting vs 2 contradicting" in explanation

    def test_uncertainty_explanation_low_quality(self, explainer):
        """Test: Explains uncertainty due to low quality sources"""
        evidence = [{"credibility_score": 0.3} for _ in range(4)]
        signals = {"supporting_count": 3, "contradicting_count": 1}

        explanation = explainer.create_uncertainty_explanation("uncertain", signals, evidence)
        assert "low quality" in explanation.lower()

    def test_uncertainty_explanation_time_sensitive(self, explainer):
        """Test: Explains uncertainty for time-sensitive claims"""
        evidence = [{"is_time_sensitive": True, "credibility_score": 0.7} for _ in range(3)]
        signals = {"supporting_count": 2, "contradicting_count": 1}

        explanation = explainer.create_uncertainty_explanation("uncertain", signals, evidence)
        assert "time-sensitive" in explanation.lower()

    def test_uncertainty_explanation_no_explanation_for_supported(self, explainer):
        """Test: No explanation for non-uncertain verdicts"""
        evidence = [{"url": "a.com"}]
        signals = {"supporting_count": 1, "contradicting_count": 0}

        explanation = explainer.create_uncertainty_explanation("supported", signals, evidence)
        assert explanation == ""

    def test_confidence_breakdown_structure(self, explainer, sample_evidence, sample_judgment, sample_signals):
        """Test: Confidence breakdown has correct structure"""
        breakdown = explainer.create_confidence_breakdown(
            sample_judgment, sample_evidence, sample_signals
        )

        assert "overall_confidence" in breakdown
        assert "factors" in breakdown
        assert isinstance(breakdown["factors"], list)

    def test_confidence_breakdown_evidence_quantity_positive(self, explainer):
        """Test: Positive factor for sufficient evidence"""
        judgment = {"confidence": 80}
        evidence = [{"url": f"{i}.com"} for i in range(5)]
        signals = {"supporting_count": 4, "contradicting_count": 1}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        quantity_factors = [f for f in breakdown["factors"] if f["factor"] == "evidence_quantity"]
        assert len(quantity_factors) > 0
        assert quantity_factors[0]["impact"] == "positive"

    def test_confidence_breakdown_evidence_quantity_negative(self, explainer):
        """Test: Negative factor for insufficient evidence"""
        judgment = {"confidence": 50}
        evidence = [{"url": "a.com"}]
        signals = {"supporting_count": 1, "contradicting_count": 0}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        quantity_factors = [f for f in breakdown["factors"] if f["factor"] == "evidence_quantity"]
        assert len(quantity_factors) > 0
        assert quantity_factors[0]["impact"] == "negative"

    def test_confidence_breakdown_quality_factor(self, explainer):
        """Test: Quality factor included for high-credibility sources"""
        judgment = {"confidence": 85}
        evidence = [{"credibility_score": 0.9} for _ in range(4)]
        signals = {"supporting_count": 3, "contradicting_count": 1}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        quality_factors = [f for f in breakdown["factors"] if f["factor"] == "evidence_quality"]
        assert len(quality_factors) > 0
        assert quality_factors[0]["impact"] == "positive"

    def test_confidence_breakdown_consensus_factor(self, explainer):
        """Test: Consensus factor for strong agreement"""
        judgment = {"confidence": 85}
        evidence = [{"url": f"{i}.com"} for i in range(4)]
        signals = {"supporting_count": 4, "contradicting_count": 0}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        consensus_factors = [f for f in breakdown["factors"] if f["factor"] == "evidence_consensus"]
        assert len(consensus_factors) > 0
        assert consensus_factors[0]["impact"] == "positive"

    def test_confidence_breakdown_factcheck_factor(self, explainer):
        """Test: Bonus factor for fact-check presence"""
        judgment = {"confidence": 85}
        evidence = [
            {"is_factcheck": True},
            {"is_factcheck": False}
        ]
        signals = {"supporting_count": 2, "contradicting_count": 0}

        breakdown = explainer.create_confidence_breakdown(judgment, evidence, signals)

        factcheck_factors = [f for f in breakdown["factors"] if f["factor"] == "fact_check_presence"]
        assert len(factcheck_factors) > 0
        assert "1 professional fact-check" in factcheck_factors[0]["description"]

    def test_explainability_summary_empty(self, explainer):
        """Test: Handles empty checks list"""
        summary = explainer.get_explainability_summary([])

        assert summary["total_checks"] == 0
        assert summary["avg_transparency_score"] == 0

    def test_explainability_summary_stats(self, explainer):
        """Test: Calculates summary statistics correctly"""
        checks = [
            {"transparency_score": 0.9, "verdict": "supported"},
            {"transparency_score": 0.7, "verdict": "uncertain", "uncertainty_explanation": "Low quality"},
            {"transparency_score": 0.85, "verdict": "contradicted"}
        ]

        summary = explainer.get_explainability_summary(checks)

        assert summary["total_checks"] == 3
        assert summary["avg_transparency_score"] == 0.82
        assert summary["uncertain_with_explanation"] == 1
        assert summary["high_transparency_count"] == 2  # 0.9 and 0.85

    def test_decision_trail_handles_missing_data(self, explainer):
        """Test: Handles missing or incomplete data gracefully"""
        claim = {}
        evidence = []
        signals = {}
        judgment = {}

        trail = explainer.create_decision_trail(claim, evidence, signals, judgment)

        assert "stages" in trail
        assert len(trail["stages"]) == 3
        assert trail["transparency_score"] >= 0

    def test_uncertainty_explanation_generic_fallback(self, explainer):
        """Test: Provides generic explanation when no specific reason found"""
        evidence = [{"url": f"{i}.com", "credibility_score": 0.7} for i in range(4)]
        signals = {"supporting_count": 2, "contradicting_count": 1}

        explanation = explainer.create_uncertainty_explanation("uncertain", signals, evidence)

        # Should provide some explanation
        assert len(explanation) > 0
        assert "mixed" in explanation.lower() or "insufficient" in explanation.lower()
