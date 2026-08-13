"""The recital tagger alone — every fixture string is verbatim from production.

Check TRU-018F-44AA: the mapper's own reasoning strings for `supports` refs on
"Donald Trump stopped 6 wars". The wired seam is tested in
test_assertion_evidence_wiring.py.
"""

from app.utils.interested_party import distinctive_tokens
from app.utils.recital_scope import element_asserts_attribution, recital_match

TOKENS = distinctive_tokens(["donald trump"])


def _match(reasoning=None, text=None, tokens=TOKENS):
    return recital_match(reasoning, text, tokens)


# ---------------------------------------------------------------------------
# The production failures, pinned — each fired as `supports` on 2026-08-13
# ---------------------------------------------------------------------------


def test_states_trump_claimed_is_a_recital():
    match = _match(
        reasoning=(
            "This news report states Trump claimed to have 'settled six wars' "
            "and lists seven conflicts, including Israel and Iran where a "
            "ceasefire was reached with U.S. and Qatari involvement."
        )
    )
    assert match is not None
    assert match["found_in"] == "reasoning"


def test_quotes_the_president_saying_is_a_recital():
    assert (
        _match(
            reasoning=(
                "This official statement directly quotes President Trump "
                "saying, 'I've solved six wars in six months'."
            )
        )
        is not None
    )


def test_announced_he_negotiated_is_a_recital():
    assert (
        _match(
            reasoning=(
                "This analysis reports Trump announced he negotiated a truce "
                "between India and Pakistan."
            )
        )
        is not None
    )


def test_purportedly_is_distancing_wherever_it_appears():
    match = _match(
        reasoning=(
            "This analysis mentions the administration touted Trump's success "
            "in purportedly ending eight global conflicts."
        )
    )
    assert match is not None
    assert match["marker"] in ("purportedly",) or "tout" in match["marker"]


# ---------------------------------------------------------------------------
# What must NOT fire — under-crediting distorts as much as over-crediting
# ---------------------------------------------------------------------------


def test_a_sources_own_account_of_events_is_not_a_recital():
    """CBS's e4 reasoning — the source's own account, not attribution."""
    assert (
        _match(
            reasoning=(
                "This news report mentions a ceasefire between Israel and Iran "
                "was reached with 'U.S. and Qatari involvement' after Israel "
                "attacked Iran's nuclear facilities, implying Trump's actions "
                "contributed to the cessation."
            )
        )
        is None
    )


def test_reported_assessment_is_not_a_recital():
    """BBC's e4 reasoning — "received praise for brokering" attributes praise,
    not the claim."""
    assert (
        _match(
            reasoning=(
                "This news report states Trump received praise for 'brokering "
                "a ceasefire' and US strikes were widely seen as bringing the "
                "conflict towards a swift close."
            )
        )
        is None
    )


def test_unanchored_attribution_never_fires():
    """ "The ONS says inflation fell" — a source reporting its own finding."""
    assert (
        _match(reasoning="The report says GDP rose 0.1% in Q3, confirming growth.")
        is None
    )


def test_a_verification_veto_in_the_reasoning_ends_the_matter():
    """PRIO's challenge carried 'Trump announced' AND challenge framing — the
    mapper did its own work, so the gate must stand down even though the
    evidence TEXT recites."""
    assert (
        _match(
            reasoning=(
                "This analysis notes that after the Rwanda-DR Congo agreement "
                "almost 400 people were killed, and India suggested the US "
                "played only a marginal role, challenging the direct causal "
                "link of Trump's actions."
            ),
            text=(
                "After three weeks of fighting, Trump announced that he had "
                "negotiated a ceasefire."
            ),
        )
        is None
    )


def test_fact_check_framing_is_a_veto():
    assert (
        _match(
            reasoning=(
                "This opinion piece, rated Pants on Fire, directly challenges "
                "the idea that Trump claimed a unique achievement."
            )
        )
        is None
    )


def test_records_show_in_the_text_is_a_veto():
    assert (
        _match(
            reasoning="Supports the element.",
            text="Trump says he's ended 6 or 7 wars. Here's what the record shows.",
        )
        is None
    )


# ---------------------------------------------------------------------------
# The fallback order — reasoning first, text only when reasoning is silent
# ---------------------------------------------------------------------------


def test_silent_reasoning_falls_back_to_the_evidence_text():
    match = _match(
        reasoning="Bears directly on the element.",
        text=(
            "President Trump has claimed that he has 'ended 8 wars in just 8 "
            "months' in a social media post."
        ),
    )
    assert match is not None
    assert match["found_in"] == "evidence"


def test_no_tokens_no_fire():
    assert _match(reasoning="Trump claimed victory.", tokens=[]) is None


# ---------------------------------------------------------------------------
# The element-shape exemption
# ---------------------------------------------------------------------------


def test_an_element_asserting_a_saying_is_exempt():
    """ "The minister stated X" is legitimately supported by a report of the
    saying — the gate must never arm for it."""
    assert element_asserts_attribution("The minister stated that inflation fell.")
    assert element_asserts_attribution(
        "According to the ONS, prices rose in September."
    )


def test_ordinary_elements_are_not_exempt():
    assert not element_asserts_attribution(
        "Donald Trump took actions that directly led to the cessation of "
        "hostilities in six specific wars."
    )
