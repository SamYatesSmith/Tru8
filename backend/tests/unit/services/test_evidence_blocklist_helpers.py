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
from app.utils.domain_status_tracker import DomainStatus


class TestGetRuntimeBlockedDomains:
    """get_runtime_blocked_domains returns BOT_BLOCKED entries from the domain
    status tracker, plus their www. variants.

    TIMEOUT is deliberately excluded (2026-08-27). It used to be blocked, which
    made one slow response on a 5-second deadline a permanent exclusion — a
    silent, receiptless removal (invariant #5) that fell hardest on the small
    outlets least able to afford fast hosting."""

    def test_returns_bot_blocked_domains_with_www_variants(self):
        mock_tracker = MagicMock()
        mock_tracker.get_domains_by_status.return_value = [
            {"domain": "facebook.com"},
            {"domain": "instagram.com"},
        ]

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            result = get_runtime_blocked_domains()

        assert "facebook.com" in result
        assert "www.facebook.com" in result
        assert "instagram.com" in result
        assert "www.instagram.com" in result

    def test_a_slow_domain_is_NOT_blocked(self):
        """The 2026-08-27 change, pinned. Slow is not hostile.

        A domain that timed out must stay eligible: the block was one-strike,
        permanent for the life of the process, and invisible downstream. The
        cost of NOT blocking is bounded — one more fetch slot, capped by the
        same 5s timeout. The cost of blocking was a publisher disappearing.
        """
        mock_tracker = MagicMock()

        def by_status(status):
            if status is DomainStatus.BOT_BLOCKED:
                return [{"domain": "facebook.com"}]
            return [{"domain": "slow-server.example"}]

        mock_tracker.get_domains_by_status.side_effect = by_status

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            result = get_runtime_blocked_domains()

        assert "slow-server.example" not in result
        assert "www.slow-server.example" not in result
        assert "facebook.com" in result  # an explicit refusal still blocks

    def test_timeout_status_is_never_even_queried(self):
        """Stronger than checking the output: the TIMEOUT bucket is not read.

        Asserting only on the returned set would still pass if someone re-added
        the union and the fixture happened to return nothing for it.
        """
        mock_tracker = MagicMock()
        mock_tracker.get_domains_by_status.return_value = []

        with patch(
            "app.services.evidence.get_domain_tracker", return_value=mock_tracker
        ):
            get_runtime_blocked_domains()

        queried = [c.args[0] for c in mock_tracker.get_domains_by_status.call_args_list]
        assert DomainStatus.TIMEOUT not in queried
        assert DomainStatus.BOT_BLOCKED in queried

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
        mock_tracker.get_domains_by_status.return_value = [
            {"domain": "facebook.com"},
            {"domain": ""},
            {"foo": "bar"},
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
