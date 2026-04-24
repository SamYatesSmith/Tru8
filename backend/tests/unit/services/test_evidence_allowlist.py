"""SC-11 regression guards for EvidenceExtractor authoritative-TLD allowlist.

The domain_status_tracker is "one-time collection" — once a domain 403s it
gets classified BOT_BLOCKED forever with no TTL. When EvidenceExtractor boots
it hydrates self.blocked_domains from every BOT_BLOCKED + TIMEOUT entry,
which has silently excluded primary-tier public sources (bls.gov,
congress.gov, sec.gov, pmc.ncbi.nlm.nih.gov, law.stanford.edu, imperial.ac.uk
and ~40 others).

SC-11 adds an allowlist of authoritative TLDs (.gov, .gov.uk, .edu, .ac.uk,
etc.) that bypass the runtime blocklist. These tests pin the bypass
behaviour and guard against regressions.
"""

from unittest.mock import patch

import pytest

from app.services.evidence import EvidenceExtractor


@pytest.fixture
def extractor():
    """EvidenceExtractor with a representative stale blocklist.

    Patches _init_blocked_domains to a no-op so we don't pull the real
    domain_status.json at test time, then injects a fixed set that matches
    the production shape (bare domain + www. variant).
    """
    with patch.object(EvidenceExtractor, "_init_blocked_domains", lambda self: None):
        ex = EvidenceExtractor()
    ex.blocked_domains = {
        "bls.gov",
        "www.bls.gov",
        "pmc.ncbi.nlm.nih.gov",
        "www.pmc.ncbi.nlm.nih.gov",
        "law.stanford.edu",
        "www.law.stanford.edu",
        "imperial.ac.uk",
        "www.imperial.ac.uk",
        "yahoo.com",  # legitimately blocked, pre-seeded
        "www.yahoo.com",
        "some-spam-site.com",
        "www.some-spam-site.com",
    }
    return ex


class TestAuthoritativeTLDAllowlist:
    """Direct unit tests on _is_authoritative_tld()."""

    def test_gov_tld_is_authoritative(self, extractor):
        assert extractor._is_authoritative_tld("bls.gov")
        assert extractor._is_authoritative_tld("congress.gov")
        assert extractor._is_authoritative_tld("sec.gov")

    def test_gov_uk_tld_is_authoritative(self, extractor):
        assert extractor._is_authoritative_tld("data.gov.uk")
        assert extractor._is_authoritative_tld("local.gov.uk")

    def test_edu_tld_is_authoritative(self, extractor):
        assert extractor._is_authoritative_tld("law.stanford.edu")
        assert extractor._is_authoritative_tld("mitpress.mit.edu")

    def test_ac_uk_tld_is_authoritative(self, extractor):
        assert extractor._is_authoritative_tld("imperial.ac.uk")
        assert extractor._is_authoritative_tld("lshtm.ac.uk")

    def test_deep_subdomain_still_matches(self, extractor):
        # The real-world motivator: PubMed Central is *.ncbi.nlm.nih.gov
        assert extractor._is_authoritative_tld("pmc.ncbi.nlm.nih.gov")

    def test_www_prefix_stripped_before_match(self, extractor):
        assert extractor._is_authoritative_tld("www.bls.gov")

    def test_case_insensitive(self, extractor):
        assert extractor._is_authoritative_tld("BLS.GOV")
        assert extractor._is_authoritative_tld("Stanford.EDU")

    def test_non_authoritative_domain_returns_false(self, extractor):
        assert not extractor._is_authoritative_tld("yahoo.com")
        assert not extractor._is_authoritative_tld("some-spam-site.com")
        assert not extractor._is_authoritative_tld("nytimes.com")

    def test_empty_or_none_domain_is_safe(self, extractor):
        assert not extractor._is_authoritative_tld("")
        assert not extractor._is_authoritative_tld(None)

    def test_false_positive_guard_on_substring(self, extractor):
        # ".gov" inside a domain that doesn't END with it must not match.
        # e.g. "notgov.com" contains "gov" but is not a .gov domain.
        assert not extractor._is_authoritative_tld("notgov.com")
        assert not extractor._is_authoritative_tld("gov-lookalike.org")


class TestAllowlistConstantShape:
    """The allowlist is dotted-prefix form to enable endswith-based matching.

    Keeping this shape explicit so a future edit doesn't accidentally drop
    a leading dot (which would open false-positive matches like
    notgov.com ends with 'gov').
    """

    def test_every_entry_starts_with_a_dot(self):
        for tld in EvidenceExtractor.AUTHORITATIVE_TLDS:
            assert tld.startswith("."), (
                f"Allowlist entry {tld!r} must start with '.' — otherwise "
                f"endswith-matching opens false positives (e.g. 'notgov.com'"
                f" would match 'gov')."
            )

    def test_allowlist_covers_known_silent_victims(self):
        """Concrete coverage check — these were the sources silently excluded
        in the SC-11 investigation. Any regression that loses coverage of
        these TLDs should blow up loudly."""
        tlds = EvidenceExtractor.AUTHORITATIVE_TLDS
        assert ".gov" in tlds
        assert ".edu" in tlds
        assert ".ac.uk" in tlds
