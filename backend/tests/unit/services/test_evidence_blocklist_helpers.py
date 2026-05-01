"""Tests for the runtime-blocklist helpers in app.services.evidence.

Background: post-filter recovery in runner.py used to append search
results straight into the evidence dict without consulting the runtime
blocklist that the extraction path applies. Bot-blocked domains
(e.g. facebook.com) leaked through whenever they had a usable
search-result snippet but the URL itself was never fetched.

Fix: shared helpers ``get_runtime_blocked_domains`` and
``is_domain_blocked`` are now used by both the EvidenceService
extraction path and the recovery loop.
"""

from unittest.mock import patch, MagicMock

from app.services.evidence import (
    get_runtime_blocked_domains,
    is_domain_blocked,
)


class TestGetRuntimeBlockedDomains:
    """get_runtime_blocked_domains aggregates BOT_BLOCKED + TIMEOUT
    entries from the domain status tracker, plus their www. variants."""

    def test_returns_bot_blocked_and_timeout_domains_with_www_variants(self):
        mock_tracker = MagicMock()
        mock_tracker.get_domains_by_status.side_effect = [
            [{"domain": "facebook.com"}, {"domain": "instagram.com"}],
            [{"domain": "slow-server.example"}],
        ]

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            result = get_runtime_blocked_domains()

        assert "facebook.com" in result
        assert "www.facebook.com" in result
        assert "instagram.com" in result
        assert "www.instagram.com" in result
        assert "slow-server.example" in result
        assert "www.slow-server.example" in result

    def test_returns_safe_fallback_on_tracker_failure(self):
        mock_tracker = MagicMock()
        mock_tracker.get_domains_by_status.side_effect = RuntimeError("boom")

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            result = get_runtime_blocked_domains()

        # Defensive fallback so a tracker outage does not disable blocking
        assert "yahoo.com" in result

    def test_skips_empty_domain_entries(self):
        mock_tracker = MagicMock()
        mock_tracker.get_domains_by_status.side_effect = [
            [{"domain": "facebook.com"}, {"domain": ""}, {"foo": "bar"}],
            [],
        ]

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            result = get_runtime_blocked_domains()

        # Empty / missing-key entries skipped, real one retained
        assert "facebook.com" in result
        assert "" not in result
        assert "www." not in result  # No standalone "www." artifact


class TestIsDomainBlocked:
    """is_domain_blocked applies substring match against the blocklist
    so 'facebook.com' in the list catches 'www.facebook.com' too."""

    def test_blocks_exact_domain_match(self):
        blocklist = {"facebook.com", "www.facebook.com"}
        assert is_domain_blocked(
            "https://www.facebook.com/BarraBest/posts/abc", blocklist
        )

    def test_blocks_bare_domain_when_only_www_variant_in_list(self):
        # extract_domain strips www., so 'facebook.com' bare is checked
        blocklist = {"facebook.com"}
        assert is_domain_blocked("https://facebook.com/page", blocklist)

    def test_does_not_block_unrelated_domain(self):
        blocklist = {"facebook.com", "www.facebook.com"}
        assert not is_domain_blocked("https://www.metoffice.gov.uk/", blocklist)

    def test_handles_empty_url(self):
        assert not is_domain_blocked("", {"facebook.com"})

    def test_handles_empty_blocklist(self):
        assert not is_domain_blocked("https://facebook.com/", set())

    def test_substring_match_catches_subdomains(self):
        # Documenting the substring semantics: m.facebook.com gets
        # caught because 'facebook.com' is a substring of it.
        blocklist = {"facebook.com"}
        assert is_domain_blocked("https://m.facebook.com/post", blocklist)
