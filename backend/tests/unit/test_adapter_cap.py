"""Unit tests for B1 (audit §2.2): domain-aware adapter cap.

The hardcoded cap of 3 was silently dropping OpenAlex from every Health
claim via the PQ-06 tier sort. Config-driven per-domain caps fix this.
These tests pin the resolver's contract so a future change that breaks
fallback behaviour fails loudly rather than silently reverting to the
old bug.
"""

import pytest


class TestGetAdapterCapForDomain:
    """get_adapter_cap_for_domain reads from settings.ADAPTER_CAPS_PER_DOMAIN
    and returns an integer cap per article domain."""

    def test_health_has_raised_cap(self):
        """Health = 4 — the specific domain the audit §2.2 bug fix targets.
        With cap=4 all four Health specialists (PubMed, WHO, S2, OpenAlex)
        fit; cap=3 silently dropped OpenAlex."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("Health") == 4

    def test_science_allows_five(self):
        """Science = 5 — accommodates PubMed, S2, OpenAlex plus generalists."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("Science") == 5

    def test_unknown_domain_falls_back_to_default(self):
        """Any domain not explicitly listed uses the DEFAULT cap (3)."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("NotARealDomain") == 3

    def test_none_domain_falls_back_to_default(self):
        """Classification failures pass domain=None; must still resolve to DEFAULT."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain(None) == 3

    def test_malformed_env_override_fails_safe(self, monkeypatch):
        """A broken ADAPTER_CAPS_PER_DOMAIN env value must not crash the pipeline.
        Resolver falls back to the hard-coded DEFAULT (3) rather than raising."""
        from app.core.config import settings
        from app.pipeline import retrieve

        monkeypatch.setattr(settings, "ADAPTER_CAPS_PER_DOMAIN", "{not valid json")
        assert retrieve.get_adapter_cap_for_domain("Health") == 3
        assert retrieve.get_adapter_cap_for_domain("Science") == 3

    def test_override_missing_default_is_supplied(self, monkeypatch):
        """If an operator overrides the config but forgets DEFAULT, the resolver
        still produces a valid cap for unknown domains. Guards against a subtle
        partial-override outage."""
        from app.core.config import settings
        from app.pipeline import retrieve

        monkeypatch.setattr(settings, "ADAPTER_CAPS_PER_DOMAIN", '{"Health": 6}')
        assert retrieve.get_adapter_cap_for_domain("Health") == 6
        assert retrieve.get_adapter_cap_for_domain("Science") == 3  # supplied DEFAULT

    def test_non_integer_cap_value_falls_back(self, monkeypatch):
        """Defensive: if a domain's cap is a non-numeric string, resolver
        returns the DEFAULT fallback rather than propagating a type error."""
        from app.core.config import settings
        from app.pipeline import retrieve

        monkeypatch.setattr(
            settings,
            "ADAPTER_CAPS_PER_DOMAIN",
            '{"Health": "lots", "DEFAULT": 3}',
        )
        assert retrieve.get_adapter_cap_for_domain("Health") == 3
