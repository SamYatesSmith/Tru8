import pytest
from datetime import datetime, timedelta
from app.utils.temporal import TemporalAnalyzer


class TestTemporalAnalyzer:
    """Test temporal context analysis for claims"""

    @pytest.fixture
    def analyzer(self):
        return TemporalAnalyzer()

    def test_present_tense_detection(self, analyzer):
        """Test: Detects present tense temporal markers"""
        test_cases = [
            "The president is currently in office",
            "The iPhone costs $999 today",
            "Water is now safe to drink in 2025",
            "This year's election results are in"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == True, f"Failed for: {claim}"
            assert "present" in result["temporal_markers"]
            assert result["temporal_window"] == "last_30_days"
            assert result["max_evidence_age_days"] == 30

    def test_recent_past_detection(self, analyzer):
        """Test: Detects recent past temporal markers"""
        test_cases = [
            "The company announced layoffs yesterday",
            "Last week the policy changed",
            "Recently, scientists discovered",
            "Last month the data showed"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == True
            assert "recent_past" in result["temporal_markers"]
            assert result["temporal_window"] == "last_90_days"
            assert result["max_evidence_age_days"] == 90

    def test_specific_year_detection(self, analyzer):
        """Test: Detects specific year mentions"""
        test_cases = [
            "In 2020, the pandemic started",
            "During 2018, unemployment was low",
            "The law passed in 2022"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == True
            assert "specific_year" in result["temporal_markers"]
            assert "year_" in result["temporal_window"]
            assert result["max_evidence_age_days"] == 365

    def test_future_tense_detection(self, analyzer):
        """Test: Detects future tense predictions"""
        test_cases = [
            "AI will replace most jobs",
            "The company is going to expand next year",
            "In 2026, the treaty expires",
            "Scientists predict this in the future"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == True
            assert "future" in result["temporal_markers"]
            assert result["claim_type"] == "prediction"

    def test_timeless_claims(self, analyzer):
        """Test: Timeless claims are not marked as time-sensitive"""
        test_cases = [
            "The Earth orbits the Sun",
            "Water boils at 100 degrees Celsius",
            "Shakespeare wrote Hamlet",
            "Paris is the capital of France"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == False
            assert result["temporal_window"] == "timeless"
            assert result["max_evidence_age_days"] is None
            assert result["claim_type"] == "timeless_fact"

    def test_temporal_type_classification(self, analyzer):
        """Test: Correctly classifies temporal claim types"""
        test_data = [
            ("The stock market is rising now", "current_state"),
            ("In 2019, GDP grew 3%", "historical_fact"),
            ("Inflation will increase next year", "prediction"),
            ("Water freezes at 0 degrees", "timeless_fact")
        ]

        for claim, expected_type in test_data:
            result = analyzer.analyze_claim(claim)
            assert result["claim_type"] == expected_type, f"Failed for: {claim}"

    def test_year_extraction(self, analyzer):
        """Test: Extracts year from claim text"""
        assert analyzer._extract_year("In 2020, the event occurred") == "2020"
        assert analyzer._extract_year("During 2018") == "2018"
        assert analyzer._extract_year("No year here") is None

    def test_evidence_filtering_recent(self, analyzer):
        """Test: Filters evidence based on temporal requirements"""
        # Create temporal analysis for present tense claim
        temporal_analysis = {
            "is_time_sensitive": True,
            "max_evidence_age_days": 30
        }

        # Create evidence with various dates
        now = datetime.now()
        evidence = [
            {"url": "a.com", "published_date": (now - timedelta(days=10)).isoformat()},  # Recent
            {"url": "b.com", "published_date": (now - timedelta(days=60)).isoformat()},  # Old
            {"url": "c.com", "published_date": (now - timedelta(days=5)).isoformat()},   # Recent
            {"url": "d.com", "published_date": None},  # No date
        ]

        filtered = analyzer.filter_evidence_by_time(evidence, temporal_analysis)

        # Should keep: a.com (10 days), c.com (5 days), d.com (no date)
        # Should filter: b.com (60 days)
        assert len(filtered) == 3
        urls = [e["url"] for e in filtered]
        assert "a.com" in urls
        assert "c.com" in urls
        assert "d.com" in urls
        assert "b.com" not in urls

    def test_evidence_filtering_no_filtering_for_timeless(self, analyzer):
        """Test: No filtering applied for timeless claims"""
        temporal_analysis = {
            "is_time_sensitive": False,
            "max_evidence_age_days": None
        }

        now = datetime.now()
        evidence = [
            {"url": "a.com", "published_date": (now - timedelta(days=10)).isoformat()},
            {"url": "b.com", "published_date": (now - timedelta(days=365)).isoformat()},
            {"url": "c.com", "published_date": (now - timedelta(days=1000)).isoformat()},
        ]

        filtered = analyzer.filter_evidence_by_time(evidence, temporal_analysis)

        # All evidence should remain
        assert len(filtered) == 3

    def test_date_parsing_formats(self, analyzer):
        """Test: Parses various date formats"""
        # ISO format
        assert analyzer._parse_date("2024-01-15") is not None
        assert analyzer._parse_date("2024/01/15") is not None

        # Date object
        date_obj = datetime(2024, 1, 15)
        assert analyzer._parse_date(date_obj) == date_obj

        # Year extraction fallback
        result = analyzer._parse_date("Published in 2023")
        assert result is not None
        assert result.year == 2023

    def test_date_parsing_invalid(self, analyzer):
        """Test: Returns None for unparseable dates"""
        assert analyzer._parse_date("invalid date string") is None
        assert analyzer._parse_date("") is None

    def test_multiple_temporal_markers(self, analyzer):
        """Test: Detects multiple temporal markers in same claim"""
        claim = "In 2020, the virus spread, and today we have vaccines"
        result = analyzer.analyze_claim(claim)

        assert result["is_time_sensitive"] == True
        assert "specific_year" in result["temporal_markers"]
        assert "present" in result["temporal_markers"]
        # Present should take priority for temporal window
        assert result["temporal_window"] == "last_30_days"

    def test_case_insensitivity(self, analyzer):
        """Test: Temporal detection is case-insensitive"""
        test_cases = [
            "The President is CURRENTLY in office",
            "YESTERDAY the news broke",
            "In 2020, THE EVENT occurred"
        ]

        for claim in test_cases:
            result = analyzer.analyze_claim(claim)
            assert result["is_time_sensitive"] == True

    def test_evidence_datetime_object_handling(self, analyzer):
        """Test: Handles datetime objects in evidence published_date"""
        temporal_analysis = {
            "is_time_sensitive": True,
            "max_evidence_age_days": 30
        }

        now = datetime.now()
        evidence = [
            {"url": "a.com", "published_date": now - timedelta(days=10)},  # datetime object
            {"url": "b.com", "published_date": (now - timedelta(days=60)).isoformat()},  # ISO string
        ]

        filtered = analyzer.filter_evidence_by_time(evidence, temporal_analysis)

        assert len(filtered) == 1
        assert filtered[0]["url"] == "a.com"
