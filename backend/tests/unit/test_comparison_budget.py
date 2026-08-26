"""COMPARE: budget arithmetic and the prompt's non-negotiables.

Budget (design §7.5): limit = 3 + re-searches on the check (re_search +
top_up kinds, minus refunds, floored at 0); used = stored comparison rows.
The cache IS the counter — there is no separate tally to drift.

Prompt (design §10.2): the claim text is DELIBERATELY absent (premise
adoption — the PARROT failure); element descriptions scope the comparison;
the hard no-adjudication rules are present. These assertions are cheap and
they are the ones a future prompt edit is most likely to break silently.
"""

import pytest

from app.services.comparison import (
    BASE_BUDGET,
    build_comparison_prompt,
    get_comparison_budget,
)


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _StubSession:
    """Returns queued scalar results in order: re_search+top_up, refunds,
    used."""

    def __init__(self, values):
        self._values = list(values)

    async def execute(self, _stmt):
        return _Result(self._values.pop(0))


class TestBudget:
    @pytest.mark.asyncio
    async def test_base_is_three(self):
        budget = await get_comparison_budget(_StubSession([0, 0, 0]), "chk")
        assert budget == {"used": 0, "limit": BASE_BUDGET}

    @pytest.mark.asyncio
    async def test_plus_one_per_re_search(self):
        budget = await get_comparison_budget(_StubSession([2, 0, 1]), "chk")
        assert budget == {"used": 1, "limit": 5}

    @pytest.mark.asyncio
    async def test_refund_does_not_inflate(self):
        # A refunded re-search grants nothing.
        budget = await get_comparison_budget(_StubSession([1, 1, 0]), "chk")
        assert budget["limit"] == BASE_BUDGET

    @pytest.mark.asyncio
    async def test_refunds_floor_at_zero(self):
        # More refunds than re-searches (a refunded check) cannot shrink
        # the base budget.
        budget = await get_comparison_budget(_StubSession([0, 2, 0]), "chk")
        assert budget["limit"] == BASE_BUDGET


class TestPromptNonNegotiables:
    def _prompt(self, **overrides):
        kwargs = dict(
            element_descriptions=[
                "What did UK CPI measure in September 2024?",
                "Was the figure below 2%?",
            ],
            source_a={"domain": "ons.gov.uk", "title": "CPI bulletin"},
            source_b={"domain": "example.org", "title": "Inflation is out of control"},
            text_a="text a",
            text_b="text b",
            basis_a="full",
            basis_b="full",
        )
        kwargs.update(overrides)
        return build_comparison_prompt(**kwargs)

    def test_element_descriptions_scope_the_prompt(self):
        prompt = self._prompt()
        assert "What did UK CPI measure in September 2024?" in prompt
        assert "Was the figure below 2%?" in prompt

    def test_no_adjudication_rules_present(self):
        prompt = self._prompt()
        assert "Never say which source is more credible" in prompt
        assert "Never state or imply an answer" in prompt
        assert "Attribute every assertion" in prompt

    def test_stored_extract_is_declared(self):
        prompt = self._prompt(basis_b="stored")
        assert "stored extract, not the full article" in prompt

    def test_full_article_has_no_extract_note_on_that_side(self):
        prompt = self._prompt()
        assert "stored extract" not in prompt

    def test_attributed_voice_is_instructed(self):
        prompt = self._prompt()
        assert "ons.gov.uk piece argues" in prompt
        assert 'never "studies show' in prompt
