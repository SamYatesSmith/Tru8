"""Recital evidence-text narrowing R0–R5 (A− recital review, 2026-09-24).

9 of the 12 recital fires on the 19 graded records were wrong, all through the
evidence-text path, each on a sentence the support did not rest on. Texts below
are verbatim (or near) from records 1ca0070f, cb939365 and 1c90a8bb. The
TRU-018F-44AA side is pinned too: a subject's self-assessment stays gated.
"""

import pytest

from app.utils.interested_party import distinctive_tokens
from app.utils.recital_scope import EvidenceNarrowing, recital_match

REFORM_CLAIM = (
    "Reform UK's £72 million came in the space of one weekend — £36 million each "
    "from crypto billionaires Ben Delo and Christopher Harborne."
)
PLEDGE_CLAIM = "Reform UK has been pledged £72m this week — £36m from Ben Delo and £36m from Christopher Harborne."
REFORM_SUBJECTS = ["reform uk", "ben delo", "christopher harborne"]
TRUMP_CLAIM = "Donald Trump stopped 6 wars"


def _fires(text, claim=REFORM_CLAIM, subjects=REFORM_SUBJECTS, element="Reform UK received £72 million in one weekend.", released=()):
    tokens = distinctive_tokens(subjects)
    n = EvidenceNarrowing([claim], element, released)
    return recital_match(None, text, tokens, claim, narrowing=n) is not None


# ── the nine misfires, released ──────────────────────────────────────────────
@pytest.mark.parametrize(
    "rule,text",
    [
        ("R1", "According to abcnews.com, Reform UK received 72 million pounds from two billionaires."),
        ("R1", "The sum is the biggest single donation ever, according to the article.\n- Delo has already donated £4m to Reform."),
        ("R2", "Reform declines to say if £72m donors returned to UK within 12-month limit"),
        ("R5", "The pledges mean Reform has received a cash injection of £72m in just 24 hours.\n- Harborne's donation was announced on Saturday afternoon."),
        ("R4", "Reform UK received 72 million pounds this weekend.\n- Christopher Harborne on Saturday announced he was matching the donation."),
        ("R4", "- On Friday Ben Delo gave Reform UK £36 million.\n- Delo announced his gift on 11 September."),
    ],
)
def test_misfires_are_released(rule, text):
    assert not _fires(text), rule


def test_R4_performative_claim_releases_without_an_own_voice_figure():
    text = "Crypto billionaire Christopher Harborne has said he has matched the record donation."
    assert not _fires(text, claim=PLEDGE_CLAIM, element="Ben Delo has pledged £36m and Christopher Harborne has pledged £36m.")


def test_R3_an_orgs_own_publication_is_released():
    claim = "Central Bank of Ireland research published in September 2026 shows multinational activity has been key."
    text = "Growth outstripped consumer demand, according to the Central Bank of Ireland."
    subjects = ["central bank of ireland"]
    tokens = [t for t, _ in distinctive_tokens(subjects)]
    assert _fires(text, claim, subjects, "Multinational activity has driven Ireland's outperformance.")
    assert not _fires(text, claim, subjects, "Multinational activity has driven Ireland's outperformance.", released=tokens)


# ── what must keep firing ────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text",
    [
        "President Trump has repeatedly claimed credit for ending six or seven wars.",
        "President Trump announced he had ended the war between Israel and Iran.",
        "Trump said he has solved six wars in six months.",
        "Trump has said he donated his salary and ended six wars.",
    ],
)
def test_018F_self_assessment_stays_gated(text):
    assert _fires(text, claim=TRUMP_CLAIM, subjects=["donald trump"], element="Donald Trump took actions that ended six wars.")


def test_R4_needs_a_performative_claim_or_an_own_voice_figure():
    # Review adversarial case: a company's own account of a completed donation,
    # with nothing in the source's own voice, stays an interested account.
    assert _fires(
        "Acme announced it donated £1bn to charity.",
        claim="Acme donated £1bn to charity.",
        subjects=["acme"],
        element="Acme donated £1bn to charity.",
    )


