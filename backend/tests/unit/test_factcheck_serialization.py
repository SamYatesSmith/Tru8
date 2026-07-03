"""Tests for the #14 fact-check rating gate in _serialize_evidence.

A publisher rating is surfaced ONLY for a fact-check confirmed to be about
THIS claim: is_factcheck && factcheck_parse_success && !factcheck_low_relevance
&& a rating is present. Everything else must omit publisher/rating entirely, so
we never attribute a verdict about a different claim to ours.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.response_builder import _serialize_evidence


def _ev(**overrides):
    """Minimal Evidence-like object for the serializer."""
    base = dict(
        id="e1",
        evidence_id="ev-1",
        source="PolitiFact",
        url="https://politifact.com/x",
        title="Fact-check: claim about X",
        snippet="...",
        published_date=None,
        relevance_score=4.0,
        tier="reporting",
        evidence_type="news_reporting",
        receipt_status="shown",
        corroboration_group_id=None,
        corroborating_evidence_ids=None,
        is_factcheck=False,
        external_source_provider=None,
        source_type=None,
        archived_url=None,
        llm_relevance_score=None,
        classification_method=None,
        content_basis=None,
        date_basis=None,
        # fact-check fields
        factcheck_publisher=None,
        factcheck_rating=None,
        factcheck_date=None,
        factcheck_parse_success=False,
        factcheck_low_relevance=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _confirmed(**overrides):
    fields = dict(
        is_factcheck=True,
        factcheck_parse_success=True,
        factcheck_low_relevance=False,
        factcheck_publisher="PolitiFact",
        factcheck_rating="False",
    )
    fields.update(overrides)
    return _ev(**fields)


def test_confirmed_factcheck_surfaces_publisher_and_rating():
    out = _serialize_evidence(_confirmed())
    assert out["factcheckPublisher"] == "PolitiFact"
    assert out["factcheckRating"] == "False"


def test_confirmed_factcheck_includes_date_isoformat():
    d = datetime(2024, 5, 1, tzinfo=timezone.utc)
    out = _serialize_evidence(_confirmed(factcheck_date=d))
    assert out["factcheckDate"] == d.isoformat()


def test_non_factcheck_has_no_rating():
    out = _serialize_evidence(_ev())  # is_factcheck False
    assert "factcheckPublisher" not in out
    assert "factcheckRating" not in out


def test_low_relevance_factcheck_is_gated_out():
    out = _serialize_evidence(_confirmed(factcheck_low_relevance=True))
    assert "factcheckPublisher" not in out
    assert "factcheckRating" not in out


def test_unparsed_factcheck_is_gated_out():
    out = _serialize_evidence(_confirmed(factcheck_parse_success=False))
    assert "factcheckPublisher" not in out
    assert "factcheckRating" not in out


def test_factcheck_without_rating_is_gated_out():
    out = _serialize_evidence(_confirmed(factcheck_rating=None))
    assert "factcheckPublisher" not in out
    assert "factcheckRating" not in out


def test_isfactcheck_flag_always_present():
    # The boolean flag is base-level (not gated) so the UI can tag the source.
    assert _serialize_evidence(_ev())["isFactcheck"] is False
    assert _serialize_evidence(_confirmed())["isFactcheck"] is True
