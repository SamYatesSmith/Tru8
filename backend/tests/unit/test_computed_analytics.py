"""Tests for computed analytics — all pure functions, no mocking needed."""

from app.services.computed_analytics import (
    _collect_deduplicated_evidence,
    _collect_all_elements,
    _build_summary,
    _count_by_field,
    _build_heatmap,
    _build_corroboration,
    _compute_diagnostic_values,
    _build_timeline,
    _build_per_claim,
)


# ---------------------------------------------------------------------------
# Helpers — reusable claim/evidence builders
# ---------------------------------------------------------------------------


def _make_evidence(
    eid, tier="reporting", etype="news_reporting", date=None, group=None
):
    ev = {
        "evidenceId": eid,
        "source": "example.com",
        "url": f"https://example.com/{eid}",
        "title": f"Evidence {eid}",
        "snippet": "...",
        "tier": tier,
        "evidenceType": etype,
    }
    if date:
        ev["publishedDate"] = date
    if group is not None:
        ev["corroborationGroupId"] = group
    return ev


def _make_element(eid, state="supported", refs=None):
    return {
        "elementId": eid,
        "text": f"Element {eid}",
        "evidenceRefs": refs or [],
        "state": state,
        "uncertainty": None,
    }


def _make_claim(position, elements=None, evidence=None):
    return {
        "position": position,
        "claimMap": {"elements": elements or []},
        "evidence": evidence or [],
    }


# ---------------------------------------------------------------------------
# _collect_deduplicated_evidence
# ---------------------------------------------------------------------------


class TestCollectDeduplicatedEvidence:
    def test_deduplicates_across_claims(self):
        ev = _make_evidence("ev-1")
        claims = [_make_claim(0, evidence=[ev]), _make_claim(1, evidence=[ev])]
        result = _collect_deduplicated_evidence(claims)
        assert len(result) == 1
        assert result[0]["evidenceId"] == "ev-1"

    def test_empty_input(self):
        assert _collect_deduplicated_evidence([]) == []

    def test_missing_evidence_key(self):
        claims = [{"position": 0, "claimMap": {"elements": []}}]
        assert _collect_deduplicated_evidence(claims) == []


# ---------------------------------------------------------------------------
# _collect_all_elements
# ---------------------------------------------------------------------------


class TestCollectAllElements:
    def test_multiple_claims(self):
        e1 = _make_element("e1")
        e2 = _make_element("e2")
        claims = [_make_claim(0, elements=[e1]), _make_claim(1, elements=[e2])]
        result = _collect_all_elements(claims)
        assert len(result) == 2

    def test_no_claim_map(self):
        claims = [{"position": 0}]
        assert _collect_all_elements(claims) == []

    def test_empty_elements(self):
        claims = [_make_claim(0, elements=[])]
        assert _collect_all_elements(claims) == []


# ---------------------------------------------------------------------------
# _build_summary
# ---------------------------------------------------------------------------


class TestBuildSummary:
    def test_counts(self):
        refs = [{"evidenceId": "ev-1", "relationship": "supports"}]
        el = _make_element("e1", state="supported", refs=refs)
        ev = _make_evidence("ev-1")
        claims = [_make_claim(0, elements=[el], evidence=[ev])]
        result = _build_summary(claims, [ev], [el])
        assert result["totalClaims"] == 1
        assert result["totalEvidence"] == 1
        assert result["totalElements"] == 1

    def test_element_states(self):
        e1 = _make_element(
            "e1",
            state="supported",
            refs=[{"evidenceId": "x", "relationship": "supports"}],
        )
        e2 = _make_element(
            "e2",
            state="disputed",
            refs=[{"evidenceId": "y", "relationship": "challenges"}],
        )
        e3 = _make_element("e3", state="unresolved")
        claims = [_make_claim(0, elements=[e1, e2, e3])]
        result = _build_summary(claims, [], [e1, e2, e3])
        assert result["elementStates"] == {
            "supported": 1,
            "disputed": 1,
            "unresolved": 1,
        }

    def test_coverage_percent(self):
        refs = [{"evidenceId": "ev-1", "relationship": "supports"}]
        e1 = _make_element("e1", refs=refs)
        e2 = _make_element("e2")  # no evidence
        claims = [_make_claim(0, elements=[e1, e2])]
        result = _build_summary(claims, [], [e1, e2])
        assert result["coveragePercent"] == 50.0

    def test_gap_elements(self):
        e1 = _make_element("e1")  # no evidence → gap
        claims = [_make_claim(0, elements=[e1])]
        result = _build_summary(claims, [], [e1])
        assert len(result["gapElements"]) == 1
        assert result["gapElements"][0]["elementId"] == "e1"
        assert result["gapElements"][0]["claimPosition"] == 0

    def test_empty(self):
        result = _build_summary([], [], [])
        assert result["totalClaims"] == 0
        assert result["totalEvidence"] == 0
        assert result["coveragePercent"] == 0
        assert result["gapElements"] == []