def test_R4_blocks_a_self_assessing_element():
    text = "- On Friday Ben Delo gave Reform UK £36 million.\n- Delo announced his gift on 11 September."
    assert _fires(text, element="The donation is the biggest ever given to a UK party.")


def test_R4_act_list_is_closed():
    # "launch" and "contribut" were cut on review: announcing a launch is not a
    # transaction, and "contributed to ending wars" must not share a stem.
    from app.utils.recital_scope import _act_stems

    assert not _act_stems("The hospital was launched") & {"launc"}
    assert "contr" not in _act_stems("Trump contributed to ending the war")


def test_R0_a_match_cannot_cross_a_sentence():
    # Subject in one bullet, verb in the next: not one attribution.
    assert not _fires("Reform UK received £72m.\n- Critics said the rules must change.")


def test_reasoning_path_is_untouched():
    # The narrowing applies to the evidence text only; an attribution in the
    # mapper's own reasoning still fires.
    tokens = distinctive_tokens(["donald trump"])
    n = EvidenceNarrowing([TRUMP_CLAIM], "x", [])
    assert recital_match("Trump said he ended the wars.", "Unrelated text about wars.", tokens, TRUMP_CLAIM, narrowing=n)


def test_R5_passive_alone_releases():
    # No transactional act shared with the claim, so R4 cannot be what releases it.
    assert not _fires(
        "Reform UK's lead grew to nine points.\n- Reform's polling result was announced on Friday.",
        claim="Reform UK's poll lead grew to nine points in September.",
        subjects=["reform uk"],
        element="Reform UK's poll lead grew to nine points.",
    )


def test_R4_a_contested_self_assessment_verb_keeps_the_gate():
    # Same act and an own-voice figure, but the actor CLAIMED it: stays gated.
    assert _fires("- On Friday Ben Delo gave Reform UK £36 million.\n- Delo claimed his gift broke every record.")


def _weekend_map():
    return {
        "claim_id": "0",
        "normalised_claim": REFORM_CLAIM,
        "elements": [{"element_id": "e1", "description": "Reform UK received £72 million in the space of one weekend.", "evidence_refs": [], "state": None}],
        "metadata": {
            "subjects": REFORM_SUBJECTS,
            "subject_kinds": {"reform uk": "org", "ben delo": "person", "christopher harborne": "person"},
            "claim_text": REFORM_CLAIM,
        },
    }


_GUARDIAN = [
    {
        "evidence_id": "ev-guardian",
        "url": "https://www.theguardian.com/politics/2026/sep/12/christopher-harborne-reform",
        "title": "Christopher Harborne matches £36m Reform donation of Ben Delo",
        "snippet": (
            "- The pledges mean Reform has received a cash injection of £72m in just 24 hours.\n"
            "- Harborne's donation was announced on Saturday afternoon."
        ),
        "tier": "reporting",
        "evidence_type": "news_reporting",
    }
]


def _resp():
    return {"elements": [{"element_id": "e1", "evidence_refs": [{"evidence_id": "ev-guardian", "relationship": "supports", "reasoning": "States £72m in 24 hours."}]}]}


def test_wired_the_weekend_source_keeps_its_support():
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    cm = _weekend_map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp(), cm, _GUARDIAN)
    ref = cm["elements"][0]["evidence_refs"][0]
    rel = ref["relationship"].value if hasattr(ref["relationship"], "value") else ref["relationship"]
    assert rel == "supports"


def test_wired_flag_off_restores_the_old_behaviour(monkeypatch):
    from app.core import config
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    monkeypatch.setattr(config.settings, "ENABLE_RECITAL_EVIDENCE_NARROWING", False)
    cm = _weekend_map()
    ClaimMapAnalyzer()._parse_mapping_response(_resp(), cm, _GUARDIAN)
    ref = cm["elements"][0]["evidence_refs"][0]
    rel = ref["relationship"].value if hasattr(ref["relationship"], "value") else ref["relationship"]
    assert rel == "context"
