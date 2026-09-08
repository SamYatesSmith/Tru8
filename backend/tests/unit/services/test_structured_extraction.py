import pytest

from app.services.structured_extraction import supplement_main_content


def test_table_caption_units_are_preserved():
    html = "<main><table><caption>Annual rainfall (mm)</caption><tr><th>Area</th><th>Total</th></tr><tr><td>North</td><td>900</td></tr></table></main>"
    assert "Annual rainfall (mm)\nArea | Total\nNorth | 900" in supplement_main_content(
        html, "Overview"
    )


def test_omitted_value_label_and_date_survive_without_publisher_selectors():
    html = "<main><div><b>37.4°C</b><span>Measured water temperature</span><p>Observed on 12 June 2024</p></div></main>"
    text = supplement_main_content(html, "Narrative overview.")
    assert text.startswith("Narrative overview.")
    assert "37.4°C Measured water temperature Observed on 12 June 2024" in text


def test_tables_keep_headers_rows_and_definition_lists_keep_pairs():
    html = "<article><table><tr><th>Group</th><th>Events</th></tr><tr><td>Treated</td><td>14</td></tr><tr><td>Control</td><td>28</td></tr></table><dl><dt>Population</dt><dd>Adults with prior disease</dd></dl></article>"
    text = supplement_main_content(html, "Trial summary.")
    assert "Group | Events\nTreated | 14\nControl | 28" in text
    assert "Population Adults with prior disease" in text


@pytest.mark.parametrize(
    "wrapper",
    [
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "div hidden",
        'div aria-hidden="true"',
        'div style="display: none"',
        'div role="dialog"',
    ],
)
def test_navigation_clocks_hidden_and_forms_are_not_supplemented(wrapper):
    tag = wrapper.split()[0]
    html = f"<main><{wrapper}><div><b>2026</b><span>Page clock</span></div><table><tr><td>Noise</td><td>99</td></tr></table></{tag}></main>"
    assert supplement_main_content(html, "Body") == "Body"


def test_no_main_region_does_not_enable_whole_body_scraping():
    assert (
        supplement_main_content(
            "<body><div><b>99</b><span>Menu count</span></div></body>", "Body"
        )
        == "Body"
    )


def test_dedup_keeps_numeric_signs_and_does_not_repeat_existing_blocks():
    html = "<main><div><b>-5%</b><span>Change</span></div></main>"
    assert "-5% Change" in supplement_main_content(html, "5% Change")
    assert supplement_main_content(html, "-5% Change") == "-5% Change"


def test_bounded_whole_blocks_and_no_duplicate_nested_main():
    html = (
        '<main><article role="main">'
        + "".join(
            f"<div><b>{i}</b><span>Reservoir level</span></div>" for i in range(40)
        )
        + "</article></main>"
    )
    text = supplement_main_content(html, "Body")
    assert text.count("Reservoir level") == 12


def test_switch_wires_the_real_extraction_method_and_fails_back(monkeypatch):
    from app.services.evidence import EvidenceExtractor, settings
    from app.services import structured_extraction

    monkeypatch.setattr(
        "app.services.evidence.trafilatura.extract", lambda *a, **k: "Narrative. " * 25
    )
    extractor = object.__new__(EvidenceExtractor)
    html = "<main><div><b>42%</b><span>Reservoir level</span></div></main>"
    monkeypatch.setattr(settings, "ENABLE_STRUCTURED_EXTRACTION", False)
    baseline = extractor._extract_main_content(html, "https://example.invalid")
    monkeypatch.setattr(settings, "ENABLE_STRUCTURED_EXTRACTION", True)
    assert "42% Reservoir level" in extractor._extract_main_content(
        html, "https://example.invalid"
    )

    def fail(*args):
        raise ValueError("Malformed structure")

    monkeypatch.setattr(structured_extraction, "supplement_main_content", fail)
    assert extractor._extract_main_content(html, "https://example.invalid") == baseline


def test_switch_has_distinct_cache_and_fingerprint(monkeypatch):
    from app.core.config import settings
    from app.core.manifest_signer import compute_pipeline_fingerprint
    from app.services.cache import CacheService

    cache = object.__new__(CacheService)
    monkeypatch.setattr(settings, "ENABLE_STRUCTURED_EXTRACTION", False)
    old_fingerprint = compute_pipeline_fingerprint()
    old_key = cache._evidence_identifier("claim")
    monkeypatch.setattr(settings, "ENABLE_STRUCTURED_EXTRACTION", True)
    assert compute_pipeline_fingerprint() != old_fingerprint
    assert cache._evidence_identifier("claim") != old_key


def test_recovered_content_reaches_retained_passages_and_api(monkeypatch):
    from app.services.evidence import EvidenceExtractor, settings
    from app.services.text_provenance import capture_text_provenance
    from app.services.evidence_payload import evidence_from_mapping
    from app.api.v1.response_builder import _serialize_evidence

    monkeypatch.setattr(
        "app.services.evidence.trafilatura.extract", lambda *a, **k: "Overview. " * 30
    )
    monkeypatch.setattr(settings, "ENABLE_STRUCTURED_EXTRACTION", True)
    html = "<main><div><b>19°C</b><span>Water temperature</span><p>Measured on 12 June 2024</p></div></main>"
    extractor = object.__new__(EvidenceExtractor)
    item = {
        "url": "https://example.invalid",
        "_full_text": extractor._extract_main_content(html, "https://example.invalid"),
    }
    capture_text_provenance(
        item,
        "water temperature",
        [{"element_id": "e1", "description": "Measured water temperature"}],
    )
    receipt = _serialize_evidence(evidence_from_mapping("claim", item))[
        "textProvenance"
    ]
    assert any(
        "19°C Water temperature Measured on 12 June 2024" in p["text"]
        for p in receipt["passages"]
    )


def test_large_table_is_not_cut_mid_row():
    html = (
        "<main><table><tr><th>Label</th><th>Value</th></tr>"
        + "<tr><td>"
        + ("Long description " * 200)
        + "</td><td>42</td></tr></table></main>"
    )
    assert supplement_main_content(html, "Body") == "Body"
