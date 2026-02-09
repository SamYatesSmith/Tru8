"""Tests for PR 2-B: Unknown-domain probation keep.

Verifies:
1. Mixed known+unknown → unknowns survive up to MAX_UNKNOWN_SOURCES_PER_CLAIM
2. 5 unknowns with max=2 → only top 2 by final_score kept
3. Best-scoring unknowns are selected
4. Satire/social (auto_exclude) never kept via probation
5. All-unknown scenario still triggers existing adaptive fallback (top 3)
6. MAX_UNKNOWN_SOURCES_PER_CLAIM=0 → all unknowns hard-dropped
7. Probation sources correctly un-marked in raw evidence tracking
"""
import pytest
import copy
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.pipeline.retrieve import EvidenceRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def retriever():
    """Minimal EvidenceRetriever for testing _apply_credibility_weighting."""
    with patch("app.pipeline.retrieve.SearchService"), \
         patch("app.pipeline.retrieve.EvidenceExtractor"), \
         patch("app.pipeline.retrieve.get_api_registry") as mock_registry:
        mock_registry.return_value = MagicMock()
        ret = EvidenceRetriever()
        yield ret


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_evidence(source, url, credibility, tier, combined_score=0.70,
                  auto_exclude=False, published_date="2026-01-15"):
    return {
        "source": source,
        "url": url,
        "title": f"Article from {source}",
        "text": f"Content from {source}",
        "snippet": f"Snippet from {source}",
        "published_date": published_date,
        "combined_score": combined_score,
        "tier": tier,
        "auto_exclude": auto_exclude,
    }


# Known high-cred sources (above 0.55 threshold)
KNOWN_REUTERS = make_evidence("reuters.com", "https://reuters.com/a1", 0.90, "tier1")
KNOWN_BBC = make_evidence("bbc.com", "https://bbc.com/a1", 0.85, "tier1", combined_score=0.65)
KNOWN_AP = make_evidence("apnews.com", "https://apnews.com/a1", 0.88, "tier1", combined_score=0.60)

# Unknown sources (tier="general", cred=0.40 → below 0.55 threshold)
UNKNOWN_A = make_evidence("localnews.example.com", "https://localnews.example.com/a1", 0.40, "general", combined_score=0.80)
UNKNOWN_B = make_evidence("regionaltimes.example.com", "https://regionaltimes.example.com/a1", 0.40, "general", combined_score=0.75)
UNKNOWN_C = make_evidence("smallblog.example.com", "https://smallblog.example.com/a1", 0.40, "general", combined_score=0.60)
UNKNOWN_D = make_evidence("nichesite.example.com", "https://nichesite.example.com/a1", 0.40, "general", combined_score=0.55)
UNKNOWN_E = make_evidence("tinyoutlet.example.com", "https://tinyoutlet.example.com/a1", 0.40, "general", combined_score=0.50)

# Auto-excluded source (satire) — should NEVER survive probation
SATIRE = make_evidence("theonion.com", "https://theonion.com/a1", 0.30, "satire", auto_exclude=True)

CRED_MAP = {
    "reuters.com": 0.90,
    "bbc.com": 0.85,
    "apnews.com": 0.88,
    "localnews.example.com": 0.40,
    "regionaltimes.example.com": 0.40,
    "smallblog.example.com": 0.40,
    "nichesite.example.com": 0.40,
    "tinyoutlet.example.com": 0.40,
    "theonion.com": 0.30,
}

FIXED_RECENCY = 0.95


