"""A1′ — the recital gate skips only an UNOWNED document speaking (2026-09-29).

Design: audit/2026-09-28_family_a_speaker_design.md (Revision 2).
Review: audit/2026-09-28_family_a_speaker_review.md — every sentence below
comes from the review's adversarial set (F1, F2, F4, G1) or the motivating
record 50e08e0e (Cook's poll). Both evidence and reasoning paths; supports and
challenges alike (invariant #7).
"""

import pytest

from app.utils.interested_party import distinctive_tokens
from app.utils.recital_scope import (
    DirectionRelease,
    EvidenceNarrowing,
    recital_match,
)

TRUMP_CLAIM = "Donald Trump stopped 6 wars"
COOK_CLAIM = (
    "Cook Political Report, GS Strategy Group and New River Strategies surveyed "
    "1,052 likely voters from September 8-11, 2026 across the 37 House districts "
    "Cook rates as competitive; the generic ballot in them is Democrats 49, "
    "Republicans 47, and Trump's job approval is 42-58."
)
COOK_SUBJECTS = ["cook political report", "democrats", "republicans", "trump"]
TRUMP_SUBJECTS = ["donald trump"]
TESLA_SUBJECTS = ["tesla"]


def _fires(
    sentence, subjects, claim, direction="supports", *, path="evidence", skip=True
):
    tokens = distinctive_tokens(subjects)
    release = DirectionRelease(direction, [claim], "", tokens)
    narrowing = EvidenceNarrowing([claim], "", [])
    if path == "evidence":
        reasoning, evidence = None, sentence
    else:
        reasoning, evidence = sentence, None
    return (
        recital_match(
            reasoning,
            evidence,
            tokens,
            None,
            narrowing=narrowing,
            release=release,
            instrument_skip=skip,
        )
        is not None
    )


# ── Skipped: an unowned document is the speaker ──────────────────────────────
SKIPPED = [
    # record 50e08e0e's exact marker
    "According to the September 2026 toplines, Democrats hold a two-point advantage.",
    "According to the poll Democrats hold a two-point advantage.",  # no comma (F4)
    "Democrats hold a two-point lead, the poll said.",
    "Democrats lead by two, the latest survey says.",
]


@pytest.mark.parametrize("path", ["evidence", "reasoning"])
@pytest.mark.parametrize("direction", ["supports", "challenges"])
@pytest.mark.parametrize("sentence", SKIPPED)
def test_an_unowned_instrument_speaking_is_not_a_recital(sentence, direction, path):
    assert _fires(sentence, COOK_SUBJECTS, COOK_CLAIM, direction, path=path) is False


@pytest.mark.parametrize("sentence", SKIPPED)
def test_the_flag_off_restores_the_old_fire(sentence):
    assert _fires(sentence, COOK_SUBJECTS, COOK_CLAIM, skip=False) is True


# ── Still fires: people, agents, owned documents, unknown pronouns ───────────
TRUMP_STILL_FIRES = [
    # F2 — the subject's own boasts with something between name and verb
    "Trump on Tuesday claimed he had ended six wars.",
    "Trump last week said he had ended six wars.",
    "Trump in a Truth Social post claimed he had ended six wars.",
    "Trump, speaking at the UN, claimed to have ended six wars.",
    "Trump ended six wars, he said.",
    # F1 — anyone else reciting it
    "Trump's spokesman said the president has ended six wars.",
    "Trump has ended six wars, his spokesman said.",
    "According to administration officials, Trump has ended six wars.",
    "According to his spokesman, Trump has ended six wars.",
    "According to a White House statement, Trump has ended six wars.",
    "According to Trump, six wars have ended.",
    # G1 — the subject's own documents are the subject's own voice
    "According to a White House report, Trump has ended six wars.",
    "According to a White House press release, Trump has ended six wars.",
    "According to the campaign's analysis, Trump has ended six wars.",
    "According to his own figures, Trump has ended six wars.",
    "Trump ended six wars, the new WH report said.",
]


@pytest.mark.parametrize("path", ["evidence", "reasoning"])
@pytest.mark.parametrize("sentence", TRUMP_STILL_FIRES)
def test_a_person_agent_or_owned_document_still_fires(sentence, path):
    assert _fires(sentence, TRUMP_SUBJECTS, TRUMP_CLAIM, path=path) is True


def test_an_owned_document_on_a_challenge_still_fires():
    # G1, challenges direction
    assert (
        _fires(
            "Trump ended no wars, their analysis says.",
            TRUMP_SUBJECTS,
            TRUMP_CLAIM,
            "challenges",
        )
        is True
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "According to the company, Tesla delivered a record 500,000 cars.",
        "According to its spokesperson, Tesla delivered a record 500,000 cars.",
        "Tesla on Thursday announced a record 500,000 deliveries.",
    ],
)
def test_an_organisation_speaking_still_fires(sentence):
    assert (
        _fires(sentence, TESLA_SUBJECTS, "Tesla delivered a record 500,000 cars")
        is True
    )


def test_an_unknown_pronoun_speaker_still_fires():
    # F4: "it" may be the poll or the outlet; unknown keeps firing, as today.
    assert (
        _fires("Democrats hold a two-point lead, it said.", COOK_SUBJECTS, COOK_CLAIM)
        is True
    )


def test_an_instrument_phrase_naming_a_subject_still_fires():
    assert (
        _fires(
            "According to the Trump survey, Democrats hold a two-point advantage.",
            COOK_SUBJECTS,
            COOK_CLAIM,
        )
        is True
    )


def test_a_later_genuine_recital_in_the_same_text_still_fires():
    text = (
        "According to the toplines, Democrats hold a two-point advantage. "
        "Trump claimed the poll was rigged."
    )
    assert _fires(text, COOK_SUBJECTS, COOK_CLAIM) is True


def test_the_veto_and_distancing_rules_are_untouched():
    assert (
        _fires(
            "The poll allegedly shows Democrats ahead, the survey says.",
            COOK_SUBJECTS,
            COOK_CLAIM,
        )
        is True
    )