# ---------------------------------------------------------------------------
# _count_by_field
# ---------------------------------------------------------------------------


class TestCountByField:
    def test_tier_counts(self):
        evs = [
            _make_evidence("a", tier="primary"),
            _make_evidence("b", tier="reporting"),
            _make_evidence("c", tier="reporting"),
        ]
        result = _count_by_field(evs, "tier")
        assert result == {"primary": 1, "reporting": 2}

    def test_type_counts(self):
        evs = [
            _make_evidence("a", etype="news_reporting"),
            _make_evidence("b", etype="official_data"),
        ]
        result = _count_by_field(evs, "evidenceType")
        assert result == {"news_reporting": 1, "official_data": 1}

    def test_missing_values_skipped(self):
        evs = [{"evidenceId": "a"}, _make_evidence("b", tier="primary")]
        result = _count_by_field(evs, "tier")
        assert result == {"primary": 1}


# ---------------------------------------------------------------------------
# _build_heatmap
# ---------------------------------------------------------------------------


class TestBuildHeatmap:
    def test_correct_pairs(self):
        evs = [
            _make_evidence("a", tier="primary", etype="official_data"),
            _make_evidence("b", tier="primary", etype="official_data"),
            _make_evidence("c", tier="reporting", etype="news_reporting"),
        ]
        result = _build_heatmap(evs)
        assert len(result) == 2
        pairs = {(r["tier"], r["type"]): r["count"] for r in result}
        assert pairs[("primary", "official_data")] == 2
        assert pairs[("reporting", "news_reporting")] == 1

    def test_empty(self):
        assert _build_heatmap([]) == []


# ---------------------------------------------------------------------------
# _build_corroboration
# ---------------------------------------------------------------------------


class TestBuildCorroboration:
    def test_groups(self):
        evs = [
            _make_evidence("a", group=1),
            _make_evidence("b", group=1),
            _make_evidence("c", group=2),
        ]
        result = _build_corroboration(evs)
        assert len(result["groups"]) == 2
        group_sizes = {g["groupId"]: g["size"] for g in result["groups"]}
        assert group_sizes[1] == 2
        assert group_sizes[2] == 1

    def test_convergence_count(self):
        # Convergence requires >= 3 members in a group.
        evs = [
            _make_evidence("a", group=1),
            _make_evidence("b", group=1),
            _make_evidence("c", group=1),
            _make_evidence("d", group=2),
        ]
        result = _build_corroboration(evs)
        assert result["convergenceCount"] == 1


# ---------------------------------------------------------------------------
# _compute_diagnostic_values
# ---------------------------------------------------------------------------


