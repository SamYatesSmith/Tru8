"""R6 — a challenge cannot rest on its subject restating the claim (2026-09-25).

Design: audit/2026-09-25_recital_direction_release_design.md. Review:
audit/2026-09-25_recital_direction_release_review.md.

Corpus claim TRU-018F-44AA ("Donald Trump stopped 6 wars"): all four recital
fires on the committed recording were fact-check CHALLENGES whose attribution
sentence was the claim itself, restated to be rebutted. The four evidence and
reasoning strings below are verbatim from that recording.

Both directions are pinned. The 2026-08-13 support trap must keep firing, and
every way a challenge genuinely rests on its subject's own words (a denial, a
lower figure, a role reversal, another speaker, another subject) must keep
firing too. The review's probes are included verbatim.
"""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.utils.interested_party import distinctive_tokens
from app.utils.recital_scope import DirectionRelease, EvidenceNarrowing, recital_match

CLAIM = "Donald Trump stopped 6 wars"
ELEMENT = (
    "Donald Trump was directly responsible for bringing an end to 6 distinct "
    "military conflicts or wars."
)
SUBJECTS = ["donald trump"]

# ── Verbatim from the TRU-018F-44AA recording ─────────────────────────────────
USA_TODAY = (
    "What six wars did Donald Trump end? See the list of conflicts he claims as "
    "settled - President Donald Trump claims to have settled six wars in six "
    "months.\n- The US has been involved in five ceasefires or peace agreements "
    "since Trump returned to office.\n- Trump announced a treaty between the "
    "Democratic Republic of Congo and Rwanda in a June 20 social media post.\n- "
    "Regarding the sixth war Trump was referring to, the White House cited "
    "Ethiopia and Egypt, but there has neither been a war nor a peace agreement "
    "between the countries."
)
AP = (
    "FACT FOCUS: Trump says he's ended eight wars. His numbers are off And one "
    "conflict that Trump has claimed to end has never been a war at all. Here's "
    "a closer look: Israel and Hamas."
)
GUARDIAN_REASONING = (
    "Identifies Trump's claims of having ended seven wars as false and "
    "misleading during his UN address."
)
CNN = (
    "Checking in on the ‘seven un-endable wars’ Trump did (not) end | "
    "CNN - US President Donald Trump claimed in an address to the United Nations "
    "that he has 'ended seven un-endable wars.'\n- Trump announced a ceasefire "
    "between Israel and Iran after 12 days of fighting in June."
)


def _fires(
    direction,
    text=None,
    reasoning=None,
    claim=CLAIM,
    element=ELEMENT,
    subjects=SUBJECTS,
    release=True,
):
    tokens = distinctive_tokens(subjects)
    rel = DirectionRelease(direction, [claim], element, tokens) if release else None
    return (
        recital_match(
            reasoning,
            text,
            tokens,
            claim,
            narrowing=EvidenceNarrowing([claim], element, []),
            release=rel,
        )
        is not None
    )


# ── The four 018F fires are released ──────────────────────────────────────────


@pytest.mark.parametrize("text", [USA_TODAY, AP, CNN], ids=["usatoday", "ap", "cnn"])
def test_fact_check_challenge_restating_the_claim_is_released(text):
    assert _fires("challenges", text=text, release=False)  # fired before R6
    assert not _fires("challenges", text=text)


def test_reasoning_path_restatement_is_released():
    assert _fires("challenges", reasoning=GUARDIAN_REASONING, release=False)
    assert not _fires("challenges", reasoning=GUARDIAN_REASONING)


# ── The support trap (2026-08-13) is untouched ────────────────────────────────


@pytest.mark.parametrize("text", [USA_TODAY, AP, CNN], ids=["usatoday", "ap", "cnn"])
def test_the_same_texts_filed_as_SUPPORTS_still_fire(text):
    assert _fires("supports", text=text)


@pytest.mark.parametrize(
    "text",
    [
        "Trump has repeatedly claimed credit for ending six wars.",
        "Trump said he has solved six wars, calling himself a peacemaker.",
        "Trump announced he had ended the war between Israel and Iran.",
        "Trump has repeatedly claimed credit for ending six wars. Critics of Trump "
        "say he did not end six wars.",
        "Trump said that without him, six wars would never have ended.",
        "Trump said he did what no president could: end six wars.",
        "Trump said he wasn't going to rest until he had ended six wars.",
    ],
)
def test_recital_supports_still_fire(text):
    assert _fires("supports", text=text)


