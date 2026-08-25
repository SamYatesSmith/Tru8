"""The recital gate must work on claims that name NOBODY (2026-08-25).

The gate shipped 2026-08-13 for TRU-018F-44AA ("Trump stopped 6 wars"), which
names a subject. Every one of the 63 existing tests across four files supplies
subjects, so nothing covered the case where `metadata.subjects` is empty — and
in that case the gate did not fail, it never armed at all.

That left a PROMPT rule as the only thing stopping a claim citing itself, and
prompt rules are model-shaped. Measured on a frozen pool, 5 repeats, identical
input:

    gemini-2.5-flash       reciting tweet -> context   10/10
    gemini-3.5-flash-lite  reciting tweet -> SUPPORTS  10/10
    gemini-3.7-flash       reciting tweet -> context    5/5

The failure survived two model generations because the old model happened to
comply with the prompt. These tests pin the mechanical path so no future model
can reopen it.
"""

import pytest

from app.utils.recital_scope import (
    claim_restatement_match,
    element_asserts_attribution,
    recital_match,
)

# The real case: Matt Ridley's tweet IS the claim being checked.
CLAIM = "2026 is the quietest year for wildfires in Europe by some distance"
RIDLEY_TWEET = (
    "2026 is the quietest year for wild fires in Europe by some distance. "
    'Column: "climate change is real and the Right needs to get serious about '
    "it,\" It's killing everything we claim to love - landscape, tradition, "
    "millions of poor chickens"
)


class TestTheRealFailure:
    def test_reciting_tweet_is_caught_with_no_subjects(self):
        """The exact reference that was labelled `supports` 10/10 in production."""
        assert recital_match(None, RIDLEY_TWEET, [], CLAIM) is not None

    def test_it_was_previously_missed(self):
        """Guards the guard: with no claim text there is nothing to match on,
        which is precisely the state the gate ran in before this fix."""
        assert recital_match(None, RIDLEY_TWEET, [], None) is None

    def test_despacing_is_what_makes_it_match(self):
        """The tweet writes 'wild fires' where the claim writes 'wildfires'.

        Any word-boundary comparison misses this. If someone 'simplifies'
        _squash to keep whitespace, this fails.
        """
        entry = claim_restatement_match(RIDLEY_TWEET, CLAIM)
        assert entry is not None
        assert entry["marker"] == "restates the claim"
        assert int(entry["matched_chars"]) >= 40


class TestDoesNotOverFire:
    """Over-firing hides genuine evidence. Invariant #7 cuts both ways."""

    def test_factcheck_quoting_the_claim_is_untouched(self):
        """Carbon Brief quotes the claim in order to demolish it.

        If this fires, the gate turns a challenge into context and the record
        goes soft on exactly the source that did the work.
        """
        cb = (
            "Factcheck: No, Europe is not having its 'quietest' year for "
            "wildfires. Carbon Brief shows the area burned across the EU in "
            "2026 is second only to 2022 for this time of year."
        )
        assert claim_restatement_match(cb, CLAIM) is None

    def test_source_reporting_its_own_finding_is_untouched(self):
        text = (
            "Satellite data show that 91,000 hectares have burnt in France as "
            "of 29 July, smashing the previous record."
        )
        assert claim_restatement_match(text, CLAIM) is None

    def test_topically_related_source_is_untouched(self):
        text = (
            "Wildfires up 57% in Europe in just four years, WHO warns. The "
            "flames have forced evacuations across France and Spain."
        )
        assert claim_restatement_match(text, CLAIM) is None

    def test_short_claims_never_match(self):
        """Short claims share wording with ordinary prose."""
        assert (
            claim_restatement_match("Inflation fell in September.", "Inflation fell")
            is None
        )

    def test_empty_inputs_are_safe(self):
        assert claim_restatement_match("", CLAIM) is None
        assert claim_restatement_match(RIDLEY_TWEET, "") is None
        assert claim_restatement_match(None, None) is None


class TestExistingGuardsSurvive:
    def test_attribution_shaped_elements_still_exempt(self):
        """An element about someone SAYING something is legitimately supported
        by a report of the saying — unchanged behaviour."""
        assert element_asserts_attribution("Ridley claimed 2026 was quiet") is True

    def test_subject_path_still_works_when_subjects_exist(self):
        tokens = [("trump", "Donald Trump")]
        reasoning = "This report states Trump claimed to have settled six wars"
        assert recital_match(reasoning, None, tokens) is not None

    def test_verification_veto_still_beats_the_subject_path(self):
        tokens = [("trump", "Donald Trump")]
        reasoning = "Records show the ceasefire was signed; this contradicts the claim"
        assert recital_match(reasoning, None, tokens) is None

    def test_subject_claims_also_get_the_restatement_fallback(self):
        """A source can recite a claim without naming who made it, so the
        fallback runs even when subjects exist and the wording path was silent.
        """
        tokens = [("ridley", "Matt Ridley")]
        assert recital_match(None, RIDLEY_TWEET, tokens, CLAIM) is not None