def _patch_settings(**overrides):
    """Create a settings-like object with defaults + overrides.

    Uses SimpleNamespace instead of MagicMock to ensure falsy values (0, False)
    are returned exactly as set, without MagicMock auto-attribute behavior.
    Includes all settings attributes accessed by _apply_credibility_weighting.
    """
    defaults = {
        "SOURCE_CREDIBILITY_THRESHOLD": 0.55,
        "MAX_UNKNOWN_SOURCES_PER_CLAIM": 2,
        "ENABLE_CORROBORATION_BOOST": False,
        "ENABLE_TEMPORAL_CONTEXT": False,
        "ENABLE_DEDUPLICATION": False,
        "ENABLE_SOURCE_DIVERSITY": False,
        "ENABLE_DOMAIN_CAPPING": False,
        "ENABLE_SOURCE_VALIDATION": False,
        # Additional settings accessed by the function
        "MAX_EVIDENCE_PER_DOMAIN": 3,
        "DOMAIN_DIVERSITY_THRESHOLD": 0.6,
        "ENABLE_DOMAIN_CREDIBILITY_FRAMEWORK": False,
        "ENABLE_PRIMARY_SOURCE_DETECTION": False,
        "ENABLE_CROSS_ENCODER_RERANK": False,
        "UNKNOWN_SOURCE_CREDIBILITY": 0.40,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUnknownProbation:
    """Verify unknown-domain probation keep behavior (PR 2-B)."""

    def test_probation_keeps_unknowns_with_known_sources(self, retriever):
        """Mixed known+unknown → unknowns survive up to max."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(KNOWN_BBC),
            copy.deepcopy(UNKNOWN_A),
            copy.deepcopy(UNKNOWN_B),
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]
        sources = {e["source"] for e in weighted}

        # Known sources pass normally
        assert "reuters.com" in sources
        assert "bbc.com" in sources
        # Unknown sources kept via probation (max=2, we have 2)
        assert "localnews.example.com" in sources
        assert "regionaltimes.example.com" in sources
        assert len(weighted) == 4

    def test_probation_caps_at_max(self, retriever):
        """5 unknowns, max=2 → only top 2 by final_score kept."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(UNKNOWN_A),  # combined=0.80
            copy.deepcopy(UNKNOWN_B),  # combined=0.75
            copy.deepcopy(UNKNOWN_C),  # combined=0.60
            copy.deepcopy(UNKNOWN_D),  # combined=0.55
            copy.deepcopy(UNKNOWN_E),  # combined=0.50
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]
        sources = {e["source"] for e in weighted}

        # 1 known + 2 probation = 3 total
        assert len(weighted) == 3
        assert "reuters.com" in sources
        # Top 2 unknowns by final_score (combined * 0.40 * 0.95)
        assert "localnews.example.com" in sources   # 0.80 * 0.40 * 0.95 = 0.304
        assert "regionaltimes.example.com" in sources  # 0.75 * 0.40 * 0.95 = 0.285

    def test_probation_sorts_by_final_score(self, retriever):
        """Best-scoring unknowns are selected when more than max available."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(UNKNOWN_C),  # combined=0.60 → final=0.228
            copy.deepcopy(UNKNOWN_A),  # combined=0.80 → final=0.304
            copy.deepcopy(UNKNOWN_D),  # combined=0.55 → final=0.209
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]
        unknown_kept = [e for e in weighted if e.get("tier") == "general"]

        assert len(unknown_kept) == 2
        # Best unknown (localnews, combined=0.80) should be kept
        kept_sources = {e["source"] for e in unknown_kept}
        assert "localnews.example.com" in kept_sources
        # Second best (smallblog, combined=0.60) over nichesite (combined=0.55)
        assert "smallblog.example.com" in kept_sources
        assert "nichesite.example.com" not in kept_sources

    def test_no_probation_for_auto_excluded(self, retriever):
        """Satire/social (auto_exclude=True) never kept via probation."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(SATIRE),
            copy.deepcopy(UNKNOWN_A),
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]
        sources = {e["source"] for e in weighted}

        # Satire is auto-excluded BEFORE credibility filtering, never reaches probation
        assert "theonion.com" not in sources
        # Unknown kept via probation
        assert "localnews.example.com" in sources
        assert "reuters.com" in sources

    def test_adaptive_fallback_unchanged(self, retriever):
        """All-unknown scenario still triggers existing top-3 fallback, not probation."""
        evidence = [
            copy.deepcopy(UNKNOWN_A),  # combined=0.80
            copy.deepcopy(UNKNOWN_B),  # combined=0.75
            copy.deepcopy(UNKNOWN_C),  # combined=0.60
            copy.deepcopy(UNKNOWN_D),  # combined=0.55
            copy.deepcopy(UNKNOWN_E),  # combined=0.50
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]

        # Adaptive fallback keeps top 3 by credibility (all same cred=0.40, so by order)
        assert len(weighted) == 3

    def test_probation_disabled_when_zero(self, retriever):
        """MAX_UNKNOWN_SOURCES_PER_CLAIM=0 → all unknowns hard-dropped."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(UNKNOWN_A),
            copy.deepcopy(UNKNOWN_B),
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings",
                   _patch_settings(MAX_UNKNOWN_SOURCES_PER_CLAIM=0)):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=False)

        weighted = result if isinstance(result, list) else result[0]
        sources = {e["source"] for e in weighted}

        # Only known source survives
        assert sources == {"reuters.com"}
        assert len(weighted) == 1

    def test_raw_evidence_tracking_updated(self, retriever):
        """Probation sources correctly un-marked in raw evidence tracking."""
        evidence = [
            copy.deepcopy(KNOWN_REUTERS),
            copy.deepcopy(UNKNOWN_A),
            copy.deepcopy(UNKNOWN_B),
        ]

        with patch.object(retriever, '_get_credibility_score',
                          side_effect=lambda s, u, e, j: CRED_MAP.get(s, 0.4)), \
             patch.object(retriever, '_get_recency_score', return_value=FIXED_RECENCY), \
             patch("app.core.config.settings", _patch_settings()):

            result = retriever._apply_credibility_weighting(evidence, track_raw_evidence=True)

        # When track_raw_evidence=True, returns (evidence_list, raw_tracking)
        weighted, raw_tracking = result

        # Build lookup
        raw_by_url = {item["url"]: item for item in raw_tracking}

        # Known source: included, no filter
        reuters_raw = raw_by_url.get("https://reuters.com/a1")
        assert reuters_raw is not None
        assert reuters_raw["is_included"] is True

        # Unknown sources kept via probation: should be un-marked (is_included=True)
        for url in ["https://localnews.example.com/a1", "https://regionaltimes.example.com/a1"]:
            raw_item = raw_by_url.get(url)
            assert raw_item is not None, f"Missing raw tracking for {url}"
            assert raw_item["is_included"] is True, f"{url} should be marked included via probation"
            assert raw_item["filter_stage"] is None, f"{url} filter_stage should be None after probation"
            assert raw_item["filter_reason"] is None, f"{url} filter_reason should be None after probation"
