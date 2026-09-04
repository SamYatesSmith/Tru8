"""The public record's title for a text check — whole, never a 70-char cut.

2026-09-04: `/r/<id>` rendered "AI triage through the NHS App reduced the
number of people queuing on ..." as its H1, browser tab, share text and OG
card, with the full claim one block below. The title is derived on every
request from the excerpt + claims, never stored, so this helper is the whole
behaviour.
"""

from app.api.v1.checks import text_check_title

CLAIM = (
    "AI triage through the NHS App reduced the number of people queuing on the "
    "phone at GP practices by 29 per cent in a Sussex pilot"
)


def test_single_claim_check_uses_the_claim_whole():
    assert text_check_title(CLAIM, [CLAIM]) == CLAIM


def test_single_claim_check_is_never_cut_or_ellipsised():
    long_claim = "Scotland " + "x" * 300 + " end"
    title = text_check_title(long_claim, [long_claim])
    assert title == long_claim
    assert "..." not in title


def test_multi_claim_text_uses_first_sentence_whole():
    excerpt = (
        "The first sentence of a pasted article runs well past seventy characters "
        "and must survive intact. The second sentence is not the title."
    )
    assert text_check_title(excerpt, ["claim a", "claim b"]) == (
        "The first sentence of a pasted article runs well past seventy characters "
        "and must survive intact."
    )


def test_decimal_and_abbreviation_do_not_end_the_title():
    excerpt = "UK inflation was 3.4% in June, the U.S. rate 2.9%. Analysts disagreed."
    assert text_check_title(excerpt, ["a", "b"]) == (
        "UK inflation was 3.4% in June, the U.S. rate 2.9%."
    )


def test_no_terminator_returns_whole_excerpt():
    excerpt = "A claim with no full stop at all"
    assert text_check_title(excerpt, ["a", "b"]) == excerpt


def test_empty_inputs():
    assert text_check_title("", []) == ""
    assert text_check_title("  ", [""]) == ""
    # A single empty claim falls back to the excerpt's first sentence.
    assert text_check_title("Only sentence.", [""]) == "Only sentence."
