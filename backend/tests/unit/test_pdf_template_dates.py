"""F2 Phase B — PDF template date provenance rendering.

Renders the real Jinja template (the thing that changed) with fixture
evidence and asserts the honest-date additions:
- suspect dates carry "(date reported by host)"
- confirmed/engine dates do not
- every source line shows its retrieval date ("retrieved DD Mon YYYY")

WeasyPrint conversion is pre-existing machinery, deliberately not exercised.
"""

from datetime import datetime
from types import SimpleNamespace

from app.api.v1.checks import jinja_env


def _evidence(**overrides):
    base = dict(
        id="db-1",
        evidence_id="ev-001",
        title="Integrated Water Resources Management",
        url="https://example.org/wp-content/uploads/2026/04/paper.pdf",
        source="example.org",
        snippet="Some snippet text.",
        tier="commentary",
        evidence_type="academic",
        receipt_status="shown",
        published_date=datetime(2026, 4, 4),
        date_basis="engine",
        created_at=datetime(2026, 7, 3, 8, 36),
        exclusion_reason=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _render(evidence_list):
    template = jinja_env.get_template("pdf/fact_check_report.html")
    check = SimpleNamespace(
        id="ec8d8bc8-730b-476d-8882-c0bf6ec8d510",
        input_url=None,
        processing_time_ms=76400,
        entry_mode="focused",
        created_at=datetime(2026, 7, 3, 8, 36),
        manifest=None,
    )
    claim = {
        "text": "Test claim text.",
        "claim_type": "empirical",
        "claim_map": None,
        "orientation": None,
        "elements": [],
        "evidence": evidence_list,
        "evidence_index": {},
    }
    return template.render(
        check=check,
        claims=[claim],
        total_evidence=len(evidence_list),
        total_elements=0,
        tier_counts={"primary": 0, "reporting": 0, "commentary": len(evidence_list)},
        type_counts={},
        now=datetime(2026, 7, 3, 12, 0),
    )


class TestPdfDateProvenance:
    def test_suspect_date_carries_host_hint(self):
        html = _render([_evidence(date_basis="url_inferred_suspect")])
        assert "(date reported by host)" in html
        assert "04 Apr 2026" in html  # date retained, never dropped

    def test_confirmed_and_engine_dates_have_no_hint(self):
        for basis in ("page_metadata", "engine", "api_adapter", None):
            html = _render([_evidence(date_basis=basis)])
            assert "(date reported by host)" not in html, f"basis={basis}"

    def test_every_source_shows_retrieval_date(self):
        html = _render([_evidence()])
        assert "retrieved 03 Jul 2026" in html

    def test_undated_source_still_shows_retrieval_date(self):
        html = _render([_evidence(published_date=None, date_basis=None)])
        assert "retrieved 03 Jul 2026" in html
        assert "(date reported by host)" not in html

    def test_excluded_receipt_unaffected(self):
        html = _render(
            [
                _evidence(),
                _evidence(
                    id="db-2",
                    evidence_id="ev-002",
                    receipt_status="excluded",
                    exclusion_reason="irrelevant",
                ),
            ]
        )
        assert "excluded: irrelevant" in html