class TestComputeDiagnosticValues:
    def test_supports_and_challenges_gives_1_0(self):
        el_a = _make_element(
            "e1",
            refs=[
                {"evidenceId": "ev-1", "relationship": "supports"},
            ],
        )
        el_b = _make_element(
            "e2",
            refs=[
                {"evidenceId": "ev-1", "relationship": "challenges"},
            ],
        )
        claims = [_make_claim(0, elements=[el_a, el_b])]
        result = _compute_diagnostic_values(claims)
        assert result["values"]["ev-1"] == 1.0
        assert result["hasDiagnosticVariance"] is True

    def test_context_only_gives_0_1(self):
        el = _make_element(
            "e1",
            refs=[
                {"evidenceId": "ev-1", "relationship": "context"},
            ],
        )
        claims = [_make_claim(0, elements=[el])]
        result = _compute_diagnostic_values(claims)
        assert result["values"]["ev-1"] == 0.1

    def test_single_non_context_gives_0_6(self):
        el = _make_element(
            "e1",
            refs=[
                {"evidenceId": "ev-1", "relationship": "supports"},
            ],
        )
        claims = [_make_claim(0, elements=[el])]
        result = _compute_diagnostic_values(claims)
        assert result["values"]["ev-1"] == 0.6
        # supports-only does NOT set hasDiagnosticVariance
        assert result["hasDiagnosticVariance"] is False

    def test_challenges_only_sets_variance(self):
        el = _make_element(
            "e1",
            refs=[
                {"evidenceId": "ev-1", "relationship": "challenges"},
            ],
        )
        claims = [_make_claim(0, elements=[el])]
        result = _compute_diagnostic_values(claims)
        assert result["values"]["ev-1"] == 0.6
        assert result["hasDiagnosticVariance"] is True


# ---------------------------------------------------------------------------
# _build_timeline
# ---------------------------------------------------------------------------


class TestBuildTimeline:
    def test_date_range(self):
        evs = [
            _make_evidence("a", date="2026-01-01T00:00:00"),
            _make_evidence("b", date="2026-02-15T00:00:00"),
        ]
        result = _build_timeline(evs)
        assert result["datedCount"] == 2
        assert result["undatedCount"] == 0
        assert result["dateRange"] is not None
        assert "2026-01-01" in result["dateRange"]["earliest"]
        assert "2026-02-15" in result["dateRange"]["latest"]

    def test_undated(self):
        evs = [_make_evidence("a"), _make_evidence("b")]
        result = _build_timeline(evs)
        assert result["datedCount"] == 0
        assert result["undatedCount"] == 2
        assert result["dateRange"] is None

    def test_gap_detection(self):
        evs = [
            _make_evidence("a", date="2026-01-01T00:00:00"),
            _make_evidence("b", date="2026-03-15T00:00:00"),  # 73 days later
        ]
        result = _build_timeline(evs)
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["gapDays"] == 73

    def test_below_threshold(self):
        # 1 dated out of 3 total = 33% < 50% threshold
        evs = [
            _make_evidence("a", date="2026-01-01T00:00:00"),
            _make_evidence("b"),
            _make_evidence("c"),
        ]
        result = _build_timeline(evs)
        assert result["belowThreshold"] is True


# ---------------------------------------------------------------------------
# _build_per_claim
# ---------------------------------------------------------------------------


class TestBuildPerClaim:
    def test_dispositions(self):
        refs = [
            {"evidenceId": "ev-1", "relationship": "supports"},
            {"evidenceId": "ev-2", "relationship": "challenges"},
        ]
        el = _make_element("e1", state="disputed", refs=refs)
        ev1 = _make_evidence("ev-1")
        ev2 = _make_evidence("ev-2")
        claim = _make_claim(0, elements=[el], evidence=[ev1, ev2])
        result = _build_per_claim(claim)
        assert result["claimPosition"] == 0
        assert result["dispositions"]["e1"]["supports"] == ["ev-1"]
        assert result["dispositions"]["e1"]["challenges"] == ["ev-2"]
        assert result["dispositions"]["e1"]["context"] == []

    def test_coverage(self):
        refs = [{"evidenceId": "ev-1", "relationship": "supports"}]
        e1 = _make_element("e1", refs=refs)
        e2 = _make_element("e2")  # no evidence
        claim = _make_claim(0, elements=[e1, e2])
        result = _build_per_claim(claim)
        assert result["coveragePercent"] == 50.0
        assert result["elementCount"] == 2
