"""M-02: Tests for landscape gap enrichment.

Covers:
- Tier gaps (no primary sources)
- Type gaps (no academic sources)
- Element-level gaps preserved
- No false positives on empty evidence
"""

import pytest


class TestLandscapeGapEnrichment:
    def _make_claims_with_evidence(self, tiers=None, types=None):
        """Build claims_data with specified tier/type coverage."""
        evidence = []
        for i, (tier, etype) in enumerate(
            zip(tiers or ["reporting"], types or ["news"])
        ):
            evidence.append(
                {
                    "evidenceId": f"ev-{i}",
                    "tier": tier,
                    "evidenceType": etype,
                    "url": f"https://example{i}.com/article",
                    "publishedDate": "2026-01-15T00:00:00Z",
                }
            )
        return [
            {
                "claimMap": {
                    "elements": [
                        {
                            "elementId": "e1",
                            "description": "Test element",
                            "state": "supported",
                            "evidenceRefs": [
                                {"evidenceId": f"ev-{i}"} for i in range(len(evidence))
                            ],
                        }
                    ]
                },
                "evidence": evidence,
            }
        ]

    def test_no_primary_gap(self):
        from app.api.v1.response_builder import _compute_landscape

        # Only reporting + commentary — no primary
        claims = self._make_claims_with_evidence(
            tiers=["reporting", "commentary"],
            types=["news", "opinion"],
        )
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        assert "no_primary_sources" in gap_reasons

    def test_no_academic_gap(self):
        from app.api.v1.response_builder import _compute_landscape

        # Only news + data — no academic
        claims = self._make_claims_with_evidence(
            tiers=["primary", "reporting"],
            types=["data", "news"],
        )
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        assert "no_academic_sources" in gap_reasons

    def test_no_gap_when_primary_present(self):
        from app.api.v1.response_builder import _compute_landscape

        claims = self._make_claims_with_evidence(
            tiers=["primary", "reporting"],
            types=["academic", "news"],
        )
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        assert "no_primary_sources" not in gap_reasons

    def test_no_gap_when_academic_present(self):
        from app.api.v1.response_builder import _compute_landscape

        claims = self._make_claims_with_evidence(
            tiers=["primary", "reporting"],
            types=["academic", "news"],
        )
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        assert "no_academic_sources" not in gap_reasons

    def test_no_false_positive_on_empty_evidence(self):
        from app.api.v1.response_builder import _compute_landscape

        # No evidence at all — should NOT add tier/type gaps (nothing to compare)
        claims = [
            {
                "claimMap": {
                    "elements": [
                        {
                            "elementId": "e1",
                            "description": "Test",
                            "state": "unresolved",
                            "evidenceRefs": [],
                        }
                    ]
                },
                "evidence": [],
            }
        ]
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        # Element-level gaps should be present
        assert any(r in ("no_evidence", "unresolved") for r in gap_reasons)
        # But NOT tier/type gaps (no evidence to check diversity against)
        assert "no_primary_sources" not in gap_reasons
        assert "no_academic_sources" not in gap_reasons

    def test_element_gaps_preserved(self):
        from app.api.v1.response_builder import _compute_landscape

        claims = [
            {
                "claimMap": {
                    "elements": [
                        {
                            "elementId": "e1",
                            "description": "Has evidence",
                            "state": "supported",
                            "evidenceRefs": [{"evidenceId": "ev-1"}],
                        },
                        {
                            "elementId": "e2",
                            "description": "No evidence",
                            "state": "unresolved",
                            "evidenceRefs": [],
                        },
                    ]
                },
                "evidence": [
                    {
                        "evidenceId": "ev-1",
                        "tier": "primary",
                        "evidenceType": "academic",
                        "url": "https://example.com",
                    }
                ],
            }
        ]
        landscape = _compute_landscape(claims)
        gap_reasons = [g.get("reason") for g in landscape["gaps"]]
        assert "no_evidence" in gap_reasons
