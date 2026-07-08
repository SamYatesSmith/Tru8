"""Guard test for the brand-aligned PDF evidence report (F5 Phase A).

The PDF is a second rendering engine (WeasyPrint/Jinja) that drifts from the
React frontend by construction. This test renders the template from a plain
fixture context — no DB, no live pipeline — and locks the Phase A guarantees
deterministically so a future edit can't silently regress them:

  * NO verdict colour on element states / ref-counts (the standing invariant).
  * Brand chassis present: embedded @font-face (Inter + JetBrains Mono),
    the accent top-rule, the diamond glyph, the split-weight wordmark.
  * Per-card tier TEXT label (tier legible without decoding a colour stripe).
  * F3 scope caveat rendered from element.basis.state_derivation.caveat.
  * Neutral state glyphs (+ / ± / ○ / ⓘ), matching the app ElementStateBadge.

A WeasyPrint smoke test renders actual PDF bytes when the GTK libraries are
available (skipped cleanly otherwise, so the guard above always runs).
"""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.pdf_assets import FONT_FACE_CSS

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "app" / "templates"


def _evidence(**kw):
    """An ORM-Evidence-like stand-in (template reads by attribute)."""
    defaults = dict(
        evidence_id="ev1",
        id="ev1",
        title="A source title",
        url="https://example.gov/report",
        tier="primary",
        evidence_type="official_document",
        source="example.gov",
        published_date=datetime(2020, 4, 1, tzinfo=timezone.utc),
        date_basis=None,
        created_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
        snippet="A snippet of the source.",
        receipt_status="included",
        exclusion_reason=None,
        relevance_score=5,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


CAVEAT_TEXT = "Supporting evidence addresses England and Wales, not Britain as a whole."


def _context():
    check = SimpleNamespace(
        id="abcd1234efgh5678",
        created_at=datetime(2026, 7, 8, 9, 3, tzinfo=timezone.utc),
        input_url="https://news.example.com/article",
        processing_time_ms=58200,
        entry_mode="article",
        status="completed",
        manifest={"signature": "a" * 64},
    )

    elements = [
        {
            "description": "Britain has a privatised water system.",
            "state": "supported",
            "evidence_refs": [
                {"evidence_id": "ev1", "relationship": "supports"},
                {"evidence_id": "ev2", "relationship": "supports"},
            ],
            "uncertainty": None,
            # F3: the reach caveat rides the neutral state_derivation channel.
            "basis": {"state_derivation": {"caveat": CAVEAT_TEXT}},
        },
        {
            "description": "It is the only such system in the world.",
            "state": "disputed",
            "evidence_refs": [
                {"evidence_id": "ev1", "relationship": "supports"},
                {"evidence_id": "ev3", "relationship": "challenges"},
            ],
            "uncertainty": "Sources conflict on scope.",
            "basis": {},
        },
    ]

    evidence = [
        _evidence(evidence_id="ev1", id="ev1", tier="primary", title="Ofwat report"),
        _evidence(
            evidence_id="ev2",
            id="ev2",
            tier="reporting",
            title="Guardian coverage",
            source="theguardian.com",
            date_basis="url_inferred_suspect",
        ),
        _evidence(
            evidence_id="ev3",
            id="ev3",
            tier="commentary",
            title="A blog post",
            source="blog.example.com",
        ),
        _evidence(
            evidence_id="ev4",
            id="ev4",
            tier="commentary",
            title="Excluded low-relevance source",
            receipt_status="excluded",
            exclusion_reason="low_relevance",
        ),
    ]

    claim = {
        "text": "Britain is the only country with a privatised water system.",
        "claim_type": "factual",
        "claim_map": {"elements": elements},
        "orientation": "Of 2 elements examined, 1 is supported and 1 is disputed.",
        "elements": elements,
        "evidence": evidence,
        "evidence_index": {"ev1": 1, "ev2": 2, "ev3": 3, "ev4": 4},
    }

    return dict(
        check=check,
        claims=[claim],
        total_evidence=4,
        total_elements=2,
        tier_counts={"primary": 1, "reporting": 1, "commentary": 2},
        type_counts={"official_document": 1, "article": 2, "blog": 1},
        font_face_css=FONT_FACE_CSS,
        now=datetime(2026, 7, 8, 9, 3, tzinfo=timezone.utc),
    )


@pytest.fixture(scope="module")
def rendered_html():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("pdf/fact_check_report.html")
    return template.render(**_context())


# ── The brand fonts actually loaded (guards the TTF copy step) ────────────────


def test_font_face_css_is_populated():
    assert (
        FONT_FACE_CSS
    ), "no brand fonts embedded — TTFs missing from templates/pdf/fonts"
    assert "@font-face" in FONT_FACE_CSS
    assert "data:font/ttf;base64," in FONT_FACE_CSS
    assert "Inter" in FONT_FACE_CSS
    assert "JetBrains Mono" in FONT_FACE_CSS


def test_fonts_embedded_in_render(rendered_html):
    assert "@font-face" in rendered_html
    assert "data:font/ttf;base64," in rendered_html
    assert "var(--sans)" in rendered_html
    assert "var(--mono)" in rendered_html


# ── NO VERDICT COLOUR — the standing invariant ────────────────────────────────


@pytest.mark.parametrize(
    "banned",
    [
        "#16A34A",  # green
        "#F0FDF4",
        "#BBF7D0",
        "#D97706",  # amber (as a STATE/ref colour)
        "#FFFBEB",
        "#FDE68A",
        "var(--green)",
        "var(--amber)",
        "--green:",
        "--amber:",
    ],
)
def test_no_verdict_colour_tokens(rendered_html, banned):
    assert (
        banned not in rendered_html
    ), f"verdict-colour token leaked into the PDF: {banned}"


def test_states_are_neutral_fill_outline(rendered_html):
    # supported = dark fill, disputed = outline, unresolved = dashed — no hue.
    assert (
        ".st-supported { color: var(--surface); background: var(--ink);"
        in rendered_html
    )
    assert "1px dashed var(--ink-4)" in rendered_html  # unresolved


# ── Neutral state glyphs (match the app ElementStateBadge) ────────────────────


def test_state_glyphs_present(rendered_html):
    assert 'class="st-glyph"' in rendered_html
    # supported '+' and disputed '±' both appear on the fixture's two elements.
    assert "±" in rendered_html or "&plusmn;" in rendered_html


# ── Per-card tier TEXT label ──────────────────────────────────────────────────


def test_tier_text_label_present(rendered_html):
    assert "ev-tier ev-tier-primary" in rendered_html
    assert "ev-tier ev-tier-reporting" in rendered_html
    assert "ev-tier ev-tier-commentary" in rendered_html


# ── F3 scope caveat rendered ──────────────────────────────────────────────────


def test_f3_caveat_rendered(rendered_html):
    assert 'class="el-caveat"' in rendered_html
    assert CAVEAT_TEXT in rendered_html


# ── Brand chassis ─────────────────────────────────────────────────────────────


def test_brand_chassis_present(rendered_html):
    assert 'class="brand-rule"' in rendered_html  # 6px accent top-rule
    assert 'class="diamond"' in rendered_html  # accent diamond glyph
    assert 'class="hdr-brand-8"' in rendered_html  # split-weight wordmark
    assert "radial-gradient" in rendered_html  # dotted-grid ground
    assert "--accent: #EA580C" in rendered_html  # brand accent retained


# ── WeasyPrint smoke (skips cleanly without GTK libs) ─────────────────────────


def test_weasyprint_renders_bytes(rendered_html):
    weasyprint = pytest.importorskip("weasyprint")

    def _fetch(url, timeout=10, ssl_context=None):
        if url.startswith("data:"):
            return weasyprint.default_url_fetcher(url, timeout, ssl_context)
        raise ValueError(f"blocked: {url}")

    try:
        pdf_bytes = weasyprint.HTML(
            string=rendered_html, url_fetcher=_fetch
        ).write_pdf()
    except OSError as exc:  # GTK/Pango native libs not installed locally
        pytest.skip(f"WeasyPrint native libs unavailable: {exc}")
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 5000


# ── The PRODUCTION fetcher itself (F-SEC-05 + the data: relaxation) ────────────


def test_production_fetcher_blocks_network_and_file():
    """The real fetcher must still refuse every non-data: scheme (F-SEC-05)."""
    from app.api.v1.checks import _block_pdf_network_fetch

    for blocked in (
        "http://attacker.example/?u=secret",
        "https://attacker.example/x.png",
        "file:///etc/passwd",
        "ftp://host/x",
        "//attacker.example/x",
    ):
        with pytest.raises(ValueError):
            _block_pdf_network_fetch(blocked)


def test_production_fetcher_allows_data_uri():
    """data: URIs are permitted (self-contained, no network) — how fonts load."""
    pytest.importorskip("weasyprint")
    from app.api.v1.checks import _block_pdf_network_fetch

    # "hi" base64 — decodes inline per RFC 2397, no network/file access.
    result = _block_pdf_network_fetch("data:text/plain;base64,aGk=")
    assert result  # a truthy fetch dict, no exception raised
