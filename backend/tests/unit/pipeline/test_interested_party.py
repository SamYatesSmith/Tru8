"""The interested-party tagger alone — the wired seam is tested separately.

Built from production check TRU-018F-44AA, where whitehouse.gov's "I've solved
six wars in six months" was a primary-weight support for "Donald Trump stopped
6 wars". See test_assertion_evidence_wiring.py for the gate through the real
mapping parser.
"""

from app.utils.interested_party import (
    claim_subjects,
    distinctive_tokens,
    interested_party_match,
)

SUBJECTS = ["donald trump"]


# ---------------------------------------------------------------------------
# claim_subjects — the arming input
# ---------------------------------------------------------------------------


def test_person_and_org_entities_become_subjects():
    entities = [
        {"text": "Donald Trump", "type": "PERSON"},
        {"text": "The White House", "type": "ORG"},
    ]
    assert claim_subjects(entities) == ["donald trump", "the white house"]


def test_other_entity_types_are_not_subjects():
    """A LAW or EVENT cannot control a domain — only actors are subjects."""
    entities = [
        {"text": "Climate Change Act 2008", "type": "LAW"},
        {"text": "COP28", "type": "EVENT"},
        {"text": "Falcon 9", "type": "PRODUCT"},
    ]
    assert claim_subjects(entities) == []


def test_plain_strings_pass_through():
    """Metadata that was already normalised (the wired path) round-trips."""
    assert claim_subjects(["Donald Trump"]) == ["donald trump"]


def test_malformed_input_is_safe():
    assert claim_subjects(None) == []
    assert claim_subjects([{"type": "PERSON"}, 42, ""]) == []


# ---------------------------------------------------------------------------
# Prong 1 — name-in-domain
# ---------------------------------------------------------------------------


def test_the_archived_trump_white_house_is_interested():
    match = interested_party_match(
        SUBJECTS, "https://trumpwhitehouse.archives.gov/people/donald-j-trump/"
    )
    assert match is not None
    assert match["prong"] == "name_in_domain"
    assert match["subject_matched"] == "donald trump"


def test_the_subjects_own_org_domain_is_interested():
    assert interested_party_match(SUBJECTS, "https://www.trump.org/about") is not None


def test_label_start_matching_not_substring():
    """ "donald" must not match mcdonalds.com — the guard that keeps prong 1 sane."""
    assert interested_party_match(SUBJECTS, "https://www.mcdonalds.com/") is None


def test_generic_tokens_never_match():
    """ "White House" must not fuzzy-match every domain containing "house"."""
    assert (
        interested_party_match(["the white house"], "https://www.housebeautiful.com/")
        is None
    )


# ---------------------------------------------------------------------------
# Prong 2 — executive-comms map
# ---------------------------------------------------------------------------


def test_the_white_house_speaks_for_its_officeholder():
    match = interested_party_match(
        SUBJECTS, "https://www.whitehouse.gov/videos/president-trump-solved/"
    )
    assert match is not None
    assert match["prong"] in ("name_in_domain", "executive_comms")


def test_subdomains_are_the_same_organ():
    assert (
        interested_party_match(
            ["trump administration"], "https://videos.whitehouse.gov/x"
        )
        is not None
    )


def test_the_org_entity_matches_the_organ():
    match = interested_party_match(
        ["the white house"], "https://www.whitehouse.gov/releases/365-wins/"
    )
    assert match is not None
    assert match["prong"] == "executive_comms"


def test_statistics_offices_are_deliberately_absent():
    """BLS/ONS independence: a stats office is never "the administration"."""
    assert (
        interested_party_match(["trump administration"], "https://www.bls.gov/cpi/")
        is None
    )
    assert (
        interested_party_match(["uk government"], "https://www.ons.gov.uk/economy/")
        is None
    )


def test_a_congressmans_site_is_aligned_not_controlled():
    """davidson.house.gov endorsing Trump survives — endorsement is not control.

    (In TRU-018F-44AA this ref legitimately remains; the recital gate handles
    endorsement-shaped recitals, not this one.)
    """
    assert (
        interested_party_match(
            SUBJECTS, "https://davidson.house.gov/2019/10/trump-right/"
        )
        is None
    )


def test_an_unrelated_leaders_claim_does_not_flag_the_white_house():
    """Terms are named, not generic: a claim about another head of state must
    not mark whitehouse.gov as interested."""
    assert (
        interested_party_match(
            ["emmanuel macron"], "https://www.whitehouse.gov/briefing/"
        )
        is None
    )


# ---------------------------------------------------------------------------
# Safe directions
# ---------------------------------------------------------------------------


def test_no_subjects_no_match():
    assert interested_party_match([], "https://www.whitehouse.gov/") is None


def test_no_url_no_match():
    assert interested_party_match(SUBJECTS, None) is None
    assert interested_party_match(SUBJECTS, "not a url") is None


def test_distinctive_tokens_drop_short_and_generic():
    tokens = dict(distinctive_tokens(["donald trump", "the white house", "un"]))
    assert "trump" in tokens
    assert "donald" in tokens
    assert "white" not in tokens  # stop-listed
    assert "house" not in tokens  # stop-listed
    assert "the" not in tokens  # too short
    assert "un" not in tokens  # too short
