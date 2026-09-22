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


# ============================================================
# Attribution claims (2026-09-22)
#
# The gate exists because a claim about a SUBJECT'S CONDUCT is not evidenced by
# that subject's own press office (TRU-018F-44AA, "Trump stopped 6 wars").
# A claim about what the subject SAID is the opposite case: their own document
# is the primary record of the saying.
#
# Production record 8d66d41a filed the Thirlwall Inquiry's own report as context
# against its own printed sentence ("A statutory barring system for managers
# should be introduced"); the element still read supported only because the
# recital gate mis-fired in the opposite direction and cancelled it.
#
# Record: audit/2026-09-22_mapper_reads_framing_defect.md
# ============================================================


class TestGenericInstitutionTokens:
    """A subject's institution-TYPE word must not claim unrelated domains."""

    def test_inquiry_token_does_not_match_a_third_party_tracker(self):
        from app.utils.interested_party import claim_subjects, interested_party_match

        subjects = claim_subjects(["Thirlwall Inquiry"])
        assert (
            interested_party_match(subjects, "https://www.inquirytracker.uk/inquiries/40/")
            is None
        )

    def test_political_token_does_not_match_a_news_domain(self):
        from app.utils.interested_party import claim_subjects, interested_party_match

        subjects = claim_subjects(["Political Action Committee"])
        assert interested_party_match(subjects, "https://politicalwire.com/x") is None

    def test_the_bodys_own_domain_still_matches(self):
        """The stop-list removes the TYPE word, never the distinctive name."""
        from app.utils.interested_party import claim_subjects, interested_party_match

        subjects = claim_subjects(["Thirlwall Inquiry"])
        match = interested_party_match(
            subjects, "https://thirlwall.public-inquiry.uk/summary-chapter/"
        )
        assert match is not None
        assert match["subject_matched"] == "thirlwall inquiry"

    def test_018f_control_is_untouched(self):
        """The claim the gate was built for must keep firing."""
        from app.utils.interested_party import claim_subjects, interested_party_match

        subjects = claim_subjects(["Donald Trump"])
        assert interested_party_match(subjects, "https://www.whitehouse.gov/a") is not None
        assert (
            interested_party_match(subjects, "https://trumpwhitehouse.archives.gov/b")
            is not None
        )
        assert interested_party_match(subjects, "https://mcdonalds.com/c") is None


class TestAttributionShapedElements:
    """Which elements release the gate, and which must never."""

    @staticmethod
    def _f(text):
        from app.utils.recital_scope import element_asserts_attribution

        return element_asserts_attribution(text)

    def test_formal_publication_verbs_release_the_gate(self):
        for text in (
            "The Inquiry specified the introduction of a statutory barring system.",
            "The Thirlwall Inquiry recommended a barring system by September 2027.",
            "The Central Bank published its Q3 2026 bulletin.",
            "The report set out 17 recommendations.",
            "The committee proposed a statutory register.",
            "The regulator called for an independent review.",
        ):
            assert self._f(text) is True, text

    def test_conduct_elements_keep_the_gate(self):
        """018F's protective shape, and ordinary factual elements."""
        for text in (
            "Donald Trump stopped six wars.",
            "Six armed conflicts ended between January and July 2026.",
            "UK CPI inflation was below 2% in September 2024.",
            "The ceasefire between Israel and Iran holds.",
        ):
            assert self._f(text) is False, text

    def test_ambiguous_finding_verbs_are_deliberately_excluded(self):
        """"found"/"shows"/"reports" read as the finding at least as often as
        the act of stating it. Widening the disarm on them costs more than the
        recitals it would spare — see recital_scope._ATTRIBUTION_SHAPED_ELEMENT.
        """
        for text in (
            "Researchers found that creatine improves strength.",
            "ONS data shows unemployment rose.",
        ):
            assert self._f(text) is False, text

    def test_symmetry_a_denial_releases_it_as_readily_as_a_boast(self):
        """Invariant 7: the disarm cannot be direction-sensitive."""
        assert self._f("The company denied polluting the river.") is True
        assert self._f("The company announced record safety results.") is True
