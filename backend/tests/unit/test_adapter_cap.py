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

    def test_climate_has_raised_cap(self):
        """SC-02: Climate = 4 — same class of bug as Health. Scorecard showed
        NOAA + WeatherAPI + Open-Meteo filling cap=3 and silently dropping the
        academic backstops (Semantic Scholar, OpenAlex, Wikipedia) on every
        Climate claim."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("Climate") == 4

    def test_finance_has_raised_cap(self):
        """SC-02: Finance = 4 — four tier-1 adapters (Marketaux, World Bank,
        FRED, ONS/Companies House) routinely contend for cap=3 slots. Raise to
        keep one specialist adapter surviving on any given Finance claim."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("Finance") == 4

    def test_law_has_raised_cap(self):
        """SC-17: Law = 4 — observed on TRU-A0C5-05DB (Data Protection Act 2018).
        UK Law claims have four genuine primary specialists: UK Parliament Bills,
        UK Parliament Hansard, GOV.UK Content API, Companies House. At cap=3
        (DEFAULT) one of them is cap-victimised on every UK Law claim — on
        TRU-A0C5-05DB it was Bills, exactly the SC-15 specialist we built.
        Same class of bug as SC-02 Climate/Finance."""
        from app.pipeline.retrieve import get_adapter_cap_for_domain

        assert get_adapter_cap_for_domain("Law") == 4

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


class TestGetEffectiveAdapterCap:
    """NF-09: get_effective_adapter_cap widens the cap when an article
    classifier returns secondary_domains, so cross-domain claims keep
    their cross-specialists instead of cap-victimising them. Each
    secondary adds 2 slots; primary keeps its full cap.

    Observed motivating case: TRU-DD26-16FE ("Climate Change Act 2008")
    classified as Climate; Bills/Hansard/GOV.UK/Companies House merged
    into the pool by retrieve.py:2050-2061 then cap-victimised by the
    primary-only Climate cap=4.
    """

    def test_no_secondaries_matches_base_cap(self):
        """No secondaries → effective cap equals the primary's base cap."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap("Climate", []) == 4
        assert get_effective_adapter_cap("Health", None) == 4
        assert get_effective_adapter_cap("Science") == 5

    def test_climate_plus_law_secondary(self):
        """Motivating case: Climate primary + Law secondary → 4 + 2 = 6.
        Pre-NF-09 this was 4, dropping the Law specialists."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap("Climate", ["Law"]) == 6

    def test_two_secondaries_adds_four_slots(self):
        """Classifier caps at 2 secondaries (article_classifier.py line ~484).
        Worst case: primary=4 + 2*2 = 8 — bounded latency."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap("Health", ["Finance", "Politics"]) == 8

    def test_unknown_primary_with_secondary(self):
        """Unknown primary uses DEFAULT (3) then adds secondary slots."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap("NotARealDomain", ["Climate"]) == 5

    def test_none_primary_with_secondary(self):
        """Primary=None (classification failure) still resolves; secondary
        bonus still applies on top of the DEFAULT cap."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap(None, ["Health"]) == 5

    def test_legal_override_path_no_secondaries(self):
        """In retrieve.py the legal-override branch sets domain='Law' and
        leaves secondary_domains=[]. Effective cap must equal the Law base
        cap (4) — no surprise widening from the new code path."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        assert get_effective_adapter_cap("Law", []) == 4

    def test_secondary_count_defensively_clipped_at_two(self):
        """NF-09 hardening: the classifier's documented contract is max 2
        secondaries. If a future prompt regression returns more, the cap
        must NOT inflate beyond the worst-case design budget (base + 4).
        Pins this so a silent prompt drift can't blow latency."""
        from app.pipeline.retrieve import get_effective_adapter_cap

        # 5 secondaries would naively give 4 + 2*5 = 14; clip enforces 4 + 2*2 = 8
        assert (
            get_effective_adapter_cap(
                "Climate", ["Law", "Politics", "Finance", "Health", "Science"]
            )
            == 8
        )
        # 3 secondaries would give 4 + 2*3 = 10; clip enforces 4 + 2*2 = 8
        assert get_effective_adapter_cap("Health", ["Finance", "Politics", "Law"]) == 8
