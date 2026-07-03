"""Tests for date provenance classification (F2).

Design: audit/2026-07-03_f1f2_design_review.md — acceptance criteria AC2-AC6.
The canonical failure this layer exists for: a 2000-era PDF hosted under
/wp-content/uploads/2026/04/ that Google reported as Apr 2026
(TRU-EC8D-8BC8 source 1).
"""

from app.utils.date_provenance import (
    DATE_BASIS_API,
    DATE_BASIS_ENGINE,
    DATE_BASIS_PAGE,
    DATE_BASIS_URL_SUSPECT,
    derive_date_basis,
)


class TestDeriveDateBasis:
    """Provenance classification of a published_date about to be stored."""

    # --- AC2: page metadata wins ---

    def test_page_date_wins(self):
        """Page-declared date present => page_metadata, regardless of engine."""
        assert (
            derive_date_basis("https://example.com/article", "2026-04-04", "2020-01-15")
            == DATE_BASIS_PAGE
        )

    def test_page_date_wins_even_without_engine_date(self):
        assert (
            derive_date_basis("https://example.com/article", None, "2020-01-15")
            == DATE_BASIS_PAGE
        )

    # --- AC3: engine date, unconfirmed ---

    def test_engine_only(self):
        """Engine date with no page date and no URL echo => engine."""
        assert (
            derive_date_basis("https://example.com/article", "2026-04-04")
            == DATE_BASIS_ENGINE
        )

    def test_engine_url_date_mismatch_is_engine(self):
        """URL has a date path but a DIFFERENT month => not suspect."""
        assert (
            derive_date_basis(
                "https://example.com/uploads/2019/11/report.pdf", "2026-04-04"
            )
            == DATE_BASIS_ENGINE
        )

    # --- AC4: the water-report case ---

    def test_url_upload_path_echo_is_suspect(self):
        """Engine date matching /YYYY/MM/ in the URL, no page date => suspect.

        Exact TRU-EC8D-8BC8 shape: 2000-era GWP paper under /uploads/2026/04/
        reported by the engine as April 2026.
        """
        assert (
            derive_date_basis(
                "https://gwpo-gwp.org/wp-content/uploads/2026/04/04-integrated"
                "-water-resources-management-2000-english.pdf",
                "2026-04-04",
            )
            == DATE_BASIS_URL_SUSPECT
        )

    def test_suspect_with_unpadded_month(self):
        """/2026/4/ (no zero padding) also matches."""
        assert (
            derive_date_basis("https://example.com/2026/4/post", "2026-04-10")
            == DATE_BASIS_URL_SUSPECT
        )

    def test_page_confirmation_defuses_suspicion(self):
        """URL echoes the engine date BUT the page declares its own date
        => page_metadata (the page confirmation is what we store)."""
        assert (
            derive_date_basis(
                "https://example.com/uploads/2026/04/doc.pdf",
                "2026-04-04",
                "2026-04-04",
            )
            == DATE_BASIS_PAGE
        )

    def test_unparseable_engine_date_is_engine_not_suspect(self):
        """Suspicion needs a parseable year+month; garbage stays engine."""
        assert (
            derive_date_basis(
                "https://example.com/uploads/2026/04/doc.pdf", "circa spring"
            )
            == DATE_BASIS_ENGINE
        )

    # --- AC6: nothing at all ---

    def test_no_dates_is_none(self):
        assert derive_date_basis("https://example.com/article", None) is None
        assert derive_date_basis("https://example.com/article", "") is None

    def test_none_url_is_safe(self):
        assert derive_date_basis(None, "2026-04-04") == DATE_BASIS_ENGINE

    # --- constants sanity (AC5's api_adapter is assigned at the adapter
    # conversion site, not derived — pin the stored value here) ---

    def test_api_constant_value(self):
        assert DATE_BASIS_API == "api_adapter"

    def test_year_boundaries(self):
        """19xx and 20xx path years match; other 4-digit segments don't."""
        assert (
            derive_date_basis("https://example.com/1999/07/story", "1999-07-01")
            == DATE_BASIS_URL_SUSPECT
        )
        # /8080/12/ is a port-like segment, not a plausible year
        assert (
            derive_date_basis("https://example.com/8080/12/x", "2026-12-01")
            == DATE_BASIS_ENGINE
        )