@pytest.mark.parametrize(
    "reasoning",
    [
        "This news report states Trump claimed to have 'settled six wars'",
        "directly quotes President Trump saying, 'I've solved six wars'",
        "The article reports Trump claimed to have ended six wars and cites aides "
        "of Trump who say they doubt it.",
    ],
)
def test_recital_support_reasoning_still_fires(reasoning):
    assert _fires("supports", reasoning=reasoning)


# ── Challenges that genuinely rest on the subject's words still fire ──────────


@pytest.mark.parametrize(
    "text",
    [
        # Denials, including contractions (review F1).
        "Trump said he didn't end six wars.",
        "Trump says he hasn't ended six wars, only helped.",
        "Trump said he did not end six wars and that only two conflicts were settled.",
        # Lower figure / downtoner (F6).
        "Trump said he has only ended two wars.",
        "In 2019 Trump said he had ended just one war.",
        # Blame shift and another party.
        "Trump said the wars were ended by Biden and not by him.",
        # "they" is not the subject (F7 / §6.5).
        "Trump said they had ended six wars between them, referring to Qatar and Egypt.",
        # Negated speech never feeds the stance (F7).
        "Trump did not say he ended six wars; Trump said the deals were signed by others.",
    ],
)
def test_subject_grounded_challenges_still_fire(text):
    assert _fires("challenges", text=text)


def test_role_reversal_still_fires():
    claim = "Amber Heard physically abused Johnny Depp during their marriage"
    subjects = ["amber heard", "johnny depp"]
    for text in [
        "Heard says she was the one physically abused during the marriage.",
        "Depp says he was physically abused by Heard during their marriage. Heard "
        "says she was the one physically abused during the marriage.",
    ]:
        assert _fires(
            "challenges", text=text, claim=claim, element=claim, subjects=subjects
        )


def test_stance_is_per_subject():
    """Harborne restating does not release Delo's denial (F5)."""
    claim = "Reform UK received £72m from Christopher Harborne and Delo"
    element = "Reform UK received donations totalling £72m from Harborne and Delo"
    text = (
        "Harborne said he had given Reform UK donations of £72m. Delo said it has "
        "not donated anything to Reform."
    )
    assert _fires(
        "challenges",
        text=text,
        claim=claim,
        element=element,
        subjects=["reform uk", "christopher harborne", "delo"],
    )


@pytest.mark.parametrize(
    "text",
    [
        "Biden says inflation was caused by Putin's war.",
        "Biden said he has cut inflation since taking office.",
        "Biden said he did not cause inflation to rise.",
    ],
)
def test_self_serving_accounts_on_an_accusation_still_fire(text):
    assert _fires(
        "challenges",
        text=text,
        claim="Joe Biden caused inflation to rise",
        element="Joe Biden's policies caused inflation to rise",
        subjects=["joe biden"],
    )


def test_an_accused_subject_restating_the_accusation_is_released():
    assert not _fires(
        "challenges",
        text="Biden says he caused inflation to rise, but economists disagree.",
        claim="Joe Biden caused inflation to rise",
        element="Joe Biden's policies caused inflation to rise",
        subjects=["joe biden"],
    )


# ── Rule-level guards (each fails if its rule is removed) ─────────────────────


def _classify(text, direction="challenges", claim=CLAIM, element=ELEMENT):
    import re

    rel = DirectionRelease(direction, [claim], element, distinctive_tokens(SUBJECTS))
    for pattern, _token, kind, _subject in rel._tagged:
        if kind != "verb":
            continue
        match = pattern.search(text)
        if match:
            return rel.classify(text, match)
    raise AssertionError("no match")  # pragma: no cover


def test_contraction_is_a_denial():
    assert _classify("Trump said he didn't end six wars.") == "contrary"


def test_one_shared_stem_is_not_a_restatement():
    assert _classify("Trump said he has solved conflicts.") is None


def test_downtoner_is_contrary():
    assert _classify("Trump said he has only ended six wars.") == "contrary"


def test_lower_figure_is_contrary():
    assert _classify("Trump said he has ended two wars.") == "contrary"


def test_a_year_is_not_a_count():
    assert _classify("Trump said he has ended six wars in 2025.") == "restates"


