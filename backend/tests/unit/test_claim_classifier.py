import pytest
from app.utils.claim_classifier import ClaimClassifier


class TestClaimClassifier:
    """Test claim type classification and verifiability assessment"""

    @pytest.fixture
    def classifier(self):
        return ClaimClassifier()

    def test_opinion_detection_subjective(self, classifier):
        """Test: Detects subjective opinions"""
        test_cases = [
            "I think climate change is important",
            "In my opinion, the policy is wrong",
            "I believe this is the best approach",
            "I feel that the decision was unfair"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "opinion", f"Failed for: {claim}"
            assert result["is_verifiable"] == False
            assert "subjective" in result["reason"].lower() or "opinion" in result["reason"].lower()

    def test_opinion_detection_value_judgment(self, classifier):
        """Test: Detects value judgments as opinions"""
        test_cases = [
            "The movie was beautiful",
            "That's the worst decision ever",
            "It's an amazing product",
            "This is a terrible policy"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "opinion", f"Failed for: {claim}"
            assert result["is_verifiable"] == False

    def test_opinion_detection_normative(self, classifier):
        """Test: Detects normative statements as opinions"""
        test_cases = [
            "The government should increase spending",
            "Companies must reduce emissions",
            "We need to change the law",
            "People ought to vote more"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "opinion", f"Failed for: {claim}"
            assert result["is_verifiable"] == False

    def test_prediction_detection_future(self, classifier):
        """Test: Detects predictions about future events"""
        test_cases = [
            "AI will replace human jobs by 2030",
            "The company is going to expand next year",
            "Experts predict rising temperatures",
            "The economy will improve in the future"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "prediction", f"Failed for: {claim}"
            assert result["is_verifiable"] == False
            assert "future" in result["reason"].lower() or "prediction" in result["reason"].lower()

    def test_personal_experience_detection(self, classifier):
        """Test: Detects personal experiences"""
        test_cases = [
            "I saw the incident happen",
            "I heard them discussing the plan",
            "This happened to me last year",
            "I experienced severe side effects"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "personal_experience", f"Failed for: {claim}"
            assert result["is_verifiable"] == False
            assert "personal" in result["reason"].lower()

    def test_factual_claim_detection(self, classifier):
        """Test: Identifies verifiable factual claims"""
        test_cases = [
            "Biden is the president of the United States",
            "Water boils at 100 degrees Celsius",
            "The population of Tokyo is 14 million",
            "Shakespeare wrote Hamlet in 1600"
        ]

        for claim in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == "factual", f"Failed for: {claim}"
            assert result["is_verifiable"] == True
            assert "factual" in result["reason"].lower() or "verified" in result["reason"].lower()

    def test_confidence_scores(self, classifier):
        """Test: Returns appropriate confidence scores"""
        test_cases = [
            ("I think this is good", "opinion", 0.8),
            ("AI will dominate by 2030", "prediction", 0.7),
            ("I saw it happen", "personal_experience", 0.7),
            ("The Earth orbits the Sun", "factual", 0.6)
        ]

        for claim, expected_type, min_confidence in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == expected_type, f"Failed for: {claim}"
            assert result["confidence"] >= min_confidence, f"Low confidence for: {claim}"

    def test_case_insensitivity(self, classifier):
        """Test: Classification is case-insensitive"""
        test_cases = [
            ("I THINK this is important", "opinion"),
            ("AI WILL replace jobs", "prediction"),
            ("I SAW the event", "personal_experience")
        ]

        for claim, expected_type in test_cases:
            result = classifier.classify(claim)
            assert result["claim_type"] == expected_type

    def test_mixed_indicators_precedence(self, classifier):
        """Test: Opinion indicators take precedence over factual content"""
        claim = "I think the population of Tokyo is 14 million"
        result = classifier.classify(claim)
        # Opinion indicator "I think" should dominate
        assert result["claim_type"] == "opinion"
        assert result["is_verifiable"] == False

    def test_classification_summary_empty(self, classifier):
        """Test: Handles empty claim list"""
        summary = classifier.get_classification_summary([])
        assert summary["total_claims"] == 0
        assert summary["verifiable"] == 0
        assert summary["non_verifiable"] == 0

    def test_classification_summary_stats(self, classifier):
        """Test: Calculates summary statistics correctly"""
        claims = [
            {"is_verifiable": True, "classification": {"claim_type": "factual"}},
            {"is_verifiable": True, "classification": {"claim_type": "factual"}},
            {"is_verifiable": False, "classification": {"claim_type": "opinion"}},
            {"is_verifiable": False, "classification": {"claim_type": "prediction"}}
        ]

        summary = classifier.get_classification_summary(claims)
        assert summary["total_claims"] == 4
        assert summary["verifiable"] == 2
        assert summary["non_verifiable"] == 2
        assert summary["verifiable_percentage"] == 50.0
        assert summary["types"]["factual"] == 2
        assert summary["types"]["opinion"] == 1
        assert summary["types"]["prediction"] == 1

    def test_reason_field_present(self, classifier):
        """Test: All classifications include reason field"""
        test_claims = [
            "I think this is good",
            "AI will replace jobs",
            "I saw the event",
            "Water boils at 100 degrees"
        ]

        for claim in test_claims:
            result = classifier.classify(claim)
            assert "reason" in result
            assert isinstance(result["reason"], str)
            assert len(result["reason"]) > 0

    def test_prediction_with_year(self, classifier):
        """Test: Detects predictions with specific future years"""
        claims = [
            "By 2030, renewable energy will dominate",
            "The market will crash by 2025"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "prediction"
            assert result["is_verifiable"] == False

    def test_factual_with_numbers(self, classifier):
        """Test: Numeric facts are classified as verifiable"""
        claims = [
            "The temperature was 25 degrees",
            "The company has 10000 employees",
            "GDP grew by 3 percent"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "factual"
            assert result["is_verifiable"] == True

    def test_complex_sentences(self, classifier):
        """Test: Handles complex multi-clause sentences"""
        claim = "Although some people think it's good, the data shows unemployment is rising"
        result = classifier.classify(claim)
        # "think" appears but in context of "some people", should still detect opinion
        assert result["claim_type"] == "opinion"

    def test_no_false_positives_factual(self, classifier):
        """Test: Doesn't misclassify clear factual claims"""
        claims = [
            "The president signed the bill yesterday",
            "Temperatures reached record highs",
            "The study found a 20% increase"
        ]

        for claim in claims:
            result = classifier.classify(claim)
            assert result["claim_type"] == "factual", f"False positive for: {claim}"
            assert result["is_verifiable"] == True