def test_negation_far_from_the_verb_is_not_a_denial():
    assert (
        _classify("Trump said he did what no president could: end six wars.")
        == "restates"
    )


def test_speaker_must_be_the_subject():
    rel = DirectionRelease("challenges", [CLAIM], ELEMENT, distinctive_tokens(SUBJECTS))
    text = "Critics of Trump say he did end six wars, then asked for proof."
    assert rel._stances(text) == {}


def test_another_speakers_attribution_in_a_proponent_text_still_fires():
    """Trump restates the claim, so the text's stance is proponent — but the
    second match is Trump's aides speaking, not Trump, and is not released."""
    text = (
        "Trump says he has ended six wars. Aides of Trump say the peace deals "
        "were brokered by Qatar."
    )
    rel = DirectionRelease("challenges", [CLAIM], ELEMENT, distinctive_tokens(SUBJECTS))
    released = [
        rel.releases(text, match)
        for pattern, _t, kind, _s in rel._tagged
        if kind == "verb"
        for match in pattern.finditer(text)
    ]
    assert released.count(True) >= 1  # "Trump says he has ended six wars"
    assert False in released  # "Aides of Trump say …"


def test_supports_are_never_released():
    rel = DirectionRelease("supports", [CLAIM], ELEMENT, distinctive_tokens(SUBJECTS))
    for pattern, *_rest in rel._tagged:
        for match in pattern.finditer(AP):
            assert not rel.releases(AP, match)


# ── The wired seam ────────────────────────────────────────────────────────────

EVIDENCE = [
    {
        "evidence_id": "ev-ap",
        "url": "https://apnews.com/article/trump-wars-fact-focus",
        "title": "FACT FOCUS",
        "snippet": AP,
        "tier": "reporting",
        "evidence_type": "news",
    },
    {
        "evidence_id": "ev-usat",
        "url": "https://www.usatoday.com/story/news/politics/2025/08/20/donald-trump-six-wars/",
        "title": "What six wars did Donald Trump end?",
        "snippet": USA_TODAY,
        "tier": "reporting",
        "evidence_type": "news",
    },
    {
        "evidence_id": "ev-cbs",
        "url": "https://www.cbsnews.com/news/trump-ended-6-or-7-wars/",
        "title": "Trump says he's ended 6 or 7 wars.",
        "snippet": "President Trump has repeatedly claimed credit for ending six or seven wars.",
        "tier": "reporting",
        "evidence_type": "news",
    },
]


def _parse():
    analyzer = ClaimMapAnalyzer()
    claim_map = {
        "claim_id": "0",
        "normalised_claim": CLAIM,
        "elements": [
            {
                "element_id": "e1",
                "description": ELEMENT,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {"jurisdiction": "US", "subjects": SUBJECTS},
    }
    response = {
        "elements": [
            {
                "element_id": "e1",
                "state": "disputed",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-ap",
                        "relationship": "challenges",
                        "reasoning": "Notes that Trump's numbers for ended wars are incorrect and some listed conflicts were never wars.",
                    },
                    {
                        "evidence_id": "ev-usat",
                        "relationship": "challenges",
                        "reasoning": "Highlights that among the six conflicts claimed, Egypt and Ethiopia had neither a war nor a peace deal.",
                    },
                    {
                        "evidence_id": "ev-cbs",
                        "relationship": "supports",
                        "reasoning": "This news report states Trump claimed to have 'settled six wars' and lists seven conflicts.",
                    },
                ],
            }
        ]
    }
    analyzer._parse_mapping_response(response, claim_map, EVIDENCE)
    elem = claim_map["elements"][0]
    return {
        r["evidence_id"]: getattr(r["relationship"], "value", r["relationship"])
        for r in elem["evidence_refs"]
    }, elem


def test_wired_fact_checks_stay_challenges_and_the_recital_support_is_scoped():
    rels, elem = _parse()
    assert rels["ev-ap"] == "challenges"
    assert rels["ev-usat"] == "challenges"
    assert rels["ev-cbs"] == "context"
    scoped = [e["evidence_id"] for e in elem["basis"]["recital_scope"]["scoped"]]
    assert scoped == ["ev-cbs"]


def test_flag_off_restores_the_old_behaviour(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_RECITAL_DIRECTION_RELEASE", False)
    rels, _elem = _parse()
    assert rels["ev-ap"] == "context"
    assert rels["ev-usat"] == "context"
    assert rels["ev-cbs"] == "context"
